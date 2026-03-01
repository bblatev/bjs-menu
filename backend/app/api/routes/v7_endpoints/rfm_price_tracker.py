"""V7 RFM analytics & price tracker"""
from fastapi import APIRouter, HTTPException, Query, Body, Depends, Path, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional, Dict
from datetime import datetime, timedelta, timezone
from enum import Enum
from decimal import Decimal

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.missing_features_models import (
    SMSCampaign, SMSOptOut, CustomerRFMScore, RFMSegmentDefinition,
    CustomerVIPStatus, VIPTier as VIPTierModel, IngredientPriceHistory,
    EmployeeBreak, BreakPolicy, ShiftTradeRequest, SingleUsePromoCode,
    PromoCodeCampaign, CustomerReferral, MenuItemReview,
    MenuItemRatingAggregate, CustomerDisplay, CateringEvent,
    CateringInvoice, CateringOrderItem, DepositPolicy, PrepTimeModel,
)
from app.models.invoice import PriceAlert
from app.models import Customer, ReservationDeposit
from app.models.operations import ReferralProgram
from app.models.core_business_models import SMSMessage

from app.core.rbac import get_current_user
from app.api.routes.v7_endpoints._helpers import (
    require_manager, verify_venue_access,
    DepositPolicyType, CampaignType, EventType, PromoCodeType,
    VIPTier, ChargebackReason, BlockType,
)

router = APIRouter()

@router.post("/{venue_id}/rfm/configure")
@limiter.limit("30/minute")
async def configure_rfm(
    request: Request,
    venue_id: int,
    recency_bins: List[int] = Body(None),
    frequency_bins: List[int] = Body(None),
    monetary_bins: List[float] = Body(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Configure RFM settings in database"""
    verify_venue_access(venue_id, current_user)
    # Default bins
    default_recency = recency_bins or [7, 30, 60, 90, 180]
    default_frequency = frequency_bins or [1, 3, 5, 10, 20]
    default_monetary = monetary_bins or [50, 100, 250, 500, 1000]

    # Check for existing segment definitions
    existing = db.query(RFMSegmentDefinition).filter(
        RFMSegmentDefinition.venue_id == venue_id
    ).first()

    if existing:
        existing.recency_bins = default_recency
        existing.frequency_bins = default_frequency
        existing.monetary_bins = default_monetary
    else:
        config = RFMSegmentDefinition(
            venue_id=venue_id,
            segment_name="default",
            recency_bins=default_recency,
            frequency_bins=default_frequency,
            monetary_bins=default_monetary,
            is_active=True
        )
        db.add(config)

    db.commit()

    return {
        "venue_id": venue_id,
        "recency_bins": default_recency,
        "frequency_bins": default_frequency,
        "monetary_bins": default_monetary,
        "configured": True
    }

@router.post("/{venue_id}/rfm/calculate/{customer_id}")
@limiter.limit("30/minute")
async def calculate_customer_rfm(
    request: Request,
    venue_id: int,
    customer_id: str,
    orders: List[Dict] = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Calculate and store customer RFM score in database"""
    verify_venue_access(venue_id, current_user)
    try:
        customer_id_int = int(customer_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    if not orders:
        return {"customer_id": customer_id, "error": "No orders provided"}

    # Calculate RFM metrics
    now = datetime.now(timezone.utc)
    order_dates = [datetime.fromisoformat(o.get("order_date", o.get("date", now.isoformat()))) for o in orders if o.get("order_date") or o.get("date")]
    order_amounts = [float(o.get("total", o.get("amount", 0))) for o in orders]

    if order_dates:
        most_recent = max(order_dates)
        recency_days = (now - most_recent).days
    else:
        recency_days = 999

    frequency = len(orders)
    monetary = sum(order_amounts)

    # Calculate RFM scores (1-5 scale)
    def score_recency(days):
        if days <= 7: return 5
        if days <= 30: return 4
        if days <= 60: return 3
        if days <= 90: return 2
        return 1

    def score_frequency(count):
        if count >= 20: return 5
        if count >= 10: return 4
        if count >= 5: return 3
        if count >= 3: return 2
        return 1

    def score_monetary(amount):
        if amount >= 1000: return 5
        if amount >= 500: return 4
        if amount >= 250: return 3
        if amount >= 100: return 2
        return 1

    r_score = score_recency(recency_days)
    f_score = score_frequency(frequency)
    m_score = score_monetary(monetary)

    rfm_score = f"{r_score}{f_score}{m_score}"

    # Determine segment
    total_score = r_score + f_score + m_score
    if total_score >= 13:
        segment = "champions"
    elif total_score >= 10:
        segment = "loyal_customers"
    elif r_score >= 4:
        segment = "potential_loyalists"
    elif r_score <= 2 and f_score >= 3:
        segment = "at_risk"
    elif r_score <= 2:
        segment = "hibernating"
    else:
        segment = "promising"

    # Store in database
    existing = db.query(CustomerRFMScore).filter(
        CustomerRFMScore.venue_id == venue_id,
        CustomerRFMScore.customer_id == customer_id_int
    ).first()

    if existing:
        existing.recency_score = r_score
        existing.frequency_score = f_score
        existing.monetary_score = m_score
        existing.rfm_score = rfm_score
        existing.segment = segment
        existing.days_since_last_order = recency_days
        existing.total_orders = frequency
        existing.total_revenue = Decimal(str(monetary))
        existing.calculated_at = now
    else:
        rfm = CustomerRFMScore(
            venue_id=venue_id,
            customer_id=customer_id_int,
            recency_score=r_score,
            frequency_score=f_score,
            monetary_score=m_score,
            rfm_score=rfm_score,
            segment=segment,
            days_since_last_order=recency_days,
            total_orders=frequency,
            total_revenue=Decimal(str(monetary)),
            calculated_at=now
        )
        db.add(rfm)

    db.commit()

    return {
        "customer_id": customer_id,
        "rfm_score": rfm_score,
        "segment": segment,
        "recency_days": recency_days,
        "frequency": frequency,
        "monetary": round(monetary, 2)
    }

@router.get("/{venue_id}/rfm/segments")
@limiter.limit("60/minute")
async def get_rfm_segments(request: Request, venue_id: int, db: Session = Depends(get_db)):
    """Get distribution of customers across RFM segments from database"""
    # Query segment distribution from database
    segment_counts = db.query(
        CustomerRFMScore.segment,
        func.count(CustomerRFMScore.id).label('count')
    ).filter(
        CustomerRFMScore.venue_id == venue_id
    ).group_by(CustomerRFMScore.segment).all()

    total_customers = sum(count for _, count in segment_counts)

    if total_customers == 0:
        return {"total_customers": 0, "segments": {}}

    segments = {}
    for segment, count in segment_counts:
        segments[segment] = {
            "count": count,
            "percentage": round(count / total_customers * 100, 1)
        }

    return {
        "total_customers": total_customers,
        "segments": segments,
        "calculated_at": datetime.now(timezone.utc).isoformat()
    }

@router.get("/{venue_id}/rfm/segments/{segment}/customers")
@limiter.limit("60/minute")
async def get_segment_customers(request: Request, venue_id: int, segment: str, limit: int = Query(100), db: Session = Depends(get_db)):
    """Get customers in a specific RFM segment from database"""
    # Query customers in segment from database
    customers = db.query(CustomerRFMScore).filter(
        CustomerRFMScore.venue_id == venue_id,
        CustomerRFMScore.segment == segment
    ).order_by(CustomerRFMScore.total_revenue.desc()).limit(limit).all()

    return [
        {
            "customer_id": c.customer_id,
            "recency_days": c.days_since_last_order,
            "frequency": c.total_orders,
            "monetary": float(c.total_revenue) if c.total_revenue else 0,
            "rfm_score": c.rfm_score
        }
        for c in customers
    ]

@router.get("/{venue_id}/rfm/segments/{segment}/recommendations")
@limiter.limit("60/minute")
async def get_segment_recommendations(
    request: Request,
    venue_id: int,
    segment: str,
    db: Session = Depends(get_db)
):
    """Get marketing recommendations for RFM segment"""
    recommendations = {
        "champions": {
            "segment": "champions",
            "description": "Best customers - highest value, most engaged",
            "actions": [
                "Offer exclusive VIP benefits",
                "Early access to new menu items",
                "Personal thank you notes",
                "Invite to exclusive events"
            ],
            "discount_recommendation": "5-10% loyalty rewards"
        },
        "loyal_customers": {
            "segment": "loyal_customers",
            "description": "Regular customers with high value",
            "actions": [
                "Upsell premium items",
                "Loyalty program bonuses",
                "Birthday special offers"
            ],
            "discount_recommendation": "10-15% on special occasions"
        },
        "potential_loyalists": {
            "segment": "potential_loyalists",
            "description": "Recent customers with growth potential",
            "actions": [
                "Send personalized recommendations",
                "Invite to loyalty program",
                "Offer incentives for repeat visits"
            ],
            "discount_recommendation": "15% next visit discount"
        },
        "at_risk": {
            "segment": "at_risk",
            "description": "Previously active customers showing decline",
            "actions": [
                "Win-back campaign",
                "Survey for feedback",
                "Strong discount incentive"
            ],
            "discount_recommendation": "25-30% win-back offer"
        },
        "hibernating": {
            "segment": "hibernating",
            "description": "Inactive customers",
            "actions": [
                "Re-engagement email campaign",
                "Major promotional offer",
                "New menu announcements"
            ],
            "discount_recommendation": "30-40% reactivation offer"
        },
        "promising": {
            "segment": "promising",
            "description": "New or occasional customers",
            "actions": [
                "Welcome series",
                "Loyalty program invitation",
                "First purchase follow-up"
            ],
            "discount_recommendation": "20% second visit discount"
        }
    }

    return recommendations.get(segment, {
        "segment": segment,
        "description": "Unknown segment",
        "actions": ["Review customer data"],
        "discount_recommendation": "Standard promotions"
    })


# ============================================================================
# TIER 2: PRICE TRACKER (4 endpoints)
# ============================================================================

@router.post("/{venue_id}/price-tracker/record")
@limiter.limit("30/minute")
async def record_ingredient_price(
    request: Request,
    venue_id: int,
    ingredient_id: str = Body(...),
    supplier_id: str = Body(...),
    unit_price: float = Body(...),
    quantity: float = Body(1),
    unit: str = Body("kg"),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Record ingredient price in database"""
    verify_venue_access(venue_id, current_user)
    try:
        ingredient_id_int = int(ingredient_id)
        supplier_id_int = int(supplier_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    record = IngredientPriceHistory(
        venue_id=venue_id,
        stock_item_id=ingredient_id_int,
        supplier_id=supplier_id_int,
        price=Decimal(str(unit_price)),
        quantity=Decimal(str(quantity)),
        unit=unit,
        recorded_date=datetime.now(timezone.utc).date()
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return {"record_id": record.id, "unit_price": float(record.price)}

@router.post("/{venue_id}/price-tracker/alerts")
@limiter.limit("30/minute")
async def create_price_alert(
    request: Request,
    venue_id: int,
    ingredient_id: str = Body(...),
    alert_type: str = Body(...),
    threshold_percentage: float = Body(10.0),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Create price alert in database"""
    verify_venue_access(venue_id, current_user)
    try:
        ingredient_id_int = int(ingredient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    alert = PriceAlert(
        venue_id=venue_id,
        stock_item_id=ingredient_id_int,
        alert_type=alert_type,
        threshold_percentage=Decimal(str(threshold_percentage)),
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )

    db.add(alert)
    db.commit()
    db.refresh(alert)

    return {"alert_id": alert.id}

@router.get("/{venue_id}/price-tracker/{ingredient_id}/history")
@limiter.limit("60/minute")
async def get_price_history(request: Request, venue_id: int, ingredient_id: str, days: int = Query(90), db: Session = Depends(get_db)):
    """Get price history for an ingredient from database"""
    try:
        ingredient_id_int = int(ingredient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid venue_id or ingredient_id format")

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Query price history from database
    records = db.query(IngredientPriceHistory).filter(
        IngredientPriceHistory.venue_id == venue_id,
        IngredientPriceHistory.stock_item_id == ingredient_id_int,
        IngredientPriceHistory.recorded_date >= cutoff.date()
    ).order_by(IngredientPriceHistory.recorded_date.asc()).all()

    if not records:
        return {
            "ingredient_id": ingredient_id,
            "records": [],
            "statistics": None
        }

    prices = [float(r.price) for r in records]

    # Calculate statistics
    current_price = prices[-1] if prices else 0
    avg_price = sum(prices) / len(prices) if prices else 0
    min_price = min(prices) if prices else 0
    max_price = max(prices) if prices else 0

    # Calculate price changes
    def calculate_change(days_back: int) -> Optional[float]:
        if len(records) < 2:
            return None
        cutoff_date = datetime.now(timezone.utc).date() - timedelta(days=days_back)
        old_records = [r for r in records if r.recorded_date >= cutoff_date]
        if len(old_records) < 2:
            return None
        old_price = float(old_records[0].price)
        new_price = float(old_records[-1].price)
        if old_price == 0:
            return None
        return round(((new_price - old_price) / old_price) * 100, 2)

    # Calculate volatility (standard deviation)
    if len(prices) > 1:
        mean = sum(prices) / len(prices)
        variance = sum((p - mean) ** 2 for p in prices) / len(prices)
        volatility = variance ** 0.5
    else:
        volatility = 0

    return {
        "ingredient_id": ingredient_id,
        "records": [
            {
                "price": float(r.price),
                "supplier_id": r.supplier_id,
                "date": r.recorded_date.isoformat()
            }
            for r in records
        ],
        "statistics": {
            "current_price": round(current_price, 2),
            "average_price": round(avg_price, 2),
            "min_price": round(min_price, 2),
            "max_price": round(max_price, 2),
            "price_change_30d": calculate_change(30),
            "price_change_90d": calculate_change(90),
            "volatility": round(volatility, 2)
        }
    }

@router.get("/{venue_id}/price-tracker/{ingredient_id}/compare")
@limiter.limit("60/minute")
async def compare_supplier_prices(
    request: Request,
    venue_id: int,
    ingredient_id: str,
    db: Session = Depends(get_db)
):
    """Compare prices across suppliers from database"""
    try:
        ingredient_id_int = int(ingredient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    # Get most recent prices by supplier
    from sqlalchemy import distinct

    # Get all suppliers for this ingredient
    supplier_ids = db.query(distinct(IngredientPriceHistory.supplier_id)).filter(
        IngredientPriceHistory.venue_id == venue_id,
        IngredientPriceHistory.stock_item_id == ingredient_id_int
    ).all()

    comparisons = []
    for (supplier_id,) in supplier_ids:
        # Get most recent price for this supplier
        latest = db.query(IngredientPriceHistory).filter(
            IngredientPriceHistory.venue_id == venue_id,
            IngredientPriceHistory.stock_item_id == ingredient_id_int,
            IngredientPriceHistory.supplier_id == supplier_id
        ).order_by(IngredientPriceHistory.recorded_date.desc()).first()

        if latest:
            comparisons.append({
                "supplier_id": supplier_id,
                "price": float(latest.price),
                "unit": latest.unit,
                "last_updated": latest.recorded_date.isoformat()
            })

    # Sort by price
    comparisons.sort(key=lambda x: x["price"])

    best_price = comparisons[0]["price"] if comparisons else 0

    return {
        "ingredient_id": ingredient_id,
        "comparisons": comparisons,
        "best_price": best_price,
        "recommended_supplier_id": comparisons[0]["supplier_id"] if comparisons else None
    }



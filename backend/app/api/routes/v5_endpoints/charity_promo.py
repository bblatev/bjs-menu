"""V5 sub-module: Fundraising, Promo Codes & Smart Quote"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Optional
from datetime import datetime, date, timezone, time, timedelta
from decimal import Decimal
from pydantic import BaseModel
import secrets

from app.db.session import get_db
from app.models import (
    MarketingCampaign, Customer, Order, MenuItem, StaffUser, OrderItem,
    Reservation, ReservationDeposit, DepositStatus, VenueSettings,
    Promotion, PromotionUsage, Table, StaffShift
)
from app.models.platform_compat import OrderStatus
from app.models.missing_features_models import (
    CateringEvent, CateringEventStatus, CateringOrderItem, CateringInvoice,
    CustomerReferral, VIPTier, CustomerVIPStatus, GuestbookEntry,
    Chargeback, ChargebackStatus, TaxReport, MenuPairing,
    CustomerDisplay, CustomerDisplayContent, FundraisingCampaign, FundraisingDonation,
    TableBlock, EmployeeBreak,
    ShiftTradeRequest as ShiftTradeRequestModel, EmployeeOnboarding,
    OnboardingChecklist, OnboardingTask, OnboardingTaskCompletion,
    IngredientPriceHistory, PriceAlertNotification, MenuItemReview,
    PrepTimePrediction
)
from app.models.operations import ReferralProgram
from app.models.invoice import PriceAlert
from app.models.core_business_models import SMSMessage
from app.models import StockItem
from dateutil.relativedelta import relativedelta
from calendar import monthrange
from app.core.rate_limit import limiter
from app.api.routes.v5_endpoints._schemas import *

router = APIRouter()

# ==================== FUNDRAISING ====================

@router.post("/charity/campaigns")
@limiter.limit("30/minute")
async def create_charity_campaign(
    request: Request,
    venue_id: int = Query(1),
    charity_name: str = Body(...),
    goal_amount: Optional[float] = Body(None),
    description: Optional[str] = Body(None),
    campaign_type: str = Body("round_up"),
    prompt_message: Optional[str] = Body(None),
    thank_you_message: Optional[str] = Body(None),
    start_date: Optional[date] = Body(None),
    end_date: Optional[date] = Body(None),
    db: Session = Depends(get_db)
):
    """Create charity campaign with database persistence"""
    campaign = FundraisingCampaign(
        venue_id=venue_id,
        name=charity_name,
        organization_name=charity_name,
        description=description,
        campaign_type=campaign_type,
        goal_amount=goal_amount,
        raised_amount=0,
        donation_count=0,
        prompt_message=prompt_message,
        thank_you_message=thank_you_message,
        start_date=start_date or date.today(),
        end_date=end_date,
        is_active=True
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    return {
        "id": campaign.id,
        "charity_name": campaign.name,
        "organization_name": campaign.organization_name,
        "campaign_type": campaign.campaign_type,
        "goal_amount": float(campaign.goal_amount) if campaign.goal_amount else None,
        "total_raised": float(campaign.raised_amount) if campaign.raised_amount else 0,
        "donation_count": campaign.donation_count,
        "is_active": campaign.is_active,
        "start_date": campaign.start_date.isoformat() if campaign.start_date else None,
        "end_date": campaign.end_date.isoformat() if campaign.end_date else None
    }

@router.get("/charity/campaigns")
@limiter.limit("60/minute")
async def list_charity_campaigns(
    request: Request,
    venue_id: int = Query(1),
    active_only: bool = Query(True),
    db: Session = Depends(get_db)
):
    """List all charity campaigns for a venue"""
    query = db.query(FundraisingCampaign).filter(FundraisingCampaign.venue_id == venue_id)
    if active_only:
        query = query.filter(FundraisingCampaign.is_active == True)

    campaigns = query.order_by(FundraisingCampaign.created_at.desc()).all()

    return {
        "campaigns": [
            {
                "id": c.id,
                "name": c.name,
                "organization_name": c.organization_name,
                "campaign_type": c.campaign_type,
                "goal_amount": float(c.goal_amount) if c.goal_amount else None,
                "raised_amount": float(c.raised_amount) if c.raised_amount else 0,
                "donation_count": c.donation_count,
                "goal_progress": (float(c.raised_amount) / float(c.goal_amount) * 100) if c.goal_amount and c.raised_amount else 0,
                "is_active": c.is_active,
                "start_date": c.start_date.isoformat() if c.start_date else None,
                "end_date": c.end_date.isoformat() if c.end_date else None
            }
            for c in campaigns
        ],
        "total": len(campaigns)
    }

@router.get("/charity/campaigns/{campaign_id}")
@limiter.limit("60/minute")
async def get_charity_campaign(
    request: Request,
    campaign_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific charity campaign"""
    campaign = db.query(FundraisingCampaign).filter(FundraisingCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    return {
        "id": campaign.id,
        "venue_id": campaign.venue_id,
        "name": campaign.name,
        "description": campaign.description,
        "organization_name": campaign.organization_name,
        "organization_logo_url": campaign.organization_logo_url,
        "campaign_type": campaign.campaign_type,
        "round_up_to": float(campaign.round_up_to) if campaign.round_up_to else None,
        "fixed_amount": float(campaign.fixed_amount) if campaign.fixed_amount else None,
        "percentage": campaign.percentage,
        "goal_amount": float(campaign.goal_amount) if campaign.goal_amount else None,
        "raised_amount": float(campaign.raised_amount) if campaign.raised_amount else 0,
        "donation_count": campaign.donation_count,
        "prompt_message": campaign.prompt_message,
        "thank_you_message": campaign.thank_you_message,
        "is_active": campaign.is_active,
        "start_date": campaign.start_date.isoformat() if campaign.start_date else None,
        "end_date": campaign.end_date.isoformat() if campaign.end_date else None,
        "created_at": campaign.created_at.isoformat() if campaign.created_at else None
    }

@router.post("/charity/donations/round-up")
@limiter.limit("30/minute")
async def process_round_up(
    request: Request,
    campaign_id: int = Body(...),
    order_id: int = Body(...),
    original_total: float = Body(...),
    customer_id: Optional[int] = Body(None),
    db: Session = Depends(get_db)
):
    """Process round-up donation with database persistence"""
    import math

    # Verify campaign exists and is active
    campaign = db.query(FundraisingCampaign).filter(
        FundraisingCampaign.id == campaign_id,
        FundraisingCampaign.is_active == True
    ).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found or inactive")

    # Calculate round-up amount
    rounded = math.ceil(original_total)
    donation_amount = rounded - original_total
    if donation_amount <= 0:
        donation_amount = 1.00
        rounded = original_total + 1

    # Create donation record
    donation = FundraisingDonation(
        campaign_id=campaign_id,
        order_id=order_id,
        customer_id=customer_id,
        amount=donation_amount,
        original_total=original_total,
        rounded_total=rounded
    )
    db.add(donation)

    # Update campaign totals
    campaign.raised_amount = (campaign.raised_amount or 0) + Decimal(str(donation_amount))
    campaign.donation_count = (campaign.donation_count or 0) + 1

    db.commit()
    db.refresh(donation)

    return {
        "id": donation.id,
        "campaign_id": campaign_id,
        "donation_amount": float(donation.amount),
        "original_total": float(donation.original_total),
        "new_total": float(donation.rounded_total),
        "campaign_total_raised": float(campaign.raised_amount)
    }

@router.post("/charity/donations/flat")
@limiter.limit("30/minute")
async def process_flat_donation(
    request: Request,
    donation: CharityDonation,
    customer_id: Optional[int] = Body(None),
    db: Session = Depends(get_db)
):
    """Process flat donation with database persistence"""
    # Verify campaign exists and is active
    campaign = db.query(FundraisingCampaign).filter(
        FundraisingCampaign.id == donation.campaign_id,
        FundraisingCampaign.is_active == True
    ).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found or inactive")

    # Create donation record
    db_donation = FundraisingDonation(
        campaign_id=donation.campaign_id,
        order_id=donation.order_id,
        customer_id=customer_id,
        amount=donation.amount
    )
    db.add(db_donation)

    # Update campaign totals
    campaign.raised_amount = (campaign.raised_amount or 0) + Decimal(str(donation.amount))
    campaign.donation_count = (campaign.donation_count or 0) + 1

    db.commit()
    db.refresh(db_donation)

    return {
        "id": db_donation.id,
        "campaign_id": donation.campaign_id,
        "amount": float(db_donation.amount),
        "campaign_total_raised": float(campaign.raised_amount),
        "campaign_donation_count": campaign.donation_count
    }

@router.get("/charity/campaigns/{campaign_id}/stats")
@limiter.limit("60/minute")
async def get_campaign_stats(
    request: Request,
    campaign_id: int,
    db: Session = Depends(get_db)
):
    """Get charity campaign statistics from database"""
    campaign = db.query(FundraisingCampaign).filter(FundraisingCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Calculate goal progress
    goal_progress = 0.0
    if campaign.goal_amount and campaign.raised_amount:
        goal_progress = (float(campaign.raised_amount) / float(campaign.goal_amount)) * 100

    # Get donation statistics
    donations = db.query(FundraisingDonation).filter(
        FundraisingDonation.campaign_id == campaign_id
    ).all()

    avg_donation = 0.0
    if donations:
        total = sum(float(d.amount) for d in donations)
        avg_donation = total / len(donations)

    return {
        "campaign_id": campaign_id,
        "campaign_name": campaign.name,
        "total_raised": float(campaign.raised_amount) if campaign.raised_amount else 0,
        "goal_amount": float(campaign.goal_amount) if campaign.goal_amount else None,
        "donation_count": campaign.donation_count or 0,
        "goal_progress": round(goal_progress, 2),
        "average_donation": round(avg_donation, 2),
        "is_active": campaign.is_active,
        "days_remaining": (campaign.end_date - date.today()).days if campaign.end_date else None
    }

@router.get("/charity/campaigns/{campaign_id}/donations")
@limiter.limit("60/minute")
async def get_campaign_donations(
    request: Request,
    campaign_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get donations for a specific campaign"""
    campaign = db.query(FundraisingCampaign).filter(FundraisingCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    total_count = db.query(func.count(FundraisingDonation.id)).filter(
        FundraisingDonation.campaign_id == campaign_id
    ).scalar()

    donations = db.query(FundraisingDonation).filter(
        FundraisingDonation.campaign_id == campaign_id
    ).order_by(FundraisingDonation.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "campaign_id": campaign_id,
        "campaign_name": campaign.name,
        "donations": [
            {
                "id": d.id,
                "amount": float(d.amount),
                "order_id": d.order_id,
                "customer_id": d.customer_id,
                "original_total": float(d.original_total) if d.original_total else None,
                "rounded_total": float(d.rounded_total) if d.rounded_total else None,
                "is_tax_deductible": d.is_tax_deductible,
                "created_at": d.created_at.isoformat() if d.created_at else None
            }
            for d in donations
        ],
        "total": total_count,
        "limit": limit,
        "offset": offset
    }

@router.patch("/charity/campaigns/{campaign_id}")
@limiter.limit("30/minute")
async def update_charity_campaign(
    request: Request,
    campaign_id: int,
    is_active: Optional[bool] = Body(None),
    goal_amount: Optional[float] = Body(None),
    end_date: Optional[date] = Body(None),
    prompt_message: Optional[str] = Body(None),
    thank_you_message: Optional[str] = Body(None),
    db: Session = Depends(get_db)
):
    """Update a charity campaign"""
    campaign = db.query(FundraisingCampaign).filter(FundraisingCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if is_active is not None:
        campaign.is_active = is_active
    if goal_amount is not None:
        campaign.goal_amount = goal_amount
    if end_date is not None:
        campaign.end_date = end_date
    if prompt_message is not None:
        campaign.prompt_message = prompt_message
    if thank_you_message is not None:
        campaign.thank_you_message = thank_you_message

    db.commit()
    db.refresh(campaign)

    return {
        "id": campaign.id,
        "name": campaign.name,
        "is_active": campaign.is_active,
        "goal_amount": float(campaign.goal_amount) if campaign.goal_amount else None,
        "raised_amount": float(campaign.raised_amount) if campaign.raised_amount else 0,
        "updated": True
    }

# ==================== PROMO CODES ====================

@router.post("/promo-codes/generate")
@limiter.limit("30/minute")
async def generate_promo_codes(
    request: Request,
    config: PromoCodeGenerate,
    venue_id: int = Query(1),
    db: Session = Depends(get_db)
):
    """Generate single-use promo codes and save them to the database"""
    created_promotions = []

    # Map discount_type to promotion_type
    promotion_type = "percentage" if config.discount_type == "percentage" else "fixed"

    for i in range(config.count):
        # Generate unique code
        code = ''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(8))

        # Create promotion in database
        promotion = Promotion(
            venue_id=venue_id,
            name=f"Promo Code {code}",
            description=f"Auto-generated promo code",
            promotion_type=promotion_type,
            discount_value=config.discount_value,
            promo_code=code,
            min_order_amount=config.minimum_order,
            start_date=datetime.now(timezone.utc),
            end_date=datetime.now(timezone.utc) + timedelta(days=config.valid_days),
            max_uses=1,  # Single-use codes
            uses_count=0,
            is_active=True
        )
        db.add(promotion)
        created_promotions.append({
            "code": code,
            "discount_type": config.discount_type,
            "discount_value": config.discount_value,
            "valid_until": (datetime.now(timezone.utc) + timedelta(days=config.valid_days)).isoformat(),
            "minimum_order": config.minimum_order
        })

    db.commit()

    return {"codes": created_promotions, "count": len(created_promotions)}

@router.post("/promo-codes/validate")
@limiter.limit("30/minute")
async def validate_promo_code(
    request: Request,
    code: str = Body(...),
    order_total: float = Body(...),
    venue_id: int = Body(1),
    db: Session = Depends(get_db)
):
    """Validate promo code against the database"""
    # Look up the promotion by promo_code
    promotion = db.query(Promotion).filter(
        Promotion.promo_code == code,
        Promotion.is_active == True
    ).first()

    if not promotion:
        return {
            "valid": False,
            "error": "Promo code not found or inactive",
            "discount": 0,
            "new_total": order_total
        }

    # Check if the promotion has expired
    now = datetime.now(timezone.utc)
    if promotion.end_date and promotion.end_date < now:
        return {
            "valid": False,
            "error": "Promo code has expired",
            "discount": 0,
            "new_total": order_total
        }

    if promotion.start_date and promotion.start_date > now:
        return {
            "valid": False,
            "error": "Promo code is not yet valid",
            "discount": 0,
            "new_total": order_total
        }

    # Check if max uses reached
    if promotion.max_uses and promotion.uses_count >= promotion.max_uses:
        return {
            "valid": False,
            "error": "Promo code has reached maximum uses",
            "discount": 0,
            "new_total": order_total
        }

    # Check minimum order amount
    if promotion.min_order_amount and order_total < promotion.min_order_amount:
        return {
            "valid": False,
            "error": f"Minimum order amount is {promotion.min_order_amount}",
            "discount": 0,
            "new_total": order_total
        }

    # Calculate discount
    if promotion.promotion_type == "percentage":
        discount = order_total * (promotion.discount_value / 100)
    else:  # fixed
        discount = min(promotion.discount_value, order_total)  # Don't exceed order total

    new_total = max(0, order_total - discount)

    return {
        "valid": True,
        "promotion_id": promotion.id,
        "promotion_name": promotion.name,
        "promotion_type": promotion.promotion_type,
        "discount": round(discount, 2),
        "new_total": round(new_total, 2)
    }

@router.post("/promo-codes/{code}/redeem")
@limiter.limit("30/minute")
async def redeem_promo_code(
    request: Request,
    code: str,
    order_id: int = Body(...),
    customer_id: Optional[int] = Body(None),
    discount_applied: float = Body(...),
    db: Session = Depends(get_db)
):
    """Redeem promo code and record usage in the database"""
    # Look up the promotion
    promotion = db.query(Promotion).filter(
        Promotion.promo_code == code,
        Promotion.is_active == True
    ).first()

    if not promotion:
        raise HTTPException(status_code=404, detail="Promo code not found or inactive")

    # Check if already at max uses
    if promotion.max_uses and promotion.uses_count >= promotion.max_uses:
        raise HTTPException(status_code=400, detail="Promo code has reached maximum uses")

    # Check if the order exists
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Create promotion usage record
    usage = PromotionUsage(
        promotion_id=promotion.id,
        customer_id=customer_id,
        order_id=order_id,
        discount_applied=discount_applied
    )
    db.add(usage)

    # Increment uses count
    promotion.uses_count = (promotion.uses_count or 0) + 1

    # If single-use and now used, deactivate
    if promotion.max_uses == 1:
        promotion.is_active = False

    db.commit()

    return {
        "code": code,
        "redeemed": True,
        "promotion_id": promotion.id,
        "order_id": order_id,
        "discount_applied": discount_applied,
        "remaining_uses": (promotion.max_uses - promotion.uses_count) if promotion.max_uses else None
    }

# ==================== SMART QUOTE ====================

@router.post("/smart-quote/estimate")
@limiter.limit("30/minute")
async def get_prep_time_estimate(
    request: Request,
    venue_id: int = Query(1),
    order_items: List[Dict] = Body(...),
    order_channel: str = Body("online"),
    order_id: Optional[int] = Body(None),
    db: Session = Depends(get_db)
):
    """Get AI-estimated prep time based on menu item data and current kitchen load"""
    if not order_items:
        raise HTTPException(status_code=400, detail="Order items list cannot be empty")

    # Get current kitchen load (active orders in progress)
    active_orders = db.query(func.count(Order.id)).filter(
        Order.venue_id == venue_id,
        Order.status.in_([OrderStatus.NEW, OrderStatus.ACCEPTED, OrderStatus.PREPARING]),
        Order.created_at >= datetime.now(timezone.utc) - timedelta(hours=2)
    ).scalar() or 0

    # Calculate base prep time from menu items
    total_prep_time = 0
    max_prep_time = 0
    item_details = []
    complexity_score = 0

    for item in order_items:
        menu_item_id = item.get("menu_item_id")
        quantity = item.get("quantity", 1)

        if menu_item_id:
            menu_item = db.query(MenuItem).filter(MenuItem.id == menu_item_id).first()
            if menu_item:
                item_prep = menu_item.preparation_time_minutes or 10
                # For parallel prep, we take max; for sequential items we add
                max_prep_time = max(max_prep_time, item_prep)
                total_prep_time += item_prep * quantity

                # Calculate complexity based on modifiers
                modifiers_count = len(item.get("modifiers", []))
                item_complexity = 1 + (modifiers_count * 0.1)
                complexity_score += item_complexity

                item_details.append({
                    "menu_item_id": menu_item_id,
                    "name": menu_item.name,
                    "quantity": quantity,
                    "base_prep_time": item_prep,
                    "modifiers_count": modifiers_count
                })
            else:
                # Unknown item, use default prep time
                max_prep_time = max(max_prep_time, 10)
                total_prep_time += 10 * quantity
                item_details.append({
                    "menu_item_id": menu_item_id,
                    "name": "Unknown",
                    "quantity": quantity,
                    "base_prep_time": 10,
                    "modifiers_count": 0
                })

    # Number of items affects prep time (parallel prep optimization)
    item_count = sum(item.get("quantity", 1) for item in order_items)

    # Calculate kitchen load factor (0-1 scale, higher means busier)
    kitchen_load_factor = min(active_orders / 10, 1.0)  # Normalize to max 10 orders

    # Apply adjustments
    # Base estimate: Use max prep time (parallel cooking) + some additive for multiple items
    base_estimate = max_prep_time + (item_count - 1) * 2  # Add 2 min per additional item

    # Kitchen load adjustment (up to 50% increase when very busy)
    load_adjustment = 1 + (kitchen_load_factor * 0.5)

    # Channel adjustment
    channel_factors = {
        "online": 1.0,
        "delivery": 1.1,  # Slightly more for packaging
        "dine-in": 0.9,   # Can be slightly faster
        "takeaway": 1.0
    }
    channel_factor = channel_factors.get(order_channel, 1.0)

    # Complexity adjustment
    avg_complexity = complexity_score / len(order_items) if order_items else 1
    complexity_factor = 0.9 + (avg_complexity * 0.1)  # 0.9 to 1.1 range

    # Final estimate
    estimated_minutes = int(base_estimate * load_adjustment * channel_factor * complexity_factor)

    # Calculate confidence based on data quality
    # More menu items found = higher confidence
    items_found = sum(1 for d in item_details if d.get("name") != "Unknown")
    data_confidence = (items_found / len(order_items)) * 100 if order_items else 50

    # Calculate range
    min_minutes = max(5, int(estimated_minutes * 0.7))
    max_minutes = int(estimated_minutes * 1.4)

    # Store prediction for model training
    if order_id:
        prediction = PrepTimePrediction(
            venue_id=venue_id,
            order_id=order_id,
            predicted_minutes=estimated_minutes,
            confidence=data_confidence / 100,
            factors={
                "kitchen_load": kitchen_load_factor,
                "complexity": avg_complexity,
                "channel_factor": channel_factor,
                "item_count": item_count
            },
            day_of_week=datetime.now(timezone.utc).weekday(),
            hour_of_day=datetime.now(timezone.utc).hour,
            current_orders=active_orders,
            item_count=item_count,
            complexity_score=complexity_score
        )
        db.add(prediction)
        db.commit()
        db.refresh(prediction)

    return {
        "estimated_minutes": estimated_minutes,
        "range": {"min": min_minutes, "max": max_minutes},
        "confidence": int(data_confidence),
        "factors": {
            "kitchen_load": round(kitchen_load_factor, 2),
            "active_orders": active_orders,
            "item_count": item_count,
            "complexity_score": round(complexity_score, 2),
            "channel": order_channel
        },
        "item_breakdown": item_details
    }


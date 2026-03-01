"""V5 sub-module: Price Tracker, VIP, Guestbook & Menu Reviews"""
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

# ==================== PRICE TRACKER ====================

@router.post("/price-tracker/record")
@limiter.limit("30/minute")
async def record_price(
    request: Request,
    stock_item_id: int = Body(...),
    supplier_id: int = Body(...),
    unit_price: float = Body(...),
    unit: str = Body("kg"),
    source: str = Body("manual"),
    venue_id: int = Query(1),
    db: Session = Depends(get_db)
):
    """Record ingredient price"""
    # Verify stock item exists
    stock_item = db.query(StockItem).filter(
        StockItem.id == stock_item_id,
        StockItem.venue_id == venue_id
    ).first()
    if not stock_item:
        raise HTTPException(status_code=404, detail="Stock item not found")

    # Create price history record
    price_record = IngredientPriceHistory(
        venue_id=venue_id,
        stock_item_id=stock_item_id,
        supplier_id=supplier_id,
        price=Decimal(str(unit_price)),
        unit=unit,
        recorded_date=date.today(),
        source=source
    )
    db.add(price_record)
    db.commit()
    db.refresh(price_record)

    return {
        "id": price_record.id,
        "stock_item_id": price_record.stock_item_id,
        "stock_item_name": stock_item.name,
        "supplier_id": price_record.supplier_id,
        "unit_price": float(price_record.price),
        "unit": price_record.unit,
        "recorded_date": price_record.recorded_date.isoformat(),
        "source": price_record.source
    }

@router.get("/price-tracker/item/{stock_item_id}/history")
@limiter.limit("60/minute")
async def get_price_history(
    request: Request,
    stock_item_id: int,
    months: int = Query(6),
    venue_id: int = Query(1),
    db: Session = Depends(get_db)
):
    """Get price history for item"""
    # Verify stock item exists
    stock_item = db.query(StockItem).filter(
        StockItem.id == stock_item_id,
        StockItem.venue_id == venue_id
    ).first()
    if not stock_item:
        raise HTTPException(status_code=404, detail="Stock item not found")

    # Calculate start date based on months
    start_date = date.today() - relativedelta(months=months)

    # Get price history from database
    history = db.query(IngredientPriceHistory).filter(
        IngredientPriceHistory.stock_item_id == stock_item_id,
        IngredientPriceHistory.venue_id == venue_id,
        IngredientPriceHistory.recorded_date >= start_date
    ).order_by(IngredientPriceHistory.recorded_date.asc()).all()

    # Calculate price change
    price_change = 0.0
    change_pct = 0.0
    if len(history) >= 2:
        oldest_price = float(history[0].price)
        newest_price = float(history[-1].price)
        price_change = newest_price - oldest_price
        if oldest_price > 0:
            change_pct = (price_change / oldest_price) * 100

    return {
        "stock_item_id": stock_item_id,
        "stock_item_name": stock_item.name,
        "current_unit": stock_item.unit,
        "history": [
            {
                "id": h.id,
                "date": h.recorded_date.isoformat(),
                "price": float(h.price),
                "unit": h.unit,
                "supplier_id": h.supplier_id,
                "source": h.source
            }
            for h in history
        ],
        "total_records": len(history),
        "price_change": round(price_change, 4),
        "change_percentage": round(change_pct, 2)
    }

@router.get("/price-tracker/alerts")
@limiter.limit("60/minute")
async def get_price_alerts(
    request: Request,
    venue_id: int = Query(1),
    unacknowledged: bool = Query(True),
    db: Session = Depends(get_db)
):
    """Get price change alerts"""
    # Get alert notifications (the actual triggered alerts)
    query = db.query(PriceAlertNotification).join(
        PriceAlert,
        PriceAlertNotification.alert_id == PriceAlert.id
    ).filter(
        PriceAlert.is_active == True
    )

    if unacknowledged:
        query = query.filter(PriceAlertNotification.is_read == False)

    notifications = query.order_by(PriceAlertNotification.created_at.desc()).limit(50).all()

    alerts = []
    for n in notifications:
        # Get the parent alert and stock item
        alert = db.query(PriceAlert).filter(PriceAlert.id == n.alert_id).first()
        if alert:
            stock_item = db.query(StockItem).filter(StockItem.id == alert.stock_item_id).first()
            alerts.append({
                "id": n.id,
                "alert_id": alert.id,
                "item_id": alert.stock_item_id,
                "item": stock_item.name if stock_item else "Unknown",
                "old_price": float(n.old_price) if n.old_price else None,
                "new_price": float(n.new_price) if n.new_price else None,
                "change_pct": round(n.change_percentage, 2) if n.change_percentage else 0,
                "alert_type": alert.alert_type,
                "acknowledged": n.is_read,
                "created_at": n.created_at.isoformat() if n.created_at else None
            })

    return {
        "alerts": alerts,
        "total": len(alerts)
    }

@router.post("/price-tracker/alerts/{alert_id}/acknowledge")
@limiter.limit("30/minute")
async def acknowledge_alert(
    request: Request,
    alert_id: int,
    staff_id: Optional[int] = Body(None),
    db: Session = Depends(get_db)
):
    """Acknowledge price alert"""
    # Find the notification
    notification = db.query(PriceAlertNotification).filter(
        PriceAlertNotification.id == alert_id
    ).first()

    if not notification:
        raise HTTPException(status_code=404, detail="Alert notification not found")

    if notification.is_read:
        return {"alert_id": alert_id, "acknowledged": True, "message": "Already acknowledged"}

    # Mark as read
    notification.is_read = True
    notification.read_at = datetime.now(timezone.utc)
    notification.read_by = staff_id

    db.commit()

    return {
        "alert_id": alert_id,
        "acknowledged": True,
        "acknowledged_at": notification.read_at.isoformat()
    }

@router.get("/price-tracker/trends")
@limiter.limit("60/minute")
async def get_price_trends(
    request: Request,
    venue_id: int = Query(1),
    days: int = Query(30),
    db: Session = Depends(get_db)
):
    """Get overall price trends"""
    start_date = date.today() - timedelta(days=days)

    # Get all price records for the period
    recent_prices = db.query(IngredientPriceHistory).filter(
        IngredientPriceHistory.venue_id == venue_id,
        IngredientPriceHistory.recorded_date >= start_date
    ).all()

    # Group by stock_item_id and calculate trends
    item_prices = {}
    for p in recent_prices:
        if p.stock_item_id not in item_prices:
            item_prices[p.stock_item_id] = []
        item_prices[p.stock_item_id].append({
            "date": p.recorded_date,
            "price": float(p.price)
        })

    items_increased = 0
    items_decreased = 0
    items_stable = 0
    total_change = 0.0
    items_with_change = 0

    for item_id, prices in item_prices.items():
        if len(prices) >= 2:
            # Sort by date
            sorted_prices = sorted(prices, key=lambda x: x["date"])
            first_price = sorted_prices[0]["price"]
            last_price = sorted_prices[-1]["price"]

            if first_price > 0:
                change_pct = ((last_price - first_price) / first_price) * 100
                total_change += change_pct
                items_with_change += 1

                if change_pct > 1:  # More than 1% increase
                    items_increased += 1
                elif change_pct < -1:  # More than 1% decrease
                    items_decreased += 1
                else:
                    items_stable += 1

    overall_change = total_change / items_with_change if items_with_change > 0 else 0

    return {
        "venue_id": venue_id,
        "period_days": days,
        "overall_change": round(overall_change, 2),
        "items_increased": items_increased,
        "items_decreased": items_decreased,
        "items_stable": items_stable,
        "total_items_tracked": len(item_prices),
        "total_price_records": len(recent_prices)
    }

# ==================== VIP & CUSTOMER ENGAGEMENT ====================

@router.post("/vip/profiles")
@limiter.limit("30/minute")
async def create_vip_profile(
    request: Request,
    customer_id: int = Body(...),
    venue_id: int = Query(1),
    vip_tier: str = Body("silver"),
    db: Session = Depends(get_db)
):
    """Create VIP profile - assigns a VIP tier to a customer"""
    # Verify customer exists
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.location_id == venue_id
    ).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Find or create VIP tier
    tier = db.query(VIPTier).filter(
        VIPTier.venue_id == venue_id,
        VIPTier.name.ilike(vip_tier)
    ).first()

    if not tier:
        # Create the tier if it doesn't exist
        tier = VIPTier(
            venue_id=venue_id,
            name=vip_tier.capitalize(),
            description=f"{vip_tier.capitalize()} tier VIP customer",
            is_active=True
        )
        db.add(tier)
        db.flush()

    # Check if VIP status already exists
    existing_status = db.query(CustomerVIPStatus).filter(
        CustomerVIPStatus.customer_id == customer_id,
        CustomerVIPStatus.venue_id == venue_id
    ).first()

    if existing_status:
        # Update existing status
        existing_status.vip_tier_id = tier.id
        existing_status.is_active = True
        db.commit()
        return {
            "id": existing_status.id,
            "customer_id": customer_id,
            "vip_tier": tier.name,
            "updated": True
        }

    # Create new VIP status
    vip_status = CustomerVIPStatus(
        venue_id=venue_id,
        customer_id=customer_id,
        vip_tier_id=tier.id,
        assigned_date=date.today(),
        assignment_reason="manual",
        is_active=True
    )
    db.add(vip_status)

    # Also update customer loyalty_tier for consistency
    customer.loyalty_tier = vip_tier.lower()

    db.commit()
    db.refresh(vip_status)

    return {
        "id": vip_status.id,
        "customer_id": customer_id,
        "vip_tier": tier.name,
        "created": True
    }

@router.get("/vip/profiles/{customer_id}")
@limiter.limit("60/minute")
async def get_vip_profile(
    request: Request,
    customer_id: int,
    venue_id: int = Query(1),
    db: Session = Depends(get_db)
):
    """Get VIP profile for a customer"""
    # Get customer with their VIP status
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.location_id == venue_id
    ).first()

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Get VIP status if exists
    vip_status = db.query(CustomerVIPStatus).filter(
        CustomerVIPStatus.customer_id == customer_id,
        CustomerVIPStatus.venue_id == venue_id,
        CustomerVIPStatus.is_active == True
    ).first()

    vip_tier_name = customer.loyalty_tier or "bronze"
    preferences = {}

    if vip_status:
        # Get tier details
        tier = db.query(VIPTier).filter(VIPTier.id == vip_status.vip_tier_id).first()
        if tier:
            vip_tier_name = tier.name
        preferences = vip_status.preferences or {}

    return {
        "customer_id": customer_id,
        "vip_tier": vip_tier_name,
        "preferences": preferences,
        "lifetime_spend": float(customer.total_spent or 0),
        "total_orders": customer.total_orders or 0,
        "loyalty_points": customer.loyalty_points or 0,
        "last_visit": customer.last_visit.isoformat() if customer.last_visit else None
    }

@router.get("/vip/upcoming-occasions")
@limiter.limit("60/minute")
async def get_upcoming_occasions(
    request: Request,
    venue_id: int = Query(1),
    days: int = Query(30),
    db: Session = Depends(get_db)
):
    """Get upcoming VIP occasions (birthdays, anniversaries) for VIP customers"""
    today = date.today()
    end_date = today + timedelta(days=days)

    # Get VIP customers (those with VIP status or high loyalty tier)
    vip_customers = db.query(Customer).join(
        CustomerVIPStatus,
        (CustomerVIPStatus.customer_id == Customer.id) &
        (CustomerVIPStatus.venue_id == venue_id) &
        (CustomerVIPStatus.is_active == True)
    ).filter(
        Customer.location_id == venue_id,
        Customer.deleted_at.is_(None)
    ).all()

    # Customer model doesn't have loyalty_tier column, so skip that filter
    # All VIP customers come from the CustomerVIPStatus join above
    all_vip_customers = {c.id: c for c in vip_customers}

    occasions = []
    for customer in all_vip_customers.values():
        if customer.birthday:
            # Check if birthday falls within the date range (ignoring year)
            bday = customer.birthday
            this_year_bday = date(today.year, bday.month, bday.day)
            if today <= this_year_bday <= end_date:
                occasions.append({
                    "customer_id": customer.id,
                    "customer_name": customer.name,
                    "occasion_type": "birthday",
                    "occasion_date": this_year_bday.isoformat(),
                    "days_until": (this_year_bday - today).days,
                    "loyalty_tier": getattr(customer, 'segment', None) or "vip"
                })

    # Sort by date
    occasions.sort(key=lambda x: x["days_until"])

    return {"occasions": occasions, "total": len(occasions)}

@router.post("/guestbook/entries")
@limiter.limit("30/minute")
async def create_guestbook_entry(
    request: Request,
    venue_id: int = Query(1),
    customer_id: Optional[int] = Body(None),
    guest_name: Optional[str] = Body(None),
    guest_email: Optional[str] = Body(None),
    message: str = Body(...),
    rating: Optional[int] = Body(None),
    visit_date: Optional[date] = Body(None),
    occasion: Optional[str] = Body(None),
    db: Session = Depends(get_db)
):
    """Create guestbook entry"""
    # Validate rating if provided
    if rating is not None and (rating < 1 or rating > 5):
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    # Get customer name if customer_id provided
    if customer_id and not guest_name:
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if customer:
            guest_name = customer.name
            guest_email = guest_email or customer.email

    entry = GuestbookEntry(
        venue_id=venue_id,
        customer_id=customer_id,
        guest_name=guest_name,
        guest_email=guest_email,
        message=message,
        rating=rating,
        visit_date=visit_date or date.today(),
        occasion=occasion,
        is_approved=False,  # Requires moderation
        is_public=True,
        show_name=True
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    return {
        "id": entry.id,
        "venue_id": entry.venue_id,
        "guest_name": entry.guest_name,
        "message": entry.message,
        "rating": entry.rating,
        "visit_date": entry.visit_date.isoformat() if entry.visit_date else None,
        "occasion": entry.occasion,
        "is_approved": entry.is_approved,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
        "recorded": True
    }

@router.get("/guestbook/entries")
@limiter.limit("60/minute")
async def list_guestbook_entries(
    request: Request,
    venue_id: int = Query(1),
    approved_only: bool = Query(True),
    featured_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get guestbook entries for a venue"""
    query = db.query(GuestbookEntry).filter(GuestbookEntry.venue_id == venue_id)

    if approved_only:
        query = query.filter(GuestbookEntry.is_approved == True)
    if featured_only:
        query = query.filter(GuestbookEntry.is_featured == True)

    total = query.count()
    entries = query.order_by(GuestbookEntry.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "entries": [
            {
                "id": e.id,
                "guest_name": e.guest_name if e.show_name else "Anonymous",
                "message": e.message,
                "rating": e.rating,
                "visit_date": e.visit_date.isoformat() if e.visit_date else None,
                "occasion": e.occasion,
                "is_featured": e.is_featured,
                "photo_urls": e.photo_urls,
                "created_at": e.created_at.isoformat() if e.created_at else None
            }
            for e in entries
        ],
        "total": total,
        "limit": limit,
        "offset": offset
    }

@router.get("/guestbook/customer/{customer_id}/history")
@limiter.limit("60/minute")
async def get_visit_history(
    request: Request,
    customer_id: int,
    venue_id: int = Query(1),
    limit: int = Query(20),
    db: Session = Depends(get_db)
):
    """Get customer visit history from guestbook and orders"""
    # Verify customer exists
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.location_id == venue_id
    ).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Get guestbook entries
    guestbook_visits = db.query(GuestbookEntry).filter(
        GuestbookEntry.customer_id == customer_id,
        GuestbookEntry.venue_id == venue_id
    ).order_by(GuestbookEntry.visit_date.desc()).limit(limit).all()

    # Get order-based visits (dine-in orders indicate visits)
    order_visits = db.query(Order).filter(
        Order.customer_id == customer_id,
        Order.venue_id == venue_id,
        Order.order_type == "dine-in"
    ).order_by(Order.created_at.desc()).limit(limit).all()

    visits = []

    # Add guestbook entries
    for g in guestbook_visits:
        visits.append({
            "source": "guestbook",
            "date": g.visit_date.isoformat() if g.visit_date else None,
            "occasion": g.occasion,
            "rating": g.rating,
            "message": g.message,
            "guestbook_id": g.id
        })

    # Add order-based visits
    for o in order_visits:
        visits.append({
            "source": "order",
            "date": o.created_at.isoformat() if o.created_at else None,
            "order_id": o.id,
            "order_total": float(o.total) if o.total else 0,
            "table_id": o.table_id
        })

    # Sort by date
    visits.sort(key=lambda x: x.get("date") or "", reverse=True)

    return {
        "customer_id": customer_id,
        "customer_name": customer.name,
        "visits": visits[:limit],
        "total_guestbook_entries": len(guestbook_visits),
        "total_dine_in_orders": len(order_visits)
    }

@router.post("/menu-reviews")
@limiter.limit("30/minute")
async def submit_menu_review(
    request: Request,
    venue_id: int = Query(1),
    menu_item_id: int = Body(...),
    rating: int = Body(...),
    comment: Optional[str] = Body(None),
    customer_id: Optional[int] = Body(None),
    order_id: Optional[int] = Body(None),
    taste_rating: Optional[int] = Body(None),
    presentation_rating: Optional[int] = Body(None),
    portion_rating: Optional[int] = Body(None),
    value_rating: Optional[int] = Body(None),
    db: Session = Depends(get_db)
):
    """Submit menu item review"""
    # Validate rating
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    # Verify menu item exists
    menu_item = db.query(MenuItem).filter(MenuItem.id == menu_item_id).first()
    if not menu_item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    # Determine if this is a verified purchase
    verified_purchase = False
    if order_id:
        # Check if this order contains this menu item
        order_item = db.query(OrderItem).filter(
            OrderItem.order_id == order_id,
            OrderItem.menu_item_id == menu_item_id
        ).first()
        if order_item:
            verified_purchase = True

    review = MenuItemReview(
        venue_id=venue_id,
        menu_item_id=menu_item_id,
        customer_id=customer_id,
        order_id=order_id,
        rating=rating,
        review_text=comment,
        taste_rating=taste_rating,
        presentation_rating=presentation_rating,
        portion_rating=portion_rating,
        value_rating=value_rating,
        verified_purchase=verified_purchase,
        status="pending"  # Requires moderation
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    return {
        "id": review.id,
        "menu_item_id": review.menu_item_id,
        "menu_item_name": menu_item.name,
        "rating": review.rating,
        "review_text": review.review_text,
        "verified_purchase": review.verified_purchase,
        "status": review.status,
        "submitted": True,
        "created_at": review.created_at.isoformat() if review.created_at else None
    }

@router.get("/menu-reviews/item/{menu_item_id}")
@limiter.limit("60/minute")
async def get_item_reviews(
    request: Request,
    menu_item_id: int,
    venue_id: int = Query(1),
    approved_only: bool = Query(True),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get reviews for menu item"""
    # Verify menu item exists
    menu_item = db.query(MenuItem).filter(MenuItem.id == menu_item_id).first()
    if not menu_item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    # Build query
    query = db.query(MenuItemReview).filter(
        MenuItemReview.menu_item_id == menu_item_id,
        MenuItemReview.venue_id == venue_id
    )

    if approved_only:
        query = query.filter(MenuItemReview.status == "approved")

    # Calculate statistics
    total_reviews = query.count()
    avg_rating_result = db.query(func.avg(MenuItemReview.rating)).filter(
        MenuItemReview.menu_item_id == menu_item_id,
        MenuItemReview.venue_id == venue_id,
        MenuItemReview.status == "approved"
    ).scalar()
    avg_rating = round(float(avg_rating_result), 1) if avg_rating_result else 0

    # Get aspect ratings
    avg_taste = db.query(func.avg(MenuItemReview.taste_rating)).filter(
        MenuItemReview.menu_item_id == menu_item_id,
        MenuItemReview.status == "approved",
        MenuItemReview.taste_rating.isnot(None)
    ).scalar()
    avg_presentation = db.query(func.avg(MenuItemReview.presentation_rating)).filter(
        MenuItemReview.menu_item_id == menu_item_id,
        MenuItemReview.status == "approved",
        MenuItemReview.presentation_rating.isnot(None)
    ).scalar()
    avg_portion = db.query(func.avg(MenuItemReview.portion_rating)).filter(
        MenuItemReview.menu_item_id == menu_item_id,
        MenuItemReview.status == "approved",
        MenuItemReview.portion_rating.isnot(None)
    ).scalar()
    avg_value = db.query(func.avg(MenuItemReview.value_rating)).filter(
        MenuItemReview.menu_item_id == menu_item_id,
        MenuItemReview.status == "approved",
        MenuItemReview.value_rating.isnot(None)
    ).scalar()

    # Get reviews
    reviews = query.order_by(MenuItemReview.created_at.desc()).offset(offset).limit(limit).all()

    # Calculate rating distribution
    rating_distribution = {}
    for r in range(1, 6):
        count = db.query(func.count(MenuItemReview.id)).filter(
            MenuItemReview.menu_item_id == menu_item_id,
            MenuItemReview.status == "approved",
            MenuItemReview.rating == r
        ).scalar()
        rating_distribution[str(r)] = count or 0

    return {
        "menu_item_id": menu_item_id,
        "menu_item_name": menu_item.name,
        "avg_rating": avg_rating,
        "total_reviews": total_reviews,
        "aspect_ratings": {
            "taste": round(float(avg_taste), 1) if avg_taste else None,
            "presentation": round(float(avg_presentation), 1) if avg_presentation else None,
            "portion": round(float(avg_portion), 1) if avg_portion else None,
            "value": round(float(avg_value), 1) if avg_value else None
        },
        "rating_distribution": rating_distribution,
        "reviews": [
            {
                "id": r.id,
                "rating": r.rating,
                "review_text": r.review_text,
                "taste_rating": r.taste_rating,
                "presentation_rating": r.presentation_rating,
                "portion_rating": r.portion_rating,
                "value_rating": r.value_rating,
                "verified_purchase": r.verified_purchase,
                "photo_urls": r.photo_urls,
                "response_text": r.response_text,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in reviews
        ],
        "limit": limit,
        "offset": offset
    }


"""V7 Reviews & prep time"""
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

# ============================================================================
# TIER 1: MENU ITEM REVIEWS (6 endpoints)
# ============================================================================

@router.post("/{venue_id}/reviews")
@limiter.limit("30/minute")
async def create_menu_review(
    request: Request,
    venue_id: int,
    menu_item_id: str = Body(...),
    customer_id: str = Body(...),
    order_id: str = Body(...),
    rating: int = Body(...),
    review_text: str = Body(""),
    would_order_again: bool = Body(True),
    taste_rating: Optional[int] = Body(None),
    presentation_rating: Optional[int] = Body(None),
    portion_rating: Optional[int] = Body(None),
    value_rating: Optional[int] = Body(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Create menu item review in database"""
    verify_venue_access(venue_id, current_user)
    try:
        menu_item_id_int = int(menu_item_id)
        customer_id_int = int(customer_id)
        order_id_int = int(order_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    # Validate rating
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    review = MenuItemReview(
        venue_id=venue_id,
        menu_item_id=menu_item_id_int,
        customer_id=customer_id_int,
        order_id=order_id_int,
        rating=rating,
        review_text=review_text,
        would_order_again=would_order_again,
        taste_rating=taste_rating,
        presentation_rating=presentation_rating,
        portion_rating=portion_rating,
        value_rating=value_rating,
        status="pending",
        verified_purchase=True,
        created_at=datetime.now(timezone.utc)
    )

    db.add(review)
    db.commit()
    db.refresh(review)

    # Update aggregate stats
    aggregate = db.query(MenuItemRatingAggregate).filter(
        MenuItemRatingAggregate.menu_item_id == menu_item_id_int
    ).first()

    if aggregate:
        total = aggregate.total_reviews or 0
        avg = aggregate.average_rating or 0
        new_avg = ((avg * total) + rating) / (total + 1)
        aggregate.average_rating = round(new_avg, 2)
        aggregate.total_reviews = total + 1
    else:
        aggregate = MenuItemRatingAggregate(
            menu_item_id=menu_item_id_int,
            average_rating=float(rating),
            total_reviews=1
        )
        db.add(aggregate)

    db.commit()

    return {"review_id": review.id, "rating": review.rating}

@router.get("/{venue_id}/reviews/item/{menu_item_id}")
@limiter.limit("60/minute")
async def get_item_reviews(request: Request, venue_id: int, menu_item_id: str, page: int = Query(1), limit: int = Query(10), db: Session = Depends(get_db)):
    """Get reviews for a menu item from database"""
    try:
        menu_item_id_int = int(menu_item_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid venue_id or menu_item_id format")

    offset = (page - 1) * limit

    # Query reviews from database
    reviews = db.query(MenuItemReview).filter(
        MenuItemReview.venue_id == venue_id,
        MenuItemReview.menu_item_id == menu_item_id_int,
        MenuItemReview.status == "approved"
    ).order_by(MenuItemReview.created_at.desc()).offset(offset).limit(limit).all()

    # Get total count
    total = db.query(func.count(MenuItemReview.id)).filter(
        MenuItemReview.venue_id == venue_id,
        MenuItemReview.menu_item_id == menu_item_id_int,
        MenuItemReview.status == "approved"
    ).scalar() or 0

    # Get aggregate stats
    aggregate = db.query(MenuItemRatingAggregate).filter(
        MenuItemRatingAggregate.menu_item_id == menu_item_id_int
    ).first()

    return {
        "reviews": [
            {
                "id": r.id,
                "customer_id": r.customer_id,
                "rating": r.rating,
                "review_text": r.review_text,
                "taste_rating": r.taste_rating,
                "presentation_rating": r.presentation_rating,
                "portion_rating": r.portion_rating,
                "value_rating": r.value_rating,
                "photo_urls": r.photo_urls or [],
                "helpful_count": r.helpful_count,
                "response_text": r.response_text,
                "verified_purchase": r.verified_purchase,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in reviews
        ],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
        "average_rating": aggregate.average_rating if aggregate else None,
        "total_reviews": aggregate.total_reviews if aggregate else 0
    }

@router.post("/{venue_id}/reviews/{review_id}/approve")
@limiter.limit("30/minute")
async def approve_review(
    request: Request,
    venue_id: int,
    review_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Approve a review in database"""
    verify_venue_access(venue_id, current_user)
    try:
        review_id_int = int(review_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid review_id format")

    review = db.query(MenuItemReview).filter(
        MenuItemReview.id == review_id_int
    ).first()

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    review.status = "approved"
    review.approved_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(review)

    return {"review_id": review.id, "is_approved": True}

@router.post("/{venue_id}/reviews/{review_id}/respond")
@limiter.limit("30/minute")
async def respond_to_review(
    request: Request,
    venue_id: int,
    review_id: str,
    response: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Respond to a review in database"""
    verify_venue_access(venue_id, current_user)
    try:
        review_id_int = int(review_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid review_id format")

    review = db.query(MenuItemReview).filter(
        MenuItemReview.id == review_id_int
    ).first()

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    review.response_text = response
    review.response_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(review)

    return {"review_id": review.id, "response": review.response_text}

@router.post("/{venue_id}/reviews/{review_id}/helpful")
@limiter.limit("30/minute")
async def vote_review_helpful(
    request: Request,
    venue_id: int,
    review_id: str,
    customer_id: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Vote review as helpful in database"""
    verify_venue_access(venue_id, current_user)
    try:
        review_id_int = int(review_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid review_id format")

    review = db.query(MenuItemReview).filter(
        MenuItemReview.id == review_id_int
    ).first()

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    review.helpful_count = (review.helpful_count or 0) + 1

    db.commit()
    db.refresh(review)

    return {"review_id": review.id, "helpful_votes": review.helpful_count}

@router.post("/{venue_id}/reviews/prompts")
@limiter.limit("30/minute")
async def get_review_prompts(
    request: Request,
    venue_id: int,
    order_id: str = Body(...),
    order_items: List[Dict] = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Get review prompts for order items"""
    verify_venue_access(venue_id, current_user)
    prompts = []
    for item in order_items:
        item_id = item.get("menu_item_id")
        item_name = item.get("name", "this item")
        prompts.append({
            "menu_item_id": item_id,
            "name": item_name,
            "questions": [
                "How was the taste?",
                "Was the portion size adequate?",
                "Would you order this again?"
            ]
        })
    return {"prompts": prompts}


# ============================================================================
# TIER 1: SMART PREP TIME (3 endpoints)
# ============================================================================

@router.post("/{venue_id}/prep-time/record")
@limiter.limit("30/minute")
async def record_prep_time(
    request: Request,
    venue_id: int,
    menu_item_id: str = Body(...),
    actual_time: int = Body(...),
    order_complexity: int = Body(1),
    kitchen_load: float = Body(0.5),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Record actual prep time in database"""
    verify_venue_access(venue_id, current_user)
    try:
        menu_item_id_int = int(menu_item_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    # Record the prep time
    record = PrepTimeModel(
        venue_id=venue_id,
        menu_item_id=menu_item_id_int,
        actual_time_seconds=actual_time,
        order_complexity=order_complexity,
        kitchen_load_factor=kitchen_load,
        recorded_at=datetime.now(timezone.utc)
    )

    db.add(record)
    db.commit()

    return {"recorded": True, "record_id": record.id}

@router.post("/{venue_id}/prep-time/estimate")
@limiter.limit("30/minute")
async def estimate_prep_time(
    request: Request,
    venue_id: int,
    order_items: List[Dict] = Body(...),
    is_delivery: bool = Body(False),
    is_priority: bool = Body(False),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Estimate prep time from database historical data"""
    verify_venue_access(venue_id, current_user)
    total_time = 0
    item_estimates = []

    for item in order_items:
        item_id = item.get("menu_item_id")
        quantity = item.get("quantity", 1)

        if item_id:
            try:
                item_id_int = int(item_id)
                # Get average prep time from history
                avg_time = db.query(func.avg(PrepTimeModel.actual_time_seconds)).filter(
                    PrepTimeModel.venue_id == venue_id,
                    PrepTimeModel.menu_item_id == item_id_int
                ).scalar()

                if avg_time:
                    item_time = int(avg_time) * quantity
                else:
                    item_time = 300 * quantity  # Default 5 min per item
            except ValueError:
                item_time = 300 * quantity
        else:
            item_time = 300 * quantity

        total_time += item_time
        item_estimates.append({
            "menu_item_id": item_id,
            "quantity": quantity,
            "estimated_seconds": item_time
        })

    # Apply modifiers
    if is_delivery:
        total_time = int(total_time * 1.1)  # 10% buffer for delivery
    if is_priority:
        total_time = int(total_time * 0.85)  # Priority orders faster

    return {
        "total_estimated_seconds": total_time,
        "estimated_minutes": round(total_time / 60, 1),
        "items": item_estimates,
        "is_delivery": is_delivery,
        "is_priority": is_priority
    }

@router.post("/{venue_id}/prep-time/kitchen-load")
@limiter.limit("30/minute")
async def update_kitchen_load(
    request: Request,
    venue_id: int,
    active_orders: int = Body(...),
    max_capacity: int = Body(20),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Update kitchen load in database"""
    verify_venue_access(venue_id, current_user)
    load_factor = min(1.0, active_orders / max(1, max_capacity))

    # Calculate delay based on load
    if load_factor > 0.9:
        delay_multiplier = 1.5
        status = "overloaded"
    elif load_factor > 0.7:
        delay_multiplier = 1.25
        status = "busy"
    elif load_factor > 0.5:
        delay_multiplier = 1.1
        status = "moderate"
    else:
        delay_multiplier = 1.0
        status = "normal"

    return {
        "venue_id": venue_id,
        "active_orders": active_orders,
        "max_capacity": max_capacity,
        "load_factor": round(load_factor, 2),
        "status": status,
        "delay_multiplier": delay_multiplier
    }



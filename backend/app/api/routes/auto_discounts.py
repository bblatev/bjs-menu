"""
Automatic Discount / Happy Hour API Endpoints
Time-based automatic discounts that apply based on day/time
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.db.session import get_db
from app.core.rbac import get_current_user
from app.core.rate_limit import limiter
from app.models import StaffUser, AutoDiscount
from app.schemas import AutoDiscountCreate, AutoDiscountResponse, AutoDiscountType


router = APIRouter()


def is_discount_currently_active(discount: AutoDiscount) -> bool:
    """Check if a discount is currently active based on time and day"""
    if not discount.active:
        return False

    now = datetime.now()
    current_day = now.strftime("%A").lower()
    current_time = now.strftime("%H:%M")

    # Check day
    valid_days = discount.valid_days or []
    if current_day not in valid_days:
        return False

    # Check time range
    start_time = discount.start_time
    end_time = discount.end_time

    # Handle overnight ranges (e.g., 22:00 to 02:00)
    if start_time <= end_time:
        return start_time <= current_time <= end_time
    else:
        return current_time >= start_time or current_time <= end_time


def calculate_discount(
    discount: AutoDiscount,
    item_price: float,
    item_id: int = None,
    category_id: int = None
) -> float:
    """Calculate discount amount for an item"""
    # Check if item is applicable
    if discount.applicable_items:
        if item_id not in discount.applicable_items:
            return 0

    if discount.applicable_categories:
        if category_id not in discount.applicable_categories:
            return 0

    # Calculate discount
    if discount.discount_percentage:
        discount_amount = item_price * (discount.discount_percentage / 100)
    elif discount.discount_amount:
        discount_amount = min(discount.discount_amount, item_price)
    else:
        return 0

    # Apply max discount limit
    if discount.max_discount_amount:
        discount_amount = min(discount_amount, discount.max_discount_amount)

    return round(discount_amount, 2)


@router.post("/", response_model=AutoDiscountResponse)
@limiter.limit("30/minute")
async def create_auto_discount(
    request: Request,
    data: AutoDiscountCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Create a new automatic discount"""
    if current_user.role not in ["owner", "manager"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Validate time format
    try:
        datetime.strptime(data.start_time, "%H:%M")
        datetime.strptime(data.end_time, "%H:%M")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid time format. Use HH:MM")

    discount = AutoDiscount(
        venue_id=current_user.venue_id,
        name=data.name,
        discount_type=data.discount_type.value,
        discount_percentage=data.discount_percentage,
        discount_amount=data.discount_amount,
        start_time=data.start_time,
        end_time=data.end_time,
        valid_days=data.valid_days,
        applicable_categories=data.applicable_categories,
        applicable_items=data.applicable_items,
        min_order_amount=data.min_order_amount,
        max_discount_amount=data.max_discount_amount,
        active=data.active
    )
    db.add(discount)
    db.commit()
    db.refresh(discount)

    return _format_discount_response(discount)


@router.get("/", response_model=List[AutoDiscountResponse])
@limiter.limit("60/minute")
async def list_auto_discounts(
    request: Request,
    active_only: bool = False,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List all automatic discounts"""
    query = db.query(AutoDiscount).filter(AutoDiscount.venue_id == current_user.venue_id)

    if active_only:
        query = query.filter(AutoDiscount.active == True)

    discounts = query.order_by(AutoDiscount.start_time).all()

    return [_format_discount_response(d) for d in discounts]


@router.get("/active", response_model=List[AutoDiscountResponse])
@limiter.limit("60/minute")
async def get_currently_active_discounts(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get discounts that are currently active (based on time and day)"""
    discounts = db.query(AutoDiscount).filter(
        AutoDiscount.venue_id == current_user.venue_id,
        AutoDiscount.active == True
    ).all()

    active_discounts = [d for d in discounts if is_discount_currently_active(d)]

    return [_format_discount_response(d) for d in active_discounts]


@router.get("/{discount_id}", response_model=AutoDiscountResponse)
@limiter.limit("60/minute")
async def get_auto_discount(
    request: Request,
    discount_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get discount details"""
    discount = db.query(AutoDiscount).filter(
        AutoDiscount.id == discount_id,
        AutoDiscount.venue_id == current_user.venue_id
    ).first()

    if not discount:
        raise HTTPException(status_code=404, detail="Discount not found")

    return _format_discount_response(discount)


@router.put("/{discount_id}", response_model=AutoDiscountResponse)
@limiter.limit("30/minute")
async def update_auto_discount(
    request: Request,
    discount_id: int,
    data: AutoDiscountCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Update an automatic discount"""
    if current_user.role not in ["owner", "manager"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    discount = db.query(AutoDiscount).filter(
        AutoDiscount.id == discount_id,
        AutoDiscount.venue_id == current_user.venue_id
    ).first()

    if not discount:
        raise HTTPException(status_code=404, detail="Discount not found")

    # Update fields
    discount.name = data.name
    discount.discount_type = data.discount_type.value
    discount.discount_percentage = data.discount_percentage
    discount.discount_amount = data.discount_amount
    discount.start_time = data.start_time
    discount.end_time = data.end_time
    discount.valid_days = data.valid_days
    discount.applicable_categories = data.applicable_categories
    discount.applicable_items = data.applicable_items
    discount.min_order_amount = data.min_order_amount
    discount.max_discount_amount = data.max_discount_amount
    discount.active = data.active

    db.commit()
    db.refresh(discount)

    return _format_discount_response(discount)


@router.put("/{discount_id}/toggle")
@limiter.limit("30/minute")
async def toggle_auto_discount(
    request: Request,
    discount_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Toggle discount active status"""
    if current_user.role not in ["owner", "manager"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    discount = db.query(AutoDiscount).filter(
        AutoDiscount.id == discount_id,
        AutoDiscount.venue_id == current_user.venue_id
    ).first()

    if not discount:
        raise HTTPException(status_code=404, detail="Discount not found")

    discount.active = not discount.active
    db.commit()

    return {"active": discount.active}


@router.delete("/{discount_id}")
@limiter.limit("30/minute")
async def delete_auto_discount(
    request: Request,
    discount_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Delete an automatic discount"""
    if current_user.role not in ["owner", "manager"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    discount = db.query(AutoDiscount).filter(
        AutoDiscount.id == discount_id,
        AutoDiscount.venue_id == current_user.venue_id
    ).first()

    if not discount:
        raise HTTPException(status_code=404, detail="Discount not found")

    db.delete(discount)
    db.commit()

    return {"message": "Discount deleted"}


@router.post("/calculate-order-discount")
@limiter.limit("30/minute")
async def calculate_order_discount(
    request: Request,
    item_prices: List[dict],  # [{"item_id": 1, "category_id": 1, "price": 10.00}, ...]
    order_total: float = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Calculate total discount for an order based on active automatic discounts"""
    # Get currently active discounts
    discounts = db.query(AutoDiscount).filter(
        AutoDiscount.venue_id == current_user.venue_id,
        AutoDiscount.active == True
    ).all()

    active_discounts = [d for d in discounts if is_discount_currently_active(d)]

    if not active_discounts:
        return {
            "total_discount": 0,
            "applied_discounts": [],
            "message": "No active discounts"
        }

    total_discount = 0
    applied_discounts = []

    for discount in active_discounts:
        # Check minimum order amount
        if discount.min_order_amount and order_total:
            if order_total < discount.min_order_amount:
                continue

        discount_total = 0
        for item in item_prices:
            item_discount = calculate_discount(
                discount,
                item.get("price", 0),
                item.get("item_id"),
                item.get("category_id")
            )
            discount_total += item_discount

        if discount_total > 0:
            total_discount += discount_total
            applied_discounts.append({
                "discount_id": discount.id,
                "discount_name": discount.name,
                "discount_type": discount.discount_type,
                "amount": round(discount_total, 2)
            })

    return {
        "total_discount": round(total_discount, 2),
        "applied_discounts": applied_discounts,
        "message": f"{len(applied_discounts)} discount(s) applied"
    }


def _format_discount_response(discount: AutoDiscount) -> AutoDiscountResponse:
    """Format discount for response"""
    return AutoDiscountResponse(
        id=discount.id,
        name=discount.name,
        discount_type=AutoDiscountType(discount.discount_type),
        discount_percentage=discount.discount_percentage,
        discount_amount=discount.discount_amount,
        start_time=discount.start_time,
        end_time=discount.end_time,
        valid_days=discount.valid_days or [],
        applicable_categories=discount.applicable_categories,
        applicable_items=discount.applicable_items,
        min_order_amount=discount.min_order_amount,
        max_discount_amount=discount.max_discount_amount,
        active=discount.active,
        currently_active=is_discount_currently_active(discount),
        created_at=discount.created_at
    )

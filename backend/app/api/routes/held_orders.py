"""
Held Orders / Bill Suspend & Resume API
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, ConfigDict

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.core.rbac import get_current_user
from app.models import (
    HeldOrder, HeldOrderStatus, StaffUser
)


router = APIRouter()


# Schemas
class HeldOrderCreate(BaseModel):
    order_id: Optional[int] = None
    table_id: Optional[int] = None
    hold_reason: Optional[str] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    order_data: dict
    total_amount: float
    expires_hours: Optional[int] = 24  # Auto-expire after X hours


class HeldOrderResponse(BaseModel):
    id: int
    venue_id: int
    original_order_id: Optional[int]
    table_id: Optional[int]
    hold_reason: Optional[str]
    customer_name: Optional[str]
    customer_phone: Optional[str]
    order_data: dict
    total_amount: float
    status: str
    held_at: datetime
    held_by: Optional[int]
    resumed_at: Optional[datetime]
    expires_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


@router.post("/", response_model=HeldOrderResponse)
@limiter.limit("30/minute")
def hold_order(
    request: Request,
    data: HeldOrderCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Hold/suspend an order for later"""
    expires_at = None
    if data.expires_hours:
        expires_at = datetime.now(timezone.utc) + timedelta(hours=data.expires_hours)

    held_order = HeldOrder(
        venue_id=current_user.venue_id,
        original_order_id=data.order_id,
        table_id=data.table_id,
        hold_reason=data.hold_reason,
        customer_name=data.customer_name,
        customer_phone=data.customer_phone,
        order_data=data.order_data,
        total_amount=data.total_amount,
        status=HeldOrderStatus.HELD,
        held_by=current_user.id,
        expires_at=expires_at
    )
    db.add(held_order)
    db.commit()
    db.refresh(held_order)
    return held_order


@router.get("/", response_model=List[HeldOrderResponse])
@limiter.limit("60/minute")
def list_held_orders(
    request: Request,
    status: Optional[str] = "held",
    table_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List held orders"""
    query = db.query(HeldOrder).filter(HeldOrder.venue_id == current_user.venue_id)

    if status:
        query = query.filter(HeldOrder.status == status)
    if table_id:
        query = query.filter(HeldOrder.table_id == table_id)

    return query.order_by(HeldOrder.held_at.desc()).all()


@router.get("/{held_order_id}", response_model=HeldOrderResponse)
@limiter.limit("60/minute")
def get_held_order(
    request: Request,
    held_order_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get a specific held order"""
    held_order = db.query(HeldOrder).filter(
        HeldOrder.id == held_order_id,
        HeldOrder.venue_id == current_user.venue_id
    ).first()

    if not held_order:
        raise HTTPException(status_code=404, detail="Held order not found")

    return held_order


@router.post("/{held_order_id}/resume")
@limiter.limit("30/minute")
def resume_held_order(
    request: Request,
    held_order_id: int,
    target_table_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Resume a held order - creates a new active order"""
    held_order = db.query(HeldOrder).filter(
        HeldOrder.id == held_order_id,
        HeldOrder.venue_id == current_user.venue_id,
        HeldOrder.status == HeldOrderStatus.HELD
    ).first()

    if not held_order:
        raise HTTPException(status_code=404, detail="Held order not found or already resumed")

    # Check if expired
    if held_order.expires_at and datetime.now(timezone.utc) > held_order.expires_at:
        held_order.status = HeldOrderStatus.EXPIRED
        db.commit()
        raise HTTPException(status_code=400, detail="Held order has expired")

    # Mark as resumed
    held_order.status = HeldOrderStatus.RESUMED
    held_order.resumed_at = datetime.now(timezone.utc)
    held_order.resumed_by = current_user.id

    db.commit()

    return {
        "message": "Order resumed successfully",
        "held_order_id": held_order_id,
        "order_data": held_order.order_data,
        "target_table_id": target_table_id or held_order.table_id
    }


@router.post("/{held_order_id}/cancel")
@limiter.limit("30/minute")
def cancel_held_order(
    request: Request,
    held_order_id: int,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Cancel a held order"""
    held_order = db.query(HeldOrder).filter(
        HeldOrder.id == held_order_id,
        HeldOrder.venue_id == current_user.venue_id,
        HeldOrder.status == HeldOrderStatus.HELD
    ).first()

    if not held_order:
        raise HTTPException(status_code=404, detail="Held order not found or already processed")

    held_order.status = HeldOrderStatus.CANCELLED
    if reason:
        held_order.hold_reason = f"{held_order.hold_reason or ''} | Cancelled: {reason}"

    db.commit()

    return {"message": "Held order cancelled", "held_order_id": held_order_id}

"""
Batch & Expiration Tracking API Endpoints
Track batches, expiration dates, and handle FIFO inventory
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.core.rbac import get_current_user
from app.models import StaffUser, StockItem, StockBatch
from app.schemas import BatchCreate, BatchResponse

router = APIRouter()


@router.post("/", response_model=BatchResponse)
@limiter.limit("30/minute")
async def create_batch(
    request: Request,
    data: BatchCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Create a new batch for a stock item"""
    stock_item = db.query(StockItem).filter(
        StockItem.id == data.stock_item_id,
        StockItem.venue_id == current_user.venue_id
    ).first()


    if not stock_item:
        raise HTTPException(status_code=404, detail="Stock item not found")

    # Check for duplicate batch number
    existing = db.query(StockBatch).filter(
        StockBatch.stock_item_id == data.stock_item_id,
        StockBatch.batch_number == data.batch_number
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Batch number already exists for this item")

    batch = StockBatch(
        stock_item_id=data.stock_item_id,
        batch_number=data.batch_number,
        initial_quantity=data.quantity,
        quantity=data.quantity,
        manufacture_date=data.manufacture_date,
        expiration_date=data.expiration_date,
        supplier_id=data.supplier_id,
        purchase_order_id=data.purchase_order_id,
        cost_per_unit=data.cost_per_unit or stock_item.cost_per_unit
    )
    db.add(batch)

    # Update main stock quantity
    stock_item.quantity = (stock_item.quantity or 0) + data.quantity

    db.commit()
    db.refresh(batch)

    return _format_batch_response(batch, stock_item)


@router.get("/", response_model=List[BatchResponse])
@limiter.limit("60/minute")
async def list_batches(
    request: Request,
    stock_item_id: Optional[int] = None,
    expiring_soon: bool = False,
    expired: bool = False,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List batches with filtering options"""
    query = db.query(StockBatch).join(StockItem).filter(
        StockItem.venue_id == current_user.venue_id
    )

    if stock_item_id:
        query = query.filter(StockBatch.stock_item_id == stock_item_id)

    now = datetime.utcnow()

    if expired:
        query = query.filter(
            StockBatch.expiration_date.isnot(None),
            StockBatch.expiration_date < now
        )
    elif expiring_soon:
        # Within 7 days
        soon = now + timedelta(days=7)
        query = query.filter(
            StockBatch.expiration_date.isnot(None),
            StockBatch.expiration_date >= now,
            StockBatch.expiration_date <= soon
        )

    # Only show batches with remaining quantity
    query = query.filter(StockBatch.quantity > 0)

    batches = query.order_by(StockBatch.expiration_date.asc().nullslast()).all()

    result = []
    for batch in batches:
        stock_item = db.query(StockItem).filter(StockItem.id == batch.stock_item_id).first()
        result.append(_format_batch_response(batch, stock_item))

    return result


@router.get("/expiring", response_model=List[BatchResponse])
@limiter.limit("60/minute")
async def get_expiring_batches(
    request: Request,
    days: int = 7,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get batches expiring within specified days"""
    now = datetime.utcnow()
    end_date = now + timedelta(days=days)

    batches = db.query(StockBatch).join(StockItem).filter(
        StockItem.venue_id == current_user.venue_id,
        StockBatch.expiration_date.isnot(None),
        StockBatch.expiration_date >= now,
        StockBatch.expiration_date <= end_date,
        StockBatch.quantity > 0
    ).order_by(StockBatch.expiration_date).all()

    result = []
    for batch in batches:
        stock_item = db.query(StockItem).filter(StockItem.id == batch.stock_item_id).first()
        result.append(_format_batch_response(batch, stock_item))

    return result


@router.get("/expired", response_model=List[BatchResponse])
@limiter.limit("60/minute")
async def get_expired_batches(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get all expired batches with remaining quantity"""
    now = datetime.utcnow()

    batches = db.query(StockBatch).join(StockItem).filter(
        StockItem.venue_id == current_user.venue_id,
        StockBatch.expiration_date.isnot(None),
        StockBatch.expiration_date < now,
        StockBatch.quantity > 0
    ).order_by(StockBatch.expiration_date).all()

    result = []
    for batch in batches:
        stock_item = db.query(StockItem).filter(StockItem.id == batch.stock_item_id).first()
        result.append(_format_batch_response(batch, stock_item))

    return result


@router.get("/{batch_id}", response_model=BatchResponse)
@limiter.limit("60/minute")
async def get_batch(
    request: Request,
    batch_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get batch details"""
    batch = db.query(StockBatch).join(StockItem).filter(
        StockBatch.id == batch_id,
        StockItem.venue_id == current_user.venue_id
    ).first()

    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    stock_item = db.query(StockItem).filter(StockItem.id == batch.stock_item_id).first()
    return _format_batch_response(batch, stock_item)


@router.put("/{batch_id}/consume")
@limiter.limit("30/minute")
async def consume_from_batch(
    request: Request,
    batch_id: int,
    quantity: float,
    reason: str = "usage",
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Consume/reduce quantity from a specific batch"""
    batch = db.query(StockBatch).join(StockItem).filter(
        StockBatch.id == batch_id,
        StockItem.venue_id == current_user.venue_id
    ).first()

    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    if batch.quantity < quantity:
        raise HTTPException(status_code=400, detail="Insufficient quantity in batch")

    batch.quantity -= quantity

    # Update main stock
    stock_item = db.query(StockItem).filter(StockItem.id == batch.stock_item_id).first()
    if stock_item:
        stock_item.quantity = (stock_item.quantity or 0) - quantity

    db.commit()

    return {
        "message": f"Consumed {quantity} from batch {batch.batch_number}",
        "remaining_in_batch": batch.quantity,
        "reason": reason
    }


@router.put("/{batch_id}/write-off")
@limiter.limit("30/minute")
async def write_off_batch(
    request: Request,
    batch_id: int,
    reason: str = "expired",
    quantity: float = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Write off a batch (expired, spoiled, damaged)"""
    batch = db.query(StockBatch).join(StockItem).filter(
        StockBatch.id == batch_id,
        StockItem.venue_id == current_user.venue_id
    ).first()

    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    write_off_quantity = quantity if quantity is not None else batch.quantity

    if write_off_quantity > batch.quantity:
        raise HTTPException(status_code=400, detail="Cannot write off more than available")

    # Update stock
    stock_item = db.query(StockItem).filter(StockItem.id == batch.stock_item_id).first()
    if stock_item:
        stock_item.quantity = (stock_item.quantity or 0) - write_off_quantity

    batch.quantity -= write_off_quantity

    db.commit()

    return {
        "message": f"Written off {write_off_quantity} from batch {batch.batch_number}",
        "reason": reason,
        "remaining_in_batch": batch.quantity
    }


@router.post("/consume-fifo")
@limiter.limit("30/minute")
async def consume_fifo(
    request: Request,
    stock_item_id: int,
    quantity: float,
    reason: str = "usage",
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Consume from stock using FIFO (First In First Out) from oldest batches first"""
    stock_item = db.query(StockItem).filter(
        StockItem.id == stock_item_id,
        StockItem.venue_id == current_user.venue_id
    ).first()

    if not stock_item:
        raise HTTPException(status_code=404, detail="Stock item not found")

    # Get batches ordered by expiration date (FIFO - oldest first)
    batches = db.query(StockBatch).filter(
        StockBatch.stock_item_id == stock_item_id,
        StockBatch.quantity > 0
    ).order_by(StockBatch.expiration_date.asc().nullslast()).all()

    total_available = sum(b.quantity for b in batches)
    if total_available < quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient stock. Available: {total_available}"
        )

    remaining_to_consume = quantity
    consumed_batches = []

    for batch in batches:
        if remaining_to_consume <= 0:
            break

        consume_from_batch = min(batch.quantity, remaining_to_consume)
        batch.quantity -= consume_from_batch
        remaining_to_consume -= consume_from_batch

        consumed_batches.append({
            "batch_number": batch.batch_number,
            "consumed": consume_from_batch,
            "remaining": batch.quantity
        })

    # Update main stock
    stock_item.quantity = (stock_item.quantity or 0) - quantity

    db.commit()

    return {
        "message": f"Consumed {quantity} using FIFO",
        "batches_affected": consumed_batches,
        "reason": reason
    }


@router.get("/item/{stock_item_id}", response_model=List[BatchResponse])
@limiter.limit("60/minute")
async def get_batches_for_item(
    request: Request,
    stock_item_id: int,
    include_empty: bool = False,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get all batches for a specific stock item"""
    stock_item = db.query(StockItem).filter(
        StockItem.id == stock_item_id,
        StockItem.venue_id == current_user.venue_id
    ).first()

    if not stock_item:
        raise HTTPException(status_code=404, detail="Stock item not found")

    query = db.query(StockBatch).filter(StockBatch.stock_item_id == stock_item_id)

    if not include_empty:
        query = query.filter(StockBatch.quantity > 0)

    batches = query.order_by(StockBatch.expiration_date.asc().nullslast()).all()

    return [_format_batch_response(b, stock_item) for b in batches]


@router.get("/summary")
@limiter.limit("60/minute")
async def get_batch_summary(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get summary of batch status across all items"""
    now = datetime.utcnow()
    soon = now + timedelta(days=7)

    batches = db.query(StockBatch).join(StockItem).filter(
        StockItem.venue_id == current_user.venue_id,
        StockBatch.quantity > 0
    ).all()

    expired_count = 0
    expired_value = 0
    expiring_soon_count = 0
    expiring_soon_value = 0
    good_count = 0

    for batch in batches:
        value = batch.quantity * (batch.cost_per_unit or 0)

        if batch.expiration_date:
            if batch.expiration_date < now:
                expired_count += 1
                expired_value += value
            elif batch.expiration_date <= soon:
                expiring_soon_count += 1
                expiring_soon_value += value
            else:
                good_count += 1
        else:
            good_count += 1

    return {
        "total_batches": len(batches),
        "expired": {
            "count": expired_count,
            "value": round(expired_value, 2)
        },
        "expiring_soon": {
            "count": expiring_soon_count,
            "value": round(expiring_soon_value, 2),
            "days": 7
        },
        "good": {
            "count": good_count
        }
    }


def _format_batch_response(batch: StockBatch, stock_item: StockItem) -> BatchResponse:
    """Format batch for response"""
    now = datetime.utcnow()

    days_until_expiry = None
    is_expired = False
    is_expiring_soon = False

    if batch.expiration_date:
        delta = batch.expiration_date - now
        days_until_expiry = delta.days

        if days_until_expiry < 0:
            is_expired = True
        elif days_until_expiry <= 7:
            is_expiring_soon = True

    return BatchResponse(
        id=batch.id,
        stock_item_id=batch.stock_item_id,
        stock_item_name=stock_item.name if stock_item else "",
        batch_number=batch.batch_number,
        quantity=batch.quantity,
        initial_quantity=batch.initial_quantity,
        manufacture_date=batch.manufacture_date,
        expiration_date=batch.expiration_date,
        days_until_expiry=days_until_expiry,
        is_expired=is_expired,
        is_expiring_soon=is_expiring_soon,
        supplier_id=batch.supplier_id,
        created_at=batch.created_at
    )

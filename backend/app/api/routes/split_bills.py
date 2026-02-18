"""
Split Bill API Endpoints
Support for splitting bills by guest, item, amount, or percentage
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timezone

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.core.rbac import get_current_user
from app.models import (
    StaffUser, Table, Order, OrderItem, SplitBill, SplitBillOrder,
    SplitBillGuest, SplitBillGuestItem, SplitBillStatus
)
from app.schemas import (
    SplitBillCreate, SplitBillResponse, SplitBillPayment,
    SplitBillType, SplitBillGuest as SplitBillGuestSchema
)

router = APIRouter()


@router.post("/", response_model=SplitBillResponse)
@limiter.limit("30/minute")
async def create_split_bill(
    request: Request,
    data: SplitBillCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Create a split bill for a table"""
    # Get table
    table = db.query(Table).filter(
        Table.id == data.table_id,
        Table.location_id == current_user.venue_id
    ).first()


    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    # Get orders for the table (or specified orders)
    if data.order_ids:
        orders = db.query(Order).filter(
            Order.id.in_(data.order_ids),
            Order.table_id == data.table_id
        ).all()
    else:
        # Get all unpaid orders for the table
        orders = db.query(Order).filter(
            Order.table_id == data.table_id,
            Order.payment_status != "paid"
        ).all()

    if not orders:
        raise HTTPException(status_code=400, detail="No orders to split")

    # Calculate total
    total_amount = sum(order.total or 0 for order in orders)

    # Create split bill
    split_bill = SplitBill(
        venue_id=current_user.venue_id,
        table_id=data.table_id,
        split_type=data.split_type.value,
        num_guests=data.num_guests,
        total_amount=total_amount,
        created_by=current_user.id
    )
    db.add(split_bill)
    db.flush()

    # Link orders
    for order in orders:
        split_order = SplitBillOrder(
            split_bill_id=split_bill.id,
            order_id=order.id
        )
        db.add(split_order)

    # Create guest entries based on split type
    if data.split_type == SplitBillType.EQUAL:
        # Split equally
        amount_per_guest = round(total_amount / data.num_guests, 2)
        for i in range(data.num_guests):
            guest = SplitBillGuest(
                split_bill_id=split_bill.id,
                guest_number=i + 1,
                amount=amount_per_guest
            )
            db.add(guest)

    elif data.split_type == SplitBillType.BY_ITEM:
        # Create guest entries from provided data
        if not data.guests:
            raise HTTPException(status_code=400, detail="Guest item assignments required for BY_ITEM split")

        for guest_data in data.guests:
            # Calculate guest amount from assigned items
            guest_amount = 0
            guest = SplitBillGuest(
                split_bill_id=split_bill.id,
                guest_number=guest_data.guest_number,
                guest_name=guest_data.guest_name,
                amount=0  # Will calculate
            )
            db.add(guest)
            db.flush()

            for item_assignment in guest_data.items:
                order_item = db.query(OrderItem).filter(
                    OrderItem.id == item_assignment.order_item_id
                ).first()
                if order_item:
                    item_price = (order_item.subtotal or 0) / (order_item.quantity or 1)
                    guest_amount += item_price * item_assignment.quantity

                    guest_item = SplitBillGuestItem(
                        guest_id=guest.id,
                        order_item_id=item_assignment.order_item_id,
                        quantity=item_assignment.quantity
                    )
                    db.add(guest_item)

            guest.amount = round(guest_amount, 2)

    elif data.split_type == SplitBillType.BY_AMOUNT:
        # Custom amounts per guest
        if not data.guests:
            raise HTTPException(status_code=400, detail="Guest amounts required for BY_AMOUNT split")

        total_assigned = sum(g.amount or 0 for g in data.guests)
        if abs(total_assigned - total_amount) > 0.01:
            raise HTTPException(
                status_code=400,
                detail=f"Guest amounts ({total_assigned}) don't match total ({total_amount})"
            )

        for guest_data in data.guests:
            guest = SplitBillGuest(
                split_bill_id=split_bill.id,
                guest_number=guest_data.guest_number,
                guest_name=guest_data.guest_name,
                amount=guest_data.amount or 0
            )
            db.add(guest)

    elif data.split_type == SplitBillType.BY_PERCENTAGE:
        # Split by percentage
        if not data.guests:
            raise HTTPException(status_code=400, detail="Guest percentages required for BY_PERCENTAGE split")

        total_percentage = sum(g.percentage or 0 for g in data.guests)
        if abs(total_percentage - 100) > 0.01:
            raise HTTPException(
                status_code=400,
                detail=f"Percentages must sum to 100, got {total_percentage}"
            )

        for guest_data in data.guests:
            guest_amount = round(total_amount * (guest_data.percentage or 0) / 100, 2)
            guest = SplitBillGuest(
                split_bill_id=split_bill.id,
                guest_number=guest_data.guest_number,
                guest_name=guest_data.guest_name,
                amount=guest_amount
            )
            db.add(guest)

    db.commit()
    db.refresh(split_bill)

    return _format_split_bill_response(split_bill, table)


@router.get("/{split_bill_id}", response_model=SplitBillResponse)
@limiter.limit("60/minute")
async def get_split_bill(
    request: Request,
    split_bill_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get split bill details"""
    split_bill = db.query(SplitBill).filter(
        SplitBill.id == split_bill_id,
        SplitBill.venue_id == current_user.venue_id
    ).first()

    if not split_bill:
        raise HTTPException(status_code=404, detail="Split bill not found")

    table = db.query(Table).filter(Table.id == split_bill.table_id).first()
    return _format_split_bill_response(split_bill, table)


@router.get("/table/{table_id}", response_model=Optional[SplitBillResponse])
@limiter.limit("60/minute")
async def get_active_split_bill_for_table(
    request: Request,
    table_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get active split bill for a table"""
    split_bill = db.query(SplitBill).filter(
        SplitBill.table_id == table_id,
        SplitBill.venue_id == current_user.venue_id,
        SplitBill.status.in_([SplitBillStatus.ACTIVE, SplitBillStatus.PARTIALLY_PAID])
    ).first()

    if not split_bill:
        return None

    table = db.query(Table).filter(Table.id == table_id).first()
    return _format_split_bill_response(split_bill, table)


@router.post("/pay", response_model=SplitBillResponse)
@limiter.limit("30/minute")
async def process_split_bill_payment(
    request: Request,
    payment: SplitBillPayment,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Process payment for one guest in a split bill"""
    split_bill = db.query(SplitBill).filter(
        SplitBill.id == payment.split_bill_id,
        SplitBill.venue_id == current_user.venue_id
    ).first()

    if not split_bill:
        raise HTTPException(status_code=404, detail="Split bill not found")

    if split_bill.status == SplitBillStatus.FULLY_PAID:
        raise HTTPException(status_code=400, detail="Split bill already fully paid")

    # Find the guest
    guest = db.query(SplitBillGuest).filter(
        SplitBillGuest.split_bill_id == split_bill.id,
        SplitBillGuest.guest_number == payment.guest_number
    ).first()

    if not guest:
        raise HTTPException(status_code=404, detail="Guest not found")

    if guest.paid:
        raise HTTPException(status_code=400, detail="Guest already paid")

    # Process payment
    guest.paid = True
    guest.paid_at = datetime.now(timezone.utc)
    guest.payment_method = payment.payment_method
    guest.tip_amount = payment.tip_amount

    # Update split bill totals
    split_bill.total_tips += payment.tip_amount

    # Check if all guests paid
    unpaid_guests = db.query(SplitBillGuest).filter(
        SplitBillGuest.split_bill_id == split_bill.id,
        SplitBillGuest.paid == False
    ).count()

    if unpaid_guests == 0:
        split_bill.status = SplitBillStatus.FULLY_PAID

        # Mark all orders as paid
        for split_order in split_bill.orders:
            order = split_order.order
            order.payment_status = "paid"
            order.tip_amount = (order.tip_amount or 0) + payment.tip_amount
    else:
        split_bill.status = SplitBillStatus.PARTIALLY_PAID

    db.commit()
    db.refresh(split_bill)

    table = db.query(Table).filter(Table.id == split_bill.table_id).first()
    return _format_split_bill_response(split_bill, table)


@router.delete("/{split_bill_id}")
@limiter.limit("30/minute")
async def cancel_split_bill(
    request: Request,
    split_bill_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Cancel a split bill"""
    split_bill = db.query(SplitBill).filter(
        SplitBill.id == split_bill_id,
        SplitBill.venue_id == current_user.venue_id
    ).first()

    if not split_bill:
        raise HTTPException(status_code=404, detail="Split bill not found")

    if split_bill.status == SplitBillStatus.FULLY_PAID:
        raise HTTPException(status_code=400, detail="Cannot cancel paid split bill")

    # Check if any payments made
    paid_guests = db.query(SplitBillGuest).filter(
        SplitBillGuest.split_bill_id == split_bill.id,
        SplitBillGuest.paid == True
    ).count()

    if paid_guests > 0:
        raise HTTPException(status_code=400, detail="Cannot cancel split bill with payments made")

    split_bill.status = SplitBillStatus.CANCELLED
    db.commit()

    return {"message": "Split bill cancelled"}


def _format_split_bill_response(split_bill: SplitBill, table: Table) -> SplitBillResponse:
    """Format split bill for response"""
    guests = []
    for guest in split_bill.guests:
        guest_items = []
        for item in guest.items:
            guest_items.append({
                "order_item_id": item.order_item_id,
                "quantity": item.quantity
            })

        guests.append(SplitBillGuestSchema(
            guest_number=guest.guest_number,
            guest_name=guest.guest_name,
            items=guest_items,
            amount=guest.amount,
            tip_amount=guest.tip_amount,
            payment_method=guest.payment_method,
            paid=guest.paid
        ))

    all_paid = all(g.paid for g in guests) if guests else False

    return SplitBillResponse(
        id=split_bill.id,
        table_id=split_bill.table_id,
        table_number=table.number if table else "Unknown",
        split_type=SplitBillType(split_bill.split_type),
        total_amount=split_bill.total_amount,
        total_tips=split_bill.total_tips,
        grand_total=split_bill.total_amount + split_bill.total_tips,
        num_guests=split_bill.num_guests,
        guests=guests,
        all_paid=all_paid,
        created_at=split_bill.created_at
    )

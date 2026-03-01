"""Payments, discounts, voids & comps"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from app.core.rate_limit import limiter
from app.db.session import get_db

# Import shared schemas and helpers
from app.api.routes.waiter_terminal._shared import *

router = APIRouter()

@router.get("/checks/{order_id}", response_model=CheckResponse)
@limiter.limit("60/minute")
async def get_check(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get check/bill details for an order"""
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.venue_id == current_user.venue_id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    items = db.query(OrderItem).filter(OrderItem.order_id == order_id).limit(500).all()

    item_list = []
    seats = set()
    for item in items:
        menu_item = db.query(MenuItem).filter(MenuItem.id == item.menu_item_id).first()
        item_list.append({
            "id": item.id,
            "name": menu_item.name if menu_item else "Unknown",
            "quantity": item.quantity,
            "price": float(item.unit_price),
            "total": float(item.total_price),
            "seat": item.seat_number
        })
        if item.seat_number:
            seats.add(item.seat_number)

    # Get payments
    payments = db.query(Payment).filter(Payment.order_id == order_id).limit(500).all()
    payment_list = [{
        "id": p.id,
        "amount": float(p.amount),
        "method": p.payment_method,
        "tip": float(p.tip or 0)
    } for p in payments]

    paid = sum(float(p.amount) for p in payments)
    balance = float(order.total or 0) - paid

    return CheckResponse(
        check_id=order.id,
        check_number=order.order_number,
        table_id=order.table_id or 0,
        seat_numbers=list(seats),
        items=item_list,
        subtotal=float(order.subtotal or 0),
        tax=float(order.tax or 0),
        discount=float(order.discount or 0),
        tip=sum(float(p.tip or 0) for p in payments),
        total=float(order.total or 0),
        status=order.status,
        payments=payment_list,
        balance_due=balance
    )


@router.post("/checks/{order_id}/split-by-seat", response_model=List[CheckResponse])
@limiter.limit("30/minute")
async def split_by_seat(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Split check by seat - creates one check per seat"""
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.venue_id == current_user.venue_id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    items = db.query(OrderItem).filter(OrderItem.order_id == order_id).limit(500).all()

    # Group items by seat
    by_seat = {}
    for item in items:
        seat = item.seat_number or 0
        if seat not in by_seat:
            by_seat[seat] = []
        by_seat[seat].append(item)

    if len(by_seat) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 seats to split")

    # Create new orders for each seat (except first which keeps original)
    new_checks = []
    seats_list = list(by_seat.keys())
    first_seat = seats_list[0]  # First seat keeps original order

    # Process all seats except the first one - create new orders for them
    for seat in seats_list[1:]:
        seat_items = by_seat[seat]

        # Calculate totals for this seat
        subtotal = sum(float(item.total_price) for item in seat_items)
        tax = subtotal * 0.10
        total = subtotal + tax

        # Create new order for this seat
        new_order = Order(
            order_number=f"{order.order_number}-S{seat}",
            table_id=order.table_id,
            session_id=order.session_id,
            station_id=order.station_id,
            venue_id=order.venue_id,
            waiter_id=order.waiter_id,
            status="new",
            parent_order_id=order.id,
            guest_count=1,
            subtotal=subtotal,
            tax=tax,
            total=total
        )
        db.add(new_order)
        db.flush()

        # Move items to new order
        for item in seat_items:
            item.order_id = new_order.id

        new_checks.append(new_order)

    # Recalculate totals for original order (first seat only)
    first_seat_items = by_seat[first_seat]
    subtotal = sum(float(item.total_price) for item in first_seat_items)
    tax = subtotal * 0.10
    order.subtotal = subtotal
    order.tax = tax
    order.total = subtotal + tax

    db.commit()

    # Return all checks
    all_orders = [order] + new_checks
    result = []

    for o in all_orders:
        check = await get_check(o.id, db, current_user)
        result.append(check)

    return result


@router.post("/checks/{order_id}/split-even")
@limiter.limit("30/minute")
async def split_even(
    request: Request,
    order_id: int,
    body: SplitEvenRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Split check evenly among N guests"""
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.venue_id == current_user.venue_id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    total = float(order.total or 0)
    split_amount = total / body.num_ways

    return {
        "original_total": total,
        "num_ways": body.num_ways,
        "amount_per_person": round(split_amount, 2),
        "checks": [
            {"check_number": f"{order.order_number}-{i+1}", "amount": round(split_amount, 2)}
            for i in range(body.num_ways)
        ]
    }


@router.post("/checks/{order_id}/split-items")
@limiter.limit("30/minute")
async def split_by_items(
    request: Request,
    order_id: int,
    body: SplitByItemRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Move specific items to a new or existing check"""
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.venue_id == current_user.venue_id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Get items to move
    items_to_move = db.query(OrderItem).filter(
        OrderItem.id.in_(body.item_ids),
        OrderItem.order_id == order_id
    ).limit(500).all()

    if not items_to_move:
        raise HTTPException(status_code=400, detail="No valid items to move")

    # Create new order or use existing
    if body.to_check_id:
        target_order = db.query(Order).filter(Order.id == body.to_check_id).first()
        if not target_order:
            raise HTTPException(status_code=404, detail="Target check not found")
    else:
        target_order = Order(
            order_number=f"{order.order_number}-SP",
            table_id=order.table_id,
            session_id=order.session_id,
            venue_id=order.venue_id,
            waiter_id=order.waiter_id,
            status="new",
            parent_order_id=order.id
        )
        db.add(target_order)
        db.flush()

    # Move items
    moved_total = 0.0
    for item in items_to_move:
        item.order_id = target_order.id
        moved_total += float(item.total_price)

    # Recalculate original order
    remaining_items = db.query(OrderItem).filter(OrderItem.order_id == order_id).limit(500).all()
    order.subtotal = sum(float(i.total_price) for i in remaining_items)
    order.tax = order.subtotal * 0.10
    order.total = order.subtotal + order.tax

    # Calculate target order
    target_items = db.query(OrderItem).filter(OrderItem.order_id == target_order.id).limit(500).all()
    target_order.subtotal = sum(float(i.total_price) for i in target_items)
    target_order.tax = target_order.subtotal * 0.10
    target_order.total = target_order.subtotal + target_order.tax

    db.commit()

    return {
        "success": True,
        "original_check": {"id": order.id, "new_total": order.total},
        "new_check": {"id": target_order.id, "total": target_order.total}
    }


@router.post("/checks/merge")
@limiter.limit("30/minute")
async def merge_checks(
    request: Request,
    body: MergeChecksRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Merge multiple checks into one"""
    orders = db.query(Order).filter(
        Order.id.in_(body.check_ids),
        Order.venue_id == current_user.venue_id
    ).limit(500).all()

    if len(orders) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 checks to merge")

    # Keep first order as target
    target = orders[0]

    # Move all items from other orders to target
    for order in orders[1:]:
        items = db.query(OrderItem).filter(OrderItem.order_id == order.id).limit(500).all()
        for item in items:
            item.order_id = target.id
        order.status = "merged"

    # Recalculate target
    all_items = db.query(OrderItem).filter(OrderItem.order_id == target.id).limit(500).all()
    target.subtotal = sum(float(i.total_price) for i in all_items)
    target.tax = target.subtotal * 0.10
    target.total = target.subtotal + target.tax

    db.commit()

    return {
        "success": True,
        "merged_check_id": target.id,
        "new_total": target.total,
        "items_count": len(all_items)
    }


# ============================================================================
# PAYMENT PROCESSING
# ============================================================================

@router.post("/payments", response_model=QuickActionResponse)
@limiter.limit("30/minute")
async def process_payment(
    request: Request,
    body: PaymentRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Process a payment for a check"""
    order = db.query(Order).filter(
        Order.id == body.check_id,
        Order.venue_id == current_user.venue_id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Check not found")

    # Calculate existing payments
    existing_payments = db.query(Payment).filter(Payment.order_id == order.id).limit(500).all()
    paid = sum(float(p.amount) for p in existing_payments)
    balance = float(order.total or 0) - paid

    if body.amount > balance + 0.01:  # Allow small rounding
        raise HTTPException(status_code=400, detail=f"Payment exceeds balance. Balance due: ${balance:.2f}")

    # Create payment
    payment = Payment(
        venue_id=current_user.venue_id,
        order_id=order.id,
        amount=body.amount,
        tip=body.tip_amount,
        payment_method=body.payment_method.value,
        card_last_four=body.card_last_four,
        auth_code=body.auth_code,
        status="completed",
        processed_by=current_user.id,
        processed_at=datetime.now(timezone.utc)
    )
    db.add(payment)

    # Check if fully paid
    new_balance = balance - body.amount
    if new_balance <= 0.01:
        order.status = "paid"

    db.commit()

    change = max(0, body.amount - balance) if body.payment_method == PaymentMethod.CASH else 0

    return QuickActionResponse(
        success=True,
        message=f"Payment of ${body.amount:.2f} processed",
        data={
            "payment_id": payment.id,
            "amount": body.amount,
            "tip": body.tip_amount,
            "change": change,
            "balance_remaining": max(0, new_balance),
            "fully_paid": new_balance <= 0.01
        }
    )


@router.post("/payments/split-tender", response_model=QuickActionResponse)
@limiter.limit("30/minute")
async def split_tender_payment(
    request: Request,
    body: SplitTenderRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Process split payment across multiple tenders"""
    order = db.query(Order).filter(
        Order.id == body.check_id,
        Order.venue_id == current_user.venue_id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Check not found")

    total_paying = sum(p.amount for p in body.payments)

    # Process each payment
    for payment_req in body.payments:
        payment = Payment(
            venue_id=current_user.venue_id,
            order_id=order.id,
            amount=payment_req.amount,
            tip=payment_req.tip_amount,
            payment_method=payment_req.payment_method.value,
            card_last_four=payment_req.card_last_four,
            status="completed",
            processed_by=current_user.id,
            processed_at=datetime.now(timezone.utc)
        )
        db.add(payment)

    # Check if fully paid
    all_payments = db.query(Payment).filter(Payment.order_id == order.id).limit(500).all()
    total_paid = sum(float(p.amount) for p in all_payments) + total_paying

    if total_paid >= float(order.total or 0):
        order.status = "paid"

    db.commit()

    return QuickActionResponse(
        success=True,
        message=f"Split payment of ${total_paying:.2f} across {len(body.payments)} tenders",
        data={"total_paid": total_paid}
    )


@router.post("/checks/{check_id}/discount", response_model=QuickActionResponse)
@limiter.limit("30/minute")
async def apply_discount(
    request: Request,
    check_id: int,
    body: ApplyDiscountRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Apply discount to a check (may require manager approval)"""
    order = db.query(Order).filter(
        Order.id == check_id,
        Order.venue_id == current_user.venue_id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Check not found")

    # Check if manager approval needed (for discounts > 10%)
    if body.discount_type == "percent" and body.discount_value > 10:
        if current_user.role not in ["owner", "manager"]:
            if not body.manager_pin:
                raise HTTPException(status_code=403, detail="Manager PIN required for discounts over 10%")
            # Verify manager PIN
            managers = db.query(StaffUser).filter(
                or_(StaffUser.location_id == current_user.venue_id, StaffUser.location_id.is_(None)),
                StaffUser.role.in_([StaffRole.ADMIN, StaffRole.MANAGER]),
                StaffUser.pin_code.isnot(None)
            ).limit(500).all()
            valid = False
            for mgr in managers:
                if verify_pin(body.manager_pin, mgr.pin_code):
                    valid = True
                    break
            if not valid:
                raise HTTPException(status_code=403, detail="Invalid manager PIN")

    # Calculate discount
    subtotal = float(order.subtotal or 0)
    if body.discount_type == "percent":
        discount = subtotal * (body.discount_value / 100)
    else:
        discount = body.discount_value

    order.discount = discount
    order.discount_reason = body.reason
    order.total = subtotal + float(order.tax or 0) - discount

    db.commit()

    return QuickActionResponse(
        success=True,
        message=f"Applied ${discount:.2f} discount",
        data={"new_total": order.total}
    )


@router.post("/checks/{check_id}/auto-gratuity", response_model=QuickActionResponse)
@limiter.limit("30/minute")
async def apply_auto_gratuity(
    request: Request,
    check_id: int,
    body: AutoGratuityRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Apply auto-gratuity to a check"""
    order = db.query(Order).filter(
        Order.id == check_id,
        Order.venue_id == current_user.venue_id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Check not found")

    subtotal = float(order.subtotal or 0)
    gratuity = subtotal * (body.gratuity_percent / 100)

    order.auto_gratuity = gratuity
    order.total = subtotal + float(order.tax or 0) - float(order.discount or 0) + gratuity

    db.commit()

    return QuickActionResponse(
        success=True,
        message=f"Applied {body.gratuity_percent}% auto-gratuity (${gratuity:.2f})",
        data={"gratuity": gratuity, "new_total": order.total}
    )


@router.post("/items/{item_id}/void", response_model=QuickActionResponse)
@limiter.limit("30/minute")
async def void_item(
    request: Request,
    item_id: int,
    body: VoidItemRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Void an item (requires manager approval)"""
    item = db.query(OrderItem).filter(OrderItem.id == item_id).first()

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Verify manager approval
    if current_user.role not in ["owner", "manager"]:
        if not body.manager_pin:
            raise HTTPException(status_code=403, detail="Manager PIN required to void items")
        managers = db.query(StaffUser).filter(
            StaffUser.location_id == current_user.venue_id,
            StaffUser.role.in_([StaffRole.ADMIN, StaffRole.MANAGER]),
            StaffUser.pin_code.isnot(None)
        ).limit(500).all()
        valid = False
        for mgr in managers:
            if verify_pin(body.manager_pin, mgr.pin_code):
                valid = True
                break
        if not valid:
            raise HTTPException(status_code=403, detail="Invalid manager PIN")

    # Void item
    item.status = "voided"
    item.void_reason = body.reason
    item.voided_by = current_user.id
    item.voided_at = datetime.now(timezone.utc)

    # Refund stock for voided item
    menu_item = db.query(MenuItem).filter(MenuItem.id == item.menu_item_id).first()
    order = db.query(Order).filter(Order.id == item.order_id).first()
    try:
        stock_service = StockDeductionService(db)
        stock_service.refund_for_order(
            order_items=[{
                "menu_item_id": item.menu_item_id,
                "quantity": item.quantity,
                "name": menu_item.name if menu_item else "Unknown",
            }],
            location_id=getattr(order, 'location_id', None) or 1 if order else 1,
            reference_type="waiter_void",
            reference_id=item.id,
        )
        logger.info(f"Stock refund for voided item {item.id}")
    except Exception as e:
        logger.warning(f"Stock refund failed for voided item {item.id}: {e}")

    # Recalculate order total
    if order:
        active_items = db.query(OrderItem).filter(
            OrderItem.order_id == order.id,
            OrderItem.status != "voided"
        ).limit(500).all()
        order.subtotal = sum(float(i.total_price) for i in active_items)
        order.tax = order.subtotal * 0.10
        order.total = order.subtotal + order.tax - float(order.discount or 0)

    db.commit()

    return QuickActionResponse(
        success=True,
        message="Item voided",
        data={"new_total": order.total if order else 0}
    )


@router.post("/items/{item_id}/comp", response_model=QuickActionResponse)
@limiter.limit("30/minute")
async def comp_item(
    request: Request,
    item_id: int,
    body: CompItemRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Comp an item (zero out price, requires manager approval)"""
    item = db.query(OrderItem).filter(OrderItem.id == item_id).first()

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Verify manager approval
    if current_user.role not in ["owner", "manager"]:
        if not body.manager_pin:
            raise HTTPException(status_code=403, detail="Manager PIN required to comp items")
        managers = db.query(StaffUser).filter(
            StaffUser.location_id == current_user.venue_id,
            StaffUser.role.in_([StaffRole.ADMIN, StaffRole.MANAGER]),
            StaffUser.pin_code.isnot(None)
        ).limit(500).all()
        valid = False
        for mgr in managers:
            if verify_pin(body.manager_pin, mgr.pin_code):
                valid = True
                break
        if not valid:
            raise HTTPException(status_code=403, detail="Invalid manager PIN")

    # Comp item
    original_price = float(item.total_price)
    item.total_price = 0
    item.comp_reason = body.reason
    item.comped_by = current_user.id
    item.comped_at = datetime.now(timezone.utc)

    # Recalculate order total
    order = db.query(Order).filter(Order.id == item.order_id).first()
    if order:
        active_items = db.query(OrderItem).filter(
            OrderItem.order_id == order.id,
            OrderItem.status != "voided"
        ).limit(500).all()
        order.subtotal = sum(float(i.total_price) for i in active_items)
        order.tax = order.subtotal * 0.10
        order.total = order.subtotal + order.tax - float(order.discount or 0)

    db.commit()

    return QuickActionResponse(
        success=True,
        message=f"Item comped (${original_price:.2f})",
        data={"comped_amount": original_price, "new_total": order.total if order else 0}
    )


# ============================================================================
# TABLE MANAGEMENT / FLOOR PLAN
# ============================================================================


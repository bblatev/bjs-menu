"""Waiter Terminal API routes - using database models."""

import asyncio
import logging
from typing import List, Optional
from datetime import datetime, timezone
from decimal import Decimal
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel

from app.db.session import DbSession
from app.models.restaurant import Table, MenuItem, Check, CheckItem, CheckPayment, KitchenOrder
from app.models.hardware import WaiterCall as WaiterCallModel
from app.services.stock_deduction_service import StockDeductionService

logger = logging.getLogger(__name__)


async def broadcast_waiter_call(call_data: dict):
    """Broadcast waiter call update to all connected WebSocket clients."""
    try:
        from app.main import get_ws_manager
        manager = get_ws_manager()
        await manager.broadcast({
            "type": "waiter_call",
            "action": "new",
            "data": call_data
        }, "waiter-calls")
    except Exception as e:
        logger.warning(f"WebSocket broadcast error: {e}")

router = APIRouter()


# ============== PYDANTIC MODELS ==============

class TableResponse(BaseModel):
    table_id: int
    table_name: str
    capacity: int
    status: str
    current_check_id: Optional[int] = None
    guest_count: Optional[int] = None
    time_seated_minutes: Optional[int] = None
    current_total: Optional[float] = None


class MenuItemResponse(BaseModel):
    id: int
    name: str
    price: float
    category: str
    image: Optional[str] = None


class OrderItemCreate(BaseModel):
    menu_item_id: int
    quantity: int
    seat_number: Optional[int] = None
    course: Optional[str] = None
    modifiers: Optional[List[str]] = None
    special_instructions: Optional[str] = None


class OrderCreate(BaseModel):
    table_id: int
    items: List[OrderItemCreate]
    guest_count: Optional[int] = None
    send_to_kitchen: bool = True


class CheckItemResponse(BaseModel):
    id: int
    name: str
    quantity: int
    price: float
    total: float
    seat: Optional[int] = None
    status: Optional[str] = None


class CheckResponse(BaseModel):
    check_id: int
    items: List[CheckItemResponse]
    subtotal: float
    tax: float
    discount: float
    total: float
    balance_due: float
    payments: List[dict]


class DiscountRequest(BaseModel):
    discount_type: str  # "percent" or "amount"
    discount_value: float
    reason: Optional[str] = None
    manager_pin: Optional[str] = None


class VoidRequest(BaseModel):
    reason: str
    manager_pin: Optional[str] = None


class PaymentRequest(BaseModel):
    check_id: int
    amount: float
    payment_method: str  # "cash" or "card"
    tip_amount: Optional[float] = None


# ============== HELPER FUNCTIONS ==============

def table_to_response(table: Table, db: DbSession) -> dict:
    """Convert database table to response format."""
    # Find active check for this table
    active_check = db.query(Check).filter(
        Check.table_id == table.id,
        Check.status == "open"
    ).first()

    time_seated = None
    if active_check and active_check.opened_at:
        time_seated = int((datetime.now(timezone.utc) - active_check.opened_at).total_seconds() / 60)

    return {
        "table_id": table.id,
        "table_name": f"Table {table.number}",
        "capacity": table.capacity or 4,
        "status": table.status or "available",
        "current_check_id": active_check.id if active_check else None,
        "guest_count": active_check.guest_count if active_check else None,
        "time_seated_minutes": time_seated,
        "current_total": float(active_check.total) if active_check else None,
    }


def check_to_response(check: Check) -> dict:
    """Convert database check to response format."""
    items = []
    for item in check.items:
        items.append({
            "id": item.id,
            "name": item.name,
            "quantity": item.quantity,
            "price": float(item.price),
            "total": float(item.total),
            "seat": item.seat_number,
            "status": item.status,
        })

    payments = []
    for payment in check.payments:
        payments.append({
            "amount": float(payment.amount),
            "method": payment.payment_type,
            "tip": float(payment.tip) if payment.tip else 0,
            "processed_at": payment.created_at.isoformat() if payment.created_at else None,
        })

    return {
        "check_id": check.id,
        "table_id": check.table_id,
        "items": items,
        "subtotal": float(check.subtotal or 0),
        "tax": float(check.tax or 0),
        "discount": float(check.discount or 0),
        "total": float(check.total or 0),
        "balance_due": float(check.balance_due or 0),
        "payments": payments,
        "created_at": check.opened_at.isoformat() if check.opened_at else None,
        "status": check.status,
    }


def recalculate_check(check: Check, db: DbSession):
    """Recalculate check totals."""
    subtotal = Decimal("0")
    for item in check.items:
        if item.status != "voided":
            subtotal += item.total

    check.subtotal = subtotal
    check.tax = subtotal * Decimal("0.1")  # 10% tax
    check.total = check.subtotal + check.tax - (check.discount or Decimal("0"))

    total_paid = sum(p.amount for p in check.payments)
    check.balance_due = max(Decimal("0"), check.total - total_paid)

    db.commit()


# ============== ROUTES ==============

@router.get("/sections")
def get_sections(db: DbSession):
    """Get all floor sections/zones."""
    tables = db.query(Table).all()
    sections = {}
    for t in tables:
        section = t.area or "Main Floor"
        if section not in sections:
            sections[section] = {"name": section, "tables": [], "table_count": 0}
        sections[section]["tables"].append(t.number)
        sections[section]["table_count"] += 1

    return {
        "sections": list(sections.values()),
        "total_tables": len(tables),
    }


@router.get("/floor-plan")
def get_floor_plan(db: DbSession):
    """Get all tables with status."""
    tables = db.query(Table).order_by(Table.number).all()
    return [table_to_response(t, db) for t in tables]


@router.get("/menu/quick")
def get_quick_menu(db: DbSession):
    """Get menu items for quick ordering."""
    items = db.query(MenuItem).filter(MenuItem.available == True).all()
    return [
        {
            "id": item.id,
            "name": item.name,
            "price": float(item.price),
            "category": item.category,
            "image": item.image_url,
        }
        for item in items
    ]


@router.get("/tables")
def get_tables(db: DbSession):
    """Get all tables (alias for floor-plan)."""
    tables = db.query(Table).order_by(Table.number).all()
    table_list = [table_to_response(t, db) for t in tables]
    return {"tables": table_list, "total": len(table_list)}


@router.get("/menu")
def get_menu(db: DbSession):
    """Get menu items (alias for menu/quick)."""
    items = db.query(MenuItem).filter(MenuItem.available == True).all()
    item_list = [
        {
            "id": item.id,
            "name": item.name,
            "price": float(item.price),
            "category": item.category,
            "image": item.image_url,
        }
        for item in items
    ]
    return {"items": item_list, "total": len(item_list)}


@router.get("/checks")
def get_all_checks(db: DbSession):
    """Get all active checks."""
    checks = db.query(Check).filter(Check.status == "open").all()
    return {"checks": [check_to_response(c) for c in checks], "total": len(checks)}


@router.get("/orders/stats")
def get_waiter_order_stats(db: DbSession):
    """Get order/check statistics."""
    from sqlalchemy import func

    total_checks = db.query(Check).count()
    open_checks = db.query(Check).filter(Check.status == "open").count()
    closed_checks = db.query(Check).filter(Check.status == "closed").count()

    revenue_result = db.query(func.sum(Check.total)).filter(
        Check.status == "closed"
    ).scalar()
    total_revenue = float(revenue_result) if revenue_result else 0

    return {
        "total_orders": total_checks,
        "pending": open_checks,
        "in_progress": open_checks,
        "completed": closed_checks,
        "cancelled": 0,
        "total_revenue": total_revenue,
        "average_order_value": total_revenue / closed_checks if closed_checks > 0 else 0,
    }


@router.post("/tables/{table_id}/seat")
def seat_table(
    db: DbSession,
    table_id: int,
    guest_count: int = Query(2),
):
    """Seat guests at a table."""
    table = db.query(Table).filter(Table.id == table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    if table.status != "available":
        raise HTTPException(status_code=400, detail="Table is not available")

    # Create new check
    check = Check(
        table_id=table.id,
        guest_count=guest_count,
        status="open",
        subtotal=Decimal("0"),
        tax=Decimal("0"),
        discount=Decimal("0"),
        total=Decimal("0"),
        balance_due=Decimal("0"),
    )
    db.add(check)

    # Update table status
    table.status = "occupied"

    db.commit()
    db.refresh(check)

    return {"status": "ok", "table_id": table_id, "check_id": check.id}


@router.post("/tables/{table_id}/clear")
def clear_table(db: DbSession, table_id: int):
    """Clear a table after payment."""
    table = db.query(Table).filter(Table.id == table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    # Close any open checks for this table
    open_checks = db.query(Check).filter(
        Check.table_id == table_id,
        Check.status == "open"
    ).all()
    for check in open_checks:
        check.status = "closed"
        check.closed_at = datetime.now(timezone.utc)

    table.status = "available"
    db.commit()

    return {"status": "ok"}


@router.get("/checks/{check_id}")
def get_check(db: DbSession, check_id: int):
    """Get check details."""
    check = db.query(Check).filter(Check.id == check_id).first()
    if not check:
        raise HTTPException(status_code=404, detail="Check not found")

    return check_to_response(check)


@router.get("/orders")
def list_orders(db: DbSession, status: Optional[str] = None, limit: int = 50):
    """List all orders/checks."""
    query = db.query(Check)
    if status:
        query = query.filter(Check.status == status)

    checks = query.order_by(Check.opened_at.desc()).limit(limit).all()

    return {
        "orders": [check_to_response(c) for c in checks],
        "total": len(checks)
    }


@router.post("/orders")
def create_order(db: DbSession, order: OrderCreate):
    """Create a new order."""
    table = db.query(Table).filter(Table.id == order.table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    # Find active check for table
    check = db.query(Check).filter(
        Check.table_id == order.table_id,
        Check.status == "open"
    ).first()

    if not check:
        raise HTTPException(status_code=400, detail="No active check for this table")

    # Add items to check
    items_added = 0
    kitchen_items = []
    for item in order.items:
        menu_item = db.query(MenuItem).filter(MenuItem.id == item.menu_item_id).first()
        if not menu_item:
            continue

        check_item = CheckItem(
            check_id=check.id,
            menu_item_id=menu_item.id,
            name=menu_item.name,
            quantity=item.quantity,
            price=menu_item.price,
            total=menu_item.price * item.quantity,
            seat_number=item.seat_number,
            course=item.course,
            status="ordered",
            notes=item.special_instructions,
            modifiers=item.modifiers,
        )
        db.add(check_item)
        items_added += 1

        # Collect items for kitchen order
        kitchen_items.append({
            "menu_item_id": menu_item.id,
            "name": menu_item.name,
            "price": float(menu_item.price),
            "quantity": item.quantity,
            "notes": item.special_instructions,
            "total": float(menu_item.price * item.quantity),
        })

    db.commit()

    # Recalculate totals
    db.refresh(check)
    recalculate_check(check, db)

    # Create a kitchen order so it appears on kitchen display
    if kitchen_items:
        kitchen_order = KitchenOrder(
            check_id=check.id,
            table_number=table.number if table else None,
            status="pending",
            items=kitchen_items,
            notes=None,
            location_id=1,  # Default location
        )
        db.add(kitchen_order)
        db.commit()

    # Deduct stock for ordered items
    stock_deduction = None
    if kitchen_items:
        try:
            stock_service = StockDeductionService(db)
            stock_deduction = stock_service.deduct_for_order(
                order_items=kitchen_items,
                location_id=1,
                reference_type="pos_sale",
                reference_id=check.id,
            )
            logger.info(f"Stock deduction for check {check.id}: {stock_deduction['total_ingredients_deducted']} ingredients")
        except Exception as e:
            logger.warning(f"Stock deduction failed for check {check.id}: {e}")

    return {
        "status": "ok",
        "check_id": check.id,
        "items_added": items_added,
        "stock_deduction": stock_deduction,
    }


@router.post("/orders/{check_id}/fire-course")
def fire_course(db: DbSession, check_id: int, course: str = "main"):
    """Fire a course to the kitchen."""
    check = db.query(Check).filter(Check.id == check_id).first()
    if not check:
        raise HTTPException(status_code=404, detail="Check not found")

    # Update items for this course
    now = datetime.now(timezone.utc)
    for item in check.items:
        if item.course == course or not item.fired_at:
            item.status = "fired"
            item.fired_at = now

    db.commit()

    return {"status": "ok", "course": course, "fired_at": now.isoformat()}


@router.post("/checks/{check_id}/discount")
def apply_discount(db: DbSession, check_id: int, request: DiscountRequest):
    """Apply discount to check."""
    check = db.query(Check).filter(Check.id == check_id).first()
    if not check:
        raise HTTPException(status_code=404, detail="Check not found")

    if request.discount_type == "percent":
        check.discount = check.subtotal * Decimal(str(request.discount_value / 100))
    else:
        check.discount = Decimal(str(request.discount_value))

    recalculate_check(check, db)

    return {"status": "ok", "discount_applied": float(check.discount)}


@router.post("/items/{item_id}/void")
def void_item(db: DbSession, item_id: int, request: VoidRequest):
    """Void an item from check."""
    item = db.query(CheckItem).filter(CheckItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    item.status = "voided"
    item.voided_at = datetime.now(timezone.utc)
    item.void_reason = request.reason

    # Recalculate check
    check = db.query(Check).filter(Check.id == item.check_id).first()
    if check:
        recalculate_check(check, db)

    return {"status": "ok", "voided": True}


@router.post("/checks/{check_id}/split-even")
def split_check_even(db: DbSession, check_id: int, num_ways: int = 2):
    """Split check evenly."""
    check = db.query(Check).filter(Check.id == check_id).first()
    if not check:
        raise HTTPException(status_code=404, detail="Check not found")

    amount_per_person = float(check.total) / num_ways

    return {
        "status": "ok",
        "num_ways": num_ways,
        "amount_per_person": amount_per_person,
        "total": float(check.total)
    }


@router.post("/checks/{check_id}/split-by-seat")
def split_check_by_seat(db: DbSession, check_id: int):
    """Split check by seat."""
    check = db.query(Check).filter(Check.id == check_id).first()
    if not check:
        raise HTTPException(status_code=404, detail="Check not found")

    # Group items by seat
    seats = {}
    for item in check.items:
        if item.status == "voided":
            continue
        seat = item.seat_number or 1
        if seat not in seats:
            seats[seat] = []
        seats[seat].append({
            "id": item.id,
            "name": item.name,
            "quantity": item.quantity,
            "price": float(item.price),
            "total": float(item.total),
        })

    # Create split info
    splits = []
    for seat, items in seats.items():
        subtotal = sum(i["total"] for i in items)
        tax = subtotal * 0.1
        splits.append({
            "seat": seat,
            "items": items,
            "subtotal": subtotal,
            "tax": tax,
            "total": subtotal + tax
        })

    return splits


@router.post("/payments")
def process_payment(db: DbSession, payment: PaymentRequest):
    """Process a payment."""
    check = db.query(Check).filter(Check.id == payment.check_id).first()
    if not check:
        raise HTTPException(status_code=404, detail="Check not found")

    # Add payment
    check_payment = CheckPayment(
        check_id=check.id,
        payment_type=payment.payment_method,
        amount=Decimal(str(payment.amount)),
        tip=Decimal(str(payment.tip_amount or 0)),
    )
    db.add(check_payment)
    db.commit()

    # Recalculate balance
    db.refresh(check)
    recalculate_check(check, db)

    total_paid = sum(float(p.amount) for p in check.payments)

    return {
        "status": "ok",
        "data": {
            "fully_paid": float(check.balance_due) <= 0,
            "balance_remaining": float(check.balance_due),
            "total_paid": total_paid
        }
    }


@router.post("/checks/{check_id}/print")
def print_check(db: DbSession, check_id: int):
    """Print check (non-fiscal)."""
    check = db.query(Check).filter(Check.id == check_id).first()
    if not check:
        raise HTTPException(status_code=404, detail="Check not found")

    return {"status": "ok", "printed": True}


# ==================== WAITER CALLS (DATABASE) ====================

class WaiterCallCreate(BaseModel):
    table_id: int
    call_type: str = "assistance"  # assistance, check, refill, other
    notes: Optional[str] = None


@router.get("/calls")
def list_waiter_calls(db: DbSession, status: Optional[str] = None):
    """List all waiter calls."""
    query = db.query(WaiterCallModel)
    if status:
        query = query.filter(WaiterCallModel.status == status)

    calls = query.order_by(WaiterCallModel.created_at.desc()).all()

    call_list = [{
        "id": call.id,
        "table_id": call.table_id,
        "table_name": call.table_number,
        "call_type": call.call_type,
        "notes": call.message,
        "status": call.status,
        "created_at": call.created_at.isoformat() if call.created_at else None,
        "acknowledged_at": call.acknowledged_at.isoformat() if call.acknowledged_at else None,
        "completed_at": call.completed_at.isoformat() if call.completed_at else None,
    } for call in calls]

    return {"calls": call_list, "total": len(call_list)}


@router.post("/calls")
def create_waiter_call(db: DbSession, call: WaiterCallCreate, background_tasks: BackgroundTasks):
    """Create a new waiter call (e.g., from guest tablet)."""
    # Get table info
    table = db.query(Table).filter(Table.id == call.table_id).first()
    table_name = f"Table {table.number}" if table else f"Table {call.table_id}"

    new_call = WaiterCallModel(
        table_id=call.table_id,
        table_number=table_name,
        call_type=call.call_type,
        message=call.notes,
        status="pending",
    )
    db.add(new_call)
    db.commit()
    db.refresh(new_call)

    call_data = {
        "id": new_call.id,
        "table_id": new_call.table_id,
        "table_name": new_call.table_number,
        "call_type": new_call.call_type,
        "notes": new_call.message,
        "status": new_call.status,
        "created_at": new_call.created_at.isoformat() if new_call.created_at else None,
    }

    # Broadcast to WebSocket clients in background
    background_tasks.add_task(lambda: asyncio.run(broadcast_waiter_call(call_data)))

    return {"status": "created", "call": call_data}


@router.post("/calls/{call_id}/acknowledge")
def acknowledge_call(db: DbSession, call_id: int):
    """Acknowledge a waiter call."""
    call = db.query(WaiterCallModel).filter(WaiterCallModel.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    call.status = "acknowledged"
    call.acknowledged_at = datetime.now(timezone.utc)
    db.commit()

    return {"status": "ok", "call": {
        "id": call.id,
        "table_id": call.table_id,
        "status": call.status,
        "acknowledged_at": call.acknowledged_at.isoformat() if call.acknowledged_at else None,
    }}


@router.post("/calls/{call_id}/complete")
def complete_call(db: DbSession, call_id: int):
    """Mark a waiter call as completed."""
    call = db.query(WaiterCallModel).filter(WaiterCallModel.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    call.status = "completed"
    call.completed_at = datetime.now(timezone.utc)
    db.commit()

    return {"status": "ok", "call": {
        "id": call.id,
        "table_id": call.table_id,
        "status": call.status,
        "completed_at": call.completed_at.isoformat() if call.completed_at else None,
    }}


@router.delete("/calls/{call_id}")
def dismiss_call(db: DbSession, call_id: int):
    """Dismiss/delete a waiter call."""
    call = db.query(WaiterCallModel).filter(WaiterCallModel.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    db.delete(call)
    db.commit()

    return {"status": "dismissed", "call_id": call_id}


# ============== CHECK TRANSFER ==============

class TransferCheckRequest(BaseModel):
    to_table_id: int
    items_to_transfer: Optional[List[int]] = None  # If None, transfer all items


@router.post("/checks/{check_id}/transfer")
def transfer_check(db: DbSession, check_id: int, request: TransferCheckRequest):
    """Transfer check or specific items to another table.

    If items_to_transfer is None or empty, transfers the entire check.
    Otherwise, transfers only specified items to a new check on the destination table.
    """
    # Get source check
    source_check = db.query(Check).filter(Check.id == check_id).first()
    if not source_check:
        raise HTTPException(status_code=404, detail="Check not found")

    if source_check.status != "open":
        raise HTTPException(status_code=400, detail="Can only transfer open checks")

    # Get destination table
    dest_table = db.query(Table).filter(Table.id == request.to_table_id).first()
    if not dest_table:
        raise HTTPException(status_code=404, detail="Destination table not found")

    # Get or create check on destination table
    dest_check = db.query(Check).filter(
        Check.table_id == request.to_table_id,
        Check.status == "open"
    ).first()

    transfer_all = not request.items_to_transfer

    if transfer_all:
        # Transfer entire check - just update the table_id
        old_table_id = source_check.table_id
        source_check.table_id = request.to_table_id

        # Update source table status
        old_table = db.query(Table).filter(Table.id == old_table_id).first()
        if old_table:
            old_table.status = "available"

        # Update destination table status
        dest_table.status = "occupied"

        db.commit()

        return {
            "status": "ok",
            "message": "Check transferred successfully",
            "check_id": source_check.id,
            "from_table_id": old_table_id,
            "to_table_id": request.to_table_id,
            "items_transferred": len(source_check.items),
        }
    else:
        # Transfer specific items
        if not dest_check:
            dest_check = Check(
                table_id=request.to_table_id,
                status="open",
                guest_count=1,
                opened_at=datetime.now(timezone.utc),
                subtotal=Decimal("0"),
                tax=Decimal("0"),
                discount=Decimal("0"),
                total=Decimal("0"),
                balance_due=Decimal("0"),
            )
            db.add(dest_check)
            db.flush()

        items_transferred = 0
        for item_id in request.items_to_transfer:
            item = db.query(CheckItem).filter(
                CheckItem.id == item_id,
                CheckItem.check_id == check_id
            ).first()
            if item:
                item.check_id = dest_check.id
                items_transferred += 1

        # Recalculate both checks
        recalculate_check(source_check, db)
        recalculate_check(dest_check, db)

        # Update table statuses
        dest_table.status = "occupied"

        # If source check is now empty, close it
        remaining_items = [i for i in source_check.items if i.status != "voided"]
        if not remaining_items:
            source_check.status = "closed"
            source_table = db.query(Table).filter(Table.id == source_check.table_id).first()
            if source_table:
                source_table.status = "available"

        db.commit()

        return {
            "status": "ok",
            "message": f"Transferred {items_transferred} items",
            "from_check_id": check_id,
            "to_check_id": dest_check.id,
            "to_table_id": request.to_table_id,
            "items_transferred": items_transferred,
        }

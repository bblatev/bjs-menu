"""Waiter Terminal API routes."""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.db.session import DbSession

router = APIRouter()


# ============== MODELS ==============

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


class CheckItem(BaseModel):
    id: int
    name: str
    quantity: int
    price: float
    total: float
    seat: Optional[int] = None
    status: Optional[str] = None


class CheckResponse(BaseModel):
    check_id: int
    items: List[CheckItem]
    subtotal: float
    tax: float
    discount: float
    total: float
    balance_due: float
    payments: List[dict]


class DiscountRequest(BaseModel):
    check_id: int
    discount_type: str  # "percent" or "amount"
    discount_value: float
    reason: Optional[str] = None
    manager_pin: Optional[str] = None


class VoidRequest(BaseModel):
    item_id: int
    reason: str
    manager_pin: Optional[str] = None


class PaymentRequest(BaseModel):
    check_id: int
    amount: float
    payment_method: str  # "cash" or "card"
    tip_amount: Optional[float] = None


# ============== IN-MEMORY DATA ==============

_tables = [
    {"table_id": i, "table_name": f"Table {i}", "capacity": 4 if i <= 10 else 2,
     "status": "available", "current_check_id": None, "guest_count": None,
     "time_seated_minutes": None, "current_total": None}
    for i in range(1, 21)
]

_menu_items = [
    {"id": 1, "name": "Chicken Wings", "price": 12.99, "category": "Appetizers", "image": None},
    {"id": 2, "name": "Nachos Supreme", "price": 14.99, "category": "Appetizers", "image": None},
    {"id": 3, "name": "Mozzarella Sticks", "price": 9.99, "category": "Appetizers", "image": None},
    {"id": 4, "name": "Classic Burger", "price": 15.99, "category": "Main", "image": None},
    {"id": 5, "name": "BBQ Ribs", "price": 24.99, "category": "Main", "image": None},
    {"id": 6, "name": "Grilled Salmon", "price": 22.99, "category": "Main", "image": None},
    {"id": 7, "name": "Caesar Salad", "price": 11.99, "category": "Salads", "image": None},
    {"id": 8, "name": "House Salad", "price": 8.99, "category": "Salads", "image": None},
    {"id": 9, "name": "Coca-Cola", "price": 3.50, "category": "Drinks", "image": None},
    {"id": 10, "name": "Sprite", "price": 3.50, "category": "Drinks", "image": None},
    {"id": 11, "name": "Draft Beer", "price": 6.00, "category": "Drinks", "image": None},
    {"id": 12, "name": "House Wine", "price": 8.00, "category": "Drinks", "image": None},
    {"id": 13, "name": "Margarita", "price": 10.00, "category": "Cocktails", "image": None},
    {"id": 14, "name": "Mojito", "price": 10.00, "category": "Cocktails", "image": None},
    {"id": 15, "name": "Chocolate Cake", "price": 7.99, "category": "Desserts", "image": None},
    {"id": 16, "name": "Ice Cream", "price": 5.99, "category": "Desserts", "image": None},
    {"id": 17, "name": "Fish & Chips", "price": 16.99, "category": "Main", "image": None},
    {"id": 18, "name": "Pasta Carbonara", "price": 14.99, "category": "Main", "image": None},
    {"id": 19, "name": "Steak 300g", "price": 29.99, "category": "Main", "image": None},
    {"id": 20, "name": "French Fries", "price": 5.99, "category": "Sides", "image": None},
]

_checks: dict = {}  # check_id -> check data
_next_check_id = 1000


# ============== ROUTES ==============

@router.get("/floor-plan", response_model=List[TableResponse])
def get_floor_plan(db: DbSession):
    """Get all tables with status."""
    return _tables


@router.get("/menu/quick", response_model=List[MenuItemResponse])
def get_quick_menu(db: DbSession):
    """Get menu items for quick ordering."""
    return _menu_items


@router.post("/tables/{table_id}/seat")
def seat_table(
    db: DbSession,
    table_id: int,
    guest_count: int = Query(2),
):
    """Seat guests at a table."""
    global _next_check_id

    for table in _tables:
        if table["table_id"] == table_id:
            if table["status"] != "available":
                raise HTTPException(status_code=400, detail="Table is not available")

            # Create new check
            check_id = _next_check_id
            _next_check_id += 1

            _checks[check_id] = {
                "check_id": check_id,
                "table_id": table_id,
                "items": [],
                "subtotal": 0,
                "tax": 0,
                "discount": 0,
                "total": 0,
                "balance_due": 0,
                "payments": [],
                "created_at": datetime.utcnow().isoformat()
            }

            table["status"] = "occupied"
            table["guest_count"] = guest_count
            table["current_check_id"] = check_id
            table["time_seated_minutes"] = 0
            table["current_total"] = 0

            return {"status": "ok", "table_id": table_id, "check_id": check_id}

    raise HTTPException(status_code=404, detail="Table not found")


@router.post("/tables/{table_id}/clear")
def clear_table(db: DbSession, table_id: int):
    """Clear a table after payment."""
    for table in _tables:
        if table["table_id"] == table_id:
            table["status"] = "available"
            table["guest_count"] = None
            table["current_check_id"] = None
            table["time_seated_minutes"] = None
            table["current_total"] = None
            return {"status": "ok"}

    raise HTTPException(status_code=404, detail="Table not found")


@router.get("/checks/{check_id}", response_model=CheckResponse)
def get_check(db: DbSession, check_id: int):
    """Get check details."""
    if check_id not in _checks:
        raise HTTPException(status_code=404, detail="Check not found")

    return _checks[check_id]


@router.post("/orders")
def create_order(db: DbSession, order: OrderCreate):
    """Create a new order."""
    # Find table's check
    table = None
    for t in _tables:
        if t["table_id"] == order.table_id:
            table = t
            break

    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    check_id = table.get("current_check_id")
    if not check_id or check_id not in _checks:
        raise HTTPException(status_code=400, detail="No active check for this table")

    check = _checks[check_id]

    # Add items to check
    for item in order.items:
        menu_item = next((m for m in _menu_items if m["id"] == item.menu_item_id), None)
        if not menu_item:
            continue

        check_item = {
            "id": len(check["items"]) + 1,
            "name": menu_item["name"],
            "quantity": item.quantity,
            "price": menu_item["price"],
            "total": menu_item["price"] * item.quantity,
            "seat": item.seat_number,
            "status": "ordered"
        }
        check["items"].append(check_item)

    # Recalculate totals
    check["subtotal"] = sum(i["total"] for i in check["items"] if i.get("status") != "voided")
    check["tax"] = check["subtotal"] * 0.1  # 10% tax
    check["total"] = check["subtotal"] + check["tax"] - check["discount"]
    check["balance_due"] = check["total"] - sum(p["amount"] for p in check["payments"])

    # Update table total
    table["current_total"] = check["total"]

    return {"status": "ok", "check_id": check_id, "items_added": len(order.items)}


@router.post("/orders/{check_id}/fire-course")
def fire_course(db: DbSession, check_id: int, course: str = "main"):
    """Fire a course to the kitchen."""
    if check_id not in _checks:
        raise HTTPException(status_code=404, detail="Check not found")

    return {"status": "ok", "course": course, "fired_at": datetime.utcnow().isoformat()}


@router.post("/checks/{check_id}/discount")
def apply_discount(db: DbSession, check_id: int, request: DiscountRequest):
    """Apply discount to check."""
    if check_id not in _checks:
        raise HTTPException(status_code=404, detail="Check not found")

    check = _checks[check_id]

    if request.discount_type == "percent":
        check["discount"] = check["subtotal"] * (request.discount_value / 100)
    else:
        check["discount"] = request.discount_value

    check["total"] = check["subtotal"] + check["tax"] - check["discount"]
    check["balance_due"] = check["total"] - sum(p["amount"] for p in check["payments"])

    return {"status": "ok", "discount_applied": check["discount"]}


@router.post("/items/{item_id}/void")
def void_item(db: DbSession, item_id: int, request: VoidRequest):
    """Void an item from check."""
    # Find item across all checks
    for check in _checks.values():
        for item in check["items"]:
            if item["id"] == item_id:
                item["status"] = "voided"

                # Recalculate
                check["subtotal"] = sum(i["total"] for i in check["items"] if i.get("status") != "voided")
                check["tax"] = check["subtotal"] * 0.1
                check["total"] = check["subtotal"] + check["tax"] - check["discount"]
                check["balance_due"] = check["total"] - sum(p["amount"] for p in check["payments"])

                return {"status": "ok", "voided": True}

    raise HTTPException(status_code=404, detail="Item not found")


@router.post("/checks/{check_id}/split-even")
def split_check_even(db: DbSession, check_id: int, num_ways: int = 2):
    """Split check evenly."""
    if check_id not in _checks:
        raise HTTPException(status_code=404, detail="Check not found")

    check = _checks[check_id]
    amount_per_person = check["total"] / num_ways

    return {
        "status": "ok",
        "num_ways": num_ways,
        "amount_per_person": amount_per_person,
        "total": check["total"]
    }


@router.post("/checks/{check_id}/split-by-seat")
def split_check_by_seat(db: DbSession, check_id: int):
    """Split check by seat."""
    if check_id not in _checks:
        raise HTTPException(status_code=404, detail="Check not found")

    check = _checks[check_id]

    # Group items by seat
    seats = {}
    for item in check["items"]:
        if item.get("status") == "voided":
            continue
        seat = item.get("seat", 1)
        if seat not in seats:
            seats[seat] = []
        seats[seat].append(item)

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
    if payment.check_id not in _checks:
        raise HTTPException(status_code=404, detail="Check not found")

    check = _checks[payment.check_id]

    # Add payment
    check["payments"].append({
        "amount": payment.amount,
        "method": payment.payment_method,
        "tip": payment.tip_amount or 0,
        "processed_at": datetime.utcnow().isoformat()
    })

    # Update balance
    total_paid = sum(p["amount"] for p in check["payments"])
    check["balance_due"] = max(0, check["total"] - total_paid)

    return {
        "status": "ok",
        "data": {
            "fully_paid": check["balance_due"] <= 0,
            "balance_remaining": check["balance_due"],
            "total_paid": total_paid
        }
    }


@router.post("/checks/{check_id}/print")
def print_check(db: DbSession, check_id: int):
    """Print check (non-fiscal)."""
    if check_id not in _checks:
        raise HTTPException(status_code=404, detail="Check not found")

    return {"status": "ok", "printed": True}

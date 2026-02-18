"""
Waiter Terminal API Endpoints
Comprehensive waiter/bartender POS functionality including:
- Order creation with seats and courses
- Bar tab management with pre-authorization
- Bill splitting (by item, seat, even, portions)
- Check merge and transfer
- Payment processing (cash, card, split tender)
- Table management and floor plan
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pydantic import BaseModel, Field
from enum import Enum

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.core.rbac import get_current_user
from app.core.rbac import RequireManager
from app.models import (
    StaffUser, StaffRole, Order, OrderItem, Table, MenuItem,
    TableSession, Payment, Customer, VenueStation
)
from app.core.security import verify_pin
from app.services.stock_deduction_service import StockDeductionService

import logging
logger = logging.getLogger(__name__)


router = APIRouter()


# ============================================================================
# ENUMS
# ============================================================================

class CourseType(str, Enum):
    DRINKS = "drinks"
    APPETIZER = "appetizer"
    SOUP_SALAD = "soup_salad"
    MAIN = "main"
    DESSERT = "dessert"
    AFTER_DINNER = "after_dinner"


class CheckStatus(str, Enum):
    OPEN = "open"
    PRINTED = "printed"
    PAID = "paid"
    VOIDED = "voided"


class TabStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    TRANSFERRED = "transferred"


class PaymentMethod(str, Enum):
    CASH = "cash"
    CARD = "card"
    MOBILE = "mobile"
    TAB = "tab"
    GIFT_CARD = "gift_card"
    COMP = "comp"


class SplitType(str, Enum):
    BY_ITEM = "by_item"
    BY_SEAT = "by_seat"
    EVEN = "even"
    CUSTOM = "custom"


# ============================================================================
# REQUEST/RESPONSE SCHEMAS
# ============================================================================

class OrderItemCreate(BaseModel):
    """Single item in an order"""
    menu_item_id: int
    quantity: int = 1
    seat_number: Optional[int] = None
    course: Optional[CourseType] = None
    modifiers: Optional[List[str]] = []
    special_instructions: Optional[str] = None
    price_override: Optional[float] = None


class WaiterOrderCreate(BaseModel):
    """Create order from waiter terminal"""
    table_id: int
    items: List[OrderItemCreate]
    guest_count: int = 1
    notes: Optional[str] = None
    send_to_kitchen: bool = True
    fire_immediately: bool = False


class WaiterOrderResponse(BaseModel):
    """Response for waiter order"""
    order_id: int
    order_number: str
    table_id: int
    table_name: str
    items: List[Dict[str, Any]]
    subtotal: float
    tax: float
    total: float
    status: str
    created_at: datetime
    waiter_name: str


class AddItemsRequest(BaseModel):
    """Add items to existing order"""
    items: List[OrderItemCreate]
    send_to_kitchen: bool = True


class FireCourseRequest(BaseModel):
    """Fire a specific course to kitchen"""
    course: CourseType
    notes: Optional[str] = None


class HoldCourseRequest(BaseModel):
    """Hold a course from firing"""
    course: CourseType
    reason: Optional[str] = None


# --- Bar Tab Schemas ---

class OpenTabRequest(BaseModel):
    """Open a new bar tab"""
    customer_name: str
    card_last_four: Optional[str] = None
    pre_auth_amount: float = 50.0
    phone: Optional[str] = None
    notes: Optional[str] = None


class TabResponse(BaseModel):
    """Bar tab response"""
    tab_id: int
    customer_name: str
    card_last_four: Optional[str]
    pre_auth_amount: float
    current_total: float
    items: List[Dict[str, Any]]
    status: str
    opened_at: datetime
    opened_by: str


class AddToTabRequest(BaseModel):
    """Add items to bar tab"""
    items: List[OrderItemCreate]


class TransferTabRequest(BaseModel):
    """Transfer tab to table"""
    table_id: int
    seat_number: Optional[int] = None


class CloseTabRequest(BaseModel):
    """Close bar tab"""
    tip_amount: float = 0.0
    payment_method: PaymentMethod = PaymentMethod.TAB


# --- Bill/Check Schemas ---

class CheckResponse(BaseModel):
    """Check/bill response"""
    check_id: int
    check_number: str
    table_id: int
    seat_numbers: List[int]
    items: List[Dict[str, Any]]
    subtotal: float
    tax: float
    discount: float
    tip: float
    total: float
    status: str
    payments: List[Dict[str, Any]]
    balance_due: float


class SplitByItemRequest(BaseModel):
    """Split check by moving items"""
    item_ids: List[int]
    to_check_id: Optional[int] = None  # None = create new check


class SplitBySeatRequest(BaseModel):
    """Split check by seat"""
    pass  # Will create one check per seat


class SplitEvenRequest(BaseModel):
    """Split check evenly"""
    num_ways: int = Field(..., ge=2, le=20)


class SplitItemPortionRequest(BaseModel):
    """Split single item into portions"""
    item_id: int
    portions: int = Field(..., ge=2, le=10)


class MergeChecksRequest(BaseModel):
    """Merge multiple checks"""
    check_ids: List[int] = Field(..., min_length=2)


class TransferItemsRequest(BaseModel):
    """Transfer items between checks"""
    item_ids: List[int]
    to_check_id: int


# --- Payment Schemas ---

class PaymentRequest(BaseModel):
    """Process payment"""
    check_id: int
    amount: float
    payment_method: PaymentMethod
    tip_amount: float = 0.0
    card_last_four: Optional[str] = None
    auth_code: Optional[str] = None


class SplitTenderRequest(BaseModel):
    """Split payment across multiple tenders"""
    check_id: int
    payments: List[PaymentRequest]


class ApplyDiscountRequest(BaseModel):
    """Apply discount to check"""
    discount_type: str = "percent"  # percent or amount
    discount_value: float
    reason: str
    manager_pin: Optional[str] = None


class AutoGratuityRequest(BaseModel):
    """Apply auto-gratuity"""
    gratuity_percent: float = 18.0


class VoidItemRequest(BaseModel):
    """Void an item"""
    reason: str
    manager_pin: Optional[str] = None


class CompItemRequest(BaseModel):
    """Comp an item"""
    reason: str
    manager_pin: Optional[str] = None


# --- Table Management Schemas ---

class TableStatusResponse(BaseModel):
    """Table status for floor plan"""
    table_id: int
    table_name: str
    capacity: int
    status: str  # available, occupied, reserved, dirty
    current_check_id: Optional[int]
    guest_count: Optional[int]
    server_name: Optional[str]
    seated_at: Optional[datetime]
    time_seated_minutes: Optional[int]
    current_total: Optional[float]


class TransferTableRequest(BaseModel):
    """Transfer table to another server"""
    to_waiter_id: int


class QuickActionResponse(BaseModel):
    """Response for quick actions"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


# ============================================================================
# ORDER MANAGEMENT ENDPOINTS
# ============================================================================

@router.get("/")
@limiter.limit("60/minute")
async def get_waiter_terminal_root(request: Request, db: Session = Depends(get_db), current_user: StaffUser = Depends(get_current_user)):
    """Waiter terminal overview."""
    return await get_floor_plan(request=request, db=db, current_user=current_user)


@router.post("/orders", response_model=WaiterOrderResponse)
@limiter.limit("30/minute")
async def create_waiter_order(
    request: Request,
    body: WaiterOrderCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Create a new order from waiter terminal.
    Supports seat assignment, course grouping, and modifiers.
    """
    # Verify table exists and is in waiter's venue
    table = db.query(Table).filter(
        Table.id == body.table_id,
        or_(Table.location_id == current_user.venue_id, Table.location_id.is_(None))
    ).first()

    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    # Get or create active session for table
    session = db.query(TableSession).filter(
        TableSession.table_id == body.table_id,
        TableSession.status == "active"
    ).first()

    if not session:
        session = TableSession(
            table_id=body.table_id,
            venue_id=current_user.venue_id,
            guest_count=body.guest_count,
            waiter_id=current_user.id,
            status="active",
            started_at=datetime.now(timezone.utc)
        )
        db.add(session)
        db.flush()

    # Create order
    order_number = f"W{datetime.now(timezone.utc).strftime('%H%M%S')}{table.id:02d}"

    # Get default station (first available or kitchen)
    default_station = db.query(VenueStation).filter(
        VenueStation.venue_id == current_user.venue_id
    ).first()
    station_id = default_station.id if default_station else 1

    order = Order(
        order_number=order_number,
        table_id=body.table_id,
        session_id=session.id,
        station_id=station_id,
        venue_id=current_user.venue_id,
        waiter_id=current_user.id,
        status="new" if body.send_to_kitchen else "draft",
        notes=body.notes,
        guest_count=body.guest_count,
        total=0.0,
        subtotal=0.0,
        tax=0.0,
        tip_amount=0.0,
        is_rush=False,
        is_vip=False,
        order_type="dine-in",
        payment_status="pending"
    )
    db.add(order)
    db.flush()

    # Add items
    subtotal = 0.0
    order_items = []

    for item_data in body.items:
        menu_item = db.query(MenuItem).filter(
            MenuItem.id == item_data.menu_item_id
        ).first()

        if not menu_item:
            raise HTTPException(
                status_code=400,
                detail=f"Menu item {item_data.menu_item_id} not found"
            )

        price = item_data.price_override or float(menu_item.price)
        item_total = price * item_data.quantity
        subtotal += item_total

        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=menu_item.id,
            quantity=item_data.quantity,
            unit_price=price,
            total_price=item_total,
            subtotal=item_total,
            seat_number=item_data.seat_number,
            course=item_data.course.value if item_data.course else None,
            modifiers_text=",".join(item_data.modifiers) if item_data.modifiers else None,
            special_instructions=item_data.special_instructions,
            status="pending" if body.send_to_kitchen else "draft",
            fired=body.fire_immediately
        )
        db.add(order_item)
        order_items.append({
            "id": None,  # Will be set after flush
            "menu_item_id": menu_item.id,
            "name": menu_item.name,
            "quantity": item_data.quantity,
            "price": price,
            "total": item_total,
            "seat": item_data.seat_number,
            "course": item_data.course.value if item_data.course else None,
            "modifiers": item_data.modifiers,
            "status": "pending" if body.send_to_kitchen else "draft"
        })

    # Calculate tax (assuming 10% for now - should come from venue settings)
    tax_rate = 0.10
    tax = subtotal * tax_rate
    total = subtotal + tax

    order.subtotal = subtotal
    order.tax = tax
    order.total = total

    db.commit()
    db.refresh(order)

    # Deduct stock for ordered items
    try:
        stock_service = StockDeductionService(db)
        stock_result = stock_service.deduct_for_order(
            order_items=order_items,
            location_id=getattr(order, 'location_id', None) or 1,
            reference_type="waiter_order",
            reference_id=order.id,
        )
        logger.info(f"Stock deduction for waiter order {order.id}: {stock_result['total_ingredients_deducted']} ingredients")
    except Exception as e:
        logger.warning(f"Stock deduction failed for waiter order {order.id}: {e}")

    return WaiterOrderResponse(
        order_id=order.id,
        order_number=order.order_number,
        table_id=table.id,
        table_name=f"Table {table.number}",
        items=order_items,
        subtotal=subtotal,
        tax=tax,
        total=total,
        status=order.status,
        created_at=order.created_at,
        waiter_name=current_user.full_name
    )


@router.post("/orders/{order_id}/items", response_model=QuickActionResponse)
@limiter.limit("30/minute")
async def add_items_to_order(
    request: Request,
    order_id: int,
    body: AddItemsRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Add items to an existing order"""
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.venue_id == current_user.venue_id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status in ["paid", "voided"]:
        raise HTTPException(status_code=400, detail="Cannot add items to closed order")

    added_items = []
    for item_data in body.items:
        menu_item = db.query(MenuItem).filter(
            MenuItem.id == item_data.menu_item_id
        ).first()

        if not menu_item:
            continue

        price = item_data.price_override or float(menu_item.price)

        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=menu_item.id,
            quantity=item_data.quantity,
            unit_price=price,
            total_price=price * item_data.quantity,
            seat_number=item_data.seat_number,
            course=item_data.course.value if item_data.course else None,
            modifiers_text=",".join(item_data.modifiers) if item_data.modifiers else None,
            special_instructions=item_data.special_instructions,
            status="pending" if body.send_to_kitchen else "draft"
        )
        db.add(order_item)
        added_items.append(menu_item.name)

    # Recalculate order totals
    db.flush()
    items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
    subtotal = sum(float(item.total_price) for item in items)
    tax = subtotal * 0.10
    order.subtotal = subtotal
    order.tax = tax
    order.total = subtotal + tax

    db.commit()

    # Deduct stock for newly added items
    try:
        new_items_data = []
        for item_data in body.items:
            menu_item = db.query(MenuItem).filter(MenuItem.id == item_data.menu_item_id).first()
            if menu_item:
                new_items_data.append({
                    "menu_item_id": item_data.menu_item_id,
                    "quantity": item_data.quantity,
                    "name": menu_item.name,
                })
        stock_service = StockDeductionService(db)
        stock_result = stock_service.deduct_for_order(
            order_items=new_items_data,
            location_id=getattr(order, 'location_id', None) or 1,
            reference_type="waiter_order",
            reference_id=order.id,
        )
        logger.info(f"Stock deduction for added items on order {order.id}: {stock_result['total_ingredients_deducted']} ingredients")
    except Exception as e:
        logger.warning(f"Stock deduction failed for added items on order {order.id}: {e}")

    return QuickActionResponse(
        success=True,
        message=f"Added {len(added_items)} items: {', '.join(added_items)}",
        data={"new_total": order.total}
    )


@router.post("/orders/{order_id}/fire-course", response_model=QuickActionResponse)
@limiter.limit("30/minute")
async def fire_course(
    request: Request,
    order_id: int,
    body: FireCourseRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Fire a specific course to kitchen/bar"""
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.venue_id == current_user.venue_id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Update items in this course
    items = db.query(OrderItem).filter(
        OrderItem.order_id == order_id,
        OrderItem.course == body.course.value
    ).all()

    if not items:
        raise HTTPException(status_code=400, detail=f"No items in {body.course.value} course")

    for item in items:
        item.fired = True
        item.fired_at = datetime.now(timezone.utc)
        item.status = "sent"

    db.commit()

    return QuickActionResponse(
        success=True,
        message=f"Fired {len(items)} items in {body.course.value} course",
        data={"items_fired": len(items)}
    )


@router.post("/orders/{order_id}/hold-course", response_model=QuickActionResponse)
@limiter.limit("30/minute")
async def hold_course(
    request: Request,
    order_id: int,
    body: HoldCourseRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Hold a course from firing"""
    items = db.query(OrderItem).filter(
        OrderItem.order_id == order_id,
        OrderItem.course == body.course.value,
        OrderItem.fired == False
    ).all()

    for item in items:
        item.status = "held"
        item.hold_reason = body.reason

    db.commit()

    return QuickActionResponse(
        success=True,
        message=f"Held {len(items)} items in {body.course.value} course"
    )


@router.post("/orders/{order_id}/fire-all", response_model=QuickActionResponse)
@limiter.limit("30/minute")
async def fire_all_items(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Fire all unfired items to kitchen/bar"""
    items = db.query(OrderItem).filter(
        OrderItem.order_id == order_id,
        OrderItem.fired == False
    ).all()

    for item in items:
        item.fired = True
        item.fired_at = datetime.now(timezone.utc)
        item.status = "sent"

    order = db.query(Order).filter(Order.id == order_id).first()
    if order:
        order.status = "sent"

    db.commit()

    return QuickActionResponse(
        success=True,
        message=f"Fired {len(items)} items to kitchen"
    )


@router.get("/orders/{order_id}/by-seat")
@limiter.limit("60/minute")
async def get_order_by_seat(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get order items grouped by seat number"""
    items = db.query(OrderItem).filter(
        OrderItem.order_id == order_id
    ).all()

    by_seat = {}
    for item in items:
        seat = item.seat_number or 0
        if seat not in by_seat:
            by_seat[seat] = {"items": [], "subtotal": 0}

        menu_item = db.query(MenuItem).filter(MenuItem.id == item.menu_item_id).first()
        by_seat[seat]["items"].append({
            "id": item.id,
            "name": menu_item.name if menu_item else "Unknown",
            "quantity": item.quantity,
            "price": float(item.unit_price),
            "total": float(item.total_price)
        })
        by_seat[seat]["subtotal"] += float(item.total_price)

    return {"seats": by_seat}


# ============================================================================
# BAR TAB MANAGEMENT
# ============================================================================

@router.post("/tabs", response_model=TabResponse)
@limiter.limit("30/minute")
async def open_tab(
    request: Request,
    body: OpenTabRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Open a new bar tab with optional card pre-authorization.
    Bartenders can open tabs for customers at the bar.
    """
    # Create a bar-specific session (no table)
    session = TableSession(
        table_id=None,  # Bar tab - no table
        venue_id=current_user.venue_id,
        guest_count=1,
        waiter_id=current_user.id,
        status="active",
        started_at=datetime.now(timezone.utc),
        customer_name=body.customer_name,
        card_last_four=body.card_last_four,
        pre_auth_amount=body.pre_auth_amount,
        is_bar_tab=True,
        notes=body.notes
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return TabResponse(
        tab_id=session.id,
        customer_name=body.customer_name,
        card_last_four=body.card_last_four,
        pre_auth_amount=body.pre_auth_amount,
        current_total=0.0,
        items=[],
        status="open",
        opened_at=session.started_at,
        opened_by=current_user.full_name
    )


@router.get("/tabs", response_model=List[TabResponse])
@limiter.limit("60/minute")
async def list_open_tabs(
    request: Request,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List all open bar tabs"""
    query = db.query(TableSession).filter(
        TableSession.venue_id == current_user.venue_id,
        TableSession.status == "active"
    )

    if search:
        query = query.filter(
            TableSession.guest_name.ilike(f"%{search}%")
        )

    tabs = query.order_by(TableSession.started_at.desc()).all()

    result = []
    for tab in tabs:
        # Get orders for this tab
        orders = db.query(Order).filter(Order.session_id == tab.id).all()
        items = []
        total = 0.0

        for order in orders:
            order_items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
            for item in order_items:
                menu_item = db.query(MenuItem).filter(MenuItem.id == item.menu_item_id).first()
                items.append({
                    "name": menu_item.name if menu_item else "Unknown",
                    "quantity": item.quantity,
                    "price": float(item.total_price)
                })
                total += float(item.total_price)

        waiter = db.query(StaffUser).filter(StaffUser.id == tab.waiter_id).first()

        result.append(TabResponse(
            tab_id=tab.id,
            customer_name=tab.guest_name or "Unknown",
            card_last_four=None,
            pre_auth_amount=0.0,
            current_total=total,
            items=items,
            status="open",
            opened_at=tab.started_at,
            opened_by=waiter.full_name if waiter else "Unknown"
        ))

    return result


@router.post("/tabs/{tab_id}/items", response_model=QuickActionResponse)
@limiter.limit("30/minute")
async def add_to_tab(
    request: Request,
    tab_id: int,
    body: AddToTabRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Add items to an open bar tab"""
    tab = db.query(TableSession).filter(
        TableSession.id == tab_id,
        TableSession.venue_id == current_user.venue_id,
        TableSession.status == "active"
    ).first()

    if not tab:
        raise HTTPException(status_code=404, detail="Tab not found or closed")

    # Get or create order for this tab
    order = db.query(Order).filter(
        Order.session_id == tab_id,
        Order.status.in_(["new", "sent", "preparing"])
    ).first()

    if not order:
        order = Order(
            order_number=f"T{datetime.now(timezone.utc).strftime('%H%M%S')}{tab_id:02d}",
            session_id=tab_id,
            venue_id=current_user.venue_id,
            waiter_id=current_user.id,
            status="new"
        )
        db.add(order)
        db.flush()

    # Add items
    tab_items_data = []
    for item_data in body.items:
        menu_item = db.query(MenuItem).filter(MenuItem.id == item_data.menu_item_id).first()
        if menu_item:
            price = float(menu_item.price)
            order_item = OrderItem(
                order_id=order.id,
                menu_item_id=menu_item.id,
                quantity=item_data.quantity,
                unit_price=price,
                total_price=price * item_data.quantity,
                status="sent"
            )
            db.add(order_item)
            tab_items_data.append({
                "menu_item_id": menu_item.id,
                "quantity": item_data.quantity,
                "name": menu_item.name,
            })

    db.commit()

    # Deduct stock for bar tab items
    try:
        stock_service = StockDeductionService(db)
        stock_result = stock_service.deduct_for_order(
            order_items=tab_items_data,
            location_id=1,
            reference_type="bar_tab",
            reference_id=order.id,
        )
        logger.info(f"Stock deduction for bar tab {tab_id}: {stock_result['total_ingredients_deducted']} ingredients")
    except Exception as e:
        logger.warning(f"Stock deduction failed for bar tab {tab_id}: {e}")

    return QuickActionResponse(
        success=True,
        message=f"Added {len(body.items)} items to tab"
    )


@router.post("/tabs/{tab_id}/transfer", response_model=QuickActionResponse)
@limiter.limit("30/minute")
async def transfer_tab(
    request: Request,
    tab_id: int,
    body: TransferTabRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Transfer bar tab to a table"""
    tab = db.query(TableSession).filter(
        TableSession.id == tab_id,
        TableSession.venue_id == current_user.venue_id,
        TableSession.status == "active"
    ).first()

    if not tab:
        raise HTTPException(status_code=404, detail="Tab not found")

    table = db.query(Table).filter(
        Table.id == body.table_id,
        or_(Table.location_id == current_user.venue_id, Table.location_id.is_(None))
    ).first()

    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    # Update tab to link to table
    tab.table_id = body.table_id
    tab.is_bar_tab = False

    # Update all orders to reference the table
    orders = db.query(Order).filter(Order.session_id == tab_id).all()
    for order in orders:
        order.table_id = body.table_id

    db.commit()

    return QuickActionResponse(
        success=True,
        message=f"Tab transferred to {f'Table {table.number}'}"
    )


@router.post("/tabs/{tab_id}/close", response_model=QuickActionResponse)
@limiter.limit("30/minute")
async def close_tab(
    request: Request,
    tab_id: int,
    body: CloseTabRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Close and charge a bar tab"""
    tab = db.query(TableSession).filter(
        TableSession.id == tab_id,
        TableSession.venue_id == current_user.venue_id,
        TableSession.status == "active"
    ).first()

    if not tab:
        raise HTTPException(status_code=404, detail="Tab not found")

    # Calculate total
    orders = db.query(Order).filter(Order.session_id == tab_id).all()
    subtotal = sum(float(o.total or 0) for o in orders)
    total = subtotal + body.tip_amount

    # Create payment record
    payment = Payment(
        venue_id=current_user.venue_id,
        session_id=tab_id,
        amount=total,
        tip=body.tip_amount,
        payment_method=body.payment_method.value,
        status="completed",
        processed_by=current_user.id,
        processed_at=datetime.now(timezone.utc)
    )
    db.add(payment)

    # Close tab
    tab.status = "closed"
    tab.ended_at = datetime.now(timezone.utc)

    # Mark orders as paid
    for order in orders:
        order.status = "paid"

    db.commit()

    return QuickActionResponse(
        success=True,
        message=f"Tab closed. Total charged: ${total:.2f}",
        data={"total": total, "tip": body.tip_amount}
    )


# ============================================================================
# BILL SPLITTING
# ============================================================================

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

    items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()

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
    payments = db.query(Payment).filter(Payment.order_id == order_id).all()
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

    items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()

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
    ).all()

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
    remaining_items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
    order.subtotal = sum(float(i.total_price) for i in remaining_items)
    order.tax = order.subtotal * 0.10
    order.total = order.subtotal + order.tax

    # Calculate target order
    target_items = db.query(OrderItem).filter(OrderItem.order_id == target_order.id).all()
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
    ).all()

    if len(orders) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 checks to merge")

    # Keep first order as target
    target = orders[0]

    # Move all items from other orders to target
    for order in orders[1:]:
        items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        for item in items:
            item.order_id = target.id
        order.status = "merged"

    # Recalculate target
    all_items = db.query(OrderItem).filter(OrderItem.order_id == target.id).all()
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
    existing_payments = db.query(Payment).filter(Payment.order_id == order.id).all()
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
    all_payments = db.query(Payment).filter(Payment.order_id == order.id).all()
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
            ).all()
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
        ).all()
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
        ).all()
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
        ).all()
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
        ).all()
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

@router.get("/floor-plan", response_model=List[TableStatusResponse])
@limiter.limit("60/minute")
async def get_floor_plan(
    request: Request,
    section: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get floor plan with table statuses"""
    query = db.query(Table).filter(or_(Table.location_id == current_user.venue_id, Table.location_id.is_(None)))

    if section:
        query = query.filter(Table.section == section)

    tables = query.all()

    result = []
    for table in tables:
        # Get active session
        session = db.query(TableSession).filter(
            TableSession.table_id == table.id,
            TableSession.status == "active"
        ).first()

        # Get current order if any
        current_order = None
        if session:
            current_order = db.query(Order).filter(
                Order.session_id == session.id,
                Order.status.notin_(["paid", "voided"])
            ).first()

        waiter = None
        if session and session.waiter_id:
            waiter = db.query(StaffUser).filter(StaffUser.id == session.waiter_id).first()

        time_seated = None
        if session and session.started_at:
            time_seated = int((datetime.now(timezone.utc) - session.started_at.replace(tzinfo=timezone.utc)).total_seconds() / 60)

        result.append(TableStatusResponse(
            table_id=table.id,
            table_name=f"Table {table.number}",
            capacity=table.capacity or 4,
            status="occupied" if session else ("reserved" if getattr(table, 'reserved', False) else "available"),
            current_check_id=current_order.id if current_order else None,
            guest_count=session.guest_count if session else None,
            server_name=waiter.full_name if waiter else None,
            seated_at=session.started_at if session else None,
            time_seated_minutes=time_seated,
            current_total=float(current_order.total or 0) if current_order else None
        ))

    return result


@router.post("/tables/{table_id}/seat", response_model=QuickActionResponse)
@limiter.limit("30/minute")
async def seat_table(
    request: Request,
    table_id: int,
    guest_count: int = Query(default=2, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Seat guests at a table"""
    table = db.query(Table).filter(
        Table.id == table_id,
        or_(Table.location_id == current_user.venue_id, Table.location_id.is_(None))
    ).first()

    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    # Check if table is already occupied
    existing = db.query(TableSession).filter(
        TableSession.table_id == table_id,
        TableSession.status == "active"
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Table is already occupied")

    # Create session
    session = TableSession(
        table_id=table_id,
        venue_id=current_user.venue_id,
        guest_count=guest_count,
        waiter_id=current_user.id,
        status="active",
        started_at=datetime.now(timezone.utc)
    )
    db.add(session)
    db.commit()

    return QuickActionResponse(
        success=True,
        message=f"Seated {guest_count} guests at {f'Table {table.number}'}",
        data={"session_id": session.id}
    )


@router.post("/tables/{table_id}/transfer", response_model=QuickActionResponse)
@limiter.limit("30/minute")
async def transfer_table(
    request: Request,
    table_id: int,
    body: TransferTableRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Transfer table to another server"""
    session = db.query(TableSession).filter(
        TableSession.table_id == table_id,
        TableSession.status == "active"
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="No active session for this table")

    new_waiter = db.query(StaffUser).filter(
        StaffUser.id == body.to_waiter_id,
        or_(StaffUser.location_id == current_user.venue_id, StaffUser.location_id.is_(None))
    ).first()

    if not new_waiter:
        raise HTTPException(status_code=404, detail="Waiter not found")

    session.waiter_id = body.to_waiter_id
    db.commit()

    return QuickActionResponse(
        success=True,
        message=f"Table transferred to {new_waiter.full_name}"
    )


@router.post("/tables/{table_id}/clear", response_model=QuickActionResponse)
@limiter.limit("30/minute")
async def clear_table(
    request: Request,
    table_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Clear table after guests leave (close session)"""
    session = db.query(TableSession).filter(
        TableSession.table_id == table_id,
        TableSession.status == "active"
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="No active session")

    # Check for unpaid orders
    unpaid = db.query(Order).filter(
        Order.session_id == session.id,
        Order.status.notin_(["paid", "voided"])
    ).first()

    if unpaid:
        raise HTTPException(status_code=400, detail="Cannot clear table with unpaid orders")

    session.status = "closed"
    session.ended_at = datetime.now(timezone.utc)
    db.commit()

    return QuickActionResponse(
        success=True,
        message="Table cleared and ready for next guests"
    )


@router.get("/my-tables", response_model=List[TableStatusResponse])
@limiter.limit("60/minute")
async def get_my_tables(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get tables assigned to current waiter"""
    sessions = db.query(TableSession).filter(
        TableSession.waiter_id == current_user.id,
        TableSession.venue_id == current_user.venue_id,
        TableSession.status == "active"
    ).all()

    result = []
    for session in sessions:
        table = db.query(Table).filter(Table.id == session.table_id).first()
        if not table:
            continue

        order = db.query(Order).filter(
            Order.session_id == session.id,
            Order.status.notin_(["paid", "voided"])
        ).first()

        time_seated = int((datetime.now(timezone.utc) - session.started_at.replace(tzinfo=timezone.utc)).total_seconds() / 60)

        result.append(TableStatusResponse(
            table_id=table.id,
            table_name=f"Table {table.number}",
            capacity=table.capacity or 4,
            status="occupied",
            current_check_id=order.id if order else None,
            guest_count=session.guest_count,
            server_name=current_user.full_name,
            seated_at=session.started_at,
            time_seated_minutes=time_seated,
            current_total=float(order.total or 0) if order else None
        ))

    return result


# ============================================================================
# QUICK ACTIONS
# ============================================================================

@router.post("/quick-reorder/{item_id}", response_model=QuickActionResponse)
@limiter.limit("30/minute")
async def quick_reorder(
    request: Request,
    item_id: int,
    quantity: int = 1,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Quick reorder - add same item again"""
    original = db.query(OrderItem).filter(OrderItem.id == item_id).first()

    if not original:
        raise HTTPException(status_code=404, detail="Item not found")

    new_item = OrderItem(
        order_id=original.order_id,
        menu_item_id=original.menu_item_id,
        quantity=quantity,
        unit_price=original.unit_price,
        total_price=float(original.unit_price) * quantity,
        seat_number=original.seat_number,
        modifiers=original.modifiers,
        status="sent"
    )
    db.add(new_item)

    # Update order total
    order = db.query(Order).filter(Order.id == original.order_id).first()
    if order:
        order.subtotal = float(order.subtotal or 0) + new_item.total_price
        order.tax = order.subtotal * 0.10
        order.total = order.subtotal + order.tax

    db.commit()

    menu_item = db.query(MenuItem).filter(MenuItem.id == original.menu_item_id).first()

    return QuickActionResponse(
        success=True,
        message=f"Reordered {quantity}x {menu_item.name if menu_item else 'item'}"
    )


@router.get("/menu/quick", response_model=List[Dict[str, Any]])
@limiter.limit("60/minute")
async def get_quick_menu(
    request: Request,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get quick menu for waiter terminal"""
    query = db.query(MenuItem).filter(
        MenuItem.available == True
    )

    if category:
        # Filter by category name
        from app.models import MenuCategory
        cat = db.query(MenuCategory).filter(MenuCategory.name == category).first()
        if cat:
            query = query.filter(MenuItem.category_id == cat.id)

    items = query.order_by(MenuItem.category_id, MenuItem.id).limit(500).all()

    result = []
    for item in items:
        # Get category name - handle JSON or string
        cat_name = ""
        if item.category:
            if hasattr(item.category, 'name'):
                cat_name = item.category.name if isinstance(item.category.name, str) else item.category.name.get('en', '')

        # Get item name - handle JSON or string
        item_name = item.name if isinstance(item.name, str) else item.name.get('en', str(item.name))

        # Get station name
        station_name = "kitchen"
        if item.station:
            station_name = item.station.name if hasattr(item.station, 'name') else "kitchen"

        # Get primary image URL
        image_url = item.image_url if hasattr(item, 'image_url') else None

        result.append({
            "id": item.id,
            "name": item_name,
            "price": float(item.price),
            "category": cat_name,
            "station": station_name,
            "image": image_url
        })

    return result


@router.post("/checks/{check_id}/print", response_model=QuickActionResponse)
@limiter.limit("30/minute")
async def print_check(
    request: Request,
    check_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Print check for customer"""
    order = db.query(Order).filter(
        Order.id == check_id,
        Order.venue_id == current_user.venue_id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Check not found")

    # Mark as printed
    order.check_printed = True
    order.check_printed_at = datetime.now(timezone.utc)
    db.commit()

    # In real implementation, would send to receipt printer
    return QuickActionResponse(
        success=True,
        message="Check sent to printer",
        data={"check_number": order.order_number, "total": float(order.total or 0)}
    )

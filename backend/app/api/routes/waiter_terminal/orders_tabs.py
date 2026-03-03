"""Orders, tabs & checks"""
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
    items = db.query(OrderItem).filter(OrderItem.order_id == order.id).limit(500).all()
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
    ).limit(500).all()

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
    ).limit(500).all()

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
    ).limit(500).all()

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
    ).limit(500).all()

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


@router.get("/tabs")
@limiter.limit("60/minute")
async def list_open_tabs(
    request: Request,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
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

    query = query.order_by(TableSession.started_at.desc())
    tabs, total = paginate_query(query, skip, limit)

    result = []
    for tab in tabs:
        # Get orders for this tab
        orders = db.query(Order).filter(Order.session_id == tab.id).limit(500).all()
        items = []
        tab_total = 0.0

        for order in orders:
            order_items = db.query(OrderItem).filter(OrderItem.order_id == order.id).limit(500).all()
            for item in order_items:
                menu_item = db.query(MenuItem).filter(MenuItem.id == item.menu_item_id).first()
                items.append({
                    "name": menu_item.name if menu_item else "Unknown",
                    "quantity": item.quantity,
                    "price": float(item.total_price)
                })
                tab_total += float(item.total_price)

        waiter = db.query(StaffUser).filter(StaffUser.id == tab.waiter_id).first()

        result.append(TabResponse(
            tab_id=tab.id,
            customer_name=tab.guest_name or "Unknown",
            card_last_four=None,
            pre_auth_amount=0.0,
            current_total=tab_total,
            items=items,
            status="open",
            opened_at=tab.started_at,
            opened_by=waiter.full_name if waiter else "Unknown"
        ))

    return PaginatedResponse.create(items=result, total=total, skip=skip, limit=limit)


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
        Order.status.in_([OrderStatus.NEW, OrderStatus.ACCEPTED, OrderStatus.PREPARING])
    ).first()

    if not order:
        order = Order(
            order_number=f"T{datetime.now(timezone.utc).strftime('%H%M%S')}{tab_id:02d}",
            session_id=tab_id,
            venue_id=current_user.venue_id,
            waiter_id=current_user.id,
            status=OrderStatus.NEW
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
    orders = db.query(Order).filter(Order.session_id == tab_id).limit(500).all()
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
    orders = db.query(Order).filter(Order.session_id == tab_id).limit(500).all()
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


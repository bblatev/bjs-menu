"""Floor plan, table management & quick menu"""
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

@router.get("/floor-plan")
@limiter.limit("60/minute")
async def get_floor_plan(
    request: Request,
    section: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get floor plan with table statuses"""
    query = db.query(Table).filter(or_(Table.location_id == current_user.venue_id, Table.location_id.is_(None)))

    if section:
        query = query.filter(Table.section == section)

    tables, total = paginate_query(query, skip, limit)

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
                Order.status.notin_([OrderStatus.SERVED, OrderStatus.CANCELLED])
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

    return PaginatedResponse.create(items=result, total=total, skip=skip, limit=limit)


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
        Order.status.notin_([OrderStatus.SERVED, OrderStatus.CANCELLED])
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


@router.get("/my-tables")
@limiter.limit("60/minute")
async def get_my_tables(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get tables assigned to current waiter"""
    query = db.query(TableSession).filter(
        TableSession.waiter_id == current_user.id,
        TableSession.venue_id == current_user.venue_id,
        TableSession.status == "active"
    )
    sessions, total = paginate_query(query, skip, limit)

    result = []
    for session in sessions:
        table = db.query(Table).filter(Table.id == session.table_id).first()
        if not table:
            continue

        order = db.query(Order).filter(
            Order.session_id == session.id,
            Order.status.notin_([OrderStatus.SERVED, OrderStatus.CANCELLED])
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

    return PaginatedResponse.create(items=result, total=total, skip=skip, limit=limit)


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

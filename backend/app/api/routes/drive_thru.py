"""
Drive-Thru Order Module API Endpoints
Complete drive-thru ordering with lane management and queue tracking
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.core.rbac import get_current_user
from app.models import (
    StaffUser, DriveThruOrder, Order, OrderItem, Table, MenuItem,
    ModifierOption, OrderStatus
)
from app.schemas import (
    DriveThruOrderCreate, DriveThruOrderResponse, DriveThruLane,
    DriveThruOrderStatus
)

router = APIRouter()


@router.get("/")
@limiter.limit("60/minute")
async def get_drive_thru_root(request: Request, db: Session = Depends(get_db), current_user: StaffUser = Depends(get_current_user)):
    """Drive-thru overview."""
    return await get_drive_thru_stats(request=request, db=db, current_user=current_user)


@router.post("/orders", response_model=DriveThruOrderResponse)
@limiter.limit("30/minute")
async def create_drive_thru_order(
    request: Request,
    data: DriveThruOrderCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Create a new drive-thru order"""
    # Get or create drive-thru table for the lane
    lane_table = db.query(Table).filter(
        Table.location_id == data.venue_id,
        Table.number == f"DT-{data.lane.value.upper()}"
    ).first()


    if not lane_table:
        lane_table = Table(
            location_id=data.venue_id,
            number=f"DT-{data.lane.value.upper()}",
            capacity=0,
            status="available",
            area=f"Drive-thru {data.lane.value}"
        )
        db.add(lane_table)
        db.flush()

    # Generate order number
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    count = db.query(Order).filter(
        Order.order_number.like(f"DT{today}%")
    ).count()
    order_number = f"DT{today}{count + 1:04d}"

    # Create base order
    order = Order(
        table_id=lane_table.id,
        order_number=order_number,
        status=OrderStatus.NEW,
        order_type="drive_thru",
        customer_name=data.customer_name,
        notes=data.notes,
        payment_status="pending"
    )
    db.add(order)
    db.flush()

    # Add items
    total = 0
    station_id = None

    for item_data in data.items:
        menu_item = db.query(MenuItem).filter(MenuItem.id == item_data.menu_item_id).first()
        if not menu_item:
            continue

        station_id = station_id or menu_item.station_id

        # Calculate price with modifiers
        item_price = menu_item.price
        for mod in item_data.modifiers:
            modifier = db.query(ModifierOption).filter(
                ModifierOption.id == mod.modifier_option_id
            ).first()
            if modifier:
                item_price += modifier.price_delta

        subtotal = item_price * item_data.quantity

        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=menu_item.id,
            quantity=item_data.quantity,
            unit_price=item_price,
            subtotal=subtotal,
            notes=item_data.notes
        )
        db.add(order_item)
        total += subtotal

    order.total = round(total, 2)
    order.station_id = station_id

    # Calculate queue position
    queue_position = db.query(DriveThruOrder).filter(
        DriveThruOrder.venue_id == data.venue_id,
        DriveThruOrder.lane == data.lane.value,
        DriveThruOrder.status.in_(["queued", "at_speaker", "confirmed", "preparing"])
    ).count() + 1

    # Estimate wait time (3-5 min per order ahead)
    estimated_wait = queue_position * 4

    # Create drive-thru entry
    drive_thru = DriveThruOrder(
        order_id=order.id,
        venue_id=data.venue_id,
        lane=data.lane.value,
        queue_position=queue_position,
        status="queued",
        vehicle_description=data.vehicle_description,
        customer_name=data.customer_name,
        estimated_wait_minutes=estimated_wait
    )
    db.add(drive_thru)

    db.commit()
    db.refresh(drive_thru)
    db.refresh(order)

    return _format_drive_thru_response(drive_thru, order, db)


@router.get("/orders", response_model=List[DriveThruOrderResponse])
@limiter.limit("60/minute")
async def list_drive_thru_orders(
    request: Request,
    lane: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List active drive-thru orders"""
    query = db.query(DriveThruOrder).filter(
        DriveThruOrder.venue_id == current_user.venue_id
    )

    if lane:
        query = query.filter(DriveThruOrder.lane == lane)

    if status:
        query = query.filter(DriveThruOrder.status == status)
    else:
        # Default to active orders only
        query = query.filter(
            DriveThruOrder.status.in_([
                "queued", "at_speaker", "confirmed",
                "preparing", "ready", "at_window"
            ])
        )

    drive_thrus = query.order_by(
        DriveThruOrder.queue_position
    ).all()

    results = []
    for dt in drive_thrus:
        order = db.query(Order).filter(Order.id == dt.order_id).first()
        if order:
            results.append(_format_drive_thru_response(dt, order, db))

    return results


@router.get("/orders/{order_id}", response_model=DriveThruOrderResponse)
@limiter.limit("60/minute")
async def get_drive_thru_order(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get drive-thru order details"""
    drive_thru = db.query(DriveThruOrder).filter(
        DriveThruOrder.id == order_id,
        DriveThruOrder.venue_id == current_user.venue_id
    ).first()

    if not drive_thru:
        raise HTTPException(status_code=404, detail="Order not found")

    order = db.query(Order).filter(Order.id == drive_thru.order_id).first()
    return _format_drive_thru_response(drive_thru, order, db)


@router.put("/orders/{order_id}/status")
@limiter.limit("30/minute")
async def update_drive_thru_status(
    request: Request,
    order_id: int,
    status: str,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Update drive-thru order status"""
    valid_statuses = [
        "queued", "at_speaker", "confirmed",
        "preparing", "ready", "at_window", "completed", "cancelled"
    ]

    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    drive_thru = db.query(DriveThruOrder).filter(
        DriveThruOrder.id == order_id,
        DriveThruOrder.venue_id == current_user.venue_id
    ).first()

    if not drive_thru:
        raise HTTPException(status_code=404, detail="Order not found")

    old_status = drive_thru.status
    drive_thru.status = status

    # Update order status in main order table
    order = db.query(Order).filter(Order.id == drive_thru.order_id).first()
    if order:
        status_mapping = {
            "queued": OrderStatus.NEW,
            "at_speaker": OrderStatus.NEW,
            "confirmed": OrderStatus.ACCEPTED,
            "preparing": OrderStatus.PREPARING,
            "ready": OrderStatus.READY,
            "at_window": OrderStatus.READY,
            "completed": OrderStatus.SERVED,
            "cancelled": OrderStatus.CANCELLED
        }
        if status in status_mapping:
            order.status = status_mapping[status]

    if status == "completed":
        drive_thru.completed_at = datetime.now(timezone.utc)
        # Recalculate queue positions for remaining orders
        _recalculate_queue(db, drive_thru.venue_id, drive_thru.lane)

    db.commit()

    return {
        "message": f"Status updated from {old_status} to {status}",
        "new_status": status
    }


@router.put("/orders/{order_id}/lane")
@limiter.limit("30/minute")
async def change_drive_thru_lane(
    request: Request,
    order_id: int,
    new_lane: str,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Move order to different lane"""
    drive_thru = db.query(DriveThruOrder).filter(
        DriveThruOrder.id == order_id,
        DriveThruOrder.venue_id == current_user.venue_id
    ).first()

    if not drive_thru:
        raise HTTPException(status_code=404, detail="Order not found")

    old_lane = drive_thru.lane
    drive_thru.lane = new_lane

    # Get new queue position
    new_position = db.query(DriveThruOrder).filter(
        DriveThruOrder.venue_id == drive_thru.venue_id,
        DriveThruOrder.lane == new_lane,
        DriveThruOrder.status.in_(["queued", "at_speaker", "confirmed", "preparing"])
    ).count()
    drive_thru.queue_position = new_position

    # Recalculate old lane queue
    _recalculate_queue(db, drive_thru.venue_id, old_lane)

    db.commit()

    return {"message": f"Moved from {old_lane} to {new_lane}"}


@router.get("/queue/{venue_id}")
@limiter.limit("60/minute")
async def get_drive_thru_queue(
    request: Request,
    venue_id: int,
    db: Session = Depends(get_db)
):
    """Get queue display for drive-thru screens (public endpoint)"""
    lanes = ["lane_1", "lane_2", "lane_3"]
    result = {}

    for lane in lanes:
        orders = db.query(DriveThruOrder).filter(
            DriveThruOrder.venue_id == venue_id,
            DriveThruOrder.lane == lane,
            DriveThruOrder.status.in_(["queued", "confirmed", "preparing", "ready"])
        ).order_by(DriveThruOrder.queue_position).limit(10).all()

        result[lane] = {
            "preparing": [],
            "ready": []
        }

        for dt in orders:
            order = db.query(Order).filter(Order.id == dt.order_id).first()
            if not order:
                continue

            order_info = {
                "order_number": order.order_number,
                "vehicle": dt.vehicle_description,
                "customer": dt.customer_name
            }

            if dt.status in ["queued", "confirmed", "preparing"]:
                result[lane]["preparing"].append(order_info)
            elif dt.status == "ready":
                result[lane]["ready"].append(order_info)

    return result


@router.get("/stats")
@limiter.limit("60/minute")
async def get_drive_thru_stats(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get drive-thru statistics"""
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    # Today's orders
    today_orders = db.query(DriveThruOrder).filter(
        DriveThruOrder.venue_id == current_user.venue_id,
        DriveThruOrder.created_at >= today_start
    ).all()

    completed = [o for o in today_orders if o.status == "completed"]

    # Average wait time
    avg_wait = 0
    if completed:
        wait_times = []
        for o in completed:
            if o.completed_at:
                wait = (o.completed_at - o.created_at).total_seconds() / 60
                wait_times.append(wait)
        if wait_times:
            avg_wait = sum(wait_times) / len(wait_times)

    # Current queue
    current_queue = {
        "lane_1": 0,
        "lane_2": 0,
        "lane_3": 0
    }

    for lane in current_queue.keys():
        current_queue[lane] = db.query(DriveThruOrder).filter(
            DriveThruOrder.venue_id == current_user.venue_id,
            DriveThruOrder.lane == lane,
            DriveThruOrder.status.in_(["queued", "confirmed", "preparing"])
        ).count()

    return {
        "today_total": len(today_orders),
        "today_completed": len(completed),
        "today_cancelled": len([o for o in today_orders if o.status == "cancelled"]),
        "average_wait_minutes": round(avg_wait, 1),
        "current_queue": current_queue,
        "total_in_queue": sum(current_queue.values())
    }


def _recalculate_queue(db: Session, venue_id: int, lane: str):
    """Recalculate queue positions after status changes"""
    orders = db.query(DriveThruOrder).filter(
        DriveThruOrder.venue_id == venue_id,
        DriveThruOrder.lane == lane,
        DriveThruOrder.status.in_(["queued", "at_speaker", "confirmed", "preparing"])
    ).order_by(DriveThruOrder.created_at).all()

    for i, order in enumerate(orders, 1):
        order.queue_position = i
        order.estimated_wait_minutes = i * 4


def _format_drive_thru_response(
    drive_thru: DriveThruOrder,
    order: Order,
    db: Session
) -> DriveThruOrderResponse:
    """Format drive-thru order for response"""
    # Get order items
    items = []
    if order:
        for item in order.items:
            items.append({
                "id": item.id,
                "menu_item_id": item.menu_item_id,
                "item_name": {"bg": item.menu_item.name_translations.get("bg", "") if item.menu_item else ""},
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "subtotal": item.subtotal,
                "notes": item.notes,
                "modifiers": []
            })

    return DriveThruOrderResponse(
        id=drive_thru.id,
        order_number=order.order_number if order else "",
        lane=DriveThruLane(drive_thru.lane),
        status=DriveThruOrderStatus(drive_thru.status),
        queue_position=drive_thru.queue_position or 0,
        estimated_wait_minutes=drive_thru.estimated_wait_minutes or 0,
        items=items,
        total=order.total if order else 0,
        customer_name=drive_thru.customer_name,
        vehicle_description=drive_thru.vehicle_description,
        created_at=drive_thru.created_at
    )

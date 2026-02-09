"""Kitchen Display System (KDS) routes - using database models."""

from datetime import timedelta
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import func

from app.db.session import DbSession
from app.models.restaurant import KitchenOrder, GuestOrder, MenuItem, Table, Check

router = APIRouter()


def _utc_aware(dt):
    """Make a datetime UTC-aware if it's naive (SQLite returns naive datetimes)."""
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def _sync_guest_order_status(db: DbSession, kitchen_order: KitchenOrder, new_status: str):
    """
    Sync the guest order status when kitchen order status changes.
    Maps kitchen statuses to guest order statuses.
    """
    # Status mapping: kitchen -> guest order
    status_map = {
        "pending": "received",
        "cooking": "preparing",
        "ready": "ready",
        "completed": "served",
        "cancelled": "cancelled",
    }

    guest_status = status_map.get(new_status)
    if not guest_status:
        return

    # Find the corresponding guest order by table_number and similar creation time
    # Guest orders are created just before kitchen orders, so find orders with matching table
    if kitchen_order.table_number:
        guest_order = db.query(GuestOrder).filter(
            GuestOrder.table_number == kitchen_order.table_number,
            GuestOrder.status.notin_(["completed", "cancelled", "paid"]),
        ).order_by(GuestOrder.created_at.desc()).first()

        if guest_order:
            guest_order.status = guest_status
            if new_status == "ready":
                guest_order.ready_at = datetime.now(timezone.utc)


def _compute_avg_cook_time(db: DbSession, location_id: Optional[int] = None) -> float:
    """Compute average cook time in minutes from completed kitchen orders."""
    query = db.query(KitchenOrder).filter(
        KitchenOrder.status == "completed",
        KitchenOrder.started_at.isnot(None),
        KitchenOrder.completed_at.isnot(None),
    )
    if location_id:
        query = query.filter(KitchenOrder.location_id == location_id)
    completed = query.all()
    if not completed:
        return 0
    total_minutes = sum(
        (o.completed_at - o.started_at).total_seconds() / 60
        for o in completed
        if o.completed_at and o.started_at
    )
    return round(total_minutes / len(completed), 1)


class KitchenStats(BaseModel):
    """Kitchen statistics response."""
    active_alerts: int = 0
    orders_by_status: dict = {}
    items_86_count: int = 0
    rush_orders_today: int = 0
    vip_orders_today: int = 0
    avg_prep_time_minutes: Optional[float] = None
    orders_completed_today: int = 0


@router.get("/stats")
def get_kitchen_stats(
    db: DbSession,
    location_id: Optional[int] = None,
):
    """Get kitchen statistics for dashboard."""
    status_counts = {"new": 0, "in_progress": 0, "ready": 0, "completed": 0}

    # Get kitchen orders from database
    db_query = db.query(KitchenOrder)
    if location_id:
        db_query = db_query.filter(KitchenOrder.location_id == location_id)
    db_orders = db_query.all()

    db_status_map = {"pending": "new", "cooking": "in_progress", "ready": "ready", "completed": "completed"}
    for ko in db_orders:
        mapped_status = db_status_map.get(ko.status, "new")
        if mapped_status in status_counts:
            status_counts[mapped_status] += 1

    active_count = status_counts["new"] + status_counts["in_progress"]
    total_count = len(db_orders)

    # Count 86'd items (unavailable menu items)
    items_86_count = db.query(MenuItem).filter(MenuItem.available == False).count()

    return {
        "total_tickets": total_count,
        "active_tickets": active_count,
        "avg_cook_time_minutes": _compute_avg_cook_time(db, location_id),
        "bumped_today": status_counts["completed"],
        "active_alerts": 0,
        "orders_by_status": status_counts,
        "items_86_count": items_86_count,
        "rush_orders_today": db.query(KitchenOrder).filter(KitchenOrder.priority >= 1).count(),
        "vip_orders_today": db.query(KitchenOrder).filter(KitchenOrder.priority >= 2).count(),
        "avg_prep_time_minutes": _compute_avg_cook_time(db, location_id),
        "orders_completed_today": status_counts["completed"],
    }


@router.get("/orders/active")
def get_active_orders(
    db: DbSession,
    location_id: Optional[int] = None,
):
    """Get all active kitchen orders (not completed/voided)."""
    query = db.query(KitchenOrder).filter(
        KitchenOrder.status.in_(["pending", "cooking", "ready"])
    )
    if location_id:
        query = query.filter(KitchenOrder.location_id == location_id)

    orders = query.order_by(KitchenOrder.created_at.asc()).all()

    return {
        "orders": [
            {
                "id": o.id,
                "check_id": o.check_id,
                "table_number": o.table_number,
                "status": o.status,
                "priority": o.priority,
                "station": o.station,
                "course": o.course,
                "items": o.items or [],
                "notes": o.notes,
                "created_at": o.created_at.isoformat() if o.created_at else None,
                "started_at": o.started_at.isoformat() if o.started_at else None,
            }
            for o in orders
        ],
        "count": len(orders),
    }


@router.get("/queue")
def get_kitchen_queue(
    db: DbSession,
    location_id: Optional[int] = None,
):
    """Get current kitchen queue."""
    query = db.query(KitchenOrder).filter(KitchenOrder.status.in_(["pending", "cooking"]))
    if location_id:
        query = query.filter(KitchenOrder.location_id == location_id)

    orders = query.order_by(KitchenOrder.created_at.asc()).all()

    queue_orders = []
    for o in orders:
        wait_time = 0
        if o.created_at:
            wait_time = int((datetime.now(timezone.utc) - _utc_aware(o.created_at)).total_seconds() / 60)

        queue_orders.append({
            "id": o.id,
            "ticket_id": f"db-{o.id}",
            "table_number": o.table_number or "Unknown",
            "status": o.status,
            "priority": o.priority,
            "items": o.items or [],
            "item_count": len(o.items) if o.items else 0,
            "notes": o.notes,
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "wait_time_minutes": wait_time,
            "is_overdue": wait_time > 15,
        })

    return {
        "orders": queue_orders,
        "total_in_queue": len(orders),
        "avg_wait_time_minutes": round(sum(q["wait_time_minutes"] for q in queue_orders) / len(queue_orders), 1) if queue_orders else 0
    }


@router.get("/tickets")
def get_kitchen_tickets(
    db: DbSession,
    location_id: Optional[int] = None,
    status: Optional[str] = None,
    station: Optional[str] = None,
):
    """Get kitchen tickets from active orders."""
    tickets = []

    # Get tickets from database (KitchenOrder table)
    db_query = db.query(KitchenOrder).filter(KitchenOrder.status.notin_(["completed", "cancelled"]))
    if location_id:
        db_query = db_query.filter(KitchenOrder.location_id == location_id)
    if status:
        status_map = {"new": "pending", "in_progress": "cooking", "ready": "ready"}
        db_status = status_map.get(status, status)
        db_query = db_query.filter(KitchenOrder.status == db_status)

    db_orders = db_query.order_by(KitchenOrder.created_at.desc()).all()

    for ko in db_orders:
        wait_time = 0
        if ko.created_at:
            wait_time = int((datetime.now(timezone.utc) - _utc_aware(ko.created_at)).total_seconds() / 60)

        kds_items = []
        if ko.items:
            for item in ko.items:
                kds_items.append({
                    "id": item.get("menu_item_id"),
                    "name": item.get("name"),
                    "quantity": item.get("quantity", 1),
                    "modifiers": item.get("modifiers", []),
                    "notes": item.get("notes"),
                    "is_fired": False,
                    "is_voided": False,
                    "course": "main",
                    "seat": None,
                    "allergens": [],
                })

        status_map = {"pending": "new", "cooking": "in_progress", "ready": "ready", "completed": "completed"}
        ticket_status = status_map.get(ko.status, ko.status)

        ticket = {
            "ticket_id": f"db-{ko.id}",
            "order_id": ko.id,
            "station_id": ko.station or "KITCHEN-1",
            "table_number": ko.table_number or "Unknown",
            "table": ko.table_number or "Unknown",
            "table_id": ko.check_id,
            "server_name": None,
            "guest_count": 1,
            "items": kds_items,
            "item_count": len(kds_items),
            "status": ticket_status,
            "order_type": "dine_in",
            "is_rush": ko.priority >= 1,
            "is_vip": ko.priority >= 2,
            "priority": ko.priority,
            "notes": ko.notes,
            "created_at": ko.created_at.isoformat() if ko.created_at else None,
            "started_at": ko.started_at.isoformat() if ko.started_at else None,
            "bumped_at": ko.completed_at.isoformat() if ko.completed_at else None,
            "wait_time_minutes": wait_time,
            "is_overdue": wait_time > 15,
            "has_allergens": False,
            "source": "database",
        }
        tickets.append(ticket)

    # Sort by priority and creation time
    tickets.sort(key=lambda t: (-t.get("priority", 0), t.get("created_at", "") or ""))
    return tickets


@router.post("/tickets/{ticket_id}/bump")
def bump_ticket(
    db: DbSession,
    ticket_id: str,
):
    """Mark a ticket as bumped/completed."""
    now = datetime.now(timezone.utc)

    # Check if it's a database ticket (prefixed with "db-")
    if ticket_id.startswith("db-"):
        order_id = int(ticket_id[3:])
        kitchen_order = db.query(KitchenOrder).filter(KitchenOrder.id == order_id).first()
        if kitchen_order:
            kitchen_order.status = "completed"
            kitchen_order.completed_at = now
            _sync_guest_order_status(db, kitchen_order, "completed")
            db.commit()
            return {"status": "ok", "ticket_id": ticket_id, "bumped_at": now.isoformat()}

    # Try to find by numeric ID
    try:
        order_id = int(ticket_id)
        kitchen_order = db.query(KitchenOrder).filter(KitchenOrder.id == order_id).first()
        if kitchen_order:
            kitchen_order.status = "completed"
            kitchen_order.completed_at = now
            _sync_guest_order_status(db, kitchen_order, "completed")
            db.commit()
            return {"status": "ok", "ticket_id": ticket_id, "bumped_at": now.isoformat()}
    except ValueError:
        pass

    raise HTTPException(status_code=404, detail="Ticket not found")


@router.post("/tickets/{ticket_id}/start")
def start_ticket(
    db: DbSession,
    ticket_id: str,
):
    """Mark a ticket as started/in progress."""
    now = datetime.now(timezone.utc)

    # Check if it's a database ticket (prefixed with "db-")
    if ticket_id.startswith("db-"):
        order_id = int(ticket_id[3:])
        kitchen_order = db.query(KitchenOrder).filter(KitchenOrder.id == order_id).first()
        if kitchen_order:
            kitchen_order.status = "cooking"
            kitchen_order.started_at = now
            _sync_guest_order_status(db, kitchen_order, "cooking")
            db.commit()
            return {"status": "ok", "ticket_id": ticket_id, "started_at": now.isoformat()}

    # Try to find by numeric ID
    try:
        order_id = int(ticket_id)
        kitchen_order = db.query(KitchenOrder).filter(KitchenOrder.id == order_id).first()
        if kitchen_order:
            kitchen_order.status = "cooking"
            kitchen_order.started_at = now
            _sync_guest_order_status(db, kitchen_order, "cooking")
            db.commit()
            return {"status": "ok", "ticket_id": ticket_id, "started_at": now.isoformat()}
    except ValueError:
        pass

    raise HTTPException(status_code=404, detail="Ticket not found")


@router.post("/tickets/{ticket_id}/recall")
def recall_ticket(
    db: DbSession,
    ticket_id: str,
):
    """Recall a bumped ticket back to the display."""
    now = datetime.now(timezone.utc)

    # Check if it's a database ticket (prefixed with "db-")
    if ticket_id.startswith("db-"):
        order_id = int(ticket_id[3:])
        kitchen_order = db.query(KitchenOrder).filter(KitchenOrder.id == order_id).first()
        if kitchen_order:
            kitchen_order.status = "pending"
            kitchen_order.completed_at = None
            db.commit()
            return {"status": "ok", "ticket_id": ticket_id, "recalled_at": now.isoformat()}

    # Try to find by numeric ID
    try:
        order_id = int(ticket_id)
        kitchen_order = db.query(KitchenOrder).filter(KitchenOrder.id == order_id).first()
        if kitchen_order:
            kitchen_order.status = "pending"
            kitchen_order.completed_at = None
            db.commit()
            return {"status": "ok", "ticket_id": ticket_id, "recalled_at": now.isoformat()}
    except ValueError:
        pass

    raise HTTPException(status_code=404, detail="Ticket not found")


@router.post("/tickets/{ticket_id}/void")
def void_ticket(
    db: DbSession,
    ticket_id: str,
    reason: Optional[str] = None,
):
    """Void a ticket."""
    now = datetime.now(timezone.utc)

    # Check if it's a database ticket (prefixed with "db-")
    if ticket_id.startswith("db-"):
        order_id = int(ticket_id[3:])
        kitchen_order = db.query(KitchenOrder).filter(KitchenOrder.id == order_id).first()
        if kitchen_order:
            kitchen_order.status = "cancelled"
            db.commit()
            return {"status": "ok", "ticket_id": ticket_id, "voided_at": now.isoformat()}

    # Try to find by numeric ID
    try:
        order_id = int(ticket_id)
        kitchen_order = db.query(KitchenOrder).filter(KitchenOrder.id == order_id).first()
        if kitchen_order:
            kitchen_order.status = "cancelled"
            db.commit()
            return {"status": "ok", "ticket_id": ticket_id, "voided_at": now.isoformat()}
    except ValueError:
        pass

    raise HTTPException(status_code=404, detail="Ticket not found")


@router.post("/tickets/{ticket_id}/priority")
def set_ticket_priority(
    db: DbSession,
    ticket_id: str,
    priority: int = 0,
):
    """Set ticket priority (0=normal, 1=rush, 2=VIP)."""
    # Check if it's a database ticket (prefixed with "db-")
    if ticket_id.startswith("db-"):
        order_id = int(ticket_id[3:])
        kitchen_order = db.query(KitchenOrder).filter(KitchenOrder.id == order_id).first()
        if kitchen_order:
            kitchen_order.priority = priority
            db.commit()
            return {"status": "ok", "ticket_id": ticket_id, "priority": priority}

    # Try to find by numeric ID
    try:
        order_id = int(ticket_id)
        kitchen_order = db.query(KitchenOrder).filter(KitchenOrder.id == order_id).first()
        if kitchen_order:
            kitchen_order.priority = priority
            db.commit()
            return {"status": "ok", "ticket_id": ticket_id, "priority": priority}
    except ValueError:
        pass

    raise HTTPException(status_code=404, detail="Ticket not found")


@router.post("/fire-course")
def fire_course(
    db: DbSession,
    ticket_id: Optional[str] = None,
    course: str = "main",
):
    """Fire a course for a ticket or all tickets."""
    # This would update check items in real implementation
    return {"status": "ok", "fired_count": 0, "course": course}


@router.get("/expo")
def get_expo_tickets(
    db: DbSession,
    location_id: Optional[int] = None,
):
    """Get tickets ready for expo/pickup."""
    query = db.query(KitchenOrder).filter(KitchenOrder.status == "ready")
    if location_id:
        query = query.filter(KitchenOrder.location_id == location_id)

    expo_tickets = []
    for ko in query.all():
        expo_tickets.append({
            "ticket_id": f"db-{ko.id}",
            "order_id": ko.id,
            "table_number": ko.table_number or "Unknown",
            "items": ko.items or [],
            "item_count": len(ko.items) if ko.items else 0,
            "ready_at": ko.completed_at.isoformat() if ko.completed_at else None,
            "order_type": "dine_in",
        })
    return expo_tickets


@router.get("/86/list")
def get_86_items(
    db: DbSession,
    location_id: Optional[int] = None,
):
    """Get list of 86'd items (unavailable menu items)."""
    query = db.query(MenuItem).filter(MenuItem.available == False)
    if location_id:
        query = query.filter(MenuItem.location_id == location_id)

    items = []
    for item in query.all():
        items.append({
            "id": item.id,
            "name": item.name,
            "marked_at": item.updated_at.isoformat() if item.updated_at else None,
            "estimated_return": None,
        })
    return items


@router.post("/86/{item_id}")
def mark_item_86(
    db: DbSession,
    item_id: int,
    name: Optional[str] = None,
    estimated_return: Optional[str] = None,
):
    """Mark an item as 86'd (out of stock)."""
    menu_item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if menu_item:
        menu_item.available = False
        db.commit()
        return {"status": "ok", "item_id": item_id, "is_86": True}

    # If item doesn't exist, just return success
    return {"status": "ok", "item_id": item_id, "is_86": True}


@router.delete("/86/{item_id}")
def unmark_item_86(
    db: DbSession,
    item_id: int,
):
    """Remove an item from 86 list (make available)."""
    menu_item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if menu_item:
        menu_item.available = True
        db.commit()
    return {"status": "ok", "item_id": item_id, "is_86": False}


class Item86Request(BaseModel):
    menu_item_id: Optional[int] = None
    item_id: Optional[int] = None
    reason: Optional[str] = None
    estimated_return: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = True


@router.post("/86")
def add_86_item(
    db: DbSession,
    data: Optional[Item86Request] = None,
    item_id: Optional[int] = None,
    name: Optional[str] = None,
):
    """Add item to 86 list (POST method). Accepts JSON body or query param."""
    resolved_id = item_id
    if data:
        resolved_id = data.menu_item_id or data.item_id or item_id
    if not resolved_id:
        raise HTTPException(status_code=422, detail="item_id or menu_item_id required")
    return mark_item_86(db, resolved_id, name)


@router.get("/")
def get_all_alerts(
    db: DbSession,
    active_only: bool = True,
    location_id: Optional[int] = None,
):
    """Get all kitchen alerts (for /kitchen-alerts/ endpoint)."""
    alerts = []

    # Get overdue tickets as alerts
    query = db.query(KitchenOrder).filter(KitchenOrder.status.in_(["pending", "cooking"]))
    if location_id:
        query = query.filter(KitchenOrder.location_id == location_id)

    target_time = 15  # 15 minute target
    for ko in query.all():
        if ko.created_at:
            wait_time = int((datetime.now(timezone.utc) - _utc_aware(ko.created_at)).total_seconds() / 60)
            if wait_time > target_time:
                alerts.append({
                    "id": ko.id,
                    "alert_type": "overdue",
                    "message": f"Order #{ko.id} (Table {ko.table_number or 'Unknown'}) overdue by {wait_time - target_time} min",
                    "order_id": ko.id,
                    "created_at": ko.created_at.isoformat() if ko.created_at else None,
                    "severity": "high" if wait_time > target_time * 1.5 else "medium",
                })
            elif ko.priority >= 2:
                alerts.append({
                    "id": ko.id + 10000,
                    "alert_type": "vip",
                    "message": f"VIP Order #{ko.id} (Table {ko.table_number or 'Unknown'})",
                    "order_id": ko.id,
                    "created_at": ko.created_at.isoformat() if ko.created_at else None,
                    "severity": "high",
                })
            elif ko.priority >= 1:
                alerts.append({
                    "id": ko.id + 20000,
                    "alert_type": "rush",
                    "message": f"Rush Order #{ko.id} (Table {ko.table_number or 'Unknown'})",
                    "order_id": ko.id,
                    "created_at": ko.created_at.isoformat() if ko.created_at else None,
                    "severity": "medium",
                })

    # Get 86'd items as alerts
    items_86 = db.query(MenuItem).filter(MenuItem.available == False).all()
    for item in items_86:
        alerts.append({
            "id": item.id + 30000,
            "alert_type": "item_86",
            "message": f"{item.name} is 86'd (out of stock)",
            "order_id": None,
            "created_at": item.updated_at.isoformat() if item.updated_at else None,
            "severity": "low",
        })

    # HACCP temperature alerts
    try:
        from app.models.operations import HACCPTemperatureLog
        temp_alerts = db.query(HACCPTemperatureLog).filter(
            HACCPTemperatureLog.status.in_(["warning", "critical"]),
        ).order_by(HACCPTemperatureLog.recorded_at.desc()).limit(20).all()
        for t in temp_alerts:
            alerts.append({
                "id": t.id + 40000,
                "alert_type": "temperature",
                "message": f"{t.location} ({t.equipment}): {t.temperature}{t.unit}",
                "order_id": None,
                "created_at": t.recorded_at.isoformat() if t.recorded_at else None,
                "severity": t.status,
            })
    except Exception:
        pass  # HACCP table may not exist yet

    return alerts


@router.get("/alerts/cook-time")
def get_cook_time_alerts(
    db: DbSession,
    location_id: Optional[int] = None,
):
    """Get tickets that are overdue or approaching target cook time."""
    query = db.query(KitchenOrder).filter(KitchenOrder.status.in_(["pending", "cooking"]))
    if location_id:
        query = query.filter(KitchenOrder.location_id == location_id)

    alerts = []
    target_time = 15  # 15 minute target

    for ko in query.all():
        if ko.created_at:
            wait_time = int((datetime.now(timezone.utc) - _utc_aware(ko.created_at)).total_seconds() / 60)
            if wait_time > target_time * 0.8:  # Alert at 80% of target
                alerts.append({
                    "ticket_id": f"db-{ko.id}",
                    "order_id": ko.id,
                    "table_number": ko.table_number or "Unknown",
                    "wait_time_minutes": wait_time,
                    "target_time": target_time,
                    "is_overdue": wait_time > target_time,
                })
    return alerts


def _station_to_dict(s, load: int = 0) -> dict:
    """Convert a KitchenStation model to frontend-expected dict."""
    return {
        "station_id": f"{s.station_type.upper()}-{s.id}",
        "id": s.id,
        "name": s.name,
        "type": s.station_type,
        "categories": s.equipment_ids or [],
        "avg_cook_time": s.avg_item_time_seconds // 60 if s.avg_item_time_seconds else 0,
        "max_capacity": s.max_concurrent_items,
        "current_load": load,
        "is_active": s.is_active,
        "printer_id": None,
        "display_order": s.id,
    }


@router.get("/stations")
def get_kitchen_stations(
    db: DbSession,
    location_id: Optional[int] = None,
):
    """Get kitchen stations."""
    from app.models.advanced_features import KitchenStation

    # Count current load per station from active kitchen orders
    station_loads = {}
    query = db.query(KitchenOrder).filter(KitchenOrder.status.in_(["pending", "cooking"]))
    if location_id:
        query = query.filter(KitchenOrder.location_id == location_id)

    for ko in query.all():
        station_id = ko.station or "KITCHEN-1"
        station_loads[station_id] = station_loads.get(station_id, 0) + 1

    # Query stations from database
    station_query = db.query(KitchenStation)
    if location_id:
        station_query = station_query.filter(KitchenStation.location_id == location_id)
    stations = station_query.order_by(KitchenStation.id).all()

    return [
        _station_to_dict(s, station_loads.get(f"{s.station_type.upper()}-{s.id}", 0))
        for s in stations
    ]


class StationCreate(BaseModel):
    name: str
    type: Optional[str] = "kitchen"
    station_type: Optional[str] = None
    categories: Optional[list] = []
    avg_cook_time: Optional[int] = 10
    max_capacity: Optional[int] = 15
    printer_id: Optional[str] = None
    is_active: Optional[bool] = True
    display_order: Optional[int] = 0
    location_id: Optional[int] = 1


class StationUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    station_type: Optional[str] = None
    categories: Optional[list] = None
    avg_cook_time: Optional[int] = None
    max_capacity: Optional[int] = None
    printer_id: Optional[str] = None
    is_active: Optional[bool] = None


@router.post("/stations")
def create_kitchen_station(
    db: DbSession,
    data: StationCreate,
):
    """Create a new kitchen station."""
    from app.models.advanced_features import KitchenStation

    station_type = data.station_type or data.type or "kitchen"

    station = KitchenStation(
        name=data.name,
        station_type=station_type,
        max_concurrent_items=data.max_capacity or 15,
        avg_item_time_seconds=(data.avg_cook_time or 10) * 60,
        equipment_ids=data.categories or [],
        is_active=data.is_active if data.is_active is not None else True,
        location_id=data.location_id or 1,
    )
    db.add(station)
    db.commit()
    db.refresh(station)

    return _station_to_dict(station)


def _resolve_station(db, station_id: str):
    """Resolve a station by numeric ID or station_id string like 'GRILL-1'."""
    from app.models.advanced_features import KitchenStation

    # Try numeric ID first
    try:
        numeric_id = int(station_id)
        station = db.query(KitchenStation).filter(KitchenStation.id == numeric_id).first()
        if station:
            return station
    except (ValueError, TypeError):
        pass

    # Try station_id format like "GRILL-1" -> extract trailing number
    if "-" in station_id:
        parts = station_id.rsplit("-", 1)
        try:
            numeric_id = int(parts[1])
            station = db.query(KitchenStation).filter(KitchenStation.id == numeric_id).first()
            if station:
                return station
        except (ValueError, IndexError):
            pass

    return None


@router.put("/stations/{station_id}")
def update_kitchen_station(
    db: DbSession,
    station_id: str,
    data: StationUpdate,
):
    """Update an existing kitchen station."""
    station = _resolve_station(db, station_id)
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")

    if data.name is not None:
        station.name = data.name
    if data.type is not None or data.station_type is not None:
        station.station_type = data.station_type or data.type
    if data.categories is not None:
        station.equipment_ids = data.categories
    if data.avg_cook_time is not None:
        station.avg_item_time_seconds = data.avg_cook_time * 60
    if data.max_capacity is not None:
        station.max_concurrent_items = data.max_capacity
    if data.is_active is not None:
        station.is_active = data.is_active

    db.commit()
    db.refresh(station)

    # Get current load
    load = db.query(KitchenOrder).filter(
        KitchenOrder.status.in_(["pending", "cooking"]),
        KitchenOrder.station == f"{station.station_type.upper()}-{station.id}",
    ).count()

    return _station_to_dict(station, load)


@router.delete("/stations/{station_id}")
def delete_kitchen_station(
    db: DbSession,
    station_id: str,
):
    """Delete a kitchen station."""
    station = _resolve_station(db, station_id)
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")

    deleted_id = station.id
    db.delete(station)
    db.commit()
    return {"status": "ok", "deleted_id": deleted_id}


@router.post("/order/{order_id}/start")
def start_order_preparation(
    db: DbSession,
    order_id: int,
):
    """Mark order as started preparation."""
    kitchen_order = db.query(KitchenOrder).filter(KitchenOrder.id == order_id).first()
    if kitchen_order:
        kitchen_order.status = "cooking"
        kitchen_order.started_at = datetime.now(timezone.utc)
        db.commit()
    return {"status": "ok", "order_id": order_id, "started_at": datetime.now(timezone.utc).isoformat()}


@router.post("/order/{order_id}/complete")
def complete_order(
    db: DbSession,
    order_id: int,
):
    """Mark order as completed."""
    kitchen_order = db.query(KitchenOrder).filter(KitchenOrder.id == order_id).first()
    if kitchen_order:
        kitchen_order.status = "completed"
        kitchen_order.completed_at = datetime.now(timezone.utc)
        db.commit()
    return {"status": "ok", "order_id": order_id, "completed_at": datetime.now(timezone.utc).isoformat()}


@router.post("/order/{order_id}/ready")
def mark_order_ready(
    db: DbSession,
    order_id: int,
):
    """Mark order as ready for pickup/serving."""
    kitchen_order = db.query(KitchenOrder).filter(KitchenOrder.id == order_id).first()
    if kitchen_order:
        kitchen_order.status = "ready"
        _sync_guest_order_status(db, kitchen_order, "ready")
        db.commit()
    return {"status": "ok", "order_id": order_id, "ready_at": datetime.now(timezone.utc).isoformat()}


@router.post("/item/{item_id}/available")
def mark_item_available(
    db: DbSession,
    item_id: int,
):
    """Mark an item as available again."""
    menu_item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if menu_item:
        menu_item.available = True
        db.commit()
    return {"status": "ok", "item_id": item_id, "is_86": False}


# ==================== WORKFLOW MODES (Gap 11) ====================

@router.get("/requests/pending")
def get_pending_requests(
    db: DbSession,
    location_id: Optional[int] = None,
):
    """
    Get pending order requests (for Request mode workflow).
    These are orders that need confirmation before going to kitchen.
    """
    query = db.query(KitchenOrder).filter(
        KitchenOrder.workflow_mode == "request",
        KitchenOrder.is_confirmed == False,
        KitchenOrder.status != "cancelled",
    )
    if location_id:
        query = query.filter(KitchenOrder.location_id == location_id)

    requests = query.order_by(KitchenOrder.created_at.asc()).all()

    return {
        "requests": [
            {
                "id": r.id,
                "check_id": r.check_id,
                "table_number": r.table_number,
                "items": r.items or [],
                "notes": r.notes,
                "priority": r.priority,
                "station": r.station,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "wait_time_minutes": int((datetime.now(timezone.utc) - _utc_aware(r.created_at)).total_seconds() / 60) if r.created_at else 0,
            }
            for r in requests
        ],
        "count": len(requests),
    }


@router.post("/requests/{request_id}/confirm")
def confirm_request(
    db: DbSession,
    request_id: int,
    staff_id: Optional[int] = None,
):
    """
    Confirm an order request and send it to kitchen.
    """
    kitchen_order = db.query(KitchenOrder).filter(KitchenOrder.id == request_id).first()
    if not kitchen_order:
        raise HTTPException(status_code=404, detail="Request not found")

    if kitchen_order.workflow_mode != "request":
        raise HTTPException(status_code=400, detail="This order is not in request mode")

    if kitchen_order.is_confirmed:
        raise HTTPException(status_code=400, detail="Request already confirmed")

    kitchen_order.is_confirmed = True
    kitchen_order.confirmed_by = staff_id
    kitchen_order.confirmed_at = datetime.now(timezone.utc)
    kitchen_order.status = "pending"  # Now it goes to kitchen queue

    db.commit()

    return {
        "status": "confirmed",
        "request_id": request_id,
        "confirmed_at": kitchen_order.confirmed_at.isoformat(),
    }


@router.post("/requests/{request_id}/reject")
def reject_request(
    db: DbSession,
    request_id: int,
    reason: Optional[str] = None,
    staff_id: Optional[int] = None,
):
    """
    Reject an order request.
    """
    kitchen_order = db.query(KitchenOrder).filter(KitchenOrder.id == request_id).first()
    if not kitchen_order:
        raise HTTPException(status_code=404, detail="Request not found")

    if kitchen_order.workflow_mode != "request":
        raise HTTPException(status_code=400, detail="This order is not in request mode")

    kitchen_order.status = "cancelled"
    kitchen_order.rejection_reason = reason
    kitchen_order.confirmed_by = staff_id
    kitchen_order.confirmed_at = datetime.now(timezone.utc)

    db.commit()

    return {
        "status": "rejected",
        "request_id": request_id,
        "reason": reason,
    }


@router.post("/requests/{request_id}/modify")
def modify_request(
    db: DbSession,
    request_id: int,
    items: Optional[list] = None,
    notes: Optional[str] = None,
):
    """
    Modify a pending order request before confirming.
    """
    kitchen_order = db.query(KitchenOrder).filter(KitchenOrder.id == request_id).first()
    if not kitchen_order:
        raise HTTPException(status_code=404, detail="Request not found")

    if kitchen_order.is_confirmed:
        raise HTTPException(status_code=400, detail="Cannot modify confirmed request")

    if items is not None:
        kitchen_order.items = items
    if notes is not None:
        kitchen_order.notes = notes

    db.commit()

    return {
        "status": "modified",
        "request_id": request_id,
        "items": kitchen_order.items,
        "notes": kitchen_order.notes,
    }


@router.get("/workflow/settings")
def get_workflow_settings(
    db: DbSession,
    location_id: Optional[int] = None,
):
    """Get current workflow mode settings from database."""
    from app.models.hardware import Integration
    SETTINGS_ID = "kitchen_workflow"
    DEFAULT_SETTINGS = {
        "default_workflow_mode": "order",
        "require_confirmation_for": ["high_value_orders", "large_party", "special_items"],
        "confirmation_timeout_minutes": 5,
        "auto_reject_on_timeout": False,
        "notify_on_new_request": True,
        "request_mode_stations": [],
    }
    integration = db.query(Integration).filter(Integration.integration_id == SETTINGS_ID).first()
    if integration and integration.config:
        return {**DEFAULT_SETTINGS, **integration.config}
    return DEFAULT_SETTINGS


@router.put("/workflow/settings")
def update_workflow_settings(
    db: DbSession,
    default_mode: Optional[str] = None,
    confirmation_timeout: Optional[int] = None,
):
    """Update workflow mode settings and persist to database."""
    from app.models.hardware import Integration
    SETTINGS_ID = "kitchen_workflow"
    integration = db.query(Integration).filter(Integration.integration_id == SETTINGS_ID).first()
    if not integration:
        integration = Integration(
            integration_id=SETTINGS_ID,
            name="Kitchen Workflow Settings",
            category="kitchen",
            status="active",
            config={},
        )
        db.add(integration)
    config = integration.config or {}
    if default_mode is not None:
        config["default_workflow_mode"] = default_mode
    if confirmation_timeout is not None:
        config["confirmation_timeout_minutes"] = confirmation_timeout
    integration.config = config
    db.commit()
    return {
        "status": "updated",
        "default_workflow_mode": config.get("default_workflow_mode", "order"),
        "confirmation_timeout_minutes": config.get("confirmation_timeout_minutes", 5),
    }


@router.post("/order/create")
def create_kitchen_order(
    db: DbSession,
    check_id: Optional[int] = None,
    table_number: Optional[str] = None,
    items: list = [],
    notes: Optional[str] = None,
    station: Optional[str] = None,
    workflow_mode: str = "order",
    priority: int = 0,
    location_id: Optional[int] = None,
):
    """
    Create a new kitchen order with specified workflow mode.

    workflow_mode:
    - "order": Direct to kitchen (default)
    - "request": Needs confirmation before kitchen
    """
    is_confirmed = workflow_mode == "order"

    kitchen_order = KitchenOrder(
        check_id=check_id,
        table_number=table_number,
        items=items,
        notes=notes,
        station=station,
        workflow_mode=workflow_mode,
        is_confirmed=is_confirmed,
        status="pending" if is_confirmed else "request_pending",
        priority=priority,
        location_id=location_id,
    )

    db.add(kitchen_order)
    db.commit()
    db.refresh(kitchen_order)

    return {
        "id": kitchen_order.id,
        "workflow_mode": kitchen_order.workflow_mode,
        "is_confirmed": kitchen_order.is_confirmed,
        "status": kitchen_order.status,
        "created_at": kitchen_order.created_at.isoformat() if kitchen_order.created_at else None,
    }


@router.post("/rush/{order_id}")
def set_rush_priority(order_id: int, db: DbSession):
    """Mark an order as rush priority."""
    order = db.query(KitchenOrder).filter(KitchenOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Kitchen order not found")
    order.priority = 1  # 1 = rush
    db.commit()
    return {"success": True, "order_id": order_id, "priority": "rush"}


@router.post("/vip/{order_id}")
def set_vip_priority(order_id: int, db: DbSession):
    """Mark an order as VIP priority."""
    order = db.query(KitchenOrder).filter(KitchenOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Kitchen order not found")
    order.priority = 2  # 2 = VIP
    db.commit()
    return {"success": True, "order_id": order_id, "priority": "vip"}


# ==================== DISPLAY (merged from kitchen_display.py) ====================

@router.get("/display/stations")
async def get_display_stations(db: DbSession):
    """Get KDS display stations."""
    from app.models.advanced_features import KitchenStation
    stations = db.query(KitchenStation).filter(KitchenStation.is_active == True).order_by(KitchenStation.id).all()

    # Count pending tickets per station
    pending_counts = dict(
        db.query(KitchenOrder.station, func.count(KitchenOrder.id))
        .filter(KitchenOrder.status.in_(["pending", "cooking"]))
        .group_by(KitchenOrder.station)
        .all()
    )

    return [
        {
            "id": s.station_type,
            "name": s.name,
            "active": s.is_active,
            "pending_tickets": pending_counts.get(s.station_type, 0),
            "avg_time": s.avg_item_time_seconds // 60 if s.avg_item_time_seconds else 0,
        }
        for s in stations
    ]


@router.get("/display/tickets")
async def get_display_tickets(db: DbSession, station: str = None):
    """Get KDS display tickets."""
    query = db.query(KitchenOrder).filter(
        KitchenOrder.status.in_(["pending", "cooking"])
    )
    if station:
        query = query.filter(KitchenOrder.station == station)
    orders = query.order_by(KitchenOrder.priority.desc(), KitchenOrder.created_at).all()
    return [
        {
            "id": o.id,
            "table_number": o.table_number,
            "station": o.station,
            "status": o.status,
            "priority": o.priority,
            "items": o.items or [],
            "notes": o.notes,
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "started_at": o.started_at.isoformat() if o.started_at else None,
        }
        for o in orders
    ]


# ==================== ALERTS (merged from kitchen_alerts.py) ====================

@router.get("/alerts/summary")
async def get_kitchen_alerts_summary(db: DbSession):
    """Get kitchen alerts (overdue orders, temp warnings)."""
    from app.models.operations import HACCPTemperatureLog
    alerts = []
    # Overdue orders: pending for more than 15 minutes
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=15)
    overdue = db.query(KitchenOrder).filter(
        KitchenOrder.status.in_(["pending", "cooking"]),
        KitchenOrder.created_at < cutoff,
    ).all()
    for o in overdue:
        alerts.append({
            "id": f"order-{o.id}",
            "type": "overdue_order",
            "severity": "warning",
            "message": f"Order #{o.id} (table {o.table_number}) has been {o.status} for over 15 min",
            "created_at": o.created_at.isoformat() if o.created_at else None,
        })
    # Temperature alerts
    temp_alerts = db.query(HACCPTemperatureLog).filter(
        HACCPTemperatureLog.status.in_(["warning", "critical"]),
    ).order_by(HACCPTemperatureLog.recorded_at.desc()).limit(20).all()
    for t in temp_alerts:
        alerts.append({
            "id": f"temp-{t.id}",
            "type": "temperature",
            "severity": t.status,
            "message": f"{t.location} ({t.equipment}): {t.temperature}{t.unit}",
            "created_at": t.recorded_at.isoformat() if t.recorded_at else None,
        })
    return alerts


@router.get("/alerts/statistics")
async def get_kitchen_alert_stats(db: DbSession):
    """Get kitchen alert statistics."""
    from app.models.operations import HACCPTemperatureLog
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=15)
    overdue_count = db.query(func.count(KitchenOrder.id)).filter(
        KitchenOrder.status.in_(["pending", "cooking"]),
        KitchenOrder.created_at < cutoff,
    ).scalar() or 0
    critical_temps = db.query(func.count(HACCPTemperatureLog.id)).filter(
        HACCPTemperatureLog.status == "critical",
    ).scalar() or 0
    warning_temps = db.query(func.count(HACCPTemperatureLog.id)).filter(
        HACCPTemperatureLog.status == "warning",
    ).scalar() or 0
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    resolved_today = db.query(func.count(KitchenOrder.id)).filter(
        KitchenOrder.status.in_(["completed", "ready"]),
        KitchenOrder.completed_at >= today_start,
    ).scalar() or 0
    return {
        "total_alerts": overdue_count + critical_temps + warning_temps,
        "critical": critical_temps,
        "warnings": overdue_count + warning_temps,
        "resolved_today": resolved_today,
    }

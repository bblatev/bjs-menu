"""Kitchen Display System (KDS) routes."""

from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.session import DbSession

# Import shared order data from waiter module
from app.api.routes.waiter import _checks, _tables

router = APIRouter()

# Track 86'd items
_items_86: dict = {}  # item_id -> {name, marked_at, estimated_return}


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
    # Count tickets by status
    status_counts = {"new": 0, "in_progress": 0, "ready": 0, "completed": 0}
    for check in _checks.values():
        status = check.get("status", "new")
        if status in status_counts:
            status_counts[status] += 1

    active_count = status_counts["new"] + status_counts["in_progress"]

    return {
        "total_tickets": len(_checks),
        "active_tickets": active_count,
        "avg_cook_time_minutes": 12.5,
        "bumped_today": status_counts["completed"],
        "active_alerts": 0,
        "orders_by_status": status_counts,
        "items_86_count": len(_items_86),
        "rush_orders_today": 0,
        "vip_orders_today": 0,
        "avg_prep_time_minutes": 12.5,
        "orders_completed_today": status_counts["completed"],
    }


@router.get("/queue")
def get_kitchen_queue(
    db: DbSession,
    location_id: Optional[int] = None,
):
    """Get current kitchen queue."""
    return {
        "orders": [],
        "total_in_queue": len(_checks),
        "avg_wait_time_minutes": 10
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
    for check_id, check in _checks.items():
        if check.get("items"):
            # Filter by status if specified
            ticket_status = check.get("status", "new")
            if status and ticket_status != status:
                continue

            # Use table_name from check if available (guest orders), otherwise look up
            table_name = check.get("table_name")
            if not table_name:
                table_name = f"Table {check.get('table_id', '?')}"
                for t in _tables:
                    if t["table_id"] == check.get("table_id"):
                        table_name = t["table_name"]
                        break

            # Calculate wait time
            created_at = check.get("created_at")
            wait_time = 0
            if created_at:
                if isinstance(created_at, str):
                    try:
                        created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        wait_time = int((datetime.utcnow() - created_dt.replace(tzinfo=None)).total_seconds() / 60)
                    except:
                        pass

            # Build items list with KDS format
            kds_items = []
            for item in check.get("items", []):
                kds_items.append({
                    "id": item.get("id") or item.get("menu_item_id"),
                    "name": item.get("name"),
                    "quantity": item.get("quantity", 1),
                    "modifiers": item.get("modifiers", []),
                    "notes": item.get("notes"),
                    "is_fired": item.get("status") == "fired",
                    "is_voided": item.get("status") == "voided",
                    "course": item.get("course", "main"),
                    "seat": item.get("seat"),
                    "allergens": item.get("allergens", []),
                })

            ticket = {
                "ticket_id": str(check_id),
                "order_id": check_id,
                "station_id": check.get("station_id", "KITCHEN-1"),
                "table_number": table_name,
                "table": table_name,
                "table_id": check.get("table_id"),
                "server_name": check.get("server_name", "Server"),
                "guest_count": check.get("guest_count", 1),
                "items": kds_items,
                "item_count": len(kds_items),
                "status": ticket_status,
                "order_type": check.get("order_type", "dine_in").replace("-", "_"),
                "is_rush": check.get("is_rush", False),
                "is_vip": check.get("is_vip", False),
                "priority": check.get("priority", 0),
                "notes": check.get("notes"),
                "created_at": created_at,
                "started_at": check.get("started_at"),
                "bumped_at": check.get("bumped_at"),
                "wait_time_minutes": wait_time,
                "is_overdue": wait_time > 15,
                "has_allergens": any(item.get("allergens") for item in kds_items),
                "source": check.get("source", "pos"),
            }
            tickets.append(ticket)

    # Sort by priority and creation time
    tickets.sort(key=lambda t: (-t.get("priority", 0), t.get("created_at", "")))
    return tickets


@router.post("/tickets/{ticket_id}/bump")
def bump_ticket(
    db: DbSession,
    ticket_id: str,
):
    """Mark a ticket as bumped/completed."""
    check_id = int(ticket_id) if ticket_id.isdigit() else ticket_id
    if check_id in _checks:
        _checks[check_id]["status"] = "completed"
        _checks[check_id]["bumped_at"] = datetime.utcnow().isoformat()
        return {"status": "ok", "ticket_id": ticket_id, "bumped_at": _checks[check_id]["bumped_at"]}
    raise HTTPException(status_code=404, detail="Ticket not found")


@router.post("/tickets/{ticket_id}/start")
def start_ticket(
    db: DbSession,
    ticket_id: str,
):
    """Mark a ticket as started/in progress."""
    check_id = int(ticket_id) if ticket_id.isdigit() else ticket_id
    if check_id in _checks:
        _checks[check_id]["status"] = "in_progress"
        _checks[check_id]["started_at"] = datetime.utcnow().isoformat()
        return {"status": "ok", "ticket_id": ticket_id, "started_at": _checks[check_id]["started_at"]}
    raise HTTPException(status_code=404, detail="Ticket not found")


@router.post("/tickets/{ticket_id}/recall")
def recall_ticket(
    db: DbSession,
    ticket_id: str,
):
    """Recall a bumped ticket back to the display."""
    check_id = int(ticket_id) if ticket_id.isdigit() else ticket_id
    if check_id in _checks:
        _checks[check_id]["status"] = "new"
        _checks[check_id]["recalled_at"] = datetime.utcnow().isoformat()
        return {"status": "ok", "ticket_id": ticket_id, "recalled_at": _checks[check_id]["recalled_at"]}
    raise HTTPException(status_code=404, detail="Ticket not found")


@router.post("/tickets/{ticket_id}/void")
def void_ticket(
    db: DbSession,
    ticket_id: str,
    reason: Optional[str] = None,
):
    """Void a ticket."""
    check_id = int(ticket_id) if ticket_id.isdigit() else ticket_id
    if check_id in _checks:
        _checks[check_id]["status"] = "voided"
        _checks[check_id]["void_reason"] = reason
        _checks[check_id]["voided_at"] = datetime.utcnow().isoformat()
        return {"status": "ok", "ticket_id": ticket_id, "voided_at": _checks[check_id]["voided_at"]}
    raise HTTPException(status_code=404, detail="Ticket not found")


@router.post("/tickets/{ticket_id}/priority")
def set_ticket_priority(
    db: DbSession,
    ticket_id: str,
    priority: int = 0,
):
    """Set ticket priority (0=normal, 1=rush, 2=VIP)."""
    check_id = int(ticket_id) if ticket_id.isdigit() else ticket_id
    if check_id in _checks:
        _checks[check_id]["priority"] = priority
        _checks[check_id]["is_rush"] = priority >= 1
        _checks[check_id]["is_vip"] = priority >= 2
        return {"status": "ok", "ticket_id": ticket_id, "priority": priority}
    raise HTTPException(status_code=404, detail="Ticket not found")


@router.post("/fire-course")
def fire_course(
    db: DbSession,
    ticket_id: Optional[str] = None,
    course: str = "main",
):
    """Fire a course for a ticket or all tickets."""
    fired_count = 0
    now = datetime.utcnow().isoformat()

    for check_id, check in _checks.items():
        if ticket_id and str(check_id) != ticket_id:
            continue
        for item in check.get("items", []):
            if item.get("course") == course or not item.get("is_fired"):
                item["is_fired"] = True
                item["fired_at"] = now
                fired_count += 1

    return {"status": "ok", "fired_count": fired_count, "course": course}


@router.get("/expo")
def get_expo_tickets(
    db: DbSession,
    location_id: Optional[int] = None,
):
    """Get tickets ready for expo/pickup."""
    expo_tickets = []
    for check_id, check in _checks.items():
        if check.get("status") == "ready":
            expo_tickets.append({
                "ticket_id": str(check_id),
                "order_id": check_id,
                "table_number": check.get("table_name") or f"Table {check.get('table_id', '?')}",
                "items": check.get("items", []),
                "item_count": len(check.get("items", [])),
                "ready_at": check.get("ready_at"),
                "order_type": check.get("order_type", "dine_in"),
            })
    return expo_tickets


@router.get("/86/list")
def get_86_items(
    db: DbSession,
    location_id: Optional[int] = None,
):
    """Get list of 86'd items."""
    items = []
    for item_id, item_data in _items_86.items():
        items.append({
            "id": item_id,
            "name": item_data.get("name", f"Item {item_id}"),
            "marked_at": item_data.get("marked_at"),
            "estimated_return": item_data.get("estimated_return"),
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
    _items_86[item_id] = {
        "name": name or f"Item {item_id}",
        "marked_at": datetime.utcnow().isoformat(),
        "estimated_return": estimated_return,
    }
    return {"status": "ok", "item_id": item_id, "is_86": True}


@router.delete("/86/{item_id}")
def unmark_item_86(
    db: DbSession,
    item_id: int,
):
    """Remove an item from 86 list."""
    if item_id in _items_86:
        del _items_86[item_id]
    return {"status": "ok", "item_id": item_id, "is_86": False}


@router.post("/86")
def add_86_item(
    db: DbSession,
    item_id: int,
    name: Optional[str] = None,
):
    """Add item to 86 list (POST method)."""
    return mark_item_86(db, item_id, name)


@router.get("/alerts/cook-time")
def get_cook_time_alerts(
    db: DbSession,
    location_id: Optional[int] = None,
):
    """Get tickets that are overdue or approaching target cook time."""
    alerts = []
    for check_id, check in _checks.items():
        if check.get("status") in ["new", "in_progress"]:
            created_at = check.get("created_at")
            wait_time = 0
            if created_at:
                if isinstance(created_at, str):
                    try:
                        created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        wait_time = int((datetime.utcnow() - created_dt.replace(tzinfo=None)).total_seconds() / 60)
                    except:
                        pass

            target_time = 15  # 15 minute target
            if wait_time > target_time * 0.8:  # Alert at 80% of target
                alerts.append({
                    "ticket_id": str(check_id),
                    "order_id": check_id,
                    "table_number": check.get("table_name") or f"Table {check.get('table_id', '?')}",
                    "wait_time_minutes": wait_time,
                    "target_time": target_time,
                    "is_overdue": wait_time > target_time,
                })
    return alerts


@router.get("/stations")
def get_kitchen_stations(
    db: DbSession,
    location_id: Optional[int] = None,
):
    """Get kitchen stations."""
    # Count current load per station from active tickets
    station_loads = {}
    for check in _checks.values():
        station_id = check.get("station_id", "KITCHEN-1")
        if check.get("status") in ["new", "in_progress"]:
            station_loads[station_id] = station_loads.get(station_id, 0) + 1

    return [
        {"station_id": "KITCHEN-1", "id": 1, "name": "Main Kitchen", "type": "kitchen", "categories": ["all"], "avg_cook_time": 12, "max_capacity": 20, "current_load": station_loads.get("KITCHEN-1", 0), "is_active": True, "printer_id": "KITCHEN-01", "display_order": 1},
        {"station_id": "GRILL-1", "id": 2, "name": "Grill Station", "type": "grill", "categories": ["steaks", "burgers", "grilled_items"], "avg_cook_time": 12, "max_capacity": 20, "current_load": station_loads.get("GRILL-1", 0), "is_active": True, "printer_id": "GRILL-01", "display_order": 2},
        {"station_id": "FRY-1", "id": 3, "name": "Fry Station", "type": "fryer", "categories": ["fried_items", "sides"], "avg_cook_time": 8, "max_capacity": 15, "current_load": station_loads.get("FRY-1", 0), "is_active": True, "printer_id": "FRY-01", "display_order": 3},
        {"station_id": "SALAD-1", "id": 4, "name": "Salad & Cold", "type": "salad", "categories": ["salads", "appetizers"], "avg_cook_time": 5, "max_capacity": 12, "current_load": station_loads.get("SALAD-1", 0), "is_active": True, "printer_id": "SALAD-01", "display_order": 4},
        {"station_id": "DESSERT-1", "id": 5, "name": "Dessert Station", "type": "dessert", "categories": ["desserts"], "avg_cook_time": 6, "max_capacity": 10, "current_load": station_loads.get("DESSERT-1", 0), "is_active": True, "printer_id": "DESSERT-01", "display_order": 5},
        {"station_id": "EXPO-1", "id": 6, "name": "Expo Window", "type": "expo", "categories": [], "avg_cook_time": 2, "max_capacity": 25, "current_load": station_loads.get("EXPO-1", 0), "is_active": True, "printer_id": "EXPO-01", "display_order": 6},
        {"station_id": "BAR-1", "id": 7, "name": "Bar", "type": "bar", "categories": ["cocktails", "beer", "wine", "spirits", "soft_drinks"], "avg_cook_time": 4, "max_capacity": 18, "current_load": station_loads.get("BAR-1", 0), "is_active": True, "printer_id": "BAR-01", "display_order": 7},
    ]


@router.post("/order/{order_id}/start")
def start_order_preparation(
    db: DbSession,
    order_id: int,
):
    """Mark order as started preparation."""
    if order_id in _checks:
        _checks[order_id]["status"] = "in_progress"
        _checks[order_id]["started_at"] = datetime.utcnow().isoformat()
    return {"status": "ok", "order_id": order_id, "started_at": datetime.utcnow().isoformat()}


@router.post("/order/{order_id}/complete")
def complete_order(
    db: DbSession,
    order_id: int,
):
    """Mark order as completed."""
    if order_id in _checks:
        _checks[order_id]["status"] = "completed"
        _checks[order_id]["completed_at"] = datetime.utcnow().isoformat()
    return {"status": "ok", "order_id": order_id, "completed_at": datetime.utcnow().isoformat()}


@router.post("/order/{order_id}/ready")
def mark_order_ready(
    db: DbSession,
    order_id: int,
):
    """Mark order as ready for pickup/serving."""
    if order_id in _checks:
        _checks[order_id]["status"] = "ready"
        _checks[order_id]["ready_at"] = datetime.utcnow().isoformat()
    return {"status": "ok", "order_id": order_id, "ready_at": datetime.utcnow().isoformat()}


@router.post("/item/{item_id}/available")
def mark_item_available(
    db: DbSession,
    item_id: int,
):
    """Mark an item as available again."""
    if item_id in _items_86:
        del _items_86[item_id]
    return {"status": "ok", "item_id": item_id, "is_86": False}

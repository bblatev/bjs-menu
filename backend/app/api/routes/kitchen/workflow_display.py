"""Workflow settings, order management & display"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone, timedelta

from app.core.rate_limit import limiter
from app.db.session import get_db

# Import shared schemas and helpers
from app.api.routes.kitchen._shared import *
from app.api.routes.kitchen._shared import _utc_aware

router = APIRouter()

# ==================== WORKFLOW MODES (Gap 11) ====================

@router.get("/requests/pending")
@limiter.limit("60/minute")
def get_pending_requests(
    request: Request,
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

    requests = query.order_by(KitchenOrder.created_at.asc()).limit(200).all()

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
@limiter.limit("30/minute")
def confirm_request(
    request: Request,
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
@limiter.limit("30/minute")
def reject_request(
    request: Request,
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
@limiter.limit("30/minute")
def modify_request(
    request: Request,
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
@limiter.limit("60/minute")
def get_workflow_settings(
    request: Request,
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
@limiter.limit("30/minute")
def update_workflow_settings(
    request: Request,
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
@limiter.limit("30/minute")
def create_kitchen_order(
    request: Request,
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
@limiter.limit("30/minute")
def set_rush_priority(request: Request, order_id: int, db: DbSession):
    """Mark an order as rush priority."""
    order = db.query(KitchenOrder).filter(KitchenOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Kitchen order not found")
    order.priority = 1  # 1 = rush
    db.commit()
    return {"success": True, "order_id": order_id, "priority": "rush"}


@router.post("/vip/{order_id}")
@limiter.limit("30/minute")
def set_vip_priority(request: Request, order_id: int, db: DbSession):
    """Mark an order as VIP priority."""
    order = db.query(KitchenOrder).filter(KitchenOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Kitchen order not found")
    order.priority = 2  # 2 = VIP
    db.commit()
    return {"success": True, "order_id": order_id, "priority": "vip"}


# ==================== DISPLAY (merged from kitchen_display.py) ====================

@router.get("/display/stations")
@limiter.limit("60/minute")
async def get_display_stations(request: Request, db: DbSession):
    """Get KDS display stations."""
    from app.models.advanced_features import KitchenStation
    stations = db.query(KitchenStation).filter(KitchenStation.is_active == True).order_by(KitchenStation.id).limit(200).all()

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
@limiter.limit("60/minute")
async def get_display_tickets(request: Request, db: DbSession, station: str = None):
    """Get KDS display tickets."""
    query = db.query(KitchenOrder).filter(
        KitchenOrder.status.in_(["pending", "cooking"])
    )
    if station:
        query = query.filter(KitchenOrder.station == station)
    orders = query.order_by(KitchenOrder.priority.desc(), KitchenOrder.created_at).limit(200).all()
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
@limiter.limit("60/minute")
async def get_kitchen_alerts_summary(request: Request, db: DbSession):
    """Get kitchen alerts (overdue orders, temp warnings)."""
    from app.models.operations import HACCPTemperatureLog
    alerts = []
    # Overdue orders: pending for more than 15 minutes
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=15)
    overdue = db.query(KitchenOrder).filter(
        KitchenOrder.status.in_(["pending", "cooking"]),
        KitchenOrder.created_at < cutoff,
    ).limit(200).all()
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
@limiter.limit("60/minute")
async def get_kitchen_alert_stats(request: Request, db: DbSession):
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


# ==================== LOCALIZATION (proxy to kds-localization) ====================

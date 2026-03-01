"""Multi-location, integrations & throttling"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body, Request, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from app.core.rate_limit import limiter
from app.db.session import get_db

# Import shared schemas and helpers
from app.api.routes.enterprise._shared import *
from app.api.routes.enterprise._shared import _load_config, _save_config, _DEFAULT_THROTTLE_STATUS

router = APIRouter()

@router.get("/")
@limiter.limit("60/minute")
def get_enterprise_root(request: Request, db: DbSession):
    """Enterprise locations overview."""
    return get_enterprise_locations(request=request, db=db)


@router.get("/locations")
@limiter.limit("60/minute")
def get_enterprise_locations(request: Request, db: DbSession):
    """Get all locations for enterprise/multi-location setup."""
    from app.models.location import Location
    locations = db.query(Location).limit(500).all()
    return {
        "locations": [
            {
                "id": loc.id,
                "name": loc.name,
                "description": loc.description,
                "is_active": loc.active,
                "is_default": loc.is_default,
            }
            for loc in locations
        ],
        "total": len(locations),
    }


@router.get("/consolidated")
@limiter.limit("60/minute")
def get_consolidated_report(request: Request, db: DbSession):
    """Get consolidated enterprise report across all locations."""
    from sqlalchemy import func, Numeric as SaNumeric
    from app.models.location import Location
    from app.models.restaurant import Check, GuestOrder

    locations = db.query(Location).limit(500).all()

    # Aggregate revenue and order counts per location from checks
    check_stats = db.query(
        Check.location_id,
        func.coalesce(func.sum(Check.total), 0).label("revenue"),
        func.count(Check.id).label("order_count"),
    ).filter(
        Check.status != "voided",
    ).group_by(Check.location_id).all()
    check_map = {row.location_id: {"revenue": float(row.revenue), "orders": int(row.order_count)} for row in check_stats}

    # Also aggregate from guest orders (QR ordering)
    guest_stats = db.query(
        GuestOrder.location_id,
        func.coalesce(func.sum(GuestOrder.total), 0).label("revenue"),
        func.count(GuestOrder.id).label("order_count"),
    ).filter(
        GuestOrder.status != "cancelled",
    ).group_by(GuestOrder.location_id).all()
    guest_map = {row.location_id: {"revenue": float(row.revenue), "orders": int(row.order_count)} for row in guest_stats}

    total_revenue = 0.0
    total_orders = 0
    by_location = []

    for loc in locations:
        c = check_map.get(loc.id, {"revenue": 0.0, "orders": 0})
        g = guest_map.get(loc.id, {"revenue": 0.0, "orders": 0})
        loc_revenue = c["revenue"] + g["revenue"]
        loc_orders = c["orders"] + g["orders"]
        total_revenue += loc_revenue
        total_orders += loc_orders
        by_location.append({
            "location_id": loc.id,
            "location_name": loc.name,
            "revenue": round(loc_revenue, 2),
            "orders": loc_orders,
        })

    return {
        "period": "all_time",
        "locations_count": len(locations),
        "total_revenue": round(total_revenue, 2),
        "total_orders": total_orders,
        "by_location": by_location,
    }


# ==================== INTEGRATIONS ====================

@router.get("/integrations/marketplace")
@limiter.limit("60/minute")
def get_integrations_marketplace(
    request: Request,
    db: DbSession,
    category: Optional[str] = None,
):
    """Get available integrations from marketplace."""
    integrations = INTEGRATIONS_MARKETPLACE
    if category:
        integrations = [i for i in integrations if i["category"] == category]
    return {"integrations": integrations, "total": len(integrations)}


@router.get("/integrations/")
@limiter.limit("60/minute")
def list_integrations(request: Request, db: DbSession):
    """List all available integrations with connection status."""
    # Get connected integrations from database
    connected = db.query(IntegrationModel).filter(IntegrationModel.status == "connected").limit(500).all()
    connected_ids = {c.integration_id for c in connected}

    result = []
    for integration in INTEGRATIONS_MARKETPLACE:
        conn = next((c for c in connected if c.integration_id == integration["id"]), None)
        result.append({
            **integration,
            "status": "connected" if integration["id"] in connected_ids else "disconnected",
            "connected_at": conn.connected_at.isoformat() if conn and conn.connected_at else None,
        })
    return {"integrations": result}


@router.get("/integrations/connected")
@limiter.limit("60/minute")
def get_connected_integrations(request: Request, db: DbSession):
    """Get only connected integrations."""
    connected = db.query(IntegrationModel).filter(IntegrationModel.status == "connected").limit(500).all()

    result = []
    for conn in connected:
        marketplace_info = next((i for i in INTEGRATIONS_MARKETPLACE if i["id"] == conn.integration_id), None)
        if marketplace_info:
            result.append({
                **marketplace_info,
                "status": "connected",
                "connected_at": conn.connected_at.isoformat() if conn.connected_at else None,
                "config": conn.config,
            })
    return {"integrations": result, "total": len(result)}


@router.post("/integrations/connections/")
@limiter.limit("30/minute")
def connect_integration(
    request: Request,
    db: DbSession,
    connection: IntegrationConnection,
):
    """Connect to an integration."""
    marketplace_info = next((i for i in INTEGRATIONS_MARKETPLACE if i["id"] == connection.integration_id), None)
    if not marketplace_info:
        raise HTTPException(status_code=404, detail="Integration not found")

    # Check if already exists
    existing = db.query(IntegrationModel).filter(IntegrationModel.integration_id == connection.integration_id).first()

    if existing:
        existing.status = "connected"
        existing.connected_at = datetime.now(timezone.utc)
        existing.config = connection.credentials
    else:
        new_integration = IntegrationModel(
            integration_id=connection.integration_id,
            name=marketplace_info["name"],
            category=marketplace_info["category"],
            description=marketplace_info["description"],
            status="connected",
            config=connection.credentials,
            connected_at=datetime.now(timezone.utc),
        )
        db.add(new_integration)

    db.commit()

    return {"status": "connected", "integration_id": connection.integration_id}


@router.delete("/integrations/connections/{integration_id}")
@limiter.limit("30/minute")
def disconnect_integration(
    request: Request,
    db: DbSession,
    integration_id: str,
):
    """Disconnect from an integration."""
    integration = db.query(IntegrationModel).filter(IntegrationModel.integration_id == integration_id).first()
    if integration:
        integration.status = "disconnected"
        integration.connected_at = None
        db.commit()
    return {"status": "disconnected", "integration_id": integration_id}


# ==================== THROTTLING ====================

@router.get("/throttling/status")
@limiter.limit("60/minute")
def get_throttle_status(request: Request, db: DbSession, location_id: Optional[int] = None):
    """Get current throttling status."""
    # Get the first active rule for max_orders_per_hour
    rule = db.query(ThrottleRuleModel).filter(ThrottleRuleModel.active == True).order_by(ThrottleRuleModel.priority.desc()).first()
    max_orders = rule.max_orders_per_hour if rule else 60

    ts = _load_config(db, "enterprise_throttle", _DEFAULT_THROTTLE_STATUS)
    return ThrottleStatus(
        is_throttling=ts.get("is_throttling", False),
        current_orders_per_hour=ts.get("current_orders_per_hour", 0),
        max_orders_per_hour=max_orders,
        queue_length=0,
        estimated_wait_minutes=0,
        snoozed_until=ts.get("snoozed_until"),
    )


@router.get("/throttling/rules")
@limiter.limit("60/minute")
def get_throttle_rules(request: Request, db: DbSession, location_id: Optional[int] = None):
    """Get throttling rules."""
    rules = db.query(ThrottleRuleModel).limit(500).all()

    rule_list = [{
        "id": r.id,
        "name": r.name,
        "max_orders_per_hour": r.max_orders_per_hour,
        "max_items_per_order": r.max_items_per_order,
        "active": r.active,
        "priority": r.priority,
        "applies_to": r.applies_to,
    } for r in rules]

    return {"rules": rule_list}


@router.post("/throttling/rules")
@limiter.limit("30/minute")
@router.post("/throttling/rules/")
@limiter.limit("30/minute")
def create_throttle_rule(
    request: Request,
    db: DbSession,
    rule: ThrottleRuleCreate,
):
    """Create a new throttling rule."""
    new_rule = ThrottleRuleModel(
        name=rule.name,
        max_orders_per_hour=rule.max_orders_per_hour,
        max_items_per_order=rule.max_items_per_order,
        active=rule.active,
        priority=rule.priority,
        applies_to=rule.applies_to,
    )
    db.add(new_rule)
    db.commit()
    db.refresh(new_rule)

    return {
        "id": new_rule.id,
        "name": new_rule.name,
        "max_orders_per_hour": new_rule.max_orders_per_hour,
        "max_items_per_order": new_rule.max_items_per_order,
        "active": new_rule.active,
        "priority": new_rule.priority,
        "applies_to": new_rule.applies_to,
    }


@router.put("/throttling/rules/{rule_id}")
@limiter.limit("30/minute")
def update_throttle_rule(
    request: Request,
    db: DbSession,
    rule_id: int,
    rule: ThrottleRuleCreate,
):
    """Update a throttling rule."""
    existing = db.query(ThrottleRuleModel).filter(ThrottleRuleModel.id == rule_id).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Rule not found")

    existing.name = rule.name
    existing.max_orders_per_hour = rule.max_orders_per_hour
    existing.max_items_per_order = rule.max_items_per_order
    existing.active = rule.active
    existing.priority = rule.priority
    existing.applies_to = rule.applies_to
    db.commit()

    return {
        "id": existing.id,
        "name": existing.name,
        "max_orders_per_hour": existing.max_orders_per_hour,
        "max_items_per_order": existing.max_items_per_order,
        "active": existing.active,
        "priority": existing.priority,
        "applies_to": existing.applies_to,
    }


@router.delete("/throttling/rules/{rule_id}")
@limiter.limit("30/minute")
def delete_throttle_rule(request: Request, db: DbSession, rule_id: int):
    """Delete a throttling rule."""
    rule = db.query(ThrottleRuleModel).filter(ThrottleRuleModel.id == rule_id).first()
    if rule:
        db.delete(rule)
        db.commit()
    return {"status": "deleted"}


@router.post("/throttling/snooze")
@limiter.limit("30/minute")
def snooze_throttling(
    request: Request,
    db: DbSession,
    minutes: int = 30,
):
    """Temporarily disable throttling."""
    ts = _load_config(db, "enterprise_throttle", _DEFAULT_THROTTLE_STATUS)
    snoozed_until = (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()
    ts["snoozed_until"] = snoozed_until
    ts["is_throttling"] = False
    _save_config(db, "enterprise_throttle", ts, "Throttle Status")
    return {"status": "snoozed", "until": snoozed_until}


@router.post("/throttling/resume")
@limiter.limit("30/minute")
def resume_throttling(request: Request, db: DbSession):
    """Resume throttling after snooze."""
    ts = _load_config(db, "enterprise_throttle", _DEFAULT_THROTTLE_STATUS)
    ts["snoozed_until"] = None
    _save_config(db, "enterprise_throttle", ts, "Throttle Status")
    return {"status": "resumed"}



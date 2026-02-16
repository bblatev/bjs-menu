"""Enterprise feature routes - integrations, throttling, hotel PMS, offline, mobile app, invoice OCR - using database."""

from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request
from pydantic import BaseModel
from enum import Enum

from app.core.file_utils import sanitize_filename
from app.core.rate_limit import limiter
from app.db.session import DbSession
from app.models.hardware import (
    Integration as IntegrationModel,
    ThrottleRule as ThrottleRuleModel,
    HotelGuest as HotelGuestModel,
    OfflineQueueItem as OfflineQueueModel,
    OCRJob as OCRJobModel,
)

router = APIRouter()


# ==================== SCHEMAS ====================

class IntegrationStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    PENDING = "pending"
    ERROR = "error"


class Integration(BaseModel):
    id: str
    name: str
    category: str
    description: str
    status: IntegrationStatus = IntegrationStatus.DISCONNECTED
    icon: Optional[str] = None
    connected_at: Optional[datetime] = None
    config: Optional[dict] = None


class IntegrationConnection(BaseModel):
    integration_id: str
    api_key: Optional[str] = None
    credentials: Optional[dict] = None


class ThrottleRule(BaseModel):
    id: int
    name: str
    max_orders_per_hour: int
    max_items_per_order: int
    active: bool = True
    priority: int = 0
    applies_to: str = "all"  # all, dine-in, delivery, takeout


class ThrottleRuleCreate(BaseModel):
    name: str
    max_orders_per_hour: int = 50
    max_items_per_order: int = 20
    active: bool = True
    priority: int = 0
    applies_to: str = "all"


class ThrottleStatus(BaseModel):
    is_throttling: bool
    current_orders_per_hour: int
    max_orders_per_hour: int
    queue_length: int
    estimated_wait_minutes: int
    snoozed_until: Optional[datetime] = None


class HotelConnection(BaseModel):
    id: int
    hotel_name: str
    pms_type: str  # opera, protel, mews, etc.
    status: IntegrationStatus
    api_endpoint: Optional[str] = None
    last_sync: Optional[datetime] = None


class HotelGuest(BaseModel):
    id: int
    room_number: str
    guest_name: str
    check_in: datetime
    check_out: datetime
    vip_status: Optional[str] = None
    preferences: Optional[dict] = None


class HotelCharge(BaseModel):
    guest_id: int
    room_number: str
    amount: float
    description: str
    order_id: Optional[int] = None


class OfflineStatus(BaseModel):
    is_online: bool
    last_sync: Optional[datetime] = None
    pending_sync_count: int
    sync_queue_size: int
    offline_since: Optional[datetime] = None


class SyncQueueItem(BaseModel):
    id: int
    type: str  # order, payment, inventory, etc.
    data: dict
    created_at: datetime
    retry_count: int = 0
    status: str = "pending"


class MobileAppConfig(BaseModel):
    app_name: str
    bundle_id: str
    version: str
    features_enabled: List[str]
    theme_colors: dict
    logo_url: Optional[str] = None


class MobileAppBuild(BaseModel):
    build_id: str
    platform: str  # ios, android
    version: str
    status: str  # building, ready, failed
    download_url: Optional[str] = None
    created_at: datetime


class OCRJob(BaseModel):
    id: int
    filename: str
    status: str  # pending, processing, completed, failed
    created_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[dict] = None
    confidence: Optional[float] = None


# ==================== INTEGRATION MARKETPLACE (static data) ====================

INTEGRATIONS_MARKETPLACE = [
    {"id": "quickbooks", "name": "QuickBooks", "category": "accounting", "description": "Sync sales and expenses with QuickBooks", "icon": "quickbooks"},
    {"id": "xero", "name": "Xero", "category": "accounting", "description": "Accounting integration with Xero", "icon": "xero"},
    {"id": "square", "name": "Square POS", "category": "pos", "description": "Import sales from Square", "icon": "square"},
    {"id": "toast", "name": "Toast POS", "category": "pos", "description": "Sync with Toast POS system", "icon": "toast"},
    {"id": "doordash", "name": "DoorDash", "category": "delivery", "description": "Manage DoorDash orders", "icon": "doordash"},
    {"id": "ubereats", "name": "Uber Eats", "category": "delivery", "description": "Manage Uber Eats orders", "icon": "ubereats"},
    {"id": "grubhub", "name": "Grubhub", "category": "delivery", "description": "Manage Grubhub orders", "icon": "grubhub"},
    {"id": "mailchimp", "name": "Mailchimp", "category": "marketing", "description": "Email marketing campaigns", "icon": "mailchimp"},
    {"id": "twilio", "name": "Twilio", "category": "communications", "description": "SMS notifications", "icon": "twilio"},
    {"id": "stripe", "name": "Stripe", "category": "payments", "description": "Payment processing", "icon": "stripe"},
]

_DEFAULT_MOBILE_CONFIG = {
    "app_name": "",
    "bundle_id": "",
    "version": "",
    "features_enabled": ["ordering", "loyalty", "reservations"],
    "theme_colors": {"primary": "", "secondary": ""},
}

_DEFAULT_THROTTLE_STATUS = {
    "is_throttling": False,
    "current_orders_per_hour": 0,
    "snoozed_until": None,
}


def _load_config(db, store_id: str, defaults: dict) -> dict:
    """Load a config dict from the integrations table."""
    from app.models.hardware import Integration
    rec = db.query(Integration).filter(Integration.integration_id == store_id).first()
    if rec and rec.config and isinstance(rec.config, dict):
        return rec.config
    return defaults.copy()


def _save_config(db, store_id: str, data: dict, name: str = ""):
    """Save a config dict to the integrations table."""
    from app.models.hardware import Integration
    rec = db.query(Integration).filter(Integration.integration_id == store_id).first()
    if not rec:
        rec = Integration(
            integration_id=store_id, name=name or store_id,
            category="enterprise", status="active", config=data,
        )
        db.add(rec)
    else:
        rec.config = data
    db.commit()


# ==================== MULTI-LOCATION ====================

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
    locations = db.query(Location).all()
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

    locations = db.query(Location).all()

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
    connected = db.query(IntegrationModel).filter(IntegrationModel.status == "connected").all()
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
    connected = db.query(IntegrationModel).filter(IntegrationModel.status == "connected").all()

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
    rules = db.query(ThrottleRuleModel).all()

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


# ==================== HOTEL PMS ====================

@router.get("/hotel-pms/connection")
@limiter.limit("60/minute")
def get_hotel_connection(request: Request, db: DbSession):
    """Get hotel PMS connection status."""
    # Check if we have a hotel-pms integration connected
    integration = db.query(IntegrationModel).filter(
        IntegrationModel.category == "hotel-pms",
        IntegrationModel.status == "connected"
    ).first()

    if not integration:
        return {"connected": False, "connection": None}

    return {"connected": True, "connection": {
        "id": integration.id,
        "hotel_name": integration.name,
        "pms_type": integration.config.get("pms_type") if integration.config else "unknown",
        "status": "connected",
        "api_endpoint": integration.config.get("api_endpoint") if integration.config else None,
        "connected_at": integration.connected_at.isoformat() if integration.connected_at else None,
    }}


@router.post("/hotel-pms/connect")
@limiter.limit("30/minute")
def connect_hotel_pms(
    request: Request,
    db: DbSession,
    hotel_name: str,
    pms_type: str,
    api_endpoint: Optional[str] = None,
    api_key: Optional[str] = None,
):
    """Connect to a hotel PMS system."""
    # Check if already connected
    existing = db.query(IntegrationModel).filter(IntegrationModel.category == "hotel-pms").first()

    if existing:
        existing.name = hotel_name
        existing.status = "connected"
        existing.connected_at = datetime.now(timezone.utc)
        existing.config = {
            "pms_type": pms_type,
            "api_endpoint": api_endpoint,
            "api_key": api_key,
        }
    else:
        new_integration = IntegrationModel(
            integration_id=f"hotel-pms-{pms_type}",
            name=hotel_name,
            category="hotel-pms",
            description=f"{pms_type.upper()} Hotel PMS Integration",
            status="connected",
            connected_at=datetime.now(timezone.utc),
            config={
                "pms_type": pms_type,
                "api_endpoint": api_endpoint,
                "api_key": api_key,
            },
        )
        db.add(new_integration)

    db.commit()

    return {"status": "connected", "connection": {
        "hotel_name": hotel_name,
        "pms_type": pms_type,
        "api_endpoint": api_endpoint,
    }}


@router.post("/hotel-pms/disconnect")
@limiter.limit("30/minute")
def disconnect_hotel_pms(request: Request, db: DbSession):
    """Disconnect from hotel PMS."""
    integration = db.query(IntegrationModel).filter(IntegrationModel.category == "hotel-pms").first()
    if integration:
        integration.status = "disconnected"
        integration.connected_at = None
        db.commit()
    return {"status": "disconnected"}


@router.get("/hotel-pms/guests")
@limiter.limit("60/minute")
def get_hotel_guests(
    request: Request,
    db: DbSession,
    room_number: Optional[str] = None,
    vip_only: bool = False,
):
    """Get hotel guests."""
    query = db.query(HotelGuestModel)
    if room_number:
        query = query.filter(HotelGuestModel.room_number == room_number)
    if vip_only:
        query = query.filter(HotelGuestModel.vip_status.isnot(None))

    guests = query.all()

    guest_list = [{
        "id": g.id,
        "room_number": g.room_number,
        "guest_name": g.guest_name,
        "check_in": g.check_in.isoformat() if g.check_in else None,
        "check_out": g.check_out.isoformat() if g.check_out else None,
        "vip_status": g.vip_status,
        "preferences": g.preferences,
    } for g in guests]

    return {"guests": guest_list, "total": len(guest_list)}


@router.post("/hotel-pms/sync-guests")
@limiter.limit("30/minute")
def sync_hotel_guests(request: Request, db: DbSession):
    """Sync guests from hotel PMS.

    In production, this would call the actual PMS API to fetch current guests.
    Currently returns the existing guest count since no PMS is connected.
    """
    integration = db.query(IntegrationModel).filter(IntegrationModel.category == "hotel-pms").first()

    if not integration or not integration.config or not integration.config.get("connected"):
        raise HTTPException(status_code=400, detail="Hotel PMS not connected. Configure PMS integration first.")

    # Update last sync timestamp
    integration.config = {**integration.config, "last_sync": datetime.now(timezone.utc).isoformat()}
    db.commit()

    guest_count = db.query(HotelGuestModel).count()
    return {"status": "synced", "guests_count": guest_count}


@router.get("/hotel-pms/charges")
@limiter.limit("60/minute")
def get_hotel_charges(request: Request, db: DbSession):
    """Get recent hotel room charges from guest orders linked to rooms."""
    from app.models.restaurant import GuestOrder
    # Find guest orders linked to hotel rooms (table_token starts with 'room-' convention)
    orders = db.query(GuestOrder).filter(
        GuestOrder.table_token.like("room-%"),
    ).order_by(GuestOrder.id.desc()).limit(50).all()
    charges = []
    for o in orders:
        room_number = o.table_token.replace("room-", "") if o.table_token else ""
        charges.append({
            "id": o.id,
            "room_number": room_number,
            "amount": float(o.total or 0),
            "description": f"Restaurant order #{o.id}",
            "order_id": o.id,
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "status": str(o.status) if o.status else "unknown",
        })
    return charges


@router.post("/hotel-pms/charges")
@limiter.limit("30/minute")
def post_hotel_charge(
    request: Request,
    db: DbSession,
    charge: HotelCharge,
):
    """Post a charge to a hotel guest's room.

    Persists the charge as a GuestOrder linked to the room (using room-{number}
    table_token convention) so it appears in GET /hotel-pms/charges.
    In production with a connected PMS, would also forward to the PMS API.
    """
    from decimal import Decimal as D
    from app.models.restaurant import GuestOrder

    guest = db.query(HotelGuestModel).filter(HotelGuestModel.id == charge.guest_id).first()
    if not guest:
        raise HTTPException(status_code=404, detail="Guest not found")

    # Persist as a GuestOrder with room-based table_token so GET /hotel-pms/charges picks it up
    order = GuestOrder(
        table_token=f"room-{charge.room_number}",
        table_number=charge.room_number,
        status="served",
        order_type="dine-in",
        subtotal=D(str(charge.amount)),
        total=D(str(charge.amount)),
        customer_name=guest.guest_name,
        notes=charge.description,
        payment_status="paid",
        payment_method="room_charge",
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    return {
        "status": "posted",
        "charge_id": order.id,
        "guest": guest.guest_name,
        "room": charge.room_number,
        "amount": charge.amount,
        "order_id": order.id,
    }


# ==================== OFFLINE MODE ====================

@router.get("/offline/connectivity")
@limiter.limit("60/minute")
def get_offline_status(request: Request, db: DbSession):
    """Get offline/online connectivity status."""
    pending_count = db.query(OfflineQueueModel).filter(OfflineQueueModel.status == "pending").count()

    return OfflineStatus(
        is_online=True,
        last_sync=datetime.now(timezone.utc),
        pending_sync_count=pending_count,
        sync_queue_size=pending_count,
        offline_since=None,
    )


@router.get("/offline/sync-queue")
@limiter.limit("60/minute")
def get_sync_queue(request: Request, db: DbSession):
    """Get pending sync queue items."""
    items = db.query(OfflineQueueModel).filter(OfflineQueueModel.status == "pending").all()

    item_list = [{
        "id": item.id,
        "type": item.item_type,
        "data": item.data,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "retry_count": item.retry_count,
        "status": item.status,
    } for item in items]

    return {"queue": item_list, "total": len(item_list)}


@router.post("/offline/sync")
@limiter.limit("30/minute")
def trigger_sync(request: Request, db: DbSession):
    """Trigger a sync of offline data."""
    pending_items = db.query(OfflineQueueModel).filter(OfflineQueueModel.status == "pending").all()
    synced_count = len(pending_items)

    # Mark all as synced
    for item in pending_items:
        item.status = "synced"

    db.commit()

    return {
        "status": "synced",
        "items_synced": synced_count,
        "synced_at": datetime.now(timezone.utc),
    }


@router.post("/offline/queue")
@limiter.limit("30/minute")
def add_to_sync_queue(
    request: Request,
    db: DbSession,
    item_type: str,
    data: dict,
):
    """Add an item to the offline sync queue."""
    new_item = OfflineQueueModel(
        item_type=item_type,
        data=data,
        status="pending",
        retry_count=0,
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)

    return {"status": "queued", "item": {
        "id": new_item.id,
        "type": new_item.item_type,
        "status": new_item.status,
        "created_at": new_item.created_at.isoformat() if new_item.created_at else None,
    }}


# ==================== MOBILE APP ====================

@router.get("/mobile-app")
@limiter.limit("60/minute")
def get_mobile_app_config(request: Request, db: DbSession):
    """Get mobile app configuration."""
    return _load_config(db, "enterprise_mobile_app", _DEFAULT_MOBILE_CONFIG)


@router.put("/mobile-app")
@limiter.limit("30/minute")
def update_mobile_app_config(
    request: Request,
    db: DbSession,
    config: MobileAppConfig,
):
    """Update mobile app configuration."""
    data = config.model_dump()
    _save_config(db, "enterprise_mobile_app", data, "Mobile App Config")
    return data


@router.post("/mobile-app/build")
@limiter.limit("30/minute")
def trigger_mobile_build(
    request: Request,
    db: DbSession,
    platform: str = "both",  # ios, android, both
):
    """Trigger a new mobile app build."""
    mc = _load_config(db, "enterprise_mobile_app", _DEFAULT_MOBILE_CONFIG)
    builds = []
    platforms = ["ios", "android"] if platform == "both" else [platform]

    for p in platforms:
        build = {
            "build_id": f"BUILD-{p.upper()}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "platform": p,
            "version": mc.get("version", "1.0.0"),
            "status": "building",
            "download_url": None,
            "created_at": datetime.now(timezone.utc),
        }
        builds.append(build)

    return {"status": "building", "builds": builds}


# ==================== INVOICE OCR ====================

@router.post("/invoice-ocr/upload")
@limiter.limit("30/minute")
async def upload_invoice_for_ocr(
    request: Request,
    db: DbSession,
    file: UploadFile = File(...),
):
    """Upload an invoice for OCR processing."""
    # Sanitize filename to prevent injection attacks
    safe_filename = sanitize_filename(file.filename) if file.filename else "unnamed"

    # Create OCR job
    job = OCRJobModel(
        filename=safe_filename,
        status="processing",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # OCR processing placeholder — actual OCR integration required
    # Job remains in "processing" status until an OCR service processes it
    db.commit()

    return {"status": "processing", "job": {
        "id": job.id,
        "filename": job.filename,
        "status": job.status,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "confidence": job.confidence,
        "result": job.result,
    }}


@router.get("/invoice-ocr/jobs")
@limiter.limit("60/minute")
def get_ocr_jobs(
    request: Request,
    db: DbSession,
    status: Optional[str] = None,
):
    """Get OCR processing jobs."""
    query = db.query(OCRJobModel)
    if status:
        query = query.filter(OCRJobModel.status == status)

    jobs = query.all()

    job_list = [{
        "id": job.id,
        "filename": job.filename,
        "status": job.status,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "confidence": job.confidence,
        "result": job.result,
    } for job in jobs]

    return {"jobs": job_list, "total": len(job_list)}


@router.get("/invoice-ocr/jobs/{job_id}")
@limiter.limit("60/minute")
def get_ocr_job(request: Request, db: DbSession, job_id: int):
    """Get a specific OCR job."""
    job = db.query(OCRJobModel).filter(OCRJobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "id": job.id,
        "filename": job.filename,
        "status": job.status,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "confidence": job.confidence,
        "result": job.result,
    }

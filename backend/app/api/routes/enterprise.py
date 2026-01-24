"""Enterprise feature routes - integrations, throttling, hotel PMS, offline, mobile app, invoice OCR."""

from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from enum import Enum

from app.db.session import DbSession

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


# ==================== IN-MEMORY STORAGE (will be replaced with DB) ====================

_integrations_marketplace = [
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

_connected_integrations = {}
_throttle_rules = [
    {"id": 1, "name": "Default", "max_orders_per_hour": 60, "max_items_per_order": 25, "active": True, "priority": 0, "applies_to": "all"},
]
_throttle_status = {
    "is_throttling": False,
    "current_orders_per_hour": 0,
    "snoozed_until": None,
}
_hotel_connection = None
_hotel_guests = []
_offline_queue = []
_ocr_jobs = []
_mobile_config = {
    "app_name": "BJ's Bar & Grill",
    "bundle_id": "com.bjsbar.app",
    "version": "1.0.0",
    "features_enabled": ["ordering", "loyalty", "reservations"],
    "theme_colors": {"primary": "#e68a00", "secondary": "#0066e6"},
}


# ==================== INTEGRATIONS ====================

@router.get("/integrations/marketplace")
def get_integrations_marketplace(
    db: DbSession,
    category: Optional[str] = None,
):
    """Get available integrations from marketplace."""
    integrations = _integrations_marketplace
    if category:
        integrations = [i for i in integrations if i["category"] == category]
    return {"integrations": integrations, "total": len(integrations)}


@router.get("/integrations/")
def list_integrations(db: DbSession):
    """List all available integrations with connection status."""
    result = []
    for integration in _integrations_marketplace:
        connected = _connected_integrations.get(integration["id"])
        result.append({
            **integration,
            "status": "connected" if connected else "disconnected",
            "connected_at": connected.get("connected_at") if connected else None,
        })
    return {"integrations": result}


@router.get("/integrations/connected")
def get_connected_integrations(db: DbSession):
    """Get only connected integrations."""
    result = []
    for int_id, conn_data in _connected_integrations.items():
        integration = next((i for i in _integrations_marketplace if i["id"] == int_id), None)
        if integration:
            result.append({**integration, "status": "connected", **conn_data})
    return {"integrations": result, "total": len(result)}


@router.post("/integrations/connections/")
def connect_integration(
    db: DbSession,
    connection: IntegrationConnection,
):
    """Connect to an integration."""
    integration = next((i for i in _integrations_marketplace if i["id"] == connection.integration_id), None)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    _connected_integrations[connection.integration_id] = {
        "connected_at": datetime.utcnow(),
        "config": connection.credentials or {},
    }

    return {"status": "connected", "integration_id": connection.integration_id}


@router.delete("/integrations/connections/{integration_id}")
def disconnect_integration(
    db: DbSession,
    integration_id: str,
):
    """Disconnect from an integration."""
    if integration_id in _connected_integrations:
        del _connected_integrations[integration_id]
    return {"status": "disconnected", "integration_id": integration_id}


# ==================== THROTTLING ====================

@router.get("/throttling/status")
def get_throttle_status(db: DbSession, location_id: Optional[int] = None):
    """Get current throttling status."""
    return ThrottleStatus(
        is_throttling=_throttle_status["is_throttling"],
        current_orders_per_hour=_throttle_status["current_orders_per_hour"],
        max_orders_per_hour=_throttle_rules[0]["max_orders_per_hour"] if _throttle_rules else 60,
        queue_length=0,
        estimated_wait_minutes=0,
        snoozed_until=_throttle_status.get("snoozed_until"),
    )


@router.get("/throttling/rules")
def get_throttle_rules(db: DbSession, location_id: Optional[int] = None):
    """Get throttling rules."""
    return {"rules": _throttle_rules}


@router.post("/throttling/rules/")
def create_throttle_rule(
    db: DbSession,
    rule: ThrottleRuleCreate,
):
    """Create a new throttling rule."""
    new_id = max(r["id"] for r in _throttle_rules) + 1 if _throttle_rules else 1
    new_rule = {
        "id": new_id,
        **rule.model_dump(),
    }
    _throttle_rules.append(new_rule)
    return new_rule


@router.put("/throttling/rules/{rule_id}")
def update_throttle_rule(
    db: DbSession,
    rule_id: int,
    rule: ThrottleRuleCreate,
):
    """Update a throttling rule."""
    for i, r in enumerate(_throttle_rules):
        if r["id"] == rule_id:
            _throttle_rules[i] = {"id": rule_id, **rule.model_dump()}
            return _throttle_rules[i]
    raise HTTPException(status_code=404, detail="Rule not found")


@router.delete("/throttling/rules/{rule_id}")
def delete_throttle_rule(db: DbSession, rule_id: int):
    """Delete a throttling rule."""
    global _throttle_rules
    _throttle_rules = [r for r in _throttle_rules if r["id"] != rule_id]
    return {"status": "deleted"}


@router.post("/throttling/snooze")
def snooze_throttling(
    db: DbSession,
    minutes: int = 30,
):
    """Temporarily disable throttling."""
    _throttle_status["snoozed_until"] = datetime.utcnow() + timedelta(minutes=minutes)
    _throttle_status["is_throttling"] = False
    return {"status": "snoozed", "until": _throttle_status["snoozed_until"]}


@router.post("/throttling/resume")
def resume_throttling(db: DbSession):
    """Resume throttling after snooze."""
    _throttle_status["snoozed_until"] = None
    return {"status": "resumed"}


# ==================== HOTEL PMS ====================

@router.get("/hotel-pms/connection")
def get_hotel_connection(db: DbSession):
    """Get hotel PMS connection status."""
    if not _hotel_connection:
        return {"connected": False, "connection": None}
    return {"connected": True, "connection": _hotel_connection}


@router.post("/hotel-pms/connect")
def connect_hotel_pms(
    db: DbSession,
    hotel_name: str,
    pms_type: str,
    api_endpoint: Optional[str] = None,
    api_key: Optional[str] = None,
):
    """Connect to a hotel PMS system."""
    global _hotel_connection
    _hotel_connection = {
        "id": 1,
        "hotel_name": hotel_name,
        "pms_type": pms_type,
        "status": "connected",
        "api_endpoint": api_endpoint,
        "connected_at": datetime.utcnow(),
        "last_sync": None,
    }
    return {"status": "connected", "connection": _hotel_connection}


@router.post("/hotel-pms/disconnect")
def disconnect_hotel_pms(db: DbSession):
    """Disconnect from hotel PMS."""
    global _hotel_connection
    _hotel_connection = None
    return {"status": "disconnected"}


@router.get("/hotel-pms/guests")
def get_hotel_guests(
    db: DbSession,
    room_number: Optional[str] = None,
    vip_only: bool = False,
):
    """Get hotel guests."""
    guests = _hotel_guests
    if room_number:
        guests = [g for g in guests if g["room_number"] == room_number]
    if vip_only:
        guests = [g for g in guests if g.get("vip_status")]
    return {"guests": guests, "total": len(guests)}


@router.post("/hotel-pms/sync-guests")
def sync_hotel_guests(db: DbSession):
    """Sync guests from hotel PMS."""
    global _hotel_guests
    # Simulate syncing guests
    _hotel_guests = [
        {"id": 1, "room_number": "101", "guest_name": "John Smith", "check_in": datetime.utcnow(), "check_out": datetime.utcnow() + timedelta(days=3), "vip_status": "gold"},
        {"id": 2, "room_number": "205", "guest_name": "Jane Doe", "check_in": datetime.utcnow(), "check_out": datetime.utcnow() + timedelta(days=2), "vip_status": None},
        {"id": 3, "room_number": "302", "guest_name": "Bob Wilson", "check_in": datetime.utcnow(), "check_out": datetime.utcnow() + timedelta(days=5), "vip_status": "platinum"},
    ]
    if _hotel_connection:
        _hotel_connection["last_sync"] = datetime.utcnow()
    return {"status": "synced", "guests_count": len(_hotel_guests)}


@router.post("/hotel-pms/charges")
def post_hotel_charge(
    db: DbSession,
    charge: HotelCharge,
):
    """Post a charge to a hotel guest's room."""
    guest = next((g for g in _hotel_guests if g["id"] == charge.guest_id), None)
    if not guest:
        raise HTTPException(status_code=404, detail="Guest not found")

    # In production, this would post to the PMS
    return {
        "status": "posted",
        "charge_id": f"CHG-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        "guest": guest["guest_name"],
        "room": charge.room_number,
        "amount": charge.amount,
    }


# ==================== OFFLINE MODE ====================

@router.get("/offline/connectivity")
def get_offline_status(db: DbSession):
    """Get offline/online connectivity status."""
    return OfflineStatus(
        is_online=True,
        last_sync=datetime.utcnow(),
        pending_sync_count=len(_offline_queue),
        sync_queue_size=len(_offline_queue),
        offline_since=None,
    )


@router.get("/offline/sync-queue")
def get_sync_queue(db: DbSession):
    """Get pending sync queue items."""
    return {"queue": _offline_queue, "total": len(_offline_queue)}


@router.post("/offline/sync")
def trigger_sync(db: DbSession):
    """Trigger a sync of offline data."""
    global _offline_queue
    synced_count = len(_offline_queue)
    _offline_queue = []  # Clear queue after sync
    return {
        "status": "synced",
        "items_synced": synced_count,
        "synced_at": datetime.utcnow(),
    }


@router.post("/offline/queue")
def add_to_sync_queue(
    db: DbSession,
    item_type: str,
    data: dict,
):
    """Add an item to the offline sync queue."""
    new_item = {
        "id": len(_offline_queue) + 1,
        "type": item_type,
        "data": data,
        "created_at": datetime.utcnow(),
        "retry_count": 0,
        "status": "pending",
    }
    _offline_queue.append(new_item)
    return {"status": "queued", "item": new_item}


# ==================== MOBILE APP ====================

@router.get("/mobile-app")
def get_mobile_app_config(db: DbSession):
    """Get mobile app configuration."""
    return _mobile_config


@router.put("/mobile-app")
def update_mobile_app_config(
    db: DbSession,
    config: MobileAppConfig,
):
    """Update mobile app configuration."""
    global _mobile_config
    _mobile_config = config.model_dump()
    return _mobile_config


@router.post("/mobile-app/build")
def trigger_mobile_build(
    db: DbSession,
    platform: str = "both",  # ios, android, both
):
    """Trigger a new mobile app build."""
    builds = []
    platforms = ["ios", "android"] if platform == "both" else [platform]

    for p in platforms:
        build = {
            "build_id": f"BUILD-{p.upper()}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "platform": p,
            "version": _mobile_config["version"],
            "status": "building",
            "download_url": None,
            "created_at": datetime.utcnow(),
        }
        builds.append(build)

    return {"status": "building", "builds": builds}


# ==================== INVOICE OCR ====================

@router.post("/invoice-ocr/upload")
async def upload_invoice_for_ocr(
    db: DbSession,
    file: UploadFile = File(...),
):
    """Upload an invoice for OCR processing."""
    # Create OCR job
    job = {
        "id": len(_ocr_jobs) + 1,
        "filename": file.filename,
        "status": "processing",
        "created_at": datetime.utcnow(),
        "completed_at": None,
        "result": None,
        "confidence": None,
    }
    _ocr_jobs.append(job)

    # Simulate OCR processing (in production, would use actual OCR)
    job["status"] = "completed"
    job["completed_at"] = datetime.utcnow()
    job["confidence"] = 0.92
    job["result"] = {
        "vendor": "Sample Supplier",
        "invoice_number": f"INV-{datetime.utcnow().strftime('%Y%m%d')}",
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "total": 1250.00,
        "items": [
            {"description": "Beer - Case", "quantity": 10, "unit_price": 45.00, "total": 450.00},
            {"description": "Wine - Red", "quantity": 5, "unit_price": 80.00, "total": 400.00},
            {"description": "Spirits - Vodka", "quantity": 4, "unit_price": 100.00, "total": 400.00},
        ],
    }

    return {"status": "processing", "job": job}


@router.get("/invoice-ocr/jobs")
def get_ocr_jobs(
    db: DbSession,
    status: Optional[str] = None,
):
    """Get OCR processing jobs."""
    jobs = _ocr_jobs
    if status:
        jobs = [j for j in jobs if j["status"] == status]
    return {"jobs": jobs, "total": len(jobs)}


@router.get("/invoice-ocr/jobs/{job_id}")
def get_ocr_job(db: DbSession, job_id: int):
    """Get a specific OCR job."""
    job = next((j for j in _ocr_jobs if j["id"] == job_id), None)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

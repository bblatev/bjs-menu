"""Enterprise feature routes - integrations, throttling, hotel PMS, offline, mobile app, invoice OCR - using database."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from enum import Enum

from app.core.file_utils import sanitize_filename
from app.core.rate_limit import limiter
from app.db.session import DbSession, get_db
from app.core.rbac import get_current_user
from app.models import StaffUser
from app.models.hardware import (
    Integration as IntegrationModel,
    ThrottleRule as ThrottleRuleModel,
    HotelGuest as HotelGuestModel,
    OfflineQueueItem as OfflineQueueModel,
    OCRJob as OCRJobModel,
)



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


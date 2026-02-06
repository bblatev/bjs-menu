"""Settings API routes."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.db.session import DbSession
from app.models.operations import AppSetting

router = APIRouter()


# --------------- Pydantic schemas (unchanged) ---------------


class VenueSettings(BaseModel):
    name: str
    address: str
    phone: str
    email: str
    timezone: str
    currency: str
    tax_rate: float
    service_charge: Optional[float] = None
    logo_url: Optional[str] = None


class PaymentSettings(BaseModel):
    cash_enabled: bool = True
    card_enabled: bool = True
    contactless_enabled: bool = True
    tips_enabled: bool = True
    default_tip_percentages: List[int] = [10, 15, 20]
    auto_gratuity_threshold: int = 6
    auto_gratuity_percentage: float = 18.0


class SecuritySettings(BaseModel):
    session_timeout_minutes: int
    require_pin_for_voids: bool
    require_manager_approval_threshold: float
    two_factor_enabled: bool
    password_expiry_days: int


class GeneralSettings(BaseModel):
    language: str
    date_format: str
    time_format: str
    first_day_of_week: str
    auto_logout_minutes: int


class FiscalSettings(BaseModel):
    fiscal_enabled: bool
    fiscal_device_id: Optional[str] = None
    tax_number: str
    company_name: str
    company_address: str


# --------------- helper utilities ---------------


def _get_setting_value(db: DbSession, category: str, key: str = "default") -> Any:
    """Return the JSON value for a category+key, or None if not found."""
    row = (
        db.query(AppSetting)
        .filter(AppSetting.category == category, AppSetting.key == key)
        .first()
    )
    return row.value if row else None


def _upsert_setting(db: DbSession, category: str, value: Any, key: str = "default") -> AppSetting:
    """Insert or update a setting row and commit."""
    row = (
        db.query(AppSetting)
        .filter(AppSetting.category == category, AppSetting.key == key)
        .first()
    )
    if row:
        row.value = value
        row.updated_at = datetime.utcnow()
    else:
        row = AppSetting(category=category, key=key, value=value)
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _get_all_for_category(db: DbSession, category: str) -> Dict[str, Any]:
    """Return a merged dict of all key->value pairs in a category."""
    rows = db.query(AppSetting).filter(AppSetting.category == category).all()
    result: Dict[str, Any] = {}
    for row in rows:
        if row.key == "default" and isinstance(row.value, dict):
            result.update(row.value)
        else:
            result[row.key] = row.value
    return result


# --------------- endpoints ---------------


@router.get("/")
async def get_all_settings(db: DbSession):
    """Get all settings as a combined object."""
    general = _get_all_for_category(db, "general") or {
        "restaurant_name": "BJ's Bar & Grill",
        "language": "bg",
        "currency": "BGN",
        "timezone": "Europe/Sofia",
    }
    security = _get_all_for_category(db, "security") or {
        "require_pin": True,
        "session_timeout": 30,
        "max_login_attempts": 5,
        "two_factor_enabled": False,
        "ip_whitelist_enabled": False,
        "password_min_length": 8,
        "force_password_change_days": 90,
    }
    notifications = _get_all_for_category(db, "notifications") or {
        "email_enabled": True,
        "sms_enabled": False,
        "push_enabled": True,
    }
    return {
        "settings": {
            "general": general,
            "security": security,
            "notifications": notifications,
        }
    }


@router.put("/")
async def update_all_settings(data: dict, db: DbSession):
    """Update settings."""
    for category, values in data.items():
        if isinstance(values, dict):
            _upsert_setting(db, category, values, key="default")
    return {"success": True, "settings": data}


@router.get("/tax/")
async def get_tax_settings(db: DbSession):
    """Get tax settings."""
    stored = _get_setting_value(db, "tax")
    if stored and isinstance(stored, dict):
        return stored
    return {"tax_rates": [], "default_rate": 0}


@router.get("/venue")
async def get_venue_settings(db: DbSession):
    """Get venue settings."""
    stored = _get_setting_value(db, "venue")
    if stored and isinstance(stored, dict):
        return VenueSettings(**stored)
    return VenueSettings(
        name="BJ's Bar & Grill",
        address="123 Main Street, Sofia",
        phone="+359 888 123 456",
        email="info@bjsbar.com",
        timezone="Europe/Sofia",
        currency="BGN",
        tax_rate=20.0,
        service_charge=10.0,
    )


@router.put("/venue")
async def update_venue_settings(settings: VenueSettings, db: DbSession):
    """Update venue settings."""
    _upsert_setting(db, "venue", settings.model_dump())
    return {"success": True}


@router.get("/payment")
async def get_payment_settings(db: DbSession):
    """Get payment settings."""
    stored = _get_setting_value(db, "payment")
    if stored and isinstance(stored, dict):
        return PaymentSettings(**stored)
    return PaymentSettings(
        cash_enabled=True,
        card_enabled=True,
        contactless_enabled=True,
        tips_enabled=True,
        default_tip_percentages=[10, 15, 20],
        auto_gratuity_threshold=6,
        auto_gratuity_percentage=18.0,
    )


@router.put("/payment")
async def update_payment_settings(settings: PaymentSettings, db: DbSession):
    """Update payment settings."""
    _upsert_setting(db, "payment", settings.model_dump())
    return {"success": True}


@router.get("/security")
async def get_security_settings(db: DbSession):
    """Get security settings."""
    stored = _get_setting_value(db, "security")
    if stored and isinstance(stored, dict):
        try:
            return SecuritySettings(**stored)
        except Exception:
            pass
    return SecuritySettings(
        session_timeout_minutes=30,
        require_pin_for_voids=True,
        require_manager_approval_threshold=100.0,
        two_factor_enabled=False,
        password_expiry_days=90,
    )


@router.put("/security")
async def update_security_settings(settings: SecuritySettings, db: DbSession):
    """Update security settings."""
    _upsert_setting(db, "security", settings.model_dump())
    return {"success": True}


@router.get("/general")
async def get_general_settings(db: DbSession):
    """Get general settings."""
    stored = _get_setting_value(db, "general")
    if stored and isinstance(stored, dict):
        try:
            return GeneralSettings(**stored)
        except Exception:
            pass
    return GeneralSettings(
        language="en",
        date_format="DD/MM/YYYY",
        time_format="24h",
        first_day_of_week="Monday",
        auto_logout_minutes=15,
    )


@router.put("/general")
async def update_general_settings(settings: GeneralSettings, db: DbSession):
    """Update general settings."""
    _upsert_setting(db, "general", settings.model_dump())
    return {"success": True}


@router.get("/fiscal")
async def get_fiscal_settings(db: DbSession):
    """Get fiscal settings."""
    stored = _get_setting_value(db, "fiscal")
    if stored and isinstance(stored, dict):
        return FiscalSettings(**stored)
    return FiscalSettings(
        fiscal_enabled=True,
        fiscal_device_id="FP-001",
        tax_number="BG123456789",
        company_name="BJ's Bar Ltd",
        company_address="123 Main Street, Sofia, Bulgaria",
    )


@router.put("/fiscal")
async def update_fiscal_settings(settings: FiscalSettings, db: DbSession):
    """Update fiscal settings."""
    _upsert_setting(db, "fiscal", settings.model_dump())
    return {"success": True}

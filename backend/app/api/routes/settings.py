"""Settings API routes."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.db.session import DbSession
from app.models.operations import AppSetting
from app.core.rate_limit import limiter

router = APIRouter()

from app.core.rbac import CurrentUser, RequireManager



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
        row.updated_at = datetime.now(timezone.utc)
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
@limiter.limit("60/minute")
async def get_all_settings(request: Request, db: DbSession, current_user: CurrentUser):
    """Get all settings as a combined object."""
    general = _get_all_for_category(db, "general") or {
        "restaurant_name": "",
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
@limiter.limit("30/minute")
async def update_all_settings(request: Request, data: dict, db: DbSession, current_user: RequireManager):
    """Update settings."""
    for category, values in data.items():
        if isinstance(values, dict):
            _upsert_setting(db, category, values, key="default")
    return {"success": True, "settings": data}


@router.get("/tax/")
@limiter.limit("60/minute")
async def get_tax_settings(request: Request, db: DbSession, current_user: CurrentUser):
    """Get tax settings."""
    stored = _get_setting_value(db, "tax")
    if stored and isinstance(stored, dict):
        return stored
    return {"tax_rates": [], "default_rate": 0}


@router.get("/venue")
@limiter.limit("60/minute")
async def get_venue_settings(request: Request, db: DbSession, current_user: CurrentUser):
    """Get venue settings."""
    stored = _get_setting_value(db, "venue")
    if stored and isinstance(stored, dict):
        return VenueSettings(**stored)
    return VenueSettings(
        name="",
        address="",
        phone="",
        email="",
        timezone="Europe/Sofia",
        currency="BGN",
        tax_rate=20.0,
        service_charge=0,
    )


@router.put("/venue")
@limiter.limit("30/minute")
async def update_venue_settings(request: Request, settings: VenueSettings, db: DbSession, current_user: RequireManager):
    """Update venue settings."""
    _upsert_setting(db, "venue", settings.model_dump())
    return {"success": True}


@router.get("/payment")
@limiter.limit("60/minute")
async def get_payment_settings(request: Request, db: DbSession, current_user: CurrentUser):
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
@limiter.limit("30/minute")
async def update_payment_settings(request: Request, settings: PaymentSettings, db: DbSession, current_user: RequireManager):
    """Update payment settings."""
    _upsert_setting(db, "payment", settings.model_dump())
    return {"success": True}


@router.get("/security")
@limiter.limit("60/minute")
async def get_security_settings(request: Request, db: DbSession, current_user: RequireManager):
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
@limiter.limit("30/minute")
async def update_security_settings(request: Request, settings: SecuritySettings, db: DbSession, current_user: RequireManager):
    """Update security settings."""
    _upsert_setting(db, "security", settings.model_dump())
    return {"success": True}


@router.get("/general")
@limiter.limit("60/minute")
async def get_general_settings(request: Request, db: DbSession, current_user: CurrentUser):
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
@limiter.limit("30/minute")
async def update_general_settings(request: Request, settings: GeneralSettings, db: DbSession, current_user: RequireManager):
    """Update general settings."""
    _upsert_setting(db, "general", settings.model_dump())
    return {"success": True}


@router.get("/fiscal")
@limiter.limit("60/minute")
async def get_fiscal_settings(request: Request, db: DbSession, current_user: CurrentUser):
    """Get fiscal settings."""
    stored = _get_setting_value(db, "fiscal")
    if stored and isinstance(stored, dict):
        return FiscalSettings(**stored)
    return FiscalSettings(
        fiscal_enabled=False,
        fiscal_device_id=None,
        tax_number="",
        company_name="",
        company_address="",
    )


@router.put("/fiscal")
@limiter.limit("30/minute")
async def update_fiscal_settings(request: Request, settings: FiscalSettings, db: DbSession, current_user: RequireManager):
    """Update fiscal settings."""
    _upsert_setting(db, "fiscal", settings.model_dump())
    return {"success": True}

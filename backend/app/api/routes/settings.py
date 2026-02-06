"""Settings API routes."""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


@router.get("/tax/")
async def get_tax_settings():
    """Get tax settings."""
    return {"tax_rates": [], "default_rate": 0}


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
    cash_enabled: bool
    card_enabled: bool
    contactless_enabled: bool
    tips_enabled: bool
    default_tip_percentages: List[int]
    auto_gratuity_threshold: int
    auto_gratuity_percentage: float


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


@router.get("/venue")
async def get_venue_settings():
    """Get venue settings."""
    return VenueSettings(
        name="BJ's Bar & Grill",
        address="123 Main Street, Sofia",
        phone="+359 888 123 456",
        email="info@bjsbar.com",
        timezone="Europe/Sofia",
        currency="BGN",
        tax_rate=20.0,
        service_charge=10.0
    )


@router.put("/venue")
async def update_venue_settings(settings: VenueSettings):
    """Update venue settings."""
    return {"success": True}


@router.get("/payment")
async def get_payment_settings():
    """Get payment settings."""
    return PaymentSettings(
        cash_enabled=True,
        card_enabled=True,
        contactless_enabled=True,
        tips_enabled=True,
        default_tip_percentages=[10, 15, 20],
        auto_gratuity_threshold=6,
        auto_gratuity_percentage=18.0
    )


@router.put("/payment")
async def update_payment_settings(settings: PaymentSettings):
    """Update payment settings."""
    return {"success": True}


@router.get("/security")
async def get_security_settings():
    """Get security settings."""
    return SecuritySettings(
        session_timeout_minutes=30,
        require_pin_for_voids=True,
        require_manager_approval_threshold=100.0,
        two_factor_enabled=False,
        password_expiry_days=90
    )


@router.put("/security")
async def update_security_settings(settings: SecuritySettings):
    """Update security settings."""
    return {"success": True}


@router.get("/general")
async def get_general_settings():
    """Get general settings."""
    return GeneralSettings(
        language="en",
        date_format="DD/MM/YYYY",
        time_format="24h",
        first_day_of_week="Monday",
        auto_logout_minutes=15
    )


@router.put("/general")
async def update_general_settings(settings: GeneralSettings):
    """Update general settings."""
    return {"success": True}


@router.get("/fiscal")
async def get_fiscal_settings():
    """Get fiscal settings."""
    return FiscalSettings(
        fiscal_enabled=True,
        fiscal_device_id="FP-001",
        tax_number="BG123456789",
        company_name="BJ's Bar Ltd",
        company_address="123 Main Street, Sofia, Bulgaria"
    )


@router.put("/fiscal")
async def update_fiscal_settings(settings: FiscalSettings):
    """Update fiscal settings."""
    return {"success": True}

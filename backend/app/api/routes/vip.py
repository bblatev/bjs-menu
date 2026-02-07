"""VIP customer management API routes."""

from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc

from app.db.session import DbSession
from app.models.operations import (
    VIPCustomerLink,
    VIPOccasion as VIPOccasionModel,
    AppSetting,
)

router = APIRouter()


@router.get("/tiers")
async def get_vip_tiers(db: DbSession):
    """Get VIP tier definitions."""
    setting = db.query(AppSetting).filter(
        AppSetting.category == "vip",
        AppSetting.key == "tiers",
    ).first()
    if setting and isinstance(setting.value, list):
        return {"tiers": setting.value}
    return {"tiers": []}


class VIPCustomer(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    tier: str  # silver, gold, platinum, diamond
    total_spent: float
    visits: int
    avg_spend: float
    preferences: List[str]
    notes: Optional[str] = None
    last_visit: str


class VIPOccasion(BaseModel):
    id: str
    customer_id: str
    customer_name: str
    occasion_type: str  # birthday, anniversary, special
    date: str
    notes: Optional[str] = None
    reminder_sent: bool = False


class VIPSettings(BaseModel):
    auto_upgrade_threshold: float
    birthday_discount_pct: int
    anniversary_discount_pct: int
    min_spend_for_vip: float
    points_multiplier: float


class TierChange(BaseModel):
    id: str
    customer_name: str
    from_tier: str
    to_tier: str
    reason: str
    date: str


class VIPCustomerCreate(BaseModel):
    venue_id: int
    customer_id: int
    tier: str  # silver, gold, platinum, diamond
    notes: Optional[str] = None
    preferences: List[str] = []


def _customer_to_schema(c: VIPCustomerLink) -> VIPCustomer:
    """Convert a VIPCustomerLink model instance to VIPCustomer schema."""
    total_spent = float(c.total_spent or 0)
    visits = c.visits or 0
    avg_spend = round(total_spent / visits, 2) if visits > 0 else 0.0
    last_visit = ""
    if c.joined_at:
        last_visit = c.joined_at.strftime("%Y-%m-%d")
    return VIPCustomer(
        id=str(c.id),
        name=c.name or "",
        email=c.email or "",
        phone=c.phone or "",
        tier=c.tier or "silver",
        total_spent=total_spent,
        visits=visits,
        avg_spend=avg_spend,
        preferences=[],
        notes=c.notes,
        last_visit=last_visit,
    )


def _occasion_to_schema(o: VIPOccasionModel) -> VIPOccasion:
    """Convert a VIPOccasionModel instance to VIPOccasion schema."""
    occasion_date = ""
    if o.occasion_date:
        occasion_date = o.occasion_date.isoformat()
    return VIPOccasion(
        id=str(o.id),
        customer_id=str(o.customer_id or ""),
        customer_name=o.customer_name or "",
        occasion_type=o.type or "",
        date=occasion_date,
        notes=o.notes,
        reminder_sent=o.notification_sent or False,
    )


@router.get("/customers")
async def get_vip_customers(db: DbSession):
    """Get all VIP customers."""
    customers = db.query(VIPCustomerLink).order_by(desc(VIPCustomerLink.total_spent)).all()
    return [_customer_to_schema(c) for c in customers]


@router.post("/customers")
async def create_vip_customer(data: VIPCustomerCreate, db: DbSession):
    """Add a customer to VIP program."""
    new_customer = VIPCustomerLink(
        customer_id=data.customer_id,
        name=f"Customer {data.customer_id}",
        tier=data.tier,
        notes=data.notes,
        points=0,
        total_spent=0,
        visits=0,
    )
    db.add(new_customer)
    db.commit()
    db.refresh(new_customer)
    return {
        "success": True,
        "id": str(new_customer.id),
        "customer_id": new_customer.customer_id,
        "tier": new_customer.tier,
        "message": f"Customer {new_customer.customer_id} added to VIP program as {new_customer.tier}",
    }


@router.get("/occasions")
async def get_vip_occasions(db: DbSession):
    """Get upcoming VIP occasions."""
    occasions = (
        db.query(VIPOccasionModel)
        .order_by(VIPOccasionModel.occasion_date)
        .all()
    )
    return [_occasion_to_schema(o) for o in occasions]


@router.get("/occasions/{occasion_id}")
async def get_vip_occasion(occasion_id: str, db: DbSession):
    """Get a specific VIP occasion."""
    occasion = db.query(VIPOccasionModel).filter(
        VIPOccasionModel.id == int(occasion_id)
    ).first()
    if not occasion:
        raise HTTPException(status_code=404, detail="Occasion not found")
    return _occasion_to_schema(occasion)


@router.post("/occasions")
async def create_vip_occasion(occasion: VIPOccasion, db: DbSession):
    """Create a new VIP occasion."""
    # Parse the date string
    occasion_date = date.fromisoformat(occasion.date) if occasion.date else date.today()
    new_occasion = VIPOccasionModel(
        customer_id=int(occasion.customer_id) if occasion.customer_id else None,
        customer_name=occasion.customer_name,
        type=occasion.occasion_type,
        occasion_date=occasion_date,
        notes=occasion.notes,
        notification_sent=occasion.reminder_sent,
    )
    db.add(new_occasion)
    db.commit()
    db.refresh(new_occasion)
    return {"success": True, "id": str(new_occasion.id)}


_DEFAULT_VIP_SETTINGS = {
    "auto_upgrade_threshold": 0,
    "birthday_discount_pct": 0,
    "anniversary_discount_pct": 0,
    "min_spend_for_vip": 0,
    "points_multiplier": 1.0,
}


@router.get("/settings")
async def get_vip_settings(db: DbSession):
    """Get VIP program settings."""
    setting = db.query(AppSetting).filter(
        AppSetting.category == "vip",
        AppSetting.key == "program_settings",
    ).first()
    if setting and setting.value:
        return VIPSettings(**setting.value)
    return VIPSettings(**_DEFAULT_VIP_SETTINGS)


@router.put("/settings")
async def update_vip_settings(settings: VIPSettings, db: DbSession):
    """Update VIP program settings."""
    existing = db.query(AppSetting).filter(
        AppSetting.category == "vip",
        AppSetting.key == "program_settings",
    ).first()
    settings_dict = settings.model_dump()
    if existing:
        existing.value = settings_dict
        existing.updated_at = datetime.utcnow()
    else:
        new_setting = AppSetting(
            category="vip",
            key="program_settings",
            value=settings_dict,
        )
        db.add(new_setting)
    db.commit()
    return {"success": True}


@router.get("/tier-changes")
async def get_tier_changes(db: DbSession):
    """Get recent tier changes."""
    # Tier changes are stored as AppSetting entries with category 'vip_tier_changes'
    setting = db.query(AppSetting).filter(
        AppSetting.category == "vip",
        AppSetting.key == "tier_changes",
    ).first()
    if setting and setting.value:
        return [TierChange(**tc) for tc in setting.value]
    return []

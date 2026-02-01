"""VIP customer management API routes."""

from typing import List, Optional
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


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


@router.get("/customers")
async def get_vip_customers():
    """Get all VIP customers."""
    return [
        VIPCustomer(id="1", name="Alexander Petrov", email="alex@corp.com", phone="+359888111222", tier="platinum", total_spent=15800.00, visits=120, avg_spend=131.67, preferences=["Corner booth", "Champagne"], notes="CEO of TechCorp", last_visit="2026-02-01"),
        VIPCustomer(id="2", name="Maria Ivanova", email="maria@business.com", phone="+359888333444", tier="gold", total_spent=8500.00, visits=65, avg_spend=130.77, preferences=["Quiet table", "Red wine"], last_visit="2026-01-28"),
        VIPCustomer(id="3", name="David Chen", email="david@invest.com", phone="+359888555666", tier="diamond", total_spent=42000.00, visits=200, avg_spend=210.00, preferences=["Private room", "Whiskey collection"], notes="Investment banker, hosts client dinners", last_visit="2026-01-30"),
    ]


@router.get("/occasions")
async def get_vip_occasions():
    """Get upcoming VIP occasions."""
    return [
        VIPOccasion(id="1", customer_id="1", customer_name="Alexander Petrov", occasion_type="birthday", date="2026-02-15", notes="Prefers surprise cake", reminder_sent=True),
        VIPOccasion(id="2", customer_id="2", customer_name="Maria Ivanova", occasion_type="anniversary", date="2026-02-20", notes="Wedding anniversary - flowers requested"),
        VIPOccasion(id="3", customer_id="3", customer_name="David Chen", occasion_type="special", date="2026-02-10", notes="Promotion celebration"),
    ]


@router.get("/occasions/{occasion_id}")
async def get_vip_occasion(occasion_id: str):
    """Get a specific VIP occasion."""
    return VIPOccasion(id=occasion_id, customer_id="1", customer_name="Alexander Petrov", occasion_type="birthday", date="2026-02-15")


@router.post("/occasions")
async def create_vip_occasion(occasion: VIPOccasion):
    """Create a new VIP occasion."""
    return {"success": True, "id": "new-id"}


@router.get("/settings")
async def get_vip_settings():
    """Get VIP program settings."""
    return VIPSettings(
        auto_upgrade_threshold=5000.00,
        birthday_discount_pct=20,
        anniversary_discount_pct=15,
        min_spend_for_vip=1000.00,
        points_multiplier=2.0
    )


@router.put("/settings")
async def update_vip_settings(settings: VIPSettings):
    """Update VIP program settings."""
    return {"success": True}


@router.get("/tier-changes")
async def get_tier_changes():
    """Get recent tier changes."""
    return [
        TierChange(id="1", customer_name="John Smith", from_tier="silver", to_tier="gold", reason="Spending threshold reached", date="2026-01-28"),
        TierChange(id="2", customer_name="Sarah Johnson", from_tier="gold", to_tier="platinum", reason="Manual upgrade - loyal customer", date="2026-01-25"),
    ]

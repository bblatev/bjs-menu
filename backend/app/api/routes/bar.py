"""Bar management API routes."""

from typing import List, Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()


class BarStats(BaseModel):
    total_sales: float = 12450.00
    total_drinks: int = 847
    avg_pour_cost: float = 22.5
    spillage_rate: float = 2.3
    top_category: str = "Cocktails"
    period: str = "today"


class TopDrink(BaseModel):
    id: str
    name: str
    quantity: int
    revenue: float
    trend: str  # up, down, stable


class InventoryAlert(BaseModel):
    id: str
    item: str
    current_stock: float
    par_level: float
    unit: str
    severity: str  # low, medium, high


class RecentActivity(BaseModel):
    id: str
    type: str
    description: str
    timestamp: str
    user: str


class SpillageRecord(BaseModel):
    id: str
    item: str
    quantity: float
    unit: str
    reason: str
    recorded_by: str
    timestamp: str
    cost: float


@router.get("/stats")
async def get_bar_stats(period: str = Query("today")):
    """Get bar statistics."""
    return BarStats(period=period)


@router.get("/top-drinks")
async def get_top_drinks(period: str = Query("today")):
    """Get top selling drinks."""
    return [
        TopDrink(id="1", name="Mojito", quantity=125, revenue=1250.00, trend="up"),
        TopDrink(id="2", name="Margarita", quantity=98, revenue=980.00, trend="stable"),
        TopDrink(id="3", name="Old Fashioned", quantity=87, revenue=1044.00, trend="up"),
        TopDrink(id="4", name="Beer Draft", quantity=245, revenue=1225.00, trend="down"),
        TopDrink(id="5", name="Gin & Tonic", quantity=76, revenue=684.00, trend="stable"),
    ]


@router.get("/inventory-alerts")
async def get_inventory_alerts():
    """Get bar inventory alerts."""
    return [
        InventoryAlert(id="1", item="Vodka Premium", current_stock=2, par_level=6, unit="bottles", severity="high"),
        InventoryAlert(id="2", item="Fresh Lime", current_stock=5, par_level=15, unit="kg", severity="medium"),
        InventoryAlert(id="3", item="Tonic Water", current_stock=12, par_level=24, unit="bottles", severity="low"),
    ]


@router.get("/recent-activity")
async def get_recent_activity():
    """Get recent bar activity."""
    return [
        RecentActivity(id="1", type="sale", description="Tab closed - Table 5", timestamp="2026-02-01T17:30:00Z", user="John"),
        RecentActivity(id="2", type="spillage", description="Spillage recorded - Beer", timestamp="2026-02-01T17:15:00Z", user="Mike"),
        RecentActivity(id="3", type="inventory", description="Stock count completed", timestamp="2026-02-01T16:00:00Z", user="Sarah"),
    ]


@router.get("/spillage/records")
async def get_spillage_records():
    """Get spillage records."""
    return [
        SpillageRecord(id="1", item="Draft Beer", quantity=0.5, unit="L", reason="Over-pour", recorded_by="Mike", timestamp="2026-02-01T17:15:00Z", cost=3.50),
        SpillageRecord(id="2", item="Vodka", quantity=50, unit="ml", reason="Broken bottle", recorded_by="John", timestamp="2026-02-01T14:30:00Z", cost=8.00),
    ]


@router.post("/spillage/records")
async def create_spillage_record(record: SpillageRecord):
    """Create a spillage record."""
    return {"success": True, "id": "new-id"}

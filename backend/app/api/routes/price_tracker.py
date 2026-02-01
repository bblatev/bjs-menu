"""Price tracking API routes."""

from typing import List, Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter()


class PriceAlert(BaseModel):
    id: str
    ingredient: str
    supplier: str
    old_price: float
    new_price: float
    change_pct: float
    detected_at: str
    acknowledged: bool = False


class AlertRule(BaseModel):
    id: str
    ingredient: Optional[str] = None
    category: Optional[str] = None
    threshold_pct: float
    alert_type: str  # increase, decrease, any
    enabled: bool = True


@router.get("/alerts")
async def get_price_alerts(date_range: str = Query("week"), acknowledged: bool = Query(None)):
    """Get price alerts."""
    return [
        PriceAlert(id="1", ingredient="Beef Ribeye", supplier="Quality Meats Ltd", old_price=42.00, new_price=45.00, change_pct=7.14, detected_at="2026-02-01T10:00:00Z"),
        PriceAlert(id="2", ingredient="Olive Oil", supplier="Mediterranean Imports", old_price=8.50, new_price=9.20, change_pct=8.24, detected_at="2026-01-30T14:00:00Z"),
        PriceAlert(id="3", ingredient="Tomatoes", supplier="Fresh Farm Produce", old_price=3.50, new_price=3.20, change_pct=-8.57, detected_at="2026-01-28T09:00:00Z", acknowledged=True),
    ]


@router.post("/alerts/acknowledge-all")
async def acknowledge_all_alerts():
    """Acknowledge all alerts."""
    return {"success": True, "acknowledged_count": 2}


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    """Acknowledge a specific alert."""
    return {"success": True}


@router.get("/alert-rules")
async def get_alert_rules():
    """Get price alert rules."""
    return [
        AlertRule(id="1", category="Meat", threshold_pct=5.0, alert_type="increase", enabled=True),
        AlertRule(id="2", category="Produce", threshold_pct=10.0, alert_type="any", enabled=True),
        AlertRule(id="3", ingredient="Olive Oil", threshold_pct=3.0, alert_type="increase", enabled=True),
    ]


@router.post("/alert-rules")
async def create_alert_rule(rule: AlertRule):
    """Create an alert rule."""
    return {"success": True, "id": "new-id"}


@router.put("/alert-rules/{rule_id}")
async def update_alert_rule(rule_id: str, rule: AlertRule):
    """Update an alert rule."""
    return {"success": True}


@router.delete("/alert-rules/{rule_id}")
async def delete_alert_rule(rule_id: str):
    """Delete an alert rule."""
    return {"success": True}

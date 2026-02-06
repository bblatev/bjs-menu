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


@router.get("/history")
async def get_price_history(date_range: str = Query("30d")):
    """Get price history for tracked items."""
    from datetime import datetime, timedelta
    base = datetime(2026, 2, 1)
    return [
        {
            "id": 1, "itemName": "Beef Ribeye", "category": "Meat", "supplier": "Quality Meats Ltd",
            "prices": [{"date": (base - timedelta(days=i*7)).strftime("%Y-%m-%d"), "price": 42.0 + (i % 3)} for i in range(8)],
            "currentPrice": 45.00, "avgPrice": 43.50, "minPrice": 42.00, "maxPrice": 45.00, "volatility": 3.2,
        },
        {
            "id": 2, "itemName": "Olive Oil", "category": "Pantry", "supplier": "Mediterranean Imports",
            "prices": [{"date": (base - timedelta(days=i*7)).strftime("%Y-%m-%d"), "price": 8.5 + (i % 2) * 0.3} for i in range(8)],
            "currentPrice": 9.20, "avgPrice": 8.80, "minPrice": 8.50, "maxPrice": 9.20, "volatility": 4.1,
        },
        {
            "id": 3, "itemName": "Tomatoes", "category": "Produce", "supplier": "Fresh Farm Produce",
            "prices": [{"date": (base - timedelta(days=i*7)).strftime("%Y-%m-%d"), "price": 3.5 - (i % 2) * 0.15} for i in range(8)],
            "currentPrice": 3.20, "avgPrice": 3.40, "minPrice": 3.20, "maxPrice": 3.50, "volatility": 4.5,
        },
    ]


@router.get("/supplier-comparisons")
async def get_supplier_comparisons():
    """Compare prices across suppliers for same items."""
    return [
        {
            "itemName": "Beef Ribeye", "category": "Meat",
            "suppliers": [
                {"name": "Quality Meats Ltd", "price": 45.00, "lastUpdated": "2026-02-01", "reliability": 95, "deliveryTime": "1 day"},
                {"name": "Metro Cash & Carry", "price": 43.50, "lastUpdated": "2026-01-28", "reliability": 88, "deliveryTime": "2 days"},
            ],
            "bestPrice": 43.50, "currentSupplier": "Quality Meats Ltd", "potentialSavings": 1.50,
        },
        {
            "itemName": "Olive Oil (1L)", "category": "Pantry",
            "suppliers": [
                {"name": "Mediterranean Imports", "price": 9.20, "lastUpdated": "2026-02-01", "reliability": 92, "deliveryTime": "3 days"},
                {"name": "Local Distributor", "price": 8.90, "lastUpdated": "2026-01-25", "reliability": 85, "deliveryTime": "1 day"},
            ],
            "bestPrice": 8.90, "currentSupplier": "Mediterranean Imports", "potentialSavings": 0.30,
        },
    ]


@router.get("/category-trends")
async def get_category_trends(date_range: str = Query("30d")):
    """Get price trends by category."""
    return [
        {"category": "Meat", "currentAvg": 38.50, "previousAvg": 36.20, "changePercent": 6.35, "itemCount": 12, "topMover": "Beef Ribeye", "topMoverChange": 7.14},
        {"category": "Produce", "currentAvg": 4.80, "previousAvg": 5.10, "changePercent": -5.88, "itemCount": 25, "topMover": "Tomatoes", "topMoverChange": -8.57},
        {"category": "Dairy", "currentAvg": 6.20, "previousAvg": 6.00, "changePercent": 3.33, "itemCount": 8, "topMover": "Mozzarella", "topMoverChange": 5.0},
        {"category": "Pantry", "currentAvg": 7.50, "previousAvg": 7.10, "changePercent": 5.63, "itemCount": 15, "topMover": "Olive Oil", "topMoverChange": 8.24},
        {"category": "Beverages", "currentAvg": 3.20, "previousAvg": 3.15, "changePercent": 1.59, "itemCount": 20, "topMover": "Craft Beer", "topMoverChange": 4.0},
    ]


@router.get("/budget-impacts")
async def get_budget_impacts(date_range: str = Query("30d")):
    """Get budget impact analysis from price changes."""
    return [
        {"category": "Meat", "budgeted": 5000.00, "projected": 5320.00, "variance": 320.00, "variancePercent": 6.4},
        {"category": "Produce", "budgeted": 3000.00, "projected": 2820.00, "variance": -180.00, "variancePercent": -6.0},
        {"category": "Dairy", "budgeted": 2000.00, "projected": 2070.00, "variance": 70.00, "variancePercent": 3.5},
        {"category": "Pantry", "budgeted": 1500.00, "projected": 1585.00, "variance": 85.00, "variancePercent": 5.67},
        {"category": "Beverages", "budgeted": 4000.00, "projected": 4065.00, "variance": 65.00, "variancePercent": 1.63},
    ]

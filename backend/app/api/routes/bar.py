"""Bar management API routes."""

from typing import List, Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()


# ==================== RESPONSE MODELS ====================

class BarStats(BaseModel):
    """Bar statistics - matches frontend expectations."""
    total_sales: float = 3450.00
    total_cost: float = 862.50
    pour_cost_percentage: float = 25.0
    avg_ticket: float = 28.75
    top_cocktail: str = "Mojito"
    spillage_today: float = 45.00
    low_stock_items: int = 4
    active_recipes: int = 86
    period: str = "today"


class TopDrink(BaseModel):
    """Top drink item - matches frontend expectations."""
    id: int
    name: str
    category: str
    sold_today: int
    revenue: float
    pour_cost: float
    margin: float


class InventoryAlert(BaseModel):
    """Inventory alert - matches frontend expectations."""
    id: int
    item_name: str
    current_stock: float
    par_level: float
    unit: str
    status: str  # critical, low, reorder


class RecentPour(BaseModel):
    """Recent pour activity - matches frontend expectations."""
    id: int
    drink_name: str
    bartender: str
    time: str
    type: str  # sale, comp, spillage, waste
    amount: str
    cost: float


class SpillageRecord(BaseModel):
    """Spillage record."""
    id: Optional[str] = None
    item: Optional[str] = None
    item_name: Optional[str] = None  # Alias for compatibility
    quantity: float
    unit: str = "ml"
    reason: str
    recorded_by: Optional[str] = None
    notes: Optional[str] = None
    timestamp: Optional[str] = None
    cost: float = 0.0


# ==================== ROUTES ====================

@router.get("/stats")
async def get_bar_stats(period: str = Query("today")):
    """Get bar statistics."""
    # Adjust values based on period
    multiplier = {"today": 1, "week": 7, "month": 30}.get(period, 1)

    return {
        "total_sales": 3450.00 * multiplier,
        "total_cost": 862.50 * multiplier,
        "pour_cost_percentage": 25.0,
        "avg_ticket": 28.75,
        "top_cocktail": "Mojito",
        "spillage_today": 45.00 * (1 if period == "today" else multiplier * 0.8),
        "low_stock_items": 4,
        "active_recipes": 86,
        "period": period,
    }


@router.get("/top-drinks")
async def get_top_drinks(period: str = Query("today")):
    """Get top selling drinks."""
    multiplier = {"today": 1, "week": 7, "month": 30}.get(period, 1)

    return [
        {
            "id": 1,
            "name": "Mojito",
            "category": "Cocktail",
            "sold_today": int(42 * multiplier),
            "revenue": 420.00 * multiplier,
            "pour_cost": 21.5,
            "margin": 78.5,
        },
        {
            "id": 2,
            "name": "Margarita",
            "category": "Cocktail",
            "sold_today": int(38 * multiplier),
            "revenue": 380.00 * multiplier,
            "pour_cost": 23.0,
            "margin": 77.0,
        },
        {
            "id": 3,
            "name": "Long Island Iced Tea",
            "category": "Cocktail",
            "sold_today": int(28 * multiplier),
            "revenue": 392.00 * multiplier,
            "pour_cost": 28.5,
            "margin": 71.5,
        },
        {
            "id": 4,
            "name": "Old Fashioned",
            "category": "Cocktail",
            "sold_today": int(25 * multiplier),
            "revenue": 312.50 * multiplier,
            "pour_cost": 24.0,
            "margin": 76.0,
        },
        {
            "id": 5,
            "name": "Beer Draft",
            "category": "Beer",
            "sold_today": int(85 * multiplier),
            "revenue": 425.00 * multiplier,
            "pour_cost": 18.0,
            "margin": 82.0,
        },
        {
            "id": 6,
            "name": "Gin & Tonic",
            "category": "Cocktail",
            "sold_today": int(32 * multiplier),
            "revenue": 288.00 * multiplier,
            "pour_cost": 20.5,
            "margin": 79.5,
        },
        {
            "id": 7,
            "name": "Wine Glass (House)",
            "category": "Wine",
            "sold_today": int(45 * multiplier),
            "revenue": 360.00 * multiplier,
            "pour_cost": 30.0,
            "margin": 70.0,
        },
    ]


@router.get("/inventory-alerts")
async def get_inventory_alerts():
    """Get bar inventory alerts."""
    return [
        {
            "id": 1,
            "item_name": "Grey Goose Vodka",
            "current_stock": 2,
            "par_level": 6,
            "unit": "bottles",
            "status": "critical",
        },
        {
            "id": 2,
            "item_name": "Bacardi White Rum",
            "current_stock": 3,
            "par_level": 8,
            "unit": "bottles",
            "status": "low",
        },
        {
            "id": 3,
            "item_name": "Fresh Lime Juice",
            "current_stock": 2,
            "par_level": 5,
            "unit": "liters",
            "status": "critical",
        },
        {
            "id": 4,
            "item_name": "Tonic Water",
            "current_stock": 12,
            "par_level": 24,
            "unit": "bottles",
            "status": "reorder",
        },
        {
            "id": 5,
            "item_name": "Triple Sec",
            "current_stock": 1,
            "par_level": 4,
            "unit": "bottles",
            "status": "critical",
        },
    ]


@router.get("/recent-activity")
async def get_recent_activity():
    """Get recent bar activity / pours."""
    now = datetime.utcnow()
    return [
        {
            "id": 1,
            "drink_name": "Mojito",
            "bartender": "Alex",
            "time": "2 min ago",
            "type": "sale",
            "amount": "1x",
            "cost": 2.15,
        },
        {
            "id": 2,
            "drink_name": "Beer Draft",
            "bartender": "Maria",
            "time": "5 min ago",
            "type": "sale",
            "amount": "2x",
            "cost": 1.80,
        },
        {
            "id": 3,
            "drink_name": "Margarita",
            "bartender": "Alex",
            "time": "8 min ago",
            "type": "sale",
            "amount": "1x",
            "cost": 2.30,
        },
        {
            "id": 4,
            "drink_name": "Vodka Shot",
            "bartender": "Maria",
            "time": "12 min ago",
            "type": "comp",
            "amount": "1x",
            "cost": 1.50,
        },
        {
            "id": 5,
            "drink_name": "Beer Draft",
            "bartender": "John",
            "time": "15 min ago",
            "type": "spillage",
            "amount": "0.5L",
            "cost": 0.90,
        },
        {
            "id": 6,
            "drink_name": "Long Island",
            "bartender": "Alex",
            "time": "18 min ago",
            "type": "sale",
            "amount": "2x",
            "cost": 5.70,
        },
    ]


@router.get("/spillage/records")
async def get_spillage_records():
    """Get spillage records."""
    return [
        {
            "id": "1",
            "item": "Draft Beer",
            "item_name": "Draft Beer",
            "quantity": 0.5,
            "unit": "L",
            "reason": "Over-pour",
            "recorded_by": "Mike",
            "timestamp": "2026-02-05T17:15:00Z",
            "cost": 3.50,
        },
        {
            "id": "2",
            "item": "Vodka",
            "item_name": "Vodka",
            "quantity": 50,
            "unit": "ml",
            "reason": "Broken bottle",
            "recorded_by": "John",
            "timestamp": "2026-02-05T14:30:00Z",
            "cost": 8.00,
        },
        {
            "id": "3",
            "item": "Tequila",
            "item_name": "Tequila",
            "quantity": 30,
            "unit": "ml",
            "reason": "Spillage",
            "recorded_by": "Alex",
            "timestamp": "2026-02-05T12:00:00Z",
            "cost": 4.50,
        },
    ]


@router.post("/spillage/records")
async def create_spillage_record(record: SpillageRecord):
    """Create a spillage record."""
    new_id = str(int(datetime.utcnow().timestamp()))
    return {
        "success": True,
        "id": new_id,
        "item": record.item or record.item_name,
        "quantity": record.quantity,
        "unit": record.unit,
        "reason": record.reason,
        "cost": record.cost,
        "timestamp": datetime.utcnow().isoformat(),
    }


# ==================== ADDITIONAL BAR ENDPOINTS ====================

@router.get("/recipes")
async def get_bar_recipes():
    """Get bar cocktail recipes."""
    return [
        {
            "id": 1,
            "name": "Mojito",
            "category": "Cocktail",
            "ingredients": [
                {"name": "White Rum", "amount": 50, "unit": "ml"},
                {"name": "Fresh Lime Juice", "amount": 25, "unit": "ml"},
                {"name": "Simple Syrup", "amount": 20, "unit": "ml"},
                {"name": "Mint Leaves", "amount": 6, "unit": "leaves"},
                {"name": "Soda Water", "amount": 60, "unit": "ml"},
            ],
            "instructions": "Muddle mint with lime juice and syrup. Add rum, ice, top with soda.",
            "pour_cost": 2.15,
            "sell_price": 10.00,
            "margin": 78.5,
        },
        {
            "id": 2,
            "name": "Margarita",
            "category": "Cocktail",
            "ingredients": [
                {"name": "Tequila", "amount": 50, "unit": "ml"},
                {"name": "Triple Sec", "amount": 25, "unit": "ml"},
                {"name": "Fresh Lime Juice", "amount": 25, "unit": "ml"},
            ],
            "instructions": "Shake with ice, strain into salt-rimmed glass.",
            "pour_cost": 2.30,
            "sell_price": 10.00,
            "margin": 77.0,
        },
    ]


@router.get("/inventory")
async def get_bar_inventory():
    """Get full bar inventory."""
    return [
        {"id": 1, "name": "Grey Goose Vodka", "category": "Spirits", "current_stock": 2, "par_level": 6, "unit": "bottles", "cost_per_unit": 35.00},
        {"id": 2, "name": "Bacardi White Rum", "category": "Spirits", "current_stock": 3, "par_level": 8, "unit": "bottles", "cost_per_unit": 22.00},
        {"id": 3, "name": "Jose Cuervo Tequila", "category": "Spirits", "current_stock": 4, "par_level": 6, "unit": "bottles", "cost_per_unit": 28.00},
        {"id": 4, "name": "Tanqueray Gin", "category": "Spirits", "current_stock": 5, "par_level": 6, "unit": "bottles", "cost_per_unit": 32.00},
        {"id": 5, "name": "Jack Daniel's", "category": "Spirits", "current_stock": 4, "par_level": 5, "unit": "bottles", "cost_per_unit": 38.00},
        {"id": 6, "name": "Fresh Lime Juice", "category": "Mixers", "current_stock": 2, "par_level": 5, "unit": "liters", "cost_per_unit": 8.00},
        {"id": 7, "name": "Simple Syrup", "category": "Mixers", "current_stock": 3, "par_level": 4, "unit": "liters", "cost_per_unit": 5.00},
        {"id": 8, "name": "Tonic Water", "category": "Mixers", "current_stock": 12, "par_level": 24, "unit": "bottles", "cost_per_unit": 1.50},
        {"id": 9, "name": "Soda Water", "category": "Mixers", "current_stock": 18, "par_level": 24, "unit": "bottles", "cost_per_unit": 1.00},
        {"id": 10, "name": "Draft Beer (Keg)", "category": "Beer", "current_stock": 2, "par_level": 3, "unit": "kegs", "cost_per_unit": 120.00},
    ]


@router.post("/inventory/count")
async def record_inventory_count(counts: List[dict]):
    """Record inventory count."""
    return {
        "success": True,
        "items_counted": len(counts),
        "timestamp": datetime.utcnow().isoformat(),
        "message": "Inventory count recorded successfully",
    }


# ==================== HAPPY HOURS ENDPOINTS ====================

class HappyHourCreate(BaseModel):
    """Happy hour creation model."""
    name: str
    description: str = ""
    days: List[str] = []
    start_time: str = "16:00"
    end_time: str = "19:00"
    discount_type: str = "percentage"  # percentage, fixed, bogo
    discount_value: float = 20.0
    applies_to: str = "category"  # all, category, items
    category_ids: Optional[List[int]] = None
    item_ids: Optional[List[int]] = None
    status: str = "active"  # active, inactive, scheduled
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    max_per_customer: Optional[int] = None
    min_purchase: Optional[float] = None


# In-memory storage for demo (in production, use database)
_happy_hours = [
    {
        "id": 1,
        "name": "Classic Happy Hour",
        "description": "50% off all draft beers",
        "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        "start_time": "16:00",
        "end_time": "19:00",
        "discount_type": "percentage",
        "discount_value": 50,
        "applies_to": "category",
        "category_ids": [1],
        "item_names": ["All Draft Beers"],
        "status": "active",
        "created_at": "2024-01-01T00:00:00Z",
    },
    {
        "id": 2,
        "name": "Wine Wednesday",
        "description": "Half price on all wines",
        "days": ["Wednesday"],
        "start_time": "17:00",
        "end_time": "21:00",
        "discount_type": "percentage",
        "discount_value": 50,
        "applies_to": "category",
        "category_ids": [2],
        "item_names": ["All Wines"],
        "status": "active",
        "created_at": "2024-01-01T00:00:00Z",
    },
    {
        "id": 3,
        "name": "Cocktail Hour",
        "description": "2-for-1 on selected cocktails",
        "days": ["Thursday", "Friday", "Saturday"],
        "start_time": "18:00",
        "end_time": "20:00",
        "discount_type": "bogo",
        "discount_value": 0,
        "applies_to": "category",
        "category_ids": [3],
        "item_names": ["Mojito", "Margarita", "Gin & Tonic"],
        "status": "active",
        "created_at": "2024-01-15T00:00:00Z",
    },
    {
        "id": 4,
        "name": "Sunday Funday",
        "description": "$3 off all drinks",
        "days": ["Sunday"],
        "start_time": "14:00",
        "end_time": "20:00",
        "discount_type": "fixed",
        "discount_value": 3,
        "applies_to": "all",
        "category_ids": [],
        "item_names": ["All Drinks"],
        "status": "active",
        "created_at": "2024-02-01T00:00:00Z",
    },
]


@router.get("/happy-hours")
async def get_happy_hours():
    """Get all happy hour promotions."""
    return _happy_hours


@router.get("/happy-hours/stats")
async def get_happy_hours_stats():
    """Get happy hour statistics."""
    active_count = sum(1 for h in _happy_hours if h["status"] == "active")
    return {
        "active_promos": active_count,
        "total_savings": 2450.00,
        "orders_with_promo": 186,
        "avg_check_increase": 12.5,
        "most_popular": "Classic Happy Hour",
        "total_promos": len(_happy_hours),
    }


@router.get("/happy-hours/{happy_hour_id}")
async def get_happy_hour(happy_hour_id: int):
    """Get a specific happy hour promotion."""
    for hh in _happy_hours:
        if hh["id"] == happy_hour_id:
            return hh
    return {"error": "Happy hour not found"}


@router.post("/happy-hours")
async def create_happy_hour(data: HappyHourCreate):
    """Create a new happy hour promotion."""
    new_id = max(h["id"] for h in _happy_hours) + 1 if _happy_hours else 1
    new_happy_hour = {
        "id": new_id,
        "name": data.name,
        "description": data.description,
        "days": data.days,
        "start_time": data.start_time,
        "end_time": data.end_time,
        "discount_type": data.discount_type,
        "discount_value": data.discount_value,
        "applies_to": data.applies_to,
        "category_ids": data.category_ids or [],
        "item_ids": data.item_ids,
        "item_names": [],
        "status": data.status,
        "start_date": data.start_date,
        "end_date": data.end_date,
        "max_per_customer": data.max_per_customer,
        "min_purchase": data.min_purchase,
        "created_at": datetime.utcnow().isoformat(),
    }
    _happy_hours.append(new_happy_hour)
    return {
        "success": True,
        "happy_hour": new_happy_hour,
    }


@router.put("/happy-hours/{happy_hour_id}")
async def update_happy_hour(happy_hour_id: int, data: HappyHourCreate):
    """Update a happy hour promotion."""
    for i, hh in enumerate(_happy_hours):
        if hh["id"] == happy_hour_id:
            _happy_hours[i] = {
                **hh,
                "name": data.name,
                "description": data.description,
                "days": data.days,
                "start_time": data.start_time,
                "end_time": data.end_time,
                "discount_type": data.discount_type,
                "discount_value": data.discount_value,
                "applies_to": data.applies_to,
                "category_ids": data.category_ids or [],
                "item_ids": data.item_ids,
                "status": data.status,
                "start_date": data.start_date,
                "end_date": data.end_date,
                "max_per_customer": data.max_per_customer,
                "min_purchase": data.min_purchase,
                "updated_at": datetime.utcnow().isoformat(),
            }
            return {
                "success": True,
                "happy_hour": _happy_hours[i],
            }
    return {"error": "Happy hour not found"}


@router.delete("/happy-hours/{happy_hour_id}")
async def delete_happy_hour(happy_hour_id: int):
    """Delete a happy hour promotion."""
    global _happy_hours
    for i, hh in enumerate(_happy_hours):
        if hh["id"] == happy_hour_id:
            del _happy_hours[i]
            return {"success": True, "message": "Happy hour deleted"}
    return {"error": "Happy hour not found"}


@router.post("/happy-hours/{happy_hour_id}/toggle")
async def toggle_happy_hour(happy_hour_id: int):
    """Toggle happy hour active/inactive status."""
    for i, hh in enumerate(_happy_hours):
        if hh["id"] == happy_hour_id:
            new_status = "inactive" if hh["status"] == "active" else "active"
            _happy_hours[i]["status"] = new_status
            return {
                "success": True,
                "happy_hour_id": happy_hour_id,
                "status": new_status,
            }
    return {"error": "Happy hour not found"}

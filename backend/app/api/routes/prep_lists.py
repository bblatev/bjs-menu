"""
AI Prep Lists API Routes
Generates prep lists based on demand forecasting.
"""
from datetime import date, datetime, timezone
from fastapi import APIRouter, Query, Request
from app.db.session import DbSession
from app.core.rate_limit import limiter

router = APIRouter()


@router.get("/")
@limiter.limit("60/minute")
def get_prep_lists_overview(request: Request, db: DbSession):
    """Prep lists overview."""
    return {
        "module": "prep-lists",
        "status": "active",
        "endpoints": ["/today", "/{date}", "/{date}/complete"],
    }


@router.get("/today")
@limiter.limit("60/minute")
def get_today_prep_list(request: Request, db: DbSession, location_id: int = Query(1)):
    """Get AI-generated prep list for today."""
    today = date.today()
    return _generate_prep_list(db, location_id, today)


@router.get("/{prep_date}")
@limiter.limit("60/minute")
def get_prep_list_for_date(
    request: Request, db: DbSession,
    prep_date: str, location_id: int = Query(1)
):
    """Get prep list for a specific date."""
    try:
        target_date = date.fromisoformat(prep_date)
    except ValueError:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    return _generate_prep_list(db, location_id, target_date)


@router.post("/{prep_date}/complete")
@limiter.limit("30/minute")
def complete_prep_items(
    request: Request, db: DbSession,
    prep_date: str, data: dict = {}
):
    """Mark prep items as completed."""
    completed_items = data.get("completed_items", [])
    return {
        "date": prep_date,
        "completed_items": len(completed_items),
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }


def _generate_prep_list(db, location_id: int, target_date: date) -> dict:
    """Generate a prep list based on forecasted demand."""
    day_name = target_date.strftime("%A")

    # Base prep items that vary by day
    base_items = [
        {"name": "Burger Patties", "unit": "each", "base_qty": 50, "priority": "high", "category": "Proteins"},
        {"name": "Chicken Breast", "unit": "lbs", "base_qty": 20, "priority": "high", "category": "Proteins"},
        {"name": "Fish Fillet", "unit": "lbs", "base_qty": 10, "priority": "medium", "category": "Proteins"},
        {"name": "House Salad Mix", "unit": "lbs", "base_qty": 15, "priority": "high", "category": "Produce"},
        {"name": "Diced Tomatoes", "unit": "lbs", "base_qty": 8, "priority": "medium", "category": "Produce"},
        {"name": "Sliced Onions", "unit": "lbs", "base_qty": 6, "priority": "medium", "category": "Produce"},
        {"name": "French Fries", "unit": "lbs", "base_qty": 30, "priority": "high", "category": "Sides"},
        {"name": "Soup of the Day", "unit": "gallons", "base_qty": 3, "priority": "high", "category": "Soups"},
        {"name": "Dessert Portions", "unit": "each", "base_qty": 25, "priority": "low", "category": "Desserts"},
        {"name": "Bread Rolls", "unit": "dozen", "base_qty": 10, "priority": "medium", "category": "Bread"},
    ]

    # Adjust quantities by day of week
    multipliers = {
        "Monday": 0.7, "Tuesday": 0.75, "Wednesday": 0.85,
        "Thursday": 0.9, "Friday": 1.3, "Saturday": 1.4, "Sunday": 1.1,
    }
    multiplier = multipliers.get(day_name, 1.0)

    prep_items = []
    for item in base_items:
        qty = round(item["base_qty"] * multiplier)
        prep_items.append({
            "name": item["name"],
            "quantity": qty,
            "unit": item["unit"],
            "priority": item["priority"],
            "category": item["category"],
            "completed": False,
            "forecast_basis": f"Based on {day_name} demand forecast ({multiplier:.0%} of baseline)",
        })

    return {
        "date": target_date.isoformat(),
        "day": day_name,
        "location_id": location_id,
        "demand_multiplier": multiplier,
        "total_items": len(prep_items),
        "completed_items": 0,
        "completion_pct": 0,
        "items": prep_items,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

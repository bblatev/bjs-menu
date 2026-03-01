"""Bar recipes, inventory & happy hours"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Dict, Optional, Any
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal

from app.core.rate_limit import limiter
from app.db.session import get_db

# Import shared schemas and helpers
from app.api.routes.bar._shared import *

router = APIRouter()

@router.post("/recipes")
@limiter.limit("30/minute")
def create_bar_recipe(
    request: Request,
    db: DbSession,
    data: dict = None,
    current_user: OptionalCurrentUser = None,
):
    """Create a bar recipe."""
    from fastapi import Body
    if data is None:
        data = {}
    name = data.get("name", "Untitled Recipe")
    recipe = Recipe(name=name)
    db.add(recipe)
    db.flush()

    for ing in data.get("ingredients", []):
        product_name = ing.get("name", "")
        product = db.query(Product).filter(Product.name.ilike(f"%{product_name}%")).first() if product_name else None
        if product:
            line = RecipeLine(
                recipe_id=recipe.id,
                product_id=product.id,
                qty=Decimal(str(ing.get("quantity", ing.get("amount", 1)))),
                unit=ing.get("unit", product.unit or "ml"),
            )
            db.add(line)

    db.commit()
    db.refresh(recipe)
    return {
        "id": recipe.id,
        "name": recipe.name,
        "category": data.get("category", "Recipe"),
        "ingredients": data.get("ingredients", []),
        "instructions": data.get("instructions", ""),
    }


@router.get("/recipes")
@limiter.limit("60/minute")
def get_bar_recipes(
    request: Request,
    db: DbSession,
    current_user: OptionalCurrentUser = None,
    category: Optional[str] = Query(None),
):
    """Get bar cocktail recipes from database."""
    query = db.query(Recipe)

    # Filter by name containing cocktail-related terms if no specific category
    if category:
        query = query.filter(Recipe.name.ilike(f"%{category}%"))

    recipes = query.order_by(Recipe.name).limit(50).all()

    results = []
    for recipe in recipes:
        # Calculate pour cost from ingredients
        pour_cost = Decimal("0")
        ingredients = []

        for line in recipe.lines:
            product = db.query(Product).filter(Product.id == line.product_id).first()
            if product:
                line_cost = Decimal(str(line.qty)) * (product.cost_price or Decimal("0"))
                pour_cost += line_cost
                ingredients.append({
                    "name": product.name,
                    "amount": float(line.qty),
                    "unit": line.unit,
                })

        results.append({
            "id": recipe.id,
            "name": recipe.name,
            "category": "Recipe",
            "ingredients": ingredients,
            "instructions": "",  # Would need instructions field in Recipe model
            "pour_cost": float(pour_cost),
            "sell_price": float(pour_cost * 4) if pour_cost > 0 else 0,
            "margin": round(75.0, 1) if pour_cost > 0 else 0,
        })

    return results


@router.get("/inventory")
@limiter.limit("60/minute")
def get_bar_inventory(
    request: Request,
    db: DbSession,
    current_user: OptionalCurrentUser = None,
    location_id: int = Query(1),
    category: Optional[str] = Query(None),
):
    """Get full bar inventory from real stock data."""
    query = db.query(StockOnHand, Product).join(
        Product, StockOnHand.product_id == Product.id
    ).filter(
        StockOnHand.location_id == location_id
    )

    # Note: Products don't have category field; filter by name instead
    if category:
        query = query.filter(Product.name.ilike(f"%{category}%"))

    stock_items = query.order_by(Product.name).all()

    results = []
    for stock, product in stock_items:
        results.append({
            "id": product.id,
            "name": product.name,
            "category": "General",  # Products don't have category field
            "current_stock": float(stock.qty),
            "par_level": float(product.par_level) if product.par_level else 0,
            "unit": product.unit or "pcs",
            "cost_per_unit": float(product.cost_price) if product.cost_price else 0,
        })

    return results


@router.post("/inventory/count")
@limiter.limit("30/minute")
def record_inventory_count(
    request: Request,
    counts: Union[List[dict], dict],
    db: DbSession,
    current_user: RequireManager,
    location_id: int = Query(1),
):
    """Record inventory count - updates stock on hand.

    Accepts either a JSON array of count objects or a single count object.
    """
    # Normalize input: accept a single object or a list
    if isinstance(counts, dict):
        counts = [counts]

    updated = 0
    errors = []

    for count in counts:
        product_id = count.get("product_id") or count.get("id")
        new_qty = count.get("quantity") or count.get("current_stock")

        if not product_id or new_qty is None:
            continue

        stock = db.query(StockOnHand).filter(
            StockOnHand.product_id == product_id,
            StockOnHand.location_id == location_id
        ).first()

        if stock:
            old_qty = stock.qty
            stock.qty = Decimal(str(new_qty))

            # Create adjustment movement
            delta = Decimal(str(new_qty)) - old_qty
            if delta != 0:
                movement = StockMovement(
                    product_id=product_id,
                    location_id=location_id,
                    qty_delta=delta,
                    reason=MovementReason.INVENTORY_COUNT.value,
                    notes="Bar inventory count",
                )
                db.add(movement)

            updated += 1
        else:
            # Create new stock record
            stock = StockOnHand(
                product_id=product_id,
                location_id=location_id,
                qty=Decimal(str(new_qty)),
            )
            db.add(stock)
            updated += 1

    db.commit()

    return {
        "success": True,
        "items_counted": updated,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": f"Inventory count recorded: {updated} items updated",
    }


# ==================== HAPPY HOURS (database-backed) ====================

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


def _happy_hour_to_dict(hh: HappyHour) -> dict:
    """Convert HappyHour model to dict for API response."""
    return {
        "id": hh.id,
        "name": hh.name,
        "description": hh.description or "",
        "days": hh.days or [],
        "start_time": hh.start_time.strftime("%H:%M") if hh.start_time else "16:00",
        "end_time": hh.end_time.strftime("%H:%M") if hh.end_time else "19:00",
        "discount_type": hh.discount_type,
        "discount_value": float(hh.discount_value),
        "applies_to": hh.applies_to,
        "category_ids": hh.category_ids or [],
        "item_ids": hh.item_ids,
        "status": hh.status,
        "start_date": hh.start_date.isoformat() if hh.start_date else None,
        "end_date": hh.end_date.isoformat() if hh.end_date else None,
        "max_per_customer": hh.max_per_customer,
        "min_purchase": float(hh.min_purchase) if hh.min_purchase else None,
        "created_at": hh.created_at.isoformat() if hh.created_at else None,
        "times_used": hh.times_used,
        "total_discount_given": float(hh.total_discount_given),
    }


@router.get("/happy-hours")
@limiter.limit("60/minute")
def get_happy_hours(
    request: Request,
    db: DbSession,
    current_user: OptionalCurrentUser = None,
    location_id: Optional[int] = Query(None),
):
    """Get all happy hour promotions from database."""
    query = db.query(HappyHour)
    if location_id:
        query = query.filter(
            (HappyHour.location_id == location_id) | (HappyHour.location_id.is_(None))
        )

    happy_hours = query.order_by(HappyHour.name).all()
    return [_happy_hour_to_dict(hh) for hh in happy_hours]


@router.get("/happy-hours/stats")
@limiter.limit("60/minute")
def get_happy_hours_stats(
    request: Request,
    db: DbSession,
    current_user: OptionalCurrentUser = None,
    location_id: Optional[int] = Query(None),
):
    """Get happy hour statistics."""
    query = db.query(HappyHour)
    if location_id:
        query = query.filter(
            (HappyHour.location_id == location_id) | (HappyHour.location_id.is_(None))
        )

    all_promos = query.all()
    active_count = sum(1 for h in all_promos if h.status == "active")
    total_savings = sum(float(h.total_discount_given) for h in all_promos)
    total_uses = sum(h.times_used for h in all_promos)

    # Find most popular
    most_popular = max(all_promos, key=lambda h: h.times_used) if all_promos else None

    return {
        "active_promos": active_count,
        "total_savings": total_savings,
        "orders_with_promo": total_uses,
        "avg_check_increase": 0,
        "most_popular": most_popular.name if most_popular else None,
        "total_promos": len(all_promos),
    }


@router.get("/happy-hours/{happy_hour_id}")
@limiter.limit("60/minute")
def get_happy_hour(
    request: Request,
    happy_hour_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Get a specific happy hour promotion."""
    hh = db.query(HappyHour).filter(HappyHour.id == happy_hour_id).first()
    if not hh:
        raise HTTPException(status_code=404, detail="Happy hour not found")
    return _happy_hour_to_dict(hh)


@router.post("/happy-hours")
@limiter.limit("30/minute")
def create_happy_hour(
    request: Request,
    data: HappyHourCreate,
    db: DbSession,
    current_user: RequireManager,
    location_id: Optional[int] = Query(None),
):
    """Create a new happy hour promotion."""
    # Parse times
    try:
        start_parts = data.start_time.split(":")
        end_parts = data.end_time.split(":")
        parsed_start = time(int(start_parts[0]), int(start_parts[1]))
        parsed_end = time(int(end_parts[0]), int(end_parts[1]))
    except (ValueError, IndexError):
        raise HTTPException(status_code=422, detail="Invalid time format. Use HH:MM.")

    hh = HappyHour(
        location_id=location_id,
        name=data.name,
        description=data.description,
        days=data.days,
        start_time=parsed_start,
        end_time=parsed_end,
        discount_type=data.discount_type,
        discount_value=Decimal(str(data.discount_value)),
        applies_to=data.applies_to,
        category_ids=data.category_ids,
        item_ids=data.item_ids,
        max_per_customer=data.max_per_customer,
        min_purchase=Decimal(str(data.min_purchase)) if data.min_purchase else None,
        status=data.status,
        start_date=date.fromisoformat(data.start_date) if data.start_date else None,
        end_date=date.fromisoformat(data.end_date) if data.end_date else None,
    )
    db.add(hh)
    db.commit()
    db.refresh(hh)

    return {
        "success": True,
        "happy_hour": _happy_hour_to_dict(hh),
    }


@router.put("/happy-hours/{happy_hour_id}")
@limiter.limit("30/minute")
def update_happy_hour(
    request: Request,
    happy_hour_id: int,
    data: HappyHourCreate,
    db: DbSession,
    current_user: RequireManager,
):
    """Update a happy hour promotion."""
    hh = db.query(HappyHour).filter(HappyHour.id == happy_hour_id).first()
    if not hh:
        raise HTTPException(status_code=404, detail="Happy hour not found")

    # Parse times
    start_parts = data.start_time.split(":")
    end_parts = data.end_time.split(":")

    hh.name = data.name
    hh.description = data.description
    hh.days = data.days
    hh.start_time = time(int(start_parts[0]), int(start_parts[1]))
    hh.end_time = time(int(end_parts[0]), int(end_parts[1]))
    hh.discount_type = data.discount_type
    hh.discount_value = Decimal(str(data.discount_value))
    hh.applies_to = data.applies_to
    hh.category_ids = data.category_ids
    hh.item_ids = data.item_ids
    hh.max_per_customer = data.max_per_customer
    hh.min_purchase = Decimal(str(data.min_purchase)) if data.min_purchase else None
    hh.status = data.status
    hh.start_date = date.fromisoformat(data.start_date) if data.start_date else None
    hh.end_date = date.fromisoformat(data.end_date) if data.end_date else None

    db.commit()
    db.refresh(hh)

    return {
        "success": True,
        "happy_hour": _happy_hour_to_dict(hh),
    }


@router.delete("/happy-hours/{happy_hour_id}")
@limiter.limit("30/minute")
def delete_happy_hour(
    request: Request,
    happy_hour_id: int,
    db: DbSession,
    current_user: RequireManager,
):
    """Delete a happy hour promotion."""
    hh = db.query(HappyHour).filter(HappyHour.id == happy_hour_id).first()
    if not hh:
        raise HTTPException(status_code=404, detail="Happy hour not found")

    db.delete(hh)
    db.commit()

    return {"success": True, "message": "Happy hour deleted"}


@router.post("/happy-hours/{happy_hour_id}/toggle")
@limiter.limit("30/minute")
def toggle_happy_hour(
    request: Request,
    happy_hour_id: int,
    db: DbSession,
    current_user: RequireManager,
):
    """Toggle happy hour active/inactive status."""
    hh = db.query(HappyHour).filter(HappyHour.id == happy_hour_id).first()
    if not hh:
        raise HTTPException(status_code=404, detail="Happy hour not found")

    hh.status = "inactive" if hh.status == "active" else "active"
    db.commit()

    return {
        "success": True,
        "happy_hour_id": happy_hour_id,
        "status": hh.status,
    }


@router.get("/cocktails")
@limiter.limit("60/minute")
def get_cocktails(request: Request, db: DbSession, current_user: OptionalCurrentUser = None):
    """Get cocktail recipes list."""
    recipes = db.query(Recipe).order_by(Recipe.name).limit(50).all()
    results = []
    for recipe in recipes:
        ingredients = []
        pour_cost = Decimal("0")
        for line in recipe.lines:
            product = db.query(Product).filter(Product.id == line.product_id).first()
            if product:
                line_cost = Decimal(str(line.qty)) * (product.cost_price or Decimal("0"))
                pour_cost += line_cost
                ingredients.append({"name": product.name, "amount": float(line.qty), "unit": line.unit})
        results.append({
            "id": recipe.id,
            "name": recipe.name,
            "category": "Cocktail",
            "ingredients": ingredients,
            "instructions": "",
            "pour_cost": float(pour_cost),
            "sell_price": float(pour_cost * 4) if pour_cost > 0 else 0,
            "margin": round(75.0, 1) if pour_cost > 0 else 0,
            "image_url": None,
        })
    return results



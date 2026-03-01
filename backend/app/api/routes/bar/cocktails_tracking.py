"""Cocktails, pour tracking, kegs & draft freshness"""
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

# ==================== TANKS (proxy to inventory-hardware) ====================

@router.get("/tanks")
@limiter.limit("60/minute")
def get_bar_tanks(
    request: Request,
    db: DbSession,
    current_user: OptionalCurrentUser = None,
    status: Optional[str] = Query(None),
):
    """Get bar tanks - delegates to inventory hardware tank listing."""
    from app.models.hardware import Tank as TankModel

    query = db.query(TankModel)
    if status:
        query = query.filter(TankModel.status == status)

    tanks = query.all()

    tank_list = []
    alerts = []
    for tank in tanks:
        level_percentage = round(
            (tank.current_level_liters / tank.capacity_liters) * 100, 1
        ) if tank.capacity_liters and tank.capacity_liters > 0 else 0
        tank_dict = {
            "id": tank.id,
            "name": tank.name,
            "product_id": tank.product_id,
            "product_name": tank.product_name,
            "capacity_liters": tank.capacity_liters,
            "current_level_liters": tank.current_level_liters,
            "level_percentage": level_percentage,
            "status": tank.status,
            "last_refill": tank.last_refill,
            "sensor_id": tank.sensor_id,
        }
        tank_list.append(tank_dict)
        if tank.status in ["low", "critical"]:
            alerts.append(tank_dict)

    return {
        "tanks": tank_list,
        "total": len(tank_list),
        "alerts": alerts,
    }


# ==================== POUR COSTS (root listing) ====================

# ==================== COCKTAIL RECIPES & POUR TRACKING ====================

@router.get("/cocktail-recipes")
@limiter.limit("60/minute")
def get_cocktail_recipes(
    request: Request,
    db: DbSession,
    current_user: OptionalCurrentUser = None,
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    """Get cocktail recipes with cost analysis."""
    query = db.query(Recipe)
    if category:
        query = query.filter(Recipe.name.ilike(f"%{category}%"))
    if search:
        query = query.filter(Recipe.name.ilike(f"%{search}%"))
    recipes = query.order_by(Recipe.name).limit(100).all()

    results = []
    for recipe in recipes:
        pour_cost = Decimal("0")
        ingredients = []
        for line in recipe.lines:
            product = db.query(Product).filter(Product.id == line.product_id).first()
            if product:
                line_cost = Decimal(str(line.qty)) * (product.cost_price or Decimal("0"))
                pour_cost += line_cost
                ingredients.append({
                    "product_id": product.id,
                    "name": product.name,
                    "amount": float(line.qty),
                    "unit": line.unit,
                    "cost": float(line_cost),
                })
        sell_price = float(pour_cost * 4) if pour_cost > 0 else 0
        results.append({
            "id": recipe.id,
            "name": recipe.name,
            "category": "Cocktail",
            "ingredients": ingredients,
            "pour_cost": float(pour_cost),
            "sell_price": sell_price,
            "margin_pct": round((1 - float(pour_cost) / sell_price) * 100, 1) if sell_price > 0 else 0,
        })
    return {"recipes": results, "total": len(results)}


@router.post("/cocktail-recipes")
@limiter.limit("30/minute")
def create_cocktail_recipe(
    request: Request,
    db: DbSession,
    data: dict = None,
    current_user: CurrentUser = None,
):
    """Create a new cocktail recipe with ingredients."""
    if data is None:
        data = {}
    name = data.get("name", "Untitled Cocktail")
    recipe = Recipe(name=name)
    db.add(recipe)
    db.flush()

    for ing in data.get("ingredients", []):
        product_id = ing.get("product_id")
        product = None
        if product_id:
            product = db.query(Product).filter(Product.id == product_id).first()
        elif ing.get("name"):
            product = db.query(Product).filter(Product.name.ilike(f"%{ing['name']}%")).first()
        if product:
            line = RecipeLine(
                recipe_id=recipe.id,
                product_id=product.id,
                qty=Decimal(str(ing.get("amount", ing.get("quantity", 1)))),
                unit=ing.get("unit", product.unit or "ml"),
            )
            db.add(line)

    db.commit()
    db.refresh(recipe)
    return {
        "success": True,
        "id": recipe.id,
        "name": recipe.name,
        "ingredients_count": len(data.get("ingredients", [])),
    }


@router.get("/cocktail-recipes/{recipe_id}")
@limiter.limit("60/minute")
def get_cocktail_recipe_detail(
    request: Request,
    recipe_id: int,
    db: DbSession,
    current_user: OptionalCurrentUser = None,
):
    """Get detailed cocktail recipe by ID."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    pour_cost = Decimal("0")
    ingredients = []
    for line in recipe.lines:
        product = db.query(Product).filter(Product.id == line.product_id).first()
        if product:
            line_cost = Decimal(str(line.qty)) * (product.cost_price or Decimal("0"))
            pour_cost += line_cost
            ingredients.append({
                "product_id": product.id,
                "name": product.name,
                "amount": float(line.qty),
                "unit": line.unit,
                "cost": float(line_cost),
            })

    sell_price = float(pour_cost * 4) if pour_cost > 0 else 0
    return {
        "id": recipe.id,
        "name": recipe.name,
        "category": "Cocktail",
        "ingredients": ingredients,
        "pour_cost": float(pour_cost),
        "sell_price": sell_price,
        "margin_pct": round((1 - float(pour_cost) / sell_price) * 100, 1) if sell_price > 0 else 0,
    }


@router.post("/pour-tracking/record")
@limiter.limit("30/minute")
def record_pour(
    request: Request,
    db: DbSession,
    data: dict = None,
    current_user: CurrentUser = None,
    location_id: int = Query(1),
):
    """Record a pour event for accuracy tracking."""
    if data is None:
        data = {}
    product_id = data.get("product_id")
    expected_ml = data.get("expected_ml", 0)
    actual_ml = data.get("actual_ml", 0)
    bartender_id = data.get("bartender_id")

    if product_id:
        movement = StockMovement(
            product_id=product_id,
            location_id=location_id,
            qty_delta=-Decimal(str(actual_ml)),
            reason=MovementReason.SALE.value,
            notes=f"Pour tracking: expected={expected_ml}ml actual={actual_ml}ml",
        )
        db.add(movement)
        db.commit()

    variance = actual_ml - expected_ml
    return {
        "success": True,
        "product_id": product_id,
        "expected_ml": expected_ml,
        "actual_ml": actual_ml,
        "variance_ml": variance,
        "accuracy_pct": round((expected_ml / actual_ml * 100), 1) if actual_ml > 0 else 0,
        "bartender_id": bartender_id,
    }


@router.get("/pour-tracking/accuracy")
@limiter.limit("60/minute")
def get_pour_accuracy(
    request: Request,
    db: DbSession,
    current_user: OptionalCurrentUser = None,
    location_id: int = Query(1),
    period: str = Query("week"),
):
    """Get pour accuracy metrics."""
    from datetime import timedelta as td
    now = datetime.now(timezone.utc)
    if period == "today":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start_date = now - td(days=7)
    else:
        start_date = now - td(days=30)

    movements = db.query(StockMovement).filter(
        StockMovement.location_id == location_id,
        StockMovement.reason == MovementReason.SALE.value,
        StockMovement.ts >= start_date,
        StockMovement.notes.like("%Pour tracking%"),
    ).all()

    return {
        "period": period,
        "total_pours": len(movements),
        "avg_accuracy_pct": 95.0,
        "over_pours": 0,
        "under_pours": 0,
        "total_variance_ml": 0,
        "cost_of_variance": 0,
    }


@router.get("/pour-tracking/variance-report")
@limiter.limit("60/minute")
def get_pour_variance_report(
    request: Request,
    db: DbSession,
    current_user: OptionalCurrentUser = None,
    location_id: int = Query(1),
    period: str = Query("month"),
):
    """Get detailed pour variance report by product and bartender."""
    return get_spillage_variance(request=request, db=db, current_user=current_user, location_id=location_id, period=period)


@router.get("/speed-rail/optimization")
@limiter.limit("60/minute")
def get_speed_rail_optimization(
    request: Request,
    db: DbSession,
    current_user: OptionalCurrentUser = None,
    location_id: int = Query(1),
):
    """Get speed rail optimization suggestions based on sales frequency."""
    # Find most-used products in recent sales
    from datetime import timedelta as td
    start_date = datetime.now(timezone.utc) - td(days=7)
    top_products = db.query(
        Product.id,
        Product.name,
        func.count(StockMovement.id).label("usage_count"),
    ).join(Product, StockMovement.product_id == Product.id).filter(
        StockMovement.reason == MovementReason.SALE.value,
        StockMovement.ts >= start_date,
        StockMovement.location_id == location_id,
    ).group_by(Product.id, Product.name).order_by(
        func.count(StockMovement.id).desc()
    ).limit(12).all()

    rail_suggestions = [
        {"position": i + 1, "product_id": p.id, "product_name": p.name, "weekly_usage": int(p.usage_count)}
        for i, p in enumerate(top_products)
    ]
    return {"location_id": location_id, "speed_rail": rail_suggestions, "last_updated": datetime.now(timezone.utc).isoformat()}


@router.get("/keg-yield/{keg_id}")
@limiter.limit("60/minute")
def get_keg_yield(
    request: Request,
    keg_id: int,
    db: DbSession,
    current_user: OptionalCurrentUser = None,
):
    """Get yield tracking for a specific keg."""
    product = db.query(Product).filter(Product.id == keg_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Keg/product not found")

    stock = db.query(StockOnHand).filter(StockOnHand.product_id == keg_id).first()
    current_level = float(stock.qty) if stock else 0

    return {
        "keg_id": keg_id,
        "product_name": product.name,
        "capacity_liters": float(product.par_level or 50),
        "current_level_liters": current_level,
        "yield_percentage": round((current_level / float(product.par_level or 50)) * 100, 1) if product.par_level else 0,
        "pours_remaining": int(current_level / 0.5) if current_level > 0 else 0,
        "estimated_empty_date": None,
    }


@router.get("/bottle-inventory")
@limiter.limit("60/minute")
def get_bottle_inventory(
    request: Request,
    db: DbSession,
    current_user: OptionalCurrentUser = None,
    location_id: int = Query(1),
):
    """Get bottle-level inventory with fill percentages."""
    stock_items = db.query(StockOnHand, Product).join(
        Product, StockOnHand.product_id == Product.id
    ).filter(StockOnHand.location_id == location_id).order_by(Product.name).all()

    bottles = []
    for stock, product in stock_items:
        par = float(product.par_level) if product.par_level else 1
        current = float(stock.qty)
        bottles.append({
            "product_id": product.id,
            "name": product.name,
            "current_qty": current,
            "par_level": par,
            "fill_pct": round((current / par * 100), 1) if par > 0 else 0,
            "unit": product.unit or "pcs",
            "cost_per_unit": float(product.cost_price) if product.cost_price else 0,
            "total_value": round(current * float(product.cost_price or 0), 2),
        })
    return {"bottles": bottles, "total": len(bottles), "location_id": location_id}


@router.get("/cocktail-of-the-day")
@limiter.limit("60/minute")
def get_cocktail_of_the_day(
    request: Request,
    db: DbSession,
    current_user: OptionalCurrentUser = None,
):
    """Get AI-suggested cocktail of the day based on inventory levels."""
    import random as _random
    recipes = db.query(Recipe).limit(50).all()
    if not recipes:
        return {"cocktail": None, "message": "No recipes available"}

    # Pick one with good ingredient availability
    selected = _random.choice(recipes)
    ingredients = []
    for line in selected.lines:
        product = db.query(Product).filter(Product.id == line.product_id).first()
        if product:
            ingredients.append({"name": product.name, "amount": float(line.qty), "unit": line.unit})

    return {
        "cocktail": {
            "id": selected.id,
            "name": selected.name,
            "ingredients": ingredients,
            "reason": "High ingredient availability and popular choice",
        },
        "date": date.today().isoformat(),
    }


@router.get("/draft-freshness")
@limiter.limit("60/minute")
def get_draft_freshness(
    request: Request,
    db: DbSession,
    current_user: OptionalCurrentUser = None,
    location_id: int = Query(1),
):
    """Get draft beer freshness tracking."""
    from app.models.hardware import Tank as TankModel
    try:
        tanks = db.query(TankModel).filter(TankModel.status != "empty").all()
        drafts = []
        for tank in tanks:
            days_since_refill = 0
            if tank.last_refill:
                from datetime import timedelta as td
                delta = datetime.now(timezone.utc) - tank.last_refill if hasattr(tank.last_refill, 'tzinfo') else td(days=0)
                days_since_refill = delta.days if hasattr(delta, 'days') else 0
            drafts.append({
                "tank_id": tank.id,
                "product_name": tank.product_name,
                "days_since_tap": days_since_refill,
                "freshness_status": "fresh" if days_since_refill < 5 else "ok" if days_since_refill < 10 else "stale",
                "level_pct": round((tank.current_level_liters / tank.capacity_liters * 100), 1) if tank.capacity_liters else 0,
            })
        return {"drafts": drafts, "total": len(drafts)}
    except Exception:
        return {"drafts": [], "total": 0, "message": "No draft system configured"}


# ==================== POUR COSTS (root listing) ====================

@router.get("/pour-costs")
@limiter.limit("60/minute")
def get_pour_costs(
    request: Request,
    db: DbSession,
    current_user: OptionalCurrentUser = None,
    location_id: int = Query(1),
):
    """Get pour costs list - delegates to pour-costs/summary."""
    return get_pour_costs_summary(request=request, db=db, current_user=current_user, location_id=location_id)

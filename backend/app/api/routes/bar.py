"""Bar management API routes - using real database data."""

from typing import Any, List, Optional, Union
from decimal import Decimal
from datetime import datetime, time, date, timezone

from fastapi import APIRouter, Query, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func

from app.core.rbac import CurrentUser, OptionalCurrentUser, RequireManager
from app.db.session import DbSession
from app.models.product import Product
from app.models.stock import StockOnHand, StockMovement, MovementReason
from app.models.recipe import Recipe, RecipeLine
from app.models.advanced_features import HappyHour, WasteTrackingEntry, WasteCategory
from app.models.hardware import BarTab

router = APIRouter()


# ==================== RESPONSE MODELS ====================

class BarStats(BaseModel):
    """Bar statistics - matches frontend expectations."""
    total_sales: float = 0.0
    total_cost: float = 0.0
    pour_cost_percentage: float = 0.0
    avg_ticket: float = 0.0
    top_cocktail: str = ""
    spillage_today: float = 0.0
    low_stock_items: int = 0
    active_recipes: int = 0
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


class SpillageRecordCreate(BaseModel):
    """Spillage record creation model."""
    item: Optional[str] = None
    item_name: Optional[str] = None  # Alias for compatibility
    product_id: Optional[int] = None
    quantity: float
    unit: str = "ml"
    reason: str
    recorded_by: Optional[str] = None
    notes: Optional[str] = None
    cost: float = 0.0


# ==================== ROUTES ====================

@router.get("/tabs")
def get_bar_tabs(
    db: DbSession,
    current_user: OptionalCurrentUser = None,
    status: Optional[str] = Query(None, description="Filter by status: open, closed, void"),
    location_id: Optional[int] = Query(None),
):
    """Get bar tabs from database."""
    query = db.query(BarTab)
    if status:
        query = query.filter(BarTab.status == status)
    else:
        # Default to open tabs
        query = query.filter(BarTab.status == "open")
    if location_id:
        query = query.filter(BarTab.location_id == location_id)

    tabs = query.order_by(BarTab.created_at.desc()).all()

    tab_list = [{
        "id": tab.id,
        "customer_name": tab.customer_name,
        "seat_number": tab.seat_number,
        "card_on_file": tab.card_on_file,
        "status": tab.status,
        "items": tab.items or [],
        "subtotal": float(tab.subtotal),
        "tax": float(tab.tax),
        "tip": float(tab.tip),
        "total": float(tab.total),
        "created_at": tab.created_at.isoformat() if tab.created_at else None,
        "closed_at": tab.closed_at.isoformat() if tab.closed_at else None,
    } for tab in tabs]

    return {"tabs": tab_list, "total": len(tab_list)}


@router.get("/spillage/variance")
def get_spillage_variance(
    db: DbSession,
    current_user: OptionalCurrentUser = None,
    location_id: int = Query(1),
    period: str = Query("month"),
):
    """Get spillage variance data - compares expected vs actual stock usage."""
    from datetime import timedelta

    now = datetime.now(timezone.utc)
    if period == "today":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start_date = now - timedelta(days=7)
    else:
        start_date = now - timedelta(days=30)

    # Get waste/spillage movements grouped by product
    waste_data = db.query(
        Product.id,
        Product.name,
        Product.unit,
        Product.cost_price,
        func.sum(StockMovement.qty_delta).label("waste_qty"),
    ).join(Product, StockMovement.product_id == Product.id).filter(
        StockMovement.reason == MovementReason.WASTE.value,
        StockMovement.ts >= start_date,
        StockMovement.location_id == location_id,
    ).group_by(Product.id, Product.name, Product.unit, Product.cost_price).all()

    # Get total sales movements for the same products to compute variance %
    sale_data = {}
    if waste_data:
        product_ids = [row.id for row in waste_data]
        sales = db.query(
            StockMovement.product_id,
            func.sum(StockMovement.qty_delta).label("sale_qty"),
        ).filter(
            StockMovement.reason == MovementReason.SALE.value,
            StockMovement.ts >= start_date,
            StockMovement.location_id == location_id,
            StockMovement.product_id.in_(product_ids),
        ).group_by(StockMovement.product_id).all()
        sale_data = {s.product_id: abs(float(s.sale_qty or 0)) for s in sales}

    variances = []
    total_variance_cost = 0.0

    for row in waste_data:
        waste_qty = abs(float(row.waste_qty or 0))
        sale_qty = sale_data.get(row.id, 0)
        cost = float(row.cost_price or 0)
        variance_cost = waste_qty * cost
        total_variance_cost += variance_cost

        # Variance percentage: waste as % of total usage (sales + waste)
        total_usage = sale_qty + waste_qty
        variance_pct = round((waste_qty / total_usage) * 100, 1) if total_usage > 0 else 0

        variances.append({
            "product_id": row.id,
            "product_name": row.name,
            "unit": row.unit or "pcs",
            "waste_qty": waste_qty,
            "sale_qty": sale_qty,
            "variance_pct": variance_pct,
            "variance_cost": round(variance_cost, 2),
        })

    # Sort by cost impact descending
    variances.sort(key=lambda x: x["variance_cost"], reverse=True)

    return {"variances": variances, "total_variance": round(total_variance_cost, 2)}


@router.get("/spillage/stats")
def get_spillage_stats(
    db: DbSession,
    current_user: OptionalCurrentUser = None,
    location_id: int = Query(1),
    period: str = Query("month"),
):
    """Get spillage statistics from waste tracking entries."""
    from datetime import timedelta

    now = datetime.now(timezone.utc)
    if period == "today":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start_date = now - timedelta(days=7)
    else:
        start_date = now - timedelta(days=30)

    # Aggregate totals
    totals = db.query(
        func.sum(WasteTrackingEntry.weight_kg).label("total_kg"),
        func.sum(WasteTrackingEntry.cost_value).label("total_cost"),
        func.count(WasteTrackingEntry.id).label("incidents"),
    ).filter(
        WasteTrackingEntry.location_id == location_id,
        WasteTrackingEntry.recorded_at >= start_date,
    ).first()

    total_spillage = float(totals.total_kg or 0)
    total_cost = float(totals.total_cost or 0)
    incidents = int(totals.incidents or 0)

    # Breakdown by waste category
    by_category_rows = db.query(
        WasteTrackingEntry.category,
        func.sum(WasteTrackingEntry.weight_kg).label("weight"),
        func.sum(WasteTrackingEntry.cost_value).label("cost"),
        func.count(WasteTrackingEntry.id).label("count"),
    ).filter(
        WasteTrackingEntry.location_id == location_id,
        WasteTrackingEntry.recorded_at >= start_date,
    ).group_by(WasteTrackingEntry.category).all()

    by_category = [{
        "category": row.category.value if hasattr(row.category, 'value') else str(row.category),
        "weight_kg": float(row.weight or 0),
        "cost": float(row.cost or 0),
        "count": int(row.count or 0),
    } for row in by_category_rows]

    return {
        "total_spillage": round(total_spillage, 3),
        "total_cost": round(total_cost, 2),
        "incidents": incidents,
        "by_category": by_category,
    }


@router.get("/pour-costs/summary")
def get_pour_costs_summary(
    db: DbSession,
    current_user: OptionalCurrentUser = None,
    location_id: int = Query(1),
):
    """Get pour cost summary computed from recipes and product costs."""
    from app.models.restaurant import MenuItem

    # Get all recipes with their ingredient costs
    recipes = db.query(Recipe).all()

    items = []
    total_pour_cost_sum = 0.0
    count_with_cost = 0
    category_map = {}  # category -> {total_cost, total_price, count}

    for recipe in recipes:
        pour_cost = Decimal("0")
        for line in recipe.lines:
            product = db.query(Product).filter(Product.id == line.product_id).first()
            if product and product.cost_price:
                pour_cost += Decimal(str(line.qty)) * product.cost_price

        # Try to find linked menu item for sell price
        sell_price = Decimal("0")
        category = "Uncategorized"
        menu_item = None
        if recipe.pos_item_id:
            menu_item = db.query(MenuItem).filter(MenuItem.id == int(recipe.pos_item_id)).first() if recipe.pos_item_id.isdigit() else None
        if not menu_item:
            menu_item = db.query(MenuItem).filter(MenuItem.recipe_id == recipe.id).first()
        if menu_item:
            sell_price = menu_item.price or Decimal("0")
            category = menu_item.category or "Uncategorized"

        pour_cost_pct = round(float(pour_cost / sell_price * 100), 1) if sell_price > 0 else 0

        items.append({
            "recipe_id": recipe.id,
            "name": recipe.name,
            "category": category,
            "pour_cost": float(pour_cost),
            "sell_price": float(sell_price),
            "pour_cost_pct": pour_cost_pct,
            "margin_pct": round(100 - pour_cost_pct, 1) if pour_cost_pct > 0 else 0,
        })

        if pour_cost_pct > 0:
            total_pour_cost_sum += pour_cost_pct
            count_with_cost += 1

        # Aggregate by category
        if category not in category_map:
            category_map[category] = {"total_cost": 0.0, "total_price": 0.0, "count": 0}
        category_map[category]["total_cost"] += float(pour_cost)
        category_map[category]["total_price"] += float(sell_price)
        category_map[category]["count"] += 1

    avg_pour_cost = round(total_pour_cost_sum / count_with_cost, 1) if count_with_cost > 0 else 0
    target_pour_cost = 25.0  # Industry standard target

    by_category = [{
        "category": cat,
        "avg_pour_cost_pct": round((data["total_cost"] / data["total_price"]) * 100, 1) if data["total_price"] > 0 else 0,
        "total_cost": round(data["total_cost"], 2),
        "total_revenue": round(data["total_price"], 2),
        "item_count": data["count"],
    } for cat, data in category_map.items()]

    # Sort items by pour cost descending (highest cost items first)
    items.sort(key=lambda x: x["pour_cost_pct"], reverse=True)

    return {
        "average_pour_cost": avg_pour_cost,
        "target_pour_cost": target_pour_cost,
        "items": items,
        "by_category": by_category,
    }


@router.get("/stats")
def get_bar_stats(
    db: DbSession,
    current_user: OptionalCurrentUser = None,
    period: str = Query("today"),
    location_id: int = Query(1),
):
    """Get bar statistics from real database data."""
    from datetime import timedelta

    # Calculate date range
    now = datetime.now(timezone.utc)
    if period == "today":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start_date = now - timedelta(days=7)
    elif period == "month":
        start_date = now - timedelta(days=30)
    else:
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Get sales movements (negative qty_delta for sales)
    sales_query = db.query(
        func.sum(StockMovement.qty_delta).label('total_qty')
    ).filter(
        StockMovement.reason == MovementReason.SALE.value,
        StockMovement.ts >= start_date,
        StockMovement.location_id == location_id
    ).first()

    total_sales_qty = abs(float(sales_query.total_qty or 0))

    # Get spillage/waste
    spillage_query = db.query(
        func.sum(WasteTrackingEntry.cost_value).label('total_cost')
    ).filter(
        WasteTrackingEntry.recorded_at >= start_date,
        WasteTrackingEntry.location_id == location_id
    ).first()

    spillage_today = float(spillage_query.total_cost or 0)

    # Count low stock items (below par level)
    low_stock_count = db.query(StockOnHand).join(Product).filter(
        StockOnHand.location_id == location_id,
        Product.par_level.isnot(None),
        StockOnHand.qty < Product.par_level
    ).count()

    # Count active recipes
    active_recipes = db.query(Recipe).count()

    # Compute total cost from stock movements
    cost_query = db.query(
        func.sum(StockMovement.qty_delta).label('total_qty')
    ).join(Product, StockMovement.product_id == Product.id).filter(
        StockMovement.reason == MovementReason.SALE.value,
        StockMovement.ts >= start_date,
        StockMovement.location_id == location_id
    ).first()

    # Compute revenue and cost from actual product prices
    sale_details = db.query(
        Product.cost_price,
        StockMovement.qty_delta,
    ).join(Product, StockMovement.product_id == Product.id).filter(
        StockMovement.reason == MovementReason.SALE.value,
        StockMovement.ts >= start_date,
        StockMovement.location_id == location_id
    ).all()

    total_cost = sum(
        abs(float(row.qty_delta)) * float(row.cost_price or 0)
        for row in sale_details
    )

    # Estimate revenue at 4x cost (standard bar markup) when no check data available
    total_revenue = total_cost * 4 if total_cost > 0 else 0

    pour_cost_pct = round((total_cost / total_revenue) * 100, 1) if total_revenue > 0 else 0

    # Find top selling product by movement count
    top_product = db.query(
        Product.name,
        func.count(StockMovement.id).label('sale_count')
    ).join(Product, StockMovement.product_id == Product.id).filter(
        StockMovement.reason == MovementReason.SALE.value,
        StockMovement.ts >= start_date,
        StockMovement.location_id == location_id
    ).group_by(Product.name).order_by(func.count(StockMovement.id).desc()).first()

    return {
        "total_sales": total_revenue,
        "total_cost": total_cost,
        "pour_cost_percentage": pour_cost_pct,
        "avg_ticket": 0,
        "top_cocktail": top_product.name if top_product else None,
        "spillage_today": spillage_today,
        "low_stock_items": low_stock_count,
        "active_recipes": active_recipes,
        "period": period,
    }


@router.get("/top-drinks")
def get_top_drinks(
    db: DbSession,
    current_user: OptionalCurrentUser = None,
    period: str = Query("today"),
    location_id: int = Query(1),
):
    """Get top selling drinks from sales data."""
    from datetime import timedelta
    from app.models.restaurant import MenuItem

    # Calculate date range
    now = datetime.now(timezone.utc)
    if period == "today":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start_date = now - timedelta(days=7)
    else:
        start_date = now - timedelta(days=30)

    # Get drink menu items with sales data
    drinks = db.query(MenuItem).filter(
        MenuItem.category.in_(["Cocktails", "Drinks", "Beverages", "Bar", "Wine", "Beer"])
    ).limit(10).all()

    results = []
    for drink in drinks:
        # Look up actual sales from stock movements via recipe linkage
        sale_count = 0
        revenue = 0.0
        drink_pour_cost = 0.0
        drink_margin = 0.0

        if drink.recipe_id:
            recipe = db.query(Recipe).filter(Recipe.id == drink.recipe_id).first()
            if recipe:
                pour_cost_val = Decimal("0")
                for line in recipe.lines:
                    product = db.query(Product).filter(Product.id == line.product_id).first()
                    if product and product.cost_price:
                        pour_cost_val += Decimal(str(line.qty)) * product.cost_price
                drink_pour_cost = round(float(pour_cost_val / drink.price * 100), 1) if drink.price and drink.price > 0 else 0
                drink_margin = round(100 - drink_pour_cost, 1)

        results.append({
            "id": drink.id,
            "name": drink.name,
            "category": drink.category or "Drinks",
            "sold_today": sale_count,
            "revenue": revenue,
            "pour_cost": drink_pour_cost,
            "margin": drink_margin,
        })

    return results


@router.get("/inventory-alerts")
def get_inventory_alerts(
    db: DbSession,
    current_user: OptionalCurrentUser = None,
    location_id: int = Query(1),
):
    """Get bar inventory alerts from real stock data."""
    # Get all products with par_level that are below threshold
    alerts = []

    stock_items = db.query(StockOnHand, Product).join(
        Product, StockOnHand.product_id == Product.id
    ).filter(
        StockOnHand.location_id == location_id,
        Product.par_level.isnot(None)
    ).all()

    for stock, product in stock_items:
        if product.par_level is None:
            continue

        current = float(stock.qty)
        par = float(product.par_level)

        if current >= par:
            continue  # Not an alert

        # Determine status
        ratio = current / par if par > 0 else 0
        if ratio < 0.25:
            status = "critical"
        elif ratio < 0.5:
            status = "low"
        else:
            status = "reorder"

        alerts.append({
            "id": product.id,
            "item_name": product.name,
            "current_stock": current,
            "par_level": par,
            "unit": product.unit or "pcs",
            "status": status,
        })

    # Sort by severity (critical first)
    status_order = {"critical": 0, "low": 1, "reorder": 2}
    alerts.sort(key=lambda x: status_order.get(x["status"], 3))

    return alerts


@router.get("/recent-activity")
def get_recent_activity(
    db: DbSession,
    current_user: OptionalCurrentUser = None,
    location_id: int = Query(1),
    limit: int = Query(10, le=50),
):
    """Get recent bar activity from stock movements."""
    from datetime import timedelta

    # Get recent stock movements
    movements = db.query(StockMovement, Product).join(
        Product, StockMovement.product_id == Product.id
    ).filter(
        StockMovement.location_id == location_id,
        StockMovement.reason.in_([MovementReason.SALE.value, MovementReason.WASTE.value, MovementReason.REFUND.value])
    ).order_by(StockMovement.ts.desc()).limit(limit).all()

    results = []
    now = datetime.now(timezone.utc)

    for movement, product in movements:
        # Calculate time ago - handle timezone-aware timestamps
        movement_ts = movement.ts
        if movement_ts.tzinfo is None:
            # Make naive timestamps timezone-aware for comparison
            movement_ts = movement_ts.replace(tzinfo=timezone.utc)
        diff = now - movement_ts
        if diff.seconds < 60:
            time_ago = "just now"
        elif diff.seconds < 3600:
            time_ago = f"{diff.seconds // 60} min ago"
        elif diff.seconds < 86400:
            time_ago = f"{diff.seconds // 3600} hours ago"
        else:
            time_ago = f"{diff.days} days ago"

        # Determine type
        if movement.reason == MovementReason.SALE.value:
            activity_type = "sale"
        elif movement.reason == MovementReason.WASTE.value:
            activity_type = "spillage"
        elif movement.reason == MovementReason.REFUND.value:
            activity_type = "comp"
        else:
            activity_type = "other"

        results.append({
            "id": movement.id,
            "drink_name": product.name,
            "bartender": None,
            "time": time_ago,
            "type": activity_type,
            "amount": f"{abs(float(movement.qty_delta)):.1f} {product.unit}",
            "cost": abs(float(movement.qty_delta) * float(product.cost_price or 0)),
        })

    return results


@router.get("/spillage/records")
def get_spillage_records(
    db: DbSession,
    current_user: OptionalCurrentUser = None,
    location_id: int = Query(1),
    limit: int = Query(20, le=100),
):
    """Get spillage records from waste tracking."""
    entries = db.query(WasteTrackingEntry).filter(
        WasteTrackingEntry.location_id == location_id
    ).order_by(WasteTrackingEntry.recorded_at.desc()).limit(limit).all()

    results = []
    for entry in entries:
        # Get product name if linked
        product_name = entry.ai_detected_item or "Unknown Item"
        if entry.product_id:
            product = db.query(Product).filter(Product.id == entry.product_id).first()
            if product:
                product_name = product.name

        results.append({
            "id": str(entry.id),
            "item": product_name,
            "item_name": product_name,
            "quantity": float(entry.weight_kg) * 1000,  # Convert kg to g
            "unit": "g",
            "reason": entry.reason or entry.category.value if entry.category else "spillage",
            "recorded_by": None,
            "timestamp": entry.recorded_at.isoformat() if entry.recorded_at else None,
            "cost": float(entry.cost_value),
        })

    return results


@router.post("/spillage/records")
def create_spillage_record(
    record: SpillageRecordCreate,
    db: DbSession,
    current_user: CurrentUser,
    location_id: int = Query(1),
):
    """Create a spillage record."""
    # Create waste tracking entry
    entry = WasteTrackingEntry(
        location_id=location_id,
        product_id=record.product_id,
        category=WasteCategory.DAMAGED,  # Default category for bar spillage
        weight_kg=Decimal(str(record.quantity / 1000)),  # Convert to kg
        cost_value=Decimal(str(record.cost)),
        reason=record.reason,
        ai_detected_item=record.item or record.item_name,
        recorded_at=datetime.now(timezone.utc),
    )
    db.add(entry)

    # Also create stock movement if product_id provided
    if record.product_id:
        movement = StockMovement(
            product_id=record.product_id,
            location_id=location_id,
            qty_delta=-Decimal(str(record.quantity)),
            reason=MovementReason.WASTE.value,
            notes=f"Spillage: {record.reason}",
        )
        db.add(movement)

        # Update stock on hand
        stock = db.query(StockOnHand).filter(
            StockOnHand.product_id == record.product_id,
            StockOnHand.location_id == location_id
        ).first()
        if stock:
            stock.qty -= Decimal(str(record.quantity))

    db.commit()
    db.refresh(entry)

    return {
        "success": True,
        "id": str(entry.id),
        "item": record.item or record.item_name,
        "quantity": record.quantity,
        "unit": record.unit,
        "reason": record.reason,
        "cost": record.cost,
        "timestamp": entry.recorded_at.isoformat(),
    }


# ==================== RECIPES (using real Recipe model) ====================

@router.post("/recipes")
def create_bar_recipe(
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
def get_bar_recipes(
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
def get_bar_inventory(
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
def record_inventory_count(
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
def get_happy_hours(
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
def get_happy_hours_stats(
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
def get_happy_hour(
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
def create_happy_hour(
    data: HappyHourCreate,
    db: DbSession,
    current_user: RequireManager,
    location_id: Optional[int] = Query(None),
):
    """Create a new happy hour promotion."""
    # Parse times
    start_parts = data.start_time.split(":")
    end_parts = data.end_time.split(":")

    hh = HappyHour(
        location_id=location_id,
        name=data.name,
        description=data.description,
        days=data.days,
        start_time=time(int(start_parts[0]), int(start_parts[1])),
        end_time=time(int(end_parts[0]), int(end_parts[1])),
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
def update_happy_hour(
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
def delete_happy_hour(
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
def toggle_happy_hour(
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
def get_cocktails(db: DbSession, current_user: OptionalCurrentUser = None):
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

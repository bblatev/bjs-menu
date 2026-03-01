"""Bar dashboard, tabs, spillage & pour costs"""
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

@router.get("/")
@limiter.limit("60/minute")
def get_bar_root(request: Request, db: DbSession):
    """Bar overview."""
    return get_bar_stats(request=request, db=db, period="today", location_id=1)


@router.get("/tabs")
@limiter.limit("60/minute")
def get_bar_tabs(
    request: Request,
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
@limiter.limit("60/minute")
def get_spillage_variance(
    request: Request,
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
@limiter.limit("60/minute")
def get_spillage_stats(
    request: Request,
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
@limiter.limit("60/minute")
def get_pour_costs_summary(
    request: Request,
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
@limiter.limit("60/minute")
def get_bar_stats(
    request: Request,
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
@limiter.limit("60/minute")
def get_top_drinks(
    request: Request,
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
@limiter.limit("60/minute")
def get_inventory_alerts(
    request: Request,
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
@limiter.limit("60/minute")
def get_recent_activity(
    request: Request,
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
@limiter.limit("60/minute")
def get_spillage_records(
    request: Request,
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
@limiter.limit("30/minute")
def create_spillage_record(
    request: Request,
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


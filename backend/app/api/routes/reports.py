"""Reporting routes."""


import csv
import io
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query, Body, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.rbac import CurrentUser, OptionalCurrentUser
from app.db.session import DbSession
from app.models.location import Location
from app.models.product import Product
from app.models.stock import StockMovement, StockOnHand
from app.core.rate_limit import limiter

router = APIRouter()


@router.get("/sales")
@limiter.limit("60/minute")
def get_sales_report(
    request: Request,
    db: DbSession,
    current_user: OptionalCurrentUser = None,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    """Get sales report from daily metrics."""
    from sqlalchemy import func
    from app.models.analytics import DailyMetrics

    query = db.query(DailyMetrics)
    if start_date:
        query = query.filter(DailyMetrics.date >= start_date)
    if end_date:
        query = query.filter(DailyMetrics.date <= end_date)
    metrics = query.order_by(DailyMetrics.date.desc()).limit(30).all()
    revenue = sum(float(m.total_revenue or 0) for m in metrics)
    orders = sum(int(m.total_orders or 0) for m in metrics)
    avg_ticket = round(revenue / orders, 2) if orders > 0 else 0

    # Build dailySales from metrics
    daily_sales = []
    for m in reversed(metrics):
        day_rev = float(m.total_revenue or 0)
        day_orders = int(m.total_orders or 0)
        daily_sales.append({
            "date": m.date.isoformat() if hasattr(m.date, 'isoformat') else str(m.date),
            "revenue": round(day_rev, 2),
            "orders": day_orders,
            "avgTicket": round(day_rev / day_orders, 2) if day_orders > 0 else 0,
        })

    return {
        "stats": [
            {"label": "Total Revenue", "value": f"{revenue:,.2f}", "subvalue": f"{len(metrics)} days", "change": "+0%", "up": True, "color": "green"},
            {"label": "Total Orders", "value": str(orders), "subvalue": f"{len(metrics)} days", "change": "+0%", "up": True, "color": "blue"},
            {"label": "Avg Ticket", "value": f"{avg_ticket:.2f}", "subvalue": "per order", "change": "+0%", "up": True, "color": "purple"},
            {"label": "Items Sold", "value": "0", "subvalue": "total", "change": "+0%", "up": True, "color": "orange"},
        ],
        "dailySales": daily_sales,
        "topItems": [],
        "categoryBreakdown": [],
        "revenueByTime": [],
    }


@router.get("/staff")
@limiter.limit("60/minute")
def get_staff_report(
    request: Request,
    db: DbSession,
    current_user: OptionalCurrentUser = None,
):
    """Get staff report from staff_users table."""
    from app.models.staff import StaffUser
    staff = db.query(StaffUser).order_by(StaffUser.full_name).all()
    return {
        "staff": [{"id": s.id, "name": s.full_name, "role": s.role, "active": s.is_active} for s in staff],
        "total": len(staff),
    }


@router.get("/staff-performance")
@limiter.limit("60/minute")
def get_staff_performance_report(
    request: Request,
    db: DbSession,
    current_user: OptionalCurrentUser = None,
):
    """Get staff performance report."""
    from app.models.staff import StaffUser
    staff = db.query(StaffUser).order_by(StaffUser.full_name).all()
    return {
        "staff": [{"id": s.id, "name": s.full_name, "role": s.role} for s in staff],
        "average_rating": 0,
    }


@router.get("/kitchen")
@limiter.limit("60/minute")
def get_kitchen_report(
    request: Request,
    db: DbSession,
    current_user: OptionalCurrentUser = None,
    range: Optional[str] = Query("today"),
):
    """Get kitchen performance report from kitchen orders."""
    from sqlalchemy import func
    from app.models.restaurant import KitchenOrder

    completed = db.query(func.count(KitchenOrder.id)).filter(KitchenOrder.status == "completed").scalar() or 0
    overdue = db.query(func.count(KitchenOrder.id)).filter(KitchenOrder.status == "overdue").scalar() or 0
    by_station = dict(
        db.query(KitchenOrder.station, func.count(KitchenOrder.id))
        .filter(KitchenOrder.status == "completed")
        .group_by(KitchenOrder.station)
        .all()
    )

    # Find busiest station
    busiest = max(by_station.items(), key=lambda x: x[1], default=(None, 0))

    station_performance = []
    for station, count in by_station.items():
        station_performance.append({
            "id": station or "default",
            "name": (station or "Main").title(),
            "icon": "🍳",
            "ticketsCompleted": count,
            "avgPrepTime": 0,
            "targetTime": 15,
            "overdueRate": 0,
            "efficiency": 100 if count > 0 else 0,
        })

    return {
        "metrics": {
            "avgPrepTime": 0,
            "avgPrepTimeTarget": 15,
            "ticketsCompleted": completed,
            "itemsCompleted": completed,
            "overdueTickets": overdue,
            "overdueRate": round(overdue / completed * 100, 1) if completed > 0 else 0,
            "peakHour": "12:00-13:00",
            "busiestStation": (busiest[0] or "Main").title() if busiest[0] else "N/A",
            "efficiency": 100 if completed > 0 else 0,
        },
        "stationPerformance": station_performance,
        "hourlyData": [],
        "topItems": [],
        "staffPerformance": [],
    }


@router.get("/inventory")
@limiter.limit("60/minute")
def get_inventory_report(
    request: Request,
    db: DbSession,
    current_user: OptionalCurrentUser = None,
):
    """Get inventory report from stock and products."""
    from sqlalchemy import func

    items_count = db.query(func.count(Product.id)).scalar() or 0
    stock_rows = db.query(StockOnHand).all()
    total_value = sum(float(s.qty or 0) for s in stock_rows)
    low_stock = [
        {"product_id": s.product_id, "qty": float(s.qty or 0), "location_id": s.location_id}
        for s in stock_rows if (s.qty or 0) < 5 and (s.qty or 0) > 0
    ]
    return {"total_value": round(total_value, 2), "items_count": items_count, "low_stock": low_stock[:20], "movements": []}


@router.get("/customers")
@limiter.limit("60/minute")
def get_customers_report(
    request: Request,
    db: DbSession,
    current_user: OptionalCurrentUser = None,
):
    """Get customers report from customer table."""
    from sqlalchemy import func
    from app.models.customer import Customer
    total = db.query(func.count(Customer.id)).scalar() or 0
    return {"total": total, "new_this_month": 0, "returning": 0, "segments": []}


@router.get("/customer-insights")
@limiter.limit("60/minute")
def get_customer_insights_report(
    request: Request,
    db: DbSession,
    current_user: OptionalCurrentUser = None,
):
    """Get customer insights from customer table."""
    from app.models.customer import Customer
    customers = db.query(Customer).order_by(Customer.total_spent.desc()).limit(20).all()
    top_spenders = [
        {"id": c.id, "name": c.name, "total_spent": float(c.total_spent or 0), "visit_count": c.visit_count or 0}
        for c in customers if (c.total_spent or 0) > 0
    ]
    return {"top_spenders": top_spenders, "frequency": [], "preferences": []}


@router.get("/stock-valuation")
@limiter.limit("60/minute")
def get_stock_valuation(
    request: Request,
    db: DbSession,
    current_user: OptionalCurrentUser = None,
    location_id: Optional[int] = Query(None),
):
    """
    Get stock valuation report.

    Returns current stock quantities and values by product.
    """
    query = db.query(StockOnHand)
    if location_id:
        query = query.filter(StockOnHand.location_id == location_id)

    stock_items = query.all()

    items = []
    total_value = Decimal("0")

    for stock in stock_items:
        product = db.query(Product).filter(Product.id == stock.product_id).first()
        if not product:
            continue

        value = stock.qty * (product.cost_price or Decimal("0"))
        total_value += value

        items.append({
            "product_id": product.id,
            "product_name": product.name,
            "location_id": stock.location_id,
            "quantity": float(stock.qty),
            "unit": product.unit,
            "cost_price": float(product.cost_price or 0),
            "total_value": float(value),
        })

    # Sort by value descending
    items.sort(key=lambda x: x["total_value"], reverse=True)

    return {
        "items": items,
        "total_value": float(total_value),
        "item_count": len(items),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/consumption")
@limiter.limit("60/minute")
def get_consumption_report(
    request: Request,
    db: DbSession,
    current_user: OptionalCurrentUser = None,
    location_id: Optional[int] = Query(None),
    days: int = Query(7, ge=1, le=90),
):
    """
    Get consumption report for the specified period.

    Shows products consumed through POS sales.
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)

    query = db.query(StockMovement).filter(
        StockMovement.ts >= since,
        StockMovement.reason == "sale",
    )
    if location_id:
        query = query.filter(StockMovement.location_id == location_id)

    movements = query.all()

    # Aggregate by product
    consumption: dict = {}
    for mv in movements:
        pid = mv.product_id
        if pid not in consumption:
            product = db.query(Product).filter(Product.id == pid).first()
            consumption[pid] = {
                "product_id": pid,
                "product_name": product.name if product else f"Product {pid}",
                "unit": product.unit if product else "unit",
                "cost_price": float(product.cost_price or 0) if product else 0,
                "quantity": 0,
                "value": 0,
                "transactions": 0,
            }

        qty = abs(float(mv.qty_delta))
        consumption[pid]["quantity"] += qty
        consumption[pid]["value"] += qty * consumption[pid]["cost_price"]
        consumption[pid]["transactions"] += 1

    items = list(consumption.values())
    items.sort(key=lambda x: x["value"], reverse=True)

    total_value = sum(item["value"] for item in items)
    total_qty = sum(item["quantity"] for item in items)

    return {
        "period_days": days,
        "since": since.isoformat(),
        "items": items,
        "total_value": total_value,
        "total_transactions": sum(item["transactions"] for item in items),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/movement-summary")
@limiter.limit("60/minute")
def get_movement_summary(
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
    location_id: Optional[int] = Query(None),
    days: int = Query(7, ge=1, le=90),
):
    """
    Get stock movement summary by reason.
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)

    query = db.query(StockMovement).filter(StockMovement.ts >= since)
    if location_id:
        query = query.filter(StockMovement.location_id == location_id)

    movements = query.all()

    # Aggregate by reason
    by_reason: dict = {}
    for mv in movements:
        reason = mv.reason or "unknown"
        if reason not in by_reason:
            by_reason[reason] = {
                "reason": reason,
                "count": 0,
                "total_in": 0,
                "total_out": 0,
            }

        by_reason[reason]["count"] += 1
        qty = float(mv.qty_delta)
        if qty > 0:
            by_reason[reason]["total_in"] += qty
        else:
            by_reason[reason]["total_out"] += abs(qty)

    return {
        "period_days": days,
        "since": since.isoformat(),
        "by_reason": list(by_reason.values()),
        "total_movements": len(movements),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/low-stock")
@limiter.limit("60/minute")
def get_low_stock_report(
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
    location_id: int = Query(1, description="Location ID"),
):
    """
    Get detailed low stock report with reorder recommendations.
    """
    products = db.query(Product).filter(Product.active == True).all()

    items = []
    total_reorder_value = Decimal("0")

    for product in products:
        stock = db.query(StockOnHand).filter(
            StockOnHand.product_id == product.id,
            StockOnHand.location_id == location_id,
        ).first()

        current_qty = stock.qty if stock else Decimal("0")

        if current_qty < product.target_stock:
            reorder_qty = product.target_stock - current_qty
            reorder_value = reorder_qty * (product.cost_price or Decimal("0"))
            total_reorder_value += reorder_value

            # Determine urgency
            if current_qty <= product.min_stock * Decimal("0.5"):
                urgency = "critical"
            elif current_qty <= product.min_stock:
                urgency = "urgent"
            else:
                urgency = "normal"

            items.append({
                "product_id": product.id,
                "product_name": product.name,
                "supplier_id": product.supplier_id,
                "current_stock": float(current_qty),
                "min_stock": float(product.min_stock),
                "target_stock": float(product.target_stock),
                "reorder_qty": float(reorder_qty),
                "unit": product.unit,
                "pack_size": product.pack_size,
                "cost_price": float(product.cost_price or 0),
                "reorder_value": float(reorder_value),
                "urgency": urgency,
                "lead_time_days": product.lead_time_days,
            })

    # Sort by urgency then by reorder value
    urgency_order = {"critical": 0, "urgent": 1, "normal": 2}
    items.sort(key=lambda x: (urgency_order[x["urgency"]], -x["reorder_value"]))

    return {
        "location_id": location_id,
        "items": items,
        "total_items": len(items),
        "critical_count": len([i for i in items if i["urgency"] == "critical"]),
        "urgent_count": len([i for i in items if i["urgency"] == "urgent"]),
        "total_reorder_value": float(total_reorder_value),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ==================== ADDITIONAL REPORT ENDPOINTS ====================

@router.get("/food-costs")
@limiter.limit("60/minute")
def get_food_costs_report(
    request: Request,
    db: DbSession,
    location_id: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    """
    Get food cost analysis report.
    Shows actual vs theoretical food costs.
    """
    return {
        "period": {
            "start": start_date or (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d"),
            "end": end_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        },
        "summary": {
            "total_sales": 0,
            "total_food_cost": 0,
            "food_cost_percentage": 0,
            "target_percentage": 0,
            "variance": 0,
            "theoretical_cost": 0,
            "actual_vs_theoretical": 0,
        },
        "by_category": [],
        "top_variances": [],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/labor-costs")
@limiter.limit("60/minute")
def get_labor_costs_report(
    request: Request,
    db: DbSession,
    location_id: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    """
    Get labor cost analysis report.
    """
    return {
        "period": {
            "start": start_date or (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d"),
            "end": end_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        },
        "summary": {
            "total_sales": 0,
            "total_labor_cost": 0,
            "labor_cost_percentage": 0,
            "target_percentage": 0,
            "total_hours": 0,
            "average_hourly_rate": 0,
            "overtime_hours": 0,
            "overtime_cost": 0,
        },
        "by_department": [],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/sales/detailed")
@limiter.limit("60/minute")
def get_detailed_sales_report(
    request: Request,
    db: DbSession,
    location_id: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    group_by: str = Query("day"),
):
    """
    Get detailed sales report with breakdowns.
    """
    return {
        "period": {
            "start": start_date or (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d"),
            "end": end_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        },
        "summary": {
            "total_sales": 0,
            "total_orders": 0,
            "average_order_value": 0,
            "total_guests": 0,
            "average_per_guest": 0,
            "tips": 0,
            "discounts": 0,
            "net_sales": 0,
        },
        "by_category": [],
        "top_items": [],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/server-performance")
@limiter.limit("60/minute")
def get_server_performance_report(
    request: Request,
    db: DbSession,
    location_id: Optional[int] = Query(None),
):
    """
    Get server/staff performance report.
    """
    return {
        "servers": [],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/voids-comps")
@limiter.limit("60/minute")
def get_voids_comps_report(
    request: Request,
    db: DbSession,
    location_id: Optional[int] = Query(None),
):
    """
    Get voids and comps report.
    """
    return {
        "summary": {
            "total_voids": 0,
            "void_percentage": 0,
            "total_comps": 0,
            "comp_percentage": 0,
        },
        "voids": [],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/product-mix")
@limiter.limit("60/minute")
def get_product_mix_report(
    request: Request,
    db: DbSession,
    location_id: Optional[int] = Query(None),
):
    """
    Get product mix analysis report.
    """
    return {
        "total_items_sold": 0,
        "total_revenue": 0,
        "categories": [],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/trends")
@limiter.limit("60/minute")
def get_trends_report(
    request: Request,
    db: DbSession,
    location_id: Optional[int] = Query(None),
    period: str = Query("week"),
):
    """
    Get sales and operational trends.
    """
    return {
        "period": period,
        "sales_trend": [],
        "comparison": {
            "current_period_sales": 0,
            "previous_period_sales": 0,
            "change_percentage": 0,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/stock")
@limiter.limit("60/minute")
def get_stock_report(
    request: Request,
    db: DbSession,
    current_user: OptionalCurrentUser = None,
    location_id: Optional[int] = Query(None),
):
    """Get stock report."""
    return {"total_items": 0, "total_value": 0, "low_stock_count": 0, "out_of_stock_count": 0, "by_category": [], "generated_at": datetime.now(timezone.utc).isoformat()}


@router.get("/financial")
@limiter.limit("60/minute")
def get_financial_report(
    request: Request,
    db: DbSession,
    current_user: OptionalCurrentUser = None,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    """Get financial report."""
    return {
        "revenue": 0, "expenses": 0, "profit": 0, "food_cost_pct": 0,
        "labor_cost_pct": 0, "prime_cost_pct": 0,
        "by_category": [], "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/transactions")
@limiter.limit("60/minute")
def get_transactions_report(
    request: Request,
    db: DbSession,
    current_user: OptionalCurrentUser = None,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(50),
):
    """Get transactions report."""
    return {"transactions": [], "total": 0, "generated_at": datetime.now(timezone.utc).isoformat()}


# ==================== TURNOVER AT BASE PRICES ====================

@router.get("/turnover-base-prices")
@limiter.limit("60/minute")
def get_turnover_base_prices_report(
    request: Request,
    db: DbSession,
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    location_id: Optional[int] = Query(None),
    category: Optional[str] = Query(None),
):
    """
    Turnover at Base Prices Report (TouchSale Gap 13).

    Shows revenue at selling prices vs base/cost prices.
    Useful for understanding true markup and gross profit margin.

    - actual_revenue: Sum of sales at selling price
    - base_revenue: Sum of sales at base/cost price
    - markup_amount: Difference (actual - base)
    - markup_percentage: Markup as percentage of base
    - gross_margin: Markup as percentage of actual
    """
    from app.models.restaurant import Check, CheckItem, MenuItem
    from datetime import timedelta

    if not start_date:
        start_date = (datetime.now(timezone.utc).date() - timedelta(days=30)).strftime("%Y-%m-%d")
    if not end_date:
        end_date = datetime.now(timezone.utc).date().strftime("%Y-%m-%d")
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    # Query closed checks within date range
    check_query = db.query(Check).filter(
        Check.status == "closed",
        Check.closed_at >= start,
        Check.closed_at <= end,
    )

    if location_id:
        check_query = check_query.filter(Check.location_id == location_id)

    checks = check_query.all()
    check_ids = [c.id for c in checks]

    if not check_ids:
        return {
            "period": {"start_date": start_date, "end_date": end_date},
            "summary": {
                "actual_revenue": 0,
                "base_revenue": 0,
                "markup_amount": 0,
                "markup_percentage": 0,
                "gross_margin_percentage": 0,
                "total_items_sold": 0,
                "total_checks": 0,
            },
            "by_category": [],
            "by_item": [],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    # Get check items
    items_query = db.query(CheckItem).filter(
        CheckItem.check_id.in_(check_ids),
        CheckItem.status != "voided",
    )
    check_items = items_query.all()

    # Build menu item lookup with base prices
    menu_item_ids = list(set(ci.menu_item_id for ci in check_items if ci.menu_item_id))
    menu_items_map = {}
    if menu_item_ids:
        menu_items = db.query(MenuItem).filter(MenuItem.id.in_(menu_item_ids)).all()
        menu_items_map = {mi.id: mi for mi in menu_items}

    # Calculate totals
    total_actual = Decimal("0")
    total_base = Decimal("0")
    total_items = 0
    by_category_data: dict = {}
    by_item_data: dict = {}

    for ci in check_items:
        actual_price = ci.total or (ci.price * ci.quantity)
        total_actual += actual_price
        total_items += ci.quantity

        # Get base price from menu item
        base_price = Decimal("0")
        item_category = "Other"

        if ci.menu_item_id and ci.menu_item_id in menu_items_map:
            mi = menu_items_map[ci.menu_item_id]
            base_price = (mi.base_price or mi.price * Decimal("0.35")) * ci.quantity  # Default 35% cost if no base
            item_category = mi.category or "Other"
        else:
            # Estimate 35% cost if no menu item link
            base_price = actual_price * Decimal("0.35")

        # Filter by category if specified
        if category and item_category != category:
            continue

        total_base += base_price

        # Aggregate by category
        if item_category not in by_category_data:
            by_category_data[item_category] = {
                "category": item_category,
                "actual_revenue": Decimal("0"),
                "base_revenue": Decimal("0"),
                "items_sold": 0,
            }
        by_category_data[item_category]["actual_revenue"] += actual_price
        by_category_data[item_category]["base_revenue"] += base_price
        by_category_data[item_category]["items_sold"] += ci.quantity

        # Aggregate by item
        item_name = ci.name
        if item_name not in by_item_data:
            by_item_data[item_name] = {
                "name": item_name,
                "actual_revenue": Decimal("0"),
                "base_revenue": Decimal("0"),
                "quantity_sold": 0,
            }
        by_item_data[item_name]["actual_revenue"] += actual_price
        by_item_data[item_name]["base_revenue"] += base_price
        by_item_data[item_name]["quantity_sold"] += ci.quantity

    # Calculate markup
    markup_amount = total_actual - total_base
    markup_pct = (markup_amount / total_base * 100) if total_base > 0 else Decimal("0")
    gross_margin_pct = (markup_amount / total_actual * 100) if total_actual > 0 else Decimal("0")

    # Format category data
    categories = []
    for cat_data in by_category_data.values():
        cat_markup = cat_data["actual_revenue"] - cat_data["base_revenue"]
        cat_margin = (cat_markup / cat_data["actual_revenue"] * 100) if cat_data["actual_revenue"] > 0 else 0
        categories.append({
            "category": cat_data["category"],
            "actual_revenue": float(cat_data["actual_revenue"]),
            "base_revenue": float(cat_data["base_revenue"]),
            "markup_amount": float(cat_markup),
            "gross_margin_percentage": float(cat_margin),
            "items_sold": cat_data["items_sold"],
        })
    categories.sort(key=lambda x: x["actual_revenue"], reverse=True)

    # Format item data (top 20)
    items = []
    for item_data in by_item_data.values():
        item_markup = item_data["actual_revenue"] - item_data["base_revenue"]
        item_margin = (item_markup / item_data["actual_revenue"] * 100) if item_data["actual_revenue"] > 0 else 0
        items.append({
            "name": item_data["name"],
            "actual_revenue": float(item_data["actual_revenue"]),
            "base_revenue": float(item_data["base_revenue"]),
            "markup_amount": float(item_markup),
            "gross_margin_percentage": float(item_margin),
            "quantity_sold": item_data["quantity_sold"],
        })
    items.sort(key=lambda x: x["actual_revenue"], reverse=True)
    items = items[:20]  # Top 20 items

    return {
        "period": {"start_date": start_date, "end_date": end_date},
        "summary": {
            "actual_revenue": float(total_actual),
            "base_revenue": float(total_base),
            "markup_amount": float(markup_amount),
            "markup_percentage": float(markup_pct),
            "gross_margin_percentage": float(gross_margin_pct),
            "total_items_sold": total_items,
            "total_checks": len(checks),
        },
        "by_category": categories,
        "by_item": items,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/export/{report_type}")
@limiter.limit("30/minute")
def export_report(
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
    report_type: str,
    format: str = Body(..., embed=True),
    period: str = Body("week", embed=True),
):
    """
    Export report in requested format (csv, excel).
    
    Supported report types: sales, inventory, financial, customers, staff
    """
    # Calculate date range based on period
    end_date = datetime.now(timezone.utc).date()
    if period == "day":
        start_date = end_date
    elif period == "week":
        start_date = end_date - timedelta(days=7)
    elif period == "month":
        start_date = end_date - timedelta(days=30)
    elif period == "quarter":
        start_date = end_date - timedelta(days=90)
    elif period == "year":
        start_date = end_date - timedelta(days=365)
    else:
        start_date = end_date - timedelta(days=7)

    # Generate report data based on type
    if report_type == "sales":
        data = _generate_sales_export(db, start_date, end_date)
        headers = ["Date", "Order ID", "Items", "Total", "Payment Method"]
    elif report_type == "inventory":
        data = _generate_inventory_export(db)
        headers = ["Product", "SKU", "Quantity", "Unit", "Value"]
    elif report_type == "staff":
        data = _generate_staff_export(db, start_date, end_date)
        headers = ["Staff Name", "Role", "Hours Worked", "Sales Total"]
    else:
        data = []
        headers = ["No data available"]

    # Generate CSV response
    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        for row in data:
            writer.writerow(row)
        output.seek(0)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={report_type}_report_{end_date}.csv"
            }
        )
    
    # Default: return JSON
    return {
        "report_type": report_type,
        "period": {"start": str(start_date), "end": str(end_date)},
        "headers": headers,
        "data": data,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }


def _generate_sales_export(db, start_date, end_date):
    """Generate sales data for export."""
    from app.models.pos import PosSalesLine
    
    sales = db.query(PosSalesLine).filter(
        PosSalesLine.ts >= datetime.combine(start_date, datetime.min.time()),
        PosSalesLine.ts <= datetime.combine(end_date, datetime.max.time())
    ).limit(1000).all()
    
    return [
        [str(s.ts.date()), s.order_ref or "", s.product_name or "", float(s.total or 0), s.payment_type or ""]
        for s in sales
    ]


def _generate_inventory_export(db):
    """Generate inventory data for export."""
    from app.models.stock import StockOnHand
    from app.models.product import Product
    
    stock = db.query(StockOnHand).limit(1000).all()
    result = []
    for s in stock:
        product = db.query(Product).filter(Product.id == s.product_id).first()
        if product:
            value = float(s.qty or 0) * float(product.cost_price or 0)
            result.append([product.name, product.sku or "", float(s.qty or 0), product.unit or "", value])
    return result


def _generate_staff_export(db, start_date, end_date):
    """Generate staff data for export."""
    from app.models.staff import StaffUser, TimeClockEntry

    staff = db.query(StaffUser).filter(StaffUser.is_active == True).all()
    result = []
    for s in staff:
        entries = db.query(TimeClockEntry).filter(
            TimeClockEntry.staff_id == s.id,
            TimeClockEntry.clock_in >= datetime.combine(start_date, datetime.min.time()),
            TimeClockEntry.clock_in <= datetime.combine(end_date, datetime.max.time())
        ).all()
        total_hours = sum(e.total_hours or 0 for e in entries)
        result.append([s.full_name, s.role, total_hours, 0])  # Sales total would need POS data
    return result


# ==================== MERGED FROM reports_enhanced.py ====================
# The following endpoints were unique to reports_enhanced.py and have been
# preserved here.  The /reports-enhanced prefix is kept via a backward-compat
# mount in __init__.py.
# ========================================================================

class KPIMetric(BaseModel):
    name: str
    value: float
    target: Optional[float] = None
    unit: Optional[str] = None
    change_percentage: Optional[float] = None
    change_direction: Optional[str] = None
    status: str = "normal"


def _enhanced_get_date_range(
    period: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """Get date range for enhanced report period."""
    now = datetime.now(timezone.utc)

    if period == "custom" and start_date and end_date:
        return datetime.fromisoformat(start_date), datetime.fromisoformat(end_date)

    if period == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now
    elif period == "yesterday":
        yesterday = now - timedelta(days=1)
        start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period == "week":
        start = now - timedelta(days=7)
        end = now
    elif period == "month":
        start = now - timedelta(days=30)
        end = now
    elif period == "quarter":
        start = now - timedelta(days=90)
        end = now
    elif period == "year":
        start = now - timedelta(days=365)
        end = now
    else:
        start = now - timedelta(days=7)
        end = now

    return start, end


@router.get("/enhanced-root")
@limiter.limit("60/minute")
def get_reports_enhanced_root(request: Request, db: DbSession):
    """Enhanced reports overview (formerly GET /reports-enhanced/)."""
    return _enhanced_detailed_sales(request=request, db=db)


def _enhanced_detailed_sales(
    request: Request,
    db: DbSession,
    period: str = "week",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """Internal helper: enhanced detailed sales used by the enhanced root endpoint."""
    start, end = _enhanced_get_date_range(period, start_date, end_date)

    from app.models.analytics import DailyMetrics

    metrics = db.query(DailyMetrics).filter(
        DailyMetrics.date >= start.strftime("%Y-%m-%d"),
        DailyMetrics.date <= end.strftime("%Y-%m-%d"),
    ).order_by(DailyMetrics.date.desc()).all()

    total_revenue = sum(float(m.total_revenue or 0) for m in metrics)
    total_orders = sum(int(m.total_orders or 0) for m in metrics)
    avg_order_value = round(total_revenue / total_orders, 2) if total_orders > 0 else 0

    daily_breakdown = []
    for m in metrics:
        day_rev = float(m.total_revenue or 0)
        day_orders = int(m.total_orders or 0)
        daily_breakdown.append({
            "date": str(m.date),
            "orders_count": day_orders,
            "revenue": round(day_rev, 2),
            "average_order_value": round(day_rev / day_orders, 2) if day_orders > 0 else 0,
        })

    period_length = (end - start).days or 1
    prev_start = start - timedelta(days=period_length)
    prev_end = start

    prev_metrics = db.query(DailyMetrics).filter(
        DailyMetrics.date >= prev_start.strftime("%Y-%m-%d"),
        DailyMetrics.date < prev_end.strftime("%Y-%m-%d"),
    ).all()

    prev_revenue = sum(float(m.total_revenue or 0) for m in prev_metrics)
    revenue_growth = ((total_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0

    return {
        "period": period,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "total_revenue": round(total_revenue, 2),
        "total_orders": total_orders,
        "average_order_value": avg_order_value,
        "daily_breakdown": daily_breakdown,
        "revenue_growth": round(revenue_growth, 2),
        "hourly_breakdown": [],
        "category_breakdown": [],
        "top_selling_items": [],
    }


@router.get("/dashboard/kpis")
@limiter.limit("60/minute")
def get_dashboard_kpis(
    request: Request,
    db: DbSession,
    current_user: OptionalCurrentUser = None,
):
    """Get real-time dashboard KPIs."""
    from app.models.analytics import DailyMetrics

    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")
    yesterday_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")

    today_metric = db.query(DailyMetrics).filter(DailyMetrics.date == today_str).first()
    yesterday_metric = db.query(DailyMetrics).filter(DailyMetrics.date == yesterday_str).first()

    today_revenue = float(today_metric.total_revenue or 0) if today_metric else 0
    today_orders = int(today_metric.total_orders or 0) if today_metric else 0
    today_aov = round(today_revenue / today_orders, 2) if today_orders > 0 else 0

    yesterday_revenue = float(yesterday_metric.total_revenue or 0) if yesterday_metric else 0

    revenue_change = ((today_revenue - yesterday_revenue) / yesterday_revenue * 100) if yesterday_revenue > 0 else 0

    return {
        "timestamp": now.isoformat(),
        "period": "today",
        "total_revenue": {
            "name": "Total Revenue",
            "value": today_revenue,
            "change_percentage": round(revenue_change, 2),
            "change_direction": "up" if revenue_change > 0 else "down",
            "status": "good" if today_revenue > yesterday_revenue else "normal",
        },
        "total_orders": {
            "name": "Total Orders",
            "value": float(today_orders),
            "status": "good",
        },
        "average_order_value": {
            "name": "Average Order Value",
            "value": today_aov,
            "status": "good" if today_aov >= 50 else "normal",
        },
        "revenue_growth": {
            "name": "Revenue Growth",
            "value": round(revenue_change, 2),
            "unit": "%",
            "status": "good" if revenue_change > 0 else "warning",
        },
    }

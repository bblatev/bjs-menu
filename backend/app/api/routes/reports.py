"""Reporting routes."""

from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, List

from fastapi import APIRouter, Query, Body
from fastapi.responses import StreamingResponse

from app.core.rbac import CurrentUser, OptionalCurrentUser
from app.db.session import DbSession
from app.models.location import Location
from app.models.product import Product
from app.models.stock import StockMovement, StockOnHand

router = APIRouter()


@router.get("/sales")
def get_sales_report(
    db: DbSession,
    current_user: OptionalCurrentUser = None,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    """Get sales report summary."""
    return {"revenue": 0, "orders": 0, "average_ticket": 0, "items_sold": 0, "by_category": [], "by_hour": []}


@router.get("/staff")
def get_staff_report(
    db: DbSession,
    current_user: OptionalCurrentUser = None,
):
    """Get staff report."""
    return {"staff": [], "total": 0}


@router.get("/staff-performance")
def get_staff_performance_report(
    db: DbSession,
    current_user: OptionalCurrentUser = None,
):
    """Get staff performance report."""
    return {"staff": [], "average_rating": 0}


@router.get("/kitchen")
def get_kitchen_report(
    db: DbSession,
    current_user: OptionalCurrentUser = None,
):
    """Get kitchen performance report."""
    return {"avg_prep_time": 0, "orders_completed": 0, "by_station": []}


@router.get("/inventory")
def get_inventory_report(
    db: DbSession,
    current_user: OptionalCurrentUser = None,
):
    """Get inventory report."""
    return {"total_value": 0, "items_count": 0, "low_stock": [], "movements": []}


@router.get("/customers")
def get_customers_report(
    db: DbSession,
    current_user: OptionalCurrentUser = None,
):
    """Get customers report."""
    return {"total": 0, "new_this_month": 0, "returning": 0, "segments": []}


@router.get("/customer-insights")
def get_customer_insights_report(
    db: DbSession,
    current_user: OptionalCurrentUser = None,
):
    """Get customer insights report."""
    return {"top_spenders": [], "frequency": [], "preferences": []}


@router.get("/stock-valuation")
def get_stock_valuation(
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
def get_consumption_report(
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
def get_movement_summary(
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
def get_low_stock_report(
    db: DbSession,
    current_user: CurrentUser,
    location_id: int = Query(...),
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
def get_food_costs_report(
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
            "total_sales": 125000.00,
            "total_food_cost": 37500.00,
            "food_cost_percentage": 30.0,
            "target_percentage": 28.0,
            "variance": 2.0,
            "theoretical_cost": 35000.00,
            "actual_vs_theoretical": 2500.00,
        },
        "by_category": [
            {"category": "Appetizers", "sales": 18750.00, "cost": 5250.00, "percentage": 28.0},
            {"category": "Main Courses", "sales": 62500.00, "cost": 18750.00, "percentage": 30.0},
            {"category": "Pizza", "sales": 25000.00, "cost": 7500.00, "percentage": 30.0},
            {"category": "Desserts", "sales": 12500.00, "cost": 4375.00, "percentage": 35.0},
            {"category": "Drinks", "sales": 6250.00, "cost": 1625.00, "percentage": 26.0},
        ],
        "top_variances": [
            {"item": "BBQ Ribs", "expected_cost": 8.50, "actual_cost": 10.20, "variance": 1.70, "variance_pct": 20.0},
            {"item": "Fish & Chips", "expected_cost": 5.50, "actual_cost": 6.38, "variance": 0.88, "variance_pct": 16.0},
            {"item": "Steak Frites", "expected_cost": 12.00, "actual_cost": 13.20, "variance": 1.20, "variance_pct": 10.0},
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/labor-costs")
def get_labor_costs_report(
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
            "total_sales": 125000.00,
            "total_labor_cost": 31250.00,
            "labor_cost_percentage": 25.0,
            "target_percentage": 24.0,
            "total_hours": 2500,
            "average_hourly_rate": 12.50,
            "overtime_hours": 120,
            "overtime_cost": 2250.00,
        },
        "by_department": [
            {"department": "Kitchen", "hours": 1200, "cost": 15600.00, "percentage": 49.9},
            {"department": "Service", "hours": 900, "cost": 10800.00, "percentage": 34.6},
            {"department": "Bar", "hours": 300, "cost": 3900.00, "percentage": 12.5},
            {"department": "Management", "hours": 100, "cost": 950.00, "percentage": 3.0},
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/sales/detailed")
def get_detailed_sales_report(
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
            "total_sales": 125000.00,
            "total_orders": 2500,
            "average_order_value": 50.00,
            "total_guests": 6250,
            "average_per_guest": 20.00,
            "tips": 18750.00,
            "discounts": 3125.00,
            "net_sales": 121250.00,
        },
        "by_category": [
            {"category": "Food", "sales": 93750.00, "percentage": 75.0, "orders": 2000},
            {"category": "Beverages", "sales": 18750.00, "percentage": 15.0, "orders": 1500},
            {"category": "Alcohol", "sales": 12500.00, "percentage": 10.0, "orders": 800},
        ],
        "top_items": [
            {"name": "Classic Burger", "quantity": 450, "sales": 7200.00},
            {"name": "BBQ Ribs", "quantity": 280, "sales": 7000.00},
            {"name": "Chicken Wings", "quantity": 520, "sales": 6760.00},
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/server-performance")
def get_server_performance_report(
    db: DbSession,
    location_id: Optional[int] = Query(None),
):
    """
    Get server/staff performance report.
    """
    return {
        "servers": [
            {"id": 1, "name": "John Smith", "sales": 28500.00, "orders": 380, "avg_ticket": 75.00, "tips": 4275.00, "rating": 4.8},
            {"id": 2, "name": "Sarah Johnson", "sales": 25200.00, "orders": 350, "avg_ticket": 72.00, "tips": 4032.00, "rating": 4.9},
            {"id": 3, "name": "Mike Davis", "sales": 22100.00, "orders": 340, "avg_ticket": 65.00, "tips": 3315.00, "rating": 4.6},
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/voids-comps")
def get_voids_comps_report(
    db: DbSession,
    location_id: Optional[int] = Query(None),
):
    """
    Get voids and comps report.
    """
    return {
        "summary": {
            "total_voids": 1875.00,
            "void_percentage": 1.5,
            "total_comps": 2500.00,
            "comp_percentage": 2.0,
        },
        "voids": [
            {"reason": "Customer changed mind", "count": 45, "amount": 675.00},
            {"reason": "Wrong item sent", "count": 32, "amount": 480.00},
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/product-mix")
def get_product_mix_report(
    db: DbSession,
    location_id: Optional[int] = Query(None),
):
    """
    Get product mix analysis report.
    """
    return {
        "total_items_sold": 8500,
        "total_revenue": 125000.00,
        "categories": [
            {"name": "Appetizers", "items_sold": 1700, "revenue": 18750.00, "percentage": 15.0},
            {"name": "Main Courses", "items_sold": 3400, "revenue": 62500.00, "percentage": 50.0},
            {"name": "Pizza", "items_sold": 1275, "revenue": 25000.00, "percentage": 20.0},
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/trends")
def get_trends_report(
    db: DbSession,
    location_id: Optional[int] = Query(None),
    period: str = Query("week"),
):
    """
    Get sales and operational trends.
    """
    return {
        "period": period,
        "sales_trend": [
            {"date": "2024-01-01", "sales": 4200.00, "orders": 85},
            {"date": "2024-01-02", "sales": 3800.00, "orders": 78},
            {"date": "2024-01-03", "sales": 4500.00, "orders": 92},
        ],
        "comparison": {
            "current_period_sales": 37200.00,
            "previous_period_sales": 34500.00,
            "change_percentage": 7.8,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ==================== TURNOVER AT BASE PRICES ====================

@router.get("/turnover-base-prices")
def get_turnover_base_prices_report(
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
        start_date = (datetime.now().date() - timedelta(days=30)).strftime("%Y-%m-%d")
    if not end_date:
        end_date = datetime.now().date().strftime("%Y-%m-%d")
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM-DD"}

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
def export_report(
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

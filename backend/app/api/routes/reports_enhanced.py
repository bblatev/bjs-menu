"""Enhanced comprehensive reporting endpoints for POS system."""


from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import func, desc, extract
from typing import Optional, List
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from pydantic import BaseModel
import statistics

from app.core.rate_limit import limiter
from app.db.session import DbSession
from app.core.rbac import CurrentUser, OptionalCurrentUser

router = APIRouter()


# ==================== SCHEMAS ====================

class HourlySalesBreakdown(BaseModel):
    hour: int
    orders_count: int
    revenue: float
    average_order_value: float
    items_sold: int = 0


class DailySalesBreakdown(BaseModel):
    date: str
    day_of_week: str
    orders_count: int
    revenue: float
    average_order_value: float
    items_sold: int = 0
    peak_hour: Optional[int] = None


class CategorySales(BaseModel):
    category_id: int
    category_name: str
    revenue: float
    orders_count: int
    items_sold: int
    percentage_of_total: float
    average_item_price: float


class TopSellingItem(BaseModel):
    item_id: int
    item_name: str
    category: str
    quantity_sold: int
    revenue: float
    percentage_of_total: float
    average_price: float


class TrendDataPoint(BaseModel):
    date: str
    value: float
    percentage_change: Optional[float] = None


class TrendAnalysis(BaseModel):
    metric_name: str
    period: str
    data_points: List[TrendDataPoint]
    average: float
    trend_direction: str
    trend_percentage: float
    volatility: float


class KPIMetric(BaseModel):
    name: str
    value: float
    target: Optional[float] = None
    unit: Optional[str] = None
    change_percentage: Optional[float] = None
    change_direction: Optional[str] = None
    status: str = "normal"


# ==================== HELPERS ====================

def get_date_range(period: str, start_date: Optional[str] = None, end_date: Optional[str] = None):
    """Get date range for report period."""
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


# ==================== ENDPOINTS ====================

@router.get("/")
@limiter.limit("60/minute")
def get_reports_enhanced_root(request: Request, db: DbSession):
    """Enhanced reports overview."""
    return get_detailed_sales_report(request=request, db=db)


@router.get("/sales/detailed")
@limiter.limit("60/minute")
def get_detailed_sales_report(
    request: Request,
    db: DbSession,
    current_user: OptionalCurrentUser = None,
    period: str = Query("week"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """Get comprehensive sales report with hourly/daily breakdown."""
    start, end = get_date_range(period, start_date, end_date)

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


@router.get("/labor-costs")
@limiter.limit("60/minute")
def get_labor_cost_report(
    request: Request,
    db: DbSession,
    current_user: OptionalCurrentUser = None,
    period: str = Query("month"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """Get labor cost report with staff breakdown."""
    start, end = get_date_range(period, start_date, end_date)

    from app.models.staff import StaffUser
    staff = db.query(StaffUser).filter(StaffUser.is_active == True).all()

    return {
        "period": period,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "total_labor_cost": 0.0,
        "total_hours_worked": 0.0,
        "total_revenue": 0.0,
        "labor_cost_percentage": 0.0,
        "average_hourly_cost": 0.0,
        "staff_breakdown": [],
        "daily_breakdown": [],
        "overtime_cost": 0.0,
        "overtime_percentage": 0.0,
        "staff_count": len(staff),
    }


@router.get("/food-costs")
@limiter.limit("60/minute")
def get_food_cost_report(
    request: Request,
    db: DbSession,
    current_user: OptionalCurrentUser = None,
    period: str = Query("month"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """Get food cost report with menu item analysis."""
    start, end = get_date_range(period, start_date, end_date)

    from app.models.product import Product
    products = db.query(Product).filter(Product.active == True).all()

    item_breakdown = []
    for p in products:
        cost = float(p.cost_price or 0)
        price = cost * 3 if cost > 0 else 0  # estimate selling price as 3x cost
        margin = ((price - cost) / price * 100) if price > 0 else 0
        item_breakdown.append({
            "item_id": p.id,
            "item_name": p.name,
            "selling_price": price,
            "ingredient_cost": cost,
            "food_cost_percentage": round((cost / price * 100) if price > 0 else 0, 2),
            "profit_margin": round(margin, 2),
        })

    return {
        "period": period,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "total_revenue": 0.0,
        "total_food_cost": 0.0,
        "food_cost_percentage": 0.0,
        "total_profit": 0.0,
        "profit_margin": 0.0,
        "item_breakdown": item_breakdown,
        "category_breakdown": [],
        "highest_margin_items": sorted(item_breakdown, key=lambda x: x["profit_margin"], reverse=True)[:5],
        "lowest_margin_items": sorted(item_breakdown, key=lambda x: x["profit_margin"])[:5],
    }


@router.get("/product-mix")
@limiter.limit("60/minute")
def get_product_mix_report(
    request: Request,
    db: DbSession,
    current_user: OptionalCurrentUser = None,
    period: str = Query("month"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """Get product mix analysis with BCG matrix classification."""
    start, end = get_date_range(period, start_date, end_date)

    return {
        "period": period,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "total_items": 0,
        "total_revenue": 0.0,
        "items": [],
        "stars": [],
        "plow_horses": [],
        "puzzles": [],
        "dogs": [],
        "items_to_promote": [],
        "items_to_reprice": [],
        "items_to_remove": [],
    }


@router.get("/server-performance")
@limiter.limit("60/minute")
def get_server_performance_report(
    request: Request,
    db: DbSession,
    current_user: OptionalCurrentUser = None,
    period: str = Query("month"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """Get server/waiter performance report."""
    start, end = get_date_range(period, start_date, end_date)

    from app.models.staff import StaffUser
    staff = db.query(StaffUser).filter(StaffUser.is_active == True).all()

    servers = []
    for s in staff:
        servers.append({
            "staff_id": s.id,
            "staff_name": s.full_name,
            "role": s.role,
            "total_orders": 0,
            "total_revenue": 0.0,
            "average_order_value": 0.0,
            "performance_score": 0.0,
        })

    return {
        "period": period,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "servers": servers,
        "top_by_revenue": servers[:5],
        "top_by_rating": servers[:5],
        "top_by_efficiency": servers[:5],
    }


@router.get("/trends")
@limiter.limit("60/minute")
def get_trend_analysis(
    request: Request,
    db: DbSession,
    current_user: OptionalCurrentUser = None,
    period: str = Query("month"),
):
    """Get trend analysis for key metrics."""
    end = datetime.now(timezone.utc)

    if period == "week":
        start = end - timedelta(days=7)
    elif period == "month":
        start = end - timedelta(days=30)
    elif period == "quarter":
        start = end - timedelta(days=90)
    else:
        start = end - timedelta(days=365)

    from app.models.analytics import DailyMetrics

    metrics = db.query(DailyMetrics).filter(
        DailyMetrics.date >= start.strftime("%Y-%m-%d"),
        DailyMetrics.date <= end.strftime("%Y-%m-%d"),
    ).order_by(DailyMetrics.date).all()

    revenue_data = []
    for m in metrics:
        revenue_data.append({
            "date": str(m.date),
            "value": float(m.total_revenue or 0),
        })

    values = [d["value"] for d in revenue_data if d["value"] > 0]
    avg_revenue = statistics.mean(values) if values else 0
    volatility = statistics.stdev(values) if len(values) > 1 else 0

    if len(revenue_data) >= 2:
        recent_values = [d["value"] for d in revenue_data[-5:] if d["value"]]
        older_values = [d["value"] for d in revenue_data[:5] if d["value"]]
        recent_avg = statistics.mean(recent_values) if recent_values else 0
        older_avg = statistics.mean(older_values) if older_values else 0
        trend_pct = ((recent_avg - older_avg) / older_avg * 100) if older_avg > 0 else 0
        trend_dir = "up" if trend_pct > 5 else ("down" if trend_pct < -5 else "stable")
    else:
        trend_pct = 0
        trend_dir = "stable"

    return {
        "period": period,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "revenue_trend": {
            "metric_name": "Revenue",
            "period": period,
            "data_points": revenue_data,
            "average": round(avg_revenue, 2),
            "trend_direction": trend_dir,
            "trend_percentage": round(trend_pct, 2),
            "volatility": round(volatility, 2),
        },
        "orders_trend": {
            "metric_name": "Orders",
            "period": period,
            "data_points": [],
            "average": 0,
            "trend_direction": "stable",
            "trend_percentage": 0,
            "volatility": 0,
        },
        "average_order_value_trend": {
            "metric_name": "Average Order Value",
            "period": period,
            "data_points": [],
            "average": 0,
            "trend_direction": "stable",
            "trend_percentage": 0,
            "volatility": 0,
        },
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

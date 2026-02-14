"""Analytics, Conversational AI & Scale routes - Lightspeed/WISK style."""

import logging
from typing import List, Optional
from datetime import datetime, date, timedelta, timezone
from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import func, and_
from sqlalchemy.orm import joinedload

from app.core.rate_limit import limiter
from app.db.session import DbSession
from app.models.pos import PosSalesLine
from app.models.restaurant import GuestOrder
from app.models.analytics import (
    MenuAnalysis, ServerPerformance, SalesForecast, DailyMetrics,
    ConversationalQuery, Benchmark, BottleWeight, ScaleReading,
    MenuQuadrant
)
from app.services.menu_engineering_service import (
    MenuEngineeringService, ServerPerformanceService, DailyMetricsService
)
from app.services.conversational_ai_service import ConversationalAIService
from app.services.scale_service import (
    ScaleService, BottleWeightDatabaseService, InventoryCountingService
)

logger = logging.getLogger(__name__)
from app.schemas.analytics import (
    MenuAnalysisResponse, MenuEngineeringReport,
    ServerPerformanceResponse, ServerRanking, ServerPerformanceReport,
    SalesForecastResponse, ForecastReport,
    DailyMetricsResponse, MetricsTrend,
    ConversationalQueryRequest, ConversationalQueryResponse, ConversationHistory, QueryFeedback,
    BenchmarkResponse, BenchmarkComparison, PerformanceReport,
    BottleWeightResponse, BottleWeightCreate,
    ScaleReadingRequest, ScaleReadingResponse,
    VisualEstimateRequest, InventoryCountRequest, InventoryCountResponse
)

router = APIRouter()


def _utc_now() -> datetime:
    """Get current UTC time with timezone awareness."""
    return datetime.now(timezone.utc)


# ============ KPI Helpers ============

def _compute_table_turns_kpi(db, today_start, yesterday_start, location_id):
    """Compute table turns KPI from completed orders."""
    from app.models.restaurant import Table as TableModel
    table_count = db.query(func.count(TableModel.id))
    if location_id:
        table_count = table_count.filter(TableModel.location_id == location_id)
    table_count = table_count.scalar() or 1

    today_completed = db.query(func.count(GuestOrder.id)).filter(
        GuestOrder.created_at >= today_start,
        GuestOrder.status.in_(["served", "completed", "closed"]),
    )
    if location_id:
        today_completed = today_completed.filter(GuestOrder.location_id == location_id)
    today_turns = round((today_completed.scalar() or 0) / table_count, 1)

    yesterday_completed = db.query(func.count(GuestOrder.id)).filter(
        GuestOrder.created_at >= yesterday_start,
        GuestOrder.created_at < today_start,
        GuestOrder.status.in_(["served", "completed", "closed"]),
    )
    if location_id:
        yesterday_completed = yesterday_completed.filter(GuestOrder.location_id == location_id)
    yesterday_turns = round((yesterday_completed.scalar() or 0) / table_count, 1)

    change = round(today_turns - yesterday_turns, 1) if yesterday_turns else 0
    return {"name": "Table Turns", "value": today_turns, "change": change, "trend": "up" if change >= 0 else "down", "unit": "ratio"}


def _compute_food_cost_kpi(db, today_start, yesterday_start, location_id):
    """Compute food cost % from orders with base_price data."""
    from app.models.restaurant import MenuItem as MenuItemModel
    orders = db.query(GuestOrder).filter(GuestOrder.created_at >= today_start)
    if location_id:
        orders = orders.filter(GuestOrder.location_id == location_id)
    orders = orders.all()

    total_revenue = 0
    total_cost = 0
    for o in orders:
        if o.items:
            for item in o.items:
                qty = item.get("quantity", 1)
                price = item.get("price", 0)
                total_revenue += price * qty
                mid = item.get("menu_item_id") or item.get("id")
                if mid:
                    mi = db.query(MenuItemModel.base_price).filter(MenuItemModel.id == mid).first()
                    if mi and mi.base_price:
                        total_cost += float(mi.base_price) * qty

    food_cost_pct = round(total_cost / total_revenue * 100, 1) if total_revenue > 0 else 0
    return {"name": "Food Cost %", "value": food_cost_pct, "change": 0, "trend": "stable", "unit": "percentage"}


# ==================== STUB ENDPOINTS ====================

@router.get("/labor")
@limiter.limit("60/minute")
def get_labor_analytics(request: Request, db: DbSession):
    """Get labor analytics."""
    from app.models.operations import PayrollEntry, ShiftSchedule
    # Compute from actual payroll and shift data
    payroll = db.query(PayrollEntry).all()
    total_cost = sum(float(p.gross_pay or 0) for p in payroll)
    overtime = sum(float(p.overtime_hours or 0) for p in payroll)
    # Group by role/department from shifts
    departments = {}
    for p in payroll:
        dept = p.staff_name or "Unknown"
        departments[dept] = departments.get(dept, 0) + float(p.gross_pay or 0)
    by_department = [{"department": k, "cost": v} for k, v in departments.items()]
    return {"total_cost": total_cost, "labor_percentage": 0, "by_department": by_department, "overtime": overtime}


@router.get("/video")
@limiter.limit("60/minute")
def get_video_analytics(request: Request, db: DbSession):
    """Get video analytics config from app settings."""
    from app.models.operations import AppSetting
    setting = db.query(AppSetting).filter(
        AppSetting.category == "video_analytics",
        AppSetting.key == "config",
    ).first()
    if setting and setting.value:
        return setting.value
    return {"cameras": [], "alerts": [], "recordings": [], "status": "not_configured"}


@router.get("/theft")
@limiter.limit("60/minute")
def get_theft_analytics(request: Request, db: DbSession):
    """Get theft/risk analytics from risk alerts."""
    from app.models.operations import RiskAlert
    alerts = db.query(RiskAlert).order_by(RiskAlert.created_at.desc()).limit(50).all()
    incidents = [
        {
            "id": a.id,
            "type": a.type,
            "severity": a.severity,
            "title": a.title,
            "amount": float(a.amount or 0),
            "staff_name": a.staff_name,
            "status": a.status,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in alerts
    ]
    total_loss = sum(float(a.amount or 0) for a in alerts)
    open_alerts = [i for i in incidents if i["status"] == "open"]
    return {"incidents": incidents, "total_loss": round(total_loss, 2), "alerts": open_alerts}


@router.get("/rfm/dashboard")
@limiter.limit("60/minute")
def get_rfm_dashboard(request: Request, db: DbSession):
    """Get RFM analysis dashboard from customer data."""
    from app.models.customer import Customer
    customers = db.query(Customer).all()
    total = len(customers)
    # Simple segmentation based on available customer data
    segments = []
    if total > 0:
        segments = [
            {"name": "All Customers", "count": total, "percentage": 100},
        ]
    return {"segments": segments, "total_customers": total, "at_risk": 0}


@router.get("/forecasting")
@limiter.limit("60/minute")
def get_forecasting_analytics(request: Request, db: DbSession):
    """Get sales forecasting analytics from forecast data."""
    forecasts = db.query(SalesForecast).order_by(SalesForecast.forecast_date.desc()).limit(30).all()
    daily_forecast = [
        {
            "date": f.forecast_date.isoformat() if f.forecast_date else None,
            "predicted_revenue": float(f.forecasted_revenue or 0),
        }
        for f in forecasts
    ]
    return {
        "daily_forecast": daily_forecast,
        "weekly_forecast": [],
        "accuracy": 0,
        "model": "seasonal_arima",
        "last_trained": None,
        "recommendations": [],
    }


# Dashboard

@router.get("/dashboard")
@limiter.limit("60/minute")
def get_dashboard_stats(
    request: Request,
    db: DbSession,
    location_id: Optional[int] = None,
):
    """Get dashboard statistics for admin panel.

    Optimized to use database aggregation instead of loading all orders into memory.
    """
    today_start = _utc_now().replace(hour=0, minute=0, second=0, microsecond=0)

    # Use database aggregation for guest orders instead of loading all into memory
    base_filter = [GuestOrder.created_at >= today_start]
    if location_id:
        base_filter.append(GuestOrder.location_id == location_id)

    # Get totals using database aggregation
    guest_stats = db.query(
        func.count(GuestOrder.id).label("total_count"),
        func.coalesce(func.sum(GuestOrder.total), 0).label("total_revenue")
    ).filter(*base_filter).first()

    total_orders = guest_stats.total_count or 0
    total_revenue = float(guest_stats.total_revenue or 0)

    # Count active orders using database query
    active_statuses = ["received", "confirmed", "preparing", "ready"]
    active_orders = db.query(func.count(GuestOrder.id)).filter(
        *base_filter,
        GuestOrder.status.in_(active_statuses)
    ).scalar() or 0

    # POS sales aggregation
    pos_filter = [
        PosSalesLine.ts >= today_start,
        PosSalesLine.is_refund == False
    ]
    if location_id:
        pos_filter.append(PosSalesLine.location_id == location_id)

    pos_result = db.query(
        func.count(PosSalesLine.id).label("total_items"),
        func.coalesce(func.sum(PosSalesLine.qty), 0).label("total_qty")
    ).filter(*pos_filter).first()

    pos_items = pos_result.total_items or 0
    pos_qty = float(pos_result.total_qty or 0)

    # Combine with POS data (count only — POS model has no price column)
    total_orders += pos_items

    # Get top items from POS using database aggregation (more reliable than JSON parsing)
    pos_top_items = db.query(
        PosSalesLine.name,
        func.sum(PosSalesLine.qty).label("count")
    ).filter(*pos_filter).group_by(
        PosSalesLine.name
    ).order_by(
        func.sum(PosSalesLine.qty).desc()
    ).limit(10).all()

    top_items = [
        {"name": item.name or "Unknown", "count": int(item.count or 0)}
        for item in pos_top_items
    ][:5]

    # Orders by hour using database aggregation - single query instead of 24 queries
    # Use EXTRACT for PostgreSQL or strftime for SQLite
    try:
        # Try PostgreSQL syntax first
        hourly_stats = db.query(
            func.extract('hour', PosSalesLine.ts).label("hour"),
            func.count(PosSalesLine.id).label("count")
        ).filter(*pos_filter).group_by(
            func.extract('hour', PosSalesLine.ts)
        ).all()
    except Exception as e:
        # Fallback for SQLite
        logger.warning(f"PostgreSQL EXTRACT failed for hourly stats, falling back to SQLite strftime: {e}")
        hourly_stats = db.query(
            func.strftime('%H', PosSalesLine.ts).label("hour"),
            func.count(PosSalesLine.id).label("count")
        ).filter(*pos_filter).group_by(
            func.strftime('%H', PosSalesLine.ts)
        ).all()

    # Build full 24-hour array
    hourly_dict = {int(h.hour): int(h.count) for h in hourly_stats if h.hour is not None}
    orders_by_hour = [{"hour": h, "count": hourly_dict.get(h, 0)} for h in range(24)]

    return {
        "total_orders_today": total_orders,
        "total_revenue_today": round(total_revenue, 2),
        "active_orders": active_orders,
        "pending_calls": 0,
        "average_rating": 0.0,
        "top_items": top_items,
        "orders_by_hour": orders_by_hour
    }


@router.get("/dashboard/kpis")
@limiter.limit("60/minute")
def get_dashboard_kpis(
    request: Request,
    db: DbSession,
    location_id: Optional[int] = None,
):
    """Get key performance indicators for dashboard widgets."""
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)

    # Get today's orders
    today_query = db.query(GuestOrder).filter(GuestOrder.created_at >= today_start)
    if location_id:
        today_query = today_query.filter(GuestOrder.location_id == location_id)
    today_orders = today_query.all()

    # Get yesterday's orders for comparison
    yesterday_query = db.query(GuestOrder).filter(
        GuestOrder.created_at >= yesterday_start,
        GuestOrder.created_at < today_start
    )
    if location_id:
        yesterday_query = yesterday_query.filter(GuestOrder.location_id == location_id)
    yesterday_orders = yesterday_query.all()

    # Calculate today's metrics
    today_revenue = sum(float(o.total) if o.total else 0 for o in today_orders)
    today_count = len(today_orders)
    today_avg_ticket = today_revenue / today_count if today_count > 0 else 0

    # Calculate yesterday's metrics
    yesterday_revenue = sum(float(o.total) if o.total else 0 for o in yesterday_orders)
    yesterday_count = len(yesterday_orders)
    yesterday_avg_ticket = yesterday_revenue / yesterday_count if yesterday_count > 0 else 0

    # Calculate changes
    def calc_change(today_val, yesterday_val):
        if yesterday_val > 0:
            return round((today_val - yesterday_val) / yesterday_val * 100, 1)
        return 0 if today_val == 0 else 100

    revenue_change = calc_change(today_revenue, yesterday_revenue)
    order_change = calc_change(today_count, yesterday_count)
    ticket_change = calc_change(today_avg_ticket, yesterday_avg_ticket)

    return {
        "kpis": [
            {"name": "Revenue Today", "value": round(today_revenue, 2), "change": revenue_change, "trend": "up" if revenue_change >= 0 else "down", "unit": "currency"},
            {"name": "Orders Today", "value": today_count, "change": order_change, "trend": "up" if order_change >= 0 else "down", "unit": "count"},
            {"name": "Avg Ticket", "value": round(today_avg_ticket, 2), "change": ticket_change, "trend": "up" if ticket_change >= 0 else "down", "unit": "currency"},
            _compute_table_turns_kpi(db, today_start, yesterday_start, location_id),
            _compute_food_cost_kpi(db, today_start, yesterday_start, location_id),
        ],
        "comparison_period": "vs yesterday",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/sales")
@limiter.limit("60/minute")
def get_sales_analytics(
    request: Request,
    db: DbSession,
    location_id: Optional[int] = None,
    period: str = "today",
):
    """Get sales analytics summary from database."""
    # Calculate date range based on period
    now = datetime.now(timezone.utc)
    if period == "today":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start_date = now - timedelta(days=7)
    elif period == "month":
        start_date = now - timedelta(days=30)
    else:
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Get guest orders from database
    query = db.query(GuestOrder).filter(GuestOrder.created_at >= start_date)
    if location_id:
        query = query.filter(GuestOrder.location_id == location_id)
    orders = query.all()

    # Calculate totals
    total_sales = sum(float(o.total) if o.total else 0 for o in orders)
    order_count = len(orders)
    average_ticket = total_sales / order_count if order_count > 0 else 0

    # Calculate sales by category
    category_sales = {}
    item_sales = {}
    for order in orders:
        if order.items:
            for item in order.items:
                name = item.get("name", "Unknown")
                category = item.get("category", "Food")  # Default to Food if not specified
                price = float(item.get("price", 0))
                qty = item.get("quantity", 1)
                item_total = price * qty

                # Determine category based on item name patterns
                if any(drink in name.lower() for drink in ["drink", "coffee", "tea", "juice", "soda"]):
                    category = "Beverages"
                elif any(dessert in name.lower() for dessert in ["brownie", "cheesecake", "sundae", "ice cream", "cake"]):
                    category = "Desserts"
                else:
                    category = "Food"

                category_sales[category] = category_sales.get(category, 0) + item_total
                if name not in item_sales:
                    item_sales[name] = {"quantity": 0, "revenue": 0}
                item_sales[name]["quantity"] += qty
                item_sales[name]["revenue"] += item_total

    # Format category sales
    sales_by_category = []
    for cat, amount in category_sales.items():
        percentage = (amount / total_sales * 100) if total_sales > 0 else 0
        sales_by_category.append({
            "category": cat,
            "amount": round(amount, 2),
            "percentage": round(percentage, 1)
        })

    # Sort by amount descending
    sales_by_category.sort(key=lambda x: x["amount"], reverse=True)

    # Calculate sales by hour
    sales_by_hour = {}
    for order in orders:
        if order.created_at:
            hour = order.created_at.hour
            order_total = float(order.total) if order.total else 0
            sales_by_hour[hour] = sales_by_hour.get(hour, 0) + order_total

    formatted_sales_by_hour = [
        {"hour": hour, "amount": round(amount, 2)}
        for hour, amount in sorted(sales_by_hour.items())
    ]

    # Get top items
    top_items = sorted(
        [{"name": name, "quantity": data["quantity"], "revenue": round(data["revenue"], 2)}
         for name, data in item_sales.items()],
        key=lambda x: x["revenue"],
        reverse=True
    )[:10]

    return {
        "period": period,
        "total_sales": round(total_sales, 2),
        "order_count": order_count,
        "average_ticket": round(average_ticket, 2),
        "sales_by_category": sales_by_category if sales_by_category else [
            {"category": "Food", "amount": 0, "percentage": 0}
        ],
        "sales_by_hour": formatted_sales_by_hour,
        "top_items": top_items,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# Menu Engineering

@router.get("/menu-engineering/", response_model=MenuEngineeringReport)
@limiter.limit("60/minute")
def get_menu_engineering_report(
    request: Request,
    db: DbSession,
    location_id: Optional[int] = None,
    days: int = 30,
):
    """Get complete menu engineering analysis."""
    service = MenuEngineeringService(db)
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    end_date = datetime.now(timezone.utc)
    result = service.analyze_menu(location_id, start_date, end_date)

    # Group by quadrant
    stars = [r for r in result if r.quadrant == MenuQuadrant.STAR]
    puzzles = [r for r in result if r.quadrant == MenuQuadrant.PUZZLE]
    plow_horses = [r for r in result if r.quadrant == MenuQuadrant.PLOW_HORSE]
    dogs = [r for r in result if r.quadrant == MenuQuadrant.DOG]

    return MenuEngineeringReport(
        location_id=location_id,
        analysis_period={
            "start": (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(),
            "end": datetime.now(timezone.utc).isoformat()
        },
        total_items_analyzed=len(result),
        quadrant_summary={
            "stars": len(stars),
            "puzzles": len(puzzles),
            "plow_horses": len(plow_horses),
            "dogs": len(dogs)
        },
        stars=stars,
        puzzles=puzzles,
        plow_horses=plow_horses,
        dogs=dogs,
        recommendations=service.generate_recommendations(result)
    )


@router.get("/menu-engineering/{product_id}", response_model=MenuAnalysisResponse)
@limiter.limit("60/minute")
def get_product_analysis(request: Request, db: DbSession, product_id: int):
    """Get menu engineering analysis for a specific product."""
    analysis = db.query(MenuAnalysis).filter(
        MenuAnalysis.product_id == product_id
    ).order_by(MenuAnalysis.calculated_at.desc()).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return analysis


# Server Performance

@router.get("/server-performance/", response_model=ServerPerformanceReport)
@limiter.limit("60/minute")
def get_server_performance_report(
    request: Request,
    db: DbSession,
    location_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    """Get server performance report."""
    service = ServerPerformanceService(db)

    if not start_date:
        start_date = date.today() - timedelta(days=7)
    if not end_date:
        end_date = date.today()

    result = service.analyze_server_performance(location_id, start_date, end_date)

    # Rank servers
    sorted_servers = sorted(result, key=lambda x: x.get("total_sales", 0), reverse=True)
    rankings = []
    for i, s in enumerate(sorted_servers[:10]):
        rankings.append(ServerRanking(
            rank=i + 1,
            user_id=s["user_id"],
            server_name=s["server_name"],
            total_sales=s["total_sales"],
            avg_ticket=s["avg_ticket"],
            tip_percentage=s["tip_percentage"],
            performance_score=s.get("performance_score", 0)
        ))

    return ServerPerformanceReport(
        date_range={"start": str(start_date), "end": str(end_date)},
        rankings=rankings,
        top_performer=rankings[0] if rankings else None,
        improvement_opportunities=service.get_improvement_suggestions(result)
    )


@router.get("/server-performance/{user_id}", response_model=List[ServerPerformanceResponse])
@limiter.limit("60/minute")
def get_server_metrics(
    request: Request,
    db: DbSession,
    user_id: int,
    days: int = 30,
):
    """Get performance metrics for a specific server."""
    start_date = date.today() - timedelta(days=days)

    return db.query(ServerPerformance).filter(
        ServerPerformance.user_id == user_id,
        ServerPerformance.period_start >= start_date
    ).order_by(ServerPerformance.period_start.desc()).all()


# Daily Metrics

@router.get("/daily-metrics/", response_model=List[DailyMetricsResponse])
@limiter.limit("60/minute")
def get_daily_metrics(
    request: Request,
    db: DbSession,
    location_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    """Get daily business metrics."""
    try:
        query = db.query(DailyMetrics)

        if location_id:
            query = query.filter(DailyMetrics.location_id == location_id)
        if start_date:
            query = query.filter(DailyMetrics.date >= start_date)
        if end_date:
            query = query.filter(DailyMetrics.date <= end_date)

        return query.order_by(DailyMetrics.date.desc()).limit(90).all()
    except Exception as e:
        logger.warning(f"Failed to query daily metrics (location_id={location_id}): {e}")
        db.rollback()
        return []


@router.post("/daily-metrics/calculate")
@limiter.limit("30/minute")
def calculate_daily_metrics(
    request: Request,
    db: DbSession,
    target_date: Optional[date] = None,
    location_id: Optional[int] = None,
):
    """Calculate daily metrics for a specific date."""
    try:
        service = DailyMetricsService(db)

        if not target_date:
            target_date = date.today() - timedelta(days=1)

        # Convert date to datetime for the service method
        target_datetime = datetime.combine(target_date, datetime.min.time())
        result = service.calculate_daily_metrics(target_datetime, location_id)
        return {"status": "ok", "date": str(target_date), "metrics_id": result.id}
    except Exception as e:
        db.rollback()
        error_msg = str(e)
        if "daily_metrics" in error_msg and "does not exist" in error_msg:
            raise HTTPException(status_code=503, detail="Daily metrics table not yet created. Run database migrations first.")
        raise HTTPException(status_code=500, detail=f"Failed to calculate metrics: {error_msg}")


@router.get("/metrics-trend/{metric_name}", response_model=MetricsTrend)
@limiter.limit("60/minute")
def get_metric_trend(
    request: Request,
    db: DbSession,
    metric_name: str,
    location_id: Optional[int] = None,
    period: str = "daily",
    days: int = 30,
):
    """Get trend for a specific metric."""
    start_date = date.today() - timedelta(days=days)

    query = db.query(DailyMetrics).filter(DailyMetrics.date >= start_date)
    if location_id:
        query = query.filter(DailyMetrics.location_id == location_id)

    metrics = query.order_by(DailyMetrics.date).all()

    # Build data points
    data_points = []
    for m in metrics:
        value = getattr(m, metric_name, None)
        if value is not None:
            data_points.append({"date": str(m.date), "value": float(value)})

    # Determine trend
    if len(data_points) >= 2:
        mid = len(data_points) // 2
        first_half = sum(dp["value"] for dp in data_points[:mid]) / mid
        second_half = sum(dp["value"] for dp in data_points[mid:]) / (len(data_points) - mid)
        change = ((second_half - first_half) / first_half * 100) if first_half > 0 else 0
        trend = "up" if change > 5 else "down" if change < -5 else "stable"
    else:
        change = 0
        trend = "stable"

    return MetricsTrend(
        metric_name=metric_name,
        period=period,
        data_points=data_points,
        trend=trend,
        change_percent=change
    )


# Conversational AI

@router.post("/chat/", response_model=ConversationalQueryResponse)
@limiter.limit("30/minute")
async def chat_query(
    request: Request,
    db: DbSession,
    body: ConversationalQueryRequest,
    user_id: Optional[int] = None,
):
    """Process a natural language analytics query."""
    service = ConversationalAIService(db)
    result = await service.process_query(
        query_text=body.query,
        user_id=user_id,
        location_id=body.location_id,
        conversation_id=body.conversation_id
    )

    return ConversationalQueryResponse(
        query=result["query"],
        intent=result["intent"],
        response=result["response"],
        data=result["data"],
        query_id=result["query_id"],
        conversation_id=result["conversation_id"],
        processing_time_ms=result["processing_time_ms"],
        suggestions=result.get("data", {}).get("suggestions", [])
    )


@router.get("/chat/history/{conversation_id}", response_model=ConversationHistory)
@limiter.limit("60/minute")
def get_conversation_history(request: Request, db: DbSession, conversation_id: str):
    """Get conversation history."""
    service = ConversationalAIService(db)
    messages = service.get_conversation_history(conversation_id)

    return ConversationHistory(
        conversation_id=conversation_id,
        messages=messages
    )


@router.post("/chat/feedback")
@limiter.limit("30/minute")
def submit_query_feedback(request: Request, db: DbSession, feedback: QueryFeedback):
    """Submit feedback on a query response."""
    service = ConversationalAIService(db)
    service.provide_feedback(feedback.query_id, feedback.was_helpful)
    return {"status": "ok"}


# Benchmarks

@router.get("/benchmarks/", response_model=List[BenchmarkResponse])
@limiter.limit("60/minute")
def list_benchmarks(
    request: Request,
    db: DbSession,
    category: Optional[str] = None,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=200, description="Maximum records to return"),
):
    """List industry benchmarks with pagination."""
    query = db.query(Benchmark)
    if category:
        query = query.filter(Benchmark.category == category)
    return query.offset(skip).limit(limit).all()


@router.get("/benchmarks/compare", response_model=PerformanceReport)
@limiter.limit("60/minute")
def compare_to_benchmarks(
    request: Request,
    db: DbSession,
    location_id: int,
):
    """Compare location performance to industry benchmarks."""
    # Get recent metrics
    recent = db.query(DailyMetrics).filter(
        DailyMetrics.location_id == location_id
    ).order_by(DailyMetrics.date.desc()).limit(30).all()

    if not recent:
        raise HTTPException(status_code=404, detail="No metrics found")

    # Get benchmarks
    benchmarks = db.query(Benchmark).all()
    benchmark_dict = {b.metric_name: b for b in benchmarks}

    comparisons = []
    strengths = []
    improvements = []

    # Average metrics
    avg_ticket = sum(m.average_ticket or 0 for m in recent) / len(recent)
    avg_margin = sum(m.gross_margin or 0 for m in recent) / len(recent)

    # Compare
    for metric_name, avg_value in [("average_ticket", avg_ticket), ("gross_margin", avg_margin)]:
        if metric_name in benchmark_dict:
            b = benchmark_dict[metric_name]
            percentile = 50
            if avg_value >= b.percentile_90:
                percentile = 90
                strengths.append(metric_name)
            elif avg_value >= b.percentile_75:
                percentile = 75
            elif avg_value >= b.percentile_50:
                percentile = 50
            elif avg_value >= b.percentile_25:
                percentile = 25
                improvements.append(metric_name)
            else:
                percentile = 10
                improvements.append(metric_name)

            comparisons.append(BenchmarkComparison(
                metric_name=metric_name,
                your_value=avg_value,
                percentile_25=b.percentile_25,
                percentile_50=b.percentile_50,
                percentile_75=b.percentile_75,
                percentile_90=b.percentile_90,
                your_percentile=percentile,
                status="above_average" if percentile >= 50 else "below_average"
            ))

    return PerformanceReport(
        location_id=location_id,
        period="last_30_days",
        comparisons=comparisons,
        overall_score=sum(c.your_percentile for c in comparisons) / len(comparisons) if comparisons else 50,
        strengths=strengths,
        improvement_areas=improvements
    )


# Scale / Bottle Weights

@router.get("/bottle-weights/", response_model=List[BottleWeightResponse])
@limiter.limit("60/minute")
def list_bottle_weights(
    request: Request,
    db: DbSession,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
):
    """List bottle weight database entries."""
    service = BottleWeightDatabaseService(db)

    if search:
        return service.search_bottle_database(search, limit)

    return db.query(BottleWeight).offset(skip).limit(limit).all()


@router.get("/bottle-weights/{product_id}", response_model=BottleWeightResponse)
@limiter.limit("60/minute")
def get_bottle_weight(request: Request, db: DbSession, product_id: int):
    """Get bottle weight for a product."""
    service = BottleWeightDatabaseService(db)
    weight = service.get_bottle_weight(product_id=product_id)

    if not weight:
        raise HTTPException(status_code=404, detail="Bottle weight not found")

    return weight


@router.post("/bottle-weights/", response_model=BottleWeightResponse)
@limiter.limit("30/minute")
def create_bottle_weight(
    request: Request,
    db: DbSession,
    weight: BottleWeightCreate,
):
    """Add bottle weight to database."""
    service = BottleWeightDatabaseService(db)
    result = service.add_bottle_weight(
        product_id=weight.product_id,
        full_weight=weight.full_weight,
        empty_weight=weight.empty_weight,
        volume_ml=weight.volume_ml,
        barcode=weight.barcode,
        brand=weight.brand,
        alcohol_category=weight.alcohol_category
    )
    return result


@router.get("/bottle-weights/missing/", response_model=List[dict])
@limiter.limit("60/minute")
def get_products_without_weights(request: Request, db: DbSession):
    """Get products that don't have bottle weight data."""
    service = BottleWeightDatabaseService(db)
    products = service.get_products_without_weights()
    return [{"id": p.id, "name": p.name} for p in products]


@router.post("/bottle-weights/import")
@limiter.limit("30/minute")
def import_bottle_weights(request: Request, db: DbSession, data: List[dict]):
    """Import bottle weights from WISK format."""
    service = BottleWeightDatabaseService(db)
    result = service.import_from_wisk_format(data)
    return result


# Scale Readings

@router.post("/scale/reading", response_model=ScaleReadingResponse)
@limiter.limit("30/minute")
def process_scale_reading(
    request: Request,
    db: DbSession,
    reading: ScaleReadingRequest,
):
    """Process a Bluetooth scale reading."""
    service = ScaleService(db)
    result = service.process_scale_reading(
        product_id=reading.product_id,
        weight_grams=reading.weight_grams,
        session_id=reading.session_id,
        device_id=reading.device_id,
        device_name=reading.device_name
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.post("/scale/visual-estimate", response_model=ScaleReadingResponse)
@limiter.limit("30/minute")
def record_visual_estimate(
    request: Request,
    db: DbSession,
    estimate: VisualEstimateRequest,
):
    """Record a visual fill level estimate."""
    service = ScaleService(db)
    result = service.record_visual_estimate(
        product_id=estimate.product_id,
        estimated_percent=estimate.estimated_percent,
        session_id=estimate.session_id
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.post("/scale/inventory-count", response_model=InventoryCountResponse)
@limiter.limit("30/minute")
def count_inventory_with_scale(
    request: Request,
    db: DbSession,
    count: InventoryCountRequest,
):
    """Count inventory including partial bottles."""
    service = InventoryCountingService(db)
    result = service.count_partial_bottle(
        session_id=count.session_id,
        product_id=count.product_id,
        weight_grams=count.weight_grams,
        visual_percent=count.visual_percent,
        full_bottles=count.full_bottles
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.get("/scale/session-summary/{session_id}")
@limiter.limit("60/minute")
def get_scale_session_summary(request: Request, db: DbSession, session_id: int):
    """Get summary of inventory session with scale readings."""
    service = InventoryCountingService(db)
    return service.get_session_summary(session_id)


@router.get("/scale-integration")
@limiter.limit("60/minute")
def get_scale_integration_status(request: Request, db: DbSession):
    """Get scale integration status and connected devices."""
    from app.models.operations import AppSetting
    setting = db.query(AppSetting).filter(
        AppSetting.category == "scale_devices",
        AppSetting.key == "config",
    ).first()
    if setting and setting.value:
        return setting.value
    return {
        "status": "inactive",
        "connected_devices": [],
        "last_reading": None,
        "supported_scales": [],
        "features": {
            "auto_detect": False,
            "batch_weighing": False,
            "tare_support": False,
        },
    }


@router.get("/menu-analysis")
@limiter.limit("60/minute")
def get_menu_analysis(request: Request, db: DbSession):
    """Get menu analysis and engineering insights."""
    from app.models.restaurant import MenuItem
    items = db.query(MenuItem).all()

    categories = {}
    for item in items:
        cat = item.category or "Other"
        if cat not in categories:
            categories[cat] = {"count": 0, "total_price": 0}
        categories[cat]["count"] += 1
        categories[cat]["total_price"] += float(item.price or 0)

    return {
        "total_items": len(items),
        "active_items": len([i for i in items if i.available]),
        "categories": [
            {
                "name": k,
                "item_count": v["count"],
                "avg_price": v["total_price"] / v["count"] if v["count"] > 0 else 0,
            }
            for k, v in categories.items()
        ],
        "insights": {
            "top_performers": [],
            "underperformers": [],
            "pricing_opportunities": [],
        },
    }

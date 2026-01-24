"""Analytics, Conversational AI & Scale routes - Lightspeed/WISK style."""

from typing import List, Optional
from datetime import datetime, date, timedelta
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func

from app.db.session import DbSession
from app.models.pos import PosSalesLine
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


# Dashboard

@router.get("/dashboard")
def get_dashboard_stats(
    db: DbSession,
    location_id: Optional[int] = None,
):
    """Get dashboard statistics for admin panel."""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    # Total orders (count of distinct pos_item_id transactions) and items sold
    sales_query = db.query(
        func.count(PosSalesLine.id).label("total_items"),
        func.sum(PosSalesLine.qty).label("total_qty")
    ).filter(
        PosSalesLine.ts >= today_start,
        PosSalesLine.is_refund == False
    )
    if location_id:
        sales_query = sales_query.filter(PosSalesLine.location_id == location_id)

    result = sales_query.first()
    total_items = result.total_items or 0
    total_qty = float(result.total_qty or 0)

    # Estimate revenue (assuming average price of 15 per item for demo)
    estimated_revenue = total_qty * 15.0

    # Top items by name
    top_items_query = db.query(
        PosSalesLine.name,
        func.sum(PosSalesLine.qty).label("count")
    ).filter(
        PosSalesLine.ts >= today_start,
        PosSalesLine.is_refund == False
    ).group_by(PosSalesLine.name).order_by(
        func.sum(PosSalesLine.qty).desc()
    ).limit(5)

    top_items = [{"name": item.name, "count": int(item.count)} for item in top_items_query.all()]

    # Orders by hour
    orders_by_hour = []
    for hour in range(24):
        hour_start = today_start.replace(hour=hour)
        hour_end = today_start.replace(hour=hour, minute=59, second=59)
        count = db.query(func.count(PosSalesLine.id)).filter(
            PosSalesLine.ts >= hour_start,
            PosSalesLine.ts <= hour_end,
            PosSalesLine.is_refund == False
        ).scalar() or 0
        orders_by_hour.append({"hour": hour, "count": count})

    return {
        "total_orders_today": total_items,
        "total_revenue_today": estimated_revenue,
        "active_orders": 0,
        "pending_calls": 0,
        "average_rating": 4.5,
        "top_items": top_items,
        "orders_by_hour": orders_by_hour
    }


@router.get("/dashboard/kpis")
def get_dashboard_kpis(
    db: DbSession,
    location_id: Optional[int] = None,
):
    """Get key performance indicators for dashboard widgets."""
    return {
        "kpis": [
            {"name": "Revenue Today", "value": 4250.00, "change": 12.5, "trend": "up", "unit": "currency"},
            {"name": "Orders Today", "value": 85, "change": 8.2, "trend": "up", "unit": "count"},
            {"name": "Avg Ticket", "value": 50.00, "change": 3.8, "trend": "up", "unit": "currency"},
            {"name": "Table Turns", "value": 2.4, "change": -5.0, "trend": "down", "unit": "ratio"},
            {"name": "Labor Cost %", "value": 24.5, "change": -1.2, "trend": "up", "unit": "percentage"},
            {"name": "Food Cost %", "value": 29.8, "change": 0.5, "trend": "down", "unit": "percentage"},
            {"name": "Guest Satisfaction", "value": 4.7, "change": 2.0, "trend": "up", "unit": "rating"},
            {"name": "Wait Time", "value": 12, "change": -15.0, "trend": "up", "unit": "minutes"},
        ],
        "comparison_period": "vs yesterday",
        "generated_at": datetime.utcnow().isoformat(),
    }


@router.get("/sales")
def get_sales_analytics(
    db: DbSession,
    location_id: Optional[int] = None,
    period: str = "today",
):
    """Get sales analytics summary."""
    return {
        "period": period,
        "total_sales": 4250.00,
        "order_count": 85,
        "average_ticket": 50.00,
        "sales_by_category": [
            {"category": "Food", "amount": 3200.00, "percentage": 75.3},
            {"category": "Beverages", "amount": 850.00, "percentage": 20.0},
            {"category": "Desserts", "amount": 200.00, "percentage": 4.7},
        ],
        "sales_by_hour": [
            {"hour": 11, "amount": 350.00},
            {"hour": 12, "amount": 680.00},
            {"hour": 13, "amount": 520.00},
            {"hour": 18, "amount": 890.00},
            {"hour": 19, "amount": 1100.00},
            {"hour": 20, "amount": 710.00},
        ],
        "top_items": [
            {"name": "Classic Burger", "quantity": 25, "revenue": 399.75},
            {"name": "BBQ Ribs", "quantity": 18, "revenue": 449.82},
            {"name": "Fish & Chips", "quantity": 15, "revenue": 284.85},
        ],
        "generated_at": datetime.utcnow().isoformat(),
    }


# Menu Engineering

@router.get("/menu-engineering/", response_model=MenuEngineeringReport)
def get_menu_engineering_report(
    db: DbSession,
    location_id: Optional[int] = None,
    days: int = 30,
):
    """Get complete menu engineering analysis."""
    service = MenuEngineeringService(db)
    start_date = datetime.utcnow() - timedelta(days=days)
    end_date = datetime.utcnow()
    result = service.analyze_menu(location_id, start_date, end_date)

    # Group by quadrant
    stars = [r for r in result if r.quadrant == MenuQuadrant.STAR]
    puzzles = [r for r in result if r.quadrant == MenuQuadrant.PUZZLE]
    plow_horses = [r for r in result if r.quadrant == MenuQuadrant.PLOW_HORSE]
    dogs = [r for r in result if r.quadrant == MenuQuadrant.DOG]

    return MenuEngineeringReport(
        location_id=location_id,
        analysis_period={
            "start": (datetime.utcnow() - timedelta(days=days)).isoformat(),
            "end": datetime.utcnow().isoformat()
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
def get_product_analysis(db: DbSession, product_id: int):
    """Get menu engineering analysis for a specific product."""
    analysis = db.query(MenuAnalysis).filter(
        MenuAnalysis.product_id == product_id
    ).order_by(MenuAnalysis.calculated_at.desc()).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return analysis


# Server Performance

@router.get("/server-performance/", response_model=ServerPerformanceReport)
def get_server_performance_report(
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
def get_server_metrics(
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
def get_daily_metrics(
    db: DbSession,
    location_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    """Get daily business metrics."""
    query = db.query(DailyMetrics)

    if location_id:
        query = query.filter(DailyMetrics.location_id == location_id)
    if start_date:
        query = query.filter(DailyMetrics.date >= start_date)
    if end_date:
        query = query.filter(DailyMetrics.date <= end_date)

    return query.order_by(DailyMetrics.date.desc()).limit(90).all()


@router.post("/daily-metrics/calculate")
def calculate_daily_metrics(
    db: DbSession,
    target_date: Optional[date] = None,
    location_id: Optional[int] = None,
):
    """Calculate daily metrics for a specific date."""
    service = DailyMetricsService(db)

    if not target_date:
        target_date = date.today() - timedelta(days=1)

    # Convert date to datetime for the service method
    target_datetime = datetime.combine(target_date, datetime.min.time())
    result = service.calculate_daily_metrics(target_datetime, location_id)
    return {"status": "ok", "date": str(target_date), "metrics_id": result.id}


@router.get("/metrics-trend/{metric_name}", response_model=MetricsTrend)
def get_metric_trend(
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
async def chat_query(
    db: DbSession,
    request: ConversationalQueryRequest,
    user_id: Optional[int] = None,
):
    """Process a natural language analytics query."""
    service = ConversationalAIService(db)
    result = await service.process_query(
        query_text=request.query,
        user_id=user_id,
        location_id=request.location_id,
        conversation_id=request.conversation_id
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
def get_conversation_history(db: DbSession, conversation_id: str):
    """Get conversation history."""
    service = ConversationalAIService(db)
    messages = service.get_conversation_history(conversation_id)

    return ConversationHistory(
        conversation_id=conversation_id,
        messages=messages
    )


@router.post("/chat/feedback")
def submit_query_feedback(db: DbSession, feedback: QueryFeedback):
    """Submit feedback on a query response."""
    service = ConversationalAIService(db)
    service.provide_feedback(feedback.query_id, feedback.was_helpful)
    return {"status": "ok"}


# Benchmarks

@router.get("/benchmarks/", response_model=List[BenchmarkResponse])
def list_benchmarks(
    db: DbSession,
    category: Optional[str] = None,
):
    """List industry benchmarks."""
    query = db.query(Benchmark)
    if category:
        query = query.filter(Benchmark.category == category)
    return query.all()


@router.get("/benchmarks/compare", response_model=PerformanceReport)
def compare_to_benchmarks(
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
def list_bottle_weights(
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
def get_bottle_weight(db: DbSession, product_id: int):
    """Get bottle weight for a product."""
    service = BottleWeightDatabaseService(db)
    weight = service.get_bottle_weight(product_id=product_id)

    if not weight:
        raise HTTPException(status_code=404, detail="Bottle weight not found")

    return weight


@router.post("/bottle-weights/", response_model=BottleWeightResponse)
def create_bottle_weight(
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
def get_products_without_weights(db: DbSession):
    """Get products that don't have bottle weight data."""
    service = BottleWeightDatabaseService(db)
    products = service.get_products_without_weights()
    return [{"id": p.id, "name": p.name} for p in products]


@router.post("/bottle-weights/import")
def import_bottle_weights(db: DbSession, data: List[dict]):
    """Import bottle weights from WISK format."""
    service = BottleWeightDatabaseService(db)
    result = service.import_from_wisk_format(data)
    return result


# Scale Readings

@router.post("/scale/reading", response_model=ScaleReadingResponse)
def process_scale_reading(
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
def record_visual_estimate(
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
def count_inventory_with_scale(
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
def get_scale_session_summary(db: DbSession, session_id: int):
    """Get summary of inventory session with scale readings."""
    service = InventoryCountingService(db)
    return service.get_session_summary(session_id)

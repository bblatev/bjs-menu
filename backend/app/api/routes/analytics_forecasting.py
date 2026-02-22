from datetime import timezone
"""
Analytics & Forecasting API Endpoints
Demand forecasting, trend analysis, predictive analytics
"""
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
from pydantic import BaseModel, Field

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.core.rbac import get_current_user
from app.models import StaffUser
from app.services.analytics_forecasting import (
    analytics_service,
    ForecastMethod,
    ForecastResult
)


router = APIRouter()


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class ForecastRequest(BaseModel):
    """Request for demand forecast"""
    item_ids: Optional[List[int]] = None
    category_id: Optional[int] = None
    forecast_days: int = Field(7, ge=1, le=90)
    method: str = Field("ensemble", description="moving_average, exponential_smoothing, linear_regression, seasonal, ensemble")


class TrendAnalysisRequest(BaseModel):
    """Request for trend analysis"""
    metric: str = Field(..., description="sales, orders, customers, stock")
    start_date: date
    end_date: date
    group_by: str = Field("day", description="day, week, month")


class StockPredictionRequest(BaseModel):
    """Request for stock requirement prediction"""
    item_ids: Optional[List[int]] = None
    lead_time_days: int = Field(3, ge=1, le=30)
    forecast_days: int = Field(14, ge=7, le=60)


# =============================================================================
# DEMAND FORECASTING ENDPOINTS
# =============================================================================

@router.get("/")
@limiter.limit("60/minute")
async def get_analytics_forecasting_root(request: Request, db: Session = Depends(get_db), current_user: StaffUser = Depends(get_current_user)):
    """Analytics forecasting overview."""
    return await get_analytics_dashboard(request=request, db=db, current_user=current_user)


@router.get("/forecast/demand", response_model=Dict[str, Any])
@limiter.limit("60/minute")
async def get_demand_forecast(
    request: Request,
    forecast_days: int = 7,
    method: str = "ensemble",
    category_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Get demand forecast for menu items.
    Uses historical sales data to predict future demand.
    """
    # Get historical sales data (last 90 days)
    # In production, query from database
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=90)

    # Mock historical data for demonstration
    historical_data = _get_mock_historical_data(
        current_user.venue_id,
        start_date,
        end_date,
        category_id
    )

    try:
        forecast_method = ForecastMethod(method)
    except ValueError:
        forecast_method = ForecastMethod.ENSEMBLE

    results = analytics_service.forecast_demand(
        historical_data=historical_data,
        forecast_days=forecast_days,
        method=forecast_method
    )

    return {
        "venue_id": current_user.venue_id,
        "forecast_days": forecast_days,
        "method": method,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "forecasts": [
            {
                "item_id": r.item_id,
                "item_name": r.item_name,
                "current_value": r.current_value,
                "forecast_values": r.forecast_values,
                "forecast_dates": r.forecast_dates,
                "confidence_interval": r.confidence_interval,
                "trend": r.trend,
                "accuracy_score": r.accuracy_score,
                "recommendations": r.recommendations
            }
            for r in results
        ]
    }


@router.post("/forecast/custom", response_model=Dict[str, Any])
@limiter.limit("30/minute")
async def create_custom_forecast(
    request: Request,
    forecast_request: ForecastRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Create a custom demand forecast with specific parameters.
    """
    # Get historical data for specified items
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=90)

    historical_data = _get_mock_historical_data(
        current_user.venue_id,
        start_date,
        end_date,
        forecast_request.category_id,
        forecast_request.item_ids
    )

    try:
        forecast_method = ForecastMethod(forecast_request.method)
    except ValueError:
        forecast_method = ForecastMethod.ENSEMBLE

    results = analytics_service.forecast_demand(
        historical_data=historical_data,
        forecast_days=forecast_request.forecast_days,
        method=forecast_method
    )

    return {
        "request": {
            "item_ids": forecast_request.item_ids,
            "category_id": forecast_request.category_id,
            "forecast_days": forecast_request.forecast_days,
            "method": forecast_request.method
        },
        "forecasts": [
            {
                "item_id": r.item_id,
                "item_name": r.item_name,
                "forecast_values": r.forecast_values,
                "forecast_dates": r.forecast_dates,
                "trend": r.trend,
                "accuracy_score": r.accuracy_score,
                "recommendations": r.recommendations
            }
            for r in results
        ]
    }


# =============================================================================
# TREND ANALYSIS ENDPOINTS
# =============================================================================

@router.get("/trends/sales", response_model=Dict[str, Any])
@limiter.limit("60/minute")
async def get_sales_trends(
    request: Request,
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    group_by: str = "day",
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Analyze sales trends over a specified period.
    """
    if start_date is None:
        start_date = date.today() - timedelta(days=30)
    if end_date is None:
        end_date = date.today()
    # Mock sales data for demonstration
    sales_data = _get_mock_sales_data(
        current_user.venue_id,
        start_date,
        end_date
    )

    analysis = analytics_service.analyze_sales_trends(
        sales_data=sales_data,
        group_by=group_by
    )

    return {
        "venue_id": current_user.venue_id,
        "period": f"{start_date} to {end_date}",
        "analysis": analysis
    }


@router.post("/trends/analyze", response_model=Dict[str, Any])
@limiter.limit("30/minute")
async def analyze_custom_trends(
    request: Request,
    trend_request: TrendAnalysisRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Analyze trends for a custom metric.
    """
    # Get data based on metric type
    if trend_request.metric == "sales":
        data = _get_mock_sales_data(
            current_user.venue_id,
            trend_request.start_date,
            trend_request.end_date
        )
    elif trend_request.metric == "orders":
        data = _get_mock_order_data(
            current_user.venue_id,
            trend_request.start_date,
            trend_request.end_date
        )
    elif trend_request.metric == "customers":
        data = _get_mock_customer_data(
            current_user.venue_id,
            trend_request.start_date,
            trend_request.end_date
        )
    else:
        data = []

    analysis = analytics_service.analyze_sales_trends(
        sales_data=data,
        group_by=trend_request.group_by
    )

    return {
        "metric": trend_request.metric,
        "period": f"{trend_request.start_date} to {trend_request.end_date}",
        "analysis": analysis
    }


# =============================================================================
# STOCK PREDICTION ENDPOINTS
# =============================================================================

@router.get("/predictions/stock-requirements", response_model=Dict[str, Any])
@limiter.limit("60/minute")
async def predict_stock_requirements(
    request: Request,
    lead_time_days: int = 3,
    forecast_days: int = 14,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Predict stock requirements based on demand forecast.
    Returns items that need reordering and suggested quantities.
    """
    # Get current stock levels
    current_stock = _get_mock_current_stock(current_user.venue_id)

    # Get demand forecast
    historical_data = _get_mock_historical_data(
        current_user.venue_id,
        datetime.now(timezone.utc) - timedelta(days=90),
        datetime.now(timezone.utc)
    )

    demand_forecast = analytics_service.forecast_demand(
        historical_data=historical_data,
        forecast_days=forecast_days
    )

    # Predict requirements
    requirements = analytics_service.predict_stock_requirements(
        current_stock=current_stock,
        demand_forecast=demand_forecast,
        lead_time_days=lead_time_days
    )

    return {
        "venue_id": current_user.venue_id,
        "lead_time_days": lead_time_days,
        "forecast_days": forecast_days,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "requirements": requirements,
        "summary": {
            "high_urgency": len([r for r in requirements if r["urgency"] == "high"]),
            "medium_urgency": len([r for r in requirements if r["urgency"] == "medium"]),
            "low_urgency": len([r for r in requirements if r["urgency"] == "low"])
        }
    }


@router.post("/predictions/reorder-suggestions", response_model=Dict[str, Any])
@limiter.limit("30/minute")
async def get_reorder_suggestions(
    request: Request,
    stock_request: StockPredictionRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Get specific reorder suggestions with quantities and timing.
    """
    current_stock = _get_mock_current_stock(current_user.venue_id)

    # Filter by item_ids if specified
    if stock_request.item_ids:
        current_stock = [s for s in current_stock if s["item_id"] in stock_request.item_ids]

    historical_data = _get_mock_historical_data(
        current_user.venue_id,
        datetime.now(timezone.utc) - timedelta(days=90),
        datetime.now(timezone.utc),
        item_ids=stock_request.item_ids
    )

    demand_forecast = analytics_service.forecast_demand(
        historical_data=historical_data,
        forecast_days=stock_request.forecast_days
    )

    requirements = analytics_service.predict_stock_requirements(
        current_stock=current_stock,
        demand_forecast=demand_forecast,
        lead_time_days=stock_request.lead_time_days
    )

    # Generate reorder suggestions
    suggestions = []
    for req in requirements:
        if req["suggested_order_quantity"] > 0:
            suggestions.append({
                "item_id": req["item_id"],
                "item_name": req["item_name"],
                "current_stock": req["current_stock"],
                "suggested_quantity": req["suggested_order_quantity"],
                "urgency": req["urgency"],
                "order_by_date": (
                    datetime.now(timezone.utc) + timedelta(days=max(0, req["days_until_reorder"] - stock_request.lead_time_days))
                ).strftime("%Y-%m-%d"),
                "expected_stockout_date": (
                    datetime.now(timezone.utc) + timedelta(days=req["days_until_reorder"])
                ).strftime("%Y-%m-%d")
            })

    return {
        "venue_id": current_user.venue_id,
        "parameters": {
            "lead_time_days": stock_request.lead_time_days,
            "forecast_days": stock_request.forecast_days
        },
        "suggestions": suggestions
    }


# =============================================================================
# DASHBOARD ENDPOINTS
# =============================================================================

@router.get("/dashboard/summary", response_model=Dict[str, Any])
@limiter.limit("60/minute")
async def get_analytics_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Get analytics dashboard summary with key metrics and forecasts.
    """
    today = datetime.now(timezone.utc)
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    # Sales trend
    sales_data = _get_mock_sales_data(current_user.venue_id, month_ago.date(), today.date())
    sales_analysis = analytics_service.analyze_sales_trends(sales_data, "day")

    # Top items forecast
    historical = _get_mock_historical_data(current_user.venue_id, month_ago, today)
    forecasts = analytics_service.forecast_demand(historical, forecast_days=7)

    # Stock alerts
    stock = _get_mock_current_stock(current_user.venue_id)
    requirements = analytics_service.predict_stock_requirements(stock, forecasts, lead_time_days=3)

    return {
        "venue_id": current_user.venue_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sales_trend": {
            "direction": sales_analysis["trend"]["direction"],
            "change_percent": sales_analysis["trend"]["change_percent"],
            "total_sales": sales_analysis["statistics"]["total"],
            "average_daily": sales_analysis["statistics"]["average"]
        },
        "demand_forecast": {
            "next_7_days": sum(f.forecast_values[0] for f in forecasts if f.forecast_values) if forecasts else 0,
            "trending_up": [f.item_name for f in forecasts if f.trend == "up"][:5],
            "trending_down": [f.item_name for f in forecasts if f.trend == "down"][:5]
        },
        "stock_alerts": {
            "high_urgency_count": len([r for r in requirements if r["urgency"] == "high"]),
            "items_to_reorder": [r["item_name"] for r in requirements if r["urgency"] == "high"][:5]
        },
        "key_insights": _generate_insights(sales_analysis, forecasts, requirements)
    }


# =============================================================================
# HELPER FUNCTIONS (Mock Data)
# =============================================================================

def _get_mock_historical_data(
    venue_id: int,
    start_date: datetime = Query(default=None),
    end_date: datetime = Query(default=None),
    category_id: int = None,
    item_ids: List[int] = None
) -> List[Dict]:
    """Generate mock historical demand data"""
    if start_date is None:
        start_date = date.today() - timedelta(days=30)
    if end_date is None:
        end_date = date.today()
    import random

    items = [
        {"id": 1, "name": "Beer - Draft", "category": 1},
        {"id": 2, "name": "Cocktail - Mojito", "category": 2},
        {"id": 3, "name": "Wine - House Red", "category": 3},
        {"id": 4, "name": "Whiskey Shot", "category": 4},
        {"id": 5, "name": "Vodka Soda", "category": 2},
    ]

    if item_ids:
        items = [i for i in items if i["id"] in item_ids]
    if category_id:
        items = [i for i in items if i["category"] == category_id]

    data = []
    current = start_date
    while current <= end_date:
        for item in items:
            # Add some seasonality (weekend bump)
            base = random.randint(10, 50)
            if current.weekday() >= 5:  # Weekend
                base = int(base * 1.5)

            data.append({
                "date": current.strftime("%Y-%m-%d"),
                "item_id": item["id"],
                "item_name": item["name"],
                "quantity": base + random.randint(-5, 5)
            })
        current += timedelta(days=1)

    return data


def _get_mock_sales_data(
    venue_id: int,
    start_date: date = Query(default=None),
    end_date: date = Query(default=None)
) -> List[Dict]:
    """Generate mock sales data"""
    if start_date is None:
        start_date = date.today() - timedelta(days=30)
    if end_date is None:
        end_date = date.today()
    import random

    data = []
    current = start_date
    while current <= end_date:
        base_amount = random.uniform(2000, 5000)
        if current.weekday() >= 5:  # Weekend
            base_amount *= 1.5

        data.append({
            "date": current.strftime("%Y-%m-%d"),
            "amount": base_amount + random.uniform(-500, 500)
        })
        current += timedelta(days=1)

    return data


def _get_mock_order_data(
    venue_id: int,
    start_date: date = Query(default=None),
    end_date: date = Query(default=None)
) -> List[Dict]:
    """Generate mock order count data"""
    if start_date is None:
        start_date = date.today() - timedelta(days=30)
    if end_date is None:
        end_date = date.today()
    import random

    data = []
    current = start_date
    while current <= end_date:
        base_orders = random.randint(50, 150)
        if current.weekday() >= 5:
            base_orders = int(base_orders * 1.4)

        data.append({
            "date": current.strftime("%Y-%m-%d"),
            "amount": base_orders
        })
        current += timedelta(days=1)

    return data


def _get_mock_customer_data(
    venue_id: int,
    start_date: date = Query(default=None),
    end_date: date = Query(default=None)
) -> List[Dict]:
    """Generate mock customer count data"""
    if start_date is None:
        start_date = date.today() - timedelta(days=30)
    if end_date is None:
        end_date = date.today()
    import random

    data = []
    current = start_date
    while current <= end_date:
        base_customers = random.randint(80, 200)
        if current.weekday() >= 5:
            base_customers = int(base_customers * 1.3)

        data.append({
            "date": current.strftime("%Y-%m-%d"),
            "amount": base_customers
        })
        current += timedelta(days=1)

    return data


def _get_mock_current_stock(venue_id: int) -> List[Dict]:
    """Generate mock current stock levels"""
    return [
        {"item_id": 1, "item_name": "Beer - Draft", "quantity": 50, "reorder_point": 20},
        {"item_id": 2, "item_name": "Cocktail - Mojito", "quantity": 15, "reorder_point": 10},
        {"item_id": 3, "item_name": "Wine - House Red", "quantity": 25, "reorder_point": 15},
        {"item_id": 4, "item_name": "Whiskey Shot", "quantity": 8, "reorder_point": 10},
        {"item_id": 5, "item_name": "Vodka Soda", "quantity": 30, "reorder_point": 12},
    ]


def _generate_insights(
    sales_analysis: Dict,
    forecasts: List[ForecastResult],
    requirements: List[Dict]
) -> List[str]:
    """Generate key insights from analytics"""
    insights = []

    # Sales insight
    trend = sales_analysis.get("trend", {})
    if trend.get("direction") == "up":
        insights.append(f"Sales are trending up by {trend.get('change_percent', 0):.1f}% - consider increasing stock levels")
    elif trend.get("direction") == "down":
        insights.append(f"Sales are trending down by {abs(trend.get('change_percent', 0)):.1f}% - review pricing and promotions")

    # Stock insight
    high_urgency = [r for r in requirements if r["urgency"] == "high"]
    if high_urgency:
        insights.append(f"{len(high_urgency)} items need immediate reordering to avoid stockouts")

    # Forecast insight
    trending_up = [f for f in forecasts if f.trend == "up"]
    if len(trending_up) > 0:
        insights.append(f"{len(trending_up)} items showing increased demand - prepare for higher sales")

    if not insights:
        insights.append("All metrics are within normal ranges - operations running smoothly")

    return insights

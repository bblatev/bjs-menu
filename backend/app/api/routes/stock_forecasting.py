"""Stock Forecasting API routes.

Predictive demand forecasting, reorder suggestions, and trend analysis
powered by historical sales data.
"""

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.core.rbac import CurrentUser
from app.core.rate_limit import limiter
from app.db.session import DbSession
from app.services.stock_forecasting_service import StockForecastingService

router = APIRouter()


# ---------------------------------------------------------------------------
# Demand forecasting
# ---------------------------------------------------------------------------

@router.get("/demand/{product_id}")
@limiter.limit("60/minute")
def get_demand_forecast(
    request: Request,
    product_id: int,
    db: DbSession,
    current_user: CurrentUser,
    location_id: int = Query(default=1, description="Location to forecast for"),
    days_ahead: int = Query(default=7, ge=1, le=90, description="Days to forecast"),
):
    """Get daily demand forecast for a product.

    Returns predicted usage per day using weighted moving averages and
    day-of-week pattern adjustments.  Confidence level is based on the
    amount of historical data available.
    """
    svc = StockForecastingService(db)
    return svc.forecast_demand(
        product_id=product_id,
        location_id=location_id,
        days_ahead=days_ahead,
    )


# ---------------------------------------------------------------------------
# Day-of-week patterns
# ---------------------------------------------------------------------------

@router.get("/patterns/{product_id}")
@limiter.limit("60/minute")
def get_dow_patterns(
    request: Request,
    product_id: int,
    db: DbSession,
    current_user: CurrentUser,
    location_id: int = Query(default=1),
):
    """Get day-of-week usage patterns for a product.

    Reveals which days see the highest and lowest demand, and the
    weekend vs weekday ratio.
    """
    svc = StockForecastingService(db)
    return svc.get_day_of_week_patterns(
        product_id=product_id,
        location_id=location_id,
    )


# ---------------------------------------------------------------------------
# EOQ (Economic Order Quantity)
# ---------------------------------------------------------------------------

@router.get("/eoq/{product_id}")
@limiter.limit("60/minute")
def get_eoq(
    request: Request,
    product_id: int,
    db: DbSession,
    current_user: CurrentUser,
    location_id: int = Query(default=1),
    ordering_cost: float = Query(default=25.0, ge=0, description="Cost per order placed"),
    holding_cost_pct: float = Query(
        default=0.25, ge=0, le=1,
        description="Annual holding cost as a fraction of unit cost",
    ),
):
    """Calculate Economic Order Quantity (EOQ) for a product.

    Returns the optimal order size that minimises the sum of ordering
    and holding costs, along with the implied order frequency.
    """
    svc = StockForecastingService(db)
    result = svc.calculate_eoq(
        product_id=product_id,
        location_id=location_id,
        ordering_cost=ordering_cost,
        holding_cost_pct=holding_cost_pct,
    )
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["error"])
    return result


# ---------------------------------------------------------------------------
# Reorder suggestions
# ---------------------------------------------------------------------------

@router.get("/reorder-suggestions/{location_id}")
@limiter.limit("30/minute")
def get_reorder_suggestions(
    request: Request,
    location_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Generate reorder suggestions for all products at a location.

    Returns products whose current stock is at or below the calculated
    reorder point (based on demand forecast, lead time, and safety stock).
    Results are sorted by urgency: critical > high > normal.
    """
    svc = StockForecastingService(db)
    suggestions = svc.generate_reorder_suggestions(location_id)
    return {
        "location_id": location_id,
        "total": len(suggestions),
        "critical": len([s for s in suggestions if s["urgency"] == "critical"]),
        "high": len([s for s in suggestions if s["urgency"] == "high"]),
        "suggestions": suggestions,
    }


# ---------------------------------------------------------------------------
# Demand trends
# ---------------------------------------------------------------------------

@router.get("/trends/{location_id}")
@limiter.limit("30/minute")
def get_demand_trends(
    request: Request,
    location_id: int,
    db: DbSession,
    current_user: CurrentUser,
    top_n: int = Query(default=20, ge=1, le=100, description="Number of top items to return"),
):
    """Get demand trend analysis for a location.

    Compares recent 7-day average demand against the 30-day average
    to identify products that are trending up, down, or remaining stable.
    """
    svc = StockForecastingService(db)
    return svc.get_demand_trends(location_id=location_id, top_n=top_n)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@router.get("/dashboard/{location_id}")
@limiter.limit("15/minute")
def get_forecasting_dashboard(
    request: Request,
    location_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Full stock forecasting dashboard for a location.

    Includes:
    - Reorder suggestions (sorted by urgency)
    - Demand trend analysis (trending up/down)
    - Summary statistics
    """
    svc = StockForecastingService(db)
    return svc.get_dashboard(location_id)


# ---------------------------------------------------------------------------
# Safety stock
# ---------------------------------------------------------------------------

@router.get("/safety-stock/{product_id}")
@limiter.limit("60/minute")
def get_safety_stock(
    request: Request,
    product_id: int,
    db: DbSession,
    current_user: CurrentUser,
    location_id: int = Query(default=1),
    service_level: float = Query(
        default=0.95, ge=0.5, le=0.999,
        description="Desired service level (probability of not stocking out)",
    ),
):
    """Calculate safety stock for a product at a given service level.

    Uses the standard safety stock formula: SS = Z * sigma_d * sqrt(L)
    where Z is the z-score for the service level, sigma_d is the standard
    deviation of daily demand, and L is the lead time in days.
    """
    svc = StockForecastingService(db)
    result = svc.calculate_safety_stock(
        product_id=product_id,
        location_id=location_id,
        service_level=service_level,
    )
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["error"])
    return result

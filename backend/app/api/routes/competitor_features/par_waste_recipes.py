"""Par levels, waste, recipes & stock takes"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body, Request, UploadFile, File, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Dict, Optional, Any
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal
from enum import Enum

from app.core.rate_limit import limiter
from app.db.session import get_db

# Import shared schemas and models
from app.api.routes.competitor_features._shared import *

router = APIRouter()

@router.post("/par-levels/{stock_item_id}/calculate", response_model=ParLevelConfigResponse)
@limiter.limit("30/minute")
async def calculate_par_levels(
    request: Request,
    stock_item_id: int,
    historical_days: int = 30,
    safety_days: int = 2,
    target_days: int = 7,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Auto-calculate par levels for a stock item"""
    service = ParLevelService(db)
    config = service.auto_calculate_par_levels(
        venue_id=current_user.venue_id,
        stock_item_id=stock_item_id,
        historical_days=historical_days,
        safety_days=safety_days,
        target_days=target_days
    )

    if not config:
        raise HTTPException(status_code=400, detail="Not enough usage data")

    return config


@router.get("/par-levels", response_model=List[ParLevelConfigResponse])
@limiter.limit("60/minute")
async def list_par_levels(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List all par level configurations"""
    configs = db.query(ParLevelConfig).filter(
        ParLevelConfig.venue_id == current_user.venue_id
    ).all()
    return configs


@router.get("/par-levels/alerts")
@limiter.limit("60/minute")
async def get_par_level_alerts(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get items below par levels"""
    configs = db.query(ParLevelConfig).filter(
        ParLevelConfig.venue_id == current_user.venue_id
    ).all()

    alerts = []
    for config in configs:
        stock = db.query(StockItem).filter(StockItem.id == config.stock_item_id).first()
        if stock and float(stock.quantity) < config.minimum_level:
            alerts.append({
                'stock_item_id': stock.id,
                'name': stock.name,
                'current_quantity': float(stock.quantity),
                'minimum_level': config.minimum_level,
                'par_level': config.par_level,
                'order_quantity': config.par_level - float(stock.quantity)
            })

    return sorted(alerts, key=lambda x: x['current_quantity'])


# =============================================================================
# WASTE TRACKING ENDPOINTS
# =============================================================================

@router.post("/waste", response_model=WasteLogResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def log_waste(
    request: Request,
    waste_data: WasteLogCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Log a waste event"""
    service = WasteAnalyticsService(db)
    log = service.log_waste(
        venue_id=current_user.venue_id,
        recorded_by=current_user.id,
        **waste_data.model_dump()
    )
    return log


@router.get("/waste/logs", response_model=List[WasteLogResponse])
@limiter.limit("60/minute")
async def list_waste_logs(
    request: Request,
    days: int = 7,
    waste_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List waste logs"""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    query = db.query(WasteLog).filter(
        WasteLog.venue_id == current_user.venue_id,
        WasteLog.recorded_at >= start_date
    )

    if waste_type:
        query = query.filter(WasteLog.waste_type == waste_type)

    return query.order_by(WasteLog.recorded_at.desc()).all()


@router.get("/waste/analytics", response_model=WasteAnalyticsResponse)
@limiter.limit("60/minute")
async def get_waste_analytics(
    request: Request,
    analytics_date: date = Query(default=None),
    period_type: str = "daily",
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get or generate waste analytics"""
    if analytics_date is None:
        analytics_date = date.today()
    service = WasteAnalyticsService(db)
    analytics = service.generate_analytics(
        venue_id=current_user.venue_id,
        analytics_date=analytics_date,
        period_type=period_type
    )
    return analytics


@router.get("/waste/summary")
@limiter.limit("60/minute")
async def get_waste_summary(
    request: Request,
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get waste summary statistics"""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    logs = db.query(WasteLog).filter(
        WasteLog.venue_id == current_user.venue_id,
        WasteLog.recorded_at >= start_date
    ).all()

    total_cost = sum(log.total_cost for log in logs)
    preventable_cost = sum(log.total_cost for log in logs if log.is_preventable)

    by_type = {}
    for log in logs:
        if log.waste_type not in by_type:
            by_type[log.waste_type] = 0
        by_type[log.waste_type] += log.total_cost

    return {
        "period_days": days,
        "total_waste_cost": total_cost,
        "daily_average": total_cost / days if days > 0 else 0,
        "preventable_cost": preventable_cost,
        "preventable_percent": (preventable_cost / total_cost * 100) if total_cost > 0 else 0,
        "by_type": by_type,
        "log_count": len(logs)
    }


# =============================================================================
# RECIPE SCALING ENDPOINTS
# =============================================================================

@router.post("/recipes/{menu_item_id}/scale", response_model=RecipeScaleResponse)
@limiter.limit("30/minute")
async def scale_recipe(
    request: Request,
    menu_item_id: int,
    body: RecipeScaleRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Scale a recipe to a target yield"""
    service = RecipeScalingService(db)
    result = service.scale_recipe(
        venue_id=current_user.venue_id,
        menu_item_id=menu_item_id,
        target_yield=body.target_yield,
        created_by=current_user.id,
        purpose=body.purpose
    )

    if not result:
        raise HTTPException(status_code=404, detail="Recipe not found")

    return result


@router.get("/recipes/scale-logs")
@limiter.limit("60/minute")
async def list_recipe_scale_logs(
    request: Request,
    menu_item_id: Optional[int] = None,
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List recipe scaling logs"""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    query = db.query(RecipeScaleLog).filter(
        RecipeScaleLog.venue_id == current_user.venue_id,
        RecipeScaleLog.created_at >= start_date
    )

    if menu_item_id:
        query = query.filter(RecipeScaleLog.menu_item_id == menu_item_id)

    return query.order_by(RecipeScaleLog.created_at.desc()).all()


# =============================================================================
# STOCK TAKING ENDPOINTS
# =============================================================================

@router.post("/stock-takes", response_model=StockTakeResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_stock_take(
    request: Request,
    body: StockTakeCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Create a new stock take session"""
    service = StockTakingService(db)
    stock_take = service.create_stock_take(
        venue_id=current_user.venue_id,
        created_by=current_user.id,
        **body.model_dump()
    )
    return stock_take


@router.get("/stock-takes", response_model=List[StockTakeResponse])
@limiter.limit("60/minute")
async def list_stock_takes(
    request: Request,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List stock takes"""
    query = db.query(StockTake).filter(
        StockTake.venue_id == current_user.venue_id
    )

    if status_filter:
        query = query.filter(StockTake.status == status_filter)

    return query.order_by(StockTake.created_at.desc()).all()


@router.get("/stock-takes/{stock_take_id}")
@limiter.limit("60/minute")
async def get_stock_take(
    request: Request,
    stock_take_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get stock take details with items"""
    stock_take = db.query(StockTake).filter(
        StockTake.id == stock_take_id,
        StockTake.venue_id == current_user.venue_id
    ).first()

    if not stock_take:
        raise HTTPException(status_code=404, detail="Stock take not found")

    items = db.query(StockTakeItem).filter(
        StockTakeItem.stock_take_id == stock_take_id
    ).all()

    return {
        "stock_take": stock_take,
        "items": items
    }


@router.post("/stock-takes/{stock_take_id}/start")
@limiter.limit("30/minute")
async def start_stock_take(
    request: Request,
    stock_take_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Start a stock take session"""
    stock_take = db.query(StockTake).filter(
        StockTake.id == stock_take_id,
        StockTake.venue_id == current_user.venue_id
    ).first()

    if not stock_take:
        raise HTTPException(status_code=404, detail="Stock take not found")

    stock_take.status = "in_progress"
    stock_take.started_at = datetime.now(timezone.utc)
    db.commit()

    return {"status": "in_progress"}


@router.post("/stock-takes/items/{item_id}/count")
@limiter.limit("30/minute")
async def record_count(
    request: Request,
    item_id: int,
    body: CountRecordRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Record a count for a stock take item"""
    service = StockTakingService(db)
    item = service.record_count(
        stock_take_item_id=item_id,
        counted_quantity=body.counted_quantity,
        counted_by=current_user.id,
        location=body.location
    )

    if not item:
        raise HTTPException(status_code=404, detail="Stock take item not found")

    return item


@router.post("/stock-takes/{stock_take_id}/complete")
@limiter.limit("30/minute")
async def complete_stock_take(
    request: Request,
    stock_take_id: int,
    apply_adjustments: bool = True,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Complete stock take and apply adjustments"""
    service = StockTakingService(db)
    stock_take = service.complete_and_adjust(
        stock_take_id=stock_take_id,
        approved_by=current_user.id,
        apply_adjustments=apply_adjustments
    )

    if not stock_take:
        raise HTTPException(status_code=404, detail="Stock take not found")

    return stock_take


@router.get("/stock-takes/{stock_take_id}/variance-report")
@limiter.limit("60/minute")
async def get_variance_report(
    request: Request,
    stock_take_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get detailed variance report for a stock take"""
    stock_take = db.query(StockTake).filter(
        StockTake.id == stock_take_id,
        StockTake.venue_id == current_user.venue_id
    ).first()

    if not stock_take:
        raise HTTPException(status_code=404, detail="Stock take not found")

    items = db.query(StockTakeItem).filter(
        StockTakeItem.stock_take_id == stock_take_id,
        StockTakeItem.variance_quantity != 0
    ).order_by(StockTakeItem.variance_value.desc()).all()

    overages = [i for i in items if i.variance_type == 'overage']
    shortages = [i for i in items if i.variance_type == 'shortage']

    return {
        "stock_take_number": stock_take.stock_take_number,
        "total_variance_value": stock_take.total_variance_value,
        "variance_percent": stock_take.variance_percent,
        "overage_count": len(overages),
        "overage_value": sum(i.variance_value or 0 for i in overages),
        "shortage_count": len(shortages),
        "shortage_value": sum(i.variance_value or 0 for i in shortages),
        "items_requiring_investigation": [i for i in items if i.requires_investigation],
        "all_variances": items
    }


# =============================================================================
# INVOICE SCANNING ENDPOINTS
# =============================================================================


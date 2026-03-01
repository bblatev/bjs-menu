"""Menu engineering, 86 system & demand forecast"""
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

@router.get("/")
@limiter.limit("60/minute")
async def get_competitor_features_root(request: Request, db: Session = Depends(get_db)):
    """Competitor feature parity overview."""
    return {"module": "competitor-features", "status": "active", "features": ["menu-engineering", "86-board", "demand-forecast", "variance-analysis"], "endpoints": ["/menu-engineering/reports", "/86/config", "/forecast/items"]}


@router.post("/menu-engineering/report", response_model=MenuEngineeringReportResponse)
@limiter.limit("30/minute")
async def generate_menu_engineering_report(
    request: Request,
    body: DateRangeRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Generate menu engineering report with BCG matrix classification"""
    service = MenuEngineeringService(db)
    report = service.generate_engineering_report(
        venue_id=current_user.venue_id,
        period_start=body.period_start,
        period_end=body.period_end,
        generated_by=current_user.id
    )
    if not report:
        return {
            "id": 0,
            "report_name": f"Menu Engineering {body.period_start} to {body.period_end}",
            "period_start": body.period_start,
            "period_end": body.period_end,
            "total_revenue": 0,
            "total_food_cost": 0,
            "total_gross_profit": 0,
            "overall_food_cost_percent": 0,
            "stars_count": 0,
            "puzzles_count": 0,
            "dogs_count": 0,
            "cash_cows_count": 0,
            "items_to_promote": [],
            "items_to_reprice": [],
            "items_to_remove": [],
            "generated_at": datetime.now(timezone.utc),
        }
    return report


@router.get("/menu-engineering/reports", response_model=List[MenuEngineeringReportResponse])
@limiter.limit("60/minute")
async def list_menu_engineering_reports(
    request: Request,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List menu engineering reports"""
    reports = db.query(MenuEngineeringReport).filter(
        MenuEngineeringReport.venue_id == current_user.venue_id
    ).order_by(MenuEngineeringReport.generated_at.desc()).offset(skip).limit(limit).all()
    return reports


@router.get("/menu-engineering/item/{menu_item_id}/profitability")
@limiter.limit("60/minute")
async def get_item_profitability(
    request: Request,
    menu_item_id: int,
    period_start: date = Query(default=None),
    period_end: date = Query(default=None),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get profitability analysis for a specific menu item"""
    if period_start is None:
        period_start = date.today() - timedelta(days=30)
    if period_end is None:
        period_end = date.today()
    service = MenuEngineeringService(db)
    result = service.calculate_item_profitability(
        venue_id=current_user.venue_id,
        menu_item_id=menu_item_id,
        period_start=period_start,
        period_end=period_end
    )
    if not result:
        raise HTTPException(status_code=404, detail="Menu item not found")
    return result


# =============================================================================
# 86 AUTOMATION ENDPOINTS
# =============================================================================

@router.get("/86/config")
@limiter.limit("60/minute")
async def get_86_config(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get 86 automation configuration"""
    config = db.query(Item86Config).filter(
        Item86Config.venue_id == current_user.venue_id
    ).first()

    if not config:
        # Create default config
        config = Item86Config(venue_id=current_user.venue_id)
        db.add(config)
        db.commit()
        db.refresh(config)

    return config


@router.put("/86/config")
@limiter.limit("30/minute")
async def update_86_config(
    request: Request,
    config_data: Item86ConfigUpdate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Update 86 automation configuration"""
    config = db.query(Item86Config).filter(
        Item86Config.venue_id == current_user.venue_id
    ).first()

    if not config:
        config = Item86Config(venue_id=current_user.venue_id)
        db.add(config)

    for field, value in config_data.model_dump().items():
        setattr(config, field, value)

    db.commit()
    db.refresh(config)
    return config


@router.post("/86/check", response_model=List[Item86LogResponse])
@limiter.limit("30/minute")
async def check_86_status(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Check and update 86 status for all items"""
    service = Item86Service(db)
    logs = service.check_and_update_86_status(current_user.venue_id)
    return logs


@router.post("/86/item/{menu_item_id}", response_model=Item86LogResponse)
@limiter.limit("30/minute")
async def manual_86_item(
    request: Request,
    menu_item_id: int,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Manually 86 an item"""
    service = Item86Service(db)
    log = service.manual_86(
        venue_id=current_user.venue_id,
        menu_item_id=menu_item_id,
        staff_user_id=current_user.id,
        reason=reason
    )
    if not log:
        raise HTTPException(status_code=404, detail="Menu item not found")
    return log


@router.post("/86/item/{menu_item_id}/restore", response_model=Item86LogResponse)
@limiter.limit("30/minute")
async def restore_86_item(
    request: Request,
    menu_item_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Restore an 86'd item"""
    service = Item86Service(db)
    log = service.manual_restore(
        venue_id=current_user.venue_id,
        menu_item_id=menu_item_id,
        staff_user_id=current_user.id
    )
    if not log:
        raise HTTPException(status_code=404, detail="Menu item not found")
    return log


@router.get("/86/logs", response_model=List[Item86LogResponse])
@limiter.limit("60/minute")
async def get_86_logs(
    request: Request,
    menu_item_id: Optional[int] = None,
    days: int = 7,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get 86 event logs"""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    query = db.query(Item86Log).filter(
        Item86Log.venue_id == current_user.venue_id,
        Item86Log.started_at >= start_date
    )

    if menu_item_id:
        query = query.filter(Item86Log.menu_item_id == menu_item_id)

    logs = query.order_by(Item86Log.started_at.desc()).all()
    return logs


# =============================================================================
# DEMAND FORECASTING ENDPOINTS
# =============================================================================

@router.post("/forecast/generate")
@limiter.limit("30/minute")
async def generate_forecasts(
    request: Request,
    forecast_date: date = Query(default=None),
    days_history: int = 30,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Generate demand forecasts for a date"""
    if forecast_date is None:
        forecast_date = date.today()
    service = DemandForecastingService(db)

    # Generate menu item forecasts
    item_forecasts = service.generate_daily_forecast(
        venue_id=current_user.venue_id,
        forecast_date=forecast_date,
        days_history=days_history
    )

    # Generate ingredient forecasts
    ingredient_forecasts = service.generate_ingredient_forecast(
        venue_id=current_user.venue_id,
        forecast_date=forecast_date
    )

    return {
        "forecast_date": forecast_date,
        "item_forecasts_count": len(item_forecasts),
        "ingredient_forecasts_count": len(ingredient_forecasts)
    }


@router.get("/forecast/items", response_model=List[DemandForecastResponse])
@limiter.limit("60/minute")
async def get_item_forecasts(
    request: Request,
    forecast_date: date = Query(default=None),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get menu item forecasts for a date"""
    if forecast_date is None:
        forecast_date = date.today()
    forecasts = db.query(DemandForecast).filter(
        DemandForecast.venue_id == current_user.venue_id,
        DemandForecast.forecast_date == forecast_date
    ).all()
    return forecasts


@router.get("/forecast/ingredients", response_model=List[IngredientForecastResponse])
@limiter.limit("60/minute")
async def get_ingredient_forecasts(
    request: Request,
    forecast_date: date = Query(default=None),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get ingredient forecasts for a date"""
    if forecast_date is None:
        forecast_date = date.today()
    forecasts = db.query(IngredientForecast).filter(
        IngredientForecast.venue_id == current_user.venue_id,
        IngredientForecast.forecast_date == forecast_date
    ).all()
    return forecasts


@router.get("/forecast/stockouts")
@limiter.limit("60/minute")
async def get_predicted_stockouts(
    request: Request,
    days_ahead: int = 7,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get ingredients predicted to stock out"""
    end_date = date.today() + timedelta(days=days_ahead)

    forecasts = db.query(IngredientForecast).filter(
        IngredientForecast.venue_id == current_user.venue_id,
        IngredientForecast.forecast_date <= end_date,
        IngredientForecast.will_stock_out == True
    ).order_by(IngredientForecast.forecast_date).all()

    return forecasts


# =============================================================================
# AUTO PURCHASE ORDER ENDPOINTS
# =============================================================================


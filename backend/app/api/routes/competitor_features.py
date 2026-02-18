from datetime import timezone
"""
Competitor Features API Endpoints
Toast, TouchBistro, iiko feature parity
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import date, datetime, timedelta
from pydantic import BaseModel, ConfigDict
import os
import uuid
import logging
import re

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.core.rbac import get_current_user
from app.models import StaffUser, MenuItem, StockItem, Supplier, PurchaseOrder, PurchaseOrderItem
from app.services.competitor_features_service import (
    MenuEngineeringService, Item86Service, DemandForecastingService,
    AutoPurchaseOrderService, FoodCostService, SupplierPerformanceService,
    ParLevelService, WasteAnalyticsService, RecipeScalingService,
    StockTakingService
)
from app.models.competitor_features import (
    Item86Config, Item86Log, IngredientForecast,
    AutoPurchaseOrderRule, SuggestedPurchaseOrder, FoodCostSnapshot,
    SupplierPerformance, SupplierIssue, ParLevelConfig, WasteLog,
    RecipeScaleLog, StockTake, StockTakeItem, ScannedInvoice,
    InvoiceMatchingRule
)
from app.models.feature_models import MenuEngineeringReport, DemandForecast


router = APIRouter()


def require_manager(current_user = Depends(get_current_user)):
    """Require manager or above role."""
    if not hasattr(current_user, 'role'):
        return current_user
    if current_user.role not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Manager access required")
    return current_user



# =============================================================================
# SCHEMAS
# =============================================================================

class DateRangeRequest(BaseModel):
    period_start: date
    period_end: date


class MenuEngineeringReportResponse(BaseModel):
    id: int
    report_name: str
    period_start: date
    period_end: date
    total_revenue: float
    total_food_cost: float
    total_gross_profit: float
    overall_food_cost_percent: float
    stars_count: int
    puzzles_count: int
    dogs_count: int
    cash_cows_count: int
    items_to_promote: List[int]
    items_to_reprice: List[int]
    items_to_remove: List[int]
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Item86ConfigUpdate(BaseModel):
    auto_86_enabled: bool = True
    auto_restore_enabled: bool = True
    threshold_quantity: float = 0.0
    notify_kitchen: bool = True
    notify_floor: bool = True
    notify_manager: bool = True


class Item86LogResponse(BaseModel):
    id: int
    menu_item_id: int
    event_type: str
    triggered_by: str
    reason: Optional[str]
    started_at: datetime
    ended_at: Optional[datetime]
    duration_minutes: Optional[int]

    model_config = ConfigDict(from_attributes=True)


class DemandForecastResponse(BaseModel):
    id: int
    forecast_date: date
    menu_item_id: Optional[int]
    predicted_quantity: int
    confidence_low: int
    confidence_high: int
    confidence_score: float
    day_of_week: Optional[int]
    historical_avg: Optional[float]
    trend_factor: float

    model_config = ConfigDict(from_attributes=True)


class IngredientForecastResponse(BaseModel):
    id: int
    forecast_date: date
    stock_item_id: int
    predicted_usage: float
    current_stock: float
    will_stock_out: bool
    days_of_stock: Optional[float]
    suggested_order_quantity: float

    model_config = ConfigDict(from_attributes=True)


class AutoPORuleCreate(BaseModel):
    stock_item_id: int
    reorder_point: float
    reorder_quantity: float
    use_par_level: bool = False
    par_level: Optional[float] = None
    preferred_supplier_id: Optional[int] = None
    minimum_order_quantity: Optional[float] = None


class SuggestedPOResponse(BaseModel):
    id: int
    supplier_id: int
    status: str
    items: List[dict]
    subtotal: float
    trigger_reason: str
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FoodCostResponse(BaseModel):
    id: int
    menu_item_id: int
    ingredients: List[dict]
    ingredient_cost: float
    adjusted_cost: float
    total_plate_cost: float
    menu_price: float
    food_cost_percent: float
    contribution_margin: float
    gross_profit_percent: float
    suggested_price_for_target: Optional[float]
    cost_change_percent: Optional[float]
    calculated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SupplierPerformanceResponse(BaseModel):
    id: int
    supplier_id: int
    period_start: date
    period_end: date
    total_orders: int
    total_order_value: float
    on_time_percent: float
    quality_score: float
    overall_score: float

    model_config = ConfigDict(from_attributes=True)


class SupplierIssueCreate(BaseModel):
    supplier_id: int
    issue_type: str
    severity: str
    description: str
    purchase_order_id: Optional[int] = None
    affected_items: Optional[List[dict]] = None


class WasteLogCreate(BaseModel):
    item_name: str
    quantity: float
    unit: str
    waste_type: str
    stock_item_id: Optional[int] = None
    menu_item_id: Optional[int] = None
    cause: Optional[str] = None
    notes: Optional[str] = None
    station_id: Optional[int] = None


class WasteLogResponse(BaseModel):
    id: int
    item_name: str
    quantity: float
    unit: str
    total_cost: float
    waste_type: str
    cause: Optional[str]
    is_preventable: bool
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WasteAnalyticsResponse(BaseModel):
    id: int
    analytics_date: date
    period_type: str
    total_waste_cost: float
    total_waste_quantity: float
    waste_percent_of_revenue: float
    waste_by_type: Optional[dict]
    top_waste_items: Optional[List[dict]]
    preventable_waste_cost: float
    preventable_waste_percent: float

    model_config = ConfigDict(from_attributes=True)


class RecipeScaleRequest(BaseModel):
    target_yield: float
    purpose: Optional[str] = None


class RecipeScaleResponse(BaseModel):
    id: int
    menu_item_id: int
    original_yield: float
    scaled_yield: float
    scale_factor: float
    scaled_ingredients: List[dict]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StockTakeCreate(BaseModel):
    name: Optional[str] = None
    scope_type: str = "full"
    blind_count: bool = True
    category_ids: Optional[List[int]] = None


class StockTakeResponse(BaseModel):
    id: int
    stock_take_number: str
    name: Optional[str]
    scope_type: str
    status: str
    items_counted: int
    items_with_variance: int
    total_expected_value: float
    total_counted_value: float
    total_variance_value: float
    variance_percent: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CountRecordRequest(BaseModel):
    counted_quantity: float
    location: Optional[str] = None


class ParLevelConfigResponse(BaseModel):
    id: int
    stock_item_id: int
    minimum_level: float
    par_level: float
    maximum_level: Optional[float]
    safety_stock: float
    average_daily_usage: Optional[float]
    last_calculated: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# MENU ENGINEERING ENDPOINTS
# =============================================================================

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

@router.post("/auto-po/rules", status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_auto_po_rule(
    request: Request,
    rule_data: AutoPORuleCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Create auto purchase order rule"""
    rule = AutoPurchaseOrderRule(
        venue_id=current_user.venue_id,
        **rule_data.model_dump()
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.get("/auto-po/rules")
@limiter.limit("60/minute")
async def list_auto_po_rules(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List all auto PO rules"""
    rules = db.query(AutoPurchaseOrderRule).filter(
        AutoPurchaseOrderRule.venue_id == current_user.venue_id
    ).all()
    return rules


@router.post("/auto-po/generate", response_model=List[SuggestedPOResponse])
@limiter.limit("30/minute")
async def generate_suggested_orders(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Generate suggested purchase orders based on rules"""
    service = AutoPurchaseOrderService(db)
    suggestions = service.check_and_generate_orders(current_user.venue_id)
    return suggestions


@router.get("/auto-po/suggestions", response_model=List[SuggestedPOResponse])
@limiter.limit("60/minute")
async def list_suggested_orders(
    request: Request,
    status_filter: Optional[str] = "pending",
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List suggested purchase orders"""
    query = db.query(SuggestedPurchaseOrder).filter(
        SuggestedPurchaseOrder.location_id == current_user.venue_id
    )

    if status_filter:
        query = query.filter(SuggestedPurchaseOrder.status == status_filter)

    return query.order_by(SuggestedPurchaseOrder.generated_at.desc()).all()


@router.post("/auto-po/suggestions/{suggestion_id}/approve")
@limiter.limit("30/minute")
async def approve_suggested_order(
    request: Request,
    suggestion_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Approve and convert suggested order to actual PO"""
    service = AutoPurchaseOrderService(db)
    po = service.approve_and_convert(suggestion_id, current_user.id)

    if not po:
        raise HTTPException(status_code=404, detail="Suggestion not found or already processed")

    return {"purchase_order_id": po.id, "order_number": po.order_number}


# =============================================================================
# FOOD COST CALCULATOR ENDPOINTS
# =============================================================================

@router.get("/food-cost/item/{menu_item_id}", response_model=FoodCostResponse)
@limiter.limit("60/minute")
async def calculate_item_food_cost(
    request: Request,
    menu_item_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Calculate food cost for a menu item"""
    service = FoodCostService(db)
    result = service.calculate_menu_item_cost(current_user.venue_id, menu_item_id)

    if not result:
        raise HTTPException(status_code=404, detail="Menu item not found")

    return result


@router.post("/food-cost/calculate-all")
@limiter.limit("30/minute")
async def calculate_all_food_costs(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Calculate food costs for all menu items"""
    logger = logging.getLogger(__name__)
    service = FoodCostService(db)

    items = db.query(MenuItem).filter(
        MenuItem.venue_id == current_user.venue_id,
        MenuItem.available == True
    ).all()

    calculated = 0
    failed = 0
    errors = []
    for item in items:
        try:
            result = service.calculate_menu_item_cost(current_user.venue_id, item.id)
            if result:
                calculated += 1
            else:
                failed += 1
                errors.append({"menu_item_id": item.id, "name": item.name, "error": "No recipe found"})
        except Exception as e:
            failed += 1
            error_msg = str(e)
            logger.warning(f"Failed to calculate food cost for menu item {item.id}: {error_msg}")
            errors.append({"menu_item_id": item.id, "name": item.name, "error": error_msg})

    return {
        "calculated_items": calculated,
        "failed_items": failed,
        "total_items": len(items),
        "errors": errors[:10] if errors else []  # Return first 10 errors for debugging
    }


@router.get("/food-cost/snapshot")
@limiter.limit("60/minute")
async def get_food_cost_snapshot(
    request: Request,
    snapshot_date: date = Query(default=None),
    period_type: str = "daily",
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get or generate food cost snapshot"""
    if snapshot_date is None:
        snapshot_date = date.today()
    service = FoodCostService(db)
    snapshot = service.generate_cost_snapshot(
        venue_id=current_user.venue_id,
        snapshot_date=snapshot_date,
        period_type=period_type
    )
    return snapshot


@router.get("/food-cost/trend")
@limiter.limit("60/minute")
async def get_food_cost_trend(
    request: Request,
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get food cost trend over time"""
    start_date = date.today() - timedelta(days=days)

    snapshots = db.query(FoodCostSnapshot).filter(
        FoodCostSnapshot.venue_id == current_user.venue_id,
        FoodCostSnapshot.snapshot_date >= start_date,
        FoodCostSnapshot.period_type == "daily"
    ).order_by(FoodCostSnapshot.snapshot_date).all()

    return snapshots


# =============================================================================
# SUPPLIER PERFORMANCE ENDPOINTS
# =============================================================================

@router.get("/supplier-performance/ranking")
@limiter.limit("60/minute")
async def get_supplier_ranking(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get suppliers ranked by performance"""
    # Get latest performance for each supplier
    subq = db.query(
        SupplierPerformance.supplier_id,
        func.max(SupplierPerformance.calculated_at).label('latest')
    ).filter(
        SupplierPerformance.venue_id == current_user.venue_id
    ).group_by(SupplierPerformance.supplier_id).subquery()

    perfs = db.query(SupplierPerformance).filter(
        SupplierPerformance.venue_id == current_user.venue_id
    ).join(
        subq,
        (SupplierPerformance.supplier_id == subq.c.supplier_id) &
        (SupplierPerformance.calculated_at == subq.c.latest)
    ).order_by(SupplierPerformance.overall_score.desc()).all()

    return perfs


@router.get("/supplier-performance/{supplier_id}", response_model=SupplierPerformanceResponse)
@limiter.limit("60/minute")
async def get_supplier_performance(
    request: Request,
    supplier_id: int,
    period_start: date = Query(default=None),
    period_end: date = Query(default=None),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get or calculate supplier performance"""
    if period_start is None:
        period_start = date.today() - timedelta(days=30)
    if period_end is None:
        period_end = date.today()
    service = SupplierPerformanceService(db)
    perf = service.calculate_performance(
        venue_id=current_user.venue_id,
        supplier_id=supplier_id,
        period_start=period_start,
        period_end=period_end
    )
    return perf


@router.post("/supplier-issues", status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def report_supplier_issue(
    request: Request,
    issue_data: SupplierIssueCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Report an issue with a supplier"""
    service = SupplierPerformanceService(db)
    issue = service.report_issue(
        venue_id=current_user.venue_id,
        reported_by=current_user.id,
        **issue_data.model_dump()
    )
    return issue


@router.get("/supplier-issues")
@limiter.limit("60/minute")
async def list_supplier_issues(
    request: Request,
    supplier_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List supplier issues"""
    query = db.query(SupplierIssue).filter(
        SupplierIssue.venue_id == current_user.venue_id
    )

    if supplier_id:
        query = query.filter(SupplierIssue.supplier_id == supplier_id)
    if status_filter:
        query = query.filter(SupplierIssue.status == status_filter)

    return query.order_by(SupplierIssue.reported_at.desc()).all()


# =============================================================================
# PAR LEVEL ENDPOINTS
# =============================================================================

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

class InvoiceProcessRequest(BaseModel):
    """Request model for manual invoice processing"""
    force_reprocess: bool = False


class InvoiceVerifyRequest(BaseModel):
    """Request model for invoice verification"""
    supplier_id: Optional[int] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: Optional[float] = None
    line_items: Optional[List[dict]] = None
    notes: Optional[str] = None


class InvoiceMatchRequest(BaseModel):
    """Request model for matching invoice to PO"""
    purchase_order_id: int


class InvoiceResponse(BaseModel):
    id: int
    file_name: str
    file_url: str
    ocr_status: str
    supplier_id: Optional[int]
    invoice_number_extracted: Optional[str]
    invoice_date_extracted: Optional[date]
    total_extracted: Optional[float]
    verification_status: str
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)


@router.post("/invoices/upload", response_model=InvoiceResponse)
@limiter.limit("30/minute")
async def upload_invoice(
    request: Request,
    file: UploadFile = File(...),
    supplier_id: Optional[int] = None,
    auto_process: bool = True,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Upload an invoice for OCR processing"""
    logger = logging.getLogger(__name__)

    # Validate file type
    allowed_types = ['application/pdf', 'image/jpeg', 'image/png', 'image/tiff']
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: PDF, JPEG, PNG, TIFF"
        )

    # Generate unique filename
    file_ext = file.filename.split('.')[-1] if '.' in file.filename else 'pdf'
    unique_filename = f"{uuid.uuid4()}.{file_ext}"

    # Create upload directory
    upload_base_dir = os.environ.get('UPLOAD_DIR', '/tmp/uploads')
    upload_dir = os.path.join(upload_base_dir, 'invoices', str(current_user.venue_id))
    os.makedirs(upload_dir, exist_ok=True)

    # Full path for the file
    file_path = os.path.join(upload_dir, unique_filename)
    file_url = f"/uploads/invoices/{current_user.venue_id}/{unique_filename}"

    # Read file content
    file_content = await file.read()
    file_size = len(file_content)

    # Actually save the file to disk
    try:
        with open(file_path, 'wb') as f:
            f.write(file_content)
    except IOError as e:
        logger.error(f"Failed to save invoice file: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to save uploaded file"
        )

    # Determine file type
    file_type = 'pdf' if 'pdf' in file.content_type else 'image'

    invoice = ScannedInvoice(
        venue_id=current_user.venue_id,
        file_url=file_url,
        file_name=file.filename,
        file_type=file_type,
        file_size_bytes=file_size,
        ocr_status='pending',
        supplier_id=supplier_id,
        uploaded_by=current_user.id
    )

    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    # Auto-process if requested
    ocr_error = None
    if auto_process:
        try:
            _process_invoice_ocr(db, invoice, current_user.venue_id, file_path)
        except Exception as e:
            ocr_error = str(e)
            logger.error(f"Auto-process failed for invoice {invoice.id}: {e}")
            # Update invoice with error status
            invoice.ocr_status = 'failed'
            invoice.ocr_error = ocr_error
            db.commit()
            db.refresh(invoice)

    return invoice


def _process_invoice_ocr(db: Session, invoice: ScannedInvoice, venue_id: int, file_path: Optional[str] = None) -> ScannedInvoice:
    """
    Process invoice OCR using available OCR backend.

    Supports multiple OCR backends with fallback:
    1. pytesseract (local, free) - requires tesseract-ocr installed
    2. pdf2image + pytesseract for PDFs
    3. Falls back to manual extraction if no OCR available
    """
    logger = logging.getLogger(__name__)

    # Update status to processing
    invoice.ocr_status = 'processing'
    db.commit()

    extracted_text = ""
    ocr_confidence = 0.0

    try:
        # Try to extract text from the file
        if file_path and os.path.exists(file_path):
            extracted_text, ocr_confidence = _extract_text_from_file(file_path, invoice.file_type)

        if not extracted_text:
            # No text extracted - mark for manual processing
            invoice.ocr_status = 'pending_manual'
            invoice.ocr_error = 'OCR extraction returned no text. Manual entry required.'
            invoice.ocr_confidence = 0.0
            db.commit()
            return invoice

        # Store raw OCR text
        invoice.ocr_raw_text = extracted_text
        invoice.ocr_confidence = ocr_confidence

        # Parse extracted text for invoice data
        parsed_data = _parse_invoice_text(extracted_text)

        # Apply parsed data to invoice
        if parsed_data.get('supplier_name'):
            invoice.supplier_name_extracted = parsed_data['supplier_name']
        if parsed_data.get('invoice_number'):
            invoice.invoice_number_extracted = parsed_data['invoice_number']
        if parsed_data.get('invoice_date'):
            invoice.invoice_date_extracted = parsed_data['invoice_date']
        if parsed_data.get('due_date'):
            invoice.due_date_extracted = parsed_data['due_date']
        if parsed_data.get('subtotal'):
            invoice.subtotal_extracted = parsed_data['subtotal']
        if parsed_data.get('tax'):
            invoice.tax_extracted = parsed_data['tax']
        if parsed_data.get('total'):
            invoice.total_extracted = parsed_data['total']
        if parsed_data.get('line_items'):
            invoice.line_items_extracted = parsed_data['line_items']

        # Try to match supplier if not already set
        if not invoice.supplier_id and invoice.supplier_name_extracted:
            supplier = db.query(Supplier).filter(
                Supplier.venue_id == venue_id,
                Supplier.name.ilike(f"%{invoice.supplier_name_extracted}%")
            ).first()
            if supplier:
                invoice.supplier_id = supplier.id

        # Try to match line items to stock items using matching rules
        if invoice.line_items_extracted:
            matched_items = []
            for item in invoice.line_items_extracted:
                matched_item = _match_invoice_item_to_stock(
                    db, venue_id, item, invoice.supplier_id
                )
                matched_items.append(matched_item)
            invoice.line_items_extracted = matched_items

        invoice.ocr_status = 'completed'
        invoice.verification_status = 'unverified'

    except Exception as e:
        logger.exception(f"OCR processing failed for invoice {invoice.id}")
        invoice.ocr_status = 'failed'
        invoice.ocr_error = str(e)

    db.commit()
    return invoice


def _extract_text_from_file(file_path: str, file_type: str) -> tuple:
    """
    Extract text from file using available OCR libraries.
    Returns (extracted_text, confidence_score)
    """
    logger = logging.getLogger(__name__)
    extracted_text = ""
    confidence = 0.0

    try:
        if file_type == 'pdf':
            # Try to extract text from PDF
            try:
                # First try direct PDF text extraction (for digital PDFs)
                import PyPDF2
                with open(file_path, 'rb') as pdf_file:
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    for page in pdf_reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            extracted_text += page_text + "\n"

                if extracted_text.strip():
                    confidence = 0.95  # High confidence for digital PDFs
                    return extracted_text, confidence
            except ImportError:
                logger.debug("PyPDF2 not available, trying OCR")
            except Exception as e:
                logger.debug(f"PDF text extraction failed: {e}, trying OCR")

            # If no text extracted, try OCR on PDF pages
            try:
                from pdf2image import convert_from_path
                import pytesseract

                images = convert_from_path(file_path, dpi=300)
                for i, image in enumerate(images):
                    page_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
                    page_text = pytesseract.image_to_string(image)
                    extracted_text += page_text + "\n"

                    # Calculate average confidence from word confidences
                    confidences = [int(c) for c in page_data['conf'] if int(c) > 0]
                    if confidences:
                        confidence = sum(confidences) / len(confidences) / 100

            except ImportError:
                logger.warning("pdf2image or pytesseract not available for PDF OCR")
            except Exception as e:
                logger.error(f"PDF OCR failed: {e}")

        else:  # Image file
            try:
                import pytesseract
                from PIL import Image

                image = Image.open(file_path)

                # Get OCR data with confidence scores
                ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
                extracted_text = pytesseract.image_to_string(image)

                # Calculate average confidence
                confidences = [int(c) for c in ocr_data['conf'] if int(c) > 0]
                if confidences:
                    confidence = sum(confidences) / len(confidences) / 100

            except ImportError:
                logger.warning("pytesseract or PIL not available for image OCR")
            except Exception as e:
                logger.error(f"Image OCR failed: {e}")

    except Exception as e:
        logger.error(f"Text extraction failed: {e}")

    return extracted_text, confidence


def _parse_invoice_text(text: str) -> dict:
    """
    Parse extracted OCR text to identify invoice fields.
    Uses regex patterns to find common invoice elements.
    """
    result = {
        'supplier_name': None,
        'invoice_number': None,
        'invoice_date': None,
        'due_date': None,
        'subtotal': None,
        'tax': None,
        'total': None,
        'line_items': []
    }

    if not text:
        return result

    lines = text.split('\n')
    text_lower = text.lower()

    # Extract invoice number
    invoice_num_patterns = [
        r'invoice\s*#?\s*:?\s*([A-Z0-9-]+)',
        r'inv\s*#?\s*:?\s*([A-Z0-9-]+)',
        r'invoice\s+number\s*:?\s*([A-Z0-9-]+)',
        r'bill\s*#?\s*:?\s*([A-Z0-9-]+)',
    ]
    for pattern in invoice_num_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result['invoice_number'] = match.group(1).strip()
            break

    # Extract dates
    date_patterns = [
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',  # DD/MM/YYYY or MM/DD/YYYY
        r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})',    # YYYY-MM-DD
        r'(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{2,4})',  # DD Month YYYY
    ]

    dates_found = []
    for pattern in date_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        dates_found.extend(matches)

    if dates_found:
        # First date is usually invoice date
        try:
            from dateutil import parser as date_parser
            result['invoice_date'] = date_parser.parse(dates_found[0], dayfirst=True).date()
            if len(dates_found) > 1:
                result['due_date'] = date_parser.parse(dates_found[1], dayfirst=True).date()
        except (ValueError, TypeError, OverflowError):
            pass

    # Extract monetary amounts
    money_pattern = r'[\$\£\€]?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'

    # Look for total
    total_patterns = [
        r'total\s*:?\s*[\$\£\€]?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        r'amount\s+due\s*:?\s*[\$\£\€]?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        r'balance\s+due\s*:?\s*[\$\£\€]?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        r'grand\s+total\s*:?\s*[\$\£\€]?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
    ]
    for pattern in total_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result['total'] = float(match.group(1).replace(',', ''))
            break

    # Look for subtotal
    subtotal_patterns = [
        r'subtotal\s*:?\s*[\$\£\€]?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        r'sub\s*-?\s*total\s*:?\s*[\$\£\€]?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
    ]
    for pattern in subtotal_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result['subtotal'] = float(match.group(1).replace(',', ''))
            break

    # Look for tax
    tax_patterns = [
        r'(?:tax|vat|gst)\s*:?\s*[\$\£\€]?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        r'(?:tax|vat|gst)\s*\(\d+%?\)\s*:?\s*[\$\£\€]?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
    ]
    for pattern in tax_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result['tax'] = float(match.group(1).replace(',', ''))
            break

    # Extract line items (simplified - looks for lines with quantity and price)
    line_item_pattern = r'^(.+?)\s+(\d+(?:\.\d+)?)\s*(?:x|@)?\s*[\$\£\€]?\s*(\d+(?:\.\d+)?)\s*[\$\£\€]?\s*(\d+(?:\.\d+)?)?$'

    for line in lines:
        line = line.strip()
        if len(line) > 10:  # Skip very short lines
            match = re.match(line_item_pattern, line, re.IGNORECASE)
            if match:
                item = {
                    'description': match.group(1).strip(),
                    'quantity': float(match.group(2)),
                    'unit_price': float(match.group(3)),
                    'total': float(match.group(4)) if match.group(4) else float(match.group(2)) * float(match.group(3))
                }
                result['line_items'].append(item)

    # Try to extract supplier name (usually at the top of invoice)
    # Take first non-empty line that looks like a company name
    for line in lines[:10]:  # Check first 10 lines
        line = line.strip()
        if len(line) > 3 and not any(keyword in line.lower() for keyword in ['invoice', 'bill', 'date', 'number', '#', 'to:', 'from:']):
            # Check if line looks like a company name (contains letters, maybe some punctuation)
            if re.match(r'^[A-Za-z][A-Za-z0-9\s&.,\'-]+$', line):
                result['supplier_name'] = line
                break

    return result


def _match_invoice_item_to_stock(
    db: Session,
    venue_id: int,
    item: dict,
    supplier_id: Optional[int]
) -> dict:
    """Match an invoice line item to a stock item using matching rules"""
    description = item.get('description', '')

    # First, try matching rules
    rules_query = db.query(InvoiceMatchingRule).filter(
        InvoiceMatchingRule.venue_id == venue_id,
        InvoiceMatchingRule.is_active == True
    ).order_by(InvoiceMatchingRule.priority.desc())

    if supplier_id:
        # Try supplier-specific rules first
        supplier_rules = rules_query.filter(
            InvoiceMatchingRule.supplier_id == supplier_id
        ).all()

        for rule in supplier_rules:
            if rule.invoice_description_pattern.lower() in description.lower():
                item['matched_stock_item_id'] = rule.stock_item_id
                item['conversion_factor'] = rule.conversion_factor
                return item

    # Try general rules
    general_rules = rules_query.filter(
        InvoiceMatchingRule.supplier_id.is_(None)
    ).all()

    for rule in general_rules:
        if rule.invoice_description_pattern.lower() in description.lower():
            item['matched_stock_item_id'] = rule.stock_item_id
            item['conversion_factor'] = rule.conversion_factor
            return item

    # Fallback: try to find stock item by name similarity
    stock_item = db.query(StockItem).filter(
        StockItem.venue_id == venue_id,
        StockItem.name.ilike(f"%{description[:50]}%")
    ).first()

    if stock_item:
        item['matched_stock_item_id'] = stock_item.id
        item['match_confidence'] = 'low'

    return item


@router.post("/invoices/{invoice_id}/process", response_model=InvoiceResponse)
@limiter.limit("30/minute")
async def process_invoice(
    request: Request,
    invoice_id: int,
    body: InvoiceProcessRequest = InvoiceProcessRequest(),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Manually trigger OCR processing for an invoice"""
    invoice = db.query(ScannedInvoice).filter(
        ScannedInvoice.id == invoice_id,
        ScannedInvoice.venue_id == current_user.venue_id
    ).first()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Check if already processed
    if invoice.ocr_status == 'completed' and not body.force_reprocess:
        raise HTTPException(
            status_code=400,
            detail="Invoice already processed. Set force_reprocess=true to reprocess."
        )

    # Reconstruct file path from URL
    upload_base_dir = os.environ.get('UPLOAD_DIR', '/tmp/uploads')
    # file_url format: /uploads/invoices/{venue_id}/{filename}
    relative_path = invoice.file_url.lstrip('/')
    file_path = os.path.join(upload_base_dir, relative_path.replace('uploads/', '', 1))

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail="Invoice file not found on disk. Please re-upload the invoice."
        )

    # Process the invoice
    invoice = _process_invoice_ocr(db, invoice, current_user.venue_id, file_path)

    return invoice


@router.post("/invoices/{invoice_id}/verify", response_model=InvoiceResponse)
@limiter.limit("30/minute")
async def verify_invoice(
    request: Request,
    invoice_id: int,
    body: InvoiceVerifyRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Verify and correct OCR-extracted invoice data"""
    invoice = db.query(ScannedInvoice).filter(
        ScannedInvoice.id == invoice_id,
        ScannedInvoice.venue_id == current_user.venue_id
    ).first()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Update with verified data
    if body.supplier_id is not None:
        invoice.supplier_id = body.supplier_id
    if body.invoice_number is not None:
        invoice.invoice_number_extracted = body.invoice_number
    if body.invoice_date is not None:
        invoice.invoice_date_extracted = body.invoice_date
    if body.subtotal is not None:
        invoice.subtotal_extracted = body.subtotal
    if body.tax is not None:
        invoice.tax_extracted = body.tax
    if body.total is not None:
        invoice.total_extracted = body.total
    if body.line_items is not None:
        invoice.line_items_extracted = body.line_items
    if body.notes is not None:
        invoice.notes = body.notes

    invoice.verification_status = 'verified'
    invoice.verified_by = current_user.id
    invoice.verified_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(invoice)

    return invoice


@router.post("/invoices/{invoice_id}/match-po")
@limiter.limit("30/minute")
async def match_invoice_to_po(
    request: Request,
    invoice_id: int,
    body: InvoiceMatchRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Match a scanned invoice to a purchase order"""
    invoice = db.query(ScannedInvoice).filter(
        ScannedInvoice.id == invoice_id,
        ScannedInvoice.venue_id == current_user.venue_id
    ).first()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    po = db.query(PurchaseOrder).filter(
        PurchaseOrder.id == body.purchase_order_id,
        PurchaseOrder.location_id == current_user.venue_id
    ).first()

    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    # Compare invoice to PO
    po_items = db.query(PurchaseOrderItem).filter(
        PurchaseOrderItem.purchase_order_id == po.id
    ).all()

    discrepancies = []
    invoice_items = invoice.line_items_extracted or []

    # Track matched invoice items
    matched_invoice_item_indices = set()

    # Check for quantity/price discrepancies
    for po_item in po_items:
        matching_invoice_item = None
        matching_index = None
        for idx, inv_item in enumerate(invoice_items):
            if inv_item.get('matched_stock_item_id') == po_item.stock_item_id:
                matching_invoice_item = inv_item
                matching_index = idx
                break

        if matching_invoice_item:
            matched_invoice_item_indices.add(matching_index)
            inv_qty = matching_invoice_item.get('quantity', 0)
            inv_price = matching_invoice_item.get('unit_price', 0)

            if inv_qty != po_item.quantity_ordered:
                discrepancies.append({
                    'type': 'quantity',
                    'stock_item_id': po_item.stock_item_id,
                    'item_name': po_item.item_name,
                    'po_quantity': po_item.quantity_ordered,
                    'invoice_quantity': inv_qty
                })

            if inv_price and abs(inv_price - float(po_item.unit_price)) > 0.01:
                discrepancies.append({
                    'type': 'price',
                    'stock_item_id': po_item.stock_item_id,
                    'item_name': po_item.item_name,
                    'po_price': float(po_item.unit_price),
                    'invoice_price': inv_price
                })
        else:
            discrepancies.append({
                'type': 'missing_on_invoice',
                'stock_item_id': po_item.stock_item_id,
                'item_name': po_item.item_name
            })

    # Check for extra items on invoice that are not on PO
    for idx, inv_item in enumerate(invoice_items):
        if idx not in matched_invoice_item_indices:
            discrepancies.append({
                'type': 'extra_on_invoice',
                'description': inv_item.get('description', 'Unknown item'),
                'stock_item_id': inv_item.get('matched_stock_item_id'),
                'quantity': inv_item.get('quantity'),
                'unit_price': inv_item.get('unit_price')
            })

    # Update invoice with match
    invoice.matched_po_id = po.id

    if discrepancies:
        invoice.verification_status = 'discrepancy'
    else:
        invoice.verification_status = 'verified'

    db.commit()

    return {
        "invoice_id": invoice.id,
        "purchase_order_id": po.id,
        "match_status": "discrepancy" if discrepancies else "matched",
        "discrepancies": discrepancies
    }


@router.post("/invoices/{invoice_id}/create-matching-rule")
@limiter.limit("30/minute")
async def create_matching_rule_from_invoice(
    request: Request,
    invoice_id: int,
    line_item_index: int,
    stock_item_id: int,
    conversion_factor: float = 1.0,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Create a matching rule from an invoice line item for future auto-matching"""
    invoice = db.query(ScannedInvoice).filter(
        ScannedInvoice.id == invoice_id,
        ScannedInvoice.venue_id == current_user.venue_id
    ).first()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if not invoice.line_items_extracted:
        raise HTTPException(status_code=400, detail="Invoice has no extracted line items")

    if line_item_index >= len(invoice.line_items_extracted):
        raise HTTPException(status_code=400, detail="Invalid line item index")

    line_item = invoice.line_items_extracted[line_item_index]
    description = line_item.get('description', '')

    if not description:
        raise HTTPException(status_code=400, detail="Line item has no description")

    # Create matching rule
    rule = InvoiceMatchingRule(
        venue_id=current_user.venue_id,
        supplier_id=invoice.supplier_id,
        invoice_description_pattern=description,
        stock_item_id=stock_item_id,
        invoice_unit=line_item.get('unit'),
        conversion_factor=conversion_factor,
        priority=10  # Default priority
    )

    db.add(rule)
    db.commit()
    db.refresh(rule)

    # Update the line item with the match - need to create a new list to flag as modified
    updated_items = list(invoice.line_items_extracted)
    updated_items[line_item_index]['matched_stock_item_id'] = stock_item_id
    updated_items[line_item_index]['conversion_factor'] = conversion_factor
    invoice.line_items_extracted = updated_items
    db.commit()

    return {
        "rule_id": rule.id,
        "pattern": description,
        "stock_item_id": stock_item_id,
        "message": "Matching rule created successfully"
    }


@router.get("/invoices")
@limiter.limit("60/minute")
async def list_invoices(
    request: Request,
    status_filter: Optional[str] = None,
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List scanned invoices"""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    query = db.query(ScannedInvoice).filter(
        ScannedInvoice.venue_id == current_user.venue_id,
        ScannedInvoice.uploaded_at >= start_date
    )

    if status_filter:
        query = query.filter(ScannedInvoice.ocr_status == status_filter)

    return query.order_by(ScannedInvoice.uploaded_at.desc()).all()


@router.get("/invoices/{invoice_id}")
@limiter.limit("60/minute")
async def get_invoice(
    request: Request,
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get invoice details with extracted data"""
    invoice = db.query(ScannedInvoice).filter(
        ScannedInvoice.id == invoice_id,
        ScannedInvoice.venue_id == current_user.venue_id
    ).first()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return invoice

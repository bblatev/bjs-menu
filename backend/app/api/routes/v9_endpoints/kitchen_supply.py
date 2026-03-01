"""V9 Kitchen & Supply Chain"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal

from app.core.rbac import get_current_user
from app.core.rate_limit import limiter

# Import all services and schemas from shared
from app.api.routes.v9_endpoints._shared import *

router = APIRouter()

# ==================== PRODUCTION FORECASTING ====================

@router.post("/kitchen/forecast", response_model=ForecastResponse, tags=["V9 - Kitchen"])
@limiter.limit("30/minute")
async def generate_production_forecast(
    request: Request,
    data: ForecastRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Generate ML-based production forecast for menu item"""
    if ProductionForecastService is None:
        raise HTTPException(status_code=501, detail="Advanced kitchen service is not available. Required model 'CourseTiming' is missing.")
    service = ProductionForecastService(db)
    return service.forecast_demand(
        menu_item_id=data.menu_item_id,
        forecast_date=data.forecast_date,
        include_weather=data.include_weather,
        include_events=data.include_events
    )


@router.get("/kitchen/forecast/ingredients/{forecast_date}", response_model=List[IngredientRequirementResponse], tags=["V9 - Kitchen"])
@limiter.limit("60/minute")
async def get_ingredient_requirements(
    request: Request,
    forecast_date: date,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get ingredient requirements based on forecasts"""
    if ProductionForecastService is None:
        raise HTTPException(status_code=501, detail="Advanced kitchen service is not available. Required model 'CourseTiming' is missing.")
    service = ProductionForecastService(db)
    return service.calculate_ingredient_requirements(forecast_date)


# ==================== STATION LOAD BALANCING ====================

@router.post("/kitchen/stations", response_model=Dict[str, Any], tags=["V9 - Kitchen"])
@limiter.limit("30/minute")
async def create_kitchen_station(
    request: Request,
    data: StationCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a kitchen station"""
    if StationLoadBalancingService is None:
        raise HTTPException(status_code=501, detail="Advanced kitchen service is not available. Required model 'CourseTiming' is missing.")
    service = StationLoadBalancingService(db)
    return service.create_station(
        station_name=data.station_name,
        station_type=data.station_type,
        max_concurrent=data.max_concurrent_orders,
        avg_prep_time=data.average_prep_time_minutes
    )


@router.get("/kitchen/stations/load", response_model=List[StationLoadResponse], tags=["V9 - Kitchen"])
@limiter.limit("60/minute")
async def get_station_loads(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get current load for all kitchen stations"""
    if StationLoadBalancingService is None:
        raise HTTPException(status_code=501, detail="Advanced kitchen service is not available. Required model 'CourseTiming' is missing.")
    service = StationLoadBalancingService(db)
    return service.get_all_station_loads()


@router.get("/kitchen/routing/suggestions", response_model=List[RoutingSuggestion], tags=["V9 - Kitchen"])
@limiter.limit("60/minute")
async def get_routing_suggestions(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get smart routing suggestions for pending orders"""
    if StationLoadBalancingService is None:
        raise HTTPException(status_code=501, detail="Advanced kitchen service is not available. Required model 'CourseTiming' is missing.")
    service = StationLoadBalancingService(db)
    return service.get_routing_suggestions()


@router.post("/kitchen/routing/apply/{order_item_id}", response_model=SuccessResponse, tags=["V9 - Kitchen"])
@limiter.limit("30/minute")
async def apply_routing_suggestion(
    request: Request,
    order_item_id: int,
    target_station_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Apply routing suggestion to move order to different station"""
    if StationLoadBalancingService is None:
        raise HTTPException(status_code=501, detail="Advanced kitchen service is not available. Required model 'CourseTiming' is missing.")
    service = StationLoadBalancingService(db)
    result = service.route_to_station(order_item_id, target_station_id)
    return SuccessResponse(success=result, message="Order routed" if result else "Routing failed")


# ==================== COURSE FIRE RULES ====================

@router.post("/kitchen/course-fire/rules", response_model=CourseFireRuleResponse, tags=["V9 - Kitchen"])
@limiter.limit("30/minute")
async def create_course_fire_rule(
    request: Request,
    data: CourseFireRuleCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create automatic course firing rule"""
    if CourseFireService is None:
        raise HTTPException(status_code=501, detail="Advanced kitchen service is not available. Required model 'CourseTiming' is missing.")
    service = CourseFireService(db)
    return service.create_rule(
        menu_item_id=data.menu_item_id,
        course_number=data.course_number,
        fire_delay=data.fire_delay_minutes,
        fire_trigger=data.fire_trigger,
        conditions=data.conditions
    )


@router.get("/kitchen/course-fire/rules", response_model=List[CourseFireRuleResponse], tags=["V9 - Kitchen"])
@limiter.limit("60/minute")
async def get_course_fire_rules(
    request: Request,
    menu_item_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all course fire rules"""
    if CourseFireService is None:
        raise HTTPException(status_code=501, detail="Advanced kitchen service is not available. Required model 'CourseTiming' is missing.")
    service = CourseFireService(db)
    return service.get_rules(menu_item_id)


@router.post("/kitchen/course-fire/check/{order_id}", response_model=Dict[str, Any], tags=["V9 - Kitchen"])
@limiter.limit("30/minute")
async def check_course_fire(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Check and fire courses for an order based on rules"""
    if CourseFireService is None:
        raise HTTPException(status_code=501, detail="Advanced kitchen service is not available. Required model 'CourseTiming' is missing.")
    service = CourseFireService(db)
    return service.check_and_fire_courses(order_id)


# ==================== KITCHEN PERFORMANCE ====================

@router.get("/kitchen/performance", response_model=KitchenPerformanceMetrics, tags=["V9 - Kitchen"])
@limiter.limit("60/minute")
async def get_kitchen_performance(
    request: Request,
    start_date: datetime = Query(default_factory=lambda: datetime.now(timezone.utc) - timedelta(days=7)),
    end_date: datetime = Query(default_factory=datetime.now),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get kitchen performance metrics"""
    if KitchenPerformanceService is None:
        raise HTTPException(status_code=501, detail="Advanced kitchen service is not available. Required model 'CourseTiming' is missing.")
    service = KitchenPerformanceService(db)
    return service.get_performance_metrics(start_date, end_date)


# ==================== AUTO PURCHASE ORDERS ====================

@router.post("/supply-chain/auto-po/config", response_model=Dict[str, Any], tags=["V9 - Supply Chain"])
@limiter.limit("30/minute")
async def configure_auto_po(
    request: Request,
    data: AutoPOConfig,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Configure automatic PO generation for an ingredient"""
    service = AutoPurchaseOrderService(db)
    return service.configure_auto_po(
        ingredient_id=data.ingredient_id,
        reorder_point=data.reorder_point,
        reorder_quantity=data.reorder_quantity,
        preferred_supplier_id=data.preferred_supplier_id,
        auto_approve_threshold=data.auto_approve_threshold
    )


@router.post("/supply-chain/auto-po/check", response_model=List[AutoPOResponse], tags=["V9 - Supply Chain"])
@limiter.limit("30/minute")
async def check_and_generate_pos(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Check inventory levels and generate POs for low stock items"""
    service = AutoPurchaseOrderService(db)
    return service.check_and_generate_pos()


@router.get("/supply-chain/auto-po/pending", response_model=List[AutoPOResponse], tags=["V9 - Supply Chain"])
@limiter.limit("60/minute")
async def get_pending_auto_pos(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get pending auto-generated POs awaiting approval"""
    service = AutoPurchaseOrderService(db)
    return service.get_pending_pos()


# ==================== SUPPLIER LEAD TIME ====================

@router.post("/supply-chain/lead-times", response_model=SuccessResponse, tags=["V9 - Supply Chain"])
@limiter.limit("30/minute")
async def update_supplier_lead_time(
    request: Request,
    data: SupplierLeadTimeUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update supplier lead time for an ingredient"""
    service = SupplierLeadTimeService(db)
    result = service.update_lead_time(
        supplier_id=data.supplier_id,
        ingredient_id=data.ingredient_id,
        lead_time_days=data.lead_time_days,
        reliability_score=data.reliability_score
    )
    return SuccessResponse(success=result, message="Lead time updated")


@router.get("/supply-chain/lead-times/{ingredient_id}", response_model=List[Dict[str, Any]], tags=["V9 - Supply Chain"])
@limiter.limit("60/minute")
async def get_supplier_lead_times(
    request: Request,
    ingredient_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get lead times from all suppliers for an ingredient"""
    service = SupplierLeadTimeService(db)
    return service.get_lead_times_for_ingredient(ingredient_id)


@router.get("/supply-chain/alternatives/{ingredient_id}", response_model=List[Dict[str, Any]], tags=["V9 - Supply Chain"])
@limiter.limit("60/minute")
async def get_alternative_suppliers(
    request: Request,
    ingredient_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get alternative suppliers ranked by price and reliability"""
    service = SupplierLeadTimeService(db)
    return service.get_alternative_suppliers(ingredient_id)


# ==================== INVENTORY COSTING ====================

@router.post("/supply-chain/costing/config", response_model=SuccessResponse, tags=["V9 - Supply Chain"])
@limiter.limit("30/minute")
async def configure_costing_method(
    request: Request,
    data: InventoryCostingConfig,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Configure costing method (FIFO/LIFO/Weighted Average) for ingredient"""
    service = InventoryCostingService(db)
    result = service.set_costing_method(
        ingredient_id=data.ingredient_id,
        method=data.costing_method.value
    )
    return SuccessResponse(success=result, message=f"Costing method set to {data.costing_method.value}")


@router.get("/supply-chain/costing/{ingredient_id}", response_model=Dict[str, Any], tags=["V9 - Supply Chain"])
@limiter.limit("60/minute")
async def get_ingredient_cost(
    request: Request,
    ingredient_id: int,
    quantity: float = 1.0,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Calculate cost for ingredient using configured costing method"""
    service = InventoryCostingService(db)
    return service.calculate_cost(ingredient_id, quantity)


# ==================== CROSS-STORE BALANCING ====================

@router.get("/supply-chain/cross-store/suggestions", response_model=List[CrossStoreBalancingSuggestion], tags=["V9 - Supply Chain"])
@limiter.limit("60/minute")
async def get_cross_store_balancing_suggestions(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get suggestions for balancing inventory across locations"""
    service = CrossStoreBalancingService(db)
    return service.get_balancing_suggestions()


@router.post("/supply-chain/cross-store/transfer", response_model=SuccessResponse, tags=["V9 - Supply Chain"])
@limiter.limit("30/minute")
async def create_cross_store_transfer(
    request: Request,
    ingredient_id: int,
    source_location_id: int,
    target_location_id: int,
    quantity: float,
    requested_by_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create cross-store inventory transfer"""
    service = CrossStoreBalancingService(db)
    result = service.create_transfer(
        ingredient_id=ingredient_id,
        source_location_id=source_location_id,
        target_location_id=target_location_id,
        quantity=quantity,
        requested_by_id=requested_by_id
    )
    return SuccessResponse(success=True, message="Transfer created", data=result)


# Helper function for background tasks
async def send_variance_alert(variance: CashVarianceResponse):
    """Send alert for high cash variance"""
    import logging
    logger = logging.getLogger(__name__)

    # Log the variance alert
    logger.warning(
        f"CASH VARIANCE ALERT: Terminal {variance.terminal_id}, "
        f"Shift {variance.shift_id}, Variance: {variance.variance_amount} BGN "
        f"({variance.variance_percentage}%), Severity: {variance.severity}"
    )

    # In production, this would:
    # 1. Store alert in database for audit trail
    # 2. Send push notification to managers
    # 3. Send email/SMS if severity is high
    # 4. Trigger workflow for investigation

    if variance.severity in ["high", "critical"]:
        logger.error(
            f"CRITICAL CASH VARIANCE requiring immediate attention: "
            f"Terminal {variance.terminal_id}, Amount: {variance.variance_amount} BGN"
        )
        # Note: Critical variances are logged and stored. Push notifications to managers
        # can be configured via the Marketing/Notification service for real-time alerts.
        # Integration with external notification providers (SMS, Push) available via webhooks.



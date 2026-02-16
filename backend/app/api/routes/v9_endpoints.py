"""
V9 Advanced Features API Endpoints
BJ's Bar V9 - Enterprise POS System
100+ Advanced Features with Full API Coverage
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal


from app.core.rbac import get_current_user

# Import V9 Services
from app.services.v9_features.advanced_operations_service import (
    PermissionOverrideService,
    TerminalHealthService,
    SafeModeService,
    CashVarianceService,
    SessionTimeoutService
)
from app.services.v9_features.advanced_kitchen_service import (
    ProductionForecastService,
    StationLoadBalancingService,
    CourseFireService,
    KitchenPerformanceService
)
from app.services.v9_features.advanced_supply_chain_service import (
    AutoPurchaseOrderService,
    SupplierLeadTimeService,
    InventoryCostingService,
    CrossStoreBalancingService
)
from app.services.v9_features.financial_controls_service import (
    PrimeCostService,
    AbuseDetectionService
)
from app.services.v9_features.advanced_crm_service import (
    GuestPreferencesService,
    CustomerLifetimeValueService,
    CustomerSegmentationService,
    VIPManagementService,
    PersonalizationService
)
from app.services.v9_features.iot_service import (
    IoTDeviceService,
    TemperatureMonitoringService,
    PourMeterService,
    ScaleService
)
from app.services.v9_features.compliance_service import (
    ImmutableAuditService,
    FiscalArchiveService,
    NRAExportService,
    AgeVerificationService
)
from app.services.v9_features.ai_automation_service import (
    AIModelService,
    PredictionService,
    AutomationRuleService,
    MenuOptimizationService,
    StaffingRecommendationService
)
from app.services.v9_features.legal_training_crisis_service import (
    LegalRiskService,
    TrainingService,
    CrisisManagementService
)
from app.services.v9_features.platform_qr_service import (
    PlatformService,
    QRSelfServiceService
)

# Import V9 Schemas
from app.schemas.v9_schemas import *
from app.core.rate_limit import limiter

# Create main V9 router
router = APIRouter()


# ==================== PERMISSION OVERRIDES ====================

@router.get("/")
@limiter.limit("60/minute")
async def get_v9_root(request: Request, db: Session = Depends(get_db)):
    """V9 API features status."""
    return {"module": "v9", "version": "9.0", "status": "active", "features": ["permissions", "terminal-health", "safe-mode", "cash-variance"]}


@router.post("/permissions/overrides", response_model=PermissionOverrideResponse, tags=["V9 - Operations"])
@limiter.limit("30/minute")
async def create_permission_override(
    request: Request,
    data: PermissionOverrideCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Grant temporary permission override to staff member"""
    service = PermissionOverrideService(db)
    return service.create_override(
        staff_id=data.staff_id,
        override_type=data.override_type.value,
        max_value=data.max_value,
        max_percentage=data.max_percentage,
        valid_from=data.valid_from,
        valid_until=data.valid_until,
        reason=data.reason,
        granted_by_id=data.granted_by_id
    )


@router.get("/permissions/overrides/{staff_id}", response_model=List[PermissionOverrideResponse], tags=["V9 - Operations"])
@limiter.limit("60/minute")
async def get_staff_overrides(
    request: Request,
    staff_id: int,
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all permission overrides for a staff member"""
    service = PermissionOverrideService(db)
    return service.get_active_overrides(staff_id, active_only)


@router.post("/permissions/overrides/use", response_model=SuccessResponse, tags=["V9 - Operations"])
@limiter.limit("30/minute")
async def use_permission_override(
    request: Request,
    data: UseOverrideRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Use a permission override for a transaction"""
    service = PermissionOverrideService(db)
    result = service.use_override(
        override_id=data.override_id,
        amount=data.amount,
        transaction_id=data.transaction_id,
        notes=data.notes
    )
    return SuccessResponse(success=result["success"], message=result.get("message", "Override applied"))


@router.delete("/permissions/overrides/{override_id}", response_model=SuccessResponse, tags=["V9 - Operations"])
@limiter.limit("30/minute")
async def revoke_permission_override(
    request: Request,
    override_id: int,
    revoked_by_id: int,
    reason: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Revoke a permission override"""
    service = PermissionOverrideService(db)
    result = service.revoke_override(override_id, revoked_by_id, reason)
    return SuccessResponse(success=result, message="Override revoked" if result else "Failed to revoke")


# ==================== TERMINAL HEALTH ====================

@router.post("/terminals", response_model=TerminalHealthResponse, tags=["V9 - Operations"])
@limiter.limit("30/minute")
async def register_terminal(
    request: Request,
    data: TerminalHealthCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Register a new POS terminal"""
    service = TerminalHealthService(db)
    return service.register_terminal(
        terminal_id=data.terminal_id,
        terminal_name=data.terminal_name,
        ip_address=data.ip_address,
        latitude=data.latitude,
        longitude=data.longitude
    )


@router.post("/terminals/{terminal_id}/heartbeat", response_model=SuccessResponse, tags=["V9 - Operations"])
@limiter.limit("30/minute")
async def terminal_heartbeat(
    request: Request,
    terminal_id: str,
    data: TerminalHealthUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Send terminal heartbeat with health data"""
    service = TerminalHealthService(db)
    result = service.record_heartbeat(
        terminal_id=terminal_id,
        battery_level=data.battery_level,
        network_strength=data.network_strength,
        printer_status=data.printer_status,
        cash_drawer_status=data.cash_drawer_status,
        latitude=data.latitude,
        longitude=data.longitude
    )
    return SuccessResponse(success=True, message="Heartbeat recorded", data=result)


@router.get("/terminals/offline", response_model=List[TerminalHealthResponse], tags=["V9 - Operations"])
@limiter.limit("60/minute")
async def get_offline_terminals(
    request: Request,
    threshold_minutes: int = 5,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get terminals that haven't sent heartbeat recently"""
    service = TerminalHealthService(db)
    return service.get_offline_terminals(threshold_minutes)


@router.post("/terminals/{terminal_id}/lock", response_model=SuccessResponse, tags=["V9 - Operations"])
@limiter.limit("30/minute")
async def lock_terminal(
    request: Request,
    terminal_id: str,
    locked_by_id: int,
    reason: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Remotely lock a terminal"""
    service = TerminalHealthService(db)
    result = service.lock_terminal(terminal_id, locked_by_id, reason)
    return SuccessResponse(success=result, message="Terminal locked" if result else "Failed to lock")


@router.post("/terminals/{terminal_id}/unlock", response_model=SuccessResponse, tags=["V9 - Operations"])
@limiter.limit("30/minute")
async def unlock_terminal(
    request: Request,
    terminal_id: str,
    unlocked_by_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Remotely unlock a terminal"""
    service = TerminalHealthService(db)
    result = service.unlock_terminal(terminal_id, unlocked_by_id)
    return SuccessResponse(success=result, message="Terminal unlocked" if result else "Failed to unlock")


@router.post("/terminals/geo-fence", response_model=SuccessResponse, tags=["V9 - Operations"])
@limiter.limit("30/minute")
async def configure_geo_fence(
    request: Request,
    data: GeoFenceConfig,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Configure geo-fencing for a terminal"""
    service = TerminalHealthService(db)
    result = service.set_geo_fence(
        terminal_id=data.terminal_id,
        center_lat=data.center_latitude,
        center_lon=data.center_longitude,
        radius_meters=data.radius_meters
    )
    return SuccessResponse(success=result, message="Geo-fence configured")


# ==================== SAFE/EMERGENCY MODE ====================

@router.post("/safe-mode/activate", response_model=SafeModeResponse, tags=["V9 - Operations"])
@limiter.limit("30/minute")
async def activate_safe_mode(
    request: Request,
    data: SafeModeActivate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Activate emergency/safe mode"""
    service = SafeModeService(db)
    return service.activate_safe_mode(
        level=data.level.value,
        reason=data.reason,
        activated_by_id=data.activated_by_id,
        auto_deactivate_hours=data.auto_deactivate_after_hours,
        allowed_operations=data.allowed_operations
    )


@router.post("/safe-mode/deactivate/{mode_id}", response_model=SuccessResponse, tags=["V9 - Operations"])
@limiter.limit("30/minute")
async def deactivate_safe_mode(
    request: Request,
    mode_id: int,
    deactivated_by_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Deactivate safe mode"""
    service = SafeModeService(db)
    result = service.deactivate_safe_mode(mode_id, deactivated_by_id)
    return SuccessResponse(success=result, message="Safe mode deactivated" if result else "Failed")


@router.get("/safe-mode/current", response_model=Optional[SafeModeResponse], tags=["V9 - Operations"])
@limiter.limit("60/minute")
async def get_current_safe_mode(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get current active safe mode if any"""
    service = SafeModeService(db)
    return service.get_active_safe_mode()


@router.get("/safe-mode/check-operation/{operation}", response_model=SuccessResponse, tags=["V9 - Operations"])
@limiter.limit("60/minute")
async def check_operation_allowed(
    request: Request,
    operation: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Check if an operation is allowed in current safe mode"""
    service = SafeModeService(db)
    allowed = service.is_operation_allowed(operation)
    return SuccessResponse(success=allowed, message="Operation allowed" if allowed else "Operation restricted")


# ==================== CASH VARIANCE ====================

@router.post("/cash-variance", response_model=CashVarianceResponse, tags=["V9 - Operations"])
@limiter.limit("30/minute")
async def submit_cash_count(
    request: Request,
    data: CashCountSubmit,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Submit cash count and detect variance"""
    service = CashVarianceService(db)
    result = service.record_count(
        shift_id=data.shift_id,
        terminal_id=data.terminal_id,
        expected_amount=data.expected_amount,
        actual_amount=data.actual_amount,
        counted_by_id=data.counted_by_id,
        notes=data.notes
    )
    # Background task for alerts on high variance
    if result.severity in ['high', 'critical']:
        background_tasks.add_task(send_variance_alert, result)
    return result


@router.get("/cash-variance/unresolved", response_model=List[CashVarianceResponse], tags=["V9 - Operations"])
@limiter.limit("60/minute")
async def get_unresolved_variances(
    request: Request,
    min_severity: str = "low",
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all unresolved cash variances"""
    service = CashVarianceService(db)
    return service.get_unresolved_variances(min_severity)


@router.post("/cash-variance/{variance_id}/resolve", response_model=SuccessResponse, tags=["V9 - Operations"])
@limiter.limit("30/minute")
async def resolve_cash_variance(
    request: Request,
    variance_id: int,
    reviewed_by_id: int,
    notes: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Resolve/investigate a cash variance"""
    service = CashVarianceService(db)
    result = service.resolve_variance(variance_id, reviewed_by_id, notes)
    return SuccessResponse(success=result, message="Variance resolved" if result else "Failed")


# ==================== SESSION TIMEOUT ====================

@router.post("/session-timeout/config", response_model=SessionTimeoutResponse, tags=["V9 - Operations"])
@limiter.limit("30/minute")
async def configure_session_timeout(
    request: Request,
    data: SessionTimeoutConfig,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Configure session timeout for a role"""
    service = SessionTimeoutService(db)
    return service.set_timeout_config(
        role=data.role,
        timeout_minutes=data.timeout_minutes,
        warning_minutes=data.warning_minutes,
        extend_allowed=data.extend_allowed,
        max_extensions=data.max_extensions
    )


@router.get("/session-timeout/config/{role}", response_model=SessionTimeoutResponse, tags=["V9 - Operations"])
@limiter.limit("60/minute")
async def get_session_timeout_config(
    request: Request,
    role: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get session timeout configuration for a role"""
    service = SessionTimeoutService(db)
    return service.get_timeout_config(role)


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
    service = CourseFireService(db)
    return service.check_and_fire_courses(order_id)


# ==================== KITCHEN PERFORMANCE ====================

@router.get("/kitchen/performance", response_model=KitchenPerformanceMetrics, tags=["V9 - Kitchen"])
@limiter.limit("60/minute")
async def get_kitchen_performance(
    request: Request,
    start_date: datetime = Query(default_factory=lambda: datetime.now() - timedelta(days=7)),
    end_date: datetime = Query(default_factory=datetime.now),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get kitchen performance metrics"""
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


# ==================== FINANCIAL CONTROLS - PRIME COST ====================

@router.post("/financial/prime-cost", response_model=Dict[str, Any], tags=["V9 - Financial Controls"])
@limiter.limit("30/minute")
async def record_prime_cost(
    request: Request,
    period_date: date,
    food_cost: Decimal,
    beverage_cost: Decimal,
    labor_cost: Decimal,
    revenue: Decimal,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Record prime cost data for a period"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return PrimeCostService.record_prime_cost(
        db=db,
        venue_id=venue_id,
        period_date=period_date,
        food_cost=food_cost,
        beverage_cost=beverage_cost,
        labor_cost=labor_cost,
        revenue=revenue,
        notes=notes
    )


@router.get("/financial/prime-cost/dashboard", response_model=Dict[str, Any], tags=["V9 - Financial Controls"])
@limiter.limit("60/minute")
async def get_prime_cost_dashboard(
    request: Request,
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get prime cost dashboard with trends and analysis"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return PrimeCostService.get_prime_cost_dashboard(db, venue_id, start_date, end_date)


@router.get("/financial/profitability/{menu_item_id}", response_model=Dict[str, Any], tags=["V9 - Financial Controls"])
@limiter.limit("60/minute")
async def get_item_profitability(
    request: Request,
    menu_item_id: int,
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Calculate profitability metrics for a menu item"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return PrimeCostService.calculate_item_profitability(db, venue_id, menu_item_id, start_date, end_date)


@router.get("/financial/profit-leaderboard", response_model=Dict[str, Any], tags=["V9 - Financial Controls"])
@limiter.limit("60/minute")
async def get_profit_leaderboard(
    request: Request,
    start_date: date,
    end_date: date,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get top and bottom performing items by profitability"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return PrimeCostService.get_profit_leaderboard(db, venue_id, start_date, end_date, limit)


# ==================== FINANCIAL CONTROLS - ABUSE DETECTION ====================

@router.get("/financial/abuse/config", response_model=Dict[str, Any], tags=["V9 - Financial Controls"])
@limiter.limit("60/minute")
async def get_abuse_config(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get abuse detection configuration"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return AbuseDetectionService.get_or_create_abuse_config(db, venue_id)


@router.put("/financial/abuse/config", response_model=Dict[str, Any], tags=["V9 - Financial Controls"])
@limiter.limit("30/minute")
async def update_abuse_config(
    request: Request,
    updates: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update abuse detection configuration"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return AbuseDetectionService.update_abuse_config(db, venue_id, updates)


@router.post("/financial/abuse/check", response_model=Dict[str, Any], tags=["V9 - Financial Controls"])
@limiter.limit("30/minute")
async def check_for_abuse(
    request: Request,
    staff_id: int,
    action_type: str,
    amount: Decimal,
    order_id: Optional[int] = None,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Check if an action triggers abuse detection"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return AbuseDetectionService.check_for_abuse(db, venue_id, staff_id, action_type, amount, order_id, reason)


@router.get("/financial/abuse/alerts", response_model=List[Dict[str, Any]], tags=["V9 - Financial Controls"])
@limiter.limit("60/minute")
async def get_pending_abuse_alerts(
    request: Request,
    severity: Optional[str] = None,
    staff_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get pending abuse alerts for investigation"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return AbuseDetectionService.get_pending_alerts(db, venue_id, severity, staff_id)


@router.post("/financial/abuse/investigate/{alert_id}", response_model=Dict[str, Any], tags=["V9 - Financial Controls"])
@limiter.limit("30/minute")
async def investigate_abuse_alert(
    request: Request,
    alert_id: int,
    status: str,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update alert investigation status"""
    investigator_id = current_user.id
    return AbuseDetectionService.investigate_alert(db, alert_id, investigator_id, status, notes)


@router.get("/financial/abuse/analytics", response_model=Dict[str, Any], tags=["V9 - Financial Controls"])
@limiter.limit("60/minute")
async def get_abuse_analytics(
    request: Request,
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get abuse analytics for a period"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return AbuseDetectionService.get_abuse_analytics(db, venue_id, start_date, end_date)


# ==================== CRM - GUEST PREFERENCES ====================

@router.post("/crm/preferences/{guest_id}", response_model=Dict[str, Any], tags=["V9 - CRM"])
@limiter.limit("30/minute")
async def set_guest_preferences(
    request: Request,
    guest_id: int,
    preferences: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Set or update guest preferences"""
    return GuestPreferencesService.set_guest_preferences(db, guest_id, preferences)


@router.get("/crm/preferences/{guest_id}", response_model=Optional[Dict[str, Any]], tags=["V9 - CRM"])
@limiter.limit("60/minute")
async def get_guest_preferences(
    request: Request,
    guest_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all preferences for a guest"""
    return GuestPreferencesService.get_guest_preferences(db, guest_id)


@router.get("/crm/service-alerts/{guest_id}", response_model=Dict[str, Any], tags=["V9 - CRM"])
@limiter.limit("60/minute")
async def get_service_alerts(
    request: Request,
    guest_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get service alerts for a guest (allergies, preferences, VIP status)"""
    return GuestPreferencesService.get_service_alerts(db, guest_id)


# ==================== CRM - CUSTOMER LIFETIME VALUE ====================

@router.get("/crm/clv/{guest_id}", response_model=Dict[str, Any], tags=["V9 - CRM"])
@limiter.limit("60/minute")
async def calculate_clv(
    request: Request,
    guest_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Calculate Customer Lifetime Value for a guest"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return CustomerLifetimeValueService.calculate_clv(db, guest_id, venue_id)


@router.post("/crm/clv/update", response_model=Dict[str, Any], tags=["V9 - CRM"])
@limiter.limit("30/minute")
async def update_clv_from_order(
    request: Request,
    guest_id: int,
    order_total: Decimal,
    order_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update CLV after a new order"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    if not order_date:
        order_date = datetime.now(timezone.utc)
    return CustomerLifetimeValueService.update_clv_from_order(db, guest_id, venue_id, order_total, order_date)


@router.get("/crm/at-risk-customers", response_model=List[Dict[str, Any]], tags=["V9 - CRM"])
@limiter.limit("60/minute")
async def get_at_risk_customers(
    request: Request,
    risk_threshold: float = 0.6,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get customers at risk of churning"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return CustomerLifetimeValueService.get_at_risk_customers(db, venue_id, risk_threshold, limit)


# ==================== CRM - CUSTOMER SEGMENTS ====================

@router.get("/crm/segments", response_model=Dict[str, Any], tags=["V9 - CRM"])
@limiter.limit("60/minute")
async def get_customer_segments(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get customer segmentation summary"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return CustomerSegmentationService.get_customer_segments(db, venue_id)


# ==================== CRM - VIP MANAGEMENT ====================

@router.post("/crm/vip/{guest_id}", response_model=Dict[str, Any], tags=["V9 - CRM"])
@limiter.limit("30/minute")
async def set_vip_status(
    request: Request,
    guest_id: int,
    vip_status: bool,
    vip_tier: Optional[str] = None,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Set or update VIP status for a guest"""
    set_by = current_user.id
    return VIPManagementService.set_vip_status(db, guest_id, vip_status, vip_tier, reason, set_by)


@router.get("/crm/vip", response_model=List[Dict[str, Any]], tags=["V9 - CRM"])
@limiter.limit("60/minute")
async def get_vip_guests(
    request: Request,
    tier: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all VIP guests, optionally filtered by tier"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return VIPManagementService.get_vip_guests(db, venue_id, tier)


# ==================== CRM - PERSONALIZATION ====================

@router.get("/crm/recommendations/{guest_id}", response_model=Dict[str, Any], tags=["V9 - CRM"])
@limiter.limit("60/minute")
async def get_personalized_recommendations(
    request: Request,
    guest_id: int,
    limit: int = 5,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get personalized menu recommendations for a guest"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return PersonalizationService.get_personalized_recommendations(db, guest_id, venue_id, limit)


@router.post("/crm/feedback", response_model=Dict[str, Any], tags=["V9 - CRM"])
@limiter.limit("30/minute")
async def record_feedback(
    request: Request,
    guest_id: int,
    order_id: int,
    rating: int,
    feedback_type: str,
    comments: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Record guest feedback for continuous improvement"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return PersonalizationService.record_feedback(db, guest_id, venue_id, order_id, rating, feedback_type, comments)


# ==================== IOT - DEVICE MANAGEMENT ====================

@router.post("/iot/devices", response_model=Dict[str, Any], tags=["V9 - IoT"])
@limiter.limit("30/minute")
async def register_iot_device(
    request: Request,
    device_type: str,
    device_name: str,
    serial_number: str,
    location: str,
    configuration: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Register a new IoT device"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return IoTDeviceService.register_device(db, venue_id, device_type, device_name, serial_number, location, configuration)


@router.put("/iot/devices/{device_id}/status", response_model=Dict[str, Any], tags=["V9 - IoT"])
@limiter.limit("30/minute")
async def update_device_status(
    request: Request,
    device_id: int,
    status: str,
    battery_level: Optional[int] = None,
    firmware_version: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update device status and metrics"""
    return IoTDeviceService.update_device_status(db, device_id, status, battery_level, firmware_version)


@router.get("/iot/devices", response_model=List[Dict[str, Any]], tags=["V9 - IoT"])
@limiter.limit("60/minute")
async def get_iot_devices(
    request: Request,
    device_type: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all devices for a venue"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return IoTDeviceService.get_devices(db, venue_id, device_type, status)


@router.get("/iot/devices/offline", response_model=List[Dict[str, Any]], tags=["V9 - IoT"])
@limiter.limit("60/minute")
async def get_offline_iot_devices(
    request: Request,
    threshold_minutes: int = 5,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get devices that haven't reported recently"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return IoTDeviceService.get_offline_devices(db, venue_id, threshold_minutes)


# ==================== IOT - TEMPERATURE MONITORING ====================

@router.post("/iot/temperature", response_model=Dict[str, Any], tags=["V9 - IoT"])
@limiter.limit("30/minute")
async def record_temperature(
    request: Request,
    device_id: int,
    temperature: Decimal,
    unit: str = "C",
    humidity: Optional[Decimal] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Record temperature reading from a sensor"""
    return TemperatureMonitoringService.record_temperature(db, device_id, temperature, unit, humidity)


@router.get("/iot/temperature/history", response_model=Dict[str, Any], tags=["V9 - IoT"])
@limiter.limit("60/minute")
async def get_temperature_history(
    request: Request,
    device_id: Optional[int] = None,
    location: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    alerts_only: bool = False,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get temperature history for HACCP compliance"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return TemperatureMonitoringService.get_temperature_history(db, venue_id, device_id, location, start_date, end_date, alerts_only)


@router.post("/iot/temperature/acknowledge/{log_id}", response_model=Dict[str, Any], tags=["V9 - IoT"])
@limiter.limit("30/minute")
async def acknowledge_temperature_alert(
    request: Request,
    log_id: int,
    corrective_action: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Acknowledge a temperature alert"""
    acknowledged_by = current_user.id
    return TemperatureMonitoringService.acknowledge_temperature_alert(db, log_id, acknowledged_by, corrective_action)


@router.get("/iot/haccp-report", response_model=Dict[str, Any], tags=["V9 - IoT"])
@limiter.limit("60/minute")
async def get_haccp_compliance_report(
    request: Request,
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Generate HACCP compliance report for inspections"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return TemperatureMonitoringService.get_haccp_compliance_report(db, venue_id, start_date, end_date)


# ==================== IOT - POUR METERS ====================

@router.post("/iot/pour", response_model=Dict[str, Any], tags=["V9 - IoT"])
@limiter.limit("30/minute")
async def record_pour(
    request: Request,
    device_id: int,
    product_id: int,
    poured_amount_ml: Decimal,
    expected_amount_ml: Decimal,
    staff_id: Optional[int] = None,
    order_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Record a pour reading from a smart pour meter"""
    return PourMeterService.record_pour(db, device_id, product_id, poured_amount_ml, expected_amount_ml, staff_id, order_id)


@router.get("/iot/pour/analytics", response_model=Dict[str, Any], tags=["V9 - IoT"])
@limiter.limit("60/minute")
async def get_pour_analytics(
    request: Request,
    start_date: date,
    end_date: date,
    product_id: Optional[int] = None,
    staff_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get pour accuracy analytics"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return PourMeterService.get_pour_analytics(db, venue_id, start_date, end_date, product_id, staff_id)


# ==================== IOT - SCALE ====================

@router.post("/iot/weight", response_model=Dict[str, Any], tags=["V9 - IoT"])
@limiter.limit("30/minute")
async def record_weight(
    request: Request,
    device_id: int,
    item_id: int,
    weight_grams: Decimal,
    expected_weight_grams: Optional[Decimal] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Record weight from a connected scale"""
    return ScaleService.record_weight(db, device_id, item_id, weight_grams, expected_weight_grams)


# ==================== COMPLIANCE - AUDIT LOGS ====================

@router.post("/compliance/audit-log", response_model=Dict[str, Any], tags=["V9 - Compliance"])
@limiter.limit("30/minute")
async def log_action(
    request: Request,
    action_type: str,
    entity_type: str,
    entity_id: int,
    action_details: Dict[str, Any],
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Log an action to the immutable audit log"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    user_id = current_user.id
    return ImmutableAuditService.log_action(db, venue_id, user_id, action_type, entity_type, entity_id, action_details, ip_address, user_agent)


@router.get("/compliance/audit-log/verify", response_model=Dict[str, Any], tags=["V9 - Compliance"])
@limiter.limit("60/minute")
async def verify_audit_chain(
    request: Request,
    start_id: Optional[int] = None,
    end_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Verify the integrity of the audit log chain"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return ImmutableAuditService.verify_audit_chain(db, venue_id, start_id, end_id)


@router.get("/compliance/audit-log", response_model=List[Dict[str, Any]], tags=["V9 - Compliance"])
@limiter.limit("60/minute")
async def get_audit_logs(
    request: Request,
    action_type: Optional[str] = None,
    entity_type: Optional[str] = None,
    user_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get audit logs with filters"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return ImmutableAuditService.get_audit_logs(db, venue_id, action_type, entity_type, user_id, start_date, end_date, limit)


# ==================== COMPLIANCE - FISCAL ARCHIVE ====================

@router.post("/compliance/fiscal-archive", response_model=Dict[str, Any], tags=["V9 - Compliance"])
@limiter.limit("30/minute")
async def archive_fiscal_receipt(
    request: Request,
    order_id: int,
    receipt_number: str,
    fiscal_device_id: str,
    receipt_data: Dict[str, Any],
    signature: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Archive a fiscal receipt for compliance"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return FiscalArchiveService.archive_fiscal_receipt(db, venue_id, order_id, receipt_number, fiscal_device_id, receipt_data, signature)


@router.get("/compliance/fiscal-archive", response_model=Dict[str, Any], tags=["V9 - Compliance"])
@limiter.limit("60/minute")
async def get_fiscal_archive(
    request: Request,
    start_date: date,
    end_date: date,
    receipt_number: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get fiscal archive for a period"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return FiscalArchiveService.get_fiscal_archive(db, venue_id, start_date, end_date, receipt_number)


# ==================== COMPLIANCE - NRA EXPORT ====================

@router.post("/compliance/nra-export", response_model=Dict[str, Any], tags=["V9 - Compliance"])
@limiter.limit("30/minute")
async def create_nra_export(
    request: Request,
    export_type: str,
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create NRA export package for Bulgarian tax authority"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    requested_by = current_user.id
    return NRAExportService.create_nra_export(db, venue_id, export_type, start_date, end_date, requested_by)


@router.get("/compliance/nra-exports", response_model=List[Dict[str, Any]], tags=["V9 - Compliance"])
@limiter.limit("60/minute")
async def get_nra_exports(
    request: Request,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get list of NRA exports"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return NRAExportService.get_nra_exports(db, venue_id, limit)


# ==================== COMPLIANCE - AGE VERIFICATION ====================

@router.post("/compliance/age-verification", response_model=Dict[str, Any], tags=["V9 - Compliance"])
@limiter.limit("30/minute")
async def log_age_verification(
    request: Request,
    verification_method: str,
    order_id: Optional[int] = None,
    guest_birth_date: Optional[date] = None,
    document_number: Optional[str] = None,
    verification_passed: bool = True,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Log an age verification for compliance"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    staff_id = current_user.id
    return AgeVerificationService.log_age_verification(
        db, venue_id, staff_id, order_id, verification_method,
        guest_birth_date, document_number, verification_passed, notes
    )


@router.get("/compliance/age-verification/report", response_model=Dict[str, Any], tags=["V9 - Compliance"])
@limiter.limit("60/minute")
async def get_age_verification_report(
    request: Request,
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get age verification report for compliance"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return AgeVerificationService.get_age_verification_report(db, venue_id, start_date, end_date)


# ==================== COMPLIANCE - GDPR ====================

@router.post("/compliance/gdpr/delete-request", response_model=Dict[str, Any], tags=["V9 - Compliance"])
@limiter.limit("30/minute")
async def process_data_deletion_request(
    request: Request,
    customer_id: int,
    reason: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Process GDPR data deletion request - anonymize personal data"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    requested_by = current_user.id
    from app.services.v9_features.compliance_service import ComplianceService
    return ComplianceService.process_data_deletion_request(db, venue_id, customer_id, requested_by, reason)


@router.get("/compliance/gdpr/export/{customer_id}", response_model=Dict[str, Any], tags=["V9 - Compliance"])
@limiter.limit("60/minute")
async def generate_gdpr_data_export(
    request: Request,
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Generate GDPR data export for a customer - compile all personal data"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    from app.services.v9_features.compliance_service import ComplianceService
    return ComplianceService.generate_data_export(db, venue_id, customer_id)


# ==================== AI - MODEL MANAGEMENT ====================

@router.post("/ai/models", response_model=Dict[str, Any], tags=["V9 - AI & Automation"])
@limiter.limit("30/minute")
async def register_ai_model(
    request: Request,
    model_name: str,
    model_type: str,
    model_version: str,
    configuration: Dict[str, Any],
    description: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Register a new AI model"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return AIModelService.register_model(db, venue_id, model_name, model_type, model_version, configuration, description)


@router.post("/ai/models/{model_id}/activate", response_model=Dict[str, Any], tags=["V9 - AI & Automation"])
@limiter.limit("30/minute")
async def activate_ai_model(
    request: Request,
    model_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Activate an AI model"""
    return AIModelService.activate_model(db, model_id)


@router.get("/ai/models/active", response_model=List[Dict[str, Any]], tags=["V9 - AI & Automation"])
@limiter.limit("60/minute")
async def get_active_ai_models(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all active AI models for a venue"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return AIModelService.get_active_models(db, venue_id)


@router.put("/ai/models/{model_id}/accuracy", response_model=Dict[str, Any], tags=["V9 - AI & Automation"])
@limiter.limit("30/minute")
async def update_model_accuracy(
    request: Request,
    model_id: int,
    accuracy_score: Decimal,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update model accuracy score after evaluation"""
    return AIModelService.update_model_accuracy(db, model_id, accuracy_score)


# ==================== AI - PREDICTIONS ====================

@router.post("/ai/predictions", response_model=Dict[str, Any], tags=["V9 - AI & Automation"])
@limiter.limit("30/minute")
async def log_prediction(
    request: Request,
    model_id: int,
    prediction_type: str,
    input_data: Dict[str, Any],
    predicted_value: Any,
    confidence_score: Decimal,
    target_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Log an AI prediction"""
    return PredictionService.log_prediction(db, model_id, prediction_type, input_data, predicted_value, confidence_score, target_date)


@router.post("/ai/predictions/{prediction_id}/actual", response_model=Dict[str, Any], tags=["V9 - AI & Automation"])
@limiter.limit("30/minute")
async def record_actual_value(
    request: Request,
    prediction_id: int,
    actual_value: Any,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Record actual value for a prediction to measure accuracy"""
    return PredictionService.record_actual_value(db, prediction_id, actual_value)


@router.get("/ai/predictions/accuracy-report", response_model=Dict[str, Any], tags=["V9 - AI & Automation"])
@limiter.limit("60/minute")
async def get_prediction_accuracy_report(
    request: Request,
    model_id: Optional[int] = None,
    prediction_type: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get prediction accuracy report"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return PredictionService.get_prediction_accuracy_report(db, venue_id, model_id, prediction_type, start_date, end_date)


# ==================== AI - AUTOMATION RULES ====================

@router.post("/ai/automation-rules", response_model=Dict[str, Any], tags=["V9 - AI & Automation"])
@limiter.limit("30/minute")
async def create_automation_rule(
    request: Request,
    rule_name: str,
    trigger_type: str,
    trigger_config: Dict[str, Any],
    action_type: str,
    action_config: Dict[str, Any],
    enabled: bool = True,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create an automation rule"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return AutomationRuleService.create_automation_rule(db, venue_id, rule_name, trigger_type, trigger_config, action_type, action_config, enabled)


@router.get("/ai/automation-rules", response_model=List[Dict[str, Any]], tags=["V9 - AI & Automation"])
@limiter.limit("60/minute")
async def get_automation_rules(
    request: Request,
    enabled_only: bool = False,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all automation rules for a venue"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return AutomationRuleService.get_automation_rules(db, venue_id, enabled_only)


@router.put("/ai/automation-rules/{rule_id}/toggle", response_model=Dict[str, Any], tags=["V9 - AI & Automation"])
@limiter.limit("30/minute")
async def toggle_automation_rule(
    request: Request,
    rule_id: int,
    enabled: bool,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Enable or disable an automation rule"""
    return AutomationRuleService.toggle_automation_rule(db, rule_id, enabled)


@router.post("/ai/automation-rules/check", response_model=List[Dict[str, Any]], tags=["V9 - AI & Automation"])
@limiter.limit("30/minute")
async def check_and_execute_automations(
    request: Request,
    trigger_type: str,
    trigger_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Check and execute matching automation rules"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return AutomationRuleService.check_and_execute_automations(db, venue_id, trigger_type, trigger_data)


# ==================== AI - MENU OPTIMIZATION ====================

@router.get("/ai/menu-optimization", response_model=Dict[str, Any], tags=["V9 - AI & Automation"])
@limiter.limit("60/minute")
async def get_menu_optimization_suggestions(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get AI-powered menu optimization suggestions based on real sales data"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return MenuOptimizationService.get_menu_optimization_suggestions(db, venue_id)


# ==================== AI - STAFFING RECOMMENDATIONS ====================

@router.get("/ai/staffing-recommendations", response_model=Dict[str, Any], tags=["V9 - AI & Automation"])
@limiter.limit("60/minute")
async def get_staffing_recommendations(
    request: Request,
    target_date: date,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get AI-powered staffing recommendations based on historical data"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return StaffingRecommendationService.get_staffing_recommendations(db, venue_id, target_date)


# ==================== LEGAL - INCIDENT REPORTS ====================

@router.post("/legal/incidents", response_model=Dict[str, Any], tags=["V9 - Legal & Training"])
@limiter.limit("30/minute")
async def create_incident_report(
    request: Request,
    incident_type: str,
    incident_date: datetime,
    location: str,
    description: str,
    severity: str,
    persons_involved: Optional[List[Dict[str, Any]]] = None,
    witnesses: Optional[List[Dict[str, Any]]] = None,
    immediate_actions: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create an incident report"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    reported_by = current_user.id
    return LegalRiskService.create_incident_report(
        db, venue_id, reported_by, incident_type, incident_date, location,
        description, severity, persons_involved, witnesses, immediate_actions
    )


@router.post("/legal/incidents/{report_id}/evidence", response_model=Dict[str, Any], tags=["V9 - Legal & Training"])
@limiter.limit("30/minute")
async def add_incident_evidence(
    request: Request,
    report_id: int,
    evidence_type: str,
    file_path: str,
    description: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Add evidence to an incident report"""
    uploaded_by = current_user.id
    return LegalRiskService.add_evidence(db, report_id, evidence_type, file_path, description, uploaded_by)


@router.put("/legal/incidents/{report_id}/status", response_model=Dict[str, Any], tags=["V9 - Legal & Training"])
@limiter.limit("30/minute")
async def update_incident_status(
    request: Request,
    report_id: int,
    status: str,
    notes: Optional[str] = None,
    resolution: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update incident report status"""
    updated_by = current_user.id
    return LegalRiskService.update_incident_status(db, report_id, status, updated_by, notes, resolution)


@router.get("/legal/incidents", response_model=List[Dict[str, Any]], tags=["V9 - Legal & Training"])
@limiter.limit("60/minute")
async def get_incident_reports(
    request: Request,
    status: Optional[str] = None,
    incident_type: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get incident reports with filters"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return LegalRiskService.get_incident_reports(db, venue_id, status, incident_type, start_date, end_date)


@router.post("/legal/incidents/{report_id}/insurance", response_model=Dict[str, Any], tags=["V9 - Legal & Training"])
@limiter.limit("30/minute")
async def link_insurance_claim(
    request: Request,
    report_id: int,
    claim_number: str,
    claim_details: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Link an insurance claim to an incident report"""
    return LegalRiskService.link_insurance_claim(db, report_id, claim_number, claim_details)


# ==================== TRAINING ====================

@router.post("/training/modules", response_model=Dict[str, Any], tags=["V9 - Legal & Training"])
@limiter.limit("30/minute")
async def create_training_module(
    request: Request,
    module_name: str,
    module_type: str,
    description: str,
    content: Dict[str, Any],
    duration_minutes: int,
    required_roles: List[str],
    passing_score: int = 80,
    certification_valid_days: Optional[int] = 365,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a training module"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return TrainingService.create_training_module(
        db, venue_id, module_name, module_type, description, content,
        duration_minutes, required_roles, passing_score, certification_valid_days
    )


@router.get("/training/modules", response_model=List[Dict[str, Any]], tags=["V9 - Legal & Training"])
@limiter.limit("60/minute")
async def get_training_modules(
    request: Request,
    module_type: Optional[str] = None,
    role: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get training modules with filters"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return TrainingService.get_training_modules(db, venue_id, module_type, role)


@router.post("/training/start/{module_id}", response_model=Dict[str, Any], tags=["V9 - Legal & Training"])
@limiter.limit("30/minute")
async def start_training(
    request: Request,
    module_id: int,
    staff_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Start a training session for a staff member"""
    return TrainingService.start_training(db, staff_id, module_id)


@router.post("/training/complete/{record_id}", response_model=Dict[str, Any], tags=["V9 - Legal & Training"])
@limiter.limit("30/minute")
async def complete_training(
    request: Request,
    record_id: int,
    score: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Complete a training session with score"""
    return TrainingService.complete_training(db, record_id, score)


@router.get("/training/status/{staff_id}", response_model=Dict[str, Any], tags=["V9 - Legal & Training"])
@limiter.limit("60/minute")
async def get_staff_training_status(
    request: Request,
    staff_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get training status for a staff member"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return TrainingService.get_staff_training_status(db, staff_id, venue_id)


@router.get("/training/expiring-certifications", response_model=List[Dict[str, Any]], tags=["V9 - Legal & Training"])
@limiter.limit("60/minute")
async def get_expiring_certifications(
    request: Request,
    days_ahead: int = 30,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get certifications expiring soon"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return TrainingService.get_expiring_certifications(db, venue_id, days_ahead)


# ==================== CRISIS MANAGEMENT ====================

@router.post("/crisis/modes", response_model=Dict[str, Any], tags=["V9 - Legal & Training"])
@limiter.limit("30/minute")
async def create_crisis_mode(
    request: Request,
    mode_name: str,
    mode_type: str,
    description: str,
    simplified_menu_ids: List[int],
    margin_protection_percentage: Decimal,
    operational_changes: Dict[str, Any],
    auto_activation_conditions: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a crisis mode configuration"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return CrisisManagementService.create_crisis_mode(
        db, venue_id, mode_name, mode_type, description, simplified_menu_ids,
        margin_protection_percentage, operational_changes, auto_activation_conditions
    )


@router.post("/crisis/modes/{crisis_mode_id}/activate", response_model=Dict[str, Any], tags=["V9 - Legal & Training"])
@limiter.limit("30/minute")
async def activate_crisis_mode(
    request: Request,
    crisis_mode_id: int,
    reason: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Activate a crisis mode"""
    activated_by = current_user.id
    return CrisisManagementService.activate_crisis_mode(db, crisis_mode_id, activated_by, reason)


@router.post("/crisis/deactivate", response_model=Dict[str, Any], tags=["V9 - Legal & Training"])
@limiter.limit("30/minute")
async def deactivate_crisis_mode(
    request: Request,
    reason: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Deactivate the current crisis mode"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    deactivated_by = current_user.id
    return CrisisManagementService.deactivate_crisis_mode(db, venue_id, deactivated_by, reason)


@router.get("/crisis/active", response_model=Optional[Dict[str, Any]], tags=["V9 - Legal & Training"])
@limiter.limit("60/minute")
async def get_active_crisis_mode(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get the currently active crisis mode"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return CrisisManagementService.get_active_crisis_mode(db, venue_id)


@router.get("/crisis/modes", response_model=List[Dict[str, Any]], tags=["V9 - Legal & Training"])
@limiter.limit("60/minute")
async def get_crisis_modes(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all crisis mode configurations"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return CrisisManagementService.get_crisis_modes(db, venue_id)


@router.post("/crisis/check-auto-activation", response_model=Optional[Dict[str, Any]], tags=["V9 - Legal & Training"])
@limiter.limit("30/minute")
async def check_crisis_auto_activation(
    request: Request,
    current_conditions: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Check if any crisis mode should be auto-activated"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return CrisisManagementService.check_auto_activation(db, venue_id, current_conditions)


# ==================== PLATFORM - FEATURE FLAGS ====================

@router.post("/platform/feature-flags", response_model=Dict[str, Any], tags=["V9 - Platform"])
@limiter.limit("30/minute")
async def create_feature_flag(
    request: Request,
    feature_key: str,
    feature_name: str,
    description: str,
    enabled: bool = False,
    rollout_percentage: int = 0,
    conditions: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a feature flag"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return PlatformService.create_feature_flag(db, venue_id, feature_key, feature_name, description, enabled, rollout_percentage, conditions)


@router.get("/platform/feature-flags/check/{feature_key}", response_model=Dict[str, Any], tags=["V9 - Platform"])
@limiter.limit("60/minute")
async def check_feature(
    request: Request,
    feature_key: str,
    user_id: Optional[int] = None,
    context: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Check if a feature is enabled for a user/context"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return PlatformService.check_feature(db, venue_id, feature_key, user_id, context)


@router.put("/platform/feature-flags/{flag_id}", response_model=Dict[str, Any], tags=["V9 - Platform"])
@limiter.limit("30/minute")
async def update_feature_flag(
    request: Request,
    flag_id: int,
    updates: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update a feature flag"""
    return PlatformService.update_feature_flag(db, flag_id, updates)


@router.get("/platform/feature-flags", response_model=List[Dict[str, Any]], tags=["V9 - Platform"])
@limiter.limit("60/minute")
async def get_feature_flags(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all feature flags for a venue"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return PlatformService.get_feature_flags(db, venue_id)


# ==================== PLATFORM - WHITE LABEL ====================

@router.post("/platform/white-label", response_model=Dict[str, Any], tags=["V9 - Platform"])
@limiter.limit("30/minute")
async def set_white_label_config(
    request: Request,
    brand_name: str,
    logo_url: Optional[str] = None,
    primary_color: str = "#2563eb",
    secondary_color: str = "#1e40af",
    accent_color: str = "#f59e0b",
    font_family: str = "Inter",
    custom_css: Optional[str] = None,
    custom_domain: Optional[str] = None,
    email_from_name: Optional[str] = None,
    email_from_address: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Set white-label configuration"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return PlatformService.set_white_label_config(
        db, venue_id, brand_name, logo_url, primary_color, secondary_color,
        accent_color, font_family, custom_css, custom_domain, email_from_name, email_from_address
    )


@router.get("/platform/white-label", response_model=Optional[Dict[str, Any]], tags=["V9 - Platform"])
@limiter.limit("60/minute")
async def get_white_label_config(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get white-label configuration"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return PlatformService.get_white_label_config(db, venue_id)


# ==================== QR - PAY AT TABLE ====================

@router.post("/qr/payment-session", response_model=Dict[str, Any], tags=["V9 - QR & Self-Service"])
@limiter.limit("30/minute")
async def create_qr_payment_session(
    request: Request,
    order_id: int,
    table_number: str,
    total_amount: Decimal,
    tip_suggestions: Optional[List[int]] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a QR payment session"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return QRSelfServiceService.create_qr_payment_session(db, venue_id, order_id, table_number, total_amount, tip_suggestions)


@router.get("/qr/payment-session/{session_code}", response_model=Optional[Dict[str, Any]], tags=["V9 - QR & Self-Service"])
@limiter.limit("60/minute")
async def get_payment_session(
    request: Request,
    session_code: str,
    db: Session = Depends(get_db)
):
    """Get payment session by code (no auth required for guest access)"""
    return QRSelfServiceService.get_payment_session(db, session_code)


@router.post("/qr/payment-session/{session_id}/split", response_model=Dict[str, Any], tags=["V9 - QR & Self-Service"])
@limiter.limit("30/minute")
async def configure_split_payment(
    request: Request,
    session_id: int,
    split_type: str,
    split_count: int,
    db: Session = Depends(get_db)
):
    """Configure split payment for a session"""
    return QRSelfServiceService.configure_split_payment(db, session_id, split_type, split_count)


@router.post("/qr/payment-session/{session_id}/pay", response_model=Dict[str, Any], tags=["V9 - QR & Self-Service"])
@limiter.limit("30/minute")
async def record_qr_payment(
    request: Request,
    session_id: int,
    amount: Decimal,
    tip_amount: Decimal,
    payment_method: str,
    payer_name: Optional[str] = None,
    transaction_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Record a payment in a QR session"""
    return QRSelfServiceService.record_payment(db, session_id, amount, tip_amount, payment_method, payer_name, transaction_id)


# ==================== QR - SCAN TO REORDER ====================

@router.post("/qr/reorder-session", response_model=Dict[str, Any], tags=["V9 - QR & Self-Service"])
@limiter.limit("30/minute")
async def create_reorder_session(
    request: Request,
    original_order_id: int,
    table_number: str,
    guest_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a scan-to-reorder session"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return QRSelfServiceService.create_reorder_session(db, venue_id, guest_id, original_order_id, table_number)


@router.get("/qr/reorder-session/{session_code}", response_model=Optional[Dict[str, Any]], tags=["V9 - QR & Self-Service"])
@limiter.limit("60/minute")
async def get_reorder_items(
    request: Request,
    session_code: str,
    db: Session = Depends(get_db)
):
    """Get items from original order for reordering (no auth for guest access)"""
    return QRSelfServiceService.get_reorder_items(db, session_code)


@router.post("/qr/reorder-session/{session_id}/confirm", response_model=Dict[str, Any], tags=["V9 - QR & Self-Service"])
@limiter.limit("30/minute")
async def confirm_reorder(
    request: Request,
    session_id: int,
    selected_item_ids: List[int],
    modifications: Optional[Dict[int, str]] = None,
    db: Session = Depends(get_db)
):
    """Confirm reorder with selected items"""
    return QRSelfServiceService.confirm_reorder(db, session_id, selected_item_ids, modifications)


# ==================== QR - TABLE QR CODES ====================

@router.get("/qr/table/{table_number}", response_model=Dict[str, Any], tags=["V9 - QR & Self-Service"])
@limiter.limit("60/minute")
async def generate_table_qr(
    request: Request,
    table_number: str,
    qr_type: str = "menu",
    current_user: dict = Depends(get_current_user)
):
    """Generate QR code data for a table"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return QRSelfServiceService.generate_table_qr(venue_id, table_number, qr_type)


# ==================== KIOSK - SELF SERVICE ====================

@router.get("/kiosk/menu", response_model=Dict[str, Any], tags=["V9 - QR & Self-Service"])
@limiter.limit("60/minute")
async def get_kiosk_menu(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get menu formatted for self-service kiosk"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return QRSelfServiceService.get_kiosk_menu(db, venue_id)


@router.post("/kiosk/order", response_model=Dict[str, Any], tags=["V9 - QR & Self-Service"])
@limiter.limit("30/minute")
async def submit_kiosk_order(
    request: Request,
    items: List[Dict[str, Any]],
    payment_method: str,
    guest_name: Optional[str] = None,
    special_instructions: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Submit order from self-service kiosk"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return QRSelfServiceService.submit_kiosk_order(db, venue_id, items, payment_method, guest_name, special_instructions)

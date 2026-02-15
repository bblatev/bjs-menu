"""
V9 Advanced Features API Endpoints - Part 2
Financial Controls, CRM, IoT, Compliance, AI, Legal/Training/Crisis, Platform/QR
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, UploadFile, File, Request
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal

from app.db.session import get_db
from app.core.rate_limit import limiter

# Import services (already imported in main v9_endpoints.py)
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
    PourMeterService
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

from app.schemas.v9_schemas import *

# Create router for part 2
router_part2 = APIRouter()


# ==================== FINANCIAL CONTROLS - PRIME COST ====================

@router_part2.post("/finance/prime-cost", response_model=Dict[str, Any], tags=["V9 - Financial Controls"])
@limiter.limit("30/minute")
async def record_prime_cost(
    request: Request,
    data: PrimeCostRecord,
    venue_id: int,
    db: Session = Depends(get_db)
):
    """Record daily prime cost data"""
    return PrimeCostService.record_prime_cost(
        db=db,
        venue_id=venue_id,
        period_date=data.date,
        food_cost=data.food_cost,
        beverage_cost=data.beverage_cost,
        labor_cost=data.labor_cost,
        revenue=data.revenue
    )


@router_part2.get("/finance/prime-cost/dashboard", response_model=Dict[str, Any], tags=["V9 - Financial Controls"])
@limiter.limit("60/minute")
async def get_prime_cost_dashboard(
    request: Request,
    venue_id: int,
    start_date: date = Query(default_factory=lambda: date.today() - timedelta(days=30)),
    end_date: date = Query(default_factory=date.today),
    db: Session = Depends(get_db)
):
    """Get prime cost dashboard with trends and alerts"""
    return PrimeCostService.get_prime_cost_dashboard(
        db=db,
        venue_id=venue_id,
        start_date=start_date,
        end_date=end_date
    )


# ==================== FINANCIAL CONTROLS - ABUSE DETECTION ====================

@router_part2.post("/finance/abuse/config", response_model=Dict[str, Any], tags=["V9 - Financial Controls"])
@limiter.limit("30/minute")
async def configure_abuse_detection(
    request: Request,
    data: AbuseConfigUpdate,
    venue_id: int,
    db: Session = Depends(get_db)
):
    """Configure abuse detection thresholds"""
    # Get or create config first, then update if needed
    config = AbuseDetectionService.get_or_create_abuse_config(db=db, venue_id=venue_id)
    if data.threshold_count or data.threshold_amount or data.time_window_hours or data.is_active is not None:
        updates = {}
        if data.threshold_count:
            updates["refund_threshold_count"] = data.threshold_count
        if data.threshold_amount:
            updates["refund_threshold_amount"] = data.threshold_amount
        if data.time_window_hours:
            updates["refund_threshold_period_hours"] = data.time_window_hours
        if data.is_active is not None:
            updates["enabled"] = data.is_active
        config = AbuseDetectionService.update_abuse_config(db=db, venue_id=venue_id, updates=updates)
    return config


@router_part2.post("/finance/abuse/check/{staff_id}", response_model=Dict[str, Any], tags=["V9 - Financial Controls"])
@limiter.limit("30/minute")
async def check_for_abuse(
    request: Request,
    staff_id: int,
    venue_id: int,
    transaction_type: str,
    amount: Decimal,
    order_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Check if transaction triggers abuse detection"""
    return AbuseDetectionService.check_for_abuse(
        db=db,
        venue_id=venue_id,
        staff_id=staff_id,
        action_type=transaction_type,
        amount=amount,
        order_id=order_id
    )


@router_part2.get("/finance/abuse/alerts", response_model=List[AbuseAlertResponse], tags=["V9 - Financial Controls"])
@limiter.limit("60/minute")
async def get_abuse_alerts(
    request: Request,
    venue_id: int,
    pending_only: bool = True,
    staff_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get abuse alerts pending investigation"""
    # When pending_only is True, we filter by status in the service
    # severity parameter filters by severity level, not status
    return AbuseDetectionService.get_pending_alerts(
        db=db,
        venue_id=venue_id,
        severity=None,  # Don't filter by severity
        staff_id=staff_id
    )


@router_part2.post("/finance/abuse/investigate", response_model=SuccessResponse, tags=["V9 - Financial Controls"])
@limiter.limit("30/minute")
async def investigate_abuse_alert(
    request: Request,
    data: InvestigationSubmit,
    db: Session = Depends(get_db)
):
    """Submit investigation results for abuse alert"""
    result = AbuseDetectionService.investigate_alert(
        db=db,
        alert_id=data.alert_id,
        investigator_id=data.investigator_id,
        status=data.action_taken,
        notes=data.notes
    )
    return SuccessResponse(success=True, message="Investigation recorded")


@router_part2.get("/finance/abuse/analytics", response_model=Dict[str, Any], tags=["V9 - Financial Controls"])
@limiter.limit("60/minute")
async def get_abuse_analytics(
    request: Request,
    venue_id: int,
    start_date: date = Query(default_factory=lambda: date.today() - timedelta(days=30)),
    end_date: date = Query(default_factory=date.today),
    db: Session = Depends(get_db)
):
    """Get abuse detection analytics"""
    return AbuseDetectionService.get_abuse_analytics(
        db=db,
        venue_id=venue_id,
        start_date=start_date,
        end_date=end_date
    )


# ==================== CRM - GUEST PREFERENCES ====================

@router_part2.post("/crm/preferences", response_model=GuestPreferencesResponse, tags=["V9 - CRM"])
@limiter.limit("30/minute")
async def set_guest_preferences(
    request: Request,
    data: GuestPreferencesUpdate,
    db: Session = Depends(get_db)
):
    """Set or update guest preferences"""
    preferences = {
        "dietary_restrictions": data.dietary_restrictions,
        "allergies": data.allergies,
        "favorite_items": data.favorite_items,
        "preferred_seating": data.preferred_seating,
        "preferred_server_ids": [data.preferred_server_id] if data.preferred_server_id else [],
        "communication_preference": data.communication_preferences,
        "special_occasions": data.special_occasions or {},
        "notes": data.notes
    }
    return GuestPreferencesService.set_guest_preferences(
        db=db,
        guest_id=data.customer_id,
        preferences=preferences
    )


@router_part2.get("/crm/preferences/{customer_id}", response_model=GuestPreferencesResponse, tags=["V9 - CRM"])
@limiter.limit("60/minute")
async def get_guest_preferences(
    request: Request,
    customer_id: int,
    db: Session = Depends(get_db)
):
    """Get guest preferences"""
    result = GuestPreferencesService.get_guest_preferences(db=db, guest_id=customer_id)
    if not result:
        raise HTTPException(status_code=404, detail="Preferences not found")
    return result


@router_part2.get("/crm/service-alerts/{customer_id}", response_model=List[ServiceAlert], tags=["V9 - CRM"])
@limiter.limit("60/minute")
async def get_service_alerts(
    request: Request,
    customer_id: int,
    db: Session = Depends(get_db)
):
    """Get service alerts for a customer (allergies, VIP status, occasions)"""
    return GuestPreferencesService.get_service_alerts(db=db, guest_id=customer_id)


# ==================== CRM - CUSTOMER LIFETIME VALUE ====================

@router_part2.get("/crm/clv/{customer_id}", response_model=CLVResponse, tags=["V9 - CRM"])
@limiter.limit("60/minute")
async def get_customer_clv(
    request: Request,
    customer_id: int,
    venue_id: int,
    db: Session = Depends(get_db)
):
    """Get customer lifetime value"""
    return CustomerLifetimeValueService.calculate_clv(db=db, guest_id=customer_id, venue_id=venue_id)


@router_part2.post("/crm/clv/update/{customer_id}", response_model=CLVResponse, tags=["V9 - CRM"])
@limiter.limit("30/minute")
async def update_clv_from_order(
    request: Request,
    customer_id: int,
    order_id: int,
    venue_id: int,
    db: Session = Depends(get_db)
):
    """Update CLV after new order"""
    # Get order details for total and date
    from app.models import Order
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return CustomerLifetimeValueService.update_clv_from_order(
        db=db,
        guest_id=customer_id,
        venue_id=venue_id,
        order_total=order.total or Decimal("0"),
        order_date=order.created_at or datetime.now(timezone.utc)
    )


@router_part2.get("/crm/at-risk", response_model=List[Dict[str, Any]], tags=["V9 - CRM"])
@limiter.limit("60/minute")
async def get_at_risk_customers(
    request: Request,
    venue_id: int,
    risk_threshold: float = 0.6,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get customers at risk of churning"""
    return CustomerLifetimeValueService.get_at_risk_customers(
        db=db,
        venue_id=venue_id,
        risk_threshold=risk_threshold,
        limit=limit
    )


# ==================== CRM - SEGMENTATION ====================

# DUPLICATE: @router_part2.get("/crm/segments", response_model=Dict[str, Any], tags=["V9 - CRM"])
async def get_customer_segments(
    venue_id: int,
    db: Session = Depends(get_db)
):
    """Get all customer segments with metrics"""
    return CustomerSegmentationService.get_customer_segments(db=db, venue_id=venue_id)


@router_part2.get("/crm/segments/{segment}/customers", response_model=List[Dict[str, Any]], tags=["V9 - CRM"])
@limiter.limit("60/minute")
async def get_segment_customers(
    request: Request,
    segment: str,
    venue_id: int,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get customers in a specific segment"""
    # Use get_at_risk_customers for at-risk segment, otherwise filter from CLV data
    from app.models.advanced_features_v9 import CustomerLifetimeValue

    customers = db.query(CustomerLifetimeValue).filter(
        CustomerLifetimeValue.venue_id == venue_id,
        CustomerLifetimeValue.segment == segment
    ).limit(limit).all()

    return [{
        "guest_id": c.guest_id,
        "segment": c.segment,
        "lifetime_value": float(c.lifetime_value) if c.lifetime_value else 0,
        "visit_count": c.visit_count,
        "average_order_value": float(c.average_order_value) if c.average_order_value else 0,
        "churn_risk_score": float(c.churn_risk_score) if c.churn_risk_score else 0,
        "last_visit_date": c.last_visit_date.isoformat() if c.last_visit_date else None
    } for c in customers]


# ==================== CRM - VIP MANAGEMENT ====================

@router_part2.post("/crm/vip", response_model=SuccessResponse, tags=["V9 - CRM"])
@limiter.limit("30/minute")
async def set_vip_status(
    request: Request,
    data: VIPStatusUpdate,
    db: Session = Depends(get_db)
):
    """Set or update VIP status for customer"""
    tier_value = data.tier.value if hasattr(data.tier, 'value') else data.tier
    result = VIPManagementService.set_vip_status(
        db=db,
        guest_id=data.customer_id,
        vip_status=True,
        vip_tier=tier_value,
        reason=data.reason
    )
    return SuccessResponse(success=True, message=f"VIP status set to {tier_value}")


@router_part2.get("/crm/vip/{customer_id}", response_model=Dict[str, Any], tags=["V9 - CRM"])
@limiter.limit("60/minute")
async def get_vip_status(
    request: Request,
    customer_id: int,
    db: Session = Depends(get_db)
):
    """Get VIP status and benefits for customer"""
    prefs = VIPManagementService.get_guest_preferences(db=db, guest_id=customer_id)
    if not prefs:
        return {
            "guest_id": customer_id,
            "vip_status": False,
            "vip_tier": None,
            "message": "Customer not found or not a VIP"
        }
    return {
        "guest_id": customer_id,
        "vip_status": prefs.get("vip_status", False),
        "vip_tier": prefs.get("vip_tier"),
        "preferred_seating": prefs.get("preferred_seating"),
        "notes": prefs.get("notes")
    }


# ==================== CRM - PERSONALIZATION ====================

@router_part2.get("/crm/recommendations/{customer_id}", response_model=Dict[str, Any], tags=["V9 - CRM"])
@limiter.limit("60/minute")
async def get_personalized_recommendations(
    request: Request,
    customer_id: int,
    venue_id: int,
    limit: int = 5,
    db: Session = Depends(get_db)
):
    """Get personalized menu recommendations for customer"""
    return PersonalizationService.get_personalized_recommendations(
        db=db,
        guest_id=customer_id,
        venue_id=venue_id,
        limit=limit
    )


# ==================== IOT - DEVICE MANAGEMENT ====================

# DUPLICATE: @router_part2.post("/iot/devices", response_model=IoTDeviceResponse, tags=["V9 - IoT"])
async def register_iot_device(
    data: IoTDeviceRegister,
    venue_id: int,
    db: Session = Depends(get_db)
):
    """Register a new IoT device"""
    return IoTDeviceService.register_device(
        db=db,
        venue_id=venue_id,
        device_type=data.device_type.value if hasattr(data.device_type, 'value') else data.device_type,
        device_name=data.device_name,
        serial_number=data.device_id,
        location=data.location,
        configuration=data.alert_thresholds or {}
    )


# DUPLICATE: @router_part2.put("/iot/devices/{device_id}/status", response_model=SuccessResponse, tags=["V9 - IoT"])
async def update_device_status(
    device_id: int,
    status: str,
    battery_level: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Update IoT device status"""
    result = IoTDeviceService.update_device_status(
        db=db,
        device_id=device_id,
        status=status,
        battery_level=battery_level
    )
    return SuccessResponse(success=True, message="Status updated")


# DUPLICATE: @router_part2.get("/iot/devices/offline", response_model=List[IoTDeviceResponse], tags=["V9 - IoT"])
async def get_offline_iot_devices(
    venue_id: int,
    threshold_minutes: int = 15,
    db: Session = Depends(get_db)
):
    """Get IoT devices that haven't reported recently"""
    return IoTDeviceService.get_offline_devices(db=db, venue_id=venue_id, offline_threshold_minutes=threshold_minutes)


# ==================== IOT - TEMPERATURE MONITORING ====================

# DUPLICATE: @router_part2.post("/iot/temperature", response_model=Dict[str, Any], tags=["V9 - IoT"])
async def record_temperature(
    data: TemperatureReading,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Record temperature reading from sensor"""
    # Get device by serial number to get device_id
    from app.models.advanced_features_v9 import IoTDevice
    device = db.query(IoTDevice).filter(IoTDevice.serial_number == data.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail=f"Device with ID {data.device_id} not found")

    result = TemperatureMonitoringService.record_temperature(
        db=db,
        device_id=device.id,
        temperature=Decimal(str(data.temperature_celsius)),
        unit="C",
        humidity=Decimal(str(data.humidity_percent)) if data.humidity_percent else None
    )
    # Check for alerts in background
    if result.get("alert") or result.get("alert_triggered"):
        background_tasks.add_task(send_temperature_alert, result)
    return result


@router_part2.get("/iot/temperature/history/{venue_id}", response_model=Dict[str, Any], tags=["V9 - IoT"])
@limiter.limit("60/minute")
async def get_temperature_history(
    request: Request,
    venue_id: int,
    device_id: Optional[int] = None,
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """Get temperature history for a venue/device"""
    from datetime import timedelta
    start = datetime.now(timezone.utc) - timedelta(hours=hours)
    return TemperatureMonitoringService.get_temperature_history(
        db=db,
        venue_id=venue_id,
        device_id=device_id,
        start_date=start
    )


@router_part2.get("/iot/temperature/alerts", response_model=Dict[str, Any], tags=["V9 - IoT"])
@limiter.limit("60/minute")
async def get_temperature_alerts(
    request: Request,
    venue_id: int,
    unacknowledged_only: bool = True,
    db: Session = Depends(get_db)
):
    """Get temperature alerts"""
    return TemperatureMonitoringService.get_temperature_history(
        db=db,
        venue_id=venue_id,
        alerts_only=True
    )


@router_part2.post("/iot/temperature/alerts/{alert_id}/acknowledge", response_model=SuccessResponse, tags=["V9 - IoT"])
@limiter.limit("30/minute")
async def acknowledge_temperature_alert(
    request: Request,
    alert_id: int,
    acknowledged_by_id: int,
    corrective_action: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Acknowledge a temperature alert"""
    result = TemperatureMonitoringService.acknowledge_temperature_alert(
        db=db,
        log_id=alert_id,
        acknowledged_by=acknowledged_by_id,
        corrective_action=corrective_action
    )
    return SuccessResponse(success=True, message="Alert acknowledged")


@router_part2.get("/iot/haccp/report", response_model=Dict[str, Any], tags=["V9 - IoT"])
@limiter.limit("60/minute")
async def get_haccp_report(
    request: Request,
    venue_id: int,
    start_date: date = Query(default_factory=lambda: date.today() - timedelta(days=7)),
    end_date: date = Query(default_factory=date.today),
    db: Session = Depends(get_db)
):
    """Get HACCP compliance report"""
    return TemperatureMonitoringService.get_haccp_compliance_report(
        db=db,
        venue_id=venue_id,
        start_date=start_date,
        end_date=end_date
    )


# ==================== IOT - POUR METERS ====================

# DUPLICATE: @router_part2.post("/iot/pour", response_model=Dict[str, Any], tags=["V9 - IoT"])
async def record_pour(
    data: PourReading,
    db: Session = Depends(get_db)
):
    """Record pour meter reading"""
    # Get device by serial number to get device_id
    from app.models.advanced_features_v9 import IoTDevice
    device = db.query(IoTDevice).filter(IoTDevice.serial_number == data.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail=f"Pour meter device with ID {data.device_id} not found")

    return PourMeterService.record_pour(
        db=db,
        device_id=device.id,
        product_id=data.product_id,
        poured_amount_ml=Decimal(str(data.actual_ml)),
        expected_amount_ml=Decimal(str(data.expected_ml)),
        staff_id=data.staff_id,
        order_id=data.order_item_id
    )


# DUPLICATE: @router_part2.get("/iot/pour/analytics", response_model=Dict[str, Any], tags=["V9 - IoT"])
async def get_pour_analytics(
    venue_id: int,
    start_date: date = Query(default_factory=lambda: date.today() - timedelta(days=7)),
    end_date: date = Query(default_factory=date.today),
    db: Session = Depends(get_db)
):
    """Get pour accuracy analytics by staff"""
    return PourMeterService.get_pour_analytics(
        db=db,
        venue_id=venue_id,
        start_date=start_date,
        end_date=end_date
    )


# ==================== COMPLIANCE - IMMUTABLE AUDIT ====================

@router_part2.post("/compliance/audit", response_model=AuditLogResponse, tags=["V9 - Compliance"])
@limiter.limit("30/minute")
async def create_audit_log(
    request: Request,
    data: AuditLogCreate,
    venue_id: int,
    db: Session = Depends(get_db)
):
    """Create immutable audit log entry"""
    return ImmutableAuditService.log_action(
        db=db,
        venue_id=venue_id,
        user_id=data.staff_id,
        action_type=data.action,
        entity_type=data.entity_type,
        entity_id=data.entity_id,
        action_details={"old_value": data.old_value, "new_value": data.new_value},
        ip_address=data.ip_address
    )


@router_part2.get("/compliance/audit/verify", response_model=Dict[str, Any], tags=["V9 - Compliance"])
@limiter.limit("60/minute")
async def verify_audit_chain(
    request: Request,
    venue_id: int,
    start_id: Optional[int] = None,
    end_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Verify integrity of audit log chain"""
    return ImmutableAuditService.verify_audit_chain(
        db=db,
        venue_id=venue_id,
        start_id=start_id,
        end_id=end_id
    )


@router_part2.get("/compliance/audit/logs", response_model=List[AuditLogResponse], tags=["V9 - Compliance"])
@limiter.limit("60/minute")
async def get_audit_logs(
    request: Request,
    venue_id: int,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    staff_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get audit logs with filters"""
    return ImmutableAuditService.get_audit_logs(
        db=db,
        venue_id=venue_id,
        action_type=None,
        entity_type=entity_type,
        user_id=staff_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )


# ==================== COMPLIANCE - FISCAL ARCHIVE ====================

@router_part2.post("/compliance/fiscal/archive", response_model=Dict[str, Any], tags=["V9 - Compliance"])
@limiter.limit("30/minute")
async def archive_fiscal_receipt(
    request: Request,
    data: FiscalArchiveCreate,
    venue_id: int,
    fiscal_device_id: str = "default",
    db: Session = Depends(get_db)
):
    """Archive fiscal receipt for long-term storage"""
    return FiscalArchiveService.archive_fiscal_receipt(
        db=db,
        venue_id=venue_id,
        order_id=data.order_id,
        receipt_number=data.receipt_number,
        fiscal_device_id=fiscal_device_id,
        receipt_data={"content": data.receipt_content},
        signature=data.fiscal_signature
    )


@router_part2.get("/compliance/fiscal/archive/{venue_id}", response_model=Dict[str, Any], tags=["V9 - Compliance"])
@limiter.limit("60/minute")
async def get_archived_receipts(
    request: Request,
    venue_id: int,
    receipt_number: Optional[str] = None,
    start_date: date = Query(default_factory=lambda: date.today() - timedelta(days=30)),
    end_date: date = Query(default_factory=date.today),
    db: Session = Depends(get_db)
):
    """Retrieve archived fiscal receipts"""
    return FiscalArchiveService.get_fiscal_archive(
        db=db,
        venue_id=venue_id,
        start_date=start_date,
        end_date=end_date,
        receipt_number=receipt_number
    )


# ==================== COMPLIANCE - NRA EXPORT ====================

@router_part2.post("/compliance/nra/export", response_model=NRAExportResponse, tags=["V9 - Compliance"])
@limiter.limit("30/minute")
async def create_nra_export(
    request: Request,
    data: NRAExportRequest,
    venue_id: int,
    requested_by: int = 1,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """Create NRA (Bulgarian tax authority) export"""
    result = NRAExportService.create_nra_export(
        db=db,
        venue_id=venue_id,
        export_type=data.export_format,
        start_date=data.start_date,
        end_date=data.end_date,
        requested_by=requested_by
    )
    # Generate file in background if background_tasks available
    if background_tasks:
        background_tasks.add_task(generate_nra_file, result.get("id"))
    return result


@router_part2.get("/compliance/nra/exports", response_model=List[NRAExportResponse], tags=["V9 - Compliance"])
@limiter.limit("60/minute")
async def get_nra_exports(
    request: Request,
    venue_id: int,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Get list of NRA exports"""
    return NRAExportService.get_nra_exports(db=db, venue_id=venue_id, limit=limit)


# ==================== COMPLIANCE - AGE VERIFICATION ====================

# DUPLICATE: @router_part2.post("/compliance/age-verification", response_model=Dict[str, Any], tags=["V9 - Compliance"])
async def log_age_verification(
    data: AgeVerificationLog,
    venue_id: int,
    db: Session = Depends(get_db)
):
    """Log age verification for alcohol/tobacco sales"""
    return AgeVerificationService.log_age_verification(
        db=db,
        venue_id=venue_id,
        staff_id=data.verified_by_id,
        order_id=data.order_id,
        verification_method=data.document_type,
        guest_birth_date=data.customer_dob,
        verification_passed=True
    )


# DUPLICATE: @router_part2.get("/compliance/age-verification/report", response_model=Dict[str, Any], tags=["V9 - Compliance"])
async def get_age_verification_report(
    venue_id: int,
    start_date: date = Query(default_factory=lambda: date.today() - timedelta(days=30)),
    end_date: date = Query(default_factory=date.today),
    db: Session = Depends(get_db)
):
    """Get age verification compliance report"""
    return AgeVerificationService.get_age_verification_report(
        db=db,
        venue_id=venue_id,
        start_date=start_date,
        end_date=end_date
    )


# ==================== AI - MODEL MANAGEMENT ====================

# DUPLICATE: @router_part2.post("/ai/models", response_model=AIModelResponse, tags=["V9 - AI & Automation"])
async def register_ai_model(
    data: AIModelRegister,
    venue_id: int,
    db: Session = Depends(get_db)
):
    """Register a new AI model"""
    return AIModelService.register_model(
        db=db,
        venue_id=venue_id,
        model_name=data.model_name,
        model_type=data.model_type,
        model_version=data.version,
        configuration=data.parameters or {},
        description=data.description
    )


# DUPLICATE: @router_part2.post("/ai/models/{model_id}/activate", response_model=SuccessResponse, tags=["V9 - AI & Automation"])
async def activate_ai_model(
    model_id: int,
    db: Session = Depends(get_db)
):
    """Activate an AI model"""
    result = AIModelService.activate_model(db=db, model_id=model_id)
    return SuccessResponse(success=True, message="Model activated")


# DUPLICATE: @router_part2.put("/ai/models/{model_id}/accuracy", response_model=SuccessResponse, tags=["V9 - AI & Automation"])
async def update_model_accuracy(
    model_id: int,
    accuracy_score: float,
    db: Session = Depends(get_db)
):
    """Update model accuracy score"""
    result = AIModelService.update_model_accuracy(db=db, model_id=model_id, accuracy_score=Decimal(str(accuracy_score)))
    return SuccessResponse(success=True, message="Accuracy updated")


# ==================== AI - PREDICTIONS ====================

# DUPLICATE: @router_part2.post("/ai/predictions", response_model=Dict[str, Any], tags=["V9 - AI & Automation"])
async def log_prediction(
    data: PredictionLog,
    db: Session = Depends(get_db)
):
    """Log a prediction from AI model"""
    return PredictionService.log_prediction(
        db=db,
        model_id=data.model_id,
        prediction_type=data.context.get("type", "general") if data.context else "general",
        input_data=data.input_data,
        predicted_value=data.prediction_value,
        confidence_score=Decimal(str(data.confidence_score)),
        target_date=data.context.get("target_date") if data.context else None
    )


# DUPLICATE: @router_part2.post("/ai/predictions/{prediction_id}/actual", response_model=SuccessResponse, tags=["V9 - AI & Automation"])
async def record_actual_value(
    prediction_id: int,
    actual_value: Any,
    db: Session = Depends(get_db)
):
    """Record actual value for prediction accuracy tracking"""
    result = PredictionService.record_actual_value(
        db=db,
        prediction_id=prediction_id,
        actual_value=actual_value
    )
    return SuccessResponse(success=True, message="Actual value recorded")


@router_part2.get("/ai/predictions/accuracy/{model_id}", response_model=Dict[str, Any], tags=["V9 - AI & Automation"])
@limiter.limit("60/minute")
async def get_prediction_accuracy(
    request: Request,
    model_id: int,
    venue_id: int,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get prediction accuracy report for model"""
    start_date = date.today() - timedelta(days=days)
    end_date = date.today()
    return PredictionService.get_prediction_accuracy_report(
        db=db,
        venue_id=venue_id,
        model_id=model_id,
        start_date=start_date,
        end_date=end_date
    )


# ==================== AI - AUTOMATION RULES ====================

@router_part2.post("/ai/automation/rules", response_model=AutomationRuleResponse, tags=["V9 - AI & Automation"])
@limiter.limit("30/minute")
async def create_automation_rule(
    request: Request,
    data: AutomationRuleCreate,
    venue_id: int,
    db: Session = Depends(get_db)
):
    """Create automation rule"""
    return AutomationRuleService.create_automation_rule(
        db=db,
        venue_id=venue_id,
        rule_name=data.rule_name,
        trigger_type=data.trigger_type.value if hasattr(data.trigger_type, 'value') else data.trigger_type,
        trigger_config=data.trigger_config,
        action_type=data.action_type.value if hasattr(data.action_type, 'value') else data.action_type,
        action_config=data.action_config,
        enabled=data.is_active
    )


@router_part2.get("/ai/automation/rules", response_model=List[AutomationRuleResponse], tags=["V9 - AI & Automation"])
@limiter.limit("60/minute")
async def get_automation_rules(
    request: Request,
    venue_id: int,
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """Get all automation rules"""
    return AutomationRuleService.get_automation_rules(db=db, venue_id=venue_id, enabled_only=active_only)


@router_part2.post("/ai/automation/execute", response_model=Dict[str, Any], tags=["V9 - AI & Automation"])
@limiter.limit("30/minute")
async def execute_automations(
    request: Request,
    venue_id: int,
    trigger_type: str,
    trigger_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Check and execute all active automation rules matching trigger"""
    results = AutomationRuleService.check_and_execute_automations(
        db=db,
        venue_id=venue_id,
        trigger_type=trigger_type,
        trigger_data=trigger_data
    )
    return {
        "venue_id": venue_id,
        "trigger_type": trigger_type,
        "executed_count": len(results),
        "results": results
    }


# ==================== AI - MENU OPTIMIZATION ====================

# DUPLICATE: @router_part2.get("/ai/menu-optimization", response_model=Dict[str, Any], tags=["V9 - AI & Automation"])
async def get_menu_optimization_suggestions(
    venue_id: int,
    db: Session = Depends(get_db)
):
    """Get AI-powered menu optimization suggestions"""
    return MenuOptimizationService.get_menu_optimization_suggestions(db=db, venue_id=venue_id)


# ==================== AI - STAFFING RECOMMENDATIONS ====================

@router_part2.get("/ai/staffing", response_model=Dict[str, Any], tags=["V9 - AI & Automation"])
@limiter.limit("60/minute")
async def get_staffing_recommendations(
    request: Request,
    venue_id: int,
    start_date: date = Query(default_factory=date.today),
    days: int = 7,
    db: Session = Depends(get_db)
):
    """Get AI-powered staffing recommendations"""
    return StaffingRecommendationService.get_staffing_recommendations(
        db=db,
        venue_id=venue_id,
        target_date=start_date
    )


# ==================== LEGAL - INCIDENT REPORTS ====================

# DUPLICATE: @router_part2.post("/legal/incidents", response_model=IncidentReportResponse, tags=["V9 - Legal & Risk"])
async def create_incident_report(
    data: IncidentReportCreate,
    venue_id: int,
    db: Session = Depends(get_db)
):
    """Create incident report"""
    return LegalRiskService.create_incident_report(
        db=db,
        venue_id=venue_id,
        reported_by=data.reported_by_id,
        incident_type=data.incident_type.value if hasattr(data.incident_type, 'value') else data.incident_type,
        incident_date=data.occurred_at,
        location=data.location,
        description=data.description,
        severity=data.severity,
        persons_involved=data.involved_parties,
        witnesses=data.witnesses
    )


@router_part2.post("/legal/incidents/{incident_id}/evidence", response_model=SuccessResponse, tags=["V9 - Legal & Risk"])
@limiter.limit("30/minute")
async def add_incident_evidence(
    request: Request,
    incident_id: int,
    data: EvidenceAdd,
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """Add evidence to incident report"""
    file_path = data.file_path
    if file:
        # Save file and get path
        file_path = f"/evidence/{incident_id}/{file.filename}"
    result = LegalRiskService.add_evidence(
        db=db,
        report_id=incident_id,
        evidence_type=data.evidence_type,
        file_path=file_path,
        description=data.description,
        uploaded_by=data.collected_by_id
    )
    return SuccessResponse(success=True, message="Evidence added")


# DUPLICATE: @router_part2.get("/legal/incidents", response_model=List[IncidentReportResponse], tags=["V9 - Legal & Risk"])
async def get_incident_reports(
    venue_id: int,
    status: Optional[str] = None,
    incident_type: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get incident reports"""
    return LegalRiskService.get_incident_reports(
        db=db,
        venue_id=venue_id,
        status=status,
        incident_type=incident_type
    )


@router_part2.put("/legal/incidents/{incident_id}/status", response_model=SuccessResponse, tags=["V9 - Legal & Risk"])
@limiter.limit("30/minute")
async def update_incident_status(
    request: Request,
    incident_id: int,
    status: str,
    updated_by: int,
    notes: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Update incident status"""
    result = LegalRiskService.update_incident_status(
        db=db,
        report_id=incident_id,
        status=status,
        updated_by=updated_by,
        notes=notes
    )
    return SuccessResponse(success=True, message="Status updated")


# ==================== TRAINING ====================

# DUPLICATE: @router_part2.post("/training/modules", response_model=TrainingModuleResponse, tags=["V9 - Training"])
async def create_training_module(
    data: TrainingModuleCreate,
    venue_id: int,
    db: Session = Depends(get_db)
):
    """Create training module"""
    return TrainingService.create_training_module(
        db=db,
        venue_id=venue_id,
        module_name=data.module_name,
        module_type=data.module_type.value if hasattr(data.module_type, 'value') else data.module_type,
        description=data.description,
        content={"url": data.content_url} if data.content_url else {},
        duration_minutes=data.duration_minutes,
        required_roles=data.prerequisites or [],
        passing_score=data.passing_score,
        certification_valid_days=data.expiry_days
    )


# DUPLICATE: @router_part2.get("/training/modules", response_model=List[TrainingModuleResponse], tags=["V9 - Training"])
async def get_training_modules(
    venue_id: int,
    module_type: Optional[str] = None,
    mandatory_only: bool = False,
    db: Session = Depends(get_db)
):
    """Get training modules"""
    return TrainingService.get_training_modules(db=db, venue_id=venue_id, module_type=module_type)


@router_part2.post("/training/complete", response_model=Dict[str, Any], tags=["V9 - Training"])
@limiter.limit("30/minute")
async def complete_training(
    request: Request,
    data: TrainingCompletion,
    db: Session = Depends(get_db)
):
    """Record training completion"""
    # First start the training if not started
    TrainingService.start_training(db=db, staff_id=data.staff_id, module_id=data.module_id)
    # Then complete with score
    # Get the record ID from recent records
    from app.models.advanced_features_v9 import StaffTrainingRecord
    record = db.query(StaffTrainingRecord).filter(
        StaffTrainingRecord.staff_id == data.staff_id,
        StaffTrainingRecord.module_id == data.module_id,
        StaffTrainingRecord.status == "in_progress"
    ).first()
    if record:
        return TrainingService.complete_training(db=db, record_id=record.id, score=data.score)
    return {"message": "Training record not found"}


@router_part2.get("/training/staff/{staff_id}/status", response_model=StaffTrainingStatus, tags=["V9 - Training"])
@limiter.limit("60/minute")
async def get_staff_training_status(
    request: Request,
    staff_id: int,
    venue_id: int,
    db: Session = Depends(get_db)
):
    """Get training status for staff member"""
    return TrainingService.get_staff_training_status(db=db, staff_id=staff_id, venue_id=venue_id)


@router_part2.get("/training/certifications/expiring", response_model=List[Dict[str, Any]], tags=["V9 - Training"])
@limiter.limit("60/minute")
async def get_expiring_certifications(
    request: Request,
    venue_id: int,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get certifications expiring soon"""
    return TrainingService.get_expiring_certifications(db=db, venue_id=venue_id, days_ahead=days)


# ==================== CRISIS MANAGEMENT ====================

# DUPLICATE: @router_part2.post("/crisis/modes", response_model=CrisisModeResponse, tags=["V9 - Crisis Management"])
async def create_crisis_mode(
    data: CrisisModeCreate,
    venue_id: int,
    description: str = "",
    db: Session = Depends(get_db)
):
    """Create crisis mode configuration"""
    return CrisisManagementService.create_crisis_mode(
        db=db,
        venue_id=venue_id,
        mode_name=data.crisis_name,
        mode_type=data.crisis_type.value if hasattr(data.crisis_type, 'value') else data.crisis_type,
        description=description,
        simplified_menu_ids=data.simplified_menu_ids or [],
        margin_protection_percentage=data.margin_protection_percentage,
        operational_changes={},
        auto_activation_conditions=data.auto_activate_conditions
    )


# DUPLICATE: # DUPLICATE: @router_part2.post("/crisis/modes/{mode_id}/activate", response_model=SuccessResponse, tags=["V9 - Crisis Management"])
async def activate_crisis_mode(
    mode_id: int,
    activated_by_id: int,
    reason: str = "Manual activation",
    db: Session = Depends(get_db)
):
    """Activate crisis mode"""
    result = CrisisManagementService.activate_crisis_mode(
        db=db,
        crisis_mode_id=mode_id,
        activated_by=activated_by_id,
        reason=reason
    )
    return SuccessResponse(success=True, message="Crisis mode activated")


@router_part2.post("/crisis/modes/{mode_id}/deactivate", response_model=SuccessResponse, tags=["V9 - Crisis Management"])
@limiter.limit("30/minute")
async def deactivate_crisis_mode(
    request: Request,
    venue_id: int,
    deactivated_by_id: int,
    reason: str = "Manual deactivation",
    db: Session = Depends(get_db)
):
    """Deactivate crisis mode"""
    result = CrisisManagementService.deactivate_crisis_mode(
        db=db,
        venue_id=venue_id,
        deactivated_by=deactivated_by_id,
        reason=reason
    )
    return SuccessResponse(success=True, message="Crisis mode deactivated")


@router_part2.get("/crisis/modes/active", response_model=Optional[CrisisModeResponse], tags=["V9 - Crisis Management"])
@limiter.limit("60/minute")
async def get_active_crisis_mode(
    request: Request,
    venue_id: int,
    db: Session = Depends(get_db)
):
    """Get currently active crisis mode"""
    return CrisisManagementService.get_active_crisis_mode(db=db, venue_id=venue_id)


# ==================== PLATFORM - FEATURE FLAGS ====================

# DUPLICATE: @router_part2.post("/platform/feature-flags", response_model=FeatureFlagResponse, tags=["V9 - Platform"])
async def create_feature_flag(
    data: FeatureFlagCreate,
    venue_id: int,
    db: Session = Depends(get_db)
):
    """Create feature flag"""
    return PlatformService.create_feature_flag(
        db=db,
        venue_id=venue_id,
        feature_key=data.flag_name,
        feature_name=data.flag_name,
        description=data.description or "",
        enabled=data.is_enabled,
        rollout_percentage=data.rollout_percentage,
        conditions=data.conditions
    )


@router_part2.get("/platform/feature-flags/{flag_name}/check", response_model=Dict[str, Any], tags=["V9 - Platform"])
@limiter.limit("60/minute")
async def check_feature_flag(
    request: Request,
    flag_name: str,
    venue_id: int,
    user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Check if feature flag is enabled for user"""
    result = PlatformService.check_feature(
        db=db,
        venue_id=venue_id,
        feature_key=flag_name,
        user_id=user_id
    )
    return {"flag_name": flag_name, "enabled": result.get("enabled", False), "reason": result.get("reason")}


# DUPLICATE: @router_part2.put("/platform/feature-flags/{flag_id}", response_model=SuccessResponse, tags=["V9 - Platform"])
async def update_feature_flag(
    flag_id: int,
    is_enabled: Optional[bool] = None,
    rollout_percentage: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Update feature flag"""
    updates = {}
    if is_enabled is not None:
        updates["enabled"] = is_enabled
    if rollout_percentage is not None:
        updates["rollout_percentage"] = rollout_percentage
    result = PlatformService.update_feature_flag(db=db, flag_id=flag_id, updates=updates)
    return SuccessResponse(success=True, message="Feature flag updated")


# ==================== PLATFORM - WHITE LABEL ====================

# DUPLICATE: @router_part2.post("/platform/white-label", response_model=WhiteLabelResponse, tags=["V9 - Platform"])
async def configure_white_label(
    data: WhiteLabelConfig,
    venue_id: int,
    db: Session = Depends(get_db)
):
    """Configure white-label branding"""
    return PlatformService.set_white_label_config(
        db=db,
        venue_id=venue_id,
        brand_name=data.brand_name,
        logo_url=data.logo_url,
        primary_color=data.primary_color,
        secondary_color=data.secondary_color,
        custom_css=data.custom_css,
        custom_domain=data.custom_domain,
        email_from_name=data.email_from_name,
        email_from_address=data.support_email
    )


@router_part2.get("/platform/white-label/{venue_id}", response_model=WhiteLabelResponse, tags=["V9 - Platform"])
@limiter.limit("60/minute")
async def get_white_label_config(
    request: Request,
    venue_id: int,
    db: Session = Depends(get_db)
):
    """Get white-label configuration"""
    result = PlatformService.get_white_label_config(db=db, venue_id=venue_id)
    if not result:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return result


# ==================== QR - PAY AT TABLE ====================

@router_part2.post("/qr/payment/session", response_model=QRPaymentSessionResponse, tags=["V9 - QR & Self-Service"])
@limiter.limit("30/minute")
async def create_qr_payment_session(
    request: Request,
    data: QRPaymentSessionCreate,
    db: Session = Depends(get_db)
):
    """Create QR payment session"""
    # Get order total from database
    from app.models import Order
    order = db.query(Order).filter(Order.id == data.order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return QRSelfServiceService.create_qr_payment_session(
        db=db,
        venue_id=order.venue_id,
        order_id=data.order_id,
        table_number=str(data.table_id),
        total_amount=order.total or Decimal("0")
    )


@router_part2.get("/qr/payment/session/{session_code}", response_model=QRPaymentSessionResponse, tags=["V9 - QR & Self-Service"])
@limiter.limit("60/minute")
async def get_payment_session(
    request: Request,
    session_code: str,
    db: Session = Depends(get_db)
):
    """Get payment session by code"""
    result = QRSelfServiceService.get_payment_session(db=db, session_code=session_code)
    if not result:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    return result


@router_part2.post("/qr/payment/split", response_model=Dict[str, Any], tags=["V9 - QR & Self-Service"])
@limiter.limit("30/minute")
async def configure_split_payment(
    request: Request,
    data: SplitPaymentConfig,
    db: Session = Depends(get_db)
):
    """Configure split payment for session"""
    return QRSelfServiceService.configure_split_payment(
        db=db,
        session_id=data.session_id,
        split_type=data.split_type,
        split_count=data.split_count
    )


@router_part2.post("/qr/payment/pay", response_model=Dict[str, Any], tags=["V9 - QR & Self-Service"])
@limiter.limit("30/minute")
async def record_payment(
    request: Request,
    data: PaymentRecord,
    db: Session = Depends(get_db)
):
    """Record payment in session"""
    return QRSelfServiceService.record_payment(
        db=db,
        session_id=data.session_id,
        amount=data.amount,
        tip_amount=data.tip_amount or Decimal("0"),
        payment_method=data.payment_method,
        payer_name=f"Payer {data.payer_number}" if data.payer_number else None
    )


# ==================== QR - REORDER ====================

@router_part2.post("/qr/reorder/session", response_model=ReorderSessionResponse, tags=["V9 - QR & Self-Service"])
@limiter.limit("30/minute")
async def create_reorder_session(
    request: Request,
    data: ReorderSessionCreate,
    db: Session = Depends(get_db)
):
    """Create scan-to-reorder session"""
    # Get original order to get venue_id and guest_id
    from app.models import Order
    order = db.query(Order).filter(Order.id == data.original_order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Original order not found")

    return QRSelfServiceService.create_reorder_session(
        db=db,
        venue_id=order.venue_id,
        guest_id=order.customer_id or 0,
        original_order_id=data.original_order_id,
        table_number=str(data.table_id)
    )


@router_part2.get("/qr/reorder/{session_code}/items", response_model=Dict[str, Any], tags=["V9 - QR & Self-Service"])
@limiter.limit("60/minute")
async def get_reorder_items(
    request: Request,
    session_code: str,
    db: Session = Depends(get_db)
):
    """Get available items for reorder"""
    result = QRSelfServiceService.get_reorder_items(db=db, session_code=session_code)
    if not result:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    return result


@router_part2.post("/qr/reorder/confirm", response_model=Dict[str, Any], tags=["V9 - QR & Self-Service"])
@limiter.limit("30/minute")
async def confirm_reorder(
    request: Request,
    data: ReorderConfirm,
    db: Session = Depends(get_db)
):
    """Confirm reorder"""
    return QRSelfServiceService.confirm_reorder(
        db=db,
        session_id=data.session_id,
        selected_item_ids=data.item_ids,
        modifications=getattr(data, 'modifications', None)
    )


# ==================== QR - TABLE QR CODES ====================

@router_part2.post("/qr/table/generate", response_model=TableQRResponse, tags=["V9 - QR & Self-Service"])
@limiter.limit("30/minute")
async def generate_table_qr(
    request: Request,
    data: TableQRGenerate,
    db: Session = Depends(get_db)
):
    """Generate QR code for table"""
    # Get venue_id from table
    from app.models import Table
    table = db.query(Table).filter(Table.id == data.table_id).first()
    venue_id = table.venue_id if table else 1

    return QRSelfServiceService.generate_table_qr(
        venue_id=venue_id,
        table_number=str(data.table_id),
        qr_type=data.qr_type.value if hasattr(data.qr_type, 'value') else data.qr_type
    )


# ==================== KIOSK ====================

# DUPLICATE: @router_part2.get("/kiosk/menu", response_model=KioskMenuResponse, tags=["V9 - QR & Self-Service"])
async def get_kiosk_menu(
    venue_id: int,
    category_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get menu for kiosk display"""
    return QRSelfServiceService.get_kiosk_menu(db=db, venue_id=venue_id)


# DUPLICATE: @router_part2.post("/kiosk/order", response_model=KioskOrderResponse, tags=["V9 - QR & Self-Service"])
async def submit_kiosk_order(
    data: KioskOrderSubmit,
    venue_id: int,
    db: Session = Depends(get_db)
):
    """Submit order from kiosk"""
    return QRSelfServiceService.submit_kiosk_order(
        db=db,
        venue_id=venue_id,
        items=data.items,
        payment_method=data.payment_method,
        guest_name=data.customer_name,
        special_instructions=data.special_instructions
    )


# Background task helpers
async def send_temperature_alert(result: dict):
    """Send temperature alert notification for HACCP compliance"""
    import logging
    logger = logging.getLogger(__name__)

    device_id = result.get("device_id", "unknown")
    temperature = result.get("temperature")
    status = result.get("status", "unknown")
    zone = result.get("zone", "unknown")

    # Log the temperature alert
    if status == "critical":
        logger.critical(
            f"HACCP CRITICAL: Temperature violation in {zone}! "
            f"Device {device_id}: {temperature}°C - Immediate action required"
        )
    elif status == "warning":
        logger.warning(
            f"HACCP WARNING: Temperature approaching limits in {zone}. "
            f"Device {device_id}: {temperature}°C"
        )
    else:
        logger.info(
            f"Temperature reading: Device {device_id} in {zone}: {temperature}°C - {status}"
        )

    # In production, this would:
    # 1. Store alert in TemperatureLog for audit trail
    # 2. Send push notification to kitchen manager
    # 3. Create incident report if critical
    # 4. Log to HACCP compliance system


async def generate_nra_file(export_id: int):
    """Generate NRA export file in background for Bulgarian tax compliance"""
    import logging
    import xml.etree.ElementTree as ET
    from datetime import datetime
    import os
    import hashlib

    logger = logging.getLogger(__name__)

    logger.info(f"Starting NRA export file generation for export_id: {export_id}")

    try:
        from app.db.session import SessionLocal, get_db
        from app.models import Order, OrderItem, Venue
        from app.models.advanced_features_v9 import NRAExportLog

        db = SessionLocal()

        try:
            # Get export record
            export_record = db.query(NRAExportLog).filter(NRAExportLog.id == export_id).first()
            if not export_record:
                raise ValueError(f"Export record {export_id} not found")

            venue = db.query(Venue).filter(Venue.id == export_record.venue_id).first()
            if not venue:
                raise ValueError(f"Venue {export_record.venue_id} not found")

            venue_name = venue.name
            venue_vat = None
            if hasattr(venue, 'tax_id') and venue.tax_id:
                venue_vat = venue.tax_id
            elif hasattr(venue, 'vat_number') and venue.vat_number:
                venue_vat = venue.vat_number
            elif hasattr(venue, 'eik') and venue.eik:
                venue_vat = venue.eik

            if not venue_vat:
                raise ValueError(
                    f"Venue {venue.name} does not have a tax ID (EIK/BULSTAT) configured. "
                    "Please configure the venue's tax_id before generating NRA exports."
                )

            # Query fiscal transactions for the period
            orders = db.query(Order).filter(
                Order.created_at >= export_record.period_start,
                Order.created_at <= export_record.period_end,
                Order.payment_status == 'paid'
            ).all()

            # Create NRA XML structure (Bulgarian NRA AUDIT.XML format)
            root = ET.Element("AUDIT")
            root.set("xmlns", "http://www.nra.bg/schemas/audit")
            root.set("version", "2.0")

            # Header section
            header = ET.SubElement(root, "HEADER")
            ET.SubElement(header, "EIKPOD").text = venue_vat
            ET.SubElement(header, "COMPANY_NAME").text = venue_name
            ET.SubElement(header, "PERIOD_START").text = export_record.period_start.strftime("%Y-%m-%d")
            ET.SubElement(header, "PERIOD_END").text = export_record.period_end.strftime("%Y-%m-%d")
            ET.SubElement(header, "EXPORT_DATE").text = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            ET.SubElement(header, "EXPORT_TIME").text = datetime.now(timezone.utc).strftime("%H:%M:%S")

            # Transactions section
            transactions = ET.SubElement(root, "TRANSACTIONS")

            # VAT totals
            vat_totals = {"20": 0.0, "9": 0.0, "0": 0.0}
            total_amount = 0.0
            total_vat = 0.0

            for order in orders:
                transaction = ET.SubElement(transactions, "TRANSACTION")

                # UNP - Unique sale number
                unp = f"{venue_vat[:9]}-{order.id:010d}-{order.created_at.strftime('%Y%m%d%H%M%S')}"
                ET.SubElement(transaction, "UNP").text = unp

                # Transaction details
                ET.SubElement(transaction, "DATE").text = order.created_at.strftime("%Y-%m-%d")
                ET.SubElement(transaction, "TIME").text = order.created_at.strftime("%H:%M:%S")
                ET.SubElement(transaction, "ORDER_NUMBER").text = order.order_number or str(order.id)
                ET.SubElement(transaction, "OPERATOR_CODE").text = str(order.waiter_id or 1)

                # Payment method
                payment_type = "1" if order.payment_method == "cash" else "2"  # 1=cash, 2=card
                ET.SubElement(transaction, "PAYMENT_TYPE").text = payment_type

                # Items
                items_elem = ET.SubElement(transaction, "ITEMS")
                order_total = 0.0

                order_items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
                for oi in order_items:
                    item = ET.SubElement(items_elem, "ITEM")
                    ET.SubElement(item, "NAME").text = str(oi.menu_item_id)
                    ET.SubElement(item, "QUANTITY").text = str(oi.quantity)
                    ET.SubElement(item, "UNIT_PRICE").text = f"{oi.unit_price:.2f}"
                    ET.SubElement(item, "SUBTOTAL").text = f"{oi.subtotal:.2f}"

                    # Standard VAT rate 20% for Bulgaria
                    vat_rate = "20"
                    vat_amount = oi.subtotal * 0.20 / 1.20
                    ET.SubElement(item, "VAT_RATE").text = vat_rate
                    ET.SubElement(item, "VAT_AMOUNT").text = f"{vat_amount:.2f}"

                    vat_totals[vat_rate] += vat_amount
                    order_total += oi.subtotal

                # Transaction totals
                ET.SubElement(transaction, "TOTAL").text = f"{order.total:.2f}"
                ET.SubElement(transaction, "TIP").text = f"{order.tip_amount:.2f}"
                total_amount += order.total

            # Summary section
            summary = ET.SubElement(root, "SUMMARY")
            ET.SubElement(summary, "TOTAL_TRANSACTIONS").text = str(len(orders))
            ET.SubElement(summary, "TOTAL_AMOUNT").text = f"{total_amount:.2f}"

            # VAT breakdown
            vat_summary = ET.SubElement(summary, "VAT_SUMMARY")
            for rate, amount in vat_totals.items():
                vat_line = ET.SubElement(vat_summary, "VAT_LINE")
                ET.SubElement(vat_line, "RATE").text = rate
                ET.SubElement(vat_line, "AMOUNT").text = f"{amount:.2f}"
                total_vat += amount

            ET.SubElement(summary, "TOTAL_VAT").text = f"{total_vat:.2f}"

            # Generate XML string
            xml_string = ET.tostring(root, encoding='unicode', method='xml')
            xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_string

            # Calculate checksum
            checksum = hashlib.sha256(xml_content.encode('utf-8')).hexdigest()

            # Save file
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"NRA_EXPORT_{export_id}_{timestamp}.xml"

            # Save to exports directory
            export_dir = os.path.join(os.getcwd(), "exports", "nra")
            os.makedirs(export_dir, exist_ok=True)
            file_path = os.path.join(export_dir, filename)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(xml_content)

            # Update export record
            export_record.file_name = filename
            export_record.file_path = file_path
            export_record.file_size_bytes = len(xml_content.encode('utf-8'))
            export_record.file_checksum = checksum
            export_record.status = "generated"
            export_record.generated_at = datetime.now(timezone.utc)

            db.commit()

            logger.info(f"NRA export file generated: {filename} ({len(orders)} transactions, {total_amount:.2f} BGN)")

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Failed to generate NRA export {export_id}: {str(e)}")
        raise

# Alias for dynamic module loader
router = router_part2

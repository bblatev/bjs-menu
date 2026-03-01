"""V9 IoT & Compliance"""
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
    start_date: Optional[date] = Query(None, description="Start date (defaults to 30 days ago)"),
    end_date: Optional[date] = Query(None, description="End date (defaults to today)"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Generate HACCP compliance report for inspections"""
    if start_date is None:
        start_date = date.today() - timedelta(days=30)
    if end_date is None:
        end_date = date.today()
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
    start_date: Optional[date] = Query(None, description="Start date (defaults to 30 days ago)"),
    end_date: Optional[date] = Query(None, description="End date (defaults to today)"),
    product_id: Optional[int] = None,
    staff_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get pour accuracy analytics"""
    if start_date is None:
        start_date = date.today() - timedelta(days=30)
    if end_date is None:
        end_date = date.today()
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
    start_date: Optional[date] = Query(None, description="Start date (defaults to 30 days ago)"),
    end_date: Optional[date] = Query(None, description="End date (defaults to today)"),
    receipt_number: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get fiscal archive for a period"""
    if start_date is None:
        start_date = date.today() - timedelta(days=30)
    if end_date is None:
        end_date = date.today()
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
    start_date: Optional[date] = Query(None, description="Start date (defaults to 30 days ago)"),
    end_date: Optional[date] = Query(None, description="End date (defaults to today)"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get age verification report for compliance"""
    if start_date is None:
        start_date = date.today() - timedelta(days=30)
    if end_date is None:
        end_date = date.today()
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
    from app.services.compliance_service import ComplianceService
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
    from app.services.compliance_service import ComplianceService
    return ComplianceService.generate_data_export(db, venue_id, customer_id)



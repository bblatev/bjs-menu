"""V9 Operations (permissions, terminals, safe mode, cash variance)"""
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



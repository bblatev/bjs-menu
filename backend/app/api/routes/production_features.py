"""
Production Features API Endpoints

Exposes new production-ready features:
- Feature flags status
- Payment ledger operations
- Offline sync operations
- Terminal status
- Anti-theft risk analysis
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.db.session import get_db
from app.core.rbac import get_current_user
from app.models import StaffUser
from app.core.feature_flags import get_flags, is_enabled
from app.core.rbac_policy import RBACPolicy, Permission, require_permission
from app.core.rate_limit import limiter

router = APIRouter()


# ============================================================================
# FEATURE FLAGS ENDPOINTS
# ============================================================================

@router.get("/")
@limiter.limit("60/minute")
async def get_production_features_root(request: Request, db: Session = Depends(get_db)):
    """Production features overview."""
    return {"module": "production-features", "status": "active", "endpoints": ["/flags", "/ledger/status", "/ledger/integrity", "/sync/status/{terminal_id}"]}


@router.get("/flags")
@limiter.limit("60/minute")
async def get_feature_flags(
    request: Request,
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Get current feature flag states.

    Returns all feature flags and their current status.
    """
    flags = get_flags()
    return {
        "flags": flags.get_all(),

        "enabled_count": len(flags.get_enabled()),
        "total_count": len(flags.REGISTRY),
    }


@router.get("/flags/{flag_name}")
@limiter.limit("60/minute")
async def get_feature_flag(
    request: Request,
    flag_name: str,
    current_user: StaffUser = Depends(get_current_user)
):
    """Get specific feature flag status."""
    flags = get_flags()

    if flag_name not in flags.REGISTRY:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature flag '{flag_name}' not found"
        )

    return {
        "flag": flag_name,
        "enabled": flags.is_enabled(flag_name),
        "description": flags.REGISTRY.get(flag_name),
    }


# ============================================================================
# PAYMENT LEDGER ENDPOINTS
# ============================================================================

@router.get("/ledger/status")
@limiter.limit("60/minute")
async def get_ledger_status(
    request: Request,
    current_user: StaffUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get payment ledger status and statistics."""
    if not is_enabled("LEDGER_ENABLED"):
        return {"status": "disabled", "message": "Ledger feature is not enabled"}

    from app.services.payment_ledger_service import PaymentLedgerService

    service = PaymentLedgerService(db)
    venue_id = current_user.venue_id

    # Get today's balance
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    return {
        "status": "active",
        "ledger_enabled": True,
        "idempotency_enabled": is_enabled("IDEMPOTENCY_KEYS_ENABLED"),
        "cash_variance_alerts": is_enabled("CASH_VARIANCE_ALERTS"),
        "today_balance_cents": service.get_ledger_balance(
            venue_id, start_date=today
        ),
    }


@router.get("/ledger/integrity")
@limiter.limit("60/minute")
async def verify_ledger_integrity(
    request: Request,
    current_user: StaffUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify ledger integrity for current venue."""
    if not is_enabled("LEDGER_ENABLED"):
        return {"status": "disabled"}

    from app.services.payment_ledger_service import PaymentLedgerService

    service = PaymentLedgerService(db)
    return service.verify_ledger_integrity(current_user.venue_id)


@router.post("/ledger/record")
@limiter.limit("30/minute")
async def record_payment(
    request: Request,
    amount: float,
    payment_method: str,
    order_id: Optional[int] = None,
    idempotency_key: Optional[str] = None,
    description: Optional[str] = None,
    current_user: StaffUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Record a payment to the ledger.

    Requires LEDGER_ENABLED feature flag.
    """
    if not is_enabled("LEDGER_ENABLED"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ledger feature is not enabled"
        )

    from app.services.payment_ledger_service import PaymentLedgerService

    service = PaymentLedgerService(db)
    entry = service.record_payment(
        venue_id=current_user.venue_id,
        amount=Decimal(str(amount)),
        payment_method=payment_method,
        order_id=order_id,
        staff_user_id=current_user.id,
        idempotency_key=idempotency_key,
        description=description,
    )

    if entry:
        return {
            "success": True,
            "entry_id": entry.id,
            "entry_number": entry.entry_number,
            "amount_cents": entry.amount_cents,
        }

    return {"success": False, "message": "Ledger not active"}


# ============================================================================
# OFFLINE SYNC ENDPOINTS
# ============================================================================

@router.get("/sync/status/{terminal_id}")
@limiter.limit("60/minute")
async def get_terminal_sync_status(
    request: Request,
    terminal_id: str,
    current_user: StaffUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get sync status for a terminal."""
    if not is_enabled("OFFLINE_SYNC_ENABLED"):
        return {"status": "disabled"}

    from app.services.offline_sync_service import OfflineSyncService

    service = OfflineSyncService(db)
    return service.get_terminal_status(current_user.venue_id, terminal_id)


@router.post("/sync/heartbeat")
@limiter.limit("30/minute")
async def record_terminal_heartbeat(
    request: Request,
    terminal_id: str,
    is_online: bool = True,
    current_user: StaffUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Record terminal heartbeat."""
    if not is_enabled("OFFLINE_SYNC_ENABLED"):
        return {"status": "disabled"}

    from app.services.offline_sync_service import OfflineSyncService

    service = OfflineSyncService(db)
    service.record_heartbeat(current_user.venue_id, terminal_id, is_online)

    return {"success": True, "terminal_id": terminal_id}


@router.get("/sync/menu-version")
@limiter.limit("60/minute")
async def get_current_menu_version(
    request: Request,
    current_user: StaffUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current menu version for offline sync."""
    if not is_enabled("MENU_VERSIONING_ENABLED"):
        return {"status": "disabled"}

    from app.services.offline_sync_service import OfflineSyncService

    service = OfflineSyncService(db)
    version = service.get_menu_version(current_user.venue_id)

    if version:
        return {
            "version_number": version.version_number,
            "version_hash": version.version_hash,
            "created_at": version.created_at.isoformat() if version.created_at else None,
        }

    return {"version_number": 0, "message": "No menu version found"}


@router.post("/sync/check-menu-update")
@limiter.limit("30/minute")
async def check_menu_update(
    request: Request,
    terminal_version: int,
    current_user: StaffUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check if terminal needs menu update."""
    if not is_enabled("MENU_VERSIONING_ENABLED"):
        return {"needs_update": False, "status": "disabled"}

    from app.services.offline_sync_service import OfflineSyncService

    service = OfflineSyncService(db)
    return service.check_menu_update(current_user.venue_id, terminal_version)


# ============================================================================
# ANTI-THEFT ENDPOINTS
# ============================================================================

@router.get("/security/risk-analysis/{staff_user_id}")
@limiter.limit("60/minute")
async def analyze_staff_risk(
    request: Request,
    staff_user_id: int,
    period_days: int = 30,
    current_user: StaffUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Analyze risk score for a staff member.

    Requires manager or admin role.
    """
    if current_user.role not in ["owner", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )

    if not is_enabled("STAFF_RISK_SCORING"):
        return {"status": "disabled"}

    from app.services.anti_theft_service import AntiTheftService

    service = AntiTheftService(db)
    return service.analyze_staff_risk(
        current_user.venue_id,
        staff_user_id,
        period_days
    )


@router.post("/security/evidence-packet")
@limiter.limit("30/minute")
async def generate_evidence_packet(
    request: Request,
    staff_user_id: int,
    incident_type: str,
    start_date: str,
    end_date: str,
    current_user: StaffUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate evidence packet for investigation.

    Requires admin role.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    if not is_enabled("EVIDENCE_PACKETS"):
        return {"status": "disabled"}

    from app.services.anti_theft_service import AntiTheftService

    service = AntiTheftService(db)

    try:
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use ISO format (YYYY-MM-DD)"
        )

    return service.generate_evidence_packet(
        current_user.venue_id,
        staff_user_id,
        incident_type,
        start,
        end
    )


# ============================================================================
# RBAC ENDPOINTS
# ============================================================================

@router.get("/rbac/permissions")
@limiter.limit("60/minute")
async def get_user_permissions(
    request: Request,
    current_user: StaffUser = Depends(get_current_user)
):
    """Get current user's permissions."""
    if not is_enabled("RBAC_V2_ENABLED"):
        return {
            "status": "legacy",
            "role": current_user.role,
            "message": "RBAC V2 not enabled"
        }

    permissions = RBACPolicy.get_role_permissions(current_user.role)

    return {
        "role": current_user.role,
        "permissions": [p.value for p in permissions],
        "permission_count": len(permissions),
    }


@router.get("/rbac/check/{permission}")
@limiter.limit("60/minute")
async def check_permission(
    request: Request,
    permission: str,
    current_user: StaffUser = Depends(get_current_user)
):
    """Check if current user has specific permission."""
    if not is_enabled("RBAC_V2_ENABLED"):
        return {"has_permission": True, "status": "legacy"}

    try:
        perm = Permission(permission)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid permission: {permission}"
        )

    has_perm = RBACPolicy.has_permission(current_user.role, perm)

    return {
        "permission": permission,
        "has_permission": has_perm,
        "role": current_user.role,
    }


# ============================================================================
# CASH VARIANCE ENDPOINTS
# ============================================================================

@router.post("/cash/variance")
@limiter.limit("30/minute")
async def record_cash_variance(
    request: Request,
    expected_cents: int,
    actual_cents: int,
    shift_id: Optional[int] = None,
    drawer_id: Optional[str] = None,
    current_user: StaffUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Record a cash variance (drawer count discrepancy).

    Automatically generates alerts for significant variances.
    """
    if not is_enabled("CASH_VARIANCE_ALERTS"):
        return {"status": "disabled"}

    from app.services.payment_ledger_service import PaymentLedgerService

    service = PaymentLedgerService(db)
    result = service.record_cash_variance(
        venue_id=current_user.venue_id,
        expected_cents=expected_cents,
        actual_cents=actual_cents,
        staff_user_id=current_user.id,
        shift_id=shift_id,
        drawer_id=drawer_id,
    )

    if result:
        entry, alert = result
        return {
            "success": True,
            "variance_cents": actual_cents - expected_cents,
            "alert_created": True,
            "alert_severity": alert.severity,
        }

    return {
        "success": True,
        "variance_cents": actual_cents - expected_cents,
        "alert_created": False,
        "message": "Variance within acceptable threshold"
    }


@router.get("/cash/alerts")
@limiter.limit("60/minute")
async def get_cash_variance_alerts(
    request: Request,
    resolved: Optional[bool] = None,
    severity: Optional[str] = None,
    limit: int = 50,
    current_user: StaffUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get cash variance alerts for venue."""
    if not is_enabled("CASH_VARIANCE_ALERTS"):
        return {"status": "disabled", "alerts": []}

    from app.models.payment_ledger import CashVarianceAlert

    query = db.query(CashVarianceAlert).filter(
        CashVarianceAlert.venue_id == current_user.venue_id
    )

    if resolved is not None:
        query = query.filter(CashVarianceAlert.is_resolved == resolved)

    if severity:
        query = query.filter(CashVarianceAlert.severity == severity)

    alerts = query.order_by(CashVarianceAlert.created_at.desc()).limit(limit).all()

    return {
        "alerts": [
            {
                "id": a.id,
                "business_date": a.business_date.isoformat() if a.business_date else None,
                "expected_cents": a.expected_amount_cents,
                "actual_cents": a.actual_amount_cents,
                "variance_cents": a.variance_cents,
                "severity": a.severity,
                "is_resolved": a.is_resolved,
            }
            for a in alerts
        ],
        "count": len(alerts),
    }

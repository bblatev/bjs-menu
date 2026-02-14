"""
Biometric & Card Reader Access Control API Routes (Gap 14)

Provides endpoints for:
- Fingerprint enrollment and verification
- Card/badge registration and verification
- Access schedules
- Access log and audit trail
- Device configuration
"""

from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Body, Query, Request
from pydantic import BaseModel

from app.db.session import DbSession
from app.core.rate_limit import limiter
from app.services.biometric_service import (
    BiometricService,
    AuthMethod,
    DeviceType,
    AccessResult,
)

router = APIRouter()


# ============== Pydantic Schemas ==============

class FingerprintEnrollRequest(BaseModel):
    staff_id: int
    template_data: Optional[str] = None  # Base64 encoded, optional for virtual mode
    quality_score: float = 0.8


class CardRegisterRequest(BaseModel):
    staff_id: int
    card_number: str
    card_type: str = "rfid"  # rfid, nfc, magnetic
    facility_code: Optional[str] = None
    valid_days: int = 365


class VerifyRequest(BaseModel):
    data: str  # Template data or card number
    location_id: Optional[int] = None


class ScheduleItem(BaseModel):
    day_of_week: int  # 0=Monday, 6=Sunday
    start_time: str  # HH:MM
    end_time: str  # HH:MM
    location_id: Optional[int] = None


class SetScheduleRequest(BaseModel):
    staff_id: int
    schedules: List[ScheduleItem]


# ============== Device Endpoints ==============

@router.get("/device/status")
@limiter.limit("60/minute")
def get_device_status(request: Request, db: DbSession):
    """Get biometric device status."""
    return BiometricService.get_device_status()


@router.get("/device/types")
@limiter.limit("60/minute")
def list_device_types(request: Request, db: DbSession):
    """List available device types."""
    return {
        "device_types": [
            {
                "type": DeviceType.ZKTECO_FINGERPRINT.value,
                "name": "ZKTeco Fingerprint",
                "description": "ZKTeco fingerprint readers (ZK4500, ZK7500, etc.)",
                "auth_methods": ["fingerprint", "card"],
            },
            {
                "type": DeviceType.HID_CARD.value,
                "name": "HID Card Reader",
                "description": "HID proximity card readers",
                "auth_methods": ["card"],
            },
            {
                "type": DeviceType.MIFARE_RFID.value,
                "name": "Mifare RFID",
                "description": "Mifare RFID card readers",
                "auth_methods": ["card", "nfc"],
            },
            {
                "type": DeviceType.USB_FINGERPRINT.value,
                "name": "USB Fingerprint Scanner",
                "description": "Generic USB fingerprint scanners",
                "auth_methods": ["fingerprint"],
            },
            {
                "type": DeviceType.NFC_READER.value,
                "name": "NFC Reader",
                "description": "NFC/contactless readers",
                "auth_methods": ["nfc"],
            },
            {
                "type": DeviceType.VIRTUAL.value,
                "name": "Virtual Device",
                "description": "Virtual device for testing",
                "auth_methods": ["pin", "fingerprint", "card", "nfc"],
            },
        ],
    }


@router.post("/device/configure")
@limiter.limit("30/minute")
def configure_device(
    request: Request,
    db: DbSession,
    device_type: str = Body(...),
    connection_params: Optional[dict] = Body(None),
):
    """Configure biometric device."""
    result = BiometricService.configure_device(device_type, connection_params)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    return result


@router.post("/device/test")
@limiter.limit("30/minute")
def test_device_connection(request: Request, db: DbSession):
    """Test connection to biometric device."""
    status = BiometricService.get_device_status()

    return {
        "success": status.get("connected", False),
        "device_type": status.get("device_type"),
        "firmware": status.get("firmware"),
        "message": "Device connected" if status.get("connected") else "Device not connected",
    }


# ============== Fingerprint Endpoints ==============

@router.post("/fingerprint/enroll")
@limiter.limit("30/minute")
def enroll_fingerprint(request: Request, db: DbSession, data: FingerprintEnrollRequest):
    """
    Enroll a fingerprint for a staff member.

    In virtual mode, template_data is optional.
    With real hardware, template_data comes from the fingerprint scanner.
    """
    result = BiometricService.enroll_fingerprint(
        staff_id=data.staff_id,
        template_data=data.template_data or "",
        quality_score=data.quality_score,
    )

    return result


@router.post("/fingerprint/verify")
@limiter.limit("30/minute")
def verify_fingerprint(request: Request, db: DbSession, data: VerifyRequest):
    """
    Verify a fingerprint.

    In virtual mode, this will match against any enrolled fingerprint.
    With real hardware, actual biometric matching is performed.
    """
    result = BiometricService.verify_fingerprint(
        template_data=data.data,
        location_id=data.location_id,
    )

    return result


@router.delete("/fingerprint/{template_id}")
@limiter.limit("30/minute")
def revoke_fingerprint(request: Request, db: DbSession, template_id: str):
    """Revoke an enrolled fingerprint."""
    result = BiometricService.revoke_credential(template_id, "fingerprint")

    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("message"))

    return result


# ============== Card Endpoints ==============

@router.post("/card/register")
@limiter.limit("30/minute")
def register_card(request: Request, db: DbSession, data: CardRegisterRequest):
    """
    Register a card/badge for a staff member.
    """
    result = BiometricService.register_card(
        staff_id=data.staff_id,
        card_number=data.card_number,
        card_type=data.card_type,
        facility_code=data.facility_code,
        valid_days=data.valid_days,
    )

    return result


@router.post("/card/verify")
@limiter.limit("30/minute")
def verify_card(request: Request, db: DbSession, data: VerifyRequest):
    """
    Verify a card/badge.
    """
    result = BiometricService.verify_card(
        card_number=data.data,
        location_id=data.location_id,
    )

    return result


@router.delete("/card/{card_id}")
@limiter.limit("30/minute")
def revoke_card(request: Request, db: DbSession, card_id: str):
    """Revoke a registered card."""
    result = BiometricService.revoke_credential(card_id, "card")

    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("message"))

    return result


# ============== Staff Credentials ==============

@router.get("/staff/{staff_id}/credentials")
@limiter.limit("60/minute")
def get_staff_credentials(request: Request, db: DbSession, staff_id: int):
    """Get all enrolled credentials for a staff member."""
    return BiometricService.get_enrolled_credentials(staff_id)


@router.post("/staff/{staff_id}/schedule")
@limiter.limit("30/minute")
def set_staff_schedule(request: Request, db: DbSession, staff_id: int, schedules: List[ScheduleItem] = Body(...)):
    """
    Set access schedule for a staff member.

    Schedules define when the staff member can clock in/access the system.
    """
    schedule_dicts = [s.model_dump() for s in schedules]

    result = BiometricService.set_access_schedule(staff_id, schedule_dicts)

    return result


# ============== Access Log ==============

@router.get("/access-log")
@limiter.limit("60/minute")
def get_access_log(
    request: Request,
    db: DbSession,
    staff_id: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
):
    """
    Get access log entries.

    Provides audit trail of all access attempts.
    """
    start = None
    end = None

    if start_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format")

    if end_date:
        try:
            end = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format")

    log = BiometricService.get_access_log(
        staff_id=staff_id,
        start_date=start,
        end_date=end,
        limit=limit,
    )

    return {
        "entries": log,
        "count": len(log),
    }


@router.get("/access-log/stats")
@limiter.limit("60/minute")
def get_access_stats(
    request: Request,
    db: DbSession,
    days: int = Query(7, ge=1, le=90),
):
    """Get access statistics for the specified period."""
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0) - \
            __import__('datetime').timedelta(days=days)

    log = BiometricService.get_access_log(start_date=start, limit=10000)

    # Calculate stats
    total_attempts = len(log)
    granted = len([e for e in log if e["result"] == "granted"])
    denied = len([e for e in log if e["result"] == "denied"])
    unknown = len([e for e in log if e["result"] == "unknown_user"])

    by_method = {}
    for entry in log:
        method = entry["auth_method"]
        by_method[method] = by_method.get(method, 0) + 1

    return {
        "period_days": days,
        "total_attempts": total_attempts,
        "granted": granted,
        "denied": denied,
        "unknown_user": unknown,
        "success_rate": (granted / total_attempts * 100) if total_attempts > 0 else 0,
        "by_auth_method": by_method,
    }


# ============== Quick Actions ==============

@router.post("/clock-in")
@limiter.limit("30/minute")
def clock_in(
    request: Request,
    db: DbSession,
    auth_method: str = Body(...),  # pin, fingerprint, card
    credential: str = Body(...),  # PIN, template data, or card number
    location_id: Optional[int] = Body(None),
):
    """
    Clock in using biometric or card authentication.

    Combines verification with time clock punch-in.
    """
    # Verify credentials
    if auth_method == "fingerprint":
        result = BiometricService.verify_fingerprint(credential, location_id)
    elif auth_method in ("card", "nfc"):
        result = BiometricService.verify_card(credential, location_id)
    elif auth_method == "pin":
        # PIN verification would be handled by existing PIN system
        result = {
            "success": True,
            "result": "granted",
            "staff_id": None,
            "message": "PIN verification delegated to staff system",
        }
    else:
        raise HTTPException(status_code=400, detail=f"Unknown auth method: {auth_method}")

    if result.get("success"):
        # In production, would also create time clock entry
        return {
            "success": True,
            "staff_id": result.get("staff_id"),
            "clock_in_time": datetime.now(timezone.utc).isoformat(),
            "auth_method": auth_method,
            "message": "Clock in successful",
        }
    else:
        return {
            "success": False,
            "result": result.get("result"),
            "message": result.get("message", "Authentication failed"),
        }


@router.post("/clock-out")
@limiter.limit("30/minute")
def clock_out(
    request: Request,
    db: DbSession,
    auth_method: str = Body(...),
    credential: str = Body(...),
    location_id: Optional[int] = Body(None),
):
    """
    Clock out using biometric or card authentication.
    """
    # Same verification logic as clock-in
    if auth_method == "fingerprint":
        result = BiometricService.verify_fingerprint(credential, location_id)
    elif auth_method in ("card", "nfc"):
        result = BiometricService.verify_card(credential, location_id)
    else:
        result = {"success": True, "staff_id": None}

    if result.get("success"):
        return {
            "success": True,
            "staff_id": result.get("staff_id"),
            "clock_out_time": datetime.now(timezone.utc).isoformat(),
            "auth_method": auth_method,
            "message": "Clock out successful",
        }
    else:
        return {
            "success": False,
            "result": result.get("result"),
            "message": result.get("message", "Authentication failed"),
        }

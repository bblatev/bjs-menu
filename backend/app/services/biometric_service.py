"""
Biometric & Card Reader Access Control Service (Gap 14)

This service provides an abstraction layer for biometric authentication:
- Fingerprint reader integration
- Card/badge reader integration (RFID, NFC, magnetic stripe)
- Multi-factor authentication support
- Access logging and audit trail

Supported device types (for future hardware integration):
- ZKTeco fingerprint readers
- HID card readers
- Mifare RFID readers
- Generic USB fingerprint scanners
- Virtual mode for testing

This foundation can be extended with actual hardware drivers.
"""

import os
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import base64


class AuthMethod(str, Enum):
    """Authentication methods."""
    PIN = "pin"
    FINGERPRINT = "fingerprint"
    CARD = "card"
    NFC = "nfc"
    FACE = "face"
    COMBINED = "combined"  # Multi-factor


class DeviceType(str, Enum):
    """Supported device types."""
    ZKTECO_FINGERPRINT = "zkteco_fingerprint"
    HID_CARD = "hid_card"
    MIFARE_RFID = "mifare_rfid"
    USB_FINGERPRINT = "usb_fingerprint"
    NFC_READER = "nfc_reader"
    VIRTUAL = "virtual"


class AccessResult(str, Enum):
    """Access attempt results."""
    GRANTED = "granted"
    DENIED = "denied"
    DEVICE_ERROR = "device_error"
    TIMEOUT = "timeout"
    UNKNOWN_USER = "unknown_user"
    DISABLED_USER = "disabled_user"
    OUTSIDE_SCHEDULE = "outside_schedule"


@dataclass
class BiometricTemplate:
    """Biometric template data."""
    template_id: str
    staff_id: int
    auth_method: AuthMethod
    template_data: str  # Base64 encoded template
    quality_score: float
    created_at: datetime
    device_type: DeviceType
    is_active: bool = True


@dataclass
class CardCredential:
    """Card/badge credential."""
    card_id: str
    card_number: str
    staff_id: int
    card_type: str  # rfid, nfc, magnetic
    facility_code: Optional[str] = None
    is_active: bool = True
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None


@dataclass
class AccessAttempt:
    """Access attempt log entry."""
    attempt_id: str
    timestamp: datetime
    staff_id: Optional[int]
    auth_method: AuthMethod
    device_id: str
    result: AccessResult
    location_id: Optional[int] = None
    details: Optional[str] = None


@dataclass
class AccessSchedule:
    """Access schedule for staff."""
    staff_id: int
    day_of_week: int  # 0=Monday, 6=Sunday
    start_time: str  # HH:MM
    end_time: str  # HH:MM
    location_id: Optional[int] = None


class BiometricService:
    """Service for biometric and card reader access control."""

    # Simulated storage (in production, would use database)
    _templates: Dict[str, BiometricTemplate] = {}
    _cards: Dict[str, CardCredential] = {}
    _access_log: List[AccessAttempt] = []
    _schedules: Dict[int, List[AccessSchedule]] = {}

    # Device configuration
    _active_device: DeviceType = DeviceType.VIRTUAL
    _device_status: Dict[str, Any] = {
        "connected": True,
        "last_seen": datetime.utcnow(),
        "firmware": "1.0.0-virtual",
    }

    @classmethod
    def get_device_status(cls) -> Dict[str, Any]:
        """Get current device status."""
        return {
            "device_type": cls._active_device.value,
            "connected": cls._device_status.get("connected", False),
            "last_seen": cls._device_status.get("last_seen", datetime.utcnow()).isoformat(),
            "firmware": cls._device_status.get("firmware", "unknown"),
            "supported_methods": cls._get_supported_methods(),
        }

    @classmethod
    def _get_supported_methods(cls) -> List[str]:
        """Get supported auth methods for current device."""
        method_map = {
            DeviceType.ZKTECO_FINGERPRINT: [AuthMethod.FINGERPRINT, AuthMethod.CARD],
            DeviceType.HID_CARD: [AuthMethod.CARD],
            DeviceType.MIFARE_RFID: [AuthMethod.CARD, AuthMethod.NFC],
            DeviceType.USB_FINGERPRINT: [AuthMethod.FINGERPRINT],
            DeviceType.NFC_READER: [AuthMethod.NFC],
            DeviceType.VIRTUAL: [AuthMethod.PIN, AuthMethod.FINGERPRINT, AuthMethod.CARD, AuthMethod.NFC],
        }
        return [m.value for m in method_map.get(cls._active_device, [])]

    @classmethod
    def enroll_fingerprint(
        cls,
        staff_id: int,
        template_data: str,
        quality_score: float = 0.8,
    ) -> Dict[str, Any]:
        """
        Enroll a fingerprint template for a staff member.

        In production, template_data would come from actual fingerprint scanner.
        """
        template_id = f"FP-{staff_id}-{secrets.token_hex(4)}"

        template = BiometricTemplate(
            template_id=template_id,
            staff_id=staff_id,
            auth_method=AuthMethod.FINGERPRINT,
            template_data=template_data or base64.b64encode(secrets.token_bytes(256)).decode(),
            quality_score=quality_score,
            created_at=datetime.utcnow(),
            device_type=cls._active_device,
        )

        cls._templates[template_id] = template

        return {
            "success": True,
            "template_id": template_id,
            "staff_id": staff_id,
            "quality_score": quality_score,
            "message": "Fingerprint enrolled successfully",
        }

    @classmethod
    def register_card(
        cls,
        staff_id: int,
        card_number: str,
        card_type: str = "rfid",
        facility_code: Optional[str] = None,
        valid_days: int = 365,
    ) -> Dict[str, Any]:
        """
        Register a card/badge for a staff member.
        """
        card_id = f"CARD-{staff_id}-{secrets.token_hex(4)}"

        card = CardCredential(
            card_id=card_id,
            card_number=card_number,
            staff_id=staff_id,
            card_type=card_type,
            facility_code=facility_code,
            valid_from=datetime.utcnow(),
            valid_until=datetime.utcnow() + timedelta(days=valid_days),
        )

        cls._cards[card_id] = card

        return {
            "success": True,
            "card_id": card_id,
            "staff_id": staff_id,
            "card_number": card_number,
            "valid_until": card.valid_until.isoformat(),
            "message": "Card registered successfully",
        }

    @classmethod
    def verify_fingerprint(
        cls,
        template_data: str,
        location_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Verify a fingerprint against enrolled templates.

        In production, would use actual biometric matching algorithm.
        """
        # Simulate fingerprint matching
        # In real implementation, would compare template_data against stored templates
        for template_id, template in cls._templates.items():
            if template.auth_method == AuthMethod.FINGERPRINT and template.is_active:
                # Simulate match (in production, use actual matching)
                if cls._active_device == DeviceType.VIRTUAL:
                    # For virtual device, accept any template that exists
                    staff_id = template.staff_id

                    # Check schedule
                    schedule_ok = cls._check_schedule(staff_id, location_id)

                    result = AccessResult.GRANTED if schedule_ok else AccessResult.OUTSIDE_SCHEDULE

                    # Log attempt
                    cls._log_access(
                        staff_id=staff_id,
                        auth_method=AuthMethod.FINGERPRINT,
                        result=result,
                        location_id=location_id,
                    )

                    return {
                        "success": result == AccessResult.GRANTED,
                        "result": result.value,
                        "staff_id": staff_id,
                        "template_id": template_id,
                        "match_score": 0.95,
                        "timestamp": datetime.utcnow().isoformat(),
                    }

        # No match found
        cls._log_access(
            staff_id=None,
            auth_method=AuthMethod.FINGERPRINT,
            result=AccessResult.UNKNOWN_USER,
            location_id=location_id,
        )

        return {
            "success": False,
            "result": AccessResult.UNKNOWN_USER.value,
            "message": "No matching fingerprint found",
        }

    @classmethod
    def verify_card(
        cls,
        card_number: str,
        location_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Verify a card/badge against registered cards.
        """
        for card_id, card in cls._cards.items():
            if card.card_number == card_number:
                if not card.is_active:
                    cls._log_access(
                        staff_id=card.staff_id,
                        auth_method=AuthMethod.CARD,
                        result=AccessResult.DISABLED_USER,
                        location_id=location_id,
                    )
                    return {
                        "success": False,
                        "result": AccessResult.DISABLED_USER.value,
                        "message": "Card is disabled",
                    }

                # Check validity period
                now = datetime.utcnow()
                if card.valid_until and now > card.valid_until:
                    cls._log_access(
                        staff_id=card.staff_id,
                        auth_method=AuthMethod.CARD,
                        result=AccessResult.DENIED,
                        location_id=location_id,
                        details="Card expired",
                    )
                    return {
                        "success": False,
                        "result": AccessResult.DENIED.value,
                        "message": "Card has expired",
                    }

                # Check schedule
                schedule_ok = cls._check_schedule(card.staff_id, location_id)
                result = AccessResult.GRANTED if schedule_ok else AccessResult.OUTSIDE_SCHEDULE

                cls._log_access(
                    staff_id=card.staff_id,
                    auth_method=AuthMethod.CARD,
                    result=result,
                    location_id=location_id,
                )

                return {
                    "success": result == AccessResult.GRANTED,
                    "result": result.value,
                    "staff_id": card.staff_id,
                    "card_id": card_id,
                    "timestamp": datetime.utcnow().isoformat(),
                }

        # Card not found
        cls._log_access(
            staff_id=None,
            auth_method=AuthMethod.CARD,
            result=AccessResult.UNKNOWN_USER,
            location_id=location_id,
        )

        return {
            "success": False,
            "result": AccessResult.UNKNOWN_USER.value,
            "message": "Card not recognized",
        }

    @classmethod
    def set_access_schedule(
        cls,
        staff_id: int,
        schedules: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Set access schedule for a staff member.

        schedules: List of {day_of_week, start_time, end_time, location_id}
        """
        staff_schedules = []
        for sched in schedules:
            staff_schedules.append(AccessSchedule(
                staff_id=staff_id,
                day_of_week=sched.get("day_of_week", 0),
                start_time=sched.get("start_time", "00:00"),
                end_time=sched.get("end_time", "23:59"),
                location_id=sched.get("location_id"),
            ))

        cls._schedules[staff_id] = staff_schedules

        return {
            "success": True,
            "staff_id": staff_id,
            "schedule_count": len(staff_schedules),
            "message": "Schedule updated",
        }

    @classmethod
    def _check_schedule(cls, staff_id: int, location_id: Optional[int] = None) -> bool:
        """Check if staff member is allowed access at current time."""
        if staff_id not in cls._schedules:
            return True  # No schedule = always allowed

        now = datetime.utcnow()
        current_day = now.weekday()
        current_time = now.strftime("%H:%M")

        for schedule in cls._schedules[staff_id]:
            if schedule.day_of_week == current_day:
                if schedule.location_id and schedule.location_id != location_id:
                    continue
                if schedule.start_time <= current_time <= schedule.end_time:
                    return True

        return False

    @classmethod
    def _log_access(
        cls,
        staff_id: Optional[int],
        auth_method: AuthMethod,
        result: AccessResult,
        location_id: Optional[int] = None,
        details: Optional[str] = None,
    ):
        """Log an access attempt."""
        attempt = AccessAttempt(
            attempt_id=secrets.token_hex(8),
            timestamp=datetime.utcnow(),
            staff_id=staff_id,
            auth_method=auth_method,
            device_id=cls._active_device.value,
            result=result,
            location_id=location_id,
            details=details,
        )
        cls._access_log.append(attempt)

        # Keep only last 1000 entries in memory
        if len(cls._access_log) > 1000:
            cls._access_log = cls._access_log[-1000:]

    @classmethod
    def get_access_log(
        cls,
        staff_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get access log entries."""
        filtered = cls._access_log

        if staff_id:
            filtered = [a for a in filtered if a.staff_id == staff_id]

        if start_date:
            filtered = [a for a in filtered if a.timestamp >= start_date]

        if end_date:
            filtered = [a for a in filtered if a.timestamp <= end_date]

        # Sort by timestamp descending and limit
        filtered = sorted(filtered, key=lambda x: x.timestamp, reverse=True)[:limit]

        return [
            {
                "attempt_id": a.attempt_id,
                "timestamp": a.timestamp.isoformat(),
                "staff_id": a.staff_id,
                "auth_method": a.auth_method.value,
                "device_id": a.device_id,
                "result": a.result.value,
                "location_id": a.location_id,
                "details": a.details,
            }
            for a in filtered
        ]

    @classmethod
    def get_enrolled_credentials(cls, staff_id: int) -> Dict[str, Any]:
        """Get all enrolled credentials for a staff member."""
        fingerprints = [
            {
                "template_id": t.template_id,
                "created_at": t.created_at.isoformat(),
                "quality_score": t.quality_score,
                "is_active": t.is_active,
            }
            for t in cls._templates.values()
            if t.staff_id == staff_id and t.auth_method == AuthMethod.FINGERPRINT
        ]

        cards = [
            {
                "card_id": c.card_id,
                "card_number": c.card_number[-4:].rjust(len(c.card_number), '*'),  # Mask card number
                "card_type": c.card_type,
                "valid_until": c.valid_until.isoformat() if c.valid_until else None,
                "is_active": c.is_active,
            }
            for c in cls._cards.values()
            if c.staff_id == staff_id
        ]

        return {
            "staff_id": staff_id,
            "fingerprints": fingerprints,
            "cards": cards,
            "has_schedule": staff_id in cls._schedules,
        }

    @classmethod
    def revoke_credential(
        cls,
        credential_id: str,
        credential_type: str,  # "fingerprint" or "card"
    ) -> Dict[str, Any]:
        """Revoke a credential."""
        if credential_type == "fingerprint" and credential_id in cls._templates:
            cls._templates[credential_id].is_active = False
            return {"success": True, "message": "Fingerprint revoked"}

        if credential_type == "card" and credential_id in cls._cards:
            cls._cards[credential_id].is_active = False
            return {"success": True, "message": "Card revoked"}

        return {"success": False, "message": "Credential not found"}

    @classmethod
    def configure_device(
        cls,
        device_type: str,
        connection_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Configure biometric device."""
        try:
            cls._active_device = DeviceType(device_type)
        except ValueError:
            return {"success": False, "error": f"Unknown device type: {device_type}"}

        cls._device_status = {
            "connected": True,
            "last_seen": datetime.utcnow(),
            "firmware": "1.0.0" if device_type != "virtual" else "1.0.0-virtual",
            "connection_params": connection_params,
        }

        return {
            "success": True,
            "device_type": cls._active_device.value,
            "supported_methods": cls._get_supported_methods(),
        }

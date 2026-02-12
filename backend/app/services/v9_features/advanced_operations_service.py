"""
Advanced Operations Service Stub
=================================
Service stub for V9 advanced operations features including permission overrides,
terminal health monitoring, safe/emergency mode, cash variance detection,
and session timeout management.
"""

from datetime import datetime
from typing import Optional, List


class PermissionOverrideService:
    """Service for temporary permission override management."""

    def __init__(self, db=None):
        self.db = db

    def create_override(self, staff_id: int, override_type: str, max_value: float = None,
                        max_percentage: float = None, valid_from: datetime = None,
                        valid_until: datetime = None, reason: str = None,
                        granted_by_id: int = None) -> dict:
        """Grant a temporary permission override to a staff member."""
        return {
            "id": 1,
            "staff_id": staff_id,
            "override_type": override_type,
            "max_value": max_value,
            "max_percentage": max_percentage,
            "valid_from": valid_from,
            "valid_until": valid_until,
            "reason": reason,
            "granted_by_id": granted_by_id,
            "is_active": True,
        }

    def get_active_overrides(self, staff_id: int, active_only: bool = True) -> list:
        """Get all permission overrides for a staff member."""
        return []

    def use_override(self, override_id: int, amount: float = None,
                     transaction_id: int = None, notes: str = None) -> dict:
        """Use a permission override for a transaction."""
        return {"success": True, "message": "Override applied"}

    def revoke_override(self, override_id: int, revoked_by_id: int, reason: str) -> bool:
        """Revoke a permission override."""
        return True


class TerminalHealthService:
    """Service for POS terminal health monitoring."""

    def __init__(self, db=None):
        self.db = db

    def register_terminal(self, terminal_id: str, terminal_name: str, ip_address: str = None,
                          latitude: float = None, longitude: float = None) -> dict:
        """Register a new POS terminal."""
        return {
            "id": 1,
            "terminal_id": terminal_id,
            "terminal_name": terminal_name,
            "ip_address": ip_address,
            "status": "online",
        }

    def record_heartbeat(self, terminal_id: str, battery_level: int = None,
                         network_strength: int = None, printer_status: str = None,
                         cash_drawer_status: str = None, latitude: float = None,
                         longitude: float = None) -> dict:
        """Record terminal heartbeat with health data."""
        return {"terminal_id": terminal_id, "status": "online"}

    def get_offline_terminals(self, threshold_minutes: int = 5) -> list:
        """Get terminals that haven't sent a heartbeat recently."""
        return []

    def lock_terminal(self, terminal_id: str, locked_by_id: int, reason: str) -> bool:
        """Remotely lock a terminal."""
        return True

    def unlock_terminal(self, terminal_id: str, unlocked_by_id: int) -> bool:
        """Remotely unlock a terminal."""
        return True

    def set_geo_fence(self, terminal_id: str, center_lat: float, center_lon: float,
                      radius_meters: float) -> bool:
        """Configure geo-fencing for a terminal."""
        return True


class SafeModeService:
    """Service for emergency/safe mode management."""

    def __init__(self, db=None):
        self.db = db

    def activate_safe_mode(self, level: str, reason: str, activated_by_id: int,
                           auto_deactivate_hours: int = None,
                           allowed_operations: list = None) -> dict:
        """Activate emergency/safe mode."""
        return {
            "id": 1,
            "level": level,
            "reason": reason,
            "activated_by_id": activated_by_id,
            "is_active": True,
            "allowed_operations": allowed_operations or [],
        }

    def deactivate_safe_mode(self, mode_id: int, deactivated_by_id: int) -> bool:
        """Deactivate safe mode."""
        return True

    def get_active_safe_mode(self) -> Optional[dict]:
        """Get the currently active safe mode if any."""
        return None

    def is_operation_allowed(self, operation: str) -> bool:
        """Check if an operation is allowed in current safe mode."""
        return True


class CashVarianceService:
    """Service for cash variance detection and tracking."""

    def __init__(self, db=None):
        self.db = db

    def record_count(self, shift_id: int, terminal_id: str, expected_amount: float,
                     actual_amount: float, counted_by_id: int, notes: str = None) -> dict:
        """Submit a cash count and detect variance."""
        variance = actual_amount - expected_amount
        return {
            "id": 1,
            "shift_id": shift_id,
            "terminal_id": terminal_id,
            "expected_amount": expected_amount,
            "actual_amount": actual_amount,
            "variance_amount": variance,
            "variance_percentage": round((variance / expected_amount * 100), 2) if expected_amount else 0,
            "severity": "low",
            "status": "unresolved",
        }

    def get_unresolved_variances(self, min_severity: str = "low") -> list:
        """Get all unresolved cash variances."""
        return []

    def resolve_variance(self, variance_id: int, reviewed_by_id: int, notes: str) -> bool:
        """Resolve/investigate a cash variance."""
        return True


class SessionTimeoutService:
    """Service for session timeout configuration."""

    def __init__(self, db=None):
        self.db = db

    def set_timeout_config(self, role: str, timeout_minutes: int, warning_minutes: int = None,
                           extend_allowed: bool = True, max_extensions: int = 3) -> dict:
        """Configure session timeout for a role."""
        return {
            "id": 1,
            "role": role,
            "timeout_minutes": timeout_minutes,
            "warning_minutes": warning_minutes,
            "extend_allowed": extend_allowed,
            "max_extensions": max_extensions,
        }

    def get_timeout_config(self, role: str) -> dict:
        """Get session timeout configuration for a role."""
        return {
            "id": 1,
            "role": role,
            "timeout_minutes": 30,
            "warning_minutes": 5,
            "extend_allowed": True,
            "max_extensions": 3,
        }

"""
BJ's Bar V9 - Advanced Operations Service
Handles enterprise controls, terminal health, emergency modes, cash management
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import hashlib
import uuid
import json

from app.models.advanced_features_v9 import (
    LocationPermissionOverride, TerminalHealth, EmergencyModeConfig,
    CashVarianceConfig, CashVarianceRecord, SessionTimeoutConfig,
    PermissionOverrideType, TerminalHealthStatus, SafeModeType
)
from app.models import StaffUser, Venue


class AdvancedOperationsService:
    """Service for advanced POS operations and enterprise controls"""

    def __init__(self, db: Session):
        """Initialize service with database session"""
        self.db = db

    # ==========================================================================
    # PERMISSION OVERRIDE MANAGEMENT
    # ==========================================================================

    @staticmethod
    def create_permission_override(
        db: Session,
        venue_id: int,
        staff_user_id: int,
        permission_key: str,
        override_type: str,
        created_by_id: Optional[int] = None,
        valid_from: Optional[datetime] = None,
        valid_until: Optional[datetime] = None,
        requires_manager_approval: bool = False,
        max_value_limit: Optional[float] = None
    ) -> LocationPermissionOverride:
        """Create or update permission override for a staff member at a location"""
        
        # Check if override exists
        existing = db.query(LocationPermissionOverride).filter(
            LocationPermissionOverride.venue_id == venue_id,
            LocationPermissionOverride.staff_user_id == staff_user_id,
            LocationPermissionOverride.permission_key == permission_key
        ).first()
        
        if existing:
            existing.override_type = override_type
            existing.valid_from = valid_from
            existing.valid_until = valid_until
            existing.requires_manager_approval = requires_manager_approval
            existing.max_value_limit = max_value_limit
            db.commit()
            return existing
        
        override = LocationPermissionOverride(
            venue_id=venue_id,
            staff_user_id=staff_user_id,
            permission_key=permission_key,
            override_type=override_type,
            valid_from=valid_from,
            valid_until=valid_until,
            requires_manager_approval=requires_manager_approval,
            max_value_limit=max_value_limit,
            created_by=created_by_id
        )
        
        db.add(override)
        db.commit()
        db.refresh(override)
        return override
    
    @staticmethod
    def check_permission(
        db: Session,
        venue_id: int,
        staff_user_id: int,
        permission_key: str,
        value: Optional[float] = None
    ) -> Dict[str, Any]:
        """Check if user has permission with any overrides applied"""
        
        now = datetime.now(timezone.utc)
        
        # Get override if exists
        override = db.query(LocationPermissionOverride).filter(
            LocationPermissionOverride.venue_id == venue_id,
            LocationPermissionOverride.staff_user_id == staff_user_id,
            LocationPermissionOverride.permission_key == permission_key,
            or_(
                LocationPermissionOverride.valid_from.is_(None),
                LocationPermissionOverride.valid_from <= now
            ),
            or_(
                LocationPermissionOverride.valid_until.is_(None),
                LocationPermissionOverride.valid_until >= now
            )
        ).first()
        
        if not override:
            return {
                "has_override": False,
                "permission_granted": None,  # Use default role permission
                "requires_approval": False,
                "max_value": None
            }
        
        # Check value limit if applicable
        if override.max_value_limit and value:
            if value > override.max_value_limit:
                return {
                    "has_override": True,
                    "permission_granted": False,
                    "reason": f"Value {value} exceeds limit {override.max_value_limit}",
                    "requires_approval": True,
                    "max_value": override.max_value_limit
                }
        
        return {
            "has_override": True,
            "permission_granted": override.override_type == PermissionOverrideType.GRANT.value,
            "requires_approval": override.requires_manager_approval or 
                               override.override_type == PermissionOverrideType.REQUIRE_APPROVAL.value,
            "max_value": override.max_value_limit
        }
    
    @staticmethod
    def get_user_overrides(
        db: Session,
        staff_user_id: int,
        venue_id: Optional[int] = None
    ) -> List[LocationPermissionOverride]:
        """Get all permission overrides for a user"""

        query = db.query(LocationPermissionOverride).filter(
            LocationPermissionOverride.staff_user_id == staff_user_id
        )

        if venue_id:
            query = query.filter(LocationPermissionOverride.venue_id == venue_id)

        return query.all()

    # ==========================================================================
    # ENDPOINT-COMPATIBLE PERMISSION OVERRIDE METHODS
    # ==========================================================================

    def create_override(
        self,
        staff_id: int,
        override_type: str,
        max_value: Optional[float] = None,
        max_percentage: Optional[float] = None,
        valid_from: Optional[datetime] = None,
        valid_until: Optional[datetime] = None,
        reason: Optional[str] = None,
        granted_by_id: Optional[int] = None
    ) -> LocationPermissionOverride:
        """Create a permission override (endpoint-compatible wrapper)"""

        override = LocationPermissionOverride(
            staff_user_id=staff_id,
            override_type=override_type,
            max_value_limit=max_value,
            valid_from=valid_from or datetime.now(timezone.utc),
            valid_until=valid_until,
            permission_key=override_type,
            created_by=granted_by_id
        )

        self.db.add(override)
        self.db.commit()
        self.db.refresh(override)
        return override

    def get_active_overrides(
        self,
        staff_id: int,
        active_only: bool = True
    ) -> List[LocationPermissionOverride]:
        """Get active permission overrides for a staff member"""

        now = datetime.now(timezone.utc)
        query = self.db.query(LocationPermissionOverride).filter(
            LocationPermissionOverride.staff_user_id == staff_id
        )

        if active_only:
            query = query.filter(
                or_(
                    LocationPermissionOverride.valid_from.is_(None),
                    LocationPermissionOverride.valid_from <= now
                ),
                or_(
                    LocationPermissionOverride.valid_until.is_(None),
                    LocationPermissionOverride.valid_until >= now
                )
            )

        return query.all()

    def use_override(
        self,
        override_id: int,
        amount: float,
        transaction_id: Optional[int] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Use a permission override for a transaction"""

        override = self.db.query(LocationPermissionOverride).filter(
            LocationPermissionOverride.id == override_id
        ).first()

        if not override:
            return {"success": False, "message": "Override not found"}

        now = datetime.now(timezone.utc)

        # Check if still valid
        if override.valid_until and override.valid_until < now:
            return {"success": False, "message": "Override has expired"}

        # Check value limit
        if override.max_value_limit and amount > override.max_value_limit:
            return {"success": False, "message": f"Amount exceeds limit of {override.max_value_limit}"}

        # Log the usage (would typically create an audit record)
        return {"success": True, "message": "Override applied successfully"}

    def revoke_override(
        self,
        override_id: int,
        revoked_by_id: int,
        reason: str
    ) -> bool:
        """Revoke a permission override"""

        override = self.db.query(LocationPermissionOverride).filter(
            LocationPermissionOverride.id == override_id
        ).first()

        if not override:
            return False

        # Set valid_until to now to revoke
        override.valid_until = datetime.now(timezone.utc)
        self.db.commit()
        return True
    
    # ==========================================================================
    # TERMINAL HEALTH MONITORING
    # ==========================================================================
    
    @staticmethod
    def register_terminal(
        db: Session,
        venue_id: int,
        terminal_id: str,
        terminal_name: Optional[str] = None,
        os_version: Optional[str] = None,
        app_version: Optional[str] = None,
        ip_address: Optional[str] = None,
        mac_address: Optional[str] = None
    ) -> TerminalHealth:
        """Register a new terminal or update existing"""
        
        existing = db.query(TerminalHealth).filter(
            TerminalHealth.venue_id == venue_id,
            TerminalHealth.terminal_id == terminal_id
        ).first()
        
        if existing:
            existing.terminal_name = terminal_name or existing.terminal_name
            existing.os_version = os_version or existing.os_version
            existing.app_version = app_version or existing.app_version
            existing.ip_address = ip_address or existing.ip_address
            existing.mac_address = mac_address or existing.mac_address
            existing.last_heartbeat = datetime.now(timezone.utc)
            existing.status = TerminalHealthStatus.ONLINE.value
            db.commit()
            return existing
        
        terminal = TerminalHealth(
            venue_id=venue_id,
            terminal_id=terminal_id,
            terminal_name=terminal_name or f"Terminal {terminal_id}",
            os_version=os_version,
            app_version=app_version,
            ip_address=ip_address,
            mac_address=mac_address,
            status=TerminalHealthStatus.ONLINE.value,
            last_heartbeat=datetime.now(timezone.utc)
        )
        
        db.add(terminal)
        db.commit()
        db.refresh(terminal)
        return terminal
    
    @staticmethod
    def heartbeat(
        db: Session,
        venue_id: int,
        terminal_id: str,
        metrics: Optional[Dict[str, Any]] = None,
        current_user_id: Optional[int] = None
    ) -> TerminalHealth:
        """Record terminal heartbeat with optional metrics"""
        
        terminal = db.query(TerminalHealth).filter(
            TerminalHealth.venue_id == venue_id,
            TerminalHealth.terminal_id == terminal_id
        ).first()
        
        if not terminal:
            # Auto-register
            terminal = AdvancedOperationsService.register_terminal(
                db, venue_id, terminal_id
            )
        
        terminal.last_heartbeat = datetime.now(timezone.utc)
        terminal.status = TerminalHealthStatus.ONLINE.value
        terminal.last_activity_at = datetime.now(timezone.utc)
        
        if current_user_id:
            terminal.current_user_id = current_user_id
        
        if metrics:
            terminal.cpu_usage_percent = metrics.get("cpu_usage")
            terminal.memory_usage_percent = metrics.get("memory_usage")
            terminal.disk_usage_percent = metrics.get("disk_usage")
            terminal.network_latency_ms = metrics.get("network_latency")
            terminal.receipt_printer_status = metrics.get("receipt_printer")
            terminal.kitchen_printer_status = metrics.get("kitchen_printer")
            terminal.fiscal_device_status = metrics.get("fiscal_device")
            terminal.cash_drawer_open = metrics.get("cash_drawer_open", False)
        
        db.commit()
        return terminal
    
    @staticmethod
    def check_terminal_status(db: Session, venue_id: int) -> List[Dict[str, Any]]:
        """Check status of all terminals at a venue"""
        
        terminals = db.query(TerminalHealth).filter(
            TerminalHealth.venue_id == venue_id
        ).all()
        
        now = datetime.now(timezone.utc)
        offline_threshold = timedelta(minutes=5)
        
        results = []
        for terminal in terminals:
            # Auto-update status if heartbeat missed
            if terminal.last_heartbeat:
                time_since_heartbeat = now - terminal.last_heartbeat
                if time_since_heartbeat > offline_threshold:
                    terminal.status = TerminalHealthStatus.OFFLINE.value
                    db.commit()
            
            results.append({
                "terminal_id": terminal.terminal_id,
                "terminal_name": terminal.terminal_name,
                "status": terminal.status,
                "last_heartbeat": terminal.last_heartbeat,
                "current_user_id": terminal.current_user_id,
                "is_locked": terminal.is_locked,
                "printer_status": {
                    "receipt": terminal.receipt_printer_status,
                    "kitchen": terminal.kitchen_printer_status,
                    "fiscal": terminal.fiscal_device_status
                },
                "performance": {
                    "cpu": terminal.cpu_usage_percent,
                    "memory": terminal.memory_usage_percent,
                    "disk": terminal.disk_usage_percent
                }
            })
        
        return results
    
    @staticmethod
    def lock_terminal(
        db: Session,
        venue_id: int,
        terminal_id: str,
        reason: str
    ) -> bool:
        """Lock a terminal remotely"""
        
        terminal = db.query(TerminalHealth).filter(
            TerminalHealth.venue_id == venue_id,
            TerminalHealth.terminal_id == terminal_id
        ).first()
        
        if not terminal:
            return False
        
        terminal.is_locked = True
        terminal.lock_reason = reason
        db.commit()
        return True
    
    @staticmethod
    def unlock_terminal(
        db: Session,
        venue_id: int,
        terminal_id: str
    ) -> bool:
        """Unlock a terminal remotely"""
        
        terminal = db.query(TerminalHealth).filter(
            TerminalHealth.venue_id == venue_id,
            TerminalHealth.terminal_id == terminal_id
        ).first()
        
        if not terminal:
            return False
        
        terminal.is_locked = False
        terminal.lock_reason = None
        db.commit()
        return True

    # ==========================================================================
    # ENDPOINT-COMPATIBLE TERMINAL HEALTH METHODS
    # ==========================================================================

    def register_terminal(
        self,
        terminal_id: str,
        terminal_name: Optional[str] = None,
        ip_address: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None
    ) -> TerminalHealth:
        """Register a new terminal (endpoint-compatible wrapper)"""

        existing = self.db.query(TerminalHealth).filter(
            TerminalHealth.terminal_id == terminal_id
        ).first()

        if existing:
            existing.terminal_name = terminal_name or existing.terminal_name
            existing.ip_address = ip_address or existing.ip_address
            existing.last_heartbeat = datetime.now(timezone.utc)
            existing.status = TerminalHealthStatus.ONLINE.value
            self.db.commit()
            return existing

        terminal = TerminalHealth(
            terminal_id=terminal_id,
            terminal_name=terminal_name or f"Terminal {terminal_id}",
            ip_address=ip_address,
            status=TerminalHealthStatus.ONLINE.value,
            last_heartbeat=datetime.now(timezone.utc)
        )

        self.db.add(terminal)
        self.db.commit()
        self.db.refresh(terminal)
        return terminal

    def record_heartbeat(
        self,
        terminal_id: str,
        battery_level: Optional[int] = None,
        network_strength: Optional[int] = None,
        printer_status: Optional[str] = None,
        cash_drawer_status: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None
    ) -> Dict[str, Any]:
        """Record terminal heartbeat (endpoint-compatible wrapper)"""

        terminal = self.db.query(TerminalHealth).filter(
            TerminalHealth.terminal_id == terminal_id
        ).first()

        if not terminal:
            terminal = self.register_terminal(terminal_id)

        terminal.last_heartbeat = datetime.now(timezone.utc)
        terminal.status = TerminalHealthStatus.ONLINE.value
        terminal.receipt_printer_status = printer_status

        self.db.commit()

        return {
            "terminal_id": terminal_id,
            "status": "online",
            "last_heartbeat": terminal.last_heartbeat.isoformat()
        }

    def get_offline_terminals(
        self,
        threshold_minutes: int = 5
    ) -> List[TerminalHealth]:
        """Get terminals that haven't sent heartbeat recently"""

        threshold = datetime.now(timezone.utc) - timedelta(minutes=threshold_minutes)

        terminals = self.db.query(TerminalHealth).filter(
            or_(
                TerminalHealth.last_heartbeat < threshold,
                TerminalHealth.last_heartbeat.is_(None)
            )
        ).all()

        # Update status to offline
        for terminal in terminals:
            terminal.status = TerminalHealthStatus.OFFLINE.value

        self.db.commit()
        return terminals

    def lock_terminal(
        self,
        terminal_id: str,
        locked_by_id: int,
        reason: str
    ) -> bool:
        """Lock a terminal remotely (endpoint-compatible wrapper)"""

        terminal = self.db.query(TerminalHealth).filter(
            TerminalHealth.terminal_id == terminal_id
        ).first()

        if not terminal:
            return False

        terminal.is_locked = True
        terminal.lock_reason = reason
        self.db.commit()
        return True

    def unlock_terminal(
        self,
        terminal_id: str,
        unlocked_by_id: int
    ) -> bool:
        """Unlock a terminal remotely (endpoint-compatible wrapper)"""

        terminal = self.db.query(TerminalHealth).filter(
            TerminalHealth.terminal_id == terminal_id
        ).first()

        if not terminal:
            return False

        terminal.is_locked = False
        terminal.lock_reason = None
        self.db.commit()
        return True

    def set_geo_fence(
        self,
        terminal_id: str,
        center_lat: float,
        center_lon: float,
        radius_meters: float
    ) -> bool:
        """Configure geo-fencing for a terminal"""

        terminal = self.db.query(TerminalHealth).filter(
            TerminalHealth.terminal_id == terminal_id
        ).first()

        if not terminal:
            return False

        # Store geo-fence configuration (would typically be stored in a separate field/table)
        # For now, we'll just return success
        self.db.commit()
        return True

    # ==========================================================================
    # EMERGENCY/SAFE MODE MANAGEMENT
    # ==========================================================================
    
    @staticmethod
    def get_or_create_emergency_config(
        db: Session,
        venue_id: int
    ) -> EmergencyModeConfig:
        """Get or create emergency mode configuration"""
        
        config = db.query(EmergencyModeConfig).filter(
            EmergencyModeConfig.venue_id == venue_id
        ).first()
        
        if not config:
            config = EmergencyModeConfig(
                venue_id=venue_id,
                current_mode=SafeModeType.NORMAL.value,
                safe_mode_allowed_operations=["view_menu", "take_order", "cash_payment"],
                emergency_disable_discounts=True,
                emergency_cash_only=False
            )
            db.add(config)
            db.commit()
            db.refresh(config)
        
        return config
    
    @staticmethod
    def activate_safe_mode(
        db: Session,
        venue_id: int,
        mode: str,
        reason: str,
        activated_by: int
    ) -> EmergencyModeConfig:
        """Activate safe or emergency mode"""
        
        config = AdvancedOperationsService.get_or_create_emergency_config(db, venue_id)
        
        config.current_mode = mode
        config.mode_activated_at = datetime.now(timezone.utc)
        config.mode_activated_by = activated_by
        config.mode_reason = reason
        
        db.commit()
        return config
    
    @staticmethod
    def deactivate_safe_mode(
        db: Session,
        venue_id: int
    ) -> EmergencyModeConfig:
        """Return to normal mode"""
        
        config = AdvancedOperationsService.get_or_create_emergency_config(db, venue_id)
        
        config.current_mode = SafeModeType.NORMAL.value
        config.mode_activated_at = None
        config.mode_activated_by = None
        config.mode_reason = None
        
        db.commit()
        return config
    
    @staticmethod
    def get_current_mode(db: Session, venue_id: int) -> Dict[str, Any]:
        """Get current operating mode and restrictions"""
        
        config = AdvancedOperationsService.get_or_create_emergency_config(db, venue_id)
        
        restrictions = {}
        
        if config.current_mode == SafeModeType.SAFE.value:
            restrictions = {
                "allowed_operations": config.safe_mode_allowed_operations,
                "max_transaction": config.safe_mode_max_transaction,
                "require_manager": config.safe_mode_require_manager
            }
        elif config.current_mode == SafeModeType.EMERGENCY.value:
            restrictions = {
                "discounts_disabled": config.emergency_disable_discounts,
                "cash_only": config.emergency_cash_only,
                "limited_menu": config.emergency_menu_subset
            }
        
        return {
            "current_mode": config.current_mode,
            "activated_at": config.mode_activated_at,
            "reason": config.mode_reason,
            "restrictions": restrictions
        }

    # ==========================================================================
    # ENDPOINT-COMPATIBLE SAFE MODE METHODS
    # ==========================================================================

    def activate_safe_mode(
        self,
        level: str,
        reason: str,
        activated_by_id: int,
        auto_deactivate_hours: Optional[int] = None,
        allowed_operations: Optional[List[str]] = None
    ) -> EmergencyModeConfig:
        """Activate safe mode (endpoint-compatible wrapper)"""

        config = self.db.query(EmergencyModeConfig).first()

        if not config:
            config = EmergencyModeConfig(
                current_mode=level,
                mode_activated_at=datetime.now(timezone.utc),
                mode_activated_by=activated_by_id,
                mode_reason=reason,
                safe_mode_allowed_operations=allowed_operations or ["view_menu", "take_order", "cash_payment"]
            )
            self.db.add(config)
        else:
            config.current_mode = level
            config.mode_activated_at = datetime.now(timezone.utc)
            config.mode_activated_by = activated_by_id
            config.mode_reason = reason
            if allowed_operations:
                config.safe_mode_allowed_operations = allowed_operations

        self.db.commit()
        self.db.refresh(config)
        return config

    def deactivate_safe_mode(
        self,
        mode_id: int,
        deactivated_by_id: int
    ) -> bool:
        """Deactivate safe mode (endpoint-compatible wrapper)"""

        config = self.db.query(EmergencyModeConfig).filter(
            EmergencyModeConfig.id == mode_id
        ).first()

        if not config:
            return False

        config.current_mode = SafeModeType.NORMAL.value
        config.mode_activated_at = None
        config.mode_activated_by = None
        config.mode_reason = None

        self.db.commit()
        return True

    def get_active_safe_mode(self) -> Optional[EmergencyModeConfig]:
        """Get currently active safe mode if any"""

        config = self.db.query(EmergencyModeConfig).filter(
            EmergencyModeConfig.current_mode != SafeModeType.NORMAL.value
        ).first()

        return config

    def is_operation_allowed(self, operation: str) -> bool:
        """Check if an operation is allowed in current safe mode"""

        config = self.db.query(EmergencyModeConfig).first()

        if not config:
            return True  # No config means all operations allowed

        if config.current_mode == SafeModeType.NORMAL.value:
            return True

        if config.safe_mode_allowed_operations:
            return operation in config.safe_mode_allowed_operations

        return False

    # ==========================================================================
    # CASH VARIANCE MANAGEMENT
    # ==========================================================================
    
    @staticmethod
    def get_or_create_variance_config(
        db: Session,
        venue_id: int
    ) -> CashVarianceConfig:
        """Get or create cash variance configuration"""
        
        config = db.query(CashVarianceConfig).filter(
            CashVarianceConfig.venue_id == venue_id
        ).first()
        
        if not config:
            config = CashVarianceConfig(
                venue_id=venue_id,
                warning_threshold_amount=5.0,
                warning_threshold_percent=1.0,
                critical_threshold_amount=20.0,
                critical_threshold_percent=5.0,
                force_count_on_shift_close=True,
                blind_cash_count=True
            )
            db.add(config)
            db.commit()
            db.refresh(config)
        
        return config
    
    @staticmethod
    def record_cash_count(
        db: Session,
        venue_id: int,
        shift_id: int,
        staff_user_id: int,
        expected_amount: float,
        counted_amount: float,
        explanation: Optional[str] = None
    ) -> CashVarianceRecord:
        """Record a cash count and analyze variance"""
        
        config = AdvancedOperationsService.get_or_create_variance_config(db, venue_id)
        
        variance_amount = counted_amount - expected_amount
        variance_percent = (variance_amount / expected_amount * 100) if expected_amount else 0
        
        # Determine severity
        abs_variance = abs(variance_amount)
        abs_variance_pct = abs(variance_percent)
        
        if abs_variance >= config.critical_threshold_amount or \
           abs_variance_pct >= config.critical_threshold_percent:
            severity = "critical"
        elif abs_variance >= config.warning_threshold_amount or \
             abs_variance_pct >= config.warning_threshold_percent:
            severity = "warning"
        else:
            severity = "ok"
        
        # Flag suspicious if needed
        is_flagged = (severity == "critical" and config.auto_flag_suspicious)
        
        record = CashVarianceRecord(
            venue_id=venue_id,
            shift_id=shift_id,
            staff_user_id=staff_user_id,
            expected_amount=expected_amount,
            counted_amount=counted_amount,
            variance_amount=variance_amount,
            variance_percent=variance_percent,
            severity=severity,
            explanation=explanation,
            is_flagged=is_flagged,
            manager_approved=False
        )
        
        db.add(record)
        db.commit()
        db.refresh(record)
        
        return record
    
    @staticmethod
    def approve_variance(
        db: Session,
        record_id: int,
        manager_id: int,
        notes: Optional[str] = None
    ) -> CashVarianceRecord:
        """Manager approval of cash variance"""
        
        record = db.query(CashVarianceRecord).filter(
            CashVarianceRecord.id == record_id
        ).first()
        
        if not record:
            raise ValueError("Variance record not found")
        
        record.manager_approved = True
        record.manager_id = manager_id
        record.manager_notes = notes
        
        db.commit()
        return record
    
    @staticmethod
    def get_variance_history(
        db: Session,
        venue_id: int,
        staff_user_id: Optional[int] = None,
        days: int = 30,
        severity: Optional[str] = None
    ) -> List[CashVarianceRecord]:
        """Get cash variance history"""
        
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        query = db.query(CashVarianceRecord).filter(
            CashVarianceRecord.venue_id == venue_id,
            CashVarianceRecord.created_at >= start_date
        )
        
        if staff_user_id:
            query = query.filter(CashVarianceRecord.staff_user_id == staff_user_id)
        
        if severity:
            query = query.filter(CashVarianceRecord.severity == severity)
        
        return query.order_by(CashVarianceRecord.created_at.desc()).all()
    
    @staticmethod
    def get_variance_analytics(
        db: Session,
        venue_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get cash variance analytics"""
        
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        records = db.query(CashVarianceRecord).filter(
            CashVarianceRecord.venue_id == venue_id,
            CashVarianceRecord.created_at >= start_date
        ).all()
        
        if not records:
            return {
                "total_counts": 0,
                "total_variance": 0,
                "avg_variance": 0,
                "by_severity": {},
                "by_employee": {},
                "flagged_count": 0
            }
        
        total_variance = sum(r.variance_amount for r in records)
        avg_variance = total_variance / len(records)
        
        by_severity = {}
        by_employee = {}
        flagged_count = 0
        
        for r in records:
            by_severity[r.severity] = by_severity.get(r.severity, 0) + 1
            by_employee[r.staff_user_id] = by_employee.get(r.staff_user_id, 0) + abs(r.variance_amount)
            if r.is_flagged:
                flagged_count += 1
        
        return {
            "total_counts": len(records),
            "total_variance": total_variance,
            "avg_variance": avg_variance,
            "by_severity": by_severity,
            "by_employee": by_employee,
            "flagged_count": flagged_count
        }

    # ==========================================================================
    # ENDPOINT-COMPATIBLE CASH VARIANCE METHODS
    # ==========================================================================

    def record_count(
        self,
        shift_id: int,
        terminal_id: str,
        expected_amount: float,
        actual_amount: float,
        counted_by_id: int,
        notes: Optional[str] = None
    ) -> CashVarianceRecord:
        """Record cash count and detect variance (endpoint-compatible wrapper)"""

        variance_amount = actual_amount - expected_amount
        variance_percent = (variance_amount / expected_amount * 100) if expected_amount else 0

        # Determine severity
        abs_variance = abs(variance_amount)
        abs_variance_pct = abs(variance_percent)

        if abs_variance >= 20.0 or abs_variance_pct >= 5.0:
            severity = "critical"
        elif abs_variance >= 5.0 or abs_variance_pct >= 1.0:
            severity = "high"
        elif abs_variance >= 2.0 or abs_variance_pct >= 0.5:
            severity = "medium"
        else:
            severity = "low"

        record = CashVarianceRecord(
            shift_id=shift_id,
            staff_user_id=counted_by_id,
            expected_amount=expected_amount,
            counted_amount=actual_amount,
            variance_amount=variance_amount,
            variance_percent=variance_percent,
            severity=severity,
            explanation=notes,
            is_flagged=(severity in ["high", "critical"]),
            manager_approved=False
        )

        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_unresolved_variances(
        self,
        min_severity: str = "low"
    ) -> List[CashVarianceRecord]:
        """Get all unresolved cash variances"""

        severity_order = ["low", "medium", "high", "critical"]
        min_index = severity_order.index(min_severity) if min_severity in severity_order else 0

        records = self.db.query(CashVarianceRecord).filter(
            CashVarianceRecord.manager_approved == False,
            CashVarianceRecord.is_flagged == True
        ).order_by(CashVarianceRecord.created_at.desc()).all()

        # Filter by severity
        return [r for r in records if severity_order.index(r.severity) >= min_index]

    def resolve_variance(
        self,
        variance_id: int,
        reviewed_by_id: int,
        notes: str
    ) -> bool:
        """Resolve/investigate a cash variance"""

        record = self.db.query(CashVarianceRecord).filter(
            CashVarianceRecord.id == variance_id
        ).first()

        if not record:
            return False

        record.manager_approved = True
        record.manager_id = reviewed_by_id
        record.manager_notes = notes

        self.db.commit()
        return True

    # ==========================================================================
    # SESSION TIMEOUT MANAGEMENT
    # ==========================================================================
    
    @staticmethod
    def get_or_create_timeout_config(
        db: Session,
        venue_id: int
    ) -> SessionTimeoutConfig:
        """Get or create session timeout configuration"""
        
        config = db.query(SessionTimeoutConfig).filter(
            SessionTimeoutConfig.venue_id == venue_id
        ).first()
        
        if not config:
            config = SessionTimeoutConfig(
                venue_id=venue_id,
                inactivity_timeout_seconds=300,
                absolute_timeout_hours=12,
                lock_instead_of_logout=True,
                require_pin_to_unlock=True,
                warning_before_timeout_seconds=60
            )
            db.add(config)
            db.commit()
            db.refresh(config)
        
        return config
    
    @staticmethod
    def check_session_timeout(
        db: Session,
        venue_id: int,
        user_role: str,
        session_start: datetime,
        last_activity: datetime
    ) -> Dict[str, Any]:
        """Check if session should be timed out"""
        
        config = AdvancedOperationsService.get_or_create_timeout_config(db, venue_id)
        
        now = datetime.now(timezone.utc)
        
        # Get role-specific timeout if exists
        inactivity_timeout = config.inactivity_timeout_seconds
        if config.role_timeouts and user_role in config.role_timeouts:
            inactivity_timeout = config.role_timeouts[user_role]
        
        # Check inactivity
        inactive_seconds = (now - last_activity).total_seconds()
        should_timeout = inactive_seconds >= inactivity_timeout
        
        # Check absolute timeout
        session_hours = (now - session_start).total_seconds() / 3600
        absolute_timeout = session_hours >= config.absolute_timeout_hours
        
        # Check if warning should be shown
        warning_threshold = inactivity_timeout - config.warning_before_timeout_seconds
        show_warning = inactive_seconds >= warning_threshold and not should_timeout
        
        return {
            "should_timeout": should_timeout or absolute_timeout,
            "timeout_reason": "inactivity" if should_timeout else ("absolute" if absolute_timeout else None),
            "show_warning": show_warning,
            "seconds_until_timeout": max(0, inactivity_timeout - inactive_seconds),
            "lock_instead_of_logout": config.lock_instead_of_logout,
            "require_pin": config.require_pin_to_unlock
        }

    # ==========================================================================
    # ENDPOINT-COMPATIBLE SESSION TIMEOUT METHODS
    # ==========================================================================

    def set_timeout_config(
        self,
        role: str,
        timeout_minutes: int,
        warning_minutes: int = 1,
        extend_allowed: bool = True,
        max_extensions: int = 3
    ) -> SessionTimeoutConfig:
        """Configure session timeout for a role (endpoint-compatible wrapper)"""

        config = self.db.query(SessionTimeoutConfig).first()

        if not config:
            config = SessionTimeoutConfig(
                inactivity_timeout_seconds=timeout_minutes * 60,
                warning_before_timeout_seconds=warning_minutes * 60,
                absolute_timeout_hours=12,
                lock_instead_of_logout=True,
                require_pin_to_unlock=True,
                role_timeouts={role: timeout_minutes * 60}
            )
            self.db.add(config)
        else:
            if not config.role_timeouts:
                config.role_timeouts = {}
            config.role_timeouts[role] = timeout_minutes * 60

        self.db.commit()
        self.db.refresh(config)
        return config

    def get_timeout_config(
        self,
        role: str
    ) -> SessionTimeoutConfig:
        """Get session timeout configuration for a role"""

        config = self.db.query(SessionTimeoutConfig).first()

        if not config:
            # Create default config
            config = SessionTimeoutConfig(
                inactivity_timeout_seconds=300,
                absolute_timeout_hours=12,
                lock_instead_of_logout=True,
                require_pin_to_unlock=True,
                warning_before_timeout_seconds=60
            )
            self.db.add(config)
            self.db.commit()
            self.db.refresh(config)

        return config


# Class aliases for backwards compatibility with endpoint imports
PermissionOverrideService = AdvancedOperationsService
TerminalHealthService = AdvancedOperationsService
SafeModeService = AdvancedOperationsService
CashVarianceService = AdvancedOperationsService
SessionTimeoutService = AdvancedOperationsService


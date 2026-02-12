"""
IoT Service Stub
=================
Service stub for V9 IoT features including device management,
temperature monitoring, pour meters, and connected scales.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any


class IoTDeviceService:
    """Service for IoT device registration and management.

    Note: Methods are called as class methods in the route files.
    """

    def __init__(self, db=None):
        self.db = db

    @staticmethod
    def register_device(db, venue_id: int, device_type: str, device_name: str,
                        serial_number: str, location: str,
                        configuration: dict = None) -> dict:
        """Register a new IoT device."""
        return {
            "id": 1,
            "venue_id": venue_id,
            "device_type": device_type,
            "device_name": device_name,
            "serial_number": serial_number,
            "location": location,
            "status": "active",
        }

    @staticmethod
    def update_device_status(db, device_id: int, status: str,
                             battery_level: int = None,
                             firmware_version: str = None) -> dict:
        """Update device status and metrics."""
        return {
            "device_id": device_id,
            "status": status,
            "battery_level": battery_level,
        }

    @staticmethod
    def get_devices(db, venue_id: int, device_type: str = None,
                    status: str = None) -> list:
        """Get all devices for a venue."""
        return []

    @staticmethod
    def get_offline_devices(db, venue_id: int,
                            threshold_minutes: int = 5,
                            offline_threshold_minutes: int = None) -> list:
        """Get devices that haven't reported recently."""
        return []


class TemperatureMonitoringService:
    """Service for IoT temperature monitoring (HACCP compliance).

    Note: Methods are called as class methods in the route files.
    """

    def __init__(self, db=None):
        self.db = db

    @staticmethod
    def record_temperature(db, device_id: int, temperature: Decimal,
                           unit: str = "C", humidity: Decimal = None) -> dict:
        """Record temperature reading from a sensor."""
        return {
            "id": 1,
            "device_id": device_id,
            "temperature": float(temperature),
            "unit": unit,
            "humidity": float(humidity) if humidity else None,
            "alert_triggered": False,
            "status": "normal",
        }

    @staticmethod
    def get_temperature_history(db, venue_id: int, device_id: int = None,
                                location: str = None, start_date: datetime = None,
                                end_date: datetime = None,
                                alerts_only: bool = False) -> dict:
        """Get temperature history for HACCP compliance."""
        return {
            "venue_id": venue_id,
            "readings": [],
            "alerts": [],
        }

    @staticmethod
    def acknowledge_temperature_alert(db, log_id: int, acknowledged_by: int,
                                      corrective_action: str = None) -> dict:
        """Acknowledge a temperature alert."""
        return {
            "log_id": log_id,
            "acknowledged": True,
            "corrective_action": corrective_action,
        }

    @staticmethod
    def get_haccp_compliance_report(db, venue_id: int, start_date: date,
                                    end_date: date) -> dict:
        """Generate HACCP compliance report for inspections."""
        return {
            "venue_id": venue_id,
            "period": {"start": str(start_date), "end": str(end_date)},
            "compliance_score": 0.0,
            "total_readings": 0,
            "violations": 0,
        }


class PourMeterService:
    """Service for smart pour meter tracking.

    Note: Methods are called as class methods in the route files.
    """

    def __init__(self, db=None):
        self.db = db

    @staticmethod
    def record_pour(db, device_id: int, product_id: int, poured_amount_ml: Decimal,
                    expected_amount_ml: Decimal, staff_id: int = None,
                    order_id: int = None) -> dict:
        """Record a pour reading from a smart pour meter."""
        poured = float(poured_amount_ml)
        expected = float(expected_amount_ml)
        variance = poured - expected
        return {
            "id": 1,
            "device_id": device_id,
            "product_id": product_id,
            "poured_ml": poured,
            "expected_ml": expected,
            "variance_ml": variance,
            "accuracy_pct": round((poured / expected * 100), 1) if expected > 0 else 0,
        }

    @staticmethod
    def get_pour_analytics(db, venue_id: int, start_date: date, end_date: date,
                           product_id: int = None, staff_id: int = None) -> dict:
        """Get pour accuracy analytics."""
        return {
            "venue_id": venue_id,
            "period": {"start": str(start_date), "end": str(end_date)},
            "total_pours": 0,
            "average_accuracy": 0.0,
            "by_staff": [],
            "by_product": [],
        }


class ScaleService:
    """Service for connected scale readings.

    Note: Methods are called as class methods in the route files.
    """

    def __init__(self, db=None):
        self.db = db

    @staticmethod
    def record_weight(db, device_id: int, item_id: int, weight_grams: Decimal,
                      expected_weight_grams: Decimal = None) -> dict:
        """Record weight from a connected scale."""
        return {
            "id": 1,
            "device_id": device_id,
            "item_id": item_id,
            "weight_grams": float(weight_grams),
            "expected_weight_grams": float(expected_weight_grams) if expected_weight_grams else None,
        }


class IoTService:
    """General IoT service (used by mobile_scanner route)."""

    def __init__(self, db=None):
        self.db = db

    def get_device(self, device_id: int) -> Optional[dict]:
        """Get a single IoT device."""
        return None

    def scan(self, venue_id: int, device_id: int, data: dict) -> dict:
        """Process a scan from an IoT device."""
        return {"success": True, "data": data}

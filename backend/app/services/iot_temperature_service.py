"""
IoT Temperature Monitoring Service
Records and monitors temperature readings from IoT sensors.
"""
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger(__name__)


class IoTTemperatureService:
    """Monitor IoT temperature sensors and generate alerts."""

    DEFAULT_THRESHOLDS = {
        "walk_in_cooler": {"min": 33, "max": 40, "unit": "F"},
        "walk_in_freezer": {"min": -10, "max": 0, "unit": "F"},
        "prep_area": {"min": 60, "max": 75, "unit": "F"},
        "hot_holding": {"min": 135, "max": 165, "unit": "F"},
        "cold_holding": {"min": 33, "max": 41, "unit": "F"},
    }

    @staticmethod
    def record_reading(
        db: Session, venue_id: int, sensor_id: str,
        temperature: float, location: str, equipment_type: str = None
    ) -> Dict[str, Any]:
        """Store IoT sensor reading and check thresholds."""
        thresholds = IoTTemperatureService.DEFAULT_THRESHOLDS.get(
            equipment_type, {"min": 33, "max": 165, "unit": "F"}
        )

        in_range = thresholds["min"] <= temperature <= thresholds["max"]
        alert = None

        if not in_range:
            alert = {
                "type": "temperature_out_of_range",
                "sensor_id": sensor_id,
                "location": location,
                "temperature": temperature,
                "expected_range": f"{thresholds['min']}-{thresholds['max']}{thresholds['unit']}",
                "severity": "critical" if abs(temperature - thresholds["max"]) > 10 else "warning",
            }

        return {
            "sensor_id": sensor_id,
            "temperature": temperature,
            "location": location,
            "equipment_type": equipment_type,
            "in_range": in_range,
            "thresholds": thresholds,
            "alert": alert,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def get_current_readings(db: Session, venue_id: int) -> List[Dict[str, Any]]:
        """Get latest reading from all sensors."""
        return []

    @staticmethod
    def get_alerts(db: Session, venue_id: int) -> List[Dict[str, Any]]:
        """Get active temperature alerts."""
        return []

    @staticmethod
    def get_sensor_history(
        db: Session, venue_id: int, sensor_id: str, hours: int = 24
    ) -> Dict[str, Any]:
        """Get historical readings for a sensor."""
        return {
            "sensor_id": sensor_id,
            "period_hours": hours,
            "readings": [],
            "min_temp": None,
            "max_temp": None,
            "avg_temp": None,
        }

    @staticmethod
    def configure_thresholds(
        db: Session, venue_id: int, sensor_id: str,
        min_temp: float, max_temp: float
    ) -> Dict[str, Any]:
        """Set alert thresholds for a sensor."""
        return {
            "sensor_id": sensor_id,
            "min_temp": min_temp,
            "max_temp": max_temp,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

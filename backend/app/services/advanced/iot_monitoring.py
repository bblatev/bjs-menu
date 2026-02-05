"""IoT Equipment Monitoring Service."""

from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from app.models.advanced_features import EquipmentSensor, SensorReading, PredictiveMaintenance


class IoTMonitoringService:
    """Service for IoT equipment monitoring and predictive maintenance."""

    def __init__(self, db: Session):
        self.db = db

    def create_sensor(
        self,
        location_id: int,
        equipment_name: str,
        equipment_type: str,
        sensor_id: str,
        sensor_type: str,
        min_threshold: Optional[float] = None,
        max_threshold: Optional[float] = None,
        maintenance_interval_days: Optional[int] = None,
        is_active: bool = True,
    ) -> EquipmentSensor:
        """Register a new sensor."""
        sensor = EquipmentSensor(
            location_id=location_id,
            equipment_name=equipment_name,
            equipment_type=equipment_type,
            sensor_id=sensor_id,
            sensor_type=sensor_type,
            min_threshold=min_threshold,
            max_threshold=max_threshold,
            maintenance_interval_days=maintenance_interval_days,
            is_active=is_active,
        )
        self.db.add(sensor)
        self.db.commit()
        self.db.refresh(sensor)
        return sensor

    def get_sensors(
        self,
        location_id: int,
        equipment_type: Optional[str] = None,
        active_only: bool = True,
    ) -> List[EquipmentSensor]:
        """Get sensors for a location."""
        query = select(EquipmentSensor).where(
            EquipmentSensor.location_id == location_id
        )

        if equipment_type:
            query = query.where(EquipmentSensor.equipment_type == equipment_type)
        if active_only:
            query = query.where(EquipmentSensor.is_active == True)

        result = self.db.execute(query)
        return list(result.scalars().all())

    def record_reading(
        self,
        sensor_db_id: int,
        value: float,
        unit: str,
    ) -> SensorReading:
        """Record a sensor reading."""
        sensor = self.db.get(EquipmentSensor, sensor_db_id)
        if not sensor:
            raise ValueError(f"Sensor {sensor_db_id} not found")

        # Check if reading triggers alert
        is_alert = False
        alert_type = None

        if sensor.min_threshold is not None and value < sensor.min_threshold:
            is_alert = True
            alert_type = "out_of_range"
        elif sensor.max_threshold is not None and value > sensor.max_threshold:
            is_alert = True
            alert_type = "out_of_range"

        reading = SensorReading(
            sensor_id=sensor_db_id,
            timestamp=datetime.utcnow(),
            value=value,
            unit=unit,
            is_alert=is_alert,
            alert_type=alert_type,
        )
        self.db.add(reading)
        self.db.commit()
        self.db.refresh(reading)

        # Check for predictive maintenance if multiple alerts
        if is_alert:
            self._check_maintenance_prediction(sensor_db_id)

        return reading

    def _check_maintenance_prediction(
        self,
        sensor_id: int,
    ) -> None:
        """Check if predictive maintenance alert should be created."""
        # Get recent alerts
        since = datetime.utcnow() - timedelta(hours=24)

        query = select(func.count(SensorReading.id)).where(
            and_(
                SensorReading.sensor_id == sensor_id,
                SensorReading.is_alert == True,
                SensorReading.timestamp >= since,
            )
        )
        result = self.db.execute(query)
        alert_count = result.scalar() or 0

        if alert_count >= 5:
            # Create predictive maintenance alert
            sensor = self.db.get(EquipmentSensor, sensor_id)

            maintenance = PredictiveMaintenance(
                sensor_id=sensor_id,
                prediction_type="anomaly_detected",
                confidence=0.7 + (min(alert_count, 20) / 100),
                predicted_failure_date=date.today() + timedelta(days=7),
                indicators={"recent_alerts": alert_count},
                recommended_action=f"Inspect {sensor.equipment_name} - frequent out-of-range readings detected",
            )
            self.db.add(maintenance)
            self.db.commit()

    def get_readings(
        self,
        sensor_id: int,
        hours: int = 24,
        alerts_only: bool = False,
    ) -> List[SensorReading]:
        """Get sensor readings."""
        since = datetime.utcnow() - timedelta(hours=hours)

        query = select(SensorReading).where(
            and_(
                SensorReading.sensor_id == sensor_id,
                SensorReading.timestamp >= since,
            )
        )

        if alerts_only:
            query = query.where(SensorReading.is_alert == True)

        query = query.order_by(SensorReading.timestamp.desc())

        result = self.db.execute(query)
        return list(result.scalars().all())

    def get_alerts(
        self,
        location_id: int,
        hours: int = 24,
    ) -> List[SensorReading]:
        """Get all alerts for a location."""
        since = datetime.utcnow() - timedelta(hours=hours)

        # Get sensor IDs for location
        sensors = self.get_sensors(location_id)
        sensor_ids = [s.id for s in sensors]

        if not sensor_ids:
            return []

        query = select(SensorReading).where(
            and_(
                SensorReading.sensor_id.in_(sensor_ids),
                SensorReading.is_alert == True,
                SensorReading.timestamp >= since,
            )
        ).order_by(SensorReading.timestamp.desc())

        result = self.db.execute(query)
        return list(result.scalars().all())

    def get_maintenance_predictions(
        self,
        location_id: int,
        acknowledged: Optional[bool] = None,
    ) -> List[PredictiveMaintenance]:
        """Get predictive maintenance alerts."""
        sensors = self.get_sensors(location_id)
        sensor_ids = [s.id for s in sensors]

        if not sensor_ids:
            return []

        query = select(PredictiveMaintenance).where(
            PredictiveMaintenance.sensor_id.in_(sensor_ids)
        )

        if acknowledged is not None:
            query = query.where(PredictiveMaintenance.acknowledged == acknowledged)

        query = query.order_by(PredictiveMaintenance.created_at.desc())

        result = self.db.execute(query)
        return list(result.scalars().all())

    def acknowledge_maintenance(
        self,
        maintenance_id: int,
        action_taken: str,
    ) -> PredictiveMaintenance:
        """Acknowledge a maintenance prediction."""
        maintenance = self.db.get(PredictiveMaintenance, maintenance_id)
        if not maintenance:
            raise ValueError(f"Maintenance {maintenance_id} not found")

        maintenance.acknowledged = True
        maintenance.action_taken = action_taken
        maintenance.resolved_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(maintenance)
        return maintenance

    def record_maintenance(
        self,
        sensor_id: int,
    ) -> EquipmentSensor:
        """Record that maintenance was performed."""
        sensor = self.db.get(EquipmentSensor, sensor_id)
        if not sensor:
            raise ValueError(f"Sensor {sensor_id} not found")

        sensor.last_maintenance = date.today()

        self.db.commit()
        self.db.refresh(sensor)
        return sensor

    def get_dashboard(
        self,
        location_id: int,
    ) -> Dict[str, Any]:
        """Get equipment monitoring dashboard."""
        sensors = self.get_sensors(location_id)
        alerts = self.get_alerts(location_id, hours=24)
        predictions = self.get_maintenance_predictions(location_id, acknowledged=False)

        # Check for maintenance due
        maintenance_due = []
        for sensor in sensors:
            if sensor.maintenance_interval_days and sensor.last_maintenance:
                next_maintenance = sensor.last_maintenance + timedelta(days=sensor.maintenance_interval_days)
                if next_maintenance <= date.today():
                    maintenance_due.append({
                        "sensor_id": sensor.id,
                        "equipment_name": sensor.equipment_name,
                        "days_overdue": (date.today() - next_maintenance).days,
                    })

        # Get temperature readings for refrigerators/freezers
        temp_readings = []
        for sensor in sensors:
            if sensor.sensor_type == "temperature":
                readings = self.get_readings(sensor.id, hours=4)
                if readings:
                    latest = readings[0]
                    temp_readings.append({
                        "equipment": sensor.equipment_name,
                        "current_temp": latest.value,
                        "unit": latest.unit,
                        "is_alert": latest.is_alert,
                        "min_threshold": sensor.min_threshold,
                        "max_threshold": sensor.max_threshold,
                    })

        return {
            "total_sensors": len(sensors),
            "sensors_in_alert": len(set(a.sensor_id for a in alerts)),
            "pending_maintenance": len(maintenance_due) + len(predictions),
            "temperature_readings": temp_readings,
            "alerts": [
                {
                    "id": a.id,
                    "sensor_id": a.sensor_id,
                    "value": a.value,
                    "timestamp": a.timestamp.isoformat(),
                    "alert_type": a.alert_type,
                }
                for a in alerts[:10]
            ],
            "maintenance_predictions": [
                {
                    "id": p.id,
                    "prediction_type": p.prediction_type,
                    "confidence": p.confidence,
                    "recommended_action": p.recommended_action,
                }
                for p in predictions
            ],
            "maintenance_due": maintenance_due,
        }

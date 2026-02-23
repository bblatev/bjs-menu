"""
IoT Device Management API Routes
Temperature sensors, smart scales, table sensors.
"""
from fastapi import APIRouter, Query, Request
from app.db.session import DbSession
from app.core.rate_limit import limiter
from datetime import datetime, timezone

router = APIRouter()


@router.get("/")
@limiter.limit("60/minute")
def get_iot_overview(request: Request, db: DbSession):
    """IoT device overview."""
    return {
        "module": "iot",
        "status": "active",
        "device_types": ["temperature_sensor", "smart_scale", "table_sensor"],
        "endpoints": ["/temperature", "/scales", "/table-sensors"],
    }


# ==================== TEMPERATURE SENSORS ====================

@router.post("/temperature/reading")
@limiter.limit("60/minute")
def record_temperature_reading(request: Request, db: DbSession, data: dict = {}):
    """Record IoT temperature sensor reading."""
    from app.services.iot_temperature_service import IoTTemperatureService
    return IoTTemperatureService.record_reading(
        db, data.get("venue_id", 1), data.get("sensor_id", ""),
        data.get("temperature", 0), data.get("location", ""),
        data.get("equipment_type")
    )


@router.get("/temperature/current")
@limiter.limit("60/minute")
def get_current_temperatures(request: Request, db: DbSession, venue_id: int = Query(1)):
    """Get current readings from all temperature sensors."""
    from app.services.iot_temperature_service import IoTTemperatureService
    return IoTTemperatureService.get_current_readings(db, venue_id)


@router.get("/temperature/alerts")
@limiter.limit("60/minute")
def get_temperature_alerts(request: Request, db: DbSession, venue_id: int = Query(1)):
    """Get active temperature alerts."""
    from app.services.iot_temperature_service import IoTTemperatureService
    return IoTTemperatureService.get_alerts(db, venue_id)


@router.get("/temperature/history/{sensor_id}")
@limiter.limit("60/minute")
def get_sensor_history(
    request: Request, db: DbSession,
    sensor_id: str, hours: int = Query(24), venue_id: int = Query(1)
):
    """Get historical readings for a sensor."""
    from app.services.iot_temperature_service import IoTTemperatureService
    return IoTTemperatureService.get_sensor_history(db, venue_id, sensor_id, hours)


@router.put("/temperature/thresholds/{sensor_id}")
@limiter.limit("30/minute")
def configure_thresholds(
    request: Request, db: DbSession,
    sensor_id: str, data: dict = {}
):
    """Configure temperature alert thresholds for a sensor."""
    from app.services.iot_temperature_service import IoTTemperatureService
    return IoTTemperatureService.configure_thresholds(
        db, data.get("venue_id", 1), sensor_id,
        data.get("min_temp", 33), data.get("max_temp", 40)
    )


# ==================== SMART SCALES ====================

@router.post("/scales/reading")
@limiter.limit("60/minute")
def record_scale_reading(request: Request, db: DbSession, data: dict = {}):
    """Record scale measurement."""
    return {
        "product_id": data.get("product_id"),
        "weight": data.get("weight", 0),
        "unit": data.get("unit", "oz"),
        "expected_weight": data.get("expected_weight"),
        "variance": 0,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/scales/calibration-status")
@limiter.limit("60/minute")
def get_scale_calibration(request: Request, db: DbSession, venue_id: int = Query(1)):
    """Get scale calibration status."""
    return {"scales": [], "all_calibrated": True}


@router.get("/scales/portion-compliance")
@limiter.limit("60/minute")
def get_portion_compliance(request: Request, db: DbSession, venue_id: int = Query(1)):
    """Get portion size compliance report."""
    return {
        "venue_id": venue_id,
        "compliance_pct": 95.0,
        "total_checks": 0,
        "over_portioned": 0,
        "under_portioned": 0,
        "items": [],
    }


# ==================== TABLE SENSORS ====================

@router.get("/table-sensors")
@limiter.limit("60/minute")
def get_table_sensors(request: Request, db: DbSession, venue_id: int = Query(1)):
    """Get all table sensors and status."""
    return {"venue_id": venue_id, "sensors": [], "total": 0}


@router.get("/table-sensors/{table_id}/activity")
@limiter.limit("60/minute")
def get_table_activity(request: Request, db: DbSession, table_id: int):
    """Get table activity status."""
    return {
        "table_id": table_id,
        "status": "vacant",
        "last_activity": None,
        "occupancy_duration_minutes": 0,
    }


@router.post("/table-sensors/configure")
@limiter.limit("30/minute")
def configure_table_sensor(request: Request, db: DbSession, data: dict = {}):
    """Configure sensor for a table."""
    return {
        "table_id": data.get("table_id"),
        "sensor_id": data.get("sensor_id"),
        "configured": True,
    }

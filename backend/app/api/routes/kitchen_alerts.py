"""Kitchen alerts routes."""

from datetime import datetime, timezone, timedelta
from fastapi import APIRouter
from sqlalchemy import func

from app.db.session import DbSession
from app.models.restaurant import KitchenOrder
from app.models.operations import HACCPTemperatureLog

router = APIRouter()


@router.get("/")
async def get_kitchen_alerts(db: DbSession):
    """Get kitchen alerts (overdue orders, temp warnings)."""
    alerts = []
    # Overdue orders: pending for more than 15 minutes
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=15)
    overdue = db.query(KitchenOrder).filter(
        KitchenOrder.status.in_(["pending", "cooking"]),
        KitchenOrder.created_at < cutoff,
    ).all()
    for o in overdue:
        alerts.append({
            "id": f"order-{o.id}",
            "type": "overdue_order",
            "severity": "warning",
            "message": f"Order #{o.id} (table {o.table_number}) has been {o.status} for over 15 min",
            "created_at": o.created_at.isoformat() if o.created_at else None,
        })
    # Temperature alerts
    temp_alerts = db.query(HACCPTemperatureLog).filter(
        HACCPTemperatureLog.status.in_(["warning", "critical"]),
    ).order_by(HACCPTemperatureLog.recorded_at.desc()).limit(20).all()
    for t in temp_alerts:
        alerts.append({
            "id": f"temp-{t.id}",
            "type": "temperature",
            "severity": t.status,
            "message": f"{t.location} ({t.equipment}): {t.temperature}{t.unit}",
            "created_at": t.recorded_at.isoformat() if t.recorded_at else None,
        })
    return alerts


@router.get("/stats")
async def get_kitchen_alert_stats(db: DbSession):
    """Get kitchen alert statistics."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=15)
    overdue_count = db.query(func.count(KitchenOrder.id)).filter(
        KitchenOrder.status.in_(["pending", "cooking"]),
        KitchenOrder.created_at < cutoff,
    ).scalar() or 0
    critical_temps = db.query(func.count(HACCPTemperatureLog.id)).filter(
        HACCPTemperatureLog.status == "critical",
    ).scalar() or 0
    warning_temps = db.query(func.count(HACCPTemperatureLog.id)).filter(
        HACCPTemperatureLog.status == "warning",
    ).scalar() or 0
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    resolved_today = db.query(func.count(KitchenOrder.id)).filter(
        KitchenOrder.status.in_(["completed", "ready"]),
        KitchenOrder.completed_at >= today_start,
    ).scalar() or 0
    return {
        "total_alerts": overdue_count + critical_temps + warning_temps,
        "critical": critical_temps,
        "warnings": overdue_count + warning_temps,
        "resolved_today": resolved_today,
    }

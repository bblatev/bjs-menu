"""
Inventory Hardware Reports API
RFID accuracy, keg yield, pour analysis, tank consumption
"""
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.core.rbac import get_current_user
from app.models import StaffUser

router = APIRouter()


# =============================================================================
# RFID INVENTORY REPORTS
# =============================================================================

@router.get("/rfid/accuracy", response_model=Dict[str, Any])
@limiter.limit("60/minute")
async def get_rfid_accuracy_report(
    request: Request,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):

    """
    RFID inventory accuracy report.
    Shows count accuracy, missing tags, and variance trends.
    """
    from app.models.advanced_features_v9 import RFIDInventoryCount

    if not start_date:
        start_date = datetime.now(timezone.utc) - timedelta(days=30)
    if not end_date:
        end_date = datetime.now(timezone.utc)

    # Get completed counts
    counts = db.query(RFIDInventoryCount).filter(
        RFIDInventoryCount.venue_id == current_user.venue_id,
        RFIDInventoryCount.status == "completed",
        RFIDInventoryCount.completed_at >= start_date,
        RFIDInventoryCount.completed_at <= end_date
    ).all()

    if not counts:
        return {
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "message": "No inventory counts in this period",
            "total_counts": 0
        }

    # Calculate accuracy metrics
    total_expected = sum(c.tags_expected or 0 for c in counts)
    total_found = sum(c.tags_found or 0 for c in counts)
    total_missing = sum(c.tags_missing or 0 for c in counts)
    total_unexpected = sum(c.tags_unexpected or 0 for c in counts)
    total_variance = sum(c.variance_value or 0 for c in counts)

    accuracy_pct = (total_found / total_expected * 100) if total_expected > 0 else 100

    # Accuracy by zone
    by_zone = {}
    for count in counts:
        zone = count.zone or "all"
        if zone not in by_zone:
            by_zone[zone] = {"expected": 0, "found": 0, "missing": 0}
        by_zone[zone]["expected"] += count.tags_expected or 0
        by_zone[zone]["found"] += count.tags_found or 0
        by_zone[zone]["missing"] += count.tags_missing or 0

    for zone, data in by_zone.items():
        data["accuracy"] = round((data["found"] / data["expected"] * 100), 1) if data["expected"] > 0 else 100

    # Trend data (daily accuracy)
    trend = []
    current = start_date
    while current <= end_date:
        next_day = current + timedelta(days=1)
        day_counts = [c for c in counts if c.completed_at and current <= c.completed_at < next_day]
        if day_counts:
            day_expected = sum(c.tags_expected or 0 for c in day_counts)
            day_found = sum(c.tags_found or 0 for c in day_counts)
            trend.append({
                "date": current.strftime("%Y-%m-%d"),
                "accuracy": round((day_found / day_expected * 100), 1) if day_expected > 0 else 100,
                "counts": len(day_counts)
            })
        current = next_day

    return {
        "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        "summary": {
            "total_counts": len(counts),
            "total_tags_expected": total_expected,
            "total_tags_found": total_found,
            "total_tags_missing": total_missing,
            "total_unexpected": total_unexpected,
            "overall_accuracy": round(accuracy_pct, 1),
            "total_variance_value": round(total_variance, 2)
        },
        "by_zone": by_zone,
        "trend": trend,
        "recommendations": [
            "Schedule regular cycle counts for high-value items" if accuracy_pct < 95 else None,
            f"Investigate {total_missing} missing tags" if total_missing > 0 else None,
            "Review receiving procedures" if total_unexpected > 10 else None
        ]
    }


@router.get("/rfid/movement", response_model=Dict[str, Any])
@limiter.limit("60/minute")
async def get_rfid_movement_report(
    request: Request,
    zone: Optional[str] = None,
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    RFID tag movement report.
    Shows item movements between zones.
    """
    from app.models.advanced_features_v9 import RFIDReading

    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    query = db.query(RFIDReading).filter(
        RFIDReading.venue_id == current_user.venue_id,
        RFIDReading.read_at >= since,
        RFIDReading.movement_detected == True
    )

    if zone:
        query = query.filter(
            (RFIDReading.location_zone == zone) | (RFIDReading.previous_zone == zone)
        )

    movements = query.order_by(RFIDReading.read_at.desc()).limit(500).all()

    # Group by zone transition
    transitions = {}
    for m in movements:
        key = f"{m.previous_zone}->{m.location_zone}"
        if key not in transitions:
            transitions[key] = {"count": 0, "tags": []}
        transitions[key]["count"] += 1

    return {
        "period_hours": hours,
        "total_movements": len(movements),
        "transitions": transitions,
        "recent_movements": [{
            "tag_id": m.tag_id,
            "from_zone": m.previous_zone,
            "to_zone": m.location_zone,
            "timestamp": m.read_at.isoformat()
        } for m in movements[:20]]
    }


@router.get("/rfid/expiring", response_model=Dict[str, Any])
@limiter.limit("60/minute")
async def get_rfid_expiring_report(
    request: Request,
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Report on RFID-tagged items expiring soon.
    """
    from app.models.advanced_features_v9 import RFIDTag

    threshold = datetime.now(timezone.utc) + timedelta(days=days)

    expiring = db.query(RFIDTag).filter(
        RFIDTag.venue_id == current_user.venue_id,
        RFIDTag.is_active == True,
        RFIDTag.expiry_date.isnot(None),
        RFIDTag.expiry_date <= threshold
    ).order_by(RFIDTag.expiry_date).all()

    already_expired = [t for t in expiring if t.expiry_date < datetime.now(timezone.utc)]
    expiring_soon = [t for t in expiring if t.expiry_date >= datetime.now(timezone.utc)]

    total_value_at_risk = sum(t.current_value or 0 for t in expiring)

    return {
        "threshold_days": days,
        "summary": {
            "already_expired": len(already_expired),
            "expiring_soon": len(expiring_soon),
            "total_items": len(expiring),
            "total_value_at_risk": round(total_value_at_risk, 2)
        },
        "expired": [{
            "tag_id": t.tag_id,
            "tag_name": t.tag_name,
            "expiry_date": t.expiry_date.isoformat(),
            "days_overdue": (datetime.now(timezone.utc) - t.expiry_date).days,
            "zone": t.current_zone,
            "value": t.current_value
        } for t in already_expired[:20]],
        "expiring": [{
            "tag_id": t.tag_id,
            "tag_name": t.tag_name,
            "expiry_date": t.expiry_date.isoformat(),
            "days_remaining": (t.expiry_date - datetime.now(timezone.utc)).days,
            "zone": t.current_zone,
            "value": t.current_value
        } for t in expiring_soon[:50]]
    }


# =============================================================================
# KEG & POUR REPORTS
# =============================================================================

@router.get("/kegs/yield", response_model=Dict[str, Any])
@limiter.limit("60/minute")
async def get_keg_yield_report(
    request: Request,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Keg yield analysis report.
    Compares expected vs actual yields.
    """
    from app.models.advanced_features_v9 import KegTracking

    if not start_date:
        start_date = datetime.now(timezone.utc) - timedelta(days=30)

    kegs = db.query(KegTracking).filter(
        KegTracking.venue_id == current_user.venue_id,
        KegTracking.status.in_(["empty", "returned"]),
        KegTracking.empty_date >= start_date if start_date else True
    ).all()

    if not kegs:
        return {
            "period": {"start": start_date.isoformat() if start_date else None},
            "message": "No completed kegs in this period"
        }

    # Calculate yields
    total_expected = sum(k.initial_volume_ml for k in kegs)
    total_dispensed = sum(k.dispensed_volume_ml or 0 for k in kegs)
    total_waste = sum(k.waste_volume_ml or 0 for k in kegs)
    total_cost = sum(k.purchase_price or 0 for k in kegs)

    avg_yield = (total_dispensed / total_expected * 100) if total_expected > 0 else 0
    loss_value = (total_expected - total_dispensed) / total_expected * total_cost if total_expected > 0 else 0

    # By product
    by_product = {}
    for keg in kegs:
        name = keg.product_name
        if name not in by_product:
            by_product[name] = {"kegs": 0, "expected": 0, "dispensed": 0, "waste": 0}
        by_product[name]["kegs"] += 1
        by_product[name]["expected"] += keg.initial_volume_ml
        by_product[name]["dispensed"] += keg.dispensed_volume_ml or 0
        by_product[name]["waste"] += keg.waste_volume_ml or 0

    for name, data in by_product.items():
        data["yield_pct"] = round((data["dispensed"] / data["expected"] * 100), 1) if data["expected"] > 0 else 0

    return {
        "period": {"start": start_date.isoformat() if start_date else None},
        "summary": {
            "total_kegs": len(kegs),
            "total_expected_ml": total_expected,
            "total_dispensed_ml": total_dispensed,
            "total_waste_ml": total_waste,
            "average_yield": round(avg_yield, 1),
            "total_cost": round(total_cost, 2),
            "estimated_loss_value": round(loss_value, 2)
        },
        "by_product": by_product,
        "insights": [
            f"Average yield is {avg_yield:.1f}%" if avg_yield < 95 else None,
            f"Estimated loss: ${loss_value:.2f}" if loss_value > 50 else None,
            "Consider staff training on pour techniques" if avg_yield < 90 else None
        ]
    }


@router.get("/kegs/status", response_model=Dict[str, Any])
@limiter.limit("60/minute")
async def get_keg_status_report(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Current keg status overview.
    """
    from app.models.advanced_features_v9 import KegTracking

    kegs = db.query(KegTracking).filter(
        KegTracking.venue_id == current_user.venue_id
    ).all()

    by_status = {}
    by_product = {}
    low_kegs = []

    for keg in kegs:
        # By status
        status = keg.status
        if status not in by_status:
            by_status[status] = 0
        by_status[status] += 1

        # By product
        if keg.status in ["tapped", "low"]:
            name = keg.product_name
            if name not in by_product:
                by_product[name] = {"tapped": 0, "remaining_ml": 0}
            by_product[name]["tapped"] += 1
            by_product[name]["remaining_ml"] += keg.current_volume_ml

        # Low inventory warning
        if keg.status == "low":
            low_kegs.append({
                "keg_id": keg.keg_id,
                "product": keg.product_name,
                "remaining_ml": keg.current_volume_ml,
                "fill_pct": round((keg.current_volume_ml / keg.initial_volume_ml * 100), 1) if keg.initial_volume_ml > 0 else 0,
                "tap_number": keg.tap_number
            })

    return {
        "total_kegs": len(kegs),
        "by_status": by_status,
        "tapped_products": by_product,
        "low_inventory_warning": low_kegs,
        "needs_reorder": len(low_kegs) > 0
    }


# =============================================================================
# TANK & BULK LIQUID REPORTS
# =============================================================================

@router.get("/tanks/consumption", response_model=Dict[str, Any])
@limiter.limit("60/minute")
async def get_tank_consumption_report(
    request: Request,
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Bulk tank consumption analysis.
    """
    from app.models.advanced_features_v9 import BulkTankLevel, FlowMeterReading

    tanks = db.query(BulkTankLevel).filter(
        BulkTankLevel.venue_id == current_user.venue_id
    ).all()

    since = datetime.now(timezone.utc) - timedelta(days=days)

    tank_consumption = []
    for tank in tanks:
        # Get flow readings for this tank
        readings = db.query(FlowMeterReading).filter(
            FlowMeterReading.venue_id == current_user.venue_id,
            FlowMeterReading.container_id == tank.tank_id,
            FlowMeterReading.recorded_at >= since
        ).all()

        total_consumed = sum(r.flow_volume_ml for r in readings)
        daily_avg = total_consumed / days if days > 0 else 0

        tank_consumption.append({
            "tank_id": tank.tank_id,
            "tank_name": tank.tank_name,
            "product_type": tank.product_type,
            "capacity_liters": tank.capacity_liters,
            "current_level_liters": tank.current_level_liters,
            "fill_percentage": round(tank.fill_percentage, 1),
            "consumed_ml": total_consumed,
            "consumed_liters": round(total_consumed / 1000, 2),
            "daily_avg_ml": round(daily_avg, 1),
            "days_until_empty": round(tank.current_level_liters * 1000 / daily_avg, 1) if daily_avg > 0 else None,
            "refills": len([r for r in readings if r.flow_volume_ml < 0])  # Negative = refill
        })

    # Sort by urgency
    tank_consumption.sort(key=lambda x: x.get("days_until_empty") or 999)

    return {
        "period_days": days,
        "total_tanks": len(tanks),
        "tanks": tank_consumption,
        "reorder_needed": [t for t in tank_consumption if t.get("days_until_empty") and t["days_until_empty"] < 3]
    }


# =============================================================================
# COMBINED DASHBOARD
# =============================================================================

@router.get("/dashboard", response_model=Dict[str, Any])
@limiter.limit("60/minute")
async def get_inventory_hardware_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Combined inventory hardware dashboard.
    Overview of all hardware tracking systems.
    """
    from app.models.advanced_features_v9 import (
        RFIDTag, RFIDInventoryCount, KegTracking, BulkTankLevel
    )

    venue_id = current_user.venue_id

    # RFID stats
    active_tags = db.query(RFIDTag).filter(
        RFIDTag.venue_id == venue_id,
        RFIDTag.is_active == True
    ).count()

    recent_counts = db.query(RFIDInventoryCount).filter(
        RFIDInventoryCount.venue_id == venue_id,
        RFIDInventoryCount.status == "completed",
        RFIDInventoryCount.completed_at >= datetime.now(timezone.utc) - timedelta(days=7)
    ).all()

    avg_accuracy = 0
    if recent_counts:
        accuracies = [
            (c.tags_found / c.tags_expected * 100) if c.tags_expected > 0 else 100
            for c in recent_counts
        ]
        avg_accuracy = sum(accuracies) / len(accuracies)

    # Keg stats
    kegs = db.query(KegTracking).filter(KegTracking.venue_id == venue_id).all()
    kegs_tapped = sum(1 for k in kegs if k.status == "tapped")
    kegs_low = sum(1 for k in kegs if k.status == "low")

    # Tank stats
    tanks = db.query(BulkTankLevel).filter(BulkTankLevel.venue_id == venue_id).all()
    tanks_low = sum(1 for t in tanks if t.status in ["low", "critical"])

    return {
        "rfid": {
            "active_tags": active_tags,
            "recent_counts": len(recent_counts),
            "avg_accuracy": round(avg_accuracy, 1)
        },
        "kegs": {
            "total": len(kegs),
            "tapped": kegs_tapped,
            "low": kegs_low
        },
        "tanks": {
            "total": len(tanks),
            "low_alerts": tanks_low
        },
        "alerts": {
            "total": kegs_low + tanks_low,
            "items": [
                {"type": "keg_low", "count": kegs_low},
                {"type": "tank_low", "count": tanks_low}
            ]
        },
        "last_updated": datetime.now(timezone.utc).isoformat()
    }

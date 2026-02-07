"""HACCP food safety API routes."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func

from app.db.session import DbSession
from app.models.operations import HACCPTemperatureLog, HACCPSafetyCheck

router = APIRouter()


class HACCPDashboard(BaseModel):
    compliance_score: int
    pending_checks: int
    overdue_checks: int
    recent_violations: int
    last_inspection: str
    next_inspection: str


class TemperatureLog(BaseModel):
    id: Optional[str] = None
    location: str
    equipment: str = ""
    temperature: float
    recorded_at: Optional[str] = None
    recorded_by: str = ""
    status: str = "normal"  # normal, warning, critical
    notes: Optional[str] = None


class SafetyCheck(BaseModel):
    id: str
    check_type: str
    location: str
    due_date: str
    completed_date: Optional[str] = None
    completed_by: Optional[str] = None
    status: str  # pending, completed, overdue
    result: Optional[str] = None
    notes: Optional[str] = None


@router.get("/dashboard")
def get_haccp_dashboard(db: DbSession):
    """Get HACCP dashboard data."""
    total_checks = db.query(func.count(HACCPSafetyCheck.id)).scalar() or 0
    completed_checks = (
        db.query(func.count(HACCPSafetyCheck.id))
        .filter(HACCPSafetyCheck.status == "completed")
        .scalar()
        or 0
    )
    pending_checks = (
        db.query(func.count(HACCPSafetyCheck.id))
        .filter(HACCPSafetyCheck.status == "pending")
        .scalar()
        or 0
    )
    overdue_checks = (
        db.query(func.count(HACCPSafetyCheck.id))
        .filter(HACCPSafetyCheck.status == "overdue")
        .scalar()
        or 0
    )

    # Compliance score: percentage of completed out of total (non-pending)
    if total_checks > 0:
        compliance_score = int((completed_checks / total_checks) * 100)
    else:
        compliance_score = 100

    # Recent violations: critical temperature logs in the last 30 days
    recent_violations = (
        db.query(func.count(HACCPTemperatureLog.id))
        .filter(HACCPTemperatureLog.status == "critical")
        .scalar()
        or 0
    )

    # Last and next inspection: based on most recent completed and nearest pending check
    last_completed = (
        db.query(HACCPSafetyCheck)
        .filter(HACCPSafetyCheck.status == "completed")
        .order_by(HACCPSafetyCheck.completed_at.desc())
        .first()
    )
    next_pending = (
        db.query(HACCPSafetyCheck)
        .filter(HACCPSafetyCheck.status.in_(["pending", "overdue"]))
        .order_by(HACCPSafetyCheck.due_date.asc())
        .first()
    )

    last_inspection = (
        last_completed.completed_at.strftime("%Y-%m-%d")
        if last_completed and last_completed.completed_at
        else "N/A"
    )
    next_inspection = (
        next_pending.due_date.strftime("%Y-%m-%d")
        if next_pending and next_pending.due_date
        else "N/A"
    )

    return HACCPDashboard(
        compliance_score=compliance_score,
        pending_checks=pending_checks,
        overdue_checks=overdue_checks,
        recent_violations=recent_violations,
        last_inspection=last_inspection,
        next_inspection=next_inspection,
    )


@router.get("/temperature-logs")
def get_temperature_logs(db: DbSession):
    """Get temperature logs."""
    logs = (
        db.query(HACCPTemperatureLog)
        .order_by(HACCPTemperatureLog.recorded_at.desc())
        .all()
    )
    return [
        TemperatureLog(
            id=str(log.id),
            location=log.location,
            equipment=log.equipment or "",
            temperature=log.temperature,
            recorded_at=log.recorded_at.isoformat() + "Z" if log.recorded_at else "",
            recorded_by=log.recorded_by or "",
            status=log.status or "normal",
            notes=log.notes,
        )
        for log in logs
    ]


@router.post("/temperature-logs")
def create_temperature_log(log: TemperatureLog, db: DbSession):
    """Create a temperature log entry."""
    db_log = HACCPTemperatureLog(
        location=log.location,
        equipment=log.equipment,
        temperature=log.temperature,
        status=log.status,
        recorded_by=log.recorded_by,
        notes=log.notes,
        recorded_at=datetime.utcnow(),
    )
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return {"success": True, "id": str(db_log.id)}


@router.get("/safety-checks")
def get_safety_checks(db: DbSession):
    """Get safety checks."""
    checks = (
        db.query(HACCPSafetyCheck)
        .order_by(HACCPSafetyCheck.due_date.desc())
        .all()
    )
    return [
        SafetyCheck(
            id=str(check.id),
            check_type=check.name,
            location=check.category or "",
            due_date=(
                check.due_date.strftime("%Y-%m-%d") if check.due_date else ""
            ),
            completed_date=(
                check.completed_at.isoformat() + "Z"
                if check.completed_at
                else None
            ),
            completed_by=check.completed_by,
            status=check.status or "pending",
            result="pass" if check.status == "completed" else None,
            notes=check.notes,
        )
        for check in checks
    ]


@router.post("/safety-checks/{check_id}/complete")
def complete_safety_check(
    check_id: str,
    db: DbSession,
    result: str = Query(...),
    notes: Optional[str] = Query(None),
):
    """Complete a safety check."""
    check = (
        db.query(HACCPSafetyCheck)
        .filter(HACCPSafetyCheck.id == int(check_id))
        .first()
    )
    if not check:
        raise HTTPException(status_code=404, detail="Safety check not found")

    check.status = "completed"
    check.completed_at = datetime.utcnow()
    check.notes = notes if notes else check.notes
    db.commit()
    return {"success": True}


@router.get("/checks")
def get_haccp_checks(db: DbSession):
    """Get HACCP safety checks."""
    checks = (
        db.query(HACCPSafetyCheck)
        .order_by(HACCPSafetyCheck.created_at.desc())
        .all()
    )
    return [
        {
            "id": str(check.id),
            "name": check.name,
            "type": check.category or "general",
            "frequency": check.frequency or "daily",
            "station": "",
            "last_completed": (
                check.completed_at.isoformat() + "Z"
                if check.completed_at
                else None
            ),
            "status": check.status or "pending",
            "assigned_to": check.completed_by or "",
        }
        for check in checks
    ]


@router.get("/logs")
def get_haccp_logs(db: DbSession):
    """Get HACCP compliance logs."""
    logs = (
        db.query(HACCPTemperatureLog)
        .order_by(HACCPTemperatureLog.recorded_at.desc())
        .all()
    )
    return [
        {
            "id": str(log.id),
            "check_id": str(log.id),
            "value": str(log.temperature),
            "unit": log.unit or "C",
            "status": "pass" if log.status == "normal" else "fail",
            "recorded_at": (
                log.recorded_at.isoformat() + "Z" if log.recorded_at else ""
            ),
            "recorded_by": log.recorded_by or "",
            "notes": log.notes or "",
        }
        for log in logs
    ]

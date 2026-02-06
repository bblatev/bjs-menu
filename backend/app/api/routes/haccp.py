"""HACCP food safety API routes."""

from typing import List, Optional
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HACCPDashboard(BaseModel):
    compliance_score: int
    pending_checks: int
    overdue_checks: int
    recent_violations: int
    last_inspection: str
    next_inspection: str


class TemperatureLog(BaseModel):
    id: str
    location: str
    equipment: str
    temperature: float
    recorded_at: str
    recorded_by: str
    status: str  # normal, warning, critical
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
async def get_haccp_dashboard():
    """Get HACCP dashboard data."""
    return HACCPDashboard(
        compliance_score=94,
        pending_checks=3,
        overdue_checks=0,
        recent_violations=1,
        last_inspection="2025-11-15",
        next_inspection="2026-05-15"
    )


@router.get("/temperature-logs")
async def get_temperature_logs():
    """Get temperature logs."""
    return [
        TemperatureLog(id="1", location="Walk-in Cooler", equipment="Cooler #1", temperature=3.5, recorded_at="2026-02-01T08:00:00Z", recorded_by="Mike", status="normal"),
        TemperatureLog(id="2", location="Walk-in Freezer", equipment="Freezer #1", temperature=-18.2, recorded_at="2026-02-01T08:00:00Z", recorded_by="Mike", status="normal"),
        TemperatureLog(id="3", location="Prep Station", equipment="Prep Fridge", temperature=5.8, recorded_at="2026-02-01T08:00:00Z", recorded_by="Mike", status="warning", notes="Slightly high, adjusted thermostat"),
    ]


@router.post("/temperature-logs")
async def create_temperature_log(log: TemperatureLog):
    """Create a temperature log entry."""
    return {"success": True, "id": "new-id"}


@router.get("/safety-checks")
async def get_safety_checks():
    """Get safety checks."""
    return [
        SafetyCheck(id="1", check_type="Opening Checklist", location="Kitchen", due_date="2026-02-01", completed_date="2026-02-01T07:30:00Z", completed_by="Chef Mike", status="completed", result="pass"),
        SafetyCheck(id="2", check_type="Closing Checklist", location="Kitchen", due_date="2026-02-01", status="pending"),
        SafetyCheck(id="3", check_type="Weekly Deep Clean", location="All Areas", due_date="2026-02-03", status="pending"),
    ]


@router.post("/safety-checks/{check_id}/complete")
async def complete_safety_check(check_id: str, result: str, notes: Optional[str] = None):
    """Complete a safety check."""
    return {"success": True}


@router.get("/checks")
async def get_haccp_checks():
    """Get HACCP safety checks."""
    return [
        {"id": "1", "name": "Morning Temperature Check", "type": "temperature", "frequency": "daily", "station": "Walk-in Cooler", "last_completed": "2026-02-06T08:00:00Z", "status": "completed", "assigned_to": "Chef Mike"},
        {"id": "2", "name": "Handwashing Station", "type": "hygiene", "frequency": "hourly", "station": "Kitchen", "last_completed": "2026-02-06T10:00:00Z", "status": "completed", "assigned_to": "All Staff"},
        {"id": "3", "name": "Food Storage Inspection", "type": "storage", "frequency": "daily", "station": "Dry Storage", "last_completed": "2026-02-05T16:00:00Z", "status": "overdue", "assigned_to": "Inventory Manager"},
    ]


@router.get("/logs")
async def get_haccp_logs():
    """Get HACCP compliance logs."""
    return [
        {"id": "1", "check_id": "1", "value": "3.5", "unit": "°C", "status": "pass", "recorded_at": "2026-02-06T08:00:00Z", "recorded_by": "Chef Mike", "notes": ""},
        {"id": "2", "check_id": "2", "value": "OK", "unit": "", "status": "pass", "recorded_at": "2026-02-06T10:00:00Z", "recorded_by": "Staff", "notes": "All stations clean"},
    ]

"""Staff shifts API routes (v5 compatibility)."""

from typing import List, Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter()


class StaffMember(BaseModel):
    id: str
    name: str
    role: str
    email: str
    phone: str
    hourly_rate: float
    status: str  # active, on_leave, inactive


class Shift(BaseModel):
    id: str
    staff_id: str
    staff_name: str
    role: str
    date: str
    start_time: str
    end_time: str
    break_minutes: int = 0
    status: str  # scheduled, in_progress, completed, missed
    actual_start: Optional[str] = None
    actual_end: Optional[str] = None
    notes: Optional[str] = None


@router.get("/staff")
async def get_staff():
    """Get all staff members."""
    return [
        StaffMember(id="1", name="John Doe", role="Server", email="john@bjsbar.com", phone="+359888111222", hourly_rate=12.50, status="active"),
        StaffMember(id="2", name="Jane Smith", role="Bartender", email="jane@bjsbar.com", phone="+359888333444", hourly_rate=14.00, status="active"),
        StaffMember(id="3", name="Mike Johnson", role="Chef", email="mike@bjsbar.com", phone="+359888555666", hourly_rate=18.00, status="active"),
        StaffMember(id="4", name="Sarah Williams", role="Host", email="sarah@bjsbar.com", phone="+359888777888", hourly_rate=11.00, status="active"),
    ]


@router.get("/shifts")
async def get_shifts(date: str = Query(None), staff_id: str = Query(None)):
    """Get shifts with optional filters."""
    return [
        Shift(id="1", staff_id="1", staff_name="John Doe", role="Server", date="2026-02-01", start_time="10:00", end_time="18:00", break_minutes=30, status="completed", actual_start="09:55", actual_end="18:05"),
        Shift(id="2", staff_id="2", staff_name="Jane Smith", role="Bartender", date="2026-02-01", start_time="16:00", end_time="00:00", break_minutes=30, status="in_progress", actual_start="15:58"),
        Shift(id="3", staff_id="3", staff_name="Mike Johnson", role="Chef", date="2026-02-01", start_time="08:00", end_time="16:00", break_minutes=30, status="completed", actual_start="08:00", actual_end="16:10"),
        Shift(id="4", staff_id="1", staff_name="John Doe", role="Server", date="2026-02-02", start_time="10:00", end_time="18:00", break_minutes=30, status="scheduled"),
    ]


@router.get("/shifts/{shift_id}")
async def get_shift(shift_id: str):
    """Get a specific shift."""
    return Shift(id=shift_id, staff_id="1", staff_name="John Doe", role="Server", date="2026-02-01", start_time="10:00", end_time="18:00", break_minutes=30, status="completed")


@router.post("/shifts")
async def create_shift(shift: Shift):
    """Create a new shift."""
    return {"success": True, "id": "new-id"}


@router.put("/shifts/{shift_id}")
async def update_shift(shift_id: str, shift: Shift):
    """Update a shift."""
    return {"success": True}


@router.delete("/shifts/{shift_id}")
async def delete_shift(shift_id: str):
    """Delete a shift."""
    return {"success": True}

"""Staff shifts API routes (v5 compatibility)."""

from datetime import date as date_type
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func

from app.db.session import DbSession
from app.models.operations import ShiftSchedule

router = APIRouter()


# ==================== Pydantic Schemas ====================

class StaffMember(BaseModel):
    id: str
    name: str
    role: str
    email: str
    phone: str
    hourly_rate: float
    status: str  # active, on_leave, inactive


class Shift(BaseModel):
    id: Optional[str] = None
    staff_id: str
    staff_name: str = ""
    role: str = ""
    date: str
    start_time: str
    end_time: str
    break_minutes: int = 0
    status: str = "scheduled"  # scheduled, in_progress, completed, missed
    actual_start: Optional[str] = None
    actual_end: Optional[str] = None
    notes: Optional[str] = None


# ==================== Helpers ====================

def _row_to_shift(row: ShiftSchedule) -> dict:
    """Convert a ShiftSchedule ORM row to a Shift-compatible dict."""
    return {
        "id": str(row.id),
        "staff_id": str(row.staff_id),
        "staff_name": row.staff_name or "",
        "role": row.role or "",
        "date": row.date.isoformat() if row.date else "",
        "start_time": row.start_time or "",
        "end_time": row.end_time or "",
        "break_minutes": row.break_minutes or 0,
        "status": row.status or "scheduled",
        "notes": row.notes,
    }


# ==================== Staff Endpoints ====================

@router.get("/staff")
def get_staff(db: DbSession):
    """Get all staff members (derived from shift_schedules)."""
    # Build a distinct list of staff from the shift_schedules table.
    rows = (
        db.query(
            ShiftSchedule.staff_id,
            ShiftSchedule.staff_name,
            ShiftSchedule.role,
        )
        .distinct(ShiftSchedule.staff_id)
        .order_by(ShiftSchedule.staff_id)
        .all()
    )
    return [
        StaffMember(
            id=str(r.staff_id),
            name=r.staff_name or "",
            role=r.role or "",
            email="",
            phone="",
            hourly_rate=0.0,
            status="active",
        )
        for r in rows
    ]


# ==================== Shift Endpoints ====================

@router.get("/shifts")
def get_shifts(
    db: DbSession,
    date: str = Query(None),
    staff_id: str = Query(None),
):
    """Get shifts with optional filters."""
    query = db.query(ShiftSchedule).order_by(ShiftSchedule.date.desc(), ShiftSchedule.start_time)

    if date:
        query = query.filter(ShiftSchedule.date == date)

    if staff_id:
        query = query.filter(ShiftSchedule.staff_id == int(staff_id))

    rows = query.all()
    return [_row_to_shift(r) for r in rows]


@router.get("/shifts/{shift_id}")
def get_shift(shift_id: str, db: DbSession):
    """Get a specific shift."""
    row = db.query(ShiftSchedule).filter(ShiftSchedule.id == int(shift_id)).first()
    if not row:
        raise HTTPException(status_code=404, detail="Shift not found")
    return _row_to_shift(row)


@router.post("/shifts")
def create_shift(shift: Shift, db: DbSession):
    """Create a new shift."""
    row = ShiftSchedule(
        staff_id=int(shift.staff_id),
        staff_name=shift.staff_name,
        role=shift.role,
        date=shift.date,
        start_time=shift.start_time,
        end_time=shift.end_time,
        break_minutes=shift.break_minutes,
        status=shift.status,
        notes=shift.notes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"success": True, "id": str(row.id)}


@router.put("/shifts/{shift_id}")
def update_shift(shift_id: str, shift: Shift, db: DbSession):
    """Update a shift."""
    row = db.query(ShiftSchedule).filter(ShiftSchedule.id == int(shift_id)).first()
    if not row:
        raise HTTPException(status_code=404, detail="Shift not found")

    row.staff_id = int(shift.staff_id)
    row.staff_name = shift.staff_name
    row.role = shift.role
    row.date = shift.date
    row.start_time = shift.start_time
    row.end_time = shift.end_time
    row.break_minutes = shift.break_minutes
    row.status = shift.status
    row.notes = shift.notes

    db.commit()
    db.refresh(row)
    return {"success": True}


@router.delete("/shifts/{shift_id}")
def delete_shift(shift_id: str, db: DbSession):
    """Delete a shift."""
    row = db.query(ShiftSchedule).filter(ShiftSchedule.id == int(shift_id)).first()
    if not row:
        raise HTTPException(status_code=404, detail="Shift not found")

    db.delete(row)
    db.commit()
    return {"success": True}


# ==================== CATERING ====================

from app.models.operations import AppSetting

CATERING_CATEGORY = "catering"
SMS_CATEGORY = "sms_marketing"


def _get_json_setting(db: DbSession, category: str, key: str):
    """Return the JSON value for a category+key, or None."""
    row = (
        db.query(AppSetting)
        .filter(AppSetting.category == category, AppSetting.key == key)
        .first()
    )
    return row.value if row else None


def _upsert_json_setting(db: DbSession, category: str, key: str, value):
    """Insert or update a JSON setting."""
    from datetime import datetime as _dt

    row = (
        db.query(AppSetting)
        .filter(AppSetting.category == category, AppSetting.key == key)
        .first()
    )
    if row:
        row.value = value
        row.updated_at = _dt.utcnow()
    else:
        row = AppSetting(category=category, key=key, value=value)
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/catering/events")
async def get_catering_events(db: DbSession):
    """Get catering events."""
    stored = _get_json_setting(db, CATERING_CATEGORY, "events")
    if stored and isinstance(stored, list):
        return stored
    return []


@router.post("/catering/events")
async def create_catering_event(data: dict, db: DbSession):
    """Create a catering event."""
    events = _get_json_setting(db, CATERING_CATEGORY, "events") or []
    new_id = str(len(events) + 1)
    data["id"] = new_id
    events.append(data)
    _upsert_json_setting(db, CATERING_CATEGORY, "events", events)
    return {"success": True, "id": new_id}


@router.get("/catering/packages")
async def get_catering_packages(db: DbSession):
    """Get catering packages."""
    stored = _get_json_setting(db, CATERING_CATEGORY, "packages")
    if stored and isinstance(stored, list):
        return stored
    return []


@router.post("/catering/packages")
async def create_catering_package(data: dict, db: DbSession):
    """Create a catering package."""
    packages = _get_json_setting(db, CATERING_CATEGORY, "packages") or []
    new_id = str(len(packages) + 1)
    data["id"] = new_id
    packages.append(data)
    _upsert_json_setting(db, CATERING_CATEGORY, "packages", packages)
    return {"success": True, "id": new_id}


@router.get("/catering/staff")
async def get_catering_staff(db: DbSession):
    """Get staff available for catering events."""
    stored = _get_json_setting(db, CATERING_CATEGORY, "staff")
    if stored and isinstance(stored, list):
        return stored
    return []


# ==================== SMS MARKETING ====================

@router.get("/sms/campaigns")
async def get_sms_campaigns(db: DbSession):
    """Get SMS marketing campaigns."""
    stored = _get_json_setting(db, SMS_CATEGORY, "campaigns")
    if stored and isinstance(stored, list):
        return stored
    return []


@router.post("/sms/campaigns")
async def create_sms_campaign(data: dict, db: DbSession):
    """Create an SMS campaign."""
    campaigns = _get_json_setting(db, SMS_CATEGORY, "campaigns") or []
    new_id = str(len(campaigns) + 1)
    data["id"] = new_id
    data.setdefault("status", "draft")
    data.setdefault("sent", 0)
    data.setdefault("delivered", 0)
    data.setdefault("opened", 0)
    data.setdefault("clicked", 0)
    campaigns.append(data)
    _upsert_json_setting(db, SMS_CATEGORY, "campaigns", campaigns)
    return {"success": True, "id": new_id}


@router.get("/sms/stats")
async def get_sms_stats(db: DbSession):
    """Get SMS marketing statistics."""
    campaigns = _get_json_setting(db, SMS_CATEGORY, "campaigns") or []
    total_sent = sum(c.get("sent", 0) for c in campaigns)
    total_delivered = sum(c.get("delivered", 0) for c in campaigns)
    total_opened = sum(c.get("opened", 0) for c in campaigns)
    total_clicked = sum(c.get("clicked", 0) for c in campaigns)

    delivery_rate = round((total_delivered / total_sent * 100), 1) if total_sent > 0 else 0.0
    avg_open_rate = round((total_opened / total_delivered * 100), 1) if total_delivered > 0 else 0.0
    avg_click_rate = round((total_clicked / total_delivered * 100), 1) if total_delivered > 0 else 0.0

    return {
        "total_campaigns": len(campaigns),
        "total_sent": total_sent,
        "total_delivered": total_delivered,
        "delivery_rate": delivery_rate,
        "avg_open_rate": avg_open_rate,
        "avg_click_rate": avg_click_rate,
        "credits_remaining": 0,
        "monthly_spend": 0.0,
    }


@router.post("/sms/campaigns/{campaign_id}/send")
async def send_sms_campaign(campaign_id: str, db: DbSession):
    """Send an SMS campaign."""
    campaigns = _get_json_setting(db, SMS_CATEGORY, "campaigns") or []
    for c in campaigns:
        if c.get("id") == campaign_id:
            c["status"] = "sending"
            break
    _upsert_json_setting(db, SMS_CATEGORY, "campaigns", campaigns)
    return {"success": True, "campaign_id": campaign_id, "status": "sending"}

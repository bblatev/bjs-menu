"""Staff CRUD, schedules & time off"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from typing import List, Dict, Optional, Any
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal

from app.core.rate_limit import limiter
from app.db.session import get_db

# Import shared helpers
from app.api.routes.staff._shared import *
from app.api.routes.staff._shared import _init_default_staff, _staff_to_dict, _shift_to_dict, _prefetch_staff_names, _time_entry_to_dict

router = APIRouter()

# ============== Staff CRUD ==============

@router.get("/staff")
@limiter.limit("60/minute")
def list_staff(
    request: Request,
    db: DbSession,
    role: Optional[str] = None,
    active_only: Optional[bool] = None,
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(50, ge=1, le=500, description="Maximum items to return"),
):
    """List all staff members with pagination."""
    _init_default_staff(db)

    query = db.query(StaffUser).filter(StaffUser.not_deleted())

    if role and role != "all":
        query = query.filter(StaffUser.role == role)
    if active_only is not None:
        query = query.filter(StaffUser.is_active == active_only)

    query = query.order_by(StaffUser.full_name)
    items, total = paginate_query(query, skip, limit)

    return {
        "items": [_staff_to_dict(s) for s in items],
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_more": (skip + len(items)) < total,
    }


@router.post("/staff")
@limiter.limit("30/minute")
def create_staff(request: Request, db: DbSession, data: StaffCreate, current_user: RequireManager):
    """Create a new staff member."""
    if data.role not in ["admin", "manager", "kitchen", "bar", "waiter"]:
        raise HTTPException(status_code=400, detail="Invalid role")

    if data.pin_code and (len(data.pin_code) < 4 or len(data.pin_code) > 6):
        raise HTTPException(status_code=400, detail="PIN must be 4-6 digits")

    staff = StaffUser(
        full_name=data.full_name,
        role=data.role,
        pin_hash=get_password_hash(data.pin_code) if data.pin_code else None,
        hourly_rate=data.hourly_rate,
        max_hours_week=data.max_hours_week,
        color=data.color or "#3B82F6",
    )
    db.add(staff)
    db.commit()
    db.refresh(staff)

    return _staff_to_dict(staff)


# Note: Staff ID routes moved to end of file to avoid catching specific paths

# ============== Schedules & Shifts ==============

@router.get("/staff/schedules/staff")
@limiter.limit("60/minute")
def get_scheduling_staff(request: Request, db: DbSession):
    """Get staff members for scheduling view."""
    _init_default_staff(db)
    staff = db.query(StaffUser).filter(StaffUser.is_active == True).all()

    return [
        {
            "id": s.id,
            "name": s.full_name,
            "role": s.role,
            "avatar_initials": "".join([n[0].upper() for n in s.full_name.split()[:2]]),
            "color": s.color or "#3B82F6",
            "hourly_rate": s.hourly_rate,
            "max_hours_week": s.max_hours_week,
        }
        for s in staff
    ]


@router.get("/staff/shifts")
@limiter.limit("60/minute")
def list_shifts(
    request: Request,
    db: DbSession,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    """List shifts for a date range."""
    if not start_date:
        start_date = (datetime.now(timezone.utc).date() - timedelta(days=30)).strftime("%Y-%m-%d")
    if not end_date:
        end_date = datetime.now(timezone.utc).date().strftime("%Y-%m-%d")
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    shifts = db.query(Shift).filter(
        and_(Shift.date >= start, Shift.date <= end)
    ).all()

    # Get staff names
    staff_ids = [s.staff_id for s in shifts]
    staff_map = {}
    if staff_ids:
        staff_list = db.query(StaffUser).filter(StaffUser.id.in_(staff_ids)).all()
        staff_map = {s.id: s.full_name for s in staff_list}

    return [_shift_to_dict(s, staff_map.get(s.staff_id)) for s in shifts]


@router.post("/staff/shifts")
@limiter.limit("30/minute")
def create_shift(request: Request, db: DbSession, data: ShiftCreate, current_user: RequireManager):
    """Create a new shift."""
    # Validate staff exists
    staff = db.query(StaffUser).filter(StaffUser.id == data.staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found")

    try:
        shift_date = datetime.strptime(data.date, "%Y-%m-%d").date()
        start_time = datetime.strptime(data.start_time, "%H:%M").time()
        end_time = datetime.strptime(data.end_time, "%H:%M").time()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date/time format")

    shift = Shift(
        staff_id=data.staff_id,
        date=shift_date,
        shift_type=data.shift_type,
        start_time=start_time,
        end_time=end_time,
        break_minutes=data.break_minutes,
        position=data.position,
        notes=data.notes,
    )
    db.add(shift)
    db.commit()
    db.refresh(shift)

    return _shift_to_dict(shift, staff.full_name)


@router.put("/staff/shifts/{shift_id}")
@limiter.limit("30/minute")
def update_shift(request: Request, db: DbSession, shift_id: int, data: ShiftUpdate):
    """Update a shift."""
    shift = db.query(Shift).filter(Shift.id == shift_id).first()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")

    if data.staff_id:
        shift.staff_id = data.staff_id
    if data.date:
        shift.date = datetime.strptime(data.date, "%Y-%m-%d").date()
    if data.shift_type:
        shift.shift_type = data.shift_type
    if data.start_time:
        shift.start_time = datetime.strptime(data.start_time, "%H:%M").time()
    if data.end_time:
        shift.end_time = datetime.strptime(data.end_time, "%H:%M").time()
    if data.break_minutes is not None:
        shift.break_minutes = data.break_minutes
    if data.status:
        shift.status = data.status
    if data.position is not None:
        shift.position = data.position
    if data.notes is not None:
        shift.notes = data.notes

    db.commit()
    db.refresh(shift)

    staff = db.query(StaffUser).filter(StaffUser.id == shift.staff_id).first()
    return _shift_to_dict(shift, staff.full_name if staff else None)


@router.delete("/staff/shifts/{shift_id}")
@limiter.limit("30/minute")
def delete_shift(request: Request, db: DbSession, shift_id: int):
    """Delete a shift."""
    shift = db.query(Shift).filter(Shift.id == shift_id).first()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")

    db.delete(shift)
    db.commit()
    return {"status": "deleted", "id": shift_id}


@router.post("/staff/shifts/copy-week")
@limiter.limit("30/minute")
def copy_week_shifts(request: Request, db: DbSession, data: dict = Body(...)):
    """Copy shifts from previous week."""
    try:
        target_start = datetime.strptime(data.get("target_start_date"), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid target_start_date")

    source_start = target_start - timedelta(days=7)
    source_end = source_start + timedelta(days=6)

    # Get source shifts
    source_shifts = db.query(Shift).filter(
        and_(Shift.date >= source_start, Shift.date <= source_end)
    ).all()

    created = 0
    for src in source_shifts:
        new_date = src.date + timedelta(days=7)
        new_shift = Shift(
            staff_id=src.staff_id,
            date=new_date,
            shift_type=src.shift_type,
            start_time=src.start_time,
            end_time=src.end_time,
            break_minutes=src.break_minutes,
            position=src.position,
            status="scheduled",
        )
        db.add(new_shift)
        created += 1

    db.commit()
    return {"status": "success", "shifts_copied": created}


@router.post("/staff/shifts/publish")
@limiter.limit("30/minute")
def publish_shifts(request: Request, db: DbSession, data: dict = Body(...)):
    """Publish shifts for a date range."""
    try:
        start = datetime.strptime(data.get("start_date"), "%Y-%m-%d").date()
        end = datetime.strptime(data.get("end_date"), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid date format")

    updated = db.query(Shift).filter(
        and_(Shift.date >= start, Shift.date <= end)
    ).update({"is_published": True})

    db.commit()
    return {"status": "success", "shifts_published": updated}


# ============== Time Off ==============

@router.get("/staff/time-off")
@limiter.limit("60/minute")
def list_time_off(
    request: Request,
    db: DbSession,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    """List time off requests for a date range."""
    if not start_date:
        start_date = (datetime.now(timezone.utc).date() - timedelta(days=30)).strftime("%Y-%m-%d")
    if not end_date:
        end_date = (datetime.now(timezone.utc).date() + timedelta(days=60)).strftime("%Y-%m-%d")
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    requests = db.query(TimeOffRequest).filter(
        or_(
            and_(TimeOffRequest.start_date >= start, TimeOffRequest.start_date <= end),
            and_(TimeOffRequest.end_date >= start, TimeOffRequest.end_date <= end),
        )
    ).all()

    staff_ids = [r.staff_id for r in requests]
    staff_names = _prefetch_staff_names(db, staff_ids)

    result = []
    for r in requests:
        result.append({
            "id": r.id,
            "staff_id": r.staff_id,
            "staff_name": staff_names.get(r.staff_id, "Unknown"),
            "start_date": r.start_date.isoformat(),
            "end_date": r.end_date.isoformat(),
            "type": r.type,
            "status": r.status,
            "notes": r.notes,
        })

    return result


@router.post("/staff/time-off")
@limiter.limit("30/minute")
def create_time_off(request: Request, db: DbSession, data: TimeOffCreate, current_user: CurrentUser):
    """Create a time off request."""
    staff = db.query(StaffUser).filter(StaffUser.id == data.staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found")

    try:
        start = datetime.strptime(data.start_date, "%Y-%m-%d").date()
        end = datetime.strptime(data.end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    time_off_request = TimeOffRequest(
        staff_id=data.staff_id,
        start_date=start,
        end_date=end,
        type=data.type,
        notes=data.notes,
    )
    db.add(time_off_request)
    db.commit()
    db.refresh(time_off_request)

    return {
        "id": time_off_request.id,
        "staff_id": time_off_request.staff_id,
        "staff_name": staff.full_name,
        "start_date": time_off_request.start_date.isoformat(),
        "end_date": time_off_request.end_date.isoformat(),
        "type": time_off_request.type,
        "status": time_off_request.status,
        "notes": time_off_request.notes,
    }


@router.patch("/staff/time-off/{request_id}/approve")
@limiter.limit("30/minute")
def approve_time_off(request: Request, db: DbSession, request_id: int, current_user: RequireManager):
    """Approve a time off request."""
    time_off_request = db.query(TimeOffRequest).filter(TimeOffRequest.id == request_id).first()
    if not time_off_request:
        raise HTTPException(status_code=404, detail="Time off request not found")

    time_off_request.status = "approved"
    time_off_request.reviewed_at = datetime.now(timezone.utc)
    db.commit()

    return {"status": "approved", "id": request_id}


@router.patch("/staff/time-off/{request_id}/reject")
@limiter.limit("30/minute")
def reject_time_off(request: Request, db: DbSession, request_id: int):
    """Reject a time off request."""
    time_off_request = db.query(TimeOffRequest).filter(TimeOffRequest.id == request_id).first()
    if not time_off_request:
        raise HTTPException(status_code=404, detail="Time off request not found")

    time_off_request.status = "rejected"
    time_off_request.reviewed_at = datetime.now(timezone.utc)
    db.commit()

    return {"status": "rejected", "id": request_id}


# ============== Time Clock ==============

@router.get("/staff/time-clock/status")
@limiter.limit("60/minute")
def get_clock_status(request: Request, db: DbSession, staff_id: Optional[int] = None):
    """Get current clock status."""
    # For now, return a default status - in production, use authenticated user
    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    query = db.query(TimeClockEntry)
    if staff_id:
        query = query.filter(TimeClockEntry.staff_id == staff_id)

    # Get current open entry
    current_entry = query.filter(TimeClockEntry.clock_out == None).first()

    # Calculate hours
    today_entries = query.filter(
        func.date(TimeClockEntry.clock_in) == today
    ).all()

    today_hours = sum(e.total_hours or 0 for e in today_entries if e.total_hours)

    week_entries = query.filter(
        func.date(TimeClockEntry.clock_in) >= week_start
    ).all()
    week_hours = sum(e.total_hours or 0 for e in week_entries if e.total_hours)

    return {
        "is_clocked_in": current_entry is not None,
        "is_on_break": current_entry.status == "on_break" if current_entry else False,
        "current_entry": _time_entry_to_dict(current_entry) if current_entry else None,
        "today_hours": round(today_hours, 2),
        "week_hours": round(week_hours, 2),
    }


@router.get("/staff/time-clock/entries")
@limiter.limit("60/minute")
def list_time_entries(
    request: Request,
    db: DbSession,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    staff_id: Optional[int] = None,
):
    """List time clock entries for a date range."""
    if not start_date:
        start_date = (datetime.now(timezone.utc).date() - timedelta(days=30)).strftime("%Y-%m-%d")
    if not end_date:
        end_date = datetime.now(timezone.utc).date().strftime("%Y-%m-%d")
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    query = db.query(TimeClockEntry).filter(
        func.date(TimeClockEntry.clock_in) >= start,
        func.date(TimeClockEntry.clock_in) <= end,
    )

    if staff_id:
        query = query.filter(TimeClockEntry.staff_id == staff_id)

    entries = query.order_by(TimeClockEntry.clock_in.desc()).all()

    # Get staff names
    staff_ids = list(set(e.staff_id for e in entries))
    staff_map = {}
    if staff_ids:
        staff_list = db.query(StaffUser).filter(StaffUser.id.in_(staff_ids)).all()
        staff_map = {s.id: s.full_name for s in staff_list}

    return [_time_entry_to_dict(e, staff_map.get(e.staff_id)) for e in entries]


@router.post("/staff/time-clock/punch-in")
@limiter.limit("30/minute")
def punch_in(request: Request, db: DbSession, current_user: CurrentUser, data: dict = Body(...)):
    """Clock in."""
    staff_id = data.get("staff_id")
    method = data.get("method", "web")

    if not staff_id:
        raise HTTPException(status_code=400, detail="staff_id is required")

    staff = db.query(StaffUser).filter(StaffUser.id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found")

    # Check if already clocked in
    existing = db.query(TimeClockEntry).filter(
        TimeClockEntry.staff_id == staff_id,
        TimeClockEntry.clock_out == None,
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Already clocked in")

    entry = TimeClockEntry(
        staff_id=staff_id,
        clock_in=datetime.now(timezone.utc),
        status="clocked_in",
        clock_in_method=method,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    return _time_entry_to_dict(entry, staff.full_name)


@router.post("/staff/time-clock/punch-out")
@limiter.limit("30/minute")
def punch_out(request: Request, db: DbSession, current_user: CurrentUser, data: dict = Body(...)):
    """Clock out."""
    staff_id = data.get("staff_id")

    if not staff_id:
        raise HTTPException(status_code=400, detail="staff_id is required")

    entry = db.query(TimeClockEntry).filter(
        TimeClockEntry.staff_id == staff_id,
        TimeClockEntry.clock_out == None,
    ).first()

    if not entry:
        raise HTTPException(status_code=400, detail="Not clocked in")

    now = datetime.now(timezone.utc)
    entry.clock_out = now
    entry.status = "clocked_out"

    # Calculate hours - ensure both datetimes are timezone-aware
    clock_in = entry.clock_in.replace(tzinfo=timezone.utc) if entry.clock_in.tzinfo is None else entry.clock_in
    delta = now - clock_in
    total_hours = delta.total_seconds() / 3600

    # Subtract break time if applicable
    break_hours = 0
    if entry.break_start and entry.break_end:
        bs = entry.break_start.replace(tzinfo=timezone.utc) if entry.break_start.tzinfo is None else entry.break_start
        be = entry.break_end.replace(tzinfo=timezone.utc) if entry.break_end.tzinfo is None else entry.break_end
        break_delta = be - bs
        break_hours = break_delta.total_seconds() / 3600

    entry.total_hours = round(total_hours - break_hours, 2)
    entry.break_hours = round(break_hours, 2)

    db.commit()
    db.refresh(entry)

    staff = db.query(StaffUser).filter(StaffUser.id == staff_id).first()
    return _time_entry_to_dict(entry, staff.full_name if staff else None)


@router.post("/staff/time-clock/break/start")
@limiter.limit("30/minute")
def start_break(request: Request, db: DbSession, data: dict = Body(...)):
    """Start break."""
    staff_id = data.get("staff_id")

    if not staff_id:
        raise HTTPException(status_code=400, detail="staff_id is required")

    entry = db.query(TimeClockEntry).filter(
        TimeClockEntry.staff_id == staff_id,
        TimeClockEntry.clock_out == None,
    ).first()

    if not entry:
        raise HTTPException(status_code=400, detail="Not clocked in")

    if entry.status == "on_break":
        raise HTTPException(status_code=400, detail="Already on break")

    entry.break_start = datetime.now(timezone.utc)
    entry.status = "on_break"
    db.commit()
    db.refresh(entry)

    staff = db.query(StaffUser).filter(StaffUser.id == staff_id).first()
    return _time_entry_to_dict(entry, staff.full_name if staff else None)


@router.post("/staff/time-clock/break/end")
@limiter.limit("30/minute")
def end_break(request: Request, db: DbSession, data: dict = Body(...)):
    """End break."""
    staff_id = data.get("staff_id")

    if not staff_id:
        raise HTTPException(status_code=400, detail="staff_id is required")

    entry = db.query(TimeClockEntry).filter(
        TimeClockEntry.staff_id == staff_id,
        TimeClockEntry.clock_out == None,
    ).first()

    if not entry:
        raise HTTPException(status_code=400, detail="Not clocked in")

    if entry.status != "on_break":
        raise HTTPException(status_code=400, detail="Not on break")

    now = datetime.now(timezone.utc)
    entry.break_end = now
    entry.status = "clocked_in"

    # Calculate break hours - ensure both datetimes are timezone-aware
    if entry.break_start:
        bs = entry.break_start.replace(tzinfo=timezone.utc) if entry.break_start.tzinfo is None else entry.break_start
        break_delta = now - bs
        entry.break_hours = round(break_delta.total_seconds() / 3600, 2)

    db.commit()
    db.refresh(entry)

    staff = db.query(StaffUser).filter(StaffUser.id == staff_id).first()
    return _time_entry_to_dict(entry, staff.full_name if staff else None)



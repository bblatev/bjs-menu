"""Staff management routes - comprehensive CRUD for staff, shifts, time clock, performance, tips."""

from typing import List, Optional, Dict
from datetime import datetime, date, time, timedelta
from fastapi import APIRouter, HTTPException, Body, Query
from sqlalchemy import func, and_, or_

from app.core.security import get_password_hash, verify_password
from app.db.session import DbSession
from app.models.staff import (
    StaffUser, Shift, TimeOffRequest, TimeClockEntry,
    TableAssignment, PerformanceMetric, PerformanceGoal,
    TipPool, TipDistribution
)
from app.schemas.staff import (
    StaffCreate, StaffUpdate, StaffResponse,
    ShiftCreate, ShiftUpdate, ShiftResponse,
    TimeOffCreate, TimeOffResponse,
    TipPoolCreate, TipPoolResponse,
    TimeClockEntryResponse,
)

router = APIRouter()


# ============== Helper Functions ==============

def _prefetch_staff_names(db: DbSession, staff_ids: List[int]) -> Dict[int, str]:
    """Batch fetch staff names to avoid N+1 queries."""
    if not staff_ids:
        return {}
    staff_list = db.query(StaffUser.id, StaffUser.full_name).filter(
        StaffUser.id.in_(staff_ids)
    ).all()
    return {s.id: s.full_name for s in staff_list}


def _staff_to_dict(staff: StaffUser) -> dict:
    """Convert StaffUser to response dict."""
    return {
        "id": staff.id,
        "full_name": staff.full_name,
        "role": staff.role,
        "active": staff.is_active,
        "has_pin": staff.pin_hash is not None,
        "hourly_rate": staff.hourly_rate,
        "max_hours_week": staff.max_hours_week,
        "color": staff.color,
        "commission_percentage": staff.commission_percentage if hasattr(staff, 'commission_percentage') and staff.commission_percentage is not None else 0.0,
        "service_fee_percentage": staff.service_fee_percentage if hasattr(staff, 'service_fee_percentage') and staff.service_fee_percentage is not None else 0.0,
        "auto_logout_after_close": staff.auto_logout_after_close if hasattr(staff, 'auto_logout_after_close') and staff.auto_logout_after_close is not None else False,
        "created_at": staff.created_at.isoformat() if staff.created_at else None,
        "last_login": staff.last_login.isoformat() if staff.last_login else None,
    }


def _shift_to_dict(shift: Shift, staff_name: str = None) -> dict:
    """Convert Shift to response dict."""
    return {
        "id": shift.id,
        "staff_id": shift.staff_id,
        "staff_name": staff_name,
        "date": shift.date.isoformat() if shift.date else None,
        "shift_type": shift.shift_type,
        "start_time": shift.start_time.strftime("%H:%M") if shift.start_time else None,
        "end_time": shift.end_time.strftime("%H:%M") if shift.end_time else None,
        "break_minutes": shift.break_minutes,
        "status": shift.status,
        "position": shift.position,
        "notes": shift.notes,
        "is_published": shift.is_published,
    }


def _time_entry_to_dict(entry: TimeClockEntry, staff_name: str = None) -> dict:
    """Convert TimeClockEntry to response dict."""
    return {
        "id": entry.id,
        "staff_id": entry.staff_id,
        "staff_name": staff_name,
        "clock_in": entry.clock_in.isoformat() if entry.clock_in else None,
        "clock_out": entry.clock_out.isoformat() if entry.clock_out else None,
        "break_start": entry.break_start.isoformat() if entry.break_start else None,
        "break_end": entry.break_end.isoformat() if entry.break_end else None,
        "total_hours": entry.total_hours,
        "break_hours": entry.break_hours,
        "status": entry.status,
        "clock_in_method": entry.clock_in_method,
    }


# ============== Staff CRUD ==============

@router.get("/staff")
def list_staff(
    db: DbSession,
    role: Optional[str] = None,
    active_only: Optional[bool] = None,
):
    """List all staff members."""
    _init_default_staff(db)

    query = db.query(StaffUser)

    if role and role != "all":
        query = query.filter(StaffUser.role == role)
    if active_only is not None:
        query = query.filter(StaffUser.is_active == active_only)

    staff = query.order_by(StaffUser.full_name).all()
    return [_staff_to_dict(s) for s in staff]


@router.post("/staff")
def create_staff(db: DbSession, data: StaffCreate):
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
def get_scheduling_staff(db: DbSession):
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
def list_shifts(
    db: DbSession,
    start_date: str = Query(...),
    end_date: str = Query(...),
):
    """List shifts for a date range."""
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
def create_shift(db: DbSession, data: ShiftCreate):
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
def update_shift(db: DbSession, shift_id: int, data: ShiftUpdate):
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
def delete_shift(db: DbSession, shift_id: int):
    """Delete a shift."""
    shift = db.query(Shift).filter(Shift.id == shift_id).first()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")

    db.delete(shift)
    db.commit()
    return {"status": "deleted", "id": shift_id}


@router.post("/staff/shifts/copy-week")
def copy_week_shifts(db: DbSession, data: dict = Body(...)):
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
def publish_shifts(db: DbSession, data: dict = Body(...)):
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
def list_time_off(
    db: DbSession,
    start_date: str = Query(...),
    end_date: str = Query(...),
):
    """List time off requests for a date range."""
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

    result = []
    for r in requests:
        staff = db.query(StaffUser).filter(StaffUser.id == r.staff_id).first()
        result.append({
            "id": r.id,
            "staff_id": r.staff_id,
            "staff_name": staff.full_name if staff else None,
            "start_date": r.start_date.isoformat(),
            "end_date": r.end_date.isoformat(),
            "type": r.type,
            "status": r.status,
            "notes": r.notes,
        })

    return result


@router.post("/staff/time-off")
def create_time_off(db: DbSession, data: TimeOffCreate):
    """Create a time off request."""
    staff = db.query(StaffUser).filter(StaffUser.id == data.staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found")

    try:
        start = datetime.strptime(data.start_date, "%Y-%m-%d").date()
        end = datetime.strptime(data.end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    request = TimeOffRequest(
        staff_id=data.staff_id,
        start_date=start,
        end_date=end,
        type=data.type,
        notes=data.notes,
    )
    db.add(request)
    db.commit()
    db.refresh(request)

    return {
        "id": request.id,
        "staff_id": request.staff_id,
        "staff_name": staff.full_name,
        "start_date": request.start_date.isoformat(),
        "end_date": request.end_date.isoformat(),
        "type": request.type,
        "status": request.status,
        "notes": request.notes,
    }


@router.patch("/staff/time-off/{request_id}/approve")
def approve_time_off(db: DbSession, request_id: int):
    """Approve a time off request."""
    request = db.query(TimeOffRequest).filter(TimeOffRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Time off request not found")

    request.status = "approved"
    request.reviewed_at = datetime.utcnow()
    db.commit()

    return {"status": "approved", "id": request_id}


@router.patch("/staff/time-off/{request_id}/reject")
def reject_time_off(db: DbSession, request_id: int):
    """Reject a time off request."""
    request = db.query(TimeOffRequest).filter(TimeOffRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Time off request not found")

    request.status = "rejected"
    request.reviewed_at = datetime.utcnow()
    db.commit()

    return {"status": "rejected", "id": request_id}


# ============== Time Clock ==============

@router.get("/staff/time-clock/status")
def get_clock_status(db: DbSession, staff_id: Optional[int] = None):
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
def list_time_entries(
    db: DbSession,
    start_date: str = Query(...),
    end_date: str = Query(...),
    staff_id: Optional[int] = None,
):
    """List time clock entries for a date range."""
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
def punch_in(db: DbSession, data: dict = Body(...)):
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
        clock_in=datetime.utcnow(),
        status="clocked_in",
        clock_in_method=method,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    return _time_entry_to_dict(entry, staff.full_name)


@router.post("/staff/time-clock/punch-out")
def punch_out(db: DbSession, data: dict = Body(...)):
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

    entry.clock_out = datetime.utcnow()
    entry.status = "clocked_out"

    # Calculate hours
    delta = entry.clock_out - entry.clock_in
    total_hours = delta.total_seconds() / 3600

    # Subtract break time if applicable
    break_hours = 0
    if entry.break_start and entry.break_end:
        break_delta = entry.break_end - entry.break_start
        break_hours = break_delta.total_seconds() / 3600

    entry.total_hours = round(total_hours - break_hours, 2)
    entry.break_hours = round(break_hours, 2)

    db.commit()
    db.refresh(entry)

    staff = db.query(StaffUser).filter(StaffUser.id == staff_id).first()
    return _time_entry_to_dict(entry, staff.full_name if staff else None)


@router.post("/staff/time-clock/break/start")
def start_break(db: DbSession, data: dict = Body(...)):
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

    entry.break_start = datetime.utcnow()
    entry.status = "on_break"
    db.commit()
    db.refresh(entry)

    staff = db.query(StaffUser).filter(StaffUser.id == staff_id).first()
    return _time_entry_to_dict(entry, staff.full_name if staff else None)


@router.post("/staff/time-clock/break/end")
def end_break(db: DbSession, data: dict = Body(...)):
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

    entry.break_end = datetime.utcnow()
    entry.status = "clocked_in"

    # Calculate break hours
    if entry.break_start:
        break_delta = entry.break_end - entry.break_start
        entry.break_hours = round(break_delta.total_seconds() / 3600, 2)

    db.commit()
    db.refresh(entry)

    staff = db.query(StaffUser).filter(StaffUser.id == staff_id).first()
    return _time_entry_to_dict(entry, staff.full_name if staff else None)


# ============== Performance ==============

@router.get("/staff/performance/leaderboard")
def get_leaderboard(
    db: DbSession,
    period: str = Query("month"),
    sort_by: str = Query("sales"),
):
    """Get performance leaderboard."""
    _init_default_staff(db)

    # Get all active staff
    staff = db.query(StaffUser).filter(StaffUser.is_active == True).all()

    # Generate sample metrics for demo
    import random
    leaderboard = []

    for i, s in enumerate(staff):
        sales = random.uniform(500, 5000)
        orders = random.randint(20, 100)
        hours = random.uniform(20, 45)

        leaderboard.append({
            "rank": i + 1,
            "staff": {
                "id": s.id,
                "name": s.full_name,
                "role": s.role,
                "avatar_initials": "".join([n[0].upper() for n in s.full_name.split()[:2]]),
                "color": s.color or "#3B82F6",
            },
            "metrics": {
                "sales_amount": round(sales, 2),
                "orders_count": orders,
                "avg_ticket": round(sales / orders, 2) if orders > 0 else 0,
                "tips_received": round(sales * 0.18, 2),
                "hours_worked": round(hours, 1),
                "sales_per_hour": round(sales / hours, 2) if hours > 0 else 0,
                "customer_rating": round(random.uniform(4.0, 5.0), 1),
                "reviews_count": random.randint(5, 30),
            },
            "change": random.randint(-3, 3),
        })

    # Sort by selected metric
    if sort_by == "sales":
        leaderboard.sort(key=lambda x: x["metrics"]["sales_amount"], reverse=True)
    elif sort_by == "orders":
        leaderboard.sort(key=lambda x: x["metrics"]["orders_count"], reverse=True)
    elif sort_by == "tips":
        leaderboard.sort(key=lambda x: x["metrics"]["tips_received"], reverse=True)
    elif sort_by == "rating":
        leaderboard.sort(key=lambda x: x["metrics"]["customer_rating"], reverse=True)

    # Update ranks
    for i, item in enumerate(leaderboard):
        item["rank"] = i + 1

    return leaderboard


@router.get("/staff/performance/goals")
def get_performance_goals(db: DbSession):
    """Get performance goals."""
    goals = db.query(PerformanceGoal).all()

    if not goals:
        # Return default goals
        return [
            {"id": 1, "metric": "Daily Sales", "target": 5000, "current": 3750, "unit": "$", "period": "day"},
            {"id": 2, "metric": "Average Ticket", "target": 45, "current": 38, "unit": "$", "period": "day"},
            {"id": 3, "metric": "Customer Rating", "target": 4.8, "current": 4.6, "unit": "stars", "period": "month"},
            {"id": 4, "metric": "Table Turnover", "target": 3.0, "current": 2.5, "unit": "turns/day", "period": "day"},
        ]

    return [
        {
            "id": g.id,
            "metric": g.metric,
            "target": g.target_value,
            "current": g.current_value,
            "unit": g.unit,
            "period": g.period,
        }
        for g in goals
    ]


@router.put("/staff/performance/goals")
def update_performance_goals(db: DbSession, data: List[dict] = Body(...)):
    """Update performance goals."""
    for goal_data in data:
        goal_id = goal_data.get("id")
        if goal_id:
            goal = db.query(PerformanceGoal).filter(PerformanceGoal.id == goal_id).first()
            if goal:
                goal.target_value = goal_data.get("target", goal.target_value)
                goal.current_value = goal_data.get("current", goal.current_value)
        else:
            # Create new goal
            goal = PerformanceGoal(
                metric=goal_data.get("metric", "New Goal"),
                target_value=goal_data.get("target", 0),
                current_value=goal_data.get("current", 0),
                unit=goal_data.get("unit", ""),
                period=goal_data.get("period", "day"),
            )
            db.add(goal)

    db.commit()
    return {"status": "success"}


# ============== Sections ==============

@router.get("/staff/sections/servers")
def get_servers_for_sections(db: DbSession):
    """Get servers and bartenders for section assignment."""
    _init_default_staff(db)

    staff = db.query(StaffUser).filter(
        StaffUser.is_active == True,
        StaffUser.role.in_(["waiter", "bar"]),
    ).all()

    # Calculate current assignments and sales
    today = date.today()

    result = []
    for s in staff:
        # Get current table assignments
        assignments = db.query(TableAssignment).filter(
            TableAssignment.staff_id == s.id,
            TableAssignment.is_active == True,
        ).count()

        result.append({
            "id": s.id,
            "name": s.full_name,
            "avatar_initials": "".join([n[0].upper() for n in s.full_name.split()[:2]]),
            "color": s.color or "#3B82F6",
            "role": s.role,
            "status": "on_shift",  # Could check time clock
            "current_tables": assignments,
            "current_covers": assignments * 3,  # Estimate
            "sales_today": 0,  # Would need to calculate from orders
        })

    return result


@router.get("/tables/assignments")
def get_table_assignments(
    db: DbSession,
    staff_user_id: Optional[int] = None,
):
    """Get table assignments."""
    query = db.query(TableAssignment).filter(TableAssignment.is_active == True)

    if staff_user_id:
        query = query.filter(TableAssignment.staff_id == staff_user_id)

    assignments = query.all()

    return [
        {
            "id": a.id,
            "staff_user_id": a.staff_id,
            "table_id": a.table_id,
            "area": a.area,
            "venue_id": a.location_id,
            "active": a.is_active,
        }
        for a in assignments
    ]


@router.post("/tables/assignments/bulk")
def bulk_assign_tables(db: DbSession, data: dict = Body(...)):
    """Bulk assign tables to a staff member."""
    staff_id = data.get("staff_user_id")
    table_ids = data.get("table_ids", [])
    areas = data.get("areas", [])

    if not staff_id:
        raise HTTPException(status_code=400, detail="staff_user_id is required")

    staff = db.query(StaffUser).filter(StaffUser.id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found")

    # Deactivate existing assignments
    db.query(TableAssignment).filter(
        TableAssignment.staff_id == staff_id
    ).update({"is_active": False})

    # Create new table assignments
    for table_id in table_ids:
        assignment = TableAssignment(
            staff_id=staff_id,
            table_id=table_id,
            is_active=True,
        )
        db.add(assignment)

    # Create area assignments
    for area in areas:
        assignment = TableAssignment(
            staff_id=staff_id,
            area=area,
            is_active=True,
        )
        db.add(assignment)

    db.commit()

    return {"status": "success", "tables_assigned": len(table_ids), "areas_assigned": len(areas)}


@router.post("/tables/sections/{section_id}/assign")
def assign_section(db: DbSession, section_id: int, data: dict = Body(...)):
    """Assign a server to a section."""
    server_id = data.get("server_id")

    if not server_id:
        raise HTTPException(status_code=400, detail="server_id is required")

    # Create assignment for the section
    assignment = TableAssignment(
        staff_id=server_id,
        area=f"Section {section_id}",
        is_active=True,
    )
    db.add(assignment)
    db.commit()

    return {"status": "success", "section_id": section_id, "server_id": server_id}


# ============== Tips ==============

@router.get("/tips/pools")
def list_tip_pools(
    db: DbSession,
    range: str = Query("week"),
):
    """List tip pools for a date range."""
    today = date.today()

    if range == "day":
        start_date = today
    elif range == "week":
        start_date = today - timedelta(days=7)
    elif range == "month":
        start_date = today - timedelta(days=30)
    else:
        start_date = today - timedelta(days=7)

    pools = db.query(TipPool).filter(TipPool.date >= start_date).order_by(TipPool.date.desc()).all()

    result = []
    for p in pools:
        distributions = db.query(TipDistribution).filter(TipDistribution.pool_id == p.id).all()
        result.append({
            "id": p.id,
            "date": p.date.isoformat(),
            "shift": p.shift,
            "total_tips_cash": p.total_tips_cash,
            "total_tips_card": p.total_tips_card,
            "total_tips": p.total_tips,
            "participants": p.participants_count,
            "distribution_method": p.distribution_method,
            "status": p.status,
            "distributed_at": p.distributed_at.isoformat() if p.distributed_at else None,
            "distributions": [
                {
                    "staff_id": d.staff_id,
                    "hours_worked": d.hours_worked,
                    "points": d.points,
                    "share_percentage": d.share_percentage,
                    "amount": d.amount,
                    "paid": d.is_paid,
                }
                for d in distributions
            ],
        })

    return result


@router.post("/tips/pools")
def create_tip_pool(db: DbSession, data: TipPoolCreate):
    """Create a new tip pool."""
    try:
        pool_date = datetime.strptime(data.date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    total_tips = data.total_tips_cash + data.total_tips_card

    pool = TipPool(
        date=pool_date,
        shift=data.shift,
        total_tips_cash=data.total_tips_cash,
        total_tips_card=data.total_tips_card,
        total_tips=total_tips,
        participants_count=len(data.participant_ids),
        distribution_method=data.distribution_method,
        status="pending",
    )
    db.add(pool)
    db.commit()
    db.refresh(pool)

    # Create distributions if participants specified
    if data.participant_ids:
        share = total_tips / len(data.participant_ids) if data.distribution_method == "equal" else 0
        for staff_id in data.participant_ids:
            dist = TipDistribution(
                pool_id=pool.id,
                staff_id=staff_id,
                share_percentage=100 / len(data.participant_ids),
                amount=share,
            )
            db.add(dist)
        db.commit()

    return {
        "id": pool.id,
        "date": pool.date.isoformat(),
        "total_tips": pool.total_tips,
        "status": pool.status,
    }


@router.get("/tips/stats")
def get_tip_stats(
    db: DbSession,
    range: str = Query("week"),
):
    """Get tip statistics."""
    today = date.today()
    week_start = today - timedelta(days=7)
    month_start = today - timedelta(days=30)

    # Calculate stats from tip pools
    today_tips = db.query(func.sum(TipPool.total_tips)).filter(TipPool.date == today).scalar() or 0
    week_tips = db.query(func.sum(TipPool.total_tips)).filter(TipPool.date >= week_start).scalar() or 0
    month_tips = db.query(func.sum(TipPool.total_tips)).filter(TipPool.date >= month_start).scalar() or 0

    pending = db.query(func.sum(TipPool.total_tips)).filter(TipPool.status == "pending").scalar() or 0

    return {
        "totalTipsToday": float(today_tips),
        "totalTipsWeek": float(week_tips),
        "totalTipsMonth": float(month_tips),
        "avgTipPerHour": round(float(week_tips) / 168, 2) if week_tips else 0,  # Rough estimate
        "pendingDistribution": float(pending),
        "topEarner": "John Smith",  # Would need to calculate
    }


@router.get("/tips/earnings")
def get_tip_earnings(
    db: DbSession,
    range: str = Query("week"),
):
    """Get individual tip earnings."""
    today = date.today()

    if range == "week":
        start_date = today - timedelta(days=7)
    elif range == "month":
        start_date = today - timedelta(days=30)
    else:
        start_date = today

    # Get distributions with staff info
    distributions = db.query(
        TipDistribution.staff_id,
        func.sum(TipDistribution.amount).label("total"),
        func.sum(TipDistribution.hours_worked).label("hours"),
    ).join(TipPool).filter(
        TipPool.date >= start_date
    ).group_by(TipDistribution.staff_id).all()

    result = []
    for d in distributions:
        staff = db.query(StaffUser).filter(StaffUser.id == d.staff_id).first()
        if staff:
            result.append({
                "staff_id": d.staff_id,
                "staff_name": staff.full_name,
                "role": staff.role,
                "total_tips": float(d.total or 0),
                "hours_worked": float(d.hours or 0),
                "avg_per_hour": round(float(d.total or 0) / float(d.hours or 1), 2),
            })

    return result


@router.post("/tips/distributions")
def distribute_tips(db: DbSession, data: dict = Body(...)):
    """Distribute tips from a pool."""
    pool_id = data.get("pool_id")

    if not pool_id:
        raise HTTPException(status_code=400, detail="pool_id is required")

    pool = db.query(TipPool).filter(TipPool.id == pool_id).first()
    if not pool:
        raise HTTPException(status_code=404, detail="Tip pool not found")

    pool.status = "distributed"
    pool.distributed_at = datetime.utcnow()
    db.commit()

    return {"status": "success", "pool_id": pool_id}


# ============== Staff CRUD by ID (must be at end to avoid catching specific routes) ==============

@router.get("/staff/{staff_id}")
def get_staff(db: DbSession, staff_id: int):
    """Get a specific staff member."""
    staff = db.query(StaffUser).filter(StaffUser.id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found")
    return _staff_to_dict(staff)


@router.put("/staff/{staff_id}")
def update_staff(db: DbSession, staff_id: int, data: StaffUpdate):
    """Update a staff member."""
    staff = db.query(StaffUser).filter(StaffUser.id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found")

    if data.full_name:
        staff.full_name = data.full_name
    if data.role:
        if data.role not in ["admin", "manager", "kitchen", "bar", "waiter"]:
            raise HTTPException(status_code=400, detail="Invalid role")
        staff.role = data.role
    if data.hourly_rate is not None:
        staff.hourly_rate = data.hourly_rate
    if data.max_hours_week is not None:
        staff.max_hours_week = data.max_hours_week
    if data.color:
        staff.color = data.color

    db.commit()
    db.refresh(staff)
    return _staff_to_dict(staff)


@router.delete("/staff/{staff_id}")
def delete_staff(db: DbSession, staff_id: int):
    """Delete a staff member."""
    staff = db.query(StaffUser).filter(StaffUser.id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found")

    db.delete(staff)
    db.commit()
    return {"status": "deleted", "id": staff_id}


@router.patch("/staff/{staff_id}/activate")
def activate_staff(db: DbSession, staff_id: int):
    """Activate a staff member."""
    staff = db.query(StaffUser).filter(StaffUser.id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found")

    staff.is_active = True
    db.commit()
    db.refresh(staff)
    return _staff_to_dict(staff)


@router.patch("/staff/{staff_id}/deactivate")
def deactivate_staff(db: DbSession, staff_id: int):
    """Deactivate a staff member."""
    staff = db.query(StaffUser).filter(StaffUser.id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found")

    staff.is_active = False
    db.commit()
    db.refresh(staff)
    return _staff_to_dict(staff)


@router.patch("/staff/{staff_id}/pin")
def set_staff_pin(db: DbSession, staff_id: int, data: dict = Body(...)):
    """Set PIN for a staff member."""
    staff = db.query(StaffUser).filter(StaffUser.id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found")

    pin_code = data.get("pin_code")
    if not pin_code:
        raise HTTPException(status_code=400, detail="pin_code is required")
    if len(pin_code) < 4 or len(pin_code) > 6:
        raise HTTPException(status_code=400, detail="PIN must be 4-6 digits")
    if not pin_code.isdigit():
        raise HTTPException(status_code=400, detail="PIN must contain only numbers")

    staff.pin_hash = get_password_hash(pin_code)
    db.commit()
    db.refresh(staff)
    return _staff_to_dict(staff)


@router.post("/staff/{staff_id}/verify-pin")
def verify_staff_pin(db: DbSession, staff_id: int, data: dict = Body(...)):
    """Verify PIN for a staff member."""
    staff = db.query(StaffUser).filter(StaffUser.id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found")

    pin_code = data.get("pin_code")
    if not pin_code:
        raise HTTPException(status_code=400, detail="pin_code is required")

    if not staff.pin_hash:
        raise HTTPException(status_code=401, detail="Staff member has no PIN set")

    if not verify_password(pin_code, staff.pin_hash):
        raise HTTPException(status_code=401, detail="Invalid PIN")

    return {"valid": True, "staff_id": staff.id, "name": staff.full_name}


@router.delete("/staff/{staff_id}/pin")
def remove_staff_pin(db: DbSession, staff_id: int):
    """Remove PIN from a staff member."""
    staff = db.query(StaffUser).filter(StaffUser.id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found")

    staff.pin_hash = None
    db.commit()
    db.refresh(staff)
    return _staff_to_dict(staff)


# ============== Service Deduction Reports ==============

@router.get("/staff/reports/service-deductions")
def get_service_deduction_report(
    db: DbSession,
    start_date: str = Query(...),
    end_date: str = Query(...),
    staff_id: Optional[int] = None,
):
    """
    Generate service deduction report for staff.
    Shows gross sales, commission earned, service fees, and net earnings.
    """
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    # Get staff with commission/service fee settings
    query = db.query(StaffUser).filter(StaffUser.is_active == True)
    if staff_id:
        query = query.filter(StaffUser.id == staff_id)

    staff_list = query.all()

    report = []
    total_gross_sales = 0
    total_commission = 0
    total_service_fees = 0
    total_net_earnings = 0

    for staff in staff_list:
        # Get performance metrics for the period
        metrics = db.query(PerformanceMetric).filter(
            PerformanceMetric.staff_id == staff.id,
            PerformanceMetric.period_date >= start,
            PerformanceMetric.period_date <= end,
        ).all()

        gross_sales = sum(m.sales_amount for m in metrics) if metrics else 0
        tips_received = sum(m.tips_received for m in metrics) if metrics else 0
        hours_worked = sum(m.hours_worked for m in metrics) if metrics else 0

        # Calculate commission and service fees
        commission_pct = getattr(staff, 'commission_percentage', 0.0) or 0.0
        service_fee_pct = getattr(staff, 'service_fee_percentage', 0.0) or 0.0

        commission_earned = gross_sales * (commission_pct / 100)
        service_fee_deducted = gross_sales * (service_fee_pct / 100)

        # Calculate base pay
        base_pay = hours_worked * staff.hourly_rate

        # Net earnings = base pay + commission + tips - service fees
        net_earnings = base_pay + commission_earned + tips_received - service_fee_deducted

        staff_report = {
            "staff_id": staff.id,
            "staff_name": staff.full_name,
            "role": staff.role,
            "hours_worked": round(hours_worked, 2),
            "hourly_rate": staff.hourly_rate,
            "base_pay": round(base_pay, 2),
            "gross_sales": round(gross_sales, 2),
            "commission_percentage": commission_pct,
            "commission_earned": round(commission_earned, 2),
            "tips_received": round(tips_received, 2),
            "service_fee_percentage": service_fee_pct,
            "service_fee_deducted": round(service_fee_deducted, 2),
            "net_earnings": round(net_earnings, 2),
        }

        report.append(staff_report)

        total_gross_sales += gross_sales
        total_commission += commission_earned
        total_service_fees += service_fee_deducted
        total_net_earnings += net_earnings

    return {
        "period": {
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
        },
        "summary": {
            "total_staff": len(report),
            "total_gross_sales": round(total_gross_sales, 2),
            "total_commission_paid": round(total_commission, 2),
            "total_service_fees_collected": round(total_service_fees, 2),
            "total_net_earnings": round(total_net_earnings, 2),
        },
        "staff_reports": report,
    }


@router.patch("/staff/{staff_id}/commission")
def update_staff_commission(db: DbSession, staff_id: int, data: dict = Body(...)):
    """Update commission and service fee settings for a staff member."""
    staff = db.query(StaffUser).filter(StaffUser.id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found")

    commission_pct = data.get("commission_percentage")
    service_fee_pct = data.get("service_fee_percentage")
    auto_logout = data.get("auto_logout_after_close")

    if commission_pct is not None:
        if commission_pct < 0 or commission_pct > 100:
            raise HTTPException(status_code=400, detail="Commission must be between 0-100%")
        staff.commission_percentage = commission_pct

    if service_fee_pct is not None:
        if service_fee_pct < 0 or service_fee_pct > 100:
            raise HTTPException(status_code=400, detail="Service fee must be between 0-100%")
        staff.service_fee_percentage = service_fee_pct

    if auto_logout is not None:
        staff.auto_logout_after_close = auto_logout

    db.commit()
    db.refresh(staff)

    return _staff_to_dict(staff)


@router.get("/staff/{staff_id}/earnings-summary")
def get_staff_earnings_summary(
    db: DbSession,
    staff_id: int,
    period: str = Query("month"),
):
    """Get earnings summary for a specific staff member."""
    staff = db.query(StaffUser).filter(StaffUser.id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found")

    today = date.today()

    if period == "day":
        start = today
    elif period == "week":
        start = today - timedelta(days=7)
    elif period == "month":
        start = today - timedelta(days=30)
    elif period == "year":
        start = today - timedelta(days=365)
    else:
        start = today - timedelta(days=30)

    # Get metrics
    metrics = db.query(PerformanceMetric).filter(
        PerformanceMetric.staff_id == staff_id,
        PerformanceMetric.period_date >= start,
        PerformanceMetric.period_date <= today,
    ).all()

    total_sales = sum(m.sales_amount for m in metrics) if metrics else 0
    total_tips = sum(m.tips_received for m in metrics) if metrics else 0
    total_hours = sum(m.hours_worked for m in metrics) if metrics else 0
    total_orders = sum(m.orders_count for m in metrics) if metrics else 0

    commission_pct = getattr(staff, 'commission_percentage', 0.0) or 0.0
    service_fee_pct = getattr(staff, 'service_fee_percentage', 0.0) or 0.0

    base_pay = total_hours * staff.hourly_rate
    commission = total_sales * (commission_pct / 100)
    service_fee = total_sales * (service_fee_pct / 100)
    net_earnings = base_pay + commission + total_tips - service_fee

    return {
        "staff_id": staff_id,
        "staff_name": staff.full_name,
        "period": period,
        "period_start": start.isoformat(),
        "period_end": today.isoformat(),
        "summary": {
            "hours_worked": round(total_hours, 2),
            "total_orders": total_orders,
            "total_sales": round(total_sales, 2),
            "avg_ticket": round(total_sales / total_orders, 2) if total_orders > 0 else 0,
            "sales_per_hour": round(total_sales / total_hours, 2) if total_hours > 0 else 0,
        },
        "earnings": {
            "base_pay": round(base_pay, 2),
            "commission": round(commission, 2),
            "tips": round(total_tips, 2),
            "service_fee_deduction": round(service_fee, 2),
            "net_total": round(net_earnings, 2),
        },
        "rates": {
            "hourly_rate": staff.hourly_rate,
            "commission_percentage": commission_pct,
            "service_fee_percentage": service_fee_pct,
        },
    }

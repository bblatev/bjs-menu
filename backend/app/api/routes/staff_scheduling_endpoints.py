"""
Staff Scheduling and Time Clock API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date, datetime, time
from pydantic import BaseModel, Field

from app.db.session import get_db
from app.models import StaffUser
from app.core.rbac import get_current_user
from app.core.rate_limit import limiter
from app.services.staff_scheduling_service import (
    get_shift_scheduling_service,
    get_time_clock_service
)


router = APIRouter(tags=["Staff Scheduling"])


def require_manager(current_user = Depends(get_current_user)):
    """Require manager or above role."""
    if not hasattr(current_user, 'role'):
        return current_user
    if current_user.role not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Manager access required")
    return current_user



# ========================= SCHEMAS =========================

class ShiftDefinitionCreate(BaseModel):
    name: str
    start_time: str = Field(..., description="HH:MM format")
    end_time: str = Field(..., description="HH:MM format")
    shift_type: str = "custom"
    break_duration_minutes: int = 30
    min_staff_count: int = 1
    days_of_week: Optional[str] = None
    color_code: Optional[str] = None
    description: Optional[str] = None


class ScheduleCreate(BaseModel):
    staff_id: int
    schedule_date: date
    scheduled_start: datetime
    scheduled_end: datetime
    shift_definition_id: Optional[int] = None
    notes: Optional[str] = None


class AvailabilitySet(BaseModel):
    day_of_week: int = Field(..., ge=0, le=6, description="0=Monday, 6=Sunday")
    available_from: Optional[str] = Field(None, description="HH:MM format")
    available_to: Optional[str] = Field(None, description="HH:MM format")
    is_preferred: bool = True


class TimeOffRequestCreate(BaseModel):
    start_date: date
    end_date: date
    request_type: str = "vacation"
    reason: Optional[str] = None


class PunchIn(BaseModel):
    clock_in_method: str = "pin"
    location: Optional[str] = None
    schedule_id: Optional[int] = None


class PunchOut(BaseModel):
    clock_out_method: str = "pin"
    location: Optional[str] = None


# ========================= SHIFT DEFINITIONS =========================

@router.get("/")
@limiter.limit("60/minute")
async def get_staff_scheduling_root(request: Request, db: Session = Depends(get_db)):
    """Staff scheduling overview."""
    return {"module": "staff-scheduling", "status": "active", "endpoints": ["/shift-definitions", "/schedules", "/availability/{staff_id}", "/time-clock/status", "/time-clock/entries"]}


@router.get("/shift-definitions")
@limiter.limit("60/minute")
async def get_shift_definitions(
    request: Request,
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Get all shift definitions"""
    service = get_shift_scheduling_service(db)
    return service.get_shift_definitions(
        venue_id=current_user.venue_id,
        active_only=active_only
    )


@router.post("/shift-definitions")
@limiter.limit("30/minute")
async def create_shift_definition(
    request: Request,
    data: ShiftDefinitionCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Create a new shift definition"""
    service = get_shift_scheduling_service(db)

    # Parse time strings
    start_parts = data.start_time.split(":")
    end_parts = data.end_time.split(":")
    start_time = time(int(start_parts[0]), int(start_parts[1]))
    end_time = time(int(end_parts[0]), int(end_parts[1]))

    return service.create_shift_definition(
        venue_id=current_user.venue_id,
        name=data.name,
        start_time=start_time,
        end_time=end_time,
        shift_type=data.shift_type,
        break_duration_minutes=data.break_duration_minutes,
        min_staff_count=data.min_staff_count,
        days_of_week=data.days_of_week,
        color_code=data.color_code,
        description=data.description
    )


# ========================= SCHEDULES =========================

@router.get("/schedules")
@limiter.limit("60/minute")
async def get_schedules(
    request: Request,
    start_date: date,
    end_date: date,
    staff_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Get schedules for a date range"""
    service = get_shift_scheduling_service(db)
    return service.get_schedules(
        venue_id=current_user.venue_id,
        start_date=start_date,
        end_date=end_date,
        staff_id=staff_id
    )


@router.post("/schedules")
@limiter.limit("30/minute")
async def create_schedule(
    request: Request,
    data: ScheduleCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Create a schedule entry"""
    service = get_shift_scheduling_service(db)
    try:
        return service.create_schedule(
            venue_id=current_user.venue_id,
            staff_id=data.staff_id,
            schedule_date=data.schedule_date,
            scheduled_start=data.scheduled_start,
            scheduled_end=data.scheduled_end,
            shift_definition_id=data.shift_definition_id,
            created_by=current_user.id,
            notes=data.notes
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/schedules/publish")
@limiter.limit("30/minute")
async def publish_schedules(
    request: Request,
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Publish draft schedules for a date range"""
    service = get_shift_scheduling_service(db)
    return service.publish_schedules(
        venue_id=current_user.venue_id,
        start_date=start_date,
        end_date=end_date
    )


@router.post("/schedules/generate")
@limiter.limit("30/minute")
async def generate_schedules(
    request: Request,
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Auto-generate schedules based on shift definitions and availability"""
    # This would be a more complex algorithm in production
    # For now, return a placeholder
    return {
        "message": "Schedule generation initiated",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "status": "pending"
    }


# ========================= AVAILABILITY =========================

@router.get("/availability/{staff_id}")
@limiter.limit("60/minute")
async def get_staff_availability(
    request: Request,
    staff_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get staff availability"""
    # Staff can view their own, managers can view all
    if current_user.role not in ["owner", "manager"] and current_user.id != staff_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    service = get_shift_scheduling_service(db)
    return service.get_staff_availability(staff_id)


@router.post("/availability/{staff_id}")
@limiter.limit("30/minute")
async def set_staff_availability(
    request: Request,
    staff_id: int,
    data: AvailabilitySet,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Set staff availability for a day of week"""
    # Staff can set their own, managers can set all
    if current_user.role not in ["owner", "manager"] and current_user.id != staff_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    service = get_shift_scheduling_service(db)

    available_from = None
    available_to = None
    if data.available_from:
        parts = data.available_from.split(":")
        available_from = time(int(parts[0]), int(parts[1]))
    if data.available_to:
        parts = data.available_to.split(":")
        available_to = time(int(parts[0]), int(parts[1]))

    return service.set_availability(
        staff_id=staff_id,
        day_of_week=data.day_of_week,
        available_from=available_from,
        available_to=available_to,
        is_preferred=data.is_preferred
    )


# ========================= TIME CLOCK =========================

@router.post("/time-clock/punch-in")
@limiter.limit("30/minute")
async def punch_in(
    request: Request,
    data: PunchIn,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Record a clock-in punch"""
    service = get_time_clock_service(db)
    try:
        return service.punch_in(
            venue_id=current_user.venue_id,
            staff_id=current_user.id,
            clock_in_method=data.clock_in_method,
            location=data.location,
            schedule_id=data.schedule_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/time-clock/punch-out")
@limiter.limit("30/minute")
async def punch_out(
    request: Request,
    data: PunchOut,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Record a clock-out punch"""
    service = get_time_clock_service(db)
    try:
        return service.punch_out(
            staff_id=current_user.id,
            clock_out_method=data.clock_out_method,
            location=data.location
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/time-clock/break/start")
@limiter.limit("30/minute")
async def start_break(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Start a break"""
    service = get_time_clock_service(db)
    try:
        return service.start_break(current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/time-clock/break/end")
@limiter.limit("30/minute")
async def end_break(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """End a break"""
    service = get_time_clock_service(db)
    try:
        return service.end_break(current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/time-clock/status")
@limiter.limit("60/minute")
async def get_clock_status(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get current clock status"""
    service = get_time_clock_service(db)
    return service.get_current_status(current_user.id)


@router.get("/time-clock/entries")
@limiter.limit("60/minute")
async def get_time_entries(
    request: Request,
    start_date: date,
    end_date: date,
    staff_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Get time clock entries for a date range"""
    service = get_time_clock_service(db)
    return service.get_time_entries(
        venue_id=current_user.venue_id,
        start_date=start_date,
        end_date=end_date,
        staff_id=staff_id
    )


# ========================= LABOR ANALYTICS =========================

@router.get("/labor/analytics")
@limiter.limit("60/minute")
async def get_labor_analytics(
    request: Request,
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Get labor analytics and hours summary"""
    service = get_time_clock_service(db)
    return service.get_hours_summary(
        venue_id=current_user.venue_id,
        start_date=start_date,
        end_date=end_date
    )


@router.get("/labor/cost-report")
@limiter.limit("60/minute")
async def get_labor_cost_report(
    request: Request,
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Get labor cost report"""
    service = get_time_clock_service(db)
    hours_summary = service.get_hours_summary(
        venue_id=current_user.venue_id,
        start_date=start_date,
        end_date=end_date
    )

    # Get hourly rates for staff (simplified)
    from app.models import StaffUser as Staff
    staff_rates = {}
    for staff_id in hours_summary.get("staff_hours", {}).keys():
        staff = db.query(Staff).filter(Staff.id == staff_id).first()
        if staff:
            staff_rates[staff_id] = {
                "name": staff.full_name,
                "hourly_rate": float(getattr(staff, 'hourly_rate', 15.0) or 15.0)
            }

    # Calculate costs
    total_labor_cost = 0
    staff_costs = {}

    for staff_id, hours in hours_summary.get("staff_hours", {}).items():
        rate = staff_rates.get(staff_id, {}).get("hourly_rate", 15.0)
        regular_cost = hours["regular_hours"] * rate
        overtime_cost = hours["overtime_hours"] * rate * 1.5
        total_cost = regular_cost + overtime_cost

        staff_costs[staff_id] = {
            "name": staff_rates.get(staff_id, {}).get("name", "Unknown"),
            "regular_hours": hours["regular_hours"],
            "overtime_hours": hours["overtime_hours"],
            "regular_cost": round(regular_cost, 2),
            "overtime_cost": round(overtime_cost, 2),
            "total_cost": round(total_cost, 2)
        }

        total_labor_cost += total_cost

    return {
        "period": hours_summary["period"],
        "total_labor_cost": round(total_labor_cost, 2),
        "staff_costs": staff_costs,
        "totals": {
            **hours_summary["totals"],
            "total_cost": round(total_labor_cost, 2)
        }
    }

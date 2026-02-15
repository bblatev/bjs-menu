"""
Staff Scheduling and Time Clock Service
Handles shift management, scheduling, and time tracking
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timezone, time
import logging

from app.models.staff_scheduling_models import (
    ShiftDefinition, StaffSchedule,
    StaffAvailability, ShiftType, ScheduleStatus, TimeClockStatus
)
from app.models.staff import TimeClockEntry

logger = logging.getLogger(__name__)


class ShiftSchedulingService:
    """
    Manage shift definitions and staff scheduling.
    """

    def __init__(self, db: Session):
        self.db = db

    # === Shift Definitions ===

    def create_shift_definition(
        self,
        venue_id: int,
        name: str,
        start_time: time,
        end_time: time,
        shift_type: str = "custom",
        **kwargs
    ) -> Dict[str, Any]:
        """Create a new shift template."""
        try:
            stype = ShiftType(shift_type)
        except ValueError:
            stype = ShiftType.CUSTOM

        shift = ShiftDefinition(
            venue_id=venue_id,
            name=name,
            shift_type=stype,
            start_time=start_time,
            end_time=end_time,
            is_active=True,
            **kwargs
        )

        self.db.add(shift)
        self.db.commit()
        self.db.refresh(shift)

        return self._shift_to_dict(shift)

    def get_shift_definitions(
        self,
        venue_id: int,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Get all shift definitions for a venue."""
        query = self.db.query(ShiftDefinition).filter(
            ShiftDefinition.venue_id == venue_id
        )

        if active_only:
            query = query.filter(ShiftDefinition.is_active == True)

        shifts = query.all()
        return [self._shift_to_dict(s) for s in shifts]

    def _shift_to_dict(self, shift: ShiftDefinition) -> Dict[str, Any]:
        return {
            "id": shift.id,
            "name": shift.name,
            "shift_type": shift.shift_type.value if shift.shift_type else None,
            "start_time": shift.start_time.strftime("%H:%M") if shift.start_time else None,
            "end_time": shift.end_time.strftime("%H:%M") if shift.end_time else None,
            "break_duration_minutes": shift.break_duration_minutes,
            "min_staff_count": shift.min_staff_count,
            "days_of_week": shift.days_of_week,
            "is_active": shift.is_active,
            "color_code": shift.color_code
        }

    # === Staff Schedules ===

    def create_schedule(
        self,
        venue_id: int,
        staff_id: int,
        schedule_date: date,
        scheduled_start: datetime,
        scheduled_end: datetime,
        shift_definition_id: Optional[int] = None,
        created_by: Optional[int] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a schedule entry for a staff member."""
        # Check for conflicts
        existing = self.db.query(StaffSchedule).filter(
            StaffSchedule.staff_id == staff_id,
            StaffSchedule.schedule_date == schedule_date,
            or_(
                and_(
                    StaffSchedule.scheduled_start <= scheduled_start,
                    StaffSchedule.scheduled_end > scheduled_start
                ),
                and_(
                    StaffSchedule.scheduled_start < scheduled_end,
                    StaffSchedule.scheduled_end >= scheduled_end
                )
            )
        ).first()

        if existing:
            raise ValueError("Schedule conflict detected")

        schedule = StaffSchedule(
            venue_id=venue_id,
            staff_id=staff_id,
            shift_definition_id=shift_definition_id,
            schedule_date=schedule_date,
            scheduled_start=scheduled_start,
            scheduled_end=scheduled_end,
            status=ScheduleStatus.DRAFT,
            notes=notes,
            created_by=created_by
        )

        self.db.add(schedule)
        self.db.commit()
        self.db.refresh(schedule)

        return self._schedule_to_dict(schedule)

    def get_schedules(
        self,
        venue_id: int,
        start_date: date,
        end_date: date,
        staff_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get schedules for a date range."""
        query = self.db.query(StaffSchedule).filter(
            StaffSchedule.venue_id == venue_id,
            StaffSchedule.schedule_date >= start_date,
            StaffSchedule.schedule_date <= end_date
        )

        if staff_id:
            query = query.filter(StaffSchedule.staff_id == staff_id)

        schedules = query.order_by(StaffSchedule.schedule_date, StaffSchedule.scheduled_start).all()
        return [self._schedule_to_dict(s) for s in schedules]

    def publish_schedules(
        self,
        venue_id: int,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Publish draft schedules for a date range."""
        schedules = self.db.query(StaffSchedule).filter(
            StaffSchedule.venue_id == venue_id,
            StaffSchedule.schedule_date >= start_date,
            StaffSchedule.schedule_date <= end_date,
            StaffSchedule.status == ScheduleStatus.DRAFT
        ).all()

        for schedule in schedules:
            schedule.status = ScheduleStatus.PUBLISHED

        self.db.commit()

        return {
            "published_count": len(schedules),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }

    def _schedule_to_dict(self, schedule: StaffSchedule) -> Dict[str, Any]:
        return {
            "id": schedule.id,
            "staff_id": schedule.staff_id,
            "shift_definition_id": schedule.shift_definition_id,
            "schedule_date": schedule.schedule_date.isoformat(),
            "scheduled_start": schedule.scheduled_start.isoformat() if schedule.scheduled_start else None,
            "scheduled_end": schedule.scheduled_end.isoformat() if schedule.scheduled_end else None,
            "actual_start": schedule.actual_start.isoformat() if schedule.actual_start else None,
            "actual_end": schedule.actual_end.isoformat() if schedule.actual_end else None,
            "status": schedule.status.value if schedule.status else None,
            "is_confirmed": schedule.is_confirmed,
            "notes": schedule.notes
        }

    # === Staff Availability ===

    def set_availability(
        self,
        staff_id: int,
        day_of_week: int,
        available_from: Optional[time] = None,
        available_to: Optional[time] = None,
        is_preferred: bool = True
    ) -> Dict[str, Any]:
        """Set staff availability for a day of week."""
        # Check for existing
        existing = self.db.query(StaffAvailability).filter(
            StaffAvailability.staff_id == staff_id,
            StaffAvailability.day_of_week == day_of_week
        ).first()

        if existing:
            existing.available_from = available_from
            existing.available_to = available_to
            existing.is_preferred = is_preferred
            availability = existing
        else:
            availability = StaffAvailability(
                staff_id=staff_id,
                day_of_week=day_of_week,
                available_from=available_from,
                available_to=available_to,
                is_preferred=is_preferred
            )
            self.db.add(availability)

        self.db.commit()

        return {
            "staff_id": staff_id,
            "day_of_week": day_of_week,
            "available_from": available_from.strftime("%H:%M") if available_from else None,
            "available_to": available_to.strftime("%H:%M") if available_to else None,
            "is_preferred": is_preferred
        }

    def get_staff_availability(self, staff_id: int) -> List[Dict[str, Any]]:
        """Get all availability records for a staff member."""
        availabilities = self.db.query(StaffAvailability).filter(
            StaffAvailability.staff_id == staff_id
        ).order_by(StaffAvailability.day_of_week).all()

        return [
            {
                "day_of_week": a.day_of_week,
                "available_from": a.available_from.strftime("%H:%M") if a.available_from else None,
                "available_to": a.available_to.strftime("%H:%M") if a.available_to else None,
                "is_preferred": a.is_preferred
            }
            for a in availabilities
        ]


class TimeClockService:
    """
    Handle time clock punches and time tracking.
    """

    def __init__(self, db: Session):
        self.db = db

    def punch_in(
        self,
        venue_id: int,
        staff_id: int,
        clock_in_method: str = "pin",
        location: Optional[str] = None,
        schedule_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Record a clock-in punch."""
        # Check for existing open entry
        existing = self.db.query(TimeClockEntry).filter(
            TimeClockEntry.staff_id == staff_id,
            TimeClockEntry.clock_out == None
        ).first()

        if existing:
            raise ValueError("Staff member is already clocked in")

        now = datetime.now(timezone.utc)

        # Find matching schedule if not provided
        if not schedule_id:
            today = now.date()
            schedule = self.db.query(StaffSchedule).filter(
                StaffSchedule.staff_id == staff_id,
                StaffSchedule.schedule_date == today,
                StaffSchedule.status == ScheduleStatus.PUBLISHED
            ).first()
            if schedule:
                schedule_id = schedule.id

        entry = TimeClockEntry(
            staff_id=staff_id,
            clock_in=now,
            clock_in_method=clock_in_method,
            status="clocked_in"
        )

        # Update schedule actual start if linked
        if schedule_id:
            schedule = self.db.query(StaffSchedule).filter(
                StaffSchedule.id == schedule_id
            ).first()
            if schedule and schedule.scheduled_start:
                schedule.actual_start = now

        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)

        return self._entry_to_dict(entry)

    def punch_out(
        self,
        staff_id: int,
        clock_out_method: str = "pin",
        location: Optional[str] = None
    ) -> Dict[str, Any]:
        """Record a clock-out punch."""
        entry = self.db.query(TimeClockEntry).filter(
            TimeClockEntry.staff_id == staff_id,
            TimeClockEntry.clock_out == None
        ).first()

        if not entry:
            raise ValueError("No active clock-in found")

        now = datetime.now(timezone.utc)

        entry.clock_out = now
        entry.status = "clocked_out"

        # Calculate hours
        clock_in = entry.clock_in
        total_seconds = (now - clock_in).total_seconds()
        total_hours = total_seconds / 3600

        # Subtract break time
        break_hrs = float(entry.break_hours or 0)
        worked_hours = total_hours - break_hrs

        entry.total_hours = round(worked_hours, 2)

        self.db.commit()
        self.db.refresh(entry)

        return self._entry_to_dict(entry)

    def start_break(self, staff_id: int) -> Dict[str, Any]:
        """Start a break."""
        entry = self.db.query(TimeClockEntry).filter(
            TimeClockEntry.staff_id == staff_id,
            TimeClockEntry.clock_out == None
        ).first()

        if not entry:
            raise ValueError("No active clock-in found")

        if entry.break_start and not entry.break_end:
            raise ValueError("Already on break")

        entry.break_start = datetime.now(timezone.utc)
        entry.status = "on_break"

        self.db.commit()

        return {"staff_id": staff_id, "break_started": True}

    def end_break(self, staff_id: int) -> Dict[str, Any]:
        """End a break."""
        entry = self.db.query(TimeClockEntry).filter(
            TimeClockEntry.staff_id == staff_id,
            TimeClockEntry.clock_out == None
        ).first()

        if not entry:
            raise ValueError("No active clock-in found")

        if not entry.break_start or entry.break_end:
            raise ValueError("Not currently on break")

        now = datetime.now(timezone.utc)
        entry.break_end = now
        entry.status = "clocked_in"

        # Calculate break duration in hours
        break_hrs = (now - entry.break_start).total_seconds() / 3600
        entry.break_hours = round(float(entry.break_hours or 0) + break_hrs, 2)

        self.db.commit()

        return {"staff_id": staff_id, "break_ended": True, "break_minutes": break_minutes}

    def get_current_status(self, staff_id: int) -> Dict[str, Any]:
        """Get current clock status for a staff member."""
        entry = self.db.query(TimeClockEntry).filter(
            TimeClockEntry.staff_id == staff_id,
            TimeClockEntry.clock_out == None
        ).first()

        if not entry:
            return {
                "staff_id": staff_id,
                "clocked_in": False,
                "status": "not_clocked_in"
            }

        return {
            "staff_id": staff_id,
            "clocked_in": True,
            "status": entry.status or "clocked_in",
            "clock_in_time": entry.clock_in.isoformat() if entry.clock_in else None,
            "on_break": entry.status == "on_break",
            "break_start": entry.break_start.isoformat() if entry.break_start else None
        }

    def get_time_entries(
        self,
        venue_id: int,
        start_date: date,
        end_date: date,
        staff_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get time clock entries for a date range."""
        start_dt = datetime.combine(start_date, time.min)
        end_dt = datetime.combine(end_date, time.max)

        query = self.db.query(TimeClockEntry).filter(
            TimeClockEntry.clock_in >= start_dt,
            TimeClockEntry.clock_in <= end_dt
        )

        if staff_id:
            query = query.filter(TimeClockEntry.staff_id == staff_id)

        entries = query.order_by(TimeClockEntry.clock_in.desc()).all()
        return [self._entry_to_dict(e) for e in entries]

    def get_hours_summary(
        self,
        venue_id: int,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Get total hours summary for all staff."""
        start_dt = datetime.combine(start_date, time.min)
        end_dt = datetime.combine(end_date, time.max)

        # Get all completed entries in range
        entries = self.db.query(TimeClockEntry).filter(
            TimeClockEntry.clock_in >= start_dt,
            TimeClockEntry.clock_in <= end_dt,
            TimeClockEntry.clock_out != None
        ).all()

        staff_hours = {}
        for entry in entries:
            sid = entry.staff_id
            if sid not in staff_hours:
                staff_hours[sid] = {
                    "regular_hours": 0,
                    "overtime_hours": 0,
                    "total_hours": 0,
                    "shifts": 0
                }

            total = float(entry.total_hours or 0)
            staff_hours[sid]["total_hours"] += total
            staff_hours[sid]["regular_hours"] += min(total, 8)
            staff_hours[sid]["overtime_hours"] += max(total - 8, 0)
            staff_hours[sid]["shifts"] += 1

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "staff_hours": staff_hours,
            "totals": {
                "regular_hours": sum(s["regular_hours"] for s in staff_hours.values()),
                "overtime_hours": sum(s["overtime_hours"] for s in staff_hours.values()),
                "total_hours": sum(s["total_hours"] for s in staff_hours.values()),
                "total_shifts": sum(s["shifts"] for s in staff_hours.values())
            }
        }

    def _entry_to_dict(self, entry: TimeClockEntry) -> Dict[str, Any]:
        total = float(entry.total_hours or 0)
        return {
            "id": entry.id,
            "staff_id": entry.staff_id,
            "clock_in": entry.clock_in.isoformat() if entry.clock_in else None,
            "clock_out": entry.clock_out.isoformat() if entry.clock_out else None,
            "status": entry.status or None,
            "total_hours": total,
            "break_hours": float(entry.break_hours or 0),
            "clock_in_method": entry.clock_in_method,
            "notes": entry.notes,
        }


# Factory functions
def get_shift_scheduling_service(db: Session) -> ShiftSchedulingService:
    return ShiftSchedulingService(db)

def get_time_clock_service(db: Session) -> TimeClockService:
    return TimeClockService(db)

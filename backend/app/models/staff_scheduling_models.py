"""
Staff Scheduling Models - Phase 1.1
Time clock, shift definitions, and staff scheduling
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, Numeric, Date, Time, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.db.base import Base


class ShiftType(str, enum.Enum):
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    NIGHT = "night"
    SPLIT = "split"
    CUSTOM = "custom"


class ScheduleStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class TimeClockStatus(str, enum.Enum):
    CLOCKED_IN = "clocked_in"
    CLOCKED_OUT = "clocked_out"
    ON_BREAK = "on_break"


class ShiftDefinition(Base):
    """Shift templates/definitions"""
    __tablename__ = "shift_definitions"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)

    name = Column(String(100), nullable=False)
    shift_type = Column(SQLEnum(ShiftType), default=ShiftType.CUSTOM)

    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    break_duration_minutes = Column(Integer, default=30)

    # Pay rates
    base_rate_multiplier = Column(Numeric(4, 2), default=1.0)  # 1.5x for overtime, etc.

    # Role requirements
    min_staff_count = Column(Integer, default=1)
    required_roles = Column(Text)  # JSON array of role IDs

    # Scheduling rules
    days_of_week = Column(String(20))  # "1,2,3,4,5" for Mon-Fri
    is_active = Column(Boolean, default=True)

    color_code = Column(String(7))  # Hex color for UI
    description = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="shift_definitions")
    schedules = relationship("StaffSchedule", back_populates="shift_definition")


class StaffSchedule(Base):
    """Staff scheduling - assigns staff to shifts"""
    __tablename__ = "staff_schedules"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    staff_id = Column(Integer, ForeignKey("staff_users.id"), nullable=False)
    shift_definition_id = Column(Integer, ForeignKey("shift_definitions.id"))

    # Schedule details
    schedule_date = Column(Date, nullable=False)
    scheduled_start = Column(DateTime, nullable=False)
    scheduled_end = Column(DateTime, nullable=False)

    # Actual times (filled when clocked in/out)
    actual_start = Column(DateTime)
    actual_end = Column(DateTime)

    # Status
    status = Column(SQLEnum(ScheduleStatus), default=ScheduleStatus.DRAFT)
    is_confirmed = Column(Boolean, default=False)
    confirmed_at = Column(DateTime)

    # Notes
    notes = Column(Text)
    manager_notes = Column(Text)

    # Trade/swap tracking
    original_staff_id = Column(Integer, ForeignKey("staff_users.id"))
    swap_requested_at = Column(DateTime)
    swap_approved_at = Column(DateTime)
    swap_approved_by = Column(Integer, ForeignKey("staff_users.id"))

    # Overtime/costs
    is_overtime = Column(Boolean, default=False)
    overtime_hours = Column(Numeric(5, 2), default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("staff_users.id"))

    # Relationships
    venue = relationship("Venue", backref="staff_schedules")
    staff = relationship("StaffUser", foreign_keys=[staff_id], backref="schedules")
    shift_definition = relationship("ShiftDefinition", back_populates="schedules")


# TimeClockEntry is defined in app.models.staff to avoid duplicate mapper registration
# Import it from there: from app.models.staff import TimeClockEntry


class StaffAvailability(Base):
    """Staff availability preferences"""
    __tablename__ = "staff_availability"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, ForeignKey("staff_users.id"), nullable=False)

    # Day of week (0=Monday, 6=Sunday)
    day_of_week = Column(Integer, nullable=False)

    # Availability windows
    available_from = Column(Time)
    available_to = Column(Time)

    # Preference
    is_preferred = Column(Boolean, default=True)  # True=available, False=unavailable
    preference_level = Column(Integer, default=3)  # 1=avoid, 2=neutral, 3=prefer

    # Date range for temporary availability changes
    effective_from = Column(Date)
    effective_to = Column(Date)

    notes = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    staff = relationship("StaffUser", backref="availability")


# TimeOffRequest model is defined in app.models.staff to avoid duplicate mapper registration

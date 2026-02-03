"""Staff management schemas - Pydantic models for staff, shifts, time tracking."""

from typing import List, Optional
from datetime import datetime, date, time
from pydantic import BaseModel, Field, field_validator


# ============== Staff Schemas ==============

class StaffCreate(BaseModel):
    """Schema for creating a new staff member."""
    full_name: str = Field(..., min_length=2, max_length=100)
    role: str = Field(default="waiter", pattern="^(waiter|bar|kitchen|manager|admin|host)$")
    pin_code: Optional[str] = Field(default=None, min_length=4, max_length=6)
    hourly_rate: float = Field(default=15.0, ge=0)
    max_hours_week: int = Field(default=40, ge=0, le=168)
    color: Optional[str] = Field(default=None, pattern="^#[0-9A-Fa-f]{6}$")

    @field_validator("pin_code")
    @classmethod
    def validate_pin(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.isdigit():
            raise ValueError("PIN must contain only digits")
        return v


class StaffUpdate(BaseModel):
    """Schema for updating a staff member."""
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    role: Optional[str] = Field(default=None, pattern="^(waiter|bar|kitchen|manager|admin|host)$")
    hourly_rate: Optional[float] = Field(default=None, ge=0)
    max_hours_week: Optional[int] = Field(default=None, ge=0, le=168)
    color: Optional[str] = Field(default=None, pattern="^#[0-9A-Fa-f]{6}$")
    commission_percentage: Optional[float] = Field(default=None, ge=0, le=100)
    service_fee_percentage: Optional[float] = Field(default=None, ge=0, le=100)
    auto_logout_after_close: Optional[bool] = None
    is_active: Optional[bool] = None


class StaffResponse(BaseModel):
    """Schema for staff member response."""
    id: int
    full_name: str
    role: str
    active: bool
    has_pin: bool
    hourly_rate: Optional[float] = None
    max_hours_week: Optional[int] = None
    color: Optional[str] = None
    commission_percentage: float = 0.0
    service_fee_percentage: float = 0.0
    auto_logout_after_close: bool = False
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ============== Shift Schemas ==============

class ShiftCreate(BaseModel):
    """Schema for creating a new shift."""
    staff_id: int
    date: str = Field(..., pattern="^\\d{4}-\\d{2}-\\d{2}$")  # YYYY-MM-DD
    shift_type: str = Field(default="morning", pattern="^(morning|afternoon|evening|night|split)$")
    start_time: str = Field(..., pattern="^\\d{2}:\\d{2}$")  # HH:MM
    end_time: str = Field(..., pattern="^\\d{2}:\\d{2}$")  # HH:MM
    break_minutes: int = Field(default=30, ge=0, le=120)
    position: Optional[str] = None
    notes: Optional[str] = Field(default=None, max_length=500)


class ShiftUpdate(BaseModel):
    """Schema for updating a shift."""
    staff_id: Optional[int] = None
    date: Optional[str] = Field(default=None, pattern="^\\d{4}-\\d{2}-\\d{2}$")
    shift_type: Optional[str] = Field(default=None, pattern="^(morning|afternoon|evening|night|split)$")
    start_time: Optional[str] = Field(default=None, pattern="^\\d{2}:\\d{2}$")
    end_time: Optional[str] = Field(default=None, pattern="^\\d{2}:\\d{2}$")
    break_minutes: Optional[int] = Field(default=None, ge=0, le=120)
    status: Optional[str] = Field(default=None, pattern="^(scheduled|confirmed|completed|cancelled|no_show)$")
    position: Optional[str] = None
    notes: Optional[str] = Field(default=None, max_length=500)


class ShiftResponse(BaseModel):
    """Schema for shift response."""
    id: int
    staff_id: int
    staff_name: Optional[str] = None
    date: Optional[str] = None
    shift_type: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    break_minutes: int
    status: str
    position: Optional[str] = None
    notes: Optional[str] = None
    is_published: bool = False

    model_config = {"from_attributes": True}


# ============== Time Off Schemas ==============

class TimeOffCreate(BaseModel):
    """Schema for creating a time off request."""
    staff_id: int
    start_date: str = Field(..., pattern="^\\d{4}-\\d{2}-\\d{2}$")
    end_date: str = Field(..., pattern="^\\d{4}-\\d{2}-\\d{2}$")
    type: str = Field(default="vacation", pattern="^(vacation|sick|personal|unpaid)$")
    notes: Optional[str] = Field(default=None, max_length=500)


class TimeOffResponse(BaseModel):
    """Schema for time off response."""
    id: int
    staff_id: int
    staff_name: Optional[str] = None
    start_date: str
    end_date: str
    type: str
    status: str
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ============== Tip Pool Schemas ==============

class TipPoolCreate(BaseModel):
    """Schema for creating a tip pool entry."""
    date: str = Field(..., pattern="^\\d{4}-\\d{2}-\\d{2}$")
    shift: str = Field(default="evening", pattern="^(morning|afternoon|evening|night)$")
    total_tips_cash: float = Field(default=0, ge=0)
    total_tips_card: float = Field(default=0, ge=0)
    distribution_method: str = Field(default="equal", pattern="^(equal|hours|points|custom)$")
    participant_ids: List[int] = Field(default_factory=list)


class TipPoolResponse(BaseModel):
    """Schema for tip pool response."""
    id: int
    date: str
    shift: str
    total_tips_cash: float
    total_tips_card: float
    total_tips: float
    distribution_method: str
    participants_count: int
    is_distributed: bool
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ============== Time Clock Schemas ==============

class TimeClockEntryResponse(BaseModel):
    """Schema for time clock entry response."""
    id: int
    staff_id: int
    staff_name: Optional[str] = None
    clock_in: Optional[datetime] = None
    clock_out: Optional[datetime] = None
    break_start: Optional[datetime] = None
    break_end: Optional[datetime] = None
    total_hours: Optional[float] = None
    break_hours: Optional[float] = None
    status: str
    clock_in_method: Optional[str] = None

    model_config = {"from_attributes": True}

"""Staff management models."""

from __future__ import annotations
from datetime import datetime, date, time
from decimal import Decimal
from typing import Optional
from enum import Enum

from sqlalchemy import Boolean, String, Integer, Float, Date, Time, DateTime, Text, ForeignKey, JSON, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.db.base import Base, TimestampMixin, SoftDeleteMixin
from app.models.validators import non_negative, positive, percentage


class StaffRole(str, Enum):
    """Staff roles."""
    ADMIN = "admin"
    MANAGER = "manager"
    KITCHEN = "kitchen"
    BAR = "bar"
    WAITER = "waiter"


class ShiftType(str, Enum):
    """Shift types."""
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    NIGHT = "night"
    SPLIT = "split"


class ShiftStatus(str, Enum):
    """Shift status."""
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    ABSENT = "absent"
    SWAP_REQUESTED = "swap_requested"


class TimeOffType(str, Enum):
    """Time off types."""
    VACATION = "vacation"
    SICK = "sick"
    PERSONAL = "personal"
    UNPAID = "unpaid"


class TimeOffStatus(str, Enum):
    """Time off request status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ClockStatus(str, Enum):
    """Time clock status."""
    CLOCKED_IN = "clocked_in"
    ON_BREAK = "on_break"
    CLOCKED_OUT = "clocked_out"


class TipDistributionMethod(str, Enum):
    """Tip distribution methods."""
    EQUAL = "equal"
    HOURS = "hours"
    POINTS = "points"
    CUSTOM = "custom"


class TipPoolStatus(str, Enum):
    """Tip pool status."""
    PENDING = "pending"
    DISTRIBUTED = "distributed"
    PAID = "paid"


class StaffUser(Base, TimestampMixin, SoftDeleteMixin):
    """Staff member model."""

    __tablename__ = "staff_users"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="waiter", nullable=False)
    pin_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    hourly_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("15.00"), nullable=False)
    max_hours_week: Mapped[int] = mapped_column(Integer, default=40, nullable=False)
    color: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    location_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    # Service deduction / commission tracking
    commission_percentage: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0"), nullable=False)
    service_fee_percentage: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0"), nullable=False)
    auto_logout_after_close: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    shifts = relationship("Shift", back_populates="staff")
    time_off_requests = relationship("app.models.staff.TimeOffRequest", back_populates="staff")
    time_clock_entries = relationship("TimeClockEntry", back_populates="staff")
    table_assignments = relationship("TableAssignment", back_populates="staff")

    @validates('hourly_rate')
    def _validate_hourly_rate(self, key, value):
        return positive(key, value)

    @validates('max_hours_week')
    def _validate_max_hours(self, key, value):
        return positive(key, value)

    @validates('commission_percentage', 'service_fee_percentage')
    def _validate_percentage(self, key, value):
        return percentage(key, value)


class Shift(Base, TimestampMixin):
    """Shift schedule model."""

    __tablename__ = "shifts"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    staff_id: Mapped[int] = mapped_column(ForeignKey("staff_users.id", ondelete="CASCADE"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    shift_type: Mapped[str] = mapped_column(String(50), default="morning", nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    break_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="scheduled", nullable=False)
    position: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    @validates('break_minutes')
    def _validate_break_minutes(self, key, value):
        return non_negative(key, value)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    location_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    staff = relationship("StaffUser", back_populates="shifts")


class TimeOffRequest(Base, TimestampMixin):
    """Time off request model."""

    __tablename__ = "time_off_requests"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    staff_id: Mapped[int] = mapped_column(ForeignKey("staff_users.id", ondelete="CASCADE"), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    type: Mapped[str] = mapped_column(String(50), default="vacation", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    location_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    staff = relationship("app.models.staff.StaffUser", back_populates="time_off_requests")


class TimeClockEntry(Base, TimestampMixin):
    """Time clock entry model."""

    __tablename__ = "time_clock_entries"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    staff_id: Mapped[int] = mapped_column(ForeignKey("staff_users.id", ondelete="CASCADE"), nullable=False)
    clock_in: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    clock_out: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    break_start: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    break_end: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    total_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    break_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="clocked_in", nullable=False)
    clock_in_method: Mapped[str] = mapped_column(String(50), default="web", nullable=False)
    location_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    staff = relationship("StaffUser", back_populates="time_clock_entries")


class TableAssignment(Base, TimestampMixin):
    """Table assignment model for servers."""

    __tablename__ = "table_assignments"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    staff_id: Mapped[int] = mapped_column(ForeignKey("staff_users.id", ondelete="CASCADE"), nullable=False)
    table_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    area: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    location_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    staff = relationship("StaffUser", back_populates="table_assignments")


class PerformanceMetric(Base, TimestampMixin):
    """Staff performance metrics model."""

    __tablename__ = "staff_performance_metrics"
    __table_args__ = (
        UniqueConstraint('staff_id', 'period', 'period_date', name='uq_perf_metric_staff_period'),
        {'extend_existing': True},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    staff_id: Mapped[int] = mapped_column(ForeignKey("staff_users.id", ondelete="CASCADE"), nullable=False)
    period: Mapped[str] = mapped_column(String(50), nullable=False)  # day, week, month
    period_date: Mapped[date] = mapped_column(Date, nullable=False)
    sales_amount: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    orders_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_ticket: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    items_sold: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tips_received: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    customer_rating: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    reviews_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    hours_worked: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    sales_per_hour: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    late_arrivals: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    absences: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    upsell_rate: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    table_turnover: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    location_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)


class PerformanceGoal(Base, TimestampMixin):
    """Performance goals model."""

    __tablename__ = "performance_goals"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    metric: Mapped[str] = mapped_column(String(100), nullable=False)
    target_value: Mapped[float] = mapped_column(Float, nullable=False)
    current_value: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    period: Mapped[str] = mapped_column(String(50), nullable=False)
    location_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)


class TipPool(Base, TimestampMixin):
    """Tip pool model."""

    __tablename__ = "tip_pools"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    shift: Mapped[str] = mapped_column(String(50), default="evening", nullable=False)
    total_tips_cash: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"), nullable=False)
    total_tips_card: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"), nullable=False)
    total_tips: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"), nullable=False)
    participants_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    distribution_method: Mapped[str] = mapped_column(String(50), default="equal", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    distributed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    location_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    distributions = relationship("TipDistribution", back_populates="pool")


class TipDistribution(Base, TimestampMixin):
    """Tip distribution to individual staff."""

    __tablename__ = "tip_distributions"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    pool_id: Mapped[int] = mapped_column(ForeignKey("tip_pools.id", ondelete="CASCADE"), nullable=False)
    staff_id: Mapped[int] = mapped_column(ForeignKey("staff_users.id", ondelete="CASCADE"), nullable=False)
    hours_worked: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    share_percentage: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"), nullable=False)
    is_paid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    pool = relationship("TipPool", back_populates="distributions")

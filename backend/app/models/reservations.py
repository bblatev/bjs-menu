"""Reservations and Waitlist models - TouchBistro style."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from app.db.base import Base


class ReservationStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SEATED = "seated"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class WaitlistStatus(str, Enum):
    WAITING = "waiting"
    NOTIFIED = "notified"
    SEATED = "seated"
    LEFT = "left"
    CANCELLED = "cancelled"


class BookingSource(str, Enum):
    WEBSITE = "website"
    PHONE = "phone"
    WALK_IN = "walk_in"
    GOOGLE = "google"
    APP = "app"
    THIRD_PARTY = "third_party"


class Reservation(Base):
    """Restaurant reservation."""
    __tablename__ = "reservations"

    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)

    # Guest info
    guest_name = Column(String(200), nullable=False)
    guest_phone = Column(String(50), nullable=True)
    guest_email = Column(String(255), nullable=True)
    customer_id = Column(Integer, nullable=True)  # Link to customer record

    # Reservation details
    party_size = Column(Integer, nullable=False)
    reservation_date = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, default=90)

    # Table assignment
    table_ids = Column(JSON, nullable=True)  # Can be multiple tables
    seating_preference = Column(String(100), nullable=True)  # indoor, outdoor, bar, booth

    # Status
    status = Column(SQLEnum(ReservationStatus), default=ReservationStatus.PENDING)
    source = Column(SQLEnum(BookingSource), default=BookingSource.WEBSITE)

    # Confirmations
    confirmation_code = Column(String(20), unique=True, nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
    reminder_sent_at = Column(DateTime, nullable=True)
    reminder_24h_sent = Column(Boolean, default=False)
    reminder_2h_sent = Column(Boolean, default=False)

    # Arrival tracking
    arrived_at = Column(DateTime, nullable=True)
    seated_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # No-show protection
    credit_card_on_file = Column(Boolean, default=False)
    no_show_fee = Column(Float, nullable=True)
    no_show_charged = Column(Boolean, default=False)

    # Special requests
    special_requests = Column(Text, nullable=True)
    occasion = Column(String(100), nullable=True)  # birthday, anniversary, business
    dietary_restrictions = Column(JSON, nullable=True)

    # VIP handling
    is_vip = Column(Boolean, default=False)
    vip_notes = Column(Text, nullable=True)

    # Internal notes
    internal_notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    location = relationship("Location", backref="reservations")


class Waitlist(Base):
    """Walk-in waitlist management."""
    __tablename__ = "waitlist"

    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)

    # Guest info
    guest_name = Column(String(200), nullable=False)
    guest_phone = Column(String(50), nullable=True)
    customer_id = Column(Integer, nullable=True)

    # Party details
    party_size = Column(Integer, nullable=False)
    seating_preference = Column(String(100), nullable=True)

    # Wait time
    added_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    estimated_wait_minutes = Column(Integer, nullable=True)
    quoted_wait_minutes = Column(Integer, nullable=True)  # What we told guest
    actual_wait_minutes = Column(Integer, nullable=True)  # Actual wait

    # Status
    status = Column(SQLEnum(WaitlistStatus), default=WaitlistStatus.WAITING)
    position = Column(Integer, nullable=True)

    # Notifications
    sms_confirmation_sent = Column(Boolean, default=False)
    sms_ready_sent = Column(Boolean, default=False)
    sms_ready_sent_at = Column(DateTime, nullable=True)

    # Outcome
    table_ids = Column(JSON, nullable=True)
    seated_at = Column(DateTime, nullable=True)
    left_at = Column(DateTime, nullable=True)
    left_reason = Column(String(200), nullable=True)  # "too_long", "found_elsewhere", etc.

    # Notes
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    location = relationship("Location", backref="waitlist_entries")


class TableAvailability(Base):
    """Table availability and blocking rules."""
    __tablename__ = "table_availability"

    id = Column(Integer, primary_key=True, index=True)
    table_id = Column(Integer, nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)

    # Availability window
    date = Column(DateTime, nullable=False)
    start_time = Column(String(10), nullable=False)  # "18:00"
    end_time = Column(String(10), nullable=False)    # "20:00"

    # Status
    is_available = Column(Boolean, default=True)
    blocked_reason = Column(String(200), nullable=True)  # "private_event", "maintenance"
    reservation_id = Column(Integer, ForeignKey("reservations.id"), nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ReservationSettings(Base):
    """Reservation system configuration."""
    __tablename__ = "reservation_settings"

    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True, unique=True)

    # Booking rules
    min_party_size = Column(Integer, default=1)
    max_party_size = Column(Integer, default=20)
    default_duration_minutes = Column(Integer, default=90)
    booking_window_days = Column(Integer, default=30)  # How far ahead can book
    min_advance_hours = Column(Integer, default=1)     # Minimum hours before

    # Time slots
    slot_interval_minutes = Column(Integer, default=15)
    first_seating_time = Column(String(10), default="11:00")
    last_seating_time = Column(String(10), default="21:00")

    # Capacity management
    max_covers_per_slot = Column(Integer, nullable=True)
    buffer_between_seatings = Column(Integer, default=15)

    # Confirmations
    require_confirmation = Column(Boolean, default=True)
    auto_confirm = Column(Boolean, default=False)
    send_confirmation_email = Column(Boolean, default=True)
    send_confirmation_sms = Column(Boolean, default=True)

    # Reminders
    send_reminder_24h = Column(Boolean, default=True)
    send_reminder_2h = Column(Boolean, default=True)

    # No-show policy
    require_credit_card = Column(Boolean, default=False)
    require_credit_card_above = Column(Integer, nullable=True)  # Party size threshold
    no_show_fee_per_person = Column(Float, nullable=True)
    no_show_window_minutes = Column(Integer, default=15)  # Grace period

    # Waitlist
    enable_waitlist = Column(Boolean, default=True)
    waitlist_sms_notification = Column(Boolean, default=True)
    max_waitlist_size = Column(Integer, default=50)

    # Integration
    google_reserve_enabled = Column(Boolean, default=False)
    online_booking_enabled = Column(Boolean, default=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class GuestHistory(Base):
    """Track guest visit history for VIP handling."""
    __tablename__ = "guest_history"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, nullable=True)
    guest_phone = Column(String(50), nullable=True)
    guest_email = Column(String(255), nullable=True)

    # Visit stats
    total_visits = Column(Integer, default=0)
    total_spend = Column(Float, default=0.0)
    total_no_shows = Column(Integer, default=0)
    total_cancellations = Column(Integer, default=0)

    # Preferences learned
    preferred_tables = Column(JSON, nullable=True)
    preferred_servers = Column(JSON, nullable=True)
    dietary_restrictions = Column(JSON, nullable=True)
    favorite_items = Column(JSON, nullable=True)

    # VIP status
    is_vip = Column(Boolean, default=False)
    vip_notes = Column(Text, nullable=True)
    is_blacklisted = Column(Boolean, default=False)
    blacklist_reason = Column(Text, nullable=True)

    first_visit_at = Column(DateTime, nullable=True)
    last_visit_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

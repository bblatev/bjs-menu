"""Reservations & Waitlist schemas - TouchBistro style."""

from __future__ import annotations

from datetime import datetime, date, time
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, EmailStr

from app.models.reservations import ReservationStatus, WaitlistStatus, BookingSource


# Reservations

class ReservationBase(BaseModel):
    """Base reservation schema."""
    guest_name: str
    guest_phone: Optional[str] = None
    guest_email: Optional[str] = None
    party_size: int = Field(..., ge=1, le=100)
    reservation_date: datetime
    duration_minutes: int = 90
    table_ids: Optional[List[int]] = None
    seating_preference: Optional[str] = None
    special_requests: Optional[str] = None
    occasion: Optional[str] = None


class ReservationCreate(ReservationBase):
    """Create reservation schema."""
    location_id: int
    source: BookingSource = BookingSource.PHONE


class ReservationUpdate(BaseModel):
    """Update reservation schema."""
    guest_name: Optional[str] = None
    guest_phone: Optional[str] = None
    guest_email: Optional[str] = None
    party_size: Optional[int] = Field(None, ge=1, le=100)
    reservation_date: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    table_ids: Optional[List[int]] = None
    seating_preference: Optional[str] = None
    special_requests: Optional[str] = None
    occasion: Optional[str] = None
    status: Optional[ReservationStatus] = None


class ReservationResponse(ReservationBase):
    """Reservation response schema."""
    id: int
    location_id: Optional[int] = None
    customer_id: Optional[int] = None
    status: ReservationStatus
    source: BookingSource
    confirmation_code: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    arrived_at: Optional[datetime] = None
    seated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    reminder_24h_sent: bool = False
    reminder_2h_sent: bool = False
    is_vip: bool = False
    credit_card_on_file: bool = False
    dietary_restrictions: Optional[List[str]] = None
    internal_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReservationCalendar(BaseModel):
    """Daily reservation calendar view."""
    date: date
    location_id: int
    reservations: List[ReservationResponse]
    total_covers: int
    available_slots: List[Dict[str, Any]]


class AvailabilityRequest(BaseModel):
    """Request availability for a date/time."""
    location_id: int
    date: date
    party_size: int
    preferred_time: Optional[time] = None


class AvailabilityResponse(BaseModel):
    """Available time slots."""
    date: date
    party_size: int
    available_times: List[time]
    suggested_times: List[time]  # Best times based on table optimization


# Waitlist

class WaitlistBase(BaseModel):
    """Base waitlist schema."""
    guest_name: str
    guest_phone: Optional[str] = None
    party_size: int = Field(..., ge=1, le=100)
    quoted_wait_minutes: Optional[int] = None
    special_requests: Optional[str] = None


class WaitlistCreate(WaitlistBase):
    """Create waitlist entry schema."""
    location_id: int


class WaitlistUpdate(BaseModel):
    """Update waitlist entry schema."""
    guest_name: Optional[str] = None
    guest_phone: Optional[str] = None
    party_size: Optional[int] = Field(None, ge=1, le=100)
    quoted_wait_minutes: Optional[int] = None
    status: Optional[WaitlistStatus] = None


class WaitlistResponse(WaitlistBase):
    """Waitlist response schema."""
    id: int
    location_id: Optional[int] = None
    customer_id: Optional[int] = None
    status: WaitlistStatus
    position: Optional[int] = None
    added_at: datetime
    estimated_wait_minutes: Optional[int] = None
    sms_confirmation_sent: bool = False
    sms_ready_sent: bool = False
    sms_ready_sent_at: Optional[datetime] = None
    table_ids: Optional[List[int]] = None
    seated_at: Optional[datetime] = None
    left_at: Optional[datetime] = None
    left_reason: Optional[str] = None
    actual_wait_minutes: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class WaitlistNotification(BaseModel):
    """Notification to send to waitlist guest."""
    waitlist_id: int
    message_type: str = "table_ready"  # table_ready, reminder, update


# Table Availability

class TableAvailabilityBase(BaseModel):
    """Base table availability schema."""
    table_id: int
    available_from: time
    available_until: time


class TableAvailabilityResponse(TableAvailabilityBase):
    """Table availability response."""
    id: int
    location_id: int
    date: date
    is_blocked: bool = False
    block_reason: Optional[str] = None

    model_config = {"from_attributes": True}


class TableBlockRequest(BaseModel):
    """Request to block a table."""
    table_id: int
    date: date
    start_time: time
    end_time: time
    reason: str


# Reservation Settings

class ReservationSettingsBase(BaseModel):
    """Base reservation settings schema."""
    min_party_size: int = 1
    max_party_size: int = 20
    default_duration_minutes: int = 90
    booking_window_days: int = 30
    min_advance_hours: int = 1
    slot_interval_minutes: int = 15
    first_seating_time: str = "11:00"
    last_seating_time: str = "21:00"
    max_covers_per_slot: Optional[int] = None
    buffer_between_seatings: int = 15
    require_confirmation: bool = True
    auto_confirm: bool = False
    send_confirmation_email: bool = True
    send_confirmation_sms: bool = True
    send_reminder_24h: bool = True
    send_reminder_2h: bool = True
    require_credit_card: bool = False
    require_credit_card_above: Optional[int] = None
    no_show_fee_per_person: Optional[float] = None
    no_show_window_minutes: int = 15
    enable_waitlist: bool = True
    waitlist_sms_notification: bool = True
    max_waitlist_size: int = 50
    google_reserve_enabled: bool = False
    online_booking_enabled: bool = True


class ReservationSettingsCreate(ReservationSettingsBase):
    """Create reservation settings schema."""
    location_id: int


class ReservationSettingsResponse(ReservationSettingsBase):
    """Reservation settings response schema."""
    id: int
    location_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# Guest History

class GuestHistoryResponse(BaseModel):
    """Guest history and preferences."""
    id: int
    customer_id: Optional[int] = None
    guest_phone: Optional[str] = None
    guest_email: Optional[str] = None
    total_visits: int = 0
    total_spend: float = 0.0
    total_no_shows: int = 0
    total_cancellations: int = 0
    preferred_tables: Optional[List[int]] = None
    preferred_servers: Optional[List[int]] = None
    dietary_restrictions: Optional[List[str]] = None
    favorite_items: Optional[List[int]] = None
    is_vip: bool = False
    vip_notes: Optional[str] = None
    is_blacklisted: bool = False
    blacklist_reason: Optional[str] = None
    first_visit_at: Optional[datetime] = None
    last_visit_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GuestNotesUpdate(BaseModel):
    """Update guest notes/preferences."""
    dietary_restrictions: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None
    vip_status: Optional[bool] = None
    notes: Optional[str] = None


# SMS Templates

class SMSTemplateResponse(BaseModel):
    """SMS template for reservations."""
    template_type: str
    template_text: str
    variables: List[str]


class SMSPreview(BaseModel):
    """Preview SMS message."""
    phone: str
    message: str


# ---------------------------------------------------------------------------
# Google Reserve with Google Integration
# ---------------------------------------------------------------------------

class GoogleSlot(BaseModel):
    """A single bookable time slot for Google Reserve."""
    slot_id: str
    start_time: datetime
    end_time: datetime
    party_size: int = Field(..., ge=1)
    available: bool = True
    resource_id: Optional[str] = None


class GoogleAvailabilityRequest(BaseModel):
    """Request availability from Google Reserve."""
    merchant_id: str
    service_id: Optional[str] = None
    start_time: datetime
    end_time: datetime
    party_size: int = Field(..., ge=1, le=100)
    resource_ids: Optional[List[str]] = None


class GoogleAvailabilityResponse(BaseModel):
    """Availability response for Google Reserve."""
    merchant_id: str
    slots: List[GoogleSlot] = []
    next_page_token: Optional[str] = None


class GoogleUserInfo(BaseModel):
    """User information provided by Google during booking."""
    google_user_id: Optional[str] = None
    given_name: str
    family_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    language_code: Optional[str] = "en"


class GoogleBookingRequest(BaseModel):
    """Booking request from Google Reserve."""
    slot_id: str
    merchant_id: str
    service_id: Optional[str] = None
    party_size: int = Field(..., ge=1, le=100)
    user_info: GoogleUserInfo
    idempotency_token: str
    additional_request: Optional[str] = None
    payment_info: Optional[Dict[str, Any]] = None


class GoogleBookingResponse(BaseModel):
    """Booking response for Google Reserve."""
    booking_id: str
    slot_id: str
    merchant_id: str
    status: str = "confirmed"
    user_info: GoogleUserInfo
    party_size: int
    start_time: datetime
    end_time: datetime
    confirmation_code: Optional[str] = None
    prepayment_status: Optional[str] = None
    created_at: datetime


class GoogleBookingStatusRequest(BaseModel):
    """Request to check booking status via Google Reserve."""
    booking_id: str
    merchant_id: str


class GoogleBookingUpdateRequest(BaseModel):
    """Request to update an existing Google booking."""
    booking_id: str
    merchant_id: str
    slot_id: Optional[str] = None
    party_size: Optional[int] = Field(None, ge=1, le=100)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: Optional[str] = None


class GoogleCancelRequest(BaseModel):
    """Request to cancel a Google Reserve booking."""
    booking_id: str
    merchant_id: str
    cancel_reason: Optional[str] = None
    cancelled_by: str = "user"  # user | merchant


class GoogleHealthCheckResponse(BaseModel):
    """Health check response for the Google Reserve integration."""
    status: str = "healthy"
    server_time: datetime
    api_version: str = "v2"
    merchant_count: int = 0
    supported_features: List[str] = []
    latency_ms: Optional[float] = None

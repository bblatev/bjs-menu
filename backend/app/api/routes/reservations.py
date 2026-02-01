"""Reservations & Waitlist routes - TouchBistro style."""

from typing import List, Optional, Union
from datetime import date, time, datetime
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

from app.db.session import DbSession
from app.models.reservations import (
    Reservation, Waitlist, ReservationSettings, GuestHistory,
    ReservationStatus, WaitlistStatus
)
from app.services.reservations_service import ReservationService, WaitlistService
from app.schemas.reservations import (
    ReservationCreate, ReservationUpdate, ReservationResponse, ReservationCalendar,
    AvailabilityRequest, AvailabilityResponse,
    WaitlistCreate, WaitlistUpdate, WaitlistResponse,
    ReservationSettingsCreate, ReservationSettingsResponse,
    GuestHistoryResponse, GuestNotesUpdate
)

router = APIRouter()


# Flexible reservation creation schema for frontend compatibility
class FlexibleReservationCreate(BaseModel):
    """Flexible reservation creation - accepts multiple date/time formats."""
    guest_name: str
    guest_phone: Optional[str] = None
    guest_email: Optional[str] = None
    party_size: int = Field(..., ge=1, le=100)
    # Accept either reservation_date (datetime) OR date + time separately
    reservation_date: Optional[datetime] = None
    date: Optional[str] = None  # YYYY-MM-DD
    time: Optional[str] = None  # HH:MM
    duration_minutes: int = 90
    location_id: int = 1  # Default to location 1
    table_ids: Optional[List[int]] = None
    seating_preference: Optional[str] = None
    special_requests: Optional[str] = None
    occasion: Optional[str] = None
    notes: Optional[str] = None


# ==================== WAITLIST ROUTES (must be before /{reservation_id}) ====================

@router.get("/waitlist", response_model=List[WaitlistResponse])
def list_waitlist_no_slash(
    db: DbSession,
    location_id: int = Query(1),
    status: Optional[str] = None,
):
    """List current waitlist (no trailing slash)."""
    query = db.query(Waitlist).filter(
        Waitlist.location_id == location_id
    )

    if status:
        query = query.filter(Waitlist.status == status)
    else:
        query = query.filter(Waitlist.status == WaitlistStatus.WAITING)

    return query.order_by(Waitlist.added_at).all()


@router.get("/waitlist/", response_model=List[WaitlistResponse])
def list_waitlist(
    db: DbSession,
    location_id: int = Query(1),
    status: Optional[str] = None,
):
    """List current waitlist."""
    query = db.query(Waitlist).filter(
        Waitlist.location_id == location_id
    )

    if status:
        query = query.filter(Waitlist.status == status)
    else:
        query = query.filter(Waitlist.status == WaitlistStatus.WAITING)

    return query.order_by(Waitlist.added_at).all()


@router.post("/waitlist", response_model=WaitlistResponse)
async def add_to_waitlist_no_slash(
    db: DbSession,
    entry: WaitlistCreate,
):
    """Add guest to waitlist (no trailing slash)."""
    service = WaitlistService(db)
    result = await service.add_to_waitlist(entry.model_dump())

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result["entry"]


@router.post("/waitlist/", response_model=WaitlistResponse)
async def add_to_waitlist(
    db: DbSession,
    entry: WaitlistCreate,
):
    """Add guest to waitlist."""
    service = WaitlistService(db)
    result = await service.add_to_waitlist(entry.model_dump())

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result["entry"]


@router.get("/waitlist/{waitlist_id}", response_model=WaitlistResponse)
def get_waitlist_entry(db: DbSession, waitlist_id: int):
    """Get waitlist entry."""
    entry = db.query(Waitlist).filter(Waitlist.id == waitlist_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Waitlist entry not found")
    return entry


@router.put("/waitlist/{waitlist_id}", response_model=WaitlistResponse)
def update_waitlist_entry(
    db: DbSession,
    waitlist_id: int,
    update: WaitlistUpdate,
):
    """Update waitlist entry."""
    entry = db.query(Waitlist).filter(Waitlist.id == waitlist_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Waitlist entry not found")

    for key, value in update.model_dump(exclude_unset=True).items():
        setattr(entry, key, value)

    db.commit()
    db.refresh(entry)
    return entry


@router.post("/waitlist/{waitlist_id}/notify")
async def notify_waitlist_guest(
    db: DbSession,
    waitlist_id: int,
):
    """Send table-ready notification to waitlist guest."""
    service = WaitlistService(db)
    result = await service.notify_guest(waitlist_id)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.post("/waitlist/{waitlist_id}/seat", response_model=WaitlistResponse)
def seat_waitlist_guest(
    db: DbSession,
    waitlist_id: int,
    table_ids: Optional[List[int]] = None,
):
    """Seat a waitlist guest."""
    service = WaitlistService(db)
    result = service.seat_guest(waitlist_id, table_ids)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result["entry"]


@router.post("/waitlist/{waitlist_id}/remove")
async def remove_from_waitlist(
    db: DbSession,
    waitlist_id: int,
    reason: Optional[str] = None,
):
    """Remove guest from waitlist."""
    service = WaitlistService(db)
    result = await service.remove_from_waitlist(waitlist_id, reason)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


# ==================== SETTINGS ROUTES ====================

@router.get("/settings/{location_id}", response_model=ReservationSettingsResponse)
def get_reservation_settings(db: DbSession, location_id: int):
    """Get reservation settings for a location."""
    settings = db.query(ReservationSettings).filter(
        ReservationSettings.location_id == location_id
    ).first()

    if not settings:
        # Return default settings if none exist
        return ReservationSettingsResponse(
            id=0,
            location_id=location_id,
            min_party_size=1,
            max_party_size=20,
            default_duration_minutes=90,
            booking_window_days=30,
            min_advance_hours=1,
            slot_interval_minutes=15,
            first_seating_time="11:00",
            last_seating_time="21:00",
            max_covers_per_slot=None,
            buffer_between_seatings=15,
            require_confirmation=True,
            auto_confirm=False,
            send_confirmation_email=True,
            send_confirmation_sms=True,
            send_reminder_24h=True,
            send_reminder_2h=True,
            require_credit_card=False,
            require_credit_card_above=None,
            no_show_fee_per_person=None,
            no_show_window_minutes=15,
            enable_waitlist=True,
            waitlist_sms_notification=True,
            max_waitlist_size=50,
            google_reserve_enabled=False,
            online_booking_enabled=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

    return settings


@router.post("/settings/", response_model=ReservationSettingsResponse)
def create_reservation_settings(
    db: DbSession,
    settings: ReservationSettingsCreate,
):
    """Create reservation settings."""
    db_settings = ReservationSettings(**settings.model_dump())
    db.add(db_settings)
    db.commit()
    db.refresh(db_settings)
    return db_settings


# ==================== GUEST ROUTES ====================

@router.get("/guests/search/", response_model=List[GuestHistoryResponse])
def search_guests(
    db: DbSession,
    q: str = Query(..., min_length=2),
):
    """Search guests by phone or email."""
    from sqlalchemy import or_

    guests = db.query(GuestHistory).filter(
        or_(
            GuestHistory.guest_phone.ilike(f"%{q}%"),
            GuestHistory.guest_email.ilike(f"%{q}%")
        )
    ).limit(20).all()

    return guests


@router.get("/guests/{customer_id}", response_model=GuestHistoryResponse)
def get_guest_history(db: DbSession, customer_id: int):
    """Get guest history and preferences."""
    history = db.query(GuestHistory).filter(
        GuestHistory.customer_id == customer_id
    ).first()

    if not history:
        raise HTTPException(status_code=404, detail="Guest history not found")

    return history


@router.put("/guests/{customer_id}/notes", response_model=GuestHistoryResponse)
def update_guest_notes(
    db: DbSession,
    customer_id: int,
    notes: GuestNotesUpdate,
):
    """Update guest notes and preferences."""
    history = db.query(GuestHistory).filter(
        GuestHistory.customer_id == customer_id
    ).first()

    if not history:
        history = GuestHistory(customer_id=customer_id)
        db.add(history)

    for key, value in notes.model_dump(exclude_unset=True).items():
        setattr(history, key, value)

    db.commit()
    db.refresh(history)
    return history


# ==================== CALENDAR & AVAILABILITY ====================

@router.get("/calendar/{location_id}", response_model=ReservationCalendar)
def get_reservation_calendar(
    db: DbSession,
    location_id: int,
    target_date: date = Query(...),
):
    """Get reservation calendar for a day."""
    reservations = db.query(Reservation).filter(
        Reservation.location_id == location_id,
        Reservation.reservation_date == target_date,
        Reservation.status.notin_([ReservationStatus.CANCELLED, ReservationStatus.NO_SHOW])
    ).order_by(Reservation.reservation_date).all()

    total_covers = sum(r.party_size for r in reservations)

    # Get available slots
    service = ReservationService(db)
    available = service.get_available_slots(location_id, target_date)

    return ReservationCalendar(
        date=target_date,
        location_id=location_id,
        reservations=reservations,
        total_covers=total_covers,
        available_slots=available
    )


@router.post("/availability", response_model=AvailabilityResponse)
def check_availability(db: DbSession, request: AvailabilityRequest):
    """Check availability for a specific party size and date."""
    service = ReservationService(db)
    result = service.check_availability(
        location_id=request.location_id,
        date=request.date,
        party_size=request.party_size,
        preferred_time=request.preferred_time
    )

    # Convert string times to time objects
    def parse_time(t):
        if isinstance(t, time):
            return t
        if isinstance(t, dict):
            t = t.get("time", "00:00")
        if isinstance(t, str):
            parts = t.split(":")
            return time(int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)
        return t

    available = [parse_time(t) for t in result.get("available_times", [])]
    suggested = [parse_time(t) for t in result.get("suggested_times", [])]

    return AvailabilityResponse(
        date=request.date,
        party_size=request.party_size,
        available_times=available,
        suggested_times=suggested
    )


# ==================== RESERVATION CRUD ====================

@router.get("/", response_model=List[ReservationResponse])
def list_reservations(
    db: DbSession,
    location_id: Optional[int] = Query(None),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    status: Optional[str] = None,
    date: Optional[date] = None,  # Alias for date_from for frontend compatibility
):
    """List reservations."""
    query = db.query(Reservation)

    if location_id:
        query = query.filter(Reservation.location_id == location_id)

    # Handle date alias
    if date and not date_from:
        date_from = date

    if date_from:
        query = query.filter(Reservation.reservation_date >= date_from)
    if date_to:
        query = query.filter(Reservation.reservation_date <= date_to)
    if status:
        query = query.filter(Reservation.status == status)

    return query.order_by(Reservation.reservation_date).all()


@router.post("/", response_model=ReservationResponse)
async def create_reservation(
    db: DbSession,
    reservation: FlexibleReservationCreate,
    background_tasks: BackgroundTasks,
):
    """Create a new reservation with flexible date/time formats."""
    # Build reservation_date from separate date/time if not provided
    res_datetime = reservation.reservation_date
    if not res_datetime and reservation.date:
        date_str = reservation.date
        time_str = reservation.time or "12:00"
        try:
            res_datetime = datetime.fromisoformat(f"{date_str}T{time_str}:00")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date or time format")

    if not res_datetime:
        raise HTTPException(status_code=400, detail="Either reservation_date or date+time is required")

    # Build the data dict for the service
    data = {
        "guest_name": reservation.guest_name,
        "guest_phone": reservation.guest_phone,
        "guest_email": reservation.guest_email,
        "party_size": reservation.party_size,
        "reservation_date": res_datetime,
        "duration_minutes": reservation.duration_minutes,
        "location_id": reservation.location_id,
        "table_ids": reservation.table_ids,
        "seating_preference": reservation.seating_preference,
        "special_requests": reservation.special_requests or reservation.notes,
        "occasion": reservation.occasion,
    }

    service = ReservationService(db)
    result = await service.create_reservation(data)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result["reservation"]


# ==================== RESERVATION BY ID (must be LAST) ====================

@router.get("/{reservation_id}", response_model=ReservationResponse)
def get_reservation(db: DbSession, reservation_id: int):
    """Get reservation by ID."""
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")
    return reservation


@router.put("/{reservation_id}", response_model=ReservationResponse)
def update_reservation(
    db: DbSession,
    reservation_id: int,
    reservation: ReservationUpdate,
):
    """Update a reservation."""
    db_reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not db_reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    for key, value in reservation.model_dump(exclude_unset=True).items():
        setattr(db_reservation, key, value)

    db.commit()
    db.refresh(db_reservation)
    return db_reservation


@router.post("/{reservation_id}/confirm", response_model=ReservationResponse)
def confirm_reservation(db: DbSession, reservation_id: int):
    """Confirm a reservation."""
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    reservation.status = ReservationStatus.CONFIRMED
    reservation.confirmed_at = datetime.utcnow()
    db.commit()
    db.refresh(reservation)
    return reservation


@router.post("/{reservation_id}/seat", response_model=ReservationResponse)
def seat_reservation(
    db: DbSession,
    reservation_id: int,
    table_ids: Optional[List[int]] = None,
):
    """Mark reservation as seated."""
    service = ReservationService(db)
    result = service.seat_reservation(reservation_id, table_ids)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result["reservation"]


@router.post("/{reservation_id}/complete", response_model=ReservationResponse)
def complete_reservation(db: DbSession, reservation_id: int):
    """Mark reservation as completed."""
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    reservation.status = ReservationStatus.COMPLETED
    reservation.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(reservation)
    return reservation


@router.post("/{reservation_id}/no-show", response_model=ReservationResponse)
def mark_no_show(db: DbSession, reservation_id: int):
    """Mark reservation as no-show."""
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    reservation.status = ReservationStatus.NO_SHOW
    reservation.no_show_at = datetime.utcnow()
    db.commit()
    db.refresh(reservation)
    return reservation


@router.post("/{reservation_id}/cancel", response_model=ReservationResponse)
async def cancel_reservation(
    db: DbSession,
    reservation_id: int,
    reason: Optional[str] = None,
):
    """Cancel a reservation."""
    service = ReservationService(db)
    result = await service.cancel_reservation(reservation_id, reason)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result["reservation"]


@router.post("/{reservation_id}/send-reminder")
async def send_reservation_reminder(
    db: DbSession,
    reservation_id: int,
):
    """Send reminder for a reservation."""
    service = ReservationService(db)
    result = await service.send_reminder(reservation_id)
    return result

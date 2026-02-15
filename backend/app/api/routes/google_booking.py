"""
Google Maps Booking API (Reserve with Google)

This module implements the Reserve with Google API for table reservations.
https://developers.google.com/maps-booking/reference/rest-api-v3

Endpoints:
- HealthCheck: Verify server availability
- CheckAvailability: Check slot availability
- CreateBooking: Create a new reservation
- UpdateBooking: Modify existing reservation
- GetBookingStatus: Get reservation status
- ListBookings: List all reservations (batch)
"""

from fastapi import APIRouter, HTTPException, Depends, Header, Request
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta, timezone
from dateutil import parser as date_parser
import secrets
import logging

from app.core.rate_limit import limiter
from app.core.config import settings
from app.db.session import get_db
from app.models import Reservation, ReservationStatus, BookingSource, Table, Venue
from app.schemas.reservations import (
    GoogleSlot,
    GoogleAvailabilityRequest,
    GoogleAvailabilityResponse,
    GoogleBookingRequest,
    GoogleBookingResponse,
    GoogleBookingStatusRequest,
    GoogleBookingUpdateRequest,
    GoogleCancelRequest,
    GoogleHealthCheckResponse,
    GoogleUserInfo,
)


router = APIRouter()
logger = logging.getLogger(__name__)

# Default venue ID for Google bookings
DEFAULT_VENUE_ID = 1


def verify_google_signature(request: Request, signature: str = Header(None, alias="X-Goog-Signature")) -> bool:
    """
    Verify the Google webhook signature using HMAC-SHA256.
    Uses GOOGLE_WEBHOOK_SECRET from environment/settings.
    """
    import hmac
    import hashlib
    import os

    # Get webhook secret from environment
    webhook_secret = settings.google_webhook_secret

    # If no secret configured, log warning but allow in non-production
    if not webhook_secret:
        import logging
        logger = logging.getLogger(__name__)
        env = settings.environment
        if env == "production":
            logger.error("GOOGLE_WEBHOOK_SECRET not configured in production!")
            return False
        logger.warning("GOOGLE_WEBHOOK_SECRET not configured - allowing request in development mode")
        return True

    # Verify signature if provided
    if not signature:
        return False

    # Calculate expected signature
    try:
        expected = hmac.new(
            webhook_secret.encode('utf-8'),
            msg=request.url.path.encode('utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(signature, expected)
    except Exception as e:
        logger.warning(f"Google webhook signature verification failed: {e}")
        return False


def generate_booking_id() -> str:
    """Generate a unique booking ID for Google"""
    return f"BJS-{secrets.token_hex(8).upper()}"


def parse_google_datetime(iso_string: str) -> datetime:
    """Parse ISO 8601 datetime from Google"""
    return date_parser.parse(iso_string)


def format_google_datetime(dt: datetime) -> str:
    """Format datetime for Google API response"""
    return dt.strftime("%Y-%m-%dT%H:%M:%S%z")


def reservation_to_google_response(reservation: Reservation) -> GoogleBookingResponse:
    """Convert internal reservation to Google booking response"""
    # Map internal status to Google status
    status_map = {
        "pending": "PENDING",
        "confirmed": "CONFIRMED",
        "seated": "CONFIRMED",
        "completed": "CONFIRMED",
        "cancelled": "CANCELLED",
        "no_show": "NO_SHOW",
    }

    return GoogleBookingResponse(
        booking_id=reservation.external_booking_id or str(reservation.id),
        slot=GoogleSlot(
            start_time=format_google_datetime(reservation.reservation_date),
            duration_seconds=reservation.duration_minutes * 60,
        ),
        user_information=GoogleUserInfo(
            user_id=reservation.guest_email or str(reservation.id),
            given_name=reservation.guest_name.split()[0] if reservation.guest_name else "",
            family_name=" ".join(reservation.guest_name.split()[1:]) if reservation.guest_name and len(reservation.guest_name.split()) > 1 else "",
            email=reservation.guest_email,
            phone=reservation.guest_phone,
        ),
        party_size=reservation.party_size,
        status=status_map.get(reservation.status.value, "PENDING"),
    )


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/health", response_model=GoogleHealthCheckResponse)
@limiter.limit("60/minute")
async def health_check(request: Request):
    """
    Health check endpoint for Google to verify server availability.
    Google will poll this endpoint to ensure the booking server is operational.
    """
    return GoogleHealthCheckResponse(serving_status="SERVING")


# ============================================================================
# AVAILABILITY CHECK
# ============================================================================

@router.post("/v3/CheckAvailability", response_model=GoogleAvailabilityResponse)
@limiter.limit("30/minute")
async def check_availability(
    request: Request,
    availability_data: GoogleAvailabilityRequest,
    db: Session = Depends(get_db),
):
    """
    Check availability for a specific time slot.
    Returns the number of available tables for the requested party size.
    """
    try:
        slot_time = parse_google_datetime(availability_data.slot.start_time)
        duration_minutes = availability_data.slot.duration_seconds // 60

        # Get all active tables that can accommodate the party
        suitable_tables = db.query(Table).filter(
            Table.venue_id == DEFAULT_VENUE_ID,
            Table.active == True,
            Table.seats >= availability_data.party_size
        ).all()

        if not suitable_tables:
            return GoogleAvailabilityResponse(
                slot=availability_data.slot,
                count_available=0,
            )

        # Check for conflicting reservations
        slot_end = slot_time + timedelta(minutes=duration_minutes)

        conflicting_reservations = db.query(Reservation).filter(
            Reservation.venue_id == DEFAULT_VENUE_ID,
            Reservation.status.in_([
                ReservationStatus.pending,
                ReservationStatus.confirmed,
                ReservationStatus.seated
            ]),
            Reservation.reservation_date < slot_end,
            Reservation.reservation_date + timedelta(minutes=90) > slot_time  # Assume 90 min default
        ).all()

        # Get table IDs with conflicts
        booked_table_ids = {r.table_id for r in conflicting_reservations if r.table_id}

        # Count available tables
        available_count = sum(1 for t in suitable_tables if t.id not in booked_table_ids)

        return GoogleAvailabilityResponse(
            slot=availability_data.slot,
            count_available=available_count,
        )

    except Exception as e:
        logger.error(f"CheckAvailability error: {e}")
        raise HTTPException(status_code=500, detail="Availability check failed")


# ============================================================================
# CREATE BOOKING
# ============================================================================

@router.post("/v3/CreateBooking", response_model=GoogleBookingResponse)
@limiter.limit("30/minute")
async def create_booking(
    request: Request,
    booking_data: GoogleBookingRequest,
    db: Session = Depends(get_db),
):
    """
    Create a new reservation from Google Maps.
    This is called when a user completes a booking on Google.
    """
    try:
        # Check for idempotency - if booking already exists with this token
        existing = db.query(Reservation).filter(
            Reservation.external_booking_id == booking_data.idempotency_token
        ).first()

        if existing:
            return reservation_to_google_response(existing)

        # Parse the slot time
        slot_time = parse_google_datetime(booking_data.slot.start_time)
        duration_minutes = booking_data.slot.duration_seconds // 60

        # Find an available table
        suitable_tables = db.query(Table).filter(
            Table.venue_id == DEFAULT_VENUE_ID,
            Table.active == True,
            Table.seats >= booking_data.party_size
        ).order_by(Table.seats.asc()).all()  # Prefer smaller tables

        # Check availability and find a table
        slot_end = slot_time + timedelta(minutes=duration_minutes)
        available_table = None

        for table in suitable_tables:
            conflict = db.query(Reservation).filter(
                Reservation.table_id == table.id,
                Reservation.status.in_([
                    ReservationStatus.pending,
                    ReservationStatus.confirmed,
                    ReservationStatus.seated
                ]),
                Reservation.reservation_date < slot_end,
            ).first()

            if not conflict:
                available_table = table
                break

        if not available_table:
            raise HTTPException(
                status_code=409,
                detail="No tables available for the requested time slot"
            )

        # Create guest name from user info
        guest_name = f"{booking_data.user_information.given_name or ''} {booking_data.user_information.family_name or ''}".strip()
        if not guest_name:
            guest_name = "Google Guest"

        # Generate booking ID
        booking_id = generate_booking_id()

        # Create the reservation
        reservation = Reservation(
            venue_id=DEFAULT_VENUE_ID,
            table_id=available_table.id,
            guest_name=guest_name,
            guest_email=booking_data.user_information.email,
            guest_phone=booking_data.user_information.phone,
            party_size=booking_data.party_size,
            reservation_date=slot_time,
            duration_minutes=duration_minutes,
            status=ReservationStatus.confirmed,  # Auto-confirm Google bookings
            confirmed_at=datetime.now(timezone.utc),
            booking_source=BookingSource.google,
            external_booking_id=booking_id,
            special_requests=booking_data.additional_request,
            confirmation_code=secrets.token_hex(4).upper(),
        )

        db.add(reservation)
        db.commit()
        db.refresh(reservation)

        logger.info(f"Created Google booking: {booking_id} for {guest_name}")

        return reservation_to_google_response(reservation)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"CreateBooking error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Booking creation failed")


# ============================================================================
# GET BOOKING STATUS
# ============================================================================

@router.post("/v3/GetBookingStatus", response_model=GoogleBookingResponse)
@limiter.limit("30/minute")
async def get_booking_status(
    request: Request,
    status_data: GoogleBookingStatusRequest,
    db: Session = Depends(get_db),
):
    """
    Get the current status of a booking.
    Called by Google to sync booking status.
    """
    reservation = db.query(Reservation).filter(
        Reservation.external_booking_id == status_data.booking_id
    ).first()

    if not reservation:
        # Try to find by internal ID
        try:
            internal_id = int(status_data.booking_id)
            reservation = db.query(Reservation).filter(
                Reservation.id == internal_id,
                Reservation.booking_source == BookingSource.google
            ).first()
        except ValueError:
            pass

    if not reservation:
        raise HTTPException(status_code=404, detail="Booking not found")

    return reservation_to_google_response(reservation)


# ============================================================================
# UPDATE BOOKING
# ============================================================================

@router.post("/v3/UpdateBooking", response_model=GoogleBookingResponse)
@limiter.limit("30/minute")
async def update_booking(
    request: Request,
    update_data: GoogleBookingUpdateRequest,
    db: Session = Depends(get_db),
):
    """
    Update an existing booking.
    Handles rescheduling and modifications from Google.
    """
    reservation = db.query(Reservation).filter(
        Reservation.external_booking_id == update_data.booking.booking_id
    ).first()

    if not reservation:
        raise HTTPException(status_code=404, detail="Booking not found")

    try:
        # Update fields based on the request
        if update_data.booking.slot:
            new_time = parse_google_datetime(update_data.booking.slot.start_time)
            reservation.reservation_date = new_time
            reservation.duration_minutes = update_data.booking.slot.duration_seconds // 60

        if update_data.booking.party_size:
            reservation.party_size = update_data.booking.party_size

        if update_data.booking.user_information:
            if update_data.booking.user_information.email:
                reservation.guest_email = update_data.booking.user_information.email
            if update_data.booking.user_information.phone:
                reservation.guest_phone = update_data.booking.user_information.phone
            if update_data.booking.user_information.given_name:
                reservation.guest_name = f"{update_data.booking.user_information.given_name} {update_data.booking.user_information.family_name or ''}".strip()

        reservation.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(reservation)

        logger.info(f"Updated Google booking: {update_data.booking.booking_id}")

        return reservation_to_google_response(reservation)

    except Exception as e:
        logger.error(f"UpdateBooking error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Booking update failed")


# ============================================================================
# CANCEL BOOKING
# ============================================================================

@router.post("/v3/CancelBooking", response_model=GoogleBookingResponse)
@limiter.limit("30/minute")
async def cancel_booking(
    request: Request,
    cancel_data: GoogleCancelRequest,
    db: Session = Depends(get_db),
):
    """
    Cancel a booking.
    Called when user cancels through Google Maps.
    """
    reservation = db.query(Reservation).filter(
        Reservation.external_booking_id == cancel_data.booking_id
    ).first()

    if not reservation:
        raise HTTPException(status_code=404, detail="Booking not found")

    reservation.status = ReservationStatus.cancelled
    reservation.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(reservation)

    logger.info(f"Cancelled Google booking: {cancel_data.booking_id}")

    return reservation_to_google_response(reservation)


# ============================================================================
# LIST BOOKINGS (Batch sync)
# ============================================================================

@router.get("/v3/ListBookings")
@limiter.limit("60/minute")
async def list_bookings(
    request: Request,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    List all Google bookings for sync purposes.
    Used by Google for batch synchronization.
    """
    query = db.query(Reservation).filter(
        Reservation.booking_source == BookingSource.google
    )

    if start_time:
        query = query.filter(Reservation.reservation_date >= parse_google_datetime(start_time))
    if end_time:
        query = query.filter(Reservation.reservation_date <= parse_google_datetime(end_time))

    reservations = query.order_by(Reservation.reservation_date.asc()).all()

    return {
        "bookings": [reservation_to_google_response(r) for r in reservations]
    }


# ============================================================================
# FEEDS ENDPOINTS (For Google data ingestion)
# ============================================================================

@router.get("/feeds/services")
@limiter.limit("60/minute")
async def get_services_feed(request: Request, db: Session = Depends(get_db)):
    """
    Returns the service feed for Google.
    Describes the booking service (table reservation).
    """
    venue = db.query(Venue).filter(Venue.id == DEFAULT_VENUE_ID).first()

    return {
        "service": {
            "service_id": "table-reservation",
            "service_name": {
                "text": "Table Reservation",
                "language": "en"
            },
            "service_description": {
                "text": "Reserve a table at BJ's Bar Borovets",
                "language": "en"
            },
            "prepayment_type": "NOT_REQUIRED",
            "tax_rate": {
                "micro_percent": 0
            }
        }
    }


@router.get("/feeds/availability")
@limiter.limit("60/minute")
async def get_availability_feed(
    request: Request,
    date: Optional[str] = None,
    days: int = 7,
    db: Session = Depends(get_db),
):
    """
    Returns availability feed for Google.
    Shows available time slots for the next N days.
    """
    start_date = datetime.strptime(date, "%Y-%m-%d") if date else datetime.now()
    end_date = start_date + timedelta(days=days)

    # Get venue info
    venue = db.query(Venue).filter(Venue.id == DEFAULT_VENUE_ID).first()
    tables = db.query(Table).filter(
        Table.venue_id == DEFAULT_VENUE_ID,
        Table.active == True
    ).all()

    max_capacity = max([t.seats for t in tables], default=4)

    # Generate slots (every 30 minutes from 10:00 to 22:00)
    slots = []
    current = start_date.replace(hour=10, minute=0, second=0, microsecond=0)

    while current < end_date:
        if current.hour >= 10 and current.hour < 22:  # Operating hours
            # Check availability for each slot
            slot_end = current + timedelta(minutes=90)

            # Count available tables
            available_count = 0
            for table in tables:
                conflict = db.query(Reservation).filter(
                    Reservation.table_id == table.id,
                    Reservation.status.in_([
                        ReservationStatus.pending,
                        ReservationStatus.confirmed,
                        ReservationStatus.seated
                    ]),
                    Reservation.reservation_date < slot_end,
                    Reservation.reservation_date + timedelta(minutes=90) > current
                ).first()

                if not conflict:
                    available_count += 1

            if available_count > 0:
                slots.append({
                    "start_time": format_google_datetime(current.replace(tzinfo=None)),
                    "duration_seconds": 5400,  # 90 minutes
                    "spots_open": available_count,
                    "spots_total": len(tables),
                })

        current += timedelta(minutes=30)

    return {
        "availability": slots,
        "merchant_id": f"bjs-bar-{DEFAULT_VENUE_ID}",
        "service_id": "table-reservation",
    }


@router.get("/feeds/merchant")
@limiter.limit("60/minute")
async def get_merchant_feed(request: Request, db: Session = Depends(get_db)):
    """
    Returns the merchant feed for Google Business Profile integration.
    """
    venue = db.query(Venue).filter(Venue.id == DEFAULT_VENUE_ID).first()

    return {
        "merchant": {
            "merchant_id": f"bjs-bar-{DEFAULT_VENUE_ID}",
            "name": (venue.name.get("en", "BJ's Bar") if isinstance(venue.name, dict) else venue.name) if venue else "BJ's Bar Borovets",
            "address": {
                "street_address": venue.address if venue else "Borovets Resort",
                "locality": "Borovets",
                "region": "Sofia Province",
                "country": "BG",
                "postal_code": "2010"
            },
            "geo": {
                "latitude": 42.2677,
                "longitude": 23.6089
            },
            "phone": venue.phone if venue else "+359 888 123 456",
            "url": "https://bjsbar.bg",
            "category": "restaurant",
            "payment_options": ["VISA", "MASTERCARD", "CASH"],
        }
    }

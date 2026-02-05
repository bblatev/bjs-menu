"""Google Reserve (Reserve with Google) API routes.

These endpoints implement the Google Maps Booking API server interface.
Google will call these endpoints to check availability and create bookings.
"""

from typing import Optional, List
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Request, Header
from pydantic import BaseModel

from app.services.google_reserve_service import (
    get_google_reserve_service,
    BookingStatus,
    TimeSlot,
    MerchantInfo,
)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class SlotRequest(BaseModel):
    merchant_id: str
    service_id: str
    start_sec: int
    duration_sec: int
    availability_tag: Optional[str] = None


class UserInformation(BaseModel):
    user_id: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    telephone: Optional[str] = None
    email: Optional[str] = None


class CheckAvailabilityRequest(BaseModel):
    slot: SlotRequest
    party_size: Optional[int] = 2


class CreateBookingRequest(BaseModel):
    slot: SlotRequest
    user_information: UserInformation
    party_size: int = 2
    idempotency_token: Optional[str] = None
    additional_request: Optional[str] = None


class UpdateBookingRequest(BaseModel):
    booking: dict


class AvailabilitySlot(BaseModel):
    start_time: str
    end_time: str
    party_size: int
    available_spots: int


class PushAvailabilityRequest(BaseModel):
    slots: List[AvailabilitySlot]


class BookingStatusUpdate(BaseModel):
    booking_id: str
    status: str  # CONFIRMED, CANCELED, NO_SHOW


# ============================================================================
# Google Booking Server API (Called by Google)
# ============================================================================

@router.post("/v3/CheckAvailability")
async def check_availability(
    request: CheckAvailabilityRequest,
    x_goog_signature: Optional[str] = Header(None, alias="X-Goog-Signature"),
):
    """
    Check availability for a specific time slot.

    Called by Google when a user views availability.
    """
    service = get_google_reserve_service()
    if not service:
        raise HTTPException(status_code=503, detail="Google Reserve not configured")

    slot_time = datetime.fromtimestamp(request.slot.start_sec)
    duration = request.slot.duration_sec // 60

    result = await service.handle_check_availability(
        slot_time=slot_time,
        party_size=request.party_size or 2,
        duration_minutes=duration,
    )

    return result


@router.post("/v3/CreateBooking")
async def create_booking(
    request: CreateBookingRequest,
    x_goog_signature: Optional[str] = Header(None, alias="X-Goog-Signature"),
):
    """
    Create a new booking.

    Called by Google when a user confirms a reservation.
    """
    service = get_google_reserve_service()
    if not service:
        raise HTTPException(status_code=503, detail="Google Reserve not configured")

    result = await service.handle_create_booking(request.dict())

    return result


@router.post("/v3/UpdateBooking")
async def update_booking(
    request: UpdateBookingRequest,
    x_goog_signature: Optional[str] = Header(None, alias="X-Goog-Signature"),
):
    """
    Update an existing booking.

    Called by Google when a user modifies or cancels a reservation.
    """
    service = get_google_reserve_service()
    if not service:
        raise HTTPException(status_code=503, detail="Google Reserve not configured")

    booking_id = request.booking.get("booking_id")
    if not booking_id:
        raise HTTPException(status_code=400, detail="Missing booking_id")

    result = await service.handle_update_booking(booking_id, request.dict())

    return result


@router.post("/v3/GetBookingStatus")
async def get_booking_status(
    booking_id: str,
    x_goog_signature: Optional[str] = Header(None, alias="X-Goog-Signature"),
):
    """
    Get the status of a booking.

    Called by Google to verify booking status.
    """
    service = get_google_reserve_service()
    if not service:
        raise HTTPException(status_code=503, detail="Google Reserve not configured")

    result = await service.handle_get_booking_status(booking_id)

    return result


@router.post("/v3/ListBookings")
async def list_bookings(
    user_id: str,
    x_goog_signature: Optional[str] = Header(None, alias="X-Goog-Signature"),
):
    """
    List all bookings for a user.

    Called by Google to show user's reservations.
    """
    service = get_google_reserve_service()
    if not service:
        raise HTTPException(status_code=503, detail="Google Reserve not configured")

    result = await service.handle_list_bookings(user_id)

    return result


# ============================================================================
# Internal API (Called by your system)
# ============================================================================

@router.post("/availability/push")
async def push_availability(request: PushAvailabilityRequest):
    """
    Push availability updates to Google.

    Call this when availability changes significantly (e.g., after a booking
    or when you manually block a time slot).
    """
    service = get_google_reserve_service()
    if not service:
        raise HTTPException(status_code=503, detail="Google Reserve not configured")

    slots = []
    for slot in request.slots:
        start = datetime.fromisoformat(slot.start_time)
        end = datetime.fromisoformat(slot.end_time)
        duration = int((end - start).total_seconds() / 60)

        slots.append(TimeSlot(
            start_time=start,
            end_time=end,
            max_party_size=slot.party_size,
            available_spots=slot.available_spots,
            duration_minutes=duration,
        ))

    success = await service.push_availability_update(slots)

    return {
        "success": success,
        "slots_pushed": len(slots),
    }


@router.post("/booking/{booking_id}/status")
async def update_booking_status(booking_id: str, request: BookingStatusUpdate):
    """
    Update booking status and notify Google.

    Call this when you confirm, cancel, or mark a no-show in your system.
    """
    service = get_google_reserve_service()
    if not service:
        raise HTTPException(status_code=503, detail="Google Reserve not configured")

    try:
        status = BookingStatus(request.status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {request.status}")

    success = await service.push_booking_notification(booking_id, status)

    return {
        "success": success,
        "booking_id": booking_id,
        "status": status.value,
    }


# ============================================================================
# Feed Generation
# ============================================================================

@router.get("/feeds/merchant")
async def get_merchant_feed(
    name: str,
    phone: str,
    address: str,
    lat: float,
    lng: float,
    timezone: str = "America/New_York",
    website: str = "",
):
    """
    Generate merchant feed for Google.

    Use this to create the initial merchant data file.
    """
    service = get_google_reserve_service()
    if not service:
        raise HTTPException(status_code=503, detail="Google Reserve not configured")

    merchant = MerchantInfo(
        merchant_id=service.merchant_id,
        name=name,
        phone=phone,
        address=address,
        geo_lat=lat,
        geo_lng=lng,
        timezone=timezone,
        website=website,
    )

    return service.generate_merchant_feed(merchant)


@router.get("/feeds/service")
async def get_service_feed():
    """
    Generate service feed for Google.

    Use this to create the service definition file.
    """
    service = get_google_reserve_service()
    if not service:
        raise HTTPException(status_code=503, detail="Google Reserve not configured")

    return service.generate_service_feed()


@router.get("/feeds/availability")
async def get_availability_feed(
    days_ahead: int = 30,
    start_hour: int = 11,
    end_hour: int = 22,
    slot_duration: int = 90,
    max_party: int = 8,
    max_concurrent: int = 8,
):
    """
    Generate availability feed for Google based on actual reservation data.

    Queries existing reservations to calculate real available spots per time slot.
    """
    service = get_google_reserve_service()
    if not service:
        raise HTTPException(status_code=503, detail="Google Reserve not configured")

    # Query existing reservations to compute availability
    from app.db.session import SessionLocal
    from app.models.reservations import Reservation, ReservationStatus
    db = SessionLocal()
    try:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = today + timedelta(days=days_ahead)
        existing = db.query(Reservation).filter(
            Reservation.date >= today.date(),
            Reservation.date <= end_date.date(),
            Reservation.status.in_([ReservationStatus.CONFIRMED, ReservationStatus.PENDING]),
        ).all()

        # Build a dict of reservation counts per (date, hour)
        reservation_counts: dict = {}
        for r in existing:
            if r.time:
                key = (r.date, r.time.hour, 0 if r.time.minute < 30 else 30)
                reservation_counts[key] = reservation_counts.get(key, 0) + 1

        slots = []
        for day in range(days_ahead):
            current_date = today + timedelta(days=day)
            for hour in range(start_hour, end_hour):
                for minute in [0, 30]:
                    slot_start = current_date.replace(hour=hour, minute=minute)
                    slot_end = slot_start + timedelta(minutes=slot_duration)
                    key = (current_date.date(), hour, minute)
                    booked = reservation_counts.get(key, 0)
                    available = max(0, max_concurrent - booked)

                    slots.append(TimeSlot(
                        start_time=slot_start,
                        end_time=slot_end,
                        max_party_size=max_party,
                        available_spots=available,
                        duration_minutes=slot_duration,
                    ))
    finally:
        db.close()

    return service.generate_availability_feed(slots)


# ============================================================================
# Configuration Status
# ============================================================================

@router.get("/status")
async def get_google_reserve_status():
    """Check Google Reserve configuration status."""
    service = get_google_reserve_service()

    if not service:
        return {
            "configured": False,
            "message": "Google Reserve not configured. Set GOOGLE_RESERVE_PARTNER_ID, GOOGLE_RESERVE_API_KEY, and GOOGLE_RESERVE_MERCHANT_ID environment variables.",
        }

    return {
        "configured": True,
        "partner_id": service.partner_id,
        "merchant_id": service.merchant_id,
        "endpoints": {
            "check_availability": "/api/v1/google-reserve/v3/CheckAvailability",
            "create_booking": "/api/v1/google-reserve/v3/CreateBooking",
            "update_booking": "/api/v1/google-reserve/v3/UpdateBooking",
            "get_booking_status": "/api/v1/google-reserve/v3/GetBookingStatus",
        },
    }

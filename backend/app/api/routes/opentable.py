"""OpenTable Integration API routes.

Handles OpenTable webhooks, availability sync, and reservation management.
"""

from typing import Optional, List
from datetime import date, time, datetime
from fastapi import APIRouter, HTTPException, Request, Header
from pydantic import BaseModel

from app.services.opentable_service import (
    get_opentable_service,
    ReservationStatus,
    AvailabilitySlot,
)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class AvailabilitySlotRequest(BaseModel):
    time: str  # HH:MM format
    party_sizes: List[int]
    tables_available: int


class PushAvailabilityRequest(BaseModel):
    date: str  # YYYY-MM-DD
    slots: List[AvailabilitySlotRequest]


class UpdateStatusRequest(BaseModel):
    status: str  # pending, confirmed, seated, completed, cancelled, no_show
    table_id: Optional[str] = None


class ReservationResponse(BaseModel):
    reservation_id: str
    opentable_id: str
    guest_name: str
    guest_email: str
    guest_phone: str
    party_size: int
    reservation_date: str
    reservation_time: str
    status: str
    special_requests: str
    occasion: Optional[str] = None
    high_chair: int
    table_id: Optional[str] = None
    created_at: str
    synced_at: Optional[str] = None


class GuestResponse(BaseModel):
    guest_id: str
    opentable_guest_id: str
    email: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    visit_count: int
    no_show_count: int
    vip_status: bool


# ============================================================================
# Webhook Endpoint
# ============================================================================

@router.post("/webhook")
async def handle_webhook(
    request: Request,
    x_opentable_signature: Optional[str] = Header(None, alias="X-OpenTable-Signature"),
):
    """
    Handle incoming webhooks from OpenTable.

    Events:
    - reservation.created: New reservation
    - reservation.updated: Reservation modified
    - reservation.cancelled: Reservation cancelled
    - guest.updated: Guest profile updated
    """
    service = get_opentable_service()

    # Get raw body for signature verification
    body = await request.body()

    # Verify signature if configured
    if service.webhook_secret and x_opentable_signature:
        if not service.verify_webhook_signature(body, x_opentable_signature):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # Parse payload
    payload = await request.json()
    event_type = payload.get("event_type", "")

    result = await service.handle_webhook(event_type, payload)

    return result


# ============================================================================
# Availability Management
# ============================================================================

@router.post("/availability")
async def push_availability(request: PushAvailabilityRequest):
    """
    Push availability to OpenTable.

    Call this whenever table availability changes to keep OpenTable in sync.
    """
    service = get_opentable_service()

    try:
        target_date = date.fromisoformat(request.date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    slots = []
    for slot in request.slots:
        try:
            hour, minute = map(int, slot.time.split(":"))
            slot_time = time(hour, minute)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid time format: {slot.time}")

        slots.append(AvailabilitySlot(
            slot_time=slot_time,
            party_sizes=slot.party_sizes,
            tables_available=slot.tables_available,
        ))

    success = await service.push_availability(target_date, slots)

    return {
        "success": success,
        "date": request.date,
        "slots_count": len(slots),
    }


@router.get("/availability/{date_str}")
async def get_availability(date_str: str):
    """Get availability for a specific date."""
    service = get_opentable_service()

    try:
        target_date = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    slots = service.get_availability(target_date)

    return {
        "date": date_str,
        "slots": [
            {
                "time": slot.slot_time.strftime("%H:%M"),
                "party_sizes": slot.party_sizes,
                "tables_available": slot.tables_available,
            }
            for slot in slots
        ],
    }


# ============================================================================
# Reservation Management
# ============================================================================

@router.get("/reservations", response_model=List[ReservationResponse])
async def list_reservations(
    date: Optional[str] = None,
    status: Optional[str] = None,
):
    """List OpenTable reservations."""
    service = get_opentable_service()

    target_date = None
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")

    res_status = None
    if status:
        try:
            res_status = ReservationStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    reservations = service.list_reservations(date=target_date, status=res_status)

    return [_reservation_to_response(r) for r in reservations]


@router.get("/reservations/{reservation_id}", response_model=ReservationResponse)
async def get_reservation(reservation_id: str):
    """Get a specific reservation."""
    service = get_opentable_service()

    reservation = service.get_reservation(reservation_id)

    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    return _reservation_to_response(reservation)


@router.put("/reservations/{reservation_id}/status", response_model=ReservationResponse)
async def update_reservation_status(reservation_id: str, request: UpdateStatusRequest):
    """
    Update reservation status.

    This updates the local status and optionally syncs back to OpenTable.
    Use this when seating guests, marking no-shows, etc.
    """
    service = get_opentable_service()

    try:
        status = ReservationStatus(request.status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {request.status}")

    reservation = service.update_reservation_status(
        reservation_id,
        status,
        table_id=request.table_id,
    )

    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    # Sync status back to OpenTable
    await service.sync_status_to_opentable(reservation_id)

    return _reservation_to_response(reservation)


@router.post("/reservations/{reservation_id}/seat")
async def seat_reservation(reservation_id: str, table_id: str):
    """Mark a reservation as seated at a specific table."""
    service = get_opentable_service()

    reservation = service.update_reservation_status(
        reservation_id,
        ReservationStatus.SEATED,
        table_id=table_id,
    )

    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    await service.sync_status_to_opentable(reservation_id)

    return {
        "success": True,
        "reservation_id": reservation_id,
        "status": "seated",
        "table_id": table_id,
    }


@router.post("/reservations/{reservation_id}/complete")
async def complete_reservation(reservation_id: str):
    """Mark a reservation as completed."""
    service = get_opentable_service()

    reservation = service.update_reservation_status(
        reservation_id,
        ReservationStatus.COMPLETED,
    )

    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    await service.sync_status_to_opentable(reservation_id)

    return {
        "success": True,
        "reservation_id": reservation_id,
        "status": "completed",
    }


@router.post("/reservations/{reservation_id}/no-show")
async def mark_no_show(reservation_id: str):
    """Mark a reservation as no-show."""
    service = get_opentable_service()

    reservation = service.update_reservation_status(
        reservation_id,
        ReservationStatus.NO_SHOW,
    )

    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    await service.sync_status_to_opentable(reservation_id)

    return {
        "success": True,
        "reservation_id": reservation_id,
        "status": "no_show",
    }


# ============================================================================
# Guest Management
# ============================================================================

@router.get("/guests", response_model=List[GuestResponse])
async def list_guests(vip_only: bool = False):
    """List OpenTable guests."""
    service = get_opentable_service()

    guests = service.list_guests(vip_only=vip_only)

    return [_guest_to_response(g) for g in guests]


@router.get("/guests/{guest_id}", response_model=GuestResponse)
async def get_guest(guest_id: str):
    """Get a specific guest."""
    service = get_opentable_service()

    guest = service.get_guest(guest_id)

    if not guest:
        raise HTTPException(status_code=404, detail="Guest not found")

    return _guest_to_response(guest)


@router.post("/guests/{guest_id}/vip")
async def toggle_guest_vip(guest_id: str, vip: bool = True):
    """Mark or unmark a guest as VIP."""
    service = get_opentable_service()

    guest = service.mark_guest_vip(guest_id, vip)

    if not guest:
        raise HTTPException(status_code=404, detail="Guest not found")

    return {
        "success": True,
        "guest_id": guest_id,
        "vip_status": guest.vip_status,
    }


# ============================================================================
# Configuration
# ============================================================================

@router.get("/config")
async def get_config():
    """Get OpenTable integration configuration status."""
    service = get_opentable_service()

    return {
        "configured": bool(service.client_id and service.client_secret),
        "restaurant_id": service.restaurant_id,
        "webhook_secret_configured": bool(service.webhook_secret),
        "authenticated": bool(service.access_token),
        "token_expires_at": service.token_expires_at.isoformat() if service.token_expires_at else None,
    }


@router.get("/stats")
async def get_opentable_stats():
    """Get OpenTable statistics."""
    return {
        "total_reservations": 0,
        "seated": 0,
        "no_shows": 0,
        "cancellations": 0,
        "avg_party_size": 0,
        "avg_rating": 0,
        "reviews_count": 0,
        "revenue_attributed": 0,
        "top_time_slots": [],
        "period": "last_30_days",
    }


@router.get("/status")
async def get_opentable_status():
    """Get OpenTable integration status."""
    return {
        "connected": False,
        "restaurant_id": None,
        "last_sync": None,
        "sync_enabled": False,
        "features": {"reservations": False, "waitlist": False, "reviews": False},
    }


@router.post("/authenticate")
async def authenticate():
    """Authenticate with OpenTable API."""
    service = get_opentable_service()

    success = await service.authenticate()

    if not success:
        raise HTTPException(status_code=401, detail="Authentication failed")

    return {
        "success": True,
        "expires_at": service.token_expires_at.isoformat() if service.token_expires_at else None,
    }


# ============================================================================
# Helper Functions
# ============================================================================

def _reservation_to_response(reservation) -> ReservationResponse:
    """Convert reservation to response model."""
    return ReservationResponse(
        reservation_id=reservation.reservation_id,
        opentable_id=reservation.opentable_id,
        guest_name=reservation.guest_name,
        guest_email=reservation.guest_email,
        guest_phone=reservation.guest_phone,
        party_size=reservation.party_size,
        reservation_date=reservation.reservation_date.isoformat(),
        reservation_time=reservation.reservation_time.strftime("%H:%M"),
        status=reservation.status.value,
        special_requests=reservation.special_requests,
        occasion=reservation.occasion,
        high_chair=reservation.high_chair,
        table_id=reservation.table_id,
        created_at=reservation.created_at.isoformat(),
        synced_at=reservation.synced_at.isoformat() if reservation.synced_at else None,
    )


def _guest_to_response(guest) -> GuestResponse:
    """Convert guest to response model."""
    return GuestResponse(
        guest_id=guest.guest_id,
        opentable_guest_id=guest.opentable_guest_id,
        email=guest.email,
        first_name=guest.first_name,
        last_name=guest.last_name,
        phone=guest.phone,
        visit_count=guest.visit_count,
        no_show_count=guest.no_show_count,
        vip_status=guest.vip_status,
    )

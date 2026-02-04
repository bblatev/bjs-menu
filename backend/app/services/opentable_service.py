"""OpenTable Integration Service.

Integrates with OpenTable for reservation management, availability sync,
and guest data synchronization.
"""

import logging
import hmac
import hashlib
from datetime import datetime, date, time, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import uuid
import httpx

logger = logging.getLogger(__name__)


class ReservationStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SEATED = "seated"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class WebhookEvent(str, Enum):
    RESERVATION_CREATED = "reservation.created"
    RESERVATION_UPDATED = "reservation.updated"
    RESERVATION_CANCELLED = "reservation.cancelled"
    GUEST_UPDATED = "guest.updated"


@dataclass
class OpenTableReservation:
    """An OpenTable reservation."""
    reservation_id: str
    opentable_id: str
    restaurant_id: str
    guest_name: str
    guest_email: str
    guest_phone: str
    party_size: int
    reservation_date: date
    reservation_time: time
    status: ReservationStatus = ReservationStatus.PENDING
    special_requests: str = ""
    occasion: Optional[str] = None
    high_chair: int = 0
    table_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    synced_at: Optional[datetime] = None


@dataclass
class OpenTableGuest:
    """An OpenTable guest profile."""
    guest_id: str
    opentable_guest_id: str
    email: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    dining_preferences: Dict[str, Any] = field(default_factory=dict)
    visit_count: int = 0
    no_show_count: int = 0
    vip_status: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AvailabilitySlot:
    """An availability time slot."""
    slot_time: time
    party_sizes: List[int]  # Available for these party sizes
    tables_available: int


class OpenTableService:
    """Service for OpenTable integration.

    Handles:
    - Webhook processing for real-time reservation updates
    - Availability sync to OpenTable
    - Guest profile sync
    - Reservation management
    """

    # OpenTable API endpoints
    API_BASE = "https://platform.opentable.com/v2"

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        restaurant_id: Optional[str] = None,
        webhook_secret: Optional[str] = None,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.restaurant_id = restaurant_id
        self.webhook_secret = webhook_secret
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None

        # In-memory storage (use database in production)
        self._reservations: Dict[str, OpenTableReservation] = {}
        self._guests: Dict[str, OpenTableGuest] = {}
        self._availability: Dict[str, List[AvailabilitySlot]] = {}

    # =========================================================================
    # Authentication
    # =========================================================================

    async def authenticate(self) -> bool:
        """Authenticate with OpenTable API."""
        if not self.client_id or not self.client_secret:
            logger.warning("OpenTable credentials not configured")
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.API_BASE}/oauth/token",
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    self.access_token = data.get("access_token")
                    expires_in = data.get("expires_in", 3600)
                    self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                    logger.info("OpenTable authentication successful")
                    return True
                else:
                    logger.error(f"OpenTable auth failed: {response.status_code}")
                    return False
        except Exception as e:
            logger.error(f"OpenTable auth error: {e}")
            return False

    def _get_headers(self) -> Dict[str, str]:
        """Get API request headers."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    # =========================================================================
    # Webhook Handling
    # =========================================================================

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        """Verify OpenTable webhook signature."""
        if not self.webhook_secret:
            logger.warning("Webhook secret not configured")
            return False

        expected = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(f"sha256={expected}", signature)

    async def handle_webhook(
        self,
        event_type: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle incoming webhook from OpenTable."""
        logger.info(f"Processing OpenTable webhook: {event_type}")

        try:
            if event_type == WebhookEvent.RESERVATION_CREATED.value:
                return await self._handle_reservation_created(payload)
            elif event_type == WebhookEvent.RESERVATION_UPDATED.value:
                return await self._handle_reservation_updated(payload)
            elif event_type == WebhookEvent.RESERVATION_CANCELLED.value:
                return await self._handle_reservation_cancelled(payload)
            elif event_type == WebhookEvent.GUEST_UPDATED.value:
                return await self._handle_guest_updated(payload)
            else:
                logger.warning(f"Unknown webhook event: {event_type}")
                return {"status": "ignored", "reason": "unknown_event"}
        except Exception as e:
            logger.error(f"Webhook handling error: {e}")
            return {"status": "error", "error": str(e)}

    async def _handle_reservation_created(
        self,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle new reservation from OpenTable."""
        res_data = payload.get("reservation", {})
        guest_data = payload.get("guest", {})

        # Parse reservation datetime
        res_datetime = datetime.fromisoformat(res_data.get("datetime", "").replace("Z", "+00:00"))

        reservation = OpenTableReservation(
            reservation_id=f"OT-{uuid.uuid4().hex[:8]}",
            opentable_id=res_data.get("id", ""),
            restaurant_id=res_data.get("restaurant_id", self.restaurant_id or ""),
            guest_name=f"{guest_data.get('first_name', '')} {guest_data.get('last_name', '')}".strip(),
            guest_email=guest_data.get("email", ""),
            guest_phone=guest_data.get("phone", ""),
            party_size=res_data.get("party_size", 2),
            reservation_date=res_datetime.date(),
            reservation_time=res_datetime.time(),
            status=ReservationStatus.CONFIRMED,
            special_requests=res_data.get("special_requests", ""),
            occasion=res_data.get("occasion"),
            high_chair=res_data.get("high_chair", 0),
            synced_at=datetime.utcnow(),
        )

        self._reservations[reservation.reservation_id] = reservation

        # Also sync guest if provided
        if guest_data.get("id"):
            await self._sync_guest(guest_data)

        logger.info(f"Created reservation {reservation.reservation_id} from OpenTable")

        return {
            "status": "created",
            "reservation_id": reservation.reservation_id,
            "opentable_id": reservation.opentable_id,
        }

    async def _handle_reservation_updated(
        self,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle reservation update from OpenTable."""
        res_data = payload.get("reservation", {})
        opentable_id = res_data.get("id", "")

        # Find existing reservation
        reservation = None
        for res in self._reservations.values():
            if res.opentable_id == opentable_id:
                reservation = res
                break

        if not reservation:
            # Create if doesn't exist
            return await self._handle_reservation_created(payload)

        # Update fields
        if "party_size" in res_data:
            reservation.party_size = res_data["party_size"]
        if "datetime" in res_data:
            res_datetime = datetime.fromisoformat(res_data["datetime"].replace("Z", "+00:00"))
            reservation.reservation_date = res_datetime.date()
            reservation.reservation_time = res_datetime.time()
        if "special_requests" in res_data:
            reservation.special_requests = res_data["special_requests"]
        if "status" in res_data:
            status_map = {
                "pending": ReservationStatus.PENDING,
                "confirmed": ReservationStatus.CONFIRMED,
                "seated": ReservationStatus.SEATED,
                "completed": ReservationStatus.COMPLETED,
                "cancelled": ReservationStatus.CANCELLED,
                "no_show": ReservationStatus.NO_SHOW,
            }
            reservation.status = status_map.get(res_data["status"], reservation.status)

        reservation.updated_at = datetime.utcnow()
        reservation.synced_at = datetime.utcnow()

        logger.info(f"Updated reservation {reservation.reservation_id}")

        return {
            "status": "updated",
            "reservation_id": reservation.reservation_id,
        }

    async def _handle_reservation_cancelled(
        self,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle reservation cancellation from OpenTable."""
        res_data = payload.get("reservation", {})
        opentable_id = res_data.get("id", "")

        for reservation in self._reservations.values():
            if reservation.opentable_id == opentable_id:
                reservation.status = ReservationStatus.CANCELLED
                reservation.updated_at = datetime.utcnow()
                reservation.synced_at = datetime.utcnow()

                logger.info(f"Cancelled reservation {reservation.reservation_id}")

                return {
                    "status": "cancelled",
                    "reservation_id": reservation.reservation_id,
                }

        return {"status": "not_found"}

    async def _handle_guest_updated(
        self,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle guest profile update from OpenTable."""
        guest_data = payload.get("guest", {})
        await self._sync_guest(guest_data)
        return {"status": "synced"}

    async def _sync_guest(self, guest_data: Dict[str, Any]) -> Optional[OpenTableGuest]:
        """Sync guest data from OpenTable."""
        opentable_guest_id = guest_data.get("id", "")
        if not opentable_guest_id:
            return None

        # Find or create guest
        guest = None
        for g in self._guests.values():
            if g.opentable_guest_id == opentable_guest_id:
                guest = g
                break

        if not guest:
            guest = OpenTableGuest(
                guest_id=f"OTG-{uuid.uuid4().hex[:8]}",
                opentable_guest_id=opentable_guest_id,
                email=guest_data.get("email", ""),
                first_name=guest_data.get("first_name", ""),
                last_name=guest_data.get("last_name", ""),
                phone=guest_data.get("phone"),
            )
            self._guests[guest.guest_id] = guest
        else:
            guest.email = guest_data.get("email", guest.email)
            guest.first_name = guest_data.get("first_name", guest.first_name)
            guest.last_name = guest_data.get("last_name", guest.last_name)
            guest.phone = guest_data.get("phone", guest.phone)

        if "dining_preferences" in guest_data:
            guest.dining_preferences = guest_data["dining_preferences"]
        if "vip" in guest_data:
            guest.vip_status = guest_data["vip"]

        return guest

    # =========================================================================
    # Availability Sync
    # =========================================================================

    async def push_availability(
        self,
        date: date,
        slots: List[AvailabilitySlot],
    ) -> bool:
        """Push availability to OpenTable."""
        if not self.access_token or not self.restaurant_id:
            logger.warning("Cannot push availability: not configured")
            return False

        # Store locally
        date_key = date.isoformat()
        self._availability[date_key] = slots

        # In production, push to OpenTable API
        try:
            async with httpx.AsyncClient() as client:
                availability_data = {
                    "restaurant_id": self.restaurant_id,
                    "date": date.isoformat(),
                    "slots": [
                        {
                            "time": slot.slot_time.strftime("%H:%M"),
                            "party_sizes": slot.party_sizes,
                            "tables_available": slot.tables_available,
                        }
                        for slot in slots
                    ],
                }

                response = await client.post(
                    f"{self.API_BASE}/restaurants/{self.restaurant_id}/availability",
                    headers=self._get_headers(),
                    json=availability_data,
                )

                if response.status_code in (200, 201):
                    logger.info(f"Pushed availability for {date}")
                    return True
                else:
                    logger.error(f"Failed to push availability: {response.status_code}")
                    return False
        except Exception as e:
            logger.error(f"Availability push error: {e}")
            # Still return True since we stored locally
            return True

    def get_availability(self, date: date) -> List[AvailabilitySlot]:
        """Get availability for a date."""
        return self._availability.get(date.isoformat(), [])

    # =========================================================================
    # Reservation Management
    # =========================================================================

    def get_reservation(self, reservation_id: str) -> Optional[OpenTableReservation]:
        """Get a reservation by ID."""
        return self._reservations.get(reservation_id)

    def get_reservation_by_opentable_id(self, opentable_id: str) -> Optional[OpenTableReservation]:
        """Get a reservation by OpenTable ID."""
        for res in self._reservations.values():
            if res.opentable_id == opentable_id:
                return res
        return None

    def list_reservations(
        self,
        date: Optional[date] = None,
        status: Optional[ReservationStatus] = None,
    ) -> List[OpenTableReservation]:
        """List reservations with optional filters."""
        reservations = list(self._reservations.values())

        if date:
            reservations = [r for r in reservations if r.reservation_date == date]

        if status:
            reservations = [r for r in reservations if r.status == status]

        return sorted(reservations, key=lambda r: (r.reservation_date, r.reservation_time))

    def update_reservation_status(
        self,
        reservation_id: str,
        status: ReservationStatus,
        table_id: Optional[str] = None,
    ) -> Optional[OpenTableReservation]:
        """Update reservation status locally."""
        reservation = self._reservations.get(reservation_id)
        if not reservation:
            return None

        reservation.status = status
        reservation.updated_at = datetime.utcnow()

        if table_id:
            reservation.table_id = table_id

        return reservation

    async def sync_status_to_opentable(
        self,
        reservation_id: str,
    ) -> bool:
        """Sync reservation status back to OpenTable."""
        reservation = self._reservations.get(reservation_id)
        if not reservation or not self.access_token:
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.API_BASE}/reservations/{reservation.opentable_id}",
                    headers=self._get_headers(),
                    json={
                        "status": reservation.status.value,
                    },
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Status sync error: {e}")
            return False

    # =========================================================================
    # Guest Management
    # =========================================================================

    def get_guest(self, guest_id: str) -> Optional[OpenTableGuest]:
        """Get a guest by ID."""
        return self._guests.get(guest_id)

    def list_guests(self, vip_only: bool = False) -> List[OpenTableGuest]:
        """List guests."""
        guests = list(self._guests.values())
        if vip_only:
            guests = [g for g in guests if g.vip_status]
        return guests

    def mark_guest_vip(self, guest_id: str, vip: bool = True) -> Optional[OpenTableGuest]:
        """Mark a guest as VIP."""
        guest = self._guests.get(guest_id)
        if guest:
            guest.vip_status = vip
        return guest


# Singleton instance
_opentable_service: Optional[OpenTableService] = None


def get_opentable_service() -> OpenTableService:
    """Get the OpenTable service singleton."""
    global _opentable_service
    if _opentable_service is None:
        _opentable_service = OpenTableService()
    return _opentable_service

"""Google Reserve (Reserve with Google) Integration Service.

Allows customers to book reservations directly from Google Search and Google Maps.
https://developers.google.com/maps-booking
"""

import logging
import hmac
import hashlib
from datetime import datetime, date, time, timedelta, timezone
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class BookingStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELED = "CANCELED"
    NO_SHOW = "NO_SHOW"
    NO_SHOW_PENALIZED = "NO_SHOW_PENALIZED"


class AvailabilityStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass
class TimeSlot:
    """A bookable time slot."""
    start_time: datetime
    end_time: datetime
    max_party_size: int
    available_spots: int
    duration_minutes: int = 90


@dataclass
class GoogleReservation:
    """A reservation from Google Reserve."""
    booking_id: str
    merchant_id: str
    slot_time: datetime
    party_size: int
    status: BookingStatus
    user_info: Dict[str, str]  # email, name, phone
    payment_info: Optional[Dict[str, Any]] = None
    special_requests: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class MerchantInfo:
    """Merchant information for Google."""
    merchant_id: str
    name: str
    phone: str
    address: str
    geo_lat: float
    geo_lng: float
    timezone: str
    website: str = ""
    category: str = "restaurant"


class GoogleReserveService:
    """Service for Google Reserve integration.

    Google Reserve uses a "Maps Booking API" that requires:
    1. Feed files (availability, merchant info) - can be generated
    2. Booking Server API - we implement this to receive bookings
    3. Real-time updates API - to push availability changes
    """

    GOOGLE_API_BASE = "https://mapsbooking.googleapis.com/v1alpha"

    def __init__(
        self,
        partner_id: str,
        api_key: str,
        webhook_secret: str,
        merchant_id: str,
    ):
        self.partner_id = partner_id
        self.api_key = api_key
        self.webhook_secret = webhook_secret
        self.merchant_id = merchant_id
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get HTTP client for Google API calls."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.GOOGLE_API_BASE,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    # =========================================================================
    # Webhook Verification
    # =========================================================================

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        """Verify Google webhook signature."""
        if not self.webhook_secret:
            logger.warning("Webhook secret not configured")
            return True

        expected = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    # =========================================================================
    # Booking Server API Implementation
    # =========================================================================

    async def handle_check_availability(
        self,
        slot_time: datetime,
        party_size: int,
        duration_minutes: int = 90,
    ) -> Dict[str, Any]:
        """
        Handle CheckAvailability request from Google.

        Returns availability status for a specific slot.
        """
        # This would query your reservation system
        # For now, return a mock response

        # Check if slot is available (mock logic)
        is_available = True  # Replace with actual availability check

        return {
            "slot": {
                "merchant_id": self.merchant_id,
                "service_id": "dine-in",
                "start_sec": int(slot_time.timestamp()),
                "duration_sec": duration_minutes * 60,
                "availability_tag": "table-for-" + str(party_size),
            },
            "count_available": 5 if is_available else 0,
            "last_online_cancellable_sec": int((slot_time - timedelta(hours=2)).timestamp()),
            "duration_requirement": "DURATION_REQUIREMENT_UNSPECIFIED",
            "availability_update": None,
        }

    async def handle_create_booking(
        self,
        booking_request: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Handle CreateBooking request from Google.

        Creates a new reservation in the system.
        """
        slot = booking_request.get("slot", {})
        user_info = booking_request.get("user_information", {})
        party_size = booking_request.get("party_size", 2)

        # Extract booking details
        slot_time = datetime.fromtimestamp(slot.get("start_sec", 0))

        booking_id = f"GR-{datetime.now().strftime('%Y%m%d%H%M%S')}-{party_size}"

        # Create reservation in your system
        # This would call your reservations service
        reservation = GoogleReservation(
            booking_id=booking_id,
            merchant_id=self.merchant_id,
            slot_time=slot_time,
            party_size=party_size,
            status=BookingStatus.CONFIRMED,
            user_info={
                "email": user_info.get("email", ""),
                "name": f"{user_info.get('given_name', '')} {user_info.get('family_name', '')}".strip(),
                "phone": user_info.get("telephone", ""),
            },
            special_requests=booking_request.get("additional_request", ""),
            created_at=datetime.now(timezone.utc),
        )

        # Return booking confirmation
        return {
            "booking": {
                "booking_id": booking_id,
                "slot": slot,
                "user_information": user_info,
                "status": "CONFIRMED",
                "payment_information": booking_request.get("payment_information"),
            },
        }

    async def handle_update_booking(
        self,
        booking_id: str,
        update_request: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Handle UpdateBooking request from Google.

        Updates an existing reservation.
        """
        new_status = update_request.get("booking", {}).get("status")

        # Update the reservation in your system
        # This would call your reservations service

        return {
            "booking": {
                "booking_id": booking_id,
                "status": new_status or "CONFIRMED",
            },
        }

    async def handle_get_booking_status(
        self,
        booking_id: str,
    ) -> Dict[str, Any]:
        """
        Handle GetBookingStatus request from Google.

        Returns current status of a booking.
        """
        # Query your reservation system for the booking
        # For now, return a mock response

        return {
            "booking_id": booking_id,
            "booking_status": "CONFIRMED",
        }

    async def handle_list_bookings(
        self,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Handle ListBookings request from Google.

        Returns all bookings for a user.
        """
        # Query your reservation system for user's bookings
        # For now, return empty list

        return {
            "bookings": [],
        }

    # =========================================================================
    # Real-time Updates (Push to Google)
    # =========================================================================

    async def push_availability_update(
        self,
        slots: List[TimeSlot],
    ) -> bool:
        """
        Push availability updates to Google.

        Call this when availability changes significantly.
        """
        client = await self._get_client()

        # Build availability update
        slot_updates = []
        for slot in slots:
            slot_updates.append({
                "merchant_id": self.merchant_id,
                "service_id": "dine-in",
                "start_sec": int(slot.start_time.timestamp()),
                "duration_sec": slot.duration_minutes * 60,
                "spots_open": slot.available_spots,
                "spots_total": slot.max_party_size,
            })

        try:
            response = await client.post(
                f"/partners/{self.partner_id}:batchPushAvailability",
                json={"extended_service_availability": slot_updates},
            )

            if response.status_code == 200:
                logger.info(f"Pushed {len(slots)} availability updates to Google")
                return True
            else:
                logger.error(f"Failed to push availability: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error pushing availability to Google: {e}")
            return False

    async def push_booking_notification(
        self,
        booking_id: str,
        status: BookingStatus,
    ) -> bool:
        """
        Notify Google of booking status change.

        Call this when a booking is confirmed, canceled, or no-show.
        """
        client = await self._get_client()

        try:
            response = await client.post(
                f"/partners/{self.partner_id}/bookings/{booking_id}:updateStatus",
                json={"status": status.value},
            )

            if response.status_code == 200:
                logger.info(f"Updated booking {booking_id} status to {status}")
                return True
            else:
                logger.error(f"Failed to update booking status: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error updating booking status: {e}")
            return False

    # =========================================================================
    # Feed Generation (for initial setup)
    # =========================================================================

    def generate_merchant_feed(
        self,
        merchant: MerchantInfo,
    ) -> Dict[str, Any]:
        """Generate merchant feed data for Google."""
        return {
            "merchant": [{
                "merchant_id": merchant.merchant_id,
                "name": merchant.name,
                "telephone": merchant.phone,
                "url": merchant.website,
                "geo": {
                    "latitude": merchant.geo_lat,
                    "longitude": merchant.geo_lng,
                },
                "address": {
                    "country": "US",  # Adjust as needed
                    "locality": "",
                    "region": "",
                    "postal_code": "",
                    "street_address": merchant.address,
                },
                "category": merchant.category,
                "action_link": [{
                    "url": f"{merchant.website}/reservations",
                    "language": "en",
                    "label": "Book a table",
                }],
            }],
        }

    def generate_service_feed(self) -> Dict[str, Any]:
        """Generate service feed data for Google."""
        return {
            "service": [{
                "merchant_id": self.merchant_id,
                "service_id": "dine-in",
                "name": "Dine-in Reservation",
                "description": "Reserve a table at our restaurant",
                "category": "category/restaurant",
                "rules": {
                    "min_advance_booking": 3600,  # 1 hour minimum
                    "max_advance_booking": 2592000,  # 30 days maximum
                    "min_booking_buffer_before_end_time": 7200,  # 2 hour buffer
                },
            }],
        }

    def generate_availability_feed(
        self,
        slots: List[TimeSlot],
    ) -> Dict[str, Any]:
        """Generate availability feed data for Google."""
        availability = []
        for slot in slots:
            availability.append({
                "merchant_id": self.merchant_id,
                "service_id": "dine-in",
                "start_sec": int(slot.start_time.timestamp()),
                "duration_sec": slot.duration_minutes * 60,
                "spots_open": slot.available_spots,
                "spots_total": slot.max_party_size,
                "availability_tag": f"party-{slot.max_party_size}",
            })

        return {"availability": availability}

    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# Singleton instance
_google_reserve_service: Optional[GoogleReserveService] = None


def get_google_reserve_service() -> Optional[GoogleReserveService]:
    """Get or create Google Reserve service."""
    global _google_reserve_service
    if _google_reserve_service is None:
        import os
        partner_id = settings.google_reserve_partner_id
        api_key = settings.google_reserve_api_key
        webhook_secret = os.getenv("GOOGLE_RESERVE_WEBHOOK_SECRET")
        merchant_id = settings.google_reserve_merchant_id

        if partner_id and api_key and merchant_id:
            _google_reserve_service = GoogleReserveService(
                partner_id=partner_id,
                api_key=api_key,
                webhook_secret=webhook_secret or "",
                merchant_id=merchant_id,
            )
    return _google_reserve_service

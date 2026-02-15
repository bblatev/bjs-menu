"""
Delivery Platform Integrations
UberEats, DoorDash, OpenTable, Resy API integrations
"""
import httpx
import hmac
import hashlib
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from enum import Enum
from decimal import Decimal
import os
from app.core.config import settings

logger = logging.getLogger(__name__)


# =============================================================================
# COMMON TYPES
# =============================================================================

class OrderStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    PREPARING = "preparing"
    READY_FOR_PICKUP = "ready_for_pickup"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class DeliveryPlatform(str, Enum):
    UBER_EATS = "uber_eats"
    DOORDASH = "doordash"
    OPENTABLE = "opentable"
    RESY = "resy"


@dataclass
class DeliveryOrder:
    id: str
    platform: str
    external_id: str
    customer_name: str
    customer_phone: Optional[str]
    customer_address: Optional[str]
    items: List[Dict]
    subtotal: Decimal
    tax: Decimal
    delivery_fee: Decimal
    tip: Decimal
    total: Decimal
    status: str
    special_instructions: Optional[str]
    estimated_pickup_time: Optional[datetime]
    created_at: datetime
    metadata: Dict = field(default_factory=dict)


@dataclass
class Reservation:
    id: str
    platform: str
    external_id: str
    customer_name: str
    customer_email: Optional[str]
    customer_phone: Optional[str]
    party_size: int
    date: str
    time: str
    table_id: Optional[int]
    special_requests: Optional[str]
    status: str
    created_at: datetime
    metadata: Dict = field(default_factory=dict)


@dataclass
class IntegrationResult:
    success: bool
    data: Optional[Any] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None


# =============================================================================
# UBER EATS INTEGRATION
# =============================================================================

class UberEatsService:
    """
    UberEats Direct Integration
    https://developer.uber.com/docs/eats
    """

    BASE_URL = "https://api.uber.com/v1/eats"

    def __init__(self):
        self.client_id = settings.ubereats_client_id
        self.client_secret = settings.ubereats_client_secret
        self.store_id = settings.ubereats_store_id
        self.webhook_secret = settings.ubereats_webhook_secret
        self._access_token: Optional[str] = None
        self._token_expires: Optional[datetime] = None

    async def _get_access_token(self) -> str:
        """Get OAuth2 access token"""
        if self._access_token and self._token_expires and datetime.now(timezone.utc) < self._token_expires:
            return self._access_token

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://login.uber.com/oauth/v2/token",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "client_credentials",
                    "scope": "eats.store eats.order"
                }
            )

            if response.status_code == 200:
                data = response.json()
                self._access_token = data["access_token"]
                self._token_expires = datetime.now(timezone.utc) + timedelta(seconds=data.get("expires_in", 3600) - 60)
                return self._access_token
            else:
                raise Exception(f"Failed to get UberEats token: {response.text}")

    async def get_active_orders(self) -> IntegrationResult:
        """Get all active orders from UberEats"""
        try:
            token = await self._get_access_token()
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{self.BASE_URL}/stores/{self.store_id}/orders",
                    headers={"Authorization": f"Bearer {token}"},
                    params={"status": "active"}
                )

                if response.status_code == 200:
                    orders = []
                    for order_data in response.json().get("orders", []):
                        orders.append(self._parse_order(order_data))
                    return IntegrationResult(success=True, data=orders)
                else:
                    return IntegrationResult(
                        success=False,
                        error_message=response.text,
                        error_code=str(response.status_code)
                    )
        except Exception as e:
            logger.error(f"UberEats get_active_orders error: {e}")
            return IntegrationResult(success=False, error_message=str(e))

    async def accept_order(self, order_id: str, prep_time_minutes: int = 20) -> IntegrationResult:
        """Accept an incoming order"""
        try:
            token = await self._get_access_token()
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.BASE_URL}/orders/{order_id}/accept",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"prep_time": prep_time_minutes}
                )

                if response.status_code in [200, 204]:
                    return IntegrationResult(success=True, data={"order_id": order_id, "status": "accepted"})
                else:
                    return IntegrationResult(
                        success=False,
                        error_message=response.text,
                        error_code=str(response.status_code)
                    )
        except Exception as e:
            logger.error(f"UberEats accept_order error: {e}")
            return IntegrationResult(success=False, error_message=str(e))

    async def deny_order(self, order_id: str, reason: str) -> IntegrationResult:
        """Deny an incoming order"""
        try:
            token = await self._get_access_token()
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.BASE_URL}/orders/{order_id}/deny",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "reason": {
                            "code": "STORE_CLOSED" if "closed" in reason.lower() else "OTHER",
                            "description": reason
                        }
                    }
                )

                if response.status_code in [200, 204]:
                    return IntegrationResult(success=True, data={"order_id": order_id, "status": "denied"})
                else:
                    return IntegrationResult(success=False, error_message=response.text)
        except Exception as e:
            logger.error(f"UberEats deny_order error: {e}")
            return IntegrationResult(success=False, error_message=str(e))

    async def update_order_status(self, order_id: str, status: str) -> IntegrationResult:
        """Update order preparation status"""
        status_map = {
            "preparing": "IN_PROGRESS",
            "ready_for_pickup": "READY_FOR_PICKUP"
        }

        try:
            token = await self._get_access_token()
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.BASE_URL}/orders/{order_id}/status",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"status": status_map.get(status, status.upper())}
                )

                if response.status_code in [200, 204]:
                    return IntegrationResult(success=True, data={"order_id": order_id, "status": status})
                else:
                    return IntegrationResult(success=False, error_message=response.text)
        except Exception as e:
            logger.error(f"UberEats update_status error: {e}")
            return IntegrationResult(success=False, error_message=str(e))

    async def cancel_order(self, order_id: str, reason: str) -> IntegrationResult:
        """Cancel an order"""
        try:
            token = await self._get_access_token()
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.BASE_URL}/orders/{order_id}/cancel",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "reason": {
                            "code": "ITEM_UNAVAILABLE" if "unavailable" in reason.lower() else "OTHER",
                            "description": reason
                        }
                    }
                )

                if response.status_code in [200, 204]:
                    return IntegrationResult(success=True, data={"order_id": order_id, "status": "cancelled"})
                else:
                    return IntegrationResult(success=False, error_message=response.text)
        except Exception as e:
            logger.error(f"UberEats cancel_order error: {e}")
            return IntegrationResult(success=False, error_message=str(e))

    async def update_menu(self, menu_items: List[Dict]) -> IntegrationResult:
        """Sync menu items to UberEats"""
        try:
            token = await self._get_access_token()
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.put(
                    f"{self.BASE_URL}/stores/{self.store_id}/menus",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"menus": [{"id": "main", "items": menu_items}]}
                )

                if response.status_code in [200, 204]:
                    return IntegrationResult(success=True, data={"synced_items": len(menu_items)})
                else:
                    return IntegrationResult(success=False, error_message=response.text)
        except Exception as e:
            logger.error(f"UberEats update_menu error: {e}")
            return IntegrationResult(success=False, error_message=str(e))

    async def set_store_status(self, is_open: bool) -> IntegrationResult:
        """Set store online/offline status"""
        try:
            token = await self._get_access_token()
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.BASE_URL}/stores/{self.store_id}/status",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"status": "ONLINE" if is_open else "OFFLINE"}
                )

                if response.status_code in [200, 204]:
                    return IntegrationResult(success=True, data={"store_status": "online" if is_open else "offline"})
                else:
                    return IntegrationResult(success=False, error_message=response.text)
        except Exception as e:
            logger.error(f"UberEats set_store_status error: {e}")
            return IntegrationResult(success=False, error_message=str(e))

    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        """Verify webhook signature"""
        if not self.webhook_secret:
            return True  # Skip verification in dev

        expected = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    def parse_webhook(self, payload: Dict) -> Optional[DeliveryOrder]:
        """Parse webhook payload into DeliveryOrder"""
        event_type = payload.get("event_type")

        if event_type in ["orders.notification", "orders.created"]:
            order_data = payload.get("meta", {}).get("resource", {})
            return self._parse_order(order_data)

        return None

    def _parse_order(self, data: Dict) -> DeliveryOrder:
        """Parse UberEats order data"""
        items = []
        for item in data.get("items", []):
            items.append({
                "id": item.get("id"),
                "name": item.get("title"),
                "quantity": item.get("quantity", 1),
                "price": Decimal(str(item.get("price", {}).get("unit_price", {}).get("amount", 0))) / 100,
                "modifiers": [m.get("title") for m in item.get("selected_modifier_groups", [])]
            })

        eater = data.get("eater", {})
        delivery = data.get("delivery", {})

        return DeliveryOrder(
            id=data.get("id", ""),
            platform="uber_eats",
            external_id=data.get("display_id", data.get("id", "")),
            customer_name=f"{eater.get('first_name', '')} {eater.get('last_name', '')}".strip(),
            customer_phone=eater.get("phone"),
            customer_address=delivery.get("location", {}).get("address"),
            items=items,
            subtotal=Decimal(str(data.get("total", {}).get("sub_total", {}).get("amount", 0))) / 100,
            tax=Decimal(str(data.get("total", {}).get("tax", {}).get("amount", 0))) / 100,
            delivery_fee=Decimal(str(data.get("total", {}).get("delivery_fee", {}).get("amount", 0))) / 100,
            tip=Decimal(str(data.get("total", {}).get("tip", {}).get("amount", 0))) / 100,
            total=Decimal(str(data.get("total", {}).get("total", {}).get("amount", 0))) / 100,
            status=data.get("current_state", "pending").lower(),
            special_instructions=data.get("special_instructions"),
            estimated_pickup_time=None,
            created_at=datetime.now(timezone.utc),
            metadata={"raw": data}
        )


# =============================================================================
# DOORDASH INTEGRATION
# =============================================================================

class DoorDashService:
    """
    DoorDash Drive & Marketplace Integration
    https://developer.doordash.com/
    """

    BASE_URL = "https://openapi.doordash.com"

    def __init__(self):
        self.developer_id = settings.doordash_developer_id
        self.key_id = settings.doordash_key_id
        self.signing_secret = settings.doordash_signing_secret
        self.store_id = settings.doordash_store_id

    def _create_jwt(self) -> str:
        """Create JWT for DoorDash API authentication"""
        import jwt

        now = datetime.now(timezone.utc)
        payload = {
            "aud": "doordash",
            "iss": self.developer_id,
            "kid": self.key_id,
            "exp": now + timedelta(minutes=30),
            "iat": now
        }

        return jwt.encode(payload, self.signing_secret, algorithm="HS256")

    async def get_active_orders(self) -> IntegrationResult:
        """Get active orders from DoorDash"""
        try:
            token = self._create_jwt()
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{self.BASE_URL}/drive/v2/deliveries",
                    headers={"Authorization": f"Bearer {token}"},
                    params={"store_id": self.store_id, "status": "active"}
                )

                if response.status_code == 200:
                    orders = []
                    for order_data in response.json().get("deliveries", []):
                        orders.append(self._parse_order(order_data))
                    return IntegrationResult(success=True, data=orders)
                else:
                    return IntegrationResult(success=False, error_message=response.text)
        except Exception as e:
            logger.error(f"DoorDash get_active_orders error: {e}")
            return IntegrationResult(success=False, error_message=str(e))

    async def accept_order(self, order_id: str, prep_time_minutes: int = 20) -> IntegrationResult:
        """Accept a DoorDash order"""
        try:
            token = self._create_jwt()
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.patch(
                    f"{self.BASE_URL}/drive/v2/deliveries/{order_id}",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "status": "confirmed",
                        "pickup_time": (datetime.now(timezone.utc) + timedelta(minutes=prep_time_minutes)).isoformat()
                    }
                )

                if response.status_code in [200, 204]:
                    return IntegrationResult(success=True, data={"order_id": order_id, "status": "accepted"})
                else:
                    return IntegrationResult(success=False, error_message=response.text)
        except Exception as e:
            logger.error(f"DoorDash accept_order error: {e}")
            return IntegrationResult(success=False, error_message=str(e))

    async def cancel_order(self, order_id: str, reason: str) -> IntegrationResult:
        """Cancel a DoorDash order"""
        try:
            token = self._create_jwt()
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.patch(
                    f"{self.BASE_URL}/drive/v2/deliveries/{order_id}",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "status": "cancelled",
                        "cancellation_reason": reason
                    }
                )

                if response.status_code in [200, 204]:
                    return IntegrationResult(success=True, data={"order_id": order_id, "status": "cancelled"})
                else:
                    return IntegrationResult(success=False, error_message=response.text)
        except Exception as e:
            logger.error(f"DoorDash cancel_order error: {e}")
            return IntegrationResult(success=False, error_message=str(e))

    async def update_order_status(self, order_id: str, status: str) -> IntegrationResult:
        """Update order status"""
        status_map = {
            "preparing": "confirmed",
            "ready_for_pickup": "ready"
        }

        try:
            token = self._create_jwt()
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.patch(
                    f"{self.BASE_URL}/drive/v2/deliveries/{order_id}",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"status": status_map.get(status, status)}
                )

                if response.status_code in [200, 204]:
                    return IntegrationResult(success=True, data={"order_id": order_id, "status": status})
                else:
                    return IntegrationResult(success=False, error_message=response.text)
        except Exception as e:
            logger.error(f"DoorDash update_status error: {e}")
            return IntegrationResult(success=False, error_message=str(e))

    async def create_delivery(
        self,
        pickup_address: str,
        dropoff_address: str,
        dropoff_phone: str,
        order_value: Decimal,
        items: List[Dict]
    ) -> IntegrationResult:
        """Create a DoorDash Drive delivery (for your own orders)"""
        try:
            token = self._create_jwt()
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.BASE_URL}/drive/v2/deliveries",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "external_delivery_id": f"V99-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
                        "pickup_address": pickup_address,
                        "pickup_phone_number": settings.venue_phone,
                        "dropoff_address": dropoff_address,
                        "dropoff_phone_number": dropoff_phone,
                        "order_value": int(order_value * 100),
                        "items": items
                    }
                )

                if response.status_code in [200, 201]:
                    return IntegrationResult(success=True, data=response.json())
                else:
                    return IntegrationResult(success=False, error_message=response.text)
        except Exception as e:
            logger.error(f"DoorDash create_delivery error: {e}")
            return IntegrationResult(success=False, error_message=str(e))

    async def get_delivery_quote(
        self,
        pickup_address: str,
        dropoff_address: str,
        order_value: Decimal
    ) -> IntegrationResult:
        """Get delivery quote from DoorDash Drive"""
        try:
            token = self._create_jwt()
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.BASE_URL}/drive/v2/quotes",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "pickup_address": pickup_address,
                        "dropoff_address": dropoff_address,
                        "order_value": int(order_value * 100)
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    return IntegrationResult(success=True, data={
                        "fee": Decimal(data.get("fee", 0)) / 100,
                        "currency": data.get("currency", "USD"),
                        "estimated_delivery_time": data.get("time_estimate")
                    })
                else:
                    return IntegrationResult(success=False, error_message=response.text)
        except Exception as e:
            logger.error(f"DoorDash get_quote error: {e}")
            return IntegrationResult(success=False, error_message=str(e))

    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        """Verify DoorDash webhook signature"""
        if not self.signing_secret:
            return True

        expected = hmac.new(
            self.signing_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    def parse_webhook(self, payload: Dict) -> Optional[DeliveryOrder]:
        """Parse webhook payload"""
        event_type = payload.get("event_type")

        if "delivery" in event_type:
            return self._parse_order(payload.get("data", {}))

        return None

    def _parse_order(self, data: Dict) -> DeliveryOrder:
        """Parse DoorDash order data"""
        items = []
        for item in data.get("items", []):
            items.append({
                "id": item.get("external_id"),
                "name": item.get("name"),
                "quantity": item.get("quantity", 1),
                "price": Decimal(str(item.get("price", 0))) / 100,
                "modifiers": []
            })

        return DeliveryOrder(
            id=data.get("external_delivery_id", ""),
            platform="doordash",
            external_id=data.get("id", ""),
            customer_name=data.get("dropoff_contact_given_name", "Customer"),
            customer_phone=data.get("dropoff_phone_number"),
            customer_address=data.get("dropoff_address"),
            items=items,
            subtotal=Decimal(str(data.get("order_value", 0))) / 100,
            tax=Decimal("0"),
            delivery_fee=Decimal(str(data.get("fee", 0))) / 100,
            tip=Decimal(str(data.get("tip", 0))) / 100,
            total=Decimal(str(data.get("order_value", 0) + data.get("fee", 0) + data.get("tip", 0))) / 100,
            status=data.get("delivery_status", "pending").lower(),
            special_instructions=data.get("dropoff_instructions"),
            estimated_pickup_time=None,
            created_at=datetime.now(timezone.utc),
            metadata={"raw": data}
        )


# =============================================================================
# OPENTABLE INTEGRATION
# =============================================================================

class OpenTableService:
    """
    OpenTable Reservation Integration
    https://platform.opentable.com/documentation/
    """

    BASE_URL = "https://platform.opentable.com/sync/v2"

    def __init__(self):
        self.client_id = os.getenv("OPENTABLE_CLIENT_ID", "")
        self.client_secret = os.getenv("OPENTABLE_CLIENT_SECRET", "")
        self.restaurant_id = os.getenv("OPENTABLE_RESTAURANT_ID", "")
        self._access_token: Optional[str] = None
        self._token_expires: Optional[datetime] = None

    async def _get_access_token(self) -> str:
        """Get OAuth2 access token"""
        if self._access_token and self._token_expires and datetime.now(timezone.utc) < self._token_expires:
            return self._access_token

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://oauth.opentable.com/api/v2/oauth/token",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "client_credentials"
                }
            )

            if response.status_code == 200:
                data = response.json()
                self._access_token = data["access_token"]
                self._token_expires = datetime.now(timezone.utc) + timedelta(seconds=data.get("expires_in", 3600) - 60)
                return self._access_token
            else:
                raise Exception(f"Failed to get OpenTable token: {response.text}")

    async def get_reservations(
        self,
        date: Optional[str] = None,
        status: Optional[str] = None
    ) -> IntegrationResult:
        """Get reservations for a date"""
        try:
            token = await self._get_access_token()
            params = {"rid": self.restaurant_id}

            if date:
                params["date"] = date
            if status:
                params["status"] = status

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{self.BASE_URL}/reservations",
                    headers={"Authorization": f"Bearer {token}"},
                    params=params
                )

                if response.status_code == 200:
                    reservations = []
                    for res_data in response.json().get("reservations", []):
                        reservations.append(self._parse_reservation(res_data))
                    return IntegrationResult(success=True, data=reservations)
                else:
                    return IntegrationResult(success=False, error_message=response.text)
        except Exception as e:
            logger.error(f"OpenTable get_reservations error: {e}")
            return IntegrationResult(success=False, error_message=str(e))

    async def get_reservation(self, reservation_id: str) -> IntegrationResult:
        """Get a specific reservation"""
        try:
            token = await self._get_access_token()
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{self.BASE_URL}/reservations/{reservation_id}",
                    headers={"Authorization": f"Bearer {token}"}
                )

                if response.status_code == 200:
                    return IntegrationResult(
                        success=True,
                        data=self._parse_reservation(response.json())
                    )
                else:
                    return IntegrationResult(success=False, error_message=response.text)
        except Exception as e:
            logger.error(f"OpenTable get_reservation error: {e}")
            return IntegrationResult(success=False, error_message=str(e))

    async def confirm_reservation(self, reservation_id: str) -> IntegrationResult:
        """Confirm a reservation"""
        try:
            token = await self._get_access_token()
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.BASE_URL}/reservations/{reservation_id}/confirm",
                    headers={"Authorization": f"Bearer {token}"}
                )

                if response.status_code in [200, 204]:
                    return IntegrationResult(success=True, data={"reservation_id": reservation_id, "status": "confirmed"})
                else:
                    return IntegrationResult(success=False, error_message=response.text)
        except Exception as e:
            logger.error(f"OpenTable confirm error: {e}")
            return IntegrationResult(success=False, error_message=str(e))

    async def cancel_reservation(self, reservation_id: str, reason: str) -> IntegrationResult:
        """Cancel a reservation"""
        try:
            token = await self._get_access_token()
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.BASE_URL}/reservations/{reservation_id}/cancel",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"reason": reason}
                )

                if response.status_code in [200, 204]:
                    return IntegrationResult(success=True, data={"reservation_id": reservation_id, "status": "cancelled"})
                else:
                    return IntegrationResult(success=False, error_message=response.text)
        except Exception as e:
            logger.error(f"OpenTable cancel error: {e}")
            return IntegrationResult(success=False, error_message=str(e))

    async def seat_reservation(self, reservation_id: str, table_id: int) -> IntegrationResult:
        """Mark reservation as seated"""
        try:
            token = await self._get_access_token()
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.BASE_URL}/reservations/{reservation_id}/seat",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"table_id": str(table_id)}
                )

                if response.status_code in [200, 204]:
                    return IntegrationResult(success=True, data={"reservation_id": reservation_id, "status": "seated"})
                else:
                    return IntegrationResult(success=False, error_message=response.text)
        except Exception as e:
            logger.error(f"OpenTable seat error: {e}")
            return IntegrationResult(success=False, error_message=str(e))

    async def complete_reservation(self, reservation_id: str) -> IntegrationResult:
        """Mark reservation as completed"""
        try:
            token = await self._get_access_token()
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.BASE_URL}/reservations/{reservation_id}/complete",
                    headers={"Authorization": f"Bearer {token}"}
                )

                if response.status_code in [200, 204]:
                    return IntegrationResult(success=True, data={"reservation_id": reservation_id, "status": "completed"})
                else:
                    return IntegrationResult(success=False, error_message=response.text)
        except Exception as e:
            logger.error(f"OpenTable complete error: {e}")
            return IntegrationResult(success=False, error_message=str(e))

    async def update_availability(self, date: str, times: List[Dict]) -> IntegrationResult:
        """Update availability for a date"""
        try:
            token = await self._get_access_token()
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.put(
                    f"{self.BASE_URL}/availability",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "rid": self.restaurant_id,
                        "date": date,
                        "times": times  # [{"time": "18:00", "party_sizes": [2, 4, 6]}]
                    }
                )

                if response.status_code in [200, 204]:
                    return IntegrationResult(success=True, data={"date": date, "slots_updated": len(times)})
                else:
                    return IntegrationResult(success=False, error_message=response.text)
        except Exception as e:
            logger.error(f"OpenTable update_availability error: {e}")
            return IntegrationResult(success=False, error_message=str(e))

    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        """Verify OpenTable webhook"""
        if not self.client_secret:
            return True

        expected = hmac.new(
            self.client_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    def parse_webhook(self, payload: Dict) -> Optional[Reservation]:
        """Parse webhook payload"""
        event_type = payload.get("event_type", "")

        if "reservation" in event_type.lower():
            return self._parse_reservation(payload.get("data", {}))

        return None

    def _parse_reservation(self, data: Dict) -> Reservation:
        """Parse OpenTable reservation data"""
        guest = data.get("guest", {})

        return Reservation(
            id=data.get("confirmation_number", ""),
            platform="opentable",
            external_id=data.get("rid", ""),
            customer_name=f"{guest.get('first_name', '')} {guest.get('last_name', '')}".strip(),
            customer_email=guest.get("email"),
            customer_phone=guest.get("phone"),
            party_size=data.get("party_size", 2),
            date=data.get("date", ""),
            time=data.get("time", ""),
            table_id=None,
            special_requests=data.get("special_requests"),
            status=data.get("state", "pending").lower(),
            created_at=datetime.now(timezone.utc),
            metadata={"raw": data}
        )


# =============================================================================
# RESY INTEGRATION
# =============================================================================

class ResyService:
    """
    Resy Reservation Integration
    https://resy.com/
    """

    BASE_URL = "https://api.resy.com/3"

    def __init__(self):
        self.api_key = os.getenv("RESY_API_KEY", "")
        self.venue_id = os.getenv("RESY_VENUE_ID", "")

    async def get_reservations(
        self,
        date: Optional[str] = None,
        status: Optional[str] = None
    ) -> IntegrationResult:
        """Get reservations for a date"""
        try:
            params = {"venue_id": self.venue_id}
            if date:
                params["day"] = date

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{self.BASE_URL}/venue/{self.venue_id}/reservations",
                    headers={
                        "Authorization": f"ResyAPI api_key=\"{self.api_key}\"",
                        "X-Resy-Auth-Token": self.api_key
                    },
                    params=params
                )

                if response.status_code == 200:
                    reservations = []
                    for res_data in response.json().get("reservations", []):
                        reservations.append(self._parse_reservation(res_data))
                    return IntegrationResult(success=True, data=reservations)
                else:
                    return IntegrationResult(success=False, error_message=response.text)
        except Exception as e:
            logger.error(f"Resy get_reservations error: {e}")
            return IntegrationResult(success=False, error_message=str(e))

    async def get_reservation(self, reservation_id: str) -> IntegrationResult:
        """Get a specific reservation"""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{self.BASE_URL}/reservation/{reservation_id}",
                    headers={
                        "Authorization": f"ResyAPI api_key=\"{self.api_key}\"",
                        "X-Resy-Auth-Token": self.api_key
                    }
                )

                if response.status_code == 200:
                    return IntegrationResult(
                        success=True,
                        data=self._parse_reservation(response.json())
                    )
                else:
                    return IntegrationResult(success=False, error_message=response.text)
        except Exception as e:
            logger.error(f"Resy get_reservation error: {e}")
            return IntegrationResult(success=False, error_message=str(e))

    async def confirm_reservation(self, reservation_id: str) -> IntegrationResult:
        """Confirm a reservation"""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.BASE_URL}/reservation/{reservation_id}/confirm",
                    headers={
                        "Authorization": f"ResyAPI api_key=\"{self.api_key}\"",
                        "X-Resy-Auth-Token": self.api_key
                    }
                )

                if response.status_code in [200, 204]:
                    return IntegrationResult(success=True, data={"reservation_id": reservation_id, "status": "confirmed"})
                else:
                    return IntegrationResult(success=False, error_message=response.text)
        except Exception as e:
            logger.error(f"Resy confirm error: {e}")
            return IntegrationResult(success=False, error_message=str(e))

    async def cancel_reservation(self, reservation_id: str, reason: str) -> IntegrationResult:
        """Cancel a reservation"""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.BASE_URL}/reservation/{reservation_id}/cancel",
                    headers={
                        "Authorization": f"ResyAPI api_key=\"{self.api_key}\"",
                        "X-Resy-Auth-Token": self.api_key
                    },
                    json={"cancellation_reason": reason}
                )

                if response.status_code in [200, 204]:
                    return IntegrationResult(success=True, data={"reservation_id": reservation_id, "status": "cancelled"})
                else:
                    return IntegrationResult(success=False, error_message=response.text)
        except Exception as e:
            logger.error(f"Resy cancel error: {e}")
            return IntegrationResult(success=False, error_message=str(e))

    async def seat_reservation(self, reservation_id: str, table_number: str) -> IntegrationResult:
        """Mark reservation as seated"""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.BASE_URL}/reservation/{reservation_id}/seat",
                    headers={
                        "Authorization": f"ResyAPI api_key=\"{self.api_key}\"",
                        "X-Resy-Auth-Token": self.api_key
                    },
                    json={"table": table_number}
                )

                if response.status_code in [200, 204]:
                    return IntegrationResult(success=True, data={"reservation_id": reservation_id, "status": "seated"})
                else:
                    return IntegrationResult(success=False, error_message=response.text)
        except Exception as e:
            logger.error(f"Resy seat error: {e}")
            return IntegrationResult(success=False, error_message=str(e))

    async def no_show(self, reservation_id: str) -> IntegrationResult:
        """Mark reservation as no-show"""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.BASE_URL}/reservation/{reservation_id}/noshow",
                    headers={
                        "Authorization": f"ResyAPI api_key=\"{self.api_key}\"",
                        "X-Resy-Auth-Token": self.api_key
                    }
                )

                if response.status_code in [200, 204]:
                    return IntegrationResult(success=True, data={"reservation_id": reservation_id, "status": "no_show"})
                else:
                    return IntegrationResult(success=False, error_message=response.text)
        except Exception as e:
            logger.error(f"Resy no_show error: {e}")
            return IntegrationResult(success=False, error_message=str(e))

    async def get_availability(self, date: str, party_size: int) -> IntegrationResult:
        """Get availability for a date"""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{self.BASE_URL}/venue/{self.venue_id}/calendar",
                    headers={
                        "Authorization": f"ResyAPI api_key=\"{self.api_key}\"",
                        "X-Resy-Auth-Token": self.api_key
                    },
                    params={
                        "day": date,
                        "party_size": party_size
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    slots = []
                    for slot in data.get("scheduled", []):
                        slots.append({
                            "time": slot.get("time_slot"),
                            "available": slot.get("quantity", 0) > 0,
                            "quantity": slot.get("quantity", 0)
                        })
                    return IntegrationResult(success=True, data={"date": date, "slots": slots})
                else:
                    return IntegrationResult(success=False, error_message=response.text)
        except Exception as e:
            logger.error(f"Resy get_availability error: {e}")
            return IntegrationResult(success=False, error_message=str(e))

    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        """Verify Resy webhook"""
        if not self.api_key:
            return True

        expected = hmac.new(
            self.api_key.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    def parse_webhook(self, payload: Dict) -> Optional[Reservation]:
        """Parse webhook payload"""
        event_type = payload.get("type", "")

        if "reservation" in event_type.lower():
            return self._parse_reservation(payload.get("reservation", {}))

        return None

    def _parse_reservation(self, data: Dict) -> Reservation:
        """Parse Resy reservation data"""
        user = data.get("user", {})

        return Reservation(
            id=str(data.get("resy_token", "")),
            platform="resy",
            external_id=str(data.get("id", "")),
            customer_name=f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
            customer_email=user.get("em_address"),
            customer_phone=user.get("mobile_number"),
            party_size=data.get("num_seats", 2),
            date=data.get("day", ""),
            time=data.get("time_slot", ""),
            table_id=None,
            special_requests=data.get("service_notes"),
            status=data.get("reservation_status", "pending").lower(),
            created_at=datetime.now(timezone.utc),
            metadata={"raw": data}
        )


# =============================================================================
# UNIFIED DELIVERY MANAGER
# =============================================================================

class DeliveryPlatformManager:
    """
    Unified manager for all delivery and reservation platforms
    """

    def __init__(self):
        self.uber_eats = UberEatsService()
        self.doordash = DoorDashService()
        self.opentable = OpenTableService()
        self.resy = ResyService()

    def get_service(self, platform: str):
        """Get service by platform name"""
        services = {
            "uber_eats": self.uber_eats,
            "doordash": self.doordash,
            "opentable": self.opentable,
            "resy": self.resy
        }
        return services.get(platform.lower())

    async def get_all_active_orders(self) -> Dict[str, List[DeliveryOrder]]:
        """Get active orders from all delivery platforms"""
        results = {}

        # UberEats
        uber_result = await self.uber_eats.get_active_orders()
        if uber_result.success:
            results["uber_eats"] = uber_result.data

        # DoorDash
        dd_result = await self.doordash.get_active_orders()
        if dd_result.success:
            results["doordash"] = dd_result.data

        return results

    async def get_all_reservations(self, date: str) -> Dict[str, List[Reservation]]:
        """Get reservations from all platforms for a date"""
        results = {}

        # OpenTable
        ot_result = await self.opentable.get_reservations(date=date)
        if ot_result.success:
            results["opentable"] = ot_result.data

        # Resy
        resy_result = await self.resy.get_reservations(date=date)
        if resy_result.success:
            results["resy"] = resy_result.data

        return results

    async def accept_order(self, platform: str, order_id: str, prep_time: int = 20) -> IntegrationResult:
        """Accept an order from any platform"""
        service = self.get_service(platform)
        if not service or not hasattr(service, 'accept_order'):
            return IntegrationResult(success=False, error_message=f"Platform {platform} not supported for orders")

        return await service.accept_order(order_id, prep_time)

    async def cancel_order(self, platform: str, order_id: str, reason: str) -> IntegrationResult:
        """Cancel an order from any platform"""
        service = self.get_service(platform)
        if not service or not hasattr(service, 'cancel_order'):
            return IntegrationResult(success=False, error_message=f"Platform {platform} not supported")

        return await service.cancel_order(order_id, reason)

    async def confirm_reservation(self, platform: str, reservation_id: str) -> IntegrationResult:
        """Confirm a reservation from any platform"""
        service = self.get_service(platform)
        if not service or not hasattr(service, 'confirm_reservation'):
            return IntegrationResult(success=False, error_message=f"Platform {platform} not supported for reservations")

        return await service.confirm_reservation(reservation_id)


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

_manager: Optional[DeliveryPlatformManager] = None

def get_delivery_manager() -> DeliveryPlatformManager:
    """Get singleton delivery platform manager"""
    global _manager
    if _manager is None:
        _manager = DeliveryPlatformManager()
    return _manager

def get_uber_eats_service() -> UberEatsService:
    return get_delivery_manager().uber_eats

def get_doordash_service() -> DoorDashService:
    return get_delivery_manager().doordash

def get_opentable_service() -> OpenTableService:
    return get_delivery_manager().opentable

def get_resy_service() -> ResyService:
    return get_delivery_manager().resy

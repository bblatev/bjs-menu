"""Square Payment Gateway Service.

Provides Square Payments integration with:
- Payment creation via Square Payments API
- Order creation and management
- Full and partial refunds
- Webhook event processing with signature verification
- Customer management
- Catalog (menu item) sync
- Terminal checkout for Square Terminal hardware

The square SDK is imported conditionally.
"""

import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class SquareService:
    """Square REST API gateway.

    Uses httpx for async HTTP calls to Square APIs.
    Supports both sandbox and production environments.
    """

    SANDBOX_BASE = "https://connect.squareupsandbox.com"
    PRODUCTION_BASE = "https://connect.squareup.com"

    def __init__(
        self,
        access_token: Optional[str] = None,
        location_id: Optional[str] = None,
        webhook_signature_key: Optional[str] = None,
        sandbox: bool = True,
    ):
        self._access_token = access_token or getattr(settings, "square_access_token", "")
        self._location_id = location_id or getattr(settings, "square_location_id", "")
        self._webhook_signature_key = webhook_signature_key or getattr(settings, "square_webhook_signature_key", "")
        self._sandbox = sandbox if sandbox is not None else getattr(settings, "square_sandbox", True)
        self._base_url = self.SANDBOX_BASE if self._sandbox else self.PRODUCTION_BASE
        self._configured = bool(self._access_token)

        if not self._configured:
            logger.warning(
                "Square credentials not configured. Set SQUARE_ACCESS_TOKEN "
                "environment variable."
            )

    @property
    def is_configured(self) -> bool:
        return self._configured

    def _require_configured(self) -> None:
        if not self._configured:
            raise RuntimeError(
                "Square is not configured. Set SQUARE_ACCESS_TOKEN "
                "environment variable."
            )

    def _headers(self) -> Dict[str, str]:
        return {
            "Square-Version": "2024-11-20",
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _idempotency_key() -> str:
        return str(uuid.uuid4())

    # ------------------------------------------------------------------
    # Payments
    # ------------------------------------------------------------------

    async def create_payment(
        self,
        amount_cents: int,
        source_id: str,
        currency: str = "USD",
        location_id: Optional[str] = None,
        order_id: Optional[str] = None,
        customer_id: Optional[str] = None,
        reference_id: Optional[str] = None,
        note: Optional[str] = None,
        tip_cents: int = 0,
        autocomplete: bool = True,
    ) -> Dict[str, Any]:
        """Create a payment using a payment source (nonce, card ID, or token)."""
        self._require_configured()

        body: Dict[str, Any] = {
            "idempotency_key": self._idempotency_key(),
            "source_id": source_id,
            "amount_money": {
                "amount": amount_cents,
                "currency": currency.upper(),
            },
            "location_id": location_id or self._location_id,
            "autocomplete": autocomplete,
        }
        if order_id:
            body["order_id"] = order_id
        if customer_id:
            body["customer_id"] = customer_id
        if reference_id:
            body["reference_id"] = reference_id
        if note:
            body["note"] = note
        if tip_cents > 0:
            body["tip_money"] = {"amount": tip_cents, "currency": currency.upper()}

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/v2/payments",
                json=body,
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()

        payment = data.get("payment", {})
        return {
            "payment_id": payment.get("id"),
            "status": payment.get("status"),
            "amount": payment.get("amount_money", {}),
            "tip": payment.get("tip_money", {}),
            "receipt_url": payment.get("receipt_url"),
            "order_id": payment.get("order_id"),
            "created_at": payment.get("created_at"),
            "card_details": payment.get("card_details", {}),
        }

    async def complete_payment(self, payment_id: str) -> Dict[str, Any]:
        """Complete a delayed-capture payment."""
        self._require_configured()

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/v2/payments/{payment_id}/complete",
                json={},
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()

        payment = data.get("payment", {})
        return {"payment_id": payment.get("id"), "status": payment.get("status")}

    async def cancel_payment(self, payment_id: str) -> Dict[str, Any]:
        """Cancel a pending payment."""
        self._require_configured()

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/v2/payments/{payment_id}/cancel",
                json={},
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()

        payment = data.get("payment", {})
        return {"payment_id": payment.get("id"), "status": payment.get("status")}

    async def get_payment(self, payment_id: str) -> Dict[str, Any]:
        """Retrieve payment details."""
        self._require_configured()

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._base_url}/v2/payments/{payment_id}",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json().get("payment", {})

    async def list_payments(
        self,
        begin_time: Optional[str] = None,
        end_time: Optional[str] = None,
        sort_order: str = "DESC",
        limit: int = 50,
    ) -> Dict[str, Any]:
        """List payments with optional date filtering."""
        self._require_configured()

        params: Dict[str, Any] = {"sort_order": sort_order, "limit": min(limit, 100)}
        if begin_time:
            params["begin_time"] = begin_time
        if end_time:
            params["end_time"] = end_time
        if self._location_id:
            params["location_id"] = self._location_id

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._base_url}/v2/payments",
                params=params,
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()

        return {
            "payments": data.get("payments", []),
            "cursor": data.get("cursor"),
        }

    # ------------------------------------------------------------------
    # Refunds
    # ------------------------------------------------------------------

    async def refund_payment(
        self,
        payment_id: str,
        amount_cents: Optional[int] = None,
        currency: str = "USD",
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Refund a payment (full or partial)."""
        self._require_configured()

        body: Dict[str, Any] = {
            "idempotency_key": self._idempotency_key(),
            "payment_id": payment_id,
        }
        if amount_cents is not None:
            body["amount_money"] = {
                "amount": amount_cents,
                "currency": currency.upper(),
            }
        if reason:
            body["reason"] = reason

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/v2/refunds",
                json=body,
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()

        refund = data.get("refund", {})
        return {
            "refund_id": refund.get("id"),
            "status": refund.get("status"),
            "amount": refund.get("amount_money", {}),
            "payment_id": refund.get("payment_id"),
        }

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------

    async def create_order(
        self,
        line_items: List[Dict[str, Any]],
        location_id: Optional[str] = None,
        customer_id: Optional[str] = None,
        reference_id: Optional[str] = None,
        taxes: Optional[List[Dict[str, Any]]] = None,
        discounts: Optional[List[Dict[str, Any]]] = None,
        service_charges: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Create a Square order."""
        self._require_configured()

        order: Dict[str, Any] = {
            "location_id": location_id or self._location_id,
            "line_items": line_items,
        }
        if customer_id:
            order["customer_id"] = customer_id
        if reference_id:
            order["reference_id"] = reference_id
        if taxes:
            order["taxes"] = taxes
        if discounts:
            order["discounts"] = discounts
        if service_charges:
            order["service_charges"] = service_charges

        body = {
            "idempotency_key": self._idempotency_key(),
            "order": order,
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/v2/orders",
                json=body,
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()

        sq_order = data.get("order", {})
        return {
            "order_id": sq_order.get("id"),
            "state": sq_order.get("state"),
            "total": sq_order.get("total_money", {}),
            "line_items": sq_order.get("line_items", []),
        }

    # ------------------------------------------------------------------
    # Customers
    # ------------------------------------------------------------------

    async def create_customer(
        self,
        given_name: str,
        family_name: str = "",
        email: Optional[str] = None,
        phone: Optional[str] = None,
        reference_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a Square customer record."""
        self._require_configured()

        body: Dict[str, Any] = {
            "idempotency_key": self._idempotency_key(),
            "given_name": given_name,
        }
        if family_name:
            body["family_name"] = family_name
        if email:
            body["email_address"] = email
        if phone:
            body["phone_number"] = phone
        if reference_id:
            body["reference_id"] = reference_id

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/v2/customers",
                json=body,
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()

        customer = data.get("customer", {})
        return {
            "customer_id": customer.get("id"),
            "given_name": customer.get("given_name"),
            "email": customer.get("email_address"),
            "created_at": customer.get("created_at"),
        }

    async def search_customers(
        self,
        query: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Search Square customers."""
        self._require_configured()

        body: Dict[str, Any] = {"limit": min(limit, 100)}
        filters: List[Dict[str, Any]] = []

        if email:
            filters.append({"email_address": {"exact": email}})
        if phone:
            filters.append({"phone_number": {"exact": phone}})
        if query:
            body["query"] = {
                "filter": {"fuzzy": {"display_name": query}},
            }
        elif filters:
            body["query"] = {"filter": filters[0] if len(filters) == 1 else {"and": filters}}

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/v2/customers/search",
                json=body,
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()

        return {"customers": data.get("customers", []), "cursor": data.get("cursor")}

    # ------------------------------------------------------------------
    # Terminal Checkout (Square Terminal hardware)
    # ------------------------------------------------------------------

    async def create_terminal_checkout(
        self,
        amount_cents: int,
        currency: str = "USD",
        device_id: Optional[str] = None,
        note: Optional[str] = None,
        reference_id: Optional[str] = None,
        tip_settings: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a terminal checkout for Square Terminal device."""
        self._require_configured()

        checkout: Dict[str, Any] = {
            "amount_money": {
                "amount": amount_cents,
                "currency": currency.upper(),
            },
        }
        if device_id:
            checkout["device_options"] = {"device_id": device_id}
        if note:
            checkout["note"] = note
        if reference_id:
            checkout["reference_id"] = reference_id
        if tip_settings:
            checkout["device_options"] = checkout.get("device_options", {})
            checkout["device_options"]["tip_settings"] = tip_settings

        body = {
            "idempotency_key": self._idempotency_key(),
            "checkout": checkout,
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/v2/terminals/checkouts",
                json=body,
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()

        co = data.get("checkout", {})
        return {
            "checkout_id": co.get("id"),
            "status": co.get("status"),
            "amount": co.get("amount_money", {}),
            "payment_ids": co.get("payment_ids", []),
        }

    # ------------------------------------------------------------------
    # Catalog Sync
    # ------------------------------------------------------------------

    async def upsert_catalog_item(
        self,
        name: str,
        price_cents: int,
        currency: str = "USD",
        description: Optional[str] = None,
        category_id: Optional[str] = None,
        item_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create or update a catalog item (menu item sync)."""
        self._require_configured()

        variation_data: Dict[str, Any] = {
            "type": "ITEM_VARIATION",
            "id": f"#variation-{item_id or uuid.uuid4().hex[:8]}",
            "item_variation_data": {
                "name": "Regular",
                "pricing_type": "FIXED_PRICING",
                "price_money": {
                    "amount": price_cents,
                    "currency": currency.upper(),
                },
            },
        }

        item_data: Dict[str, Any] = {
            "name": name,
            "variations": [variation_data],
        }
        if description:
            item_data["description"] = description
        if category_id:
            item_data["category_id"] = category_id

        obj = {
            "type": "ITEM",
            "id": item_id or f"#item-{uuid.uuid4().hex[:8]}",
            "item_data": item_data,
        }

        body = {
            "idempotency_key": self._idempotency_key(),
            "object": obj,
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/v2/catalog/object",
                json=body,
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()

        catalog_obj = data.get("catalog_object", {})
        return {
            "catalog_id": catalog_obj.get("id"),
            "type": catalog_obj.get("type"),
            "version": catalog_obj.get("version"),
        }

    async def list_catalog(
        self,
        types: Optional[List[str]] = None,
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List catalog items."""
        self._require_configured()

        params: Dict[str, Any] = {}
        if types:
            params["types"] = ",".join(types)
        if cursor:
            params["cursor"] = cursor

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._base_url}/v2/catalog/list",
                params=params,
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()

        return {
            "objects": data.get("objects", []),
            "cursor": data.get("cursor"),
        }

    # ------------------------------------------------------------------
    # Webhooks
    # ------------------------------------------------------------------

    def verify_webhook(
        self,
        body: bytes,
        signature: str,
        url: str,
    ) -> bool:
        """Verify Square webhook HMAC-SHA256 signature."""
        if not self._webhook_signature_key:
            logger.warning("Square webhook signature key not set; skipping verification")
            return True

        combined = url.encode("utf-8") + body
        expected = hmac.new(
            self._webhook_signature_key.encode("utf-8"),
            combined,
            hashlib.sha256,
        ).digest()
        import base64
        expected_b64 = base64.b64encode(expected).decode("utf-8")

        return hmac.compare_digest(expected_b64, signature)

    def parse_webhook_event(self, body: bytes) -> Dict[str, Any]:
        """Parse a Square webhook event."""
        event = json.loads(body)
        return {
            "event_id": event.get("event_id"),
            "type": event.get("type"),
            "merchant_id": event.get("merchant_id"),
            "data": event.get("data", {}),
            "created_at": event.get("created_at"),
        }

    # ------------------------------------------------------------------
    # Inventory
    # ------------------------------------------------------------------

    async def batch_change_inventory(
        self,
        changes: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Batch update inventory counts in Square."""
        self._require_configured()

        body = {
            "idempotency_key": self._idempotency_key(),
            "changes": changes,
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/v2/inventory/changes/batch-create",
                json=body,
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------

_square_service: Optional[SquareService] = None


def get_square_service() -> SquareService:
    global _square_service
    if _square_service is None:
        _square_service = SquareService()
    return _square_service

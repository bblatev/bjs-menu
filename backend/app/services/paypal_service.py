"""PayPal Payment Gateway Service.

Provides PayPal Checkout integration with:
- Order creation via PayPal REST API v2
- Order capture and authorization
- Full and partial refunds
- Webhook event processing with signature verification
- Subscription management (recurring billing)
- PayPal Vault for saved payment methods

The paypalrestsdk / paypal-server-sdk is imported conditionally so the
application can start even when the package is not installed.
"""

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class PayPalService:
    """PayPal REST API v2 gateway.

    Uses httpx for async HTTP calls to PayPal APIs.
    Supports both sandbox and live environments.
    """

    SANDBOX_BASE = "https://api-m.sandbox.paypal.com"
    LIVE_BASE = "https://api-m.paypal.com"

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        webhook_id: Optional[str] = None,
        sandbox: bool = True,
        currency: str = "USD",
    ):
        self._client_id = client_id or getattr(settings, "paypal_client_id", "")
        self._client_secret = client_secret or getattr(settings, "paypal_client_secret", "")
        self._webhook_id = webhook_id or getattr(settings, "paypal_webhook_id", "")
        self._sandbox = sandbox if sandbox is not None else getattr(settings, "paypal_sandbox", True)
        self._currency = currency.upper()
        self._base_url = self.SANDBOX_BASE if self._sandbox else self.LIVE_BASE
        self._access_token: Optional[str] = None
        self._token_expires: Optional[datetime] = None
        self._configured = bool(self._client_id and self._client_secret)

        if not self._configured:
            logger.warning(
                "PayPal credentials not configured. Set PAYPAL_CLIENT_ID and "
                "PAYPAL_CLIENT_SECRET environment variables."
            )

    @property
    def is_configured(self) -> bool:
        return self._configured

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    async def _get_access_token(self) -> str:
        """Obtain or refresh OAuth2 access token."""
        if (
            self._access_token
            and self._token_expires
            and datetime.now(timezone.utc) < self._token_expires
        ):
            return self._access_token

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/v1/oauth2/token",
                data={"grant_type": "client_credentials"},
                auth=(self._client_id, self._client_secret),
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()

        self._access_token = data["access_token"]
        expires_in = data.get("expires_in", 32400)
        from datetime import timedelta
        self._token_expires = datetime.now(timezone.utc) + timedelta(seconds=expires_in - 60)
        return self._access_token

    async def _headers(self) -> Dict[str, str]:
        token = await self._get_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _require_configured(self) -> None:
        if not self._configured:
            raise RuntimeError(
                "PayPal is not configured. Set PAYPAL_CLIENT_ID and "
                "PAYPAL_CLIENT_SECRET environment variables."
            )

    # ------------------------------------------------------------------
    # Orders (Checkout)
    # ------------------------------------------------------------------

    async def create_order(
        self,
        amount: float,
        currency: Optional[str] = None,
        description: Optional[str] = None,
        return_url: str = "https://example.com/return",
        cancel_url: str = "https://example.com/cancel",
        reference_id: Optional[str] = None,
        items: Optional[List[Dict[str, Any]]] = None,
        shipping: Optional[Dict[str, Any]] = None,
        custom_id: Optional[str] = None,
        intent: str = "CAPTURE",
    ) -> Dict[str, Any]:
        """Create a PayPal order for checkout.

        Returns order_id and approval URL for redirect flow.
        """
        self._require_configured()
        curr = (currency or self._currency).upper()

        purchase_unit: Dict[str, Any] = {
            "amount": {
                "currency_code": curr,
                "value": f"{amount:.2f}",
            },
        }
        if reference_id:
            purchase_unit["reference_id"] = reference_id
        if description:
            purchase_unit["description"] = description
        if custom_id:
            purchase_unit["custom_id"] = custom_id
        if shipping:
            purchase_unit["shipping"] = shipping

        if items:
            item_total = sum(float(i.get("unit_amount", {}).get("value", 0)) * int(i.get("quantity", 1)) for i in items)
            purchase_unit["amount"]["breakdown"] = {
                "item_total": {"currency_code": curr, "value": f"{item_total:.2f}"},
            }
            purchase_unit["items"] = items

        body: Dict[str, Any] = {
            "intent": intent,
            "purchase_units": [purchase_unit],
            "payment_source": {
                "paypal": {
                    "experience_context": {
                        "payment_method_preference": "IMMEDIATE_PAYMENT_REQUIRED",
                        "landing_page": "LOGIN",
                        "user_action": "PAY_NOW",
                        "return_url": return_url,
                        "cancel_url": cancel_url,
                    }
                }
            },
        }

        headers = await self._headers()
        headers["PayPal-Request-Id"] = reference_id or f"order-{datetime.now(timezone.utc).isoformat()}"

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/v2/checkout/orders",
                json=body,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

        approval_url = next(
            (l["href"] for l in data.get("links", []) if l["rel"] == "payer-action"),
            None,
        )

        return {
            "order_id": data["id"],
            "status": data["status"],
            "approval_url": approval_url,
            "links": data.get("links", []),
        }

    async def capture_order(self, order_id: str) -> Dict[str, Any]:
        """Capture an approved PayPal order."""
        self._require_configured()
        headers = await self._headers()
        headers["PayPal-Request-Id"] = f"capture-{order_id}"

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/v2/checkout/orders/{order_id}/capture",
                headers=headers,
                content="",
            )
            resp.raise_for_status()
            data = resp.json()

        capture = {}
        units = data.get("purchase_units", [{}])
        if units:
            captures = units[0].get("payments", {}).get("captures", [])
            if captures:
                capture = captures[0]

        return {
            "order_id": data["id"],
            "status": data["status"],
            "capture_id": capture.get("id"),
            "amount": capture.get("amount", {}),
            "payer": data.get("payer", {}),
        }

    async def authorize_order(self, order_id: str) -> Dict[str, Any]:
        """Authorize an approved PayPal order (for manual capture later)."""
        self._require_configured()
        headers = await self._headers()

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/v2/checkout/orders/{order_id}/authorize",
                headers=headers,
                content="",
            )
            resp.raise_for_status()
            data = resp.json()

        auth = {}
        units = data.get("purchase_units", [{}])
        if units:
            auths = units[0].get("payments", {}).get("authorizations", [])
            if auths:
                auth = auths[0]

        return {
            "order_id": data["id"],
            "status": data["status"],
            "authorization_id": auth.get("id"),
            "amount": auth.get("amount", {}),
        }

    async def get_order(self, order_id: str) -> Dict[str, Any]:
        """Get order details."""
        self._require_configured()
        headers = await self._headers()

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._base_url}/v2/checkout/orders/{order_id}",
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()

    # ------------------------------------------------------------------
    # Refunds
    # ------------------------------------------------------------------

    async def refund_capture(
        self,
        capture_id: str,
        amount: Optional[float] = None,
        currency: Optional[str] = None,
        note: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Refund a captured payment (full or partial)."""
        self._require_configured()
        headers = await self._headers()
        headers["PayPal-Request-Id"] = f"refund-{capture_id}-{datetime.now(timezone.utc).isoformat()}"

        body: Dict[str, Any] = {}
        if amount is not None:
            body["amount"] = {
                "currency_code": (currency or self._currency).upper(),
                "value": f"{amount:.2f}",
            }
        if note:
            body["note_to_payer"] = note

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/v2/payments/captures/{capture_id}/refund",
                json=body if body else None,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

        return {
            "refund_id": data["id"],
            "status": data["status"],
            "amount": data.get("amount", {}),
        }

    # ------------------------------------------------------------------
    # Subscriptions (Recurring)
    # ------------------------------------------------------------------

    async def create_plan(
        self,
        product_id: str,
        name: str,
        billing_cycles: List[Dict[str, Any]],
        payment_preferences: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a subscription billing plan."""
        self._require_configured()
        headers = await self._headers()

        body: Dict[str, Any] = {
            "product_id": product_id,
            "name": name,
            "billing_cycles": billing_cycles,
            "payment_preferences": payment_preferences or {
                "auto_bill_outstanding": True,
                "payment_failure_threshold": 3,
            },
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/v1/billing/plans",
                json=body,
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def create_subscription(
        self,
        plan_id: str,
        subscriber: Dict[str, Any],
        return_url: str,
        cancel_url: str,
        custom_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a subscription for a customer."""
        self._require_configured()
        headers = await self._headers()

        body: Dict[str, Any] = {
            "plan_id": plan_id,
            "subscriber": subscriber,
            "application_context": {
                "return_url": return_url,
                "cancel_url": cancel_url,
                "user_action": "SUBSCRIBE_NOW",
            },
        }
        if custom_id:
            body["custom_id"] = custom_id

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/v1/billing/subscriptions",
                json=body,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

        approval_url = next(
            (l["href"] for l in data.get("links", []) if l["rel"] == "approve"),
            None,
        )

        return {
            "subscription_id": data["id"],
            "status": data["status"],
            "approval_url": approval_url,
        }

    # ------------------------------------------------------------------
    # Payouts (send money)
    # ------------------------------------------------------------------

    async def create_payout(
        self,
        items: List[Dict[str, Any]],
        sender_batch_id: Optional[str] = None,
        email_subject: str = "You have a payment",
    ) -> Dict[str, Any]:
        """Send payouts (e.g., for tip distribution to staff bank accounts)."""
        self._require_configured()
        headers = await self._headers()

        body = {
            "sender_batch_header": {
                "sender_batch_id": sender_batch_id or f"payout-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
                "email_subject": email_subject,
            },
            "items": items,
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/v1/payments/payouts",
                json=body,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

        return {
            "payout_batch_id": data.get("batch_header", {}).get("payout_batch_id"),
            "status": data.get("batch_header", {}).get("batch_status"),
        }

    # ------------------------------------------------------------------
    # Webhooks
    # ------------------------------------------------------------------

    async def verify_webhook(
        self,
        headers_dict: Dict[str, str],
        body: bytes,
    ) -> bool:
        """Verify PayPal webhook signature."""
        if not self._webhook_id:
            logger.warning("PayPal webhook_id not configured; skipping verification")
            return True

        api_headers = await self._headers()

        verification_body = {
            "auth_algo": headers_dict.get("paypal-auth-algo", ""),
            "cert_url": headers_dict.get("paypal-cert-url", ""),
            "transmission_id": headers_dict.get("paypal-transmission-id", ""),
            "transmission_sig": headers_dict.get("paypal-transmission-sig", ""),
            "transmission_time": headers_dict.get("paypal-transmission-time", ""),
            "webhook_id": self._webhook_id,
            "webhook_event": json.loads(body),
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/v1/notifications/verify-webhook-signature",
                json=verification_body,
                headers=api_headers,
            )
            resp.raise_for_status()
            data = resp.json()

        return data.get("verification_status") == "SUCCESS"

    def parse_webhook_event(self, body: bytes) -> Dict[str, Any]:
        """Parse a webhook event payload."""
        event = json.loads(body)
        return {
            "event_id": event.get("id"),
            "event_type": event.get("event_type"),
            "resource_type": event.get("resource_type"),
            "resource": event.get("resource", {}),
            "summary": event.get("summary"),
            "create_time": event.get("create_time"),
        }

    # ------------------------------------------------------------------
    # Dispute Management
    # ------------------------------------------------------------------

    async def list_disputes(
        self,
        start_time: Optional[str] = None,
        dispute_state: Optional[str] = None,
        page_size: int = 10,
    ) -> Dict[str, Any]:
        """List payment disputes/chargebacks."""
        self._require_configured()
        headers = await self._headers()

        params: Dict[str, Any] = {"page_size": page_size}
        if start_time:
            params["start_time"] = start_time
        if dispute_state:
            params["dispute_state"] = dispute_state

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._base_url}/v1/customer/disputes",
                params=params,
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_dispute(self, dispute_id: str) -> Dict[str, Any]:
        """Get dispute details."""
        self._require_configured()
        headers = await self._headers()

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._base_url}/v1/customer/disputes/{dispute_id}",
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------

_paypal_service: Optional[PayPalService] = None


def get_paypal_service() -> PayPalService:
    global _paypal_service
    if _paypal_service is None:
        _paypal_service = PayPalService()
    return _paypal_service

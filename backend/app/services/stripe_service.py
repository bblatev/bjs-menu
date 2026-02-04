"""Stripe Payment Gateway Integration Service."""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
import httpx

logger = logging.getLogger(__name__)


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


class PaymentMethod(str, Enum):
    CARD = "card"
    APPLE_PAY = "apple_pay"
    GOOGLE_PAY = "google_pay"
    LINK = "link"


@dataclass
class PaymentResult:
    """Result of a payment operation."""
    success: bool
    payment_id: Optional[str] = None
    client_secret: Optional[str] = None
    status: Optional[PaymentStatus] = None
    amount: Optional[int] = None  # in cents
    currency: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    receipt_url: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class RefundResult:
    """Result of a refund operation."""
    success: bool
    refund_id: Optional[str] = None
    status: Optional[str] = None
    amount: Optional[int] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class StripeService:
    """Service for Stripe payment processing."""

    STRIPE_API_BASE = "https://api.stripe.com/v1"
    API_VERSION = "2023-10-16"

    def __init__(
        self,
        secret_key: str,
        webhook_secret: Optional[str] = None,
        currency: str = "usd",
    ):
        self.secret_key = secret_key
        self.webhook_secret = webhook_secret
        self.currency = currency.lower()
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.STRIPE_API_BASE,
                auth=(self.secret_key, ""),
                headers={
                    "Stripe-Version": self.API_VERSION,
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                timeout=30.0,
            )
        return self._client

    async def create_payment_intent(
        self,
        amount: int,  # in cents
        currency: Optional[str] = None,
        customer_id: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        payment_method_types: Optional[List[str]] = None,
        capture_method: str = "automatic",  # "automatic" or "manual"
        receipt_email: Optional[str] = None,
    ) -> PaymentResult:
        """
        Create a payment intent for processing a payment.

        Args:
            amount: Amount in cents (e.g., 1000 = $10.00)
            currency: ISO currency code (default: configured currency)
            customer_id: Stripe customer ID
            description: Payment description
            metadata: Additional metadata (order_id, table_number, etc.)
            payment_method_types: Allowed payment methods
            capture_method: "automatic" for immediate capture, "manual" for auth-only
            receipt_email: Email to send receipt to
        """
        client = await self._get_client()

        data = {
            "amount": str(amount),
            "currency": currency or self.currency,
            "capture_method": capture_method,
        }

        if customer_id:
            data["customer"] = customer_id
        if description:
            data["description"] = description
        if receipt_email:
            data["receipt_email"] = receipt_email
        if payment_method_types:
            for i, pm in enumerate(payment_method_types):
                data[f"payment_method_types[{i}]"] = pm
        else:
            # Default to card + link
            data["payment_method_types[0]"] = "card"
            data["payment_method_types[1]"] = "link"
        if metadata:
            for key, value in metadata.items():
                data[f"metadata[{key}]"] = str(value)

        try:
            response = await client.post("/payment_intents", data=data)

            if response.status_code in (200, 201):
                result = response.json()
                return PaymentResult(
                    success=True,
                    payment_id=result["id"],
                    client_secret=result["client_secret"],
                    status=PaymentStatus(result["status"].replace("requires_", "").replace("_method", "")),
                    amount=result["amount"],
                    currency=result["currency"],
                    created_at=datetime.fromtimestamp(result["created"]),
                )
            else:
                error = response.json().get("error", {})
                return PaymentResult(
                    success=False,
                    error_code=error.get("code"),
                    error_message=error.get("message", f"HTTP {response.status_code}"),
                )

        except Exception as e:
            logger.error(f"Stripe create_payment_intent error: {e}")
            return PaymentResult(
                success=False,
                error_message=str(e),
            )

    async def confirm_payment_intent(
        self,
        payment_intent_id: str,
        payment_method_id: Optional[str] = None,
    ) -> PaymentResult:
        """Confirm a payment intent (server-side confirmation)."""
        client = await self._get_client()

        data = {}
        if payment_method_id:
            data["payment_method"] = payment_method_id

        try:
            response = await client.post(
                f"/payment_intents/{payment_intent_id}/confirm",
                data=data,
            )

            if response.status_code == 200:
                result = response.json()
                return PaymentResult(
                    success=result["status"] == "succeeded",
                    payment_id=result["id"],
                    status=PaymentStatus.SUCCEEDED if result["status"] == "succeeded" else PaymentStatus.PROCESSING,
                    amount=result["amount"],
                    currency=result["currency"],
                    receipt_url=result.get("charges", {}).get("data", [{}])[0].get("receipt_url"),
                )
            else:
                error = response.json().get("error", {})
                return PaymentResult(
                    success=False,
                    payment_id=payment_intent_id,
                    error_code=error.get("code"),
                    error_message=error.get("message"),
                )

        except Exception as e:
            logger.error(f"Stripe confirm_payment_intent error: {e}")
            return PaymentResult(
                success=False,
                payment_id=payment_intent_id,
                error_message=str(e),
            )

    async def capture_payment_intent(
        self,
        payment_intent_id: str,
        amount_to_capture: Optional[int] = None,
    ) -> PaymentResult:
        """Capture a previously authorized payment."""
        client = await self._get_client()

        data = {}
        if amount_to_capture:
            data["amount_to_capture"] = str(amount_to_capture)

        try:
            response = await client.post(
                f"/payment_intents/{payment_intent_id}/capture",
                data=data,
            )

            if response.status_code == 200:
                result = response.json()
                return PaymentResult(
                    success=True,
                    payment_id=result["id"],
                    status=PaymentStatus.SUCCEEDED,
                    amount=result["amount_received"],
                    currency=result["currency"],
                    receipt_url=result.get("charges", {}).get("data", [{}])[0].get("receipt_url"),
                )
            else:
                error = response.json().get("error", {})
                return PaymentResult(
                    success=False,
                    payment_id=payment_intent_id,
                    error_code=error.get("code"),
                    error_message=error.get("message"),
                )

        except Exception as e:
            logger.error(f"Stripe capture_payment_intent error: {e}")
            return PaymentResult(
                success=False,
                payment_id=payment_intent_id,
                error_message=str(e),
            )

    async def cancel_payment_intent(
        self,
        payment_intent_id: str,
        cancellation_reason: Optional[str] = None,
    ) -> PaymentResult:
        """Cancel a payment intent."""
        client = await self._get_client()

        data = {}
        if cancellation_reason:
            data["cancellation_reason"] = cancellation_reason

        try:
            response = await client.post(
                f"/payment_intents/{payment_intent_id}/cancel",
                data=data,
            )

            if response.status_code == 200:
                result = response.json()
                return PaymentResult(
                    success=True,
                    payment_id=result["id"],
                    status=PaymentStatus.CANCELED,
                )
            else:
                error = response.json().get("error", {})
                return PaymentResult(
                    success=False,
                    payment_id=payment_intent_id,
                    error_code=error.get("code"),
                    error_message=error.get("message"),
                )

        except Exception as e:
            logger.error(f"Stripe cancel_payment_intent error: {e}")
            return PaymentResult(
                success=False,
                payment_id=payment_intent_id,
                error_message=str(e),
            )

    async def get_payment_intent(self, payment_intent_id: str) -> PaymentResult:
        """Retrieve a payment intent."""
        client = await self._get_client()

        try:
            response = await client.get(f"/payment_intents/{payment_intent_id}")

            if response.status_code == 200:
                result = response.json()
                status_map = {
                    "succeeded": PaymentStatus.SUCCEEDED,
                    "canceled": PaymentStatus.CANCELED,
                    "processing": PaymentStatus.PROCESSING,
                    "requires_payment_method": PaymentStatus.PENDING,
                    "requires_confirmation": PaymentStatus.PENDING,
                    "requires_action": PaymentStatus.PENDING,
                    "requires_capture": PaymentStatus.PROCESSING,
                }
                return PaymentResult(
                    success=True,
                    payment_id=result["id"],
                    status=status_map.get(result["status"], PaymentStatus.PENDING),
                    amount=result["amount"],
                    currency=result["currency"],
                    receipt_url=result.get("charges", {}).get("data", [{}])[0].get("receipt_url"),
                    created_at=datetime.fromtimestamp(result["created"]),
                )
            else:
                error = response.json().get("error", {})
                return PaymentResult(
                    success=False,
                    error_code=error.get("code"),
                    error_message=error.get("message"),
                )

        except Exception as e:
            logger.error(f"Stripe get_payment_intent error: {e}")
            return PaymentResult(
                success=False,
                error_message=str(e),
            )

    async def create_refund(
        self,
        payment_intent_id: str,
        amount: Optional[int] = None,  # None = full refund
        reason: Optional[str] = None,  # duplicate, fraudulent, requested_by_customer
        metadata: Optional[Dict[str, str]] = None,
    ) -> RefundResult:
        """Create a refund for a payment."""
        client = await self._get_client()

        data = {"payment_intent": payment_intent_id}
        if amount:
            data["amount"] = str(amount)
        if reason:
            data["reason"] = reason
        if metadata:
            for key, value in metadata.items():
                data[f"metadata[{key}]"] = str(value)

        try:
            response = await client.post("/refunds", data=data)

            if response.status_code in (200, 201):
                result = response.json()
                return RefundResult(
                    success=True,
                    refund_id=result["id"],
                    status=result["status"],
                    amount=result["amount"],
                )
            else:
                error = response.json().get("error", {})
                return RefundResult(
                    success=False,
                    error_code=error.get("code"),
                    error_message=error.get("message"),
                )

        except Exception as e:
            logger.error(f"Stripe create_refund error: {e}")
            return RefundResult(
                success=False,
                error_message=str(e),
            )

    async def create_customer(
        self,
        email: Optional[str] = None,
        name: Optional[str] = None,
        phone: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Create a Stripe customer."""
        client = await self._get_client()

        data = {}
        if email:
            data["email"] = email
        if name:
            data["name"] = name
        if phone:
            data["phone"] = phone
        if metadata:
            for key, value in metadata.items():
                data[f"metadata[{key}]"] = str(value)

        try:
            response = await client.post("/customers", data=data)

            if response.status_code in (200, 201):
                result = response.json()
                return {
                    "success": True,
                    "customer_id": result["id"],
                    "email": result.get("email"),
                    "name": result.get("name"),
                }
            else:
                error = response.json().get("error", {})
                return {
                    "success": False,
                    "error": error.get("message"),
                }

        except Exception as e:
            logger.error(f"Stripe create_customer error: {e}")
            return {"success": False, "error": str(e)}

    async def list_payment_methods(
        self,
        customer_id: str,
        type: str = "card",
    ) -> List[Dict[str, Any]]:
        """List saved payment methods for a customer."""
        client = await self._get_client()

        try:
            response = await client.get(
                "/payment_methods",
                params={"customer": customer_id, "type": type},
            )

            if response.status_code == 200:
                result = response.json()
                return [
                    {
                        "id": pm["id"],
                        "type": pm["type"],
                        "card": {
                            "brand": pm["card"]["brand"],
                            "last4": pm["card"]["last4"],
                            "exp_month": pm["card"]["exp_month"],
                            "exp_year": pm["card"]["exp_year"],
                        } if pm.get("card") else None,
                    }
                    for pm in result.get("data", [])
                ]
            return []

        except Exception as e:
            logger.error(f"Stripe list_payment_methods error: {e}")
            return []

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        """Verify a webhook signature."""
        if not self.webhook_secret:
            logger.warning("Webhook secret not configured, skipping verification")
            return True

        import hmac
        import hashlib
        import time

        try:
            # Parse signature header
            sig_parts = {}
            for part in signature.split(","):
                key, value = part.split("=")
                sig_parts[key] = value

            timestamp = sig_parts.get("t")
            expected_sig = sig_parts.get("v1")

            if not timestamp or not expected_sig:
                return False

            # Check timestamp (allow 5 min tolerance)
            if abs(time.time() - int(timestamp)) > 300:
                logger.warning("Webhook timestamp too old")
                return False

            # Compute expected signature
            signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
            computed_sig = hmac.new(
                self.webhook_secret.encode("utf-8"),
                signed_payload.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()

            return hmac.compare_digest(computed_sig, expected_sig)

        except Exception as e:
            logger.error(f"Webhook signature verification error: {e}")
            return False

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# Singleton instance
_stripe_service: Optional[StripeService] = None


def get_stripe_service() -> Optional[StripeService]:
    """Get or create the Stripe service singleton."""
    global _stripe_service
    if _stripe_service is None:
        import os
        secret_key = os.getenv("STRIPE_SECRET_KEY")
        if secret_key:
            _stripe_service = StripeService(
                secret_key=secret_key,
                webhook_secret=os.getenv("STRIPE_WEBHOOK_SECRET"),
                currency=os.getenv("STRIPE_CURRENCY", "usd"),
            )
    return _stripe_service

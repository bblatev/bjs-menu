"""Payment Gateway Service - Stripe integration with database-backed transaction tracking.

Provides a complete Stripe payment gateway with:
- PaymentIntent creation, confirmation, and status checking
- Full and partial refunds
- Stripe Checkout sessions
- Webhook event processing with signature verification
- Stripe Terminal support (connection tokens, payment capture)
- PaymentTransaction model for persistent audit trail

The stripe library is imported conditionally so the application
can start even when the package is not installed.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    ForeignKey,
    Integer,
    String,
    Text,
    func,
    select,
)
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.config import settings
from app.db.base import Base, TimestampMixin

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Conditional stripe import
# ---------------------------------------------------------------------------
try:
    import stripe

    STRIPE_AVAILABLE = True
except ImportError:
    stripe = None  # type: ignore[assignment]
    STRIPE_AVAILABLE = False
    logger.warning(
        "stripe package is not installed. Payment gateway features will be "
        "unavailable. Install with: pip install stripe"
    )


# ============================================================================
# SQLAlchemy model
# ============================================================================


class PaymentTransaction(Base, TimestampMixin):
    """Persistent record of every payment processed through Stripe."""

    __tablename__ = "payment_transactions"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id"), index=True
    )
    stripe_payment_intent_id: Mapped[Optional[str]] = mapped_column(
        String(200), unique=True, nullable=True
    )
    stripe_charge_id: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True
    )
    amount_cents: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="usd")
    status: Mapped[str] = mapped_column(
        String(30), default="pending", index=True
    )
    payment_method: Mapped[str] = mapped_column(
        String(30)
    )  # card, apple_pay, google_pay, terminal
    check_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    guest_order_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    customer_email: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    refund_amount_cents: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, default=0
    )
    refund_id: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True
    )
    failure_reason: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    processed_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )


# ============================================================================
# Service
# ============================================================================


class PaymentGatewayService:
    """High-level Stripe gateway that wraps the ``stripe`` Python SDK.

    All public methods are synchronous because the official ``stripe``
    library uses synchronous HTTP under the hood.  Callers from async
    FastAPI routes should use ``asyncio.to_thread`` or call these methods
    directly (FastAPI handles the threadpool automatically for sync
    dependencies / ``def`` routes).
    """

    def __init__(
        self,
        secret_key: Optional[str] = None,
        webhook_secret: Optional[str] = None,
        currency: str = "usd",
    ):
        self._secret_key = secret_key or settings.stripe_secret_key
        self._webhook_secret = webhook_secret or settings.stripe_webhook_secret
        self._currency = (currency or settings.stripe_currency or "usd").lower()
        self._configured = False

        if not STRIPE_AVAILABLE:
            logger.error("stripe package not installed -- gateway disabled")
            return

        if not self._secret_key:
            logger.warning(
                "stripe_secret_key is empty -- gateway disabled. "
                "Set STRIPE_SECRET_KEY in environment."
            )
            return

        stripe.api_key = self._secret_key
        self._configured = True

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def is_configured(self) -> bool:
        return self._configured

    def _require_configured(self) -> None:
        if not STRIPE_AVAILABLE:
            raise RuntimeError(
                "stripe package is not installed. "
                "Install with: pip install stripe"
            )
        if not self._configured:
            raise RuntimeError(
                "Stripe is not configured. "
                "Set STRIPE_SECRET_KEY environment variable."
            )

    # ------------------------------------------------------------------
    # PaymentIntent
    # ------------------------------------------------------------------

    def create_payment_intent(
        self,
        amount_cents: int,
        currency: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        payment_method_types: Optional[List[str]] = None,
        customer_id: Optional[str] = None,
        receipt_email: Optional[str] = None,
        description: Optional[str] = None,
        capture_method: str = "automatic",
    ) -> Dict[str, Any]:
        """Create a Stripe PaymentIntent.

        Returns a dict with ``payment_intent_id``, ``client_secret``,
        ``status``, ``amount``, and ``currency``.
        """
        self._require_configured()

        params: Dict[str, Any] = {
            "amount": amount_cents,
            "currency": (currency or self._currency).lower(),
            "capture_method": capture_method,
            "metadata": metadata or {},
        }
        if payment_method_types:
            params["payment_method_types"] = payment_method_types
        else:
            params["automatic_payment_methods"] = {"enabled": True}
        if customer_id:
            params["customer"] = customer_id
        if receipt_email:
            params["receipt_email"] = receipt_email
        if description:
            params["description"] = description

        try:
            intent = stripe.PaymentIntent.create(**params)
            return {
                "success": True,
                "payment_intent_id": intent.id,
                "client_secret": intent.client_secret,
                "status": intent.status,
                "amount": intent.amount,
                "currency": intent.currency,
            }
        except stripe.error.StripeError as exc:
            logger.error("Stripe create_payment_intent error: %s", exc)
            return {
                "success": False,
                "error": str(exc.user_message or exc),
                "error_code": getattr(exc, "code", None),
            }

    def confirm_payment(self, payment_intent_id: str) -> Dict[str, Any]:
        """Confirm (server-side) a PaymentIntent."""
        self._require_configured()
        try:
            intent = stripe.PaymentIntent.confirm(payment_intent_id)
            return {
                "success": True,
                "payment_intent_id": intent.id,
                "status": intent.status,
                "amount": intent.amount,
                "currency": intent.currency,
            }
        except stripe.error.StripeError as exc:
            logger.error("Stripe confirm_payment error: %s", exc)
            return {
                "success": False,
                "error": str(exc.user_message or exc),
                "error_code": getattr(exc, "code", None),
            }

    def get_payment_status(self, payment_intent_id: str) -> Dict[str, Any]:
        """Retrieve the current status of a PaymentIntent."""
        self._require_configured()
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            charges = intent.get("charges", {}).get("data", [])
            charge_id = charges[0]["id"] if charges else None
            receipt_url = charges[0].get("receipt_url") if charges else None
            return {
                "success": True,
                "payment_intent_id": intent.id,
                "status": intent.status,
                "amount": intent.amount,
                "currency": intent.currency,
                "charge_id": charge_id,
                "receipt_url": receipt_url,
                "payment_method": intent.get("payment_method"),
                "created": intent.get("created"),
            }
        except stripe.error.StripeError as exc:
            logger.error("Stripe get_payment_status error: %s", exc)
            return {
                "success": False,
                "error": str(exc.user_message or exc),
                "error_code": getattr(exc, "code", None),
            }

    # ------------------------------------------------------------------
    # Refunds
    # ------------------------------------------------------------------

    def refund_payment(
        self,
        payment_intent_id: str,
        amount_cents: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Full or partial refund of a PaymentIntent.

        If ``amount_cents`` is ``None`` a full refund is issued.
        ``reason`` may be ``duplicate``, ``fraudulent``, or
        ``requested_by_customer``.
        """
        self._require_configured()
        params: Dict[str, Any] = {"payment_intent": payment_intent_id}
        if amount_cents is not None:
            params["amount"] = amount_cents
        if reason:
            params["reason"] = reason

        try:
            refund = stripe.Refund.create(**params)
            return {
                "success": True,
                "refund_id": refund.id,
                "status": refund.status,
                "amount": refund.amount,
                "currency": refund.currency,
            }
        except stripe.error.StripeError as exc:
            logger.error("Stripe refund_payment error: %s", exc)
            return {
                "success": False,
                "error": str(exc.user_message or exc),
                "error_code": getattr(exc, "code", None),
            }

    # ------------------------------------------------------------------
    # Checkout Session
    # ------------------------------------------------------------------

    def create_checkout_session(
        self,
        items: List[Dict[str, Any]],
        success_url: str,
        cancel_url: str,
        metadata: Optional[Dict[str, str]] = None,
        customer_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a Stripe Checkout Session.

        ``items`` is a list of dicts with keys ``name``, ``amount_cents``,
        ``quantity``, and optionally ``description`` / ``image_url``.
        """
        self._require_configured()

        line_items = []
        for item in items:
            li: Dict[str, Any] = {
                "price_data": {
                    "currency": self._currency,
                    "unit_amount": item["amount_cents"],
                    "product_data": {
                        "name": item["name"],
                    },
                },
                "quantity": item.get("quantity", 1),
            }
            if item.get("description"):
                li["price_data"]["product_data"]["description"] = item[
                    "description"
                ]
            if item.get("image_url"):
                li["price_data"]["product_data"]["images"] = [
                    item["image_url"]
                ]
            line_items.append(li)

        params: Dict[str, Any] = {
            "mode": "payment",
            "line_items": line_items,
            "success_url": success_url,
            "cancel_url": cancel_url,
            "metadata": metadata or {},
        }
        if customer_email:
            params["customer_email"] = customer_email

        try:
            session = stripe.checkout.Session.create(**params)
            return {
                "success": True,
                "session_id": session.id,
                "url": session.url,
            }
        except stripe.error.StripeError as exc:
            logger.error("Stripe create_checkout_session error: %s", exc)
            return {
                "success": False,
                "error": str(exc.user_message or exc),
                "error_code": getattr(exc, "code", None),
            }

    # ------------------------------------------------------------------
    # Webhook
    # ------------------------------------------------------------------

    def handle_webhook(
        self,
        payload: bytes,
        sig_header: str,
    ) -> Dict[str, Any]:
        """Verify and parse a Stripe webhook event.

        Returns a dict with ``event_type``, ``event_id``, and ``data``
        (the event object) on success, or ``error`` on failure.
        """
        self._require_configured()

        if not self._webhook_secret:
            # Fallback: parse without verification (dev only)
            logger.warning(
                "STRIPE_WEBHOOK_SECRET is not set -- skipping signature "
                "verification.  This is UNSAFE in production."
            )
            try:
                event = json.loads(payload)
            except json.JSONDecodeError as exc:
                return {"success": False, "error": f"Invalid JSON: {exc}"}
        else:
            try:
                event = stripe.Webhook.construct_event(
                    payload, sig_header, self._webhook_secret
                )
            except stripe.error.SignatureVerificationError:
                logger.warning("Webhook signature verification failed")
                return {"success": False, "error": "Invalid signature"}
            except ValueError as exc:
                logger.warning("Webhook payload invalid: %s", exc)
                return {"success": False, "error": f"Invalid payload: {exc}"}

        event_type = event.get("type") if isinstance(event, dict) else event.type
        event_id = event.get("id") if isinstance(event, dict) else event.id
        event_data = (
            event.get("data", {}).get("object", {})
            if isinstance(event, dict)
            else event.data.object
        )

        return {
            "success": True,
            "event_type": event_type,
            "event_id": event_id,
            "data": event_data,
        }

    # ------------------------------------------------------------------
    # Terminal
    # ------------------------------------------------------------------

    def create_terminal_connection_token(self) -> Dict[str, Any]:
        """Create a connection token for Stripe Terminal (card readers)."""
        self._require_configured()
        try:
            token = stripe.terminal.ConnectionToken.create()
            return {"success": True, "secret": token.secret}
        except stripe.error.StripeError as exc:
            logger.error("Stripe terminal connection token error: %s", exc)
            return {
                "success": False,
                "error": str(exc.user_message or exc),
            }

    def capture_terminal_payment(
        self, payment_intent_id: str, amount_to_capture: Optional[int] = None
    ) -> Dict[str, Any]:
        """Capture a terminal payment that was authorized with manual capture."""
        self._require_configured()
        params: Dict[str, Any] = {}
        if amount_to_capture is not None:
            params["amount_to_capture"] = amount_to_capture

        try:
            intent = stripe.PaymentIntent.capture(
                payment_intent_id, **params
            )
            return {
                "success": True,
                "payment_intent_id": intent.id,
                "status": intent.status,
                "amount_received": intent.amount_received,
                "currency": intent.currency,
            }
        except stripe.error.StripeError as exc:
            logger.error("Stripe capture_terminal_payment error: %s", exc)
            return {
                "success": False,
                "error": str(exc.user_message or exc),
                "error_code": getattr(exc, "code", None),
            }

    # ------------------------------------------------------------------
    # DB helpers (work with an externally-provided Session)
    # ------------------------------------------------------------------

    @staticmethod
    def record_transaction(
        db: Session,
        *,
        location_id: int,
        amount_cents: int,
        payment_method: str,
        currency: str = "usd",
        status: str = "pending",
        stripe_payment_intent_id: Optional[str] = None,
        stripe_charge_id: Optional[str] = None,
        check_id: Optional[int] = None,
        guest_order_id: Optional[int] = None,
        customer_email: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        processed_by: Optional[int] = None,
    ) -> PaymentTransaction:
        """Insert a PaymentTransaction row and flush (but don't commit)."""
        txn = PaymentTransaction(
            location_id=location_id,
            amount_cents=amount_cents,
            currency=currency,
            status=status,
            payment_method=payment_method,
            stripe_payment_intent_id=stripe_payment_intent_id,
            stripe_charge_id=stripe_charge_id,
            check_id=check_id,
            guest_order_id=guest_order_id,
            customer_email=customer_email,
            metadata_json=json.dumps(metadata) if metadata else None,
            processed_by=processed_by,
        )
        db.add(txn)
        db.flush()
        return txn

    @staticmethod
    def update_transaction_status(
        db: Session,
        stripe_payment_intent_id: str,
        status: str,
        charge_id: Optional[str] = None,
        failure_reason: Optional[str] = None,
    ) -> Optional[PaymentTransaction]:
        """Update an existing transaction by its Stripe PaymentIntent ID."""
        stmt = select(PaymentTransaction).where(
            PaymentTransaction.stripe_payment_intent_id
            == stripe_payment_intent_id
        )
        txn = db.execute(stmt).scalar_one_or_none()
        if txn is None:
            return None
        txn.status = status
        if charge_id:
            txn.stripe_charge_id = charge_id
        if failure_reason:
            txn.failure_reason = failure_reason
        db.flush()
        return txn

    @staticmethod
    def record_refund(
        db: Session,
        stripe_payment_intent_id: str,
        refund_id: str,
        refund_amount_cents: int,
    ) -> Optional[PaymentTransaction]:
        """Attach refund info to an existing transaction."""
        stmt = select(PaymentTransaction).where(
            PaymentTransaction.stripe_payment_intent_id
            == stripe_payment_intent_id
        )
        txn = db.execute(stmt).scalar_one_or_none()
        if txn is None:
            return None
        txn.refund_id = refund_id
        txn.refund_amount_cents = (txn.refund_amount_cents or 0) + refund_amount_cents
        # Determine if fully or partially refunded
        if txn.refund_amount_cents >= txn.amount_cents:
            txn.status = "refunded"
        else:
            txn.status = "partially_refunded"
        db.flush()
        return txn

    @staticmethod
    def get_transaction_by_intent(
        db: Session, stripe_payment_intent_id: str
    ) -> Optional[PaymentTransaction]:
        stmt = select(PaymentTransaction).where(
            PaymentTransaction.stripe_payment_intent_id
            == stripe_payment_intent_id
        )
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def list_transactions(
        db: Session,
        *,
        location_id: Optional[int] = None,
        status: Optional[str] = None,
        payment_method: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Return paginated list of PaymentTransaction rows."""
        base = select(PaymentTransaction)
        count_base = select(func.count(PaymentTransaction.id))

        if location_id is not None:
            base = base.where(
                PaymentTransaction.location_id == location_id
            )
            count_base = count_base.where(
                PaymentTransaction.location_id == location_id
            )
        if status:
            base = base.where(PaymentTransaction.status == status)
            count_base = count_base.where(
                PaymentTransaction.status == status
            )
        if payment_method:
            base = base.where(
                PaymentTransaction.payment_method == payment_method
            )
            count_base = count_base.where(
                PaymentTransaction.payment_method == payment_method
            )

        total = db.execute(count_base).scalar() or 0
        rows = (
            db.execute(
                base.order_by(PaymentTransaction.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            .scalars()
            .all()
        )
        return {"transactions": rows, "total": total}

    @staticmethod
    def get_dashboard_stats(
        db: Session,
        location_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Aggregate payment statistics for the dashboard."""
        base = select(PaymentTransaction)

        if location_id is not None:
            base = base.where(
                PaymentTransaction.location_id == location_id
            )

        # Total revenue (succeeded)
        revenue_q = select(
            func.coalesce(func.sum(PaymentTransaction.amount_cents), 0)
        ).where(PaymentTransaction.status == "succeeded")
        if location_id is not None:
            revenue_q = revenue_q.where(
                PaymentTransaction.location_id == location_id
            )
        total_revenue = db.execute(revenue_q).scalar() or 0

        # Total refunded
        refund_q = select(
            func.coalesce(func.sum(PaymentTransaction.refund_amount_cents), 0)
        ).where(
            PaymentTransaction.refund_amount_cents.isnot(None),
            PaymentTransaction.refund_amount_cents > 0,
        )
        if location_id is not None:
            refund_q = refund_q.where(
                PaymentTransaction.location_id == location_id
            )
        total_refunded = db.execute(refund_q).scalar() or 0

        # Counts by status
        count_q = (
            select(
                PaymentTransaction.status,
                func.count(PaymentTransaction.id),
            )
            .group_by(PaymentTransaction.status)
        )
        if location_id is not None:
            count_q = count_q.where(
                PaymentTransaction.location_id == location_id
            )
        status_rows = db.execute(count_q).all()
        by_status = {row[0]: row[1] for row in status_rows}

        # Counts by payment method
        method_q = (
            select(
                PaymentTransaction.payment_method,
                func.count(PaymentTransaction.id),
            )
            .group_by(PaymentTransaction.payment_method)
        )
        if location_id is not None:
            method_q = method_q.where(
                PaymentTransaction.location_id == location_id
            )
        method_rows = db.execute(method_q).all()
        by_method = {row[0]: row[1] for row in method_rows}

        # Total count
        total_count_q = select(func.count(PaymentTransaction.id))
        if location_id is not None:
            total_count_q = total_count_q.where(
                PaymentTransaction.location_id == location_id
            )
        total_count = db.execute(total_count_q).scalar() or 0

        return {
            "total_transactions": total_count,
            "total_revenue_cents": total_revenue,
            "total_refunded_cents": total_refunded,
            "net_revenue_cents": total_revenue - total_refunded,
            "by_status": by_status,
            "by_payment_method": by_method,
        }


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------
_gateway_instance: Optional[PaymentGatewayService] = None


def get_payment_gateway() -> PaymentGatewayService:
    """Return (and lazily create) the singleton PaymentGatewayService."""
    global _gateway_instance
    if _gateway_instance is None:
        _gateway_instance = PaymentGatewayService()
    return _gateway_instance

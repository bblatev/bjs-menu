"""Payment processing API routes (Stripe integration).

Provides a comprehensive set of endpoints for Stripe payment processing,
including PaymentIntent management, refunds, webhook handling, Stripe
Terminal support, transaction tracking via the ``PaymentTransaction``
model, and a management dashboard.

Existing endpoints from the original stripe_service httpx layer are
preserved alongside the new payment-gateway-based routes so both code
paths remain usable during migration.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.rbac import CurrentUser, RequireManager

from app.db.session import DbSession
from app.models.restaurant import GuestOrder
from app.services.notification_service import get_notification_service
from app.services.payment_gateway_service import (
    PaymentGatewayService,
    PaymentTransaction,
    get_payment_gateway,
)

# Keep backward-compat imports for the legacy endpoints that still use them
from app.services.stripe_service import (
    get_stripe_service,
    PaymentStatus,
    PaymentResult,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Pydantic v2 request / response schemas
# ============================================================================


class CreatePaymentIntentRequest(BaseModel):
    """Body for POST /payments/create-intent."""

    amount: int = Field(..., gt=0, description="Amount in cents")
    currency: Optional[str] = Field(None, max_length=3)
    customer_id: Optional[str] = None
    description: Optional[str] = None
    order_id: Optional[str] = None
    table_number: Optional[str] = None
    receipt_email: Optional[str] = None
    capture_method: str = Field("automatic", pattern="^(automatic|manual)$")
    payment_method_types: Optional[List[str]] = None
    location_id: Optional[int] = None
    check_id: Optional[int] = None
    guest_order_id: Optional[int] = None
    payment_method: str = Field("card", description="card, apple_pay, google_pay, terminal")


class PaymentIntentResponse(BaseModel):
    success: bool
    payment_intent_id: Optional[str] = None
    client_secret: Optional[str] = None
    status: Optional[str] = None
    amount: Optional[int] = None
    currency: Optional[str] = None
    error: Optional[str] = None
    transaction_id: Optional[int] = None


class ConfirmPaymentResponse(BaseModel):
    success: bool
    payment_intent_id: Optional[str] = None
    status: Optional[str] = None
    amount: Optional[int] = None
    currency: Optional[str] = None
    error: Optional[str] = None


class RefundRequest(BaseModel):
    amount: Optional[int] = Field(None, ge=1, description="Partial refund amount in cents; omit for full refund")
    reason: Optional[str] = Field(None, pattern="^(duplicate|fraudulent|requested_by_customer)$")


class RefundResponse(BaseModel):
    success: bool
    refund_id: Optional[str] = None
    status: Optional[str] = None
    amount: Optional[int] = None
    currency: Optional[str] = None
    error: Optional[str] = None


class PaymentStatusResponse(BaseModel):
    success: bool
    payment_intent_id: Optional[str] = None
    status: Optional[str] = None
    amount: Optional[int] = None
    currency: Optional[str] = None
    charge_id: Optional[str] = None
    receipt_url: Optional[str] = None
    payment_method: Optional[str] = None
    created: Optional[int] = None
    error: Optional[str] = None


class TransactionOut(BaseModel):
    id: int
    location_id: int
    stripe_payment_intent_id: Optional[str] = None
    stripe_charge_id: Optional[str] = None
    amount_cents: int
    currency: str
    status: str
    payment_method: str
    check_id: Optional[int] = None
    guest_order_id: Optional[int] = None
    customer_email: Optional[str] = None
    refund_amount_cents: Optional[int] = None
    refund_id: Optional[str] = None
    failure_reason: Optional[str] = None
    metadata_json: Optional[str] = None
    processed_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TransactionListResponse(BaseModel):
    transactions: List[TransactionOut]
    total: int
    limit: int
    offset: int


class TerminalConnectionTokenResponse(BaseModel):
    success: bool
    secret: Optional[str] = None
    error: Optional[str] = None


class PaymentConfigResponse(BaseModel):
    publishable_key: Optional[str] = None
    currency: str
    stripe_configured: bool


class DashboardResponse(BaseModel):
    total_transactions: int
    total_revenue_cents: int
    total_refunded_cents: int
    net_revenue_cents: int
    by_status: Dict[str, int]
    by_payment_method: Dict[str, int]


class CapturePaymentRequest(BaseModel):
    amount_to_capture: Optional[int] = None


class CreateCustomerRequest(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    customer_id: Optional[str] = None


class CustomerResponse(BaseModel):
    success: bool
    stripe_customer_id: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    error: Optional[str] = None


class PaymentMethodOut(BaseModel):
    id: str
    type: str
    brand: Optional[str] = None
    last4: Optional[str] = None
    exp_month: Optional[int] = None
    exp_year: Optional[int] = None


class CheckoutLineItem(BaseModel):
    name: str
    amount_cents: int = Field(..., gt=0)
    quantity: int = Field(1, ge=1)
    description: Optional[str] = None
    image_url: Optional[str] = None


class CreateCheckoutSessionRequest(BaseModel):
    items: List[CheckoutLineItem]
    success_url: str
    cancel_url: str
    customer_email: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None


class CheckoutSessionResponse(BaseModel):
    success: bool
    session_id: Optional[str] = None
    url: Optional[str] = None
    error: Optional[str] = None


# ============================================================================
# Helper: get gateway or return not-configured response
# ============================================================================


def _stripe_not_configured():
    """Return a structured 'not configured' response for Stripe."""
    return JSONResponse(status_code=200, content={
        "status": "not_configured",
        "message": "Stripe payment processing is not configured. Set STRIPE_SECRET_KEY in Settings > Integrations.",
        "data": None,
    })


def _gateway() -> Optional[PaymentGatewayService]:
    gw = get_payment_gateway()
    if not gw.is_configured:
        return None
    return gw


# ============================================================================
# Module overview
# ============================================================================


@router.get("/")
@limiter.limit("60/minute")
def get_payments_root(request: Request, db: DbSession):
    """Payments module overview."""
    return {
        "module": "payments",
        "status": "active",
        "endpoints": [
            "/create-intent",
            "/confirm/{payment_intent_id}",
            "/refund/{payment_intent_id}",
            "/webhook",
            "/status/{payment_intent_id}",
            "/transactions",
            "/transactions/{id}",
            "/terminal/connection-token",
            "/config",
            "/dashboard",
            # Legacy endpoints kept for backward compatibility
            "/intents",
            "/customers",
            "/terminal/readers",
        ],
    }


# ============================================================================
# NEW: Create Payment Intent (via payment_gateway_service)
# ============================================================================


@router.post("/create-intent", response_model=PaymentIntentResponse)
@limiter.limit("10/minute")
def create_payment_intent_v2(
    request: Request,
    body: CreatePaymentIntentRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    """Create a Stripe PaymentIntent and record the transaction.

    Returns the ``client_secret`` that the frontend should pass to
    ``stripe.confirmCardPayment()`` (Stripe.js / Elements).
    """
    gw = _gateway()
    if not gw:
        return _stripe_not_configured()

    metadata: Dict[str, str] = {}
    if body.order_id:
        metadata["order_id"] = body.order_id
    if body.table_number:
        metadata["table_number"] = body.table_number
    if body.check_id is not None:
        metadata["check_id"] = str(body.check_id)
    if body.guest_order_id is not None:
        metadata["guest_order_id"] = str(body.guest_order_id)

    result = gw.create_payment_intent(
        amount_cents=body.amount,
        currency=body.currency,
        metadata=metadata if metadata else None,
        payment_method_types=body.payment_method_types,
        customer_id=body.customer_id,
        receipt_email=body.receipt_email,
        description=body.description,
        capture_method=body.capture_method,
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to create payment intent"))

    # Persist transaction record
    location_id = body.location_id or current_user.venue_id or 1
    txn = PaymentGatewayService.record_transaction(
        db,
        location_id=location_id,
        amount_cents=body.amount,
        currency=(body.currency or settings.stripe_currency or "usd").lower(),
        status="pending",
        payment_method=body.payment_method,
        stripe_payment_intent_id=result["payment_intent_id"],
        check_id=body.check_id,
        guest_order_id=body.guest_order_id,
        customer_email=body.receipt_email,
        metadata=metadata if metadata else None,
        processed_by=current_user.id,
    )
    db.commit()

    return PaymentIntentResponse(
        success=True,
        payment_intent_id=result["payment_intent_id"],
        client_secret=result["client_secret"],
        status=result.get("status"),
        amount=result.get("amount"),
        currency=result.get("currency"),
        transaction_id=txn.id,
    )


# ============================================================================
# NEW: Confirm Payment
# ============================================================================


@router.post("/confirm/{payment_intent_id}", response_model=ConfirmPaymentResponse)
@limiter.limit("10/minute")
def confirm_payment(
    request: Request,
    payment_intent_id: str,
    db: DbSession,
    current_user: CurrentUser,
):
    """Server-side confirmation of a PaymentIntent.

    Typically the frontend handles confirmation via Stripe.js, but this
    endpoint is available for server-side flows.
    """
    gw = _gateway()
    if not gw:
        return _stripe_not_configured()
    result = gw.confirm_payment(payment_intent_id)

    if not result.get("success"):
        # Record failure
        PaymentGatewayService.update_transaction_status(
            db, payment_intent_id, status="failed",
            failure_reason=result.get("error"),
        )
        db.commit()
        raise HTTPException(status_code=400, detail=result.get("error", "Confirmation failed"))

    # Update transaction status
    PaymentGatewayService.update_transaction_status(
        db, payment_intent_id, status=result.get("status", "succeeded"),
    )
    db.commit()

    return ConfirmPaymentResponse(
        success=True,
        payment_intent_id=result.get("payment_intent_id"),
        status=result.get("status"),
        amount=result.get("amount"),
        currency=result.get("currency"),
    )


# ============================================================================
# NEW: Refund
# ============================================================================


@router.post("/refund/{payment_intent_id}", response_model=RefundResponse)
@limiter.limit("5/minute")
def refund_payment_v2(
    request: Request,
    payment_intent_id: str,
    db: DbSession,
    current_user: RequireManager,
    body: RefundRequest = None,
):
    """Issue a full or partial refund.

    Requires manager role. If ``amount`` is omitted a full refund is
    created.
    """
    gw = _gateway()
    if not gw:
        return _stripe_not_configured()
    result = gw.refund_payment(
        payment_intent_id=payment_intent_id,
        amount_cents=body.amount if body else None,
        reason=body.reason if body else None,
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Refund failed"))

    # Record refund in transaction table
    PaymentGatewayService.record_refund(
        db,
        stripe_payment_intent_id=payment_intent_id,
        refund_id=result["refund_id"],
        refund_amount_cents=result["amount"],
    )
    db.commit()

    return RefundResponse(
        success=True,
        refund_id=result.get("refund_id"),
        status=result.get("status"),
        amount=result.get("amount"),
        currency=result.get("currency"),
    )


# ============================================================================
# NEW: Webhook (NO AUTH -- Stripe sends it directly)
# ============================================================================


@router.post("/webhook")
@limiter.limit("60/minute")
async def stripe_webhook(
    request: Request,
    db: DbSession,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
):
    """Handle Stripe webhook events.

    This endpoint does NOT require authentication. Stripe signs the
    payload and we verify using ``STRIPE_WEBHOOK_SECRET``.

    Configure this URL in the Stripe Dashboard under Webhooks:
        ``https://your-domain.com/api/v1/payments/webhook``
    """
    gw = get_payment_gateway()

    payload = await request.body()

    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")

    # If the gateway service is configured, use its SDK-based verification.
    # Otherwise fall back to the legacy httpx-based service.
    if gw.is_configured:
        event_result = gw.handle_webhook(payload, stripe_signature)
        if not event_result.get("success"):
            raise HTTPException(status_code=400, detail=event_result.get("error", "Webhook verification failed"))

        event_type = event_result["event_type"]
        event_data = event_result["data"]
    else:
        # Fallback to legacy stripe_service
        legacy = get_stripe_service()
        if not legacy:
            return _stripe_not_configured()
        if not legacy.verify_webhook_signature(payload, stripe_signature):
            raise HTTPException(status_code=400, detail="Invalid webhook signature")
        parsed = json.loads(payload)
        event_type = parsed.get("type")
        event_data = parsed.get("data", {}).get("object", {})

    # ------------------------------------------------------------------
    # Dispatch by event type
    # ------------------------------------------------------------------
    if event_type == "payment_intent.succeeded":
        return await _handle_payment_succeeded(db, event_data)

    elif event_type == "payment_intent.payment_failed":
        return await _handle_payment_failed(db, event_data)

    elif event_type == "charge.refunded":
        return await _handle_charge_refunded(db, event_data)

    elif event_type == "charge.dispute.created":
        return await _handle_dispute_created(db, event_data)

    elif event_type == "checkout.session.completed":
        return _handle_checkout_completed(db, event_data)

    # Acknowledge any unhandled event type
    logger.info("Unhandled webhook event: %s", event_type)
    return {"received": True, "event_type": event_type}


# ============================================================================
# NEW: Get payment status
# ============================================================================


@router.get("/status/{payment_intent_id}", response_model=PaymentStatusResponse)
@limiter.limit("30/minute")
def get_payment_status_by_id(
    request: Request,
    payment_intent_id: str,
    current_user: CurrentUser,
):
    """Retrieve the current status of a PaymentIntent from Stripe."""
    gw = _gateway()
    if not gw:
        return _stripe_not_configured()
    result = gw.get_payment_status(payment_intent_id)

    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Payment not found"))

    return PaymentStatusResponse(**result)


# ============================================================================
# NEW: Transaction list & detail
# ============================================================================


@router.get("/transactions", response_model=TransactionListResponse)
@limiter.limit("60/minute")
def list_transactions(
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
    location_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    payment_method: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List payment transactions with optional filters.

    Results come from the ``payment_transactions`` table (gateway
    service model). Falls back to the legacy ``check_payments`` table
    when no gateway transactions exist yet.
    """
    try:
        data = PaymentGatewayService.list_transactions(
            db,
            location_id=location_id,
            status=status,
            payment_method=payment_method,
            limit=limit,
            offset=offset,
        )

        txns = data.get("transactions", [])

        # If no gateway transactions found, try legacy check_payments
        if not txns and not location_id and not status and not payment_method:
            try:
                return _legacy_transactions(db, limit, offset)
            except Exception as e:
                logger.warning(f"Legacy transaction fallback failed: {e}")
                return TransactionListResponse(
                    transactions=[], total=0, limit=limit, offset=offset,
                )

        items = [TransactionOut.model_validate(t) for t in txns]
        return TransactionListResponse(
            transactions=items,
            total=data.get("total", 0),
            limit=limit,
            offset=offset,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to list transactions")
        return TransactionListResponse(
            transactions=[], total=0, limit=limit, offset=offset,
        )


@router.get("/transactions/{transaction_id}", response_model=TransactionOut)
@limiter.limit("60/minute")
def get_transaction(
    request: Request,
    transaction_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Get a single payment transaction by its database ID."""
    try:
        from sqlalchemy import select as sa_select

        stmt = sa_select(PaymentTransaction).where(PaymentTransaction.id == transaction_id)
        txn = db.execute(stmt).scalar_one_or_none()
        if txn is None:
            raise HTTPException(status_code=404, detail="Transaction not found")
        return TransactionOut.model_validate(txn)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get transaction {transaction_id}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve transaction: {str(e)}")


# ============================================================================
# NEW: Terminal connection token
# ============================================================================


@router.post("/terminal/connection-token", response_model=TerminalConnectionTokenResponse)
@limiter.limit("30/minute")
def terminal_connection_token(
    request: Request,
    current_user: CurrentUser,
):
    """Create a connection token for Stripe Terminal (card reader devices)."""
    gw = _gateway()
    if not gw:
        return _stripe_not_configured()
    result = gw.create_terminal_connection_token()

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to create connection token"))

    return TerminalConnectionTokenResponse(success=True, secret=result["secret"])


# ============================================================================
# NEW: Terminal capture
# ============================================================================


@router.post("/terminal/capture/{payment_intent_id}")
@limiter.limit("10/minute")
def terminal_capture(
    request: Request,
    payment_intent_id: str,
    db: DbSession,
    current_user: CurrentUser,
    body: CapturePaymentRequest = None,
):
    """Capture a terminal payment that was authorized with manual capture."""
    gw = _gateway()
    if not gw:
        return _stripe_not_configured()
    result = gw.capture_terminal_payment(
        payment_intent_id,
        amount_to_capture=body.amount_to_capture if body else None,
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Capture failed"))

    PaymentGatewayService.update_transaction_status(
        db, payment_intent_id, status="succeeded",
    )
    db.commit()

    return result


# ============================================================================
# NEW: Config (publishable key for frontend)
# ============================================================================


@router.get("/config", response_model=PaymentConfigResponse)
@limiter.limit("60/minute")
def get_payment_config(request: Request):
    """Return the Stripe publishable key and currency for the frontend.

    This endpoint is intentionally public (no auth) so the frontend can
    initialize Stripe.js before the user logs in.
    """
    return PaymentConfigResponse(
        publishable_key=settings.stripe_publishable_key,
        currency=settings.stripe_currency or "usd",
        stripe_configured=bool(settings.stripe_secret_key),
    )


# ============================================================================
# NEW: Dashboard (aggregate stats)
# ============================================================================


@router.get("/dashboard", response_model=DashboardResponse)
@limiter.limit("30/minute")
def payment_dashboard(
    request: Request,
    db: DbSession,
    current_user: RequireManager,
    location_id: Optional[int] = Query(None),
):
    """Payment statistics dashboard. Requires manager role."""
    stats = PaymentGatewayService.get_dashboard_stats(db, location_id=location_id)
    return DashboardResponse(**stats)


# ============================================================================
# NEW: Checkout Session
# ============================================================================


@router.post("/checkout-session", response_model=CheckoutSessionResponse)
@limiter.limit("10/minute")
def create_checkout_session(
    request: Request,
    body: CreateCheckoutSessionRequest,
    current_user: CurrentUser,
):
    """Create a Stripe Checkout Session for hosted payment pages."""
    gw = _gateway()
    if not gw:
        return _stripe_not_configured()
    items = [item.model_dump() for item in body.items]
    result = gw.create_checkout_session(
        items=items,
        success_url=body.success_url,
        cancel_url=body.cancel_url,
        metadata=body.metadata,
        customer_email=body.customer_email,
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to create checkout session"))

    return CheckoutSessionResponse(
        success=True,
        session_id=result.get("session_id"),
        url=result.get("url"),
    )


# ============================================================================
# LEGACY endpoints (kept for backward compatibility)
# ============================================================================


@router.post("/intents", response_model=PaymentIntentResponse)
@limiter.limit("5/minute")
async def create_payment_intent_legacy(
    request: Request,
    current_user: CurrentUser,
    body: CreatePaymentIntentRequest,
):
    """[Legacy] Create a payment intent via the httpx-based StripeService.

    Prefer ``POST /payments/create-intent`` for new integrations.
    """
    stripe_svc = get_stripe_service()
    if not stripe_svc:
        return _stripe_not_configured()

    metadata: Dict[str, str] = {}
    if body.order_id:
        metadata["order_id"] = body.order_id
    if body.table_number:
        metadata["table_number"] = body.table_number

    result = await stripe_svc.create_payment_intent(
        amount=body.amount,
        currency=body.currency,
        customer_id=body.customer_id,
        description=body.description,
        metadata=metadata if metadata else None,
        payment_method_types=body.payment_method_types,
        capture_method=body.capture_method,
        receipt_email=body.receipt_email,
    )

    return PaymentIntentResponse(
        success=result.success,
        payment_intent_id=result.payment_id,
        client_secret=result.client_secret,
        status=result.status.value if result.status else None,
        amount=result.amount,
        currency=result.currency,
        error=result.error_message,
    )


@router.get("/intents/{payment_intent_id}", response_model=PaymentIntentResponse)
@limiter.limit("60/minute")
async def get_payment_intent_legacy(
    request: Request,
    payment_intent_id: str,
    current_user: CurrentUser,
):
    """[Legacy] Get the status of a payment intent."""
    stripe_svc = get_stripe_service()
    if not stripe_svc:
        return _stripe_not_configured()

    result = await stripe_svc.get_payment_intent(payment_intent_id)

    return PaymentIntentResponse(
        success=result.success,
        payment_intent_id=result.payment_id,
        status=result.status.value if result.status else None,
        amount=result.amount,
        currency=result.currency,
        error=result.error_message,
    )


@router.post("/intents/{payment_intent_id}/capture", response_model=PaymentIntentResponse)
@limiter.limit("5/minute")
async def capture_payment_intent_legacy(
    request: Request,
    payment_intent_id: str,
    current_user: CurrentUser,
    body: CapturePaymentRequest = None,
):
    """[Legacy] Capture a previously authorized payment."""
    stripe_svc = get_stripe_service()
    if not stripe_svc:
        return _stripe_not_configured()

    result = await stripe_svc.capture_payment_intent(
        payment_intent_id=payment_intent_id,
        amount_to_capture=body.amount_to_capture if body else None,
    )

    return PaymentIntentResponse(
        success=result.success,
        payment_intent_id=result.payment_id,
        status=result.status.value if result.status else None,
        amount=result.amount,
        currency=result.currency,
        error=result.error_message,
    )


@router.post("/intents/{payment_intent_id}/cancel", response_model=PaymentIntentResponse)
@limiter.limit("5/minute")
async def cancel_payment_intent_legacy(
    request: Request,
    payment_intent_id: str,
    current_user: RequireManager,
    reason: Optional[str] = None,
):
    """[Legacy] Cancel a payment intent."""
    stripe_svc = get_stripe_service()
    if not stripe_svc:
        return _stripe_not_configured()

    result = await stripe_svc.cancel_payment_intent(
        payment_intent_id=payment_intent_id,
        cancellation_reason=reason,
    )

    return PaymentIntentResponse(
        success=result.success,
        payment_intent_id=result.payment_id,
        status=result.status.value if result.status else None,
        error=result.error_message,
    )


@router.post("/intents/{payment_intent_id}/refund", response_model=RefundResponse)
@limiter.limit("5/minute")
async def refund_payment_legacy(
    request: Request,
    payment_intent_id: str,
    current_user: RequireManager,
    body: RefundRequest = None,
):
    """[Legacy] Create a refund via the httpx-based StripeService."""
    stripe_svc = get_stripe_service()
    if not stripe_svc:
        return _stripe_not_configured()

    result = await stripe_svc.create_refund(
        payment_intent_id=payment_intent_id,
        amount=body.amount if body else None,
        reason=body.reason if body else None,
    )

    return RefundResponse(
        success=result.success,
        refund_id=result.refund_id,
        status=result.status,
        amount=result.amount,
        error=result.error_message,
    )


@router.post("/customers", response_model=CustomerResponse)
@limiter.limit("10/minute")
async def create_customer_legacy(
    request: Request,
    current_user: CurrentUser,
    body: CreateCustomerRequest,
):
    """[Legacy] Create a Stripe customer."""
    stripe_svc = get_stripe_service()
    if not stripe_svc:
        return _stripe_not_configured()

    metadata: Dict[str, str] = {}
    if body.customer_id:
        metadata["internal_customer_id"] = body.customer_id

    result = await stripe_svc.create_customer(
        email=body.email,
        name=body.name,
        phone=body.phone,
        metadata=metadata if metadata else None,
    )

    return CustomerResponse(
        success=result.get("success", False),
        stripe_customer_id=result.get("customer_id"),
        email=result.get("email"),
        name=result.get("name"),
        error=result.get("error"),
    )


@router.get("/customers/{customer_id}/payment-methods", response_model=List[PaymentMethodOut])
@limiter.limit("60/minute")
async def list_customer_payment_methods_legacy(
    request: Request,
    customer_id: str,
    current_user: CurrentUser,
    type: str = "card",
):
    """[Legacy] List saved payment methods for a customer."""
    stripe_svc = get_stripe_service()
    if not stripe_svc:
        return _stripe_not_configured()

    methods = await stripe_svc.list_payment_methods(customer_id=customer_id, type=type)

    return [
        PaymentMethodOut(
            id=pm["id"],
            type=pm["type"],
            brand=pm.get("card", {}).get("brand") if pm.get("card") else None,
            last4=pm.get("card", {}).get("last4") if pm.get("card") else None,
            exp_month=pm.get("card", {}).get("exp_month") if pm.get("card") else None,
            exp_year=pm.get("card", {}).get("exp_year") if pm.get("card") else None,
        )
        for pm in methods
    ]


@router.get("/terminal/readers")
@limiter.limit("60/minute")
async def list_terminal_readers_legacy(request: Request, current_user: CurrentUser):
    """[Legacy] List connected Stripe Terminal readers."""
    stripe_svc = get_stripe_service()
    if not stripe_svc:
        return _stripe_not_configured()

    return {
        "readers": [],
        "message": "Terminal readers require Stripe Terminal SDK integration",
    }


@router.get("/status")
@limiter.limit("60/minute")
async def get_payment_module_status(request: Request, current_user: RequireManager):
    """[Legacy] Check if payment processing is configured and working."""
    stripe_svc = get_stripe_service()

    if not stripe_svc:
        return {
            "configured": False,
            "provider": "stripe",
            "message": "Stripe is not configured. Set STRIPE_SECRET_KEY environment variable.",
        }

    try:
        client = await stripe_svc._get_client()
        response = await client.get("/balance")

        if response.status_code == 200:
            balance = response.json()
            return {
                "configured": True,
                "provider": "stripe",
                "status": "connected",
                "currency": stripe_svc.currency,
                "available_balance": balance.get("available", [{}])[0].get("amount", 0),
            }
        else:
            return {
                "configured": True,
                "provider": "stripe",
                "status": "error",
                "message": f"API error: {response.status_code}",
            }

    except Exception as e:
        return {
            "configured": True,
            "provider": "stripe",
            "status": "error",
            "message": str(e),
        }


# ============================================================================
# Webhook handler helpers (async for WebSocket broadcasts)
# ============================================================================


async def _handle_payment_succeeded(db, event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process ``payment_intent.succeeded`` webhook event."""
    payment_intent_id = event_data.get("id")
    amount = event_data.get("amount_received")
    metadata = event_data.get("metadata", {})
    order_id = metadata.get("order_id")
    charges = event_data.get("charges", {}).get("data", [])
    charge_id = charges[0].get("id") if charges else None

    # Update PaymentTransaction
    PaymentGatewayService.update_transaction_status(
        db, payment_intent_id, status="succeeded", charge_id=charge_id,
    )

    # Update GuestOrder if linked
    if order_id:
        order = db.query(GuestOrder).filter(GuestOrder.id == int(order_id)).first()
        if order:
            order.payment_status = "paid"
            order.payment_method = "card"
            order.paid_at = datetime.now(timezone.utc)

    db.commit()
    logger.info("payment_intent.succeeded: PI=%s order=%s amount=%s", payment_intent_id, order_id, amount)

    # WebSocket broadcast
    try:
        from app.main import ws_manager
        await ws_manager.broadcast(
            {
                "event": "payment_succeeded",
                "order_id": order_id,
                "amount": amount,
                "payment_intent_id": payment_intent_id,
            },
            channel="staff-notifications",
        )
    except Exception as exc:
        logger.warning("WebSocket broadcast failed: %s", exc)

    return {"received": True, "action": "payment_succeeded", "order_id": order_id}


async def _handle_payment_failed(db, event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process ``payment_intent.payment_failed`` webhook event."""
    payment_intent_id = event_data.get("id")
    error_obj = event_data.get("last_payment_error", {})
    error_message = error_obj.get("message", "Payment failed")
    metadata = event_data.get("metadata", {})
    order_id = metadata.get("order_id")
    table_number = metadata.get("table_number")

    # Update PaymentTransaction
    PaymentGatewayService.update_transaction_status(
        db, payment_intent_id, status="failed", failure_reason=error_message,
    )

    if order_id:
        order = db.query(GuestOrder).filter(GuestOrder.id == int(order_id)).first()
        if order:
            order.payment_status = "unpaid"

    db.commit()
    logger.warning("payment_intent.payment_failed: PI=%s error=%s", payment_intent_id, error_message)

    # WebSocket
    try:
        from app.main import ws_manager
        await ws_manager.broadcast(
            {
                "event": "payment_failed",
                "order_id": order_id,
                "table_number": table_number,
                "error": error_message,
            },
            channel="staff-notifications",
        )
    except Exception as exc:
        logger.warning("WebSocket broadcast failed: %s", exc)

    # Manager alert
    try:
        notifier = get_notification_service()
        await notifier.send_manager_alert(
            alert_name="Payment Failed",
            alert_type="payment",
            message=f"Payment failed for order #{order_id} (Table {table_number}): {error_message}",
            phones=[],
            emails=[],
            send_sms=False,
            send_email=False,
        )
    except Exception as exc:
        logger.warning("Manager alert failed: %s", exc)

    return {"received": True, "action": "payment_failed", "order_id": order_id, "error": error_message}


async def _handle_charge_refunded(db, event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process ``charge.refunded`` webhook event."""
    charge_id = event_data.get("id")
    amount_refunded = event_data.get("amount_refunded")
    payment_intent_id = event_data.get("payment_intent")
    metadata = event_data.get("metadata", {})
    order_id = metadata.get("order_id")
    refunds = event_data.get("refunds", {}).get("data", [])
    refund_id = refunds[0].get("id") if refunds else None

    # Update PaymentTransaction
    if payment_intent_id and refund_id and amount_refunded:
        PaymentGatewayService.record_refund(
            db,
            stripe_payment_intent_id=payment_intent_id,
            refund_id=refund_id,
            refund_amount_cents=amount_refunded,
        )

    if order_id:
        order = db.query(GuestOrder).filter(GuestOrder.id == int(order_id)).first()
        if order:
            order.payment_status = "refunded"

    db.commit()
    logger.info("charge.refunded: charge=%s PI=%s amount=%s", charge_id, payment_intent_id, amount_refunded)

    # WebSocket
    try:
        from app.main import ws_manager
        await ws_manager.broadcast(
            {
                "event": "payment_refunded",
                "order_id": order_id,
                "amount_refunded": amount_refunded,
                "charge_id": charge_id,
            },
            channel="staff-notifications",
        )
    except Exception as exc:
        logger.warning("WebSocket broadcast failed: %s", exc)

    return {"received": True, "action": "refunded", "order_id": order_id, "amount": amount_refunded}


async def _handle_dispute_created(db, event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process ``charge.dispute.created`` webhook event."""
    dispute_id = event_data.get("id")
    amount = event_data.get("amount")
    reason = event_data.get("reason", "unknown")
    charge_id = event_data.get("charge")

    logger.warning("CHARGEBACK DISPUTE created: %s amount=%s reason=%s", dispute_id, amount, reason)

    # WebSocket alert
    try:
        from app.main import ws_manager
        await ws_manager.broadcast(
            {
                "event": "chargeback_dispute",
                "dispute_id": dispute_id,
                "amount": amount,
                "reason": reason,
                "charge_id": charge_id,
                "urgency": "high",
            },
            channel="staff-notifications",
        )
    except Exception as exc:
        logger.warning("WebSocket broadcast failed: %s", exc)

    # Manager alert
    try:
        notifier = get_notification_service()
        await notifier.send_manager_alert(
            alert_name="Chargeback Dispute",
            alert_type="chargeback",
            message=(
                f"URGENT: Chargeback dispute {dispute_id} for "
                f"${amount / 100:.2f}. Reason: {reason}. Respond within 7 days."
            ),
            phones=[],
            emails=[],
            send_sms=False,
            send_email=False,
        )
    except Exception as exc:
        logger.warning("Manager alert failed: %s", exc)

    return {"received": True, "action": "dispute_created", "dispute_id": dispute_id, "amount": amount}


def _handle_checkout_completed(db, event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process ``checkout.session.completed`` webhook event."""
    session_id = event_data.get("id")
    payment_intent_id = event_data.get("payment_intent")
    amount_total = event_data.get("amount_total")
    customer_email = event_data.get("customer_details", {}).get("email")
    metadata = event_data.get("metadata", {})

    logger.info(
        "checkout.session.completed: session=%s PI=%s amount=%s email=%s",
        session_id, payment_intent_id, amount_total, customer_email,
    )

    # Update the transaction if it exists
    if payment_intent_id:
        PaymentGatewayService.update_transaction_status(
            db, payment_intent_id, status="succeeded",
        )
        db.commit()

    return {
        "received": True,
        "action": "checkout_completed",
        "session_id": session_id,
        "payment_intent_id": payment_intent_id,
    }


# ============================================================================
# Legacy fallback helper for /transactions
# ============================================================================


def _legacy_transactions(db, limit: int, offset: int) -> TransactionListResponse:
    """Fall back to check_payments table when no gateway transactions exist."""
    try:
        from sqlalchemy import func as sa_func
        from app.models.restaurant import CheckPayment

        total = db.query(sa_func.count(CheckPayment.id)).scalar() or 0
        payments = (
            db.query(CheckPayment)
            .order_by(CheckPayment.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        items = [
            TransactionOut(
                id=p.id,
                location_id=0,
                amount_cents=int((p.amount or 0) * 100),
                currency="usd",
                status="succeeded",
                payment_method=p.payment_type or "card",
                check_id=getattr(p, 'check_id', None),
                created_at=p.created_at,
            )
            for p in payments
        ]
        return TransactionListResponse(
            transactions=items,
            total=total,
            limit=limit,
            offset=offset,
        )
    except Exception as e:
        logger.warning(f"Legacy transactions fallback failed: {e}")
        return TransactionListResponse(
            transactions=[],
            total=0,
            limit=limit,
            offset=offset,
        )

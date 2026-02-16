"""Payment processing API routes (Stripe integration)."""

import json
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict
from fastapi import APIRouter, HTTPException, Request, Header
from pydantic import BaseModel
from app.core.rate_limit import limiter
from app.core.rbac import CurrentUser, RequireManager

from app.db.session import DbSession
from app.models.restaurant import GuestOrder
from app.services.stripe_service import (
    get_stripe_service,
    PaymentStatus,
    PaymentResult,
)
from app.services.notification_service import get_notification_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class CreatePaymentIntentRequest(BaseModel):
    amount: int  # in cents
    currency: Optional[str] = None
    customer_id: Optional[str] = None
    description: Optional[str] = None
    order_id: Optional[str] = None
    table_number: Optional[str] = None
    receipt_email: Optional[str] = None
    capture_method: str = "automatic"  # "automatic" or "manual"
    payment_method_types: Optional[List[str]] = None


class PaymentIntentResponse(BaseModel):
    success: bool
    payment_intent_id: Optional[str] = None
    client_secret: Optional[str] = None
    status: Optional[str] = None
    amount: Optional[int] = None
    currency: Optional[str] = None
    error: Optional[str] = None


class CapturePaymentRequest(BaseModel):
    amount_to_capture: Optional[int] = None  # partial capture


class RefundRequest(BaseModel):
    amount: Optional[int] = None  # None = full refund
    reason: Optional[str] = None  # duplicate, fraudulent, requested_by_customer


class RefundResponse(BaseModel):
    success: bool
    refund_id: Optional[str] = None
    status: Optional[str] = None
    amount: Optional[int] = None
    error: Optional[str] = None


class CreateCustomerRequest(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    customer_id: Optional[str] = None  # Internal customer ID for metadata


class CustomerResponse(BaseModel):
    success: bool
    stripe_customer_id: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    error: Optional[str] = None


class PaymentMethodResponse(BaseModel):
    id: str
    type: str
    brand: Optional[str] = None
    last4: Optional[str] = None
    exp_month: Optional[int] = None
    exp_year: Optional[int] = None


# ============================================================================
# Payment Intents
# ============================================================================

@router.get("/")
@limiter.limit("60/minute")
def get_payments_root(request: Request, db: DbSession):
    """Payments module overview."""
    return {"module": "payments", "status": "active", "endpoints": ["/status", "/intents", "/customers", "/terminal", "/transactions"]}


@router.post("/intents", response_model=PaymentIntentResponse)
@limiter.limit("5/minute")
async def create_payment_intent(request: Request, current_user: CurrentUser, body: CreatePaymentIntentRequest):
    """
    Create a payment intent for processing a payment.

    The client_secret returned should be used with Stripe.js on the frontend
    to complete the payment.

    Rate limited to 5 requests per minute per IP.
    """
    stripe = get_stripe_service()
    if not stripe:
        raise HTTPException(
            status_code=503,
            detail="Stripe is not configured. Set STRIPE_SECRET_KEY environment variable.",
        )

    metadata = {}
    if body.order_id:
        metadata["order_id"] = body.order_id
    if body.table_number:
        metadata["table_number"] = body.table_number

    result = await stripe.create_payment_intent(
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
async def get_payment_intent(request: Request, payment_intent_id: str, current_user: CurrentUser):
    """Get the status of a payment intent."""
    stripe = get_stripe_service()
    if not stripe:
        raise HTTPException(status_code=503, detail="Stripe not configured")

    result = await stripe.get_payment_intent(payment_intent_id)

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
async def capture_payment_intent(request: Request, payment_intent_id: str, current_user: CurrentUser, body: CapturePaymentRequest = None):
    """
    Capture a previously authorized payment.

    Only needed if capture_method was set to "manual" when creating the intent.
    """
    stripe = get_stripe_service()
    if not stripe:
        raise HTTPException(status_code=503, detail="Stripe not configured")

    result = await stripe.capture_payment_intent(
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
async def cancel_payment_intent(
    request: Request,
    payment_intent_id: str,
    current_user: RequireManager,
    reason: Optional[str] = None,
):
    """Cancel a payment intent."""
    stripe = get_stripe_service()
    if not stripe:
        raise HTTPException(status_code=503, detail="Stripe not configured")

    result = await stripe.cancel_payment_intent(
        payment_intent_id=payment_intent_id,
        cancellation_reason=reason,
    )

    return PaymentIntentResponse(
        success=result.success,
        payment_intent_id=result.payment_id,
        status=result.status.value if result.status else None,
        error=result.error_message,
    )


# ============================================================================
# Refunds
# ============================================================================

@router.post("/intents/{payment_intent_id}/refund", response_model=RefundResponse)
@limiter.limit("5/minute")
async def refund_payment(request: Request, payment_intent_id: str, current_user: RequireManager, body: RefundRequest = None):
    """
    Create a refund for a payment.

    If amount is not specified, creates a full refund.
    """
    stripe = get_stripe_service()
    if not stripe:
        raise HTTPException(status_code=503, detail="Stripe not configured")

    result = await stripe.create_refund(
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


# ============================================================================
# Customers
# ============================================================================

@router.post("/customers", response_model=CustomerResponse)
@limiter.limit("10/minute")
async def create_customer(request: Request, current_user: CurrentUser, body: CreateCustomerRequest):
    """Create a Stripe customer for saving payment methods."""
    stripe = get_stripe_service()
    if not stripe:
        raise HTTPException(status_code=503, detail="Stripe not configured")

    metadata = {}
    if body.customer_id:
        metadata["internal_customer_id"] = body.customer_id

    result = await stripe.create_customer(
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


@router.get("/customers/{customer_id}/payment-methods", response_model=List[PaymentMethodResponse])
@limiter.limit("60/minute")
async def list_customer_payment_methods(request: Request, customer_id: str, current_user: CurrentUser, type: str = "card"):
    """List saved payment methods for a customer."""
    stripe = get_stripe_service()
    if not stripe:
        raise HTTPException(status_code=503, detail="Stripe not configured")

    methods = await stripe.list_payment_methods(customer_id=customer_id, type=type)

    return [
        PaymentMethodResponse(
            id=pm["id"],
            type=pm["type"],
            brand=pm.get("card", {}).get("brand") if pm.get("card") else None,
            last4=pm.get("card", {}).get("last4") if pm.get("card") else None,
            exp_month=pm.get("card", {}).get("exp_month") if pm.get("card") else None,
            exp_year=pm.get("card", {}).get("exp_year") if pm.get("card") else None,
        )
        for pm in methods
    ]


# ============================================================================
# Webhooks
# ============================================================================

@router.post("/webhook")
@limiter.limit("30/minute")
async def stripe_webhook(
    request: Request,
    db: DbSession,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
):
    """
    Handle Stripe webhook events.

    Configure this URL in Stripe Dashboard -> Webhooks:
    https://your-domain.com/api/v1/payments/webhook
    """
    stripe = get_stripe_service()
    if not stripe:
        raise HTTPException(status_code=503, detail="Stripe not configured")

    payload = await request.body()

    # Verify signature - MUST be present and valid
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")
    if not stripe.verify_webhook_signature(payload, stripe_signature):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    event = json.loads(payload)

    event_type = event.get("type")
    event_data = event.get("data", {}).get("object", {})

    # Handle different event types
    if event_type == "payment_intent.succeeded":
        payment_intent_id = event_data.get("id")
        amount = event_data.get("amount_received")
        metadata = event_data.get("metadata", {})
        order_id = metadata.get("order_id")

        # Update order payment status in database
        if order_id:
            order = db.query(GuestOrder).filter(GuestOrder.id == int(order_id)).first()
            if order:
                order.payment_status = "paid"
                order.payment_method = "card"
                order.paid_at = datetime.now(timezone.utc)
                db.commit()
                logger.info(f"Order {order_id} marked as paid via webhook (PI: {payment_intent_id})")

        # Broadcast to staff via WebSocket
        try:
            from app.main import ws_manager
            await ws_manager.broadcast({
                "event": "payment_succeeded",
                "order_id": order_id,
                "amount": amount,
                "payment_intent_id": payment_intent_id,
            }, channel="staff-notifications")
        except Exception as e:
            logger.warning(f"WebSocket broadcast failed: {e}")

        return {"received": True, "action": "payment_succeeded", "order_id": order_id}

    elif event_type == "payment_intent.payment_failed":
        payment_intent_id = event_data.get("id")
        error = event_data.get("last_payment_error", {})
        error_message = error.get("message", "Payment failed")
        metadata = event_data.get("metadata", {})
        order_id = metadata.get("order_id")
        table_number = metadata.get("table_number")

        # Update order status
        if order_id:
            order = db.query(GuestOrder).filter(GuestOrder.id == int(order_id)).first()
            if order:
                order.payment_status = "unpaid"
                db.commit()

        # Notify staff via WebSocket
        try:
            from app.main import ws_manager
            await ws_manager.broadcast({
                "event": "payment_failed",
                "order_id": order_id,
                "table_number": table_number,
                "error": error_message,
            }, channel="staff-notifications")
        except Exception as e:
            logger.warning(f"WebSocket broadcast failed: {e}")

        # Send manager alert for failed payments
        try:
            notifier = get_notification_service()
            await notifier.send_manager_alert(
                alert_name="Payment Failed",
                alert_type="payment",
                message=f"Payment failed for order #{order_id} (Table {table_number}): {error_message}",
                phones=[], emails=[],
                send_sms=False, send_email=False,
            )
        except Exception as e:
            logger.warning(f"Manager alert failed: {e}")

        return {"received": True, "action": "payment_failed", "order_id": order_id, "error": error_message}

    elif event_type == "charge.refunded":
        charge_id = event_data.get("id")
        amount_refunded = event_data.get("amount_refunded")
        payment_intent_id = event_data.get("payment_intent")
        metadata = event_data.get("metadata", {})
        order_id = metadata.get("order_id")

        # Update order payment status to refunded
        if order_id:
            order = db.query(GuestOrder).filter(GuestOrder.id == int(order_id)).first()
            if order:
                order.payment_status = "refunded"
                db.commit()
                logger.info(f"Order {order_id} marked as refunded (amount: {amount_refunded})")

        # Notify staff
        try:
            from app.main import ws_manager
            await ws_manager.broadcast({
                "event": "payment_refunded",
                "order_id": order_id,
                "amount_refunded": amount_refunded,
                "charge_id": charge_id,
            }, channel="staff-notifications")
        except Exception as e:
            logger.warning(f"WebSocket broadcast failed: {e}")

        return {"received": True, "action": "refunded", "order_id": order_id, "amount": amount_refunded}

    elif event_type == "charge.dispute.created":
        dispute_id = event_data.get("id")
        amount = event_data.get("amount")
        reason = event_data.get("reason", "unknown")
        charge_id = event_data.get("charge")

        logger.warning(f"CHARGEBACK DISPUTE created: {dispute_id}, amount={amount}, reason={reason}")

        # Alert management via WebSocket
        try:
            from app.main import ws_manager
            await ws_manager.broadcast({
                "event": "chargeback_dispute",
                "dispute_id": dispute_id,
                "amount": amount,
                "reason": reason,
                "charge_id": charge_id,
                "urgency": "high",
            }, channel="staff-notifications")
        except Exception as e:
            logger.warning(f"WebSocket broadcast failed: {e}")

        # Send manager alert
        try:
            notifier = get_notification_service()
            await notifier.send_manager_alert(
                alert_name="Chargeback Dispute",
                alert_type="chargeback",
                message=f"URGENT: Chargeback dispute {dispute_id} for ${amount/100:.2f}. Reason: {reason}. Respond within 7 days.",
                phones=[], emails=[],
                send_sms=False, send_email=False,
            )
        except Exception as e:
            logger.warning(f"Manager alert failed: {e}")

        return {"received": True, "action": "dispute_created", "dispute_id": dispute_id, "amount": amount}

    # Acknowledge other events
    return {"received": True, "event_type": event_type}


# ============================================================================
# Terminal / Reader (for physical card terminals)
# ============================================================================

@router.get("/terminal/readers")
@limiter.limit("60/minute")
async def list_terminal_readers(request: Request, current_user: CurrentUser):
    """List connected Stripe Terminal readers."""
    stripe = get_stripe_service()
    if not stripe:
        raise HTTPException(status_code=503, detail="Stripe not configured")

    # This would require Stripe Terminal SDK integration
    # Placeholder for now
    return {
        "readers": [],
        "message": "Terminal readers require Stripe Terminal SDK integration",
    }


@router.post("/terminal/connection-token")
@limiter.limit("30/minute")
async def create_terminal_connection_token(request: Request, current_user: CurrentUser):
    """Create a connection token for Stripe Terminal."""
    stripe = get_stripe_service()
    if not stripe:
        raise HTTPException(status_code=503, detail="Stripe not configured")

    # This requires calling Stripe's /terminal/connection_tokens endpoint
    client = await stripe._get_client()

    try:
        response = await client.post("/terminal/connection_tokens")
        if response.status_code == 200:
            result = response.json()
            return {"secret": result.get("secret")}
        else:
            raise HTTPException(status_code=response.status_code, detail="Failed to create connection token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Configuration Status
# ============================================================================

@router.get("/status")
@limiter.limit("60/minute")
async def get_payment_status(request: Request, current_user: RequireManager):
    """Check if payment processing is configured and working."""
    stripe = get_stripe_service()

    if not stripe:
        return {
            "configured": False,
            "provider": "stripe",
            "message": "Stripe is not configured. Set STRIPE_SECRET_KEY environment variable.",
        }

    # Try a simple API call to verify credentials
    try:
        client = await stripe._get_client()
        response = await client.get("/balance")

        if response.status_code == 200:
            balance = response.json()
            return {
                "configured": True,
                "provider": "stripe",
                "status": "connected",
                "currency": stripe.currency,
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


@router.get("/transactions")
@limiter.limit("60/minute")
def get_payment_transactions(
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
    limit: int = 50,
    offset: int = 0,
):
    """Get payment transactions from check_payments table."""
    from sqlalchemy import func
    from app.models.restaurant import CheckPayment

    total = db.query(func.count(CheckPayment.id)).scalar() or 0
    payments = db.query(CheckPayment).order_by(
        CheckPayment.created_at.desc()
    ).offset(offset).limit(limit).all()

    transactions = [
        {
            "id": p.id,
            "check_id": p.check_id,
            "type": p.payment_type,
            "amount": float(p.amount or 0),
            "tip": float(p.tip or 0),
            "card_last_four": p.card_last_four,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in payments
    ]
    return {"transactions": transactions, "total": total, "limit": limit, "offset": offset}

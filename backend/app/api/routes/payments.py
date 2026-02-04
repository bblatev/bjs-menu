"""Payment processing API routes (Stripe integration)."""

from typing import Optional, List, Dict
from fastapi import APIRouter, HTTPException, Request, Header
from pydantic import BaseModel

from app.services.stripe_service import (
    get_stripe_service,
    PaymentStatus,
    PaymentResult,
)

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

@router.post("/intents", response_model=PaymentIntentResponse)
async def create_payment_intent(request: CreatePaymentIntentRequest):
    """
    Create a payment intent for processing a payment.

    The client_secret returned should be used with Stripe.js on the frontend
    to complete the payment.
    """
    stripe = get_stripe_service()
    if not stripe:
        raise HTTPException(
            status_code=503,
            detail="Stripe is not configured. Set STRIPE_SECRET_KEY environment variable.",
        )

    metadata = {}
    if request.order_id:
        metadata["order_id"] = request.order_id
    if request.table_number:
        metadata["table_number"] = request.table_number

    result = await stripe.create_payment_intent(
        amount=request.amount,
        currency=request.currency,
        customer_id=request.customer_id,
        description=request.description,
        metadata=metadata if metadata else None,
        payment_method_types=request.payment_method_types,
        capture_method=request.capture_method,
        receipt_email=request.receipt_email,
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
async def get_payment_intent(payment_intent_id: str):
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
async def capture_payment_intent(payment_intent_id: str, request: CapturePaymentRequest):
    """
    Capture a previously authorized payment.

    Only needed if capture_method was set to "manual" when creating the intent.
    """
    stripe = get_stripe_service()
    if not stripe:
        raise HTTPException(status_code=503, detail="Stripe not configured")

    result = await stripe.capture_payment_intent(
        payment_intent_id=payment_intent_id,
        amount_to_capture=request.amount_to_capture,
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
async def cancel_payment_intent(
    payment_intent_id: str,
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
async def refund_payment(payment_intent_id: str, request: RefundRequest):
    """
    Create a refund for a payment.

    If amount is not specified, creates a full refund.
    """
    stripe = get_stripe_service()
    if not stripe:
        raise HTTPException(status_code=503, detail="Stripe not configured")

    result = await stripe.create_refund(
        payment_intent_id=payment_intent_id,
        amount=request.amount,
        reason=request.reason,
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
async def create_customer(request: CreateCustomerRequest):
    """Create a Stripe customer for saving payment methods."""
    stripe = get_stripe_service()
    if not stripe:
        raise HTTPException(status_code=503, detail="Stripe not configured")

    metadata = {}
    if request.customer_id:
        metadata["internal_customer_id"] = request.customer_id

    result = await stripe.create_customer(
        email=request.email,
        name=request.name,
        phone=request.phone,
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
async def list_customer_payment_methods(customer_id: str, type: str = "card"):
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
async def stripe_webhook(
    request: Request,
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

    # Verify signature
    if stripe_signature and not stripe.verify_webhook_signature(payload, stripe_signature):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    import json
    event = json.loads(payload)

    event_type = event.get("type")
    event_data = event.get("data", {}).get("object", {})

    # Handle different event types
    if event_type == "payment_intent.succeeded":
        # Payment successful
        payment_intent_id = event_data.get("id")
        amount = event_data.get("amount_received")
        metadata = event_data.get("metadata", {})
        order_id = metadata.get("order_id")

        # TODO: Update order status in database
        # await update_order_payment_status(order_id, "paid", payment_intent_id)

        return {"received": True, "action": "payment_succeeded", "order_id": order_id}

    elif event_type == "payment_intent.payment_failed":
        # Payment failed
        payment_intent_id = event_data.get("id")
        error = event_data.get("last_payment_error", {})
        error_message = error.get("message", "Payment failed")

        # TODO: Notify staff or update order status
        return {"received": True, "action": "payment_failed", "error": error_message}

    elif event_type == "charge.refunded":
        # Refund processed
        charge_id = event_data.get("id")
        amount_refunded = event_data.get("amount_refunded")

        # TODO: Update order status
        return {"received": True, "action": "refunded", "amount": amount_refunded}

    elif event_type == "charge.dispute.created":
        # Chargeback/dispute
        dispute_id = event_data.get("id")
        amount = event_data.get("amount")

        # TODO: Alert management
        return {"received": True, "action": "dispute_created", "amount": amount}

    # Acknowledge other events
    return {"received": True, "event_type": event_type}


# ============================================================================
# Terminal / Reader (for physical card terminals)
# ============================================================================

@router.get("/terminal/readers")
async def list_terminal_readers():
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
async def create_terminal_connection_token():
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
async def get_payment_status():
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

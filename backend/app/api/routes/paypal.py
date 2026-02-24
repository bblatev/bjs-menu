"""PayPal payment gateway API routes.

Provides endpoints for PayPal Checkout integration:
- Order creation and capture
- Refunds
- Webhook processing
- Subscription management
- Dispute listing
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request, Header
from pydantic import BaseModel, Field

from app.core.rate_limit import limiter
from app.core.rbac import CurrentUser, RequireManager
from app.services.paypal_service import get_paypal_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ---- Schemas ----

class CreatePayPalOrderRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Amount in currency units")
    currency: Optional[str] = "USD"
    description: Optional[str] = None
    return_url: str = Field(..., description="URL to redirect after payment approval")
    cancel_url: str = Field(..., description="URL to redirect if payment cancelled")
    reference_id: Optional[str] = None
    custom_id: Optional[str] = None
    intent: str = Field("CAPTURE", pattern="^(CAPTURE|AUTHORIZE)$")


class CaptureOrderRequest(BaseModel):
    order_id: str


class RefundRequest(BaseModel):
    capture_id: str
    amount: Optional[float] = None
    currency: Optional[str] = "USD"
    note: Optional[str] = None


class CreateSubscriptionRequest(BaseModel):
    plan_id: str
    subscriber_email: str
    subscriber_name: Optional[str] = None
    return_url: str
    cancel_url: str
    custom_id: Optional[str] = None


class PayoutItemRequest(BaseModel):
    recipient_email: str
    amount: float
    currency: str = "USD"
    note: Optional[str] = None


class CreatePayoutRequest(BaseModel):
    items: List[PayoutItemRequest]
    email_subject: str = "You have a payment"


# ---- Routes ----

@router.get("/")
@limiter.limit("60/minute")
async def paypal_overview(request: Request):
    """PayPal integration status."""
    svc = get_paypal_service()
    return {
        "provider": "paypal",
        "configured": svc.is_configured,
        "endpoints": [
            "POST /paypal/orders - Create checkout order",
            "POST /paypal/orders/capture - Capture approved order",
            "POST /paypal/orders/authorize - Authorize order",
            "GET /paypal/orders/{order_id} - Get order details",
            "POST /paypal/refunds - Refund a captured payment",
            "POST /paypal/subscriptions - Create subscription",
            "POST /paypal/payouts - Send payouts",
            "POST /paypal/webhooks - Webhook handler",
            "GET /paypal/disputes - List disputes",
        ],
    }


@router.post("/orders")
@limiter.limit("30/minute")
async def create_order(request: Request, body: CreatePayPalOrderRequest, user: CurrentUser):
    """Create a PayPal checkout order."""
    svc = get_paypal_service()
    try:
        result = await svc.create_order(
            amount=body.amount,
            currency=body.currency,
            description=body.description,
            return_url=body.return_url,
            cancel_url=body.cancel_url,
            reference_id=body.reference_id,
            custom_id=body.custom_id,
            intent=body.intent,
        )
        return {"success": True, **result}
    except Exception as e:
        logger.error(f"PayPal order creation failed: {e}")
        raise HTTPException(status_code=502, detail=f"PayPal error: {str(e)}")


@router.post("/orders/capture")
@limiter.limit("30/minute")
async def capture_order(request: Request, body: CaptureOrderRequest, user: CurrentUser):
    """Capture an approved PayPal order."""
    svc = get_paypal_service()
    try:
        result = await svc.capture_order(body.order_id)
        return {"success": True, **result}
    except Exception as e:
        logger.error(f"PayPal capture failed: {e}")
        raise HTTPException(status_code=502, detail=f"PayPal error: {str(e)}")


@router.post("/orders/authorize")
@limiter.limit("30/minute")
async def authorize_order(request: Request, body: CaptureOrderRequest, user: CurrentUser):
    """Authorize a PayPal order for manual capture later."""
    svc = get_paypal_service()
    try:
        result = await svc.authorize_order(body.order_id)
        return {"success": True, **result}
    except Exception as e:
        logger.error(f"PayPal authorization failed: {e}")
        raise HTTPException(status_code=502, detail=f"PayPal error: {str(e)}")


@router.get("/orders/{order_id}")
@limiter.limit("60/minute")
async def get_order(request: Request, order_id: str, user: CurrentUser):
    """Get PayPal order details."""
    svc = get_paypal_service()
    try:
        result = await svc.get_order(order_id)
        return {"success": True, "order": result}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"PayPal error: {str(e)}")


@router.post("/refunds")
@limiter.limit("20/minute")
async def refund_payment(request: Request, body: RefundRequest, user: RequireManager):
    """Refund a captured PayPal payment (full or partial)."""
    svc = get_paypal_service()
    try:
        result = await svc.refund_capture(
            capture_id=body.capture_id,
            amount=body.amount,
            currency=body.currency,
            note=body.note,
        )
        return {"success": True, **result}
    except Exception as e:
        logger.error(f"PayPal refund failed: {e}")
        raise HTTPException(status_code=502, detail=f"PayPal error: {str(e)}")


@router.post("/subscriptions")
@limiter.limit("10/minute")
async def create_subscription(request: Request, body: CreateSubscriptionRequest, user: RequireManager):
    """Create a PayPal subscription."""
    svc = get_paypal_service()
    subscriber = {"email_address": body.subscriber_email}
    if body.subscriber_name:
        parts = body.subscriber_name.split(" ", 1)
        subscriber["name"] = {
            "given_name": parts[0],
            "surname": parts[1] if len(parts) > 1 else "",
        }
    try:
        result = await svc.create_subscription(
            plan_id=body.plan_id,
            subscriber=subscriber,
            return_url=body.return_url,
            cancel_url=body.cancel_url,
            custom_id=body.custom_id,
        )
        return {"success": True, **result}
    except Exception as e:
        logger.error(f"PayPal subscription creation failed: {e}")
        raise HTTPException(status_code=502, detail=f"PayPal error: {str(e)}")


@router.post("/payouts")
@limiter.limit("10/minute")
async def create_payout(request: Request, body: CreatePayoutRequest, user: RequireManager):
    """Send PayPal payouts to staff (e.g. tip distribution)."""
    svc = get_paypal_service()
    items = [
        {
            "recipient_type": "EMAIL",
            "receiver": item.recipient_email,
            "amount": {"value": f"{item.amount:.2f}", "currency": item.currency},
            "note": item.note or "Payment from BJS Menu",
        }
        for item in body.items
    ]
    try:
        result = await svc.create_payout(items=items, email_subject=body.email_subject)
        return {"success": True, **result}
    except Exception as e:
        logger.error(f"PayPal payout failed: {e}")
        raise HTTPException(status_code=502, detail=f"PayPal error: {str(e)}")


@router.post("/webhooks")
async def handle_webhook(request: Request):
    """Handle PayPal webhook events."""
    svc = get_paypal_service()
    body = await request.body()
    headers_dict = dict(request.headers)

    try:
        verified = await svc.verify_webhook(headers_dict, body)
        if not verified:
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

        event = svc.parse_webhook_event(body)
        event_type = event.get("event_type", "")
        logger.info(f"PayPal webhook: {event_type} (ID: {event.get('event_id')})")

        # Process known event types
        if event_type == "CHECKOUT.ORDER.APPROVED":
            logger.info(f"Order approved: {event['resource'].get('id')}")
        elif event_type == "PAYMENT.CAPTURE.COMPLETED":
            logger.info(f"Payment captured: {event['resource'].get('id')}")
        elif event_type == "PAYMENT.CAPTURE.REFUNDED":
            logger.info(f"Payment refunded: {event['resource'].get('id')}")
        elif event_type.startswith("CUSTOMER.DISPUTE"):
            logger.warning(f"Dispute event: {event_type}")
        elif event_type.startswith("BILLING.SUBSCRIPTION"):
            logger.info(f"Subscription event: {event_type}")

        return {"status": "processed", "event_id": event.get("event_id")}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/disputes")
@limiter.limit("20/minute")
async def list_disputes(
    request: Request,
    user: RequireManager,
    dispute_state: Optional[str] = None,
    page_size: int = 10,
):
    """List PayPal payment disputes/chargebacks."""
    svc = get_paypal_service()
    try:
        result = await svc.list_disputes(
            dispute_state=dispute_state,
            page_size=page_size,
        )
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"PayPal error: {str(e)}")

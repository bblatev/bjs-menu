"""Square payment gateway API routes.

Provides endpoints for Square Payments integration:
- Payment creation, completion, and cancellation
- Order management
- Refunds
- Customer management
- Terminal checkout
- Catalog sync
- Webhook processing
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.rate_limit import limiter
from app.core.rbac import CurrentUser, RequireManager
from app.services.square_service import get_square_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ---- Schemas ----

class CreateSquarePaymentRequest(BaseModel):
    amount_cents: int = Field(..., gt=0)
    source_id: str = Field(..., description="Payment source nonce, card ID, or token")
    currency: str = "USD"
    order_id: Optional[str] = None
    customer_id: Optional[str] = None
    reference_id: Optional[str] = None
    note: Optional[str] = None
    tip_cents: int = 0
    autocomplete: bool = True


class SquareRefundRequest(BaseModel):
    payment_id: str
    amount_cents: Optional[int] = None
    currency: str = "USD"
    reason: Optional[str] = None


class SquareOrderLineItem(BaseModel):
    name: str
    quantity: str = "1"
    base_price_cents: int
    currency: str = "USD"
    note: Optional[str] = None


class CreateSquareOrderRequest(BaseModel):
    line_items: List[SquareOrderLineItem]
    customer_id: Optional[str] = None
    reference_id: Optional[str] = None


class CreateSquareCustomerRequest(BaseModel):
    given_name: str
    family_name: str = ""
    email: Optional[str] = None
    phone: Optional[str] = None
    reference_id: Optional[str] = None


class TerminalCheckoutRequest(BaseModel):
    amount_cents: int = Field(..., gt=0)
    currency: str = "USD"
    device_id: Optional[str] = None
    note: Optional[str] = None
    reference_id: Optional[str] = None


class CatalogItemRequest(BaseModel):
    name: str
    price_cents: int
    currency: str = "USD"
    description: Optional[str] = None
    category_id: Optional[str] = None
    item_id: Optional[str] = None


# ---- Routes ----

@router.get("/")
@limiter.limit("60/minute")
async def square_overview(request: Request):
    """Square integration status."""
    svc = get_square_service()
    return {
        "provider": "square",
        "configured": svc.is_configured,
        "endpoints": [
            "POST /square/payments - Create payment",
            "POST /square/payments/{id}/complete - Complete payment",
            "POST /square/payments/{id}/cancel - Cancel payment",
            "GET /square/payments/{id} - Get payment details",
            "GET /square/payments - List payments",
            "POST /square/refunds - Refund payment",
            "POST /square/orders - Create order",
            "POST /square/customers - Create customer",
            "POST /square/customers/search - Search customers",
            "POST /square/terminal/checkout - Terminal checkout",
            "POST /square/catalog/items - Upsert catalog item",
            "GET /square/catalog - List catalog",
            "POST /square/webhooks - Webhook handler",
        ],
    }


# ---- Payments ----

@router.post("/payments")
@limiter.limit("30/minute")
async def create_payment(request: Request, body: CreateSquarePaymentRequest, user: CurrentUser):
    """Create a Square payment."""
    svc = get_square_service()
    try:
        result = await svc.create_payment(
            amount_cents=body.amount_cents,
            source_id=body.source_id,
            currency=body.currency,
            order_id=body.order_id,
            customer_id=body.customer_id,
            reference_id=body.reference_id,
            note=body.note,
            tip_cents=body.tip_cents,
            autocomplete=body.autocomplete,
        )
        return {"success": True, **result}
    except Exception as e:
        logger.error(f"Square payment failed: {e}")
        raise HTTPException(status_code=502, detail=f"Square error: {str(e)}")


@router.post("/payments/{payment_id}/complete")
@limiter.limit("30/minute")
async def complete_payment(request: Request, payment_id: str, user: CurrentUser):
    """Complete a delayed-capture Square payment."""
    svc = get_square_service()
    try:
        result = await svc.complete_payment(payment_id)
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Square error: {str(e)}")


@router.post("/payments/{payment_id}/cancel")
@limiter.limit("30/minute")
async def cancel_payment(request: Request, payment_id: str, user: CurrentUser):
    """Cancel a pending Square payment."""
    svc = get_square_service()
    try:
        result = await svc.cancel_payment(payment_id)
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Square error: {str(e)}")


@router.get("/payments/{payment_id}")
@limiter.limit("60/minute")
async def get_payment(request: Request, payment_id: str, user: CurrentUser):
    """Get Square payment details."""
    svc = get_square_service()
    try:
        result = await svc.get_payment(payment_id)
        return {"success": True, "payment": result}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Square error: {str(e)}")


@router.get("/payments")
@limiter.limit("30/minute")
async def list_payments(
    request: Request,
    user: CurrentUser,
    begin_time: Optional[str] = None,
    end_time: Optional[str] = None,
    sort_order: str = "DESC",
    limit: int = 50,
):
    """List Square payments."""
    svc = get_square_service()
    try:
        result = await svc.list_payments(
            begin_time=begin_time,
            end_time=end_time,
            sort_order=sort_order,
            limit=limit,
        )
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Square error: {str(e)}")


# ---- Refunds ----

@router.post("/refunds")
@limiter.limit("20/minute")
async def refund_payment(request: Request, body: SquareRefundRequest, user: RequireManager):
    """Refund a Square payment (full or partial)."""
    svc = get_square_service()
    try:
        result = await svc.refund_payment(
            payment_id=body.payment_id,
            amount_cents=body.amount_cents,
            currency=body.currency,
            reason=body.reason,
        )
        return {"success": True, **result}
    except Exception as e:
        logger.error(f"Square refund failed: {e}")
        raise HTTPException(status_code=502, detail=f"Square error: {str(e)}")


# ---- Orders ----

@router.post("/orders")
@limiter.limit("30/minute")
async def create_order(request: Request, body: CreateSquareOrderRequest, user: CurrentUser):
    """Create a Square order."""
    svc = get_square_service()
    line_items = [
        {
            "name": item.name,
            "quantity": item.quantity,
            "base_price_money": {
                "amount": item.base_price_cents,
                "currency": item.currency.upper(),
            },
        }
        for item in body.line_items
    ]
    try:
        result = await svc.create_order(
            line_items=line_items,
            customer_id=body.customer_id,
            reference_id=body.reference_id,
        )
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Square error: {str(e)}")


# ---- Customers ----

@router.post("/customers")
@limiter.limit("20/minute")
async def create_customer(request: Request, body: CreateSquareCustomerRequest, user: CurrentUser):
    """Create a Square customer."""
    svc = get_square_service()
    try:
        result = await svc.create_customer(
            given_name=body.given_name,
            family_name=body.family_name,
            email=body.email,
            phone=body.phone,
            reference_id=body.reference_id,
        )
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Square error: {str(e)}")


@router.post("/customers/search")
@limiter.limit("30/minute")
async def search_customers(
    request: Request,
    user: CurrentUser,
    query: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    limit: int = 50,
):
    """Search Square customers."""
    svc = get_square_service()
    try:
        result = await svc.search_customers(
            query=query, email=email, phone=phone, limit=limit,
        )
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Square error: {str(e)}")


# ---- Terminal ----

@router.post("/terminal/checkout")
@limiter.limit("30/minute")
async def terminal_checkout(request: Request, body: TerminalCheckoutRequest, user: CurrentUser):
    """Create a Square Terminal checkout."""
    svc = get_square_service()
    try:
        result = await svc.create_terminal_checkout(
            amount_cents=body.amount_cents,
            currency=body.currency,
            device_id=body.device_id,
            note=body.note,
            reference_id=body.reference_id,
        )
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Square error: {str(e)}")


# ---- Catalog ----

@router.post("/catalog/items")
@limiter.limit("30/minute")
async def upsert_catalog_item(request: Request, body: CatalogItemRequest, user: RequireManager):
    """Create or update a Square catalog item (menu sync)."""
    svc = get_square_service()
    try:
        result = await svc.upsert_catalog_item(
            name=body.name,
            price_cents=body.price_cents,
            currency=body.currency,
            description=body.description,
            category_id=body.category_id,
            item_id=body.item_id,
        )
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Square error: {str(e)}")


@router.get("/catalog")
@limiter.limit("30/minute")
async def list_catalog(
    request: Request,
    user: CurrentUser,
    types: Optional[str] = None,
    cursor: Optional[str] = None,
):
    """List Square catalog items."""
    svc = get_square_service()
    type_list = types.split(",") if types else None
    try:
        result = await svc.list_catalog(types=type_list, cursor=cursor)
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Square error: {str(e)}")


# ---- Webhooks ----

@router.post("/webhooks")
async def handle_webhook(request: Request):
    """Handle Square webhook events."""
    svc = get_square_service()
    body = await request.body()
    signature = request.headers.get("x-square-hmacsha256-signature", "")
    url = str(request.url)

    if not svc.verify_webhook(body, signature, url):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    event = svc.parse_webhook_event(body)
    event_type = event.get("type", "")
    logger.info(f"Square webhook: {event_type} (ID: {event.get('event_id')})")

    if event_type == "payment.completed":
        logger.info(f"Payment completed: {event['data'].get('id')}")
    elif event_type == "payment.updated":
        logger.info(f"Payment updated: {event['data'].get('id')}")
    elif event_type == "refund.created":
        logger.info(f"Refund created: {event['data'].get('id')}")
    elif event_type.startswith("order."):
        logger.info(f"Order event: {event_type}")
    elif event_type.startswith("inventory."):
        logger.info(f"Inventory event: {event_type}")

    return {"status": "processed", "event_id": event.get("event_id")}

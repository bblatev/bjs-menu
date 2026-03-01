"""Payment processing"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Body, Request
from pydantic import BaseModel, Field, field_validator

from app.core.sanitize import sanitize_text
from app.core.responses import list_response, paginated_response

from app.db.session import DbSession
from app.models.restaurant import (
    GuestOrder as GuestOrderModel, KitchenOrder, Table, MenuItem,
    ModifierGroup, ModifierOption, MenuItemModifierGroup,
    ComboMeal, ComboItem, MenuCategory as MenuCategoryModel,
    CheckItem,
)
from app.models.operations import AppSetting
from app.services.stock_deduction_service import StockDeductionService
import logging
from app.core.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter()

# Import shared schemas and helpers
from app.api.routes.guest_orders._shared import *
from app.api.routes.guest_orders._shared import _get_venue_name

# ==================== CUSTOMER PAYMENT ENDPOINTS ====================

class GuestPaymentRequest(BaseModel):
    order_id: int
    payment_method: str = "card"  # card, cash, online
    tip_amount: Optional[float] = None
    tip_percent: Optional[int] = None
    card_token: Optional[str] = None  # For saved card payments
    payment_intent_id: Optional[str] = None  # Stripe payment intent ID (for card payments)


class GuestPaymentResponse(BaseModel):
    payment_id: int
    order_id: int
    status: str
    amount: float
    tip: float
    total_charged: float
    payment_method: str
    receipt_url: Optional[str] = None


@router.get("/orders/{order_id}/payment")
@limiter.limit("60/minute")
def get_order_payment_status(request: Request, db: DbSession, order_id: int):
    """Get payment status for an order."""
    order = db.query(GuestOrderModel).filter(GuestOrderModel.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return {
        "order_id": order.id,
        "order_status": order.status,
        "subtotal": float(order.subtotal) if order.subtotal else 0,
        "tax": float(order.tax) if order.tax else 0,
        "total": float(order.total) if order.total else 0,
        "payment_status": order.payment_status or "unpaid",
        "payment_method": order.payment_method,
        "tip_amount": float(order.tip_amount) if order.tip_amount else 0,
        "total_with_tip": float(order.total) + (float(order.tip_amount) if order.tip_amount else 0),
        "paid_at": order.paid_at.isoformat() if order.paid_at else None,
    }


@router.get("/orders/table/{token}/payment-summary")
@limiter.limit("60/minute")
def get_table_payment_summary(request: Request, db: DbSession, token: str):
    """Get payment summary for all orders at a table."""
    orders = db.query(GuestOrderModel).filter(
        GuestOrderModel.table_token == token,
        GuestOrderModel.status.notin_(["cancelled", "void"])
    ).all()

    total_subtotal = sum(float(o.subtotal) if o.subtotal else 0 for o in orders)
    total_tax = sum(float(o.tax) if o.tax else 0 for o in orders)
    total_amount = sum(float(o.total) if o.total else 0 for o in orders)
    total_paid = sum(float(o.total) if o.total and o.payment_status == "paid" else 0 for o in orders)

    unpaid_orders = [o for o in orders if o.payment_status != "paid"]

    return {
        "table_token": token,
        "total_orders": len(orders),
        "subtotal": total_subtotal,
        "tax": total_tax,
        "total_amount": total_amount,
        "total_paid": total_paid,
        "balance_due": total_amount - total_paid,
        "unpaid_orders": [
            {
                "id": o.id,
                "total": float(o.total) if o.total else 0,
                "items_count": len(o.items) if o.items else 0,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            }
            for o in unpaid_orders
        ],
        "payment_status": "paid" if total_paid >= total_amount and len(orders) > 0 else "unpaid",
    }


@router.post("/orders/{order_id}/pay")
@limiter.limit("30/minute")
def process_guest_payment(
    request: Request,
    db: DbSession,
    order_id: int,
    payment: GuestPaymentRequest,
):
    """
    Process payment for a guest order.
    This endpoint is used by the customer-facing QR code ordering page.
    """
    order = db.query(GuestOrderModel).filter(GuestOrderModel.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.payment_status == "paid":
        raise HTTPException(status_code=400, detail="Order already paid")

    # Calculate tip
    tip = Decimal("0")
    if payment.tip_amount:
        tip = Decimal(str(payment.tip_amount))
    elif payment.tip_percent:
        tip = order.total * Decimal(str(payment.tip_percent)) / Decimal("100")

    total_charged = order.total + tip

    # If a Stripe payment_intent_id is provided, verify it succeeded
    if payment.payment_intent_id and payment.payment_method == "card":
        try:
            from app.services.stripe_service import get_stripe_service, PaymentStatus
            stripe = get_stripe_service()
            if stripe:
                import asyncio
                loop = asyncio.new_event_loop()
                try:
                    result = loop.run_until_complete(
                        stripe.get_payment_intent(payment.payment_intent_id)
                    )
                finally:
                    loop.close()

                if not result or not result.success:
                    raise HTTPException(
                        status_code=402,
                        detail=f"Payment verification failed: {result.error_message if result else 'Stripe unavailable'}",
                    )
                if result.status != PaymentStatus.SUCCEEDED:
                    raise HTTPException(
                        status_code=402,
                        detail=f"Payment not completed. Current status: {result.status.value if result.status else 'unknown'}",
                    )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Stripe verification failed for order {order_id}: {e}")
            raise HTTPException(
                status_code=502,
                detail="Payment verification service unavailable. Please try again.",
            )

    # Record payment
    order.payment_status = "paid"
    order.payment_method = payment.payment_method
    order.tip_amount = tip
    order.paid_at = datetime.now(timezone.utc)
    order.status = "completed"
    db.commit()

    return {
        "status": "success",
        "payment_id": order.id,
        "order_id": order.id,
        "amount": float(order.total),
        "tip": float(tip),
        "total_charged": float(total_charged),
        "payment_method": payment.payment_method,
        "receipt_url": f"/api/v1/guest-orders/orders/{order.id}/receipt",
        "message": "Payment successful! Thank you for your order.",
    }


@router.post("/orders/table/{token}/pay-all")
@limiter.limit("30/minute")
def pay_all_table_orders(
    request: Request,
    db: DbSession,
    token: str,
    payment_method: str = Query("card"),
    tip_percent: Optional[int] = Query(None),
    tip_amount: Optional[float] = Query(None),
):
    """
    Pay all unpaid orders for a table at once.
    """
    orders = db.query(GuestOrderModel).filter(
        GuestOrderModel.table_token == token,
        GuestOrderModel.payment_status != "paid",
        GuestOrderModel.status.notin_(["cancelled", "void"])
    ).all()

    if not orders:
        return {
            "status": "success",
            "orders_paid": 0,
            "subtotal": 0,
            "tip": 0,
            "total_charged": 0,
            "payment_method": payment_method,
            "message": "No unpaid orders found for this table.",
        }

    total_amount = sum(float(o.total) if o.total else 0 for o in orders)

    # Calculate tip
    tip = Decimal("0")
    if tip_amount:
        tip = Decimal(str(tip_amount))
    elif tip_percent:
        tip = Decimal(str(total_amount)) * Decimal(str(tip_percent)) / Decimal("100")

    total_charged = Decimal(str(total_amount)) + tip

    # Mark all orders as paid
    now = datetime.now(timezone.utc)
    for order in orders:
        order.payment_status = "paid"
        order.payment_method = payment_method
        order.paid_at = now
        order.status = "completed"

    # Apply tip to the last order
    if orders and tip > 0:
        orders[-1].tip_amount = tip

    db.commit()

    return {
        "status": "success",
        "orders_paid": len(orders),
        "subtotal": total_amount,
        "tip": float(tip),
        "total_charged": float(total_charged),
        "payment_method": payment_method,
        "message": f"Successfully paid {len(orders)} order(s). Thank you!",
    }


@router.get("/orders/{order_id}/receipt")
@limiter.limit("60/minute")
def get_order_receipt(request: Request, db: DbSession, order_id: int):
    """Get receipt for a paid order."""
    order = db.query(GuestOrderModel).filter(GuestOrderModel.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return {
        "receipt": {
            "order_id": order.id,
            "venue": _get_venue_name(db),
            "table": order.table_number,
            "date": order.created_at.isoformat() if order.created_at else None,
            "items": order.items or [],
            "subtotal": float(order.subtotal) if order.subtotal else 0,
            "tax": float(order.tax) if order.tax else 0,
            "tip": float(order.tip_amount) if order.tip_amount else 0,
            "total": float(order.total) + (float(order.tip_amount) if order.tip_amount else 0),
            "payment_method": order.payment_method,
            "payment_status": order.payment_status or "unpaid",
            "paid_at": order.paid_at.isoformat() if order.paid_at else None,
        },
        "message": "Thank you for dining with us!"
    }


@router.post("/orders/{order_id}/request-payment")
@limiter.limit("30/minute")
def request_payment_assistance(
    request: Request,
    db: DbSession,
    order_id: int,
    message: Optional[str] = Query(None),
):
    """
    Request payment assistance from waiter.
    Creates a waiter call for payment/check request.
    """
    from app.models.hardware import WaiterCall as WaiterCallModel

    order = db.query(GuestOrderModel).filter(GuestOrderModel.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Create waiter call for payment
    call = WaiterCallModel(
        table_id=order.table_id,
        table_number=f"Table {order.table_number}",
        call_type="check",
        message=message or f"Payment requested for order #{order.id} - Total: ${float(order.total):.2f}",
        status="pending",
    )
    db.add(call)
    db.commit()
    db.refresh(call)

    return {
        "status": "requested",
        "call_id": call.id,
        "order_id": order.id,
        "total": float(order.total) if order.total else 0,
        "message": "A server will be with you shortly to process your payment.",
    }


"""
Bulgarian Payment Processors API Endpoints
Borica and ePay.bg integration for Bulgarian market
"""
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal
import logging

from app.db.session import get_db
from app.core.rbac import get_current_user
from app.core.rate_limit import limiter
from app.services.bulgarian_payments import (
    get_borica_service, get_epay_service
)


router = APIRouter(tags=["Bulgarian Payments"])
logger = logging.getLogger(__name__)


# =============================================================================
# SCHEMAS
# =============================================================================

class BoricaPaymentRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, description="Amount in BGN")
    order_id: str = Field(..., min_length=1, max_length=50)
    description: str = Field(..., min_length=1, max_length=255)
    customer_email: Optional[str] = None
    success_url: Optional[str] = None
    fail_url: Optional[str] = None


class EPayPaymentRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, description="Amount in BGN")
    invoice_id: str = Field(..., min_length=1, max_length=50)
    description: str = Field(..., min_length=1, max_length=255)
    customer_email: Optional[str] = None
    expiration_minutes: int = Field(default=60, ge=15, le=1440)


class RefundRequest(BaseModel):
    transaction_id: str
    amount: Optional[Decimal] = None
    reason: Optional[str] = None


class PaymentStatusRequest(BaseModel):
    invoice_id: str


# =============================================================================
# BORICA ENDPOINTS
# =============================================================================

@router.get("/")
@limiter.limit("60/minute")
async def get_bulgarian_payments_root(request: Request):
    """Bulgarian payment methods."""
    return await get_bulgarian_payment_methods(request=request)


@router.post("/borica/create")
@limiter.limit("30/minute")
async def create_borica_payment(
    request: Request,
    payment_data: BoricaPaymentRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a Borica payment and get redirect URL

    Returns a redirect URL where customer should be sent to complete payment
    """
    borica = get_borica_service()

    result = borica.create_payment(
        amount=payment_data.amount,
        order_id=payment_data.order_id,
        description=payment_data.description,
        customer_email=payment_data.customer_email,
        success_url=payment_data.success_url,
        fail_url=payment_data.fail_url
    )

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {
        "success": True,
        "transaction_id": result.transaction_id,
        "redirect_url": result.redirect_url,
        "message": "Redirect customer to payment page"
    }


@router.post("/borica/callback")
@limiter.limit("30/minute")
async def borica_callback(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Handle Borica payment callback (called by Borica servers)

    This endpoint receives payment confirmation from Borica
    """
    try:
        # Get callback data
        if request.headers.get("content-type", "").startswith("application/json"):
            callback_data = await request.json()
        else:
            form_data = await request.form()
            callback_data = dict(form_data)

        borica = get_borica_service()
        result = borica.verify_callback(callback_data)

        if result.success:
            # Update order status in background
            background_tasks.add_task(
                _update_order_payment_status,
                db,
                result.metadata.get("order_id"),
                "paid",
                "borica",
                result.transaction_id
            )

            logger.info(f"Borica payment successful: {result.transaction_id}")
            return {"status": "OK"}
        else:
            logger.warning(f"Borica payment failed: {result.error_message}")
            return {"status": "FAILED", "error": result.error_message}

    except Exception as e:
        logger.error(f"Borica callback error: {e}")
        raise HTTPException(status_code=500, detail="Callback processing failed")


@router.post("/borica/refund")
@limiter.limit("30/minute")
async def refund_borica_payment(
    request: Request,
    refund_data: RefundRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Refund a Borica payment

    Requires admin or manager role
    """
    # Check permissions
    if current_user.role not in ["owner", "manager"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    borica = get_borica_service()
    result = borica.refund(
        original_transaction_id=refund_data.transaction_id,
        amount=refund_data.amount,
        reason=refund_data.reason
    )

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {
        "success": True,
        "refund_transaction_id": result.transaction_id,
        "status": result.status,
        "message": "Refund processed successfully"
    }


# =============================================================================
# EPAY ENDPOINTS
# =============================================================================

@router.post("/epay/create")
@limiter.limit("30/minute")
async def create_epay_payment(
    request: Request,
    payment_data: EPayPaymentRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create an ePay.bg payment

    Returns payment URL and form data for customer redirect
    """
    epay = get_epay_service()

    result = epay.create_payment(
        amount=payment_data.amount,
        invoice_id=payment_data.invoice_id,
        description=payment_data.description,
        customer_email=payment_data.customer_email,
        expiration_minutes=payment_data.expiration_minutes
    )

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {
        "success": True,
        "transaction_id": result.transaction_id,
        "redirect_url": result.redirect_url,
        "payment_url": result.metadata.get("payment_url"),
        "form_data": result.metadata.get("form_data"),
        "message": "Redirect customer to ePay payment page"
    }


@router.post("/epay/notify")
@limiter.limit("30/minute")
async def epay_notification(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Handle ePay IPN (Instant Payment Notification)

    Called by ePay servers when payment status changes
    """
    try:
        # ePay sends form data
        form_data = await request.form()
        notification_data = dict(form_data)

        epay = get_epay_service()
        result = epay.verify_notification(notification_data)

        if result.success:
            status = result.status
            invoice_id = result.metadata.get("invoice_id")

            if status == "PAID":
                background_tasks.add_task(
                    _update_order_payment_status,
                    db,
                    invoice_id,
                    "paid",
                    "epay",
                    result.transaction_id
                )
            elif status == "DENIED":
                background_tasks.add_task(
                    _update_order_payment_status,
                    db,
                    invoice_id,
                    "failed",
                    "epay",
                    result.transaction_id
                )
            elif status == "EXPIRED":
                background_tasks.add_task(
                    _update_order_payment_status,
                    db,
                    invoice_id,
                    "expired",
                    "epay",
                    result.transaction_id
                )

            logger.info(f"ePay notification processed: {invoice_id} -> {status}")
            return {"status": "OK"}
        else:
            logger.warning(f"ePay notification invalid: {result.error_message}")
            return {"status": "ERR", "error": result.error_message}

    except Exception as e:
        logger.error(f"ePay notification error: {e}")
        raise HTTPException(status_code=500, detail="Notification processing failed")


@router.post("/epay/status")
@limiter.limit("30/minute")
async def check_epay_status(
    request: Request,
    status_data: PaymentStatusRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check ePay payment status
    """
    epay = get_epay_service()
    result = epay.check_payment_status(status_data.invoice_id)

    return {
        "invoice_id": status_data.invoice_id,
        "status": result.status,
        "transaction_id": result.transaction_id,
        "success": result.success
    }


# =============================================================================
# PAYMENT METHODS INFO
# =============================================================================

@router.get("/methods")
@limiter.limit("60/minute")
async def get_bulgarian_payment_methods(request: Request):
    """
    Get available Bulgarian payment methods
    """
    return {
        "methods": [
            {
                "id": "borica",
                "name": "Borica",
                "name_bg": "Борика",
                "description": "Pay with Visa or Mastercard",
                "description_bg": "Плащане с Visa или Mastercard",
                "cards": ["visa", "mastercard", "maestro"],
                "supports_3ds": True,
                "currency": "BGN",
                "min_amount": 1.00,
                "max_amount": 50000.00,
                "icon": "/icons/payments/borica.svg"
            },
            {
                "id": "epay",
                "name": "ePay.bg",
                "name_bg": "ePay.bg",
                "description": "Pay via ePay, bank transfer, or EasyPay",
                "description_bg": "Плащане чрез ePay, банков превод или EasyPay",
                "options": ["epay_wallet", "bank_transfer", "easypay"],
                "currency": "BGN",
                "min_amount": 0.01,
                "max_amount": 100000.00,
                "icon": "/icons/payments/epay.svg"
            }
        ],
        "default_method": "borica",
        "currency": {
            "code": "BGN",
            "symbol": "лв.",
            "name": "Bulgarian Lev"
        }
    }


@router.get("/borica/supported-cards")
@limiter.limit("60/minute")
async def get_borica_supported_cards(request: Request):
    """
    Get Borica supported card types
    """
    return {
        "cards": [
            {"type": "visa", "name": "Visa", "icon": "/icons/cards/visa.svg"},
            {"type": "mastercard", "name": "Mastercard", "icon": "/icons/cards/mastercard.svg"},
            {"type": "maestro", "name": "Maestro", "icon": "/icons/cards/maestro.svg"}
        ],
        "features": {
            "3d_secure": True,
            "tokenization": True,
            "recurring": True,
            "refunds": True
        }
    }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def _update_order_payment_status(
    db: Session,
    order_id: str,
    status: str,
    provider: str,
    transaction_id: str
):
    """Update order payment status after callback"""
    try:
        from app.models import Order, Payment

        # Find order
        order = db.query(Order).filter(
            Order.order_number == order_id
        ).first()

        if order:
            # Update order status
            if status == "paid":
                order.payment_status = "paid"
                order.status = "confirmed"
            elif status == "failed":
                order.payment_status = "failed"
            elif status == "expired":
                order.payment_status = "expired"

            # Create payment record
            payment = Payment(
                order_id=order.id,
                amount=order.total_amount,
                payment_method=provider,
                transaction_id=transaction_id,
                status=status
            )
            db.add(payment)
            db.commit()

            logger.info(f"Order {order_id} payment status updated to {status}")
        else:
            logger.warning(f"Order not found for payment update: {order_id}")

    except Exception as e:
        logger.error(f"Failed to update order payment status: {e}")
        db.rollback()

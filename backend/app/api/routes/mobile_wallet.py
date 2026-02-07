"""Mobile Wallet Payment API routes.

Apple Pay and Google Pay payment handling via Stripe.
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.mobile_wallet_service import (
    get_mobile_wallet_service,
    WalletType,
    WalletPaymentStatus,
)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class CreateSessionRequest(BaseModel):
    order_id: str
    amount: int  # Amount in cents
    currency: str = "usd"
    venue_id: int = 0
    description: Optional[str] = None
    metadata: Optional[dict] = None


class ConfirmPaymentRequest(BaseModel):
    payment_id: str
    wallet_type: str  # apple_pay, google_pay, link
    payment_method_id: Optional[str] = None
    card_brand: Optional[str] = None
    card_last4: Optional[str] = None
    customer_email: Optional[str] = None


class UpdateConfigRequest(BaseModel):
    apple_pay_enabled: Optional[bool] = None
    google_pay_enabled: Optional[bool] = None
    link_enabled: Optional[bool] = None
    merchant_name: Optional[str] = None
    merchant_country: Optional[str] = None
    merchant_currency: Optional[str] = None
    apple_pay_merchant_id: Optional[str] = None
    supported_networks: Optional[List[str]] = None


class PaymentResponse(BaseModel):
    payment_id: str
    order_id: str
    wallet_type: str
    amount: int
    currency: str
    status: str
    card_brand: Optional[str] = None
    card_last4: Optional[str] = None
    customer_email: Optional[str] = None
    receipt_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None


# ============================================================================
# Payment Session
# ============================================================================

@router.post("/sessions")
async def create_payment_session(request: CreateSessionRequest):
    """
    Create a payment session for Apple Pay or Google Pay.

    Returns a client_secret to use with Stripe.js PaymentRequest API.
    The client uses this to display the native Apple Pay or Google Pay sheet.

    Flow:
    1. Call this endpoint to get client_secret
    2. Create Stripe PaymentRequest on client with wallet_config
    3. User authorizes payment in Apple Pay/Google Pay sheet
    4. Call /confirm with the payment details
    """
    service = get_mobile_wallet_service()

    if request.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    session = service.create_payment_session(
        order_id=request.order_id,
        amount=request.amount,
        currency=request.currency,
        venue_id=request.venue_id,
        description=request.description,
        metadata=request.metadata,
    )

    return session


@router.post("/confirm", response_model=PaymentResponse)
async def confirm_payment(request: ConfirmPaymentRequest):
    """
    Confirm a wallet payment completed successfully.

    Call this after the Apple Pay/Google Pay sheet completes.
    Verifies the payment with Stripe and updates the order.
    """
    service = get_mobile_wallet_service()

    payment = service.confirm_payment(
        payment_id=request.payment_id,
        wallet_type=request.wallet_type,
        payment_method_id=request.payment_method_id,
        card_brand=request.card_brand,
        card_last4=request.card_last4,
        customer_email=request.customer_email,
    )

    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    return _payment_to_response(payment)


@router.post("/{payment_id}/cancel")
async def cancel_payment(payment_id: str, reason: str = ""):
    """Cancel a pending wallet payment."""
    service = get_mobile_wallet_service()

    payment = service.cancel_payment(payment_id, reason)

    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found or cannot be canceled")

    return {
        "success": True,
        "payment_id": payment_id,
        "status": payment.status.value,
    }


# ============================================================================
# Payment Retrieval
# ============================================================================

@router.get("/payments/{payment_id}", response_model=PaymentResponse)
async def get_payment(payment_id: str):
    """Get a wallet payment by ID."""
    service = get_mobile_wallet_service()

    payment = service.get_payment(payment_id)

    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    return _payment_to_response(payment)


@router.get("/payments/order/{order_id}", response_model=List[PaymentResponse])
async def get_payments_by_order(order_id: str):
    """Get all wallet payments for an order."""
    service = get_mobile_wallet_service()

    payments = service.get_payments_by_order(order_id)

    return [_payment_to_response(p) for p in payments]


@router.get("/payments", response_model=List[PaymentResponse])
async def list_payments(
    wallet_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
):
    """List wallet payments."""
    service = get_mobile_wallet_service()

    wt = None
    if wallet_type:
        try:
            wt = WalletType(wallet_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid wallet type: {wallet_type}")

    st = None
    if status:
        try:
            st = WalletPaymentStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    payments = service.list_payments(wallet_type=wt, status=st, limit=limit)

    return [_payment_to_response(p) for p in payments]


# ============================================================================
# Configuration
# ============================================================================

@router.get("/config")
async def get_default_configuration():
    """Get default wallet configuration."""
    return {
        "venue_id": 0,
        "apple_pay_enabled": True,
        "google_pay_enabled": True,
        "link_enabled": False,
        "merchant_name": "",
        "merchant_country": "BG",
        "merchant_currency": "BGN",
        "supported_networks": ["visa", "mastercard"],
    }


@router.get("/config/{venue_id}")
async def get_configuration(venue_id: int):
    """Get wallet configuration for a venue."""
    service = get_mobile_wallet_service()

    config = service.get_configuration(venue_id)

    return {
        "venue_id": venue_id,
        "apple_pay_enabled": config.apple_pay_enabled,
        "google_pay_enabled": config.google_pay_enabled,
        "link_enabled": config.link_enabled,
        "merchant_name": config.merchant_name,
        "merchant_country": config.merchant_country,
        "merchant_currency": config.merchant_currency,
        "supported_networks": config.supported_networks,
    }


@router.put("/config")
async def update_default_configuration(request: UpdateConfigRequest):
    """Update default wallet configuration (venue_id=0)."""
    return await update_configuration(0, request)


@router.put("/config/{venue_id}")
async def update_configuration(venue_id: int, request: UpdateConfigRequest):
    """Update wallet configuration for a venue."""
    service = get_mobile_wallet_service()

    updates = {}
    if request.apple_pay_enabled is not None:
        updates["apple_pay_enabled"] = request.apple_pay_enabled
    if request.google_pay_enabled is not None:
        updates["google_pay_enabled"] = request.google_pay_enabled
    if request.link_enabled is not None:
        updates["link_enabled"] = request.link_enabled
    if request.merchant_name is not None:
        updates["merchant_name"] = request.merchant_name
    if request.merchant_country is not None:
        updates["merchant_country"] = request.merchant_country
    if request.merchant_currency is not None:
        updates["merchant_currency"] = request.merchant_currency
    if request.apple_pay_merchant_id is not None:
        updates["apple_pay_merchant_id"] = request.apple_pay_merchant_id
    if request.supported_networks is not None:
        updates["supported_networks"] = request.supported_networks

    config = service.update_configuration(venue_id, **updates)

    return {
        "success": True,
        "venue_id": venue_id,
        "apple_pay_enabled": config.apple_pay_enabled,
        "google_pay_enabled": config.google_pay_enabled,
        "link_enabled": config.link_enabled,
    }


@router.get("/client-config/{venue_id}")
async def get_client_config(venue_id: int):
    """
    Get client-side configuration for Stripe PaymentRequest.

    Use this configuration when initializing the Stripe PaymentRequest
    on the frontend.
    """
    service = get_mobile_wallet_service()

    return service.get_client_config(venue_id)


# ============================================================================
# Statistics
# ============================================================================

@router.get("/stats")
async def get_stats():
    """Get wallet payment statistics."""
    service = get_mobile_wallet_service()

    return service.get_stats()


# ============================================================================
# Info
# ============================================================================

@router.get("/wallet-types")
async def get_wallet_types():
    """Get supported wallet types."""
    return {
        "types": [
            {
                "id": "apple_pay",
                "name": "Apple Pay",
                "description": "Pay with Apple Pay on iOS/Safari",
                "icon": "apple",
            },
            {
                "id": "google_pay",
                "name": "Google Pay",
                "description": "Pay with Google Pay on Android/Chrome",
                "icon": "google",
            },
            {
                "id": "link",
                "name": "Link by Stripe",
                "description": "Fast checkout with saved payment info",
                "icon": "link",
            },
        ],
        "supported_networks": [
            "visa",
            "mastercard",
            "amex",
            "discover",
            "jcb",
            "diners",
        ],
    }


# ============================================================================
# Helper Functions
# ============================================================================

def _payment_to_response(payment) -> PaymentResponse:
    """Convert payment to response model."""
    return PaymentResponse(
        payment_id=payment.payment_id,
        order_id=payment.order_id,
        wallet_type=payment.wallet_type.value,
        amount=payment.amount,
        currency=payment.currency,
        status=payment.status.value,
        card_brand=payment.card_brand,
        card_last4=payment.card_last4,
        customer_email=payment.customer_email,
        receipt_url=payment.receipt_url,
        error_message=payment.error_message,
        created_at=payment.created_at.isoformat(),
        completed_at=payment.completed_at.isoformat() if payment.completed_at else None,
    )

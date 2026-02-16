"""EMV Card Terminal API routes.

Hardware card terminal integration via Stripe Terminal.
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.core.rate_limit import limiter
from app.services.card_terminal_service import (
    get_card_terminal_service,
    TerminalType,
    TerminalStatus,
    PaymentEntryMode,
    TerminalPaymentStatus,
)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class RegisterTerminalRequest(BaseModel):
    name: str
    terminal_type: str  # stripe_s700, stripe_m2, stripe_wisepos_e, etc.
    registration_code: Optional[str] = None
    venue_id: Optional[int] = None
    location_id: Optional[str] = None


class UpdateTerminalRequest(BaseModel):
    name: Optional[str] = None
    location_id: Optional[str] = None


class CreatePaymentRequest(BaseModel):
    terminal_id: str
    order_id: str
    amount: int  # Amount in cents
    currency: str = "usd"
    description: Optional[str] = None
    metadata: Optional[dict] = None


class ProcessPaymentRequest(BaseModel):
    payment_id: str
    entry_mode: str  # chip, contactless, swipe, manual
    card_brand: Optional[str] = None
    card_last4: Optional[str] = None
    cardholder_name: Optional[str] = None
    auth_code: Optional[str] = None


class DisplayMessageRequest(BaseModel):
    message: str


class CartDisplayRequest(BaseModel):
    items: List[dict]  # [{description, amount, quantity}]
    total: int  # Total in cents
    currency: str = "usd"


class TerminalResponse(BaseModel):
    terminal_id: str
    stripe_terminal_id: Optional[str] = None
    name: str
    terminal_type: str
    serial_number: Optional[str] = None
    location_id: Optional[str] = None
    venue_id: Optional[int] = None
    status: str
    ip_address: Optional[str] = None
    firmware_version: Optional[str] = None
    last_seen: Optional[str] = None
    registered_at: str


class PaymentResponse(BaseModel):
    payment_id: str
    terminal_id: str
    order_id: str
    amount: int
    currency: str
    status: str
    entry_mode: Optional[str] = None
    card_brand: Optional[str] = None
    card_last4: Optional[str] = None
    cardholder_name: Optional[str] = None
    auth_code: Optional[str] = None
    receipt_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None


# ============================================================================
# Terminal Registration
# ============================================================================

@router.get("/")
@limiter.limit("60/minute")
async def get_card_terminals_root(request: Request):
    """Card terminals overview."""
    return await list_terminals(request=request)


@router.post("/terminals", response_model=TerminalResponse)
@limiter.limit("30/minute")
async def register_terminal(request: Request, data: RegisterTerminalRequest):
    """
    Register a new card terminal.

    For Stripe Terminal readers, provide the registration code displayed
    on the terminal screen during setup.
    """
    service = get_card_terminal_service()

    try:
        terminal_type = TerminalType(data.terminal_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid terminal type: {data.terminal_type}")

    terminal = service.register_terminal(
        name=data.name,
        terminal_type=terminal_type,
        registration_code=data.registration_code,
        venue_id=data.venue_id,
        location_id=data.location_id,
    )

    return _terminal_to_response(terminal)


@router.get("/terminals", response_model=List[TerminalResponse])
@limiter.limit("60/minute")
async def list_terminals(
    request: Request,
    venue_id: Optional[int] = None,
    status: Optional[str] = None,
):
    """List registered card terminals."""
    service = get_card_terminal_service()

    term_status = None
    if status:
        try:
            term_status = TerminalStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    terminals = service.list_terminals(venue_id=venue_id, status=term_status)

    return [_terminal_to_response(t) for t in terminals]


@router.get("/terminals/{terminal_id}", response_model=TerminalResponse)
@limiter.limit("60/minute")
async def get_terminal(request: Request, terminal_id: str):
    """Get a specific terminal."""
    service = get_card_terminal_service()

    terminal = service.get_terminal(terminal_id)

    if not terminal:
        raise HTTPException(status_code=404, detail="Terminal not found")

    return _terminal_to_response(terminal)


@router.put("/terminals/{terminal_id}", response_model=TerminalResponse)
@limiter.limit("30/minute")
async def update_terminal(request: Request, terminal_id: str, data: UpdateTerminalRequest):
    """Update terminal information."""
    service = get_card_terminal_service()

    updates = {}
    if data.name is not None:
        updates["name"] = data.name
    if data.location_id is not None:
        updates["location_id"] = data.location_id

    terminal = service.update_terminal(terminal_id, **updates)

    if not terminal:
        raise HTTPException(status_code=404, detail="Terminal not found")

    return _terminal_to_response(terminal)


@router.delete("/terminals/{terminal_id}")
@limiter.limit("30/minute")
async def delete_terminal(request: Request, terminal_id: str):
    """Delete a terminal registration."""
    service = get_card_terminal_service()

    if not service.delete_terminal(terminal_id):
        raise HTTPException(status_code=404, detail="Terminal not found")

    return {"success": True, "message": "Terminal deleted"}


@router.post("/terminals/{terminal_id}/status")
@limiter.limit("30/minute")
async def update_terminal_status(
    request: Request,
    terminal_id: str,
    status: str,
    ip_address: Optional[str] = None,
):
    """Update terminal status (heartbeat)."""
    service = get_card_terminal_service()

    try:
        term_status = TerminalStatus(status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    terminal = service.update_terminal_status(terminal_id, term_status, ip_address)

    if not terminal:
        raise HTTPException(status_code=404, detail="Terminal not found")

    return {
        "success": True,
        "terminal_id": terminal_id,
        "status": terminal.status.value,
    }


# ============================================================================
# Connection Token
# ============================================================================

@router.post("/connection-token")
@limiter.limit("30/minute")
async def create_connection_token(request: Request, location_id: Optional[str] = None):
    """
    Create a connection token for the terminal SDK.

    The POS application uses this token to connect to Stripe Terminal.
    Fetch a fresh token each time before connecting.
    """
    service = get_card_terminal_service()

    token = service.create_connection_token(location_id)

    return {
        "secret": token.secret,
        "created_at": token.created_at.isoformat(),
    }


# ============================================================================
# Payments
# ============================================================================

@router.post("/payments")
@limiter.limit("30/minute")
async def create_payment(request: Request, data: CreatePaymentRequest):
    """
    Create a payment intent for terminal payment.

    Returns the PaymentIntent that the terminal SDK will use
    to collect the card payment.
    """
    service = get_card_terminal_service()

    if data.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    result = service.create_payment_intent(
        terminal_id=data.terminal_id,
        order_id=data.order_id,
        amount=data.amount,
        currency=data.currency,
        description=data.description,
        metadata=data.metadata,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.post("/payments/process", response_model=PaymentResponse)
@limiter.limit("30/minute")
async def process_payment(request: Request, data: ProcessPaymentRequest):
    """
    Process a terminal payment after card read.

    Called after the terminal SDK successfully reads the card.
    """
    service = get_card_terminal_service()

    try:
        entry_mode = PaymentEntryMode(data.entry_mode)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid entry mode: {data.entry_mode}")

    payment = service.process_payment(
        payment_id=data.payment_id,
        entry_mode=entry_mode,
        card_brand=data.card_brand,
        card_last4=data.card_last4,
        cardholder_name=data.cardholder_name,
        auth_code=data.auth_code,
    )

    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    return _payment_to_response(payment)


@router.post("/payments/{payment_id}/cancel")
@limiter.limit("30/minute")
async def cancel_payment(request: Request, payment_id: str, reason: str = ""):
    """Cancel a pending terminal payment."""
    service = get_card_terminal_service()

    payment = service.cancel_payment(payment_id, reason)

    if not payment:
        raise HTTPException(status_code=400, detail="Payment not found or cannot be canceled")

    return {
        "success": True,
        "payment_id": payment_id,
        "status": payment.status.value,
    }


@router.get("/payments/{payment_id}", response_model=PaymentResponse)
@limiter.limit("60/minute")
async def get_payment(request: Request, payment_id: str):
    """Get a terminal payment by ID."""
    service = get_card_terminal_service()

    payment = service.get_payment(payment_id)

    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    return _payment_to_response(payment)


@router.get("/payments", response_model=List[PaymentResponse])
@limiter.limit("60/minute")
async def list_payments(
    request: Request,
    terminal_id: Optional[str] = None,
    status: Optional[str] = None,
    entry_mode: Optional[str] = None,
    limit: int = 50,
):
    """List terminal payments."""
    service = get_card_terminal_service()

    if terminal_id:
        payments = service.get_payments_by_terminal(terminal_id, limit)
    else:
        pay_status = None
        if status:
            try:
                pay_status = TerminalPaymentStatus(status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

        pay_entry_mode = None
        if entry_mode:
            try:
                pay_entry_mode = PaymentEntryMode(entry_mode)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid entry mode: {entry_mode}")

        payments = service.list_payments(status=pay_status, entry_mode=pay_entry_mode, limit=limit)

    return [_payment_to_response(p) for p in payments]


@router.get("/payments/order/{order_id}", response_model=List[PaymentResponse])
@limiter.limit("60/minute")
async def get_payments_by_order(request: Request, order_id: str):
    """Get terminal payments for an order."""
    service = get_card_terminal_service()

    payments = service.get_payments_by_order(order_id)

    return [_payment_to_response(p) for p in payments]


# ============================================================================
# Terminal Display Actions
# ============================================================================

@router.post("/terminals/{terminal_id}/display")
@limiter.limit("30/minute")
async def display_message(request: Request, terminal_id: str, data: DisplayMessageRequest):
    """Display a message on the terminal screen."""
    service = get_card_terminal_service()

    success = service.display_message(terminal_id, data.message)

    if not success:
        raise HTTPException(status_code=400, detail="Terminal not available")

    return {"success": True, "terminal_id": terminal_id}


@router.post("/terminals/{terminal_id}/clear")
@limiter.limit("30/minute")
async def clear_display(request: Request, terminal_id: str):
    """Clear the terminal display."""
    service = get_card_terminal_service()

    success = service.clear_display(terminal_id)

    if not success:
        raise HTTPException(status_code=400, detail="Terminal not available")

    return {"success": True, "terminal_id": terminal_id}


@router.post("/terminals/{terminal_id}/cart")
@limiter.limit("30/minute")
async def set_cart_display(request: Request, terminal_id: str, data: CartDisplayRequest):
    """Set the cart/line items display on the terminal."""
    service = get_card_terminal_service()

    success = service.set_reader_display(
        terminal_id,
        data.items,
        data.total,
        data.currency,
    )

    if not success:
        raise HTTPException(status_code=400, detail="Terminal not available")

    return {"success": True, "terminal_id": terminal_id}


# ============================================================================
# Statistics
# ============================================================================

@router.get("/stats")
@limiter.limit("60/minute")
async def get_stats(request: Request):
    """Get terminal payment statistics."""
    service = get_card_terminal_service()

    return service.get_stats()


# ============================================================================
# Reference Data
# ============================================================================

@router.get("/terminal-types")
@limiter.limit("60/minute")
async def get_terminal_types(request: Request):
    """Get supported terminal types."""
    return {
        "types": [
            {
                "id": "stripe_s700",
                "name": "Stripe Reader S700",
                "description": "Countertop terminal with touchscreen",
                "features": ["chip", "contactless", "swipe"],
            },
            {
                "id": "stripe_m2",
                "name": "Stripe Reader M2",
                "description": "Portable Bluetooth reader",
                "features": ["chip", "contactless", "swipe"],
            },
            {
                "id": "stripe_wisepos_e",
                "name": "WisePOS E",
                "description": "Smart terminal with apps",
                "features": ["chip", "contactless", "swipe", "pin"],
            },
            {
                "id": "verifone_p400",
                "name": "Verifone P400",
                "description": "Countertop PIN pad",
                "features": ["chip", "contactless", "pin"],
            },
            {
                "id": "bbpos_chipper",
                "name": "BBPOS Chipper",
                "description": "Mobile chip reader",
                "features": ["chip", "swipe"],
            },
            {
                "id": "bbpos_wisepad3",
                "name": "BBPOS WisePad 3",
                "description": "Mobile contactless reader",
                "features": ["chip", "contactless"],
            },
        ],
    }


@router.get("/entry-modes")
@limiter.limit("60/minute")
async def get_entry_modes(request: Request):
    """Get payment entry modes."""
    return {
        "modes": [
            {"id": "chip", "name": "Chip (EMV)", "description": "Insert card chip"},
            {"id": "contactless", "name": "Contactless (NFC)", "description": "Tap card or phone"},
            {"id": "swipe", "name": "Magnetic Stripe", "description": "Swipe card"},
            {"id": "manual", "name": "Manual Entry", "description": "Key in card number"},
        ],
    }


# ============================================================================
# Helper Functions
# ============================================================================

def _terminal_to_response(terminal) -> TerminalResponse:
    """Convert terminal to response model."""
    return TerminalResponse(
        terminal_id=terminal.terminal_id,
        stripe_terminal_id=terminal.stripe_terminal_id,
        name=terminal.name,
        terminal_type=terminal.terminal_type.value,
        serial_number=terminal.serial_number,
        location_id=terminal.location_id,
        venue_id=terminal.venue_id,
        status=terminal.status.value,
        ip_address=terminal.ip_address,
        firmware_version=terminal.firmware_version,
        last_seen=terminal.last_seen.isoformat() if terminal.last_seen else None,
        registered_at=terminal.registered_at.isoformat(),
    )


def _payment_to_response(payment) -> PaymentResponse:
    """Convert payment to response model."""
    return PaymentResponse(
        payment_id=payment.payment_id,
        terminal_id=payment.terminal_id,
        order_id=payment.order_id,
        amount=payment.amount,
        currency=payment.currency,
        status=payment.status.value,
        entry_mode=payment.entry_mode.value if payment.entry_mode else None,
        card_brand=payment.card_brand,
        card_last4=payment.card_last4,
        cardholder_name=payment.cardholder_name,
        auth_code=payment.auth_code,
        receipt_url=payment.receipt_url,
        error_message=payment.error_message,
        created_at=payment.created_at.isoformat(),
        completed_at=payment.completed_at.isoformat() if payment.completed_at else None,
    )

"""Training/Sandbox Mode API routes.

Allows staff to practice using the POS system without affecting real data.
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.training_mode_service import (
    get_training_service,
    is_training_order,
)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class StartSessionRequest(BaseModel):
    user_id: int
    terminal_id: Optional[str] = None
    notes: str = ""


class EndSessionRequest(BaseModel):
    user_id: Optional[int] = None
    session_id: Optional[str] = None
    terminal_id: Optional[str] = None


class OrderItem(BaseModel):
    name: str
    price: float
    quantity: int = 1
    modifiers: List[str] = []


class CreateOrderRequest(BaseModel):
    user_id: int
    table_number: str
    items: List[OrderItem]


class ProcessPaymentRequest(BaseModel):
    order_id: str
    payment_method: str  # cash, card, split


class VoidOrderRequest(BaseModel):
    order_id: str
    reason: str = ""


class SessionResponse(BaseModel):
    session_id: str
    user_id: int
    terminal_id: Optional[str] = None
    started_at: str
    ended_at: Optional[str] = None
    orders_created: int
    payments_processed: int
    notes: str = ""


class OrderResponse(BaseModel):
    order_id: str
    session_id: str
    user_id: int
    table_number: str
    items: List[dict]
    subtotal: float
    tax: float
    total: float
    payment_method: Optional[str] = None
    status: str
    created_at: str
    is_training: bool = True


class TrainingStatusResponse(BaseModel):
    is_training_mode: bool
    session_id: Optional[str] = None
    user_id: Optional[int] = None
    terminal_id: Optional[str] = None
    orders_created: int = 0


# ============================================================================
# Session Management
# ============================================================================

@router.post("/sessions/start", response_model=SessionResponse)
async def start_training_session(request: StartSessionRequest):
    """
    Start a training session for a user.

    While in training mode:
    - Orders are prefixed with "TR-"
    - Inventory is not affected
    - Fiscal receipts are not printed
    - Data doesn't appear in production reports
    """
    service = get_training_service()

    session = service.start_training_session(
        user_id=request.user_id,
        terminal_id=request.terminal_id,
        notes=request.notes,
    )

    return SessionResponse(
        session_id=session.session_id,
        user_id=session.user_id,
        terminal_id=session.terminal_id,
        started_at=session.started_at.isoformat(),
        ended_at=session.ended_at.isoformat() if session.ended_at else None,
        orders_created=session.orders_created,
        payments_processed=session.payments_processed,
        notes=session.notes,
    )


@router.post("/sessions/end")
async def end_training_session(request: EndSessionRequest):
    """End a training session."""
    service = get_training_service()

    session = service.end_training_session(
        user_id=request.user_id,
        session_id=request.session_id,
        terminal_id=request.terminal_id,
    )

    if not session:
        raise HTTPException(status_code=404, detail="No active training session found")

    stats = service.get_session_stats(session.session_id)

    return {
        "success": True,
        "session": {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "started_at": session.started_at.isoformat(),
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        },
        "stats": stats,
    }


@router.get("/sessions/active")
async def get_active_sessions():
    """Get all active training sessions."""
    service = get_training_service()
    sessions = service.get_all_active_sessions()

    return {
        "sessions": sessions,
        "count": len(sessions),
    }


@router.get("/sessions/{session_id}/stats")
async def get_session_stats(session_id: str):
    """Get statistics for a training session."""
    service = get_training_service()
    stats = service.get_session_stats(session_id)

    if not stats:
        raise HTTPException(status_code=404, detail="Session not found")

    return stats


# ============================================================================
# Status Check
# ============================================================================

@router.get("/status/{user_id}", response_model=TrainingStatusResponse)
async def check_training_status(user_id: int):
    """Check if a user is currently in training mode."""
    service = get_training_service()

    session = service.get_active_session(user_id=user_id)

    if session:
        return TrainingStatusResponse(
            is_training_mode=True,
            session_id=session.session_id,
            user_id=session.user_id,
            terminal_id=session.terminal_id,
            orders_created=session.orders_created,
        )
    else:
        return TrainingStatusResponse(
            is_training_mode=False,
            user_id=user_id,
        )


@router.get("/terminal/{terminal_id}/status", response_model=TrainingStatusResponse)
async def check_terminal_training_status(terminal_id: str):
    """Check if a terminal is currently in training mode."""
    service = get_training_service()

    session = service.get_active_session(terminal_id=terminal_id)

    if session:
        return TrainingStatusResponse(
            is_training_mode=True,
            session_id=session.session_id,
            user_id=session.user_id,
            terminal_id=session.terminal_id,
            orders_created=session.orders_created,
        )
    else:
        return TrainingStatusResponse(
            is_training_mode=False,
            terminal_id=terminal_id,
        )


# ============================================================================
# Training Orders
# ============================================================================

@router.post("/orders", response_model=OrderResponse)
async def create_training_order(request: CreateOrderRequest):
    """
    Create a training order.

    Training orders:
    - Have order IDs prefixed with "TR-"
    - Don't affect real inventory
    - Don't generate fiscal receipts
    - Are tracked separately from production orders
    """
    service = get_training_service()

    items = [
        {
            "name": item.name,
            "price": item.price,
            "quantity": item.quantity,
            "modifiers": item.modifiers,
        }
        for item in request.items
    ]

    order = service.create_training_order(
        user_id=request.user_id,
        table_number=request.table_number,
        items=items,
    )

    if not order:
        raise HTTPException(
            status_code=400,
            detail="User is not in training mode. Start a training session first.",
        )

    return OrderResponse(
        order_id=order.order_id,
        session_id=order.session_id,
        user_id=order.user_id,
        table_number=order.table_number,
        items=order.items,
        subtotal=order.subtotal,
        tax=order.tax,
        total=order.total,
        payment_method=order.payment_method,
        status=order.status,
        created_at=order.created_at.isoformat(),
        is_training=True,
    )


@router.post("/orders/pay")
async def process_training_payment(request: ProcessPaymentRequest):
    """Process a training payment."""
    service = get_training_service()

    if not is_training_order(request.order_id):
        raise HTTPException(
            status_code=400,
            detail="This endpoint is for training orders only (TR-* prefix)",
        )

    order = service.process_training_payment(
        order_id=request.order_id,
        payment_method=request.payment_method,
    )

    if not order:
        raise HTTPException(status_code=404, detail="Training order not found")

    return {
        "success": True,
        "order_id": order.order_id,
        "status": order.status,
        "payment_method": order.payment_method,
        "total": order.total,
        "message": "Training payment processed (no real transaction)",
    }


@router.post("/orders/void")
async def void_training_order(request: VoidOrderRequest):
    """Void a training order."""
    service = get_training_service()

    if not is_training_order(request.order_id):
        raise HTTPException(
            status_code=400,
            detail="This endpoint is for training orders only (TR-* prefix)",
        )

    order = service.void_training_order(
        order_id=request.order_id,
        reason=request.reason,
    )

    if not order:
        raise HTTPException(status_code=404, detail="Training order not found")

    return {
        "success": True,
        "order_id": order.order_id,
        "status": order.status,
        "message": "Training order voided",
    }


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_training_order(order_id: str):
    """Get a training order."""
    service = get_training_service()

    if not is_training_order(order_id):
        raise HTTPException(
            status_code=400,
            detail="This endpoint is for training orders only (TR-* prefix)",
        )

    order = service.get_training_order(order_id)

    if not order:
        raise HTTPException(status_code=404, detail="Training order not found")

    return OrderResponse(
        order_id=order.order_id,
        session_id=order.session_id,
        user_id=order.user_id,
        table_number=order.table_number,
        items=order.items,
        subtotal=order.subtotal,
        tax=order.tax,
        total=order.total,
        payment_method=order.payment_method,
        status=order.status,
        created_at=order.created_at.isoformat(),
        is_training=True,
    )


# ============================================================================
# Cleanup
# ============================================================================

@router.post("/cleanup")
async def cleanup_old_sessions(hours: int = 24):
    """Clean up old training sessions and orders."""
    service = get_training_service()
    result = service.cleanup_old_sessions(hours=hours)

    return {
        "success": True,
        **result,
    }


# ============================================================================
# Utility: Check if order is training
# ============================================================================

@router.get("/is-training/{order_id}")
async def check_if_training_order(order_id: str):
    """Check if an order ID is a training order."""
    return {
        "order_id": order_id,
        "is_training": is_training_order(order_id),
    }

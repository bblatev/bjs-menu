"""Training/Sandbox Mode API routes.

Allows staff to practice using the POS system without affecting real data.
"""

import json
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Body, Request
from app.core.rate_limit import limiter
from pydantic import BaseModel

from app.db.session import DbSession
from app.models.operations import AppSetting
from app.models.staff import StaffUser
from app.services.training_mode_service import (
    get_training_service,
    is_training_order,
)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class StartSessionRequest(BaseModel):
    user_id: int = 1
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
@limiter.limit("30/minute")
async def start_training_session(request: Request, body: StartSessionRequest = None):
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
        user_id=body.user_id,
        terminal_id=body.terminal_id,
        notes=body.notes,
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
@limiter.limit("30/minute")
async def end_training_session(request: Request, body: EndSessionRequest = None):
    """End a training session."""
    service = get_training_service()

    session = service.end_training_session(
        user_id=body.user_id,
        session_id=body.session_id,
        terminal_id=body.terminal_id,
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
@limiter.limit("60/minute")
async def get_active_sessions(request: Request):
    """Get all active training sessions."""
    service = get_training_service()
    sessions = service.get_all_active_sessions()

    return {
        "sessions": sessions,
        "count": len(sessions),
    }


@router.get("/sessions/{session_id}/stats")
@limiter.limit("60/minute")
async def get_session_stats(request: Request, session_id: str):
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
@limiter.limit("60/minute")
async def check_training_status(request: Request, user_id: int):
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
@limiter.limit("60/minute")
async def check_terminal_training_status(request: Request, terminal_id: str):
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
@limiter.limit("30/minute")
async def create_training_order(request: Request, body: CreateOrderRequest = None):
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
        for item in body.items
    ]

    order = service.create_training_order(
        user_id=body.user_id,
        table_number=body.table_number,
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
@limiter.limit("30/minute")
async def process_training_payment(request: Request, body: ProcessPaymentRequest = None):
    """Process a training payment."""
    service = get_training_service()

    if not is_training_order(body.order_id):
        raise HTTPException(
            status_code=400,
            detail="This endpoint is for training orders only (TR-* prefix)",
        )

    order = service.process_training_payment(
        order_id=body.order_id,
        payment_method=body.payment_method,
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
@limiter.limit("30/minute")
async def void_training_order(request: Request, body: VoidOrderRequest = None):
    """Void a training order."""
    service = get_training_service()

    if not is_training_order(body.order_id):
        raise HTTPException(
            status_code=400,
            detail="This endpoint is for training orders only (TR-* prefix)",
        )

    order = service.void_training_order(
        order_id=body.order_id,
        reason=body.reason,
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
@limiter.limit("60/minute")
async def get_training_order(request: Request, order_id: str):
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
@limiter.limit("30/minute")
async def cleanup_old_sessions(request: Request, hours: int = 24):
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
@limiter.limit("60/minute")
async def check_if_training_order(request: Request, order_id: str):
    """Check if an order ID is a training order."""
    return {
        "order_id": order_id,
        "is_training": is_training_order(order_id),
    }


# ============================================================================
# Training Config & Stats (for settings/training-mode page)
# ============================================================================

@router.get("/config")
@limiter.limit("60/minute")
async def get_training_config(request: Request, db: DbSession):
    """Get training mode configuration."""
    setting = db.query(AppSetting).filter(
        AppSetting.category == "training_config",
        AppSetting.key == "config",
    ).first()

    if setting and setting.value:
        return json.loads(setting.value)

    return {
        "enabled": False,
        "require_pin": False,
        "training_pin": None,
        "auto_end_minutes": 60,
        "show_hints": True,
        "allow_void_practice": True,
        "allow_discount_practice": True,
        "allow_refund_practice": False,
    }


@router.put("/config")
@limiter.limit("30/minute")
async def update_training_config(request: Request, db: DbSession, config: dict = Body(...)):
    """Update training mode configuration."""
    setting = db.query(AppSetting).filter(
        AppSetting.category == "training_config",
        AppSetting.key == "config",
    ).first()

    if setting:
        setting.value = json.dumps(config)
    else:
        setting = AppSetting(
            category="training_config",
            key="config",
            value=json.dumps(config),
        )
        db.add(setting)

    db.commit()
    return {"success": True, **config}


@router.get("/sessions")
@limiter.limit("60/minute")
async def list_training_sessions(request: Request, db: DbSession, limit: int = 20):
    """List all training sessions."""
    service = get_training_service()

    # Batch fetch staff names
    all_sessions = list(service._sessions.values())
    staff_ids = list(set(s.user_id for s in all_sessions))
    staff_map = {}
    if staff_ids:
        staff_list = db.query(StaffUser.id, StaffUser.full_name).filter(
            StaffUser.id.in_(staff_ids)
        ).all()
        staff_map = {s.id: s.full_name for s in staff_list}

    sessions = []
    for sid, s in list(service._sessions.items()):
        sessions.append({
            "session_id": s.session_id,
            "staff_id": s.user_id,
            "staff_name": staff_map.get(s.user_id),
            "started_at": s.started_at.isoformat() if s.started_at else "",
            "ended_at": s.ended_at.isoformat() if s.ended_at else None,
            "orders_created": s.orders_created,
            "payments_processed": s.payments_processed,
            "errors_made": 0,
            "score": None,
            "status": "active" if not s.ended_at else "completed",
        })

    return sessions[:limit]


@router.get("/stats")
@limiter.limit("60/minute")
async def get_training_stats(request: Request):
    """Get training mode statistics."""
    service = get_training_service()
    all_sessions = list(service._sessions.values())
    total_orders = sum(s.orders_created for s in all_sessions)

    return {
        "total_sessions": len(all_sessions),
        "avg_score": 0,
        "total_practice_orders": total_orders,
    }

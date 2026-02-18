"""
Multi-Terminal Bill Sharing API Endpoints
TouchSale feature: Work with the same bill from any terminal
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import json
import asyncio
import logging

from app.db.session import get_db
from app.core.rbac import get_current_user
from app.models import StaffUser, Order, OrderItem, Table, OrderStatus
from app.core.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# SCHEMAS
# =============================================================================

class TerminalSession(BaseModel):
    terminal_id: str = Field(..., description="Unique terminal identifier")
    terminal_name: str = Field(..., description="Human-readable terminal name")
    location: Optional[str] = Field(None, description="Terminal location in venue")


class OrderLockRequest(BaseModel):
    order_id: int
    terminal_id: str
    lock_reason: Optional[str] = Field(None, description="Why terminal is locking order")


class OrderLockResponse(BaseModel):
    success: bool
    order_id: int
    locked_by_terminal: Optional[str]
    locked_at: Optional[datetime]
    message: str


class SharedOrderUpdate(BaseModel):
    order_id: int
    terminal_id: str
    action: str  # add_item, remove_item, update_quantity, apply_discount, add_payment
    data: Dict[str, Any]


class TerminalOrderView(BaseModel):
    order_id: int
    table_number: str
    status: str
    items: List[Dict[str, Any]]
    subtotal: float
    tax: float
    total: float
    payments: List[Dict[str, Any]]
    balance_due: float
    locked_by: Optional[str]
    last_updated: datetime
    updated_by_terminal: Optional[str]


# =============================================================================
# IN-MEMORY STATE (Production should use Redis)
# =============================================================================

# Order locks: {order_id: {"terminal_id": str, "locked_at": datetime, "staff_id": int}}
order_locks: Dict[int, Dict[str, Any]] = {}

# Active terminal sessions: {terminal_id: {"staff_id": int, "connected_at": datetime, "order_ids": []}}
terminal_sessions: Dict[str, Dict[str, Any]] = {}

# WebSocket connections for real-time updates
terminal_connections: Dict[str, WebSocket] = {}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def is_order_locked(order_id: int) -> bool:
    """Check if an order is currently locked by any terminal"""
    return order_id in order_locks


def get_order_lock_info(order_id: int) -> Optional[Dict[str, Any]]:
    """Get lock information for an order"""
    return order_locks.get(order_id)


def can_modify_order(order_id: int, terminal_id: str) -> bool:
    """Check if a terminal can modify an order"""
    if order_id not in order_locks:
        return True
    return order_locks[order_id]["terminal_id"] == terminal_id


async def broadcast_order_update(order_id: int, update_data: Dict[str, Any], exclude_terminal: str = None):
    """Broadcast order update to all connected terminals"""
    message = json.dumps({
        "type": "order_update",
        "order_id": order_id,
        "data": update_data,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

    for terminal_id, ws in terminal_connections.items():
        if terminal_id != exclude_terminal:
            try:
                await ws.send_text(message)
            except Exception as e:
                logger.warning(f"Failed to send WebSocket order update to terminal {terminal_id}: {e}")


# =============================================================================
# TERMINAL SESSION MANAGEMENT
# =============================================================================

@router.get("/")
@limiter.limit("60/minute")
async def get_multi_terminal_root(request: Request, db: Session = Depends(get_db), current_user: StaffUser = Depends(get_current_user)):
    """Multi-terminal overview."""
    return await list_active_terminals(request=request, db=db, current_user=current_user)


@router.post("/session/register")
@limiter.limit("30/minute")
async def register_terminal(
    request: Request,
    data: TerminalSession,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Register a terminal for multi-terminal operations

    Each terminal should register when starting a shift.
    """
    terminal_sessions[data.terminal_id] = {
        "staff_id": current_user.id,
        "staff_name": current_user.full_name,
        "terminal_name": data.terminal_name,
        "location": data.location,
        "venue_id": current_user.venue_id,
        "connected_at": datetime.now(timezone.utc),
        "order_ids": [],
        "active": True
    }

    return {
        "success": True,
        "terminal_id": data.terminal_id,
        "message": f"Terminal '{data.terminal_name}' registered successfully"
    }


@router.post("/session/unregister/{terminal_id}")
@limiter.limit("30/minute")
async def unregister_terminal(
    request: Request,
    terminal_id: str,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Unregister a terminal and release all its locks
    """
    if terminal_id in terminal_sessions:
        del terminal_sessions[terminal_id]

    # Release all locks held by this terminal
    orders_to_unlock = [
        oid for oid, lock in order_locks.items()
        if lock["terminal_id"] == terminal_id
    ]

    for order_id in orders_to_unlock:
        del order_locks[order_id]

    if terminal_id in terminal_connections:
        del terminal_connections[terminal_id]

    return {
        "success": True,
        "message": f"Terminal unregistered, {len(orders_to_unlock)} orders unlocked"
    }


@router.get("/session/list")
@limiter.limit("60/minute")
async def list_active_terminals(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List all active terminals in the venue"""
    venue_terminals = {
        tid: session for tid, session in terminal_sessions.items()
        if session.get("venue_id") == current_user.venue_id and session.get("active")
    }

    return {
        "terminals": [
            {
                "terminal_id": tid,
                "terminal_name": session["terminal_name"],
                "staff_name": session["staff_name"],
                "location": session.get("location"),
                "connected_at": session["connected_at"].isoformat(),
                "orders_count": len(session.get("order_ids", []))
            }
            for tid, session in venue_terminals.items()
        ],
        "total": len(venue_terminals)
    }


# =============================================================================
# ORDER LOCKING
# =============================================================================

@router.post("/orders/{order_id}/lock", response_model=OrderLockResponse)
@limiter.limit("30/minute")
async def lock_order(
    request: Request,
    order_id: int,
    data: OrderLockRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Lock an order for exclusive editing by a terminal

    Used when a terminal needs to make complex modifications
    to prevent conflicts from other terminals.
    """
    # Verify order exists and belongs to venue
    order = db.query(Order).filter(
        Order.id == order_id
    ).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    # Check if already locked
    if is_order_locked(order_id):
        lock_info = get_order_lock_info(order_id)
        if lock_info["terminal_id"] != data.terminal_id:
            return OrderLockResponse(
                success=False,
                order_id=order_id,
                locked_by_terminal=lock_info["terminal_id"],
                locked_at=lock_info["locked_at"],
                message=f"Order is locked by terminal {lock_info['terminal_id']}"
            )

    # Lock the order
    order_locks[order_id] = {
        "terminal_id": data.terminal_id,
        "locked_at": datetime.now(timezone.utc),
        "staff_id": current_user.id,
        "staff_name": current_user.full_name,
        "reason": data.lock_reason
    }

    # Broadcast lock notification
    await broadcast_order_update(order_id, {
        "action": "locked",
        "locked_by": data.terminal_id,
        "staff_name": current_user.full_name
    }, exclude_terminal=data.terminal_id)

    return OrderLockResponse(
        success=True,
        order_id=order_id,
        locked_by_terminal=data.terminal_id,
        locked_at=order_locks[order_id]["locked_at"],
        message="Order locked successfully"
    )


@router.post("/orders/{order_id}/unlock")
@limiter.limit("30/minute")
async def unlock_order(
    request: Request,
    order_id: int,
    terminal_id: str,
    force: bool = False,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Unlock an order for editing by other terminals

    force=True allows managers to unlock orders locked by other terminals
    """
    if not is_order_locked(order_id):
        return {"success": True, "message": "Order was not locked"}

    lock_info = get_order_lock_info(order_id)

    # Check if terminal owns the lock or if force unlock by manager
    if lock_info["terminal_id"] != terminal_id:
        if not force or current_user.role not in ["owner", "manager"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot unlock order locked by another terminal"
            )

    del order_locks[order_id]

    # Broadcast unlock notification
    await broadcast_order_update(order_id, {
        "action": "unlocked",
        "unlocked_by": terminal_id
    }, exclude_terminal=terminal_id)

    return {"success": True, "message": "Order unlocked successfully"}


@router.get("/orders/{order_id}/lock-status")
@limiter.limit("60/minute")
async def get_order_lock_status(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get the lock status of an order"""
    if is_order_locked(order_id):
        lock_info = get_order_lock_info(order_id)
        return {
            "locked": True,
            "terminal_id": lock_info["terminal_id"],
            "staff_name": lock_info.get("staff_name"),
            "locked_at": lock_info["locked_at"].isoformat(),
            "reason": lock_info.get("reason")
        }

    return {"locked": False}


# =============================================================================
# SHARED ORDER OPERATIONS
# =============================================================================

@router.get("/orders/{order_id}/shared-view", response_model=TerminalOrderView)
@limiter.limit("60/minute")
async def get_shared_order_view(
    request: Request,
    order_id: int,
    terminal_id: str = Query("", description="Terminal ID"),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Get a complete view of an order for any terminal

    This is the primary endpoint for viewing orders across terminals.
    """
    order = db.query(Order).filter(Order.id == order_id).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    # Get order items
    items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()

    # Format items
    formatted_items = [
        {
            "id": item.id,
            "menu_item_id": item.menu_item_id,
            "name": item.menu_item.name if item.menu_item else "Unknown",
            "quantity": item.quantity,
            "unit_price": float(item.unit_price),
            "total_price": float(item.total_price),
            "modifiers": item.modifiers,
            "notes": item.notes,
            "status": item.status
        }
        for item in items
    ]

    # Get table info
    table = db.query(Table).filter(Table.id == order.table_id).first() if order.table_id else None

    # Get lock info
    lock_info = get_order_lock_info(order_id)

    return TerminalOrderView(
        order_id=order.id,
        table_number=table.number if table else "N/A",
        status=order.status,
        items=formatted_items,
        subtotal=float(order.subtotal or 0),
        tax=float(order.tax or 0),
        total=float(order.total or 0),
        payments=[],  # Would include payment details
        balance_due=float(order.total or 0) - float(order.paid_amount or 0),
        locked_by=lock_info["terminal_id"] if lock_info else None,
        last_updated=order.updated_at or order.created_at,
        updated_by_terminal=None
    )


@router.post("/orders/{order_id}/shared-update")
@limiter.limit("30/minute")
async def apply_shared_update(
    request: Request,
    order_id: int,
    update: SharedOrderUpdate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Apply an update to an order from any terminal

    Handles optimistic locking for concurrent modifications.
    """
    # Check if order is locked by another terminal
    if not can_modify_order(order_id, update.terminal_id):
        lock_info = get_order_lock_info(order_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Order is locked by terminal {lock_info['terminal_id']}"
        )

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    result = {"success": True, "action": update.action}

    if update.action == "add_item":
        # Add item to order
        item = OrderItem(
            order_id=order_id,
            menu_item_id=update.data.get("menu_item_id"),
            quantity=update.data.get("quantity", 1),
            unit_price=update.data.get("unit_price"),
            total_price=update.data.get("unit_price") * update.data.get("quantity", 1),
            modifiers=update.data.get("modifiers"),
            notes=update.data.get("notes"),
            status="pending"
        )
        db.add(item)
        result["item_id"] = item.id

    elif update.action == "remove_item":
        item = db.query(OrderItem).filter(
            OrderItem.id == update.data.get("item_id"),
            OrderItem.order_id == order_id
        ).first()
        if item:
            db.delete(item)

    elif update.action == "update_quantity":
        item = db.query(OrderItem).filter(
            OrderItem.id == update.data.get("item_id"),
            OrderItem.order_id == order_id
        ).first()
        if item:
            item.quantity = update.data.get("quantity")
            item.total_price = item.unit_price * item.quantity

    elif update.action == "apply_discount":
        order.discount_percent = update.data.get("discount_percent")
        order.discount_amount = update.data.get("discount_amount")

    elif update.action == "add_payment":
        # Handle partial payment
        payment_amount = update.data.get("amount", 0)
        order.paid_amount = (order.paid_amount or 0) + payment_amount

    # Recalculate order totals
    items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
    order.subtotal = sum(item.total_price for item in items)
    order.total = order.subtotal + (order.tax or 0) - (order.discount_amount or 0)
    order.updated_at = datetime.now(timezone.utc)

    db.commit()

    # Broadcast update to other terminals
    await broadcast_order_update(order_id, {
        "action": update.action,
        "data": update.data,
        "updated_by": update.terminal_id,
        "staff_name": current_user.full_name,
        "new_total": float(order.total)
    }, exclude_terminal=update.terminal_id)

    result["new_total"] = float(order.total)
    return result


# =============================================================================
# WEBSOCKET FOR REAL-TIME UPDATES
# =============================================================================

@router.websocket("/ws/{terminal_id}")
async def websocket_terminal_connection(
    websocket: WebSocket,
    terminal_id: str,
    db: Session = Depends(get_db)
):
    """
    WebSocket connection for real-time order updates

    Terminals connect here to receive live updates about orders
    they're watching.
    """
    await websocket.accept()
    terminal_connections[terminal_id] = websocket

    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "terminal_id": terminal_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        # Keep connection alive and handle incoming messages
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)

                # Handle different message types
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})

                elif data.get("type") == "subscribe_order":
                    order_id = data.get("order_id")
                    if terminal_id in terminal_sessions:
                        if order_id not in terminal_sessions[terminal_id].get("order_ids", []):
                            terminal_sessions[terminal_id]["order_ids"].append(order_id)
                    await websocket.send_json({
                        "type": "subscribed",
                        "order_id": order_id
                    })

                elif data.get("type") == "unsubscribe_order":
                    order_id = data.get("order_id")
                    if terminal_id in terminal_sessions:
                        if order_id in terminal_sessions[terminal_id].get("order_ids", []):
                            terminal_sessions[terminal_id]["order_ids"].remove(order_id)

            except asyncio.TimeoutError:
                # Send keepalive
                try:
                    await websocket.send_json({"type": "keepalive"})
                except Exception as e:
                    logger.warning(f"Failed to send WebSocket keepalive to terminal {terminal_id}: {e}")
                    break

    except WebSocketDisconnect:
        pass
    finally:
        # Cleanup on disconnect
        if terminal_id in terminal_connections:
            del terminal_connections[terminal_id]

        # Release any locks held by this terminal
        orders_to_unlock = [
            oid for oid, lock in order_locks.items()
            if lock["terminal_id"] == terminal_id
        ]
        for order_id in orders_to_unlock:
            del order_locks[order_id]
            # Notify other terminals
            await broadcast_order_update(order_id, {
                "action": "unlocked",
                "reason": "terminal_disconnected"
            })


# =============================================================================
# TERMINAL WORKLOAD DISTRIBUTION
# =============================================================================

@router.get("/workload/distribution")
@limiter.limit("60/minute")
async def get_workload_distribution(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Get workload distribution across terminals

    TouchSale feature: Enables proper distribution of terminal workload
    """
    venue_terminals = {
        tid: session for tid, session in terminal_sessions.items()
        if session.get("venue_id") == current_user.venue_id and session.get("active")
    }

    # Count active orders per terminal
    terminal_orders = {}
    for tid, session in venue_terminals.items():
        active_orders = db.query(Order).filter(
            Order.status.in_([OrderStatus.NEW, OrderStatus.ACCEPTED, OrderStatus.PREPARING, OrderStatus.READY]),
            Order.staff_id == session.get("staff_id")
        ).count()

        locked_orders = len([
            oid for oid, lock in order_locks.items()
            if lock["terminal_id"] == tid
        ])

        terminal_orders[tid] = {
            "terminal_name": session["terminal_name"],
            "staff_name": session["staff_name"],
            "active_orders": active_orders,
            "locked_orders": locked_orders,
            "location": session.get("location")
        }

    # Find optimal terminal for new orders
    if terminal_orders:
        optimal_terminal = min(
            terminal_orders.keys(),
            key=lambda t: terminal_orders[t]["active_orders"]
        )
    else:
        optimal_terminal = None

    return {
        "terminals": terminal_orders,
        "optimal_terminal": optimal_terminal,
        "total_active_terminals": len(venue_terminals)
    }


@router.post("/workload/transfer-order")
@limiter.limit("30/minute")
async def transfer_order_to_terminal(
    request: Request,
    order_id: int,
    target_terminal_id: str,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Transfer an order to a different terminal

    Useful for load balancing during peak hours
    """
    if target_terminal_id not in terminal_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target terminal not found or not active"
        )

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    # Check if order is locked
    if is_order_locked(order_id):
        lock_info = get_order_lock_info(order_id)
        if lock_info["terminal_id"] != target_terminal_id:
            del order_locks[order_id]

    target_session = terminal_sessions[target_terminal_id]

    # Add to target terminal's order list
    if order_id not in target_session.get("order_ids", []):
        target_session.setdefault("order_ids", []).append(order_id)

    # Broadcast transfer notification
    await broadcast_order_update(order_id, {
        "action": "transferred",
        "to_terminal": target_terminal_id,
        "to_terminal_name": target_session["terminal_name"]
    })

    return {
        "success": True,
        "message": f"Order transferred to {target_session['terminal_name']}"
    }

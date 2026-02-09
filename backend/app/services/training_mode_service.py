"""Training/Sandbox Mode Service.

Allows staff to practice using the POS system without affecting real data.
Training mode orders don't affect inventory, don't trigger fiscal printing,
and are clearly marked as training data.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class TrainingModeStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


@dataclass
class TrainingSession:
    """A training session for a user."""
    session_id: str
    user_id: int
    terminal_id: Optional[str] = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: Optional[datetime] = None
    orders_created: int = 0
    payments_processed: int = 0
    notes: str = ""


@dataclass
class TrainingOrder:
    """A training order (doesn't affect real data)."""
    order_id: str
    session_id: str
    user_id: int
    table_number: str
    items: List[Dict[str, Any]]
    subtotal: float
    tax: float
    total: float
    payment_method: Optional[str] = None
    status: str = "open"
    created_at: datetime = field(default_factory=datetime.utcnow)


class TrainingModeService:
    """Service for managing training/sandbox mode.

    Training mode features:
    - Orders created in training mode are prefixed with "TR-"
    - Training orders don't affect inventory levels
    - Training orders don't trigger fiscal printing
    - Training orders don't appear in reports (unless specifically filtered)
    - Training sessions track performance metrics for staff
    """

    # In-memory storage for training sessions and orders
    # In production, you might want to persist this to a database
    _sessions: Dict[str, TrainingSession] = {}
    _orders: Dict[str, TrainingOrder] = {}
    _active_users: Dict[int, str] = {}  # user_id -> session_id
    _active_terminals: Dict[str, str] = {}  # terminal_id -> session_id

    def __init__(self):
        pass

    # =========================================================================
    # Session Management
    # =========================================================================

    def start_training_session(
        self,
        user_id: int,
        terminal_id: Optional[str] = None,
        notes: str = "",
    ) -> TrainingSession:
        """Start a new training session for a user."""
        # Check if user already has active session
        if user_id in self._active_users:
            existing_session_id = self._active_users[user_id]
            if existing_session_id in self._sessions:
                logger.warning(f"User {user_id} already has active training session")
                return self._sessions[existing_session_id]

        # Create new session
        session_id = f"TS-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{user_id}"
        session = TrainingSession(
            session_id=session_id,
            user_id=user_id,
            terminal_id=terminal_id,
            notes=notes,
        )

        self._sessions[session_id] = session
        self._active_users[user_id] = session_id

        if terminal_id:
            self._active_terminals[terminal_id] = session_id

        logger.info(f"Started training session {session_id} for user {user_id}")
        return session

    def end_training_session(
        self,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None,
        terminal_id: Optional[str] = None,
    ) -> Optional[TrainingSession]:
        """End a training session."""
        # Find the session
        sid = session_id
        if not sid and user_id and user_id in self._active_users:
            sid = self._active_users[user_id]
        if not sid and terminal_id and terminal_id in self._active_terminals:
            sid = self._active_terminals[terminal_id]

        if not sid or sid not in self._sessions:
            logger.warning(f"No active training session found")
            return None

        session = self._sessions[sid]
        session.ended_at = datetime.now(timezone.utc)

        # Clean up active mappings
        if session.user_id in self._active_users:
            del self._active_users[session.user_id]
        if session.terminal_id and session.terminal_id in self._active_terminals:
            del self._active_terminals[session.terminal_id]

        logger.info(f"Ended training session {sid}")
        return session

    def get_active_session(
        self,
        user_id: Optional[int] = None,
        terminal_id: Optional[str] = None,
    ) -> Optional[TrainingSession]:
        """Get active training session for a user or terminal."""
        sid = None
        if user_id and user_id in self._active_users:
            sid = self._active_users[user_id]
        elif terminal_id and terminal_id in self._active_terminals:
            sid = self._active_terminals[terminal_id]

        if sid and sid in self._sessions:
            return self._sessions[sid]
        return None

    def is_training_mode(
        self,
        user_id: Optional[int] = None,
        terminal_id: Optional[str] = None,
    ) -> bool:
        """Check if user or terminal is in training mode."""
        return self.get_active_session(user_id, terminal_id) is not None

    # =========================================================================
    # Order Management
    # =========================================================================

    def create_training_order(
        self,
        user_id: int,
        table_number: str,
        items: List[Dict[str, Any]],
    ) -> Optional[TrainingOrder]:
        """Create a training order."""
        session = self.get_active_session(user_id=user_id)
        if not session:
            logger.warning(f"User {user_id} not in training mode")
            return None

        # Calculate totals
        subtotal = sum(
            item.get("price", 0) * item.get("quantity", 1)
            for item in items
        )
        tax = subtotal * 0.1  # 10% tax for training
        total = subtotal + tax

        # Create training order
        order_id = f"TR-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{session.orders_created + 1}"
        order = TrainingOrder(
            order_id=order_id,
            session_id=session.session_id,
            user_id=user_id,
            table_number=table_number,
            items=items,
            subtotal=subtotal,
            tax=tax,
            total=total,
        )

        self._orders[order_id] = order
        session.orders_created += 1

        logger.info(f"Created training order {order_id}")
        return order

    def process_training_payment(
        self,
        order_id: str,
        payment_method: str,
    ) -> Optional[TrainingOrder]:
        """Process a training payment."""
        if order_id not in self._orders:
            logger.warning(f"Training order {order_id} not found")
            return None

        order = self._orders[order_id]
        order.payment_method = payment_method
        order.status = "paid"

        # Update session stats
        session = self._sessions.get(order.session_id)
        if session:
            session.payments_processed += 1

        logger.info(f"Processed training payment for {order_id}")
        return order

    def void_training_order(
        self,
        order_id: str,
        reason: str = "",
    ) -> Optional[TrainingOrder]:
        """Void a training order."""
        if order_id not in self._orders:
            logger.warning(f"Training order {order_id} not found")
            return None

        order = self._orders[order_id]
        order.status = "voided"

        logger.info(f"Voided training order {order_id}: {reason}")
        return order

    def get_training_order(self, order_id: str) -> Optional[TrainingOrder]:
        """Get a training order."""
        return self._orders.get(order_id)

    def get_session_orders(self, session_id: str) -> List[TrainingOrder]:
        """Get all orders for a training session."""
        return [
            order for order in self._orders.values()
            if order.session_id == session_id
        ]

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a training session."""
        session = self._sessions.get(session_id)
        if not session:
            return {}

        orders = self.get_session_orders(session_id)
        total_sales = sum(o.total for o in orders if o.status == "paid")
        average_ticket = total_sales / len(orders) if orders else 0

        duration = None
        if session.ended_at:
            ended = session.ended_at.replace(tzinfo=timezone.utc) if session.ended_at.tzinfo is None else session.ended_at
            started = session.started_at.replace(tzinfo=timezone.utc) if session.started_at.tzinfo is None else session.started_at
            duration = (ended - started).total_seconds() / 60
        elif session.started_at:
            started = session.started_at.replace(tzinfo=timezone.utc) if session.started_at.tzinfo is None else session.started_at
            duration = (datetime.now(timezone.utc) - started).total_seconds() / 60

        return {
            "session_id": session_id,
            "user_id": session.user_id,
            "started_at": session.started_at.isoformat(),
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
            "duration_minutes": round(duration, 1) if duration else None,
            "orders_created": session.orders_created,
            "payments_processed": session.payments_processed,
            "total_sales": round(total_sales, 2),
            "average_ticket": round(average_ticket, 2),
            "orders": [
                {
                    "order_id": o.order_id,
                    "table": o.table_number,
                    "total": o.total,
                    "status": o.status,
                }
                for o in orders
            ],
        }

    def get_all_active_sessions(self) -> List[Dict[str, Any]]:
        """Get all active training sessions."""
        active = []
        for user_id, session_id in self._active_users.items():
            session = self._sessions.get(session_id)
            if session:
                active.append({
                    "session_id": session_id,
                    "user_id": user_id,
                    "terminal_id": session.terminal_id,
                    "started_at": session.started_at.isoformat(),
                    "orders_created": session.orders_created,
                })
        return active

    # =========================================================================
    # Cleanup
    # =========================================================================

    def cleanup_old_sessions(self, hours: int = 24):
        """Clean up training sessions older than specified hours."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        removed_sessions = []
        removed_orders = []

        for session_id, session in list(self._sessions.items()):
            if session.ended_at and session.ended_at < cutoff:
                removed_sessions.append(session_id)
                del self._sessions[session_id]

        for order_id, order in list(self._orders.items()):
            if order.session_id in removed_sessions:
                removed_orders.append(order_id)
                del self._orders[order_id]

        logger.info(
            f"Cleaned up {len(removed_sessions)} sessions and "
            f"{len(removed_orders)} orders older than {hours} hours"
        )

        return {
            "sessions_removed": len(removed_sessions),
            "orders_removed": len(removed_orders),
        }


# Singleton instance
_training_service: Optional[TrainingModeService] = None


def get_training_service() -> TrainingModeService:
    """Get the training mode service singleton."""
    global _training_service
    if _training_service is None:
        _training_service = TrainingModeService()
    return _training_service


# Context manager for checking training mode in routes
@contextmanager
def training_mode_context(user_id: int):
    """Context manager that indicates if operations should use training mode."""
    service = get_training_service()
    is_training = service.is_training_mode(user_id=user_id)
    yield is_training


def is_training_order(order_id: str) -> bool:
    """Check if an order ID is a training order."""
    return order_id.startswith("TR-")

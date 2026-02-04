"""EMV Card Terminal Service.

Handles integration with hardware card terminals via Stripe Terminal SDK.
Supports chip card, contactless, and swipe payments.
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class TerminalStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    ERROR = "error"


class TerminalType(str, Enum):
    STRIPE_S700 = "stripe_s700"  # Stripe Reader S700
    STRIPE_M2 = "stripe_m2"  # Stripe Reader M2
    STRIPE_WISEPOS_E = "stripe_wisepos_e"  # WisePOS E
    VERIFONE_P400 = "verifone_p400"
    BBPOS_CHIPPER = "bbpos_chipper"
    BBPOS_WISEPAD3 = "bbpos_wisepad3"


class PaymentEntryMode(str, Enum):
    CHIP = "chip"  # EMV chip
    CONTACTLESS = "contactless"  # NFC tap
    SWIPE = "swipe"  # Magnetic stripe
    MANUAL = "manual"  # Key entry


class TerminalPaymentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    REQUIRES_CONFIRMATION = "requires_confirmation"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


@dataclass
class CardTerminal:
    """A registered card terminal."""
    terminal_id: str
    stripe_terminal_id: Optional[str] = None
    name: str = ""
    terminal_type: TerminalType = TerminalType.STRIPE_S700
    serial_number: Optional[str] = None
    location_id: Optional[str] = None
    venue_id: Optional[int] = None
    status: TerminalStatus = TerminalStatus.OFFLINE
    ip_address: Optional[str] = None
    firmware_version: Optional[str] = None
    last_seen: Optional[datetime] = None
    registered_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TerminalPayment:
    """A payment processed through a card terminal."""
    payment_id: str
    terminal_id: str
    order_id: str
    amount: int  # Amount in cents
    currency: str
    status: TerminalPaymentStatus
    entry_mode: Optional[PaymentEntryMode] = None
    stripe_payment_intent_id: Optional[str] = None
    card_brand: Optional[str] = None
    card_last4: Optional[str] = None
    cardholder_name: Optional[str] = None
    auth_code: Optional[str] = None
    receipt_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


@dataclass
class ConnectionToken:
    """A connection token for terminal SDK."""
    secret: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


class CardTerminalService:
    """Service for EMV card terminal integration.

    Uses Stripe Terminal for:
    - Terminal registration and management
    - Connection token generation for SDK
    - Payment intent creation for terminal payments
    - Payment processing and confirmation
    """

    def __init__(self, stripe_service=None):
        self.stripe_service = stripe_service

        # In-memory storage
        self._terminals: Dict[str, CardTerminal] = {}
        self._payments: Dict[str, TerminalPayment] = {}
        self._connection_tokens: List[ConnectionToken] = []

    # =========================================================================
    # Terminal Registration
    # =========================================================================

    def register_terminal(
        self,
        name: str,
        terminal_type: TerminalType,
        registration_code: Optional[str] = None,
        venue_id: Optional[int] = None,
        location_id: Optional[str] = None,
    ) -> CardTerminal:
        """Register a new card terminal.

        For Stripe Terminal, provide the registration code from the terminal.
        """
        terminal_id = f"term-{uuid.uuid4().hex[:8]}"

        # In production, register with Stripe Terminal API
        stripe_terminal_id = f"tmr_{uuid.uuid4().hex}"

        terminal = CardTerminal(
            terminal_id=terminal_id,
            stripe_terminal_id=stripe_terminal_id,
            name=name,
            terminal_type=terminal_type,
            venue_id=venue_id,
            location_id=location_id,
            status=TerminalStatus.OFFLINE,
        )

        self._terminals[terminal_id] = terminal
        logger.info(f"Registered terminal {terminal_id}: {name}")

        return terminal

    def update_terminal(self, terminal_id: str, **updates) -> Optional[CardTerminal]:
        """Update terminal information."""
        terminal = self._terminals.get(terminal_id)
        if not terminal:
            return None

        for key, value in updates.items():
            if hasattr(terminal, key) and value is not None:
                setattr(terminal, key, value)

        return terminal

    def get_terminal(self, terminal_id: str) -> Optional[CardTerminal]:
        """Get terminal by ID."""
        return self._terminals.get(terminal_id)

    def list_terminals(
        self,
        venue_id: Optional[int] = None,
        status: Optional[TerminalStatus] = None,
    ) -> List[CardTerminal]:
        """List registered terminals."""
        terminals = list(self._terminals.values())

        if venue_id is not None:
            terminals = [t for t in terminals if t.venue_id == venue_id]

        if status:
            terminals = [t for t in terminals if t.status == status]

        return terminals

    def delete_terminal(self, terminal_id: str) -> bool:
        """Delete a terminal registration."""
        if terminal_id in self._terminals:
            del self._terminals[terminal_id]
            return True
        return False

    def update_terminal_status(
        self,
        terminal_id: str,
        status: TerminalStatus,
        ip_address: Optional[str] = None,
    ) -> Optional[CardTerminal]:
        """Update terminal status (called by terminal heartbeat)."""
        terminal = self._terminals.get(terminal_id)
        if not terminal:
            return None

        terminal.status = status
        terminal.last_seen = datetime.utcnow()
        if ip_address:
            terminal.ip_address = ip_address

        return terminal

    # =========================================================================
    # Connection Token
    # =========================================================================

    def create_connection_token(self, location_id: Optional[str] = None) -> ConnectionToken:
        """Create a connection token for terminal SDK.

        The POS app uses this token to connect to Stripe Terminal.
        Tokens expire after a short time and should be fetched fresh.
        """
        # In production, call Stripe API to create connection token
        # stripe.terminal.ConnectionToken.create(location=location_id)

        token = ConnectionToken(
            secret=f"pst_test_{uuid.uuid4().hex}",
            expires_at=datetime.utcnow(),
        )

        self._connection_tokens.append(token)
        logger.info("Created connection token for terminal SDK")

        return token

    # =========================================================================
    # Payment Processing
    # =========================================================================

    def create_payment_intent(
        self,
        terminal_id: str,
        order_id: str,
        amount: int,
        currency: str = "usd",
        description: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Create a payment intent for terminal payment.

        Returns the PaymentIntent that the terminal SDK will use
        to collect the payment.
        """
        terminal = self._terminals.get(terminal_id)
        if not terminal:
            return {"error": "Terminal not found"}

        if terminal.status != TerminalStatus.ONLINE:
            return {"error": "Terminal is not online"}

        # In production, create Stripe PaymentIntent
        payment_intent_id = f"pi_{uuid.uuid4().hex}"

        # Create local payment record
        payment = TerminalPayment(
            payment_id=f"tp-{uuid.uuid4().hex[:8]}",
            terminal_id=terminal_id,
            order_id=order_id,
            amount=amount,
            currency=currency,
            status=TerminalPaymentStatus.PENDING,
            stripe_payment_intent_id=payment_intent_id,
        )

        self._payments[payment.payment_id] = payment

        logger.info(f"Created terminal payment {payment.payment_id} for {amount} cents")

        return {
            "payment_id": payment.payment_id,
            "payment_intent_id": payment_intent_id,
            "client_secret": f"{payment_intent_id}_secret_{uuid.uuid4().hex[:8]}",
            "amount": amount,
            "currency": currency,
            "terminal_id": terminal_id,
        }

    def process_payment(
        self,
        payment_id: str,
        entry_mode: PaymentEntryMode,
        card_brand: Optional[str] = None,
        card_last4: Optional[str] = None,
        cardholder_name: Optional[str] = None,
        auth_code: Optional[str] = None,
    ) -> Optional[TerminalPayment]:
        """Process a terminal payment after card read.

        Called after the terminal SDK reads the card and processes payment.
        """
        payment = self._payments.get(payment_id)
        if not payment:
            return None

        payment.status = TerminalPaymentStatus.PROCESSING
        payment.entry_mode = entry_mode
        payment.card_brand = card_brand
        payment.card_last4 = card_last4
        payment.cardholder_name = cardholder_name
        payment.auth_code = auth_code

        # In production, Stripe handles the actual processing
        # Simulate success
        payment.status = TerminalPaymentStatus.SUCCEEDED
        payment.completed_at = datetime.utcnow()
        payment.receipt_url = f"https://pay.stripe.com/receipts/{payment.stripe_payment_intent_id}"

        logger.info(f"Processed terminal payment {payment_id}: {payment.status.value}")

        return payment

    def cancel_payment(self, payment_id: str, reason: str = "") -> Optional[TerminalPayment]:
        """Cancel a pending terminal payment."""
        payment = self._payments.get(payment_id)
        if not payment:
            return None

        if payment.status not in (TerminalPaymentStatus.PENDING, TerminalPaymentStatus.PROCESSING):
            return None

        payment.status = TerminalPaymentStatus.CANCELED
        payment.error_message = reason

        logger.info(f"Canceled terminal payment {payment_id}")

        return payment

    def fail_payment(self, payment_id: str, error_message: str) -> Optional[TerminalPayment]:
        """Mark a payment as failed."""
        payment = self._payments.get(payment_id)
        if not payment:
            return None

        payment.status = TerminalPaymentStatus.FAILED
        payment.error_message = error_message

        logger.info(f"Failed terminal payment {payment_id}: {error_message}")

        return payment

    # =========================================================================
    # Payment Retrieval
    # =========================================================================

    def get_payment(self, payment_id: str) -> Optional[TerminalPayment]:
        """Get a terminal payment by ID."""
        return self._payments.get(payment_id)

    def get_payments_by_terminal(
        self,
        terminal_id: str,
        limit: int = 50,
    ) -> List[TerminalPayment]:
        """Get payments for a terminal."""
        payments = [p for p in self._payments.values() if p.terminal_id == terminal_id]
        return sorted(payments, key=lambda p: p.created_at, reverse=True)[:limit]

    def get_payments_by_order(self, order_id: str) -> List[TerminalPayment]:
        """Get payments for an order."""
        return [p for p in self._payments.values() if p.order_id == order_id]

    def list_payments(
        self,
        status: Optional[TerminalPaymentStatus] = None,
        entry_mode: Optional[PaymentEntryMode] = None,
        limit: int = 50,
    ) -> List[TerminalPayment]:
        """List terminal payments."""
        payments = list(self._payments.values())

        if status:
            payments = [p for p in payments if p.status == status]

        if entry_mode:
            payments = [p for p in payments if p.entry_mode == entry_mode]

        return sorted(payments, key=lambda p: p.created_at, reverse=True)[:limit]

    # =========================================================================
    # Terminal Actions
    # =========================================================================

    def display_message(self, terminal_id: str, message: str) -> bool:
        """Display a message on the terminal screen."""
        terminal = self._terminals.get(terminal_id)
        if not terminal or terminal.status != TerminalStatus.ONLINE:
            return False

        # In production, call Stripe Terminal API
        logger.info(f"Displaying message on {terminal_id}: {message}")
        return True

    def clear_display(self, terminal_id: str) -> bool:
        """Clear the terminal display."""
        terminal = self._terminals.get(terminal_id)
        if not terminal or terminal.status != TerminalStatus.ONLINE:
            return False

        logger.info(f"Cleared display on {terminal_id}")
        return True

    def set_reader_display(
        self,
        terminal_id: str,
        cart_items: List[Dict[str, Any]],
        total: int,
        currency: str = "usd",
    ) -> bool:
        """Set the cart display on the terminal."""
        terminal = self._terminals.get(terminal_id)
        if not terminal or terminal.status != TerminalStatus.ONLINE:
            return False

        # In production, call Stripe Terminal setReaderDisplay
        logger.info(f"Set cart display on {terminal_id}: {len(cart_items)} items, total {total}")
        return True

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get terminal payment statistics."""
        payments = list(self._payments.values())
        terminals = list(self._terminals.values())

        succeeded = [p for p in payments if p.status == TerminalPaymentStatus.SUCCEEDED]
        failed = [p for p in payments if p.status == TerminalPaymentStatus.FAILED]

        chip_count = sum(1 for p in succeeded if p.entry_mode == PaymentEntryMode.CHIP)
        contactless_count = sum(1 for p in succeeded if p.entry_mode == PaymentEntryMode.CONTACTLESS)
        swipe_count = sum(1 for p in succeeded if p.entry_mode == PaymentEntryMode.SWIPE)

        total_amount = sum(p.amount for p in succeeded)

        online_terminals = sum(1 for t in terminals if t.status == TerminalStatus.ONLINE)

        return {
            "total_terminals": len(terminals),
            "online_terminals": online_terminals,
            "total_payments": len(payments),
            "succeeded_payments": len(succeeded),
            "failed_payments": len(failed),
            "success_rate": round(len(succeeded) / len(payments) * 100, 2) if payments else 0,
            "by_entry_mode": {
                "chip": chip_count,
                "contactless": contactless_count,
                "swipe": swipe_count,
            },
            "total_amount_cents": total_amount,
            "total_amount": round(total_amount / 100, 2),
        }


# Singleton instance
_card_terminal_service: Optional[CardTerminalService] = None


def get_card_terminal_service() -> CardTerminalService:
    """Get the card terminal service singleton."""
    global _card_terminal_service
    if _card_terminal_service is None:
        _card_terminal_service = CardTerminalService()
    return _card_terminal_service

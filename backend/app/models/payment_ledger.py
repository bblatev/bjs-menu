"""
Payment Ledger Models - Immutable Audit Trail for All Payment Operations

MONEY-CRITICAL: These models provide immutable audit trails for all
payment operations. Once created, ledger entries cannot be modified.

Key Features:
- Immutable entries (append-only)
- Idempotency key support
- Complete audit trail
- Cash variance tracking and alerts
"""

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey,
    Text, JSON, Enum, Index, Numeric, CheckConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum
import hashlib
import uuid

from app.db.base import Base


class LedgerEntryType(str, enum.Enum):
    """Types of ledger entries."""
    PAYMENT_RECEIVED = "payment_received"
    PAYMENT_REFUNDED = "payment_refunded"
    PAYMENT_VOIDED = "payment_voided"
    TIP_RECEIVED = "tip_received"
    TIP_ADJUSTED = "tip_adjusted"
    CASH_IN = "cash_in"
    CASH_OUT = "cash_out"
    CASH_DROP = "cash_drop"
    CASH_VARIANCE = "cash_variance"
    ADJUSTMENT = "adjustment"


class PaymentLedgerEntry(Base):
    """
    Immutable payment ledger entry.

    Once created, these entries CANNOT be modified or deleted.
    Corrections must be made via new offsetting entries.
    """
    __tablename__ = "payment_ledger"
    __table_args__ = (
        Index('idx_ledger_venue_date', 'venue_id', 'created_at'),
        Index('idx_ledger_order', 'order_id'),
        Index('idx_ledger_idempotency', 'idempotency_key'),
        Index('idx_ledger_type', 'entry_type'),
        {'extend_existing': True}
    )

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)

    # Idempotency - prevents duplicate entries
    idempotency_key = Column(String(64), unique=True, nullable=False, index=True)

    # Entry details
    entry_type = Column(Enum(LedgerEntryType), nullable=False)
    entry_number = Column(String(50), nullable=False)  # Sequential number

    # Related entities
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    payment_intent_id = Column(Integer, nullable=True)  # Reference to PaymentIntent
    staff_user_id = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    shift_id = Column(Integer, nullable=True)  # Reference to shift if applicable

    # Money amounts (all in smallest currency unit to avoid float issues)
    amount_cents = Column(Integer, nullable=False)  # Amount in cents/stotinki
    currency = Column(String(3), default="BGN")

    # Payment method details
    payment_method = Column(String(50), nullable=False)  # cash, card, voucher
    payment_method_detail = Column(String(100), nullable=True)  # card last 4, etc.

    # Audit trail
    description = Column(String(500), nullable=True)
    reference = Column(String(100), nullable=True)  # External reference
    extra_data = Column(JSON, nullable=True)  # Additional context

    # Integrity
    previous_entry_id = Column(Integer, ForeignKey("payment_ledger.id"), nullable=True)
    entry_hash = Column(String(64), nullable=False)  # SHA-256 of entry data

    # Timestamps (immutable - no updated_at)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    business_date = Column(DateTime(timezone=True), nullable=False)  # Business day

    # Relationships
    venue = relationship("Venue", backref="payment_ledger_entries")
    order = relationship("Order", backref="ledger_entries")
    staff_user = relationship("StaffUser", backref="ledger_entries")
    previous_entry = relationship("PaymentLedgerEntry", remote_side=[id])

    def __init__(self, **kwargs):
        """Generate idempotency key and hash on creation."""
        # Generate idempotency key if not provided
        if 'idempotency_key' not in kwargs:
            kwargs['idempotency_key'] = str(uuid.uuid4())

        # Set business date if not provided
        if 'business_date' not in kwargs:
            kwargs['business_date'] = datetime.utcnow()

        super().__init__(**kwargs)

        # Generate entry hash after all fields are set
        self.entry_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        """Compute SHA-256 hash of entry data for integrity verification."""
        data = f"{self.venue_id}|{self.entry_type}|{self.amount_cents}|" \
               f"{self.currency}|{self.order_id}|{self.payment_method}|" \
               f"{self.created_at}|{self.previous_entry_id}"
        return hashlib.sha256(data.encode()).hexdigest()

    def verify_integrity(self) -> bool:
        """Verify entry has not been tampered with."""
        return self.entry_hash == self._compute_hash()


class IdempotencyKey(Base):
    """
    Track idempotency keys for payment operations.

    Prevents duplicate payment processing due to retries/network issues.
    Keys expire after 24 hours.
    """
    __tablename__ = "idempotency_keys"
    __table_args__ = (
        Index('idx_idemp_key', 'key'),
        Index('idx_idemp_expires', 'expires_at'),
        {'extend_existing': True}
    )

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(64), unique=True, nullable=False, index=True)

    # Request details
    request_path = Column(String(200), nullable=False)
    request_method = Column(String(10), nullable=False)
    request_hash = Column(String(64), nullable=False)  # Hash of request body

    # Response (cached)
    response_status = Column(Integer, nullable=True)
    response_body = Column(JSON, nullable=True)

    # State
    is_processing = Column(Boolean, default=True)
    is_completed = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    # Related ledger entry
    ledger_entry_id = Column(Integer, ForeignKey("payment_ledger.id"), nullable=True)


class CashVarianceAlert(Base):
    """
    Cash variance alerts for anti-theft detection.

    Generated when cash drawer count differs from expected amount.
    """
    __tablename__ = "cash_variance_alerts"
    __table_args__ = (
        Index('idx_variance_venue_date', 'venue_id', 'created_at'),
        Index('idx_variance_severity', 'severity'),
        {'extend_existing': True}
    )

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)

    # Variance details
    business_date = Column(DateTime(timezone=True), nullable=False)
    shift_id = Column(Integer, nullable=True)
    drawer_id = Column(String(50), nullable=True)  # If multiple drawers

    expected_amount_cents = Column(Integer, nullable=False)
    actual_amount_cents = Column(Integer, nullable=False)
    variance_cents = Column(Integer, nullable=False)
    variance_percentage = Column(Numeric(5, 2), nullable=False)

    # Severity based on variance amount
    severity = Column(String(20), nullable=False)  # low, medium, high, critical

    # Context
    staff_user_id = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    transactions_count = Column(Integer, default=0)
    cash_sales_total_cents = Column(Integer, default=0)

    # Resolution
    is_resolved = Column(Boolean, default=False)
    resolved_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)

    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    venue = relationship("Venue", backref="cash_variance_alerts")
    staff_user = relationship("StaffUser", foreign_keys=[staff_user_id])
    resolved_by_user = relationship("StaffUser", foreign_keys=[resolved_by])


class PaymentAuditLog(Base):
    """
    Detailed audit log for all payment-related actions.

    Records who did what, when, and from where.
    """
    __tablename__ = "payment_audit_logs"
    __table_args__ = (
        Index('idx_payment_audit_venue_date', 'venue_id', 'created_at'),
        Index('idx_payment_audit_action', 'action'),
        {'extend_existing': True}
    )

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)

    # Action details
    action = Column(String(50), nullable=False)  # create_payment, void_payment, refund, etc.
    action_detail = Column(String(200), nullable=True)

    # Related entities
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    ledger_entry_id = Column(Integer, ForeignKey("payment_ledger.id"), nullable=True)

    # Actor
    staff_user_id = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    terminal_id = Column(String(50), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)

    # Data (before/after for changes)
    old_data = Column(JSON, nullable=True)
    new_data = Column(JSON, nullable=True)

    # Result
    was_successful = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)

    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    venue = relationship("Venue", backref="payment_audit_logs")
    order = relationship("Order", backref="payment_audit_logs")
    staff_user = relationship("StaffUser", backref="payment_audit_logs")

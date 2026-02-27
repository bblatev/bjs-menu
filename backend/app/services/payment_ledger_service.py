"""
Payment Ledger Service

Handles immutable payment recording, idempotency key management,
and cash variance detection.

MONEY-CRITICAL: All payment operations MUST go through this service
when LEDGER_ENABLED feature flag is active.
"""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, Dict, Any, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.feature_flags import is_enabled
from app.models.payment_ledger import (
    PaymentLedgerEntry,
    LedgerEntryType,
    IdempotencyKey,
    CashVarianceAlert,
    PaymentAuditLog,
)


class PaymentLedgerService:
    """
    Service for recording payments to immutable ledger.

    All methods check the LEDGER_ENABLED feature flag and gracefully
    degrade to no-op when disabled (maintaining backwards compatibility).
    """

    # Cash variance thresholds (in cents)
    VARIANCE_THRESHOLD_LOW = 500  # 5 BGN
    VARIANCE_THRESHOLD_MEDIUM = 2000  # 20 BGN
    VARIANCE_THRESHOLD_HIGH = 5000  # 50 BGN
    VARIANCE_THRESHOLD_CRITICAL = 10000  # 100 BGN

    def __init__(self, db: Session):
        self.db = db

    def is_active(self) -> bool:
        """Check if ledger feature is enabled."""
        return is_enabled("LEDGER_ENABLED")

    def record_payment(
        self,
        venue_id: int,
        amount: Decimal,
        payment_method: str,
        order_id: Optional[int] = None,
        staff_user_id: Optional[int] = None,
        idempotency_key: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        currency: str = "BGN",
    ) -> Optional[PaymentLedgerEntry]:
        """
        Record a payment to the immutable ledger.

        Args:
            venue_id: Venue ID
            amount: Payment amount (Decimal)
            payment_method: Payment method (cash, card, etc.)
            order_id: Related order ID
            staff_user_id: Staff user processing payment
            idempotency_key: Unique key for deduplication
            description: Payment description
            metadata: Additional context
            currency: Currency code

        Returns:
            PaymentLedgerEntry if created, None if feature disabled
        """
        if not self.is_active():
            return None

        # Check idempotency
        if idempotency_key:
            existing = self._check_idempotency(idempotency_key)
            if existing:
                return existing

        # Convert to cents
        amount_cents = int(amount * 100)

        # Get previous entry for chain
        previous_entry = self.db.query(PaymentLedgerEntry).filter(
            PaymentLedgerEntry.venue_id == venue_id
        ).order_by(PaymentLedgerEntry.id.desc()).first()

        # Generate entry number
        entry_number = self._generate_entry_number(venue_id)

        # Create entry
        entry = PaymentLedgerEntry(
            venue_id=venue_id,
            idempotency_key=idempotency_key or str(uuid.uuid4()),
            entry_type=LedgerEntryType.PAYMENT_RECEIVED,
            entry_number=entry_number,
            order_id=order_id,
            staff_user_id=staff_user_id,
            amount_cents=amount_cents,
            currency=currency,
            payment_method=payment_method,
            description=description,
            extra_data=metadata,
            previous_entry_id=previous_entry.id if previous_entry else None,
            business_date=datetime.now(timezone.utc),
        )

        try:
            with self.db.begin_nested():
                self.db.add(entry)
                self.db.flush()

                # Update idempotency key if provided
                if idempotency_key:
                    self._complete_idempotency(idempotency_key, entry)

                # Audit log
                self._audit_log(
                    venue_id=venue_id,
                    action="payment_recorded",
                    order_id=order_id,
                    ledger_entry_id=entry.id,
                    staff_user_id=staff_user_id,
                    new_data={"amount": str(amount), "method": payment_method}
                )

            self.db.commit()
            self.db.refresh(entry)
        except Exception as e:
            self.db.rollback()
            raise ValueError(f"Failed to record payment: {str(e)}")

        return entry

    def record_refund(
        self,
        venue_id: int,
        amount: Decimal,
        payment_method: str,
        order_id: Optional[int] = None,
        original_payment_id: Optional[int] = None,
        staff_user_id: Optional[int] = None,
        reason: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Optional[PaymentLedgerEntry]:
        """Record a refund to the ledger."""
        if not self.is_active():
            return None

        if idempotency_key:
            existing = self._check_idempotency(idempotency_key)
            if existing:
                return existing

        amount_cents = int(amount * 100)
        entry_number = self._generate_entry_number(venue_id)

        previous_entry = self.db.query(PaymentLedgerEntry).filter(
            PaymentLedgerEntry.venue_id == venue_id
        ).order_by(PaymentLedgerEntry.id.desc()).first()

        entry = PaymentLedgerEntry(
            venue_id=venue_id,
            idempotency_key=idempotency_key or str(uuid.uuid4()),
            entry_type=LedgerEntryType.PAYMENT_REFUNDED,
            entry_number=entry_number,
            order_id=order_id,
            staff_user_id=staff_user_id,
            amount_cents=-amount_cents,  # Negative for refunds
            currency="BGN",
            payment_method=payment_method,
            description=reason or "Refund",
            extra_data={"original_payment_id": original_payment_id},
            previous_entry_id=previous_entry.id if previous_entry else None,
            business_date=datetime.now(timezone.utc),
        )

        try:
            with self.db.begin_nested():
                self.db.add(entry)
                self.db.flush()

                if idempotency_key:
                    self._complete_idempotency(idempotency_key, entry)

                self._audit_log(
                    venue_id=venue_id,
                    action="refund_recorded",
                    order_id=order_id,
                    ledger_entry_id=entry.id,
                    staff_user_id=staff_user_id,
                    new_data={"amount": str(amount), "reason": reason}
                )

            self.db.commit()
            self.db.refresh(entry)
        except Exception as e:
            self.db.rollback()
            raise ValueError(f"Failed to record refund: {str(e)}")

        return entry

    def record_cash_variance(
        self,
        venue_id: int,
        expected_cents: int,
        actual_cents: int,
        staff_user_id: Optional[int] = None,
        shift_id: Optional[int] = None,
        drawer_id: Optional[str] = None,
    ) -> Optional[Tuple[PaymentLedgerEntry, CashVarianceAlert]]:
        """
        Record a cash variance and generate alert if significant.

        Returns tuple of (ledger_entry, alert) or None if feature disabled.
        """
        if not is_enabled("CASH_VARIANCE_ALERTS"):
            return None

        variance_cents = actual_cents - expected_cents

        # Only create alert for significant variances
        if abs(variance_cents) < self.VARIANCE_THRESHOLD_LOW:
            return None

        # Determine severity
        abs_variance = abs(variance_cents)
        if abs_variance >= self.VARIANCE_THRESHOLD_CRITICAL:
            severity = "critical"
        elif abs_variance >= self.VARIANCE_THRESHOLD_HIGH:
            severity = "high"
        elif abs_variance >= self.VARIANCE_THRESHOLD_MEDIUM:
            severity = "medium"
        else:
            severity = "low"

        # Calculate percentage
        variance_percentage = (variance_cents / expected_cents * 100) if expected_cents else 0

        # Create alert
        alert = CashVarianceAlert(
            venue_id=venue_id,
            business_date=datetime.now(timezone.utc),
            shift_id=shift_id,
            drawer_id=drawer_id,
            expected_amount_cents=expected_cents,
            actual_amount_cents=actual_cents,
            variance_cents=variance_cents,
            variance_percentage=round(variance_percentage, 2),
            severity=severity,
            staff_user_id=staff_user_id,
        )

        entry = None

        try:
            with self.db.begin_nested():
                self.db.add(alert)

                # Record in ledger if ledger is active
                if self.is_active():
                    entry_number = self._generate_entry_number(venue_id)
                    previous_entry = self.db.query(PaymentLedgerEntry).filter(
                        PaymentLedgerEntry.venue_id == venue_id
                    ).order_by(PaymentLedgerEntry.id.desc()).first()

                    entry = PaymentLedgerEntry(
                        venue_id=venue_id,
                        idempotency_key=str(uuid.uuid4()),
                        entry_type=LedgerEntryType.CASH_VARIANCE,
                        entry_number=entry_number,
                        staff_user_id=staff_user_id,
                        amount_cents=variance_cents,
                        currency="BGN",
                        payment_method="cash",
                        description=f"Cash variance: {severity}",
                        extra_data={
                            "expected": expected_cents,
                            "actual": actual_cents,
                            "severity": severity,
                            "shift_id": shift_id,
                        },
                        previous_entry_id=previous_entry.id if previous_entry else None,
                        business_date=datetime.now(timezone.utc),
                    )
                    self.db.add(entry)

                self.db.flush()

                self._audit_log(
                    venue_id=venue_id,
                    action="cash_variance_detected",
                    staff_user_id=staff_user_id,
                    new_data={
                        "expected": expected_cents,
                        "actual": actual_cents,
                        "variance": variance_cents,
                        "severity": severity,
                    }
                )

            self.db.commit()

            if entry:
                self.db.refresh(entry)
            self.db.refresh(alert)
        except Exception as e:
            self.db.rollback()
            raise ValueError(f"Failed to record cash variance: {str(e)}")

        return (entry, alert)

    def get_ledger_balance(
        self,
        venue_id: int,
        payment_method: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> int:
        """Get ledger balance in cents for venue."""
        if not self.is_active():
            return 0

        query = self.db.query(func.sum(PaymentLedgerEntry.amount_cents)).filter(
            PaymentLedgerEntry.venue_id == venue_id
        )

        if payment_method:
            query = query.filter(PaymentLedgerEntry.payment_method == payment_method)

        if start_date:
            query = query.filter(PaymentLedgerEntry.business_date >= start_date)

        if end_date:
            query = query.filter(PaymentLedgerEntry.business_date <= end_date)

        result = query.scalar()
        return result or 0

    def verify_ledger_integrity(self, venue_id: int) -> Dict[str, Any]:
        """Verify integrity of ledger entries for a venue."""
        if not self.is_active():
            return {"status": "disabled", "checked": 0, "valid": 0, "invalid": 0}

        entries = self.db.query(PaymentLedgerEntry).filter(
            PaymentLedgerEntry.venue_id == venue_id
        ).order_by(PaymentLedgerEntry.id).all()

        valid_count = 0
        invalid_entries = []

        for entry in entries:
            if entry.verify_integrity():
                valid_count += 1
            else:
                invalid_entries.append(entry.id)

        return {
            "status": "ok" if not invalid_entries else "integrity_error",
            "checked": len(entries),
            "valid": valid_count,
            "invalid": len(invalid_entries),
            "invalid_entry_ids": invalid_entries[:10],  # Limit to first 10
        }

    def _generate_entry_number(self, venue_id: int) -> str:
        """Generate sequential entry number."""
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        count = self.db.query(PaymentLedgerEntry).filter(
            PaymentLedgerEntry.venue_id == venue_id,
            func.date(PaymentLedgerEntry.created_at) == datetime.now(timezone.utc).date()
        ).count()
        return f"PAY-{today}-{count + 1:05d}"

    def _check_idempotency(self, key: str) -> Optional[PaymentLedgerEntry]:
        """Check if idempotency key already exists."""
        if not is_enabled("IDEMPOTENCY_KEYS_ENABLED"):
            return None

        existing = self.db.query(IdempotencyKey).filter(
            IdempotencyKey.key == key,
            IdempotencyKey.is_completed == True,
            IdempotencyKey.expires_at > datetime.now(timezone.utc)
        ).first()

        if existing and existing.ledger_entry_id:
            return self.db.query(PaymentLedgerEntry).filter(
                PaymentLedgerEntry.id == existing.ledger_entry_id
            ).first()

        return None

    def _complete_idempotency(self, key: str, entry: PaymentLedgerEntry) -> None:
        """Mark idempotency key as completed."""
        if not is_enabled("IDEMPOTENCY_KEYS_ENABLED"):
            return

        idemp = IdempotencyKey(
            key=key,
            request_path="/api/v1/payments",
            request_method="POST",
            request_hash=hashlib.sha256(key.encode()).hexdigest(),
            is_processing=False,
            is_completed=True,
            completed_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            ledger_entry_id=entry.id,
        )
        self.db.add(idemp)

    def _audit_log(
        self,
        venue_id: int,
        action: str,
        order_id: Optional[int] = None,
        ledger_entry_id: Optional[int] = None,
        staff_user_id: Optional[int] = None,
        old_data: Optional[Dict] = None,
        new_data: Optional[Dict] = None,
    ) -> None:
        """Create audit log entry."""
        log = PaymentAuditLog(
            venue_id=venue_id,
            action=action,
            order_id=order_id,
            ledger_entry_id=ledger_entry_id,
            staff_user_id=staff_user_id,
            old_data=old_data,
            new_data=new_data,
            was_successful=True,
        )
        self.db.add(log)


def create_idempotency_key() -> str:
    """Generate a new idempotency key."""
    return str(uuid.uuid4())

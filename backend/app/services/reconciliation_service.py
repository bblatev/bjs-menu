"""Reconciliation service: Compare expected vs counted quantities."""

from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import logging

from sqlalchemy.orm import Session

from app.models.inventory import InventorySession, InventoryLine
from app.models.reconciliation import ReconciliationResult, DeltaSeverity
from app.models.product import Product
from app.services.pos import get_pos_adapter, POSStockLevel

logger = logging.getLogger(__name__)


class ReconciliationConfig:
    """Configuration for reconciliation thresholds."""

    def __init__(
        self,
        critical_threshold_qty: Decimal = Decimal("5"),
        critical_threshold_percent: Decimal = Decimal("20"),
        warning_threshold_qty: Decimal = Decimal("2"),
        warning_threshold_percent: Decimal = Decimal("10"),
    ):
        self.critical_threshold_qty = critical_threshold_qty
        self.critical_threshold_percent = critical_threshold_percent
        self.warning_threshold_qty = warning_threshold_qty
        self.warning_threshold_percent = warning_threshold_percent


class ReconciliationService:
    """Service for reconciling inventory counts against expected values."""

    def __init__(self, db: Session, config: Optional[ReconciliationConfig] = None):
        self.db = db
        self.config = config or ReconciliationConfig()
        self.pos_adapter = get_pos_adapter(db)

    def get_expected_stock(
        self,
        location_id: int,
        product_ids: Optional[List[int]] = None,
    ) -> Dict[int, POSStockLevel]:
        """Fetch expected stock levels from POS/database."""
        stock_levels = self.pos_adapter.get_stock_levels(
            location_id=location_id,
            product_ids=product_ids,
        )
        # Index by product_id for fast lookup
        return {sl.product_id: sl for sl in stock_levels}

    def get_counted_quantities(
        self,
        session_id: int,
    ) -> Dict[int, Tuple[Decimal, Optional[Decimal]]]:
        """
        Get counted quantities from inventory session.
        Returns dict mapping product_id -> (total_counted, avg_confidence)
        """
        lines = (
            self.db.query(InventoryLine)
            .filter(InventoryLine.session_id == session_id)
            .all()
        )

        # Aggregate by product (in case multiple counts)
        product_counts: Dict[int, List[Tuple[Decimal, Optional[Decimal]]]] = {}
        for line in lines:
            if line.product_id not in product_counts:
                product_counts[line.product_id] = []
            product_counts[line.product_id].append((line.counted_qty, line.confidence))

        # Sum quantities, average confidences
        result = {}
        for product_id, counts in product_counts.items():
            total_qty = sum(c[0] for c in counts)
            confidences = [c[1] for c in counts if c[1] is not None]
            avg_conf = sum(confidences) / len(confidences) if confidences else None
            result[product_id] = (total_qty, avg_conf)

        return result

    def calculate_severity(
        self,
        expected: Decimal,
        counted: Decimal,
        delta: Decimal,
        confidence: Optional[Decimal] = None,
    ) -> Tuple[DeltaSeverity, str]:
        """
        Determine severity level based on delta and thresholds.
        Returns (severity, reason).
        """
        abs_delta = abs(delta)

        # Calculate percentage if expected > 0
        delta_percent = None
        if expected > 0:
            delta_percent = (abs_delta / expected) * 100

        # Low confidence from AI counts
        if confidence is not None and confidence < Decimal("0.65"):
            return DeltaSeverity.WARNING, f"Low AI confidence ({confidence:.1%})"

        # Check critical thresholds
        if abs_delta >= self.config.critical_threshold_qty:
            return DeltaSeverity.CRITICAL, f"Delta exceeds {self.config.critical_threshold_qty} units"

        if delta_percent is not None and delta_percent >= self.config.critical_threshold_percent:
            return DeltaSeverity.CRITICAL, f"Delta exceeds {self.config.critical_threshold_percent}%"

        # Check warning thresholds
        if abs_delta >= self.config.warning_threshold_qty:
            return DeltaSeverity.WARNING, f"Delta exceeds {self.config.warning_threshold_qty} units"

        if delta_percent is not None and delta_percent >= self.config.warning_threshold_percent:
            return DeltaSeverity.WARNING, f"Delta exceeds {self.config.warning_threshold_percent}%"

        return DeltaSeverity.OK, "Within acceptable tolerance"

    def reconcile_session(
        self,
        session_id: int,
        expected_source: str = "pos_stock",
        clear_previous: bool = True,
    ) -> List[ReconciliationResult]:
        """
        Run reconciliation for an inventory session.

        Args:
            session_id: The inventory session to reconcile
            expected_source: Source of expected values (pos_stock, calculated, manual)
            clear_previous: If True, delete previous reconciliation results for this session

        Returns:
            List of ReconciliationResult objects created
        """
        # Get the session
        session = self.db.query(InventorySession).filter(
            InventorySession.id == session_id
        ).first()

        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Clear previous results if requested
        if clear_previous:
            self.db.query(ReconciliationResult).filter(
                ReconciliationResult.session_id == session_id
            ).delete()

        # Get counted quantities
        counted_data = self.get_counted_quantities(session_id)

        if not counted_data:
            logger.warning(f"No inventory lines found for session {session_id}")
            return []

        # Get expected stock for all products in session
        product_ids = list(counted_data.keys())
        expected_stock = self.get_expected_stock(
            location_id=session.location_id,
            product_ids=product_ids,
        )

        # Get product info for value calculations
        products = {
            p.id: p
            for p in self.db.query(Product).filter(Product.id.in_(product_ids)).all()
        }

        results = []

        for product_id, (counted_qty, confidence) in counted_data.items():
            product = products.get(product_id)
            stock = expected_stock.get(product_id)

            # Expected quantity from POS stock
            expected_qty = Decimal(stock.qty_on_hand) if stock else Decimal("0")

            # Calculate delta (positive = missing, negative = excess)
            delta_qty = expected_qty - counted_qty

            # Calculate delta value if cost available
            delta_value = None
            if product and product.cost_price:
                delta_value = delta_qty * product.cost_price

            # Calculate delta percentage
            delta_percent = None
            if expected_qty > 0:
                delta_percent = (delta_qty / expected_qty) * 100

            # Determine severity
            severity, reason = self.calculate_severity(
                expected_qty, counted_qty, delta_qty, confidence
            )

            # Create result record
            result = ReconciliationResult(
                session_id=session_id,
                product_id=product_id,
                expected_qty=expected_qty,
                counted_qty=counted_qty,
                delta_qty=delta_qty,
                delta_value=delta_value,
                delta_percent=delta_percent,
                severity=severity,
                reason=reason,
                expected_source=expected_source,
                confidence=confidence,
            )

            self.db.add(result)
            results.append(result)

        self.db.flush()  # Assign IDs

        logger.info(
            f"Reconciliation complete for session {session_id}: "
            f"{len(results)} products, "
            f"{sum(1 for r in results if r.severity == DeltaSeverity.CRITICAL)} critical, "
            f"{sum(1 for r in results if r.severity == DeltaSeverity.WARNING)} warnings"
        )

        return results

    def get_reconciliation_summary(
        self,
        session_id: int,
    ) -> Dict:
        """Get summary of reconciliation results for a session."""
        results = (
            self.db.query(ReconciliationResult)
            .filter(ReconciliationResult.session_id == session_id)
            .all()
        )

        if not results:
            return {
                "session_id": session_id,
                "total_products": 0,
                "products_ok": 0,
                "products_warning": 0,
                "products_critical": 0,
                "total_delta_value": None,
            }

        # Get product names
        product_ids = [r.product_id for r in results]
        products = {
            p.id: p
            for p in self.db.query(Product).filter(Product.id.in_(product_ids)).all()
        }

        # Build summary
        total_delta_value = sum(
            r.delta_value for r in results if r.delta_value is not None
        )

        return {
            "session_id": session_id,
            "total_products": len(results),
            "products_ok": sum(1 for r in results if r.severity == DeltaSeverity.OK),
            "products_warning": sum(1 for r in results if r.severity == DeltaSeverity.WARNING),
            "products_critical": sum(1 for r in results if r.severity == DeltaSeverity.CRITICAL),
            "total_delta_value": float(total_delta_value) if total_delta_value else None,
            "results": [
                {
                    "id": r.id,
                    "product_id": r.product_id,
                    "product_name": products.get(r.product_id, {}).name if products.get(r.product_id) else None,
                    "product_barcode": products.get(r.product_id, {}).barcode if products.get(r.product_id) else None,
                    "expected_qty": float(r.expected_qty),
                    "counted_qty": float(r.counted_qty),
                    "delta_qty": float(r.delta_qty),
                    "delta_value": float(r.delta_value) if r.delta_value else None,
                    "delta_percent": float(r.delta_percent) if r.delta_percent else None,
                    "severity": r.severity.value,
                    "reason": r.reason,
                    "confidence": float(r.confidence) if r.confidence else None,
                }
                for r in sorted(results, key=lambda x: (
                    0 if x.severity == DeltaSeverity.CRITICAL else (
                        1 if x.severity == DeltaSeverity.WARNING else 2
                    ),
                    abs(x.delta_qty)
                ), reverse=True)
            ],
        }


def run_reconciliation(
    db: Session,
    session_id: int,
    expected_source: str = "pos_stock",
    critical_threshold_qty: Decimal = Decimal("5"),
    critical_threshold_percent: Decimal = Decimal("20"),
    warning_threshold_qty: Decimal = Decimal("2"),
    warning_threshold_percent: Decimal = Decimal("10"),
) -> Dict:
    """
    Convenience function to run reconciliation with custom thresholds.
    Returns the reconciliation summary.
    """
    config = ReconciliationConfig(
        critical_threshold_qty=critical_threshold_qty,
        critical_threshold_percent=critical_threshold_percent,
        warning_threshold_qty=warning_threshold_qty,
        warning_threshold_percent=warning_threshold_percent,
    )

    service = ReconciliationService(db, config)
    service.reconcile_session(session_id, expected_source)

    return service.get_reconciliation_summary(session_id)

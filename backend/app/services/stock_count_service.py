"""Stock count service - centralised commit, creation, and variance logic for inventory sessions.

This service extracts the duplicated stock-count commit logic that previously
existed in three separate route files (inventory.py, stock.py, stock_management.py)
into a single, reusable class.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.inventory import InventoryLine, InventorySession, SessionStatus
from app.models.location import Location
from app.models.product import Product
from app.models.stock import MovementReason, StockMovement, StockOnHand

logger = logging.getLogger(__name__)


class StockCountService:
    """Centralised service for inventory count session operations."""

    # ------------------------------------------------------------------
    # commit_session
    # ------------------------------------------------------------------
    @staticmethod
    def commit_session(
        db: Session,
        session_id: int,
        committed_by: Optional[int] = None,
        ref_type: str = "inventory_session",
        build_notes: Optional[callable] = None,
        require_lines: bool = True,
    ) -> Dict[str, Any]:
        """Commit an inventory session: apply counted quantities to stock.

        Steps:
        1. Validate the session exists and is in DRAFT status.
        2. Optionally validate the session has lines.
        3. For each line, look up current StockOnHand, compute the delta
           (counted_qty - current qty), create a StockMovement, and
           update (or create) the StockOnHand record.
        4. Mark the session as COMMITTED with a timestamp.
        5. Commit the database transaction (or roll back on error).

        Args:
            db: SQLAlchemy database session.
            session_id: ID of the InventorySession to commit.
            committed_by: Optional user ID recorded on each StockMovement.
            ref_type: The ``ref_type`` value written to StockMovement
                      (e.g. ``"inventory_session"`` or ``"ai_shelf_scan"``).
            build_notes: Optional callable ``(line) -> str | None`` that
                         produces per-movement notes. If *None*, no notes
                         are set.
            require_lines: When *True* (the default), raise if the session
                           has no lines.

        Returns:
            A dict with ``session_id``, ``status``, ``committed_at``,
            ``movements_created``, and ``adjustments`` (list of dicts).

        Raises:
            ValueError: If the session is not found, not in DRAFT status,
                        or has no lines (when *require_lines* is True).
        """
        session = (
            db.query(InventorySession)
            .filter(InventorySession.id == session_id)
            .first()
        )
        if not session:
            raise ValueError("Session not found")

        if session.status != SessionStatus.DRAFT:
            raise ValueError("Session is not in draft status")

        if require_lines and not session.lines:
            raise ValueError("Session has no lines to commit")

        movements_created = 0
        adjustments: List[Dict[str, Any]] = []

        try:
            for line in session.lines:
                stock = (
                    db.query(StockOnHand)
                    .filter(
                        StockOnHand.product_id == line.product_id,
                        StockOnHand.location_id == session.location_id,
                    )
                    .first()
                )

                current_qty = stock.qty if stock else Decimal("0")
                delta = line.counted_qty - current_qty

                if delta != 0:
                    movement_kwargs: Dict[str, Any] = {
                        "product_id": line.product_id,
                        "location_id": session.location_id,
                        "qty_delta": delta,
                        "reason": MovementReason.INVENTORY_COUNT.value,
                        "ref_type": ref_type,
                        "ref_id": session.id,
                    }
                    if committed_by is not None:
                        movement_kwargs["created_by"] = committed_by
                    if build_notes is not None:
                        notes = build_notes(line)
                        if notes:
                            movement_kwargs["notes"] = notes

                    movement = StockMovement(**movement_kwargs)
                    db.add(movement)
                    movements_created += 1

                    # Update or create StockOnHand
                    if stock:
                        stock.qty = line.counted_qty
                    else:
                        stock = StockOnHand(
                            product_id=line.product_id,
                            location_id=session.location_id,
                            qty=line.counted_qty,
                        )
                        db.add(stock)

                    adjustments.append(
                        {
                            "product_id": line.product_id,
                            "previous_qty": float(current_qty),
                            "counted_qty": float(line.counted_qty),
                            "delta": float(delta),
                        }
                    )

            # Mark session as committed
            session.status = SessionStatus.COMMITTED
            session.committed_at = datetime.now(timezone.utc)

            db.commit()
        except Exception:
            db.rollback()
            raise

        logger.info(
            "Inventory session committed: ID=%s, location=%s, movements=%s, user=%s",
            session.id,
            session.location_id,
            movements_created,
            committed_by,
        )
        if adjustments:
            logger.info("Stock adjustments for session %s: %s", session.id, adjustments)

        return {
            "session_id": session.id,
            "status": session.status,
            "committed_at": session.committed_at,
            "movements_created": movements_created,
            "adjustments": adjustments,
        }

    # ------------------------------------------------------------------
    # create_session
    # ------------------------------------------------------------------
    @staticmethod
    def create_session(
        db: Session,
        location_id: int,
        created_by: Optional[int] = None,
        notes: Optional[str] = None,
        shelf_zone: Optional[str] = None,
        count_method: str = "MANUAL",
    ) -> InventorySession:
        """Create a new inventory counting session.

        Args:
            db: SQLAlchemy database session.
            location_id: ID of the location being counted.
            created_by: Optional user ID who initiated the count.
            notes: Freeform notes on the session.
            shelf_zone: Optional shelf / zone identifier.
            count_method: Informational label (not persisted on the session
                          model itself, but useful for callers).

        Returns:
            The newly created ``InventorySession`` instance (already
            committed and refreshed).

        Raises:
            ValueError: If the location does not exist.
        """
        location = db.query(Location).filter(Location.id == location_id).first()
        if not location:
            raise ValueError("Location not found")

        session = InventorySession(
            location_id=location_id,
            created_by=created_by,
            notes=notes,
            shelf_zone=shelf_zone,
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        logger.info(
            "Inventory session created: ID=%s, location=%s, user=%s, method=%s",
            session.id,
            location_id,
            created_by,
            count_method,
        )
        return session

    # ------------------------------------------------------------------
    # get_session_with_variance
    # ------------------------------------------------------------------
    @staticmethod
    def get_session_with_variance(
        db: Session,
        session_id: int,
    ) -> Dict[str, Any]:
        """Return session details with per-line variance calculations.

        For each line the variance is ``counted_qty - current StockOnHand``.
        A cost-weighted ``variance_value`` is also computed using the
        product's ``cost_price``.

        Args:
            db: SQLAlchemy database session.
            session_id: ID of the InventorySession.

        Returns:
            A dict containing session metadata and a ``lines`` list with
            variance information.

        Raises:
            ValueError: If the session does not exist.
        """
        session = (
            db.query(InventorySession)
            .filter(InventorySession.id == session_id)
            .first()
        )
        if not session:
            raise ValueError("Session not found")

        lines_data: List[Dict[str, Any]] = []
        total_variance_count = 0
        total_variance_value = 0.0

        for line in (session.lines or []):
            stock = (
                db.query(StockOnHand)
                .filter(
                    StockOnHand.product_id == line.product_id,
                    StockOnHand.location_id == session.location_id,
                )
                .first()
            )
            current_qty = float(stock.qty) if stock else 0.0
            delta = float(line.counted_qty) - current_qty

            product = db.query(Product).filter(Product.id == line.product_id).first()
            cost = float(product.cost_price) if product and product.cost_price else 0.0
            variance_value = delta * cost

            if delta != 0:
                total_variance_count += 1
                total_variance_value += variance_value

            lines_data.append(
                {
                    "line_id": line.id,
                    "product_id": line.product_id,
                    "product_name": product.name if product else f"Product {line.product_id}",
                    "counted_qty": float(line.counted_qty),
                    "current_qty": current_qty,
                    "delta": delta,
                    "variance_value": round(variance_value, 2),
                    "method": line.method,
                    "confidence": line.confidence,
                }
            )

        status_val = session.status.value if hasattr(session.status, "value") else str(session.status)

        return {
            "session_id": session.id,
            "location_id": session.location_id,
            "status": status_val,
            "notes": session.notes,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "committed_at": session.committed_at.isoformat() if session.committed_at else None,
            "lines": lines_data,
            "total_lines": len(lines_data),
            "variance_count": total_variance_count,
            "variance_value": round(total_variance_value, 2),
        }

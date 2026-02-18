"""Guest Order Cleanup Service.

Handles automatic cleanup of abandoned guest orders (QR code orders)
that were never completed. Runs as a periodic background task.

Abandoned orders:
- Status is still 'pending' or 'draft' after SESSION_TIMEOUT_MINUTES
- Never had a payment associated
- Customer left without completing order

Cleanup actions:
1. Mark abandoned orders as 'expired'
2. Release any reserved stock
3. Free up table capacity
4. Log cleanup for audit trail
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.restaurant import GuestOrder, Table
from app.models.stock import StockMovement, MovementReason

logger = logging.getLogger(__name__)

# Configuration
SESSION_TIMEOUT_MINUTES = 30  # Orders older than this are considered abandoned
CLEANUP_BATCH_SIZE = 100  # Process this many orders per cleanup run


class GuestOrderCleanupService:
    """Service for cleaning up abandoned guest orders."""

    def __init__(self, db: Session):
        self.db = db

    def cleanup_abandoned_orders(self) -> Dict[str, Any]:
        """Find and clean up abandoned guest orders.

        Returns summary of cleanup actions taken.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=SESSION_TIMEOUT_MINUTES)
        results = {
            "cleaned_up": 0,
            "stock_released": 0,
            "tables_freed": 0,
            "errors": [],
        }

        try:
            # Find abandoned orders: pending/draft status, created before cutoff
            abandoned = self.db.query(GuestOrder).filter(
                GuestOrder.status.in_(["pending", "draft", "new"]),
                GuestOrder.created_at < cutoff,
            ).limit(CLEANUP_BATCH_SIZE).all()

            if not abandoned:
                logger.debug("No abandoned guest orders found")
                return results

            logger.info(f"Found {len(abandoned)} abandoned guest orders to clean up")

            for order in abandoned:
                try:
                    self._expire_order(order)
                    results["cleaned_up"] += 1
                except Exception as e:
                    results["errors"].append({
                        "order_id": order.id,
                        "error": str(e),
                    })
                    logger.warning(f"Failed to cleanup order {order.id}: {e}")

            self.db.commit()
            logger.info(
                f"Guest order cleanup: {results['cleaned_up']} expired, "
                f"{len(results['errors'])} errors"
            )

        except Exception as e:
            self.db.rollback()
            results["errors"].append({"error": f"Cleanup batch failed: {str(e)}"})
            logger.error(f"Guest order cleanup failed: {e}", exc_info=True)

        return results

    def _expire_order(self, order: GuestOrder) -> None:
        """Mark a single order as expired and release resources."""
        order.status = "expired"
        if hasattr(order, 'updated_at'):
            order.updated_at = datetime.now(timezone.utc)

        # Release reserved stock if any was reserved
        self._release_reserved_stock(order)

        # Update table status if it was held by this order
        if hasattr(order, 'table_id') and order.table_id:
            self._check_table_release(order.table_id)

        logger.debug(f"Expired abandoned guest order {order.id} "
                      f"(table: {getattr(order, 'table_id', '?')})")

    def _release_reserved_stock(self, order: GuestOrder) -> None:
        """Release any stock that was reserved for this order.

        Looks for RESERVATION movements referencing this order and
        creates offsetting RESERVATION_RELEASE movements.
        """
        try:
            reservations = self.db.query(StockMovement).filter(
                StockMovement.ref_type == "guest_order",
                StockMovement.ref_id == order.id,
                StockMovement.reason == MovementReason.RESERVATION.value,
            ).all()

            for reservation in reservations:
                # Check if already released
                existing_release = self.db.query(StockMovement).filter(
                    StockMovement.ref_type == "guest_order_release",
                    StockMovement.ref_id == order.id,
                    StockMovement.product_id == reservation.product_id,
                    StockMovement.reason == MovementReason.RESERVATION_RELEASE.value,
                ).first()

                if existing_release:
                    continue

                release = StockMovement(
                    product_id=reservation.product_id,
                    location_id=reservation.location_id,
                    qty_delta=-reservation.qty_delta,  # Reverse the reservation
                    reason=MovementReason.RESERVATION_RELEASE.value,
                    ref_type="guest_order_release",
                    ref_id=order.id,
                    notes=f"Auto-release: abandoned guest order #{order.id}",
                )
                self.db.add(release)

        except Exception as e:
            logger.debug(f"Stock release for order {order.id}: {e}")

    def _check_table_release(self, table_id: int) -> None:
        """Check if a table can be freed (no other active orders)."""
        try:
            active_orders = self.db.query(func.count(GuestOrder.id)).filter(
                GuestOrder.table_id == table_id,
                GuestOrder.status.in_(["pending", "draft", "new", "confirmed", "preparing"]),
            ).scalar()

            if active_orders == 0:
                table = self.db.query(Table).filter(Table.id == table_id).first()
                if table and hasattr(table, 'status'):
                    table.status = "available"
                    logger.debug(f"Table {table_id} freed after last order expired")
        except Exception as e:
            logger.debug(f"Table release check for {table_id}: {e}")

    def get_abandoned_order_count(self) -> int:
        """Get count of currently abandoned orders (for monitoring)."""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=SESSION_TIMEOUT_MINUTES)
        return self.db.query(func.count(GuestOrder.id)).filter(
            GuestOrder.status.in_(["pending", "draft", "new"]),
            GuestOrder.created_at < cutoff,
        ).scalar() or 0

    def get_cleanup_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get cleanup statistics for the past N days."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        expired_count = self.db.query(func.count(GuestOrder.id)).filter(
            GuestOrder.status == "expired",
            GuestOrder.updated_at >= cutoff,
        ).scalar() or 0

        total_orders = self.db.query(func.count(GuestOrder.id)).filter(
            GuestOrder.created_at >= cutoff,
        ).scalar() or 0

        return {
            "period_days": days,
            "total_orders": total_orders,
            "expired_orders": expired_count,
            "abandonment_rate": round(expired_count / max(total_orders, 1) * 100, 1),
            "currently_abandoned": self.get_abandoned_order_count(),
        }


def run_guest_order_cleanup() -> Dict[str, Any]:
    """Standalone function to run cleanup (called from background scheduler)."""
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        service = GuestOrderCleanupService(db)
        return service.cleanup_abandoned_orders()
    finally:
        db.close()

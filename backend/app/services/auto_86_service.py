"""Auto-86 Service - Automatically 86 menu items when stock runs out.

When stock for a recipe ingredient drops below the threshold needed to
make at least 1 serving, the menu item is automatically marked as
unavailable (86'd) across all channels: POS, KDS, QR ordering.

When stock is replenished (purchase, transfer_in, adjustment), items
are automatically un-86'd.

Industry standard: Toast Auto-86, Square KDS Auto-86, Revel Auto-86.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import ForeignKey, String, and_, func, select
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.location import Location
from app.models.product import Product
from app.models.recipe import Recipe, RecipeLine
from app.models.restaurant import MenuItem
from app.models.stock import StockOnHand

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

class Auto86Event(Base, TimestampMixin):
    """Ledger entry for every 86 / un-86 event."""

    __tablename__ = "auto_86_events"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(primary_key=True)
    menu_item_id: Mapped[int] = mapped_column(
        ForeignKey("menu_items.id", ondelete="CASCADE"), index=True,
    )
    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"), index=True,
    )
    event_type: Mapped[str] = mapped_column(String(20))  # "86" or "un86"
    reason: Mapped[str] = mapped_column(String(50))  # "auto_stock", "manual", "auto_restock"
    triggered_by_product_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("products.id"), nullable=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True,
    )

    # Relationships
    menu_item: Mapped["MenuItem"] = relationship("MenuItem", foreign_keys=[menu_item_id])
    location: Mapped["Location"] = relationship("Location", foreign_keys=[location_id])
    product: Mapped[Optional["Product"]] = relationship("Product", foreign_keys=[triggered_by_product_id])


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class Auto86Service:
    """Business logic for the Auto-86 system."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Core: check stock and flip 86 status
    # ------------------------------------------------------------------

    def check_and_update_86_status(
        self,
        product_id: int,
        location_id: int,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """After any stock change for *product_id*, check every recipe that
        uses this product.  If any ingredient's stock is below what's needed
        for 1 serving, 86 the linked menu item.  If all ingredients now have
        enough stock, un-86 it.

        Returns a summary dict of items 86'd and un-86'd.
        """
        # Find all recipe lines that reference this product
        recipe_lines = (
            self.db.query(RecipeLine)
            .filter(RecipeLine.product_id == product_id)
            .all()
        )

        items_86d: List[Dict[str, Any]] = []
        items_un86d: List[Dict[str, Any]] = []

        recipe_ids_seen: set[int] = set()
        for rl in recipe_lines:
            if rl.recipe_id in recipe_ids_seen:
                continue
            recipe_ids_seen.add(rl.recipe_id)

            # Find menu items linked to this recipe
            menu_items = (
                self.db.query(MenuItem)
                .filter(
                    MenuItem.recipe_id == rl.recipe_id,
                    MenuItem.deleted_at.is_(None),
                )
                .all()
            )

            for mi in menu_items:
                should_86 = self._should_86_item(mi.recipe_id, location_id)

                if should_86 and mi.available:
                    # 86 the item
                    mi.available = False
                    self._record_event(
                        menu_item_id=mi.id,
                        location_id=location_id,
                        event_type="86",
                        reason="auto_stock",
                        triggered_by_product_id=product_id,
                        notes=f"Stock for product {product_id} too low for recipe {rl.recipe_id}",
                        created_by=user_id,
                    )
                    items_86d.append({"id": mi.id, "name": mi.name})
                    logger.info(
                        "Auto-86: menu_item %s (%s) at location %s - product %s low",
                        mi.id, mi.name, location_id, product_id,
                    )

                elif not should_86 and not mi.available:
                    # Check if the item was auto-86'd (not manually)
                    last_event = (
                        self.db.query(Auto86Event)
                        .filter(
                            Auto86Event.menu_item_id == mi.id,
                            Auto86Event.location_id == location_id,
                            Auto86Event.event_type == "86",
                        )
                        .order_by(Auto86Event.created_at.desc())
                        .first()
                    )
                    # Only auto-restore if last 86 was automatic
                    if last_event and last_event.reason == "auto_stock":
                        mi.available = True
                        self._record_event(
                            menu_item_id=mi.id,
                            location_id=location_id,
                            event_type="un86",
                            reason="auto_restock",
                            triggered_by_product_id=product_id,
                            notes=f"Stock for product {product_id} replenished",
                            created_by=user_id,
                        )
                        items_un86d.append({"id": mi.id, "name": mi.name})
                        logger.info(
                            "Auto-un86: menu_item %s (%s) at location %s - stock replenished",
                            mi.id, mi.name, location_id,
                        )

        self.db.commit()

        return {
            "product_id": product_id,
            "location_id": location_id,
            "items_86d": items_86d,
            "items_un86d": items_un86d,
            "total_checked": len(recipe_ids_seen),
        }

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def get_86d_items(self, location_id: int) -> List[Dict[str, Any]]:
        """Return all currently 86'd menu items for a location."""
        items = (
            self.db.query(MenuItem)
            .filter(
                MenuItem.available == False,  # noqa: E712
                MenuItem.deleted_at.is_(None),
            )
            .all()
        )

        result: List[Dict[str, Any]] = []
        for mi in items:
            # Get last 86 event for context
            last_event = (
                self.db.query(Auto86Event)
                .filter(
                    Auto86Event.menu_item_id == mi.id,
                    Auto86Event.location_id == location_id,
                    Auto86Event.event_type == "86",
                )
                .order_by(Auto86Event.created_at.desc())
                .first()
            )
            result.append({
                "id": mi.id,
                "name": mi.name,
                "category": mi.category,
                "price": float(mi.price) if mi.price else 0,
                "recipe_id": mi.recipe_id,
                "reason": last_event.reason if last_event else "unknown",
                "since": last_event.created_at.isoformat() if last_event else None,
                "notes": last_event.notes if last_event else None,
                "triggered_by_product_id": last_event.triggered_by_product_id if last_event else None,
            })
        return result

    def manual_86(
        self,
        menu_item_id: int,
        location_id: int,
        reason: str,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Manually 86 a menu item (manager override)."""
        mi = self.db.query(MenuItem).filter(MenuItem.id == menu_item_id).first()
        if not mi:
            raise ValueError(f"Menu item {menu_item_id} not found")
        if not mi.available:
            return {"status": "already_86d", "menu_item_id": menu_item_id}

        mi.available = False
        self._record_event(
            menu_item_id=mi.id,
            location_id=location_id,
            event_type="86",
            reason="manual",
            notes=reason or "Manager override",
            created_by=user_id,
        )
        self.db.commit()
        logger.info("Manual 86: menu_item %s by user %s", menu_item_id, user_id)
        return {"status": "86d", "menu_item_id": menu_item_id, "name": mi.name}

    def manual_un86(
        self,
        menu_item_id: int,
        location_id: int,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Manually restore (un-86) a menu item."""
        mi = self.db.query(MenuItem).filter(MenuItem.id == menu_item_id).first()
        if not mi:
            raise ValueError(f"Menu item {menu_item_id} not found")
        if mi.available:
            return {"status": "already_available", "menu_item_id": menu_item_id}

        mi.available = True
        self._record_event(
            menu_item_id=mi.id,
            location_id=location_id,
            event_type="un86",
            reason="manual",
            notes="Manually restored by manager",
            created_by=user_id,
        )
        self.db.commit()
        logger.info("Manual un-86: menu_item %s by user %s", menu_item_id, user_id)
        return {"status": "un86d", "menu_item_id": menu_item_id, "name": mi.name}

    def get_86_history(
        self,
        location_id: int,
        days: int = 7,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """History of 86/un-86 events for a location."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        query = (
            self.db.query(Auto86Event)
            .filter(
                Auto86Event.location_id == location_id,
                Auto86Event.created_at >= cutoff,
            )
            .order_by(Auto86Event.created_at.desc())
        )

        total = query.count()
        events = query.offset(offset).limit(limit).all()

        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "days": days,
            "events": [
                {
                    "id": e.id,
                    "menu_item_id": e.menu_item_id,
                    "menu_item_name": e.menu_item.name if e.menu_item else None,
                    "event_type": e.event_type,
                    "reason": e.reason,
                    "triggered_by_product_id": e.triggered_by_product_id,
                    "notes": e.notes,
                    "created_by": e.created_by,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in events
            ],
        }

    def get_dashboard(self, location_id: int) -> Dict[str, Any]:
        """Dashboard summary: 86'd items, at-risk items (low stock), recent events."""
        currently_86d = self.get_86d_items(location_id)

        # At-risk items: items whose recipe ingredients are running low
        at_risk = self._get_at_risk_items(location_id)

        # Recent events (last 24h)
        recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        recent_events = (
            self.db.query(Auto86Event)
            .filter(
                Auto86Event.location_id == location_id,
                Auto86Event.created_at >= recent_cutoff,
            )
            .order_by(Auto86Event.created_at.desc())
            .limit(20)
            .all()
        )

        # Stats
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        events_today = (
            self.db.query(Auto86Event)
            .filter(
                Auto86Event.location_id == location_id,
                Auto86Event.created_at >= today_start,
            )
            .count()
        )
        auto_86_today = (
            self.db.query(Auto86Event)
            .filter(
                Auto86Event.location_id == location_id,
                Auto86Event.created_at >= today_start,
                Auto86Event.event_type == "86",
                Auto86Event.reason == "auto_stock",
            )
            .count()
        )

        return {
            "currently_86d": currently_86d,
            "count_86d": len(currently_86d),
            "at_risk_items": at_risk,
            "count_at_risk": len(at_risk),
            "recent_events": [
                {
                    "id": e.id,
                    "menu_item_id": e.menu_item_id,
                    "menu_item_name": e.menu_item.name if e.menu_item else None,
                    "event_type": e.event_type,
                    "reason": e.reason,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in recent_events
            ],
            "stats": {
                "total_events_today": events_today,
                "auto_86_today": auto_86_today,
            },
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _should_86_item(self, recipe_id: Optional[int], location_id: int) -> bool:
        """Return True if any ingredient in the recipe has stock below what's
        needed for 1 serving."""
        if not recipe_id:
            return False

        lines = (
            self.db.query(RecipeLine)
            .filter(RecipeLine.recipe_id == recipe_id)
            .all()
        )
        if not lines:
            return False

        for line in lines:
            stock = (
                self.db.query(StockOnHand)
                .filter(
                    StockOnHand.product_id == line.product_id,
                    StockOnHand.location_id == location_id,
                )
                .first()
            )
            available_qty = Decimal("0")
            if stock:
                available_qty = stock.qty - stock.reserved_qty

            if available_qty < line.qty:
                return True

        return False

    def _get_at_risk_items(self, location_id: int) -> List[Dict[str, Any]]:
        """Items not yet 86'd but close to running out (< 3 servings worth)."""
        threshold_servings = 3

        menu_items = (
            self.db.query(MenuItem)
            .filter(
                MenuItem.available == True,  # noqa: E712
                MenuItem.recipe_id.isnot(None),
                MenuItem.deleted_at.is_(None),
            )
            .all()
        )

        at_risk: List[Dict[str, Any]] = []
        for mi in menu_items:
            servings_possible = self._calculate_servings_possible(mi.recipe_id, location_id)
            if servings_possible is not None and servings_possible < threshold_servings:
                at_risk.append({
                    "id": mi.id,
                    "name": mi.name,
                    "category": mi.category,
                    "servings_remaining": servings_possible,
                    "recipe_id": mi.recipe_id,
                    "limiting_ingredient": self._get_limiting_ingredient(mi.recipe_id, location_id),
                })
        return at_risk

    def _calculate_servings_possible(
        self, recipe_id: int, location_id: int
    ) -> Optional[int]:
        """Calculate how many servings can be made given current stock."""
        lines = (
            self.db.query(RecipeLine)
            .filter(RecipeLine.recipe_id == recipe_id)
            .all()
        )
        if not lines:
            return None

        min_servings: Optional[int] = None
        for line in lines:
            if line.qty <= 0:
                continue
            stock = (
                self.db.query(StockOnHand)
                .filter(
                    StockOnHand.product_id == line.product_id,
                    StockOnHand.location_id == location_id,
                )
                .first()
            )
            available = Decimal("0")
            if stock:
                available = stock.qty - stock.reserved_qty
            servings = int(available / line.qty) if line.qty > 0 else 0
            if min_servings is None or servings < min_servings:
                min_servings = servings

        return min_servings

    def _get_limiting_ingredient(
        self, recipe_id: int, location_id: int
    ) -> Optional[Dict[str, Any]]:
        """Return the ingredient with the fewest servings remaining."""
        lines = (
            self.db.query(RecipeLine)
            .filter(RecipeLine.recipe_id == recipe_id)
            .all()
        )
        if not lines:
            return None

        worst: Optional[Dict[str, Any]] = None
        worst_servings: Optional[int] = None

        for line in lines:
            if line.qty <= 0:
                continue
            stock = (
                self.db.query(StockOnHand)
                .filter(
                    StockOnHand.product_id == line.product_id,
                    StockOnHand.location_id == location_id,
                )
                .first()
            )
            available = Decimal("0")
            if stock:
                available = stock.qty - stock.reserved_qty
            servings = int(available / line.qty) if line.qty > 0 else 0

            product = self.db.query(Product).filter(Product.id == line.product_id).first()

            if worst_servings is None or servings < worst_servings:
                worst_servings = servings
                worst = {
                    "product_id": line.product_id,
                    "product_name": product.name if product else f"product-{line.product_id}",
                    "available_qty": float(available),
                    "required_per_serving": float(line.qty),
                    "servings_possible": servings,
                }
        return worst

    def _record_event(
        self,
        menu_item_id: int,
        location_id: int,
        event_type: str,
        reason: str,
        triggered_by_product_id: Optional[int] = None,
        notes: Optional[str] = None,
        created_by: Optional[int] = None,
    ) -> Auto86Event:
        """Persist a new Auto86Event row."""
        event = Auto86Event(
            menu_item_id=menu_item_id,
            location_id=location_id,
            event_type=event_type,
            reason=reason,
            triggered_by_product_id=triggered_by_product_id,
            notes=notes,
            created_by=created_by,
        )
        self.db.add(event)
        return event

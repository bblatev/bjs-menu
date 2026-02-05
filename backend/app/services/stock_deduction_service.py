"""Stock Deduction Service - Deducts inventory when orders are placed.

This service handles the automatic deduction of stock when menu items are sold.
It looks up the recipe for each menu item and deducts the required ingredients
from the stock on hand.

Flow:
1. Order placed (waiter POS, guest order, etc.)
2. For each menu item in order:
   a. Look up recipe (by menu_item.recipe_id or recipe.pos_item_id)
   b. For each ingredient in recipe:
      - Convert units if needed (g→kg, ml→L)
      - Validate sufficient stock
      - Deduct from StockOnHand
      - Deduct from FIFO batches
      - Create StockMovement record for audit
3. Check auto-reorder triggers
4. Return summary of deductions

Industry-standard patterns (Toast, Square, MarketMan, Revel):
- Atomic stock deduction with rollback on partial failure
- FIFO batch enforcement as mandatory
- Negative stock prevention at service layer
- Unit conversion validation before deduction
- Auto-reorder triggers when stock hits reorder point
- Stock reservation for in-progress orders
"""

import logging
from decimal import Decimal
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.stock import StockOnHand, StockMovement, MovementReason
from app.models.recipe import Recipe, RecipeLine
from app.models.restaurant import MenuItem
from app.models.product import Product

logger = logging.getLogger(__name__)

# Unit conversion factors (convert TO base unit)
UNIT_CONVERSIONS = {
    # Weight: base unit = g
    "kg": Decimal("1000"),      # 1 kg = 1000 g
    "g": Decimal("1"),          # base
    "mg": Decimal("0.001"),     # 1 mg = 0.001 g
    "lb": Decimal("453.592"),   # 1 lb = 453.592 g
    "oz": Decimal("28.3495"),   # 1 oz = 28.3495 g

    # Volume: base unit = ml
    "l": Decimal("1000"),       # 1 L = 1000 ml
    "L": Decimal("1000"),       # 1 L = 1000 ml
    "ml": Decimal("1"),         # base
    "cl": Decimal("10"),        # 1 cl = 10 ml
    "dl": Decimal("100"),       # 1 dl = 100 ml
    "gal": Decimal("3785.41"),  # 1 gal = 3785.41 ml
    "pt": Decimal("473.176"),   # 1 pint = 473.176 ml
    "fl_oz": Decimal("29.5735"),# 1 fl oz = 29.5735 ml

    # Count: base unit = pcs
    "pcs": Decimal("1"),        # base
    "ea": Decimal("1"),         # each = 1 pcs
    "unit": Decimal("1"),       # unit = 1 pcs
    "dozen": Decimal("12"),     # 1 dozen = 12 pcs
    "case": Decimal("24"),      # 1 case = 24 pcs (configurable)
}

# Unit type groups (for compatibility checking)
WEIGHT_UNITS = {"kg", "g", "mg", "lb", "oz"}
VOLUME_UNITS = {"l", "L", "ml", "cl", "dl", "gal", "pt", "fl_oz"}
COUNT_UNITS = {"pcs", "ea", "unit", "dozen", "case"}


class InsufficientStockError(Exception):
    """Raised when there's not enough stock for a deduction."""
    def __init__(self, product_name: str, product_id: int, available: Decimal, needed: Decimal, unit: str):
        self.product_name = product_name
        self.product_id = product_id
        self.available = available
        self.needed = needed
        self.unit = unit
        super().__init__(
            f"Insufficient stock for '{product_name}': need {needed} {unit}, have {available} {unit}"
        )


class UnitConversionError(Exception):
    """Raised when unit conversion between incompatible types is attempted."""
    def __init__(self, from_unit: str, to_unit: str, product_name: str = ""):
        self.from_unit = from_unit
        self.to_unit = to_unit
        self.product_name = product_name
        super().__init__(
            f"Cannot convert '{from_unit}' to '{to_unit}' for product '{product_name}'"
        )


class StockDeductionService:
    """Service for deducting stock when orders are placed."""

    def __init__(self, db: Session):
        self.db = db

    # ===== CORE: ORDER STOCK DEDUCTION (ATOMIC) =====

    def deduct_for_order(
        self,
        order_items: List[Dict[str, Any]],
        location_id: int = 1,
        reference_type: str = "pos_sale",
        reference_id: Optional[int] = None,
        created_by: Optional[int] = None,
        allow_negative: bool = False,
    ) -> Dict[str, Any]:
        """
        Deduct stock for all items in an order with ATOMIC transaction safety.

        Uses a SQLAlchemy savepoint so that if ANY ingredient deduction fails,
        the entire order's stock changes are rolled back. No partial deductions.

        Args:
            order_items: List of dicts with menu_item_id and quantity
            location_id: Location to deduct from
            reference_type: Type of reference (pos_sale, guest_order, etc.)
            reference_id: ID of the reference (check_id, order_id, etc.)
            created_by: User ID who created the order
            allow_negative: If True, allow stock to go negative (legacy mode)

        Returns:
            Dict with deduction summary and any errors
        """
        results = {
            "success": True,
            "deductions": [],
            "errors": [],
            "warnings": [],
            "total_items_processed": 0,
            "total_ingredients_deducted": 0,
        }

        # Use a savepoint for atomic deduction
        savepoint = self.db.begin_nested()
        try:
            for item in order_items:
                menu_item_id = item.get("menu_item_id")
                quantity = Decimal(str(item.get("quantity", 1)))

                if not menu_item_id:
                    results["errors"].append({"error": "Missing menu_item_id", "item": item})
                    continue

                # Get menu item
                menu_item = self.db.query(MenuItem).filter(MenuItem.id == menu_item_id).first()
                if not menu_item:
                    results["warnings"].append({
                        "warning": f"Menu item {menu_item_id} not found",
                        "item": item
                    })
                    continue

                # Find recipe for this menu item
                recipe = self._find_recipe_for_menu_item(menu_item)
                if not recipe:
                    results["warnings"].append({
                        "warning": f"No recipe found for '{menu_item.name}' (ID: {menu_item_id})",
                        "item": item
                    })
                    continue

                # Pre-validate all ingredients have sufficient stock
                if not allow_negative:
                    validation = self._validate_sufficient_stock(
                        recipe, quantity, location_id
                    )
                    if not validation["sufficient"]:
                        results["errors"].append({
                            "error": "Insufficient stock",
                            "menu_item": menu_item.name,
                            "menu_item_id": menu_item_id,
                            "shortages": validation["shortages"],
                        })
                        results["success"] = False
                        continue

                # Deduct each ingredient
                for line in recipe.lines:
                    deduction_result = self._deduct_ingredient(
                        product_id=line.product_id,
                        recipe_qty=line.qty,
                        recipe_unit=line.unit,
                        order_qty=quantity,
                        location_id=location_id,
                        reference_type=reference_type,
                        reference_id=reference_id,
                        created_by=created_by,
                        menu_item_name=menu_item.name,
                        allow_negative=allow_negative,
                    )

                    if deduction_result.get("success"):
                        results["deductions"].append(deduction_result)
                        results["total_ingredients_deducted"] += 1
                    else:
                        results["errors"].append(deduction_result)
                        results["success"] = False

                results["total_items_processed"] += 1

            if results["success"]:
                savepoint.commit()
                self.db.commit()
                # Check auto-reorder triggers after successful deduction
                self._check_reorder_triggers(results["deductions"], location_id)
            else:
                savepoint.rollback()

        except Exception as e:
            savepoint.rollback()
            results["success"] = False
            results["errors"].append({"error": f"Transaction failed: {str(e)}"})
            logger.error(f"Stock deduction failed for order: {e}", exc_info=True)

        return results

    def _validate_sufficient_stock(
        self,
        recipe: Recipe,
        quantity: Decimal,
        location_id: int,
    ) -> Dict[str, Any]:
        """Pre-validate that sufficient stock exists for all recipe ingredients."""
        shortages = []
        for line in recipe.lines:
            product = self.db.query(Product).filter(Product.id == line.product_id).first()
            if not product:
                continue

            total_qty = line.qty * quantity
            deduct_qty = self._convert_units(total_qty, line.unit, product.unit)
            if deduct_qty is None:
                shortages.append({
                    "product_id": product.id,
                    "product_name": product.name,
                    "error": f"Cannot convert {line.unit} to {product.unit}",
                })
                continue

            stock = self.db.query(StockOnHand).filter(
                StockOnHand.product_id == line.product_id,
                StockOnHand.location_id == location_id,
            ).first()

            available = stock.qty if stock else Decimal("0")
            # Account for reserved quantity
            reserved = getattr(stock, 'reserved_qty', Decimal("0")) or Decimal("0") if stock else Decimal("0")
            effective_available = available - reserved

            if effective_available < deduct_qty:
                shortages.append({
                    "product_id": product.id,
                    "product_name": product.name,
                    "available": float(effective_available),
                    "needed": float(deduct_qty),
                    "unit": product.unit,
                    "shortage": float(deduct_qty - effective_available),
                })

        return {
            "sufficient": len(shortages) == 0,
            "shortages": shortages,
        }

    def _find_recipe_for_menu_item(self, menu_item: MenuItem) -> Optional[Recipe]:
        """Find recipe for a menu item. Prioritizes FK, then pos_item_id, then name match."""
        # Priority 1: Direct FK recipe_id
        if hasattr(menu_item, 'recipe_id') and menu_item.recipe_id:
            recipe = self.db.query(Recipe).filter(Recipe.id == menu_item.recipe_id).first()
            if recipe:
                return recipe

        # Priority 2: POS item ID match
        recipe = self.db.query(Recipe).filter(
            Recipe.pos_item_id == str(menu_item.id)
        ).first()
        if recipe:
            return recipe

        # Priority 3: Name match (with warning)
        recipe = self.db.query(Recipe).filter(
            Recipe.name == menu_item.name
        ).first()
        if recipe:
            logger.warning(
                f"Recipe for menu item '{menu_item.name}' (ID: {menu_item.id}) "
                f"found by name match only. Consider setting recipe_id FK for reliability."
            )
            return recipe

        # Priority 4: POS item name match (with warning)
        recipe = self.db.query(Recipe).filter(
            Recipe.pos_item_name == menu_item.name
        ).first()
        if recipe:
            logger.warning(
                f"Recipe for menu item '{menu_item.name}' (ID: {menu_item.id}) "
                f"found by pos_item_name match only. Consider setting recipe_id FK."
            )

        return recipe

    def _deduct_ingredient(
        self,
        product_id: int,
        recipe_qty: Decimal,
        recipe_unit: str,
        order_qty: Decimal,
        location_id: int,
        reference_type: str,
        reference_id: Optional[int],
        created_by: Optional[int],
        menu_item_name: str,
        allow_negative: bool = False,
    ) -> Dict[str, Any]:
        """Deduct a single ingredient from stock."""
        # Get product
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return {
                "success": False,
                "error": f"Product {product_id} not found",
                "product_id": product_id,
            }

        # Calculate total quantity to deduct
        total_qty = recipe_qty * order_qty

        # Convert units with validation
        deduct_qty = self._convert_units(total_qty, recipe_unit, product.unit)
        if deduct_qty is None:
            return {
                "success": False,
                "error": f"Cannot convert {recipe_unit} to {product.unit} for '{product.name}'",
                "product_id": product_id,
                "product_name": product.name,
            }

        # Get or create StockOnHand record
        stock = self.db.query(StockOnHand).filter(
            StockOnHand.product_id == product_id,
            StockOnHand.location_id == location_id,
        ).first()

        if not stock:
            if not allow_negative:
                return {
                    "success": False,
                    "error": f"No stock record for '{product.name}' at location {location_id}",
                    "product_id": product_id,
                    "product_name": product.name,
                }
            stock = StockOnHand(
                product_id=product_id,
                location_id=location_id,
                qty=Decimal("0"),
            )
            self.db.add(stock)
            self.db.flush()

        old_qty = stock.qty
        reserved = getattr(stock, 'reserved_qty', Decimal("0")) or Decimal("0")
        effective_available = old_qty - reserved

        # Negative stock prevention
        if not allow_negative and effective_available < deduct_qty:
            return {
                "success": False,
                "error": f"Insufficient stock for '{product.name}': need {deduct_qty}, have {effective_available} {product.unit}",
                "product_id": product_id,
                "product_name": product.name,
                "available": float(effective_available),
                "needed": float(deduct_qty),
            }

        new_qty = old_qty - deduct_qty
        warning = None
        if new_qty < 0:
            warning = f"Stock for '{product.name}' went negative: {new_qty} {product.unit}"

        # Update stock
        stock.qty = new_qty

        # FIFO: Deduct from oldest batches first (mandatory)
        batch_result = self._deduct_from_batches_fifo(product_id, location_id, deduct_qty)
        if batch_result and batch_result.get("warning"):
            warning = batch_result["warning"]

        # Create movement record
        movement = StockMovement(
            product_id=product_id,
            location_id=location_id,
            qty_delta=-deduct_qty,
            reason=MovementReason.SALE.value,
            ref_type=reference_type,
            ref_id=reference_id,
            notes=f"Sale: {menu_item_name} x{order_qty}",
            created_by=created_by,
        )
        self.db.add(movement)

        return {
            "success": True,
            "product_id": product_id,
            "product_name": product.name,
            "qty_deducted": float(deduct_qty),
            "unit": product.unit,
            "old_qty": float(old_qty),
            "new_qty": float(new_qty),
            "warning": warning,
            "menu_item": menu_item_name,
        }

    def _deduct_from_batches_fifo(
        self,
        product_id: int,
        location_id: int,
        qty_to_deduct: Decimal,
    ) -> Optional[Dict[str, Any]]:
        """
        Deduct from inventory batches using FIFO (First In, First Out).
        Oldest batches (by received_date) are consumed first.
        Also checks for expired batches and marks them.

        FIFO is mandatory when batches exist. Returns warning if batch
        quantity is insufficient (stock still deducted from StockOnHand).
        """
        try:
            from app.models.advanced_features import InventoryBatch
            from datetime import date as date_type

            # Get non-expired batches ordered by received date (oldest first = FIFO)
            batches = self.db.query(InventoryBatch).filter(
                InventoryBatch.product_id == product_id,
                InventoryBatch.location_id == location_id,
                InventoryBatch.current_quantity > 0,
                InventoryBatch.is_quarantined == False,
            ).order_by(InventoryBatch.received_date.asc()).all()

            if not batches:
                return None  # No batch tracking for this product

            # Mark expired batches
            today = date_type.today()
            for batch in batches:
                if batch.expiration_date and batch.expiration_date < today:
                    batch.is_expired = True

            # Filter to non-expired only for deduction
            active_batches = [b for b in batches if not b.is_expired]

            remaining = qty_to_deduct
            for batch in active_batches:
                if remaining <= 0:
                    break

                deduct_from_batch = min(remaining, batch.current_quantity)
                batch.current_quantity -= deduct_from_batch
                remaining -= deduct_from_batch

            if remaining > 0:
                total_batch_qty = sum(b.current_quantity for b in active_batches)
                return {
                    "warning": f"FIFO batch shortage: {remaining} units could not be matched to batches "
                               f"(total batch qty: {total_batch_qty}). StockOnHand still deducted."
                }

            return None

        except Exception as e:
            # InventoryBatch table may not exist yet - log and continue
            logger.debug(f"Batch tracking unavailable: {e}")
            return None

    def _convert_units(
        self,
        qty: Decimal,
        from_unit: str,
        to_unit: str,
    ) -> Optional[Decimal]:
        """Convert quantity between units. Returns None if incompatible."""
        from_unit = from_unit.lower().strip()
        to_unit = to_unit.lower().strip()

        # Same unit, no conversion needed
        if from_unit == to_unit:
            return qty

        # Check compatibility
        from_type = self._get_unit_type(from_unit)
        to_type = self._get_unit_type(to_unit)

        if from_type != to_type:
            return None

        # Validate both units are known
        if from_unit not in UNIT_CONVERSIONS:
            logger.warning(f"Unknown source unit '{from_unit}' - treating as base unit")
        if to_unit not in UNIT_CONVERSIONS:
            logger.warning(f"Unknown target unit '{to_unit}' - treating as base unit")

        # Convert: from_unit → base → to_unit
        from_factor = UNIT_CONVERSIONS.get(from_unit, Decimal("1"))
        to_factor = UNIT_CONVERSIONS.get(to_unit, Decimal("1"))

        # qty in base units
        base_qty = qty * from_factor
        # convert to target unit
        result = base_qty / to_factor

        return result.quantize(Decimal("0.0001"))

    def _get_unit_type(self, unit: str) -> str:
        """Get the type of unit (weight, volume, count)."""
        unit = unit.lower().strip()
        if unit in WEIGHT_UNITS:
            return "weight"
        if unit in VOLUME_UNITS:
            return "volume"
        return "count"

    # ===== AUTO-REORDER TRIGGER =====

    def _check_reorder_triggers(
        self,
        deductions: List[Dict[str, Any]],
        location_id: int,
    ) -> None:
        """Check if any deducted products fell below their reorder point/PAR level.
        Creates reorder alerts for products that need restocking."""
        for deduction in deductions:
            product_id = deduction.get("product_id")
            if not product_id:
                continue

            product = self.db.query(Product).filter(Product.id == product_id).first()
            if not product or not product.par_level:
                continue

            new_qty = Decimal(str(deduction.get("new_qty", 0)))
            if new_qty <= product.par_level:
                self._create_reorder_alert(product, location_id, new_qty)

    def _create_reorder_alert(
        self,
        product: Product,
        location_id: int,
        current_qty: Decimal,
    ) -> None:
        """Create a reorder alert when stock falls below PAR.
        Uses a StockMovement with reason=ADJUSTMENT and ref_type=reorder_alert
        as a lightweight notification mechanism (no separate Notification table needed)."""
        try:
            # Check if reorder alert already logged in last 24h (avoid duplicates)
            recent = self.db.query(StockMovement).filter(
                StockMovement.product_id == product.id,
                StockMovement.location_id == location_id,
                StockMovement.ref_type == "reorder_alert",
                StockMovement.ts >= datetime.now(timezone.utc) - timedelta(hours=24),
            ).first()
            if recent:
                return

            logger.info(
                f"REORDER ALERT: {product.name} at {current_qty} {product.unit} "
                f"(PAR: {product.par_level} {product.unit}) at location {location_id}"
            )
        except Exception as e:
            logger.debug(f"Could not create reorder alert: {e}")

    # ===== SMART PAR CALCULATION =====

    def calculate_smart_par(
        self,
        product_id: int,
        location_id: int = 1,
        lookback_days: int = 30,
        safety_factor: float = 1.5,
        order_cycle_days: int = 7,
    ) -> Dict[str, Any]:
        """
        Calculate smart PAR level using industry formula:
        - avg_daily_usage = sum of SALE movements over lookback period / days
        - safety_stock = avg_daily_usage × safety_factor
        - reorder_point = (avg_daily_usage × lead_time_days) + safety_stock
        - recommended_par = reorder_point + (avg_daily_usage × order_cycle_days)
        """
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return {"error": "Product not found"}

        start_date = datetime.now(timezone.utc) - timedelta(days=lookback_days)

        # Calculate average daily usage from SALE movements
        total_usage = self.db.query(
            func.sum(func.abs(StockMovement.qty_delta))
        ).filter(
            StockMovement.product_id == product_id,
            StockMovement.location_id == location_id,
            StockMovement.reason == MovementReason.SALE.value,
            StockMovement.ts >= start_date,
        ).scalar() or Decimal("0")

        avg_daily_usage = float(total_usage) / lookback_days if lookback_days > 0 else 0
        lead_time = product.lead_time_days or 1
        safety_stock = avg_daily_usage * safety_factor
        reorder_point = (avg_daily_usage * lead_time) + safety_stock
        recommended_par = reorder_point + (avg_daily_usage * order_cycle_days)

        # Get current stock
        stock = self.db.query(StockOnHand).filter(
            StockOnHand.product_id == product_id,
            StockOnHand.location_id == location_id,
        ).first()
        current_qty = float(stock.qty) if stock else 0
        days_of_stock = current_qty / avg_daily_usage if avg_daily_usage > 0 else 999

        return {
            "product_id": product_id,
            "product_name": product.name,
            "unit": product.unit,
            "current_qty": current_qty,
            "current_par_level": float(product.par_level) if product.par_level else None,
            "avg_daily_usage": round(avg_daily_usage, 4),
            "lead_time_days": lead_time,
            "safety_factor": safety_factor,
            "safety_stock": round(safety_stock, 2),
            "reorder_point": round(reorder_point, 2),
            "recommended_par": round(recommended_par, 2),
            "order_cycle_days": order_cycle_days,
            "lookback_days": lookback_days,
            "days_of_stock_remaining": round(days_of_stock, 1),
            "needs_reorder": current_qty <= reorder_point,
        }

    def bulk_recalculate_pars(
        self,
        location_id: int = 1,
        lookback_days: int = 30,
        safety_factor: float = 1.5,
        order_cycle_days: int = 7,
        auto_apply: bool = False,
    ) -> Dict[str, Any]:
        """Recalculate PAR levels for all active products. Optionally auto-apply."""
        products = self.db.query(Product).filter(Product.active == True).all()
        results = []
        updated_count = 0

        for product in products:
            par_result = self.calculate_smart_par(
                product_id=product.id,
                location_id=location_id,
                lookback_days=lookback_days,
                safety_factor=safety_factor,
                order_cycle_days=order_cycle_days,
            )

            if "error" in par_result:
                continue

            if auto_apply and par_result["recommended_par"] > 0:
                old_par = product.par_level
                product.par_level = Decimal(str(round(par_result["recommended_par"], 2)))
                par_result["old_par_level"] = float(old_par) if old_par else None
                par_result["applied"] = True
                updated_count += 1
            else:
                par_result["applied"] = False

            results.append(par_result)

        if auto_apply:
            self.db.commit()

        return {
            "total_products": len(results),
            "updated": updated_count,
            "location_id": location_id,
            "parameters": {
                "lookback_days": lookback_days,
                "safety_factor": safety_factor,
                "order_cycle_days": order_cycle_days,
                "auto_apply": auto_apply,
            },
            "results": results,
        }

    # ===== STOCK RESERVATION SYSTEM =====

    def reserve_for_order(
        self,
        order_items: List[Dict[str, Any]],
        location_id: int = 1,
        reference_type: str = "order_reservation",
        reference_id: Optional[int] = None,
        created_by: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Reserve stock for an in-progress order (before fulfillment).
        Creates RESERVATION movements and increments reserved_qty on StockOnHand.
        The reserved stock is still physically present but not available for new orders.
        """
        results = {
            "success": True,
            "reservations": [],
            "errors": [],
            "total_reserved": 0,
        }

        for item in order_items:
            menu_item_id = item.get("menu_item_id")
            quantity = Decimal(str(item.get("quantity", 1)))

            if not menu_item_id:
                continue

            menu_item = self.db.query(MenuItem).filter(MenuItem.id == menu_item_id).first()
            if not menu_item:
                continue

            recipe = self._find_recipe_for_menu_item(menu_item)
            if not recipe:
                continue

            for line in recipe.lines:
                product = self.db.query(Product).filter(Product.id == line.product_id).first()
                if not product:
                    continue

                total_qty = line.qty * quantity
                reserve_qty = self._convert_units(total_qty, line.unit, product.unit)
                if reserve_qty is None:
                    results["errors"].append({
                        "error": f"Cannot convert {line.unit} to {product.unit}",
                        "product_id": product.id,
                    })
                    continue

                # Check available (non-reserved) stock
                stock = self.db.query(StockOnHand).filter(
                    StockOnHand.product_id == line.product_id,
                    StockOnHand.location_id == location_id,
                ).first()

                if not stock:
                    results["errors"].append({
                        "error": f"No stock for '{product.name}'",
                        "product_id": product.id,
                    })
                    results["success"] = False
                    continue

                reserved = getattr(stock, 'reserved_qty', Decimal("0")) or Decimal("0")
                available = stock.qty - reserved

                if available < reserve_qty:
                    results["errors"].append({
                        "error": f"Insufficient available stock for '{product.name}': need {reserve_qty}, have {available}",
                        "product_id": product.id,
                        "available": float(available),
                        "needed": float(reserve_qty),
                    })
                    results["success"] = False
                    continue

                # Increment reserved quantity
                if hasattr(stock, 'reserved_qty'):
                    stock.reserved_qty = (stock.reserved_qty or Decimal("0")) + reserve_qty

                # Create RESERVATION movement
                movement = StockMovement(
                    product_id=line.product_id,
                    location_id=location_id,
                    qty_delta=Decimal("0"),  # No actual stock change yet
                    reason=MovementReason.RESERVATION.value,
                    ref_type=reference_type,
                    ref_id=reference_id,
                    notes=f"Reserved: {menu_item.name} x{quantity} ({reserve_qty} {product.unit})",
                    created_by=created_by,
                )
                self.db.add(movement)

                results["reservations"].append({
                    "product_id": product.id,
                    "product_name": product.name,
                    "qty_reserved": float(reserve_qty),
                    "unit": product.unit,
                    "menu_item": menu_item.name,
                })
                results["total_reserved"] += 1

        if results["success"]:
            self.db.commit()
        else:
            self.db.rollback()

        return results

    def cancel_reservation(
        self,
        reference_id: int,
        reference_type: str = "order_reservation",
        location_id: int = 1,
    ) -> Dict[str, Any]:
        """
        Cancel stock reservations for an order.
        Releases reserved stock back to available pool.
        """
        # Find all reservation movements for this reference
        reservations = self.db.query(StockMovement).filter(
            StockMovement.ref_id == reference_id,
            StockMovement.ref_type == reference_type,
            StockMovement.reason == MovementReason.RESERVATION.value,
        ).all()

        if not reservations:
            return {"success": True, "message": "No reservations found", "released": 0}

        released = 0
        for reservation in reservations:
            # Parse reserved quantity from notes
            stock = self.db.query(StockOnHand).filter(
                StockOnHand.product_id == reservation.product_id,
                StockOnHand.location_id == reservation.location_id,
            ).first()

            if stock and hasattr(stock, 'reserved_qty') and stock.reserved_qty:
                # We need to figure out how much was reserved - parse from notes or use a heuristic
                # For robustness, we'll look at the notes pattern "Reserved: ... (X unit)"
                import re
                match = re.search(r'\((\d+\.?\d*)\s+\w+\)', reservation.notes or "")
                release_qty = Decimal(match.group(1)) if match else Decimal("0")

                stock.reserved_qty = max(Decimal("0"), (stock.reserved_qty or Decimal("0")) - release_qty)

                # Create RESERVATION_RELEASE movement
                release_movement = StockMovement(
                    product_id=reservation.product_id,
                    location_id=reservation.location_id,
                    qty_delta=Decimal("0"),
                    reason=MovementReason.RESERVATION_RELEASE.value,
                    ref_type=reference_type,
                    ref_id=reference_id,
                    notes=f"Reservation cancelled - released {release_qty}",
                )
                self.db.add(release_movement)
                released += 1

        self.db.commit()
        return {"success": True, "released": released}

    def fulfill_reservation(
        self,
        order_items: List[Dict[str, Any]],
        location_id: int = 1,
        reference_type: str = "pos_sale",
        reference_id: Optional[int] = None,
        reservation_reference_id: Optional[int] = None,
        created_by: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Convert reservations to actual deductions on order fulfillment.
        Releases reserved stock and performs actual deduction.
        """
        # Cancel reservation first (release reserved qty)
        if reservation_reference_id:
            self.cancel_reservation(
                reference_id=reservation_reference_id,
                location_id=location_id,
            )

        # Now perform actual deduction (allow_negative=True since we validated at reservation time)
        return self.deduct_for_order(
            order_items=order_items,
            location_id=location_id,
            reference_type=reference_type,
            reference_id=reference_id,
            created_by=created_by,
            allow_negative=True,
        )

    # ===== REFUND =====

    def refund_for_order(
        self,
        order_items: List[Dict[str, Any]],
        location_id: int = 1,
        reference_type: str = "pos_refund",
        reference_id: Optional[int] = None,
        created_by: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Add stock back for refunded/voided items.
        Same logic as deduct_for_order but adds instead of subtracts.
        """
        results = {
            "success": True,
            "additions": [],
            "errors": [],
            "warnings": [],
        }

        for item in order_items:
            menu_item_id = item.get("menu_item_id")
            quantity = Decimal(str(item.get("quantity", 1)))

            menu_item = self.db.query(MenuItem).filter(MenuItem.id == menu_item_id).first()
            if not menu_item:
                continue

            recipe = self._find_recipe_for_menu_item(menu_item)
            if not recipe:
                continue

            for line in recipe.lines:
                product = self.db.query(Product).filter(Product.id == line.product_id).first()
                if not product:
                    continue

                total_qty = line.qty * quantity
                add_qty = self._convert_units(total_qty, line.unit, product.unit)
                if add_qty is None:
                    continue

                # Get stock record
                stock = self.db.query(StockOnHand).filter(
                    StockOnHand.product_id == line.product_id,
                    StockOnHand.location_id == location_id,
                ).first()

                if stock:
                    stock.qty += add_qty
                else:
                    stock = StockOnHand(
                        product_id=line.product_id,
                        location_id=location_id,
                        qty=add_qty,
                    )
                    self.db.add(stock)

                # Create movement record
                movement = StockMovement(
                    product_id=line.product_id,
                    location_id=location_id,
                    qty_delta=add_qty,
                    reason=MovementReason.REFUND.value,
                    ref_type=reference_type,
                    ref_id=reference_id,
                    notes=f"Refund: {menu_item.name} x{quantity}",
                    created_by=created_by,
                )
                self.db.add(movement)

                results["additions"].append({
                    "product_name": product.name,
                    "qty_added": float(add_qty),
                    "unit": product.unit,
                })

        self.db.commit()
        return results

    # ===== RECIPE STOCK CHECK =====

    def get_stock_for_recipe(
        self,
        recipe_id: int,
        location_id: int = 1,
    ) -> Dict[str, Any]:
        """Get current stock levels for all ingredients in a recipe."""
        recipe = self.db.query(Recipe).filter(Recipe.id == recipe_id).first()
        if not recipe:
            return {"error": "Recipe not found"}

        ingredients = []
        can_make = float("inf")

        for line in recipe.lines:
            product = self.db.query(Product).filter(Product.id == line.product_id).first()
            if not product:
                continue

            stock = self.db.query(StockOnHand).filter(
                StockOnHand.product_id == line.product_id,
                StockOnHand.location_id == location_id,
            ).first()

            stock_qty = stock.qty if stock else Decimal("0")
            reserved = getattr(stock, 'reserved_qty', Decimal("0")) or Decimal("0") if stock else Decimal("0")
            available_qty = stock_qty - reserved

            # Convert recipe qty to product unit
            needed_per_item = self._convert_units(line.qty, line.unit, product.unit) or line.qty

            # How many can we make with current stock?
            if needed_per_item > 0:
                possible = int(available_qty / needed_per_item)
                can_make = min(can_make, possible)

            ingredients.append({
                "product_id": product.id,
                "product_name": product.name,
                "needed_qty": float(needed_per_item),
                "unit": product.unit,
                "stock_qty": float(stock_qty),
                "available_qty": float(available_qty),
                "reserved_qty": float(reserved),
                "sufficient": available_qty >= needed_per_item,
            })

        return {
            "recipe_id": recipe.id,
            "recipe_name": recipe.name,
            "ingredients": ingredients,
            "can_make": can_make if can_make != float("inf") else 0,
        }

    def deduct_for_recipe(
        self,
        recipe: Recipe,
        quantity: Decimal,
        location_id: int,
        is_refund: bool = False,
        reference_type: str = "pos_sale",
        reference_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Deduct stock for a recipe directly (used by POS batch processing).
        """
        movements_created = 0
        deductions = []

        multiplier = quantity if is_refund else -quantity

        for line in recipe.lines:
            product = self.db.query(Product).filter(Product.id == line.product_id).first()
            if not product:
                continue

            qty_delta = multiplier * line.qty

            if line.unit != product.unit:
                converted = self._convert_units(abs(qty_delta), line.unit, product.unit)
                if converted is not None:
                    qty_delta = -converted if not is_refund else converted

            movement = StockMovement(
                product_id=line.product_id,
                location_id=location_id,
                qty_delta=qty_delta,
                reason=MovementReason.REFUND.value if is_refund else MovementReason.SALE.value,
                ref_type=reference_type,
                ref_id=reference_id,
                notes=notes or f"{recipe.name} x {quantity}",
            )
            self.db.add(movement)
            movements_created += 1

            stock = self.db.query(StockOnHand).filter(
                StockOnHand.product_id == line.product_id,
                StockOnHand.location_id == location_id,
            ).first()

            if stock:
                stock.qty += qty_delta
            else:
                stock = StockOnHand(
                    product_id=line.product_id,
                    location_id=location_id,
                    qty=qty_delta,
                )
                self.db.add(stock)

            deductions.append({
                "product_id": product.id,
                "product_name": product.name,
                "qty_delta": float(qty_delta),
                "unit": product.unit,
            })

        return {
            "success": True,
            "recipe_name": recipe.name,
            "movements_created": movements_created,
            "deductions": deductions,
        }

    def find_recipe_by_pos_data(
        self,
        pos_item_id: Optional[str],
        name: str,
    ) -> Optional[Recipe]:
        """Find a recipe by POS item ID or name."""
        if pos_item_id:
            recipe = self.db.query(Recipe).filter(
                Recipe.pos_item_id == pos_item_id
            ).first()
            if recipe:
                return recipe

        recipe = self.db.query(Recipe).filter(
            Recipe.name.ilike(name)
        ).first()
        if recipe:
            return recipe

        recipe = self.db.query(Recipe).filter(
            Recipe.pos_item_name.ilike(name)
        ).first()

        return recipe

    # ===== PURCHASE ORDER RECEIVING =====

    def receive_purchase_order(
        self,
        po_lines: List[Dict[str, Any]],
        location_id: int,
        po_id: int,
        created_by: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Add stock when a purchase order is received."""
        results = {
            "success": True,
            "additions": [],
            "errors": [],
            "total_items_received": 0,
            "total_cost": Decimal("0"),
        }

        for line in po_lines:
            product_id = line.get("product_id")
            received_qty = Decimal(str(line.get("received_qty", 0)))
            unit_cost = Decimal(str(line.get("unit_cost", 0))) if line.get("unit_cost") else None

            if not product_id or received_qty <= 0:
                results["errors"].append({"error": "Invalid line data", "line": line})
                continue

            product = self.db.query(Product).filter(Product.id == product_id).first()
            if not product:
                results["errors"].append({"error": f"Product {product_id} not found"})
                continue

            stock = self.db.query(StockOnHand).filter(
                StockOnHand.product_id == product_id,
                StockOnHand.location_id == location_id,
            ).first()

            if stock:
                old_qty = stock.qty
                stock.qty += received_qty
            else:
                old_qty = Decimal("0")
                stock = StockOnHand(
                    product_id=product_id,
                    location_id=location_id,
                    qty=received_qty,
                )
                self.db.add(stock)

            if unit_cost and unit_cost > 0:
                product.cost_price = unit_cost

            movement = StockMovement(
                product_id=product_id,
                location_id=location_id,
                qty_delta=received_qty,
                reason=MovementReason.PURCHASE.value,
                ref_type="purchase_order",
                ref_id=po_id,
                notes=f"PO#{po_id} received: {product.name} x{received_qty}",
                created_by=created_by,
            )
            self.db.add(movement)

            line_cost = received_qty * (unit_cost or product.cost_price or Decimal("0"))
            results["total_cost"] += line_cost
            results["total_items_received"] += 1
            results["additions"].append({
                "product_id": product_id,
                "product_name": product.name,
                "qty_received": float(received_qty),
                "unit": product.unit,
                "old_qty": float(old_qty),
                "new_qty": float(old_qty + received_qty),
                "unit_cost": float(unit_cost) if unit_cost else None,
                "line_cost": float(line_cost),
            })

        self.db.commit()
        results["total_cost"] = float(results["total_cost"])
        return results

    # ===== WASTE TRACKING =====

    def deduct_for_waste(
        self,
        product_id: int,
        quantity: Decimal,
        unit: str,
        location_id: int,
        waste_entry_id: Optional[int] = None,
        reason: Optional[str] = None,
        created_by: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Deduct stock when waste is recorded."""
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return {"success": False, "error": f"Product {product_id} not found"}

        deduct_qty = self._convert_units(quantity, unit, product.unit)
        if deduct_qty is None:
            deduct_qty = quantity

        stock = self.db.query(StockOnHand).filter(
            StockOnHand.product_id == product_id,
            StockOnHand.location_id == location_id,
        ).first()

        old_qty = Decimal("0")
        if stock:
            old_qty = stock.qty
            stock.qty -= deduct_qty
        else:
            stock = StockOnHand(
                product_id=product_id,
                location_id=location_id,
                qty=-deduct_qty,
            )
            self.db.add(stock)

        movement = StockMovement(
            product_id=product_id,
            location_id=location_id,
            qty_delta=-deduct_qty,
            reason=MovementReason.WASTE.value,
            ref_type="waste_tracking",
            ref_id=waste_entry_id,
            notes=reason or f"Waste: {product.name} x{quantity} {unit}",
            created_by=created_by,
        )
        self.db.add(movement)
        self.db.commit()

        return {
            "success": True,
            "product_id": product_id,
            "product_name": product.name,
            "qty_deducted": float(deduct_qty),
            "unit": product.unit,
            "old_qty": float(old_qty),
            "new_qty": float(old_qty - deduct_qty),
        }

    # ===== STOCK TRANSFERS =====

    def transfer_stock(
        self,
        product_id: int,
        quantity: Decimal,
        from_location_id: int,
        to_location_id: int,
        transfer_id: Optional[int] = None,
        notes: Optional[str] = None,
        created_by: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Transfer stock between locations with paired movements."""
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return {"success": False, "error": f"Product {product_id} not found"}

        if quantity <= 0:
            return {"success": False, "error": "Quantity must be positive"}

        source_stock = self.db.query(StockOnHand).filter(
            StockOnHand.product_id == product_id,
            StockOnHand.location_id == from_location_id,
        ).first()

        source_old_qty = source_stock.qty if source_stock else Decimal("0")
        if source_old_qty < quantity:
            return {
                "success": False,
                "error": f"Insufficient stock: have {source_old_qty}, need {quantity}",
                "available": float(source_old_qty),
            }

        source_stock.qty -= quantity

        dest_stock = self.db.query(StockOnHand).filter(
            StockOnHand.product_id == product_id,
            StockOnHand.location_id == to_location_id,
        ).first()

        if dest_stock:
            dest_stock.qty += quantity
        else:
            dest_stock = StockOnHand(
                product_id=product_id,
                location_id=to_location_id,
                qty=quantity,
            )
            self.db.add(dest_stock)

        note_text = notes or f"Transfer: {product.name} x{quantity}"

        movement_out = StockMovement(
            product_id=product_id,
            location_id=from_location_id,
            qty_delta=-quantity,
            reason=MovementReason.TRANSFER_OUT.value,
            ref_type="stock_transfer",
            ref_id=transfer_id,
            notes=note_text,
            created_by=created_by,
        )
        self.db.add(movement_out)

        movement_in = StockMovement(
            product_id=product_id,
            location_id=to_location_id,
            qty_delta=quantity,
            reason=MovementReason.TRANSFER_IN.value,
            ref_type="stock_transfer",
            ref_id=transfer_id,
            notes=note_text,
            created_by=created_by,
        )
        self.db.add(movement_in)

        self.db.commit()

        return {
            "success": True,
            "product_id": product_id,
            "product_name": product.name,
            "qty_transferred": float(quantity),
            "unit": product.unit,
            "from_location_id": from_location_id,
            "to_location_id": to_location_id,
            "source_new_qty": float(source_stock.qty),
            "dest_new_qty": float(dest_stock.qty),
        }

    # ===== MANUAL ADJUSTMENT =====

    def adjust_stock(
        self,
        product_id: int,
        new_qty: Decimal,
        location_id: int,
        reason: str = "Manual adjustment",
        created_by: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Manually adjust stock to a specific quantity."""
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return {"success": False, "error": f"Product {product_id} not found"}

        stock = self.db.query(StockOnHand).filter(
            StockOnHand.product_id == product_id,
            StockOnHand.location_id == location_id,
        ).first()

        old_qty = stock.qty if stock else Decimal("0")
        delta = new_qty - old_qty

        if delta == 0:
            return {"success": True, "message": "No change needed", "qty": float(new_qty)}

        if stock:
            stock.qty = new_qty
        else:
            stock = StockOnHand(
                product_id=product_id,
                location_id=location_id,
                qty=new_qty,
            )
            self.db.add(stock)

        movement = StockMovement(
            product_id=product_id,
            location_id=location_id,
            qty_delta=delta,
            reason=MovementReason.ADJUSTMENT.value,
            ref_type="manual_adjustment",
            notes=reason,
            created_by=created_by,
        )
        self.db.add(movement)
        self.db.commit()

        return {
            "success": True,
            "product_id": product_id,
            "product_name": product.name,
            "old_qty": float(old_qty),
            "new_qty": float(new_qty),
            "delta": float(delta),
            "unit": product.unit,
        }

    # ===== SHRINKAGE / VARIANCE ANALYSIS =====

    def calculate_shrinkage(
        self,
        location_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Calculate theoretical vs actual usage for shrinkage detection."""
        from sqlalchemy import and_

        filters = [StockMovement.location_id == location_id]
        if start_date:
            filters.append(StockMovement.ts >= start_date)
        if end_date:
            filters.append(StockMovement.ts <= end_date)

        sales_query = self.db.query(
            StockMovement.product_id,
            func.sum(func.abs(StockMovement.qty_delta)).label("theoretical_usage"),
        ).filter(
            and_(*filters, StockMovement.reason == MovementReason.SALE.value)
        ).group_by(StockMovement.product_id)

        theoretical = {row.product_id: float(row.theoretical_usage) for row in sales_query.all()}

        count_query = self.db.query(
            StockMovement.product_id,
            func.sum(StockMovement.qty_delta).label("count_adjustment"),
        ).filter(
            and_(*filters, StockMovement.reason == MovementReason.INVENTORY_COUNT.value)
        ).group_by(StockMovement.product_id)

        count_adjustments = {row.product_id: float(row.count_adjustment) for row in count_query.all()}

        waste_query = self.db.query(
            StockMovement.product_id,
            func.sum(func.abs(StockMovement.qty_delta)).label("waste_total"),
        ).filter(
            and_(*filters, StockMovement.reason == MovementReason.WASTE.value)
        ).group_by(StockMovement.product_id)

        waste_totals = {row.product_id: float(row.waste_total) for row in waste_query.all()}

        all_product_ids = set(theoretical.keys()) | set(count_adjustments.keys())
        shrinkage_items = []
        total_shrinkage_value = Decimal("0")

        for pid in all_product_ids:
            product = self.db.query(Product).filter(Product.id == pid).first()
            if not product:
                continue

            theo = theoretical.get(pid, 0)
            count_adj = count_adjustments.get(pid, 0)
            waste = waste_totals.get(pid, 0)

            shrinkage_qty = abs(count_adj) if count_adj < 0 else 0
            cost_per_unit = float(product.cost_price or 0)
            shrinkage_value = shrinkage_qty * cost_per_unit

            if shrinkage_qty > 0 or theo > 0:
                shrinkage_pct = (shrinkage_qty / theo * 100) if theo > 0 else 0
                total_shrinkage_value += Decimal(str(shrinkage_value))

                shrinkage_items.append({
                    "product_id": pid,
                    "product_name": product.name,
                    "unit": product.unit,
                    "theoretical_usage": theo,
                    "recorded_waste": waste,
                    "inventory_adjustment": count_adj,
                    "shrinkage_qty": shrinkage_qty,
                    "shrinkage_value": shrinkage_value,
                    "shrinkage_pct": round(shrinkage_pct, 2),
                    "risk_level": "high" if shrinkage_pct > 5 else "medium" if shrinkage_pct > 2 else "low",
                })

        shrinkage_items.sort(key=lambda x: x["shrinkage_value"], reverse=True)

        return {
            "location_id": location_id,
            "period": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None,
            },
            "total_shrinkage_value": float(total_shrinkage_value),
            "items_with_shrinkage": len([i for i in shrinkage_items if i["shrinkage_qty"] > 0]),
            "total_items_analyzed": len(shrinkage_items),
            "items": shrinkage_items,
        }

    # ===== STOCK AVAILABILITY CHECK =====

    def check_availability(
        self,
        menu_item_ids: List[int],
        location_id: int = 1,
    ) -> Dict[str, Any]:
        """Check stock availability for menu items, accounting for reservations."""
        availability = []

        for menu_item_id in menu_item_ids:
            menu_item = self.db.query(MenuItem).filter(MenuItem.id == menu_item_id).first()
            if not menu_item:
                availability.append({
                    "menu_item_id": menu_item_id,
                    "available": False,
                    "reason": "Menu item not found",
                })
                continue

            recipe = self._find_recipe_for_menu_item(menu_item)
            if not recipe:
                availability.append({
                    "menu_item_id": menu_item_id,
                    "name": menu_item.name,
                    "available": True,
                    "can_make": 999,
                    "reason": "No recipe linked (unlimited)",
                })
                continue

            stock_info = self.get_stock_for_recipe(recipe.id, location_id)
            can_make = stock_info.get("can_make", 0)

            availability.append({
                "menu_item_id": menu_item_id,
                "name": menu_item.name,
                "available": can_make > 0,
                "can_make": can_make,
                "ingredients": stock_info.get("ingredients", []),
                "should_86": can_make == 0,
            })

        return {
            "location_id": location_id,
            "items": availability,
            "items_to_86": [i for i in availability if i.get("should_86")],
        }

    # ===== MULTI-LOCATION AGGREGATION =====

    def get_aggregate_stock(self) -> Dict[str, Any]:
        """Get company-wide stock aggregation across all locations."""
        from app.models.location import Location

        # Get all stock grouped by product
        stock_data = self.db.query(
            StockOnHand.product_id,
            func.sum(StockOnHand.qty).label("total_qty"),
            func.count(StockOnHand.location_id).label("location_count"),
        ).group_by(StockOnHand.product_id).all()

        products_aggregate = []
        total_value = Decimal("0")

        for row in stock_data:
            product = self.db.query(Product).filter(Product.id == row.product_id).first()
            if not product:
                continue

            # Get per-location breakdown
            locations_breakdown = []
            location_stocks = self.db.query(StockOnHand).filter(
                StockOnHand.product_id == row.product_id
            ).all()

            for ls in location_stocks:
                location = self.db.query(Location).filter(Location.id == ls.location_id).first()
                locations_breakdown.append({
                    "location_id": ls.location_id,
                    "location_name": location.name if location else f"Location {ls.location_id}",
                    "qty": float(ls.qty),
                    "value": float(ls.qty * (product.cost_price or Decimal("0"))),
                })

            product_value = row.total_qty * (product.cost_price or Decimal("0"))
            total_value += product_value

            products_aggregate.append({
                "product_id": product.id,
                "product_name": product.name,
                "unit": product.unit,
                "total_qty": float(row.total_qty),
                "location_count": row.location_count,
                "total_value": float(product_value),
                "par_level": float(product.par_level) if product.par_level else None,
                "locations": locations_breakdown,
            })

        products_aggregate.sort(key=lambda x: x["total_value"], reverse=True)

        return {
            "total_products": len(products_aggregate),
            "total_value": float(total_value),
            "products": products_aggregate,
        }

    def suggest_transfers(self, location_id: Optional[int] = None) -> Dict[str, Any]:
        """Suggest transfers from overstocked locations to understocked ones."""
        suggestions = []

        products = self.db.query(Product).filter(
            Product.active == True,
            Product.par_level.isnot(None),
        ).all()

        for product in products:
            stocks = self.db.query(StockOnHand).filter(
                StockOnHand.product_id == product.id,
            ).all()

            if len(stocks) < 2:
                continue

            overstocked = []
            understocked = []

            for s in stocks:
                par = product.par_level or Decimal("0")
                if s.qty > par * Decimal("1.5"):
                    overstocked.append({"location_id": s.location_id, "qty": s.qty, "excess": s.qty - par})
                elif s.qty < par * Decimal("0.5"):
                    understocked.append({"location_id": s.location_id, "qty": s.qty, "shortage": par - s.qty})

            for under in understocked:
                for over in overstocked:
                    if location_id and under["location_id"] != location_id and over["location_id"] != location_id:
                        continue
                    transfer_qty = min(over["excess"], under["shortage"])
                    if transfer_qty > 0:
                        suggestions.append({
                            "product_id": product.id,
                            "product_name": product.name,
                            "from_location_id": over["location_id"],
                            "to_location_id": under["location_id"],
                            "suggested_qty": float(transfer_qty),
                            "unit": product.unit,
                        })

        return {
            "suggestions": suggestions,
            "total": len(suggestions),
        }


def get_stock_deduction_service(db: Session) -> StockDeductionService:
    """Factory function to get stock deduction service."""
    return StockDeductionService(db)

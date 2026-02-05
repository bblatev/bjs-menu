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
      - Deduct from StockOnHand
      - Create StockMovement record for audit
3. Return summary of deductions
"""

from decimal import Decimal
from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.stock import StockOnHand, StockMovement, MovementReason
from app.models.recipe import Recipe, RecipeLine
from app.models.restaurant import MenuItem
from app.models.product import Product


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


class StockDeductionService:
    """Service for deducting stock when orders are placed."""

    def __init__(self, db: Session):
        self.db = db

    def deduct_for_order(
        self,
        order_items: List[Dict[str, Any]],
        location_id: int = 1,
        reference_type: str = "pos_sale",
        reference_id: Optional[int] = None,
        created_by: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Deduct stock for all items in an order.

        Args:
            order_items: List of dicts with menu_item_id and quantity
            location_id: Location to deduct from
            reference_type: Type of reference (pos_sale, guest_order, etc.)
            reference_id: ID of the reference (check_id, order_id, etc.)
            created_by: User ID who created the order

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
                )

                if deduction_result.get("success"):
                    results["deductions"].append(deduction_result)
                    results["total_ingredients_deducted"] += 1
                else:
                    results["errors"].append(deduction_result)
                    results["success"] = False

            results["total_items_processed"] += 1

        self.db.commit()
        return results

    def _find_recipe_for_menu_item(self, menu_item: MenuItem) -> Optional[Recipe]:
        """Find recipe for a menu item."""
        # First try by recipe_id if MenuItem has it
        if hasattr(menu_item, 'recipe_id') and menu_item.recipe_id:
            recipe = self.db.query(Recipe).filter(Recipe.id == menu_item.recipe_id).first()
            if recipe:
                return recipe

        # Try by pos_item_id (menu item ID as string)
        recipe = self.db.query(Recipe).filter(
            Recipe.pos_item_id == str(menu_item.id)
        ).first()
        if recipe:
            return recipe

        # Try by name match
        recipe = self.db.query(Recipe).filter(
            Recipe.name == menu_item.name
        ).first()
        if recipe:
            return recipe

        # Try by pos_item_name match
        recipe = self.db.query(Recipe).filter(
            Recipe.pos_item_name == menu_item.name
        ).first()

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

        # Convert units if needed
        deduct_qty = self._convert_units(total_qty, recipe_unit, product.unit)
        if deduct_qty is None:
            return {
                "success": False,
                "error": f"Cannot convert {recipe_unit} to {product.unit}",
                "product_id": product_id,
                "product_name": product.name,
            }

        # Get or create StockOnHand record
        stock = self.db.query(StockOnHand).filter(
            StockOnHand.product_id == product_id,
            StockOnHand.location_id == location_id,
        ).first()

        if not stock:
            # Create new stock record with 0 (will go negative)
            stock = StockOnHand(
                product_id=product_id,
                location_id=location_id,
                qty=Decimal("0"),
            )
            self.db.add(stock)
            self.db.flush()

        # Check if enough stock (warning only, still deduct)
        old_qty = stock.qty
        new_qty = old_qty - deduct_qty
        warning = None
        if new_qty < 0:
            warning = f"Stock for '{product.name}' went negative: {new_qty} {product.unit}"

        # Update stock
        stock.qty = new_qty

        # FIFO: Deduct from oldest batches first
        self._deduct_from_batches_fifo(product_id, location_id, deduct_qty)

        # Create movement record
        movement = StockMovement(
            product_id=product_id,
            location_id=location_id,
            qty_delta=-deduct_qty,  # Negative for deduction
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
    ) -> None:
        """
        Deduct from inventory batches using FIFO (First In, First Out).
        Oldest batches (by received_date) are consumed first.
        Also checks for expired batches and marks them.
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

        except Exception:
            pass  # Batch tracking is optional — if table doesn't exist, skip silently

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
            # Incompatible units
            return None

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
                    qty_delta=add_qty,  # Positive for refund
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

            # Convert recipe qty to product unit
            needed_per_item = self._convert_units(line.qty, line.unit, product.unit) or line.qty

            # How many can we make with current stock?
            if needed_per_item > 0:
                possible = int(stock_qty / needed_per_item)
                can_make = min(can_make, possible)

            ingredients.append({
                "product_id": product.id,
                "product_name": product.name,
                "needed_qty": float(needed_per_item),
                "unit": product.unit,
                "stock_qty": float(stock_qty),
                "sufficient": stock_qty >= needed_per_item,
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

        Args:
            recipe: The Recipe object to deduct for
            quantity: Number of items sold
            location_id: Location to deduct from
            is_refund: True if this is a refund (adds stock back)
            reference_type: Type of reference
            reference_id: ID of the reference
            notes: Optional notes for the movement

        Returns:
            Dict with deduction summary
        """
        movements_created = 0
        deductions = []

        # Calculate multiplier (negative for sales, positive for refunds)
        multiplier = quantity if is_refund else -quantity

        for line in recipe.lines:
            product = self.db.query(Product).filter(Product.id == line.product_id).first()
            if not product:
                continue

            # Calculate qty delta
            qty_delta = multiplier * line.qty

            # Convert units if needed
            if line.unit != product.unit:
                converted = self._convert_units(abs(qty_delta), line.unit, product.unit)
                if converted is not None:
                    qty_delta = -converted if not is_refund else converted

            # Create stock movement
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

            # Update stock on hand
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
        """
        Find a recipe by POS item ID or name.

        Args:
            pos_item_id: POS system item ID
            name: Item name from POS

        Returns:
            Recipe if found, None otherwise
        """
        # Try by pos_item_id first
        if pos_item_id:
            recipe = self.db.query(Recipe).filter(
                Recipe.pos_item_id == pos_item_id
            ).first()
            if recipe:
                return recipe

        # Try by exact name match (case-insensitive)
        recipe = self.db.query(Recipe).filter(
            Recipe.name.ilike(name)
        ).first()
        if recipe:
            return recipe

        # Try by pos_item_name
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
        """
        Add stock when a purchase order is received.

        Args:
            po_lines: List of dicts with product_id, received_qty, unit_cost
            location_id: Location receiving the goods
            po_id: Purchase order ID for audit trail
            created_by: User ID who received the goods

        Returns:
            Dict with receiving summary
        """
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

            # Update stock on hand
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

            # Update product cost price if provided
            if unit_cost and unit_cost > 0:
                product.cost_price = unit_cost

            # Create stock movement
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

    # ===== WASTE TRACKING → STOCK INTEGRATION =====

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
        """
        Deduct stock when waste is recorded.

        Args:
            product_id: Product that was wasted
            quantity: Amount wasted
            unit: Unit of measurement for the waste
            location_id: Location where waste occurred
            waste_entry_id: WasteTrackingEntry ID for audit trail
            reason: Reason for waste
            created_by: User ID

        Returns:
            Dict with deduction result
        """
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return {"success": False, "error": f"Product {product_id} not found"}

        # Convert units if needed
        deduct_qty = self._convert_units(quantity, unit, product.unit)
        if deduct_qty is None:
            # If unit conversion fails, try using quantity directly
            deduct_qty = quantity

        # Update stock
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

        # Create stock movement
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
        """
        Transfer stock between locations.
        Creates paired TRANSFER_OUT and TRANSFER_IN movements.

        Args:
            product_id: Product to transfer
            quantity: Amount to transfer
            from_location_id: Source location
            to_location_id: Destination location
            transfer_id: Transfer record ID for audit trail
            notes: Transfer notes
            created_by: User ID

        Returns:
            Dict with transfer result
        """
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return {"success": False, "error": f"Product {product_id} not found"}

        if quantity <= 0:
            return {"success": False, "error": "Quantity must be positive"}

        # Check source stock
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

        # Deduct from source
        source_stock.qty -= quantity

        # Add to destination
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

        # Create TRANSFER_OUT movement
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

        # Create TRANSFER_IN movement
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
        """
        Manually adjust stock to a specific quantity.

        Args:
            product_id: Product to adjust
            new_qty: New quantity to set
            location_id: Location
            reason: Reason for adjustment
            created_by: User ID

        Returns:
            Dict with adjustment result
        """
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
        """
        Calculate theoretical vs actual usage for shrinkage detection.

        Theoretical = sum of recipe-based deductions (SALE movements)
        Actual = difference measured by inventory counts
        Shrinkage = Theoretical - Actual (positive = unaccounted loss)
        """
        from sqlalchemy import func, and_

        filters = [StockMovement.location_id == location_id]
        if start_date:
            filters.append(StockMovement.ts >= start_date)
        if end_date:
            filters.append(StockMovement.ts <= end_date)

        # Get theoretical usage (sales deductions)
        sales_query = self.db.query(
            StockMovement.product_id,
            func.sum(func.abs(StockMovement.qty_delta)).label("theoretical_usage"),
        ).filter(
            and_(*filters, StockMovement.reason == MovementReason.SALE.value)
        ).group_by(StockMovement.product_id)

        theoretical = {row.product_id: float(row.theoretical_usage) for row in sales_query.all()}

        # Get actual adjustments from inventory counts
        count_query = self.db.query(
            StockMovement.product_id,
            func.sum(StockMovement.qty_delta).label("count_adjustment"),
        ).filter(
            and_(*filters, StockMovement.reason == MovementReason.INVENTORY_COUNT.value)
        ).group_by(StockMovement.product_id)

        count_adjustments = {row.product_id: float(row.count_adjustment) for row in count_query.all()}

        # Get waste records
        waste_query = self.db.query(
            StockMovement.product_id,
            func.sum(func.abs(StockMovement.qty_delta)).label("waste_total"),
        ).filter(
            and_(*filters, StockMovement.reason == MovementReason.WASTE.value)
        ).group_by(StockMovement.product_id)

        waste_totals = {row.product_id: float(row.waste_total) for row in waste_query.all()}

        # Calculate shrinkage per product
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

            # Shrinkage = unaccounted loss
            # If count adjustment is negative (counted less than expected), that's shrinkage
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

        # Sort by shrinkage value descending
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
        """
        Check stock availability for menu items.
        Returns which items can be made and how many.
        """
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


def get_stock_deduction_service(db: Session) -> StockDeductionService:
    """Factory function to get stock deduction service."""
    return StockDeductionService(db)

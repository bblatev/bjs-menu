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


def get_stock_deduction_service(db: Session) -> StockDeductionService:
    """Factory function to get stock deduction service."""
    return StockDeductionService(db)

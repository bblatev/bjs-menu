"""
Order Inventory Sync Service
Automatically deducts stock when orders are placed
"""
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from datetime import datetime, timezone
import logging

from app.models import (
    Order, OrderItem, MenuItem, StockItem, Recipe, RecipeIngredient,
    StockMovement
)

logger = logging.getLogger(__name__)


class OrderInventorySyncService:
    """
    Handles automatic stock deduction when orders are placed.
    Links orders to recipes and deducts ingredients from inventory.
    """

    def __init__(self, db: Session):
        self.db = db

    def _prefetch_order_data(self, order_items: List, venue_id: int) -> Dict[str, Any]:
        """
        Batch-load all MenuItem, Recipe, RecipeIngredient, and StockItem
        records needed for order processing, avoiding N+1 queries.
        """
        menu_item_ids = [oi.menu_item_id for oi in order_items]

        # Batch-load menu items
        menu_items_list = self.db.query(MenuItem).filter(
            MenuItem.id.in_(menu_item_ids)
        ).all()
        menu_items_map = {mi.id: mi for mi in menu_items_list}

        # Batch-load active recipes for these menu items
        recipes_list = self.db.query(Recipe).filter(
            Recipe.menu_item_id.in_(menu_item_ids),
            Recipe.is_active == True
        ).all()
        recipes_map = {r.menu_item_id: r for r in recipes_list}

        # Batch-load recipe ingredients for all recipes
        recipe_ids = [r.id for r in recipes_list]
        ingredients_list = self.db.query(RecipeIngredient).filter(
            RecipeIngredient.recipe_id.in_(recipe_ids)
        ).all() if recipe_ids else []
        ingredients_map: Dict[int, List] = {}
        for ing in ingredients_list:
            ingredients_map.setdefault(ing.recipe_id, []).append(ing)

        # Batch-load stock items for this venue
        stock_item_ids = [ing.stock_item_id for ing in ingredients_list]
        stock_items_list = self.db.query(StockItem).filter(
            StockItem.id.in_(stock_item_ids),
            StockItem.venue_id == venue_id
        ).all() if stock_item_ids else []
        stock_items_map = {si.id: si for si in stock_items_list}

        return {
            "menu_items": menu_items_map,
            "recipes": recipes_map,
            "ingredients": ingredients_map,
            "stock_items": stock_items_map,
        }

    def deduct_order_stock(self, order_id: int) -> Dict[str, Any]:
        """
        Deduct stock for all items in an order based on recipes.

        Args:
            order_id: The order ID to process

        Returns:
            Dict with deduction results
        """
        order = self.db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return {"success": False, "error": "Order not found"}

        results = {
            "order_id": order_id,
            "items_processed": 0,
            "stock_deductions": [],
            "warnings": [],
            "errors": []
        }

        order_items = self.db.query(OrderItem).filter(OrderItem.order_id == order_id).all()

        # Batch-load all related records to avoid N+1 queries
        prefetched = self._prefetch_order_data(order_items, order.venue_id)

        for order_item in order_items:
            try:
                deduction_result = self._deduct_item_stock(
                    order_item.menu_item_id,
                    order_item.quantity,
                    order.venue_id,
                    order_id,
                    prefetched
                )
                results["items_processed"] += 1
                results["stock_deductions"].extend(deduction_result.get("deductions", []))
                results["warnings"].extend(deduction_result.get("warnings", []))
            except Exception as e:
                results["errors"].append({
                    "menu_item_id": order_item.menu_item_id,
                    "error": str(e)
                })

        self.db.commit()

        results["success"] = len(results["errors"]) == 0
        return results

    def _deduct_item_stock(
        self,
        menu_item_id: int,
        quantity: int,
        venue_id: int,
        order_id: int,
        prefetched: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Deduct stock for a single menu item based on its recipe.
        Uses prefetched data to avoid individual queries.
        """
        result = {"deductions": [], "warnings": []}

        # Look up menu item from prefetched data
        menu_item = prefetched["menu_items"].get(menu_item_id)
        if not menu_item:
            return result

        # Look up recipe from prefetched data
        recipe = prefetched["recipes"].get(menu_item_id)

        if not recipe:
            # No recipe - can't deduct stock
            result["warnings"].append({
                "menu_item_id": menu_item_id,
                "message": "No recipe found for item"
            })
            return result

        # Look up recipe ingredients from prefetched data
        ingredients = prefetched["ingredients"].get(recipe.id, [])

        for ingredient in ingredients:
            # Calculate total quantity needed
            qty_needed = float(ingredient.quantity) * quantity

            # Look up stock item from prefetched data
            stock_item = prefetched["stock_items"].get(ingredient.stock_item_id)

            if not stock_item:
                result["warnings"].append({
                    "stock_item_id": ingredient.stock_item_id,
                    "message": "Stock item not found"
                })
                continue

            # Check if enough stock
            current_qty = float(stock_item.current_quantity or 0)
            if current_qty < qty_needed:
                result["warnings"].append({
                    "stock_item_id": stock_item.id,
                    "stock_item_name": stock_item.name,
                    "message": f"Low stock: needed {qty_needed}, available {current_qty}"
                })

            # Deduct stock (even if insufficient - will go negative)
            stock_item.current_quantity = current_qty - qty_needed

            # Create stock movement record
            movement = StockMovement(
                venue_id=venue_id,
                stock_item_id=stock_item.id,
                movement_type="order_deduction",
                quantity=-qty_needed,
                reference_type="order",
                reference_id=order_id,
                notes=f"Auto-deducted for order #{order_id}",
                created_at=datetime.now(timezone.utc)
            )
            self.db.add(movement)

            result["deductions"].append({
                "stock_item_id": stock_item.id,
                "stock_item_name": stock_item.name,
                "quantity_deducted": qty_needed,
                "remaining_quantity": current_qty - qty_needed
            })

        return result

    def reverse_order_stock(self, order_id: int) -> Dict[str, Any]:
        """
        Reverse stock deductions for a cancelled/voided order.
        """
        # Find all stock movements for this order
        movements = self.db.query(StockMovement).filter(
            StockMovement.reference_type == "order",
            StockMovement.reference_id == order_id,
            StockMovement.movement_type == "order_deduction"
        ).all()

        results = {
            "order_id": order_id,
            "items_reversed": 0,
            "reversals": []
        }

        # Batch-load all stock items referenced by movements
        stock_item_ids = [m.stock_item_id for m in movements]
        stock_items_list = self.db.query(StockItem).filter(
            StockItem.id.in_(stock_item_ids)
        ).all() if stock_item_ids else []
        stock_items_map = {si.id: si for si in stock_items_list}

        for movement in movements:
            stock_item = stock_items_map.get(movement.stock_item_id)

            if stock_item:
                # Add back the quantity (movement.quantity is negative)
                qty_to_add = abs(float(movement.quantity))
                stock_item.current_quantity = float(stock_item.current_quantity or 0) + qty_to_add

                # Create reversal movement
                reversal = StockMovement(
                    venue_id=movement.venue_id,
                    stock_item_id=movement.stock_item_id,
                    movement_type="order_reversal",
                    quantity=qty_to_add,
                    reference_type="order",
                    reference_id=order_id,
                    notes=f"Reversed for cancelled order #{order_id}",
                    created_at=datetime.now(timezone.utc)
                )
                self.db.add(reversal)

                results["items_reversed"] += 1
                results["reversals"].append({
                    "stock_item_id": stock_item.id,
                    "quantity_restored": qty_to_add
                })

        self.db.commit()

        results["success"] = True
        return results

    def check_stock_availability(
        self,
        menu_item_id: int,
        quantity: int,
        venue_id: int
    ) -> Dict[str, Any]:
        """
        Check if there's enough stock for a menu item without deducting.
        """
        result = {
            "available": True,
            "menu_item_id": menu_item_id,
            "requested_quantity": quantity,
            "missing_ingredients": []
        }

        recipe = self.db.query(Recipe).filter(
            Recipe.menu_item_id == menu_item_id,
            Recipe.is_active == True
        ).first()

        if not recipe:
            return result  # No recipe means unlimited availability

        ingredients = self.db.query(RecipeIngredient).filter(
            RecipeIngredient.recipe_id == recipe.id
        ).all()

        # Batch-load all stock items for this venue referenced by ingredients
        stock_item_ids = [ing.stock_item_id for ing in ingredients]
        stock_items_list = self.db.query(StockItem).filter(
            StockItem.id.in_(stock_item_ids),
            StockItem.venue_id == venue_id
        ).all() if stock_item_ids else []
        stock_items_map = {si.id: si for si in stock_items_list}

        for ingredient in ingredients:
            qty_needed = float(ingredient.quantity) * quantity

            stock_item = stock_items_map.get(ingredient.stock_item_id)

            if not stock_item or float(stock_item.current_quantity or 0) < qty_needed:
                result["available"] = False
                result["missing_ingredients"].append({
                    "stock_item_id": ingredient.stock_item_id,
                    "stock_item_name": stock_item.name if stock_item else "Unknown",
                    "needed": qty_needed,
                    "available": float(stock_item.current_quantity or 0) if stock_item else 0
                })

        return result

    def get_low_stock_items(self, venue_id: int) -> List[Dict[str, Any]]:
        """
        Get all stock items that are below their low stock threshold.
        """
        low_stock = self.db.query(StockItem).filter(
            StockItem.venue_id == venue_id,
            StockItem.quantity <= StockItem.low_stock_threshold
        ).all()

        return [
            {
                "id": item.id,
                "name": item.name,
                "current_quantity": float(item.quantity or 0),
                "reorder_point": float(item.low_stock_threshold or 0),
                "par_level": float(getattr(item, 'par_level', 0) or 0),
                "unit": item.unit,
                "category": getattr(item, 'category', None)
            }
            for item in low_stock
        ]


def get_inventory_sync_service(db: Session) -> OrderInventorySyncService:
    """Factory function to get inventory sync service"""
    return OrderInventorySyncService(db)

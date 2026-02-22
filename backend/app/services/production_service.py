"""
Production Module Service
Manages recipes, production orders, cost calculation, and batch production
Critical for kitchen/bar operations
"""

from typing import List, Dict, Optional
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
import logging

from app.models import (
    MenuItem, StockItem, Recipe, RecipeIngredient,
    ProductionOrder, ProductionBatch
)

logger = logging.getLogger(__name__)


class ProductionService:
    """Service for managing production, recipes, and cost calculation"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ==================== RECIPE MANAGEMENT ====================
    
    def create_recipe(
        self,
        menu_item_id: int,
        name: Dict,  # Multilingual
        ingredients: List[Dict],
        yield_quantity: Decimal,
        yield_unit: str,
        preparation_time: Optional[int] = None,
        difficulty: Optional[str] = None,
        instructions: Optional[Dict] = None
    ) -> Recipe:
        """
        Create a new recipe for a menu item
        
        Args:
            menu_item_id: Menu item this recipe produces
            name: Recipe name in multiple languages
            ingredients: List of ingredients with quantities
            yield_quantity: How much this recipe produces
            yield_unit: Unit of yield (portions, liters, etc.)
            preparation_time: Time in minutes
            difficulty: easy, medium, hard
            instructions: Step-by-step in multiple languages
        """
        # Verify menu item exists
        menu_item = self.db.query(MenuItem).filter(
            MenuItem.id == menu_item_id
        ).first()
        
        if not menu_item:
            raise ValueError(f"Menu item {menu_item_id} not found")
        
        # Create recipe
        recipe = Recipe(
            menu_item_id=menu_item_id,
            name=name,
            yield_quantity=yield_quantity,
            yield_unit=yield_unit,
            preparation_time=preparation_time,
            difficulty=difficulty or 'medium',
            instructions=instructions,
            version=1,
            active=True
        )
        
        self.db.add(recipe)
        self.db.flush()
        
        # Add ingredients
        for ing in ingredients:
            ingredient = RecipeIngredient(
                recipe_id=recipe.id,
                stock_item_id=ing['stock_item_id'],
                quantity=Decimal(str(ing['quantity'])),
                unit=ing['unit'],
                cost_per_unit=Decimal(str(ing.get('cost_per_unit', 0))),
                is_optional=ing.get('is_optional', False),
                substitutes=ing.get('substitutes')
            )
            self.db.add(ingredient)
        
        self.db.commit()
        self.db.refresh(recipe)
        
        logger.info(f"Created recipe {recipe.id} for item {menu_item_id}")
        
        return recipe
    
    def get_recipe(self, recipe_id: int) -> Optional[Recipe]:
        """Get recipe with all ingredients"""
        recipe = self.db.query(Recipe).filter(
            Recipe.id == recipe_id
        ).first()

        return recipe

    def get_recipes(
        self,
        menu_item_id: Optional[int] = None,
        active: Optional[bool] = True,
        difficulty: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Recipe]:
        """
        Get recipes with filters

        Args:
            menu_item_id: Filter by menu item
            active: Filter by active status
            difficulty: Filter by difficulty (easy, medium, hard)
            skip: Pagination offset
            limit: Maximum results
        """
        query = self.db.query(Recipe)

        if menu_item_id is not None:
            query = query.filter(Recipe.menu_item_id == menu_item_id)

        if active is not None:
            query = query.filter(Recipe.active == active)

        if difficulty:
            query = query.filter(Recipe.difficulty == difficulty)

        return query.offset(skip).limit(limit).all()

    def get_production_orders(
        self,
        venue_id: Optional[int] = None,
        status: Optional[str] = None,
        recipe_id: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[ProductionOrder]:
        """
        Get production orders with filters

        Args:
            venue_id: Filter by venue
            status: Filter by status (pending, in_progress, completed, cancelled)
            recipe_id: Filter by recipe
            date_from: Start date filter
            date_to: End date filter
            skip: Pagination offset
            limit: Maximum results
        """
        query = self.db.query(ProductionOrder)

        if venue_id is not None:
            query = query.filter(ProductionOrder.venue_id == venue_id)

        if status:
            query = query.filter(ProductionOrder.status == status)

        if recipe_id is not None:
            query = query.filter(ProductionOrder.recipe_id == recipe_id)

        if date_from:
            query = query.filter(ProductionOrder.created_at >= date_from)

        if date_to:
            query = query.filter(ProductionOrder.created_at <= date_to)

        return query.order_by(ProductionOrder.created_at.desc()).offset(skip).limit(limit).all()
    
    def calculate_recipe_cost(self, recipe_id: int) -> Dict:
        """
        Calculate total cost of a recipe based on current ingredient prices
        
        Returns cost breakdown and cost per portion/unit
        """
        recipe = self.get_recipe(recipe_id)
        if not recipe:
            raise ValueError(f"Recipe {recipe_id} not found")
        
        total_cost = Decimal('0')
        ingredients_cost = []

        # Support both 'ingredients' (RecipeIngredient backref) and 'lines' (RecipeLine) relationships
        ingredient_list = getattr(recipe, 'ingredients', None) or getattr(recipe, 'lines', None) or []

        for ingredient in ingredient_list:
            # Get current stock item cost - support both RecipeIngredient and RecipeLine
            stock_item = getattr(ingredient, 'stock_item', None)
            product = getattr(ingredient, 'product', None)

            # Calculate cost for this ingredient
            if stock_item:
                unit_cost = getattr(ingredient, 'cost_per_unit', None) or getattr(stock_item, 'unit_cost', None) or Decimal('0')
                item_qty = getattr(ingredient, 'quantity', None) or getattr(ingredient, 'qty', Decimal('0'))
                ingredient_total = Decimal(str(item_qty or 0)) * Decimal(str(unit_cost or 0))
                total_cost += ingredient_total

                ingredients_cost.append({
                    'stock_item_id': stock_item.id,
                    'name': stock_item.name,
                    'quantity': float(item_qty or 0),
                    'unit': ingredient.unit,
                    'unit_cost': float(unit_cost),
                    'total_cost': float(ingredient_total),
                    'is_optional': getattr(ingredient, 'is_optional', False)
                })
            elif product:
                unit_cost = getattr(product, 'cost_price', None) or Decimal('0')
                item_qty = getattr(ingredient, 'qty', None) or getattr(ingredient, 'quantity', Decimal('0'))
                ingredient_total = Decimal(str(item_qty or 0)) * Decimal(str(unit_cost or 0))
                total_cost += ingredient_total

                ingredients_cost.append({
                    'stock_item_id': product.id,
                    'name': product.name,
                    'quantity': float(item_qty or 0),
                    'unit': ingredient.unit,
                    'unit_cost': float(unit_cost),
                    'total_cost': float(ingredient_total),
                    'is_optional': getattr(ingredient, 'is_optional', False)
                })

        # Calculate cost per yield unit
        yield_qty = recipe.yield_quantity if recipe.yield_quantity and recipe.yield_quantity > 0 else Decimal('1')
        cost_per_unit = total_cost / yield_qty

        # Calculate recommended selling price (typical margin: 3x cost)
        recommended_price = cost_per_unit * Decimal('3')

        # Get current menu item selling price
        menu_item = recipe.menu_item
        current_price = menu_item.price if menu_item and menu_item.price is not None else Decimal('0')

        # Calculate profit margin
        if current_price and current_price > 0:
            profit = current_price - cost_per_unit
            margin_percent = (profit / current_price) * 100
        else:
            profit = Decimal('0')
            margin_percent = Decimal('0')
        
        return {
            'recipe_id': recipe.id,
            'recipe_name': recipe.name if isinstance(recipe.name, dict) else {"en": recipe.name} if recipe.name else {},
            'total_cost': float(total_cost),
            'yield_quantity': float(recipe.yield_quantity or 1),
            'yield_unit': recipe.yield_unit or "portion",
            'cost_per_unit': float(cost_per_unit),
            'ingredients': ingredients_cost,
            'pricing': {
                'current_selling_price': float(current_price),
                'recommended_price': float(recommended_price),
                'profit_per_unit': float(profit),
                'margin_percent': float(margin_percent)
            }
        }
    
    def update_recipe(
        self,
        recipe_id: int,
        updates: Dict
    ) -> Recipe:
        """Update existing recipe"""
        recipe = self.get_recipe(recipe_id)
        if not recipe:
            raise ValueError(f"Recipe {recipe_id} not found")
        
        # Update fields
        for key, value in updates.items():
            if hasattr(recipe, key):
                setattr(recipe, key, value)
        
        recipe.updated_at = datetime.now(timezone.utc)
        
        # If ingredients updated, create new version
        if 'ingredients' in updates:
            recipe.version += 1
            # Delete old ingredients
            for old_ing in recipe.ingredients:
                self.db.delete(old_ing)
            # Add new ingredients
            for ing in updates['ingredients']:
                ingredient = RecipeIngredient(
                    recipe_id=recipe.id,
                    stock_item_id=ing['stock_item_id'],
                    quantity=Decimal(str(ing['quantity'])),
                    unit=ing['unit'],
                    cost_per_unit=Decimal(str(ing.get('cost_per_unit', 0))),
                    is_optional=ing.get('is_optional', False)
                )
                self.db.add(ingredient)
        
        self.db.commit()
        self.db.refresh(recipe)
        
        return recipe
    
    # ==================== PRODUCTION ORDERS ====================
    
    def create_production_order(
        self,
        venue_id: int,
        recipe_id: int,
        quantity: int,
        scheduled_for: Optional[datetime] = None,
        notes: Optional[str] = None
    ) -> ProductionOrder:
        """
        Create a production order for a recipe
        
        Args:
            venue_id: Venue where production will occur
            recipe_id: Recipe to produce
            quantity: How many units/batches to produce
            scheduled_for: When to produce
            notes: Additional notes
        """
        recipe = self.get_recipe(recipe_id)
        if not recipe:
            raise ValueError(f"Recipe {recipe_id} not found")
        
        # Calculate expected cost
        cost_data = self.calculate_recipe_cost(recipe_id)
        expected_cost = Decimal(str(cost_data['cost_per_unit'])) * quantity
        
        production_order = ProductionOrder(
            venue_id=venue_id,
            recipe_id=recipe_id,
            quantity=quantity,
            status='pending',
            scheduled_for=scheduled_for or datetime.now(timezone.utc),
            actual_cost=expected_cost,
            notes=notes
        )
        
        self.db.add(production_order)
        self.db.commit()
        self.db.refresh(production_order)
        
        logger.info(f"Created production order {production_order.id}")
        
        return production_order
    
    def start_production(
        self,
        order_id: int,
        staff_id: int
    ) -> ProductionOrder:
        """Start a production order"""
        order = self.db.query(ProductionOrder).filter(
            ProductionOrder.id == order_id
        ).first()
        
        if not order:
            raise ValueError(f"Production order {order_id} not found")
        
        if order.status != 'pending':
            raise ValueError(f"Cannot start order with status {order.status}")
        
        # Check stock availability
        recipe = order.recipe
        for ingredient in recipe.ingredients:
            stock = ingredient.stock_item
            required = ingredient.quantity * order.quantity
            
            if stock.quantity < required:
                raise ValueError(
                    f"Insufficient stock for {stock.name}: "
                    f"need {required}, have {stock.quantity}"
                )
        
        # Start production
        order.status = 'in_progress'
        order.started_at = datetime.now(timezone.utc)
        order.produced_by = staff_id
        
        # Deduct ingredients from stock
        for ingredient in recipe.ingredients:
            stock = ingredient.stock_item
            used_quantity = ingredient.quantity * order.quantity
            stock.quantity -= used_quantity
            
            # Log stock movement
            # (Would create StockMovement record here)
        
        self.db.commit()
        self.db.refresh(order)
        
        return order
    
    def complete_production(
        self,
        order_id: int,
        actual_quantity_produced: int,
        actual_cost: Optional[Decimal] = None
    ) -> ProductionOrder:
        """Complete a production order and create batch"""
        order = self.db.query(ProductionOrder).filter(
            ProductionOrder.id == order_id
        ).first()
        
        if not order:
            raise ValueError(f"Production order {order_id} not found")
        
        if order.status != 'in_progress':
            raise ValueError(f"Cannot complete order with status {order.status}")
        
        # Complete order
        order.status = 'completed'
        order.completed_at = datetime.now(timezone.utc)
        
        if actual_cost:
            order.actual_cost = actual_cost
        
        # Create production batch
        batch_code = self._generate_batch_code(order)
        
        batch = ProductionBatch(
            production_order_id=order.id,
            batch_code=batch_code,
            menu_item_id=order.recipe.menu_item_id,
            quantity_produced=actual_quantity_produced,
            production_date=datetime.now(timezone.utc).date(),
            expiry_date=self._calculate_expiry_date(order.recipe),
            status='active'
        )
        
        self.db.add(batch)
        
        # Add produced items to stock
        menu_item = order.recipe.menu_item
        if menu_item.stock_item_id:
            stock = self.db.query(StockItem).filter(
                StockItem.id == menu_item.stock_item_id
            ).first()
            if stock:
                stock.quantity += actual_quantity_produced
        
        self.db.commit()
        self.db.refresh(order)
        
        logger.info(
            f"Completed production order {order_id}, "
            f"created batch {batch_code}"
        )
        
        return order
    
    def _generate_batch_code(self, order: ProductionOrder) -> str:
        """Generate unique batch code"""
        date_part = datetime.now(timezone.utc).strftime('%Y%m%d')
        recipe_id = str(order.recipe_id).zfill(4)
        order_id = str(order.id).zfill(4)
        return f"BATCH-{date_part}-{recipe_id}-{order_id}"
    
    def _calculate_expiry_date(self, recipe: Recipe) -> Optional[datetime.date]:
        """Calculate expiry date based on recipe type"""
        # This would be more sophisticated in production
        # For now, default to 7 days for prepared food
        return (datetime.now(timezone.utc) + timedelta(days=7)).date()
    
    # ==================== BATCH MANAGEMENT ====================
    
    def get_batches(
        self,
        venue_id: Optional[int] = None,
        status: Optional[str] = None,
        expiring_days: Optional[int] = None
    ) -> List[ProductionBatch]:
        """Get production batches with filters"""
        query = self.db.query(ProductionBatch)

        if venue_id:
            query = query.filter(ProductionBatch.venue_id == venue_id)
        
        if status:
            query = query.filter(ProductionBatch.status == status)
        
        if expiring_days:
            expiry_threshold = datetime.now(timezone.utc) + timedelta(days=expiring_days)
            query = query.filter(
                ProductionBatch.use_by_date <= expiry_threshold,
                ProductionBatch.status == 'completed'
            )
        
        return query.all()
    
    def consume_batch(
        self,
        batch_id: int,
        quantity_consumed: int
    ):
        """Mark batch quantity as consumed"""
        batch = self.db.query(ProductionBatch).filter(
            ProductionBatch.id == batch_id
        ).first()
        
        if not batch:
            raise ValueError(f"Batch {batch_id} not found")
        
        batch.quantity_produced -= quantity_consumed
        
        if batch.quantity_produced <= 0:
            batch.status = 'consumed'
        
        self.db.commit()
    
    def expire_old_batches(self):
        """Automatically expire batches past expiry date"""
        today = datetime.now(timezone.utc).date()
        
        expired = self.db.query(ProductionBatch).filter(
            ProductionBatch.expiry_date < today,
            ProductionBatch.status == 'active'
        ).all()
        
        for batch in expired:
            batch.status = 'expired'
            logger.warning(
                f"Batch {batch.batch_code} expired on {batch.expiry_date}"
            )
        
        self.db.commit()
        
        return len(expired)
    
    # ==================== REPORTING ====================
    
    def get_production_report(
        self,
        venue_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """Get production statistics for a period"""
        
        orders = self.db.query(ProductionOrder).filter(
            ProductionOrder.venue_id == venue_id,
            ProductionOrder.created_at >= start_date,
            ProductionOrder.created_at <= end_date
        ).all()
        
        total_orders = len(orders)
        completed = [o for o in orders if o.status == 'completed']
        in_progress = [o for o in orders if o.status == 'in_progress']
        
        total_cost = sum(
            o.actual_cost or Decimal('0') for o in completed
        )
        
        return {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'total_orders': total_orders,
            'completed': len(completed),
            'in_progress': len(in_progress),
            'total_cost': float(total_cost),
            'avg_cost_per_order': float(
                total_cost / len(completed) if completed else 0
            )
        }

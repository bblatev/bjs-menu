"""
Production Module API Endpoints
Recipe management, production orders, cost calculation, batch tracking
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from datetime import datetime, date
from decimal import Decimal

from app.db.session import get_db
from app.services.production_service import ProductionService
from pydantic import BaseModel, Field



router = APIRouter()


# ==================== SCHEMAS ====================

class IngredientInput(BaseModel):
    """Recipe ingredient input"""
    stock_item_id: int
    quantity: float = Field(..., gt=0)
    unit: str = Field(..., min_length=1, max_length=20)
    cost_per_unit: Optional[float] = None
    is_optional: bool = False
    substitutes: Optional[Dict] = None


class RecipeCreate(BaseModel):
    """Create recipe"""
    menu_item_id: int
    name: Dict = Field(..., description="Multilingual name")
    ingredients: List[IngredientInput] = Field(..., min_length=1)
    yield_quantity: float = Field(..., gt=0)
    yield_unit: str = Field(..., min_length=1)
    preparation_time: Optional[int] = Field(None, description="Minutes")
    difficulty: Optional[str] = Field("medium", pattern="^(easy|medium|hard)$")
    instructions: Optional[Dict] = None


class RecipeResponse(BaseModel):
    """Recipe details"""
    id: int
    menu_item_id: int
    menu_item_name: Dict
    name: Dict
    version: int
    yield_quantity: float
    yield_unit: str
    preparation_time: Optional[int]
    difficulty: str
    instructions: Optional[Dict]
    active: bool
    ingredient_count: int
    created_at: datetime


class RecipeCostResponse(BaseModel):
    """Recipe cost breakdown"""
    recipe_id: int
    recipe_name: Dict
    total_cost: float
    yield_quantity: float
    yield_unit: str
    cost_per_unit: float
    ingredients: List[Dict]
    pricing: Dict


class ProductionOrderCreate(BaseModel):
    """Create production order"""
    venue_id: int
    recipe_id: int
    quantity: int = Field(..., gt=0)
    scheduled_for: Optional[datetime] = None
    notes: Optional[str] = None


class ProductionOrderResponse(BaseModel):
    """Production order details"""
    id: int
    venue_id: int
    recipe_id: int
    recipe_name: Dict
    quantity: int
    status: str
    scheduled_for: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    produced_by: Optional[int]
    producer_name: Optional[str]
    batch_number: Optional[str]
    actual_cost: Optional[float]
    notes: Optional[str]
    created_at: datetime


class ProductionBatchResponse(BaseModel):
    """Production batch details"""
    id: int
    production_order_id: int
    batch_code: str
    menu_item_id: int
    menu_item_name: Dict
    quantity_produced: int
    production_date: date
    expiry_date: Optional[date]
    days_until_expiry: Optional[int]
    status: str
    created_at: datetime


# ==================== RECIPE ENDPOINTS ====================

@router.post(
    "/recipes",
    response_model=RecipeResponse,
    summary="Create recipe",
    description="Create new recipe with ingredients and instructions"
)
def create_recipe(
    data: RecipeCreate,
    db: Session = Depends(get_db)
):
    """
    Create new recipe
    
    Use for:
    - Cocktails (mojito, margarita, etc.)
    - Hot drinks (hot chocolate, coffee drinks)
    - Food items (burgers, sandwiches, etc.)
    - Prepared dishes
    
    Example - Hot Chocolate Recipe:
    ```json
    {
      "menu_item_id": 5,
      "name": {
        "en": "Hot Chocolate",
        "bg": "Топло какао",
        "de": "Heiße Schokolade",
        "ru": "Горячий шоколад"
      },
      "ingredients": [
        {
          "stock_item_id": 10,
          "quantity": 0.02,
          "unit": "kg",
          "cost_per_unit": 15.00
        },
        {
          "stock_item_id": 11,
          "quantity": 0.25,
          "unit": "L",
          "cost_per_unit": 2.00
        }
      ],
      "yield_quantity": 1,
      "yield_unit": "portion",
      "preparation_time": 5,
      "difficulty": "easy"
    }
    ```
    """
    service = ProductionService(db)
    
    try:
        recipe = service.create_recipe(
            menu_item_id=data.menu_item_id,
            name=data.name,
            ingredients=[ing.dict() for ing in data.ingredients],
            yield_quantity=Decimal(str(data.yield_quantity)),
            yield_unit=data.yield_unit,
            preparation_time=data.preparation_time,
            difficulty=data.difficulty,
            instructions=data.instructions
        )
        
        return {
            "id": recipe.id,
            "menu_item_id": recipe.menu_item_id,
            "menu_item_name": recipe.menu_item.name if recipe.menu_item else {},
            "name": recipe.name,
            "version": recipe.version,
            "yield_quantity": float(recipe.yield_quantity),
            "yield_unit": recipe.yield_unit,
            "preparation_time": recipe.preparation_time,
            "difficulty": recipe.difficulty,
            "instructions": recipe.instructions,
            "active": recipe.active,
            "ingredient_count": len(recipe.ingredients),
            "created_at": recipe.created_at
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/recipes/{recipe_id}",
    response_model=RecipeResponse,
    summary="Get recipe",
    description="Get recipe details with all ingredients"
)
def get_recipe(
    recipe_id: int,
    db: Session = Depends(get_db)
):
    """Get recipe details"""
    service = ProductionService(db)
    recipe = service.get_recipe(recipe_id)
    
    if not recipe:
        raise HTTPException(status_code=404, detail=f"Recipe {recipe_id} not found")
    
    return {
        "id": recipe.id,
        "menu_item_id": recipe.menu_item_id,
        "menu_item_name": recipe.menu_item.name if recipe.menu_item else {},
        "name": recipe.name,
        "version": recipe.version,
        "yield_quantity": float(recipe.yield_quantity),
        "yield_unit": recipe.yield_unit,
        "preparation_time": recipe.preparation_time,
        "difficulty": recipe.difficulty,
        "instructions": recipe.instructions,
        "active": recipe.active,
        "ingredient_count": len(recipe.ingredients),
        "created_at": recipe.created_at
    }


@router.get(
    "/recipes",
    response_model=List[RecipeResponse],
    summary="List recipes",
    description="List all recipes with optional filters"
)
def list_recipes(
    menu_item_id: Optional[int] = None,
    active: Optional[bool] = True,
    difficulty: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List recipes with filters

    Filters:
    - menu_item_id: Recipes for specific menu item
    - active: Only active recipes (default: true)
    - difficulty: Filter by difficulty (easy, medium, hard)
    """
    service = ProductionService(db)
    recipes = service.get_recipes(
        menu_item_id=menu_item_id,
        active=active,
        difficulty=difficulty,
        skip=skip,
        limit=limit
    )

    result = []
    for recipe in recipes:
        result.append({
            "id": recipe.id,
            "menu_item_id": recipe.menu_item_id,
            "menu_item_name": recipe.menu_item.name if recipe.menu_item else {},
            "name": recipe.name,
            "version": recipe.version,
            "yield_quantity": float(recipe.yield_quantity),
            "yield_unit": recipe.yield_unit,
            "preparation_time": recipe.preparation_time,
            "difficulty": recipe.difficulty,
            "instructions": recipe.instructions,
            "active": recipe.active,
            "ingredient_count": len(recipe.ingredients) if recipe.ingredients else 0,
            "created_at": recipe.created_at
        })

    return result


@router.get(
    "/recipes/{recipe_id}/cost",
    response_model=RecipeCostResponse,
    summary="Calculate recipe cost",
    description="Get detailed cost breakdown and pricing analysis"
)
def calculate_recipe_cost(
    recipe_id: int,
    db: Session = Depends(get_db)
):
    """
    Calculate recipe cost
    
    Returns:
    - Total ingredient cost
    - Cost per portion/unit
    - Ingredient breakdown
    - Recommended selling price (3x cost)
    - Current profit margin
    - Pricing analysis
    
    Example response:
    ```json
    {
      "total_cost": 0.80,
      "cost_per_unit": 0.80,
      "ingredients": [
        {
          "name": "Cocoa powder",
          "quantity": 0.02,
          "unit": "kg",
          "unit_cost": 15.00,
          "total_cost": 0.30
        },
        {
          "name": "Milk",
          "quantity": 0.25,
          "unit": "L",
          "unit_cost": 2.00,
          "total_cost": 0.50
        }
      ],
      "pricing": {
        "current_selling_price": 3.50,
        "recommended_price": 2.40,
        "profit_per_unit": 2.70,
        "margin_percent": 77.14
      }
    }
    ```
    """
    service = ProductionService(db)
    
    try:
        cost_data = service.calculate_recipe_cost(recipe_id)
        return cost_data
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put(
    "/recipes/{recipe_id}",
    response_model=RecipeResponse,
    summary="Update recipe",
    description="Update recipe (creates new version if ingredients changed)"
)
def update_recipe(
    recipe_id: int,
    updates: Dict,
    db: Session = Depends(get_db)
):
    """
    Update recipe
    
    If ingredients are changed, creates a new version.
    Version history is maintained for cost tracking.
    """
    service = ProductionService(db)
    
    try:
        recipe = service.update_recipe(recipe_id, updates)
        
        return {
            "id": recipe.id,
            "menu_item_id": recipe.menu_item_id,
            "menu_item_name": recipe.menu_item.name if recipe.menu_item else {},
            "name": recipe.name,
            "version": recipe.version,
            "yield_quantity": float(recipe.yield_quantity),
            "yield_unit": recipe.yield_unit,
            "preparation_time": recipe.preparation_time,
            "difficulty": recipe.difficulty,
            "instructions": recipe.instructions,
            "active": recipe.active,
            "ingredient_count": len(recipe.ingredients),
            "created_at": recipe.created_at
        }
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==================== PRODUCTION ORDER ENDPOINTS ====================

@router.post(
    "/production",
    response_model=ProductionOrderResponse,
    summary="Create production order",
    description="Schedule production of a recipe"
)
def create_production_order(
    data: ProductionOrderCreate,
    db: Session = Depends(get_db)
):
    """
    Create production order
    
    Use for:
    - Batch production (prep 50 burgers)
    - Scheduled production (tomorrow morning)
    - Pre-production (cocktail mix in advance)
    
    Workflow:
    1. Create order (pending)
    2. Start production (deducts stock)
    3. Complete production (creates batch)
    """
    service = ProductionService(db)
    
    try:
        order = service.create_production_order(
            venue_id=data.venue_id,
            recipe_id=data.recipe_id,
            quantity=data.quantity,
            scheduled_for=data.scheduled_for,
            notes=data.notes
        )
        
        return {
            "id": order.id,
            "venue_id": order.venue_id,
            "recipe_id": order.recipe_id,
            "recipe_name": order.recipe.name if order.recipe else {},
            "quantity": order.quantity,
            "status": order.status,
            "scheduled_for": order.scheduled_for,
            "started_at": order.started_at,
            "completed_at": order.completed_at,
            "produced_by": order.produced_by,
            "producer_name": order.producer.full_name if order.producer else None,
            "batch_number": order.batch_number,
            "actual_cost": float(order.actual_cost) if order.actual_cost else None,
            "notes": order.notes,
            "created_at": order.created_at
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/production/{order_id}/start",
    response_model=ProductionOrderResponse,
    summary="Start production",
    description="Start production order (deducts ingredients from stock)"
)
def start_production(
    order_id: int,
    staff_id: int = Query(..., description="Staff member starting production"),
    db: Session = Depends(get_db)
):
    """
    Start production order
    
    Actions:
    1. Validates stock availability
    2. Deducts ingredients from inventory
    3. Sets status to 'in_progress'
    4. Records who started production
    
    Throws error if insufficient stock
    """
    service = ProductionService(db)
    
    try:
        order = service.start_production(
            order_id=order_id,
            staff_id=staff_id
        )
        
        return {
            "id": order.id,
            "venue_id": order.venue_id,
            "recipe_id": order.recipe_id,
            "recipe_name": order.recipe.name if order.recipe else {},
            "quantity": order.quantity,
            "status": order.status,
            "scheduled_for": order.scheduled_for,
            "started_at": order.started_at,
            "completed_at": order.completed_at,
            "produced_by": order.produced_by,
            "producer_name": order.producer.full_name if order.producer else None,
            "batch_number": order.batch_number,
            "actual_cost": float(order.actual_cost) if order.actual_cost else None,
            "notes": order.notes,
            "created_at": order.created_at
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/production/{order_id}/complete",
    response_model=ProductionOrderResponse,
    summary="Complete production",
    description="Complete production and create batch"
)
def complete_production(
    order_id: int,
    actual_quantity: int = Query(..., gt=0, description="Actual quantity produced"),
    actual_cost: Optional[float] = Query(None, description="Actual cost if different"),
    db: Session = Depends(get_db)
):
    """
    Complete production order
    
    Actions:
    1. Sets status to 'completed'
    2. Creates production batch
    3. Adds produced items to stock
    4. Records actual cost/quantity
    
    Batch code is auto-generated for tracking
    """
    service = ProductionService(db)
    
    try:
        order = service.complete_production(
            order_id=order_id,
            actual_quantity_produced=actual_quantity,
            actual_cost=Decimal(str(actual_cost)) if actual_cost else None
        )
        
        return {
            "id": order.id,
            "venue_id": order.venue_id,
            "recipe_id": order.recipe_id,
            "recipe_name": order.recipe.name if order.recipe else {},
            "quantity": order.quantity,
            "status": order.status,
            "scheduled_for": order.scheduled_for,
            "started_at": order.started_at,
            "completed_at": order.completed_at,
            "produced_by": order.produced_by,
            "producer_name": order.producer.full_name if order.producer else None,
            "batch_number": order.batch_number,
            "actual_cost": float(order.actual_cost) if order.actual_cost else None,
            "notes": order.notes,
            "created_at": order.created_at
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/production",
    response_model=List[ProductionOrderResponse],
    summary="List production orders",
    description="List production orders with filters"
)
def list_production_orders(
    venue_id: Optional[int] = None,
    status: Optional[str] = None,
    recipe_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List production orders

    Filters:
    - venue_id: Orders for specific venue
    - status: pending, in_progress, completed, cancelled
    - recipe_id: Orders for specific recipe
    - date_from/to: Date range
    """
    service = ProductionService(db)
    orders = service.get_production_orders(
        venue_id=venue_id,
        status=status,
        recipe_id=recipe_id,
        date_from=datetime.combine(date_from, datetime.min.time()) if date_from else None,
        date_to=datetime.combine(date_to, datetime.max.time()) if date_to else None,
        skip=skip,
        limit=limit
    )

    result = []
    for order in orders:
        result.append({
            "id": order.id,
            "venue_id": order.venue_id,
            "recipe_id": order.recipe_id,
            "recipe_name": order.recipe.name if order.recipe else {},
            "quantity": order.quantity,
            "status": order.status,
            "scheduled_for": order.scheduled_for,
            "started_at": order.started_at,
            "completed_at": order.completed_at,
            "produced_by": order.produced_by,
            "producer_name": order.producer.full_name if order.producer else None,
            "batch_number": order.batch_number,
            "actual_cost": float(order.actual_cost) if order.actual_cost else None,
            "notes": order.notes,
            "created_at": order.created_at
        })

    return result


# ==================== BATCH ENDPOINTS ====================

@router.get(
    "/production/batches",
    response_model=List[ProductionBatchResponse],
    summary="List production batches",
    description="List production batches with filters"
)
def list_production_batches(
    venue_id: Optional[int] = None,
    status: Optional[str] = None,
    expiring_days: Optional[int] = Query(None, description="Get batches expiring within N days"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List production batches
    
    Filters:
    - venue_id: Batches for specific venue
    - status: active, consumed, expired, discarded
    - expiring_days: Batches expiring soon
    
    Use for:
    - Checking what's ready to use
    - Finding batches near expiry
    - Production tracking
    """
    service = ProductionService(db)
    
    batches = service.get_batches(
        venue_id=venue_id,
        status=status,
        expiring_days=expiring_days
    )
    
    result = []
    for batch in batches:
        days_until_expiry = None
        if batch.expiry_date:
            days_until_expiry = (batch.expiry_date - date.today()).days
        
        result.append({
            "id": batch.id,
            "production_order_id": batch.production_order_id,
            "batch_code": batch.batch_code,
            "menu_item_id": batch.menu_item_id,
            "menu_item_name": batch.menu_item.name if batch.menu_item else {},
            "quantity_produced": batch.quantity_produced,
            "production_date": batch.production_date,
            "expiry_date": batch.expiry_date,
            "days_until_expiry": days_until_expiry,
            "status": batch.status,
            "created_at": batch.created_at
        })
    
    return result


# ==================== REPORTING ====================

@router.get(
    "/production/report",
    summary="Get production report",
    description="Get production statistics for a period"
)
def get_production_report(
    venue_id: int,
    start_date: date = Query(..., description="Report start date"),
    end_date: date = Query(..., description="Report end date"),
    db: Session = Depends(get_db)
):
    """
    Get production report
    
    Returns:
    - Total orders created
    - Orders completed
    - Orders in progress
    - Total production cost
    - Average cost per order
    - Cost efficiency metrics
    
    Use for:
    - Monthly production review
    - Cost analysis
    - Efficiency tracking
    """
    service = ProductionService(db)
    
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    
    report = service.get_production_report(
        venue_id=venue_id,
        start_date=start_datetime,
        end_date=end_datetime
    )
    
    return report

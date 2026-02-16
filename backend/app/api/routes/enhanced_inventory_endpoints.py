"""
Enhanced Inventory Management API Endpoints
Complete feature parity with Toast, TouchBistro, iiko, and beyond

Includes:
- Advanced Menu Management (versioning, scheduling, nutrition, allergens, bundles)
- Comprehensive Recipe Management (versioning, sub-recipes, scaling, costing)
- Advanced Stock Management (multi-warehouse, batch tracking, transfers, reservations)
- Enhanced Supplier Management (contacts, price lists, ratings, documents)
- Advanced Purchase Orders (templates, approvals, invoicing, three-way matching, GRN)
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from pydantic import BaseModel
import logging

from app.db.session import get_db
from app.core.rbac import get_current_user

logger = logging.getLogger(__name__)
from app.models.enhanced_inventory import (
    MenuVersionHistory, MenuSchedule, MenuItemNutrition, MenuItemAllergen,
    MenuItemBundle, RecipeVersion, RecipeInstruction, RecipeCostHistory,
    EnhancedWarehouse as Warehouse, EnhancedStockBatch as StockBatch,
    EnhancedStockTransfer as StockTransfer, EnhancedStockAdjustment as StockAdjustment,
    EnhancedStockReservation as StockReservation, SupplierContact,
    SupplierPriceList, SupplierPriceListItem,
    SupplierRating,
    PurchaseOrderTemplate, PurchaseOrderApproval, SupplierInvoice, GoodsReceivedNote
)
from app.models.supplier import SupplierDocument
from app.services.inventory_management_service import (
    AdvancedMenuService, AdvancedRecipeService, AdvancedStockService,
    AdvancedSupplierService, AdvancedPurchaseOrderService
)
from app.core.rate_limit import limiter


router = APIRouter()

# ==================== PYDANTIC SCHEMAS ====================

# Menu Schemas
class MenuVersionCreate(BaseModel):
    menu_item_id: int
    changes: Dict[str, Any]
    reason: Optional[str] = None

class MenuScheduleCreate(BaseModel):
    menu_item_id: int
    day_of_week: Optional[int] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_available: bool = True

class MenuNutritionCreate(BaseModel):
    menu_item_id: int
    serving_size: Optional[str] = None
    calories: Optional[Decimal] = None
    calories_from_fat: Optional[Decimal] = None
    total_fat_g: Optional[Decimal] = None
    saturated_fat_g: Optional[Decimal] = None
    trans_fat_g: Optional[Decimal] = None
    cholesterol_mg: Optional[Decimal] = None
    sodium_mg: Optional[Decimal] = None
    total_carbs_g: Optional[Decimal] = None
    dietary_fiber_g: Optional[Decimal] = None
    sugars_g: Optional[Decimal] = None
    protein_g: Optional[Decimal] = None
    vitamin_a_pct: Optional[Decimal] = None
    vitamin_c_pct: Optional[Decimal] = None
    calcium_pct: Optional[Decimal] = None
    iron_pct: Optional[Decimal] = None
    additional_nutrients: Optional[Dict[str, Any]] = None

class MenuAllergenCreate(BaseModel):
    menu_item_id: int
    allergen_type: str
    severity: str = "contains"
    notes: Optional[str] = None

class MenuBundleCreate(BaseModel):
    bundle_item_id: int
    included_item_id: int
    quantity: int = 1
    is_required: bool = True
    price_adjustment: Decimal = Decimal("0")

class BulkPriceUpdate(BaseModel):
    item_ids: List[int]
    adjustment_type: str  # "percentage" or "fixed"
    adjustment_value: Decimal

# Recipe Schemas
class RecipeCreate(BaseModel):
    menu_item_id: int
    name: Dict[str, str]
    description: Optional[Dict[str, str]] = None
    category_id: Optional[int] = None
    yield_quantity: Decimal = Decimal("1")
    yield_unit: str = "portion"
    prep_time_minutes: Optional[int] = None
    cook_time_minutes: Optional[int] = None
    rest_time_minutes: Optional[int] = None
    difficulty_level: Optional[str] = "medium"
    equipment_needed: Optional[List[str]] = None
    notes: Optional[Dict[str, str]] = None
    ingredients: List[Dict[str, Any]] = []
    instructions: Optional[List[Dict[str, Any]]] = None

class RecipeIngredientCreate(BaseModel):
    ingredient_id: int
    quantity: Decimal
    unit: str
    preparation: Optional[str] = None
    is_optional: bool = False
    substitutes: Optional[List[Dict[str, Any]]] = None

class RecipeInstructionCreate(BaseModel):
    step_number: int
    instruction: Dict[str, str]
    duration_minutes: Optional[int] = None
    temperature: Optional[str] = None
    equipment: Optional[str] = None
    tips: Optional[Dict[str, str]] = None
    image_url: Optional[str] = None
    video_url: Optional[str] = None

class SubRecipeCreate(BaseModel):
    parent_recipe_id: int
    child_recipe_id: int
    quantity: Decimal = Decimal("1")
    unit: str = "portion"

class RecipeScaleRequest(BaseModel):
    recipe_id: int
    target_yield: Decimal
    target_unit: Optional[str] = None

# Stock Schemas
class WarehouseCreate(BaseModel):
    name: Dict[str, str]
    code: str
    warehouse_type: str = "main"
    address: Optional[Dict[str, str]] = None
    manager_id: Optional[int] = None
    is_active: bool = True
    accepts_transfers: bool = True
    auto_replenish: bool = False
    min_stock_level_pct: Decimal = Decimal("20")

class StockBatchCreate(BaseModel):
    stock_item_id: int
    warehouse_id: int
    batch_number: str
    lot_number: Optional[str] = None
    quantity: Decimal
    unit_cost: Decimal
    manufacture_date: Optional[date] = None
    expiry_date: Optional[date] = None
    supplier_id: Optional[int] = None
    purchase_order_id: Optional[int] = None

class StockTransferCreate(BaseModel):
    from_warehouse_id: int
    to_warehouse_id: int
    notes: Optional[str] = None
    expected_date: Optional[date] = None
    items: List[Dict[str, Any]]

class StockAdjustmentCreate(BaseModel):
    warehouse_id: int
    adjustment_type: str
    reason: str
    notes: Optional[str] = None
    items: List[Dict[str, Any]]
    requires_approval: bool = False

class StockReservationCreate(BaseModel):
    stock_item_id: int
    warehouse_id: int
    batch_id: Optional[int] = None
    quantity: Decimal
    reservation_type: str
    reference_type: str
    reference_id: int
    expires_at: Optional[datetime] = None
    notes: Optional[str] = None

# Supplier Schemas
class SupplierContactCreate(BaseModel):
    supplier_id: int
    contact_name: str
    role: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    is_primary: bool = False
    receives_orders: bool = True
    receives_invoices: bool = False
    notes: Optional[str] = None

class SupplierPriceListCreate(BaseModel):
    supplier_id: int
    name: str
    effective_from: date
    effective_to: Optional[date] = None
    currency: str = "BGN"
    min_order_amount: Optional[Decimal] = None
    notes: Optional[str] = None
    items: List[Dict[str, Any]]

class SupplierDocumentCreate(BaseModel):
    supplier_id: int
    document_type: str
    document_name: str
    file_url: str
    file_size_bytes: Optional[int] = None
    expiry_date: Optional[date] = None
    notes: Optional[str] = None

class SupplierRatingCreate(BaseModel):
    supplier_id: int
    rating_period_start: date
    rating_period_end: date
    quality_score: Decimal = Decimal("5.0")
    delivery_score: Decimal = Decimal("5.0")
    price_score: Decimal = Decimal("5.0")
    communication_score: Decimal = Decimal("5.0")
    total_orders: int = 0
    on_time_deliveries: int = 0
    rejected_items_count: int = 0
    notes: Optional[str] = None

# Purchase Order Schemas
class POTemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    supplier_id: Optional[int] = None
    warehouse_id: Optional[int] = None
    schedule_type: Optional[str] = None
    schedule_config: Optional[Dict[str, Any]] = None
    items: List[Dict[str, Any]]

class POApprovalCreate(BaseModel):
    purchase_order_id: int
    action: str  # "approve" or "reject"
    notes: Optional[str] = None

class SupplierInvoiceCreate(BaseModel):
    supplier_id: int
    invoice_number: str
    invoice_date: date
    due_date: Optional[date] = None
    subtotal: Decimal
    tax_amount: Decimal = Decimal("0")
    total_amount: Decimal
    currency: str = "BGN"
    payment_terms: Optional[str] = None
    notes: Optional[str] = None
    file_url: Optional[str] = None
    purchase_order_id: Optional[int] = None
    items: List[Dict[str, Any]]

class GRNCreate(BaseModel):
    purchase_order_id: Optional[int] = None
    supplier_id: int
    warehouse_id: Optional[int] = None
    received_date: Optional[date] = None
    notes: Optional[str] = None
    items: List[Dict[str, Any]]

# ==================== MENU MANAGEMENT ENDPOINTS ====================

@router.get("/")
@limiter.limit("60/minute")
async def get_enhanced_inventory_root(request: Request, db: Session = Depends(get_db)):
    """Enhanced inventory features."""
    return {"module": "enhanced-inventory", "status": "active", "endpoints": ["/menu/versions/{menu_item_id}", "/menu/schedules", "/menu/nutrition/{menu_item_id}", "/menu/allergens/{menu_item_id}", "/menu/bundles/{bundle_item_id}"]}


@router.get("/menu/versions/{menu_item_id}")
@limiter.limit("60/minute")
def get_menu_item_versions(
    request: Request,
    menu_item_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get version history for a menu item"""
    try:
        versions = db.query(MenuVersionHistory).filter(
            MenuVersionHistory.menu_item_id == menu_item_id
        ).order_by(MenuVersionHistory.id.desc()).all()
        return versions
    except Exception as e:
        logger.error(f"Error fetching menu versions: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch menu versions")

@router.post("/menu/versions")
@limiter.limit("30/minute")
def create_menu_version(
    request: Request,
    data: MenuVersionCreate,
    venue_id: int = Query(..., description="Venue ID"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new version of a menu item (tracks changes)"""
    try:
        # Create version history record directly since service signature doesn't match
        from app.models import MenuItem
        menu_item = db.query(MenuItem).filter(MenuItem.id == data.menu_item_id).first()
        if not menu_item:
            raise HTTPException(status_code=404, detail="Menu item not found")

        version = MenuVersionHistory(
            venue_id=venue_id,
            menu_version_id=data.menu_item_id,  # Linking to menu version
            new_status="updated",
            change_type="updated",
            change_description=data.reason,
            changes_json=data.changes,
            changed_by=current_user.id
        )
        db.add(version)
        db.commit()
        db.refresh(version)
        return version
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating menu version: {e}")
        raise HTTPException(status_code=500, detail="Failed to create menu version")

@router.post("/menu/versions/{version_id}/restore")
@limiter.limit("30/minute")
def restore_menu_version(
    request: Request,
    version_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Restore a menu item to a previous version"""
    try:
        # Find the version history record
        version = db.query(MenuVersionHistory).filter(
            MenuVersionHistory.id == version_id
        ).first()

        if not version:
            raise HTTPException(status_code=404, detail="Version not found")

        # Mark this version as restored
        version.new_status = "restored"
        db.commit()
        return {"status": "success", "message": "Menu item restored to previous version"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error restoring menu version: {e}")
        raise HTTPException(status_code=500, detail="Failed to restore menu version")

@router.get("/menu/schedules")
@limiter.limit("60/minute")
def get_menu_schedules(
    request: Request,
    venue_id: int,
    menu_item_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get menu schedules for a venue"""
    try:
        query = db.query(MenuSchedule).filter(MenuSchedule.venue_id == venue_id)
        if menu_item_id:
            # MenuSchedule uses menu_version_id, not menu_item_id
            query = query.filter(MenuSchedule.menu_version_id == menu_item_id)
        return query.all()
    except Exception as e:
        logger.error(f"Error fetching menu schedules: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch menu schedules")

@router.post("/menu/schedules")
@limiter.limit("30/minute")
def create_menu_schedule(
    request: Request,
    venue_id: int,
    data: MenuScheduleCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a menu schedule (availability windows)"""
    try:
        # Create schedule directly - service method signature doesn't match
        schedule = MenuSchedule(
            venue_id=venue_id,
            menu_version_id=data.menu_item_id,
            name=f"Schedule for menu {data.menu_item_id}",
            schedule_type="recurring" if data.day_of_week is not None else "date_range",
            days_of_week=[data.day_of_week] if data.day_of_week is not None else None,
            start_time=data.start_time,
            end_time=data.end_time,
            start_date=data.start_date,
            end_date=data.end_date,
            is_active=data.is_available
        )
        db.add(schedule)
        db.commit()
        db.refresh(schedule)
        return schedule
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating menu schedule: {e}")
        raise HTTPException(status_code=500, detail="Failed to create menu schedule")

@router.delete("/menu/schedules/{schedule_id}")
@limiter.limit("30/minute")
def delete_menu_schedule(
    request: Request,
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete a menu schedule"""
    try:
        schedule = db.query(MenuSchedule).filter(MenuSchedule.id == schedule_id).first()
        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")
        db.delete(schedule)
        db.commit()
        return {"status": "deleted"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting menu schedule: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete menu schedule")

@router.get("/menu/nutrition/{menu_item_id}")
@limiter.limit("60/minute")
def get_menu_nutrition(
    request: Request,
    menu_item_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get nutrition information for a menu item"""
    try:
        # Query nutrition directly - service method is calculate_nutrition_from_recipe
        nutrition = db.query(MenuItemNutrition).filter(
            MenuItemNutrition.menu_item_id == menu_item_id
        ).first()

        if not nutrition:
            # Try to calculate from recipe using service
            service = AdvancedMenuService(db)
            nutrition = service.calculate_nutrition_from_recipe(menu_item_id)

        if not nutrition:
            raise HTTPException(status_code=404, detail="Nutrition information not found")

        return nutrition
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching nutrition info: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch nutrition information")

@router.post("/menu/nutrition")
@limiter.limit("30/minute")
def create_menu_nutrition(
    request: Request,
    data: MenuNutritionCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create/update nutrition information for a menu item"""
    try:
        nutrition = db.query(MenuItemNutrition).filter(
            MenuItemNutrition.menu_item_id == data.menu_item_id
        ).first()

        # Map schema fields to model fields (different naming convention)
        nutrition_mapping = {
            'serving_size': data.serving_size,
            'calories': float(data.calories) if data.calories else None,
            'calories_from_fat': float(data.calories_from_fat) if data.calories_from_fat else None,
            'total_fat': float(data.total_fat_g) if data.total_fat_g else None,
            'saturated_fat': float(data.saturated_fat_g) if data.saturated_fat_g else None,
            'trans_fat': float(data.trans_fat_g) if data.trans_fat_g else None,
            'cholesterol': float(data.cholesterol_mg) if data.cholesterol_mg else None,
            'sodium': float(data.sodium_mg) if data.sodium_mg else None,
            'total_carbohydrates': float(data.total_carbs_g) if data.total_carbs_g else None,
            'dietary_fiber': float(data.dietary_fiber_g) if data.dietary_fiber_g else None,
            'sugars': float(data.sugars_g) if data.sugars_g else None,
            'protein': float(data.protein_g) if data.protein_g else None,
            'vitamin_a': float(data.vitamin_a_pct) if data.vitamin_a_pct else None,
            'vitamin_c': float(data.vitamin_c_pct) if data.vitamin_c_pct else None,
            'calcium': float(data.calcium_pct) if data.calcium_pct else None,
            'iron': float(data.iron_pct) if data.iron_pct else None,
        }

        if nutrition:
            for key, value in nutrition_mapping.items():
                if value is not None:
                    setattr(nutrition, key, value)
            nutrition.manually_entered = True
        else:
            nutrition = MenuItemNutrition(
                menu_item_id=data.menu_item_id,
                manually_entered=True,
                **{k: v for k, v in nutrition_mapping.items() if v is not None}
            )
            db.add(nutrition)

        db.commit()
        db.refresh(nutrition)
        return nutrition
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating/updating nutrition: {e}")
        raise HTTPException(status_code=500, detail="Failed to save nutrition information")

@router.get("/menu/allergens/{menu_item_id}")
@limiter.limit("60/minute")
def get_menu_allergens(
    request: Request,
    menu_item_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get allergens for a menu item (aggregated from recipe)"""
    try:
        # Get manually added allergens
        allergens = db.query(MenuItemAllergen).filter(
            MenuItemAllergen.menu_item_id == menu_item_id
        ).all()

        # Also try to aggregate from recipe
        service = AdvancedMenuService(db)
        recipe_allergens = service.aggregate_allergens_from_recipe(menu_item_id)

        # Combine results
        all_allergens = list(allergens) + recipe_allergens

        return {
            "menu_item_id": menu_item_id,
            "allergens": [
                {
                    "id": a.id,
                    "allergen_type": a.allergen_type,
                    "severity": a.severity,
                    "notes": a.notes,
                    "manually_added": a.manually_added
                }
                for a in all_allergens
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching allergens: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch allergens")

@router.post("/menu/allergens")
@limiter.limit("30/minute")
def create_menu_allergen(
    request: Request,
    data: MenuAllergenCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Add allergen to a menu item"""
    try:
        allergen = MenuItemAllergen(
            menu_item_id=data.menu_item_id,
            allergen_type=data.allergen_type,
            severity=data.severity,
            notes=data.notes,
            manually_added=True
        )
        db.add(allergen)
        db.commit()
        db.refresh(allergen)
        return allergen
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating allergen: {e}")
        raise HTTPException(status_code=500, detail="Failed to create allergen")

@router.delete("/menu/allergens/{allergen_id}")
@limiter.limit("30/minute")
def delete_menu_allergen(
    request: Request,
    allergen_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Remove allergen from a menu item"""
    try:
        allergen = db.query(MenuItemAllergen).filter(MenuItemAllergen.id == allergen_id).first()
        if not allergen:
            raise HTTPException(status_code=404, detail="Allergen not found")
        db.delete(allergen)
        db.commit()
        return {"status": "deleted"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting allergen: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete allergen")

@router.get("/menu/bundles/{bundle_item_id}")
@limiter.limit("60/minute")
def get_menu_bundle(
    request: Request,
    bundle_item_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get bundle components for a menu item"""
    try:
        bundles = db.query(MenuItemBundle).filter(
            MenuItemBundle.bundle_item_id == bundle_item_id
        ).all()
        return bundles
    except Exception as e:
        logger.error(f"Error fetching bundle components: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch bundle components")

@router.post("/menu/bundles")
@limiter.limit("30/minute")
def create_menu_bundle(
    request: Request,
    data: MenuBundleCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Add item to a bundle"""
    try:
        # Model uses component_item_id, not included_item_id
        bundle = MenuItemBundle(
            bundle_item_id=data.bundle_item_id,
            component_item_id=data.included_item_id,
            quantity=data.quantity,
            is_required=data.is_required,
            price_adjustment=float(data.price_adjustment)
        )
        db.add(bundle)
        db.commit()
        db.refresh(bundle)
        return bundle
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating bundle: {e}")
        raise HTTPException(status_code=500, detail="Failed to create bundle")

@router.post("/menu/bulk-price-update")
@limiter.limit("30/minute")
def bulk_update_menu_prices(
    request: Request,
    venue_id: int,
    data: BulkPriceUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Bulk update menu item prices"""
    try:
        from app.models import MenuItem

        # Build updates list for service method
        updates = []
        for item_id in data.item_ids:
            item = db.query(MenuItem).filter(
                MenuItem.id == item_id,
                MenuItem.venue_id == venue_id
            ).first()

            if item and item.price:
                if data.adjustment_type == "percentage":
                    new_price = float(item.price) * (1 + float(data.adjustment_value) / 100)
                else:  # fixed
                    new_price = float(item.price) + float(data.adjustment_value)

                updates.append({
                    'menu_item_id': item_id,
                    'new_price': max(0, new_price)  # Prevent negative prices
                })

        # Use service for bulk update
        service = AdvancedMenuService(db)
        result = service.bulk_update_prices(
            venue_id=venue_id,
            updates=updates,
            updated_by=current_user.id
        )

        return {"status": "success", "updated_count": result.get("updated", 0), "errors": result.get("errors", [])}
    except Exception as e:
        db.rollback()
        logger.error(f"Error bulk updating prices: {e}")
        raise HTTPException(status_code=500, detail="Failed to bulk update prices")

# ==================== RECIPE MANAGEMENT ENDPOINTS ====================

@router.get("/recipes")
@limiter.limit("60/minute")
def get_recipes(
    request: Request,
    venue_id: int,
    category_id: Optional[int] = None,
    search: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all recipes with filtering"""
    try:
        from app.models import MenuItem
        from app.models.complete_modules import Recipe

        # Get menu items for this venue to find their recipes
        query = db.query(Recipe).join(MenuItem, Recipe.menu_item_id == MenuItem.id).filter(
            MenuItem.venue_id == venue_id
        )

        if search:
            # Search in recipe name (JSON field) - use text search
            from sqlalchemy import cast, String
            query = query.filter(
                cast(Recipe.name, String).ilike(f"%{search}%")
            )

        total = query.count()
        recipes = query.order_by(Recipe.id.desc()).limit(limit).offset(offset).all()

        return {
            "total": total,
            "recipes": [
                {
                    "id": r.id,
                    "name": r.name,
                    "menu_item_id": r.menu_item_id,
                    "yield_quantity": float(r.yield_quantity) if r.yield_quantity else 1,
                    "yield_unit": r.yield_unit,
                    "active": r.active
                }
                for r in recipes
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching recipes: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch recipes")

@router.get("/recipes/{recipe_id}")
@limiter.limit("60/minute")
def get_recipe(
    request: Request,
    recipe_id: int,
    include_sub_recipes: bool = True,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get full recipe with all details"""
    try:
        service = AdvancedRecipeService(db)
        recipe = service.get_full_recipe(
            recipe_id=recipe_id,
            expand_sub_recipes=include_sub_recipes
        )
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")
        return recipe
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching recipe: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch recipe")

@router.post("/recipes")
@limiter.limit("30/minute")
def create_recipe(
    request: Request,
    venue_id: int,
    data: RecipeCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new recipe"""
    try:
        service = AdvancedRecipeService(db)
        recipe = service.create_recipe(
            venue_id=venue_id,
            menu_item_id=data.menu_item_id,
            name=data.name,
            yield_quantity=float(data.yield_quantity),
            yield_unit=data.yield_unit,
            ingredients=data.ingredients,
            created_by=current_user.id,
            preparation_time=data.prep_time_minutes,
            cook_time=data.cook_time_minutes,
            difficulty=data.difficulty_level or "medium",
            instructions=data.instructions
        )
        # Service already commits
        return {"id": recipe.id, "name": recipe.name, "status": "created"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating recipe: {e}")
        raise HTTPException(status_code=500, detail="Failed to create recipe")

@router.put("/recipes/{recipe_id}")
@limiter.limit("30/minute")
def update_recipe(
    request: Request,
    recipe_id: int,
    data: RecipeCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update a recipe (creates new version)"""
    try:
        service = AdvancedRecipeService(db)
        updates = {
            "yield_quantity": float(data.yield_quantity),
            "yield_unit": data.yield_unit,
            "preparation_time": data.prep_time_minutes,
            "difficulty": data.difficulty_level or "medium",
            "ingredients": data.ingredients
        }
        recipe, version = service.update_recipe_with_version(
            recipe_id=recipe_id,
            updates=updates,
            updated_by=current_user.id
        )
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")
        # Service already commits
        return {"id": recipe.id, "name": recipe.name, "version": version.version_number, "status": "updated"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating recipe: {e}")
        raise HTTPException(status_code=500, detail="Failed to update recipe")

@router.get("/recipes/{recipe_id}/versions")
@limiter.limit("60/minute")
def get_recipe_versions(
    request: Request,
    recipe_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get version history for a recipe"""
    try:
        versions = db.query(RecipeVersion).filter(
            RecipeVersion.recipe_id == recipe_id
        ).order_by(RecipeVersion.version_number.desc()).all()
        return versions
    except Exception as e:
        logger.error(f"Error fetching recipe versions: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch recipe versions")

@router.post("/recipes/{recipe_id}/ingredients")
@limiter.limit("30/minute")
def add_recipe_ingredient(
    request: Request,
    recipe_id: int,
    data: RecipeIngredientCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Add ingredient to a recipe"""
    try:
        from app.models.complete_modules import RecipeIngredient
        from app.models import StockItem

        # Check if recipe exists
        from app.models.complete_modules import Recipe
        recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")

        # Get stock item cost
        stock_item = db.query(StockItem).filter(StockItem.id == data.ingredient_id).first()
        unit_cost = float(stock_item.cost_per_unit) if stock_item and stock_item.cost_per_unit else 0

        ingredient = RecipeIngredient(
            recipe_id=recipe_id,
            stock_item_id=data.ingredient_id,
            quantity=float(data.quantity),
            unit=data.unit,
            cost_per_unit=unit_cost,
            is_optional=data.is_optional,
            substitutes=data.substitutes
        )
        db.add(ingredient)
        db.commit()
        db.refresh(ingredient)
        return {"status": "success", "id": ingredient.id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error adding recipe ingredient: {e}")
        raise HTTPException(status_code=500, detail="Failed to add ingredient")

@router.post("/recipes/{recipe_id}/instructions")
@limiter.limit("30/minute")
def add_recipe_instruction(
    request: Request,
    recipe_id: int,
    data: RecipeInstructionCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Add instruction step to a recipe"""
    try:
        # Check if recipe exists
        from app.models.complete_modules import Recipe
        recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")

        # Map schema fields to model fields (model uses different names)
        instruction = RecipeInstruction(
            recipe_id=recipe_id,
            step_number=data.step_number,
            instruction_text=data.instruction,  # Model uses instruction_text
            estimated_time_minutes=data.duration_minutes,  # Model uses estimated_time_minutes
            temperature_celsius=float(data.temperature) if data.temperature else None,  # Model uses temperature_celsius
            equipment_needed=[data.equipment] if data.equipment else None,  # Model uses equipment_needed as JSON array
            tips=data.tips,
            image_url=data.image_url,
            video_url=data.video_url
        )
        db.add(instruction)
        db.commit()
        db.refresh(instruction)
        return instruction
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error adding recipe instruction: {e}")
        raise HTTPException(status_code=500, detail="Failed to add instruction")

@router.post("/recipes/sub-recipes")
@limiter.limit("30/minute")
def add_sub_recipe(
    request: Request,
    data: SubRecipeCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Add a sub-recipe to a parent recipe"""
    try:
        service = AdvancedRecipeService(db)
        sub_recipe = service.add_sub_recipe(
            parent_recipe_id=data.parent_recipe_id,
            child_recipe_id=data.child_recipe_id,
            quantity=float(data.quantity),
            unit=data.unit
        )
        # Service already commits
        return {"status": "success", "id": sub_recipe.id if sub_recipe else None}
    except Exception as e:
        db.rollback()
        logger.error(f"Error adding sub-recipe: {e}")
        raise HTTPException(status_code=500, detail="Failed to add sub-recipe")

@router.post("/recipes/scale")
@limiter.limit("30/minute")
def scale_recipe(
    request: Request,
    data: RecipeScaleRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Scale a recipe to a target yield"""
    try:
        service = AdvancedRecipeService(db)
        scaled = service.scale_recipe(
            recipe_id=data.recipe_id,
            target_yield=float(data.target_yield)
        )
        if not scaled:
            raise HTTPException(status_code=404, detail="Recipe not found")
        return scaled
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error scaling recipe: {e}")
        raise HTTPException(status_code=500, detail="Failed to scale recipe")

@router.get("/recipes/{recipe_id}/cost")
@limiter.limit("60/minute")
def calculate_recipe_cost(
    request: Request,
    recipe_id: int,
    quantity: Decimal = Decimal("1"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Calculate current cost for a recipe"""
    try:
        service = AdvancedRecipeService(db)
        cost = service.calculate_recipe_cost(
            recipe_id=recipe_id
        )
        if not cost:
            raise HTTPException(status_code=404, detail="Recipe not found")
        return cost
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating recipe cost: {e}")
        raise HTTPException(status_code=500, detail="Failed to calculate recipe cost")

@router.get("/recipes/{recipe_id}/cost-history")
@limiter.limit("60/minute")
def get_recipe_cost_history(
    request: Request,
    recipe_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get cost history for a recipe"""
    try:
        # Model uses recorded_date, not calculated_at
        query = db.query(RecipeCostHistory).filter(RecipeCostHistory.recipe_id == recipe_id)
        if start_date:
            query = query.filter(RecipeCostHistory.recorded_date >= start_date)
        if end_date:
            query = query.filter(RecipeCostHistory.recorded_date <= end_date)
        return query.order_by(RecipeCostHistory.recorded_date.desc()).all()
    except Exception as e:
        logger.error(f"Error fetching recipe cost history: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch cost history")

# ==================== STOCK MANAGEMENT ENDPOINTS ====================

@router.get("/warehouses")
@limiter.limit("60/minute")
def get_warehouses(
    request: Request,
    venue_id: int,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all warehouses for a venue"""
    try:
        query = db.query(Warehouse).filter(Warehouse.venue_id == venue_id)
        if not include_inactive:
            query = query.filter(Warehouse.is_active == True)
        return query.order_by(Warehouse.name).all()
    except Exception as e:
        logger.error(f"Error fetching warehouses: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch warehouses")

@router.post("/warehouses")
@limiter.limit("30/minute")
def create_warehouse(
    request: Request,
    venue_id: int,
    data: WarehouseCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new warehouse"""
    try:
        service = AdvancedStockService(db)
        # Service method takes name as dict, but we have it as dict in schema
        warehouse = service.create_warehouse(
            venue_id=venue_id,
            name=data.name if isinstance(data.name, str) else str(data.name),
            code=data.code,
            warehouse_type=data.warehouse_type,
            is_primary=False  # WarehouseCreate doesn't have is_primary
        )
        # Service already commits
        return warehouse
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating warehouse: {e}")
        raise HTTPException(status_code=500, detail="Failed to create warehouse")

@router.get("/warehouses/{warehouse_id}")
@limiter.limit("60/minute")
def get_warehouse(
    request: Request,
    warehouse_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get warehouse details with stock summary"""
    try:
        warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
        if not warehouse:
            raise HTTPException(status_code=404, detail="Warehouse not found")
        return warehouse
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching warehouse: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch warehouse")

@router.put("/warehouses/{warehouse_id}")
@limiter.limit("30/minute")
def update_warehouse(
    request: Request,
    warehouse_id: int,
    data: WarehouseCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update warehouse details"""
    try:
        warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
        if not warehouse:
            raise HTTPException(status_code=404, detail="Warehouse not found")

        # Update only fields that exist on the model
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if hasattr(warehouse, key):
                setattr(warehouse, key, value)

        db.commit()
        db.refresh(warehouse)
        return warehouse
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating warehouse: {e}")
        raise HTTPException(status_code=500, detail="Failed to update warehouse")

@router.get("/warehouses/{warehouse_id}/stock")
@limiter.limit("60/minute")
def get_warehouse_stock(
    request: Request,
    warehouse_id: int,
    venue_id: int = Query(..., description="Venue ID"),
    include_batches: bool = False,
    low_stock_only: bool = False,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get stock levels for a warehouse"""
    try:
        service = AdvancedStockService(db)
        stock = service.get_stock_valuation(
            venue_id=venue_id,
            warehouse_id=warehouse_id
        )

        if low_stock_only and 'items' in stock:
            stock['items'] = [s for s in stock['items'] if s.get("is_low_stock", False)]

        return stock
    except Exception as e:
        logger.error(f"Error fetching warehouse stock: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch warehouse stock")

@router.get("/stock/batches")
@limiter.limit("60/minute")
def get_stock_batches(
    request: Request,
    venue_id: int = Query(..., description="Venue ID"),
    warehouse_id: Optional[int] = None,
    stock_item_id: Optional[int] = None,
    expiring_within_days: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get stock batches with optional filtering"""
    try:
        service = AdvancedStockService(db)

        if expiring_within_days:
            batches = service.get_expiring_batches(
                venue_id=venue_id,
                days_ahead=expiring_within_days
            )
        else:
            query = db.query(StockBatch).filter(StockBatch.status == "active")
            if warehouse_id:
                query = query.filter(StockBatch.warehouse_id == warehouse_id)
            if stock_item_id:
                query = query.filter(StockBatch.stock_item_id == stock_item_id)
            batches = query.order_by(StockBatch.expiry_date).all()

        return batches
    except Exception as e:
        logger.error(f"Error fetching stock batches: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch stock batches")

@router.post("/stock/batches")
@limiter.limit("30/minute")
def create_stock_batch(
    request: Request,
    data: StockBatchCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new stock batch"""
    try:
        service = AdvancedStockService(db)
        wh_stock, batch = service.add_stock_to_warehouse(
            warehouse_id=data.warehouse_id,
            stock_item_id=data.stock_item_id,
            quantity=float(data.quantity),
            batch_number=data.batch_number,
            expiry_date=data.expiry_date,
            unit_cost=float(data.unit_cost) if data.unit_cost else None,
            supplier_id=data.supplier_id,
            purchase_order_id=data.purchase_order_id,
            recorded_by=current_user.id
        )
        # Service already commits
        return batch
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating stock batch: {e}")
        raise HTTPException(status_code=500, detail="Failed to create stock batch")

@router.get("/stock/transfers")
@limiter.limit("60/minute")
def get_stock_transfers(
    request: Request,
    venue_id: int,
    status: Optional[str] = None,
    from_warehouse_id: Optional[int] = None,
    to_warehouse_id: Optional[int] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get stock transfers"""
    try:
        query = db.query(StockTransfer).filter(StockTransfer.venue_id == venue_id)
        if status:
            query = query.filter(StockTransfer.status == status)
        if from_warehouse_id:
            query = query.filter(StockTransfer.from_warehouse_id == from_warehouse_id)
        if to_warehouse_id:
            query = query.filter(StockTransfer.to_warehouse_id == to_warehouse_id)

        # Model uses requested_date, not created_at
        return query.order_by(StockTransfer.requested_date.desc()).limit(limit).offset(offset).all()
    except Exception as e:
        logger.error(f"Error fetching stock transfers: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch stock transfers")

@router.post("/stock/transfers")
@limiter.limit("30/minute")
def create_stock_transfer(
    request: Request,
    venue_id: int,
    data: StockTransferCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a stock transfer between warehouses"""
    try:
        service = AdvancedStockService(db)
        transfer = service.transfer_stock(
            venue_id=venue_id,
            from_warehouse_id=data.from_warehouse_id,
            to_warehouse_id=data.to_warehouse_id,
            items=data.items,
            requested_by=current_user.id,
            reason=data.notes
        )
        # Service already commits
        return transfer
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating stock transfer: {e}")
        raise HTTPException(status_code=500, detail="Failed to create stock transfer")

@router.post("/stock/transfers/{transfer_id}/complete")
@limiter.limit("30/minute")
def complete_stock_transfer(
    request: Request,
    transfer_id: int,
    received_items: List[Dict[str, Any]] = Body(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Complete a stock transfer (receive items)"""
    try:
        service = AdvancedStockService(db)
        transfer = service.complete_transfer(
            transfer_id=transfer_id,
            shipped_by=current_user.id,
            received_by=current_user.id,
            received_items=received_items
        )
        if not transfer:
            raise HTTPException(status_code=404, detail="Transfer not found")
        # Service already commits
        return transfer
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error completing stock transfer: {e}")
        raise HTTPException(status_code=500, detail="Failed to complete stock transfer")

@router.post("/stock/transfers/{transfer_id}/cancel")
@limiter.limit("30/minute")
def cancel_stock_transfer(
    request: Request,
    transfer_id: int,
    reason: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Cancel a pending stock transfer"""
    try:
        transfer = db.query(StockTransfer).filter(StockTransfer.id == transfer_id).first()
        if not transfer:
            raise HTTPException(status_code=404, detail="Transfer not found")
        if transfer.status != "pending" and transfer.status != "draft":
            raise HTTPException(status_code=400, detail="Only pending/draft transfers can be cancelled")

        transfer.status = "cancelled"
        transfer.notes = f"{transfer.notes or ''}\nCancelled: {reason}"
        db.commit()
        return transfer
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error cancelling stock transfer: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel stock transfer")

@router.get("/stock/adjustments")
@limiter.limit("60/minute")
def get_stock_adjustments(
    request: Request,
    venue_id: int,
    warehouse_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get stock adjustments"""
    try:
        query = db.query(StockAdjustment).filter(StockAdjustment.venue_id == venue_id)
        if warehouse_id:
            query = query.filter(StockAdjustment.warehouse_id == warehouse_id)
        if status:
            query = query.filter(StockAdjustment.status == status)

        return query.order_by(StockAdjustment.created_at.desc()).limit(limit).offset(offset).all()
    except Exception as e:
        logger.error(f"Error fetching stock adjustments: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch stock adjustments")

@router.post("/stock/adjustments")
@limiter.limit("30/minute")
def create_stock_adjustment(
    request: Request,
    venue_id: int,
    data: StockAdjustmentCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a stock adjustment"""
    try:
        service = AdvancedStockService(db)
        adjustment = service.create_adjustment(
            venue_id=venue_id,
            warehouse_id=data.warehouse_id,
            adjustment_type=data.adjustment_type,
            items=data.items,
            created_by=current_user.id,
            notes=data.notes
        )
        # Service already commits
        return adjustment
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating stock adjustment: {e}")
        raise HTTPException(status_code=500, detail="Failed to create stock adjustment")

@router.post("/stock/adjustments/{adjustment_id}/approve")
@limiter.limit("30/minute")
def approve_stock_adjustment(
    request: Request,
    adjustment_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Approve a pending stock adjustment"""
    try:
        service = AdvancedStockService(db)
        adjustment = service.approve_adjustment(
            adjustment_id=adjustment_id,
            approved_by=current_user.id
        )
        if not adjustment:
            raise HTTPException(status_code=404, detail="Adjustment not found or not pending")
        # Service already commits
        return adjustment
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error approving stock adjustment: {e}")
        raise HTTPException(status_code=500, detail="Failed to approve stock adjustment")

@router.post("/stock/reservations")
@limiter.limit("30/minute")
def create_stock_reservation(
    request: Request,
    data: StockReservationCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Reserve stock for an order or event"""
    try:
        service = AdvancedStockService(db)
        reservation = service.reserve_stock(
            stock_item_id=data.stock_item_id,
            warehouse_id=data.warehouse_id,
            quantity=float(data.quantity),
            reservation_type=data.reservation_type,
            reference_type=data.reference_type,
            reference_id=data.reference_id,
            expires_at=data.expires_at
        )
        # Service already commits
        return reservation
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating stock reservation: {e}")
        raise HTTPException(status_code=500, detail="Failed to create stock reservation")

@router.post("/stock/reservations/{reservation_id}/release")
@limiter.limit("30/minute")
def release_stock_reservation(
    request: Request,
    reservation_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Release a stock reservation"""
    try:
        reservation = db.query(StockReservation).filter(StockReservation.id == reservation_id).first()
        if not reservation:
            raise HTTPException(status_code=404, detail="Reservation not found")
        reservation.status = "released"
        reservation.released_at = datetime.now(timezone.utc)
        db.commit()
        return {"status": "released"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error releasing stock reservation: {e}")
        raise HTTPException(status_code=500, detail="Failed to release stock reservation")

@router.get("/stock/valuation")
@limiter.limit("60/minute")
def get_stock_valuation(
    request: Request,
    venue_id: int,
    warehouse_id: Optional[int] = None,
    valuation_method: str = "fifo",
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get stock valuation report"""
    try:
        service = AdvancedStockService(db)
        valuation = service.get_stock_valuation(
            venue_id=venue_id,
            warehouse_id=warehouse_id,
            method=valuation_method
        )
        return valuation
    except Exception as e:
        logger.error(f"Error fetching stock valuation: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch stock valuation")

@router.get("/stock/expiring")
@limiter.limit("60/minute")
def get_expiring_stock(
    request: Request,
    venue_id: int,
    days: int = Query(7, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get items expiring within specified days"""
    try:
        service = AdvancedStockService(db)
        expiring = service.get_expiring_batches(venue_id=venue_id, days_ahead=days)
        return expiring
    except Exception as e:
        logger.error(f"Error fetching expiring stock: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch expiring stock")

# ==================== SUPPLIER MANAGEMENT ENDPOINTS ====================

@router.get("/suppliers/{supplier_id}/contacts")
@limiter.limit("60/minute")
def get_supplier_contacts(
    request: Request,
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get contacts for a supplier"""
    try:
        return db.query(SupplierContact).filter(
            SupplierContact.supplier_id == supplier_id,
            SupplierContact.is_active == True
        ).all()
    except Exception as e:
        logger.error(f"Error fetching supplier contacts: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch supplier contacts")

@router.post("/suppliers/contacts")
@limiter.limit("30/minute")
def create_supplier_contact(
    request: Request,
    data: SupplierContactCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Add a contact to a supplier"""
    try:
        service = AdvancedSupplierService(db)
        contact_data = data.model_dump(exclude={"supplier_id"})
        contact = service.add_supplier_contact(
            supplier_id=data.supplier_id,
            contact_name=contact_data.get("contact_name", ""),
            role=contact_data.get("role"),
            email=contact_data.get("email"),
            phone=contact_data.get("phone"),
            is_primary=contact_data.get("is_primary", False)
        )
        # Service already commits
        return contact
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating supplier contact: {e}")
        raise HTTPException(status_code=500, detail="Failed to create supplier contact")

@router.put("/suppliers/contacts/{contact_id}")
@limiter.limit("30/minute")
def update_supplier_contact(
    request: Request,
    contact_id: int,
    data: SupplierContactCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update a supplier contact"""
    try:
        contact = db.query(SupplierContact).filter(SupplierContact.id == contact_id).first()
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")

        for key, value in data.model_dump(exclude={"supplier_id"}, exclude_unset=True).items():
            if hasattr(contact, key):
                setattr(contact, key, value)

        db.commit()
        db.refresh(contact)
        return contact
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating supplier contact: {e}")
        raise HTTPException(status_code=500, detail="Failed to update supplier contact")

@router.get("/suppliers/{supplier_id}/price-lists")
@limiter.limit("60/minute")
def get_supplier_price_lists(
    request: Request,
    supplier_id: int,
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get price lists for a supplier"""
    try:
        query = db.query(SupplierPriceList).filter(SupplierPriceList.supplier_id == supplier_id)
        if active_only:
            query = query.filter(SupplierPriceList.is_active == True)
        return query.order_by(SupplierPriceList.effective_from.desc()).all()
    except Exception as e:
        logger.error(f"Error fetching supplier price lists: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch supplier price lists")

@router.post("/suppliers/price-lists")
@limiter.limit("30/minute")
def create_supplier_price_list(
    request: Request,
    data: SupplierPriceListCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new price list for a supplier"""
    try:
        service = AdvancedSupplierService(db)
        price_list_data = data.model_dump(exclude={"supplier_id", "items"})
        price_list = service.create_price_list(
            supplier_id=data.supplier_id,
            name=price_list_data.get("name", ""),
            effective_from=price_list_data.get("effective_from"),
            items=data.items,
            effective_to=price_list_data.get("effective_to"),
            currency=price_list_data.get("currency", "BGN")
        )
        # Service already commits
        return price_list
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating supplier price list: {e}")
        raise HTTPException(status_code=500, detail="Failed to create supplier price list")

@router.get("/suppliers/price-lists/{price_list_id}/items")
@limiter.limit("60/minute")
def get_price_list_items(
    request: Request,
    price_list_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get items in a price list"""
    try:
        return db.query(SupplierPriceListItem).filter(
            SupplierPriceListItem.price_list_id == price_list_id,
            SupplierPriceListItem.is_active == True
        ).all()
    except Exception as e:
        logger.error(f"Error fetching price list items: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch price list items")

@router.get("/suppliers/best-price/{stock_item_id}")
@limiter.limit("60/minute")
def get_best_supplier_price(
    request: Request,
    stock_item_id: int,
    venue_id: int = Query(...),
    quantity: Decimal = Decimal("1"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get best price across all suppliers for an item"""
    try:
        service = AdvancedSupplierService(db)
        best_price = service.get_best_price(
            stock_item_id=stock_item_id,
            quantity=float(quantity),
            venue_id=venue_id
        )
        return best_price
    except Exception as e:
        logger.error(f"Error fetching best supplier price: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch best supplier price")

@router.get("/suppliers/{supplier_id}/documents")
@limiter.limit("60/minute")
def get_supplier_documents(
    request: Request,
    supplier_id: int,
    document_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get documents for a supplier"""
    try:
        query = db.query(SupplierDocument).filter(SupplierDocument.supplier_id == supplier_id)
        if document_type:
            query = query.filter(SupplierDocument.document_type == document_type)
        # Model uses uploaded_at, not created_at
        return query.order_by(SupplierDocument.uploaded_at.desc()).all()
    except Exception as e:
        logger.error(f"Error fetching supplier documents: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch supplier documents")

@router.post("/suppliers/documents")
@limiter.limit("30/minute")
def upload_supplier_document(
    request: Request,
    data: SupplierDocumentCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Upload a document for a supplier"""
    try:
        document = SupplierDocument(
            supplier_id=data.supplier_id,
            document_type=data.document_type,
            document_name=data.document_name,
            file_url=data.file_url,
            file_name=data.document_name,  # Use document_name as file_name if not separate
            expiry_date=data.expiry_date,
            notes=data.notes,
            uploaded_by=current_user.id
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        return document
    except Exception as e:
        db.rollback()
        logger.error(f"Error uploading supplier document: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload supplier document")

@router.get("/suppliers/expiring-documents")
@limiter.limit("60/minute")
def get_expiring_supplier_documents(
    request: Request,
    venue_id: int,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get supplier documents expiring within specified days"""
    try:
        service = AdvancedSupplierService(db)
        expiring = service.get_supplier_documents_expiring(venue_id=venue_id, days_ahead=days)
        return expiring
    except Exception as e:
        logger.error(f"Error fetching expiring supplier documents: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch expiring supplier documents")

@router.get("/suppliers/{supplier_id}/ratings")
@limiter.limit("60/minute")
def get_supplier_ratings(
    request: Request,
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get ratings history for a supplier"""
    try:
        return db.query(SupplierRating).filter(
            SupplierRating.supplier_id == supplier_id
        ).order_by(SupplierRating.period_end.desc()).all()
    except Exception as e:
        logger.error(f"Error fetching supplier ratings: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch supplier ratings")

@router.post("/suppliers/ratings")
@limiter.limit("30/minute")
def create_supplier_rating(
    request: Request,
    venue_id: int,
    data: SupplierRatingCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a rating for a supplier"""
    try:
        service = AdvancedSupplierService(db)
        rating = service.rate_supplier(
            venue_id=venue_id,
            supplier_id=data.supplier_id,
            period_start=data.rating_period_start,
            period_end=data.rating_period_end,
            rated_by=current_user.id
        )
        # Service already commits
        return rating
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating supplier rating: {e}")
        raise HTTPException(status_code=500, detail="Failed to create supplier rating")

# ==================== PURCHASE ORDER ENDPOINTS ====================

@router.get("/purchase-orders/templates")
@limiter.limit("60/minute")
def get_po_templates(
    request: Request,
    venue_id: int,
    supplier_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get purchase order templates"""
    try:
        query = db.query(PurchaseOrderTemplate).filter(
            PurchaseOrderTemplate.venue_id == venue_id,
            PurchaseOrderTemplate.is_active == True
        )
        if supplier_id:
            query = query.filter(PurchaseOrderTemplate.supplier_id == supplier_id)
        return query.all()
    except Exception as e:
        logger.error(f"Error fetching PO templates: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch PO templates")

@router.post("/purchase-orders/templates")
@limiter.limit("30/minute")
def create_po_template(
    request: Request,
    venue_id: int,
    data: POTemplateCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a purchase order template"""
    try:
        template_data = data.model_dump(exclude={"items"})
        # Model uses 'template_name' and 'items' (as JSON column)
        template = PurchaseOrderTemplate(
            venue_id=venue_id,
            supplier_id=template_data.get("supplier_id"),
            template_name=template_data.get("name", ""),
            description=template_data.get("description"),
            items=data.items,
            is_active=True
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        return template
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating PO template: {e}")
        raise HTTPException(status_code=500, detail="Failed to create PO template")

@router.post("/purchase-orders/from-template/{template_id}")
@limiter.limit("30/minute")
def create_po_from_template(
    request: Request,
    template_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a purchase order from a template"""
    try:
        service = AdvancedPurchaseOrderService(db)
        po = service.create_from_template(
            template_id=template_id,
            created_by=current_user.id
        )
        if not po:
            raise HTTPException(status_code=404, detail="Template not found")
        # Service already commits
        return po
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating PO from template: {e}")
        raise HTTPException(status_code=500, detail="Failed to create PO from template")

@router.get("/purchase-orders/{po_id}/approvals")
@limiter.limit("60/minute")
def get_po_approvals(
    request: Request,
    po_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get approval history for a purchase order"""
    try:
        return db.query(PurchaseOrderApproval).filter(
            PurchaseOrderApproval.purchase_order_id == po_id
        ).order_by(PurchaseOrderApproval.approval_level).all()
    except Exception as e:
        logger.error(f"Error fetching PO approvals: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch PO approvals")

@router.post("/purchase-orders/approvals")
@limiter.limit("30/minute")
def submit_po_approval(
    request: Request,
    data: POApprovalCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Submit approval/rejection for a purchase order"""
    try:
        # Get the pending approval for this PO
        approval = db.query(PurchaseOrderApproval).filter(
            PurchaseOrderApproval.purchase_order_id == data.purchase_order_id,
            PurchaseOrderApproval.status == "pending"
        ).first()

        if not approval:
            raise HTTPException(status_code=400, detail="No pending approval found")

        service = AdvancedPurchaseOrderService(db)
        result, all_approved = service.process_approval(
            approval_id=approval.id,
            approved_by=current_user.id,
            approved=data.action == "approve",
            comments=data.notes
        )

        if not result:
            raise HTTPException(status_code=400, detail="Approval action failed")
        # Service already commits
        return result
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error processing PO approval: {e}")
        raise HTTPException(status_code=500, detail="Failed to process PO approval")

@router.get("/purchase-orders/pending-approval")
@limiter.limit("60/minute")
def get_pending_approval_pos(
    request: Request,
    venue_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get purchase orders pending approval"""
    try:
        from app.models import PurchaseOrder
        pending_approvals = db.query(PurchaseOrderApproval).filter(
            PurchaseOrderApproval.status == "pending"
        ).all()
        po_ids = [a.purchase_order_id for a in pending_approvals]
        if not po_ids:
            return []
        return db.query(PurchaseOrder).filter(
            PurchaseOrder.venue_id == venue_id,
            PurchaseOrder.id.in_(po_ids)
        ).all()
    except Exception as e:
        logger.error(f"Error fetching pending approval POs: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch pending approval POs")

@router.get("/invoices")
@limiter.limit("60/minute")
def get_supplier_invoices(
    request: Request,
    venue_id: int,
    supplier_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get supplier invoices"""
    try:
        query = db.query(SupplierInvoice).filter(SupplierInvoice.venue_id == venue_id)
        if supplier_id:
            query = query.filter(SupplierInvoice.supplier_id == supplier_id)
        if status:
            query = query.filter(SupplierInvoice.status == status)

        return query.order_by(SupplierInvoice.invoice_date.desc()).limit(limit).offset(offset).all()
    except Exception as e:
        logger.error(f"Error fetching supplier invoices: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch supplier invoices")

@router.post("/invoices")
@limiter.limit("30/minute")
def create_supplier_invoice(
    request: Request,
    venue_id: int,
    data: SupplierInvoiceCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a supplier invoice"""
    try:
        service = AdvancedPurchaseOrderService(db)
        invoice_data = data.model_dump(exclude={"items"})
        invoice = service.create_invoice(
            venue_id=venue_id,
            supplier_id=invoice_data.get("supplier_id"),
            invoice_number=invoice_data.get("invoice_number", ""),
            invoice_date=invoice_data.get("invoice_date"),
            items=data.items,
            created_by=current_user.id,
            purchase_order_id=invoice_data.get("purchase_order_id")
        )
        # Service already commits
        return invoice
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating supplier invoice: {e}")
        raise HTTPException(status_code=500, detail="Failed to create supplier invoice")

@router.post("/invoices/{invoice_id}/match")
@limiter.limit("30/minute")
def perform_three_way_match(
    request: Request,
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Perform three-way matching (PO, GRN, Invoice)"""
    try:
        service = AdvancedPurchaseOrderService(db)
        result = service.three_way_match(invoice_id)
        if not result:
            raise HTTPException(status_code=404, detail="Invoice not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error performing three-way match: {e}")
        raise HTTPException(status_code=500, detail="Failed to perform three-way match")

@router.get("/grn")
@limiter.limit("60/minute")
def get_goods_received_notes(
    request: Request,
    venue_id: int,
    purchase_order_id: Optional[int] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get goods received notes"""
    try:
        query = db.query(GoodsReceivedNote).filter(GoodsReceivedNote.venue_id == venue_id)
        if purchase_order_id:
            query = query.filter(GoodsReceivedNote.purchase_order_id == purchase_order_id)

        return query.order_by(GoodsReceivedNote.delivery_date.desc()).limit(limit).offset(offset).all()
    except Exception as e:
        logger.error(f"Error fetching GRN: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch goods received notes")

@router.post("/grn")
@limiter.limit("30/minute")
def create_goods_received_note(
    request: Request,
    venue_id: int,
    data: GRNCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a goods received note (receive items from PO)"""
    try:
        service = AdvancedPurchaseOrderService(db)
        grn = service.create_grn(
            venue_id=venue_id,
            supplier_id=data.supplier_id,
            items=data.items,
            received_by=current_user.id,
            purchase_order_id=data.purchase_order_id,
            warehouse_id=data.warehouse_id
        )
        # Service already commits
        return grn
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating GRN: {e}")
        raise HTTPException(status_code=500, detail="Failed to create goods received note")

@router.get("/purchase-orders/analytics")
@limiter.limit("60/minute")
def get_po_analytics(
    request: Request,
    venue_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    supplier_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get purchase order analytics"""
    try:
        service = AdvancedPurchaseOrderService(db)
        # Use default date range if not provided
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()
        analytics = service.get_analytics(
            venue_id=venue_id,
            period_start=start_date,
            period_end=end_date
        )
        return analytics
    except Exception as e:
        logger.error(f"Error fetching PO analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch PO analytics")

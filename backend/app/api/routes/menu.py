"""Menu API routes - frontend-facing /menu/* endpoints.

Provides proxy/alias endpoints for menu management features
that the frontend expects under the /menu prefix.

Includes advanced menu management features (versioning, scheduling,
nutrition, allergens, bundles, bulk-price-update) merged from
enhanced_inventory_endpoints.py.
"""

import logging
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime, date, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.rate_limit import limiter
from app.db.session import DbSession, get_db
from app.core.rbac import get_current_user
from app.models.restaurant import (
    MenuItem, ModifierGroup, ModifierOption, MenuItemModifierGroup,
    ComboMeal, ComboItem, MenuCategory,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== MODIFIERS ====================

@router.get("/modifiers")
@limiter.limit("60/minute")
def get_menu_modifiers(
    request: Request,
    db: DbSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """Get modifier groups with their options (paginated)."""
    total = db.query(func.count(ModifierGroup.id)).scalar() or 0

    groups = (
        db.query(ModifierGroup)
        .order_by(ModifierGroup.sort_order, ModifierGroup.name)
        .offset(skip)
        .limit(limit)
        .all()
    )

    # Batch-load all options for the fetched groups to avoid N+1
    group_ids = [g.id for g in groups]
    all_options = (
        db.query(ModifierOption)
        .filter(ModifierOption.group_id.in_(group_ids))
        .order_by(ModifierOption.sort_order)
        .all()
    ) if group_ids else []
    options_map: dict = {}
    for opt in all_options:
        options_map.setdefault(opt.group_id, []).append(opt)

    results = []
    for group in groups:
        options = options_map.get(group.id, [])

        results.append({
            "id": group.id,
            "name": group.name,
            "min_selections": group.min_selections,
            "max_selections": group.max_selections,
            "active": group.active,
            "sort_order": group.sort_order,
            "options": [
                {
                    "id": opt.id,
                    "name": opt.name,
                    "price_adjustment": float(opt.price_adjustment or 0),
                    "available": opt.available,
                    "sort_order": opt.sort_order,
                }
                for opt in options
            ],
            "created_at": group.created_at.isoformat() if group.created_at else None,
            "updated_at": group.updated_at.isoformat() if group.updated_at else None,
        })

    return {
        "modifier_groups": results,
        "total": total,
        "skip": skip,
        "limit": limit,
    }


# ==================== COMBOS ====================

@router.get("/combos")
@limiter.limit("60/minute")
def get_menu_combos(request: Request, db: DbSession):
    """Get combo meals with their items."""
    combos = db.query(ComboMeal).order_by(ComboMeal.name).all()

    results = []
    for combo in combos:
        items = db.query(ComboItem).filter(
            ComboItem.combo_id == combo.id,
        ).all()

        results.append({
            "id": combo.id,
            "name": combo.name,
            "description": combo.description,
            "price": float(combo.price),
            "image_url": combo.image_url,
            "available": combo.available,
            "featured": combo.featured,
            "category": combo.category,
            "items": [
                {
                    "id": item.id,
                    "name": item.name,
                    "menu_item_id": item.menu_item_id,
                    "quantity": item.quantity,
                    "is_choice": item.is_choice,
                    "choice_group": item.choice_group,
                }
                for item in items
            ],
            "created_at": combo.created_at.isoformat() if combo.created_at else None,
            "updated_at": combo.updated_at.isoformat() if combo.updated_at else None,
        })

    return {
        "combos": results,
        "total": len(results),
    }


# ==================== ALLERGENS ====================

@router.get("/allergens")
@limiter.limit("60/minute")
def get_menu_allergens(request: Request, db: DbSession):
    """Get menu items with allergen information."""
    items = db.query(MenuItem).filter(
        MenuItem.available == True,
        MenuItem.not_deleted(),
    ).order_by(MenuItem.name).all()

    # Collect all unique allergens
    all_allergens = set()
    item_list = []
    for item in items:
        allergens = item.allergens or []
        if isinstance(allergens, list):
            all_allergens.update(allergens)
        item_list.append({
            "id": item.id,
            "name": item.name,
            "category": item.category,
            "price": float(item.price),
            "allergens": allergens if isinstance(allergens, list) else [],
        })

    return {
        "items": item_list,
        "total": len(item_list),
        "all_allergens": sorted(all_allergens),
    }


# ==================== SCHEDULING ====================

@router.get("/scheduling")
@limiter.limit("60/minute")
def get_menu_scheduling(request: Request, db: DbSession):
    """Get menu scheduling / daypart information."""
    categories = db.query(MenuCategory).filter(
        MenuCategory.active == True,
    ).order_by(MenuCategory.sort_order).all()

    schedules = []
    for cat in categories:
        if cat.schedule:
            schedules.append({
                "id": cat.id,
                "category_name": cat.name_bg or cat.name_en or "",
                "category_name_en": cat.name_en or "",
                "schedule": cat.schedule,
                "active": cat.active,
            })

    # Also include menu items with prep time as scheduling-relevant
    items = db.query(MenuItem).filter(
        MenuItem.available == True,
        MenuItem.not_deleted(),
    ).order_by(MenuItem.name).all()

    item_schedules = []
    for item in items:
        item_schedules.append({
            "id": item.id,
            "name": item.name,
            "category": item.category,
            "available": item.available,
            "prep_time_minutes": item.prep_time_minutes,
            "station": item.station,
        })

    return {
        "category_schedules": schedules,
        "items": item_schedules,
        "total_categories": len(schedules),
        "total_items": len(item_schedules),
    }


# ==================== INVENTORY (menu item stock status) ====================

@router.get("/inventory")
@limiter.limit("60/minute")
def get_menu_inventory(request: Request, db: DbSession):
    """Get menu item inventory/availability status."""
    items = db.query(MenuItem).filter(
        MenuItem.not_deleted(),
    ).order_by(MenuItem.name).all()

    results = []
    available_count = 0
    unavailable_count = 0
    for item in items:
        results.append({
            "id": item.id,
            "name": item.name,
            "category": item.category,
            "price": float(item.price),
            "available": item.available,
            "station": item.station,
            "prep_time_minutes": item.prep_time_minutes,
            "recipe_id": item.recipe_id,
            "pos_item_id": item.pos_item_id,
        })
        if item.available:
            available_count += 1
        else:
            unavailable_count += 1

    return {
        "items": results,
        "total": len(results),
        "available": available_count,
        "unavailable": unavailable_count,
    }


# ==================== ADVANCED MENU MANAGEMENT ====================
# (merged from enhanced_inventory_endpoints.py)

# --- Schemas ---

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


# --- Endpoints ---


@router.get("/versions/{menu_item_id}")
@limiter.limit("60/minute")
def get_menu_item_versions(
    request: Request,
    menu_item_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get version history for a menu item."""
    try:
        from app.models.enhanced_inventory import MenuItemVersionHistory

        versions = db.query(MenuItemVersionHistory).filter(
            MenuItemVersionHistory.menu_item_id == menu_item_id
        ).order_by(MenuItemVersionHistory.id.desc()).all()
        return versions
    except Exception as e:
        logger.error(f"Error fetching menu versions: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch menu versions")


@router.post("/versions")
@limiter.limit("30/minute")
def create_menu_version(
    request: Request,
    data: MenuVersionCreate,
    venue_id: int = Query(..., description="Venue ID"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create a new version of a menu item (tracks changes)."""
    try:
        from app.models.enhanced_inventory import MenuVersionHistory

        menu_item = db.query(MenuItem).filter(MenuItem.id == data.menu_item_id).first()
        if not menu_item:
            raise HTTPException(status_code=404, detail="Menu item not found")

        version = MenuVersionHistory(
            venue_id=venue_id,
            menu_version_id=data.menu_item_id,
            new_status="updated",
            change_type="updated",
            change_description=data.reason,
            changes_json=data.changes,
            changed_by=current_user.id,
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


@router.post("/versions/{version_id}/restore")
@limiter.limit("30/minute")
def restore_menu_version(
    request: Request,
    version_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Restore a menu item to a previous version."""
    try:
        from app.models.enhanced_inventory import MenuVersionHistory

        version = db.query(MenuVersionHistory).filter(
            MenuVersionHistory.id == version_id
        ).first()

        if not version:
            raise HTTPException(status_code=404, detail="Version not found")

        version.new_status = "restored"
        db.commit()
        return {"status": "success", "message": "Menu item restored to previous version"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error restoring menu version: {e}")
        raise HTTPException(status_code=500, detail="Failed to restore menu version")


@router.get("/schedules")
@limiter.limit("60/minute")
def get_menu_schedules(
    request: Request,
    venue_id: int = Query(1, description="Venue ID"),
    menu_item_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get menu schedules for a venue."""
    try:
        from app.models.enhanced_inventory import MenuSchedule

        query = db.query(MenuSchedule).filter(MenuSchedule.venue_id == venue_id)
        if menu_item_id:
            query = query.filter(MenuSchedule.menu_version_id == menu_item_id)
        return query.all()
    except Exception as e:
        logger.error(f"Error fetching menu schedules: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch menu schedules")


@router.post("/schedules")
@limiter.limit("30/minute")
def create_menu_schedule(
    request: Request,
    venue_id: int,
    data: MenuScheduleCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create a menu schedule (availability windows)."""
    try:
        from app.models.enhanced_inventory import MenuSchedule

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
            is_active=data.is_available,
        )
        db.add(schedule)
        db.commit()
        db.refresh(schedule)
        return schedule
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating menu schedule: {e}")
        raise HTTPException(status_code=500, detail="Failed to create menu schedule")


@router.delete("/schedules/{schedule_id}")
@limiter.limit("30/minute")
def delete_menu_schedule(
    request: Request,
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Delete a menu schedule."""
    try:
        from app.models.enhanced_inventory import MenuSchedule

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


@router.get("/nutrition/{menu_item_id}")
@limiter.limit("60/minute")
def get_menu_nutrition(
    request: Request,
    menu_item_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get nutrition information for a menu item."""
    try:
        from app.models.enhanced_inventory import MenuItemNutrition
        from app.services.inventory_management_service import AdvancedMenuService

        nutrition = db.query(MenuItemNutrition).filter(
            MenuItemNutrition.menu_item_id == menu_item_id
        ).first()

        if not nutrition:
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


@router.post("/nutrition")
@limiter.limit("30/minute")
def create_menu_nutrition(
    request: Request,
    data: MenuNutritionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create/update nutrition information for a menu item."""
    try:
        from app.models.enhanced_inventory import MenuItemNutrition

        nutrition = db.query(MenuItemNutrition).filter(
            MenuItemNutrition.menu_item_id == data.menu_item_id
        ).first()

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
                **{k: v for k, v in nutrition_mapping.items() if v is not None},
            )
            db.add(nutrition)

        db.commit()
        db.refresh(nutrition)
        return nutrition
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating/updating nutrition: {e}")
        raise HTTPException(status_code=500, detail="Failed to save nutrition information")


@router.get("/allergens/{menu_item_id}/details")
@limiter.limit("60/minute")
def get_menu_allergen_details(
    request: Request,
    menu_item_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get allergens for a menu item (aggregated from recipe)."""
    try:
        from app.models.enhanced_inventory import MenuItemAllergen
        from app.services.inventory_management_service import AdvancedMenuService

        allergens = db.query(MenuItemAllergen).filter(
            MenuItemAllergen.menu_item_id == menu_item_id
        ).all()

        service = AdvancedMenuService(db)
        recipe_allergens = service.aggregate_allergens_from_recipe(menu_item_id)

        all_allergens = list(allergens) + recipe_allergens

        return {
            "menu_item_id": menu_item_id,
            "allergens": [
                {
                    "id": a.id,
                    "allergen_type": a.allergen_type,
                    "severity": a.severity,
                    "notes": a.notes,
                    "manually_added": a.manually_added,
                }
                for a in all_allergens
            ],
        }
    except Exception as e:
        logger.error(f"Error fetching allergens: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch allergens")


@router.post("/allergens/item")
@limiter.limit("30/minute")
def create_menu_allergen(
    request: Request,
    data: MenuAllergenCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Add allergen to a menu item."""
    try:
        from app.models.enhanced_inventory import MenuItemAllergen

        allergen = MenuItemAllergen(
            menu_item_id=data.menu_item_id,
            allergen_type=data.allergen_type,
            severity=data.severity,
            notes=data.notes,
            manually_added=True,
        )
        db.add(allergen)
        db.commit()
        db.refresh(allergen)
        return allergen
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating allergen: {e}")
        raise HTTPException(status_code=500, detail="Failed to create allergen")


@router.delete("/allergens/item/{allergen_id}")
@limiter.limit("30/minute")
def delete_menu_allergen(
    request: Request,
    allergen_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Remove allergen from a menu item."""
    try:
        from app.models.enhanced_inventory import MenuItemAllergen

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


@router.get("/bundles/{bundle_item_id}")
@limiter.limit("60/minute")
def get_menu_bundle(
    request: Request,
    bundle_item_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get bundle components for a menu item."""
    try:
        from app.models.enhanced_inventory import MenuItemBundle

        bundles = db.query(MenuItemBundle).filter(
            MenuItemBundle.bundle_item_id == bundle_item_id
        ).all()
        return bundles
    except Exception as e:
        logger.error(f"Error fetching bundle components: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch bundle components")


@router.post("/bundles")
@limiter.limit("30/minute")
def create_menu_bundle(
    request: Request,
    data: MenuBundleCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Add item to a bundle."""
    try:
        from app.models.enhanced_inventory import MenuItemBundle

        bundle = MenuItemBundle(
            bundle_item_id=data.bundle_item_id,
            component_item_id=data.included_item_id,
            quantity=data.quantity,
            is_required=data.is_required,
            price_adjustment=float(data.price_adjustment),
        )
        db.add(bundle)
        db.commit()
        db.refresh(bundle)
        return bundle
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating bundle: {e}")
        raise HTTPException(status_code=500, detail="Failed to create bundle")


@router.post("/bulk-price-update")
@limiter.limit("30/minute")
def bulk_update_menu_prices(
    request: Request,
    venue_id: int,
    data: BulkPriceUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Bulk update menu item prices."""
    try:
        from app.services.inventory_management_service import AdvancedMenuService

        updates = []
        for item_id in data.item_ids:
            item = db.query(MenuItem).filter(
                MenuItem.id == item_id,
            ).first()

            if item and item.price:
                if data.adjustment_type == "percentage":
                    new_price = float(item.price) * (1 + float(data.adjustment_value) / 100)
                else:
                    new_price = float(item.price) + float(data.adjustment_value)

                updates.append({
                    'menu_item_id': item_id,
                    'new_price': max(0, new_price),
                })

        service = AdvancedMenuService(db)
        result = service.bulk_update_prices(
            venue_id=venue_id,
            updates=updates,
            updated_by=current_user.id,
        )

        return {"status": "success", "updated_count": result.get("updated", 0), "errors": result.get("errors", [])}
    except Exception as e:
        db.rollback()
        logger.error(f"Error bulk updating prices: {e}")
        raise HTTPException(status_code=500, detail="Failed to bulk update prices")

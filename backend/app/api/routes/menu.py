"""Menu API routes - frontend-facing /menu/* endpoints.

Provides proxy/alias endpoints for menu management features
that the frontend expects under the /menu prefix.
"""

from typing import Optional, List
from decimal import Decimal
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import func

from app.core.rate_limit import limiter
from app.db.session import DbSession
from app.models.restaurant import (
    MenuItem, ModifierGroup, ModifierOption, MenuItemModifierGroup,
    ComboMeal, ComboItem, MenuCategory,
)

router = APIRouter()


# ==================== MODIFIERS ====================

@router.get("/modifiers")
@limiter.limit("60/minute")
def get_menu_modifiers(request: Request, db: DbSession):
    """Get modifier groups with their options."""
    groups = db.query(ModifierGroup).order_by(ModifierGroup.sort_order, ModifierGroup.name).all()

    results = []
    for group in groups:
        options = db.query(ModifierOption).filter(
            ModifierOption.group_id == group.id,
        ).order_by(ModifierOption.sort_order).all()

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
        "total": len(results),
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

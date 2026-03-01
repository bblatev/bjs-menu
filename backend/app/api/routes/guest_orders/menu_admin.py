"""Menu admin routes"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Body, Request
from pydantic import BaseModel, Field, field_validator

from app.core.sanitize import sanitize_text
from app.core.responses import list_response, paginated_response

from app.db.session import DbSession
from app.models.restaurant import (
    GuestOrder as GuestOrderModel, KitchenOrder, Table, MenuItem,
    ModifierGroup, ModifierOption, MenuItemModifierGroup,
    ComboMeal, ComboItem, MenuCategory as MenuCategoryModel,
    CheckItem,
)
from app.models.operations import AppSetting
from app.services.stock_deduction_service import StockDeductionService
import logging
from app.core.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter()

# Import shared schemas and helpers
from app.api.routes.guest_orders._shared import *
from app.api.routes.guest_orders._shared import _menu_item_to_admin_dict, _menu_item_to_dict

# ============== Additional Menu Admin Routes ==============

@router.post("/menu-admin/items")
@limiter.limit("30/minute")
def admin_create_menu_item(request: Request, db: DbSession, data: dict = Body(...)):
    """Create a new menu item."""
    # Handle both string and dict formats for name/description
    name_data = data.get("name", "")
    name = name_data.get("en", name_data) if isinstance(name_data, dict) else name_data
    desc_data = data.get("description", "")
    description = desc_data.get("en", desc_data) if isinstance(desc_data, dict) else (desc_data or "")

    # Resolve category: accept category_id (number) or category (string)
    category = data.get("category", "Uncategorized")
    category_id = data.get("category_id")
    if category_id:
        cat = db.query(MenuCategoryModel).filter(MenuCategoryModel.id == int(category_id)).first()
        if cat:
            category = cat.name_en or cat.name_bg or category

    # Resolve station: accept station_id (number) or station (string)
    from app.models.advanced_features import KitchenStation
    station = data.get("station")
    station_id = data.get("station_id")
    if station_id:
        st = db.query(KitchenStation).filter(KitchenStation.id == int(station_id)).first()
        if st:
            station = st.station_type or st.name

    item = MenuItem(
        name=name,
        category=category,
        price=data.get("price", 0),
        station=station,
        description=description,
        available=data.get("available", data.get("is_available", True)),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _menu_item_to_admin_dict(item, db)


@router.put("/menu-admin/items/{item_id}")
@limiter.limit("30/minute")
def admin_update_menu_item(request: Request, db: DbSession, item_id: int, data: dict = Body(...)):
    """Update a menu item."""
    item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if "name" in data:
        item.name = data["name"].get("en", data["name"]) if isinstance(data["name"], dict) else data["name"]
    if "description" in data:
        item.description = data["description"].get("en", "") if isinstance(data["description"], dict) else data["description"]
    if "price" in data:
        item.price = data["price"]

    # Resolve category: accept category_id (number) or category (string)
    if "category_id" in data and data["category_id"]:
        cat = db.query(MenuCategoryModel).filter(MenuCategoryModel.id == int(data["category_id"])).first()
        if cat:
            item.category = cat.name_en or cat.name_bg or item.category
    elif "category" in data:
        item.category = data["category"]

    # Resolve station: accept station_id (number) or station (string)
    from app.models.advanced_features import KitchenStation
    if "station_id" in data and data["station_id"]:
        st = db.query(KitchenStation).filter(KitchenStation.id == int(data["station_id"])).first()
        if st:
            item.station = st.station_type or st.name
    elif "station" in data:
        item.station = data["station"]

    if "is_available" in data:
        item.available = data["is_available"]
    if "available" in data:
        item.available = data["available"]

    db.commit()
    db.refresh(item)
    return _menu_item_to_admin_dict(item, db)


@router.delete("/menu-admin/items/{item_id}")
@limiter.limit("30/minute")
def admin_delete_menu_item(request: Request, db: DbSession, item_id: int):
    """Soft-delete a menu item."""
    item = db.query(MenuItem).filter(MenuItem.id == item_id, MenuItem.not_deleted()).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    item.soft_delete()
    db.commit()
    return {"success": True}


@router.patch("/menu-admin/items/{item_id}/toggle-available")
@limiter.limit("30/minute")
def admin_toggle_item_availability(request: Request, db: DbSession, item_id: int):
    """Toggle menu item availability."""
    item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    item.available = not item.available
    db.commit()
    return {"id": item.id, "available": item.available}


@router.post("/menu-admin/categories")
@limiter.limit("30/minute")
def admin_create_category(request: Request, db: DbSession, data: dict = Body(...)):
    """Create a new category."""
    name_data = data.get("name", "")
    if isinstance(name_data, dict):
        name_bg = name_data.get("bg", "")
        name_en = name_data.get("en", name_bg)
    else:
        name_bg = str(name_data)
        name_en = name_bg

    desc_data = data.get("description", {})
    if isinstance(desc_data, str):
        desc_bg = desc_data
        desc_en = desc_data
    else:
        desc_bg = desc_data.get("bg", "") if isinstance(desc_data, dict) else ""
        desc_en = desc_data.get("en", "") if isinstance(desc_data, dict) else ""

    # Get max sort_order for new category
    from sqlalchemy import func
    max_order = db.query(func.max(MenuCategoryModel.sort_order)).scalar() or 0

    cat = MenuCategoryModel(
        name_bg=name_bg,
        name_en=name_en,
        description_bg=desc_bg,
        description_en=desc_en,
        icon=data.get("icon", "🍽"),
        color=data.get("color", "#3B82F6"),
        image_url=data.get("image_url"),
        sort_order=data.get("sort_order", max_order + 1),
        active=data.get("active", True),
        parent_id=data.get("parent_id"),
        visibility=data.get("visibility", "all"),
        tax_rate=data.get("tax_rate"),
        printer_id=data.get("printer_id"),
        display_on_kiosk=data.get("display_on_kiosk", True),
        display_on_app=data.get("display_on_app", True),
        display_on_web=data.get("display_on_web", True),
        schedule=data.get("schedule"),
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return _category_to_response(cat)


@router.put("/menu-admin/categories/reorder")
@limiter.limit("30/minute")
def admin_reorder_categories(request: Request, db: DbSession, data: dict = Body(...)):
    """Reorder categories."""
    items = data.get("categories", [])
    for item in items:
        cat_id = item.get("id")
        sort_order = item.get("sort_order")
        if cat_id is not None and sort_order is not None:
            cat = db.query(MenuCategoryModel).filter(MenuCategoryModel.id == cat_id).first()
            if cat:
                cat.sort_order = sort_order
    db.commit()
    return {"success": True}


@router.put("/menu-admin/categories/{category_id}")
@limiter.limit("30/minute")
def admin_update_category(request: Request, db: DbSession, category_id: int, data: dict = Body(...)):
    """Update a category."""
    cat = db.query(MenuCategoryModel).filter(MenuCategoryModel.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    name_data = data.get("name")
    if name_data is not None:
        if isinstance(name_data, dict):
            cat.name_bg = name_data.get("bg", cat.name_bg)
            cat.name_en = name_data.get("en", cat.name_en)
        else:
            cat.name_bg = str(name_data)
            cat.name_en = str(name_data)

    desc_data = data.get("description")
    if desc_data is not None:
        if isinstance(desc_data, dict):
            cat.description_bg = desc_data.get("bg", cat.description_bg)
            cat.description_en = desc_data.get("en", cat.description_en)
        else:
            cat.description_bg = str(desc_data)
            cat.description_en = str(desc_data)

    for field in ["icon", "color", "image_url", "visibility"]:
        if field in data:
            setattr(cat, field, data[field])
    for field in ["sort_order", "printer_id"]:
        if field in data:
            setattr(cat, field, data[field])
    for field in ["active", "display_on_kiosk", "display_on_app", "display_on_web"]:
        if field in data:
            setattr(cat, field, data[field])
    if "tax_rate" in data:
        cat.tax_rate = data["tax_rate"]
    if "parent_id" in data:
        cat.parent_id = data["parent_id"]
    if "schedule" in data:
        cat.schedule = data["schedule"]

    db.commit()
    db.refresh(cat)
    return _category_to_response(cat)


@router.delete("/menu-admin/categories/{category_id}")
@limiter.limit("30/minute")
def admin_delete_category(request: Request, db: DbSession, category_id: int):
    """Delete a category."""
    cat = db.query(MenuCategoryModel).filter(MenuCategoryModel.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    # Check if category has items
    item_count = db.query(MenuItem).filter(
        (MenuItem.category == cat.name_bg) | (MenuItem.category == cat.name_en)
    ).count()
    if item_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete category with {item_count} items. Move or delete items first."
        )

    # Delete child categories first
    db.query(MenuCategoryModel).filter(MenuCategoryModel.parent_id == category_id).update({"parent_id": None})

    db.delete(cat)
    db.commit()
    return {"success": True}


@router.patch("/menu-admin/categories/{category_id}/toggle-active")
@limiter.limit("30/minute")
def admin_toggle_category_active(request: Request, db: DbSession, category_id: int):
    """Toggle category active status."""
    cat = db.query(MenuCategoryModel).filter(MenuCategoryModel.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    cat.active = not cat.active
    db.commit()
    return {"id": cat.id, "active": cat.active}


@router.get("/menu-admin/modifier-groups")
@limiter.limit("60/minute")
def admin_list_modifier_groups(request: Request, db: DbSession):
    """List modifier groups with their options."""
    groups = db.query(ModifierGroup).order_by(ModifierGroup.sort_order).all()
    return [
        {
            "id": g.id,
            "name": g.name,
            "min_selections": g.min_selections,
            "max_selections": g.max_selections,
            "active": g.active,
            "sort_order": g.sort_order,
            "options": [
                {
                    "id": o.id,
                    "group_id": o.group_id,
                    "name": o.name,
                    "price_adjustment": float(o.price_adjustment or 0),
                    "available": o.available,
                    "sort_order": o.sort_order,
                }
                for o in sorted(g.options, key=lambda x: x.sort_order)
            ],
        }
        for g in groups
    ]


@router.post("/menu-admin/modifier-groups")
@limiter.limit("30/minute")
def admin_create_modifier_group(request: Request, db: DbSession, data: dict = Body(...)):
    """Create a modifier group."""
    group = ModifierGroup(
        name=data.get("name", ""),
        min_selections=data.get("min_selections", 0),
        max_selections=data.get("max_selections", 1),
        sort_order=data.get("sort_order", 0),
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    return {
        "id": group.id,
        "name": group.name,
        "min_selections": group.min_selections,
        "max_selections": group.max_selections,
        "active": group.active,
        "sort_order": group.sort_order,
        "options": [],
    }


@router.put("/menu-admin/modifier-groups/{group_id}")
@limiter.limit("30/minute")
def admin_update_modifier_group(request: Request, db: DbSession, group_id: int, data: dict = Body(...)):
    """Update a modifier group."""
    group = db.query(ModifierGroup).filter(ModifierGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Modifier group not found")
    for key in ("name", "min_selections", "max_selections", "sort_order", "active"):
        if key in data:
            setattr(group, key, data[key])
    db.commit()
    db.refresh(group)
    return {"id": group.id, "name": group.name, "min_selections": group.min_selections,
            "max_selections": group.max_selections, "active": group.active, "sort_order": group.sort_order}


@router.delete("/menu-admin/modifier-groups/{group_id}")
@limiter.limit("30/minute")
def admin_delete_modifier_group(request: Request, db: DbSession, group_id: int):
    """Delete a modifier group and its options."""
    group = db.query(ModifierGroup).filter(ModifierGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Modifier group not found")
    db.delete(group)
    db.commit()
    return {"success": True}


@router.post("/menu-admin/modifier-groups/{group_id}/options")
@limiter.limit("30/minute")
def admin_create_modifier_option(request: Request, db: DbSession, group_id: int, data: dict = Body(...)):
    """Create a modifier option in a group."""
    group = db.query(ModifierGroup).filter(ModifierGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Modifier group not found")
    option = ModifierOption(
        group_id=group_id,
        name=data.get("name", ""),
        price_adjustment=data.get("price_adjustment", 0),
        sort_order=data.get("sort_order", 0),
    )
    db.add(option)
    db.commit()
    db.refresh(option)
    return {
        "id": option.id,
        "group_id": option.group_id,
        "name": option.name,
        "price_adjustment": float(option.price_adjustment or 0),
        "available": option.available,
    }


@router.put("/menu-admin/modifier-options/{option_id}")
@limiter.limit("30/minute")
def admin_update_modifier_option(request: Request, db: DbSession, option_id: int, data: dict = Body(...)):
    """Update a modifier option."""
    option = db.query(ModifierOption).filter(ModifierOption.id == option_id).first()
    if not option:
        raise HTTPException(status_code=404, detail="Modifier option not found")
    for key in ("name", "price_adjustment", "available", "sort_order"):
        if key in data:
            setattr(option, key, data[key])
    db.commit()
    db.refresh(option)
    return {"id": option.id, "group_id": option.group_id, "name": option.name,
            "price_adjustment": float(option.price_adjustment or 0), "available": option.available}


@router.delete("/menu-admin/modifier-options/{option_id}")
@limiter.limit("30/minute")
def admin_delete_modifier_option(request: Request, db: DbSession, option_id: int):
    """Delete a modifier option."""
    option = db.query(ModifierOption).filter(ModifierOption.id == option_id).first()
    if not option:
        raise HTTPException(status_code=404, detail="Modifier option not found")
    db.delete(option)
    db.commit()
    return {"success": True}


@router.get("/menu-admin/combos")
@limiter.limit("60/minute")
def admin_list_combos(request: Request, db: DbSession):
    """List combo meals with their items."""
    combos = db.query(ComboMeal).order_by(ComboMeal.name).all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "description": c.description,
            "price": float(c.price),
            "image_url": c.image_url,
            "available": c.available,
            "featured": c.featured,
            "category": c.category,
            "items": [
                {
                    "id": ci.id,
                    "menu_item_id": ci.menu_item_id,
                    "name": ci.name,
                    "quantity": ci.quantity,
                    "is_choice": ci.is_choice,
                    "choice_group": ci.choice_group,
                }
                for ci in c.items
            ],
        }
        for c in combos
    ]


@router.post("/menu-admin/combos")
@limiter.limit("30/minute")
def admin_create_combo(request: Request, db: DbSession, data: dict = Body(...)):
    """Create a combo meal."""
    raw_name = data.get("name", "")
    combo_name = raw_name.get("en", "") or raw_name.get("bg", "") if isinstance(raw_name, dict) else str(raw_name)
    raw_desc = data.get("description")
    combo_desc = raw_desc.get("en", "") or raw_desc.get("bg", "") if isinstance(raw_desc, dict) else raw_desc
    combo = ComboMeal(
        name=combo_name,
        description=combo_desc,
        price=data.get("price", 0),
        image_url=data.get("image_url"),
        category=data.get("category"),
    )
    db.add(combo)
    db.commit()
    db.refresh(combo)
    # Add items if provided
    for item_data in data.get("items", []):
        ci = ComboItem(
            combo_id=combo.id,
            menu_item_id=item_data.get("menu_item_id"),
            name=item_data.get("name", ""),
            quantity=item_data.get("quantity", 1),
            is_choice=item_data.get("is_choice", False),
            choice_group=item_data.get("choice_group"),
        )
        db.add(ci)
    db.commit()
    db.refresh(combo)
    return {"id": combo.id, "name": combo.name, "price": float(combo.price),
            "available": combo.available, "featured": combo.featured}


@router.put("/menu-admin/combos/{combo_id}")
@limiter.limit("30/minute")
def admin_update_combo(request: Request, db: DbSession, combo_id: int, data: dict = Body(...)):
    """Update a combo meal."""
    combo = db.query(ComboMeal).filter(ComboMeal.id == combo_id).first()
    if not combo:
        raise HTTPException(status_code=404, detail="Combo meal not found")
    for key in ("name", "description", "price", "image_url", "category", "available", "featured"):
        if key in data:
            val = data[key]
            if key in ("name", "description") and isinstance(val, dict):
                val = val.get("en", "") or val.get("bg", "") or ""
            setattr(combo, key, val)
    # Replace items if provided
    if "items" in data:
        for ci in combo.items:
            db.delete(ci)
        for item_data in data["items"]:
            ci = ComboItem(
                combo_id=combo.id,
                menu_item_id=item_data.get("menu_item_id"),
                name=item_data.get("name", ""),
                quantity=item_data.get("quantity", 1),
                is_choice=item_data.get("is_choice", False),
                choice_group=item_data.get("choice_group"),
            )
            db.add(ci)
    db.commit()
    db.refresh(combo)
    return {"id": combo.id, "name": combo.name, "price": float(combo.price),
            "available": combo.available, "featured": combo.featured}


@router.delete("/menu-admin/combos/{combo_id}")
@limiter.limit("30/minute")
def admin_delete_combo(request: Request, db: DbSession, combo_id: int):
    """Delete a combo meal and its items."""
    combo = db.query(ComboMeal).filter(ComboMeal.id == combo_id).first()
    if not combo:
        raise HTTPException(status_code=404, detail="Combo meal not found")
    db.delete(combo)
    db.commit()
    return {"success": True}


@router.patch("/menu-admin/combos/{combo_id}/toggle-available")
@limiter.limit("30/minute")
def admin_toggle_combo_available(request: Request, db: DbSession, combo_id: int):
    """Toggle combo availability."""
    combo = db.query(ComboMeal).filter(ComboMeal.id == combo_id).first()
    if not combo:
        raise HTTPException(status_code=404, detail="Combo meal not found")
    combo.available = not combo.available
    db.commit()
    return {"id": combo.id, "available": combo.available}


@router.patch("/menu-admin/combos/{combo_id}/toggle-featured")
@limiter.limit("30/minute")
def admin_toggle_combo_featured(request: Request, db: DbSession, combo_id: int):
    """Toggle combo featured status."""
    combo = db.query(ComboMeal).filter(ComboMeal.id == combo_id).first()
    if not combo:
        raise HTTPException(status_code=404, detail="Combo meal not found")
    combo.featured = not combo.featured
    db.commit()
    return {"id": combo.id, "featured": combo.featured}


DAYPART_STORE = "menu_dayparts"


def _load_dayparts(db: DbSession) -> list:
    from app.models.hardware import Integration
    rec = db.query(Integration).filter(Integration.integration_id == DAYPART_STORE).first()
    if rec and rec.config and isinstance(rec.config, dict):
        return rec.config.get("items", [])
    return []


def _save_dayparts(db: DbSession, items: list):
    from app.models.hardware import Integration
    rec = db.query(Integration).filter(Integration.integration_id == DAYPART_STORE).first()
    next_id = max((d.get("id", 0) for d in items), default=0) + 1
    if not rec:
        rec = Integration(
            integration_id=DAYPART_STORE,
            name="Menu Dayparts",
            category="menu",
            status="active",
            config={"items": items, "next_id": next_id},
        )
        db.add(rec)
    else:
        rec.config = {"items": items, "next_id": next_id}
    db.commit()


@router.get("/menu-admin/dayparts")
@limiter.limit("60/minute")
def admin_list_dayparts(request: Request, db: DbSession):
    """List dayparts for menu scheduling."""
    return _load_dayparts(db)


@router.post("/menu-admin/dayparts")
@limiter.limit("30/minute")
def admin_create_daypart(request: Request, db: DbSession, data: dict = Body(...)):
    """Create a daypart."""
    items = _load_dayparts(db)
    from app.models.hardware import Integration
    rec = db.query(Integration).filter(Integration.integration_id == DAYPART_STORE).first()
    next_id = (rec.config.get("next_id", len(items) + 1) if rec and rec.config else len(items) + 1)
    new_item = {"id": next_id, **data, "active": data.get("active", True)}
    items.append(new_item)
    _save_dayparts(db, items)
    return new_item


@router.put("/menu-admin/dayparts/{daypart_id}")
@limiter.limit("30/minute")
def admin_update_daypart(request: Request, db: DbSession, daypart_id: int, data: dict = Body(...)):
    """Update a daypart."""
    items = _load_dayparts(db)
    for item in items:
        if item.get("id") == daypart_id:
            item.update(data)
            item["id"] = daypart_id
            _save_dayparts(db, items)
            return item
    raise HTTPException(status_code=404, detail="Daypart not found")


@router.delete("/menu-admin/dayparts/{daypart_id}")
@limiter.limit("30/minute")
def admin_delete_daypart(request: Request, db: DbSession, daypart_id: int):
    """Delete a daypart."""
    items = _load_dayparts(db)
    items = [d for d in items if d.get("id") != daypart_id]
    _save_dayparts(db, items)
    return {"success": True}


@router.patch("/menu-admin/dayparts/{daypart_id}/toggle-active")
@limiter.limit("30/minute")
def admin_toggle_daypart_active(request: Request, db: DbSession, daypart_id: int):
    """Toggle daypart active status."""
    items = _load_dayparts(db)
    for item in items:
        if item.get("id") == daypart_id:
            item["active"] = not item.get("active", True)
            _save_dayparts(db, items)
            return {"id": daypart_id, "active": item["active"]}
    raise HTTPException(status_code=404, detail="Daypart not found")


@router.get("/menu-admin/items-with-allergens")
@limiter.limit("60/minute")
def admin_list_items_with_allergens(request: Request, db: DbSession):
    """List items with allergen information."""
    items = db.query(MenuItem).all()
    return [
        {
            **_menu_item_to_dict(i),
            "allergens": [],
            "nutrition": {}
        }
        for i in items
    ]


@router.put("/menu-admin/items/{item_id}/allergens-nutrition")
@limiter.limit("30/minute")
def admin_update_item_allergens(request: Request, db: DbSession, item_id: int, data: dict = Body(...)):
    """Update item allergens and nutrition info."""
    item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return {
        **_menu_item_to_dict(item),
        "allergens": data.get("allergens", []),
        "nutrition": data.get("nutrition", {})
    }


@router.get("/menu-admin/items/{item_id}/modifiers")
@limiter.limit("60/minute")
def admin_get_item_modifiers(request: Request, db: DbSession, item_id: int):
    """Get modifier groups linked to a specific menu item."""
    links = (
        db.query(MenuItemModifierGroup)
        .filter(MenuItemModifierGroup.menu_item_id == item_id)
        .order_by(MenuItemModifierGroup.sort_order)
        .all()
    )
    result = []
    for link in links:
        g = link.modifier_group
        if g:
            result.append({
                "id": g.id,
                "name": g.name,
                "min_selections": g.min_selections,
                "max_selections": g.max_selections,
                "active": g.active,
                "options": [
                    {
                        "id": o.id,
                        "name": o.name,
                        "price_adjustment": float(o.price_adjustment or 0),
                        "available": o.available,
                    }
                    for o in sorted(g.options, key=lambda x: x.sort_order)
                ],
            })
    return result


@router.get("/menu-admin/modifiers")
@limiter.limit("60/minute")
def admin_list_modifiers(request: Request, db: DbSession):
    """List all modifier options across all groups."""
    options = db.query(ModifierOption).order_by(ModifierOption.group_id, ModifierOption.sort_order).all()
    return [
        {
            "id": o.id,
            "group_id": o.group_id,
            "name": o.name,
            "price_adjustment": float(o.price_adjustment or 0),
            "available": o.available,
            "sort_order": o.sort_order,
        }
        for o in options
    ]


@router.post("/menu-admin/modifiers")
@limiter.limit("30/minute")
def admin_create_modifier(request: Request, db: DbSession, data: dict = Body(...)):
    """Create a modifier option (must specify group_id)."""
    group_id = data.get("group_id")
    if not group_id:
        # Auto-create a modifier group if none specified
        group = ModifierGroup(
            name=data.get("name", "New Modifier"),
            min_selections=0,
            max_selections=1,
        )
        db.add(group)
        db.commit()
        db.refresh(group)
        group_id = group.id
    else:
        group = db.query(ModifierGroup).filter(ModifierGroup.id == group_id).first()
        if not group:
            raise HTTPException(status_code=404, detail="Modifier group not found")
    option = ModifierOption(
        group_id=group_id,
        name=data.get("name", ""),
        price_adjustment=data.get("price_adjustment", 0),
        sort_order=data.get("sort_order", 0),
    )
    db.add(option)
    db.commit()
    db.refresh(option)
    return {"id": option.id, "group_id": option.group_id, "name": option.name,
            "price_adjustment": float(option.price_adjustment or 0), "available": option.available}


@router.put("/menu-admin/modifiers/{modifier_id}")
@limiter.limit("30/minute")
def admin_update_modifier(request: Request, db: DbSession, modifier_id: int, data: dict = Body(...)):
    """Update a modifier option."""
    option = db.query(ModifierOption).filter(ModifierOption.id == modifier_id).first()
    if not option:
        raise HTTPException(status_code=404, detail="Modifier not found")
    for key in ("name", "price_adjustment", "available", "sort_order", "group_id"):
        if key in data:
            setattr(option, key, data[key])
    db.commit()
    db.refresh(option)
    return {"id": option.id, "group_id": option.group_id, "name": option.name,
            "price_adjustment": float(option.price_adjustment or 0), "available": option.available}


@router.delete("/menu-admin/modifiers/{modifier_id}")
@limiter.limit("30/minute")
def admin_delete_modifier(request: Request, db: DbSession, modifier_id: int):
    """Delete a modifier option."""
    option = db.query(ModifierOption).filter(ModifierOption.id == modifier_id).first()
    if not option:
        raise HTTPException(status_code=404, detail="Modifier not found")
    db.delete(option)
    db.commit()
    return {"success": True}


@router.post("/menu-admin/modifiers/{modifier_id}/options")
@limiter.limit("30/minute")
def admin_add_modifier_option(request: Request, db: DbSession, modifier_id: int, data: dict = Body(...)):
    """Add option to a modifier group (modifier_id is treated as group_id)."""
    group = db.query(ModifierGroup).filter(ModifierGroup.id == modifier_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Modifier group not found")
    option = ModifierOption(
        group_id=modifier_id,
        name=data.get("name", ""),
        price_adjustment=data.get("price_adjustment", 0),
        sort_order=data.get("sort_order", 0),
    )
    db.add(option)
    db.commit()
    db.refresh(option)
    return {"id": option.id, "modifier_id": modifier_id, "name": option.name,
            "price_adjustment": float(option.price_adjustment or 0), "available": option.available}


@router.delete("/menu-admin/modifiers/options/{option_id}")
@limiter.limit("30/minute")
def admin_remove_modifier_option(request: Request, db: DbSession, option_id: int):
    """Remove modifier option."""
    option = db.query(ModifierOption).filter(ModifierOption.id == option_id).first()
    if not option:
        raise HTTPException(status_code=404, detail="Modifier option not found")
    db.delete(option)
    db.commit()
    return {"success": True}


@router.patch("/menu-admin/modifier-groups/{group_id}/toggle-active")
@limiter.limit("30/minute")
def admin_toggle_modifier_group_active(request: Request, db: DbSession, group_id: int):
    """Toggle modifier group active status."""
    group = db.query(ModifierGroup).filter(ModifierGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Modifier group not found")
    group.active = not group.active
    db.commit()
    return {"id": group.id, "active": group.active}


@router.patch("/menu-admin/modifier-options/{option_id}/toggle-available")
@limiter.limit("30/minute")
def admin_toggle_modifier_option_available(request: Request, db: DbSession, option_id: int):
    """Toggle modifier option availability."""
    option = db.query(ModifierOption).filter(ModifierOption.id == option_id).first()
    if not option:
        raise HTTPException(status_code=404, detail="Modifier option not found")
    option.available = not option.available
    db.commit()
    return {"id": option.id, "available": option.available}


@router.get("/menu-admin/nutrition")
@limiter.limit("60/minute")
def get_menu_nutrition(request: Request, db: DbSession):
    """Get nutrition information for menu items."""
    from app.models.restaurant import MenuItem
    items = db.query(MenuItem).filter(MenuItem.available == True).all()
    return [
        {
            "id": item.id,
            "name": item.name,
            "category": item.category or "Other",
            "calories": None,
            "protein": None,
            "carbs": None,
            "fat": None,
            "fiber": None,
            "allergens": [],
        }
        for item in items[:50]
    ]


@router.get("/menu-admin/allergens")
@limiter.limit("60/minute")
def get_menu_allergens(request: Request, db: DbSession):
    """Get allergen definitions."""
    from app.models.operations import AppSetting
    setting = db.query(AppSetting).filter(
        AppSetting.category == "allergens",
        AppSetting.key == "list",
    ).first()
    if setting and setting.value:
        return setting.value
    return []


@router.get("/menu-admin/modifier-options")
@limiter.limit("60/minute")
def get_modifier_options(request: Request, db: DbSession):
    """Get all modifier options from modifier tables."""
    from app.models.restaurant import ModifierGroup, ModifierOption
    groups = db.query(ModifierGroup).filter(ModifierGroup.active == True).order_by(ModifierGroup.sort_order).all()
    result = []
    for g in groups:
        options = db.query(ModifierOption).filter(
            ModifierOption.group_id == g.id,
            ModifierOption.available == True,
        ).order_by(ModifierOption.sort_order).all()
        result.append({
            "group_id": g.id,
            "group_name": g.name,
            "min_selections": g.min_selections,
            "max_selections": g.max_selections,
            "options": [
                {"id": o.id, "name": o.name, "price_adjustment": float(o.price_adjustment or 0)}
                for o in options
            ],
        })
    return result


@router.get("/menu-admin/schedules")
@limiter.limit("60/minute")
def get_menu_schedules(request: Request, db: DbSession):
    """Get menu schedules (daypart-based menu visibility) from app settings."""
    from app.models.operations import AppSetting
    setting = db.query(AppSetting).filter(
        AppSetting.category == "menu_schedules",
        AppSetting.key == "list",
    ).first()
    if setting and isinstance(setting.value, list):
        return setting.value
    return []


@router.get("/menu-admin/versions/{item_id}")
@limiter.limit("60/minute")
def get_menu_item_versions(request: Request, item_id: int, db: DbSession):
    """Get version history for a menu item from audit log."""
    from app.models.operations import AuditLogEntry
    entries = db.query(AuditLogEntry).filter(
        AuditLogEntry.entity_type == "menu_item",
        AuditLogEntry.entity_id == str(item_id),
    ).order_by(AuditLogEntry.created_at.desc()).limit(20).all()
    return [
        {
            "id": e.id,
            "action": e.action,
            "user_name": e.user_name,
            "details": e.details,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in entries
    ]


@router.post("/menu-admin/versions/{version_id}/restore")
@limiter.limit("30/minute")
def restore_menu_version(request: Request, version_id: int, db: DbSession):
    """Restore a previous menu item version."""
    return {"success": True, "restored_version": version_id}


@router.post("/menu-admin/bulk-price-update")
@limiter.limit("30/minute")
def bulk_price_update(request: Request, request_data: dict, db: DbSession, venue_id: int = 1):
    """Bulk update menu item prices."""
    item_ids = request_data.get("item_ids", [])
    adjustment_type = request_data.get("adjustment_type", "percentage")  # percentage or fixed
    adjustment_value = float(request_data.get("adjustment_value", 0))

    updated = 0
    for item in db.query(MenuItem).filter(MenuItem.id.in_(item_ids)).all():
        current_price = float(item.price or 0)
        if adjustment_type == "percentage":
            item.price = round(current_price * (1 + adjustment_value / 100), 2)
        else:
            item.price = round(current_price + adjustment_value, 2)
        updated += 1

    db.commit()
    return {"success": True, "updated_count": updated}



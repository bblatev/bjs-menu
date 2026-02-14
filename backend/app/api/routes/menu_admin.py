"""Menu Admin API routes - CRUD operations for categories and menu items."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from typing import List, Optional, Dict
from datetime import datetime
from pydantic import BaseModel, Field

from app.db.session import DbSession
from app.core.rbac import CurrentUser, OptionalCurrentUser
from app.core.rate_limit import limiter
from app.models.restaurant import MenuItem, MenuCategory, ModifierGroup, ModifierOption

router = APIRouter()


# ==================== SCHEMAS ====================

class CategoryCreate(BaseModel):
    name_bg: str = ""
    name_en: str = ""
    description: Optional[str] = None
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    name_bg: Optional[str] = None
    name_en: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None
    active: Optional[bool] = None


class CategoryResponse(BaseModel):
    id: int
    name_bg: Optional[str] = None
    name_en: Optional[str] = None
    description: Optional[str] = None
    sort_order: int
    active: bool


class MenuItemCreate(BaseModel):
    category: Optional[str] = None
    name: str
    description: Optional[str] = None
    price: float = Field(..., gt=0)
    sort_order: int = 0
    available: bool = True
    allergens: Optional[List[str]] = None
    station: Optional[str] = None
    prep_time_minutes: Optional[int] = None


class MenuItemUpdate(BaseModel):
    category: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    sort_order: Optional[int] = None
    available: Optional[bool] = None
    allergens: Optional[List[str]] = None
    station: Optional[str] = None
    prep_time_minutes: Optional[int] = None


class MenuItemResponse(BaseModel):
    id: int
    category: Optional[str] = None
    name: str
    description: Optional[str] = None
    price: float
    sort_order: int = 0
    available: bool
    allergens: Optional[List[str]] = None
    station: Optional[str] = None
    prep_time_minutes: Optional[int] = None


class ModifierOptionCreateSchema(BaseModel):
    name: str
    price_adjustment: float = 0.0
    sort_order: int = 0
    available: bool = True


class ModifierOptionUpdateSchema(BaseModel):
    name: Optional[str] = None
    price_adjustment: Optional[float] = None
    sort_order: Optional[int] = None
    available: Optional[bool] = None


class ModifierGroupCreateSchema(BaseModel):
    name: str
    min_selections: int = 0
    max_selections: int = 1
    sort_order: int = 0


class ModifierGroupUpdateSchema(BaseModel):
    name: Optional[str] = None
    min_selections: Optional[int] = None
    max_selections: Optional[int] = None
    sort_order: Optional[int] = None


# ==================== CATEGORIES ====================

@router.get("/categories", response_model=List[CategoryResponse])
@limiter.limit("60/minute")
def list_categories(request: Request, db: DbSession, current_user: OptionalCurrentUser = None):
    """List all menu categories."""
    categories = db.query(MenuCategory).filter(
        MenuCategory.active == True,
    ).order_by(MenuCategory.sort_order).all()

    return [
        CategoryResponse(
            id=c.id,
            name_bg=c.name_bg,
            name_en=c.name_en,
            description=None,
            sort_order=c.sort_order,
            active=c.active,
        )
        for c in categories
    ]


@router.post("/categories", response_model=CategoryResponse, status_code=201)
@limiter.limit("30/minute")
def create_category(request: Request, data: CategoryCreate, db: DbSession, current_user: CurrentUser = None):
    """Create new menu category (manager only)."""
    category = MenuCategory(
        name_bg=data.name_bg,
        name_en=data.name_en,
        sort_order=data.sort_order,
        active=True,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return CategoryResponse(
        id=category.id, name_bg=category.name_bg, name_en=category.name_en,
        description=None, sort_order=category.sort_order, active=category.active,
    )


@router.put("/categories/{category_id}", response_model=CategoryResponse)
@limiter.limit("30/minute")
def update_category(request: Request, category_id: int, data: CategoryUpdate, db: DbSession, current_user: CurrentUser = None):
    """Update menu category (manager only)."""
    category = db.query(MenuCategory).filter(MenuCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    if data.name_bg is not None:
        category.name_bg = data.name_bg
    if data.name_en is not None:
        category.name_en = data.name_en
    if data.sort_order is not None:
        category.sort_order = data.sort_order
    if data.active is not None:
        category.active = data.active

    db.commit()
    db.refresh(category)
    return CategoryResponse(
        id=category.id, name_bg=category.name_bg, name_en=category.name_en,
        description=None, sort_order=category.sort_order, active=category.active,
    )


@router.delete("/categories/{category_id}", status_code=204)
@limiter.limit("30/minute")
def delete_category(request: Request, category_id: int, db: DbSession, current_user: CurrentUser = None):
    """Delete menu category (manager only)."""
    category = db.query(MenuCategory).filter(MenuCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    items_count = db.query(MenuItem).filter(MenuItem.category == category.name_en).count()
    if items_count > 0:
        raise HTTPException(status_code=400, detail=f"Cannot delete category with {items_count} items. Delete items first.")

    db.delete(category)
    db.commit()
    return None


# ==================== MENU ITEMS ====================

@router.get("/items", response_model=List[MenuItemResponse])
@limiter.limit("60/minute")
def list_items(request: Request, db: DbSession, current_user: OptionalCurrentUser = None, category: Optional[str] = None):
    """List all menu items, optionally filtered by category."""
    query = db.query(MenuItem).filter(MenuItem.not_deleted())

    if category:
        query = query.filter(MenuItem.category == category)

    items = query.order_by(MenuItem.category, MenuItem.name).all()
    return [
        MenuItemResponse(
            id=item.id, category=item.category, name=item.name,
            description=item.description, price=float(item.price),
            sort_order=0, available=item.available,
            allergens=item.allergens if isinstance(item.allergens, list) else [],
            station=item.station, prep_time_minutes=item.prep_time_minutes,
        )
        for item in items
    ]


@router.get("/items/{item_id}", response_model=MenuItemResponse)
@limiter.limit("60/minute")
def get_item(request: Request, item_id: int, db: DbSession, current_user: OptionalCurrentUser = None):
    """Get menu item by ID."""
    item = db.query(MenuItem).filter(MenuItem.id == item_id, MenuItem.not_deleted()).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    return MenuItemResponse(
        id=item.id, category=item.category, name=item.name,
        description=item.description, price=float(item.price),
        sort_order=0, available=item.available,
        allergens=item.allergens if isinstance(item.allergens, list) else [],
        station=item.station, prep_time_minutes=item.prep_time_minutes,
    )


@router.post("/items", response_model=MenuItemResponse, status_code=201)
@limiter.limit("30/minute")
def create_item(request: Request, data: MenuItemCreate, db: DbSession, current_user: CurrentUser = None):
    """Create new menu item (manager only)."""
    item = MenuItem(
        category=data.category,
        name=data.name,
        description=data.description,
        price=data.price,
        available=data.available,
        allergens=data.allergens,
        station=data.station,
        prep_time_minutes=data.prep_time_minutes,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    return MenuItemResponse(
        id=item.id, category=item.category, name=item.name,
        description=item.description, price=float(item.price),
        sort_order=0, available=item.available,
        allergens=item.allergens if isinstance(item.allergens, list) else [],
        station=item.station, prep_time_minutes=item.prep_time_minutes,
    )


@router.put("/items/{item_id}", response_model=MenuItemResponse)
@limiter.limit("30/minute")
def update_item(request: Request, item_id: int, data: MenuItemUpdate, db: DbSession, current_user: CurrentUser = None):
    """Update menu item (manager only)."""
    item = db.query(MenuItem).filter(MenuItem.id == item_id, MenuItem.not_deleted()).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if data.category is not None:
        item.category = data.category
    if data.name is not None:
        item.name = data.name
    if data.description is not None:
        item.description = data.description
    if data.price is not None:
        item.price = data.price
    if data.available is not None:
        item.available = data.available
    if data.allergens is not None:
        item.allergens = data.allergens
    if data.station is not None:
        item.station = data.station
    if data.prep_time_minutes is not None:
        item.prep_time_minutes = data.prep_time_minutes

    db.commit()
    db.refresh(item)

    return MenuItemResponse(
        id=item.id, category=item.category, name=item.name,
        description=item.description, price=float(item.price),
        sort_order=0, available=item.available,
        allergens=item.allergens if isinstance(item.allergens, list) else [],
        station=item.station, prep_time_minutes=item.prep_time_minutes,
    )


@router.delete("/items/{item_id}", status_code=204)
@limiter.limit("30/minute")
def delete_item(request: Request, item_id: int, db: DbSession, current_user: CurrentUser = None):
    """Delete menu item (manager only)."""
    item = db.query(MenuItem).filter(MenuItem.id == item_id, MenuItem.not_deleted()).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()
    return None


@router.patch("/items/{item_id}/toggle-available")
@limiter.limit("30/minute")
def toggle_item_availability(request: Request, item_id: int, db: DbSession, current_user: OptionalCurrentUser = None):
    """Toggle item availability (any staff)."""
    item = db.query(MenuItem).filter(MenuItem.id == item_id, MenuItem.not_deleted()).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    item.available = not item.available
    db.commit()
    return {"id": item.id, "available": item.available}


# ==================== MODIFIER GROUPS ====================

@router.get("/items/{item_id}/modifiers")
@limiter.limit("60/minute")
def list_item_modifiers(request: Request, item_id: int, db: DbSession, current_user: OptionalCurrentUser = None):
    """List all modifier groups for a menu item."""
    from app.models.restaurant import MenuItemModifierGroup

    links = db.query(MenuItemModifierGroup).filter(
        MenuItemModifierGroup.menu_item_id == item_id,
    ).all()

    results = []
    for link in links:
        group = db.query(ModifierGroup).filter(ModifierGroup.id == link.modifier_group_id).first()
        if group:
            options = db.query(ModifierOption).filter(
                ModifierOption.group_id == group.id,
            ).order_by(ModifierOption.sort_order).all()

            results.append({
                "id": group.id,
                "name": group.name,
                "min_selections": group.min_selections,
                "max_selections": group.max_selections,
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
            })

    return results


@router.post("/modifiers", status_code=201)
@limiter.limit("30/minute")
def create_modifier_group(request: Request, data: ModifierGroupCreateSchema, db: DbSession, current_user: CurrentUser = None):
    """Create a new modifier group (manager only)."""
    group = ModifierGroup(
        name=data.name,
        min_selections=data.min_selections,
        max_selections=data.max_selections,
        sort_order=data.sort_order,
    )
    db.add(group)
    db.commit()
    db.refresh(group)

    return {
        "id": group.id,
        "name": group.name,
        "min_selections": group.min_selections,
        "max_selections": group.max_selections,
        "sort_order": group.sort_order,
        "options": [],
    }


@router.put("/modifiers/{group_id}")
@limiter.limit("30/minute")
def update_modifier_group(request: Request, group_id: int, data: ModifierGroupUpdateSchema, db: DbSession, current_user: CurrentUser = None):
    """Update a modifier group (manager only)."""
    group = db.query(ModifierGroup).filter(ModifierGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Modifier group not found")

    if data.name is not None:
        group.name = data.name
    if data.min_selections is not None:
        group.min_selections = data.min_selections
    if data.max_selections is not None:
        group.max_selections = data.max_selections
    if data.sort_order is not None:
        group.sort_order = data.sort_order

    db.commit()
    db.refresh(group)
    return {"id": group.id, "name": group.name, "min_selections": group.min_selections, "max_selections": group.max_selections, "sort_order": group.sort_order}


@router.delete("/modifiers/{group_id}", status_code=204)
@limiter.limit("30/minute")
def delete_modifier_group(request: Request, group_id: int, db: DbSession, current_user: CurrentUser = None):
    """Delete a modifier group and all its options (manager only)."""
    group = db.query(ModifierGroup).filter(ModifierGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Modifier group not found")

    db.query(ModifierOption).filter(ModifierOption.group_id == group_id).delete()
    db.delete(group)
    db.commit()
    return None


# ==================== MODIFIER OPTIONS ====================

@router.post("/modifiers/{group_id}/options", status_code=201)
@limiter.limit("30/minute")
def create_modifier_option(request: Request, group_id: int, data: ModifierOptionCreateSchema, db: DbSession, current_user: CurrentUser = None):
    """Create a new option in a modifier group (manager only)."""
    group = db.query(ModifierGroup).filter(ModifierGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Modifier group not found")

    option = ModifierOption(
        group_id=group_id,
        name=data.name,
        price_adjustment=data.price_adjustment,
        sort_order=data.sort_order,
        available=data.available,
    )
    db.add(option)
    db.commit()
    db.refresh(option)
    return {"id": option.id, "group_id": group_id, "name": option.name, "price_adjustment": float(option.price_adjustment or 0), "sort_order": option.sort_order, "available": option.available}


@router.put("/modifiers/options/{option_id}")
@limiter.limit("30/minute")
def update_modifier_option(request: Request, option_id: int, data: ModifierOptionUpdateSchema, db: DbSession, current_user: CurrentUser = None):
    """Update a modifier option (manager only)."""
    option = db.query(ModifierOption).filter(ModifierOption.id == option_id).first()
    if not option:
        raise HTTPException(status_code=404, detail="Modifier option not found")

    if data.name is not None:
        option.name = data.name
    if data.price_adjustment is not None:
        option.price_adjustment = data.price_adjustment
    if data.sort_order is not None:
        option.sort_order = data.sort_order
    if data.available is not None:
        option.available = data.available

    db.commit()
    db.refresh(option)
    return {"id": option.id, "group_id": option.group_id, "name": option.name, "price_adjustment": float(option.price_adjustment or 0), "sort_order": option.sort_order, "available": option.available}


@router.delete("/modifiers/options/{option_id}", status_code=204)
@limiter.limit("30/minute")
def delete_modifier_option(request: Request, option_id: int, db: DbSession, current_user: CurrentUser = None):
    """Delete a modifier option (manager only)."""
    option = db.query(ModifierOption).filter(ModifierOption.id == option_id).first()
    if not option:
        raise HTTPException(status_code=404, detail="Modifier option not found")
    db.delete(option)
    db.commit()
    return None


@router.patch("/modifiers/options/{option_id}/toggle-available")
@limiter.limit("30/minute")
def toggle_modifier_option_availability(request: Request, option_id: int, db: DbSession, current_user: OptionalCurrentUser = None):
    """Toggle modifier option availability (any staff)."""
    option = db.query(ModifierOption).filter(ModifierOption.id == option_id).first()
    if not option:
        raise HTTPException(status_code=404, detail="Modifier option not found")

    option.available = not option.available
    db.commit()
    return {"id": option.id, "available": option.available}


# ==================== BULK PRICE UPDATE ====================

class BulkPriceUpdateRequest(BaseModel):
    item_ids: List[int]
    adjustment_type: str  # "percentage" or "fixed"
    adjustment_value: float


@router.post("/bulk-price-update")
@limiter.limit("30/minute")
def bulk_update_prices(request: Request, data: BulkPriceUpdateRequest, db: DbSession, current_user: CurrentUser = None):
    """Bulk update menu item prices."""
    updated_count = 0

    for item_id in data.item_ids:
        item = db.query(MenuItem).filter(MenuItem.id == item_id, MenuItem.not_deleted()).first()
        if item:
            if data.adjustment_type == "percentage":
                item.price = float(item.price) * (1 + data.adjustment_value / 100)
            else:
                item.price = float(item.price) + data.adjustment_value
            item.price = round(item.price, 2)
            updated_count += 1

    db.commit()
    return {"status": "success", "updated_count": updated_count}

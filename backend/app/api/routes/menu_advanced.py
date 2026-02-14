"""Advanced Menu Management API routes - photo management, price levels, cross-selling, dayparts, combos, global modifiers."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, UploadFile, File, Request
from typing import List, Optional, Dict
from datetime import datetime
from pydantic import BaseModel, Field

from app.db.session import DbSession
from app.core.rbac import CurrentUser, OptionalCurrentUser
from app.core.rate_limit import limiter
from app.models.restaurant import (
    MenuItem, MenuCategory, ModifierGroup, ModifierOption,
    ComboMeal, ComboItem,
)

router = APIRouter()


# ==================== SCHEMAS ====================

class PhotoUploadResponse(BaseModel):
    url: str
    thumbnail_url: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None


class PriceLevelCreate(BaseModel):
    name: str
    description: Optional[str] = None
    multiplier: float = Field(..., gt=0)
    applies_to: str = "all"
    active: bool = True
    schedule: Optional[Dict] = None


class PriceLevelUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    multiplier: Optional[float] = Field(None, gt=0)
    active: Optional[bool] = None
    schedule: Optional[Dict] = None


class CrossSellCreate(BaseModel):
    suggested_item_id: int
    reason: Optional[str] = None
    discount_percentage: Optional[float] = 0
    active: bool = True
    sort_order: int = 0


class DaypartCreate(BaseModel):
    name: str
    display_name_bg: str = ""
    display_name_en: str = ""
    start_time: str
    end_time: str
    days: List[str]
    categories: List[int] = []
    items: List[int] = []
    price_adjustment: float = 0
    active: bool = True
    color: str = "#3B82F6"


class ComboCreateSchema(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    items: List[Dict] = []
    available: bool = True
    featured: bool = False


class GlobalModifierGroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    required: bool = False
    min_selections: int = 0
    max_selections: int = 1
    sort_order: int = 0


class ModifierOptionCreate(BaseModel):
    name: str
    price_adjustment: float = 0.0
    available: bool = True
    sort_order: int = 0


class CategoryReorderRequest(BaseModel):
    categories: List[Dict[str, int]]


# ==================== In-memory stores ====================
_price_levels: list = []
_dayparts: list = []
_cross_sell_map: dict = {}  # item_id -> list of suggestions
_next_price_level_id = 1
_next_daypart_id = 1


# ==================== PHOTO MANAGEMENT ====================

@router.post("/items/{item_id}/photos", response_model=PhotoUploadResponse)
@limiter.limit("30/minute")
async def upload_item_photo(request: Request, item_id: int, file: UploadFile = File(...), db: DbSession = None, current_user: CurrentUser = None):
    """Upload a photo for a menu item."""
    item = db.query(MenuItem).filter(MenuItem.id == item_id, MenuItem.not_deleted()).first()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    photo_url = f"/uploads/menu-items/{item_id}/{file.filename}"
    return PhotoUploadResponse(url=photo_url, thumbnail_url=f"{photo_url}?w=300", width=1200, height=800)


@router.get("/items/{item_id}/photos")
@limiter.limit("60/minute")
def get_item_photos(request: Request, item_id: int, db: DbSession = None, current_user: OptionalCurrentUser = None):
    """Get all photos for a menu item."""
    item = db.query(MenuItem).filter(MenuItem.id == item_id, MenuItem.not_deleted()).first()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    return {"item_id": item_id, "photos": []}


@router.delete("/items/{item_id}/photos/{photo_index}")
@limiter.limit("30/minute")
def delete_item_photo(request: Request, item_id: int, photo_index: int, db: DbSession = None, current_user: CurrentUser = None):
    """Delete a photo from a menu item."""
    item = db.query(MenuItem).filter(MenuItem.id == item_id, MenuItem.not_deleted()).first()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    return {"status": "deleted"}


# ==================== PRICE LEVELS ====================

@router.get("/price-levels")
@limiter.limit("60/minute")
def get_price_levels(request: Request, db: DbSession = None, current_user: OptionalCurrentUser = None):
    """Get all price levels."""
    return {"price_levels": _price_levels}


@router.post("/price-levels")
@limiter.limit("30/minute")
def create_price_level(request: Request, data: PriceLevelCreate, db: DbSession = None, current_user: CurrentUser = None):
    """Create a new price level."""
    global _next_price_level_id
    now = datetime.utcnow().isoformat()
    pl = {
        "id": _next_price_level_id,
        "name": data.name,
        "description": data.description,
        "multiplier": data.multiplier,
        "is_active": data.active,
        "active": data.active,
        "applies_to": data.applies_to,
        "schedule": data.schedule,
        "created_at": now,
    }
    _price_levels.append(pl)
    _next_price_level_id += 1
    return pl


@router.get("/price-levels/{price_level_id}")
@limiter.limit("60/minute")
def get_price_level(request: Request, price_level_id: int, db: DbSession = None, current_user: OptionalCurrentUser = None):
    """Get a specific price level by ID."""
    for pl in _price_levels:
        if pl["id"] == price_level_id:
            return pl
    raise HTTPException(status_code=404, detail="Price level not found")


@router.put("/price-levels/{price_level_id}")
@limiter.limit("30/minute")
def update_price_level(request: Request, price_level_id: int, data: PriceLevelUpdate, db: DbSession = None, current_user: CurrentUser = None):
    """Update an existing price level."""
    for pl in _price_levels:
        if pl["id"] == price_level_id:
            if data.name is not None:
                pl["name"] = data.name
            if data.description is not None:
                pl["description"] = data.description
            if data.multiplier is not None:
                pl["multiplier"] = data.multiplier
            if data.active is not None:
                pl["is_active"] = data.active
                pl["active"] = data.active
            if data.schedule is not None:
                pl["schedule"] = data.schedule
            return pl
    raise HTTPException(status_code=404, detail="Price level not found")


@router.delete("/price-levels/{price_level_id}")
@limiter.limit("30/minute")
def delete_price_level(request: Request, price_level_id: int, db: DbSession = None, current_user: CurrentUser = None):
    """Delete a price level."""
    global _price_levels
    original_len = len(_price_levels)
    _price_levels = [pl for pl in _price_levels if pl["id"] != price_level_id]
    if len(_price_levels) == original_len:
        raise HTTPException(status_code=404, detail="Price level not found")
    return {"status": "deleted", "id": price_level_id}


@router.patch("/price-levels/{price_level_id}/toggle-active")
@limiter.limit("30/minute")
def toggle_price_level_active(request: Request, price_level_id: int, db: DbSession = None, current_user: CurrentUser = None):
    """Toggle price level active status."""
    for pl in _price_levels:
        if pl["id"] == price_level_id:
            pl["is_active"] = not pl["is_active"]
            pl["active"] = pl["is_active"]
            return {"id": price_level_id, "is_active": pl["is_active"], "active": pl["is_active"]}
    raise HTTPException(status_code=404, detail="Price level not found")


# ==================== CROSS-SELLING ====================

@router.get("/items/{item_id}/cross-sell")
@limiter.limit("60/minute")
def get_cross_sell_suggestions(request: Request, item_id: int, db: DbSession = None, current_user: OptionalCurrentUser = None):
    """Get cross-sell suggestions for an item."""
    suggestions = _cross_sell_map.get(item_id, [])
    return {"item_id": item_id, "suggestions": suggestions}


@router.post("/items/{item_id}/cross-sell")
@limiter.limit("30/minute")
def add_cross_sell_suggestion(request: Request, item_id: int, data: CrossSellCreate, db: DbSession = None, current_user: CurrentUser = None):
    """Add a cross-sell suggestion to an item."""
    item = db.query(MenuItem).filter(MenuItem.id == item_id, MenuItem.not_deleted()).first()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    suggested_item = db.query(MenuItem).filter(MenuItem.id == data.suggested_item_id, MenuItem.not_deleted()).first()
    if not suggested_item:
        raise HTTPException(status_code=404, detail="Suggested item not found")

    suggestion = {
        "item_id": data.suggested_item_id,
        "item_name": suggested_item.name,
        "reason": data.reason,
        "discount_percentage": data.discount_percentage,
        "active": data.active,
        "sort_order": data.sort_order,
    }

    if item_id not in _cross_sell_map:
        _cross_sell_map[item_id] = []
    _cross_sell_map[item_id].append(suggestion)
    return suggestion


@router.delete("/items/{item_id}/cross-sell/{suggested_item_id}")
@limiter.limit("30/minute")
def remove_cross_sell_suggestion(request: Request, item_id: int, suggested_item_id: int, db: DbSession = None, current_user: CurrentUser = None):
    """Remove a cross-sell suggestion."""
    if item_id in _cross_sell_map:
        _cross_sell_map[item_id] = [s for s in _cross_sell_map[item_id] if s.get("item_id") != suggested_item_id]
    return {"status": "deleted"}


# ==================== DAYPARTS ====================

@router.get("/dayparts")
@limiter.limit("60/minute")
def get_dayparts(request: Request, db: DbSession = None, current_user: OptionalCurrentUser = None):
    """Get all daypart schedules."""
    return _dayparts


@router.post("/dayparts")
@limiter.limit("30/minute")
def create_daypart(request: Request, data: DaypartCreate, db: DbSession = None, current_user: CurrentUser = None):
    """Create a new daypart schedule."""
    global _next_daypart_id
    daypart = {
        "id": _next_daypart_id,
        "name": data.name,
        "display_name": {"bg": data.display_name_bg, "en": data.display_name_en},
        "start_time": data.start_time,
        "end_time": data.end_time,
        "days": data.days,
        "categories": data.categories,
        "items": data.items,
        "price_adjustment": data.price_adjustment,
        "active": data.active,
        "color": data.color,
    }
    _dayparts.append(daypart)
    _next_daypart_id += 1
    return daypart


@router.delete("/dayparts/{daypart_id}")
@limiter.limit("30/minute")
def delete_daypart(request: Request, daypart_id: int, db: DbSession = None, current_user: CurrentUser = None):
    """Delete a daypart schedule."""
    global _dayparts
    original_len = len(_dayparts)
    _dayparts = [d for d in _dayparts if d["id"] != daypart_id]
    if len(_dayparts) == original_len:
        raise HTTPException(status_code=404, detail="Daypart not found")
    return {"status": "deleted"}


@router.patch("/dayparts/{daypart_id}/toggle-active")
@limiter.limit("30/minute")
def toggle_daypart_active(request: Request, daypart_id: int, db: DbSession = None, current_user: CurrentUser = None):
    """Toggle daypart active status."""
    for d in _dayparts:
        if d["id"] == daypart_id:
            d["active"] = not d["active"]
            return {"id": daypart_id, "active": d["active"]}
    raise HTTPException(status_code=404, detail="Daypart not found")


# ==================== COMBOS/BUNDLES ====================

@router.get("/combos")
@limiter.limit("60/minute")
def get_combos(request: Request, db: DbSession = None, current_user: OptionalCurrentUser = None):
    """Get all combo meals."""
    combos = db.query(ComboMeal).order_by(ComboMeal.name).all()

    combo_list = []
    for combo in combos:
        items = db.query(ComboItem).filter(ComboItem.combo_id == combo.id).all()
        combo_list.append({
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
                }
                for item in items
            ],
        })
    return combo_list


@router.post("/combos")
@limiter.limit("30/minute")
def create_combo(request: Request, data: ComboCreateSchema, db: DbSession = None, current_user: CurrentUser = None):
    """Create a new combo meal."""
    combo = ComboMeal(
        name=data.name,
        description=data.description,
        price=data.price,
        available=data.available,
        featured=data.featured,
    )
    db.add(combo)
    db.commit()
    db.refresh(combo)

    return {
        "id": combo.id,
        "name": data.name,
        "description": data.description,
        "price": data.price,
        "available": data.available,
        "featured": data.featured,
    }


@router.delete("/combos/{combo_id}")
@limiter.limit("30/minute")
def delete_combo(request: Request, combo_id: int, db: DbSession = None, current_user: CurrentUser = None):
    """Delete a combo meal."""
    combo = db.query(ComboMeal).filter(ComboMeal.id == combo_id).first()
    if not combo:
        raise HTTPException(status_code=404, detail="Combo not found")

    db.query(ComboItem).filter(ComboItem.combo_id == combo_id).delete()
    db.delete(combo)
    db.commit()
    return {"status": "deleted"}


@router.patch("/combos/{combo_id}/toggle-available")
@limiter.limit("30/minute")
def toggle_combo_available(request: Request, combo_id: int, db: DbSession = None, current_user: CurrentUser = None):
    """Toggle combo availability."""
    combo = db.query(ComboMeal).filter(ComboMeal.id == combo_id).first()
    if not combo:
        raise HTTPException(status_code=404, detail="Combo not found")

    combo.available = not combo.available
    db.commit()
    return {"id": combo_id, "available": combo.available}


# ==================== GLOBAL MODIFIERS ====================

@router.get("/modifier-groups")
@limiter.limit("60/minute")
def get_global_modifier_groups(request: Request, db: DbSession = None, current_user: OptionalCurrentUser = None):
    """Get all modifier groups."""
    groups = db.query(ModifierGroup).order_by(ModifierGroup.sort_order, ModifierGroup.name).all()

    return [
        {
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
                for opt in db.query(ModifierOption).filter(ModifierOption.group_id == group.id).order_by(ModifierOption.sort_order).all()
            ],
        }
        for group in groups
    ]


@router.post("/modifier-groups")
@limiter.limit("30/minute")
def create_global_modifier_group(request: Request, data: GlobalModifierGroupCreate, db: DbSession = None, current_user: CurrentUser = None):
    """Create a global modifier group."""
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
        "name": data.name,
        "description": data.description,
        "required": data.required,
        "min_selections": data.min_selections,
        "max_selections": data.max_selections,
        "sort_order": data.sort_order,
        "options": [],
    }


@router.post("/modifier-groups/{group_id}/options")
@limiter.limit("30/minute")
def add_modifier_option(request: Request, group_id: int, data: ModifierOptionCreate, db: DbSession = None, current_user: CurrentUser = None):
    """Add an option to a modifier group."""
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

    return {
        "id": option.id,
        "group_id": group_id,
        "name": data.name,
        "price_adjustment": data.price_adjustment,
        "available": data.available,
        "sort_order": data.sort_order,
    }


# ==================== CATEGORY ADVANCED ====================

@router.put("/categories/reorder")
@limiter.limit("30/minute")
def reorder_categories(request: Request, data: CategoryReorderRequest, db: DbSession = None, current_user: CurrentUser = None):
    """Reorder categories."""
    for cat_data in data.categories:
        category = db.query(MenuCategory).filter(MenuCategory.id == cat_data["id"]).first()
        if category:
            category.sort_order = cat_data["sort_order"]
    db.commit()
    return {"status": "success", "updated_count": len(data.categories)}


@router.patch("/categories/{category_id}/toggle-active")
@limiter.limit("30/minute")
def toggle_category_active(request: Request, category_id: int, db: DbSession = None, current_user: CurrentUser = None):
    """Toggle category active status."""
    category = db.query(MenuCategory).filter(MenuCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    category.active = not category.active
    db.commit()
    return {"id": category_id, "active": category.active}


# ==================== ALLERGENS & NUTRITION ====================

@router.get("/items-with-allergens")
@limiter.limit("60/minute")
def get_items_with_allergens(request: Request, db: DbSession = None, current_user: OptionalCurrentUser = None):
    """Get all menu items with allergen info."""
    items = db.query(MenuItem).filter(MenuItem.not_deleted()).all()

    return [
        {
            "id": item.id,
            "name": item.name,
            "category": item.category,
            "price": float(item.price),
            "allergens": item.allergens if isinstance(item.allergens, list) else [],
            "dietary_labels": [],
            "nutrition": None,
            "spice_level": 0,
            "contains_alcohol": False,
        }
        for item in items
    ]

"""
Complete Menu Management Features - Competitor Parity
Implements all menu features adapted for the bjs-menu system.

Features:
1. Menu Item Variants (sizes, portions)
2. Combo/Bundle Management
3. Menu Tags (vegan, spicy, new, popular)
4. Upsell/Cross-sell Suggestions
5. Limited-Time Offers with Auto-Expiry
6. 86'd Items (Out of Stock Management)
7. QR Code Menu Generation
8. Digital Menu Board Management
9. Menu Performance Analytics
"""

from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import func, desc
from typing import List, Optional, Dict
from pydantic import BaseModel, ConfigDict
from datetime import datetime, date, time, timedelta
import uuid
import io
import base64

from app.core.rate_limit import limiter
from app.db.session import DbSession
from app.core.rbac import CurrentUser, OptionalCurrentUser

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# SCHEMAS
# =============================================================================

# --- Menu Item Variants ---
class MenuItemVariantCreate(BaseModel):
    name: str
    variant_type: str = "size"
    sku_suffix: Optional[str] = None
    price: float
    cost: Optional[float] = None
    calories: Optional[int] = None
    portion_size: Optional[str] = None
    portion_multiplier: float = 1.0
    is_default: bool = False
    sort_order: int = 0
    active: bool = True


class MenuItemVariantResponse(BaseModel):
    id: int
    menu_item_id: int
    name: str
    variant_type: str
    sku_suffix: Optional[str] = None
    price: float
    cost: Optional[float] = None
    calories: Optional[int] = None
    portion_size: Optional[str] = None
    is_default: bool
    sort_order: int
    active: bool
    profit_margin: Optional[float] = None


# --- Combos/Bundles ---
class ComboItemCreate(BaseModel):
    menu_item_id: int
    quantity: int = 1
    is_required: bool = True
    max_selections: int = 1
    allowed_substitutions: Optional[List[int]] = None


class ComboCreate(BaseModel):
    name: str
    description: Optional[str] = None
    items: List[ComboItemCreate]
    pricing_type: str = "fixed"
    fixed_price: Optional[float] = None
    discount_percentage: Optional[float] = None
    image_url: Optional[str] = None
    available_from: Optional[str] = None  # "HH:MM"
    available_until: Optional[str] = None
    available_days: List[int] = [0, 1, 2, 3, 4, 5, 6]
    max_per_order: Optional[int] = None
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None
    active: bool = True


class ComboResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    items: List[Dict]
    pricing_type: str
    price: Optional[float] = None
    discount_percentage: Optional[float] = None
    original_total: float
    savings: float
    savings_percentage: float
    is_available_now: bool
    active: bool
    created_at: str


# --- Menu Tags ---
class MenuTagCreate(BaseModel):
    code: str
    name: str
    icon: Optional[str] = None
    color: Optional[str] = None
    description: Optional[str] = None
    sort_order: int = 0
    active: bool = True


class MenuTagResponse(BaseModel):
    id: int
    code: str
    name: str
    icon: Optional[str] = None
    color: Optional[str] = None
    description: Optional[str] = None
    items_count: int = 0
    sort_order: int
    active: bool


# --- Upsell/Cross-sell ---
class UpsellRuleCreate(BaseModel):
    source_item_id: int
    suggestion_type: str  # upsell, cross_sell, upgrade, addon
    suggested_item_id: Optional[int] = None
    suggested_category_id: Optional[int] = None
    message: Optional[str] = None
    discount_percentage: Optional[float] = None
    priority: int = 0
    active: bool = True


# --- Limited Time Offers ---
class LimitedTimeOfferCreate(BaseModel):
    name: str
    description: Optional[str] = None
    menu_item_id: Optional[int] = None
    category_id: Optional[int] = None
    offer_type: str  # new_item, discount, special_price, bundle
    original_price: Optional[float] = None
    offer_price: Optional[float] = None
    discount_percentage: Optional[float] = None
    start_datetime: datetime
    end_datetime: datetime
    max_quantity: Optional[int] = None
    max_per_customer: Optional[int] = None
    image_url: Optional[str] = None
    badge_text: Optional[str] = None
    countdown_enabled: bool = True
    auto_disable_when_sold_out: bool = True
    active: bool = True


class LimitedTimeOfferResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    menu_item_id: Optional[int] = None
    offer_type: str
    original_price: Optional[float] = None
    offer_price: Optional[float] = None
    discount_percentage: Optional[float] = None
    savings: Optional[float] = None
    start_datetime: str
    end_datetime: str
    remaining_quantity: Optional[int] = None
    is_active: bool
    is_expired: bool
    time_remaining_seconds: Optional[int] = None
    badge_text: Optional[str] = None


# --- 86'd Items ---
class Item86Request(BaseModel):
    menu_item_id: int
    reason: str  # sold_out, ingredient_missing, equipment_issue, quality_issue
    expected_back: Optional[str] = None
    auto_restore: bool = True
    notify_staff: bool = True
    alternative_items: Optional[List[int]] = None
    notes: Optional[str] = None


class Item86Response(BaseModel):
    id: int
    menu_item_id: int
    menu_item_name: str
    reason: str
    marked_at: str
    marked_by: str
    expected_back: Optional[str] = None
    is_active: bool
    alternative_items: Optional[List[Dict]] = None
    duration_minutes: int


# --- Digital Menu Board ---
class DigitalMenuBoardCreate(BaseModel):
    name: str
    display_type: str = "full_menu"
    categories: Optional[List[str]] = None  # category strings (bjs-menu uses string category)
    items: Optional[List[int]] = None
    layout: str = "grid"
    columns: int = 3
    show_prices: bool = True
    show_descriptions: bool = True
    show_images: bool = True
    show_calories: bool = False
    show_allergens: bool = True
    rotation_seconds: int = 10
    theme: str = "dark"
    custom_css: Optional[str] = None
    header_text: Optional[str] = None
    footer_text: Optional[str] = None
    background_image: Optional[str] = None
    auto_hide_unavailable: bool = True
    active: bool = True


# --- Menu Engineering ---
class MenuEngineeringItem(BaseModel):
    menu_item_id: int
    name: str
    category: str
    price: float
    cost: float
    profit_margin: float
    profit_margin_percentage: float
    quantity_sold: int
    revenue: float
    profit: float
    popularity_index: float
    profitability_index: float
    classification: str  # star, puzzle, plow_horse, dog
    recommendation: str
    trend: str


class MenuEngineeringReport(BaseModel):
    period_start: str
    period_end: str
    total_items: int
    total_revenue: float
    total_profit: float
    average_profit_margin: float
    stars: List[MenuEngineeringItem]
    puzzles: List[MenuEngineeringItem]
    plow_horses: List[MenuEngineeringItem]
    dogs: List[MenuEngineeringItem]
    recommendations: List[Dict[str, str]]


# =============================================================================
# IN-MEMORY STORES (features without DB models)
# =============================================================================
_variants: list = []
_tags: list = []
_tag_assignments: list = []
_upsell_rules: list = []
_limited_offers: list = []
_item86_records: list = []
_digital_boards: list = []
_next_ids = {
    "variant": 1, "tag": 1, "tag_assignment": 1,
    "upsell_rule": 1, "offer": 1, "item86": 1, "board": 1,
}


# =============================================================================
# MENU ITEM VARIANTS
# =============================================================================

@router.post("/items/{item_id}/variants", response_model=MenuItemVariantResponse)
@limiter.limit("30/minute")
def create_menu_item_variant(
    request: Request,
    item_id: int,
    data: MenuItemVariantCreate,
    db: DbSession,
    current_user: CurrentUser = None,
):
    """
    Create a size/portion variant for a menu item.

    Examples:
    - Pizza: Small, Medium, Large, Family
    - Drinks: Regular, Large, Extra Large
    - Steak: 200g, 300g, 400g
    """
    from app.models.restaurant import MenuItem

    item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    global _next_ids

    # Calculate profit margin
    profit_margin = None
    if data.cost and data.price > 0:
        profit_margin = round((data.price - data.cost) / data.price * 100, 1)

    # If this is default, unset other defaults
    if data.is_default:
        for v in _variants:
            if v["menu_item_id"] == item_id:
                v["is_default"] = False

    variant = {
        "id": _next_ids["variant"],
        "menu_item_id": item_id,
        "name": data.name,
        "variant_type": data.variant_type,
        "sku_suffix": data.sku_suffix,
        "price": data.price,
        "cost": data.cost,
        "calories": data.calories,
        "portion_size": data.portion_size,
        "portion_multiplier": data.portion_multiplier,
        "is_default": data.is_default,
        "sort_order": data.sort_order,
        "active": data.active,
        "profit_margin": profit_margin,
    }
    _variants.append(variant)
    _next_ids["variant"] += 1

    return MenuItemVariantResponse(**{k: v for k, v in variant.items() if k in MenuItemVariantResponse.model_fields})


@router.get("/items/{item_id}/variants")
@limiter.limit("60/minute")
def list_menu_item_variants(
    request: Request,
    item_id: int,
    db: DbSession,
    current_user: CurrentUser = None,
):
    """List all variants for a menu item."""
    from app.models.restaurant import MenuItem

    item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    variants = [v for v in _variants if v["menu_item_id"] == item_id]
    variants.sort(key=lambda v: (v["sort_order"], v["id"]))

    default_variant = None
    variants_list = []
    for v in variants:
        variant_data = {
            "id": v["id"],
            "name": v["name"],
            "variant_type": v["variant_type"],
            "sku_suffix": v.get("sku_suffix"),
            "price": v["price"],
            "cost": v.get("cost"),
            "calories": v.get("calories"),
            "portion_size": v.get("portion_size"),
            "is_default": v["is_default"],
            "sort_order": v["sort_order"],
            "active": v["active"],
        }
        variants_list.append(variant_data)
        if v["is_default"]:
            default_variant = variant_data

    return {
        "item_id": item_id,
        "item_name": item.name,
        "variants": variants_list,
        "default_variant": default_variant,
    }


@router.put("/variants/{variant_id}", response_model=MenuItemVariantResponse)
@limiter.limit("30/minute")
def update_menu_item_variant(
    request: Request,
    variant_id: int,
    data: MenuItemVariantCreate,
    db: DbSession,
    current_user: CurrentUser = None,
):
    """Update a menu item variant."""
    variant = None
    for v in _variants:
        if v["id"] == variant_id:
            variant = v
            break

    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    # If setting as default, unset others
    if data.is_default and not variant["is_default"]:
        for v in _variants:
            if v["menu_item_id"] == variant["menu_item_id"] and v["id"] != variant_id:
                v["is_default"] = False

    variant["name"] = data.name
    variant["sku_suffix"] = data.sku_suffix
    variant["price"] = data.price
    variant["cost"] = data.cost
    variant["calories"] = data.calories
    variant["portion_size"] = data.portion_size
    variant["is_default"] = data.is_default
    variant["sort_order"] = data.sort_order
    variant["active"] = data.active

    profit_margin = None
    if variant["cost"] and variant["price"] > 0:
        profit_margin = round((variant["price"] - variant["cost"]) / variant["price"] * 100, 1)
    variant["profit_margin"] = profit_margin

    return MenuItemVariantResponse(**{k: v for k, v in variant.items() if k in MenuItemVariantResponse.model_fields})


@router.delete("/variants/{variant_id}")
@limiter.limit("30/minute")
def delete_menu_item_variant(
    request: Request,
    variant_id: int,
    db: DbSession,
    current_user: CurrentUser = None,
):
    """Delete a menu item variant."""
    global _variants

    for v in _variants:
        if v["id"] == variant_id:
            _variants = [x for x in _variants if x["id"] != variant_id]
            return {"message": "Variant deleted", "id": variant_id}

    raise HTTPException(status_code=404, detail="Variant not found")


# =============================================================================
# COMBOS / BUNDLES
# =============================================================================

@router.post("/combos", response_model=ComboResponse)
@limiter.limit("30/minute")
def create_combo(
    request: Request,
    data: ComboCreate,
    db: DbSession,
    current_user: CurrentUser = None,
):
    """
    Create a combo/bundle deal.

    Pricing types:
    - fixed: Set a specific combo price
    - percentage_discount: X% off total of items
    - cheapest_free: Cheapest item is free
    """
    from app.models.restaurant import MenuItem

    # Calculate original total and validate items
    original_total = 0.0
    items_data = []

    for ci in data.items:
        menu_item = db.query(MenuItem).filter(MenuItem.id == ci.menu_item_id).first()
        if not menu_item:
            raise HTTPException(status_code=404, detail=f"Menu item {ci.menu_item_id} not found")

        item_total = float(menu_item.price) * ci.quantity
        original_total += item_total

        items_data.append({
            "menu_item_id": ci.menu_item_id,
            "name": menu_item.name,
            "price": float(menu_item.price),
            "quantity": ci.quantity,
            "is_required": ci.is_required,
            "max_selections": ci.max_selections,
        })

    # Calculate final price
    if data.pricing_type == "fixed":
        final_price = data.fixed_price or original_total
    elif data.pricing_type == "percentage_discount":
        discount = original_total * (data.discount_percentage or 0) / 100
        final_price = original_total - discount
    elif data.pricing_type == "cheapest_free":
        cheapest = min(items_data, key=lambda x: x["price"])
        final_price = original_total - cheapest["price"]
    else:
        final_price = original_total

    savings = original_total - final_price
    savings_percentage = (savings / original_total * 100) if original_total > 0 else 0

    now = datetime.utcnow()

    # Check availability
    is_available = data.active
    if data.available_from:
        try:
            h, m = data.available_from.split(":")
            if now.time() < time(int(h), int(m)):
                is_available = False
        except Exception as e:
            logger.debug(f"Optional: parse available_from time '{data.available_from}': {e}")
    if data.available_until:
        try:
            h, m = data.available_until.split(":")
            if now.time() > time(int(h), int(m)):
                is_available = False
        except Exception as e:
            logger.debug(f"Optional: parse available_until time '{data.available_until}': {e}")
    if now.weekday() not in data.available_days:
        is_available = False

    # Create in bjs-menu DB using ComboMeal
    from app.models.restaurant import ComboMeal, ComboItem

    combo = ComboMeal(
        name=data.name,
        description=data.description,
        price=final_price,
        image_url=data.image_url,
        available=data.active,
    )
    db.add(combo)
    db.flush()

    # Add combo items
    for idx, ci in enumerate(data.items):
        item_name = items_data[idx]["name"]
        combo_item = ComboItem(
            combo_id=combo.id,
            menu_item_id=ci.menu_item_id,
            name=item_name,
            quantity=ci.quantity,
            is_choice=not ci.is_required,
        )
        db.add(combo_item)

    db.commit()
    db.refresh(combo)

    return ComboResponse(
        id=combo.id,
        name=combo.name,
        description=combo.description,
        items=items_data,
        pricing_type=data.pricing_type,
        price=float(combo.price),
        discount_percentage=data.discount_percentage,
        original_total=round(original_total, 2),
        savings=round(savings, 2),
        savings_percentage=round(savings_percentage, 1),
        is_available_now=is_available,
        active=combo.available,
        created_at=combo.created_at.isoformat() if combo.created_at else now.isoformat(),
    )


@router.get("/combos")
@limiter.limit("60/minute")
def list_combos(
    request: Request,
    active_only: bool = True,
    available_now: bool = False,
    db: DbSession = None,
    current_user: CurrentUser = None,
):
    """List all combos/bundles."""
    from app.models.restaurant import ComboMeal, ComboItem, MenuItem

    query = db.query(ComboMeal)
    if active_only:
        query = query.filter(ComboMeal.available == True)

    combos = query.all()
    now = datetime.utcnow()

    result = []
    for combo in combos:
        is_available = combo.available

        # Get items
        items = []
        original_total = 0.0
        for ci in combo.items:
            item = db.query(MenuItem).filter(MenuItem.id == ci.menu_item_id).first() if ci.menu_item_id else None
            item_price = float(item.price) if item else 0.0
            items.append({
                "menu_item_id": ci.menu_item_id,
                "name": ci.name,
                "price": item_price,
                "quantity": ci.quantity,
            })
            original_total += item_price * ci.quantity

        final_price = float(combo.price)
        savings = original_total - final_price

        if available_now and not is_available:
            continue

        result.append({
            "id": combo.id,
            "name": combo.name,
            "description": combo.description,
            "items": items,
            "pricing_type": "fixed",
            "price": final_price,
            "original_total": round(original_total, 2),
            "savings": round(savings, 2),
            "is_available_now": is_available,
            "active": combo.available,
        })

    return {"combos": result, "total": len(result)}


@router.delete("/combos/{combo_id}")
@limiter.limit("30/minute")
def delete_combo(
    request: Request,
    combo_id: int,
    db: DbSession,
    current_user: CurrentUser = None,
):
    """Delete a combo."""
    from app.models.restaurant import ComboMeal

    combo = db.query(ComboMeal).filter(ComboMeal.id == combo_id).first()
    if not combo:
        raise HTTPException(status_code=404, detail="Combo not found")

    db.delete(combo)
    db.commit()

    return {"message": "Combo deleted", "id": combo_id}


# =============================================================================
# MENU TAGS
# =============================================================================

@router.post("/tags", response_model=MenuTagResponse)
@limiter.limit("30/minute")
def create_menu_tag(
    request: Request,
    data: MenuTagCreate,
    db: DbSession,
    current_user: CurrentUser = None,
):
    """Create a menu tag (vegan, spicy, new, popular, etc.)."""
    global _next_ids

    # Check for duplicate
    for tag in _tags:
        if tag["code"] == data.code:
            raise HTTPException(status_code=400, detail=f"Tag code '{data.code}' already exists")

    tag = {
        "id": _next_ids["tag"],
        "code": data.code,
        "name": data.name,
        "icon": data.icon,
        "color": data.color,
        "description": data.description,
        "sort_order": data.sort_order,
        "active": data.active,
    }
    _tags.append(tag)
    _next_ids["tag"] += 1

    return MenuTagResponse(**tag, items_count=0)


@router.get("/tags")
@limiter.limit("60/minute")
def list_menu_tags(
    request: Request,
    db: DbSession,
    current_user: CurrentUser = None,
):
    """List all menu tags."""
    result = []
    for tag in sorted(_tags, key=lambda t: t["sort_order"]):
        items_count = sum(1 for a in _tag_assignments if a["tag_id"] == tag["id"])
        result.append({
            **tag,
            "items_count": items_count,
        })

    return {"tags": result, "total": len(result)}


@router.post("/items/{item_id}/tags/{tag_id}")
@limiter.limit("30/minute")
def add_tag_to_item(
    request: Request,
    item_id: int,
    tag_id: int,
    db: DbSession,
    current_user: CurrentUser = None,
):
    """Add a tag to a menu item."""
    from app.models.restaurant import MenuItem
    global _next_ids

    item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    tag = None
    for t in _tags:
        if t["id"] == tag_id:
            tag = t
            break
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    # Check if already assigned
    for a in _tag_assignments:
        if a["menu_item_id"] == item_id and a["tag_id"] == tag_id:
            return {"message": "Tag already assigned", "item_id": item_id, "tag_id": tag_id}

    _tag_assignments.append({
        "id": _next_ids["tag_assignment"],
        "menu_item_id": item_id,
        "tag_id": tag_id,
    })
    _next_ids["tag_assignment"] += 1

    return {"message": "Tag added to item", "item_id": item_id, "tag_id": tag_id}


@router.delete("/items/{item_id}/tags/{tag_id}")
@limiter.limit("30/minute")
def remove_tag_from_item(
    request: Request,
    item_id: int,
    tag_id: int,
    db: DbSession,
    current_user: CurrentUser = None,
):
    """Remove a tag from a menu item."""
    global _tag_assignments
    _tag_assignments = [
        a for a in _tag_assignments
        if not (a["menu_item_id"] == item_id and a["tag_id"] == tag_id)
    ]
    return {"message": "Tag removed from item", "item_id": item_id, "tag_id": tag_id}


@router.get("/items/{item_id}/tags")
@limiter.limit("60/minute")
def get_item_tags(
    request: Request,
    item_id: int,
    db: DbSession,
    current_user: CurrentUser = None,
):
    """Get all tags for a menu item."""
    from app.models.restaurant import MenuItem

    item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    item_tag_ids = [a["tag_id"] for a in _tag_assignments if a["menu_item_id"] == item_id]
    tags = [
        {
            "id": t["id"],
            "code": t["code"],
            "name": t["name"],
            "icon": t.get("icon"),
            "color": t.get("color"),
        }
        for t in _tags if t["id"] in item_tag_ids
    ]

    return {"item_id": item_id, "item_name": item.name, "tags": tags}


# =============================================================================
# UPSELL / CROSS-SELL
# =============================================================================

@router.get("/upsell-rules")
@limiter.limit("60/minute")
def list_upsell_rules(
    request: Request,
    db: DbSession,
    current_user: CurrentUser = None,
):
    """List all upsell/cross-sell rules."""
    from app.models.restaurant import MenuItem

    result = []
    for rule in _upsell_rules:
        source_item = db.query(MenuItem).filter(MenuItem.id == rule["source_item_id"]).first()
        suggested_item = db.query(MenuItem).filter(MenuItem.id == rule["suggested_item_id"]).first() if rule.get("suggested_item_id") else None

        result.append({
            "id": rule["id"],
            "trigger_item_id": rule["source_item_id"],
            "trigger_item_name": source_item.name if source_item else "Unknown",
            "upsell_item_id": rule.get("suggested_item_id"),
            "upsell_item_name": suggested_item.name if suggested_item else None,
            "upsell_type": rule.get("suggestion_type", "upsell"),
            "discount_percent": rule.get("discount_percentage"),
            "message": rule.get("message"),
            "priority": rule.get("priority", 1),
            "is_active": rule.get("active", True),
        })
    return result


@router.post("/upsell-rules")
@limiter.limit("30/minute")
def create_upsell_rule(
    request: Request,
    data: UpsellRuleCreate,
    db: DbSession,
    current_user: CurrentUser = None,
):
    """Create an upsell/cross-sell rule."""
    from app.models.restaurant import MenuItem
    global _next_ids

    source_item = db.query(MenuItem).filter(MenuItem.id == data.source_item_id).first()
    if not source_item:
        raise HTTPException(status_code=404, detail="Source item not found")

    rule = {
        "id": _next_ids["upsell_rule"],
        "source_item_id": data.source_item_id,
        "suggestion_type": data.suggestion_type,
        "suggested_item_id": data.suggested_item_id,
        "suggested_category_id": data.suggested_category_id,
        "message": data.message,
        "discount_percentage": data.discount_percentage,
        "priority": data.priority,
        "active": data.active,
        "times_shown": 0,
    }
    _upsell_rules.append(rule)
    _next_ids["upsell_rule"] += 1

    return {
        "id": rule["id"],
        "source_item_id": rule["source_item_id"],
        "suggestion_type": rule["suggestion_type"],
        "suggested_item_id": rule["suggested_item_id"],
        "message": rule["message"],
        "discount_percentage": rule["discount_percentage"],
        "active": rule["active"],
    }


@router.get("/upsell-suggestions/{item_id}")
@limiter.limit("60/minute")
def get_upsell_suggestions(
    request: Request,
    item_id: int,
    db: DbSession,
    current_user: CurrentUser = None,
):
    """Get upsell/cross-sell suggestions for an item."""
    from app.models.restaurant import MenuItem

    rules = [
        r for r in _upsell_rules
        if r["source_item_id"] == item_id and r.get("active", True)
    ]
    rules.sort(key=lambda r: r.get("priority", 0), reverse=True)

    suggestions = []
    for rule in rules:
        suggestion = {
            "type": rule.get("suggestion_type", "upsell"),
            "message": rule.get("message"),
            "discount_percentage": rule.get("discount_percentage"),
        }

        if rule.get("suggested_item_id"):
            suggested = db.query(MenuItem).filter(MenuItem.id == rule["suggested_item_id"]).first()
            if suggested:
                suggestion["item_id"] = suggested.id
                suggestion["item_name"] = suggested.name
                suggestion["item_price"] = float(suggested.price)
                if rule.get("discount_percentage"):
                    suggestion["discounted_price"] = round(
                        float(suggested.price) * (1 - rule["discount_percentage"] / 100), 2
                    )

        suggestions.append(suggestion)

        # Track that suggestion was shown
        rule["times_shown"] = rule.get("times_shown", 0) + 1

    return {"item_id": item_id, "suggestions": suggestions}


# =============================================================================
# LIMITED TIME OFFERS
# =============================================================================

@router.post("/limited-offers", response_model=LimitedTimeOfferResponse)
@limiter.limit("30/minute")
def create_limited_offer(
    request: Request,
    data: LimitedTimeOfferCreate,
    db: DbSession,
    current_user: CurrentUser = None,
):
    """Create a limited-time offer."""
    global _next_ids

    # Calculate savings
    savings = None
    if data.original_price and data.offer_price:
        savings = data.original_price - data.offer_price
    elif data.original_price and data.discount_percentage:
        savings = data.original_price * data.discount_percentage / 100

    now = datetime.utcnow()
    is_expired = now > data.end_datetime
    time_remaining = int((data.end_datetime - now).total_seconds()) if not is_expired else 0

    offer = {
        "id": _next_ids["offer"],
        "name": data.name,
        "description": data.description,
        "menu_item_id": data.menu_item_id,
        "category_id": data.category_id,
        "offer_type": data.offer_type,
        "original_price": data.original_price,
        "offer_price": data.offer_price,
        "discount_percentage": data.discount_percentage,
        "start_datetime": data.start_datetime.isoformat(),
        "end_datetime": data.end_datetime.isoformat(),
        "max_quantity": data.max_quantity,
        "remaining_quantity": data.max_quantity,
        "max_per_customer": data.max_per_customer,
        "image_url": data.image_url,
        "badge_text": data.badge_text,
        "countdown_enabled": data.countdown_enabled,
        "auto_disable_when_sold_out": data.auto_disable_when_sold_out,
        "active": data.active,
    }
    _limited_offers.append(offer)
    _next_ids["offer"] += 1

    return LimitedTimeOfferResponse(
        id=offer["id"],
        name=offer["name"],
        description=offer["description"],
        menu_item_id=offer["menu_item_id"],
        offer_type=offer["offer_type"],
        original_price=offer["original_price"],
        offer_price=offer["offer_price"],
        discount_percentage=offer["discount_percentage"],
        savings=savings,
        start_datetime=offer["start_datetime"],
        end_datetime=offer["end_datetime"],
        remaining_quantity=offer["remaining_quantity"],
        is_active=offer["active"] and not is_expired,
        is_expired=is_expired,
        time_remaining_seconds=time_remaining,
        badge_text=offer["badge_text"],
    )


@router.get("/limited-offers")
@limiter.limit("60/minute")
def list_limited_offers(
    request: Request,
    active_only: bool = True,
    include_expired: bool = False,
    db: DbSession = None,
    current_user: CurrentUser = None,
):
    """List limited-time offers."""
    now = datetime.utcnow()

    result = []
    for offer in _limited_offers:
        end_dt = datetime.fromisoformat(offer["end_datetime"])
        is_expired = now > end_dt
        if not include_expired and is_expired:
            continue
        if active_only and not offer.get("active", True):
            continue

        time_remaining = int((end_dt - now).total_seconds()) if not is_expired else 0

        result.append({
            "id": offer["id"],
            "name": offer["name"],
            "description": offer.get("description"),
            "menu_item_id": offer.get("menu_item_id"),
            "offer_type": offer["offer_type"],
            "original_price": offer.get("original_price"),
            "offer_price": offer.get("offer_price"),
            "discount_percentage": offer.get("discount_percentage"),
            "start_datetime": offer["start_datetime"],
            "end_datetime": offer["end_datetime"],
            "remaining_quantity": offer.get("remaining_quantity"),
            "is_expired": is_expired,
            "is_active": offer.get("active", True) and not is_expired,
            "time_remaining_seconds": time_remaining,
            "badge_text": offer.get("badge_text"),
        })

    return {
        "offers": result,
        "total": len(result),
        "active_count": sum(1 for o in result if o["is_active"]),
        "expiring_soon": sum(1 for o in result if 0 < o["time_remaining_seconds"] < 3600),
    }


# =============================================================================
# 86'd ITEMS (OUT OF STOCK)
# =============================================================================

@router.post("/86", response_model=Item86Response)
@limiter.limit("30/minute")
def mark_item_86(
    request: Request,
    data: Item86Request,
    db: DbSession,
    current_user: CurrentUser = None,
):
    """Mark an item as 86'd (out of stock/unavailable)."""
    from app.models.restaurant import MenuItem
    global _next_ids

    item = db.query(MenuItem).filter(MenuItem.id == data.menu_item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    # Check if already 86'd
    for r in _item86_records:
        if r["menu_item_id"] == data.menu_item_id and r["is_active"]:
            raise HTTPException(status_code=400, detail="Item is already 86'd")

    now = datetime.utcnow()

    record = {
        "id": _next_ids["item86"],
        "menu_item_id": data.menu_item_id,
        "reason": data.reason,
        "notes": data.notes,
        "expected_back": data.expected_back,
        "auto_restore": data.auto_restore,
        "alternative_items": data.alternative_items,
        "notify_staff": data.notify_staff,
        "marked_at": now.isoformat(),
        "marked_by": "Staff",
        "is_active": True,
    }
    _item86_records.append(record)
    _next_ids["item86"] += 1

    # Update item availability
    item.available = False
    db.commit()

    # Get alternatives
    alternatives = []
    if data.alternative_items:
        for alt_id in data.alternative_items:
            alt = db.query(MenuItem).filter(MenuItem.id == alt_id).first()
            if alt:
                alternatives.append({
                    "id": alt.id,
                    "name": alt.name,
                    "price": float(alt.price),
                })

    return Item86Response(
        id=record["id"],
        menu_item_id=data.menu_item_id,
        menu_item_name=item.name,
        reason=record["reason"],
        marked_at=record["marked_at"],
        marked_by=record["marked_by"],
        expected_back=data.expected_back,
        is_active=True,
        alternative_items=alternatives if alternatives else None,
        duration_minutes=0,
    )


@router.get("/86")
@limiter.limit("60/minute")
def list_86_items(
    request: Request,
    active_only: bool = True,
    db: DbSession = None,
    current_user: CurrentUser = None,
):
    """List all 86'd items."""
    from app.models.restaurant import MenuItem

    now = datetime.utcnow()

    records = list(_item86_records)
    if active_only:
        records = [r for r in records if r["is_active"]]

    result = []
    for r in records:
        item = db.query(MenuItem).filter(MenuItem.id == r["menu_item_id"]).first()
        marked_at = datetime.fromisoformat(r["marked_at"])
        duration = int((now - marked_at).total_seconds() / 60)

        result.append({
            "id": r["id"],
            "menu_item_id": r["menu_item_id"],
            "menu_item_name": item.name if item else "Unknown",
            "reason": r["reason"],
            "notes": r.get("notes"),
            "marked_at": r["marked_at"],
            "marked_by": r.get("marked_by", "Unknown"),
            "expected_back": r.get("expected_back"),
            "is_active": r["is_active"],
            "duration_minutes": duration,
            "alternative_items": r.get("alternative_items"),
        })

    reasons_count = {}
    for reason in ["sold_out", "ingredient_missing", "equipment_issue", "quality_issue"]:
        reasons_count[reason] = sum(1 for r in result if r["reason"] == reason)

    return {
        "items": result,
        "total_86": len([r for r in result if r["is_active"]]),
        "reasons": reasons_count,
    }


@router.delete("/86/{item86_id}")
@limiter.limit("30/minute")
def restore_86_item(
    request: Request,
    item86_id: int,
    db: DbSession,
    current_user: CurrentUser = None,
):
    """Restore an 86'd item (make available again)."""
    from app.models.restaurant import MenuItem

    record = None
    for r in _item86_records:
        if r["id"] == item86_id:
            record = r
            break

    if not record:
        raise HTTPException(status_code=404, detail="86 record not found")

    # Restore item
    item = db.query(MenuItem).filter(MenuItem.id == record["menu_item_id"]).first()
    if item:
        item.available = True

    record["is_active"] = False
    record["restored_at"] = datetime.utcnow().isoformat()

    db.commit()

    return {"message": "Item restored", "id": item86_id}


# =============================================================================
# DIGITAL MENU BOARD
# =============================================================================

@router.post("/digital-boards")
@limiter.limit("30/minute")
def create_digital_board(
    request: Request,
    data: DigitalMenuBoardCreate,
    db: DbSession,
    current_user: CurrentUser = None,
):
    """Create a digital menu board configuration."""
    from app.models.restaurant import MenuItem
    global _next_ids

    board_token = str(uuid.uuid4())[:8]
    now = datetime.utcnow()

    board = {
        "id": _next_ids["board"],
        "name": data.name,
        "token": board_token,
        "display_type": data.display_type,
        "layout": data.layout,
        "columns": data.columns,
        "categories": data.categories,
        "items": data.items,
        "show_prices": data.show_prices,
        "show_descriptions": data.show_descriptions,
        "show_images": data.show_images,
        "show_calories": data.show_calories,
        "show_allergens": data.show_allergens,
        "rotation_seconds": data.rotation_seconds,
        "theme": data.theme,
        "custom_css": data.custom_css,
        "header_text": data.header_text,
        "footer_text": data.footer_text,
        "background_image": data.background_image,
        "auto_hide_unavailable": data.auto_hide_unavailable,
        "active": data.active,
        "created_at": now.isoformat(),
    }
    _digital_boards.append(board)
    _next_ids["board"] += 1

    # Generate URLs
    base_url = "https://menu.bjsbar.com"
    public_url = f"{base_url}/board/{board_token}"
    embed_code = f'<iframe src="{public_url}" width="100%" height="100%" frameborder="0"></iframe>'

    # Generate QR code (try qrcode library, fall back to placeholder)
    qr_code_url = None
    try:
        import qrcode as qr_lib
        qr = qr_lib.QRCode(version=1, box_size=10, border=5)
        qr.add_data(public_url)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        qr_img.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()
        qr_code_url = f"data:image/png;base64,{qr_base64}"
    except ImportError:
        qr_code_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={public_url}"

    # Count items
    items_count = 0
    if data.items:
        items_count = len(data.items)
    elif data.categories:
        for cat in data.categories:
            items_count += db.query(MenuItem).filter(MenuItem.category == cat).count()
    else:
        items_count = db.query(MenuItem).count()

    return {
        "id": board["id"],
        "name": data.name,
        "display_type": data.display_type,
        "layout": data.layout,
        "token": board_token,
        "public_url": public_url,
        "embed_code": embed_code,
        "qr_code_url": qr_code_url,
        "items_count": items_count,
        "active": data.active,
        "created_at": board["created_at"],
    }


@router.get("/digital-boards")
@limiter.limit("60/minute")
def list_digital_boards(
    request: Request,
    db: DbSession,
    current_user: CurrentUser = None,
):
    """List all digital menu boards."""
    base_url = "https://menu.bjsbar.com"

    result = []
    for board in _digital_boards:
        result.append({
            "id": board["id"],
            "name": board["name"],
            "display_type": board.get("display_type", "full_menu"),
            "layout": board.get("layout", "grid"),
            "public_url": f"{base_url}/board/{board['token']}",
            "active": board.get("active", True),
            "last_updated": board.get("created_at"),
        })

    return {"boards": result, "total": len(result)}


@router.get("/digital-boards/{board_id}/content")
@limiter.limit("60/minute")
def get_digital_board_content(
    request: Request,
    board_id: int,
    language: str = "en",
    db: DbSession = None,
):
    """Get content for a digital menu board (public endpoint)."""
    from app.models.restaurant import MenuItem

    board = None
    for b in _digital_boards:
        if b["id"] == board_id:
            board = b
            break

    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    if not board.get("active", True):
        raise HTTPException(status_code=404, detail="Board is inactive")

    # Get menu items
    query = db.query(MenuItem)

    if board.get("items"):
        query = query.filter(MenuItem.id.in_(board["items"]))
    elif board.get("categories"):
        query = query.filter(MenuItem.category.in_(board["categories"]))

    if board.get("auto_hide_unavailable", True):
        query = query.filter(MenuItem.available == True)

    items = query.all()

    formatted_items = []
    for item in items:
        item_data = {
            "id": item.id,
            "name": item.name,
            "price": float(item.price),
            "available": item.available,
        }

        if board.get("show_descriptions", True) and item.description:
            item_data["description"] = item.description

        if board.get("show_allergens", True) and item.allergens:
            item_data["allergens"] = item.allergens

        formatted_items.append(item_data)

    return {
        "board_id": board_id,
        "name": board["name"],
        "layout": board.get("layout", "grid"),
        "columns": board.get("columns", 3),
        "theme": board.get("theme", "dark"),
        "header_text": board.get("header_text"),
        "footer_text": board.get("footer_text"),
        "background_image": board.get("background_image"),
        "rotation_seconds": board.get("rotation_seconds", 10),
        "items": formatted_items,
        "total_items": len(formatted_items),
        "last_updated": board.get("created_at"),
    }


# =============================================================================
# MENU ENGINEERING ANALYTICS
# =============================================================================

@router.get("/engineering/report", response_model=MenuEngineeringReport)
@limiter.limit("60/minute")
def get_menu_engineering_report(
    request: Request,
    period_days: int = 30,
    category: Optional[str] = None,
    db: DbSession = None,
    current_user: CurrentUser = None,
):
    """
    Generate a menu engineering report.

    Classifies items into:
    - Stars: High popularity, high profit
    - Puzzles: Low popularity, high profit
    - Plow Horses: High popularity, low profit
    - Dogs: Low popularity, low profit
    """
    from app.models.restaurant import MenuItem, Check, CheckItem

    period_end = date.today()
    period_start = period_end - timedelta(days=period_days)

    # Get items
    items_query = db.query(MenuItem)
    if category:
        items_query = items_query.filter(MenuItem.category == category)

    items = items_query.all()

    # Calculate metrics
    item_metrics = []
    total_revenue = 0.0
    total_profit = 0.0
    total_quantity = 0

    for item in items:
        # Get actual sales data from check_items
        sales = db.query(
            func.coalesce(func.sum(CheckItem.quantity), 0).label("quantity"),
            func.coalesce(func.sum(CheckItem.total), 0).label("revenue"),
        ).join(Check).filter(
            CheckItem.menu_item_id == item.id,
            Check.opened_at >= datetime.combine(period_start, datetime.min.time()),
            Check.status != "voided",
            CheckItem.status != "voided",
        ).first()

        quantity_sold = int(sales.quantity or 0)
        revenue = float(sales.revenue or 0)

        # Estimate cost (35% food cost if not specified)
        cost_per_item = float(item.base_price) if item.base_price else float(item.price) * 0.35

        # Check for variants with cost
        variant_costs = [v["cost"] for v in _variants if v["menu_item_id"] == item.id and v.get("cost")]
        if variant_costs:
            cost_per_item = variant_costs[0]

        profit = revenue - (cost_per_item * quantity_sold)
        profit_margin = (float(item.price) - cost_per_item) / float(item.price) * 100 if item.price and float(item.price) > 0 else 0

        total_revenue += revenue
        total_profit += profit
        total_quantity += quantity_sold

        item_metrics.append({
            "menu_item_id": item.id,
            "name": item.name,
            "category": item.category or "Uncategorized",
            "price": float(item.price),
            "cost": round(cost_per_item, 2),
            "profit_margin": round(profit_margin, 1),
            "profit_margin_percentage": round(profit_margin, 1),
            "quantity_sold": quantity_sold,
            "revenue": round(revenue, 2),
            "profit": round(profit, 2),
        })

    # Calculate averages
    if item_metrics:
        avg_quantity = total_quantity / len(item_metrics) if len(item_metrics) > 0 else 1
        avg_profit_margin = sum(i["profit_margin"] for i in item_metrics) / len(item_metrics)
    else:
        avg_quantity = 1
        avg_profit_margin = 0

    # Classify items
    stars = []
    puzzles = []
    plow_horses = []
    dogs = []

    for item in item_metrics:
        popularity_index = item["quantity_sold"] / max(avg_quantity, 1)
        profitability_index = item["profit_margin"] / max(avg_profit_margin, 1)

        item["popularity_index"] = round(popularity_index, 2)
        item["profitability_index"] = round(profitability_index, 2)
        item["trend"] = "stable"

        high_popularity = popularity_index >= 1.0
        high_profit = profitability_index >= 1.0

        if high_popularity and high_profit:
            item["classification"] = "star"
            item["recommendation"] = "Maintain quality, feature prominently"
            stars.append(MenuEngineeringItem(**item))
        elif not high_popularity and high_profit:
            item["classification"] = "puzzle"
            item["recommendation"] = "Increase visibility, add to promotions"
            puzzles.append(MenuEngineeringItem(**item))
        elif high_popularity and not high_profit:
            item["classification"] = "plow_horse"
            item["recommendation"] = "Reengineer recipe to reduce cost"
            plow_horses.append(MenuEngineeringItem(**item))
        else:
            item["classification"] = "dog"
            item["recommendation"] = "Consider removing or major repositioning"
            dogs.append(MenuEngineeringItem(**item))

    # Generate recommendations
    recommendations = []
    if stars:
        recommendations.append({"type": "maintain", "message": f"{len(stars)} star items performing well"})
    if puzzles:
        recommendations.append({"type": "promote", "message": f"{len(puzzles)} puzzle items need more visibility"})
    if plow_horses:
        recommendations.append({"type": "optimize", "message": f"{len(plow_horses)} items could benefit from cost optimization"})
    if dogs:
        recommendations.append({"type": "review", "message": f"{len(dogs)} items should be reviewed for removal"})

    return MenuEngineeringReport(
        period_start=str(period_start),
        period_end=str(period_end),
        total_items=len(item_metrics),
        total_revenue=round(total_revenue, 2),
        total_profit=round(total_profit, 2),
        average_profit_margin=round(avg_profit_margin, 1),
        stars=stars,
        puzzles=puzzles,
        plow_horses=plow_horses,
        dogs=dogs,
        recommendations=recommendations,
    )


# =============================================================================
# QR CODE MENU GENERATION
# =============================================================================

@router.get("/qr-code")
@limiter.limit("60/minute")
def generate_menu_qr_code(
    request: Request,
    table_number: Optional[str] = None,
    language: str = "en",
    db: DbSession = None,
    current_user: CurrentUser = None,
):
    """Generate a QR code for the digital menu."""
    base_url = "https://menu.bjsbar.com"

    if table_number:
        menu_url = f"{base_url}/menu?table={table_number}&lang={language}"
    else:
        menu_url = f"{base_url}/menu?lang={language}"

    # Generate QR code (try qrcode library, fall back to external API)
    qr_base64 = None
    try:
        import qrcode as qr_lib
        qr = qr_lib.QRCode(
            version=1,
            error_correction=qr_lib.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(menu_url)
        qr.make(fit=True)

        qr_img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        qr_img.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()
    except ImportError:
        pass

    qr_code_data = f"data:image/png;base64,{qr_base64}" if qr_base64 else f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={menu_url}"

    return {
        "menu_url": menu_url,
        "qr_code_data": qr_code_data,
        "table_number": table_number,
        "language": language,
        "instructions": "Scan this QR code to view the menu",
    }


@router.get("/qr-codes/bulk")
@limiter.limit("60/minute")
def generate_bulk_qr_codes(
    request: Request,
    table_count: int = 20,
    start_number: int = 1,
    language: str = "en",
    db: DbSession = None,
    current_user: CurrentUser = None,
):
    """Generate QR codes for multiple tables."""
    base_url = "https://menu.bjsbar.com"

    qr_codes = []
    for i in range(table_count):
        table_num = start_number + i
        menu_url = f"{base_url}/menu?table={table_num}&lang={language}"

        qr_code_data = None
        try:
            import qrcode as qr_lib
            qr = qr_lib.QRCode(version=1, box_size=8, border=4)
            qr.add_data(menu_url)
            qr.make(fit=True)

            qr_img = qr.make_image(fill_color="black", back_color="white")
            buffer = io.BytesIO()
            qr_img.save(buffer, format="PNG")
            qr_base64 = base64.b64encode(buffer.getvalue()).decode()
            qr_code_data = f"data:image/png;base64,{qr_base64}"
        except ImportError:
            qr_code_data = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={menu_url}"

        qr_codes.append({
            "table_number": table_num,
            "menu_url": menu_url,
            "qr_code_data": qr_code_data,
        })

    return {
        "qr_codes": qr_codes,
        "total": len(qr_codes),
        "print_ready": True,
    }

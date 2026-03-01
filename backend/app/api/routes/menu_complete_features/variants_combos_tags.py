"""Variants, combos, tags & upsell rules"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Dict, Optional, Any
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal

from app.core.rate_limit import limiter
from app.db.session import get_db

# Import shared schemas and helpers
from app.api.routes.menu_complete_features._shared import *
from app.api.routes.menu_complete_features._shared import _variants, _next_ids, _tags, _tag_assignments, _upsell_rules

router = APIRouter()

@router.get("/")
@limiter.limit("60/minute")
def get_menu_complete_features_root(request: Request, db: DbSession):
    """Menu features overview."""
    return list_menu_tags(request=request, db=db)


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

    now = datetime.now(timezone.utc)

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
    now = datetime.now(timezone.utc)

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


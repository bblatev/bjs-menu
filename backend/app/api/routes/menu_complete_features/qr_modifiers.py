"""QR codes, modifier groups & item management"""
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
from app.api.routes.menu_complete_features._shared import _tags, _tag_assignments, _upsell_rules, _limited_offers, _digital_boards

router = APIRouter()

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


# =============================================================================
# ENDPOINTS MIGRATED FROM menu_complete.py
# =============================================================================

# --- Schemas for migrated modifier / menu-item endpoints ---

class _MultiLang(BaseModel):
    bg: str = ""
    en: str = ""
    de: Optional[str] = None
    ru: Optional[str] = None


class _ModifierGroupSchema(BaseModel):
    id: Optional[int] = None
    name: _MultiLang
    required: bool = False
    min_selections: int = 0
    max_selections: int = 1
    is_active: bool = True


class _ModifierOptionSchema(BaseModel):
    id: Optional[int] = None
    group_id: int
    name: _MultiLang
    price: float = 0
    is_active: bool = True


# --- Modifier Groups (DB-backed) ---

@router.get("/modifier-groups")
@limiter.limit("60/minute")
def get_modifier_groups(request: Request, db: DbSession):
    """List all modifier groups from the database."""
    from app.models.restaurant import ModifierGroup as ModifierGroupModel
    groups = (
        db.query(ModifierGroupModel)
        .filter(ModifierGroupModel.active == True)
        .order_by(ModifierGroupModel.sort_order)
        .all()
    )
    return [
        {
            "id": g.id,
            "name": {"bg": g.name, "en": g.name},
            "required": g.min_selections > 0,
            "min_selections": g.min_selections,
            "max_selections": g.max_selections,
            "is_active": g.active,
        }
        for g in groups
    ]


@router.post("/modifier-groups")
@limiter.limit("30/minute")
def create_modifier_group(request: Request, item: _ModifierGroupSchema, db: DbSession):
    """Create a modifier group in the database."""
    from app.models.restaurant import ModifierGroup as ModifierGroupModel
    group = ModifierGroupModel(
        name=item.name.en or item.name.bg,
        min_selections=item.min_selections,
        max_selections=item.max_selections,
        active=item.is_active,
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    return {
        "id": group.id,
        "name": item.name.model_dump(),
        "required": item.required,
        "min_selections": group.min_selections,
        "max_selections": group.max_selections,
        "is_active": group.active,
    }


# --- Modifier Options (DB-backed) ---

@router.get("/modifier-options")
@limiter.limit("60/minute")
def get_modifier_options(request: Request, db: DbSession):
    """List all modifier options from the database."""
    from app.models.restaurant import ModifierOption as ModifierOptionModel
    options = (
        db.query(ModifierOptionModel)
        .filter(ModifierOptionModel.available == True)
        .order_by(ModifierOptionModel.sort_order)
        .all()
    )
    return [
        {
            "id": o.id,
            "group_id": o.group_id,
            "name": {"bg": o.name, "en": o.name},
            "price": float(o.price_adjustment),
            "is_active": o.available,
        }
        for o in options
    ]


@router.post("/modifier-options")
@limiter.limit("30/minute")
def create_modifier_option(request: Request, item: _ModifierOptionSchema, db: DbSession):
    """Create a modifier option in the database."""
    from app.models.restaurant import ModifierOption as ModifierOptionModel
    option = ModifierOptionModel(
        group_id=item.group_id,
        name=item.name.en or item.name.bg,
        price_adjustment=item.price,
        available=item.is_active,
    )
    db.add(option)
    db.commit()
    db.refresh(option)
    return {
        "id": option.id,
        "group_id": option.group_id,
        "name": item.name.model_dump(),
        "price": float(option.price_adjustment),
        "is_active": option.available,
    }


# --- Menu Items listing (DB-backed) ---

@router.get("/items")
@limiter.limit("60/minute")
def get_menu_complete_items(request: Request, db: DbSession):
    """Get all menu items with complete details."""
    from app.models.restaurant import MenuItem
    items = db.query(MenuItem).filter(MenuItem.available == True).all()
    return [
        {
            "id": i.id,
            "name": i.name,
            "price": float(i.price) if i.price else 0,
            "category": i.category,
            "available": i.available,
        }
        for i in items
    ]


# --- Delete endpoints (tags, upsell-rules, limited-offers, digital-boards) ---

@router.delete("/tags/{tag_id}")
@limiter.limit("30/minute")
def delete_menu_tag(
    request: Request,
    tag_id: int,
    db: DbSession,
    current_user: CurrentUser = None,
):
    """Delete a menu tag."""
    global _tags, _tag_assignments
    found = False
    for t in _tags:
        if t["id"] == tag_id:
            found = True
            break
    if not found:
        raise HTTPException(status_code=404, detail="Tag not found")
    _tags = [t for t in _tags if t["id"] != tag_id]
    _tag_assignments = [a for a in _tag_assignments if a["tag_id"] != tag_id]
    return {"message": "Tag deleted", "id": tag_id}


@router.delete("/upsell-rules/{rule_id}")
@limiter.limit("30/minute")
def delete_upsell_rule(
    request: Request,
    rule_id: int,
    db: DbSession,
    current_user: CurrentUser = None,
):
    """Delete an upsell/cross-sell rule."""
    global _upsell_rules
    found = False
    for r in _upsell_rules:
        if r["id"] == rule_id:
            found = True
            break
    if not found:
        raise HTTPException(status_code=404, detail="Upsell rule not found")
    _upsell_rules = [r for r in _upsell_rules if r["id"] != rule_id]
    return {"message": "Upsell rule deleted", "id": rule_id}


@router.delete("/limited-offers/{offer_id}")
@limiter.limit("30/minute")
def delete_limited_offer(
    request: Request,
    offer_id: int,
    db: DbSession,
    current_user: CurrentUser = None,
):
    """Delete a limited-time offer."""
    global _limited_offers
    found = False
    for o in _limited_offers:
        if o["id"] == offer_id:
            found = True
            break
    if not found:
        raise HTTPException(status_code=404, detail="Limited offer not found")
    _limited_offers = [o for o in _limited_offers if o["id"] != offer_id]
    return {"message": "Limited offer deleted", "id": offer_id}


@router.delete("/digital-boards/{board_id}")
@limiter.limit("30/minute")
def delete_digital_board(
    request: Request,
    board_id: int,
    db: DbSession,
    current_user: CurrentUser = None,
):
    """Delete a digital menu board."""
    global _digital_boards
    found = False
    for b in _digital_boards:
        if b["id"] == board_id:
            found = True
            break
    if not found:
        raise HTTPException(status_code=404, detail="Digital board not found")
    _digital_boards = [b for b in _digital_boards if b["id"] != board_id]
    return {"message": "Digital board deleted", "id": board_id}

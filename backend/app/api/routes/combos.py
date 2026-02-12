"""
Combo Menus & Set Meals API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, time
from pydantic import BaseModel, ConfigDict

from app.db.session import get_db
from app.core.rbac import get_current_user
from app.models import (
    ComboMenu, ComboMenuItem, MenuItem, StaffUser
)


router = APIRouter()


# Schemas
class ComboItemInput(BaseModel):
    menu_item_id: int
    quantity: int = 1
    is_optional: bool = False
    group_name: Optional[str] = None  # For "choose one from" groups


class ComboCreate(BaseModel):
    name: dict  # {"bg": "...", "en": "..."}
    description: Optional[dict] = None
    combo_price: float
    original_price: Optional[float] = None  # Auto-calculated if not provided
    items: List[ComboItemInput]
    available_from: Optional[time] = None
    available_until: Optional[time] = None
    days_available: Optional[List[int]] = None  # 0=Mon, 6=Sun
    max_per_order: Optional[int] = None
    image_url: Optional[str] = None


class ComboUpdate(BaseModel):
    name: Optional[dict] = None
    description: Optional[dict] = None
    combo_price: Optional[float] = None
    available_from: Optional[time] = None
    available_until: Optional[time] = None
    days_available: Optional[List[int]] = None
    max_per_order: Optional[int] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None


class ComboResponse(BaseModel):
    id: int
    venue_id: int
    name: dict
    description: Optional[dict]
    combo_price: float
    original_price: float
    savings: float
    savings_percent: float
    is_active: bool
    available_from: Optional[time]
    available_until: Optional[time]
    days_available: Optional[List[int]]
    image_url: Optional[str]
    items: List[dict]

    model_config = ConfigDict(from_attributes=True)


# CRUD Operations
@router.post("/", response_model=ComboResponse)
def create_combo(
    data: ComboCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Create a new combo menu"""
    # Calculate original price from items
    original_price = 0
    for item_input in data.items:
        menu_item = db.query(MenuItem).filter(
            MenuItem.id == item_input.menu_item_id,
            MenuItem.venue_id == current_user.venue_id
        ).first()
        if not menu_item:
            raise HTTPException(
                status_code=404,
                detail=f"Menu item {item_input.menu_item_id} not found"
            )
        original_price += menu_item.price * item_input.quantity

    # Use provided original_price or calculated
    final_original_price = data.original_price if data.original_price else original_price

    combo = ComboMenu(
        venue_id=current_user.venue_id,
        name=data.name,
        description=data.description,
        combo_price=data.combo_price,
        original_price=final_original_price,
        available_from=data.available_from,
        available_until=data.available_until,
        days_available=data.days_available,
        max_per_order=data.max_per_order,
        image_url=data.image_url,
        is_active=True,
        created_by=current_user.id
    )
    db.add(combo)
    db.flush()

    # Add combo items
    for item_input in data.items:
        combo_item = ComboMenuItem(
            combo_id=combo.id,
            menu_item_id=item_input.menu_item_id,
            quantity=item_input.quantity,
            is_optional=item_input.is_optional,
            group_name=item_input.group_name
        )
        db.add(combo_item)

    db.commit()
    db.refresh(combo)

    return _combo_to_response(combo, db)


@router.get("/", response_model=List[ComboResponse])
def list_combos(
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List all combo menus"""
    query = db.query(ComboMenu).filter(ComboMenu.venue_id == current_user.venue_id)

    if active_only:
        query = query.filter(ComboMenu.is_active == True)

    combos = query.order_by(ComboMenu.created_at.desc()).all()

    return [_combo_to_response(c, db) for c in combos]


@router.get("/available", response_model=List[ComboResponse])
def get_available_combos(
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get currently available combos (based on time/day restrictions)"""
    now = datetime.utcnow()
    current_time = now.time()
    current_day = now.weekday()

    combos = db.query(ComboMenu).filter(
        ComboMenu.venue_id == current_user.venue_id,
        ComboMenu.is_active == True
    ).all()

    available = []
    for combo in combos:
        # Check time availability
        if combo.available_from and current_time < combo.available_from:
            continue
        if combo.available_until and current_time > combo.available_until:
            continue
        # Check day availability
        if combo.days_available and current_day not in combo.days_available:
            continue
        available.append(combo)

    return [_combo_to_response(c, db) for c in available]


@router.get("/{combo_id}", response_model=ComboResponse)
def get_combo(
    combo_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get a specific combo"""
    combo = db.query(ComboMenu).filter(
        ComboMenu.id == combo_id,
        ComboMenu.venue_id == current_user.venue_id
    ).first()

    if not combo:
        raise HTTPException(status_code=404, detail="Combo not found")

    return _combo_to_response(combo, db)


@router.put("/{combo_id}", response_model=ComboResponse)
def update_combo(
    combo_id: int,
    data: ComboUpdate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Update a combo"""
    combo = db.query(ComboMenu).filter(
        ComboMenu.id == combo_id,
        ComboMenu.venue_id == current_user.venue_id
    ).first()

    if not combo:
        raise HTTPException(status_code=404, detail="Combo not found")

    for field, value in data.dict(exclude_unset=True).items():
        setattr(combo, field, value)

    db.commit()
    db.refresh(combo)

    return _combo_to_response(combo, db)


@router.delete("/{combo_id}")
def delete_combo(
    combo_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Delete a combo (soft delete by deactivating)"""
    combo = db.query(ComboMenu).filter(
        ComboMenu.id == combo_id,
        ComboMenu.venue_id == current_user.venue_id
    ).first()

    if not combo:
        raise HTTPException(status_code=404, detail="Combo not found")

    combo.is_active = False
    db.commit()

    return {"message": "Combo deleted", "combo_id": combo_id}


# Combo Items Management
@router.post("/{combo_id}/items")
def add_combo_item(
    combo_id: int,
    item: ComboItemInput,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Add an item to a combo"""
    combo = db.query(ComboMenu).filter(
        ComboMenu.id == combo_id,
        ComboMenu.venue_id == current_user.venue_id
    ).first()

    if not combo:
        raise HTTPException(status_code=404, detail="Combo not found")

    # Verify menu item exists
    menu_item = db.query(MenuItem).filter(
        MenuItem.id == item.menu_item_id,
        MenuItem.venue_id == current_user.venue_id
    ).first()

    if not menu_item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    combo_item = ComboMenuItem(
        combo_id=combo_id,
        menu_item_id=item.menu_item_id,
        quantity=item.quantity,
        is_optional=item.is_optional,
        group_name=item.group_name
    )
    db.add(combo_item)

    # Update original price
    combo.original_price += menu_item.price * item.quantity

    db.commit()

    return {"message": "Item added to combo"}


@router.delete("/{combo_id}/items/{item_id}")
def remove_combo_item(
    combo_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Remove an item from a combo"""
    combo_item = db.query(ComboMenuItem).filter(
        ComboMenuItem.combo_id == combo_id,
        ComboMenuItem.id == item_id
    ).first()

    if not combo_item:
        raise HTTPException(status_code=404, detail="Combo item not found")

    # Update original price
    combo = db.query(ComboMenu).filter(ComboMenu.id == combo_id).first()
    menu_item = db.query(MenuItem).filter(MenuItem.id == combo_item.menu_item_id).first()
    if combo and menu_item:
        combo.original_price -= menu_item.price * combo_item.quantity

    db.delete(combo_item)
    db.commit()

    return {"message": "Item removed from combo"}


# Helper function
def _combo_to_response(combo: ComboMenu, db: Session) -> dict:
    """Convert combo to response with items"""
    combo_items = db.query(ComboMenuItem).filter(
        ComboMenuItem.combo_id == combo.id
    ).all()

    items = []
    for ci in combo_items:
        menu_item = db.query(MenuItem).filter(MenuItem.id == ci.menu_item_id).first()
        if menu_item:
            items.append({
                "id": ci.id,
                "menu_item_id": ci.menu_item_id,
                "name": menu_item.name,
                "price": menu_item.price,
                "quantity": ci.quantity,
                "is_optional": ci.is_optional,
                "group_name": ci.group_name
            })

    savings = combo.original_price - combo.combo_price
    savings_percent = (savings / combo.original_price * 100) if combo.original_price > 0 else 0

    return {
        "id": combo.id,
        "venue_id": combo.venue_id,
        "name": combo.name,
        "description": combo.description,
        "combo_price": combo.combo_price,
        "original_price": combo.original_price,
        "savings": savings,
        "savings_percent": round(savings_percent, 1),
        "is_active": combo.is_active,
        "available_from": combo.available_from,
        "available_until": combo.available_until,
        "days_available": combo.days_available,
        "image_url": combo.image_url,
        "items": items
    }

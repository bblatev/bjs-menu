"""Menu browsing & table management"""
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
from app.api.routes.guest_orders._shared import _get_table_by_token, _menu_item_to_dict, _get_venue_name

# ==================== ROUTES ====================

@router.get("/")
@limiter.limit("60/minute")
def get_guest_orders_root(request: Request, db: DbSession):
    """Guest ordering overview."""
    return {"module": "guest-orders", "status": "active", "endpoints": ["/menu/items", "/menu/categories", "/menu/display", "/menu/table/{token}"]}


@router.get("/menu/table/{token}")
@limiter.limit("60/minute")
def get_table_menu(
    request: Request,
    db: DbSession,
    token: str,
):
    """
    Get table information and menu for guest ordering.
    This endpoint is used by the customer-facing QR code ordering page.
    """
    table = _get_table_by_token(db, token)

    # Get menu items from database
    menu_items = db.query(MenuItem).filter(MenuItem.available == True, MenuItem.not_deleted()).limit(500).all()

    # Group menu items by category
    categories = {}
    for item in menu_items:
        cat = item.category
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(_menu_item_to_dict(item))

    menu_categories = [
        {"id": i + 1, "name": cat, "items": items}
        for i, (cat, items) in enumerate(categories.items())
    ]

    return {
        "table": {
            **table,
            "venue_name": _get_venue_name(db),
        },
        "categories": menu_categories,
        "menu": {
            "categories": menu_categories,
            "total_items": len(menu_items),
        },
    }


@router.get("/menu/items")
@limiter.limit("60/minute")
def get_menu_items(
    request: Request,
    db: DbSession,
    category: Optional[str] = None,
    available_only: bool = True,
):
    """Get all menu items, optionally filtered by category."""
    query = db.query(MenuItem).filter(MenuItem.not_deleted())
    if category:
        query = query.filter(MenuItem.category == category)
    if available_only:
        query = query.filter(MenuItem.available == True)

    items = query.all()
    return {"items": [_menu_item_to_dict(i) for i in items], "total": len(items)}


@router.get("/menu/items/{item_id}")
@limiter.limit("60/minute")
def get_menu_item(request: Request, db: DbSession, item_id: int):
    """Get a specific menu item."""
    item = db.query(MenuItem).filter(MenuItem.id == item_id, MenuItem.not_deleted()).first()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    return _menu_item_to_dict(item)


@router.get("/menu/categories")
@limiter.limit("60/minute")
def get_menu_categories(request: Request, db: DbSession):
    """Get all menu categories."""
    items = db.query(MenuItem).filter(MenuItem.available == True, MenuItem.not_deleted()).all()
    categories = list(set(item.category for item in items))
    return {"categories": categories}


@router.get("/menu/display")
@limiter.limit("60/minute")
def get_menu_display(request: Request, db: DbSession):
    """Get full menu display for guests (grouped by category)."""
    items = db.query(MenuItem).filter(MenuItem.available == True, MenuItem.not_deleted()).all()
    categories_dict: dict = {}
    for item in items:
        cat = item.category or "Other"
        if cat not in categories_dict:
            categories_dict[cat] = []
        categories_dict[cat].append(_menu_item_to_dict(item))
    return {
        "categories": [
            {"name": cat, "items": cat_items}
            for cat, cat_items in categories_dict.items()
        ],
        "total_items": len(items),
    }


# ==================== MENU ITEM CRUD ====================

@router.post("/menu/items")
@limiter.limit("30/minute")
def create_menu_item(request: Request, db: DbSession, item: MenuItemCreate):
    """Create a new menu item."""
    db_item = MenuItem(
        name=item.name,
        description=item.description,
        price=Decimal(str(item.price)),
        category=item.category,
        image_url=item.image_url,
        available=item.available,
        allergens=item.allergens,
        modifiers=item.modifiers,
        prep_time_minutes=item.prep_time_minutes,
        station=item.station,
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return {
        "status": "created",
        "item": _menu_item_to_dict(db_item),
    }


@router.put("/menu/items/{item_id}")
@limiter.limit("30/minute")
def update_menu_item(request: Request, db: DbSession, item_id: int, item: MenuItemUpdate):
    """Update a menu item."""
    db_item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    if item.name is not None:
        db_item.name = item.name
    if item.description is not None:
        db_item.description = item.description
    if item.price is not None:
        db_item.price = Decimal(str(item.price))
    if item.category is not None:
        db_item.category = item.category
    if item.image_url is not None:
        db_item.image_url = item.image_url
    if item.available is not None:
        db_item.available = item.available
    if item.allergens is not None:
        db_item.allergens = item.allergens
    if item.modifiers is not None:
        db_item.modifiers = item.modifiers
    if item.prep_time_minutes is not None:
        db_item.prep_time_minutes = item.prep_time_minutes
    if item.station is not None:
        db_item.station = item.station

    db.commit()
    db.refresh(db_item)
    return {
        "status": "updated",
        "item": _menu_item_to_dict(db_item),
    }


@router.delete("/menu/items/{item_id}")
@limiter.limit("30/minute")
def delete_menu_item(request: Request, db: DbSession, item_id: int):
    """Soft-delete a menu item."""
    db_item = db.query(MenuItem).filter(MenuItem.id == item_id, MenuItem.not_deleted()).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    db_item.soft_delete()
    db.commit()
    return {"status": "deleted", "item_id": item_id}


# ==================== CATEGORY MANAGEMENT ====================

@router.post("/menu/categories")
@limiter.limit("30/minute")
def create_category(request: Request, db: DbSession, category: CategoryCreate):
    """Create a new category."""
    # Check if category already exists
    existing = db.query(MenuItem).filter(MenuItem.category == category.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category already exists")

    return {
        "status": "created",
        "category": {
            "name": category.name,
            "description": category.description,
        },
        "message": "Category created. Add items using POST /menu/items with this category name."
    }


@router.put("/menu/categories/{old_name}")
@limiter.limit("30/minute")
def rename_category(request: Request, db: DbSession, old_name: str, new_name: str):
    """Rename a category (updates all items in that category)."""
    items = db.query(MenuItem).filter(MenuItem.category == old_name).all()
    if not items:
        raise HTTPException(status_code=404, detail="Category not found")

    for item in items:
        item.category = new_name
    db.commit()

    return {"status": "renamed", "old_name": old_name, "new_name": new_name, "items_updated": len(items)}


@router.delete("/menu/categories/{name}")
@limiter.limit("30/minute")
def delete_category(request: Request, db: DbSession, name: str, delete_items: bool = False):
    """Delete a category. Set delete_items=true to also delete all items."""
    items = db.query(MenuItem).filter(MenuItem.category == name).all()
    if not items:
        raise HTTPException(status_code=404, detail="Category not found")

    if delete_items:
        for item in items:
            item.soft_delete()
        db.commit()
        return {"status": "deleted", "category": name, "items_deleted": len(items)}
    else:
        # Move items to "Uncategorized"
        for item in items:
            item.category = "Uncategorized"
        db.commit()
        return {"status": "deleted", "category": name, "items_moved_to": "Uncategorized"}


# ==================== TABLE MANAGEMENT ====================

@router.get("/tables")
@limiter.limit("60/minute")
def list_tables(request: Request, db: DbSession):
    """List all tables."""
    tables = db.query(Table).order_by(Table.number).all()
    return list_response([
        {
            "id": t.id,
            "number": t.number,
            "capacity": t.capacity,
            "status": t.status,
            "area": t.area,
            "token": t.token,
        }
        for t in tables
    ])


@router.post("/tables")
@limiter.limit("30/minute")
def create_table(request: Request, db: DbSession, table: TableCreate):
    """Create a new table."""
    # Check if table number already exists
    existing = db.query(Table).filter(Table.number == table.number).first()
    if existing:
        raise HTTPException(status_code=400, detail="Table number already exists")

    # Generate a secure random token for QR code
    import secrets
    token = secrets.token_urlsafe(16)

    db_table = Table(
        number=table.number,
        capacity=table.capacity,
        area=table.area,
        status=table.status,
        token=token,
    )
    db.add(db_table)
    db.commit()
    db.refresh(db_table)

    return {
        "status": "created",
        "table": {
            "id": db_table.id,
            "number": db_table.number,
            "capacity": db_table.capacity,
            "status": db_table.status,
            "area": db_table.area,
            "token": db_table.token,
        },
    }


@router.put("/tables/{table_id}")
@limiter.limit("30/minute")
def update_table(request: Request, db: DbSession, table_id: int, table: TableUpdate):
    """Update a table."""
    db_table = db.query(Table).filter(Table.id == table_id).first()
    if not db_table:
        raise HTTPException(status_code=404, detail="Table not found")

    if table.number is not None:
        db_table.number = table.number
    if table.capacity is not None:
        db_table.capacity = table.capacity
    if table.area is not None:
        db_table.area = table.area
    if table.status is not None:
        db_table.status = table.status

    db.commit()
    db.refresh(db_table)

    return {
        "status": "updated",
        "table": {
            "id": db_table.id,
            "number": db_table.number,
            "capacity": db_table.capacity,
            "status": db_table.status,
            "area": db_table.area,
            "token": db_table.token,
        },
    }


@router.delete("/tables/{table_id}")
@limiter.limit("30/minute")
def delete_table(request: Request, db: DbSession, table_id: int):
    """Delete a table."""
    db_table = db.query(Table).filter(Table.id == table_id).first()
    if not db_table:
        raise HTTPException(status_code=404, detail="Table not found")

    db.delete(db_table)
    db.commit()
    return {"status": "deleted", "table_id": table_id}


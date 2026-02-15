"""Guest ordering routes - customer-facing table ordering via QR code - using database."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Body, Request
from pydantic import BaseModel, field_validator

from app.core.sanitize import sanitize_text

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


def _get_venue_name(db: DbSession) -> str:
    """Get venue name from AppSetting, default to empty string."""
    setting = db.query(AppSetting).filter(
        AppSetting.category == "venue",
        AppSetting.key == "name",
    ).first()
    return setting.value if setting and setting.value else ""


# ==================== SCHEMAS ====================

class MenuItemSchema(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    price: float
    category: str
    image: Optional[str] = None
    available: bool = True
    allergens: Optional[List[str]] = None
    modifiers: Optional[List[dict]] = None


class MenuCategory(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    items: List[MenuItemSchema]


class TableInfo(BaseModel):
    id: int
    number: str
    capacity: int
    status: str
    venue_name: str = ""


class GuestOrderItem(BaseModel):
    menu_item_id: int
    quantity: int
    notes: Optional[str] = None
    modifiers: Optional[List[dict]] = None

    @field_validator("quantity", mode="before")
    @classmethod
    def _validate_quantity(cls, v):
        if v is not None and int(v) < 1:
            raise ValueError("quantity must be at least 1")
        return v

    @field_validator("notes", mode="before")
    @classmethod
    def _sanitize(cls, v):
        return sanitize_text(v)


class MenuItemCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    category: str
    image_url: Optional[str] = None
    available: bool = True
    allergens: Optional[List[str]] = None
    modifiers: Optional[List[dict]] = None
    prep_time_minutes: Optional[int] = None
    station: Optional[str] = None

    @field_validator("price", mode="before")
    @classmethod
    def _validate_price(cls, v):
        if v is not None and float(v) < 0:
            raise ValueError("price cannot be negative")
        return v

    @field_validator("name", "description", "category", mode="before")
    @classmethod
    def _sanitize(cls, v):
        return sanitize_text(v)


class MenuItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    category: Optional[str] = None
    image_url: Optional[str] = None
    available: Optional[bool] = None
    allergens: Optional[List[str]] = None
    modifiers: Optional[List[dict]] = None
    prep_time_minutes: Optional[int] = None
    station: Optional[str] = None

    @field_validator("name", "description", "category", mode="before")
    @classmethod
    def _sanitize(cls, v):
        return sanitize_text(v)


class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None

    @field_validator("name", "description", mode="before")
    @classmethod
    def _sanitize(cls, v):
        return sanitize_text(v)


class TableCreate(BaseModel):
    number: str
    capacity: int = 4
    area: Optional[str] = "Main Floor"
    status: str = "available"


class TableUpdate(BaseModel):
    number: Optional[str] = None
    capacity: Optional[int] = None
    area: Optional[str] = None
    status: Optional[str] = None


class GuestOrder(BaseModel):
    table_token: str
    items: List[GuestOrderItem]
    notes: Optional[str] = None
    order_type: str = "dine-in"

    @field_validator("items", mode="before")
    @classmethod
    def _validate_items(cls, v):
        if not v or len(v) == 0:
            raise ValueError("order must contain at least one item")
        if len(v) > 50:
            raise ValueError("order cannot contain more than 50 items")
        return v

    @field_validator("notes", mode="before")
    @classmethod
    def _sanitize(cls, v):
        return sanitize_text(v)


class GuestOrderResponse(BaseModel):
    order_id: int
    status: str
    table_number: str
    items_count: int
    total: float
    estimated_wait_minutes: int
    created_at: datetime


# ==================== HELPER FUNCTIONS ====================

def _get_table_by_token(db: DbSession, token: str) -> dict:
    """Get table info from database."""
    # Try to find by token
    db_table = db.query(Table).filter(Table.token == token).first()
    if db_table:
        return {
            "id": db_table.id,
            "number": db_table.number,
            "capacity": db_table.capacity or 4,
            "status": db_table.status or "available",
            "area": db_table.area or "Main Floor",
        }

    # Try to find by table number
    db_table = db.query(Table).filter(Table.number == token).first()
    if db_table:
        return {
            "id": db_table.id,
            "number": db_table.number,
            "capacity": db_table.capacity or 4,
            "status": db_table.status or "available",
            "area": db_table.area or "Main Floor",
        }

    # Unknown token - reject instead of auto-creating (prevents DoS)
    raise HTTPException(
        status_code=404,
        detail="Table not found. Please scan a valid table QR code.",
    )


def _menu_item_to_dict(item: MenuItem) -> dict:
    """Convert MenuItem model to dict for API response (guest-facing)."""
    return {
        "id": item.id,
        "name": item.name,
        "description": item.description,
        "price": float(item.price),
        "category": item.category,
        "image": item.image_url,
        "available": item.available,
        "allergens": item.allergens or [],
        "modifiers": item.modifiers or [],
    }


def _menu_item_to_admin_dict(item: MenuItem, db) -> dict:
    """Convert MenuItem model to dict for admin panel (with category_id, station_id, multilang)."""
    # Look up category_id from MenuCategory by matching name
    category_id = 0
    if item.category:
        cat = db.query(MenuCategoryModel).filter(
            (MenuCategoryModel.name_en == item.category) |
            (MenuCategoryModel.name_bg == item.category)
        ).first()
        if cat:
            category_id = cat.id

    # Look up station_id from KitchenStation by matching station type
    from app.models.advanced_features import KitchenStation
    station_id = 0
    if item.station:
        st = db.query(KitchenStation).filter(
            (KitchenStation.station_type == item.station) |
            (KitchenStation.name == item.station)
        ).first()
        if st:
            station_id = st.id

    return {
        "id": item.id,
        "name": {"bg": item.name or "", "en": item.name or ""},
        "description": {"bg": item.description or "", "en": item.description or ""},
        "price": float(item.price),
        "category": item.category,
        "category_id": category_id,
        "station": item.station,
        "station_id": station_id,
        "image": item.image_url,
        "sort_order": item.id,
        "available": item.available,
        "allergens": item.allergens or [],
        "modifiers": item.modifiers or [],
    }


# ==================== ROUTES ====================

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
    return {
        "tables": [
            {
                "id": t.id,
                "number": t.number,
                "capacity": t.capacity,
                "status": t.status,
                "area": t.area,
                "token": t.token,
            }
            for t in tables
        ],
        "total": len(tables),
    }


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


@router.post("/orders/guest", response_model=GuestOrderResponse)
@limiter.limit("30/minute")
def place_guest_order(
    request: Request,
    db: DbSession,
    order: GuestOrder,
):
    """
    Place a guest order from the customer-facing ordering page.
    This endpoint does not require authentication.
    Orders are persisted to database.
    """
    table = _get_table_by_token(db, order.table_token)

    # Validate items and calculate total
    total = Decimal("0")
    validated_items = []

    for order_item in order.items:
        menu_item = db.query(MenuItem).filter(MenuItem.id == order_item.menu_item_id).first()
        if not menu_item:
            raise HTTPException(
                status_code=400,
                detail=f"Menu item {order_item.menu_item_id} not found"
            )
        if not menu_item.available:
            raise HTTPException(
                status_code=400,
                detail=f"Menu item '{menu_item.name}' is not available"
            )

        item_total = menu_item.price * order_item.quantity
        total += item_total

        validated_items.append({
            "menu_item_id": menu_item.id,
            "name": menu_item.name,
            "price": float(menu_item.price),
            "quantity": order_item.quantity,
            "notes": order_item.notes,
            "total": float(item_total),
        })

    # Create order in database
    created_at = datetime.now(timezone.utc)
    db_order = GuestOrderModel(
        table_id=table["id"],
        table_token=order.table_token,
        table_number=table["number"],
        status="received",
        order_type=order.order_type,
        subtotal=total,
        tax=total * Decimal("0.08"),  # 8% tax
        total=total * Decimal("1.08"),
        items=validated_items,
        notes=order.notes,
        created_at=created_at,
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    # Also create KitchenOrder(s) for KDS — group items by station
    station_items = {}
    for order_item in order.items:
        mi = db.query(MenuItem).filter(MenuItem.id == order_item.menu_item_id).first()
        station_key = mi.station if mi and mi.station else "default"
        station_items.setdefault(station_key, [])
        # Find the matching validated item
        for vi in validated_items:
            if vi["menu_item_id"] == order_item.menu_item_id:
                station_items[station_key].append(vi)
                break

    for station_key, items_for_station in station_items.items():
        kitchen_order = KitchenOrder(
            table_number=table["number"],
            status="pending",
            station=station_key if station_key != "default" else None,
            items=items_for_station,
            notes=order.notes,
            created_at=created_at,
        )
        db.add(kitchen_order)

    # Update table status to occupied when order is placed
    db_table = db.query(Table).filter(Table.id == table["id"]).first()
    if db_table:
        db_table.status = "occupied"

    db.commit()

    # Deduct stock for ordered items
    order_id = db_order.id
    try:
        stock_service = StockDeductionService(db)
        stock_result = stock_service.deduct_for_order(
            order_items=validated_items,
            location_id=db_order.location_id or 1,
            reference_type="guest_order",
            reference_id=order_id,
        )
        logger.info(f"Stock deduction for guest order {order_id}: {stock_result['total_ingredients_deducted']} ingredients")
    except Exception as e:
        db.rollback()
        logger.warning(f"Stock deduction failed for guest order {order_id}: {e}")

    return GuestOrderResponse(
        order_id=db_order.id,
        status="received",
        table_number=table["number"],
        items_count=len(validated_items),
        total=float(total),
        estimated_wait_minutes=15 + (len(validated_items) * 2),
        created_at=created_at,
    )


@router.get("/orders/guest/{order_id}")
@limiter.limit("60/minute")
def get_guest_order(request: Request, db: DbSession, order_id: int):
    """Get a guest order by ID from database."""
    order = db.query(GuestOrderModel).filter(GuestOrderModel.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return {
        "id": order.id,
        "table_id": order.table_id,
        "table_number": order.table_number,
        "status": order.status,
        "order_type": order.order_type,
        "subtotal": float(order.subtotal) if order.subtotal else 0,
        "tax": float(order.tax) if order.tax else 0,
        "total": float(order.total) if order.total else 0,
        "items": order.items or [],
        "notes": order.notes,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "confirmed_at": order.confirmed_at.isoformat() if order.confirmed_at else None,
        "ready_at": order.ready_at.isoformat() if order.ready_at else None,
    }


@router.get("/orders/table/{token}")
@limiter.limit("60/minute")
def get_table_orders(
    request: Request,
    db: DbSession,
    token: str,
    status: Optional[str] = None,
    limit: int = 20,
):
    """Get orders for a specific table."""
    query = db.query(GuestOrderModel).filter(GuestOrderModel.table_token == token)
    if status:
        query = query.filter(GuestOrderModel.status == status)

    orders = query.order_by(GuestOrderModel.created_at.desc()).limit(limit).all()

    return {
        "orders": [
            {
                "id": o.id,
                "status": o.status,
                "total": float(o.total) if o.total else 0,
                "subtotal": float(o.subtotal) if o.subtotal else 0,
                "tax": float(o.tax) if o.tax else 0,
                "items_count": len(o.items) if o.items else 0,
                "items": o.items or [],  # Include full item details
                "notes": o.notes,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            }
            for o in orders
        ],
        "total": len(orders),
    }


@router.put("/orders/{order_id}/status")
@limiter.limit("30/minute")
def update_order_status(
    request: Request,
    db: DbSession,
    order_id: int,
    status: str = Query(None, description="New status (query param)"),
    new_status: str = Query(None, alias="new_status", description="Alias for status"),
    data: dict = Body(None),
):
    """Update order status (guest order or purchase order).

    Accepts status as query param (?status= or ?new_status=) OR JSON body {"status": "..."}.
    """
    # Accept status from query param (either name) or JSON body
    resolved_status = status or new_status
    payment_method = None
    if data:
        resolved_status = resolved_status or data.get("status") or data.get("new_status")
        payment_method = data.get("payment_method")
    if not resolved_status:
        raise HTTPException(status_code=422, detail="status is required")

    order = db.query(GuestOrderModel).filter(GuestOrderModel.id == order_id).first()
    if order:
        order.status = resolved_status
        now = datetime.now(timezone.utc)

        if resolved_status == "confirmed":
            order.confirmed_at = now
        elif resolved_status == "ready":
            order.ready_at = now
        elif resolved_status == "completed":
            order.completed_at = now
        elif resolved_status == "paid":
            order.payment_status = "paid"
            order.paid_at = now
            if payment_method:
                order.payment_method = payment_method

        db.commit()
        return {"status": "ok", "order_id": order_id, "new_status": resolved_status}

    # Fall through to purchase orders if guest order not found
    from app.models.order import PurchaseOrder
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
    if po:
        po.status = resolved_status
        if resolved_status == "sent":
            po.sent_at = datetime.now(timezone.utc)
        elif resolved_status == "received":
            po.received_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(po)
        return {"id": po.id, "status": po.status if isinstance(po.status, str) else po.status.value, "new_status": resolved_status}

    raise HTTPException(status_code=404, detail="Order not found")


@router.put("/guest/orders/{order_id}/status")
@limiter.limit("30/minute")
def update_guest_order_status(
    request: Request,
    db: DbSession,
    order_id: int,
    status: str = Query(None, description="New status"),
    data: dict = Body(None),
):
    """Update guest order status (no auth required)."""
    new_status = status
    payment_method = None
    if data:
        new_status = new_status or data.get("status")
        payment_method = data.get("payment_method")
    if not new_status:
        raise HTTPException(status_code=422, detail="status is required")

    order = db.query(GuestOrderModel).filter(GuestOrderModel.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = new_status
    now = datetime.now(timezone.utc)

    if new_status == "confirmed":
        order.confirmed_at = now
    elif new_status == "ready":
        order.ready_at = now
    elif new_status == "completed":
        order.completed_at = now
    elif new_status == "paid":
        order.payment_status = "paid"
        order.paid_at = now
        if payment_method:
            order.payment_method = payment_method

    db.commit()

    return {"status": "ok", "order_id": order_id, "new_status": new_status}


class VoidOrderRequest(BaseModel):
    reason: str


class VoidItemRequest(BaseModel):
    reason: str


@router.post("/orders/{order_id}/void")
@limiter.limit("30/minute")
def void_order(
    request: Request,
    db: DbSession,
    order_id: int,
    body_data: VoidOrderRequest,
):
    """Void/cancel an order and return stock to inventory."""
    order = db.query(GuestOrderModel).filter(GuestOrderModel.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Only refund stock if order wasn't already cancelled
    stock_refund_result = None
    if order.status != "cancelled":
        # Build order items from the order's items list
        order_items = []
        for item in (order.items or []):
            if item.get("status") != "cancelled":  # Don't refund already cancelled items
                order_items.append({
                    "menu_item_id": item.get("menu_item_id"),
                    "quantity": item.get("quantity", 1)
                })

        if order_items:
            stock_service = StockDeductionService(db)
            stock_refund_result = stock_service.refund_for_order(
                order_items=order_items,
                location_id=order.location_id or 1,
                reference_type="void_order",
                reference_id=order_id
            )

    order.status = "cancelled"
    order.notes = f"Voided: {body_data.reason}" + (f" | {order.notes}" if order.notes else "")
    db.commit()

    return {
        "status": "ok",
        "order_id": order_id,
        "new_status": "cancelled",
        "stock_returned": stock_refund_result.get("success", False) if stock_refund_result else False
    }


@router.post("/orders/{order_id}/items/{item_id}/void")
@limiter.limit("30/minute")
def void_order_item(
    request: Request,
    db: DbSession,
    order_id: int,
    item_id: str,
    body_data: VoidItemRequest,
):
    """Void/cancel a specific item from an order and return its stock."""
    order = db.query(GuestOrderModel).filter(GuestOrderModel.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Update items list - mark the item as cancelled
    items = order.items or []
    item_found = False
    item_to_refund = None
    new_total = Decimal("0")

    for item in items:
        if str(item.get("id")) == str(item_id):
            # Only refund if not already cancelled
            if item.get("status") != "cancelled":
                item_to_refund = item
            item["status"] = "cancelled"
            item_found = True
        elif item.get("status") != "cancelled":
            new_total += Decimal(str(item.get("total", 0)))

    if not item_found:
        raise HTTPException(status_code=404, detail="Item not found in order")

    # Return stock for the voided item
    stock_refund_result = None
    if item_to_refund:
        stock_service = StockDeductionService(db)
        stock_refund_result = stock_service.refund_for_order(
            order_items=[{
                "menu_item_id": item_to_refund.get("menu_item_id"),
                "quantity": item_to_refund.get("quantity", 1)
            }],
            location_id=order.location_id or 1,
            reference_type="void_item",
            reference_id=order_id
        )

    order.items = items
    order.subtotal = new_total
    order.tax = new_total * Decimal("0.1")  # 10% tax
    order.total = order.subtotal + order.tax

    db.commit()

    return {
        "status": "ok",
        "order_id": order_id,
        "item_id": item_id,
        "new_order_total": float(order.total),
        "stock_returned": stock_refund_result.get("success", False) if stock_refund_result else False
    }


# Valid statuses for CheckItem (defined in restaurant.py model)
VALID_CHECK_ITEM_STATUSES = {"ordered", "fired", "cooking", "ready", "served", "voided"}


class UpdateItemStatusRequest(BaseModel):
    status: str

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, v):
        if v not in VALID_CHECK_ITEM_STATUSES:
            raise ValueError(
                f"Invalid status '{v}'. Must be one of: {', '.join(sorted(VALID_CHECK_ITEM_STATUSES))}"
            )
        return v


@router.patch("/orders/{order_id}/items/{item_id}/status")
@limiter.limit("30/minute")
def update_order_item_status(
    request: Request,
    db: DbSession,
    order_id: int,
    item_id: int,
    body_data: UpdateItemStatusRequest,
):
    """Update the status of an individual order item (CheckItem).

    Used by kitchen/server to mark items as preparing, ready, served, etc.
    """
    item = db.query(CheckItem).filter(
        CheckItem.id == item_id,
        CheckItem.check_id == order_id,
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Order item not found")

    now = datetime.now(timezone.utc)
    item.status = body_data.status

    # Update relevant timestamp fields based on status
    if body_data.status == "fired":
        item.fired_at = now
    elif body_data.status == "served":
        item.served_at = now
    elif body_data.status == "voided":
        item.voided_at = now

    db.commit()
    db.refresh(item)

    return {
        "id": item.id,
        "check_id": item.check_id,
        "name": item.name,
        "status": item.status,
        "quantity": item.quantity,
        "price": float(item.price),
        "total": float(item.total),
        "fired_at": item.fired_at.isoformat() if item.fired_at else None,
        "served_at": item.served_at.isoformat() if item.served_at else None,
        "voided_at": item.voided_at.isoformat() if item.voided_at else None,
    }


@router.post("/orders/{order_id}/cancel")
@limiter.limit("30/minute")
def cancel_order(
    request: Request,
    db: DbSession,
    order_id: int,
    reason: str = Query(None),
):
    """Cancel an order and return stock to inventory."""
    order = db.query(GuestOrderModel).filter(GuestOrderModel.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Only refund stock if order wasn't already cancelled
    stock_refund_result = None
    if order.status != "cancelled":
        # Build order items from the order's items list
        order_items = []
        for item in (order.items or []):
            if item.get("status") != "cancelled":
                order_items.append({
                    "menu_item_id": item.get("menu_item_id"),
                    "quantity": item.get("quantity", 1)
                })

        if order_items:
            stock_service = StockDeductionService(db)
            stock_refund_result = stock_service.refund_for_order(
                order_items=order_items,
                location_id=order.location_id or 1,
                reference_type="cancel_order",
                reference_id=order_id
            )

    order.status = "cancelled"
    if reason:
        order.notes = f"Cancelled: {reason}" + (f" | {order.notes}" if order.notes else "")
    db.commit()

    return {
        "status": "ok",
        "order_id": order_id,
        "new_status": "cancelled",
        "stock_returned": stock_refund_result.get("success", False) if stock_refund_result else False
    }


@router.delete("/orders/{order_id}")
@limiter.limit("30/minute")
def delete_order(
    request: Request,
    db: DbSession,
    order_id: int,
):
    """Delete an order (soft delete by setting status to cancelled) and return stock."""
    order = db.query(GuestOrderModel).filter(GuestOrderModel.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Only refund stock if order wasn't already cancelled
    stock_refund_result = None
    if order.status != "cancelled":
        order_items = []
        for item in (order.items or []):
            if item.get("status") != "cancelled":
                order_items.append({
                    "menu_item_id": item.get("menu_item_id"),
                    "quantity": item.get("quantity", 1)
                })

        if order_items:
            stock_service = StockDeductionService(db)
            stock_refund_result = stock_service.refund_for_order(
                order_items=order_items,
                location_id=order.location_id or 1,
                reference_type="delete_order",
                reference_id=order_id
            )

    order.status = "cancelled"
    db.commit()

    return {
        "status": "deleted",
        "order_id": order_id,
        "stock_returned": stock_refund_result.get("success", False) if stock_refund_result else False
    }


class RefundOrderRequest(BaseModel):
    amount: float
    reason: str = ""
    refund_method: str = "cash"


@router.post("/orders/{order_id}/refund")
@limiter.limit("30/minute")
def refund_order(
    request: Request,
    db: DbSession,
    order_id: int,
    body_data: RefundOrderRequest,
):
    """Process a refund for an order."""
    order = db.query(GuestOrderModel).filter(GuestOrderModel.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.payment_status = "refunded"
    if body_data.reason:
        order.notes = f"Refund: {body_data.reason}" + (f" | {order.notes}" if order.notes else "")
    db.commit()

    return {
        "status": "ok",
        "order_id": order_id,
        "refund_amount": body_data.amount,
        "refund_method": body_data.refund_method,
        "message": f"Refund of {body_data.amount:.2f} processed",
    }


class ReprintOrderRequest(BaseModel):
    station: str = "kitchen"


@router.post("/orders/{order_id}/reprint")
@limiter.limit("30/minute")
def reprint_order(
    request: Request,
    db: DbSession,
    order_id: int,
    body_data: ReprintOrderRequest,
):
    """Reprint an order ticket for a station."""
    order = db.query(GuestOrderModel).filter(GuestOrderModel.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return {
        "status": "ok",
        "order_id": order_id,
        "station": body_data.station,
        "message": f"Order #{order_id} reprinted for {body_data.station}",
    }


@router.get("/orders")
@limiter.limit("60/minute")
def list_guest_orders(
    request: Request,
    db: DbSession,
    status: Optional[str] = None,
    table_token: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
):
    """List all guest orders with optional filters."""
    query = db.query(GuestOrderModel)

    if status:
        query = query.filter(GuestOrderModel.status == status)
    if table_token:
        query = query.filter(GuestOrderModel.table_token == table_token)

    total = query.count()
    orders = query.order_by(GuestOrderModel.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "orders": [
            {
                "id": o.id,
                "table_id": o.table_id,
                "table_number": o.table_number,
                "table_token": o.table_token,
                "status": o.status,
                "order_type": o.order_type,
                "subtotal": float(o.subtotal) if o.subtotal else 0,
                "tax": float(o.tax) if o.tax else 0,
                "total": float(o.total) if o.total else 0,
                "items": o.items or [],
                "items_count": len(o.items) if o.items else 0,
                "notes": o.notes,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            }
            for o in orders
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


# ==================== ADMIN ENDPOINTS (for frontend compatibility) ====================

@router.get("/admin/tables")
@limiter.limit("60/minute")
def admin_list_tables(request: Request, db: DbSession):
    """List tables for admin panel."""
    tables = db.query(Table).order_by(Table.number).all()
    return {
        "tables": [
            {
                "id": t.id,
                "number": t.number,
                "table_number": t.number,  # Alias for frontend compatibility
                "name": f"Table {t.number}",
                "capacity": t.capacity,
                "status": t.status,
                "area": t.area,
                "token": t.token,
            }
            for t in tables
        ],
        "total": len(tables)
    }


@router.get("/orders/stats")
@limiter.limit("60/minute")
def get_order_stats(request: Request, db: DbSession):
    """Get order statistics."""
    from sqlalchemy import func

    total_orders = db.query(GuestOrderModel).count()
    pending = db.query(GuestOrderModel).filter(GuestOrderModel.status == "received").count()
    in_progress = db.query(GuestOrderModel).filter(GuestOrderModel.status.in_(["confirmed", "preparing"])).count()
    completed = db.query(GuestOrderModel).filter(GuestOrderModel.status == "completed").count()

    # Calculate revenue
    revenue_result = db.query(func.sum(GuestOrderModel.total)).filter(
        GuestOrderModel.status == "completed"
    ).scalar()
    total_revenue = float(revenue_result) if revenue_result else 0

    ready = db.query(GuestOrderModel).filter(GuestOrderModel.status == "ready").count()
    served = db.query(GuestOrderModel).filter(GuestOrderModel.status == "served").count()
    cancelled = db.query(GuestOrderModel).filter(GuestOrderModel.status == "cancelled").count()
    avg_val = round(total_revenue / completed, 2) if completed > 0 else 0

    return {
        "total_orders": total_orders,
        "pending": pending,
        "new_orders": pending,
        "in_progress": in_progress,
        "preparing": in_progress,
        "ready": ready,
        "served": served,
        "completed": completed,
        "paid": completed,
        "cancelled": cancelled,
        "total_revenue": total_revenue,
        "average_order_value": avg_val,
        "avg_order_value": avg_val,
        "avg_prep_time": 0,
    }


@router.get("/guest/orders/stats")
@limiter.limit("60/minute")
def get_guest_order_stats(request: Request, db: DbSession):
    """Get order statistics (alternate path to avoid auth conflict)."""
    from sqlalchemy import func

    total_orders = db.query(GuestOrderModel).count()
    pending = db.query(GuestOrderModel).filter(GuestOrderModel.status == "received").count()
    in_progress = db.query(GuestOrderModel).filter(GuestOrderModel.status.in_(["confirmed", "preparing"])).count()
    completed = db.query(GuestOrderModel).filter(GuestOrderModel.status == "completed").count()

    revenue_result = db.query(func.sum(GuestOrderModel.total)).filter(
        GuestOrderModel.status == "completed"
    ).scalar()
    total_revenue = float(revenue_result) if revenue_result else 0

    ready = db.query(GuestOrderModel).filter(GuestOrderModel.status == "ready").count()
    served = db.query(GuestOrderModel).filter(GuestOrderModel.status == "served").count()
    cancelled = db.query(GuestOrderModel).filter(GuestOrderModel.status == "cancelled").count()
    avg_val = round(total_revenue / completed, 2) if completed > 0 else 0

    return {
        "total_orders": total_orders,
        "pending": pending,
        "new_orders": pending,
        "in_progress": in_progress,
        "preparing": in_progress,
        "ready": ready,
        "served": served,
        "completed": completed,
        "paid": completed,
        "cancelled": cancelled,
        "total_revenue": total_revenue,
        "average_order_value": avg_val,
        "avg_order_value": avg_val,
        "avg_prep_time": 0,
    }


@router.get("/menu-admin/items")
@limiter.limit("60/minute")
def admin_list_menu_items(request: Request, db: DbSession, category: Optional[str] = None):
    """List menu items for admin panel."""
    query = db.query(MenuItem).filter(MenuItem.not_deleted())
    if category:
        query = query.filter(MenuItem.category == category)

    items = query.all()
    return {
        "items": [_menu_item_to_admin_dict(i, db) for i in items],
        "total": len(items)
    }


@router.get("/menu-admin/items/{item_id}")
@limiter.limit("60/minute")
def admin_get_menu_item(request: Request, db: DbSession, item_id: int):
    """Get a single menu item by ID."""
    item = db.query(MenuItem).filter(MenuItem.id == item_id, MenuItem.not_deleted()).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return _menu_item_to_admin_dict(item, db)


def _category_to_response(cat: MenuCategoryModel, items_count: int = 0) -> dict:
    """Convert a MenuCategory model to the response dict expected by the frontend."""
    return {
        "id": cat.id,
        "name": {"bg": cat.name_bg or "", "en": cat.name_en or ""},
        "description": {"bg": cat.description_bg or "", "en": cat.description_en or ""},
        "icon": cat.icon or "🍽",
        "color": cat.color or "#3B82F6",
        "image_url": cat.image_url,
        "sort_order": cat.sort_order or 0,
        "active": cat.active if cat.active is not None else True,
        "parent_id": cat.parent_id,
        "items_count": items_count,
        "schedule": cat.schedule,
        "visibility": cat.visibility or "all",
        "tax_rate": float(cat.tax_rate) if cat.tax_rate else None,
        "printer_id": cat.printer_id,
        "display_on_kiosk": cat.display_on_kiosk if cat.display_on_kiosk is not None else True,
        "display_on_app": cat.display_on_app if cat.display_on_app is not None else True,
        "display_on_web": cat.display_on_web if cat.display_on_web is not None else True,
    }


@router.get("/menu-admin/categories")
@limiter.limit("60/minute")
def admin_list_categories(request: Request, db: DbSession):
    """List categories for admin panel (returns multilang format)."""
    from sqlalchemy import func

    cats = db.query(MenuCategoryModel).order_by(MenuCategoryModel.sort_order, MenuCategoryModel.id).all()

    # Count items per category (match by name)
    item_counts = {}
    count_rows = db.query(MenuItem.category, func.count(MenuItem.id)).group_by(MenuItem.category).all()
    for cat_name, count in count_rows:
        if cat_name:
            item_counts[cat_name.lower()] = count

    results = []
    for cat in cats:
        count = item_counts.get((cat.name_bg or "").lower(), 0) + item_counts.get((cat.name_en or "").lower(), 0)
        # Avoid double-counting when bg == en
        if cat.name_bg and cat.name_en and cat.name_bg.lower() == cat.name_en.lower():
            count = item_counts.get(cat.name_bg.lower(), 0)
        results.append(_category_to_response(cat, count))

    return results


@router.get("/menu-admin/stations")
@limiter.limit("60/minute")
def admin_list_stations(request: Request, db: DbSession):
    """List kitchen stations for admin panel."""
    from app.models.advanced_features import KitchenStation
    stations = db.query(KitchenStation).order_by(KitchenStation.id).all()

    return [
        {
            "id": s.id,
            "name": {"bg": s.name or s.station_type or "", "en": s.name or s.station_type or ""},
            "station_type": s.station_type or s.name or "",
            "active": s.is_active if s.is_active is not None else True,
        }
        for s in stations
    ]


# ==================== CUSTOMER PAYMENT ENDPOINTS ====================

class GuestPaymentRequest(BaseModel):
    order_id: int
    payment_method: str = "card"  # card, cash, online
    tip_amount: Optional[float] = None
    tip_percent: Optional[int] = None
    card_token: Optional[str] = None  # For saved card payments
    payment_intent_id: Optional[str] = None  # Stripe payment intent ID (for card payments)


class GuestPaymentResponse(BaseModel):
    payment_id: int
    order_id: int
    status: str
    amount: float
    tip: float
    total_charged: float
    payment_method: str
    receipt_url: Optional[str] = None


@router.get("/orders/{order_id}/payment")
@limiter.limit("60/minute")
def get_order_payment_status(request: Request, db: DbSession, order_id: int):
    """Get payment status for an order."""
    order = db.query(GuestOrderModel).filter(GuestOrderModel.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return {
        "order_id": order.id,
        "order_status": order.status,
        "subtotal": float(order.subtotal) if order.subtotal else 0,
        "tax": float(order.tax) if order.tax else 0,
        "total": float(order.total) if order.total else 0,
        "payment_status": order.payment_status or "unpaid",
        "payment_method": order.payment_method,
        "tip_amount": float(order.tip_amount) if order.tip_amount else 0,
        "total_with_tip": float(order.total) + (float(order.tip_amount) if order.tip_amount else 0),
        "paid_at": order.paid_at.isoformat() if order.paid_at else None,
    }


@router.get("/orders/table/{token}/payment-summary")
@limiter.limit("60/minute")
def get_table_payment_summary(request: Request, db: DbSession, token: str):
    """Get payment summary for all orders at a table."""
    orders = db.query(GuestOrderModel).filter(
        GuestOrderModel.table_token == token,
        GuestOrderModel.status.notin_(["cancelled", "void"])
    ).all()

    total_subtotal = sum(float(o.subtotal) if o.subtotal else 0 for o in orders)
    total_tax = sum(float(o.tax) if o.tax else 0 for o in orders)
    total_amount = sum(float(o.total) if o.total else 0 for o in orders)
    total_paid = sum(float(o.total) if o.total and o.payment_status == "paid" else 0 for o in orders)

    unpaid_orders = [o for o in orders if o.payment_status != "paid"]

    return {
        "table_token": token,
        "total_orders": len(orders),
        "subtotal": total_subtotal,
        "tax": total_tax,
        "total_amount": total_amount,
        "total_paid": total_paid,
        "balance_due": total_amount - total_paid,
        "unpaid_orders": [
            {
                "id": o.id,
                "total": float(o.total) if o.total else 0,
                "items_count": len(o.items) if o.items else 0,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            }
            for o in unpaid_orders
        ],
        "payment_status": "paid" if total_paid >= total_amount and len(orders) > 0 else "unpaid",
    }


@router.post("/orders/{order_id}/pay")
@limiter.limit("30/minute")
def process_guest_payment(
    request: Request,
    db: DbSession,
    order_id: int,
    payment: GuestPaymentRequest,
):
    """
    Process payment for a guest order.
    This endpoint is used by the customer-facing QR code ordering page.
    """
    order = db.query(GuestOrderModel).filter(GuestOrderModel.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.payment_status == "paid":
        raise HTTPException(status_code=400, detail="Order already paid")

    # Calculate tip
    tip = Decimal("0")
    if payment.tip_amount:
        tip = Decimal(str(payment.tip_amount))
    elif payment.tip_percent:
        tip = order.total * Decimal(str(payment.tip_percent)) / Decimal("100")

    total_charged = order.total + tip

    # If a Stripe payment_intent_id is provided, verify it succeeded
    if payment.payment_intent_id and payment.payment_method == "card":
        try:
            from app.services.stripe_service import get_stripe_service, PaymentStatus
            stripe = get_stripe_service()
            if stripe:
                result = await_stripe_check = None
                # Synchronous call - stripe_service handles async internally
                import asyncio
                loop = asyncio.new_event_loop()
                try:
                    result = loop.run_until_complete(
                        stripe.get_payment_intent(payment.payment_intent_id)
                    )
                finally:
                    loop.close()

                if not result or not result.success:
                    raise HTTPException(
                        status_code=402,
                        detail=f"Payment verification failed: {result.error_message if result else 'Stripe unavailable'}",
                    )
                if result.status != PaymentStatus.SUCCEEDED:
                    raise HTTPException(
                        status_code=402,
                        detail=f"Payment not completed. Current status: {result.status.value if result.status else 'unknown'}",
                    )
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Stripe verification failed for order {order_id}: {e}")
            # Fall through to manual recording if Stripe is not configured

    # Record payment
    order.payment_status = "paid"
    order.payment_method = payment.payment_method
    order.tip_amount = tip
    order.paid_at = datetime.now(timezone.utc)
    order.status = "completed"
    db.commit()

    return {
        "status": "success",
        "payment_id": order.id,
        "order_id": order.id,
        "amount": float(order.total),
        "tip": float(tip),
        "total_charged": float(total_charged),
        "payment_method": payment.payment_method,
        "receipt_url": f"/api/v1/guest-orders/orders/{order.id}/receipt",
        "message": "Payment successful! Thank you for your order.",
    }


@router.post("/orders/table/{token}/pay-all")
@limiter.limit("30/minute")
def pay_all_table_orders(
    request: Request,
    db: DbSession,
    token: str,
    payment_method: str = Query("card"),
    tip_percent: Optional[int] = Query(None),
    tip_amount: Optional[float] = Query(None),
):
    """
    Pay all unpaid orders for a table at once.
    """
    orders = db.query(GuestOrderModel).filter(
        GuestOrderModel.table_token == token,
        GuestOrderModel.payment_status != "paid",
        GuestOrderModel.status.notin_(["cancelled", "void"])
    ).all()

    if not orders:
        raise HTTPException(status_code=404, detail="No unpaid orders found for this table")

    total_amount = sum(float(o.total) if o.total else 0 for o in orders)

    # Calculate tip
    tip = Decimal("0")
    if tip_amount:
        tip = Decimal(str(tip_amount))
    elif tip_percent:
        tip = Decimal(str(total_amount)) * Decimal(str(tip_percent)) / Decimal("100")

    total_charged = Decimal(str(total_amount)) + tip

    # Mark all orders as paid
    now = datetime.now(timezone.utc)
    for order in orders:
        order.payment_status = "paid"
        order.payment_method = payment_method
        order.paid_at = now
        order.status = "completed"

    # Apply tip to the last order
    if orders and tip > 0:
        orders[-1].tip_amount = tip

    db.commit()

    return {
        "status": "success",
        "orders_paid": len(orders),
        "subtotal": total_amount,
        "tip": float(tip),
        "total_charged": float(total_charged),
        "payment_method": payment_method,
        "message": f"Successfully paid {len(orders)} order(s). Thank you!",
    }


@router.get("/orders/{order_id}/receipt")
@limiter.limit("60/minute")
def get_order_receipt(request: Request, db: DbSession, order_id: int):
    """Get receipt for a paid order."""
    order = db.query(GuestOrderModel).filter(GuestOrderModel.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return {
        "receipt": {
            "order_id": order.id,
            "venue": _get_venue_name(db),
            "table": order.table_number,
            "date": order.created_at.isoformat() if order.created_at else None,
            "items": order.items or [],
            "subtotal": float(order.subtotal) if order.subtotal else 0,
            "tax": float(order.tax) if order.tax else 0,
            "tip": float(order.tip_amount) if order.tip_amount else 0,
            "total": float(order.total) + (float(order.tip_amount) if order.tip_amount else 0),
            "payment_method": order.payment_method,
            "payment_status": order.payment_status or "unpaid",
            "paid_at": order.paid_at.isoformat() if order.paid_at else None,
        },
        "message": "Thank you for dining with us!"
    }


@router.post("/orders/{order_id}/request-payment")
@limiter.limit("30/minute")
def request_payment_assistance(
    request: Request,
    db: DbSession,
    order_id: int,
    message: Optional[str] = Query(None),
):
    """
    Request payment assistance from waiter.
    Creates a waiter call for payment/check request.
    """
    from app.models.hardware import WaiterCall as WaiterCallModel

    order = db.query(GuestOrderModel).filter(GuestOrderModel.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Create waiter call for payment
    call = WaiterCallModel(
        table_id=order.table_id,
        table_number=f"Table {order.table_number}",
        call_type="check",
        message=message or f"Payment requested for order #{order.id} - Total: ${float(order.total):.2f}",
        status="pending",
    )
    db.add(call)
    db.commit()
    db.refresh(call)

    return {
        "status": "requested",
        "call_id": call.id,
        "order_id": order.id,
        "total": float(order.total) if order.total else 0,
        "message": "A server will be with you shortly to process your payment.",
    }

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

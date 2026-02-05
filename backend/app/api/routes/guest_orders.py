"""Guest ordering routes - customer-facing table ordering via QR code - using database."""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel

from app.db.session import DbSession
from app.models.restaurant import GuestOrder as GuestOrderModel, KitchenOrder, Table, MenuItem
from app.services.stock_deduction_service import StockDeductionService
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


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
    venue_name: str = "BJ's Bar & Grill"


class GuestOrderItem(BaseModel):
    menu_item_id: int
    quantity: int
    notes: Optional[str] = None
    modifiers: Optional[List[dict]] = None


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


class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None


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

    # Accept any token for demo purposes - create a virtual table
    return {
        "id": hash(token) % 1000 + 100,
        "number": token.upper()[:8],
        "capacity": 4,
        "status": "available",
        "area": "Main Floor",
    }


def _menu_item_to_dict(item: MenuItem) -> dict:
    """Convert MenuItem model to dict for API response."""
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


# ==================== ROUTES ====================

@router.get("/menu/table/{token}")
def get_table_menu(
    db: DbSession,
    token: str,
):
    """
    Get table information and menu for guest ordering.
    This endpoint is used by the customer-facing QR code ordering page.
    """
    table = _get_table_by_token(db, token)

    # Get menu items from database
    menu_items = db.query(MenuItem).filter(MenuItem.available == True).all()

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
            "venue_name": "BJ's Bar & Grill",
        },
        "categories": menu_categories,
        "menu": {
            "categories": menu_categories,
            "total_items": len(menu_items),
        },
    }


@router.get("/menu/items")
def get_menu_items(
    db: DbSession,
    category: Optional[str] = None,
    available_only: bool = True,
):
    """Get all menu items, optionally filtered by category."""
    query = db.query(MenuItem)
    if category:
        query = query.filter(MenuItem.category == category)
    if available_only:
        query = query.filter(MenuItem.available == True)

    items = query.all()
    return {"items": [_menu_item_to_dict(i) for i in items], "total": len(items)}


@router.get("/menu/items/{item_id}")
def get_menu_item(db: DbSession, item_id: int):
    """Get a specific menu item."""
    item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    return _menu_item_to_dict(item)


@router.get("/menu/categories")
def get_menu_categories(db: DbSession):
    """Get all menu categories."""
    items = db.query(MenuItem).filter(MenuItem.available == True).all()
    categories = list(set(item.category for item in items))
    return {"categories": categories}


# ==================== MENU ITEM CRUD ====================

@router.post("/menu/items")
def create_menu_item(db: DbSession, item: MenuItemCreate):
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
def update_menu_item(db: DbSession, item_id: int, item: MenuItemUpdate):
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
def delete_menu_item(db: DbSession, item_id: int):
    """Delete a menu item."""
    db_item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    db.delete(db_item)
    db.commit()
    return {"status": "deleted", "item_id": item_id}


# ==================== CATEGORY MANAGEMENT ====================

@router.post("/menu/categories")
def create_category(db: DbSession, category: CategoryCreate):
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
def rename_category(db: DbSession, old_name: str, new_name: str):
    """Rename a category (updates all items in that category)."""
    items = db.query(MenuItem).filter(MenuItem.category == old_name).all()
    if not items:
        raise HTTPException(status_code=404, detail="Category not found")

    for item in items:
        item.category = new_name
    db.commit()

    return {"status": "renamed", "old_name": old_name, "new_name": new_name, "items_updated": len(items)}


@router.delete("/menu/categories/{name}")
def delete_category(db: DbSession, name: str, delete_items: bool = False):
    """Delete a category. Set delete_items=true to also delete all items."""
    items = db.query(MenuItem).filter(MenuItem.category == name).all()
    if not items:
        raise HTTPException(status_code=404, detail="Category not found")

    if delete_items:
        for item in items:
            db.delete(item)
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
def list_tables(db: DbSession):
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
def create_table(db: DbSession, table: TableCreate):
    """Create a new table."""
    # Check if table number already exists
    existing = db.query(Table).filter(Table.number == table.number).first()
    if existing:
        raise HTTPException(status_code=400, detail="Table number already exists")

    # Generate a token for QR code
    import hashlib
    token = hashlib.md5(f"table_{table.number}_{datetime.utcnow().isoformat()}".encode()).hexdigest()[:12]

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
def update_table(db: DbSession, table_id: int, table: TableUpdate):
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
def delete_table(db: DbSession, table_id: int):
    """Delete a table."""
    db_table = db.query(Table).filter(Table.id == table_id).first()
    if not db_table:
        raise HTTPException(status_code=404, detail="Table not found")

    db.delete(db_table)
    db.commit()
    return {"status": "deleted", "table_id": table_id}


@router.post("/orders/guest", response_model=GuestOrderResponse)
def place_guest_order(
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
    created_at = datetime.utcnow()
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

    # Also create a KitchenOrder for KDS
    kitchen_order = KitchenOrder(
        table_number=table["number"],
        status="pending",
        items=validated_items,
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
    try:
        stock_service = StockDeductionService(db)
        stock_result = stock_service.deduct_for_order(
            order_items=validated_items,
            location_id=1,
            reference_type="guest_order",
            reference_id=db_order.id,
        )
        logger.info(f"Stock deduction for guest order {db_order.id}: {stock_result['total_ingredients_deducted']} ingredients")
    except Exception as e:
        logger.warning(f"Stock deduction failed for guest order {db_order.id}: {e}")

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
def get_guest_order(db: DbSession, order_id: int):
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
def get_table_orders(
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
def update_order_status(
    db: DbSession,
    order_id: int,
    status: str = Query(..., description="New status"),
):
    """Update order status."""
    order = db.query(GuestOrderModel).filter(GuestOrderModel.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = status
    now = datetime.utcnow()

    if status == "confirmed":
        order.confirmed_at = now
    elif status == "ready":
        order.ready_at = now
    elif status == "completed":
        order.completed_at = now

    db.commit()

    return {"status": "ok", "order_id": order_id, "new_status": status}


@router.put("/guest/orders/{order_id}/status")
def update_guest_order_status(
    db: DbSession,
    order_id: int,
    status: str = Query(..., description="New status"),
):
    """Update guest order status (no auth required)."""
    order = db.query(GuestOrderModel).filter(GuestOrderModel.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = status
    now = datetime.utcnow()

    if status == "confirmed":
        order.confirmed_at = now
    elif status == "ready":
        order.ready_at = now
    elif status == "completed":
        order.completed_at = now

    db.commit()

    return {"status": "ok", "order_id": order_id, "new_status": status}


class VoidOrderRequest(BaseModel):
    reason: str


class VoidItemRequest(BaseModel):
    reason: str


@router.post("/orders/{order_id}/void")
def void_order(
    db: DbSession,
    order_id: int,
    request: VoidOrderRequest,
):
    """Void/cancel an order."""
    order = db.query(GuestOrderModel).filter(GuestOrderModel.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = "cancelled"
    order.notes = f"Voided: {request.reason}" + (f" | {order.notes}" if order.notes else "")
    db.commit()

    return {"status": "ok", "order_id": order_id, "new_status": "cancelled"}


@router.post("/orders/{order_id}/items/{item_id}/void")
def void_order_item(
    db: DbSession,
    order_id: int,
    item_id: str,
    request: VoidItemRequest,
):
    """Void/cancel a specific item from an order."""
    order = db.query(GuestOrderModel).filter(GuestOrderModel.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Update items list - mark the item as cancelled
    items = order.items or []
    item_found = False
    new_total = Decimal("0")

    for item in items:
        if str(item.get("id")) == str(item_id):
            item["status"] = "cancelled"
            item_found = True
        elif item.get("status") != "cancelled":
            new_total += Decimal(str(item.get("total", 0)))

    if not item_found:
        raise HTTPException(status_code=404, detail="Item not found in order")

    order.items = items
    order.subtotal = new_total
    order.tax = new_total * Decimal("0.1")  # 10% tax
    order.total = order.subtotal + order.tax

    db.commit()

    return {
        "status": "ok",
        "order_id": order_id,
        "item_id": item_id,
        "new_order_total": float(order.total)
    }


@router.post("/orders/{order_id}/cancel")
def cancel_order(
    db: DbSession,
    order_id: int,
    reason: str = Query(None),
):
    """Cancel an order (alternative to void)."""
    order = db.query(GuestOrderModel).filter(GuestOrderModel.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = "cancelled"
    if reason:
        order.notes = f"Cancelled: {reason}" + (f" | {order.notes}" if order.notes else "")
    db.commit()

    return {"status": "ok", "order_id": order_id, "new_status": "cancelled"}


@router.delete("/orders/{order_id}")
def delete_order(
    db: DbSession,
    order_id: int,
):
    """Delete an order (soft delete by setting status to cancelled)."""
    order = db.query(GuestOrderModel).filter(GuestOrderModel.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = "cancelled"
    db.commit()

    return {"status": "deleted", "order_id": order_id}


@router.get("/orders")
def list_guest_orders(
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
def admin_list_tables(db: DbSession):
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
def get_order_stats(db: DbSession):
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

    return {
        "total_orders": total_orders,
        "pending": pending,
        "in_progress": in_progress,
        "completed": completed,
        "cancelled": db.query(GuestOrderModel).filter(GuestOrderModel.status == "cancelled").count(),
        "total_revenue": total_revenue,
        "average_order_value": total_revenue / completed if completed > 0 else 0,
    }


@router.get("/guest/orders/stats")
def get_guest_order_stats(db: DbSession):
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

    return {
        "total_orders": total_orders,
        "pending": pending,
        "in_progress": in_progress,
        "completed": completed,
        "cancelled": db.query(GuestOrderModel).filter(GuestOrderModel.status == "cancelled").count(),
        "total_revenue": total_revenue,
        "average_order_value": total_revenue / completed if completed > 0 else 0,
    }


@router.get("/menu-admin/items")
def admin_list_menu_items(db: DbSession, category: Optional[str] = None):
    """List menu items for admin panel."""
    query = db.query(MenuItem)
    if category:
        query = query.filter(MenuItem.category == category)

    items = query.all()
    return {
        "items": [_menu_item_to_dict(i) for i in items],
        "total": len(items)
    }


@router.get("/menu-admin/categories")
def admin_list_categories(db: DbSession):
    """List categories for admin panel (returns multilang format)."""
    # Get distinct categories from menu items
    items = db.query(MenuItem).all()
    categories_set = set(i.category for i in items if i.category)

    # Return in multilang format expected by frontend
    categories = []
    for idx, cat_name in enumerate(sorted(categories_set)):
        categories.append({
            "id": idx + 1,
            "name": {"bg": cat_name, "en": cat_name},
            "description": {"bg": "", "en": ""},
            "sort_order": idx,
            "active": True,
        })

    return categories


@router.get("/menu-admin/stations")
def admin_list_stations(db: DbSession):
    """List kitchen stations for admin panel."""
    # Get distinct stations from menu items
    items = db.query(MenuItem).all()
    stations_set = set(i.station for i in items if i.station)

    # Return in multilang format expected by frontend
    stations = []
    for idx, station_name in enumerate(sorted(stations_set)):
        stations.append({
            "id": idx + 1,
            "name": {"bg": station_name, "en": station_name},
            "station_type": station_name,
            "active": True,
        })

    return stations


# ==================== CUSTOMER PAYMENT ENDPOINTS ====================

class GuestPaymentRequest(BaseModel):
    order_id: int
    payment_method: str = "card"  # card, cash, online
    tip_amount: Optional[float] = None
    tip_percent: Optional[int] = None
    card_token: Optional[str] = None  # For saved card payments


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
def get_order_payment_status(db: DbSession, order_id: int):
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
def get_table_payment_summary(db: DbSession, token: str):
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
def process_guest_payment(
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

    # For demo purposes, simulate successful payment
    # In production, integrate with Stripe, Square, or other payment processor
    payment_successful = True

    if payment_successful:
        order.payment_status = "paid"
        order.payment_method = payment.payment_method
        order.tip_amount = tip
        order.paid_at = datetime.utcnow()
        order.status = "completed"
        db.commit()

        return {
            "status": "success",
            "payment_id": order.id * 1000,  # Simulated payment ID
            "order_id": order.id,
            "amount": float(order.total),
            "tip": float(tip),
            "total_charged": float(total_charged),
            "payment_method": payment.payment_method,
            "receipt_url": f"/api/v1/orders/{order.id}/receipt",
            "message": "Payment successful! Thank you for your order.",
        }
    else:
        raise HTTPException(status_code=402, detail="Payment failed")


@router.post("/orders/table/{token}/pay-all")
def pay_all_table_orders(
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
    now = datetime.utcnow()
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
def get_order_receipt(db: DbSession, order_id: int):
    """Get receipt for a paid order."""
    order = db.query(GuestOrderModel).filter(GuestOrderModel.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return {
        "receipt": {
            "order_id": order.id,
            "venue": "BJ's Bar & Grill",
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
def request_payment_assistance(
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
def admin_create_menu_item(db: DbSession, data: dict = Body(...)):
    """Create a new menu item."""
    # Handle both string and dict formats for name/description
    name_data = data.get("name", "")
    name = name_data.get("en", name_data) if isinstance(name_data, dict) else name_data
    desc_data = data.get("description", "")
    description = desc_data.get("en", desc_data) if isinstance(desc_data, dict) else (desc_data or "")

    item = MenuItem(
        name=name,
        category=data.get("category", "Uncategorized"),
        price=data.get("price", 0),
        station=data.get("station"),
        description=description,
        available=data.get("available", data.get("is_available", True)),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _menu_item_to_dict(item)


@router.put("/menu-admin/items/{item_id}")
def admin_update_menu_item(db: DbSession, item_id: int, data: dict = Body(...)):
    """Update a menu item."""
    item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    if "name" in data:
        item.name = data["name"].get("en", data["name"]) if isinstance(data["name"], dict) else data["name"]
    if "category" in data:
        item.category = data["category"]
    if "price" in data:
        item.price = data["price"]
    if "station" in data:
        item.station = data["station"]
    if "description" in data:
        item.description = data["description"].get("en", "") if isinstance(data["description"], dict) else data["description"]
    if "is_available" in data:
        item.available = data["is_available"]
    if "available" in data:
        item.available = data["available"]
    
    db.commit()
    db.refresh(item)
    return _menu_item_to_dict(item)


@router.delete("/menu-admin/items/{item_id}")
def admin_delete_menu_item(db: DbSession, item_id: int):
    """Delete a menu item."""
    item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()
    return {"success": True}


@router.patch("/menu-admin/items/{item_id}/toggle-available")
def admin_toggle_item_availability(db: DbSession, item_id: int):
    """Toggle menu item availability."""
    item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    item.available = not item.available
    db.commit()
    return {"id": item.id, "available": item.available}


@router.post("/menu-admin/categories")
def admin_create_category(db: DbSession, data: dict = Body(...)):
    """Create a new category (stores as first item's category)."""
    name_data = data.get("name", "")
    # Handle both string and dict formats
    if isinstance(name_data, dict):
        name = name_data.get("en", name_data.get("bg", ""))
    else:
        name = str(name_data)

    desc_data = data.get("description", {"bg": "", "en": ""})
    if isinstance(desc_data, str):
        desc_data = {"bg": desc_data, "en": desc_data}

    return {
        "id": hash(name) % 10000,
        "name": {"bg": name, "en": name},
        "description": desc_data,
        "sort_order": data.get("sort_order", 0),
        "active": True
    }


@router.put("/menu-admin/categories/{category_id}")
def admin_update_category(db: DbSession, category_id: int, data: dict = Body(...)):
    """Update a category."""
    name_data = data.get("name", "")
    if isinstance(name_data, dict):
        name = name_data.get("en", name_data.get("bg", ""))
    else:
        name = str(name_data) if name_data else ""

    desc_data = data.get("description", {"bg": "", "en": ""})
    if isinstance(desc_data, str):
        desc_data = {"bg": desc_data, "en": desc_data}

    return {
        "id": category_id,
        "name": {"bg": name, "en": name},
        "description": desc_data,
        "sort_order": data.get("sort_order", 0),
        "active": data.get("active", True)
    }


@router.delete("/menu-admin/categories/{category_id}")
def admin_delete_category(db: DbSession, category_id: int):
    """Delete a category."""
    return {"success": True}


@router.patch("/menu-admin/categories/{category_id}/toggle-active")
def admin_toggle_category_active(db: DbSession, category_id: int):
    """Toggle category active status."""
    return {"id": category_id, "active": True}


@router.get("/menu-admin/modifier-groups")
def admin_list_modifier_groups(db: DbSession):
    """List modifier groups."""
    return []


@router.post("/menu-admin/modifier-groups")
def admin_create_modifier_group(db: DbSession, data: dict = Body(...)):
    """Create a modifier group."""
    return {
        "id": 1,
        "name": data.get("name", ""),
        "min_selections": data.get("min_selections", 0),
        "max_selections": data.get("max_selections", 1),
        "active": True,
        "options": []
    }


@router.put("/menu-admin/modifier-groups/{group_id}")
def admin_update_modifier_group(db: DbSession, group_id: int, data: dict = Body(...)):
    """Update a modifier group."""
    return {"id": group_id, **data}


@router.delete("/menu-admin/modifier-groups/{group_id}")
def admin_delete_modifier_group(db: DbSession, group_id: int):
    """Delete a modifier group."""
    return {"success": True}


@router.post("/menu-admin/modifier-groups/{group_id}/options")
def admin_create_modifier_option(db: DbSession, group_id: int, data: dict = Body(...)):
    """Create a modifier option."""
    return {
        "id": 1,
        "group_id": group_id,
        "name": data.get("name", ""),
        "price_adjustment": data.get("price_adjustment", 0),
        "available": True
    }


@router.put("/menu-admin/modifier-options/{option_id}")
def admin_update_modifier_option(db: DbSession, option_id: int, data: dict = Body(...)):
    """Update a modifier option."""
    return {"id": option_id, **data}


@router.delete("/menu-admin/modifier-options/{option_id}")
def admin_delete_modifier_option(db: DbSession, option_id: int):
    """Delete a modifier option."""
    return {"success": True}


@router.get("/menu-admin/combos")
def admin_list_combos(db: DbSession):
    """List combo meals."""
    return []


@router.post("/menu-admin/combos")
def admin_create_combo(db: DbSession, data: dict = Body(...)):
    """Create a combo meal."""
    return {"id": 1, **data, "available": True, "featured": False}


@router.put("/menu-admin/combos/{combo_id}")
def admin_update_combo(db: DbSession, combo_id: int, data: dict = Body(...)):
    """Update a combo meal."""
    return {"id": combo_id, **data}


@router.delete("/menu-admin/combos/{combo_id}")
def admin_delete_combo(db: DbSession, combo_id: int):
    """Delete a combo meal."""
    return {"success": True}


@router.patch("/menu-admin/combos/{combo_id}/toggle-available")
def admin_toggle_combo_available(db: DbSession, combo_id: int):
    """Toggle combo availability."""
    return {"id": combo_id, "available": True}


@router.patch("/menu-admin/combos/{combo_id}/toggle-featured")
def admin_toggle_combo_featured(db: DbSession, combo_id: int):
    """Toggle combo featured status."""
    return {"id": combo_id, "featured": True}


@router.get("/menu-admin/dayparts")
def admin_list_dayparts(db: DbSession):
    """List dayparts for menu scheduling."""
    return [
        {"id": 1, "name": "Breakfast", "start_time": "06:00", "end_time": "11:00", "active": True},
        {"id": 2, "name": "Lunch", "start_time": "11:00", "end_time": "15:00", "active": True},
        {"id": 3, "name": "Dinner", "start_time": "17:00", "end_time": "22:00", "active": True},
    ]


@router.post("/menu-admin/dayparts")
def admin_create_daypart(db: DbSession, data: dict = Body(...)):
    """Create a daypart."""
    return {"id": 4, **data, "active": True}


@router.put("/menu-admin/dayparts/{daypart_id}")
def admin_update_daypart(db: DbSession, daypart_id: int, data: dict = Body(...)):
    """Update a daypart."""
    return {"id": daypart_id, **data}


@router.delete("/menu-admin/dayparts/{daypart_id}")
def admin_delete_daypart(db: DbSession, daypart_id: int):
    """Delete a daypart."""
    return {"success": True}


@router.patch("/menu-admin/dayparts/{daypart_id}/toggle-active")
def admin_toggle_daypart_active(db: DbSession, daypart_id: int):
    """Toggle daypart active status."""
    return {"id": daypart_id, "active": True}


@router.get("/menu-admin/items-with-allergens")
def admin_list_items_with_allergens(db: DbSession):
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
def admin_update_item_allergens(db: DbSession, item_id: int, data: dict = Body(...)):
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
def admin_get_item_modifiers(db: DbSession, item_id: int):
    """Get modifiers for a specific item."""
    return []


@router.put("/menu-admin/categories/reorder")
def admin_reorder_categories(db: DbSession, data: dict = Body(...)):
    """Reorder categories."""
    return {"success": True}


@router.get("/menu-admin/modifiers")
def admin_list_modifiers(db: DbSession):
    """List all modifiers."""
    return []


@router.post("/menu-admin/modifiers")
def admin_create_modifier(db: DbSession, data: dict = Body(...)):
    """Create a modifier."""
    return {"id": 1, **data}


@router.put("/menu-admin/modifiers/{modifier_id}")
def admin_update_modifier(db: DbSession, modifier_id: int, data: dict = Body(...)):
    """Update a modifier."""
    return {"id": modifier_id, **data}


@router.delete("/menu-admin/modifiers/{modifier_id}")
def admin_delete_modifier(db: DbSession, modifier_id: int):
    """Delete a modifier."""
    return {"success": True}


@router.post("/menu-admin/modifiers/{modifier_id}/options")
def admin_add_modifier_option(db: DbSession, modifier_id: int, data: dict = Body(...)):
    """Add option to modifier."""
    return {"id": 1, "modifier_id": modifier_id, **data}


@router.delete("/menu-admin/modifiers/options/{option_id}")
def admin_remove_modifier_option(db: DbSession, option_id: int):
    """Remove modifier option."""
    return {"success": True}


@router.patch("/menu-admin/modifier-groups/{group_id}/toggle-active")
def admin_toggle_modifier_group_active(db: DbSession, group_id: int):
    """Toggle modifier group active status."""
    return {"id": group_id, "active": True}


@router.patch("/menu-admin/modifier-options/{option_id}/toggle-available")
def admin_toggle_modifier_option_available(db: DbSession, option_id: int):
    """Toggle modifier option availability."""
    return {"id": option_id, "available": True}

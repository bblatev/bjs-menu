"""Guest ordering routes - customer-facing table ordering via QR code."""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.session import DbSession

# Import shared check data for KDS integration
from app.api.routes.waiter import _checks

router = APIRouter()

# Track check ID for guest orders (start at 5000 to avoid conflicts)
_guest_check_id = 5000


# ==================== SCHEMAS ====================

class MenuItem(BaseModel):
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
    items: List[MenuItem]


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


# ==================== SAMPLE DATA ====================

_menu_items = [
    # Appetizers
    {"id": 1, "name": "Chicken Wings", "description": "Crispy fried wings with your choice of sauce", "price": 12.99, "category": "Appetizers", "image": "/images/wings.jpg", "available": True, "allergens": ["gluten"]},
    {"id": 2, "name": "Nachos Supreme", "description": "Loaded nachos with cheese, jalapeños, and sour cream", "price": 14.99, "category": "Appetizers", "image": "/images/nachos.jpg", "available": True, "allergens": ["dairy", "gluten"]},
    {"id": 3, "name": "Mozzarella Sticks", "description": "Golden fried mozzarella with marinara", "price": 9.99, "category": "Appetizers", "image": "/images/mozzsticks.jpg", "available": True, "allergens": ["dairy", "gluten"]},
    {"id": 4, "name": "Onion Rings", "description": "Beer-battered onion rings", "price": 8.99, "category": "Appetizers", "image": "/images/onionrings.jpg", "available": True, "allergens": ["gluten"]},
    {"id": 5, "name": "Loaded Potato Skins", "description": "Potato skins with bacon, cheese, and chives", "price": 10.99, "category": "Appetizers", "image": "/images/potatoskins.jpg", "available": True, "allergens": ["dairy"]},

    # Main Courses
    {"id": 10, "name": "Classic Burger", "description": "1/2 lb beef patty with lettuce, tomato, and special sauce", "price": 15.99, "category": "Main", "image": "/images/burger.jpg", "available": True, "allergens": ["gluten", "dairy"]},
    {"id": 11, "name": "BBQ Ribs", "description": "Slow-smoked baby back ribs with coleslaw and fries", "price": 24.99, "category": "Main", "image": "/images/ribs.jpg", "available": True, "allergens": []},
    {"id": 12, "name": "Fish & Chips", "description": "Beer-battered cod with fries and tartar sauce", "price": 18.99, "category": "Main", "image": "/images/fishnchips.jpg", "available": True, "allergens": ["gluten", "fish"]},
    {"id": 13, "name": "Grilled Chicken Sandwich", "description": "Grilled chicken breast with avocado and bacon", "price": 14.99, "category": "Main", "image": "/images/chickensandwich.jpg", "available": True, "allergens": ["gluten"]},
    {"id": 14, "name": "Caesar Salad", "description": "Romaine lettuce with caesar dressing and croutons", "price": 12.99, "category": "Main", "image": "/images/caesarsalad.jpg", "available": True, "allergens": ["gluten", "dairy", "fish"]},
    {"id": 15, "name": "Steak Frites", "description": "8oz ribeye with garlic butter and fries", "price": 28.99, "category": "Main", "image": "/images/steakfrites.jpg", "available": True, "allergens": ["dairy"]},

    # Pizza
    {"id": 20, "name": "Margherita Pizza", "description": "Fresh mozzarella, tomatoes, and basil", "price": 16.99, "category": "Pizza", "image": "/images/margherita.jpg", "available": True, "allergens": ["gluten", "dairy"]},
    {"id": 21, "name": "Pepperoni Pizza", "description": "Classic pepperoni with mozzarella", "price": 17.99, "category": "Pizza", "image": "/images/pepperoni.jpg", "available": True, "allergens": ["gluten", "dairy"]},
    {"id": 22, "name": "BBQ Chicken Pizza", "description": "BBQ chicken, red onion, and cilantro", "price": 18.99, "category": "Pizza", "image": "/images/bbqchicken.jpg", "available": True, "allergens": ["gluten", "dairy"]},

    # Drinks
    {"id": 30, "name": "Soft Drink", "description": "Coke, Sprite, Fanta, or Lemonade", "price": 3.99, "category": "Drinks", "image": "/images/soda.jpg", "available": True, "allergens": []},
    {"id": 31, "name": "Fresh Juice", "description": "Orange, Apple, or Cranberry", "price": 4.99, "category": "Drinks", "image": "/images/juice.jpg", "available": True, "allergens": []},
    {"id": 32, "name": "Iced Tea", "description": "Freshly brewed sweet or unsweet", "price": 3.49, "category": "Drinks", "image": "/images/icedtea.jpg", "available": True, "allergens": []},
    {"id": 33, "name": "Coffee", "description": "Regular or decaf", "price": 2.99, "category": "Drinks", "image": "/images/coffee.jpg", "available": True, "allergens": []},

    # Desserts
    {"id": 40, "name": "Chocolate Brownie", "description": "Warm brownie with vanilla ice cream", "price": 7.99, "category": "Desserts", "image": "/images/brownie.jpg", "available": True, "allergens": ["gluten", "dairy", "eggs"]},
    {"id": 41, "name": "Cheesecake", "description": "New York style cheesecake", "price": 8.99, "category": "Desserts", "image": "/images/cheesecake.jpg", "available": True, "allergens": ["gluten", "dairy", "eggs"]},
    {"id": 42, "name": "Ice Cream Sundae", "description": "Three scoops with your choice of toppings", "price": 6.99, "category": "Desserts", "image": "/images/sundae.jpg", "available": True, "allergens": ["dairy"]},
]

# Table tokens - in production these would be in database
_table_tokens = {
    "table1": {"id": 1, "number": "1", "capacity": 4, "status": "available"},
    "table2": {"id": 2, "number": "2", "capacity": 4, "status": "available"},
    "table3": {"id": 3, "number": "3", "capacity": 2, "status": "available"},
    "table4": {"id": 4, "number": "4", "capacity": 6, "status": "available"},
    "table5": {"id": 5, "number": "5", "capacity": 4, "status": "available"},
    "bar1": {"id": 11, "number": "Bar 1", "capacity": 2, "status": "available"},
    "bar2": {"id": 12, "number": "Bar 2", "capacity": 2, "status": "available"},
    "patio1": {"id": 15, "number": "Patio 1", "capacity": 4, "status": "available"},
    "vip1": {"id": 18, "number": "VIP 1", "capacity": 8, "status": "available"},
    # Accept any token format for demo
    "test123": {"id": 99, "number": "Demo", "capacity": 4, "status": "available"},
}

_guest_orders = []


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
    # Look up table by token
    table = _table_tokens.get(token)

    # Accept any token for demo purposes
    if not table:
        table = {
            "id": hash(token) % 1000,
            "number": token.upper()[:8],
            "capacity": 4,
            "status": "available"
        }

    # Group menu items by category
    categories = {}
    for item in _menu_items:
        if item["available"]:
            cat = item["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)

    menu_categories = [
        {"id": i + 1, "name": cat, "items": items}
        for i, (cat, items) in enumerate(categories.items())
    ]

    # Return categories at root level for frontend compatibility
    return {
        "table": {
            **table,
            "venue_name": "BJ's Bar & Grill",
        },
        "categories": menu_categories,
        "menu": {
            "categories": menu_categories,
            "total_items": len(_menu_items),
        },
    }


@router.get("/menu/items")
def get_menu_items(
    db: DbSession,
    category: Optional[str] = None,
    available_only: bool = True,
):
    """Get all menu items, optionally filtered by category."""
    items = _menu_items
    if category:
        items = [i for i in items if i["category"] == category]
    if available_only:
        items = [i for i in items if i["available"]]
    return {"items": items, "total": len(items)}


@router.get("/menu/items/{item_id}")
def get_menu_item(db: DbSession, item_id: int):
    """Get a specific menu item."""
    item = next((i for i in _menu_items if i["id"] == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    return item


@router.get("/menu/categories")
def get_menu_categories(db: DbSession):
    """Get all menu categories."""
    categories = list(set(item["category"] for item in _menu_items))
    return {"categories": categories}


@router.post("/orders/guest", response_model=GuestOrderResponse)
def place_guest_order(
    db: DbSession,
    order: GuestOrder,
):
    """
    Place a guest order from the customer-facing ordering page.
    This endpoint does not require authentication.
    """
    # Validate table token
    table = _table_tokens.get(order.table_token)
    if not table:
        # Accept any token for demo
        table = {
            "id": hash(order.table_token) % 1000,
            "number": order.table_token.upper()[:8],
            "capacity": 4,
            "status": "available"
        }

    # Validate items and calculate total
    total = 0.0
    validated_items = []

    for order_item in order.items:
        menu_item = next((i for i in _menu_items if i["id"] == order_item.menu_item_id), None)
        if not menu_item:
            raise HTTPException(
                status_code=400,
                detail=f"Menu item {order_item.menu_item_id} not found"
            )
        if not menu_item["available"]:
            raise HTTPException(
                status_code=400,
                detail=f"Menu item '{menu_item['name']}' is not available"
            )

        item_total = menu_item["price"] * order_item.quantity
        total += item_total

        validated_items.append({
            "menu_item_id": menu_item["id"],
            "name": menu_item["name"],
            "price": menu_item["price"],
            "quantity": order_item.quantity,
            "notes": order_item.notes,
            "total": item_total,
        })

    # Create order
    order_id = len(_guest_orders) + 1
    created_at = datetime.utcnow()
    new_order = {
        "id": order_id,
        "table_id": table["id"],
        "table_number": table["number"],
        "items": validated_items,
        "notes": order.notes,
        "order_type": order.order_type,
        "total": round(total, 2),
        "status": "received",
        "created_at": created_at,
    }
    _guest_orders.append(new_order)

    # Update table status
    table["status"] = "occupied"

    # Create kitchen ticket for KDS
    global _guest_check_id
    _guest_check_id += 1
    check_id = _guest_check_id

    # Format items for KDS display
    kds_items = []
    for item in validated_items:
        for _ in range(item["quantity"]):
            kds_items.append({
                "id": item["menu_item_id"],
                "name": item["name"],
                "price": item["price"],
                "quantity": 1,
                "notes": item.get("notes", ""),
                "status": "new",
                "modifiers": [],
            })

    _checks[check_id] = {
        "check_id": check_id,
        "table_id": table["id"],
        "table_name": f"Table {table['number']}",
        "guest_order_id": order_id,
        "items": kds_items,
        "status": "new",
        "total": round(total, 2),
        "guest_count": 1,
        "created_at": created_at.isoformat(),
        "order_type": order.order_type,
        "notes": order.notes,
        "source": "guest_order",
    }

    return GuestOrderResponse(
        order_id=order_id,
        status="received",
        table_number=table["number"],
        items_count=len(validated_items),
        total=round(total, 2),
        estimated_wait_minutes=15 + (len(validated_items) * 2),
        created_at=new_order["created_at"],
    )


@router.get("/orders/guest/{order_id}")
def get_guest_order(db: DbSession, order_id: int):
    """Get a guest order by ID."""
    order = next((o for o in _guest_orders if o["id"] == order_id), None)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.get("/orders/table/{table_token}")
def get_table_orders(db: DbSession, table_token: str):
    """Get all orders for a table."""
    table = _table_tokens.get(table_token)
    if not table:
        table = {"id": hash(table_token) % 1000}

    orders = [o for o in _guest_orders if o["table_id"] == table["id"]]
    return {"orders": orders, "total": len(orders)}


# Also support the /orders endpoint for guest orders
@router.post("/orders")
def place_order_legacy(
    db: DbSession,
    order: GuestOrder,
):
    """
    Legacy endpoint for placing orders.
    Redirects to guest order endpoint.
    """
    return place_guest_order(db, order)

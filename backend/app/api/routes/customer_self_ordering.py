"""
Customer Self-Ordering API (MyMenu/TouchSale Style)
====================================================
QR code-based ordering from customer's own device
Similar to TouchSale MyMenu and Microinvest Restaurant Plus

Features:
- QR code session management
- Browse menu with real-time availability
- Add items to cart with customizations
- Place orders directly
- Track order status and prep time
- Call waiter
- Order history and favorites
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, ConfigDict
import secrets

from app.db.session import get_db
from app.core.rate_limit import limiter
from app.models import (
    Table, Menu, MenuItem, MenuCategory, Order, OrderItem,
    Venue, ModifierGroup, ModifierOption
)
from app.models.microinvest_touchsale_features import (
    CustomerOrderingSession, CustomerOrderItem, CustomerWaiterCall,
    CustomerFavorite, MenuItemPrepTime, CustomerPrepTimeNotification,
    MenuItemAvailability
)


router = APIRouter()


# =============================================================================
# SCHEMAS
# =============================================================================

class SessionStartRequest(BaseModel):
    table_token: str
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    language: str = "en"


class SessionResponse(BaseModel):
    session_token: str
    table_id: int
    table_name: str
    venue_id: int
    venue_name: str
    language: str
    expires_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MenuItemResponse(BaseModel):
    id: int
    name: dict  # Multilingual
    description: Optional[dict]
    price: float
    image_url: Optional[str]
    category_id: int
    category_name: dict
    is_available: bool
    availability_status: str
    portions_available: Optional[int]
    prep_time_minutes: Optional[int]
    allergens: Optional[List[str]]
    modifiers: List[dict]
    is_popular: bool
    is_favorite: bool


class CartItemRequest(BaseModel):
    menu_item_id: int
    quantity: int = 1
    modifiers: Optional[List[dict]] = None
    special_requests: Optional[str] = None


class CartItemResponse(BaseModel):
    id: int
    menu_item_id: int
    menu_item_name: dict
    quantity: int
    unit_price: float
    total_price: float
    modifiers: Optional[List[dict]]
    special_requests: Optional[str]
    estimated_prep_minutes: Optional[int]
    status: str

    model_config = ConfigDict(from_attributes=True)


class PlaceOrderResponse(BaseModel):
    order_id: int
    order_number: str
    estimated_ready_at: datetime
    estimated_wait_minutes: int
    items_count: int
    total_amount: float


class OrderStatusResponse(BaseModel):
    order_id: int
    status: str
    items: List[dict]
    estimated_ready_at: Optional[datetime]
    actual_ready_at: Optional[datetime]
    is_ready: bool


class WaiterCallRequest(BaseModel):
    call_type: str  # waiter, bill, help, water, complaint
    message: Optional[str] = None


# =============================================================================
# SESSION MANAGEMENT
# =============================================================================

@router.get("/")
@limiter.limit("60/minute")
async def get_self_order_root(request: Request, db: Session = Depends(get_db)):
    """Self-ordering module overview."""
    return {"module": "self-order", "status": "active", "endpoints": ["/session/validate", "/menu", "/cart", "/order/status/{order_id}"]}


@router.post("/session/start", response_model=SessionResponse)
@limiter.limit("30/minute")
async def start_session(
    data: SessionStartRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Start a new customer ordering session by scanning table QR code"""
    # Validate table token
    table = db.query(Table).filter(
        Table.token == data.table_token
    ).first()

    if not table:
        raise HTTPException(status_code=404, detail="Invalid table QR code")

    venue = db.query(Venue).filter(Venue.id == table.location_id).first()
    if not venue or not venue.active:
        raise HTTPException(status_code=404, detail="Venue not found or inactive")

    # Check if there's an existing active session for this table
    existing_session = db.query(CustomerOrderingSession).filter(
        CustomerOrderingSession.table_id == table.id,
        CustomerOrderingSession.status == "active"
    ).first()

    if existing_session:
        # Update last activity and return existing session
        existing_session.last_activity = datetime.now(timezone.utc)
        db.commit()

        venue_name = venue.name.get(data.language, venue.name.get("en", ""))

        return SessionResponse(
            session_token=existing_session.session_token,
            table_id=table.id,
            table_name=table.name,
            venue_id=venue.id,
            venue_name=venue_name,
            language=existing_session.language,
            expires_at=existing_session.expires_at
        )

    # Create new session
    session_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=4)

    session = CustomerOrderingSession(
        venue_id=venue.id,
        table_id=table.id,
        session_token=session_token,
        customer_name=data.customer_name,
        customer_phone=data.customer_phone,
        language=data.language,
        expires_at=expires_at,
        device_type=_detect_device_type(request),
        user_agent=request.headers.get("user-agent", "")[:500],
        ip_address=request.client.host if request.client else None
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    venue_name = venue.name.get(data.language, venue.name.get("en", ""))

    return SessionResponse(
        session_token=session.session_token,
        table_id=table.id,
        table_name=table.name,
        venue_id=venue.id,
        venue_name=venue_name,
        language=session.language,
        expires_at=session.expires_at
    )


@router.get("/session/validate")
@limiter.limit("60/minute")
async def validate_session(
    request: Request,
    session_token: str = Query("", description="Session token"),
    db: Session = Depends(get_db)
):
    """Validate if a session is still active"""
    session = _get_valid_session(session_token, db)

    return {
        "valid": True,
        "table_id": session.table_id,
        "venue_id": session.venue_id,
        "language": session.language,
        "expires_at": session.expires_at
    }


@router.post("/session/close")
@limiter.limit("30/minute")
async def close_session(
    request: Request,
    session_token: str,
    db: Session = Depends(get_db)
):
    """Close a customer ordering session"""
    session = _get_valid_session(session_token, db)

    session.status = "closed"
    session.closed_at = datetime.now(timezone.utc)
    db.commit()

    return {"message": "Session closed", "session_id": session.id}


# =============================================================================
# MENU BROWSING
# =============================================================================

@router.get("/menu", response_model=List[dict])
@limiter.limit("60/minute")
async def get_menu(
    request: Request,
    session_token: str = Query("", description="Session token"),
    category_id: Optional[int] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get menu with real-time availability for customer ordering"""
    session = _get_valid_session(session_token, db)
    lang = session.language

    # Get active menu for venue
    menu = db.query(Menu).filter(
        Menu.venue_id == session.venue_id,
        Menu.active == True
    ).first()

    if not menu:
        return []

    # Build category query
    cat_query = db.query(MenuCategory).filter(
        MenuCategory.menu_id == menu.id,
        MenuCategory.active == True
    )

    if category_id:
        cat_query = cat_query.filter(MenuCategory.id == category_id)

    categories = cat_query.order_by(MenuCategory.sort_order).all()

    result = []
    for cat in categories:
        # Get items in category
        item_query = db.query(MenuItem).filter(
            MenuItem.category_id == cat.id,
            MenuItem.available == True
        )

        if search:
            # Search in name (JSON field)
            item_query = item_query.filter(
                MenuItem.name.cast(str).ilike(f"%{search}%")
            )

        items = item_query.order_by(MenuItem.sort_order).all()

        cat_items = []
        for item in items:
            # Get availability
            availability = db.query(MenuItemAvailability).filter(
                MenuItemAvailability.menu_item_id == item.id
            ).first()

            is_available = True
            availability_status = "available"
            portions_available = None

            if availability:
                is_available = availability.is_available
                availability_status = availability.availability_type
                portions_available = availability.portions_available

            # Get prep time
            prep_time = db.query(MenuItemPrepTime).filter(
                MenuItemPrepTime.menu_item_id == item.id
            ).first()

            prep_minutes = prep_time.standard_prep_minutes if prep_time else None

            # Check if favorite (if customer is logged in)
            is_favorite = False
            if session.customer_id:
                fav = db.query(CustomerFavorite).filter(
                    CustomerFavorite.customer_id == session.customer_id,
                    CustomerFavorite.menu_item_id == item.id
                ).first()
                is_favorite = fav is not None

            # Get modifiers
            modifiers = []
            if item.modifier_groups:
                for mg_id in item.modifier_groups:
                    mg = db.query(ModifierGroup).filter(ModifierGroup.id == mg_id).first()
                    if mg:
                        options = db.query(ModifierOption).filter(
                            ModifierOption.group_id == mg.id,
                            ModifierOption.active == True
                        ).all()

                        modifiers.append({
                            "group_id": mg.id,
                            "group_name": mg.name,
                            "required": mg.required,
                            "min_select": mg.min_select,
                            "max_select": mg.max_select,
                            "options": [
                                {
                                    "id": opt.id,
                                    "name": opt.name,
                                    "price": float(opt.price) if opt.price else 0
                                } for opt in options
                            ]
                        })

            cat_items.append({
                "id": item.id,
                "name": item.name,
                "description": item.description,
                "price": float(item.price),
                "image_url": item.image_url,
                "is_available": is_available,
                "availability_status": availability_status,
                "portions_available": portions_available,
                "prep_time_minutes": prep_minutes,
                "allergens": item.allergens if hasattr(item, 'allergens') else None,
                "modifiers": modifiers,
                "is_popular": getattr(item, 'is_popular', False),
                "is_favorite": is_favorite
            })

        if cat_items:  # Only include categories with available items
            result.append({
                "category_id": cat.id,
                "category_name": cat.name,
                "category_description": cat.description,
                "items": cat_items
            })

    return result


@router.get("/menu/item/{item_id}")
@limiter.limit("60/minute")
async def get_menu_item_detail(
    request: Request,
    item_id: int,
    session_token: str = Query("", description="Session token"),
    db: Session = Depends(get_db)
):
    """Get detailed information for a single menu item"""
    session = _get_valid_session(session_token, db)

    item = db.query(MenuItem).filter(
        MenuItem.id == item_id,
        MenuItem.active == True
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    # Get availability
    availability = db.query(MenuItemAvailability).filter(
        MenuItemAvailability.menu_item_id == item.id
    ).first()

    # Get prep time
    prep_time = db.query(MenuItemPrepTime).filter(
        MenuItemPrepTime.menu_item_id == item.id
    ).first()

    # Get modifiers with full details
    modifiers = []
    if item.modifier_groups:
        for mg_id in item.modifier_groups:
            mg = db.query(ModifierGroup).filter(ModifierGroup.id == mg_id).first()
            if mg:
                options = db.query(ModifierOption).filter(
                    ModifierOption.group_id == mg.id,
                    ModifierOption.active == True
                ).all()

                modifiers.append({
                    "group_id": mg.id,
                    "group_name": mg.name,
                    "required": mg.required,
                    "min_select": mg.min_select,
                    "max_select": mg.max_select,
                    "options": [
                        {
                            "id": opt.id,
                            "name": opt.name,
                            "description": opt.description,
                            "price": float(opt.price) if opt.price else 0
                        } for opt in options
                    ]
                })

    return {
        "id": item.id,
        "name": item.name,
        "description": item.description,
        "price": float(item.price),
        "image_url": item.image_url,
        "is_available": availability.is_available if availability else True,
        "availability_status": availability.availability_type if availability else "available",
        "prep_time_minutes": prep_time.standard_prep_minutes if prep_time else 15,
        "prep_time_range": {
            "min": prep_time.minimum_prep_minutes,
            "max": prep_time.maximum_prep_minutes
        } if prep_time else None,
        "allergens": item.allergens if hasattr(item, 'allergens') else [],
        "nutritional_info": item.nutritional_info if hasattr(item, 'nutritional_info') else None,
        "modifiers": modifiers
    }


# =============================================================================
# CART MANAGEMENT
# =============================================================================

@router.post("/cart/add", response_model=CartItemResponse)
@limiter.limit("30/minute")
async def add_to_cart(
    request: Request,
    data: CartItemRequest,
    session_token: str,
    db: Session = Depends(get_db)
):
    """Add item to cart"""
    session = _get_valid_session(session_token, db)

    # Validate menu item
    item = db.query(MenuItem).filter(
        MenuItem.id == data.menu_item_id,
        MenuItem.active == True
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    # Check availability
    availability = db.query(MenuItemAvailability).filter(
        MenuItemAvailability.menu_item_id == item.id
    ).first()

    if availability and not availability.is_available:
        raise HTTPException(status_code=400, detail="Item is not available")

    # Calculate price with modifiers
    unit_price = float(item.price)
    modifier_price = 0

    if data.modifiers:
        for mod in data.modifiers:
            opt = db.query(ModifierOption).filter(
                ModifierOption.id == mod.get("option_id")
            ).first()
            if opt and opt.price:
                modifier_price += float(opt.price)

    unit_price += modifier_price
    total_price = unit_price * data.quantity

    # Get prep time
    prep_time = db.query(MenuItemPrepTime).filter(
        MenuItemPrepTime.menu_item_id == item.id
    ).first()

    cart_item = CustomerOrderItem(
        session_id=session.id,
        menu_item_id=item.id,
        quantity=data.quantity,
        unit_price=unit_price,
        total_price=total_price,
        modifiers=data.modifiers,
        special_requests=data.special_requests,
        estimated_prep_minutes=prep_time.standard_prep_minutes if prep_time else 15
    )
    db.add(cart_item)
    db.commit()
    db.refresh(cart_item)

    return CartItemResponse(
        id=cart_item.id,
        menu_item_id=cart_item.menu_item_id,
        menu_item_name=item.name,
        quantity=cart_item.quantity,
        unit_price=cart_item.unit_price,
        total_price=cart_item.total_price,
        modifiers=cart_item.modifiers,
        special_requests=cart_item.special_requests,
        estimated_prep_minutes=cart_item.estimated_prep_minutes,
        status=cart_item.status
    )


@router.get("/cart", response_model=List[CartItemResponse])
@limiter.limit("60/minute")
async def get_cart(
    request: Request,
    session_token: str = Query("", description="Session token"),
    db: Session = Depends(get_db)
):
    """Get current cart contents"""
    session = _get_valid_session(session_token, db)

    cart_items = db.query(CustomerOrderItem).filter(
        CustomerOrderItem.session_id == session.id,
        CustomerOrderItem.status == "in_cart"
    ).all()

    result = []
    for cart_item in cart_items:
        item = db.query(MenuItem).filter(MenuItem.id == cart_item.menu_item_id).first()
        result.append(CartItemResponse(
            id=cart_item.id,
            menu_item_id=cart_item.menu_item_id,
            menu_item_name=item.name if item else {"en": "Unknown"},
            quantity=cart_item.quantity,
            unit_price=cart_item.unit_price,
            total_price=cart_item.total_price,
            modifiers=cart_item.modifiers,
            special_requests=cart_item.special_requests,
            estimated_prep_minutes=cart_item.estimated_prep_minutes,
            status=cart_item.status
        ))

    return result


@router.put("/cart/{item_id}")
@limiter.limit("30/minute")
async def update_cart_item(
    request: Request,
    item_id: int,
    quantity: int,
    session_token: str,
    db: Session = Depends(get_db)
):
    """Update cart item quantity"""
    session = _get_valid_session(session_token, db)

    cart_item = db.query(CustomerOrderItem).filter(
        CustomerOrderItem.id == item_id,
        CustomerOrderItem.session_id == session.id,
        CustomerOrderItem.status == "in_cart"
    ).first()

    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    if quantity <= 0:
        db.delete(cart_item)
        db.commit()
        return {"message": "Item removed from cart"}

    cart_item.quantity = quantity
    cart_item.total_price = cart_item.unit_price * quantity
    db.commit()

    return {"message": "Cart updated", "quantity": quantity, "total_price": cart_item.total_price}


@router.delete("/cart/{item_id}")
@limiter.limit("30/minute")
async def remove_from_cart(
    request: Request,
    item_id: int,
    session_token: str,
    db: Session = Depends(get_db)
):
    """Remove item from cart"""
    session = _get_valid_session(session_token, db)

    cart_item = db.query(CustomerOrderItem).filter(
        CustomerOrderItem.id == item_id,
        CustomerOrderItem.session_id == session.id,
        CustomerOrderItem.status == "in_cart"
    ).first()

    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    db.delete(cart_item)
    db.commit()

    return {"message": "Item removed from cart"}


@router.delete("/cart")
@limiter.limit("30/minute")
async def clear_cart(
    request: Request,
    session_token: str,
    db: Session = Depends(get_db)
):
    """Clear all items from cart"""
    session = _get_valid_session(session_token, db)

    db.query(CustomerOrderItem).filter(
        CustomerOrderItem.session_id == session.id,
        CustomerOrderItem.status == "in_cart"
    ).delete()
    db.commit()

    return {"message": "Cart cleared"}


# =============================================================================
# ORDER PLACEMENT
# =============================================================================

@router.post("/order/place", response_model=PlaceOrderResponse)
@limiter.limit("30/minute")
async def place_order(
    request: Request,
    session_token: str,
    db: Session = Depends(get_db)
):
    """Place order from cart"""
    session = _get_valid_session(session_token, db)

    # Get cart items
    cart_items = db.query(CustomerOrderItem).filter(
        CustomerOrderItem.session_id == session.id,
        CustomerOrderItem.status == "in_cart"
    ).all()

    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    # Calculate total prep time
    max_prep_time = max(item.estimated_prep_minutes or 15 for item in cart_items)
    total_amount = sum(item.total_price for item in cart_items)

    # Create order
    order = Order(
        venue_id=session.venue_id,
        table_id=session.table_id,
        status="new",
        order_type="dine_in",
        source="customer_app",
        total_amount=total_amount,
        notes=f"Customer self-order from table"
    )
    db.add(order)
    db.flush()

    # Create order items
    for cart_item in cart_items:
        menu_item = db.query(MenuItem).filter(MenuItem.id == cart_item.menu_item_id).first()

        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=cart_item.menu_item_id,
            quantity=cart_item.quantity,
            unit_price=cart_item.unit_price,
            total_price=cart_item.total_price,
            modifiers=cart_item.modifiers,
            notes=cart_item.special_requests,
            status="pending"
        )
        db.add(order_item)

        # Update cart item status
        cart_item.status = "ordered"
        cart_item.ordered_at = datetime.now(timezone.utc)

    # Update session stats
    session.total_orders += 1
    session.total_amount += total_amount
    session.last_activity = datetime.now(timezone.utc)

    db.commit()
    db.refresh(order)

    estimated_ready_at = datetime.now(timezone.utc) + timedelta(minutes=max_prep_time)

    # Create prep notification
    notification = CustomerPrepTimeNotification(
        session_id=session.id,
        order_id=order.id,
        notification_type="order_received",
        message={
            "en": f"Your order #{order.id} has been received!",
            "bg": f"Вашата поръчка #{order.id} е получена!"
        },
        estimated_ready_at=estimated_ready_at,
        estimated_wait_minutes=max_prep_time
    )
    db.add(notification)
    db.commit()

    return PlaceOrderResponse(
        order_id=order.id,
        order_number=str(order.id),
        estimated_ready_at=estimated_ready_at,
        estimated_wait_minutes=max_prep_time,
        items_count=len(cart_items),
        total_amount=total_amount
    )


@router.get("/order/status/{order_id}", response_model=OrderStatusResponse)
@limiter.limit("60/minute")
async def get_order_status(
    request: Request,
    order_id: int,
    session_token: str = Query("", description="Session token"),
    db: Session = Depends(get_db)
):
    """Get order status and prep time updates"""
    session = _get_valid_session(session_token, db)

    order = db.query(Order).filter(
        Order.id == order_id,
        Order.venue_id == session.venue_id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Get order items with status
    order_items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()

    items = []
    for oi in order_items:
        menu_item = db.query(MenuItem).filter(MenuItem.id == oi.menu_item_id).first()
        items.append({
            "id": oi.id,
            "name": menu_item.name if menu_item else {"en": "Unknown"},
            "quantity": oi.quantity,
            "status": oi.status
        })

    # Get latest notification for estimated time
    notification = db.query(CustomerPrepTimeNotification).filter(
        CustomerPrepTimeNotification.order_id == order.id
    ).order_by(CustomerPrepTimeNotification.created_at.desc()).first()

    return OrderStatusResponse(
        order_id=order.id,
        status=order.status,
        items=items,
        estimated_ready_at=notification.estimated_ready_at if notification else None,
        actual_ready_at=None,
        is_ready=order.status in ["ready", "served"]
    )


@router.get("/orders", response_model=List[dict])
@limiter.limit("60/minute")
async def get_session_orders(
    request: Request,
    session_token: str = Query("", description="Session token"),
    db: Session = Depends(get_db)
):
    """Get all orders placed in this session"""
    session = _get_valid_session(session_token, db)

    # Get orders from cart items
    cart_items = db.query(CustomerOrderItem).filter(
        CustomerOrderItem.session_id == session.id,
        CustomerOrderItem.status != "in_cart"
    ).all()

    order_ids = list(set(ci.order_id for ci in cart_items if hasattr(ci, 'order_id') and ci.order_id))

    orders = db.query(Order).filter(
        Order.venue_id == session.venue_id,
        Order.table_id == session.table_id
    ).order_by(Order.created_at.desc()).all()

    result = []
    for order in orders:
        items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        result.append({
            "order_id": order.id,
            "status": order.status,
            "total_amount": float(order.total_amount) if order.total_amount else 0,
            "items_count": len(items),
            "created_at": order.created_at
        })

    return result


# =============================================================================
# WAITER CALLS
# =============================================================================

@router.post("/waiter/call")
@limiter.limit("30/minute")
async def call_waiter(
    request: Request,
    data: WaiterCallRequest,
    session_token: str,
    db: Session = Depends(get_db)
):
    """Request waiter assistance"""
    session = _get_valid_session(session_token, db)

    # Check for recent duplicate calls
    recent_call = db.query(CustomerWaiterCall).filter(
        CustomerWaiterCall.session_id == session.id,
        CustomerWaiterCall.call_type == data.call_type,
        CustomerWaiterCall.status == "pending",
        CustomerWaiterCall.created_at >= datetime.now(timezone.utc) - timedelta(minutes=5)
    ).first()

    if recent_call:
        return {
            "message": "Request already pending",
            "call_id": recent_call.id,
            "call_type": recent_call.call_type
        }

    call = CustomerWaiterCall(
        session_id=session.id,
        call_type=data.call_type,
        message=data.message
    )
    db.add(call)
    db.commit()
    db.refresh(call)

    return {
        "message": "Waiter has been notified",
        "call_id": call.id,
        "call_type": call.call_type
    }


@router.get("/waiter/calls")
@limiter.limit("60/minute")
async def get_waiter_calls(
    request: Request,
    session_token: str = Query("", description="Session token"),
    db: Session = Depends(get_db)
):
    """Get status of waiter calls"""
    session = _get_valid_session(session_token, db)

    calls = db.query(CustomerWaiterCall).filter(
        CustomerWaiterCall.session_id == session.id
    ).order_by(CustomerWaiterCall.created_at.desc()).limit(10).all()

    return [
        {
            "id": call.id,
            "call_type": call.call_type,
            "message": call.message,
            "status": call.status,
            "created_at": call.created_at,
            "acknowledged_at": call.acknowledged_at,
            "resolved_at": call.resolved_at
        } for call in calls
    ]


# =============================================================================
# FAVORITES
# =============================================================================

@router.post("/favorites/{menu_item_id}")
@limiter.limit("30/minute")
async def add_favorite(
    request: Request,
    menu_item_id: int,
    session_token: str,
    db: Session = Depends(get_db)
):
    """Add menu item to favorites"""
    session = _get_valid_session(session_token, db)

    if not session.customer_id:
        raise HTTPException(status_code=401, detail="Login required to save favorites")

    # Check if already favorite
    existing = db.query(CustomerFavorite).filter(
        CustomerFavorite.customer_id == session.customer_id,
        CustomerFavorite.venue_id == session.venue_id,
        CustomerFavorite.menu_item_id == menu_item_id
    ).first()

    if existing:
        return {"message": "Already in favorites", "favorite_id": existing.id}

    favorite = CustomerFavorite(
        customer_id=session.customer_id,
        venue_id=session.venue_id,
        menu_item_id=menu_item_id
    )
    db.add(favorite)
    db.commit()
    db.refresh(favorite)

    return {"message": "Added to favorites", "favorite_id": favorite.id}


@router.delete("/favorites/{menu_item_id}")
@limiter.limit("30/minute")
async def remove_favorite(
    request: Request,
    menu_item_id: int,
    session_token: str,
    db: Session = Depends(get_db)
):
    """Remove menu item from favorites"""
    session = _get_valid_session(session_token, db)

    if not session.customer_id:
        raise HTTPException(status_code=401, detail="Login required")

    favorite = db.query(CustomerFavorite).filter(
        CustomerFavorite.customer_id == session.customer_id,
        CustomerFavorite.menu_item_id == menu_item_id
    ).first()

    if favorite:
        db.delete(favorite)
        db.commit()

    return {"message": "Removed from favorites"}


@router.get("/favorites")
@limiter.limit("60/minute")
async def get_favorites(
    request: Request,
    session_token: str = Query("", description="Session token"),
    db: Session = Depends(get_db)
):
    """Get customer's favorite items"""
    session = _get_valid_session(session_token, db)

    if not session.customer_id:
        return []

    favorites = db.query(CustomerFavorite).filter(
        CustomerFavorite.customer_id == session.customer_id,
        CustomerFavorite.venue_id == session.venue_id
    ).order_by(CustomerFavorite.times_ordered.desc()).all()

    result = []
    for fav in favorites:
        item = db.query(MenuItem).filter(MenuItem.id == fav.menu_item_id).first()
        if item and item.active:
            result.append({
                "id": fav.id,
                "menu_item_id": fav.menu_item_id,
                "name": item.name,
                "price": float(item.price),
                "image_url": item.image_url,
                "times_ordered": fav.times_ordered,
                "last_ordered_at": fav.last_ordered_at
            })

    return result


# =============================================================================
# NOTIFICATIONS
# =============================================================================

@router.get("/notifications")
@limiter.limit("60/minute")
async def get_notifications(
    request: Request,
    session_token: str = Query("", description="Session token"),
    unread_only: bool = False,
    db: Session = Depends(get_db)
):
    """Get prep time and order status notifications"""
    session = _get_valid_session(session_token, db)

    query = db.query(CustomerPrepTimeNotification).filter(
        CustomerPrepTimeNotification.session_id == session.id
    )

    if unread_only:
        query = query.filter(CustomerPrepTimeNotification.read == False)

    notifications = query.order_by(
        CustomerPrepTimeNotification.created_at.desc()
    ).limit(20).all()

    return [
        {
            "id": n.id,
            "type": n.notification_type,
            "message": n.message.get(session.language, n.message.get("en", "")),
            "order_id": n.order_id,
            "estimated_ready_at": n.estimated_ready_at,
            "estimated_wait_minutes": n.estimated_wait_minutes,
            "read": n.read,
            "created_at": n.created_at
        } for n in notifications
    ]


@router.post("/notifications/{notification_id}/read")
@limiter.limit("30/minute")
async def mark_notification_read(
    request: Request,
    notification_id: int,
    session_token: str,
    db: Session = Depends(get_db)
):
    """Mark notification as read"""
    session = _get_valid_session(session_token, db)

    notification = db.query(CustomerPrepTimeNotification).filter(
        CustomerPrepTimeNotification.id == notification_id,
        CustomerPrepTimeNotification.session_id == session.id
    ).first()

    if notification:
        notification.read = True
        notification.read_at = datetime.now(timezone.utc)
        db.commit()

    return {"message": "Notification marked as read"}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _get_valid_session(session_token: str, db: Session) -> CustomerOrderingSession:
    """Get and validate a customer ordering session"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Session token is required")

    session = db.query(CustomerOrderingSession).filter(
        CustomerOrderingSession.session_token == session_token,
        CustomerOrderingSession.status == "active"
    ).first()

    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    if session.expires_at and session.expires_at < datetime.now(timezone.utc):
        session.status = "expired"
        db.commit()
        raise HTTPException(status_code=401, detail="Session expired")

    # Update last activity
    session.last_activity = datetime.now(timezone.utc)
    db.commit()

    return session


def _detect_device_type(request: Request) -> str:
    """Detect device type from user agent"""
    user_agent = request.headers.get("user-agent", "").lower()

    if "mobile" in user_agent or "android" in user_agent or "iphone" in user_agent:
        return "mobile"
    elif "tablet" in user_agent or "ipad" in user_agent:
        return "tablet"
    return "desktop"

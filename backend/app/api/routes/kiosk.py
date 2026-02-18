"""
Kiosk Mode API Endpoints
Self-service kiosk configuration and ordering
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.db.session import get_db
from app.core.rbac import get_current_user
from app.models import (
    StaffUser, KioskConfig, Order, OrderItem, Table, MenuItem,
    ModifierOption, OrderStatus
)
from app.schemas import KioskModeConfig, KioskOrderCreate
from app.core.rate_limit import limiter

router = APIRouter()


@router.get("/")
@limiter.limit("60/minute")
async def get_kiosk_root(request: Request, db: Session = Depends(get_db)):
    """Kiosk mode overview."""
    return {"module": "kiosk", "status": "active", "endpoints": ["/config", "/orders/{venue_id}/queue", "/orders/{order_number}/status"]}


@router.get("/config", response_model=KioskModeConfig)
@limiter.limit("60/minute")
async def get_kiosk_config(
    request: Request,
    venue_id: int = Query(1, description="Venue ID"),
    db: Session = Depends(get_db)
):
    """Get kiosk configuration for a venue (public endpoint)"""
    config = db.query(KioskConfig).filter(
        KioskConfig.venue_id == venue_id
    ).first()

    if not config:
        # Return default config
        return KioskModeConfig(
            venue_id=venue_id,
            enabled=False
        )


    return KioskModeConfig(
        venue_id=config.venue_id,
        enabled=config.enabled,
        idle_timeout_seconds=config.idle_timeout_seconds,
        show_prices=config.show_prices,
        allow_cash_payment=config.allow_cash_payment,
        allow_card_payment=config.allow_card_payment,
        require_phone_number=config.require_phone_number,
        show_allergens=config.show_allergens,
        show_calories=config.show_calories,
        language_options=config.language_options or ["bg", "en"],
        default_language=config.default_language or "bg",
        receipt_print_mode=config.receipt_print_mode,
        custom_welcome_message=config.custom_welcome_message,
        custom_thank_you_message=config.custom_thank_you_message
    )


@router.put("/config", response_model=KioskModeConfig)
@limiter.limit("30/minute")
async def update_kiosk_config(
    request: Request,
    data: KioskModeConfig,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Update kiosk configuration (admin only)"""
    if current_user.role not in ["owner", "manager"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    if data.venue_id != current_user.venue_id:
        raise HTTPException(status_code=403, detail="Cannot modify other venue's config")

    config = db.query(KioskConfig).filter(
        KioskConfig.venue_id == data.venue_id
    ).first()

    if not config:
        config = KioskConfig(venue_id=data.venue_id)
        db.add(config)

    config.enabled = data.enabled
    config.idle_timeout_seconds = data.idle_timeout_seconds
    config.show_prices = data.show_prices
    config.allow_cash_payment = data.allow_cash_payment
    config.allow_card_payment = data.allow_card_payment
    config.require_phone_number = data.require_phone_number
    config.show_allergens = data.show_allergens
    config.show_calories = data.show_calories
    config.language_options = data.language_options
    config.default_language = data.default_language
    config.receipt_print_mode = data.receipt_print_mode
    config.custom_welcome_message = data.custom_welcome_message
    config.custom_thank_you_message = data.custom_thank_you_message

    db.commit()
    db.refresh(config)

    return data


@router.post("/order")
@limiter.limit("30/minute")
async def create_kiosk_order(
    request: Request,
    data: KioskOrderCreate,
    db: Session = Depends(get_db)
):
    """Create an order from kiosk (public endpoint)"""
    # Verify kiosk is enabled
    config = db.query(KioskConfig).filter(
        KioskConfig.venue_id == data.venue_id,
        KioskConfig.enabled == True
    ).first()

    if not config:
        raise HTTPException(status_code=400, detail="Kiosk ordering not enabled")

    # Check phone requirement
    if config.require_phone_number and not data.customer_phone:
        raise HTTPException(status_code=400, detail="Phone number required")

    # Get or create kiosk table
    kiosk_table = db.query(Table).filter(
        Table.location_id == data.venue_id,
        Table.number == "KIOSK"
    ).first()

    if not kiosk_table:
        kiosk_table = Table(
            location_id=data.venue_id,
            number="KIOSK",
            capacity=0,
            status="available",
            area="Self-service kiosk"
        )
        db.add(kiosk_table)
        db.flush()

    # Generate order number
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    count = db.query(Order).filter(
        Order.order_number.like(f"K{today}%")
    ).count()
    order_number = f"K{today}{count + 1:04d}"

    # Create order
    order = Order(
        table_id=kiosk_table.id,
        order_number=order_number,
        status=OrderStatus.NEW,
        order_type="kiosk",
        customer_name="Kiosk Customer",
        customer_phone=data.customer_phone,
        notes=data.notes,
        payment_method=data.payment_method,
        payment_status="pending" if data.payment_method == "cash" else "processing"
    )
    db.add(order)
    db.flush()

    # Add items
    total = 0
    station_id = None

    for item_data in data.items:
        menu_item = db.query(MenuItem).filter(MenuItem.id == item_data.menu_item_id).first()
        if not menu_item:
            continue

        station_id = station_id or menu_item.station_id

        # Calculate item price with modifiers
        item_price = menu_item.price
        for mod in item_data.modifiers:
            modifier = db.query(ModifierOption).filter(
                ModifierOption.id == mod.modifier_option_id
            ).first()
            if modifier:
                item_price += modifier.price_delta

        subtotal = item_price * item_data.quantity

        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=menu_item.id,
            quantity=item_data.quantity,
            unit_price=item_price,
            subtotal=subtotal,
            notes=item_data.notes
        )
        db.add(order_item)
        total += subtotal

    order.total = round(total, 2)
    order.station_id = station_id

    db.commit()
    db.refresh(order)

    return {
        "order_id": order.id,
        "order_number": order.order_number,
        "total": order.total,
        "status": order.status.value,
        "payment_status": order.payment_status,
        "message": "Order created successfully. Please proceed to payment." if data.payment_method == "card" else "Order created. Please pay at counter."
    }


@router.get("/orders/{venue_id}/queue")
@limiter.limit("60/minute")
async def get_kiosk_order_queue(
    request: Request,
    venue_id: int,
    db: Session = Depends(get_db)
):
    """Get kiosk order queue for display (public endpoint)"""
    # Get kiosk table
    kiosk_table = db.query(Table).filter(
        Table.location_id == venue_id,
        Table.number == "KIOSK"
    ).first()

    if not kiosk_table:
        return {"preparing": [], "ready": []}

    # Get orders
    preparing_orders = db.query(Order).filter(
        Order.table_id == kiosk_table.id,
        Order.status.in_([OrderStatus.ACCEPTED, OrderStatus.PREPARING])
    ).order_by(Order.created_at).all()

    ready_orders = db.query(Order).filter(
        Order.table_id == kiosk_table.id,
        Order.status == OrderStatus.READY
    ).order_by(Order.created_at).all()

    return {
        "preparing": [
            {
                "order_number": o.order_number,
                "status": o.status.value
            }
            for o in preparing_orders
        ],
        "ready": [
            {
                "order_number": o.order_number
            }
            for o in ready_orders
        ]
    }


@router.get("/orders/{order_number}/status")
@limiter.limit("60/minute")
async def get_kiosk_order_status(
    request: Request,
    order_number: str,
    db: Session = Depends(get_db)
):
    """Get order status for kiosk display (public endpoint)"""
    order = db.query(Order).filter(Order.order_number == order_number).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Estimate wait time based on queue position
    queue_ahead = db.query(Order).filter(
        Order.table_id == order.table_id,
        Order.status.in_([OrderStatus.NEW, OrderStatus.ACCEPTED, OrderStatus.PREPARING]),
        Order.created_at < order.created_at
    ).count()

    estimated_wait = queue_ahead * 5  # 5 min per order estimate

    return {
        "order_number": order.order_number,
        "status": order.status.value,
        "payment_status": order.payment_status,
        "total": order.total,
        "queue_position": queue_ahead + 1 if order.status in [OrderStatus.NEW, OrderStatus.ACCEPTED, OrderStatus.PREPARING] else 0,
        "estimated_wait_minutes": estimated_wait,
        "created_at": order.created_at.isoformat()
    }

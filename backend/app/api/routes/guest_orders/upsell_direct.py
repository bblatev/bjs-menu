"""Upsell suggestions & direct ordering"""
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

# ==================== UPSELL SUGGESTIONS (#2) ====================


@router.get("/upsell-suggestions")
@limiter.limit("60/minute")
def get_upsell_suggestions(
    request: Request,
    db: DbSession,
    cart_items: str = Query("", description="Comma-separated item IDs in cart"),
    venue_id: int = 1,
    limit: int = 4,
):
    """Get AI-powered upsell suggestions based on current cart items.
    Uses collaborative filtering: items frequently ordered together."""
    cart_ids = [int(x.strip()) for x in cart_items.split(",") if x.strip().isdigit()]

    if not cart_ids:
        # Return popular items as fallback
        popular = db.query(MenuItem).filter(
            MenuItem.venue_id == venue_id,
            MenuItem.is_available == True,
        ).order_by(MenuItem.sort_order.asc()).limit(limit).all()
        return {
            "suggestions": [
                {
                    "id": item.id,
                    "name": item.name,
                    "price": float(item.price or 0),
                    "category": item.category_name if hasattr(item, 'category_name') else None,
                    "reason": "Popular item",
                }
                for item in popular
            ],
            "strategy": "popular",
        }

    # Find items commonly ordered with cart items (co-occurrence)
    from sqlalchemy import func, and_

    # Get order IDs that contain any of the cart items
    order_ids_subq = db.query(CheckItem.check_id).filter(
        CheckItem.menu_item_id.in_(cart_ids)
    ).subquery()

    # Find other items from those same orders, excluding cart items
    suggestions_query = db.query(
        CheckItem.menu_item_id,
        func.count(CheckItem.id).label("freq"),
    ).filter(
        CheckItem.check_id.in_(db.query(order_ids_subq)),
        ~CheckItem.menu_item_id.in_(cart_ids),
    ).group_by(
        CheckItem.menu_item_id
    ).order_by(
        func.count(CheckItem.id).desc()
    ).limit(limit)

    suggested_ids = [row[0] for row in suggestions_query.all()]

    if not suggested_ids:
        return {"suggestions": [], "strategy": "no_data"}

    items = db.query(MenuItem).filter(MenuItem.id.in_(suggested_ids)).all()
    return {
        "suggestions": [
            {
                "id": item.id,
                "name": item.name,
                "price": float(item.price or 0),
                "image_url": item.image_url if hasattr(item, 'image_url') else None,
                "reason": "Frequently ordered together",
            }
            for item in items
        ],
        "strategy": "collaborative_filtering",
    }


# ==================== DIRECT ORDERING (#80) ====================


class DeliveryOrderRequest(BaseModel):
    """Schema for commission-free delivery order."""
    items: list
    delivery_address: str
    delivery_notes: str = ""
    customer_name: str
    customer_phone: str
    customer_email: str = ""
    payment_method: str = "card"  # card, cash
    venue_id: int = 1


class PickupOrderRequest(BaseModel):
    """Schema for pickup order."""
    items: list
    pickup_time: str  # ISO datetime
    customer_name: str
    customer_phone: str
    customer_email: str = ""
    payment_method: str = "card"
    venue_id: int = 1


@router.post("/delivery")
@limiter.limit("30/minute")
def create_delivery_order(
    request: Request,
    order_data: DeliveryOrderRequest,
    db: DbSession,
):
    """Create a commission-free direct delivery order.
    Public endpoint — no auth required."""
    from app.models.platform_compat import Order, OrderItem

    # Create order
    order = Order(
        venue_id=order_data.venue_id,
        order_type="delivery",
        status="pending",
        customer_name=sanitize_text(order_data.customer_name),
        customer_phone=sanitize_text(order_data.customer_phone),
        customer_email=sanitize_text(order_data.customer_email) if order_data.customer_email else None,
        delivery_address=sanitize_text(order_data.delivery_address),
        delivery_notes=sanitize_text(order_data.delivery_notes) if order_data.delivery_notes else None,
        payment_method=order_data.payment_method,
        source="direct_website",
    )
    db.add(order)
    db.flush()

    total = Decimal("0")
    for item_data in order_data.items:
        menu_item = db.query(MenuItem).filter(MenuItem.id == item_data.get("menu_item_id")).first()
        if not menu_item:
            continue
        qty = int(item_data.get("quantity", 1))
        price = Decimal(str(menu_item.price or 0))
        line_total = price * qty

        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=menu_item.id,
            item_name=menu_item.name,
            quantity=qty,
            unit_price=price,
            total_price=line_total,
        )
        db.add(order_item)
        total += line_total

    order.total_amount = total
    db.commit()
    db.refresh(order)

    return {
        "order_id": order.id,
        "status": "pending",
        "total": float(total),
        "estimated_delivery": "45-60 minutes",
        "message": "Order placed successfully! You'll receive a confirmation shortly.",
    }


@router.post("/pickup")
@limiter.limit("30/minute")
def create_pickup_order(
    request: Request,
    order_data: PickupOrderRequest,
    db: DbSession,
):
    """Create a pickup order.
    Public endpoint — no auth required."""
    from app.models.platform_compat import Order, OrderItem

    order = Order(
        venue_id=order_data.venue_id,
        order_type="pickup",
        status="pending",
        customer_name=sanitize_text(order_data.customer_name),
        customer_phone=sanitize_text(order_data.customer_phone),
        customer_email=sanitize_text(order_data.customer_email) if order_data.customer_email else None,
        pickup_time=order_data.pickup_time,
        payment_method=order_data.payment_method,
        source="direct_website",
    )
    db.add(order)
    db.flush()

    total = Decimal("0")
    for item_data in order_data.items:
        menu_item = db.query(MenuItem).filter(MenuItem.id == item_data.get("menu_item_id")).first()
        if not menu_item:
            continue
        qty = int(item_data.get("quantity", 1))
        price = Decimal(str(menu_item.price or 0))
        line_total = price * qty

        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=menu_item.id,
            item_name=menu_item.name,
            quantity=qty,
            unit_price=price,
            total_price=line_total,
        )
        db.add(order_item)
        total += line_total

    order.total_amount = total
    db.commit()
    db.refresh(order)

    return {
        "order_id": order.id,
        "status": "pending",
        "total": float(total),
        "pickup_time": order_data.pickup_time,
        "message": "Pickup order placed! Your order will be ready at the specified time.",
    }

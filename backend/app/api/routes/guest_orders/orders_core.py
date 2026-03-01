"""Order CRUD, void, cancel, refund"""
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
from app.api.routes.guest_orders._shared import _get_table_by_token


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

    # Also create KitchenOrder(s) for KDS — group items by station
    # Pre-fetch all menu items in one query to avoid N+1
    menu_item_ids = [oi.menu_item_id for oi in order.items]
    menu_items_map = {
        mi.id: mi for mi in db.query(MenuItem).filter(MenuItem.id.in_(menu_item_ids)).all()
    }

    station_items = {}
    for order_item in order.items:
        mi = menu_items_map.get(order_item.menu_item_id)
        station_key = mi.station if mi and mi.station else "default"
        station_items.setdefault(station_key, [])
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

    # Single commit for order + kitchen orders + table update
    db.commit()
    db.refresh(db_order)

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

    return paginated_response(
        items=[
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
        total=total,
        skip=offset,
        limit=limit,
    )



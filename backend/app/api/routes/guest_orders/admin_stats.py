"""Admin endpoints & statistics"""
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
from app.api.routes.guest_orders._shared import _menu_item_to_admin_dict

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



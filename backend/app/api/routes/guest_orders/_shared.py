"""Guest ordering routes - customer-facing table ordering via QR code - using database."""

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


class ModifierSelection(BaseModel):
    modifier_id: Optional[int] = None
    group_id: Optional[int] = None
    option_id: Optional[int] = None
    name: Optional[str] = None
    price: Optional[float] = 0.0


class GuestOrderItem(BaseModel):
    menu_item_id: int
    quantity: int
    notes: Optional[str] = Field(None, max_length=500)
    modifiers: Optional[List[ModifierSelection]] = None

    @field_validator("quantity", mode="before")
    @classmethod
    def _validate_quantity(cls, v):
        if v is not None and int(v) < 1:
            raise ValueError("quantity must be at least 1")
        if v is not None and int(v) > 99:
            raise ValueError("quantity cannot exceed 99")
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
    """Get table info from database.

    Only looks up by cryptographic token — never by table number.
    This prevents guests from ordering on arbitrary tables by guessing numbers.
    """
    if not token or len(token) < 8:
        raise HTTPException(
            status_code=400,
            detail="Invalid table token. Please scan a valid table QR code.",
        )

    db_table = db.query(Table).filter(Table.token == token).first()
    if db_table:
        return {
            "id": db_table.id,
            "number": db_table.number,
            "capacity": db_table.capacity or 4,
            "status": db_table.status or "available",
            "area": db_table.area or "Main Floor",
        }

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



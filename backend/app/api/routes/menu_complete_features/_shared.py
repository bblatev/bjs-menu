"""
Complete Menu Management Features - Competitor Parity
Implements all menu features adapted for the bjs-menu system.

Features:
1. Menu Item Variants (sizes, portions)
2. Combo/Bundle Management
3. Menu Tags (vegan, spicy, new, popular)
4. Upsell/Cross-sell Suggestions
5. Limited-Time Offers with Auto-Expiry
6. 86'd Items (Out of Stock Management)
7. QR Code Menu Generation
8. Digital Menu Board Management
9. Menu Performance Analytics
"""


import logging
from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import func, desc
from typing import List, Optional, Dict
from pydantic import BaseModel, ConfigDict
from datetime import datetime, date, timezone, time, timedelta
import uuid
import io
import base64

from app.core.rate_limit import limiter
from app.db.session import DbSession
from app.core.rbac import CurrentUser, OptionalCurrentUser

logger = logging.getLogger(__name__)



# =============================================================================
# SCHEMAS
# =============================================================================

# --- Menu Item Variants ---
class MenuItemVariantCreate(BaseModel):
    name: str
    variant_type: str = "size"
    sku_suffix: Optional[str] = None
    price: float
    cost: Optional[float] = None
    calories: Optional[int] = None
    portion_size: Optional[str] = None
    portion_multiplier: float = 1.0
    is_default: bool = False
    sort_order: int = 0
    active: bool = True


class MenuItemVariantResponse(BaseModel):
    id: int
    menu_item_id: int
    name: str
    variant_type: str
    sku_suffix: Optional[str] = None
    price: float
    cost: Optional[float] = None
    calories: Optional[int] = None
    portion_size: Optional[str] = None
    is_default: bool
    sort_order: int
    active: bool
    profit_margin: Optional[float] = None


# --- Combos/Bundles ---
class ComboItemCreate(BaseModel):
    menu_item_id: int
    quantity: int = 1
    is_required: bool = True
    max_selections: int = 1
    allowed_substitutions: Optional[List[int]] = None


class ComboCreate(BaseModel):
    name: str
    description: Optional[str] = None
    items: List[ComboItemCreate]
    pricing_type: str = "fixed"
    fixed_price: Optional[float] = None
    discount_percentage: Optional[float] = None
    image_url: Optional[str] = None
    available_from: Optional[str] = None  # "HH:MM"
    available_until: Optional[str] = None
    available_days: List[int] = [0, 1, 2, 3, 4, 5, 6]
    max_per_order: Optional[int] = None
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None
    active: bool = True


class ComboResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    items: List[Dict]
    pricing_type: str
    price: Optional[float] = None
    discount_percentage: Optional[float] = None
    original_total: float
    savings: float
    savings_percentage: float
    is_available_now: bool
    active: bool
    created_at: str


# --- Menu Tags ---
class MenuTagCreate(BaseModel):
    code: str
    name: str
    icon: Optional[str] = None
    color: Optional[str] = None
    description: Optional[str] = None
    sort_order: int = 0
    active: bool = True


class MenuTagResponse(BaseModel):
    id: int
    code: str
    name: str
    icon: Optional[str] = None
    color: Optional[str] = None
    description: Optional[str] = None
    items_count: int = 0
    sort_order: int
    active: bool


# --- Upsell/Cross-sell ---
class UpsellRuleCreate(BaseModel):
    source_item_id: int
    suggestion_type: str  # upsell, cross_sell, upgrade, addon
    suggested_item_id: Optional[int] = None
    suggested_category_id: Optional[int] = None
    message: Optional[str] = None
    discount_percentage: Optional[float] = None
    priority: int = 0
    active: bool = True


# --- Limited Time Offers ---
class LimitedTimeOfferCreate(BaseModel):
    name: str
    description: Optional[str] = None
    menu_item_id: Optional[int] = None
    category_id: Optional[int] = None
    offer_type: str  # new_item, discount, special_price, bundle
    original_price: Optional[float] = None
    offer_price: Optional[float] = None
    discount_percentage: Optional[float] = None
    start_datetime: datetime
    end_datetime: datetime
    max_quantity: Optional[int] = None
    max_per_customer: Optional[int] = None
    image_url: Optional[str] = None
    badge_text: Optional[str] = None
    countdown_enabled: bool = True
    auto_disable_when_sold_out: bool = True
    active: bool = True


class LimitedTimeOfferResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    menu_item_id: Optional[int] = None
    offer_type: str
    original_price: Optional[float] = None
    offer_price: Optional[float] = None
    discount_percentage: Optional[float] = None
    savings: Optional[float] = None
    start_datetime: str
    end_datetime: str
    remaining_quantity: Optional[int] = None
    is_active: bool
    is_expired: bool
    time_remaining_seconds: Optional[int] = None
    badge_text: Optional[str] = None


# --- 86'd Items ---
class Item86Request(BaseModel):
    menu_item_id: int
    reason: str  # sold_out, ingredient_missing, equipment_issue, quality_issue
    expected_back: Optional[str] = None
    auto_restore: bool = True
    notify_staff: bool = True
    alternative_items: Optional[List[int]] = None
    notes: Optional[str] = None


class Item86Response(BaseModel):
    id: int
    menu_item_id: int
    menu_item_name: str
    reason: str
    marked_at: str
    marked_by: str
    expected_back: Optional[str] = None
    is_active: bool
    alternative_items: Optional[List[Dict]] = None
    duration_minutes: int


# --- Digital Menu Board ---
class DigitalMenuBoardCreate(BaseModel):
    name: str
    display_type: str = "full_menu"
    categories: Optional[List[str]] = None  # category strings (bjs-menu uses string category)
    items: Optional[List[int]] = None
    layout: str = "grid"
    columns: int = 3
    show_prices: bool = True
    show_descriptions: bool = True
    show_images: bool = True
    show_calories: bool = False
    show_allergens: bool = True
    rotation_seconds: int = 10
    theme: str = "dark"
    custom_css: Optional[str] = None
    header_text: Optional[str] = None
    footer_text: Optional[str] = None
    background_image: Optional[str] = None
    auto_hide_unavailable: bool = True
    active: bool = True


# --- Menu Engineering ---
class MenuEngineeringItem(BaseModel):
    menu_item_id: int
    name: str
    category: str
    price: float
    cost: float
    profit_margin: float
    profit_margin_percentage: float
    quantity_sold: int
    revenue: float
    profit: float
    popularity_index: float
    profitability_index: float
    classification: str  # star, puzzle, plow_horse, dog
    recommendation: str
    trend: str


class MenuEngineeringReport(BaseModel):
    period_start: str
    period_end: str
    total_items: int
    total_revenue: float
    total_profit: float
    average_profit_margin: float
    stars: List[MenuEngineeringItem]
    puzzles: List[MenuEngineeringItem]
    plow_horses: List[MenuEngineeringItem]
    dogs: List[MenuEngineeringItem]
    recommendations: List[Dict[str, str]]


# =============================================================================
# IN-MEMORY STORES (features without DB models)
# =============================================================================
_variants: list = []
_tags: list = []
_tag_assignments: list = []
_upsell_rules: list = []
_limited_offers: list = []
_item86_records: list = []
_digital_boards: list = []
_next_ids = {
    "variant": 1, "tag": 1, "tag_assignment": 1,
    "upsell_rule": 1, "offer": 1, "item86": 1, "board": 1,
}


# =============================================================================
# MENU ITEM VARIANTS
# =============================================================================


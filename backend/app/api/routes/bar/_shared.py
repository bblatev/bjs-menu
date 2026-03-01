"""Bar management API routes - using real database data."""

from typing import Any, List, Optional, Union
from decimal import Decimal
from datetime import datetime, time, date, timezone

from fastapi import APIRouter, Query, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import func

from app.core.rate_limit import limiter

from app.core.rbac import CurrentUser, OptionalCurrentUser, RequireManager
from app.db.session import DbSession
from app.models.product import Product
from app.models.stock import StockOnHand, StockMovement, MovementReason
from app.models.recipe import Recipe, RecipeLine
from app.models.advanced_features import HappyHour, WasteTrackingEntry, WasteCategory
from app.models.hardware import BarTab



# ==================== RESPONSE MODELS ====================

class BarStats(BaseModel):
    """Bar statistics - matches frontend expectations."""
    total_sales: float = 0.0
    total_cost: float = 0.0
    pour_cost_percentage: float = 0.0
    avg_ticket: float = 0.0
    top_cocktail: str = ""
    spillage_today: float = 0.0
    low_stock_items: int = 0
    active_recipes: int = 0
    period: str = "today"


class TopDrink(BaseModel):
    """Top drink item - matches frontend expectations."""
    id: int
    name: str
    category: str
    sold_today: int
    revenue: float
    pour_cost: float
    margin: float


class InventoryAlert(BaseModel):
    """Inventory alert - matches frontend expectations."""
    id: int
    item_name: str
    current_stock: float
    par_level: float
    unit: str
    status: str  # critical, low, reorder


class RecentPour(BaseModel):
    """Recent pour activity - matches frontend expectations."""
    id: int
    drink_name: str
    bartender: str
    time: str
    type: str  # sale, comp, spillage, waste
    amount: str
    cost: float


class SpillageRecordCreate(BaseModel):
    """Spillage record creation model."""
    item: Optional[str] = None
    item_name: Optional[str] = None  # Alias for compatibility
    product_id: Optional[int] = None
    quantity: float
    unit: str = "ml"
    reason: str
    recorded_by: Optional[str] = None
    notes: Optional[str] = None
    cost: float = 0.0


# ==================== ROUTES ====================


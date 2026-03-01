from datetime import timezone
"""
Competitor Features API Endpoints
Toast, TouchBistro, iiko feature parity
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import date, datetime, timedelta
from pydantic import BaseModel, ConfigDict
import os
import uuid
import logging
import re

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.core.rbac import get_current_user
from app.models import StaffUser, MenuItem, StockItem, Supplier, PurchaseOrder, PurchaseOrderItem
try:
    from app.services.competitor_features_service import (
        MenuEngineeringService, Item86Service, DemandForecastingService,
        AutoPurchaseOrderService, FoodCostService, SupplierPerformanceService,
        ParLevelService, WasteAnalyticsService, RecipeScalingService,
        StockTakingService
    )
except ImportError as _e:
    import logging as _logging
    _logging.getLogger(__name__).warning(f"Competitor features service import failed: {_e}")
    MenuEngineeringService = None
    Item86Service = None
    DemandForecastingService = None
    AutoPurchaseOrderService = None
    FoodCostService = None
    SupplierPerformanceService = None
    ParLevelService = None
    WasteAnalyticsService = None
    RecipeScalingService = None
    StockTakingService = None
try:
    from app.models.competitor_features import (
        Item86Config, Item86Log, IngredientForecast,
        AutoPurchaseOrderRule, SuggestedPurchaseOrder, FoodCostSnapshot,
        SupplierPerformance, SupplierIssue, ParLevelConfig, WasteLog,
        RecipeScaleLog, StockTake, StockTakeItem, ScannedInvoice,
        InvoiceMatchingRule
    )
except ImportError as _e:
    import logging as _logging
    _logging.getLogger(__name__).warning(f"Competitor features model import failed: {_e}")
    Item86Config = None
    Item86Log = None
    IngredientForecast = None
    AutoPurchaseOrderRule = None
    SuggestedPurchaseOrder = None
    FoodCostSnapshot = None
    SupplierPerformance = None
    SupplierIssue = None
    ParLevelConfig = None
    WasteLog = None
    RecipeScaleLog = None
    StockTake = None
    StockTakeItem = None
    ScannedInvoice = None
    InvoiceMatchingRule = None

try:
    from app.models.feature_models import MenuEngineeringReport, DemandForecast
except ImportError as _e:
    import logging as _logging
    _logging.getLogger(__name__).warning(f"Feature models import failed: {_e}")
    MenuEngineeringReport = None
    DemandForecast = None




def require_manager(current_user = Depends(get_current_user)):
    """Require manager or above role."""
    if not hasattr(current_user, 'role'):
        return current_user
    if current_user.role not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Manager access required")
    return current_user



# =============================================================================
# SCHEMAS
# =============================================================================

class DateRangeRequest(BaseModel):
    period_start: date
    period_end: date


class MenuEngineeringReportResponse(BaseModel):
    id: int
    report_name: str
    period_start: date
    period_end: date
    total_revenue: float
    total_food_cost: float
    total_gross_profit: float
    overall_food_cost_percent: float
    stars_count: int
    puzzles_count: int
    dogs_count: int
    cash_cows_count: int
    items_to_promote: List[int]
    items_to_reprice: List[int]
    items_to_remove: List[int]
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Item86ConfigUpdate(BaseModel):
    auto_86_enabled: bool = True
    auto_restore_enabled: bool = True
    threshold_quantity: float = 0.0
    notify_kitchen: bool = True
    notify_floor: bool = True
    notify_manager: bool = True


class Item86LogResponse(BaseModel):
    id: int
    menu_item_id: int
    event_type: str
    triggered_by: str
    reason: Optional[str]
    started_at: datetime
    ended_at: Optional[datetime]
    duration_minutes: Optional[int]

    model_config = ConfigDict(from_attributes=True)


class DemandForecastResponse(BaseModel):
    id: int
    forecast_date: date
    menu_item_id: Optional[int]
    predicted_quantity: int
    confidence_low: int
    confidence_high: int
    confidence_score: float
    day_of_week: Optional[int]
    historical_avg: Optional[float]
    trend_factor: float

    model_config = ConfigDict(from_attributes=True)


class IngredientForecastResponse(BaseModel):
    id: int
    forecast_date: date
    stock_item_id: int
    predicted_usage: float
    current_stock: float
    will_stock_out: bool
    days_of_stock: Optional[float]
    suggested_order_quantity: float

    model_config = ConfigDict(from_attributes=True)


class AutoPORuleCreate(BaseModel):
    stock_item_id: int
    reorder_point: float
    reorder_quantity: float
    use_par_level: bool = False
    par_level: Optional[float] = None
    preferred_supplier_id: Optional[int] = None
    minimum_order_quantity: Optional[float] = None


class SuggestedPOResponse(BaseModel):
    id: int
    supplier_id: int
    status: str
    items: List[dict]
    subtotal: float
    trigger_reason: str
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FoodCostResponse(BaseModel):
    id: int
    menu_item_id: int
    ingredients: List[dict]
    ingredient_cost: float
    adjusted_cost: float
    total_plate_cost: float
    menu_price: float
    food_cost_percent: float
    contribution_margin: float
    gross_profit_percent: float
    suggested_price_for_target: Optional[float]
    cost_change_percent: Optional[float]
    calculated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SupplierPerformanceResponse(BaseModel):
    id: int
    supplier_id: int
    period_start: date
    period_end: date
    total_orders: int
    total_order_value: float
    on_time_percent: float
    quality_score: float
    overall_score: float

    model_config = ConfigDict(from_attributes=True)


class SupplierIssueCreate(BaseModel):
    supplier_id: int
    issue_type: str
    severity: str
    description: str
    purchase_order_id: Optional[int] = None
    affected_items: Optional[List[dict]] = None


class WasteLogCreate(BaseModel):
    item_name: str
    quantity: float
    unit: str
    waste_type: str
    stock_item_id: Optional[int] = None
    menu_item_id: Optional[int] = None
    cause: Optional[str] = None
    notes: Optional[str] = None
    station_id: Optional[int] = None


class WasteLogResponse(BaseModel):
    id: int
    item_name: str
    quantity: float
    unit: str
    total_cost: float
    waste_type: str
    cause: Optional[str]
    is_preventable: bool
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WasteAnalyticsResponse(BaseModel):
    id: int
    analytics_date: date
    period_type: str
    total_waste_cost: float
    total_waste_quantity: float
    waste_percent_of_revenue: float
    waste_by_type: Optional[dict]
    top_waste_items: Optional[List[dict]]
    preventable_waste_cost: float
    preventable_waste_percent: float

    model_config = ConfigDict(from_attributes=True)


class RecipeScaleRequest(BaseModel):
    target_yield: float
    purpose: Optional[str] = None


class RecipeScaleResponse(BaseModel):
    id: int
    menu_item_id: int
    original_yield: float
    scaled_yield: float
    scale_factor: float
    scaled_ingredients: List[dict]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StockTakeCreate(BaseModel):
    name: Optional[str] = None
    scope_type: str = "full"
    blind_count: bool = True
    category_ids: Optional[List[int]] = None


class StockTakeResponse(BaseModel):
    id: int
    stock_take_number: str
    name: Optional[str]
    scope_type: str
    status: str
    items_counted: int
    items_with_variance: int
    total_expected_value: float
    total_counted_value: float
    total_variance_value: float
    variance_percent: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CountRecordRequest(BaseModel):
    counted_quantity: float
    location: Optional[str] = None


class ParLevelConfigResponse(BaseModel):
    id: int
    stock_item_id: int
    minimum_level: float
    par_level: float
    maximum_level: Optional[float]
    safety_stock: float
    average_daily_usage: Optional[float]
    last_calculated: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# MENU ENGINEERING ENDPOINTS
# =============================================================================


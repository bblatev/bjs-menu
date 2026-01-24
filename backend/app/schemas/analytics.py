"""Analytics & Conversational AI schemas - Lightspeed style."""

from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field

from app.models.analytics import MenuQuadrant


# Menu Engineering

class MenuAnalysisResponse(BaseModel):
    """Menu item analysis result."""
    id: int
    product_id: int
    location_id: Optional[int] = None
    analysis_period_start: datetime
    analysis_period_end: datetime
    quantity_sold: int = 0
    total_revenue: float = 0.0
    total_cost: float = 0.0
    total_profit: float = 0.0
    food_cost_percent: Optional[float] = None
    profit_margin_percent: Optional[float] = None
    contribution_margin: Optional[float] = None
    popularity_index: Optional[float] = None
    profitability_index: Optional[float] = None
    quadrant: Optional[MenuQuadrant] = None
    recommended_action: Optional[str] = None
    recommended_price: Optional[float] = None
    recommendation_reason: Optional[str] = None
    sales_trend: Optional[str] = None
    sales_trend_percent: Optional[float] = None
    calculated_at: datetime

    model_config = {"from_attributes": True}


class MenuEngineeringReport(BaseModel):
    """Complete menu engineering report."""
    location_id: Optional[int] = None
    analysis_period: Dict[str, str]
    total_items_analyzed: int
    quadrant_summary: Dict[str, int]  # Count per quadrant
    stars: List[MenuAnalysisResponse]
    puzzles: List[MenuAnalysisResponse]
    plow_horses: List[MenuAnalysisResponse]
    dogs: List[MenuAnalysisResponse]
    recommendations: List[Dict[str, Any]]


class MenuOptimizationSuggestion(BaseModel):
    """AI-generated menu optimization suggestion."""
    product_id: int
    product_name: str
    current_quadrant: MenuQuadrant
    suggestion_type: str  # "price_increase", "promote", "reposition", "remove"
    suggestion: str
    expected_impact: Dict[str, Any]
    confidence: float


# Server Performance

class ServerPerformanceResponse(BaseModel):
    """Server performance metrics."""
    id: int
    user_id: int
    location_id: Optional[int] = None
    period_start: datetime
    period_end: datetime
    total_orders: int = 0
    total_covers: int = 0
    total_revenue: float = 0.0
    total_tips: float = 0.0
    avg_ticket_size: Optional[float] = None
    avg_tip_percent: Optional[float] = None
    avg_covers_per_order: Optional[float] = None
    appetizer_attach_rate: Optional[float] = None
    dessert_attach_rate: Optional[float] = None
    drink_attach_rate: Optional[float] = None
    side_attach_rate: Optional[float] = None
    avg_table_turn_minutes: Optional[float] = None
    avg_order_to_serve_minutes: Optional[float] = None
    vs_avg_ticket: Optional[float] = None
    vs_avg_tips: Optional[float] = None
    vs_avg_upsell: Optional[float] = None
    rank_by_revenue: Optional[int] = None
    rank_by_tips: Optional[int] = None
    rank_by_upsell: Optional[int] = None
    coaching_notes: Optional[List[str]] = None
    calculated_at: datetime

    model_config = {"from_attributes": True}


class ServerRanking(BaseModel):
    """Server ranking comparison."""
    rank: int
    user_id: int
    server_name: str
    total_sales: Decimal
    avg_ticket: Decimal
    tip_percentage: float
    performance_score: float


class ServerPerformanceReport(BaseModel):
    """Server performance report."""
    date_range: Dict[str, str]
    rankings: List[ServerRanking]
    top_performer: Optional[ServerRanking] = None
    improvement_opportunities: List[Dict[str, Any]]


# Sales Forecast

class SalesForecastResponse(BaseModel):
    """Sales forecast for a date."""
    id: int
    location_id: Optional[int] = None
    product_id: Optional[int] = None
    forecast_date: datetime
    forecasted_quantity: Optional[int] = None
    forecasted_revenue: Optional[float] = None
    forecasted_covers: Optional[int] = None
    confidence_level: Optional[float] = None
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    factors: Optional[Dict[str, Any]] = None
    actual_quantity: Optional[int] = None
    actual_revenue: Optional[float] = None
    forecast_accuracy: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ForecastRequest(BaseModel):
    """Request sales forecast."""
    location_id: int
    start_date: date
    end_date: date
    include_factors: bool = True


class ForecastReport(BaseModel):
    """Complete forecast report."""
    location_id: int
    forecasts: List[SalesForecastResponse]
    total_predicted_revenue: Decimal
    avg_accuracy: Optional[float] = None
    key_factors: List[str]


# Daily Metrics

class DailyMetricsResponse(BaseModel):
    """Daily business metrics."""
    id: int
    location_id: Optional[int] = None
    date: datetime
    total_revenue: float = 0.0
    food_revenue: float = 0.0
    beverage_revenue: float = 0.0
    alcohol_revenue: float = 0.0
    total_orders: int = 0
    dine_in_orders: int = 0
    takeout_orders: int = 0
    delivery_orders: int = 0
    total_covers: int = 0
    avg_party_size: Optional[float] = None
    avg_ticket: Optional[float] = None
    avg_tip_percent: Optional[float] = None
    total_tips: float = 0.0
    cash_tips: float = 0.0
    card_tips: float = 0.0
    labor_cost: Optional[float] = None
    labor_hours: Optional[float] = None
    labor_percent: Optional[float] = None
    food_cost: Optional[float] = None
    food_cost_percent: Optional[float] = None
    beverage_cost: Optional[float] = None
    beverage_cost_percent: Optional[float] = None
    gross_profit: Optional[float] = None
    net_profit: Optional[float] = None
    vs_last_week: Optional[float] = None
    vs_last_month: Optional[float] = None
    vs_last_year: Optional[float] = None
    calculated_at: datetime

    model_config = {"from_attributes": True}


class MetricsTrend(BaseModel):
    """Metrics trend over time."""
    metric_name: str
    period: str  # "daily", "weekly", "monthly"
    data_points: List[Dict[str, Any]]
    trend: str  # "up", "down", "stable"
    change_percent: float


# Conversational AI

class ConversationalQueryRequest(BaseModel):
    """Request for conversational AI query."""
    query: str
    conversation_id: Optional[str] = None
    location_id: Optional[int] = None


class ConversationalQueryResponse(BaseModel):
    """Response from conversational AI."""
    query: str
    intent: str
    response: str
    data: Dict[str, Any] = Field(default_factory=dict)
    query_id: int
    conversation_id: Optional[str] = None
    processing_time_ms: int
    suggestions: List[str] = Field(default_factory=list)


class ConversationHistory(BaseModel):
    """Conversation history."""
    conversation_id: str
    messages: List[Dict[str, Any]]


class QueryFeedback(BaseModel):
    """Feedback on AI query response."""
    query_id: int
    was_helpful: bool


# Benchmarks

class BenchmarkResponse(BaseModel):
    """Industry benchmark data."""
    id: int
    location_id: Optional[int] = None
    period_start: datetime
    period_end: datetime
    restaurant_type: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    your_avg_ticket: Optional[float] = None
    your_covers_per_day: Optional[float] = None
    your_revenue_per_sqft: Optional[float] = None
    your_labor_percent: Optional[float] = None
    your_food_cost_percent: Optional[float] = None
    your_tip_percent: Optional[float] = None
    benchmark_avg_ticket: Optional[float] = None
    benchmark_covers_per_day: Optional[float] = None
    benchmark_revenue_per_sqft: Optional[float] = None
    benchmark_labor_percent: Optional[float] = None
    benchmark_food_cost_percent: Optional[float] = None
    benchmark_tip_percent: Optional[float] = None
    percentile_avg_ticket: Optional[int] = None
    percentile_covers: Optional[int] = None
    percentile_revenue: Optional[int] = None
    improvement_areas: Optional[List[str]] = None
    calculated_at: datetime

    model_config = {"from_attributes": True}


class BenchmarkComparison(BaseModel):
    """Compare your metrics to benchmarks."""
    metric_name: str
    your_value: Decimal
    percentile_25: Decimal
    percentile_50: Decimal
    percentile_75: Decimal
    percentile_90: Decimal
    your_percentile: int
    status: str  # "below_average", "average", "above_average", "top_performer"


class PerformanceReport(BaseModel):
    """Complete performance vs benchmark report."""
    location_id: int
    period: str
    comparisons: List[BenchmarkComparison]
    overall_score: float
    strengths: List[str]
    improvement_areas: List[str]


# Bottle Weight / Scale

class BottleWeightResponse(BaseModel):
    """Bottle weight data."""
    id: int
    product_id: Optional[int] = None
    barcode: Optional[str] = None
    product_name: str
    brand: Optional[str] = None
    full_weight: float
    empty_weight: float
    volume_ml: Optional[int] = None
    alcohol_category: Optional[str] = None
    density: Optional[float] = None
    is_verified: bool = False
    verified_by: Optional[int] = None
    verification_count: int = 0
    source: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BottleWeightCreate(BaseModel):
    """Create bottle weight entry."""
    product_id: int
    full_weight: float
    empty_weight: float
    volume_ml: int
    barcode: Optional[str] = None
    brand: Optional[str] = None
    alcohol_category: Optional[str] = None


class ScaleReadingRequest(BaseModel):
    """Process scale reading."""
    product_id: int
    weight_grams: float
    session_id: Optional[int] = None
    device_id: Optional[str] = None
    device_name: Optional[str] = None


class ScaleReadingResponse(BaseModel):
    """Scale reading result."""
    product_id: int
    product_name: str
    weight_grams: float
    remaining_percent: float
    remaining_ml: float
    reading_id: int
    method: str  # "precise" or "estimated"
    confidence: float


class VisualEstimateRequest(BaseModel):
    """Record visual fill estimate."""
    product_id: int
    estimated_percent: float = Field(..., ge=0, le=100)
    session_id: Optional[int] = None


class InventoryCountRequest(BaseModel):
    """Count inventory with partial bottles."""
    session_id: int
    product_id: int
    full_bottles: int = 0
    weight_grams: Optional[float] = None
    visual_percent: Optional[float] = None


class InventoryCountResponse(BaseModel):
    """Inventory count result."""
    session_id: int
    product_id: int
    full_bottles: int
    partial_amount: float
    total_count: float
    reading: Optional[ScaleReadingResponse] = None

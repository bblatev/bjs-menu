"""Pydantic schemas for advanced competitor features."""

from __future__ import annotations

from decimal import Decimal
from datetime import datetime, date, time
from typing import Optional, List, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# ENUMS
# ============================================================================

class WasteCategoryEnum(str, Enum):
    OVERPRODUCTION = "overproduction"
    SPOILAGE = "spoilage"
    PLATE_WASTE = "plate_waste"
    PREP_WASTE = "prep_waste"
    EXPIRED = "expired"
    DAMAGED = "damaged"
    TRIM_WASTE = "trim_waste"
    OTHER = "other"


class SentimentEnum(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class NotificationTypeEnum(str, Enum):
    ORDER_RECEIVED = "order_received"
    PREPARING = "preparing"
    READY = "ready"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"


class ChannelEnum(str, Enum):
    SMS = "sms"
    EMAIL = "email"
    PUSH = "push"


class AlertSeverityEnum(str, Enum):
    WARNING = "warning"
    CRITICAL = "critical"


# ============================================================================
# 1. AI FOOD WASTE TRACKING
# ============================================================================

class WasteTrackingEntryCreate(BaseModel):
    location_id: int
    product_id: Optional[int] = None
    category: WasteCategoryEnum
    weight_kg: Decimal = Field(gt=0)
    cost_value: Decimal = Field(ge=0)
    carbon_kg: Optional[Decimal] = None
    image_url: Optional[str] = None
    station: Optional[str] = None
    shift: Optional[str] = None
    reason: Optional[str] = None
    recorded_by_id: Optional[int] = None


class WasteTrackingEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    location_id: int
    product_id: Optional[int]
    category: WasteCategoryEnum
    weight_kg: Decimal
    cost_value: Decimal
    carbon_kg: Optional[Decimal]
    image_url: Optional[str]
    ai_detected_item: Optional[str]
    ai_confidence: Optional[float]
    ai_verified: bool
    station: Optional[str]
    shift: Optional[str]
    reason: Optional[str]
    recorded_by_id: Optional[int]
    recorded_at: datetime
    created_at: datetime


class WasteForecastCreate(BaseModel):
    location_id: int
    forecast_date: date
    predicted_waste_kg: Decimal
    predicted_cost: Decimal
    confidence_interval: Optional[Dict[str, Any]] = None


class WasteForecastResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    location_id: int
    forecast_date: date
    predicted_waste_kg: Decimal
    predicted_cost: Decimal
    confidence_interval: Optional[Dict[str, Any]]
    actual_waste_kg: Optional[Decimal]
    actual_cost: Optional[Decimal]


class WasteSummaryResponse(BaseModel):
    total_waste_kg: Decimal
    total_cost: Decimal
    total_carbon_kg: Optional[Decimal]
    by_category: Dict[str, Decimal]
    by_station: Dict[str, Decimal]
    trend_vs_previous: Optional[float]


# ============================================================================
# 2. ADVANCED LABOR FORECASTING
# ============================================================================

class LaborForecastCreate(BaseModel):
    location_id: int
    forecast_date: date
    hourly_forecasts: Dict[str, Dict[str, Any]]
    recommended_staff: Dict[str, int]
    estimated_labor_cost: Decimal
    weather_factor: Optional[float] = None
    event_factor: Optional[float] = None
    historical_factor: Optional[float] = None


class LaborForecastResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    location_id: int
    forecast_date: date
    hourly_forecasts: Dict[str, Dict[str, Any]]
    weather_factor: Optional[float]
    event_factor: Optional[float]
    historical_factor: Optional[float]
    recommended_staff: Dict[str, int]
    estimated_labor_cost: Decimal
    actual_covers: Optional[int]
    actual_revenue: Optional[Decimal]
    actual_labor_cost: Optional[Decimal]


class LaborComplianceRuleCreate(BaseModel):
    location_id: Optional[int] = None
    jurisdiction: str
    rule_type: str
    rule_name: str
    parameters: Dict[str, Any]
    penalty_amount: Optional[Decimal] = None
    is_active: bool = True


class LaborComplianceRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    location_id: Optional[int]
    jurisdiction: str
    rule_type: str
    rule_name: str
    parameters: Dict[str, Any]
    penalty_amount: Optional[Decimal]
    is_active: bool


class LaborComplianceViolationCreate(BaseModel):
    rule_id: int
    employee_id: int
    location_id: int
    violation_date: date
    description: str
    penalty_amount: Optional[Decimal] = None


class LaborComplianceViolationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rule_id: int
    employee_id: int
    location_id: int
    violation_date: date
    description: str
    penalty_amount: Optional[Decimal]
    resolved: bool
    resolved_at: Optional[datetime]
    resolution_notes: Optional[str]


# ============================================================================
# 3. ORDER THROTTLING SYSTEM
# ============================================================================

class KitchenCapacityCreate(BaseModel):
    location_id: int
    max_orders_per_15min: int = 20
    max_items_per_15min: int = 100
    station_capacities: Optional[Dict[str, int]] = None
    peak_hour_multiplier: float = 1.0
    off_peak_multiplier: float = 1.5
    is_active: bool = True


class KitchenCapacityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    location_id: int
    max_orders_per_15min: int
    max_items_per_15min: int
    station_capacities: Optional[Dict[str, int]]
    peak_hour_multiplier: float
    off_peak_multiplier: float
    is_active: bool


class OrderThrottleEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    location_id: int
    event_time: datetime
    throttle_type: str
    current_load: int
    max_capacity: int
    orders_affected: int
    avg_delay_minutes: Optional[float]
    auto_recovered: bool
    recovered_at: Optional[datetime]


class ThrottleStatusResponse(BaseModel):
    is_throttling: bool
    current_load: int
    max_capacity: int
    load_percent: float
    estimated_wait_minutes: Optional[int]
    affected_orders: int


# ============================================================================
# 4. GUEST WIFI MARKETING
# ============================================================================

class GuestWifiSessionCreate(BaseModel):
    location_id: int
    mac_address: str
    device_type: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    name: Optional[str] = None
    marketing_consent: bool = False


class GuestWifiSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    location_id: int
    mac_address: str
    device_type: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    name: Optional[str]
    marketing_consent: bool
    consent_timestamp: Optional[datetime]
    connected_at: datetime
    disconnected_at: Optional[datetime]
    session_duration_minutes: Optional[int]
    visit_count: int
    last_visit: datetime


class WifiMarketingStatsResponse(BaseModel):
    total_sessions: int
    unique_guests: int
    emails_captured: int
    phones_captured: int
    marketing_opt_ins: int
    avg_session_duration: Optional[float]
    repeat_visitors: int


# ============================================================================
# 5. A/B MENU TESTING
# ============================================================================

class MenuExperimentCreate(BaseModel):
    location_id: Optional[int] = None
    name: str
    description: Optional[str] = None
    experiment_type: str
    control_variant: Dict[str, Any]
    test_variants: List[Dict[str, Any]]
    traffic_split: Dict[str, int]
    start_date: date
    end_date: Optional[date] = None


class MenuExperimentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    location_id: Optional[int]
    name: str
    description: Optional[str]
    experiment_type: str
    control_variant: Dict[str, Any]
    test_variants: List[Dict[str, Any]]
    traffic_split: Dict[str, int]
    start_date: date
    end_date: Optional[date]
    is_active: bool
    winner_variant: Optional[str]
    statistical_significance: Optional[float]


class MenuExperimentResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    experiment_id: int
    variant_name: str
    impressions: int
    clicks: int
    orders: int
    revenue: Decimal
    conversion_rate: Optional[float]
    avg_order_value: Optional[Decimal]
    date: date


class ExperimentAnalysisResponse(BaseModel):
    experiment_id: int
    variants: List[Dict[str, Any]]
    winner: Optional[str]
    statistical_significance: float
    lift_vs_control: Dict[str, float]
    recommendation: str


# ============================================================================
# 6. DYNAMIC SURGE PRICING
# ============================================================================

class DynamicPricingRuleCreate(BaseModel):
    location_id: Optional[int] = None
    name: str
    trigger_type: str
    trigger_conditions: Dict[str, Any]
    adjustment_type: str
    adjustment_value: Decimal
    max_adjustment_percent: Optional[float] = None
    applies_to: str
    item_ids: Optional[List[int]] = None
    category_ids: Optional[List[int]] = None
    is_active: bool = True


class DynamicPricingRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    location_id: Optional[int]
    name: str
    trigger_type: str
    trigger_conditions: Dict[str, Any]
    adjustment_type: str
    adjustment_value: Decimal
    max_adjustment_percent: Optional[float]
    applies_to: str
    item_ids: Optional[List[int]]
    category_ids: Optional[List[int]]
    is_active: bool


class DynamicPriceAdjustmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rule_id: int
    location_id: int
    activated_at: datetime
    deactivated_at: Optional[datetime]
    original_price: Decimal
    adjusted_price: Decimal
    trigger_value: Optional[str]
    orders_during_surge: int
    additional_revenue: Decimal


class SurgePricingStatusResponse(BaseModel):
    is_surge_active: bool
    active_rules: List[int]
    current_multiplier: float
    affected_items: List[int]
    estimated_end_time: Optional[datetime]


# ============================================================================
# 7. CURBSIDE "I'M HERE" NOTIFICATIONS
# ============================================================================

class CurbsideOrderCreate(BaseModel):
    order_id: int
    location_id: int
    customer_name: str
    customer_phone: str
    vehicle_description: Optional[str] = None
    vehicle_color: Optional[str] = None
    vehicle_make: Optional[str] = None
    estimated_ready_time: Optional[datetime] = None


class CurbsideOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    location_id: int
    customer_name: str
    customer_phone: str
    vehicle_description: Optional[str]
    vehicle_color: Optional[str]
    vehicle_make: Optional[str]
    parking_spot: Optional[str]
    estimated_ready_time: Optional[datetime]
    customer_arrived_at: Optional[datetime]
    order_delivered_at: Optional[datetime]
    arrival_notification_sent: bool
    ready_notification_sent: bool


class CurbsideArrivalRequest(BaseModel):
    parking_spot: Optional[str] = None


class CurbsideStatusResponse(BaseModel):
    pending_arrivals: int
    arrived_waiting: int
    avg_wait_time_minutes: Optional[float]
    orders: List[CurbsideOrderResponse]


# ============================================================================
# 8. MULTI-PROVIDER DELIVERY DISPATCH
# ============================================================================

class DeliveryProviderCreate(BaseModel):
    location_id: int
    provider_name: str
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    merchant_id: Optional[str] = None
    base_fee: Decimal = Decimal("0")
    per_mile_fee: Decimal = Decimal("0")
    commission_percent: Optional[float] = None
    priority_rank: int = 1
    is_active: bool = True


class DeliveryProviderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    location_id: int
    provider_name: str
    merchant_id: Optional[str]
    base_fee: Decimal
    per_mile_fee: Decimal
    commission_percent: Optional[float]
    avg_delivery_time_minutes: Optional[float]
    reliability_score: Optional[float]
    priority_rank: int
    is_active: bool


class DeliveryDispatchRequest(BaseModel):
    order_id: int
    location_id: int
    delivery_address: str
    preferred_provider_id: Optional[int] = None
    dispatch_strategy: str = "cost_optimal"


class DeliveryDispatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    location_id: int
    selected_provider_id: int
    dispatch_reason: str
    provider_quotes: Optional[Dict[str, Any]]
    dispatched_at: datetime
    driver_assigned_at: Optional[datetime]
    picked_up_at: Optional[datetime]
    delivered_at: Optional[datetime]
    quoted_fee: Decimal
    actual_fee: Optional[Decimal]


class DispatchQuoteResponse(BaseModel):
    provider_id: int
    provider_name: str
    estimated_fee: Decimal
    estimated_eta_minutes: int
    availability: bool


# ============================================================================
# 9. REVIEW SENTIMENT ANALYSIS
# ============================================================================

class ReviewSentimentCreate(BaseModel):
    location_id: int
    source: str
    external_review_id: Optional[str] = None
    review_text: str
    rating: Optional[float] = None
    review_date: date
    reviewer_name: Optional[str] = None


class ReviewSentimentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    location_id: int
    source: str
    external_review_id: Optional[str]
    review_text: str
    rating: Optional[float]
    review_date: date
    reviewer_name: Optional[str]
    overall_sentiment: str
    sentiment_score: float
    topics: Optional[List[Dict[str, Any]]]
    positive_phrases: Optional[List[str]]
    negative_phrases: Optional[List[str]]
    needs_response: bool
    response_sent: bool
    response_text: Optional[str]
    responded_at: Optional[datetime]


class SentimentSummaryResponse(BaseModel):
    total_reviews: int
    avg_sentiment_score: float
    positive_count: int
    negative_count: int
    neutral_count: int
    mixed_count: int
    top_positive_topics: List[Dict[str, Any]]
    top_negative_topics: List[Dict[str, Any]]
    pending_responses: int


class AIResponseSuggestion(BaseModel):
    review_id: int
    suggested_response: str
    tone: str
    key_points_addressed: List[str]


# ============================================================================
# 10. ADVANCED GIFT CARD PLATFORM
# ============================================================================

class GiftCardProgramCreate(BaseModel):
    name: str
    denominations: List[Decimal]
    custom_amount_allowed: bool = True
    min_amount: Decimal = Decimal("5")
    max_amount: Decimal = Decimal("500")
    bonus_enabled: bool = False
    bonus_rules: Optional[Dict[str, Any]] = None
    expiration_months: Optional[int] = None
    dormancy_fee_enabled: bool = False
    is_active: bool = True


class GiftCardProgramResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    denominations: List[Decimal]
    custom_amount_allowed: bool
    min_amount: Decimal
    max_amount: Decimal
    bonus_enabled: bool
    bonus_rules: Optional[Dict[str, Any]]
    expiration_months: Optional[int]
    dormancy_fee_enabled: bool
    is_active: bool


class GiftCardCreate(BaseModel):
    program_id: int
    initial_balance: Decimal
    purchaser_email: Optional[str] = None
    purchaser_name: Optional[str] = None
    recipient_email: Optional[str] = None
    recipient_name: Optional[str] = None
    recipient_message: Optional[str] = None
    delivery_method: str = "email"


class GiftCardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    program_id: int
    card_number: str
    initial_balance: Decimal
    current_balance: Decimal
    bonus_balance: Decimal
    purchaser_email: Optional[str]
    purchaser_name: Optional[str]
    recipient_email: Optional[str]
    recipient_name: Optional[str]
    recipient_message: Optional[str]
    delivery_method: str
    delivered_at: Optional[datetime]
    is_active: bool
    expires_at: Optional[datetime]


class GiftCardTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    gift_card_id: int
    transaction_type: str
    amount: Decimal
    balance_after: Decimal
    order_id: Optional[int]
    location_id: Optional[int]
    performed_by_id: Optional[int]
    notes: Optional[str]
    created_at: datetime


class GiftCardRedemptionRequest(BaseModel):
    card_number: str
    pin: Optional[str] = None
    amount: Decimal
    order_id: Optional[int] = None


class GiftCardBalanceResponse(BaseModel):
    card_number: str
    current_balance: Decimal
    bonus_balance: Decimal
    total_available: Decimal
    expires_at: Optional[datetime]
    is_active: bool


# ============================================================================
# 11. TIPS POOLING & DISTRIBUTION
# ============================================================================

class TipPoolConfigurationCreate(BaseModel):
    location_id: int
    name: str
    pool_type: str
    distribution_rules: Dict[str, Any]
    exclude_management: bool = True
    minimum_hours_to_participate: Optional[float] = None
    is_active: bool = True


class TipPoolConfigurationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    location_id: int
    name: str
    pool_type: str
    distribution_rules: Dict[str, Any]
    exclude_management: bool
    minimum_hours_to_participate: Optional[float]
    is_active: bool


class TipPoolDistributionCreate(BaseModel):
    configuration_id: int
    location_id: int
    distribution_date: date
    pay_period_start: date
    pay_period_end: date
    total_tips_collected: Decimal
    employee_distributions: List[Dict[str, Any]]


class TipPoolDistributionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    configuration_id: int
    location_id: int
    distribution_date: date
    pay_period_start: date
    pay_period_end: date
    total_tips_collected: Decimal
    total_tips_distributed: Decimal
    employee_distributions: List[Dict[str, Any]]
    approved_by_id: Optional[int]
    approved_at: Optional[datetime]


class TipCalculationRequest(BaseModel):
    configuration_id: int
    pay_period_start: date
    pay_period_end: date
    employee_hours: Dict[int, float]
    total_tips: Decimal


class TipCalculationResponse(BaseModel):
    configuration_id: int
    total_tips: Decimal
    distributions: List[Dict[str, Any]]
    validation_warnings: List[str]


# ============================================================================
# 12. AI CROSS-SELL ENGINE
# ============================================================================

class CrossSellRuleCreate(BaseModel):
    location_id: Optional[int] = None
    name: str
    rule_type: str
    trigger_product_ids: Optional[List[int]] = None
    trigger_category_ids: Optional[List[int]] = None
    trigger_cart_minimum: Optional[Decimal] = None
    recommend_product_ids: List[int]
    recommendation_message: Optional[str] = None
    display_position: str
    priority: int = 1
    is_active: bool = True


class CrossSellRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    location_id: Optional[int]
    name: str
    rule_type: str
    trigger_product_ids: Optional[List[int]]
    trigger_category_ids: Optional[List[int]]
    trigger_cart_minimum: Optional[Decimal]
    recommend_product_ids: List[int]
    recommendation_message: Optional[str]
    display_position: str
    priority: int
    impressions: int
    conversions: int
    revenue_generated: Decimal
    is_active: bool


class CrossSellRecommendationRequest(BaseModel):
    cart_items: List[int]
    cart_total: Decimal
    customer_id: Optional[int] = None
    location_id: Optional[int] = None


class CrossSellRecommendationResponse(BaseModel):
    recommendations: List[Dict[str, Any]]
    rule_ids_triggered: List[int]


class CrossSellPerformanceResponse(BaseModel):
    total_impressions: int
    total_conversions: int
    conversion_rate: float
    total_revenue: Decimal
    avg_revenue_per_conversion: Decimal
    top_performing_rules: List[Dict[str, Any]]


# ============================================================================
# 13. CUSTOMER JOURNEY ANALYTICS
# ============================================================================

class CustomerJourneyEventCreate(BaseModel):
    customer_id: Optional[int] = None
    session_id: str
    location_id: Optional[int] = None
    event_type: str
    event_data: Optional[Dict[str, Any]] = None
    channel: str
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    device_type: Optional[str] = None
    browser: Optional[str] = None


class CustomerJourneyEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: Optional[int]
    session_id: str
    location_id: Optional[int]
    event_type: str
    event_data: Optional[Dict[str, Any]]
    channel: str
    utm_source: Optional[str]
    utm_medium: Optional[str]
    utm_campaign: Optional[str]
    device_type: Optional[str]
    browser: Optional[str]
    timestamp: datetime


class CustomerJourneyFunnelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    location_id: Optional[int]
    date: date
    channel: str
    sessions: int
    menu_views: int
    item_views: int
    add_to_carts: int
    checkout_starts: int
    orders_placed: int
    menu_to_item_rate: Optional[float]
    cart_rate: Optional[float]
    checkout_rate: Optional[float]
    conversion_rate: Optional[float]
    total_revenue: Decimal
    avg_order_value: Optional[Decimal]


class FunnelAnalysisResponse(BaseModel):
    date_range: Dict[str, date]
    total_sessions: int
    total_conversions: int
    overall_conversion_rate: float
    by_channel: Dict[str, Dict[str, Any]]
    drop_off_points: List[Dict[str, Any]]
    recommendations: List[str]


# ============================================================================
# 14. SHELF LIFE & EXPIRATION TRACKING
# ============================================================================

class ProductShelfLifeCreate(BaseModel):
    product_id: int
    shelf_life_days: int
    use_by_type: str
    storage_temp_min: Optional[float] = None
    storage_temp_max: Optional[float] = None
    requires_refrigeration: bool = False
    alert_days_before: int = 3
    markdown_days_before: Optional[int] = None
    markdown_percent: Optional[float] = None


class ProductShelfLifeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    shelf_life_days: int
    use_by_type: str
    storage_temp_min: Optional[float]
    storage_temp_max: Optional[float]
    requires_refrigeration: bool
    alert_days_before: int
    markdown_days_before: Optional[int]
    markdown_percent: Optional[float]


class InventoryBatchCreate(BaseModel):
    product_id: int
    location_id: int
    batch_number: str
    lot_number: Optional[str] = None
    received_quantity: Decimal
    current_quantity: Decimal
    received_date: date
    production_date: Optional[date] = None
    expiration_date: date
    unit_cost: Decimal


class InventoryBatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    location_id: int
    batch_number: str
    lot_number: Optional[str]
    received_quantity: Decimal
    current_quantity: Decimal
    received_date: date
    production_date: Optional[date]
    expiration_date: date
    unit_cost: Decimal
    is_expired: bool
    is_quarantined: bool
    quarantine_reason: Optional[str]


class ExpirationAlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    batch_id: int
    location_id: int
    alert_type: str
    days_until_expiry: int
    quantity_affected: Decimal
    value_at_risk: Decimal
    action_taken: Optional[str]
    action_date: Optional[datetime]
    action_by_id: Optional[int]
    acknowledged: bool


class ExpirationSummaryResponse(BaseModel):
    expiring_today: int
    expiring_3_days: int
    expiring_7_days: int
    total_value_at_risk: Decimal
    batches_requiring_action: List[InventoryBatchResponse]


# ============================================================================
# 15. AUTO PREP LIST GENERATION
# ============================================================================

class PrepListCreate(BaseModel):
    location_id: int
    prep_date: date
    station: Optional[str] = None
    generated_from: str
    forecast_covers: Optional[int] = None
    assigned_to_id: Optional[int] = None


class PrepListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    location_id: int
    prep_date: date
    station: Optional[str]
    generated_from: str
    forecast_covers: Optional[int]
    status: str
    assigned_to_id: Optional[int]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


class PrepListItemCreate(BaseModel):
    prep_list_id: int
    product_id: int
    required_quantity: Decimal
    unit: str
    current_stock: Decimal
    to_prep_quantity: Decimal
    notes: Optional[str] = None
    priority: int = 1


class PrepListItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    prep_list_id: int
    product_id: int
    required_quantity: Decimal
    unit: str
    current_stock: Decimal
    to_prep_quantity: Decimal
    actual_prepped: Optional[Decimal]
    completed: bool
    completed_at: Optional[datetime]
    notes: Optional[str]
    priority: int


class PrepListGenerationRequest(BaseModel):
    location_id: int
    prep_date: date
    forecast_method: str = "forecast"
    station: Optional[str] = None


class PrepListGenerationResponse(BaseModel):
    prep_list: PrepListResponse
    items: List[PrepListItemResponse]
    warnings: List[str]


# ============================================================================
# 16. KITCHEN LOAD BALANCING
# ============================================================================

class KitchenStationCreate(BaseModel):
    location_id: int
    name: str
    station_type: str
    max_concurrent_items: int = 10
    avg_item_time_seconds: int = 300
    equipment_ids: Optional[List[int]] = None
    min_staff: int = 1
    max_staff: int = 3
    is_active: bool = True


class KitchenStationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    location_id: int
    name: str
    station_type: str
    max_concurrent_items: int
    avg_item_time_seconds: int
    equipment_ids: Optional[List[int]]
    min_staff: int
    max_staff: int
    is_active: bool


class StationLoadMetricResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    station_id: int
    timestamp: datetime
    items_in_queue: int
    items_in_progress: int
    avg_wait_time_seconds: Optional[int]
    avg_cook_time_seconds: Optional[int]
    load_percent: float
    is_overloaded: bool


class KitchenLoadSummaryResponse(BaseModel):
    total_stations: int
    overloaded_stations: int
    total_items_in_queue: int
    total_items_in_progress: int
    avg_load_percent: float
    station_loads: List[Dict[str, Any]]
    bottleneck_station: Optional[str]


# ============================================================================
# 17. ML WAIT TIME PREDICTION
# ============================================================================

class WaitTimePredictionRequest(BaseModel):
    location_id: int
    order_id: int
    order_items: List[Dict[str, Any]]


class WaitTimePredictionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    location_id: int
    order_id: int
    predicted_wait_minutes: int
    confidence: float
    factors: Optional[Dict[str, Any]]
    actual_wait_minutes: Optional[int]
    prediction_error: Optional[int]
    predicted_at: datetime
    order_completed_at: Optional[datetime]


class WaitTimePredictionAccuracyResponse(BaseModel):
    total_predictions: int
    completed_orders: int
    avg_prediction_error_minutes: float
    within_2_minutes: float
    within_5_minutes: float
    accuracy_by_time_of_day: Dict[str, float]


# ============================================================================
# 18. ALLERGEN CROSS-CONTACT ALERTS
# ============================================================================

class AllergenProfileCreate(BaseModel):
    product_id: int
    contains_gluten: bool = False
    contains_dairy: bool = False
    contains_eggs: bool = False
    contains_peanuts: bool = False
    contains_tree_nuts: bool = False
    contains_soy: bool = False
    contains_fish: bool = False
    contains_shellfish: bool = False
    contains_sesame: bool = False
    may_contain: Optional[List[str]] = None
    prepared_on_shared_equipment: bool = False
    other_allergens: Optional[List[str]] = None
    dietary_flags: Optional[List[str]] = None


class AllergenProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    contains_gluten: bool
    contains_dairy: bool
    contains_eggs: bool
    contains_peanuts: bool
    contains_tree_nuts: bool
    contains_soy: bool
    contains_fish: bool
    contains_shellfish: bool
    contains_sesame: bool
    may_contain: Optional[List[str]]
    prepared_on_shared_equipment: bool
    other_allergens: Optional[List[str]]
    dietary_flags: Optional[List[str]]


class AllergenAlertCreate(BaseModel):
    order_id: int
    location_id: int
    allergens_flagged: List[str]
    alert_message: str
    severity: AlertSeverityEnum
    special_prep_required: bool = False
    prep_instructions: Optional[str] = None


class AllergenAlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    location_id: int
    allergens_flagged: List[str]
    alert_message: str
    severity: str
    acknowledged: bool
    acknowledged_by_id: Optional[int]
    acknowledged_at: Optional[datetime]
    special_prep_required: bool
    prep_instructions: Optional[str]


class AllergenCheckRequest(BaseModel):
    order_items: List[int]
    customer_allergens: List[str]


class AllergenCheckResponse(BaseModel):
    is_safe: bool
    conflicts: List[Dict[str, Any]]
    warnings: List[Dict[str, Any]]
    recommendations: List[str]


# ============================================================================
# 19. ESG & SUSTAINABILITY REPORTING
# ============================================================================

class SustainabilityMetricCreate(BaseModel):
    location_id: int
    date: date
    carbon_kg: Decimal = Decimal("0")
    food_waste_kg: Decimal = Decimal("0")
    food_donated_kg: Decimal = Decimal("0")
    food_composted_kg: Decimal = Decimal("0")
    landfill_kg: Decimal = Decimal("0")
    energy_kwh: Optional[Decimal] = None
    water_liters: Optional[Decimal] = None
    single_use_plastic_items: int = 0
    recyclable_packaging_percent: Optional[float] = None
    local_sourcing_percent: Optional[float] = None
    organic_percent: Optional[float] = None


class SustainabilityMetricResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    location_id: int
    date: date
    carbon_kg: Decimal
    carbon_per_cover: Optional[Decimal]
    food_waste_kg: Decimal
    food_donated_kg: Decimal
    food_composted_kg: Decimal
    landfill_kg: Decimal
    energy_kwh: Optional[Decimal]
    water_liters: Optional[Decimal]
    single_use_plastic_items: int
    recyclable_packaging_percent: Optional[float]
    local_sourcing_percent: Optional[float]
    organic_percent: Optional[float]


class ESGReportCreate(BaseModel):
    location_id: Optional[int] = None
    report_period: str
    period_start: date
    period_end: date


class ESGReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    location_id: Optional[int]
    report_period: str
    period_start: date
    period_end: date
    total_carbon_kg: Decimal
    total_waste_kg: Decimal
    waste_diversion_rate: float
    carbon_target_kg: Optional[Decimal]
    waste_target_kg: Optional[Decimal]
    carbon_vs_target_percent: Optional[float]
    waste_vs_target_percent: Optional[float]
    status: str
    published_at: Optional[datetime]


class ESGDashboardResponse(BaseModel):
    carbon_footprint: Dict[str, Any]
    waste_metrics: Dict[str, Any]
    sustainability_score: float
    vs_previous_period: Dict[str, float]
    targets: Dict[str, Any]
    recommendations: List[str]


# ============================================================================
# 20. IoT EQUIPMENT MONITORING
# ============================================================================

class EquipmentSensorCreate(BaseModel):
    location_id: int
    equipment_name: str
    equipment_type: str
    sensor_id: str
    sensor_type: str
    min_threshold: Optional[float] = None
    max_threshold: Optional[float] = None
    maintenance_interval_days: Optional[int] = None
    is_active: bool = True


class EquipmentSensorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    location_id: int
    equipment_name: str
    equipment_type: str
    sensor_id: str
    sensor_type: str
    min_threshold: Optional[float]
    max_threshold: Optional[float]
    last_maintenance: Optional[date]
    maintenance_interval_days: Optional[int]
    is_active: bool


class SensorReadingCreate(BaseModel):
    sensor_id: int
    value: float
    unit: str


class SensorReadingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sensor_id: int
    timestamp: datetime
    value: float
    unit: str
    is_alert: bool
    alert_type: Optional[str]


class PredictiveMaintenanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sensor_id: int
    prediction_type: str
    confidence: float
    predicted_failure_date: Optional[date]
    indicators: Optional[Dict[str, Any]]
    recommended_action: str
    acknowledged: bool
    action_taken: Optional[str]
    resolved_at: Optional[datetime]


class EquipmentDashboardResponse(BaseModel):
    total_sensors: int
    sensors_in_alert: int
    pending_maintenance: int
    temperature_readings: List[Dict[str, Any]]
    alerts: List[SensorReadingResponse]
    maintenance_predictions: List[PredictiveMaintenanceResponse]


# ============================================================================
# 21. VENDOR SCORECARD SYSTEM
# ============================================================================

class VendorScorecardCreate(BaseModel):
    supplier_id: int
    period_start: date
    period_end: date
    quality_score: float
    defect_rate: float
    on_time_delivery_rate: float
    fill_rate: float
    avg_lead_time_days: float
    price_competitiveness: float
    price_stability: float
    responsiveness_score: float
    issue_resolution_time_hours: Optional[float] = None
    food_safety_score: Optional[float] = None
    certifications_valid: bool = True


class VendorScorecardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    supplier_id: int
    period_start: date
    period_end: date
    quality_score: float
    defect_rate: float
    on_time_delivery_rate: float
    fill_rate: float
    avg_lead_time_days: float
    price_competitiveness: float
    price_stability: float
    responsiveness_score: float
    issue_resolution_time_hours: Optional[float]
    food_safety_score: Optional[float]
    certifications_valid: bool
    overall_score: float
    tier: str


class VendorComparisonResponse(BaseModel):
    vendors: List[VendorScorecardResponse]
    category_averages: Dict[str, float]
    top_performer: int
    at_risk_vendors: List[int]


# ============================================================================
# 22. MULTI-CONCEPT / GHOST KITCHEN
# ============================================================================

class VirtualBrandCreate(BaseModel):
    parent_location_id: int
    brand_name: str
    brand_slug: str
    logo_url: Optional[str] = None
    description: Optional[str] = None
    cuisine_type: Optional[str] = None
    menu_ids: Optional[List[int]] = None
    delivery_platforms: List[str]
    operating_hours: Optional[Dict[str, Any]] = None
    is_active: bool = True


class VirtualBrandResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    parent_location_id: int
    brand_name: str
    brand_slug: str
    logo_url: Optional[str]
    description: Optional[str]
    cuisine_type: Optional[str]
    menu_ids: Optional[List[int]]
    delivery_platforms: List[str]
    operating_hours: Optional[Dict[str, Any]]
    total_orders: int
    total_revenue: Decimal
    avg_rating: Optional[float]
    is_active: bool


class VirtualBrandPerformanceResponse(BaseModel):
    brand_id: int
    orders_today: int
    revenue_today: Decimal
    orders_this_week: int
    revenue_this_week: Decimal
    avg_order_value: Decimal
    top_items: List[Dict[str, Any]]
    platform_breakdown: Dict[str, Dict[str, Any]]


# ============================================================================
# 23. TABLE TURN OPTIMIZATION
# ============================================================================

class TableTurnMetricCreate(BaseModel):
    location_id: int
    table_id: int
    seated_at: datetime
    party_size: int


class TableTurnMetricResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    location_id: int
    table_id: int
    seated_at: datetime
    party_size: int
    order_placed_at: Optional[datetime]
    food_delivered_at: Optional[datetime]
    check_requested_at: Optional[datetime]
    check_paid_at: Optional[datetime]
    table_cleared_at: Optional[datetime]
    time_to_order: Optional[int]
    time_to_food: Optional[int]
    dining_time: Optional[int]
    total_turn_time: Optional[int]
    check_total: Optional[Decimal]
    revenue_per_minute: Optional[Decimal]


class TableTurnForecastResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    location_id: int
    table_id: int
    current_party_seated_at: datetime
    predicted_available_at: datetime
    confidence: float
    actual_available_at: Optional[datetime]
    prediction_error_minutes: Optional[int]


class TableTurnSummaryResponse(BaseModel):
    avg_turn_time_minutes: float
    avg_time_to_order: float
    avg_time_to_food: float
    avg_dining_time: float
    avg_revenue_per_turn: Decimal
    avg_revenue_per_minute: Decimal
    turns_today: int
    tables_available: int
    predicted_next_availability: List[TableTurnForecastResponse]


class TableMilestoneUpdate(BaseModel):
    milestone: str
    timestamp: Optional[datetime] = None


# ============================================================================
# 24. REAL-TIME SMS ORDER UPDATES
# ============================================================================

class OrderStatusNotificationCreate(BaseModel):
    order_id: int
    notification_type: NotificationTypeEnum
    channel: ChannelEnum
    recipient: str
    message: str
    tracking_url: Optional[str] = None


class OrderStatusNotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    notification_type: str
    channel: str
    recipient: str
    message: str
    sent_at: Optional[datetime]
    delivered_at: Optional[datetime]
    failed: bool
    failure_reason: Optional[str]
    tracking_url: Optional[str]


class NotificationTemplateCreate(BaseModel):
    notification_type: NotificationTypeEnum
    channel: ChannelEnum
    template: str
    variables: List[str]


class NotificationStatsResponse(BaseModel):
    total_sent: int
    total_delivered: int
    total_failed: int
    delivery_rate: float
    by_type: Dict[str, int]
    by_channel: Dict[str, int]


# ============================================================================
# 25. BLOCKCHAIN TRACEABILITY
# ============================================================================

class SupplyChainTraceCreate(BaseModel):
    product_id: int
    batch_id: Optional[int] = None
    trace_id: str
    farm_name: Optional[str] = None
    farm_location: Optional[str] = None
    harvest_date: Optional[date] = None
    processor_name: Optional[str] = None
    processing_date: Optional[date] = None
    distributor_name: Optional[str] = None
    ship_date: Optional[date] = None
    received_date: Optional[date] = None
    certifications: Optional[List[str]] = None


class SupplyChainTraceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    batch_id: Optional[int]
    trace_id: str
    farm_name: Optional[str]
    farm_location: Optional[str]
    harvest_date: Optional[date]
    processor_name: Optional[str]
    processing_date: Optional[date]
    distributor_name: Optional[str]
    ship_date: Optional[date]
    received_date: Optional[date]
    certifications: Optional[List[str]]
    blockchain_hash: Optional[str]
    blockchain_verified: bool
    qr_code_url: Optional[str]


class TraceabilityQueryResponse(BaseModel):
    product_name: str
    trace: SupplyChainTraceResponse
    chain_of_custody: List[Dict[str, Any]]
    certifications: List[str]
    days_from_farm: Optional[int]
    sustainability_score: Optional[float]


class BlockchainVerificationResponse(BaseModel):
    trace_id: str
    is_verified: bool
    blockchain_hash: str
    verification_timestamp: datetime
    chain_integrity: bool

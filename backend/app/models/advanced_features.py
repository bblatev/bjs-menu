"""Advanced competitor features - Models for gap closure."""

from __future__ import annotations

from decimal import Decimal
from datetime import datetime, date, time, timezone
from typing import Optional, List, Dict, Any
from enum import Enum

from sqlalchemy import (
    Boolean, ForeignKey, Integer, Numeric, String, Text, DateTime, Date, Time,
    JSON, Float, Enum as SQLEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.db.base import Base, TimestampMixin, VersionMixin
from app.models.validators import validate_list


# ============================================================================
# 1. AI FOOD WASTE TRACKING (Leanpath/Winnow style)
# ============================================================================

class WasteCategory(str, Enum):
    OVERPRODUCTION = "overproduction"
    SPOILAGE = "spoilage"
    PLATE_WASTE = "plate_waste"
    PREP_WASTE = "prep_waste"
    EXPIRED = "expired"
    DAMAGED = "damaged"
    TRIM_WASTE = "trim_waste"
    OTHER = "other"


class WasteTrackingEntry(Base, TimestampMixin):
    """AI-powered food waste tracking with image recognition."""

    __tablename__ = "waste_tracking_entries"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    product_id: Mapped[Optional[int]] = mapped_column(ForeignKey("products.id"), nullable=True)

    # Waste details
    category: Mapped[WasteCategory] = mapped_column(
        SQLEnum(WasteCategory, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    cost_value: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    carbon_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 3), nullable=True)

    # AI recognition
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    ai_detected_item: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ai_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ai_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Context
    station: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    shift: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recorded_by_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class WasteForecast(Base, TimestampMixin):
    """Predicted waste based on historical patterns."""

    __tablename__ = "waste_forecasts"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    forecast_date: Mapped[date] = mapped_column(Date, nullable=False)

    predicted_waste_kg: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    predicted_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    confidence_interval: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)

    actual_waste_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 3), nullable=True)
    actual_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)


# ============================================================================
# 2. ADVANCED LABOR FORECASTING (7shifts/HotSchedules style)
# ============================================================================

class LaborForecast(Base, TimestampMixin):
    """ML-based labor demand forecasting."""

    __tablename__ = "labor_forecasts"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    forecast_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Forecasts by hour
    hourly_forecasts: Mapped[Dict] = mapped_column(JSON, nullable=False)  # {hour: {covers, revenue, staff_needed}}

    # Factors considered
    weather_factor: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    event_factor: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    historical_factor: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Recommended staffing
    recommended_staff: Mapped[Dict] = mapped_column(JSON, nullable=False)  # {role: count}
    estimated_labor_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Actuals for comparison
    actual_covers: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    actual_revenue: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    actual_labor_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)


class LaborComplianceRule(Base, TimestampMixin):
    """Labor law compliance rules (Fair Workweek, breaks, overtime)."""

    __tablename__ = "labor_compliance_rules"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    jurisdiction: Mapped[str] = mapped_column(String(100), nullable=False)

    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)  # break, overtime, predictive_scheduling
    rule_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Rule parameters
    parameters: Mapped[Dict] = mapped_column(JSON, nullable=False)
    # e.g., {"hours_before_break": 5, "break_duration_minutes": 30}

    penalty_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class LaborComplianceViolation(Base, TimestampMixin):
    """Tracked labor compliance violations."""

    __tablename__ = "labor_compliance_violations"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("labor_compliance_rules.id"), nullable=False)
    employee_id: Mapped[int] = mapped_column(Integer, nullable=False)
    location_id: Mapped[int] = mapped_column(Integer, nullable=False)

    violation_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    penalty_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


# ============================================================================
# 3. ORDER THROTTLING SYSTEM (Olo style)
# ============================================================================

class KitchenCapacity(Base, TimestampMixin):
    """Kitchen capacity configuration for order throttling."""

    __tablename__ = "kitchen_capacities"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Capacity settings
    max_orders_per_15min: Mapped[int] = mapped_column(Integer, default=20)
    max_items_per_15min: Mapped[int] = mapped_column(Integer, default=100)

    # Station-specific capacities
    station_capacities: Mapped[Dict] = mapped_column(JSON, nullable=True)
    # {"grill": 30, "fryer": 25, "expo": 50}

    # Time-based adjustments
    peak_hour_multiplier: Mapped[float] = mapped_column(Float, default=1.0)
    off_peak_multiplier: Mapped[float] = mapped_column(Float, default=1.5)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class OrderThrottleEvent(Base, TimestampMixin):
    """Logged throttling events."""

    __tablename__ = "order_throttle_events"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    event_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    throttle_type: Mapped[str] = mapped_column(String(50), nullable=False)  # delay, reject, queue

    current_load: Mapped[int] = mapped_column(Integer, nullable=False)
    max_capacity: Mapped[int] = mapped_column(Integer, nullable=False)

    orders_affected: Mapped[int] = mapped_column(Integer, default=0)
    avg_delay_minutes: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    auto_recovered: Mapped[bool] = mapped_column(Boolean, default=False)
    recovered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


# ============================================================================
# 4. GUEST WIFI MARKETING (WiFi data capture)
# ============================================================================

class GuestWifiSession(Base, TimestampMixin):
    """Guest WiFi login sessions for marketing."""

    __tablename__ = "guest_wifi_sessions"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Device info
    mac_address: Mapped[str] = mapped_column(String(17), nullable=False, index=True)
    device_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Guest info captured
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Marketing consent
    marketing_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Session tracking
    connected_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    disconnected_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    session_duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Visit tracking
    visit_count: Mapped[int] = mapped_column(Integer, default=1)
    last_visit: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


# ============================================================================
# 5. A/B MENU TESTING
# ============================================================================

class MenuExperiment(Base, TimestampMixin):
    """A/B testing for menu items, prices, and layouts."""

    __tablename__ = "menu_experiments"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # null = all locations

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    experiment_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # price, description, image, position, combo

    # Variants
    control_variant: Mapped[Dict] = mapped_column(JSON, nullable=False)
    test_variants: Mapped[List[Dict]] = mapped_column(JSON, nullable=False)

    # Traffic allocation
    traffic_split: Mapped[Dict] = mapped_column(JSON, nullable=False)
    # {"control": 50, "variant_a": 25, "variant_b": 25}

    # Timeline
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Results
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    winner_variant: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    statistical_significance: Mapped[Optional[float]] = mapped_column(Float, nullable=True)


class MenuExperimentResult(Base, TimestampMixin):
    """Results tracking for menu experiments."""

    __tablename__ = "menu_experiment_results"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("menu_experiments.id"), nullable=False)
    variant_name: Mapped[str] = mapped_column(String(50), nullable=False)

    # Metrics
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    orders: Mapped[int] = mapped_column(Integer, default=0)
    revenue: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)

    # Calculated
    conversion_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_order_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)

    date: Mapped[date] = mapped_column(Date, nullable=False)


# ============================================================================
# 6. DYNAMIC SURGE PRICING
# ============================================================================

class DynamicPricingRule(Base, TimestampMixin):
    """Demand-based dynamic pricing rules."""

    __tablename__ = "dynamic_pricing_rules"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Trigger conditions
    trigger_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # demand, time, weather, event, inventory

    trigger_conditions: Mapped[Dict] = mapped_column(JSON, nullable=False)
    # {"demand_percentile": 90, "min_wait_time_minutes": 30}

    # Price adjustment
    adjustment_type: Mapped[str] = mapped_column(String(20), nullable=False)  # percentage, fixed
    adjustment_value: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    max_adjustment_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Scope
    applies_to: Mapped[str] = mapped_column(String(50), nullable=False)  # all, category, item
    item_ids: Mapped[Optional[List[int]]] = mapped_column(JSON, nullable=True)
    category_ids: Mapped[Optional[List[int]]] = mapped_column(JSON, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class DynamicPriceAdjustment(Base, TimestampMixin):
    """Log of dynamic price adjustments."""

    __tablename__ = "dynamic_price_adjustments"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("dynamic_pricing_rules.id"), nullable=False)
    location_id: Mapped[int] = mapped_column(Integer, nullable=False)

    activated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    deactivated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    original_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    adjusted_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    trigger_value: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    orders_during_surge: Mapped[int] = mapped_column(Integer, default=0)
    additional_revenue: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)


# ============================================================================
# 7. CURBSIDE "I'M HERE" NOTIFICATIONS
# ============================================================================

class CurbsideOrder(Base, TimestampMixin):
    """Curbside pickup order tracking."""

    __tablename__ = "curbside_orders"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    location_id: Mapped[int] = mapped_column(Integer, nullable=False)

    # Customer info
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(20), nullable=False)

    # Vehicle info
    vehicle_description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    vehicle_color: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    vehicle_make: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    parking_spot: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Status tracking
    estimated_ready_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    customer_arrived_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    order_delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Notifications
    arrival_notification_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    ready_notification_sent: Mapped[bool] = mapped_column(Boolean, default=False)


# ============================================================================
# 8. MULTI-PROVIDER DELIVERY DISPATCH (Smart routing)
# ============================================================================

class DeliveryProvider(Base, TimestampMixin):
    """Delivery provider configuration."""

    __tablename__ = "delivery_providers"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    provider_name: Mapped[str] = mapped_column(String(50), nullable=False)
    # doordash_drive, uber_direct, in_house, postmates, relay

    api_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    api_secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    merchant_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Pricing
    base_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    per_mile_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    commission_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Performance metrics
    avg_delivery_time_minutes: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    reliability_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Priority
    priority_rank: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class DeliveryDispatch(Base, TimestampMixin):
    """Smart delivery dispatch decisions."""

    __tablename__ = "delivery_dispatches"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    location_id: Mapped[int] = mapped_column(Integer, nullable=False)

    # Dispatch decision
    selected_provider_id: Mapped[int] = mapped_column(ForeignKey("delivery_providers.id"), nullable=False)
    dispatch_reason: Mapped[str] = mapped_column(String(100), nullable=False)
    # cost_optimal, fastest, reliability, load_balancing

    # Provider quotes
    provider_quotes: Mapped[Dict] = mapped_column(JSON, nullable=True)
    # {"doordash": {"fee": 5.99, "eta": 25}, "uber": {"fee": 6.49, "eta": 20}}

    # Tracking
    dispatched_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    driver_assigned_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    picked_up_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Costs
    quoted_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    actual_fee: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)


# ============================================================================
# 9. REVIEW SENTIMENT ANALYSIS
# ============================================================================

class ReviewSentiment(Base, TimestampMixin):
    """AI-analyzed customer review sentiment."""

    __tablename__ = "review_sentiments"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Source
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    # google, yelp, tripadvisor, facebook, internal
    external_review_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Review content
    review_text: Mapped[str] = mapped_column(Text, nullable=False)
    rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    review_date: Mapped[date] = mapped_column(Date, nullable=False)
    reviewer_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # AI Analysis
    overall_sentiment: Mapped[str] = mapped_column(String(20), nullable=False)
    # positive, negative, neutral, mixed
    sentiment_score: Mapped[float] = mapped_column(Float, nullable=False)  # -1 to 1

    # Topic extraction
    topics: Mapped[List[Dict]] = mapped_column(JSON, nullable=True)
    # [{"topic": "food_quality", "sentiment": 0.8}, {"topic": "service", "sentiment": -0.3}]

    # Key phrases
    positive_phrases: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    negative_phrases: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)

    # Response
    needs_response: Mapped[bool] = mapped_column(Boolean, default=False)
    response_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    response_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    responded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


# ============================================================================
# 10. ADVANCED GIFT CARD PLATFORM
# ============================================================================

class GiftCardProgram(Base, TimestampMixin):
    """Gift card program configuration."""

    __tablename__ = "gift_card_programs"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Card options
    denominations: Mapped[List[Decimal]] = mapped_column(JSON, nullable=False)
    custom_amount_allowed: Mapped[bool] = mapped_column(Boolean, default=True)
    min_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=5)
    max_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=500)

    # Bonus promotions
    bonus_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    bonus_rules: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    # {"buy_amount": 50, "bonus_amount": 10}

    # Expiration
    expiration_months: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    dormancy_fee_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class GiftCard(Base, TimestampMixin, VersionMixin):
    """Individual gift card."""

    __tablename__ = "gift_cards"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("gift_card_programs.id"), nullable=False)

    card_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    pin: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Balances
    initial_balance: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    current_balance: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    bonus_balance: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)

    # Purchaser
    purchaser_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    purchaser_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Recipient
    recipient_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    recipient_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    recipient_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Delivery
    delivery_method: Mapped[str] = mapped_column(String(20), nullable=False)  # email, sms, physical
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Purchase info
    purchase_order_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    purchase_location_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    transactions = relationship("GiftCardTransaction", back_populates="gift_card", cascade="all, delete-orphan")


class GiftCardTransaction(Base, TimestampMixin):
    """Gift card transaction history."""

    __tablename__ = "gift_card_transactions"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    gift_card_id: Mapped[int] = mapped_column(ForeignKey("gift_cards.id"), nullable=False)

    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # activation, redemption, reload, void, adjustment

    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    order_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    location_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    performed_by_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    gift_card = relationship("GiftCard", back_populates="transactions")


# ============================================================================
# 11. TIPS POOLING & DISTRIBUTION
# ============================================================================

class TipPoolConfiguration(Base, TimestampMixin):
    """Tip pooling configuration."""

    __tablename__ = "tip_pool_configurations"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Pool type
    pool_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # percentage, points, hours_worked, hybrid

    # Distribution rules
    distribution_rules: Mapped[Dict] = mapped_column(JSON, nullable=False)
    # {"server": 70, "busser": 15, "bartender": 10, "host": 5}
    # or {"server": {"base": 50, "per_hour": 10}, ...}

    # Exclusions
    exclude_management: Mapped[bool] = mapped_column(Boolean, default=True)
    minimum_hours_to_participate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class TipPoolDistribution(Base, TimestampMixin):
    """Tip pool distribution record."""

    __tablename__ = "tip_pool_distributions"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    configuration_id: Mapped[int] = mapped_column(ForeignKey("tip_pool_configurations.id"), nullable=False)
    location_id: Mapped[int] = mapped_column(Integer, nullable=False)

    distribution_date: Mapped[date] = mapped_column(Date, nullable=False)
    pay_period_start: Mapped[date] = mapped_column(Date, nullable=False)
    pay_period_end: Mapped[date] = mapped_column(Date, nullable=False)

    # Pool totals
    total_tips_collected: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_tips_distributed: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Breakdown by employee
    employee_distributions: Mapped[List[Dict]] = mapped_column(JSON, nullable=False)
    # [{"employee_id": 1, "amount": 150.00, "hours": 32, "role": "server"}, ...]

    approved_by_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


# ============================================================================
# 12. AI CROSS-SELL ENGINE
# ============================================================================

class CrossSellRule(Base, TimestampMixin):
    """AI-powered cross-sell/upsell rules."""

    __tablename__ = "cross_sell_rules"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # ai_recommendation, manual, frequently_bought_together, category_upsell

    # Trigger
    trigger_product_ids: Mapped[Optional[List[int]]] = mapped_column(JSON, nullable=True)
    trigger_category_ids: Mapped[Optional[List[int]]] = mapped_column(JSON, nullable=True)
    trigger_cart_minimum: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)

    # Recommendation
    recommend_product_ids: Mapped[List[int]] = mapped_column(JSON, nullable=False)
    recommendation_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Presentation
    display_position: Mapped[str] = mapped_column(String(50), nullable=False)  # cart, checkout, kds
    priority: Mapped[int] = mapped_column(Integer, default=1)

    # Performance
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    conversions: Mapped[int] = mapped_column(Integer, default=0)
    revenue_generated: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class CrossSellImpression(Base, TimestampMixin):
    """Cross-sell impression tracking."""

    __tablename__ = "cross_sell_impressions"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("cross_sell_rules.id"), nullable=False)
    order_id: Mapped[int] = mapped_column(Integer, nullable=False)

    shown_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    converted: Mapped[bool] = mapped_column(Boolean, default=False)
    converted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    recommended_product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    added_product_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    revenue: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)


# ============================================================================
# 13. CUSTOMER JOURNEY ANALYTICS
# ============================================================================

class CustomerJourneyEvent(Base, TimestampMixin):
    """Customer journey touchpoint tracking."""

    __tablename__ = "customer_journey_events"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    session_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    location_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Event details
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # page_view, menu_view, item_view, add_to_cart, remove_from_cart, checkout_start, order_placed

    event_data: Mapped[Dict] = mapped_column(JSON, nullable=True)

    # Channel
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    # web, mobile_app, kiosk, pos, phone

    # Attribution
    utm_source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    utm_medium: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    utm_campaign: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Device
    device_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    browser: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class CustomerJourneyFunnel(Base, TimestampMixin):
    """Pre-calculated funnel analytics."""

    __tablename__ = "customer_journey_funnels"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)

    # Funnel stages
    sessions: Mapped[int] = mapped_column(Integer, default=0)
    menu_views: Mapped[int] = mapped_column(Integer, default=0)
    item_views: Mapped[int] = mapped_column(Integer, default=0)
    add_to_carts: Mapped[int] = mapped_column(Integer, default=0)
    checkout_starts: Mapped[int] = mapped_column(Integer, default=0)
    orders_placed: Mapped[int] = mapped_column(Integer, default=0)

    # Calculated rates
    menu_to_item_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cart_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    checkout_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    conversion_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Revenue
    total_revenue: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    avg_order_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)


# ============================================================================
# 14. SHELF LIFE & EXPIRATION TRACKING
# ============================================================================

class ProductShelfLife(Base, TimestampMixin):
    """Product shelf life configuration."""

    __tablename__ = "product_shelf_lives"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)

    # Shelf life
    shelf_life_days: Mapped[int] = mapped_column(Integer, nullable=False)
    use_by_type: Mapped[str] = mapped_column(String(20), nullable=False)  # use_by, best_before, sell_by

    # Storage requirements
    storage_temp_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    storage_temp_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    requires_refrigeration: Mapped[bool] = mapped_column(Boolean, default=False)

    # Alerts
    alert_days_before: Mapped[int] = mapped_column(Integer, default=3)
    markdown_days_before: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    markdown_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)


class InventoryBatch(Base, TimestampMixin):
    """Inventory batch with expiration tracking."""

    __tablename__ = "inventory_batches"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    location_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    batch_number: Mapped[str] = mapped_column(String(50), nullable=False)
    lot_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Quantities
    received_quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    current_quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Dates
    received_date: Mapped[date] = mapped_column(Date, nullable=False)
    production_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    expiration_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Cost
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Status
    is_expired: Mapped[bool] = mapped_column(Boolean, default=False)
    is_quarantined: Mapped[bool] = mapped_column(Boolean, default=False)
    quarantine_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class ExpirationAlert(Base, TimestampMixin):
    """Expiration alerts and actions."""

    __tablename__ = "expiration_alerts"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("inventory_batches.id"), nullable=False)
    location_id: Mapped[int] = mapped_column(Integer, nullable=False)

    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # approaching_expiry, expired, markdown_required

    days_until_expiry: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_affected: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    value_at_risk: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Action taken
    action_taken: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # donated, discounted, disposed, transferred
    action_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    action_by_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)


# ============================================================================
# 15. AUTO PREP LIST GENERATION
# ============================================================================

class PrepList(Base, TimestampMixin):
    """Auto-generated prep lists."""

    __tablename__ = "prep_lists"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    prep_date: Mapped[date] = mapped_column(Date, nullable=False)
    station: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Generation source
    generated_from: Mapped[str] = mapped_column(String(50), nullable=False)
    # forecast, par_level, manual, event

    forecast_covers: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    # pending, in_progress, completed

    assigned_to_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class PrepListItem(Base, TimestampMixin):
    """Individual prep list items."""

    __tablename__ = "prep_list_items"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    prep_list_id: Mapped[int] = mapped_column(ForeignKey("prep_lists.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)

    # Required quantities
    required_quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)

    # Current stock
    current_stock: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    to_prep_quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Completion
    actual_prepped: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=1)


# ============================================================================
# 16. KITCHEN LOAD BALANCING
# ============================================================================

class KitchenStation(Base, TimestampMixin):
    """Kitchen station configuration for load balancing."""

    __tablename__ = "kitchen_stations"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    station_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # grill, fryer, saute, salad, dessert, expo, bar

    # Capacity
    max_concurrent_items: Mapped[int] = mapped_column(Integer, default=10)
    avg_item_time_seconds: Mapped[int] = mapped_column(Integer, default=300)

    # Equipment
    equipment_ids: Mapped[Optional[List[int]]] = mapped_column(JSON, nullable=True)

    # Staffing
    min_staff: Mapped[int] = mapped_column(Integer, default=1)
    max_staff: Mapped[int] = mapped_column(Integer, default=3)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class StationLoadMetric(Base, TimestampMixin):
    """Real-time station load tracking."""

    __tablename__ = "station_load_metrics"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    station_id: Mapped[int] = mapped_column(ForeignKey("kitchen_stations.id"), nullable=False)

    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Current load
    items_in_queue: Mapped[int] = mapped_column(Integer, default=0)
    items_in_progress: Mapped[int] = mapped_column(Integer, default=0)

    # Performance
    avg_wait_time_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    avg_cook_time_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Load percentage
    load_percent: Mapped[float] = mapped_column(Float, default=0)
    is_overloaded: Mapped[bool] = mapped_column(Boolean, default=False)


# ============================================================================
# 17. ML WAIT TIME PREDICTION
# ============================================================================

class WaitTimePrediction(Base, TimestampMixin):
    """ML-based wait time predictions."""

    __tablename__ = "wait_time_predictions"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    order_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Prediction
    predicted_wait_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # Factors used
    factors: Mapped[Dict] = mapped_column(JSON, nullable=True)
    # {"queue_depth": 15, "staff_count": 3, "item_complexity": 2.5, "time_of_day": "lunch_rush"}

    # Actuals
    actual_wait_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    prediction_error: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    predicted_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    order_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


# ============================================================================
# 18. ALLERGEN CROSS-CONTACT ALERTS
# ============================================================================

class AllergenProfile(Base, TimestampMixin):
    """Allergen profiles for products."""

    __tablename__ = "allergen_profiles"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)

    # Common allergens
    contains_gluten: Mapped[bool] = mapped_column(Boolean, default=False)
    contains_dairy: Mapped[bool] = mapped_column(Boolean, default=False)
    contains_eggs: Mapped[bool] = mapped_column(Boolean, default=False)
    contains_peanuts: Mapped[bool] = mapped_column(Boolean, default=False)
    contains_tree_nuts: Mapped[bool] = mapped_column(Boolean, default=False)
    contains_soy: Mapped[bool] = mapped_column(Boolean, default=False)
    contains_fish: Mapped[bool] = mapped_column(Boolean, default=False)
    contains_shellfish: Mapped[bool] = mapped_column(Boolean, default=False)
    contains_sesame: Mapped[bool] = mapped_column(Boolean, default=False)

    # Cross-contact risks
    may_contain: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    prepared_on_shared_equipment: Mapped[bool] = mapped_column(Boolean, default=False)

    # Additional info
    other_allergens: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    dietary_flags: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    # ["vegan", "vegetarian", "halal", "kosher", "keto", "low_sodium"]


class AllergenAlert(Base, TimestampMixin):
    """Kitchen alerts for allergen orders."""

    __tablename__ = "allergen_alerts"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    location_id: Mapped[int] = mapped_column(Integer, nullable=False)

    allergens_flagged: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    # ["peanuts", "tree_nuts"]

    alert_message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # warning, critical

    # Acknowledgment
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    acknowledged_by_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Cross-contact prevention
    special_prep_required: Mapped[bool] = mapped_column(Boolean, default=False)
    prep_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


# ============================================================================
# 19. ESG & SUSTAINABILITY REPORTING
# ============================================================================

class SustainabilityMetric(Base, TimestampMixin):
    """Daily sustainability metrics."""

    __tablename__ = "sustainability_metrics"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)

    # Carbon footprint
    carbon_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=0)
    carbon_per_cover: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)

    # Waste metrics
    food_waste_kg: Mapped[Decimal] = mapped_column(Numeric(10, 3), default=0)
    food_donated_kg: Mapped[Decimal] = mapped_column(Numeric(10, 3), default=0)
    food_composted_kg: Mapped[Decimal] = mapped_column(Numeric(10, 3), default=0)
    landfill_kg: Mapped[Decimal] = mapped_column(Numeric(10, 3), default=0)

    # Energy & water
    energy_kwh: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    water_liters: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)

    # Packaging
    single_use_plastic_items: Mapped[int] = mapped_column(Integer, default=0)
    recyclable_packaging_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Sourcing
    local_sourcing_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    organic_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)


class ESGReport(Base, TimestampMixin):
    """ESG reporting periods."""

    __tablename__ = "esg_reports"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # null = company-wide

    report_period: Mapped[str] = mapped_column(String(20), nullable=False)  # monthly, quarterly, annual
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)

    # Aggregated metrics
    total_carbon_kg: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    total_waste_kg: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    waste_diversion_rate: Mapped[float] = mapped_column(Float, nullable=False)

    # Goals & targets
    carbon_target_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 3), nullable=True)
    waste_target_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 3), nullable=True)

    # Performance
    carbon_vs_target_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    waste_vs_target_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Report status
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    # draft, pending_review, approved, published
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


# ============================================================================
# 20. IoT EQUIPMENT MONITORING
# ============================================================================

class EquipmentSensor(Base, TimestampMixin):
    """IoT equipment sensors."""

    __tablename__ = "equipment_sensors"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    equipment_name: Mapped[str] = mapped_column(String(255), nullable=False)
    equipment_type: Mapped[str] = mapped_column(String(100), nullable=False)
    # refrigerator, freezer, oven, fryer, dishwasher, hvac

    sensor_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    sensor_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # temperature, humidity, power, door_open, vibration

    # Thresholds
    min_threshold: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_threshold: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Maintenance
    last_maintenance: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    maintenance_interval_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class SensorReading(Base):
    """IoT sensor readings."""

    __tablename__ = "sensor_readings"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    sensor_id: Mapped[int] = mapped_column(ForeignKey("equipment_sensors.id"), nullable=False, index=True)

    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)

    is_alert: Mapped[bool] = mapped_column(Boolean, default=False)
    alert_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # out_of_range, rapid_change, sensor_failure


class PredictiveMaintenance(Base, TimestampMixin):
    """Predictive maintenance alerts."""

    __tablename__ = "predictive_maintenance"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    sensor_id: Mapped[int] = mapped_column(ForeignKey("equipment_sensors.id"), nullable=False)

    prediction_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # failure_imminent, maintenance_due, anomaly_detected

    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_failure_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Analysis
    indicators: Mapped[Dict] = mapped_column(JSON, nullable=True)
    recommended_action: Mapped[str] = mapped_column(Text, nullable=False)

    # Status
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    action_taken: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


# ============================================================================
# 21. VENDOR SCORECARD SYSTEM
# ============================================================================

class VendorScorecard(Base, TimestampMixin):
    """Comprehensive vendor performance scorecard."""

    __tablename__ = "vendor_scorecards"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)

    # Quality metrics (0-100)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False)
    defect_rate: Mapped[float] = mapped_column(Float, nullable=False)

    # Delivery metrics
    on_time_delivery_rate: Mapped[float] = mapped_column(Float, nullable=False)
    fill_rate: Mapped[float] = mapped_column(Float, nullable=False)
    avg_lead_time_days: Mapped[float] = mapped_column(Float, nullable=False)

    # Pricing metrics
    price_competitiveness: Mapped[float] = mapped_column(Float, nullable=False)
    price_stability: Mapped[float] = mapped_column(Float, nullable=False)

    # Service metrics
    responsiveness_score: Mapped[float] = mapped_column(Float, nullable=False)
    issue_resolution_time_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Compliance
    food_safety_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    certifications_valid: Mapped[bool] = mapped_column(Boolean, default=True)

    # Overall
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    tier: Mapped[str] = mapped_column(String(20), nullable=False)
    # preferred, approved, probation, suspended


# ============================================================================
# 22. MULTI-CONCEPT / GHOST KITCHEN
# ============================================================================

class VirtualBrand(Base, TimestampMixin):
    """Virtual/ghost kitchen brand management."""

    __tablename__ = "virtual_brands"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_location_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    brand_name: Mapped[str] = mapped_column(String(255), nullable=False)
    brand_slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    # Branding
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cuisine_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Menu
    menu_ids: Mapped[Optional[List[int]]] = mapped_column(JSON, nullable=True)

    # Channels
    delivery_platforms: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    # ["doordash", "ubereats", "grubhub"]

    # Operating hours (may differ from parent)
    operating_hours: Mapped[Dict] = mapped_column(JSON, nullable=True)

    # Performance
    total_orders: Mapped[int] = mapped_column(Integer, default=0)
    total_revenue: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    avg_rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


# ============================================================================
# 23. TABLE TURN OPTIMIZATION
# ============================================================================

class TableTurnMetric(Base, TimestampMixin):
    """Table turn time tracking and optimization."""

    __tablename__ = "table_turn_metrics"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    table_id: Mapped[int] = mapped_column(Integer, nullable=False)

    # Seating
    seated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    party_size: Mapped[int] = mapped_column(Integer, nullable=False)

    # Service milestones
    order_placed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    food_delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    check_requested_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    check_paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    table_cleared_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Calculated times (in minutes)
    time_to_order: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    time_to_food: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    dining_time: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_turn_time: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Check
    check_total: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    revenue_per_minute: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)


class TableTurnForecast(Base, TimestampMixin):
    """Predicted table availability."""

    __tablename__ = "table_turn_forecasts"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    table_id: Mapped[int] = mapped_column(Integer, nullable=False)

    current_party_seated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    predicted_available_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    actual_available_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    prediction_error_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


# ============================================================================
# 24. REAL-TIME SMS ORDER UPDATES
# ============================================================================

class OrderStatusNotification(Base, TimestampMixin):
    """Customer order status notifications."""

    __tablename__ = "order_status_notifications"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    notification_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # order_received, preparing, ready, out_for_delivery, delivered

    channel: Mapped[str] = mapped_column(String(20), nullable=False)  # sms, email, push
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)

    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Delivery status
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    failed: Mapped[bool] = mapped_column(Boolean, default=False)
    failure_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Tracking
    tracking_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)


# ============================================================================
# 25. BLOCKCHAIN TRACEABILITY
# ============================================================================

class SupplyChainTrace(Base, TimestampMixin):
    """Supply chain traceability records."""

    __tablename__ = "supply_chain_traces"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    batch_id: Mapped[Optional[int]] = mapped_column(ForeignKey("inventory_batches.id"), nullable=True)

    # Chain of custody
    trace_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    # Origin
    farm_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    farm_location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    harvest_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Processing
    processor_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    processing_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Distribution
    distributor_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ship_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    received_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Certifications
    certifications: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    # ["organic", "fair_trade", "non_gmo", "sustainable"]

    # Blockchain reference
    blockchain_hash: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    blockchain_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # QR code for customer scanning
    qr_code_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)


# ============================================================================
# 26. HAPPY HOUR PROMOTIONS
# ============================================================================

class HappyHour(Base, TimestampMixin):
    """Happy hour and time-based promotions."""

    __tablename__ = "happy_hours"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Schedule
    days: Mapped[List[str]] = mapped_column(JSON, nullable=False)  # ["Monday", "Tuesday", etc.]
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)

    # Date range (optional, for seasonal promos)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Discount configuration
    discount_type: Mapped[str] = mapped_column(String(20), nullable=False)  # percentage, fixed, bogo
    discount_value: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Scope
    applies_to: Mapped[str] = mapped_column(String(50), nullable=False)  # all, category, items
    category_ids: Mapped[Optional[List[int]]] = mapped_column(JSON, nullable=True)
    item_ids: Mapped[Optional[List[int]]] = mapped_column(JSON, nullable=True)

    # Limits
    max_per_customer: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    min_purchase: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")  # active, inactive, scheduled

    # Analytics
    times_used: Mapped[int] = mapped_column(Integer, default=0)
    total_discount_given: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)

    @validates('days', 'category_ids', 'item_ids')
    def _validate_list_fields(self, key, value):
        return validate_list(key, value)

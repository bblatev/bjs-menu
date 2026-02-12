"""
Feature Models - Phase 1.2
Menu engineering, auto-reorder rules, and other feature tables
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, Numeric, Date, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.db.base import Base


class MenuCategoryType(str, enum.Enum):
    """Menu engineering category classification"""
    STAR = "star"  # High profit, high popularity
    PUZZLE = "puzzle"  # High profit, low popularity
    PLOW_HORSE = "plow_horse"  # Low profit, high popularity
    DOG = "dog"  # Low profit, low popularity


class AutoReorderTrigger(str, enum.Enum):
    BELOW_PAR = "below_par"
    BELOW_REORDER_POINT = "below_reorder_point"
    FORECAST_BASED = "forecast_based"
    SCHEDULED = "scheduled"


class MenuEngineeringReport(Base):
    """Menu engineering analysis data"""
    __tablename__ = "menu_engineering_reports"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)

    # Report period
    report_date = Column(Date, nullable=False)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    period_type = Column(String(20))  # daily, weekly, monthly, quarterly

    # Averages for classification
    avg_contribution_margin = Column(Numeric(10, 2))
    avg_popularity_index = Column(Numeric(6, 4))
    total_menu_items = Column(Integer)

    # Summary statistics
    total_revenue = Column(Numeric(12, 2))
    total_food_cost = Column(Numeric(12, 2))
    overall_food_cost_pct = Column(Numeric(5, 2))
    total_items_sold = Column(Integer)

    # Category breakdown
    star_items_count = Column(Integer, default=0)
    puzzle_items_count = Column(Integer, default=0)
    plow_horse_items_count = Column(Integer, default=0)
    dog_items_count = Column(Integer, default=0)

    # Recommendations generated
    recommendations = Column(JSON)

    # Status
    is_current = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    generated_at = Column(DateTime, default=datetime.utcnow)  # Alias for created_at

    # Relationships
    venue = relationship("Venue", backref="menu_engineering_reports")
    items = relationship("MenuEngineeringItem", back_populates="report")


class MenuEngineeringItem(Base):
    """Menu engineering data for individual items"""
    __tablename__ = "menu_engineering_items"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("menu_engineering_reports.id"), nullable=False)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False)

    # Sales data
    quantity_sold = Column(Integer, default=0)
    total_revenue = Column(Numeric(12, 2), default=0)

    # Cost data
    food_cost = Column(Numeric(10, 2))
    food_cost_pct = Column(Numeric(5, 2))

    # Pricing
    selling_price = Column(Numeric(10, 2))
    contribution_margin = Column(Numeric(10, 2))

    # Popularity metrics
    sales_mix_pct = Column(Numeric(5, 2))  # % of total items sold
    popularity_index = Column(Numeric(6, 4))  # vs average

    # Classification
    category = Column(SQLEnum(MenuCategoryType))
    previous_category = Column(SQLEnum(MenuCategoryType))
    category_changed = Column(Boolean, default=False)

    # Recommendations
    recommended_action = Column(String(50))  # keep, reprice, reposition, remove, promote
    recommended_price = Column(Numeric(10, 2))
    recommendation_notes = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    report = relationship("MenuEngineeringReport", back_populates="items")
    menu_item = relationship("MenuItem", backref="engineering_data")


class AutoReorderRule(Base):
    """Auto-reorder rules for inventory items"""
    __tablename__ = "auto_reorder_rules"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=False)

    # Rule settings
    is_active = Column(Boolean, default=True)
    trigger_type = Column(SQLEnum(AutoReorderTrigger), default=AutoReorderTrigger.BELOW_REORDER_POINT)

    # Trigger thresholds
    reorder_point = Column(Numeric(10, 2))  # Trigger when below this
    par_level = Column(Numeric(10, 2))  # Target level to reorder to
    safety_stock = Column(Numeric(10, 2))  # Minimum buffer

    # Order quantities
    min_order_quantity = Column(Numeric(10, 2))
    max_order_quantity = Column(Numeric(10, 2))
    order_multiple = Column(Numeric(10, 2))  # Must order in multiples of

    # Supplier
    preferred_supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    alternative_supplier_ids = Column(JSON)  # Fallback suppliers

    # Lead time
    lead_time_days = Column(Integer, default=1)
    buffer_days = Column(Integer, default=0)

    # Schedule (for scheduled trigger)
    schedule_days = Column(String(20))  # "1,3,5" for Mon, Wed, Fri
    schedule_time = Column(String(10))  # "09:00"

    # Approval
    requires_approval = Column(Boolean, default=True)
    auto_approve_below_amount = Column(Numeric(10, 2))

    # Notifications
    notify_on_trigger = Column(Boolean, default=True)
    notification_emails = Column(String(500))

    # Statistics
    times_triggered = Column(Integer, default=0)
    last_triggered_at = Column(DateTime)
    last_order_id = Column(Integer, ForeignKey("purchase_orders.id"))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("staff_users.id"))

    # Relationships
    venue = relationship("Venue", backref="auto_reorder_rules")
    stock_item = relationship("StockItem", backref="auto_reorder_rules")
    preferred_supplier = relationship("Supplier", backref="preferred_reorder_rules")


class AutoReorderLog(Base):
    """Log of auto-reorder executions"""
    __tablename__ = "auto_reorder_logs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    rule_id = Column(Integer, ForeignKey("auto_reorder_rules.id"), nullable=False)
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=False)

    # Trigger details
    triggered_at = Column(DateTime, nullable=False)
    trigger_type = Column(String(50))
    trigger_reason = Column(Text)

    # Stock levels at trigger
    current_stock = Column(Numeric(10, 2))
    reorder_point = Column(Numeric(10, 2))
    par_level = Column(Numeric(10, 2))

    # Calculated order
    suggested_quantity = Column(Numeric(10, 2))
    final_quantity = Column(Numeric(10, 2))
    unit_price = Column(Numeric(10, 2))
    total_amount = Column(Numeric(10, 2))

    # Supplier used
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))

    # Result
    status = Column(String(30))  # pending_approval, approved, ordered, cancelled, failed
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"))

    # Approval
    approved_by = Column(Integer, ForeignKey("staff_users.id"))
    approved_at = Column(DateTime)
    rejection_reason = Column(Text)

    # Notes
    notes = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="auto_reorder_logs")
    rule = relationship("AutoReorderRule", backref="reorder_logs")
    stock_item = relationship("StockItem", backref="auto_reorder_logs")


class DemandForecast(Base):
    """Demand forecasting data"""
    __tablename__ = "demand_forecasts"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"))
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"))

    # Forecast period
    forecast_date = Column(Date, nullable=False)
    forecast_type = Column(String(20))  # daily, weekly, monthly

    # Predictions
    predicted_quantity = Column(Numeric(10, 2))
    predicted_revenue = Column(Numeric(12, 2))

    # Confidence
    confidence_level = Column(Numeric(5, 2))  # 0-100%
    lower_bound = Column(Numeric(10, 2))
    upper_bound = Column(Numeric(10, 2))

    # Model info
    model_type = Column(String(50))  # arima, prophet, ml, moving_avg
    model_version = Column(String(20))

    # Actual (filled after the fact)
    actual_quantity = Column(Numeric(10, 2))
    actual_revenue = Column(Numeric(12, 2))
    accuracy_pct = Column(Numeric(5, 2))

    # Factors considered
    factors = Column(JSON)  # weather, events, day_of_week, etc.

    generated_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="demand_forecasts")


class SeasonalityPattern(Base):
    """Seasonal patterns for forecasting"""
    __tablename__ = "seasonality_patterns"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"))
    category_id = Column(Integer, ForeignKey("menu_categories.id"))

    # Pattern type
    pattern_type = Column(String(30))  # hourly, daily, weekly, monthly, yearly

    # Pattern data
    pattern_data = Column(JSON)  # Coefficients/multipliers for each period

    # Example: weekly pattern
    # {"monday": 0.8, "tuesday": 0.85, "wednesday": 1.0, "thursday": 1.1, "friday": 1.4, "saturday": 1.5, "sunday": 1.2}

    # Confidence
    sample_size = Column(Integer)
    r_squared = Column(Numeric(5, 4))

    # Date range analyzed
    analysis_start = Column(Date)
    analysis_end = Column(Date)

    is_active = Column(Boolean, default=True)
    last_updated = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="seasonality_patterns")


class WastageLog(Base):
    """Track food/item wastage"""
    __tablename__ = "wastage_logs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"))
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"))

    # Wastage details
    waste_date = Column(DateTime, nullable=False)
    quantity = Column(Numeric(10, 3), nullable=False)
    unit = Column(String(20))
    cost = Column(Numeric(10, 2))

    # Reason
    reason_category = Column(String(50))  # expired, spoiled, damaged, overproduction, customer_return
    reason_detail = Column(Text)

    # Batch tracking
    batch_number = Column(String(100))
    expiry_date = Column(Date)

    # Staff
    recorded_by = Column(Integer, ForeignKey("staff_users.id"))
    verified_by = Column(Integer, ForeignKey("staff_users.id"))

    # Photo evidence
    photo_url = Column(String(500))

    # Disposition
    disposition = Column(String(50))  # discarded, donated, composted, recycled

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="wastage_logs")
    stock_item = relationship("StockItem", backref="wastage_logs")


class ProductionBatch(Base):
    """Track production batches for food prep"""
    __tablename__ = "production_batches"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)

    # Batch details
    batch_number = Column(String(100), nullable=False, unique=True)
    batch_date = Column(DateTime, nullable=False)

    # Quantities
    planned_quantity = Column(Numeric(10, 3))
    actual_quantity = Column(Numeric(10, 3))
    yield_pct = Column(Numeric(5, 2))

    # Costs
    ingredient_cost = Column(Numeric(10, 2))
    labor_cost = Column(Numeric(10, 2))
    total_cost = Column(Numeric(10, 2))
    cost_per_unit = Column(Numeric(10, 4))

    # Quality
    quality_score = Column(Integer)  # 1-5
    quality_notes = Column(Text)

    # Expiry
    production_date = Column(DateTime)
    use_by_date = Column(DateTime)

    # Staff
    prepared_by = Column(Integer, ForeignKey("staff_users.id"))
    verified_by = Column(Integer, ForeignKey("staff_users.id"))

    # Status
    status = Column(String(30))  # in_progress, completed, cancelled

    # HACCP
    temperature_log = Column(JSON)  # Temperature readings
    haccp_compliant = Column(Boolean, default=True)
    haccp_notes = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

    # Relationships
    venue = relationship("Venue", backref="production_batches")


class SpecialEvent(Base):
    """Special events that affect demand"""
    __tablename__ = "special_events"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)

    name = Column(String(200), nullable=False)
    event_type = Column(String(50))  # holiday, sports, local_event, promotion, private_party

    # Dates
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    is_all_day = Column(Boolean, default=True)

    # Impact
    expected_impact = Column(String(20))  # major_increase, increase, neutral, decrease, major_decrease
    impact_multiplier = Column(Numeric(4, 2), default=1.0)  # 1.5 = 50% more business

    # Affected items
    affects_all_items = Column(Boolean, default=True)
    affected_categories = Column(JSON)
    affected_items = Column(JSON)

    # Prep notes
    prep_notes = Column(Text)
    staffing_notes = Column(Text)

    # Results (filled after event)
    actual_impact_multiplier = Column(Numeric(4, 2))
    notes = Column(Text)

    is_recurring = Column(Boolean, default=False)
    recurrence_rule = Column(String(200))  # RRULE format

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="special_events")


class VIPCustomer(Base):
    """VIP customer designations and perks"""
    __tablename__ = "vip_customers"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)

    # VIP tier
    vip_tier = Column(String(50), nullable=False)  # bronze, silver, gold, platinum, diamond
    tier_since = Column(DateTime)

    # Status
    is_active = Column(Boolean, default=True)
    status_reason = Column(String(100))  # auto, manual, referral

    # Perks
    discount_pct = Column(Numeric(5, 2), default=0)
    free_delivery = Column(Boolean, default=False)
    priority_seating = Column(Boolean, default=False)
    complimentary_items = Column(JSON)  # List of free item IDs
    birthday_offer = Column(Text)
    anniversary_offer = Column(Text)

    # Custom preferences
    preferred_table = Column(String(50))
    preferred_server_id = Column(Integer, ForeignKey("staff_users.id"))
    special_requests = Column(Text)
    dietary_notes = Column(Text)

    # Communication preferences
    allow_vip_notifications = Column(Boolean, default=True)
    preferred_contact_method = Column(String(30))

    # Statistics
    total_lifetime_spend = Column(Numeric(12, 2), default=0)
    total_visits = Column(Integer, default=0)
    last_visit_date = Column(DateTime)
    avg_spend_per_visit = Column(Numeric(10, 2))

    # Notes
    host_notes = Column(Text)  # Notes for front-of-house staff

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("staff_users.id"))

    # Relationships
    venue = relationship("Venue", backref="vip_customers")
    customer = relationship("Customer", backref="vip_status")


class Referral(Base):
    """Individual referrals"""
    __tablename__ = "referrals"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    program_id = Column(Integer, ForeignKey("referral_programs.id"), nullable=False)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)

    # Referrer
    referrer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    referral_code = Column(String(50), nullable=False, unique=True)

    # Referee
    referee_id = Column(Integer, ForeignKey("customers.id"))
    referee_email = Column(String(200))
    referee_phone = Column(String(50))

    # Status
    status = Column(String(30), default="pending")  # pending, signup, converted, expired, cancelled

    # Conversion
    signup_date = Column(DateTime)
    conversion_date = Column(DateTime)
    conversion_order_id = Column(Integer, ForeignKey("orders.id"))

    # Rewards
    referrer_rewarded = Column(Boolean, default=False)
    referrer_reward_date = Column(DateTime)
    referrer_reward_amount = Column(Numeric(10, 2))

    referee_rewarded = Column(Boolean, default=False)
    referee_reward_date = Column(DateTime)
    referee_reward_amount = Column(Numeric(10, 2))

    # Tracking
    referral_source = Column(String(50))  # email, social, in_app, qr_code
    utm_source = Column(String(100))
    utm_medium = Column(String(100))
    utm_campaign = Column(String(100))

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    program = relationship("ReferralProgram", backref="referrals")
    venue = relationship("Venue", backref="referrals")
    referrer = relationship("Customer", foreign_keys=[referrer_id], backref="referrals_made")
    referee = relationship("Customer", foreign_keys=[referee_id], backref="referred_by")

"""
BJS V6.1 Enterprise - Missing Features Models
Implements all 33 missing features from GAP analysis
"""

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, JSON,
    ForeignKey, Enum, Date, Time, Numeric, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from datetime import datetime, date, time
from enum import Enum as PyEnum
from app.db.base import Base


# =====================================================
# TIER 1 - CRITICAL FEATURES
# =====================================================

# 1. RESERVATION DEPOSITS
# Note: ReservationDeposit model is defined in __init__.py to avoid duplicate table definitions
class ReservationDepositStatus(str, PyEnum):
    PENDING = "pending"
    COLLECTED = "collected"
    APPLIED = "applied"
    REFUNDED = "refunded"
    FORFEITED = "forfeited"


class DepositPolicy(Base):
    __tablename__ = "deposit_policies"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)

    # Policy rules
    min_party_size = Column(Integer, default=1)  # Apply for parties of X+
    min_deposit_amount = Column(Numeric(10, 2))  # Fixed amount
    deposit_percentage = Column(Float)  # Or percentage of estimated bill

    # Time-based rules
    applies_to_days = Column(JSON)  # ["friday", "saturday"]
    applies_to_times = Column(JSON)  # Peak hours
    applies_to_occasions = Column(JSON)  # Special events

    # Cancellation policy
    cancellation_deadline_hours = Column(Integer, default=24)
    partial_refund_percentage = Column(Float, default=50)
    no_show_forfeit = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="deposit_policies")


# 2. SMS MARKETING
class SMSCampaignStatus(str, PyEnum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENDING = "sending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class SMSCampaign(Base):
    __tablename__ = "sms_campaigns"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    name = Column(String(200), nullable=False)
    message_template = Column(Text, nullable=False)  # Max 160 chars
    status = Column(String(20), default=SMSCampaignStatus.DRAFT.value)

    # Targeting
    target_segment = Column(String(50))  # all, loyal, inactive, new
    target_filters = Column(JSON)  # Custom filters
    estimated_recipients = Column(Integer, default=0)

    # Scheduling
    scheduled_at = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # Results
    total_sent = Column(Integer, default=0)
    total_delivered = Column(Integer, default=0)
    total_failed = Column(Integer, default=0)
    total_opted_out = Column(Integer, default=0)

    # Tracking
    promo_code = Column(String(50))  # Associated promo
    redemption_count = Column(Integer, default=0)
    revenue_generated = Column(Numeric(10, 2), default=0)

    created_by = Column(Integer, ForeignKey("staff_users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="sms_campaigns")
    creator = relationship("StaffUser", backref="created_sms_campaigns")
    messages = relationship("SMSMessage", back_populates="campaign")


# SMSMessage is defined in core_business_models.py - DO NOT define here to avoid duplicate


class SMSOptOut(Base):
    __tablename__ = "sms_opt_outs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    phone_number = Column(String(20), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), index=True)

    opted_out_at = Column(DateTime, default=datetime.utcnow)
    reason = Column(String(100))

    # Relationships
    venue = relationship("Venue", backref="sms_opt_outs")
    customer = relationship("Customer", backref="sms_opt_outs")

    __table_args__ = (
        UniqueConstraint('venue_id', 'phone_number', name='uq_sms_opt_out'),
        Index('ix_sms_opt_outs_venue_phone', 'venue_id', 'phone_number'),
    )


# 3. BENCHMARKING
class BenchmarkCategory(str, PyEnum):
    REVENUE = "revenue"
    LABOR = "labor"
    FOOD_COST = "food_cost"
    SPEED = "speed"
    SATISFACTION = "satisfaction"
    EFFICIENCY = "efficiency"


class RestaurantBenchmark(Base):
    __tablename__ = "restaurant_benchmarks"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)

    # Revenue metrics
    revenue_per_seat = Column(Numeric(10, 2))
    revenue_per_labor_hour = Column(Numeric(10, 2))
    average_check = Column(Numeric(10, 2))
    covers_per_day = Column(Float)
    table_turn_time_minutes = Column(Float)

    # Cost metrics
    food_cost_percentage = Column(Float)
    labor_cost_percentage = Column(Float)
    prime_cost_percentage = Column(Float)
    waste_percentage = Column(Float)

    # Efficiency metrics
    orders_per_labor_hour = Column(Float)
    items_per_order = Column(Float)
    upsell_rate = Column(Float)

    # Speed metrics
    avg_ticket_time_minutes = Column(Float)
    avg_table_service_minutes = Column(Float)

    # Satisfaction metrics
    average_rating = Column(Float)
    nps_score = Column(Float)
    repeat_customer_rate = Column(Float)

    # Industry comparison (percentile rank)
    revenue_percentile = Column(Integer)
    efficiency_percentile = Column(Integer)
    satisfaction_percentile = Column(Integer)

    calculated_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="restaurant_benchmarks")

    __table_args__ = (
        Index('ix_restaurant_benchmarks_venue_period', 'venue_id', 'period_start', 'period_end'),
    )


class IndustryBenchmark(Base):
    """Anonymized industry-wide benchmarks"""
    __tablename__ = "industry_benchmarks"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)

    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)

    restaurant_type = Column(String(50), index=True)  # fine_dining, casual, fast_casual, qsr
    region = Column(String(50), index=True)  # bulgaria, sofia, plovdiv

    # Aggregated metrics (percentiles)
    metric_name = Column(String(100), nullable=False, index=True)
    percentile_25 = Column(Float)
    percentile_50 = Column(Float)  # Median
    percentile_75 = Column(Float)
    percentile_90 = Column(Float)

    sample_size = Column(Integer)

    updated_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('ix_industry_benchmarks_type_region', 'restaurant_type', 'region'),
        Index('ix_industry_benchmarks_period', 'period_start', 'period_end'),
    )


# 4. CATERING & EVENTS MODULE
class CateringEventStatus(str, PyEnum):
    INQUIRY = "inquiry"
    QUOTED = "quoted"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    DELIVERED = "delivered"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CateringEvent(Base):
    __tablename__ = "catering_events"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    
    # Event details
    event_name = Column(String(200), nullable=False)
    event_type = Column(String(50))  # wedding, corporate, birthday, etc.
    event_date = Column(Date, nullable=False)
    event_time = Column(Time)
    
    # Venue
    venue_type = Column(String(20))  # on_site, off_site, pickup
    venue_name = Column(String(200))
    venue_address = Column(Text)
    venue_notes = Column(Text)
    
    # Guest info
    guest_count = Column(Integer, nullable=False)
    dietary_requirements = Column(JSON)  # {"vegetarian": 5, "gluten_free": 3}
    
    # Contact
    contact_name = Column(String(100))
    contact_phone = Column(String(20))
    contact_email = Column(String(255))
    
    # Status & timeline
    status = Column(String(20), default=CateringEventStatus.INQUIRY.value)
    inquiry_date = Column(DateTime, default=datetime.utcnow)
    quote_sent_date = Column(DateTime)
    confirmed_date = Column(DateTime)
    
    # Pricing
    subtotal = Column(Numeric(10, 2), default=0)
    service_charge = Column(Numeric(10, 2), default=0)
    delivery_fee = Column(Numeric(10, 2), default=0)
    tax = Column(Numeric(10, 2), default=0)
    total = Column(Numeric(10, 2), default=0)
    
    # Deposits
    deposit_required = Column(Numeric(10, 2))
    deposit_paid = Column(Numeric(10, 2), default=0)
    balance_due = Column(Numeric(10, 2))
    
    # Staff assignment
    assigned_coordinator = Column(Integer, ForeignKey("staff_users.id"))
    assigned_chef = Column(Integer, ForeignKey("staff_users.id"))
    
    notes = Column(Text)
    internal_notes = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="catering_events")
    customer = relationship("Customer", backref="catering_events")
    coordinator = relationship("StaffUser", foreign_keys=[assigned_coordinator], backref="coordinated_catering_events")
    chef = relationship("StaffUser", foreign_keys=[assigned_chef], backref="chef_catering_events")
    order_items = relationship("CateringOrderItem", back_populates="catering_event")
    invoices = relationship("CateringInvoice", back_populates="catering_event")
    kitchen_sheets = relationship("KitchenSheet", back_populates="catering_event")


class CateringMenu(Base):
    __tablename__ = "catering_menus"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    name = Column(String(200), nullable=False)
    description = Column(Text)
    menu_type = Column(String(50))  # buffet, plated, family_style, cocktail

    min_guest_count = Column(Integer, default=10)
    max_guest_count = Column(Integer)

    price_per_person = Column(Numeric(10, 2))
    setup_fee = Column(Numeric(10, 2), default=0)

    is_active = Column(Boolean, default=True)

    # Menu items (JSON for flexibility)
    menu_sections = Column(JSON)  # {"appetizers": [...], "mains": [...]}

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="catering_menus")


class CateringOrderItem(Base):
    __tablename__ = "catering_order_items"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    catering_event_id = Column(Integer, ForeignKey("catering_events.id"), nullable=False, index=True)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), index=True)

    item_name = Column(String(200), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)

    special_instructions = Column(Text)
    dietary_tags = Column(JSON)

    # For production tracking
    prep_status = Column(String(20), default="pending")
    prep_notes = Column(Text)

    # Relationships
    catering_event = relationship("CateringEvent", back_populates="order_items")
    menu_item = relationship("MenuItem", backref="catering_order_items")


class CateringInvoice(Base):
    __tablename__ = "catering_invoices"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    catering_event_id = Column(Integer, ForeignKey("catering_events.id"), nullable=False, index=True)

    invoice_number = Column(String(50), unique=True, nullable=False, index=True)
    invoice_date = Column(Date, default=date.today)
    due_date = Column(Date)

    subtotal = Column(Numeric(10, 2), nullable=False)
    tax = Column(Numeric(10, 2), default=0)
    total = Column(Numeric(10, 2), nullable=False)

    amount_paid = Column(Numeric(10, 2), default=0)
    balance_due = Column(Numeric(10, 2))

    status = Column(String(20), default="draft", index=True)  # draft, sent, paid, overdue
    sent_at = Column(DateTime)
    paid_at = Column(DateTime)

    notes = Column(Text)
    terms = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="catering_invoices")
    catering_event = relationship("CateringEvent", back_populates="invoices")


# 5. CUSTOMER DISPLAY SYSTEM
class CustomerDisplay(Base):
    __tablename__ = "customer_displays"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    device_id = Column(String(100), unique=True, nullable=False, index=True)
    device_name = Column(String(100))

    # Assignment
    terminal_id = Column(Integer)  # Associated POS terminal
    location = Column(String(100))  # "Register 1", "Drive-thru"

    # Display settings
    display_mode = Column(String(20), default="order")  # order, idle, promo
    theme = Column(String(50), default="default")
    language = Column(String(10), default="bg")

    # Content settings
    show_item_prices = Column(Boolean, default=True)
    show_modifiers = Column(Boolean, default=True)
    show_running_total = Column(Boolean, default=True)
    show_tax = Column(Boolean, default=True)
    show_tips = Column(Boolean, default=True)

    # Idle content
    idle_content_type = Column(String(20))  # promotions, menu, slideshow
    idle_content_config = Column(JSON)

    # Status
    is_active = Column(Boolean, default=True)
    last_seen_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="customer_displays")


class CustomerDisplayContent(Base):
    """Promotional content for customer displays"""
    __tablename__ = "customer_display_content"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    content_type = Column(String(20), nullable=False, index=True)  # promo, ad, menu_item, message
    title = Column(String(200))
    description = Column(Text)
    image_url = Column(String(500))
    video_url = Column(String(500))

    # Scheduling
    start_date = Column(Date)
    end_date = Column(Date)
    display_hours = Column(JSON)  # {"start": "11:00", "end": "14:00"}

    # Display settings
    duration_seconds = Column(Integer, default=10)
    priority = Column(Integer, default=0)

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="customer_display_content")


# 6. MENU ITEM REVIEWS
class MenuItemReview(Base):
    __tablename__ = "menu_item_reviews"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), index=True)

    rating = Column(Integer, nullable=False)  # 1-5
    review_text = Column(Text)

    # Review aspects
    taste_rating = Column(Integer)  # 1-5
    presentation_rating = Column(Integer)  # 1-5
    portion_rating = Column(Integer)  # 1-5
    value_rating = Column(Integer)  # 1-5

    # Photo reviews
    photo_urls = Column(JSON)  # List of uploaded photos

    # Verification
    verified_purchase = Column(Boolean, default=False)

    # Moderation
    status = Column(String(20), default="pending", index=True)  # pending, approved, rejected
    moderated_at = Column(DateTime)
    moderated_by = Column(Integer, ForeignKey("staff_users.id"))

    # Response
    response_text = Column(Text)
    responded_at = Column(DateTime)
    responded_by = Column(Integer, ForeignKey("staff_users.id"))

    # Stats
    helpful_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="menu_item_reviews")
    menu_item = relationship("MenuItem", backref="menu_item_reviews")
    customer = relationship("Customer", backref="menu_item_reviews")
    order = relationship("Order", backref="menu_item_reviews")
    moderator = relationship("StaffUser", foreign_keys=[moderated_by], backref="moderated_reviews")
    responder = relationship("StaffUser", foreign_keys=[responded_by], backref="responded_reviews")


class MenuItemRatingAggregate(Base):
    """Pre-calculated rating aggregates for menu items"""
    __tablename__ = "menu_item_rating_aggregates"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), unique=True, nullable=False, index=True)

    total_reviews = Column(Integer, default=0)
    average_rating = Column(Float, default=0)

    rating_1_count = Column(Integer, default=0)
    rating_2_count = Column(Integer, default=0)
    rating_3_count = Column(Integer, default=0)
    rating_4_count = Column(Integer, default=0)
    rating_5_count = Column(Integer, default=0)

    avg_taste = Column(Float)
    avg_presentation = Column(Float)
    avg_portion = Column(Float)
    avg_value = Column(Float)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    menu_item = relationship("MenuItem", backref="rating_aggregate")


# 7. SMART QUOTE PREP TIME
class PrepTimeModel(Base):
    """AI model for predicting prep times"""
    __tablename__ = "prep_time_models"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    model_version = Column(String(20), nullable=False)
    model_type = Column(String(50), default="gradient_boost")

    # Model parameters (serialized)
    model_params = Column(JSON)
    feature_weights = Column(JSON)

    # Performance metrics
    mae_minutes = Column(Float)  # Mean Absolute Error
    accuracy_within_5min = Column(Float)  # % within 5 min

    # Training info
    training_samples = Column(Integer)
    trained_at = Column(DateTime)
    is_active = Column(Boolean, default=False, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="prep_time_models")


class PrepTimePrediction(Base):
    """Historical prep time predictions for model improvement"""
    __tablename__ = "prep_time_predictions"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)

    # Prediction
    predicted_minutes = Column(Float, nullable=False)
    confidence = Column(Float)  # 0-1

    # Actual
    actual_minutes = Column(Float)

    # Factors considered
    factors = Column(JSON)  # {"kitchen_load": 0.8, "complexity": 0.6, ...}

    # For model training
    day_of_week = Column(Integer)
    hour_of_day = Column(Integer)
    current_orders = Column(Integer)
    item_count = Column(Integer)
    complexity_score = Column(Float)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="prep_time_predictions")
    order = relationship("Order", backref="prep_time_predictions")


# =====================================================
# TIER 2 - HIGH PRIORITY FEATURES
# =====================================================

# 8. SINGLE-USE PROMO CODES
class SingleUsePromoCode(Base):
    __tablename__ = "single_use_promo_codes"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    campaign_id = Column(Integer, ForeignKey("promo_campaigns.id"), index=True)

    code = Column(String(50), unique=True, nullable=False, index=True)

    # Discount settings
    discount_type = Column(String(20), nullable=False)  # percentage, fixed, item
    discount_value = Column(Numeric(10, 2), nullable=False)
    max_discount = Column(Numeric(10, 2))  # Cap for percentage discounts

    # Usage rules
    min_order_value = Column(Numeric(10, 2))
    valid_for_items = Column(JSON)  # Specific items/categories

    # Validity
    valid_from = Column(DateTime)
    valid_until = Column(DateTime)

    # Assignment
    customer_id = Column(Integer, ForeignKey("customers.id"), index=True)
    email = Column(String(255))
    phone = Column(String(20))

    # Status
    is_used = Column(Boolean, default=False, index=True)
    used_at = Column(DateTime)
    used_order_id = Column(Integer, ForeignKey("orders.id"), index=True)
    discount_amount = Column(Numeric(10, 2))

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="single_use_promo_codes")
    campaign = relationship("PromoCodeCampaign", back_populates="codes")
    customer = relationship("Customer", backref="single_use_promo_codes")
    used_order = relationship("Order", backref="single_use_promo_codes")


class PromoCodeCampaign(Base):
    __tablename__ = "promo_campaigns"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    name = Column(String(200), nullable=False)
    description = Column(Text)

    code_prefix = Column(String(10))  # For generated codes

    # Discount settings (template for generated codes)
    discount_type = Column(String(20), nullable=False)
    discount_value = Column(Numeric(10, 2), nullable=False)
    max_discount = Column(Numeric(10, 2))
    min_order_value = Column(Numeric(10, 2))

    # Generation
    total_codes = Column(Integer, default=0)
    codes_used = Column(Integer, default=0)

    # Validity
    valid_from = Column(DateTime)
    valid_until = Column(DateTime)

    is_active = Column(Boolean, default=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="promo_campaigns")
    codes = relationship("SingleUsePromoCode", back_populates="campaign")


# 9. REFERRAL PROGRAM
# ReferralProgram is defined elsewhere - commented out to avoid duplicate
# class ReferralProgram(Base):
#     __tablename__ = "referral_programs"
#     __table_args__ = {'extend_existing': True}

#     id = Column(Integer, primary_key=True, index=True)
#     venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

#     name = Column(String(200), nullable=False)

#     # Rewards
#     referrer_reward_type = Column(String(20))  # points, credit, discount
#     referrer_reward_value = Column(Numeric(10, 2))

#     referee_reward_type = Column(String(20))
#     referee_reward_value = Column(Numeric(10, 2))

#     # Requirements
#     min_order_value = Column(Numeric(10, 2))  # First order minimum
#     reward_after_orders = Column(Integer, default=1)  # Orders before reward

#     # Limits
#     max_referrals_per_customer = Column(Integer)

#     is_active = Column(Boolean, default=True, index=True)

#     created_at = Column(DateTime, default=datetime.utcnow)

#     # Relationships
#     venue = relationship("Venue", backref="mf_referral_programs")
#     referrals = relationship("CustomerReferral", back_populates="program")


class CustomerReferral(Base):
    __tablename__ = "customer_referrals"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    program_id = Column(Integer, ForeignKey("referral_programs.id"), nullable=False, index=True)

    referrer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    referee_id = Column(Integer, ForeignKey("customers.id"), index=True)

    referral_code = Column(String(20), unique=True, nullable=False, index=True)
    referee_email = Column(String(255))
    referee_phone = Column(String(20))

    # Status
    status = Column(String(20), default="pending", index=True)  # pending, registered, qualified, rewarded

    registered_at = Column(DateTime)
    qualified_at = Column(DateTime)  # When referee met requirements
    rewarded_at = Column(DateTime)

    # Rewards issued
    referrer_reward_issued = Column(Boolean, default=False)
    referee_reward_issued = Column(Boolean, default=False)

    qualifying_order_id = Column(Integer, ForeignKey("orders.id"), index=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="customer_referrals")
    program = relationship("ReferralProgram", backref="customer_referrals")
    referrer = relationship("Customer", foreign_keys=[referrer_id], backref="mf_referrals_made")
    referee = relationship("Customer", foreign_keys=[referee_id], backref="referral_received")
    qualifying_order = relationship("Order", backref="referral_qualifications")


# 10. RFM ANALYTICS
class CustomerRFMScore(Base):
    """Recency, Frequency, Monetary scoring for customers"""
    __tablename__ = "customer_rfm_scores"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)

    # Raw values
    days_since_last_order = Column(Integer)
    total_orders = Column(Integer)
    total_revenue = Column(Numeric(10, 2))
    avg_order_value = Column(Numeric(10, 2))

    # Scores (1-5 or 1-10)
    recency_score = Column(Integer)
    frequency_score = Column(Integer)
    monetary_score = Column(Integer)

    # Combined score
    rfm_score = Column(Integer)  # Combined RFM

    # Segment
    segment = Column(String(50), index=True)  # champions, loyal, at_risk, lost, etc.

    # Period
    calculation_date = Column(Date, nullable=False, index=True)
    period_days = Column(Integer, default=365)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="customer_rfm_scores")
    customer = relationship("Customer", backref="customer_rfm_scores")

    __table_args__ = (
        UniqueConstraint('venue_id', 'customer_id', 'calculation_date', name='uq_rfm_score'),
    )


class RFMSegmentDefinition(Base):
    __tablename__ = "rfm_segment_definitions"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    segment_name = Column(String(50), nullable=False)
    description = Column(Text)

    # Score ranges
    min_recency = Column(Integer)
    max_recency = Column(Integer)
    min_frequency = Column(Integer)
    max_frequency = Column(Integer)
    min_monetary = Column(Integer)
    max_monetary = Column(Integer)

    # Recommended actions
    recommended_actions = Column(JSON)

    # Display
    color = Column(String(20))
    priority = Column(Integer, default=0)

    is_active = Column(Boolean, default=True)

    # Relationships
    venue = relationship("Venue", backref="rfm_segment_definitions")


# 11. PRICE TRACKER
class IngredientPriceHistory(Base):
    __tablename__ = "ingredient_price_history"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=False, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), index=True)

    price = Column(Numeric(10, 4), nullable=False)
    unit = Column(String(20), nullable=False)

    recorded_date = Column(Date, nullable=False, index=True)
    source = Column(String(50))  # purchase_order, manual, api

    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), index=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="ingredient_price_history")
    stock_item = relationship("StockItem", backref="mf_price_history")
    supplier = relationship("Supplier", backref="ingredient_price_history")
    purchase_order = relationship("PurchaseOrder", backref="ingredient_price_history")


class PriceAlertNotification(Base):
    __tablename__ = "price_alert_notifications"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, ForeignKey("price_alerts.id"), nullable=False, index=True)

    old_price = Column(Numeric(10, 4))
    new_price = Column(Numeric(10, 4))
    change_percentage = Column(Float)

    is_read = Column(Boolean, default=False, index=True)
    read_at = Column(DateTime)
    read_by = Column(Integer, ForeignKey("staff_users.id"))

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    alert = relationship("PriceAlert", backref="notifications")
    reader = relationship("StaffUser", backref="read_price_alerts")


# 12. BREAK MANAGEMENT
class BreakPolicy(Base):
    __tablename__ = "break_policies"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    name = Column(String(100), nullable=False)

    # Rules
    min_shift_hours = Column(Float)  # Minimum shift length for break
    break_duration_minutes = Column(Integer, nullable=False)
    is_paid = Column(Boolean, default=False)

    # Scheduling
    must_take_after_hours = Column(Float)  # Must take after X hours
    must_take_before_hours = Column(Float)  # Must take before X hours from end

    # Compliance
    is_mandatory = Column(Boolean, default=False)

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="break_policies")


class EmployeeBreak(Base):
    __tablename__ = "employee_breaks"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    staff_id = Column(Integer, ForeignKey("staff_users.id"), nullable=False, index=True)
    shift_id = Column(Integer, ForeignKey("staff_shifts.id"), index=True)

    break_type = Column(String(20))  # meal, rest, smoke

    scheduled_start = Column(DateTime)
    scheduled_end = Column(DateTime)
    scheduled_duration_minutes = Column(Integer)

    actual_start = Column(DateTime)
    actual_end = Column(DateTime)
    actual_duration_minutes = Column(Integer)

    status = Column(String(20), default="scheduled", index=True)  # scheduled, in_progress, completed, missed

    is_paid = Column(Boolean, default=False)

    notes = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="employee_breaks")
    staff = relationship("StaffUser", backref="employee_breaks")
    shift = relationship("StaffShift", backref="employee_breaks")


# 13. SHIFT TRADING
class ShiftTradeRequest(Base):
    __tablename__ = "shift_trade_requests"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    # Original shift
    original_shift_id = Column(Integer, ForeignKey("staff_shifts.id"), nullable=False, index=True)
    requester_id = Column(Integer, ForeignKey("staff_users.id"), nullable=False, index=True)

    # Trade type
    trade_type = Column(String(20), nullable=False)  # swap, giveaway, pickup

    # For swaps
    offered_shift_id = Column(Integer, ForeignKey("staff_shifts.id"), index=True)

    # Target (for directed requests)
    target_employee_id = Column(Integer, ForeignKey("staff_users.id"), index=True)

    # For open trades
    is_open_to_all = Column(Boolean, default=True)

    # Status
    status = Column(String(20), default="pending", index=True)  # pending, accepted, rejected, cancelled, expired

    # Response
    accepted_by_id = Column(Integer, ForeignKey("staff_users.id"), index=True)
    accepted_at = Column(DateTime)

    # Manager approval
    requires_approval = Column(Boolean, default=True)
    approved_by_id = Column(Integer, ForeignKey("staff_users.id"), index=True)
    approved_at = Column(DateTime)
    rejection_reason = Column(Text)

    # Expiration
    expires_at = Column(DateTime)

    reason = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="shift_trade_requests")
    original_shift = relationship("StaffShift", foreign_keys=[original_shift_id], backref="trade_requests_from")
    offered_shift = relationship("StaffShift", foreign_keys=[offered_shift_id], backref="trade_requests_to")
    requester = relationship("StaffUser", foreign_keys=[requester_id], backref="shift_trade_requests_made")
    target_employee = relationship("StaffUser", foreign_keys=[target_employee_id], backref="shift_trade_requests_received")
    accepted_by = relationship("StaffUser", foreign_keys=[accepted_by_id], backref="shift_trades_accepted")
    approved_by = relationship("StaffUser", foreign_keys=[approved_by_id], backref="shift_trades_approved")


# 14. VIP MANAGEMENT
class VIPTier(Base):
    __tablename__ = "vip_tiers"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    name = Column(String(50), nullable=False)  # Bronze, Silver, Gold, Platinum
    description = Column(Text)

    # Qualification
    min_annual_spend = Column(Numeric(10, 2))
    min_visits = Column(Integer)
    min_loyalty_points = Column(Integer)
    is_invite_only = Column(Boolean, default=False)

    # Benefits
    discount_percentage = Column(Float)
    points_multiplier = Column(Float, default=1.0)
    priority_reservations = Column(Boolean, default=False)
    complimentary_items = Column(JSON)  # List of free items

    # Perks
    dedicated_contact = Column(Boolean, default=False)
    special_events_access = Column(Boolean, default=False)
    birthday_reward = Column(JSON)
    anniversary_reward = Column(JSON)

    # Display
    badge_color = Column(String(20))
    badge_icon = Column(String(50))

    priority = Column(Integer, default=0)  # Higher = better tier
    is_active = Column(Boolean, default=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="vip_tiers")
    customer_statuses = relationship("CustomerVIPStatus", back_populates="vip_tier")


class CustomerVIPStatus(Base):
    __tablename__ = "customer_vip_status"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    vip_tier_id = Column(Integer, ForeignKey("vip_tiers.id"), nullable=False, index=True)

    # Assignment
    assigned_date = Column(Date, nullable=False)
    assigned_by = Column(Integer, ForeignKey("staff_users.id"))
    assignment_reason = Column(String(50))  # auto, manual, invite

    # Validity
    valid_until = Column(Date)

    # Stats at assignment
    total_spend_at_assignment = Column(Numeric(10, 2))
    total_visits_at_assignment = Column(Integer)

    # Notes
    notes = Column(Text)
    preferences = Column(JSON)  # Special preferences for this VIP

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="customer_vip_statuses")
    customer = relationship("Customer", backref="mf_vip_status")
    vip_tier = relationship("VIPTier", back_populates="customer_statuses")
    assigned_by_user = relationship("StaffUser", backref="vip_assignments")

    __table_args__ = (
        UniqueConstraint('venue_id', 'customer_id', name='uq_customer_vip'),
    )


# =====================================================
# TIER 3 - ENHANCEMENT FEATURES
# =====================================================

# 15. GUESTBOOK
class GuestbookEntry(Base):
    __tablename__ = "guestbook_entries"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), index=True)

    guest_name = Column(String(100))
    guest_email = Column(String(255))

    message = Column(Text, nullable=False)
    rating = Column(Integer)  # 1-5

    visit_date = Column(Date)
    occasion = Column(String(100))  # birthday, anniversary, etc.

    # Media
    photo_urls = Column(JSON)

    # Moderation
    is_approved = Column(Boolean, default=False, index=True)
    is_featured = Column(Boolean, default=False, index=True)
    moderated_at = Column(DateTime)
    moderated_by = Column(Integer, ForeignKey("staff_users.id"))

    # Display settings
    is_public = Column(Boolean, default=True)
    show_name = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="guestbook_entries")
    customer = relationship("Customer", backref="guestbook_entries")
    moderator = relationship("StaffUser", backref="moderated_guestbook_entries")


# 16. FUNDRAISING / ROUND-UP
class FundraisingCampaign(Base):
    __tablename__ = "fundraising_campaigns"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    name = Column(String(200), nullable=False)
    description = Column(Text)
    organization_name = Column(String(200))
    organization_logo_url = Column(String(500))

    # Type
    campaign_type = Column(String(20), nullable=False)  # round_up, fixed_donation, percentage

    # Settings
    round_up_to = Column(Numeric(10, 2))  # Round up to nearest X
    fixed_amount = Column(Numeric(10, 2))  # Fixed donation amount
    percentage = Column(Float)  # Percentage of bill

    # Goal
    goal_amount = Column(Numeric(10, 2))
    raised_amount = Column(Numeric(10, 2), default=0)
    donation_count = Column(Integer, default=0)

    # Duration
    start_date = Column(Date)
    end_date = Column(Date)

    # Display
    prompt_message = Column(Text)
    thank_you_message = Column(Text)

    is_active = Column(Boolean, default=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="fundraising_campaigns")
    donations = relationship("FundraisingDonation", back_populates="campaign")


class FundraisingDonation(Base):
    __tablename__ = "fundraising_donations"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("fundraising_campaigns.id"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), index=True)

    amount = Column(Numeric(10, 2), nullable=False)
    original_total = Column(Numeric(10, 2))
    rounded_total = Column(Numeric(10, 2))

    # For receipts
    is_tax_deductible = Column(Boolean, default=False)
    receipt_sent = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    campaign = relationship("FundraisingCampaign", back_populates="donations")
    order = relationship("Order", backref="fundraising_donations")
    customer = relationship("Customer", backref="fundraising_donations")


# 17. CHARGEBACK MANAGEMENT
class ChargebackStatus(str, PyEnum):
    RECEIVED = "received"
    UNDER_REVIEW = "under_review"
    EVIDENCE_SUBMITTED = "evidence_submitted"
    WON = "won"
    LOST = "lost"


class Chargeback(Base):
    __tablename__ = "chargebacks"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), index=True)
    payment_id = Column(Integer)

    # Chargeback details
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="BGN")
    reason_code = Column(String(50))
    reason = Column(Text)

    # Provider info
    provider_case_id = Column(String(100), index=True)
    provider = Column(String(50))  # stripe, etc.

    # Status
    status = Column(String(20), default=ChargebackStatus.RECEIVED.value, index=True)

    # Timeline
    received_at = Column(DateTime, nullable=False)
    due_date = Column(DateTime)  # Evidence submission deadline
    resolved_at = Column(DateTime)

    # Response
    evidence_submitted = Column(Boolean, default=False)
    evidence_submitted_at = Column(DateTime)
    evidence_documents = Column(JSON)  # List of document URLs
    response_notes = Column(Text)

    # Outcome
    won = Column(Boolean)
    amount_recovered = Column(Numeric(10, 2))

    # Assignment
    assigned_to = Column(Integer, ForeignKey("staff_users.id"), index=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="chargebacks")
    order = relationship("Order", backref="chargebacks")
    assignee = relationship("StaffUser", backref="assigned_chargebacks")


# 18. TAX CENTER
class TaxReport(Base):
    __tablename__ = "tax_reports"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    report_type = Column(String(50), nullable=False, index=True)  # vat, income, payroll
    period_type = Column(String(20))  # monthly, quarterly, annual

    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)

    # Financial data
    gross_revenue = Column(Numeric(12, 2))
    net_revenue = Column(Numeric(12, 2))
    total_tax_collected = Column(Numeric(12, 2))
    total_tax_owed = Column(Numeric(12, 2))

    # Breakdown by tax rate
    tax_breakdown = Column(JSON)  # {"20%": 5000, "9%": 1000}

    # Status
    status = Column(String(20), default="draft", index=True)  # draft, finalized, submitted
    finalized_at = Column(DateTime)
    submitted_at = Column(DateTime)

    # Filing info
    filing_reference = Column(String(100))
    filed_by = Column(Integer, ForeignKey("staff_users.id"))

    # Document
    report_url = Column(String(500))

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="tax_reports")
    filer = relationship("StaffUser", backref="filed_tax_reports")


class TaxReminder(Base):
    __tablename__ = "tax_reminders"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    tax_type = Column(String(50), nullable=False)
    description = Column(Text)

    due_date = Column(Date, nullable=False, index=True)
    reminder_days_before = Column(JSON)  # [30, 14, 7, 1]

    is_recurring = Column(Boolean, default=False)
    recurrence_pattern = Column(String(20))  # monthly, quarterly, annual

    last_reminder_sent = Column(DateTime)
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="tax_reminders")


# 19. EMPLOYEE ONBOARDING
class OnboardingChecklist(Base):
    __tablename__ = "onboarding_checklists"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    name = Column(String(200), nullable=False)
    description = Column(Text)

    applies_to_roles = Column(JSON)  # ["server", "cook", "manager"]

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="onboarding_checklists")
    tasks = relationship("OnboardingTask", back_populates="checklist")
    onboardings = relationship("EmployeeOnboarding", back_populates="checklist")


class OnboardingTask(Base):
    __tablename__ = "onboarding_tasks"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    checklist_id = Column(Integer, ForeignKey("onboarding_checklists.id"), nullable=False, index=True)

    title = Column(String(200), nullable=False)
    description = Column(Text)

    task_type = Column(String(20))  # document, training, form, acknowledgement

    # For document tasks
    document_url = Column(String(500))
    requires_signature = Column(Boolean, default=False)

    # For form tasks
    form_fields = Column(JSON)

    # For training
    training_module_id = Column(String(100))

    due_days = Column(Integer)  # Days from start to complete
    is_required = Column(Boolean, default=True)

    order = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    checklist = relationship("OnboardingChecklist", back_populates="tasks")
    completions = relationship("OnboardingTaskCompletion", back_populates="task")


class EmployeeOnboarding(Base):
    __tablename__ = "employee_onboardings"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    staff_id = Column(Integer, ForeignKey("staff_users.id"), nullable=False, index=True)
    checklist_id = Column(Integer, ForeignKey("onboarding_checklists.id"), nullable=False, index=True)

    start_date = Column(Date, nullable=False)
    target_completion_date = Column(Date)
    actual_completion_date = Column(Date)

    status = Column(String(20), default="in_progress", index=True)  # in_progress, completed, overdue

    progress_percentage = Column(Float, default=0)

    assigned_mentor = Column(Integer, ForeignKey("staff_users.id"))

    notes = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="employee_onboardings")
    staff = relationship("StaffUser", foreign_keys=[staff_id], backref="onboardings")
    checklist = relationship("OnboardingChecklist", back_populates="onboardings")
    mentor = relationship("StaffUser", foreign_keys=[assigned_mentor], backref="mentored_onboardings")
    task_completions = relationship("OnboardingTaskCompletion", back_populates="onboarding")


class OnboardingTaskCompletion(Base):
    __tablename__ = "onboarding_task_completions"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    onboarding_id = Column(Integer, ForeignKey("employee_onboardings.id"), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey("onboarding_tasks.id"), nullable=False, index=True)

    status = Column(String(20), default="pending", index=True)  # pending, in_progress, completed, skipped

    completed_at = Column(DateTime)
    completed_by = Column(Integer, ForeignKey("staff_users.id"))

    # For forms
    form_responses = Column(JSON)

    # For signatures
    signature_url = Column(String(500))
    signed_at = Column(DateTime)

    # For training
    score = Column(Float)
    passed = Column(Boolean)

    notes = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    onboarding = relationship("EmployeeOnboarding", back_populates="task_completions")
    task = relationship("OnboardingTask", back_populates="completions")
    completer = relationship("StaffUser", backref="completed_onboarding_tasks")


# 20. MENU PAIRING SUGGESTIONS
class MenuPairing(Base):
    __tablename__ = "menu_pairings"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    primary_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False, index=True)
    paired_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False, index=True)

    pairing_type = Column(String(20))  # food_drink, complementary, upsell

    # AI or manual
    source = Column(String(20), default="manual")  # manual, ai_generated, learned

    # Strength
    confidence_score = Column(Float, default=1.0)  # 0-1

    # Display
    pairing_reason = Column(Text)  # "Pairs well with the rich flavors"
    display_priority = Column(Integer, default=0)

    # Stats
    times_suggested = Column(Integer, default=0)
    times_accepted = Column(Integer, default=0)
    acceptance_rate = Column(Float)

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="menu_pairings")
    primary_item = relationship("MenuItem", foreign_keys=[primary_item_id], backref="pairings_as_primary")
    paired_item = relationship("MenuItem", foreign_keys=[paired_item_id], backref="pairings_as_paired")


# 21. KITCHEN SHEETS (Catering)
class KitchenSheet(Base):
    __tablename__ = "kitchen_sheets"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    catering_event_id = Column(Integer, ForeignKey("catering_events.id"), nullable=False, index=True)

    sheet_type = Column(String(20), nullable=False)  # prep, production, packing

    title = Column(String(200))

    # Content
    items = Column(JSON)  # List of items with quantities and instructions

    # Assignment
    assigned_station = Column(String(50))
    assigned_to = Column(Integer, ForeignKey("staff_users.id"), index=True)

    # Timeline
    prep_start_time = Column(DateTime)
    prep_end_time = Column(DateTime)

    # Status
    status = Column(String(20), default="pending", index=True)
    completed_at = Column(DateTime)

    notes = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="kitchen_sheets")
    catering_event = relationship("CateringEvent", back_populates="kitchen_sheets")
    assignee = relationship("StaffUser", backref="assigned_kitchen_sheets")


# 22. PRINTABLE LABELS
class LabelTemplate(Base):
    __tablename__ = "label_templates"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    name = Column(String(100), nullable=False)
    label_type = Column(String(20), nullable=False, index=True)  # food, container, ingredient, allergen

    # Dimensions
    width_mm = Column(Float)
    height_mm = Column(Float)

    # Template content
    template_content = Column(JSON)  # Layout definition

    # Fields
    available_fields = Column(JSON)  # ["item_name", "date", "allergens", "barcode"]

    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="label_templates")
    printed_labels = relationship("PrintedLabel", back_populates="template")


class PrintedLabel(Base):
    __tablename__ = "printed_labels"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    template_id = Column(Integer, ForeignKey("label_templates.id"), nullable=False, index=True)

    # Reference
    reference_type = Column(String(20), index=True)  # menu_item, catering, production_batch
    reference_id = Column(Integer, index=True)

    # Content
    label_data = Column(JSON, nullable=False)

    # Print info
    printed_at = Column(DateTime)
    printed_by = Column(Integer, ForeignKey("staff_users.id"))
    copies = Column(Integer, default=1)
    printer_id = Column(String(100))

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="printed_labels")
    template = relationship("LabelTemplate", back_populates="printed_labels")
    printer = relationship("StaffUser", backref="printed_labels")


# 23. THIRD-PARTY GIFT CARDS
class ThirdPartyGiftCardProvider(Base):
    __tablename__ = "third_party_gift_card_providers"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    provider_name = Column(String(100), nullable=False)  # square, shopify, etc.

    # API config
    api_endpoint = Column(String(500))
    api_key_encrypted = Column(Text)

    # Settings
    auto_validate = Column(Boolean, default=True)

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="third_party_gift_card_providers")
    redemptions = relationship("ThirdPartyGiftCardRedemption", back_populates="provider")


class ThirdPartyGiftCardRedemption(Base):
    __tablename__ = "third_party_gift_card_redemptions"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    provider_id = Column(Integer, ForeignKey("third_party_gift_card_providers.id"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), index=True)

    card_number = Column(String(100))  # Masked
    card_number_hash = Column(String(256), index=True)  # For lookup

    amount_redeemed = Column(Numeric(10, 2), nullable=False)
    remaining_balance = Column(Numeric(10, 2))

    # Provider response
    authorization_code = Column(String(100))
    provider_response = Column(JSON)

    redeemed_at = Column(DateTime, default=datetime.utcnow)
    redeemed_by = Column(Integer, ForeignKey("staff_users.id"))

    # Relationships
    venue = relationship("Venue", backref="third_party_gift_card_redemptions")
    provider = relationship("ThirdPartyGiftCardProvider", back_populates="redemptions")
    order = relationship("Order", backref="third_party_gift_card_redemptions")
    redeemer = relationship("StaffUser", backref="third_party_gift_card_redemptions")


# 24. TABLE TIME BLOCKING
class TableBlock(Base):
    __tablename__ = "table_blocks"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    table_id = Column(Integer, ForeignKey("tables.id"), nullable=False, index=True)

    block_type = Column(String(20), nullable=False)  # reservation, private_event, maintenance

    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)

    # Recurrence (for regular blocks)
    is_recurring = Column(Boolean, default=False)
    recurrence_pattern = Column(String(50))  # daily, weekly, etc.
    recurrence_end_date = Column(Date)

    # Reason
    reason = Column(Text)

    # Reference
    reservation_id = Column(Integer, ForeignKey("reservations.id"), index=True)
    event_id = Column(Integer, ForeignKey("catering_events.id"), index=True)

    created_by = Column(Integer, ForeignKey("staff_users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="table_blocks")
    table = relationship("Table", backref="blocks")
    reservation = relationship("Reservation", backref="table_blocks")
    catering_event = relationship("CateringEvent", backref="table_blocks")
    creator = relationship("StaffUser", backref="created_table_blocks")


# =====================================================
# ADVANCED PAYMENT MODELS
# =====================================================

# 25. CUSTOMER WALLETS
class CustomerWalletStatus(str, PyEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"


class CustomerWallet(Base):
    """Customer digital wallet for stored value payments"""
    __tablename__ = "customer_wallets"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)

    # Balance
    balance = Column(Numeric(10, 2), default=0, nullable=False)
    currency = Column(String(3), default="BGN", nullable=False)

    # Lifetime stats
    lifetime_loaded = Column(Numeric(10, 2), default=0, nullable=False)
    lifetime_spent = Column(Numeric(10, 2), default=0, nullable=False)

    # Auto-reload settings
    auto_reload_enabled = Column(Boolean, default=False)
    auto_reload_amount = Column(Numeric(10, 2), default=50)
    auto_reload_threshold = Column(Numeric(10, 2), default=10)
    auto_reload_payment_method_id = Column(String(100))  # Stored payment method reference

    # Status
    status = Column(String(20), default=CustomerWalletStatus.ACTIVE.value)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_used_at = Column(DateTime)

    # Relationships
    venue = relationship("Venue", backref="customer_wallets")
    customer = relationship("Customer", backref="wallet")
    transactions = relationship("CustomerWalletTransaction", back_populates="wallet")

    __table_args__ = (
        UniqueConstraint('venue_id', 'customer_id', name='uq_customer_wallet'),
        Index('ix_customer_wallet_venue_customer', 'venue_id', 'customer_id'),
    )


class CustomerWalletTransaction(Base):
    """Transaction history for customer wallets"""
    __tablename__ = "customer_wallet_transactions"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    wallet_id = Column(Integer, ForeignKey("customer_wallets.id"), nullable=False, index=True)

    # Transaction details
    transaction_type = Column(String(20), nullable=False)  # load, spend, refund, adjustment
    amount = Column(Numeric(10, 2), nullable=False)
    balance_after = Column(Numeric(10, 2), nullable=False)

    # Payment method for loads
    payment_method = Column(String(50))  # card, cash, bank_transfer

    # Order reference for spends
    order_id = Column(Integer, ForeignKey("orders.id"))

    # Additional info
    description = Column(String(255))
    reference_id = Column(String(100))  # External reference

    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("staff_users.id"))

    # Relationships
    wallet = relationship("CustomerWallet", back_populates="transactions")
    order = relationship("Order", backref="wallet_transactions")
    creator = relationship("StaffUser", backref="wallet_transactions_created")

    __table_args__ = (
        Index('ix_wallet_transactions_wallet', 'wallet_id', 'created_at'),
    )


# 26. CRYPTOCURRENCY PAYMENTS
class CryptoPaymentStatus(str, PyEnum):
    PENDING = "pending"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    EXPIRED = "expired"
    REFUNDED = "refunded"


# CryptoPayment is defined elsewhere - commented out to avoid duplicate
# class CryptoPayment(Base):
#     """Cryptocurrency payment records"""
#     __tablename__ = "crypto_payments"
#     __table_args__ = {'extend_existing': True}

#     id = Column(Integer, primary_key=True, index=True)
#     venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
#     order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)

#     # Crypto details
#     crypto_type = Column(String(10), nullable=False)  # btc, eth, usdt, etc.
#     amount_fiat = Column(Numeric(10, 2), nullable=False)
#     fiat_currency = Column(String(3), default="BGN")
#     amount_crypto = Column(Numeric(20, 10), nullable=False)
#     exchange_rate = Column(Numeric(20, 10), nullable=False)

#     # Payment address
#     wallet_address = Column(String(100), nullable=False)
#     payment_uri = Column(String(500))  # BIP21 URI for QR code

#     # Status
#     status = Column(String(20), default=CryptoPaymentStatus.PENDING.value)

#     # Blockchain info
#     tx_hash = Column(String(100), index=True)
#     confirmations = Column(Integer, default=0)
#     required_confirmations = Column(Integer, default=1)

#     # Expiration (crypto payments have time-limited exchange rates)
#     expires_at = Column(DateTime)

#     # Timestamps
#     created_at = Column(DateTime, default=datetime.utcnow)
#     confirmed_at = Column(DateTime)
#     updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

#     # Relationships
#     venue = relationship("Venue", backref="crypto_payments")
#     order = relationship("Order", backref="crypto_payments")

#     __table_args__ = (
#         Index('ix_crypto_payments_venue_order', 'venue_id', 'order_id'),
#         Index('ix_crypto_payments_status', 'status', 'expires_at'),
#     )


# 27. BUY NOW PAY LATER (BNPL)
class BNPLStatus(str, PyEnum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    DEFAULTED = "defaulted"
    CANCELLED = "cancelled"


class BNPLPlan(Base):
    """Buy Now Pay Later installment plans"""
    __tablename__ = "bnpl_plans"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)

    # Plan details
    total_amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="BGN")
    installments = Column(Integer, nullable=False, default=3)
    installment_amount = Column(Numeric(10, 2), nullable=False)

    # Provider info
    provider = Column(String(50), default="internal")  # internal, paynetics, klarna
    provider_plan_id = Column(String(100))  # External reference

    # Status
    status = Column(String(20), default=BNPLStatus.PENDING.value)
    paid_installments = Column(Integer, default=0)
    total_paid = Column(Numeric(10, 2), default=0)

    # Schedule
    first_payment_date = Column(Date)
    next_payment_date = Column(Date)

    # Late payment tracking
    late_fees = Column(Numeric(10, 2), default=0)
    days_overdue = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)

    # Relationships
    venue = relationship("Venue", backref="bnpl_plans")
    order = relationship("Order", backref="bnpl_plans")
    customer = relationship("Customer", backref="bnpl_plans")
    installments = relationship("BNPLInstallment", back_populates="plan")

    __table_args__ = (
        Index('ix_bnpl_plans_venue_customer', 'venue_id', 'customer_id'),
        Index('ix_bnpl_plans_status', 'status', 'next_payment_date'),
    )


class BNPLInstallment(Base):
    """Individual BNPL installment payments"""
    __tablename__ = "bnpl_installments"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("bnpl_plans.id"), nullable=False, index=True)

    # Installment info
    installment_number = Column(Integer, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    due_date = Column(Date, nullable=False)

    # Payment
    status = Column(String(20), default="pending")  # pending, paid, overdue, failed
    paid_at = Column(DateTime)
    paid_amount = Column(Numeric(10, 2))
    payment_method = Column(String(50))

    # Late fees
    late_fee = Column(Numeric(10, 2), default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    plan = relationship("BNPLPlan", back_populates="installments")

    __table_args__ = (
        Index('ix_bnpl_installments_plan', 'plan_id', 'installment_number'),
        Index('ix_bnpl_installments_due', 'due_date', 'status'),
    )


# CURRENCY EXCHANGE RATES (for cryptocurrency and multi-currency support)
class CurrencyExchangeRate(Base):
    """Exchange rates for cryptocurrencies and fiat currencies"""
    __tablename__ = "currency_exchange_rates"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)

    # Currency info
    from_currency = Column(String(10), nullable=False)  # BGN, USD, EUR
    to_currency = Column(String(10), nullable=False)    # BTC, ETH, USDT, USD, EUR

    # Exchange rate
    rate = Column(Numeric(20, 10), nullable=False)  # High precision for crypto

    # Source info
    source = Column(String(50))  # coingecko, coinbase, exchangerate-api, manual

    # Validity
    valid_from = Column(DateTime, nullable=False, default=datetime.utcnow)
    valid_until = Column(DateTime)  # Optional expiry

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('ix_exchange_rate_lookup', 'from_currency', 'to_currency', 'is_active'),
        Index('ix_exchange_rate_valid', 'valid_from', 'valid_until'),
    )


# Additional indexes
Index('ix_sms_campaigns_venue_status', SMSCampaign.venue_id, SMSCampaign.status)
Index('ix_catering_events_venue_date', CateringEvent.venue_id, CateringEvent.event_date)
Index('ix_menu_item_reviews_item', MenuItemReview.menu_item_id, MenuItemReview.status)
Index('ix_customer_rfm_venue_customer', CustomerRFMScore.venue_id, CustomerRFMScore.customer_id)
Index('ix_ingredient_price_history_item_date', IngredientPriceHistory.stock_item_id, IngredientPriceHistory.recorded_date)
Index('ix_table_blocks_table_time', TableBlock.table_id, TableBlock.start_time, TableBlock.end_time)


# =====================================================
# KDS (Kitchen Display System) MODELS
# =====================================================

class KDSStationType(str, PyEnum):
    KITCHEN = "kitchen"
    BAR = "bar"
    GRILL = "grill"
    FRYER = "fryer"
    SALAD = "salad"
    DESSERT = "dessert"
    EXPO = "expo"
    PREP = "prep"


class KDSTicketStatus(str, PyEnum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    READY = "ready"
    BUMPED = "bumped"
    RECALLED = "recalled"
    VOIDED = "voided"


class KDSStation(Base):
    """Kitchen Display System Station configuration"""
    __tablename__ = "kds_stations"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    station_code = Column(String(50), nullable=False)  # e.g., "KITCHEN-1", "BAR-1"
    name = Column(String(100), nullable=False)
    station_type = Column(String(20), nullable=False)  # KDSStationType values

    # Categories this station handles
    categories = Column(JSON, default=list)  # ["appetizers", "mains", "sides"]

    # Performance config
    avg_cook_time_minutes = Column(Integer, default=10)
    max_capacity = Column(Integer, default=15)

    # Status
    is_active = Column(Boolean, default=True)
    current_load = Column(Integer, default=0)

    # Display settings
    display_color = Column(String(20), default="#3B82F6")  # Blue
    alert_threshold_minutes = Column(Integer, default=15)
    display_order = Column(Integer, default=1)
    printer_id = Column(String(100), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="kds_stations")
    tickets = relationship("KDSTicket", back_populates="station")

    __table_args__ = (
        UniqueConstraint('venue_id', 'station_code', name='uq_kds_station_venue_code'),
        Index('ix_kds_station_venue_active', 'venue_id', 'is_active'),
    )


class KDSTicket(Base):
    """Kitchen Display System Ticket (prep ticket for orders)"""
    __tablename__ = "kds_tickets"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    station_id = Column(Integer, ForeignKey("kds_stations.id"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)

    ticket_code = Column(String(50), nullable=False, unique=True)  # e.g., "TKT-A1B2C3D4"

    # Items on this ticket (may be subset of order items for specific station)
    items = Column(JSON, nullable=False)  # [{id, name, quantity, mods, notes}]
    item_count = Column(Integer, default=0)

    # Order info for display
    table_number = Column(String(20))
    server_name = Column(String(100))

    # Status
    status = Column(String(20), default="new", index=True)  # KDSTicketStatus values
    is_rush = Column(Boolean, default=False)
    priority = Column(Integer, default=1)  # 1=normal, 2=rush, 3=recalled

    # Course info
    course = Column(String(20), default="main")  # appetizer, main, dessert
    fire_sequence = Column(Integer)  # Order to fire

    # Notes
    notes = Column(Text)
    recall_reason = Column(Text)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime)  # When prep started
    fired_at = Column(DateTime)  # When course was fired
    bumped_at = Column(DateTime)  # When completed
    recalled_at = Column(DateTime)

    # Metrics
    cook_time_seconds = Column(Integer)  # Actual cook time

    # Staff tracking
    started_by = Column(Integer, ForeignKey("staff_users.id"))
    bumped_by = Column(Integer, ForeignKey("staff_users.id"))

    # Relationships
    venue = relationship("Venue", backref="kds_tickets")
    station = relationship("KDSStation", back_populates="tickets")
    order = relationship("Order", backref="kds_tickets")
    starter = relationship("StaffUser", foreign_keys=[started_by], backref="started_kds_tickets")
    bumper = relationship("StaffUser", foreign_keys=[bumped_by], backref="bumped_kds_tickets")

    __table_args__ = (
        Index('ix_kds_ticket_station_status', 'station_id', 'status'),
        Index('ix_kds_ticket_venue_created', 'venue_id', 'created_at'),
        Index('ix_kds_ticket_order', 'order_id'),
    )


class KDSBumpHistory(Base):
    """History of ticket bumps for analytics"""
    __tablename__ = "kds_bump_history"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    ticket_id = Column(Integer, ForeignKey("kds_tickets.id"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    station_id = Column(Integer, ForeignKey("kds_stations.id"), nullable=False, index=True)

    cook_time_seconds = Column(Integer, nullable=False)
    item_count = Column(Integer, default=1)
    was_rush = Column(Boolean, default=False)
    was_recalled = Column(Boolean, default=False)

    bumped_at = Column(DateTime, default=datetime.utcnow, index=True)
    bumped_by = Column(Integer, ForeignKey("staff_users.id"))

    # Relationships
    venue = relationship("Venue", backref="kds_bump_history")
    ticket = relationship("KDSTicket", backref="bump_history")
    order = relationship("Order", backref="kds_bump_history")
    station = relationship("KDSStation", backref="bump_history")
    staff = relationship("StaffUser", backref="kds_bumps")

    __table_args__ = (
        Index('ix_kds_bump_venue_date', 'venue_id', 'bumped_at'),
        Index('ix_kds_bump_station_date', 'station_id', 'bumped_at'),
    )


Index('ix_kds_tickets_lookup', KDSTicket.venue_id, KDSTicket.station_id, KDSTicket.status)


# =====================================================
# ADDITIONAL MISSING MODELS
# =====================================================

class PromotionRedemption(Base):
    """Track promotion/discount redemptions by staff for risk analysis"""
    __tablename__ = "promotion_redemptions"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    promotion_id = Column(Integer, ForeignKey("promotions.id"), nullable=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    staff_user_id = Column(Integer, ForeignKey("staff_users.id"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)

    # Discount details
    discount_type = Column(String(50), nullable=False)  # percentage, fixed, comp, manager_override
    discount_amount = Column(Numeric(10, 2), nullable=False)
    discount_percentage = Column(Float, nullable=True)
    original_amount = Column(Numeric(10, 2), nullable=True)
    reason = Column(Text, nullable=True)

    # Authorization
    authorized_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    requires_authorization = Column(Boolean, default=False)

    redeemed_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    venue = relationship("Venue", backref="promotion_redemptions")
    promotion = relationship("Promotion", backref="redemptions")
    order = relationship("Order", backref="promotion_redemptions")
    staff_user = relationship("StaffUser", foreign_keys=[staff_user_id], backref="applied_discounts")
    authorizer = relationship("StaffUser", foreign_keys=[authorized_by], backref="authorized_discounts")

    __table_args__ = (
        Index('ix_promo_redemption_staff_date', 'staff_user_id', 'redeemed_at'),
        Index('ix_promo_redemption_venue_date', 'venue_id', 'redeemed_at'),
    )


class SMSTemplate(Base):
    """SMS message templates for various notifications"""
    __tablename__ = "sms_templates"
    __table_args__ = (
        Index('ix_sms_template_venue_type', 'venue_id', 'template_type'),
        {'extend_existing': True},
    )

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=True, index=True)

    name = Column(String(100), nullable=False)
    template_type = Column(String(50), nullable=True)  # reservation, waitlist, order, marketing, custom
    content = Column(Text, nullable=True)  # Template content (used by v7_endpoints)
    message_template = Column(Text, nullable=True)  # Template with {{placeholders}}
    category = Column(String(100), nullable=True)  # general, marketing, transactional, etc.

    # System vs custom
    is_system_template = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    # Multilingual support
    language = Column(String(5), default="en")

    # Character count tracking
    character_count = Column(Integer, default=0)
    segment_count = Column(Integer, default=1)  # SMS segments needed

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)

    # Relationships
    venue = relationship("Venue", backref="mf_sms_templates")


class CateringPackage(Base):
    """Pre-configured catering packages"""
    __tablename__ = "catering_packages"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)  # breakfast, lunch, dinner, cocktail, etc.

    # Pricing
    price_per_person = Column(Numeric(10, 2), nullable=False)
    min_guests = Column(Integer, default=10)
    max_guests = Column(Integer, nullable=True)

    # Package contents
    included_items = Column(JSON, nullable=True)  # [{item_id, quantity_per_person, category}]
    optional_addons = Column(JSON, nullable=True)  # [{item_id, price}]

    # Customization
    allow_substitutions = Column(Boolean, default=True)
    dietary_options = Column(JSON, nullable=True)  # vegetarian, vegan, gluten-free variants

    # Availability
    is_active = Column(Boolean, default=True)
    available_days = Column(JSON, nullable=True)  # ["monday", "tuesday", ...]
    advance_notice_hours = Column(Integer, default=48)

    # Media
    image_url = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="catering_packages")

    __table_args__ = (
        Index('ix_catering_package_venue_active', 'venue_id', 'is_active'),
    )


class ShiftTradingConfig(Base):
    """Configuration for shift trading feature"""
    __tablename__ = "shift_trading_configs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, unique=True, index=True)

    # Enable/disable
    is_enabled = Column(Boolean, default=True)

    # Approval settings
    require_manager_approval = Column(Boolean, default=True)
    auto_approve_same_role = Column(Boolean, default=False)
    auto_approve_certified_only = Column(Boolean, default=True)

    # Time constraints
    min_notice_hours = Column(Integer, default=24)  # Minimum hours before shift to request trade
    max_advance_days = Column(Integer, default=14)  # Maximum days in advance to trade

    # Eligibility rules
    allow_cross_department = Column(Boolean, default=False)
    require_equal_hours = Column(Boolean, default=False)
    max_trades_per_week = Column(Integer, default=2)
    max_trades_per_month = Column(Integer, default=8)

    # Notifications
    notify_manager_on_request = Column(Boolean, default=True)
    notify_staff_on_approval = Column(Boolean, default=True)

    # Blackout dates (no trading allowed)
    blackout_dates = Column(JSON, nullable=True)  # ["2024-12-25", "2024-12-31"]

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="shift_trading_config", uselist=False)


class TimeOffRequestStatus(str, PyEnum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    CANCELLED = "cancelled"


# TimeOffRequest is defined elsewhere - commented out to avoid duplicate
# class TimeOffRequest(Base):
#     """Staff time off / leave requests"""
#     __tablename__ = "time_off_requests"
#     __table_args__ = {'extend_existing': True}

#     id = Column(Integer, primary_key=True, index=True)
#     venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
#     staff_user_id = Column(Integer, ForeignKey("staff_users.id"), nullable=False, index=True)

#     # Request details
#     request_type = Column(String(50), nullable=False)  # vacation, sick, personal, bereavement, other
#     start_date = Column(Date, nullable=False)
#     end_date = Column(Date, nullable=False)
#     start_time = Column(Time, nullable=True)  # For partial day requests
#     end_time = Column(Time, nullable=True)

#     # Hours calculation
#     total_hours = Column(Float, nullable=True)
#     is_paid = Column(Boolean, default=True)

#     # Reason
#     reason = Column(Text, nullable=True)
#     notes = Column(Text, nullable=True)

#     # Status
#     status = Column(String(20), default=TimeOffRequestStatus.PENDING.value, index=True)

#     # Approval
#     reviewed_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
#     reviewed_at = Column(DateTime, nullable=True)
#     denial_reason = Column(Text, nullable=True)

#     # Attachments (e.g., doctor's note)
#     attachments = Column(JSON, nullable=True)

#     created_at = Column(DateTime, default=datetime.utcnow)
#     updated_at = Column(DateTime, onupdate=datetime.utcnow)

#     # Relationships
#     venue = relationship("Venue", backref="mf_time_off_requests")
#     staff_user = relationship("StaffUser", foreign_keys=[staff_user_id], backref="mf_time_off_requests")
#     reviewer = relationship("StaffUser", foreign_keys=[reviewed_by], backref="reviewed_time_off_requests")

#     __table_args__ = (
#         Index('ix_time_off_staff_date', 'staff_user_id', 'start_date'),
#         Index('ix_time_off_venue_status', 'venue_id', 'status'),
#         {'extend_existing': True},
#     )


# =====================================================
# WAITLIST & QUEUE MANAGEMENT
# =====================================================

class WaitlistStatus(str, PyEnum):
    WAITING = "waiting"
    NOTIFIED = "notified"
    SEATED = "seated"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class WaitlistEntry(Base):
    """Unified waitlist entry model for queue management - matches database schema"""
    __tablename__ = "waitlist_entries"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)
    entry_code = Column(String(50), nullable=False, unique=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)

    # Guest information (column names match database schema)
    customer_name = Column(String(200), nullable=False)
    customer_phone = Column(String(50), nullable=False)
    party_size = Column(Integer, nullable=False)

    # Wait time tracking
    quoted_wait_minutes = Column(Integer, nullable=False)
    actual_wait_minutes = Column(Integer, nullable=True)
    check_in_time = Column(DateTime, default=datetime.utcnow)

    # Status
    status = Column(String(20), default=WaitlistStatus.WAITING.value)

    # Preferences
    seating_preference = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)

    # Priority
    priority = Column(Integer, default=0)
    has_reservation = Column(Boolean, default=False)

    # Notifications
    notified_at = Column(DateTime, nullable=True)

    # Seating
    table_id = Column(Integer, ForeignKey("tables.id"), nullable=True)
    seated_at = Column(DateTime, nullable=True)
    pager_number = Column(Integer, nullable=True)

    # Audit
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    venue = relationship("Venue")
    table = relationship("Table")


# =====================================================
# RESERVATION PLATFORM INTEGRATIONS
# =====================================================

class ReservationPlatformType(str, PyEnum):
    GOOGLE = "google"
    TRIPADVISOR = "tripadvisor"
    THEFORK = "thefork"
    OPENTABLE = "opentable"
    RESY = "resy"


class ReservationPlatformConnection(Base):
    """Store connections to external reservation platforms"""
    __tablename__ = "reservation_platform_connections"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    platform = Column(String(50), nullable=False, index=True)

    # Connection credentials (encrypted in production)
    api_key = Column(String(500), nullable=True)
    api_secret = Column(String(500), nullable=True)
    venue_id_external = Column(String(100), nullable=True)  # ID on external platform
    webhook_secret = Column(String(200), nullable=True)

    # Status
    is_connected = Column(Boolean, default=False)
    sync_enabled = Column(Boolean, default=True)
    auto_confirm = Column(Boolean, default=False)

    # Sync tracking
    last_sync_at = Column(DateTime, nullable=True)
    last_sync_status = Column(String(50), nullable=True)  # success, error
    last_sync_error = Column(Text, nullable=True)
    sync_errors_count = Column(Integer, default=0)

    # Timestamps
    connected_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="reservation_platform_connections")

    __table_args__ = (
        Index('ix_platform_venue', 'venue_id', 'platform'),
        UniqueConstraint('venue_id', 'platform', name='uq_venue_platform'),
    )


class ExternalReservationStatus(str, PyEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"
    COMPLETED = "completed"


class ExternalReservation(Base):
    """Track reservations from external platforms"""
    __tablename__ = "external_reservations"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    platform = Column(String(50), nullable=False, index=True)

    # External reference
    external_id = Column(String(100), nullable=False, index=True)
    external_confirmation_code = Column(String(100), nullable=True)

    # Link to local reservation (once synced)
    local_reservation_id = Column(Integer, ForeignKey("reservations.id"), nullable=True)

    # Guest info
    guest_name = Column(String(255), nullable=False)
    guest_phone = Column(String(50), nullable=True)
    guest_email = Column(String(255), nullable=True)
    party_size = Column(Integer, nullable=False)

    # Reservation details
    reservation_date = Column(DateTime, nullable=False, index=True)
    duration_minutes = Column(Integer, default=90)

    # Status
    status = Column(String(50), default=ExternalReservationStatus.PENDING.value, index=True)
    confirmed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    cancellation_reason = Column(Text, nullable=True)

    # Special requests
    notes = Column(Text, nullable=True)
    seating_preference = Column(String(100), nullable=True)
    special_occasion = Column(String(100), nullable=True)

    # Sync tracking
    synced_to_local = Column(Boolean, default=False)
    synced_at = Column(DateTime, nullable=True)
    sync_error = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="external_reservations")
    local_reservation = relationship("Reservation", backref="external_source")

    __table_args__ = (
        Index('ix_external_res_venue_date', 'venue_id', 'reservation_date'),
        Index('ix_external_res_platform_id', 'platform', 'external_id'),
        UniqueConstraint('platform', 'external_id', name='uq_platform_external_id'),
    )


class PlatformWebhookLog(Base):
    """Log incoming webhooks from platforms"""
    __tablename__ = "platform_webhook_logs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    platform = Column(String(50), nullable=False, index=True)

    # Webhook details
    event_type = Column(String(100), nullable=True)
    payload = Column(JSON, nullable=True)
    headers = Column(JSON, nullable=True)

    # Processing status
    processed = Column(Boolean, default=False)
    processed_at = Column(DateTime, nullable=True)
    processing_error = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="webhook_logs")

    __table_args__ = (
        Index('ix_webhook_venue_platform', 'venue_id', 'platform'),
    )


class ExternalAvailabilityBlock(Base):
    """Track availability blocks published to external platforms"""
    __tablename__ = "external_availability_blocks"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    # Block details
    block_date = Column(Date, nullable=False, index=True)
    time_slots = Column(JSON, nullable=False)  # List of blocked time slots
    reason = Column(Text, nullable=True)

    # Sync status
    synced_to_platforms = Column(JSON, nullable=True)  # List of platforms synced to
    synced_at = Column(DateTime, nullable=True)

    created_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="availability_blocks")
    created_by_user = relationship("StaffUser", backref="availability_blocks_created")


# =====================================================
# V7 TIER 3 ADDITIONAL MODELS
# =====================================================

class GuestbookVisit(Base):
    """Guestbook visit tracking"""
    __tablename__ = "guestbook_visits"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    guest_id = Column(Integer, ForeignKey("guestbook_entries.id"), nullable=False)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    visit_date = Column(DateTime, default=datetime.utcnow)
    party_size = Column(Integer, default=1)
    total_spent = Column(Numeric(10, 2), default=0)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    guest = relationship("GuestbookEntry", backref="visits")
    venue = relationship("Venue", backref="guestbook_visits")


class ChargebackCase(Base):
    """Chargeback case management"""
    __tablename__ = "chargeback_cases"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)

    case_number = Column(String(100), unique=True, nullable=False)
    reason = Column(String(100), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="BGN")

    status = Column(String(50), default="pending")
    deadline = Column(DateTime, nullable=True)

    processor = Column(String(50), nullable=True)
    processor_case_id = Column(String(100), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    venue = relationship("Venue", backref="chargeback_cases")
    order = relationship("Order", backref="chargeback_cases")


class ChargebackEvidence(Base):
    """Evidence for chargeback disputes"""
    __tablename__ = "chargeback_evidence"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("chargeback_cases.id"), nullable=False)

    evidence_type = Column(String(50), nullable=False)
    file_url = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)

    uploaded_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("ChargebackCase", backref="evidence")


class TaxConfiguration(Base):
    """Tax configuration for venue"""
    __tablename__ = "tax_configurations"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    name = Column(String(100), nullable=False)
    rate = Column(Float, nullable=False)
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    applies_to = Column(JSON, nullable=True)
    excluded_items = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    venue = relationship("Venue", backref="tax_configurations")


class TaxSummary(Base):
    """Tax summary for reporting"""
    __tablename__ = "tax_summaries"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)

    gross_sales = Column(Numeric(12, 2), default=0)
    net_sales = Column(Numeric(12, 2), default=0)
    total_tax = Column(Numeric(12, 2), default=0)
    tax_breakdown = Column(JSON, nullable=True)

    generated_at = Column(DateTime, default=datetime.utcnow)

    venue = relationship("Venue", backref="tax_summaries")

    __table_args__ = (
        Index('ix_tax_summary_period', 'venue_id', 'period_start', 'period_end'),
    )


class MenuPairingRule(Base):
    """Rules for menu item pairings"""
    __tablename__ = "menu_pairing_rules"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    pairing_id = Column(Integer, ForeignKey("menu_pairings.id"), nullable=False)

    rule_type = Column(String(50), nullable=False)
    priority = Column(Integer, default=0)
    discount_percent = Column(Float, nullable=True)
    discount_amount = Column(Numeric(10, 2), nullable=True)

    conditions = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    pairing = relationship("MenuPairing", backref="rules")


class ThirdPartyGiftCardConfig(Base):
    """Configuration for third-party gift card providers"""
    __tablename__ = "third_party_gift_card_configs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    provider_name = Column(String(100), nullable=False)
    api_key = Column(String(500), nullable=True)
    api_secret = Column(String(500), nullable=True)

    is_active = Column(Boolean, default=True)
    settings = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    venue = relationship("Venue", backref="gift_card_configs")


class ThirdPartyGiftCardTransaction(Base):
    """Transactions for third-party gift cards"""
    __tablename__ = "third_party_gift_card_transactions"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    config_id = Column(Integer, ForeignKey("third_party_gift_card_configs.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)

    card_number = Column(String(100), nullable=False)
    transaction_type = Column(String(20), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    balance_after = Column(Numeric(10, 2), nullable=True)

    external_transaction_id = Column(String(100), nullable=True)
    status = Column(String(20), default="pending")

    created_at = Column(DateTime, default=datetime.utcnow)

    config = relationship("ThirdPartyGiftCardConfig", backref="transactions")
    order = relationship("Order", backref="third_party_gift_card_transactions")

"""Marketing Automation models - SpotOn style."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from app.db.base import Base


class CampaignStatus(str, Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CampaignType(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    FACEBOOK = "facebook"
    GOOGLE = "google"
    MULTI_CHANNEL = "multi_channel"


class TriggerType(str, Enum):
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    BIRTHDAY = "birthday"
    ANNIVERSARY = "anniversary"
    WIN_BACK = "win_back"  # Lapsed customer
    LOYALTY_MILESTONE = "loyalty_milestone"
    FIRST_VISIT = "first_visit"
    POST_VISIT = "post_visit"


class MarketingCampaign(Base):
    """Marketing campaign configuration."""
    __tablename__ = "marketing_campaigns"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Campaign type and status
    campaign_type = Column(SQLEnum(CampaignType), default=CampaignType.EMAIL)
    status = Column(SQLEnum(CampaignStatus), default=CampaignStatus.DRAFT)
    trigger_type = Column(SQLEnum(TriggerType), default=TriggerType.MANUAL)

    # Scheduling
    scheduled_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)

    # Content (AI-generated or manual)
    subject_line = Column(String(500), nullable=True)
    content_html = Column(Text, nullable=True)
    content_text = Column(Text, nullable=True)
    ai_generated = Column(Boolean, default=False)

    # Targeting
    target_segment = Column(String(100), nullable=True)  # all, vip, lapsed, new, etc.
    target_criteria = Column(JSON, nullable=True)  # Advanced targeting rules
    exclude_recent_contacts = Column(Boolean, default=True)
    exclude_days = Column(Integer, default=7)  # Don't contact if contacted in X days

    # Offer details
    offer_type = Column(String(50), nullable=True)  # discount_percent, discount_amount, free_item
    offer_value = Column(Float, nullable=True)
    offer_code = Column(String(50), nullable=True)
    offer_expires_at = Column(DateTime, nullable=True)

    # Performance metrics
    total_sent = Column(Integer, default=0)
    total_delivered = Column(Integer, default=0)
    total_opened = Column(Integer, default=0)
    total_clicked = Column(Integer, default=0)
    total_converted = Column(Integer, default=0)
    total_revenue = Column(Float, default=0.0)
    total_unsubscribed = Column(Integer, default=0)

    # Cost tracking
    campaign_cost = Column(Float, default=0.0)
    roi = Column(Float, nullable=True)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    recipients = relationship("CampaignRecipient", back_populates="campaign", cascade="all, delete-orphan")


class CampaignRecipient(Base):
    """Individual recipient tracking for campaigns."""
    __tablename__ = "campaign_recipients"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("marketing_campaigns.id"), nullable=False)
    customer_id = Column(Integer, nullable=True)  # Reference to customer

    # Contact info
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)

    # Delivery status
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    opened_at = Column(DateTime, nullable=True)
    clicked_at = Column(DateTime, nullable=True)
    converted_at = Column(DateTime, nullable=True)
    unsubscribed_at = Column(DateTime, nullable=True)

    # Conversion tracking
    conversion_order_id = Column(Integer, nullable=True)
    conversion_amount = Column(Float, nullable=True)

    # Error tracking
    error_message = Column(Text, nullable=True)

    # Relationships
    campaign = relationship("MarketingCampaign", back_populates="recipients")


class CustomerSegment(Base):
    """Customer segmentation for targeting."""
    __tablename__ = "customer_segments"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Segment rules (JSON criteria)
    criteria = Column(JSON, nullable=True)
    # Example: {"min_visits": 5, "min_spend": 100, "last_visit_days": 30}

    # Calculated stats
    customer_count = Column(Integer, default=0)
    avg_spend = Column(Float, nullable=True)
    total_revenue = Column(Float, nullable=True)
    last_calculated_at = Column(DateTime, nullable=True)

    is_dynamic = Column(Boolean, default=True)  # Auto-update membership
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class AutomatedTrigger(Base):
    """Automated marketing triggers."""
    __tablename__ = "automated_triggers"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    trigger_type = Column(SQLEnum(TriggerType), nullable=False)

    # Trigger conditions
    days_threshold = Column(Integer, nullable=True)  # e.g., 30 days for win-back
    amount_threshold = Column(Float, nullable=True)  # e.g., $100 for loyalty milestone

    # Action
    campaign_template_id = Column(Integer, ForeignKey("marketing_campaigns.id"), nullable=True)
    reward_points = Column(Integer, nullable=True)
    discount_percent = Column(Float, nullable=True)
    discount_amount = Column(Float, nullable=True)

    # Timing
    send_time = Column(String(10), nullable=True)  # "09:00" - time to send
    send_days_before = Column(Integer, default=0)  # For birthday: send X days before

    is_active = Column(Boolean, default=True)
    total_triggered = Column(Integer, default=0)
    total_converted = Column(Integer, default=0)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class MenuRecommendation(Base):
    """AI-powered menu recommendations - 'Picked for You' style."""
    __tablename__ = "menu_recommendations"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, nullable=True)
    session_id = Column(String(100), nullable=True)  # For anonymous users

    # Context signals
    day_of_week = Column(Integer, nullable=True)  # 0-6
    hour_of_day = Column(Integer, nullable=True)  # 0-23
    is_weekend = Column(Boolean, default=False)

    # Recommendations (product IDs and scores)
    recommended_items = Column(JSON, nullable=True)
    # [{"product_id": 1, "score": 0.95, "reason": "frequently_ordered"}]

    # Performance
    items_shown = Column(JSON, nullable=True)  # Product IDs shown to user
    items_ordered = Column(JSON, nullable=True)  # Product IDs actually ordered
    conversion_rate = Column(Float, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class LoyaltyProgram(Base):
    """Loyalty program configuration."""
    __tablename__ = "loyalty_programs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)

    # Program type
    program_type = Column(String(50), default="points")  # points, visits, spend
    points_per_dollar = Column(Float, default=1.0)
    points_per_visit = Column(Integer, default=10)

    # Redemption
    points_to_dollar = Column(Float, default=0.01)  # 100 points = $1
    min_redemption = Column(Integer, default=100)

    # Tiers
    tiers = Column(JSON, nullable=True)
    # [{"name": "Bronze", "min_points": 0}, {"name": "Silver", "min_points": 500}]

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class CustomerLoyalty(Base):
    """Customer loyalty status and points."""
    __tablename__ = "customer_loyalty"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, nullable=False, unique=True)
    program_id = Column(Integer, ForeignKey("loyalty_programs.id"), nullable=True)

    # Points
    current_points = Column(Integer, default=0)
    lifetime_points = Column(Integer, default=0)
    redeemed_points = Column(Integer, default=0)

    # Visits
    total_visits = Column(Integer, default=0)
    total_spend = Column(Float, default=0.0)

    # Tier
    current_tier = Column(String(50), nullable=True)

    # Dates
    first_visit_at = Column(DateTime, nullable=True)
    last_visit_at = Column(DateTime, nullable=True)
    birthday = Column(DateTime, nullable=True)
    anniversary = Column(DateTime, nullable=True)  # Signup anniversary

    # Preferences
    favorite_items = Column(JSON, nullable=True)  # Product IDs
    dietary_preferences = Column(JSON, nullable=True)
    communication_preferences = Column(JSON, nullable=True)  # email, sms, push

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

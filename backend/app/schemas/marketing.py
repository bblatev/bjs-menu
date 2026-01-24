"""Marketing Automation schemas - SpotOn style."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, EmailStr

from app.models.marketing import CampaignStatus, CampaignType, TriggerType


# Marketing Campaigns

class CampaignBase(BaseModel):
    """Base campaign schema."""
    name: str
    campaign_type: CampaignType
    subject_line: Optional[str] = None
    content_text: Optional[str] = None
    content_html: Optional[str] = None
    target_segment: Optional[str] = None
    scheduled_at: Optional[datetime] = None


class CampaignCreate(CampaignBase):
    """Create campaign schema."""
    pass


class CampaignUpdate(BaseModel):
    """Update campaign schema."""
    name: Optional[str] = None
    subject_line: Optional[str] = None
    content_text: Optional[str] = None
    content_html: Optional[str] = None
    target_segment: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    status: Optional[CampaignStatus] = None


class CampaignResponse(CampaignBase):
    """Campaign response schema."""
    id: int
    status: CampaignStatus
    trigger_type: Optional[TriggerType] = None
    description: Optional[str] = None
    total_sent: int = 0
    total_delivered: int = 0
    total_opened: int = 0
    total_clicked: int = 0
    total_converted: int = 0
    total_unsubscribed: int = 0
    total_revenue: float = 0.0
    campaign_cost: float = 0.0
    roi: Optional[float] = None
    ai_generated: bool = False
    created_at: datetime
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CampaignStats(BaseModel):
    """Campaign statistics."""
    campaign_id: int
    total_sent: int
    total_delivered: int
    total_opened: int
    open_rate: float
    total_clicked: int
    click_rate: float
    total_unsubscribed: int
    total_revenue: float
    roi: Optional[float] = None


# Campaign Recipients

class CampaignRecipientResponse(BaseModel):
    """Campaign recipient response."""
    id: int
    campaign_id: int
    customer_id: int
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    sent_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    clicked_at: Optional[datetime] = None
    converted: bool = False
    conversion_amount: Optional[Decimal] = None

    model_config = {"from_attributes": True}


# Customer Segments

class SegmentBase(BaseModel):
    """Base segment schema."""
    name: str
    description: Optional[str] = None
    criteria: Dict[str, Any] = Field(default_factory=dict)
    is_dynamic: bool = True


class SegmentCreate(SegmentBase):
    """Create segment schema."""
    pass


class SegmentUpdate(BaseModel):
    """Update segment schema."""
    name: Optional[str] = None
    description: Optional[str] = None
    criteria: Optional[Dict[str, Any]] = None
    is_dynamic: Optional[bool] = None


class SegmentResponse(SegmentBase):
    """Segment response schema."""
    id: int
    customer_count: int = 0
    avg_spend: Optional[float] = None
    total_revenue: Optional[float] = None
    is_active: bool = True
    created_at: datetime
    last_calculated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SegmentPreview(BaseModel):
    """Preview of segment matching."""
    segment_id: Optional[int] = None
    criteria: Dict[str, Any]
    matching_count: int
    sample_customers: List[Dict[str, Any]]


# Automated Triggers

class TriggerBase(BaseModel):
    """Base trigger schema."""
    name: str
    trigger_type: TriggerType
    days_threshold: Optional[int] = None
    amount_threshold: Optional[float] = None
    campaign_template_id: Optional[int] = None
    reward_points: Optional[int] = None
    discount_percent: Optional[float] = None
    discount_amount: Optional[float] = None
    send_time: Optional[str] = None
    send_days_before: int = 0
    is_active: bool = True


class TriggerCreate(TriggerBase):
    """Create trigger schema."""
    pass


class TriggerUpdate(BaseModel):
    """Update trigger schema."""
    name: Optional[str] = None
    days_threshold: Optional[int] = None
    amount_threshold: Optional[float] = None
    reward_points: Optional[int] = None
    discount_percent: Optional[float] = None
    discount_amount: Optional[float] = None
    send_time: Optional[str] = None
    is_active: Optional[bool] = None


class TriggerResponse(TriggerBase):
    """Trigger response schema."""
    id: int
    total_triggered: int = 0
    total_converted: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


# Menu Recommendations

class MenuRecommendationResponse(BaseModel):
    """Menu recommendation for a customer."""
    id: int
    customer_id: Optional[int] = None
    session_id: Optional[str] = None
    day_of_week: Optional[int] = None
    hour_of_day: Optional[int] = None
    is_weekend: bool = False
    recommended_items: Optional[List[Dict[str, Any]]] = None
    items_shown: Optional[List[int]] = None
    items_ordered: Optional[List[int]] = None
    conversion_rate: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CustomerRecommendations(BaseModel):
    """All recommendations for a customer."""
    customer_id: int
    recommendations: List[MenuRecommendationResponse]
    generated_at: datetime


# Loyalty Program

class LoyaltyProgramBase(BaseModel):
    """Base loyalty program schema."""
    name: str
    program_type: str = "points"
    points_per_dollar: float = 1.0
    points_per_visit: int = 10
    points_to_dollar: float = 0.01
    min_redemption: int = 100
    tiers: Optional[List[Dict[str, Any]]] = None


class LoyaltyProgramCreate(LoyaltyProgramBase):
    """Create loyalty program schema."""
    pass


class LoyaltyProgramResponse(LoyaltyProgramBase):
    """Loyalty program response schema."""
    id: int
    is_active: bool = True
    created_at: datetime

    model_config = {"from_attributes": True}


# Customer Loyalty

class CustomerLoyaltyResponse(BaseModel):
    """Customer loyalty status."""
    id: int
    customer_id: int
    program_id: Optional[int] = None
    current_points: int = 0
    lifetime_points: int = 0
    redeemed_points: int = 0
    total_visits: int = 0
    total_spend: float = 0.0
    current_tier: Optional[str] = None
    first_visit_at: Optional[datetime] = None
    last_visit_at: Optional[datetime] = None
    birthday: Optional[datetime] = None
    favorite_items: Optional[List[int]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LoyaltyTransaction(BaseModel):
    """Loyalty points transaction."""
    customer_id: int
    points: int
    transaction_type: str  # "earn", "redeem", "bonus", "adjust"
    description: str
    order_id: Optional[int] = None


class LoyaltyRedemption(BaseModel):
    """Loyalty points redemption request."""
    customer_id: int
    points_to_redeem: int


class LoyaltyRedemptionResponse(BaseModel):
    """Loyalty redemption response."""
    customer_id: int
    points_redeemed: int
    dollar_value: Decimal
    new_balance: int


# AI Campaign Generation

class AICampaignRequest(BaseModel):
    """Request AI to generate campaign content."""
    campaign_type: CampaignType
    target_segment: Optional[str] = None
    promotion_details: Optional[str] = None
    tone: str = "friendly"  # friendly, professional, casual, urgent


class AICampaignResponse(BaseModel):
    """AI-generated campaign content."""
    subject: str
    email_content: str
    sms_content: str
    suggested_send_time: datetime
    predicted_open_rate: float
    predicted_click_rate: float

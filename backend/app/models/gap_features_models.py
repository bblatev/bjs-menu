"""
Gap Features Models
====================
Database models for Phase 2-7 gap features:
- Mobile & Offline Sync
- Developer Portal & Marketplace
- Third-Party Integrations
- Team Chat & Labor Compliance
- A/B Testing & Review Automation
- SSO & Enterprise Security
- Demand Forecasting
- P&L Analysis
- Hardware SDK & BNPL
"""

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, JSON,
    ForeignKey, Date, Numeric, Index
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from enum import Enum as PyEnum
from app.db.base import Base


# =====================================================
# ENUMS
# =====================================================

class SSOProviderType(str, PyEnum):
    SAML = "saml"
    OIDC = "oidc"
    GOOGLE = "google"
    MICROSOFT = "microsoft"
    OKTA = "okta"
    ONELOGIN = "onelogin"


class ExperimentStatus(str, PyEnum):
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"


class AppStatus(str, PyEnum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUSPENDED = "suspended"


class PricingType(str, PyEnum):
    FREE = "free"
    PAID = "paid"
    FREEMIUM = "freemium"


# =====================================================
# SSO & ENTERPRISE SECURITY MODELS
# =====================================================

class SSOConfiguration(Base):
    """SSO configuration for a tenant."""
    __tablename__ = "sso_configurations"
    __table_args__ = {'extend_existing': True}

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), nullable=False, index=True)
    provider_type = Column(String(20), nullable=False)  # SSOProviderType value
    display_name = Column(String(200), nullable=False)
    config = Column(JSON, default=dict)
    domain_whitelist = Column(JSON, default=list)
    auto_provision_users = Column(Boolean, default=True)
    default_role = Column(String(50), default="staff")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class SSOSession(Base):
    """SSO session tracking."""
    __tablename__ = "sso_sessions"
    __table_args__ = {'extend_existing': True}

    id = Column(String(36), primary_key=True)
    sso_config_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(36), nullable=False, index=True)
    provider_user_id = Column(String(255), nullable=True)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    id_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    user_info = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_activity_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    ended_at = Column(DateTime, nullable=True)


# =====================================================
# TEAM CHAT & COMMUNICATION MODELS
# =====================================================

class ChatChannel(Base):
    """Chat channel for team communication."""
    __tablename__ = "chat_channels"
    __table_args__ = {'extend_existing': True}

    id = Column(String(36), primary_key=True)
    venue_id = Column(String(36), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    channel_type = Column(String(20), default="public")  # public, private, shift, direct
    description = Column(Text, nullable=True)
    created_by = Column(String(36), nullable=True)
    members = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    last_message_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ChatMessage(Base):
    """Chat message in a channel."""
    __tablename__ = "chat_messages"
    __table_args__ = {'extend_existing': True}

    id = Column(String(36), primary_key=True)
    channel_id = Column(String(36), nullable=False, index=True)
    sender_id = Column(String(36), nullable=False, index=True)
    content = Column(Text, nullable=False)
    message_type = Column(String(20), default="text")  # text, image, file, system
    attachments = Column(JSON, default=list)
    reply_to_id = Column(String(36), nullable=True)
    mentions = Column(JSON, default=list)
    is_edited = Column(Boolean, default=False)
    edited_at = Column(DateTime, nullable=True)
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class MessageAcknowledgment(Base):
    """Read receipt for a message."""
    __tablename__ = "message_acknowledgments"
    __table_args__ = {'extend_existing': True}

    id = Column(String(36), primary_key=True)
    message_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(36), nullable=False, index=True)
    read_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class TeamAnnouncement(Base):
    """Team announcement."""
    __tablename__ = "team_announcements"
    __table_args__ = {'extend_existing': True}

    id = Column(String(36), primary_key=True)
    venue_id = Column(String(36), nullable=False, index=True)
    title = Column(String(300), nullable=False)
    content = Column(Text, nullable=False)
    created_by = Column(String(36), nullable=False)
    priority = Column(String(20), default="normal")  # low, normal, high, urgent
    target_roles = Column(JSON, default=list)
    target_staff_ids = Column(JSON, default=list)
    expires_at = Column(DateTime, nullable=True)
    require_acknowledgment = Column(Boolean, default=False)
    acknowledgments = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# =====================================================
# LABOR COMPLIANCE MODELS
# =====================================================

class LaborComplianceRule(Base):
    """Labor compliance rule."""
    __tablename__ = "labor_compliance_rules"
    __table_args__ = {'extend_existing': True}

    id = Column(String(36), primary_key=True)
    venue_id = Column(String(36), nullable=False, index=True)
    rule_type = Column(String(50), nullable=False)  # break, overtime, minor, scheduling, split_shift
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    conditions = Column(JSON, default=dict)
    action = Column(String(20), default="warn")  # warn, block, notify
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class LaborComplianceViolation(Base):
    """Labor compliance violation record."""
    __tablename__ = "labor_compliance_violations"
    __table_args__ = {'extend_existing': True}

    id = Column(String(36), primary_key=True)
    venue_id = Column(String(36), nullable=False, index=True)
    rule_id = Column(String(36), nullable=False)
    staff_id = Column(String(36), nullable=False)
    shift_id = Column(String(36), nullable=True)
    violation_type = Column(String(50), nullable=False)
    details = Column(JSON, default=dict)
    status = Column(String(20), default="open")  # open, resolved, dismissed
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# =====================================================
# A/B TESTING MODELS
# =====================================================

class ABExperiment(Base):
    """A/B experiment definition."""
    __tablename__ = "ab_experiments"
    __table_args__ = {'extend_existing': True}

    id = Column(String(36), primary_key=True)
    venue_id = Column(String(36), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    experiment_type = Column(String(50), nullable=False)  # menu_item, pricing, promotion, feature, upsell
    variants = Column(JSON, default=list)
    target_metric = Column(String(50), nullable=False)  # conversion_rate, avg_order_value, item_sales, revenue
    traffic_percentage = Column(Integer, default=100)
    status = Column(String(20), default="draft")  # ExperimentStatus value
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    winner_variant = Column(String(100), nullable=True)
    created_by = Column(String(36), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ExperimentAssignment(Base):
    """User assignment to an experiment variant."""
    __tablename__ = "experiment_assignments"
    __table_args__ = {'extend_existing': True}

    id = Column(String(36), primary_key=True)
    experiment_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    user_type = Column(String(20), default="customer")  # customer, session, order
    variant_id = Column(String(100), nullable=True)
    assigned_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    converted = Column(Boolean, default=False)
    converted_at = Column(DateTime, nullable=True)
    conversion_value = Column(Float, nullable=True)
    conversion_metadata = Column(JSON, default=dict)


# =====================================================
# REVIEW AUTOMATION MODELS
# =====================================================

class ReviewLink(Base):
    """Review platform link."""
    __tablename__ = "review_links"
    __table_args__ = {'extend_existing': True}

    id = Column(String(36), primary_key=True)
    venue_id = Column(String(36), nullable=False, index=True)
    platform = Column(String(50), nullable=False)  # google, yelp, tripadvisor, facebook
    link_url = Column(String(500), nullable=False)
    click_count = Column(Integer, default=0)
    last_clicked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class ReviewRequest(Base):
    """Review request sent to a customer."""
    __tablename__ = "review_requests"
    __table_args__ = {'extend_existing': True}

    id = Column(String(36), primary_key=True)
    venue_id = Column(String(36), nullable=False, index=True)
    order_id = Column(String(36), nullable=False)
    customer_id = Column(String(36), nullable=False)
    method = Column(String(20), default="email")  # email, sms, both
    status = Column(String(20), default="scheduled")  # scheduled, sent, failed
    scheduled_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# =====================================================
# THIRD-PARTY INTEGRATION MODELS
# =====================================================

class IntegrationCredential(Base):
    """Encrypted credentials for third-party integrations."""
    __tablename__ = "integration_credentials"
    __table_args__ = {'extend_existing': True}

    id = Column(String(36), primary_key=True)
    venue_id = Column(String(36), nullable=False, index=True)
    integration_type = Column(String(50), nullable=False)  # 7shifts, homebase, marginedge, quickbooks, xero
    encrypted_credentials = Column(Text, nullable=True)
    meta_data = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    last_sync_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class ZapierWebhook(Base):
    """Zapier webhook subscription."""
    __tablename__ = "zapier_webhooks"
    __table_args__ = {'extend_existing': True}

    id = Column(String(36), primary_key=True)
    venue_id = Column(String(36), nullable=False, index=True)
    event_type = Column(String(100), nullable=False)
    webhook_url = Column(String(500), nullable=False)
    webhook_secret = Column(String(100), nullable=True)
    filters = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    trigger_count = Column(Integer, default=0)
    last_triggered_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# =====================================================
# MOBILE & OFFLINE SYNC MODELS
# =====================================================

class PushToken(Base):
    """Push notification token for a device."""
    __tablename__ = "push_tokens"
    __table_args__ = {'extend_existing': True}

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=False, index=True)
    user_type = Column(String(20), default="staff")  # staff, customer
    venue_id = Column(String(36), nullable=False, index=True)
    token = Column(String(500), nullable=False, unique=True)
    platform = Column(String(20), nullable=False)  # fcm, apns, web, expo
    device_info = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class PushNotification(Base):
    """Push notification record."""
    __tablename__ = "push_notifications"
    __table_args__ = {'extend_existing': True}

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    data = Column(JSON, default=dict)
    channel = Column(String(50), default="default")
    priority = Column(String(20), default="normal")
    status = Column(String(20), default="pending")  # pending, sent, failed, read
    device_token = Column(String(500), nullable=True)
    scheduled_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class EmployeeAppSession(Base):
    """Employee mobile app session."""
    __tablename__ = "employee_app_sessions"
    __table_args__ = {'extend_existing': True}

    id = Column(String(36), primary_key=True)
    staff_id = Column(String(36), nullable=False, index=True)
    venue_id = Column(String(36), nullable=False, index=True)
    device_id = Column(String(100), nullable=False)
    device_type = Column(String(50), default="unknown")
    device_os = Column(String(50), default="unknown")
    app_version = Column(String(20), nullable=True)
    last_sync_at = Column(DateTime, nullable=True)
    sync_version = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    ended_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class CustomerAppSession(Base):
    """Customer mobile app session."""
    __tablename__ = "customer_app_sessions"
    __table_args__ = {'extend_existing': True}

    id = Column(String(36), primary_key=True)
    customer_id = Column(String(36), nullable=False, index=True)
    venue_id = Column(String(36), nullable=False, index=True)
    device_id = Column(String(100), nullable=False)
    device_type = Column(String(50), default="unknown")
    device_os = Column(String(50), default="unknown")
    app_version = Column(String(20), nullable=True)
    last_sync_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    ended_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# =====================================================
# DEVELOPER PORTAL & MARKETPLACE MODELS
# =====================================================

class Developer(Base):
    """Developer account for API access."""
    __tablename__ = "developers"
    __table_args__ = {'extend_existing': True}

    id = Column(String(36), primary_key=True)
    email = Column(String(255), nullable=False, unique=True)
    company_name = Column(String(200), nullable=False)
    contact_name = Column(String(200), nullable=False)
    website = Column(String(500), nullable=True)
    use_case = Column(Text, nullable=True)
    is_verified = Column(Boolean, default=False)
    verified_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    tier = Column(String(20), default="free")  # free, starter, professional, enterprise
    rate_limit_per_minute = Column(Integer, default=60)
    rate_limit_per_day = Column(Integer, default=10000)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class APIKey(Base):
    """API key for developer access."""
    __tablename__ = "api_keys"
    __table_args__ = {'extend_existing': True}

    id = Column(String(36), primary_key=True)
    developer_id = Column(String(36), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    key_prefix = Column(String(20), nullable=False)
    key_hash = Column(String(64), nullable=False)
    scopes = Column(JSON, default=list)
    venue_id = Column(String(36), nullable=True)
    is_active = Column(Boolean, default=True)
    rate_limit_per_minute = Column(Integer, default=60)
    rate_limit_per_day = Column(Integer, default=10000)
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class APILog(Base):
    """API request log."""
    __tablename__ = "api_logs"
    __table_args__ = {'extend_existing': True}

    id = Column(String(36), primary_key=True)
    api_key_id = Column(String(36), nullable=False, index=True)
    method = Column(String(10), nullable=False)
    path = Column(String(500), nullable=False)
    status_code = Column(Integer, nullable=False)
    response_time_ms = Column(Integer, default=0)
    request_body_size = Column(Integer, default=0)
    response_body_size = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class MarketplaceApp(Base):
    """Marketplace application."""
    __tablename__ = "marketplace_apps"
    __table_args__ = {'extend_existing': True}

    id = Column(String(36), primary_key=True)
    developer_id = Column(String(36), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    slug = Column(String(200), nullable=False, unique=True)
    short_description = Column(String(500), nullable=False)
    full_description = Column(Text, nullable=True)
    category = Column(String(50), nullable=False)
    icon_url = Column(String(500), nullable=True)
    screenshots = Column(JSON, default=list)
    webhook_url = Column(String(500), nullable=True)
    oauth_redirect_uri = Column(String(500), nullable=True)
    required_scopes = Column(JSON, default=list)
    pricing_type = Column(String(20), default="free")  # PricingType value
    price_monthly = Column(Float, default=0)
    price_yearly = Column(Float, default=0)
    status = Column(String(20), default="draft")  # AppStatus value
    version = Column(String(20), default="1.0.0")
    install_count = Column(Integer, default=0)
    avg_rating = Column(Float, default=0)
    review_count = Column(Integer, default=0)
    submitted_at = Column(DateTime, nullable=True)
    published_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class AppInstallation(Base):
    """App installation for a venue."""
    __tablename__ = "app_installations"
    __table_args__ = {'extend_existing': True}

    id = Column(String(36), primary_key=True)
    app_id = Column(String(36), nullable=False, index=True)
    venue_id = Column(String(36), nullable=False, index=True)
    installed_by = Column(String(36), nullable=True)
    granted_scopes = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    billing_cycle = Column(String(20), default="monthly")
    installed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    uninstalled_at = Column(DateTime, nullable=True)


class AppReview(Base):
    """App review from a venue."""
    __tablename__ = "app_reviews"
    __table_args__ = {'extend_existing': True}

    id = Column(String(36), primary_key=True)
    app_id = Column(String(36), nullable=False, index=True)
    venue_id = Column(String(36), nullable=False, index=True)
    reviewer_id = Column(String(36), nullable=True)
    rating = Column(Integer, nullable=False)
    title = Column(String(200), nullable=True)
    body = Column(Text, nullable=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


# =====================================================
# DEMAND FORECASTING MODELS
# =====================================================

class AIDemandForecast(Base):
    """AI-generated demand forecast."""
    __tablename__ = "ai_demand_forecasts"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, nullable=False, index=True)
    forecast_date = Column(Date, nullable=False)
    forecast_type = Column(String(20), default="daily")  # daily, weekly, monthly
    expected_covers = Column(Integer, default=0)
    expected_revenue = Column(Numeric(12, 2), default=0)
    confidence_low = Column(Numeric(12, 2), default=0)
    confidence_high = Column(Numeric(12, 2), default=0)
    confidence_level = Column(Numeric(5, 2), default=0)
    factors = Column(JSON, default=list)
    model_version = Column(String(20), nullable=True)
    actual_covers = Column(Integer, nullable=True)
    actual_revenue = Column(Numeric(12, 2), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class AIItemDemandForecast(Base):
    """Item-level demand forecast."""
    __tablename__ = "ai_item_demand_forecasts"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    forecast_id = Column(Integer, nullable=False, index=True)
    menu_item_id = Column(Integer, nullable=False, index=True)
    expected_quantity = Column(Integer, default=0)
    confidence_low = Column(Float, default=0)
    confidence_high = Column(Float, default=0)
    actual_quantity = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ScheduleProposal(Base):
    """Auto-generated schedule proposal."""
    __tablename__ = "schedule_proposals"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, nullable=False, index=True)
    week_start = Column(Date, nullable=False)
    week_end = Column(Date, nullable=False)
    total_labor_hours = Column(Numeric(10, 2), default=0)
    estimated_labor_cost = Column(Numeric(12, 2), default=0)
    coverage_score = Column(Numeric(5, 2), default=0)
    shifts_data = Column(JSON, default=list)
    status = Column(String(20), default="proposed")  # proposed, approved, rejected
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class PurchasePlanProposal(Base):
    """Auto-generated purchase plan."""
    __tablename__ = "purchase_plan_proposals"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, nullable=False, index=True)
    plan_date = Column(Date, nullable=False)
    total_cost = Column(Numeric(12, 2), default=0)
    purchase_orders = Column(JSON, default=list)
    status = Column(String(20), default="proposed")  # proposed, approved, rejected
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# =====================================================
# P&L ANALYSIS MODELS
# =====================================================

class PLSnapshot(Base):
    """Profit & Loss snapshot."""
    __tablename__ = "pl_snapshots"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, nullable=False, index=True)
    period_type = Column(String(20), nullable=False)  # daily, weekly, monthly
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    gross_revenue = Column(Numeric(12, 2), default=0)
    net_revenue = Column(Numeric(12, 2), default=0)
    food_cost = Column(Numeric(12, 2), default=0)
    food_cost_pct = Column(Numeric(5, 2), default=0)
    beverage_cost = Column(Numeric(12, 2), default=0)
    beverage_cost_pct = Column(Numeric(5, 2), default=0)
    labor_cost = Column(Numeric(12, 2), default=0)
    labor_cost_pct = Column(Numeric(5, 2), default=0)
    prime_cost = Column(Numeric(12, 2), default=0)
    prime_cost_pct = Column(Numeric(5, 2), default=0)
    operating_expenses = Column(Numeric(12, 2), default=0)
    net_profit = Column(Numeric(12, 2), default=0)
    net_margin_pct = Column(Numeric(5, 2), default=0)
    order_count = Column(Integer, default=0)
    avg_ticket = Column(Numeric(10, 2), default=0)
    guest_count = Column(Integer, default=0)
    meta_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class SavingOpportunity(Base):
    """Cost saving opportunity."""
    __tablename__ = "saving_opportunities"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, nullable=False, index=True)
    category = Column(String(50), nullable=False)
    title = Column(String(300), nullable=False)
    current_value = Column(Float, default=0)
    target_value = Column(Float, default=0)
    potential_savings = Column(Float, default=0)
    priority = Column(String(20), default="medium")
    description = Column(Text, nullable=True)
    status = Column(String(20), default="open")  # open, in_progress, resolved, dismissed
    actual_savings = Column(Float, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


# =====================================================
# WEBHOOK DELIVERY MODELS
# =====================================================

class WebhookDelivery(Base):
    """Webhook delivery tracking."""
    __tablename__ = "webhook_deliveries"
    __table_args__ = {'extend_existing': True}

    id = Column(String(36), primary_key=True)
    webhook_id = Column(String(36), nullable=False, index=True)
    event_type = Column(String(100), nullable=False)
    endpoint_url = Column(String(500), nullable=False)
    payload = Column(JSON, default=dict)
    success = Column(Boolean, default=False)
    response_status = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# =====================================================
# HARDWARE SDK MODELS
# =====================================================

class SDKHardwareDevice(Base):
    """Registered hardware device."""
    __tablename__ = "sdk_hardware_devices"
    __table_args__ = {'extend_existing': True}

    id = Column(String(36), primary_key=True)
    venue_id = Column(String(36), nullable=False, index=True)
    station_id = Column(String(36), nullable=True)
    device_type = Column(String(50), nullable=False)  # payment_terminal, receipt_printer, kitchen_display, etc.
    serial_number = Column(String(100), nullable=True)
    manufacturer = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    name = Column(String(200), nullable=True)
    firmware_version = Column(String(50), nullable=True)
    connection_type = Column(String(20), default="usb")  # usb, network, bluetooth, serial
    connection_params = Column(JSON, default=dict)
    capabilities = Column(JSON, default=list)
    device_token_hash = Column(String(64), nullable=True)
    status = Column(String(20), default="registered")  # registered, online, offline, deactivated
    status_details = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    last_seen_at = Column(DateTime, nullable=True)
    last_heartbeat = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class SDKTerminalSession(Base):
    """Payment terminal session."""
    __tablename__ = "sdk_terminal_sessions"
    __table_args__ = {'extend_existing': True}

    id = Column(String(36), primary_key=True)
    device_id = Column(String(36), nullable=False, index=True)
    session_type = Column(String(20), default="payment")
    status = Column(String(20), default="active")  # active, completed, expired
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    ended_at = Column(DateTime, nullable=True)


class SDKTerminalCommand(Base):
    """Terminal command record."""
    __tablename__ = "sdk_terminal_commands"
    __table_args__ = {'extend_existing': True}

    id = Column(String(36), primary_key=True)
    device_id = Column(String(36), nullable=False, index=True)
    command = Column(String(50), nullable=False)
    params = Column(JSON, default=dict)
    status = Column(String(20), default="pending")  # pending, processing, completed, failed
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)


class SDKDeviceLog(Base):
    """Hardware device event log."""
    __tablename__ = "sdk_device_logs"
    __table_args__ = {'extend_existing': True}

    id = Column(String(36), primary_key=True)
    device_id = Column(String(36), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)
    message = Column(Text, nullable=True)
    data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# =====================================================
# BNPL (BUY NOW PAY LATER) MODELS
# =====================================================

class BNPLConfiguration(Base):
    """BNPL provider configuration."""
    __tablename__ = "bnpl_configurations"
    __table_args__ = {'extend_existing': True}

    id = Column(String(36), primary_key=True)
    venue_id = Column(String(36), nullable=False, index=True)
    provider = Column(String(50), nullable=False)  # klarna, affirm, afterpay, clearpay, zip
    credentials_encrypted = Column(Text, nullable=True)
    settings = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class BNPLTransaction(Base):
    """BNPL transaction record."""
    __tablename__ = "bnpl_transactions"
    __table_args__ = {'extend_existing': True}

    id = Column(String(36), primary_key=True)
    venue_id = Column(String(36), nullable=False, index=True)
    order_id = Column(String(36), nullable=False, index=True)
    provider = Column(String(50), nullable=False)
    external_session_id = Column(String(255), nullable=True)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="USD")
    status = Column(String(20), default="pending")  # pending, authorized, captured, completed, cancelled, declined, expired, refunded, partially_refunded
    redirect_url = Column(String(500), nullable=True)
    customer_info = Column(JSON, default=dict)
    webhook_data = Column(JSON, default=dict)
    auto_capture = Column(Boolean, default=False)
    captured_at = Column(DateTime, nullable=True)
    refunded_amount = Column(Numeric(10, 2), nullable=True)
    refunded_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

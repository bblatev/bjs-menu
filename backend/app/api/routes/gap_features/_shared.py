"""
Gap Features API Endpoints
Exposes all Phase 2-7 gap features:
- Mobile & Offline Sync
- Developer Portal & Marketplace
- Third-Party Integrations
- Team Chat & Labor Compliance
- A/B Testing & Review Automation
- SSO & Enterprise Security
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.rbac import get_current_user, get_current_venue
from app.core.rate_limit import limiter
try:
    from app.core.security import validate_redirect_uri
except ImportError:
    validate_redirect_uri = None
from app.models import StaffUser as Staff




# ==================== SCHEMAS ====================

# Mobile & Offline
class SyncPackageRequest(BaseModel):
    device_id: str
    last_sync: Optional[datetime] = None
    include_menu: bool = True
    include_tables: bool = True
    include_staff: bool = True
    include_inventory: bool = False


class OfflineTransactionRequest(BaseModel):
    device_id: str
    transactions: List[Dict[str, Any]]


class PushTokenRequest(BaseModel):
    token: str
    platform: str  # 'fcm', 'apns', 'web', 'expo'
    device_info: Optional[Dict[str, Any]] = None


class NotificationRequest(BaseModel):
    title: str
    body: str
    data: Optional[Dict[str, Any]] = None
    channel: str = "default"


# Developer Portal
class DeveloperRegistrationRequest(BaseModel):
    email: EmailStr
    company_name: str
    contact_name: str
    website: Optional[str] = None
    use_case: Optional[str] = None


class APIKeyRequest(BaseModel):
    name: str
    scopes: List[str]
    expires_in_days: Optional[int] = None


class AppSubmissionRequest(BaseModel):
    name: str
    slug: str
    short_description: str
    full_description: str
    category: str
    icon_url: str
    screenshots: List[str]
    webhook_url: Optional[str] = None
    oauth_redirect_uri: Optional[str] = None
    required_scopes: List[str] = []
    pricing_type: str = "free"
    price_monthly: float = 0
    price_yearly: float = 0


# Integrations
class ZapierWebhookRequest(BaseModel):
    event_type: str
    webhook_url: str
    filters: Optional[Dict[str, Any]] = None


class IntegrationCredentialRequest(BaseModel):
    integration_type: str
    credentials: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


# Team Chat
class ChannelCreateRequest(BaseModel):
    name: str
    channel_type: str = "public"
    description: Optional[str] = None
    members: Optional[List[UUID]] = None


class MessageRequest(BaseModel):
    content: str
    message_type: str = "text"
    attachments: Optional[List[Dict[str, Any]]] = None
    reply_to_id: Optional[UUID] = None
    mentions: Optional[List[UUID]] = None


class AnnouncementRequest(BaseModel):
    title: str
    content: str
    priority: str = "normal"
    target_roles: Optional[List[str]] = None
    target_staff_ids: Optional[List[UUID]] = None
    expires_at: Optional[datetime] = None
    require_acknowledgment: bool = False


class ComplianceRuleRequest(BaseModel):
    rule_type: str
    name: str
    description: str
    conditions: Dict[str, Any]
    action: str = "warn"


# A/B Testing
class ExperimentRequest(BaseModel):
    name: str
    description: str
    experiment_type: str
    variants: List[Dict[str, Any]]
    target_metric: str
    traffic_percentage: int = 100
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class ConversionRequest(BaseModel):
    user_id: str
    metric_name: str
    metric_value: float
    order_id: Optional[UUID] = None
    metadata: Optional[Dict[str, Any]] = None


# Review Automation
class ReviewLinkRequest(BaseModel):
    platform: str
    link_url: str


class ReviewRequestRequest(BaseModel):
    order_id: UUID
    customer_id: UUID
    method: str = "email"
    delay_hours: int = 2


# SSO
class SSOConfigRequest(BaseModel):
    provider_type: str
    display_name: str
    config: Dict[str, Any]
    domain_whitelist: Optional[List[str]] = None
    auto_provision_users: bool = True
    default_role: str = "staff"


# ==================== MOBILE & OFFLINE ENDPOINTS ====================


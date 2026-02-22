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
from app.core.security import validate_redirect_uri
from app.models import StaffUser as Staff


router = APIRouter()


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

@router.get("/")
@limiter.limit("60/minute")
async def get_gap_features_root(request: Request, db: Session = Depends(get_db)):
    """Gap features overview."""
    return {"module": "gap-features", "status": "active", "features": ["mobile-sync", "push-notifications", "developer-api", "marketplace"], "endpoints": ["/mobile/sync", "/push/notifications", "/marketplace/apps"]}


@router.get("/mobile/sync")
@limiter.limit("60/minute")
async def get_sync_package(
    request: Request,
    device_id: str = Query("", description="Device ID"),
    last_sync: Optional[datetime] = Query(None, description="Last sync timestamp"),
    include_menu: bool = True,
    include_tables: bool = True,
    include_staff: bool = True,
    include_inventory: bool = False,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
    venue_id: int = Depends(get_current_venue)
):
    """Get sync package for offline operation."""
    from app.services.mobile_offline_service import MobileOfflineService

    service = MobileOfflineService(db)
    return await service.get_sync_package(
        venue_id=venue_id,
        device_id=device_id,
        last_sync=last_sync,
        include_menu=include_menu,
        include_tables=include_tables,
        include_staff=include_staff,
        include_inventory=include_inventory
    )


@router.post("/mobile/sync/transactions")
@limiter.limit("30/minute")
async def process_offline_transactions(
    request: Request,
    body: OfflineTransactionRequest,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
    venue_id: int = Depends(get_current_venue)
):
    """Process transactions created while offline."""
    from app.services.mobile_offline_service import MobileOfflineService

    service = MobileOfflineService(db)
    return await service.process_offline_transactions(
        venue_id=venue_id,
        device_id=body.device_id,
        transactions=body.transactions
    )


@router.post("/push/register")
@limiter.limit("30/minute")
async def register_push_token(
    request: Request,
    body: PushTokenRequest,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
    venue_id: int = Depends(get_current_venue)
):
    """Register a push notification token."""
    from app.services.mobile_offline_service import PushNotificationService

    service = PushNotificationService(db)
    token = await service.register_token(
        user_id=current_user.id,
        user_type="staff",
        venue_id=venue_id,
        token=body.token,
        platform=body.platform,
        device_info=body.device_info
    )
    return {"status": "registered", "token_id": str(token.id)}


@router.delete("/push/unregister")
@limiter.limit("30/minute")
async def unregister_push_token(
    request: Request,
    token: str,
    db: Session = Depends(get_db)
):
    """Unregister a push notification token."""
    from app.services.mobile_offline_service import PushNotificationService

    service = PushNotificationService(db)
    success = await service.unregister_token(token)
    return {"status": "unregistered" if success else "not_found"}


@router.post("/push/send")
@limiter.limit("30/minute")
async def send_push_notification(
    request: Request,
    user_id: str,
    body: NotificationRequest,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user)
):
    """Send a push notification to a user."""
    from app.services.mobile_offline_service import PushNotificationService

    service = PushNotificationService(db)
    notification = await service.send_notification(
        user_id=user_id,
        title=body.title,
        body=body.body,
        data=body.data,
        channel=body.channel
    )
    return {"status": notification.status, "notification_id": str(notification.id)}


@router.get("/push/notifications")
@limiter.limit("60/minute")
async def get_notifications(
    request: Request,
    limit: int = 50,
    include_read: bool = False,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user)
):
    """Get notifications for the current user."""
    from app.services.mobile_offline_service import PushNotificationService

    service = PushNotificationService(db)
    notifications = await service.get_user_notifications(
        user_id=current_user.id,
        limit=limit,
        include_read=include_read
    )
    return {"notifications": notifications}


# ==================== DEVELOPER PORTAL ENDPOINTS ====================

@router.post("/developers/register")
@limiter.limit("30/minute")
async def register_developer(
    request: Request,
    body: DeveloperRegistrationRequest,
    db: Session = Depends(get_db)
):
    """Register as a developer."""
    from app.services.developer_portal_service import DeveloperPortalService

    service = DeveloperPortalService(db)
    developer = await service.register_developer(
        email=body.email,
        company_name=body.company_name,
        contact_name=body.contact_name,
        website=body.website,
        use_case=body.use_case
    )
    return {
        "developer_id": str(developer.id),
        "email": developer.email,
        "tier": developer.tier,
        "status": "pending_verification"
    }


@router.post("/developers/{developer_id}/api-keys")
@limiter.limit("30/minute")
async def create_api_key(
    request: Request,
    developer_id: str,
    body: APIKeyRequest,
    db: Session = Depends(get_db)
):
    """Create a new API key."""
    from app.services.developer_portal_service import DeveloperPortalService

    service = DeveloperPortalService(db)
    api_key, raw_key = await service.create_api_key(
        developer_id=developer_id,
        name=body.name,
        scopes=body.scopes,
        expires_in_days=body.expires_in_days
    )
    return {
        "api_key_id": str(api_key.id),
        "name": api_key.name,
        "key": raw_key,  # Only shown once
        "scopes": api_key.scopes,
        "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
        "warning": "Save this key securely. It will not be shown again."
    }


@router.get("/developers/{developer_id}/api-keys")
@limiter.limit("60/minute")
async def list_api_keys(
    request: Request,
    developer_id: str,
    db: Session = Depends(get_db)
):
    """List all API keys for a developer."""
    from app.services.developer_portal_service import DeveloperPortalService

    service = DeveloperPortalService(db)
    keys = await service.list_api_keys(developer_id)
    return {
        "api_keys": [
            {
                "id": str(k.id),
                "name": k.name,
                "key_prefix": k.key_prefix,
                "scopes": k.scopes,
                "is_active": k.is_active,
                "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
                "expires_at": k.expires_at.isoformat() if k.expires_at else None
            }
            for k in keys
        ]
    }


@router.delete("/developers/{developer_id}/api-keys/{api_key_id}")
@limiter.limit("30/minute")
async def revoke_api_key(
    request: Request,
    developer_id: str,
    api_key_id: str,
    db: Session = Depends(get_db)
):
    """Revoke an API key."""
    from app.services.developer_portal_service import DeveloperPortalService

    service = DeveloperPortalService(db)
    success = await service.revoke_api_key(api_key_id, developer_id)
    return {"status": "revoked" if success else "not_found"}


@router.get("/developers/{developer_id}/usage")
@limiter.limit("60/minute")
async def get_api_usage(
    request: Request,
    developer_id: str,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get API usage statistics."""
    from app.services.developer_portal_service import DeveloperPortalService

    service = DeveloperPortalService(db)
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    stats = await service.get_api_usage_stats(developer_id, start_date, end_date)
    return stats


# ==================== MARKETPLACE ENDPOINTS ====================

@router.post("/marketplace/apps")
@limiter.limit("30/minute")
async def submit_app(
    request: Request,
    body: AppSubmissionRequest,
    developer_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """Submit a new app to the marketplace."""
    from app.services.developer_portal_service import MarketplaceService

    service = MarketplaceService(db)
    app = await service.submit_app(
        developer_id=developer_id,
        **body.model_dump()
    )
    return {
        "app_id": str(app.id),
        "slug": app.slug,
        "status": app.status.value
    }


@router.get("/marketplace/apps")
@limiter.limit("60/minute")
async def list_marketplace_apps(
    request: Request,
    category: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "popular",
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """List apps in the marketplace."""
    from app.services.developer_portal_service import MarketplaceService

    service = MarketplaceService(db)
    apps, total = await service.list_apps(
        category=category,
        search=search,
        sort_by=sort_by,
        limit=limit,
        offset=offset
    )
    return {
        "apps": [
            {
                "id": str(a.id),
                "name": a.name,
                "slug": a.slug,
                "short_description": a.short_description,
                "category": a.category,
                "icon_url": a.icon_url,
                "pricing_type": a.pricing_type.value,
                "price_monthly": a.price_monthly,
                "avg_rating": a.avg_rating,
                "install_count": a.install_count
            }
            for a in apps
        ],
        "total": total
    }


@router.get("/marketplace/apps/{app_slug}")
@limiter.limit("60/minute")
async def get_marketplace_app(
    request: Request,
    app_slug: str,
    db: Session = Depends(get_db)
):
    """Get app details by slug."""
    from app.services.developer_portal_service import MarketplaceService

    service = MarketplaceService(db)
    app = await service.get_app_by_slug(app_slug)
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    return app


@router.post("/marketplace/apps/{app_id}/install")
@limiter.limit("30/minute")
async def install_app(
    request: Request,
    app_id: str,
    granted_scopes: List[str] = Body(...),
    billing_cycle: str = "monthly",
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
    venue_id: int = Depends(get_current_venue)
):
    """Install an app."""
    from app.services.developer_portal_service import MarketplaceService

    service = MarketplaceService(db)
    installation = await service.install_app(
        app_id=app_id,
        venue_id=venue_id,
        installed_by=current_user.id,
        granted_scopes=granted_scopes,
        billing_cycle=billing_cycle
    )
    return {
        "installation_id": str(installation.id),
        "status": "installed"
    }


@router.delete("/marketplace/apps/{app_id}/install")
@limiter.limit("30/minute")
async def uninstall_app(
    request: Request,
    app_id: str,
    db: Session = Depends(get_db),
    venue_id: int = Depends(get_current_venue)
):
    """Uninstall an app."""
    from app.services.developer_portal_service import MarketplaceService

    service = MarketplaceService(db)
    success = await service.uninstall_app(app_id, venue_id)
    return {"status": "uninstalled" if success else "not_found"}


@router.get("/marketplace/installed")
@limiter.limit("60/minute")
async def get_installed_apps(
    request: Request,
    db: Session = Depends(get_db),
    venue_id: int = Depends(get_current_venue)
):
    """Get installed apps for the venue."""
    from app.services.developer_portal_service import MarketplaceService

    service = MarketplaceService(db)
    installations = await service.get_installed_apps(venue_id)
    return {
        "apps": [
            {
                "installation_id": str(inst.id),
                "app_id": str(app.id),
                "app_name": app.name,
                "app_slug": app.slug,
                "installed_at": inst.installed_at.isoformat()
            }
            for inst, app in installations
        ]
    }


# ==================== INTEGRATIONS ENDPOINTS ====================

@router.get("/integrations")
@limiter.limit("60/minute")
async def list_integrations(
    request: Request,
    db: Session = Depends(get_db),
    venue_id: int = Depends(get_current_venue)
):
    """List configured integrations."""
    from app.services.third_party_integrations_service import IntegrationCredentialService

    service = IntegrationCredentialService(db)
    return await service.list_integrations(venue_id)


@router.post("/integrations/configure")
@limiter.limit("30/minute")
async def configure_integration(
    request: Request,
    body: IntegrationCredentialRequest,
    db: Session = Depends(get_db),
    venue_id: int = Depends(get_current_venue)
):
    """Configure an integration."""
    from app.services.third_party_integrations_service import IntegrationCredentialService

    service = IntegrationCredentialService(db)
    credential = await service.store_credential(
        venue_id=venue_id,
        integration_type=body.integration_type,
        credentials=body.credentials,
        metadata=body.metadata
    )
    return {"status": "configured", "id": str(credential.id)}


@router.delete("/integrations/{integration_type}")
@limiter.limit("30/minute")
async def delete_integration(
    request: Request,
    integration_type: str,
    db: Session = Depends(get_db),
    venue_id: int = Depends(get_current_venue)
):
    """Delete an integration."""
    from app.services.third_party_integrations_service import IntegrationCredentialService

    service = IntegrationCredentialService(db)
    success = await service.delete_credential(venue_id, integration_type)
    return {"status": "deleted" if success else "not_found"}


@router.post("/integrations/zapier/webhooks")
@limiter.limit("30/minute")
async def create_zapier_webhook(
    request: Request,
    body: ZapierWebhookRequest,
    db: Session = Depends(get_db),
    venue_id: int = Depends(get_current_venue)
):
    """Create a Zapier webhook."""
    from app.services.third_party_integrations_service import ZapierService

    service = ZapierService(db)
    webhook = await service.create_webhook(
        venue_id=venue_id,
        event_type=body.event_type,
        webhook_url=body.webhook_url,
        filters=body.filters
    )
    return {
        "webhook_id": str(webhook.id),
        "webhook_secret": webhook.webhook_secret
    }


@router.get("/integrations/zapier/webhooks")
@limiter.limit("60/minute")
async def list_zapier_webhooks(
    request: Request,
    db: Session = Depends(get_db),
    venue_id: int = Depends(get_current_venue)
):
    """List Zapier webhooks."""
    from app.services.third_party_integrations_service import ZapierService

    service = ZapierService(db)
    webhooks = await service.list_webhooks(venue_id)
    return {
        "webhooks": [
            {
                "id": str(w.id),
                "event_type": w.event_type,
                "webhook_url": w.webhook_url,
                "is_active": w.is_active,
                "trigger_count": w.trigger_count
            }
            for w in webhooks
        ]
    }


@router.get("/integrations/zapier/events")
@limiter.limit("60/minute")
async def get_zapier_events(
    request: Request,
    db: Session = Depends(get_db)
):
    """Get available Zapier event types."""
    from app.services.third_party_integrations_service import ZapierService

    service = ZapierService(db)
    return {"events": service.get_available_events()}


# ==================== TEAM CHAT ENDPOINTS ====================

@router.post("/chat/channels")
@limiter.limit("30/minute")
async def create_channel(
    request: Request,
    body: ChannelCreateRequest,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
    venue_id: int = Depends(get_current_venue)
):
    """Create a chat channel."""
    from app.services.team_chat_service import TeamChatService

    service = TeamChatService(db)
    channel = await service.create_channel(
        venue_id=venue_id,
        name=body.name,
        channel_type=body.channel_type,
        description=body.description,
        created_by=current_user.id,
        members=body.members
    )
    return {"channel_id": str(channel.id), "name": channel.name}


@router.get("/chat/channels")
@limiter.limit("60/minute")
async def get_channels(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
    venue_id: int = Depends(get_current_venue)
):
    """Get channels the user has access to."""
    from app.services.team_chat_service import TeamChatService

    service = TeamChatService(db)
    channels = await service.get_user_channels(venue_id, current_user.id)
    return {
        "channels": [
            {
                "id": str(c.id),
                "name": c.name,
                "channel_type": c.channel_type,
                "description": c.description,
                "last_message_at": c.last_message_at.isoformat() if c.last_message_at else None
            }
            for c in channels
        ]
    }


@router.post("/chat/channels/{channel_id}/messages")
@limiter.limit("30/minute")
async def send_message(
    request: Request,
    channel_id: str,
    body: MessageRequest,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user)
):
    """Send a message to a channel."""
    from app.services.team_chat_service import TeamChatService

    service = TeamChatService(db)
    message = await service.send_message(
        channel_id=channel_id,
        sender_id=current_user.id,
        content=body.content,
        message_type=body.message_type,
        attachments=body.attachments,
        reply_to_id=body.reply_to_id,
        mentions=body.mentions
    )
    return {"message_id": str(message.id), "created_at": message.created_at.isoformat()}


@router.get("/chat/channels/{channel_id}/messages")
@limiter.limit("60/minute")
async def get_messages(
    request: Request,
    channel_id: str,
    limit: int = 50,
    before: Optional[datetime] = None,
    after: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user)
):
    """Get messages from a channel."""
    from app.services.team_chat_service import TeamChatService

    service = TeamChatService(db)
    messages = await service.get_channel_messages(
        channel_id=channel_id,
        limit=limit,
        before=before,
        after=after
    )
    return {
        "messages": [
            {
                "id": str(m.id),
                "sender_id": str(m.sender_id),
                "content": m.content,
                "message_type": m.message_type,
                "attachments": m.attachments,
                "is_edited": m.is_edited,
                "created_at": m.created_at.isoformat()
            }
            for m in messages
        ]
    }


@router.post("/chat/channels/{channel_id}/read")
@limiter.limit("30/minute")
async def mark_channel_read(
    request: Request,
    channel_id: str,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user)
):
    """Mark all messages in a channel as read."""
    from app.services.team_chat_service import TeamChatService

    service = TeamChatService(db)
    count = await service.mark_channel_read(channel_id, current_user.id)
    return {"marked_read": count}


@router.post("/announcements")
@limiter.limit("30/minute")
async def create_announcement(
    request: Request,
    body: AnnouncementRequest,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
    venue_id: int = Depends(get_current_venue)
):
    """Create a team announcement."""
    from app.services.team_chat_service import TeamChatService

    service = TeamChatService(db)
    announcement = await service.create_announcement(
        venue_id=venue_id,
        title=body.title,
        content=body.content,
        created_by=current_user.id,
        priority=body.priority,
        target_roles=body.target_roles,
        target_staff_ids=body.target_staff_ids,
        expires_at=body.expires_at,
        require_acknowledgment=body.require_acknowledgment
    )
    return {"announcement_id": str(announcement.id)}


@router.get("/announcements")
@limiter.limit("60/minute")
async def get_announcements(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
    venue_id: int = Depends(get_current_venue)
):
    """Get active announcements."""
    from app.services.team_chat_service import TeamChatService

    service = TeamChatService(db)
    announcements = await service.get_active_announcements(
        venue_id=venue_id,
        user_id=current_user.id,
        role=current_user.role
    )
    return {
        "announcements": [
            {
                "id": str(a.id),
                "title": a.title,
                "content": a.content,
                "priority": a.priority,
                "require_acknowledgment": a.require_acknowledgment,
                "created_at": a.created_at.isoformat(),
                "expires_at": a.expires_at.isoformat() if a.expires_at else None
            }
            for a in announcements
        ]
    }


@router.post("/announcements/{announcement_id}/acknowledge")
@limiter.limit("30/minute")
async def acknowledge_announcement(
    request: Request,
    announcement_id: str,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user)
):
    """Acknowledge an announcement."""
    from app.services.team_chat_service import TeamChatService

    service = TeamChatService(db)
    success = await service.acknowledge_announcement(announcement_id, current_user.id)
    return {"status": "acknowledged" if success else "not_found"}


# ==================== LABOR COMPLIANCE ENDPOINTS ====================

@router.post("/labor/compliance/rules")
@limiter.limit("30/minute")
async def create_compliance_rule(
    request: Request,
    body: ComplianceRuleRequest,
    db: Session = Depends(get_db),
    venue_id: int = Depends(get_current_venue)
):
    """Create a labor compliance rule."""
    from app.services.team_chat_service import LaborComplianceService

    service = LaborComplianceService(db)
    rule = await service.create_compliance_rule(
        venue_id=venue_id,
        rule_type=body.rule_type,
        name=body.name,
        description=body.description,
        conditions=body.conditions,
        action=body.action
    )
    return rule


@router.post("/labor/compliance/check")
@limiter.limit("30/minute")
async def check_shift_compliance(
    request: Request,
    staff_id: str,
    shift_start: datetime,
    shift_end: datetime,
    db: Session = Depends(get_db),
    venue_id: int = Depends(get_current_venue)
):
    """Check if a proposed shift complies with labor rules."""
    from app.services.team_chat_service import LaborComplianceService

    service = LaborComplianceService(db)
    violations = await service.check_shift_compliance(
        venue_id=venue_id,
        staff_id=staff_id,
        shift_start=shift_start,
        shift_end=shift_end
    )
    return {"violations": violations, "compliant": len(violations) == 0}


@router.get("/labor/compliance/violations")
@limiter.limit("60/minute")
async def get_violations(
    request: Request,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    venue_id: int = Depends(get_current_venue)
):
    """Get labor compliance violations."""
    from app.services.team_chat_service import LaborComplianceService

    service = LaborComplianceService(db)
    violations = await service.get_violations(
        venue_id=venue_id,
        start_date=start_date,
        end_date=end_date,
        status=status
    )
    return {"violations": violations}


# ==================== A/B TESTING ENDPOINTS ====================

@router.post("/experiments")
@limiter.limit("30/minute")
async def create_experiment(
    request: Request,
    body: ExperimentRequest,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
    venue_id: int = Depends(get_current_venue)
):
    """Create an A/B experiment."""
    from app.services.ab_testing_service import ABTestingService

    service = ABTestingService(db)
    experiment = await service.create_experiment(
        venue_id=venue_id,
        name=body.name,
        description=body.description,
        experiment_type=body.experiment_type,
        variants=body.variants,
        target_metric=body.target_metric,
        traffic_percentage=body.traffic_percentage,
        start_date=body.start_date,
        end_date=body.end_date,
        created_by=current_user.id
    )
    return {"experiment_id": str(experiment.id), "status": experiment.status.value}


@router.get("/experiments")
@limiter.limit("60/minute")
async def list_experiments(
    request: Request,
    status: Optional[str] = None,
    experiment_type: Optional[str] = None,
    db: Session = Depends(get_db),
    venue_id: int = Depends(get_current_venue)
):
    """List experiments."""
    from app.services.ab_testing_service import ABTestingService

    service = ABTestingService(db)
    experiments = await service.list_experiments(
        venue_id=venue_id,
        status=status,
        experiment_type=experiment_type
    )
    return {
        "experiments": [
            {
                "id": str(e.id),
                "name": e.name,
                "experiment_type": e.experiment_type,
                "status": e.status.value,
                "target_metric": e.target_metric,
                "started_at": e.started_at.isoformat() if e.started_at else None
            }
            for e in experiments
        ]
    }


@router.post("/experiments/{experiment_id}/start")
@limiter.limit("30/minute")
async def start_experiment(
    request: Request,
    experiment_id: str,
    db: Session = Depends(get_db)
):
    """Start an experiment."""
    from app.services.ab_testing_service import ABTestingService

    service = ABTestingService(db)
    experiment = await service.start_experiment(experiment_id)
    return {"status": experiment.status.value}


@router.post("/experiments/{experiment_id}/pause")
@limiter.limit("30/minute")
async def pause_experiment(
    request: Request,
    experiment_id: str,
    db: Session = Depends(get_db)
):
    """Pause an experiment."""
    from app.services.ab_testing_service import ABTestingService

    service = ABTestingService(db)
    experiment = await service.pause_experiment(experiment_id)
    return {"status": experiment.status.value}


@router.post("/experiments/{experiment_id}/complete")
@limiter.limit("30/minute")
async def complete_experiment(
    request: Request,
    experiment_id: str,
    winner_variant: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Complete an experiment."""
    from app.services.ab_testing_service import ABTestingService

    service = ABTestingService(db)
    experiment = await service.complete_experiment(experiment_id, winner_variant)
    return {"status": experiment.status.value, "winner": experiment.winner_variant}


@router.get("/experiments/{experiment_id}/variant")
@limiter.limit("60/minute")
async def get_variant(
    request: Request,
    experiment_id: str,
    user_id: str = Query("", description="User ID"),
    user_type: str = Query("customer", description="User type"),
    db: Session = Depends(get_db)
):
    """Get the variant assigned to a user."""
    from app.services.ab_testing_service import ABTestingService

    service = ABTestingService(db)
    variant = await service.get_user_variant(experiment_id, user_id, user_type)
    return {"variant": variant}


@router.post("/experiments/{experiment_id}/convert")
@limiter.limit("30/minute")
async def record_conversion(
    request: Request,
    experiment_id: str,
    body: ConversionRequest,
    db: Session = Depends(get_db)
):
    """Record a conversion event."""
    from app.services.ab_testing_service import ABTestingService

    service = ABTestingService(db)
    success = await service.record_conversion(
        experiment_id=experiment_id,
        user_id=body.user_id,
        metric_name=body.metric_name,
        metric_value=body.metric_value,
        order_id=body.order_id,
        metadata=body.metadata
    )
    return {"recorded": success}


@router.get("/experiments/{experiment_id}/results")
@limiter.limit("60/minute")
async def get_experiment_results(
    request: Request,
    experiment_id: str,
    db: Session = Depends(get_db)
):
    """Get experiment results and statistics."""
    from app.services.ab_testing_service import ABTestingService

    service = ABTestingService(db)
    results = await service.get_experiment_results(experiment_id)
    return results


# ==================== REVIEW AUTOMATION ENDPOINTS ====================

@router.post("/reviews/links")
@limiter.limit("30/minute")
async def create_review_link(
    request: Request,
    body: ReviewLinkRequest,
    db: Session = Depends(get_db),
    venue_id: int = Depends(get_current_venue)
):
    """Create a review link."""
    from app.services.ab_testing_service import ReviewAutomationService

    service = ReviewAutomationService(db)
    link = await service.create_review_link(
        venue_id=venue_id,
        platform=body.platform,
        link_url=body.link_url
    )
    return link


@router.get("/reviews/links")
@limiter.limit("60/minute")
async def get_review_links(
    request: Request,
    db: Session = Depends(get_db),
    venue_id: int = Depends(get_current_venue)
):
    """Get review links."""
    from app.services.ab_testing_service import ReviewAutomationService

    service = ReviewAutomationService(db)
    links = await service.get_review_links(venue_id)
    return {"links": links}


@router.post("/reviews/requests")
@limiter.limit("30/minute")
async def send_review_request(
    request: Request,
    body: ReviewRequestRequest,
    db: Session = Depends(get_db),
    venue_id: int = Depends(get_current_venue)
):
    """Send a review request."""
    from app.services.ab_testing_service import ReviewAutomationService

    service = ReviewAutomationService(db)
    result = await service.send_review_request(
        venue_id=venue_id,
        order_id=body.order_id,
        customer_id=body.customer_id,
        method=body.method,
        delay_hours=body.delay_hours
    )
    return result


@router.get("/reviews/analytics")
@limiter.limit("60/minute")
async def get_review_analytics(
    request: Request,
    days: int = 30,
    db: Session = Depends(get_db),
    venue_id: int = Depends(get_current_venue)
):
    """Get review request analytics."""
    from app.services.ab_testing_service import ReviewAutomationService

    service = ReviewAutomationService(db)
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    analytics = await service.get_review_analytics(venue_id, start_date, end_date)
    return analytics


# ==================== SSO ENDPOINTS ====================

@router.post("/sso/configurations")
@limiter.limit("30/minute")
async def create_sso_config(
    request: Request,
    body: SSOConfigRequest,
    tenant_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """Create SSO configuration."""
    from app.services.sso_service import SSOService

    service = SSOService(db)
    config = await service.create_sso_config(
        tenant_id=tenant_id,
        provider_type=body.provider_type,
        display_name=body.display_name,
        config=body.config,
        domain_whitelist=body.domain_whitelist,
        auto_provision_users=body.auto_provision_users,
        default_role=body.default_role
    )
    return {"config_id": str(config.id), "provider": config.provider_type.value}


@router.get("/sso/configurations")
@limiter.limit("60/minute")
async def get_sso_config(
    request: Request,
    tenant_id: str = Query("", description="Tenant ID"),
    db: Session = Depends(get_db)
):
    """Get SSO configuration."""
    from app.services.sso_service import SSOService

    service = SSOService(db)
    config = await service.get_sso_config(tenant_id)
    if not config:
        raise HTTPException(status_code=404, detail="SSO configuration not found")

    return {
        "id": str(config.id),
        "provider_type": config.provider_type.value,
        "display_name": config.display_name,
        "domain_whitelist": config.domain_whitelist,
        "auto_provision_users": config.auto_provision_users,
        "default_role": config.default_role
    }


@router.get("/sso/login")
@limiter.limit("60/minute")
async def initiate_sso_login(
    request: Request,
    tenant_id: str = Query("", description="Tenant ID"),
    redirect_uri: str = Query("", description="Redirect URI after login"),
    db: Session = Depends(get_db)
):
    """Initiate SSO login flow."""
    if redirect_uri and not validate_redirect_uri(redirect_uri):
        raise HTTPException(status_code=400, detail="Invalid redirect URI")

    from app.services.sso_service import SSOService

    service = SSOService(db)
    config = await service.get_sso_config(tenant_id)
    if not config:
        raise HTTPException(status_code=404, detail="SSO configuration not found")

    if config.provider_type.value == "saml":
        result = await service.initiate_saml_login(config)
    else:
        result = await service.initiate_oauth_login(config, redirect_uri)

    return result


@router.post("/sso/callback")
@limiter.limit("30/minute")
async def handle_sso_callback(
    request: Request,
    tenant_id: str,
    code: Optional[str] = None,
    saml_response: Optional[str] = Body(None, alias="SAMLResponse"),
    redirect_uri: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Handle SSO callback."""
    if redirect_uri and not validate_redirect_uri(redirect_uri):
        raise HTTPException(status_code=400, detail="Invalid redirect URI")

    from app.services.sso_service import SSOService

    service = SSOService(db)
    config = await service.get_sso_config(tenant_id)
    if not config:
        raise HTTPException(status_code=404, detail="SSO configuration not found")

    if config.provider_type.value == "saml" and saml_response:
        result = await service.handle_saml_callback(config, saml_response)
    elif code and redirect_uri:
        result = await service.handle_oauth_callback(config, code, redirect_uri)
    else:
        raise HTTPException(status_code=400, detail="Invalid callback parameters")

    # Provision or find user
    user_id, is_new = await service.provision_sso_user(
        config,
        result["user_info"]
    )

    # Create session
    tokens = result.get("tokens", {})
    session = await service.create_sso_session(
        sso_config_id=config.id,
        user_id=user_id,
        provider_user_id=result["user_info"].get("sub", ""),
        tokens=tokens,
        user_info=result["user_info"]
    )

    return {
        "session_id": str(session.id),
        "user_id": str(user_id),
        "is_new_user": is_new,
        "user_info": result["user_info"]
    }


@router.post("/sso/logout")
@limiter.limit("30/minute")
async def sso_logout(
    request: Request,
    session_id: str,
    db: Session = Depends(get_db)
):
    """End SSO session."""
    from app.services.sso_service import SSOService

    service = SSOService(db)
    success = await service.end_sso_session(session_id)
    return {"status": "logged_out" if success else "session_not_found"}


# ==================== BACKGROUND WORKERS ====================

@router.get("/system/workers/stats")
@limiter.limit("60/minute")
async def get_worker_stats(
    request: Request,
    current_user: Staff = Depends(get_current_user)
):
    """
    Get background worker statistics.
    Requires admin privileges.
    """
    if current_user.role not in ["owner"]:
        raise HTTPException(status_code=403, detail="Admin access required")

    from app.services.background_workers import worker_manager
    return worker_manager.get_stats()


@router.post("/system/workers/schedule")
@limiter.limit("30/minute")
async def schedule_task(
    request: Request,
    task_type: str = Body(...),
    name: str = Body(...),
    payload: Dict[str, Any] = Body(default={}),
    delay_seconds: int = Body(default=0),
    priority: str = Body(default="normal"),
    current_user: Staff = Depends(get_current_user),
    venue = Depends(get_current_venue)
):
    """
    Schedule a background task.
    Requires admin privileges.
    """
    if current_user.role not in ["owner"]:
        raise HTTPException(status_code=403, detail="Admin access required")

    from app.services.background_workers import schedule_task as bg_schedule, TaskPriority

    priority_map = {
        "low": TaskPriority.LOW,
        "normal": TaskPriority.NORMAL,
        "high": TaskPriority.HIGH,
        "critical": TaskPriority.CRITICAL
    }

    task_id = await bg_schedule(
        task_type=task_type,
        name=name,
        payload=payload,
        venue_id=venue.id,
        delay_seconds=delay_seconds,
        priority=priority_map.get(priority, TaskPriority.NORMAL)
    )

    return {"task_id": task_id, "status": "scheduled"}


@router.get("/system/workers/task/{task_id}")
@limiter.limit("60/minute")
async def get_task_status(
    request: Request,
    task_id: str,
    current_user: Staff = Depends(get_current_user)
):
    """Get status of a background task."""
    if current_user.role not in ["owner"]:
        raise HTTPException(status_code=403, detail="Admin access required")

    from app.services.background_workers import worker_manager

    task = worker_manager.get_task_status(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "id": task.id,
        "name": task.name,
        "task_type": task.task_type,
        "status": task.status.value,
        "priority": task.priority.value,
        "scheduled_at": task.scheduled_at.isoformat() if task.scheduled_at else None,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "error_message": task.error_message,
        "retry_count": task.retry_count,
        "result": task.result
    }


@router.post("/system/workers/trigger/{task_type}")
@limiter.limit("30/minute")
async def trigger_task(
    request: Request,
    task_type: str,
    current_user: Staff = Depends(get_current_user),
    venue = Depends(get_current_venue)
):
    """
    Immediately trigger a specific task type.
    Requires admin privileges.
    """
    if current_user.role not in ["owner"]:
        raise HTTPException(status_code=403, detail="Admin access required")

    valid_tasks = [
        "process_review_requests",
        "check_experiment_significance",
        "check_compliance",
        "send_break_reminders",
        "check_device_health",
        "retry_failed_webhooks",
        "sync_7shifts",
        "sync_homebase",
        "sync_marginedge",
        "sync_accounting"
    ]

    if task_type not in valid_tasks:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid task type. Valid types: {', '.join(valid_tasks)}"
        )

    from app.services.background_workers import schedule_task as bg_schedule, TaskPriority

    task_id = await bg_schedule(
        task_type=task_type,
        name=f"Manual trigger: {task_type}",
        payload={"venue_id": venue.id},
        venue_id=venue.id,
        delay_seconds=0,
        priority=TaskPriority.HIGH
    )

    return {"task_id": task_id, "status": "triggered"}

"""Marketplace apps & integrations"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from app.core.rate_limit import limiter
from app.db.session import get_db

# Import shared schemas and helpers
from app.api.routes.gap_features._shared import *

router = APIRouter()

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


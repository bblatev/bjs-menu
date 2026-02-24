"""Zapier/Make.com Automation Webhook Connector API routes.

Provides endpoints for:
- Subscription management (create, update, delete webhook subscriptions)
- Event triggering (fire events to subscriptions)
- Incoming action processing (receive actions from Zapier/Make)
- Event log and statistics
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.rate_limit import limiter
from app.core.rbac import CurrentUser, RequireManager
from app.services.zapier_service import get_zapier_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ---- Schemas ----

class CreateSubscriptionRequest(BaseModel):
    name: str
    webhook_url: str
    events: List[str]
    platform: str = "zapier"
    secret: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, str]] = None


class UpdateSubscriptionRequest(BaseModel):
    name: Optional[str] = None
    webhook_url: Optional[str] = None
    events: Optional[List[str]] = None
    is_active: Optional[bool] = None
    filters: Optional[Dict[str, Any]] = None


class TriggerEventRequest(BaseModel):
    event_type: str
    payload: Dict[str, Any]


class IncomingActionRequest(BaseModel):
    action_type: str
    payload: Dict[str, Any]
    platform: str = "zapier"


# ---- Routes ----

@router.get("/")
@limiter.limit("60/minute")
async def automation_overview(request: Request):
    """Automation webhook connector overview."""
    svc = get_zapier_service()
    return svc.get_stats()


# ---- Subscriptions ----

@router.post("/subscriptions")
@limiter.limit("20/minute")
async def create_subscription(request: Request, body: CreateSubscriptionRequest, user: RequireManager):
    """Create a new webhook subscription."""
    svc = get_zapier_service()
    result = svc.create_subscription(
        name=body.name,
        webhook_url=body.webhook_url,
        events=body.events,
        platform=body.platform,
        secret=body.secret,
        filters=body.filters,
        headers=body.headers,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"success": True, "subscription": result}


@router.get("/subscriptions")
@limiter.limit("30/minute")
async def list_subscriptions(
    request: Request,
    user: RequireManager,
    platform: Optional[str] = None,
    is_active: Optional[bool] = None,
):
    """List all webhook subscriptions."""
    svc = get_zapier_service()
    return {"subscriptions": svc.list_subscriptions(platform=platform, is_active=is_active)}


@router.get("/subscriptions/{sub_id}")
@limiter.limit("60/minute")
async def get_subscription(request: Request, sub_id: int, user: RequireManager):
    """Get subscription details."""
    svc = get_zapier_service()
    result = svc.get_subscription(sub_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.put("/subscriptions/{sub_id}")
@limiter.limit("20/minute")
async def update_subscription(request: Request, sub_id: int, body: UpdateSubscriptionRequest, user: RequireManager):
    """Update a webhook subscription."""
    svc = get_zapier_service()
    result = svc.update_subscription(
        sub_id, name=body.name, webhook_url=body.webhook_url,
        events=body.events, is_active=body.is_active, filters=body.filters,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"success": True, "subscription": result}


@router.delete("/subscriptions/{sub_id}")
@limiter.limit("20/minute")
async def delete_subscription(request: Request, sub_id: int, user: RequireManager):
    """Delete a webhook subscription."""
    svc = get_zapier_service()
    result = svc.delete_subscription(sub_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ---- Events ----

@router.post("/trigger")
@limiter.limit("60/minute")
async def trigger_event(request: Request, body: TriggerEventRequest, user: CurrentUser):
    """Manually trigger an event (for testing or manual workflows)."""
    svc = get_zapier_service()
    result = await svc.trigger_event(body.event_type, body.payload)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"success": True, **result}


@router.get("/events")
@limiter.limit("30/minute")
async def get_event_log(
    request: Request,
    user: RequireManager,
    limit: int = 50,
    event_type: Optional[str] = None,
):
    """Get event trigger log."""
    svc = get_zapier_service()
    return {"events": svc.get_event_log(limit=limit, event_type=event_type)}


@router.get("/events/types")
@limiter.limit("60/minute")
async def get_event_types(request: Request):
    """List all available trigger event types."""
    from app.services.zapier_service import TRIGGER_EVENTS
    return {"event_types": TRIGGER_EVENTS}


@router.get("/actions/types")
@limiter.limit("60/minute")
async def get_action_types(request: Request):
    """List all available incoming action types."""
    from app.services.zapier_service import ACTION_TYPES
    return {"action_types": ACTION_TYPES}


# ---- Incoming Actions ----

@router.post("/actions/incoming")
@limiter.limit("60/minute")
async def receive_action(request: Request, body: IncomingActionRequest):
    """Receive and process an incoming action from Zapier/Make."""
    svc = get_zapier_service()
    # Optionally verify signature
    signature = request.headers.get("x-bjs-signature", "")
    if signature:
        raw_body = await request.body()
        secret = getattr(settings, "automation_webhook_secret", "")
        if secret and not svc.verify_incoming_webhook(raw_body, signature, secret):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    result = svc.process_incoming_action(
        action_type=body.action_type,
        payload=body.payload,
        platform=body.platform,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

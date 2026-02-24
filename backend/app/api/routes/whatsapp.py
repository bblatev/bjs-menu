"""WhatsApp Business API routes.

Provides endpoints for:
- Sending messages (text, template, interactive, media)
- Business-specific messages (order confirmation, reservation, waitlist)
- Webhook handling (incoming messages and status updates)
- Menu sharing via WhatsApp
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.core.rate_limit import limiter
from app.core.rbac import CurrentUser, RequireManager
from app.services.whatsapp_service import get_whatsapp_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ---- Schemas ----

class SendTextRequest(BaseModel):
    to: str = Field(..., description="Phone number in E.164 format")
    text: str
    preview_url: bool = False


class SendTemplateRequest(BaseModel):
    to: str
    template_name: str
    language_code: str = "en"
    components: Optional[List[Dict[str, Any]]] = None


class SendButtonRequest(BaseModel):
    to: str
    body_text: str
    buttons: List[Dict[str, str]]
    header: Optional[str] = None
    footer: Optional[str] = None


class SendListRequest(BaseModel):
    to: str
    body_text: str
    button_text: str
    sections: List[Dict[str, Any]]
    header: Optional[str] = None
    footer: Optional[str] = None


class SendImageRequest(BaseModel):
    to: str
    image_url: str
    caption: Optional[str] = None


class OrderConfirmationRequest(BaseModel):
    to: str
    order_id: int
    items: List[Dict[str, Any]]
    total: float
    estimated_time: Optional[int] = None


class ReservationConfirmationRequest(BaseModel):
    to: str
    guest_name: str
    date: str
    time: str
    party_size: int
    confirmation_code: str


class WaitlistUpdateRequest(BaseModel):
    to: str
    guest_name: str
    position: int
    estimated_wait: int


class TableReadyRequest(BaseModel):
    to: str
    guest_name: str
    table_number: Optional[str] = None


class SendMenuRequest(BaseModel):
    to: str
    categories: List[Dict[str, Any]]


# ---- Routes ----

@router.get("/")
@limiter.limit("60/minute")
async def whatsapp_overview(request: Request):
    """WhatsApp integration status."""
    svc = get_whatsapp_service()
    return {
        "provider": "whatsapp_business",
        "configured": svc.is_configured,
        "endpoints": [
            "POST /whatsapp/send/text",
            "POST /whatsapp/send/template",
            "POST /whatsapp/send/buttons",
            "POST /whatsapp/send/list",
            "POST /whatsapp/send/image",
            "POST /whatsapp/send/order-confirmation",
            "POST /whatsapp/send/reservation-confirmation",
            "POST /whatsapp/send/waitlist-update",
            "POST /whatsapp/send/table-ready",
            "POST /whatsapp/send/menu",
            "GET /whatsapp/webhook - Verification",
            "POST /whatsapp/webhook - Incoming messages",
            "GET /whatsapp/log - Message log",
        ],
    }


# ---- Sending ----

@router.post("/send/text")
@limiter.limit("30/minute")
async def send_text(request: Request, body: SendTextRequest, user: CurrentUser):
    """Send a plain text message via WhatsApp."""
    svc = get_whatsapp_service()
    result = await svc.send_text(body.to, body.text, body.preview_url)
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error", "Send failed"))
    return result


@router.post("/send/template")
@limiter.limit("30/minute")
async def send_template(request: Request, body: SendTemplateRequest, user: CurrentUser):
    """Send a pre-approved template message."""
    svc = get_whatsapp_service()
    result = await svc.send_template(body.to, body.template_name, body.language_code, body.components)
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error", "Send failed"))
    return result


@router.post("/send/buttons")
@limiter.limit("30/minute")
async def send_buttons(request: Request, body: SendButtonRequest, user: CurrentUser):
    """Send a message with interactive reply buttons."""
    svc = get_whatsapp_service()
    result = await svc.send_button_message(body.to, body.body_text, body.buttons, body.header, body.footer)
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error", "Send failed"))
    return result


@router.post("/send/list")
@limiter.limit("30/minute")
async def send_list(request: Request, body: SendListRequest, user: CurrentUser):
    """Send a list selection message."""
    svc = get_whatsapp_service()
    result = await svc.send_list_message(body.to, body.body_text, body.button_text, body.sections, body.header, body.footer)
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error", "Send failed"))
    return result


@router.post("/send/image")
@limiter.limit("30/minute")
async def send_image(request: Request, body: SendImageRequest, user: CurrentUser):
    """Send an image message."""
    svc = get_whatsapp_service()
    result = await svc.send_image(body.to, body.image_url, body.caption)
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error", "Send failed"))
    return result


# ---- Business Messages ----

@router.post("/send/order-confirmation")
@limiter.limit("30/minute")
async def send_order_confirmation(request: Request, body: OrderConfirmationRequest, user: CurrentUser):
    """Send order confirmation via WhatsApp."""
    svc = get_whatsapp_service()
    result = await svc.send_order_confirmation(body.to, body.order_id, body.items, body.total, body.estimated_time)
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error", "Send failed"))
    return result


@router.post("/send/reservation-confirmation")
@limiter.limit("30/minute")
async def send_reservation_confirmation(request: Request, body: ReservationConfirmationRequest, user: CurrentUser):
    """Send reservation confirmation via WhatsApp."""
    svc = get_whatsapp_service()
    result = await svc.send_reservation_confirmation(
        body.to, body.guest_name, body.date, body.time, body.party_size, body.confirmation_code,
    )
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error", "Send failed"))
    return result


@router.post("/send/waitlist-update")
@limiter.limit("60/minute")
async def send_waitlist_update(request: Request, body: WaitlistUpdateRequest, user: CurrentUser):
    """Send waitlist position update via WhatsApp."""
    svc = get_whatsapp_service()
    result = await svc.send_waitlist_update(body.to, body.guest_name, body.position, body.estimated_wait)
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error", "Send failed"))
    return result


@router.post("/send/table-ready")
@limiter.limit("60/minute")
async def send_table_ready(request: Request, body: TableReadyRequest, user: CurrentUser):
    """Notify guest their table is ready via WhatsApp."""
    svc = get_whatsapp_service()
    result = await svc.send_table_ready(body.to, body.guest_name, body.table_number)
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error", "Send failed"))
    return result


@router.post("/send/menu")
@limiter.limit("20/minute")
async def send_menu(request: Request, body: SendMenuRequest, user: CurrentUser):
    """Send interactive menu for WhatsApp ordering."""
    svc = get_whatsapp_service()
    result = await svc.send_menu(body.to, body.categories)
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error", "Send failed"))
    return result


# ---- Webhook ----

@router.get("/webhook")
async def verify_webhook(
    request: Request,
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    """WhatsApp webhook verification (GET from Meta)."""
    svc = get_whatsapp_service()
    if hub_mode and hub_verify_token:
        challenge = svc.verify_webhook(hub_mode, hub_verify_token, hub_challenge or "")
        if challenge:
            from fastapi.responses import PlainTextResponse
            return PlainTextResponse(challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook")
async def handle_webhook(request: Request):
    """Handle incoming WhatsApp messages and status updates."""
    svc = get_whatsapp_service()
    body = await request.json()
    messages = svc.parse_webhook(body)

    for msg in messages:
        msg_type = msg.get("type")
        if msg_type == "text":
            logger.info(f"WhatsApp text from {msg.get('from')}: {msg.get('text', '')[:50]}")
        elif msg_type == "interactive":
            logger.info(f"WhatsApp interactive from {msg.get('from')}: button={msg.get('button_id')} list={msg.get('list_id')}")
        elif msg_type == "status":
            logger.debug(f"WhatsApp status: {msg.get('status')} for {msg.get('message_id')}")

    return {"status": "processed", "messages_received": len(messages)}


# ---- Log ----

@router.get("/log")
@limiter.limit("30/minute")
async def get_message_log(request: Request, user: RequireManager, limit: int = 50):
    """Get WhatsApp message send log."""
    svc = get_whatsapp_service()
    return {"messages": svc.get_message_log(limit=limit)}

"""Customer-Facing Display API routes.

Provides endpoints for:
- Display registration and management
- Pole display operations (item, total, message)
- Second screen content (order view, tip prompt, promo, welcome)
- Screen content polling for tablets/monitors
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.rate_limit import limiter
from app.core.rbac import CurrentUser, RequireManager
from app.services.customer_display_service import get_customer_display_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ---- Schemas ----

class RegisterDisplayRequest(BaseModel):
    display_id: str
    name: str
    display_type: str = Field("pole", pattern="^(pole|tablet|monitor|kiosk)$")
    connection_type: str = Field("serial", pattern="^(serial|usb|network|websocket)$")
    host: Optional[str] = None
    port: Optional[int] = None
    serial_port: Optional[str] = None
    baud_rate: int = 9600
    width: int = 20
    lines: int = 2


class ShowItemRequest(BaseModel):
    display_id: str
    item_name: str
    price: float


class ShowTotalRequest(BaseModel):
    display_id: str
    label: str = "TOTAL"
    amount: float


class ShowMessageRequest(BaseModel):
    display_id: str
    line1: str
    line2: str = ""


class OrderDisplayRequest(BaseModel):
    display_id: str
    items: List[Dict[str, Any]]
    subtotal: float
    tax: float
    total: float
    tip: float = 0
    discount: float = 0


class TipPromptRequest(BaseModel):
    display_id: str
    total: float
    presets: Optional[List[int]] = None


class WelcomeScreenRequest(BaseModel):
    display_id: str
    venue_name: str
    message: str = "Welcome!"
    logo_url: Optional[str] = None


class PromotionalRequest(BaseModel):
    display_id: str
    slides: List[Dict[str, Any]]
    interval_seconds: int = 10


class ThankYouRequest(BaseModel):
    display_id: str
    message: str = "Thank you for your visit!"
    survey_url: Optional[str] = None


# ---- Routes ----

@router.get("/")
@limiter.limit("60/minute")
async def displays_overview(request: Request):
    """Customer display service overview."""
    svc = get_customer_display_service()
    return {
        "module": "customer-displays",
        "registered_displays": len(svc.list_displays()),
        "display_types": ["pole (VFD/LCD)", "tablet", "monitor", "kiosk"],
        "connection_types": ["serial", "usb", "network", "websocket"],
    }


# ---- Display Management ----

@router.post("/displays")
@limiter.limit("10/minute")
async def register_display(request: Request, body: RegisterDisplayRequest, user: RequireManager):
    """Register a customer-facing display."""
    svc = get_customer_display_service()
    return svc.register_display(
        display_id=body.display_id, name=body.name,
        display_type=body.display_type, connection_type=body.connection_type,
        host=body.host, port=body.port,
        serial_port=body.serial_port, baud_rate=body.baud_rate,
        width=body.width, lines=body.lines,
    )


@router.get("/displays")
@limiter.limit("60/minute")
async def list_displays(request: Request, user: CurrentUser):
    """List all registered displays."""
    svc = get_customer_display_service()
    return {"displays": svc.list_displays()}


@router.get("/displays/{display_id}")
@limiter.limit("60/minute")
async def get_display(request: Request, display_id: str, user: CurrentUser):
    """Get display details."""
    svc = get_customer_display_service()
    d = svc.get_display(display_id)
    if not d:
        raise HTTPException(status_code=404, detail="Display not found")
    return d


@router.delete("/displays/{display_id}")
@limiter.limit("10/minute")
async def remove_display(request: Request, display_id: str, user: RequireManager):
    """Remove a display."""
    svc = get_customer_display_service()
    result = svc.remove_display(display_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ---- Pole Display Operations ----

@router.post("/pole/item")
@limiter.limit("120/minute")
async def show_item(request: Request, body: ShowItemRequest, user: CurrentUser):
    """Show item being added on pole display."""
    svc = get_customer_display_service()
    result = svc.show_item(body.display_id, body.item_name, body.price)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/pole/total")
@limiter.limit("120/minute")
async def show_total(request: Request, body: ShowTotalRequest, user: CurrentUser):
    """Show total on pole display."""
    svc = get_customer_display_service()
    result = svc.show_total(body.display_id, body.label, body.amount)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/pole/message")
@limiter.limit("60/minute")
async def show_message(request: Request, body: ShowMessageRequest, user: CurrentUser):
    """Show custom message on pole display."""
    svc = get_customer_display_service()
    result = svc.show_message(body.display_id, body.line1, body.line2)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/pole/{display_id}/clear")
@limiter.limit("60/minute")
async def clear_pole_display(request: Request, display_id: str, user: CurrentUser):
    """Clear pole display."""
    svc = get_customer_display_service()
    result = svc.clear_display(display_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ---- Second Screen Content ----

@router.post("/screen/order")
@limiter.limit("60/minute")
async def display_order(request: Request, body: OrderDisplayRequest, user: CurrentUser):
    """Show order details on second screen."""
    svc = get_customer_display_service()
    return svc.display_order(
        body.display_id, body.items, body.subtotal,
        body.tax, body.total, body.tip, body.discount,
    )


@router.post("/screen/tip")
@limiter.limit("60/minute")
async def display_tip_prompt(request: Request, body: TipPromptRequest, user: CurrentUser):
    """Show tip selection on second screen."""
    svc = get_customer_display_service()
    return svc.display_tip_prompt(body.display_id, body.total, body.presets)


@router.post("/screen/welcome")
@limiter.limit("30/minute")
async def display_welcome(request: Request, body: WelcomeScreenRequest, user: CurrentUser):
    """Show welcome/idle screen."""
    svc = get_customer_display_service()
    return svc.display_welcome(body.display_id, body.venue_name, body.message, body.logo_url)


@router.post("/screen/promotional")
@limiter.limit("20/minute")
async def display_promotional(request: Request, body: PromotionalRequest, user: RequireManager):
    """Show promotional slideshow on second screen."""
    svc = get_customer_display_service()
    return svc.display_promotional(body.display_id, body.slides, body.interval_seconds)


@router.post("/screen/thankyou")
@limiter.limit("60/minute")
async def display_thank_you(request: Request, body: ThankYouRequest, user: CurrentUser):
    """Show thank-you screen after payment."""
    svc = get_customer_display_service()
    return svc.display_thank_you(body.display_id, body.message, body.survey_url)


# ---- Content Polling (for tablets/monitors) ----

@router.get("/screen/{display_id}/content")
@limiter.limit("120/minute")
async def get_screen_content(request: Request, display_id: str):
    """Poll current screen content (for tablet/monitor displays - no auth required)."""
    svc = get_customer_display_service()
    return svc.get_screen_content(display_id)


# ---- Log ----

@router.get("/log")
@limiter.limit("30/minute")
async def get_display_log(
    request: Request, user: CurrentUser,
    display_id: Optional[str] = None, limit: int = 50,
):
    """Get display activity log."""
    svc = get_customer_display_service()
    return {"log": svc.get_display_log(display_id=display_id, limit=limit)}

"""Email Campaign Builder API routes.

Visual email campaign builder with templates, segmentation, and tracking.
"""

from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from app.services.email_campaign_service import (
    get_email_campaign_service,
    CampaignStatus,
)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class TemplateBlockRequest(BaseModel):
    block_id: Optional[str] = None
    type: str  # header, text, image, button, divider, coupon, footer
    content: dict
    styles: dict = {}
    order: int = 0


class CreateTemplateRequest(BaseModel):
    name: str
    subject: str
    preview_text: str = ""
    blocks: List[TemplateBlockRequest] = []
    global_styles: dict = {}


class UpdateTemplateRequest(BaseModel):
    name: Optional[str] = None
    subject: Optional[str] = None
    preview_text: Optional[str] = None
    blocks: Optional[List[TemplateBlockRequest]] = None
    global_styles: Optional[dict] = None


class TemplateResponse(BaseModel):
    template_id: str
    name: str
    subject: str
    preview_text: str
    blocks: List[dict]
    global_styles: dict
    created_at: str
    updated_at: str


class SegmentRuleRequest(BaseModel):
    field: str  # last_order_date, total_spent, visit_count, etc.
    operator: str  # equals, not_equals, greater_than, less_than, contains, in_list, between
    value: str | int | float | list


class CreateSegmentRequest(BaseModel):
    name: str
    description: str = ""
    rules: List[SegmentRuleRequest] = []
    rule_logic: str = "AND"  # AND or OR


class SegmentResponse(BaseModel):
    segment_id: str
    name: str
    description: str
    rules: List[dict]
    rule_logic: str
    customer_count: int
    created_at: str


class CreateCampaignRequest(BaseModel):
    name: str
    subject: str
    preview_text: str = ""
    template_id: Optional[str] = None
    segment_id: Optional[str] = None
    venue_id: Optional[int] = None


class UpdateCampaignRequest(BaseModel):
    name: Optional[str] = None
    subject: Optional[str] = None
    preview_text: Optional[str] = None
    template_id: Optional[str] = None
    segment_id: Optional[str] = None


class ScheduleCampaignRequest(BaseModel):
    scheduled_at: str  # ISO format datetime


class TestSendRequest(BaseModel):
    emails: List[str]


class CampaignResponse(BaseModel):
    campaign_id: str
    name: str
    subject: str
    preview_text: str
    template_id: Optional[str] = None
    segment_id: Optional[str] = None
    venue_id: Optional[int] = None
    status: str
    scheduled_at: Optional[str] = None
    sent_at: Optional[str] = None
    total_recipients: int
    sent_count: int
    opened_count: int
    clicked_count: int
    created_at: str
    updated_at: str


class CampaignStatsResponse(BaseModel):
    campaign_id: str
    status: str
    total_recipients: int
    sent_count: int
    delivered_count: int
    opened_count: int
    clicked_count: int
    bounced_count: int
    unsubscribed_count: int
    open_rate: float
    click_rate: float


# ============================================================================
# Templates
# ============================================================================

@router.post("/templates", response_model=TemplateResponse)
async def create_template(request: CreateTemplateRequest):
    """
    Create a new email template.

    Templates use blocks for visual building:
    - header: Logo and title
    - text: Paragraph text
    - image: Image with alt text
    - button: Call-to-action button
    - divider: Horizontal line
    - coupon: Discount code display
    - footer: Address and unsubscribe link

    Use {{variable}} placeholders for personalization.
    """
    service = get_email_campaign_service()

    blocks = [block.model_dump() for block in request.blocks]

    template = service.create_template(
        name=request.name,
        subject=request.subject,
        preview_text=request.preview_text,
        blocks=blocks,
        global_styles=request.global_styles,
    )

    return _template_to_response(template)


@router.get("/templates", response_model=List[TemplateResponse])
async def list_templates():
    """List all email templates."""
    service = get_email_campaign_service()
    templates = service.list_templates()

    return [_template_to_response(t) for t in templates]


@router.get("/templates/{template_id}", response_model=TemplateResponse)
async def get_template(template_id: str):
    """Get a specific template."""
    service = get_email_campaign_service()
    template = service.get_template(template_id)

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return _template_to_response(template)


@router.put("/templates/{template_id}", response_model=TemplateResponse)
async def update_template(template_id: str, request: UpdateTemplateRequest):
    """Update a template."""
    service = get_email_campaign_service()

    updates = {}
    if request.name is not None:
        updates["name"] = request.name
    if request.subject is not None:
        updates["subject"] = request.subject
    if request.preview_text is not None:
        updates["preview_text"] = request.preview_text
    if request.blocks is not None:
        updates["blocks"] = [block.model_dump() for block in request.blocks]
    if request.global_styles is not None:
        updates["global_styles"] = request.global_styles

    template = service.update_template(template_id, **updates)

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return _template_to_response(template)


@router.delete("/templates/{template_id}")
async def delete_template(template_id: str):
    """Delete a template."""
    service = get_email_campaign_service()

    if not service.delete_template(template_id):
        raise HTTPException(status_code=404, detail="Template not found")

    return {"success": True, "message": "Template deleted"}


@router.post("/templates/{template_id}/preview")
async def preview_template(template_id: str, variables: dict = {}):
    """
    Preview a rendered template with variables.

    Pass variables to replace {{placeholders}} in the template.
    """
    service = get_email_campaign_service()

    template = service.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    html = service.render_template(template_id, variables)

    return {
        "template_id": template_id,
        "subject": service._replace_vars(template.subject, variables),
        "preview_text": service._replace_vars(template.preview_text, variables),
        "html": html,
    }


# ============================================================================
# Segments
# ============================================================================

@router.post("/segments", response_model=SegmentResponse)
async def create_segment(request: CreateSegmentRequest):
    """
    Create a customer segment.

    Rules define which customers belong to this segment:
    - field: Customer attribute (total_spent, visit_count, last_order_date, etc.)
    - operator: equals, not_equals, greater_than, less_than, contains, in_list, between
    - value: The value to compare against

    rule_logic: "AND" (all rules must match) or "OR" (any rule must match)
    """
    service = get_email_campaign_service()

    rules = [rule.model_dump() for rule in request.rules]

    segment = service.create_segment(
        name=request.name,
        description=request.description,
        rules=rules,
        rule_logic=request.rule_logic,
    )

    return _segment_to_response(segment)


@router.get("/segments", response_model=List[SegmentResponse])
async def list_segments():
    """List all customer segments."""
    service = get_email_campaign_service()
    segments = service.list_segments()

    return [_segment_to_response(s) for s in segments]


@router.get("/segments/{segment_id}", response_model=SegmentResponse)
async def get_segment(segment_id: str):
    """Get a specific segment."""
    service = get_email_campaign_service()
    segment = service.get_segment(segment_id)

    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")

    return _segment_to_response(segment)


@router.delete("/segments/{segment_id}")
async def delete_segment(segment_id: str):
    """Delete a segment."""
    service = get_email_campaign_service()

    if not service.delete_segment(segment_id):
        raise HTTPException(status_code=404, detail="Segment not found")

    return {"success": True, "message": "Segment deleted"}


# ============================================================================
# Campaigns
# ============================================================================

@router.post("/campaigns", response_model=CampaignResponse)
async def create_campaign(request: CreateCampaignRequest):
    """Create a new email campaign."""
    service = get_email_campaign_service()

    campaign = service.create_campaign(
        name=request.name,
        subject=request.subject,
        preview_text=request.preview_text,
        template_id=request.template_id,
        segment_id=request.segment_id,
        venue_id=request.venue_id,
    )

    return _campaign_to_response(campaign)


@router.get("/campaigns", response_model=List[CampaignResponse])
async def list_campaigns(
    status: Optional[str] = None,
    venue_id: Optional[int] = None,
):
    """List campaigns."""
    service = get_email_campaign_service()

    campaign_status = None
    if status:
        try:
            campaign_status = CampaignStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    campaigns = service.list_campaigns(status=campaign_status, venue_id=venue_id)

    return [_campaign_to_response(c) for c in campaigns]


@router.get("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(campaign_id: str):
    """Get a specific campaign."""
    service = get_email_campaign_service()
    campaign = service.get_campaign(campaign_id)

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    return _campaign_to_response(campaign)


@router.put("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(campaign_id: str, request: UpdateCampaignRequest):
    """Update a campaign."""
    service = get_email_campaign_service()

    updates = {}
    if request.name is not None:
        updates["name"] = request.name
    if request.subject is not None:
        updates["subject"] = request.subject
    if request.preview_text is not None:
        updates["preview_text"] = request.preview_text
    if request.template_id is not None:
        updates["template_id"] = request.template_id
    if request.segment_id is not None:
        updates["segment_id"] = request.segment_id

    campaign = service.update_campaign(campaign_id, **updates)

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    return _campaign_to_response(campaign)


@router.delete("/campaigns/{campaign_id}")
async def delete_campaign(campaign_id: str):
    """Delete a campaign."""
    service = get_email_campaign_service()

    if not service.delete_campaign(campaign_id):
        raise HTTPException(status_code=404, detail="Campaign not found")

    return {"success": True, "message": "Campaign deleted"}


@router.post("/campaigns/{campaign_id}/schedule", response_model=CampaignResponse)
async def schedule_campaign(campaign_id: str, request: ScheduleCampaignRequest):
    """Schedule a campaign for future sending."""
    service = get_email_campaign_service()

    try:
        scheduled_at = datetime.fromisoformat(request.scheduled_at.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid datetime format. Use ISO format.")

    if scheduled_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Scheduled time must be in the future")

    campaign = service.schedule_campaign(campaign_id, scheduled_at)

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    return _campaign_to_response(campaign)


@router.post("/campaigns/{campaign_id}/send")
async def send_campaign(campaign_id: str):
    """Send a campaign immediately."""
    service = get_email_campaign_service()

    result = await service.send_campaign(campaign_id)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to send"))

    return result


@router.post("/campaigns/{campaign_id}/test")
async def test_send_campaign(campaign_id: str, request: TestSendRequest):
    """
    Send a test campaign to specific email addresses.

    Use this to preview how the email will look before sending to all recipients.
    """
    service = get_email_campaign_service()

    if not request.emails:
        raise HTTPException(status_code=400, detail="At least one email is required")

    result = await service.send_campaign(campaign_id, test_emails=request.emails)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to send"))

    return result


@router.get("/campaigns/{campaign_id}/stats", response_model=CampaignStatsResponse)
async def get_campaign_stats(campaign_id: str):
    """Get campaign statistics (opens, clicks, bounces, etc.)."""
    service = get_email_campaign_service()

    stats = service.get_campaign_stats(campaign_id)

    if not stats:
        raise HTTPException(status_code=404, detail="Campaign not found")

    return CampaignStatsResponse(**stats)


# ============================================================================
# Block Types Info
# ============================================================================

@router.get("/block-types")
async def get_block_types():
    """Get available template block types."""
    return {
        "types": [
            {
                "id": "header",
                "name": "Header",
                "description": "Logo and title block",
                "content_fields": ["logo_url", "title"],
            },
            {
                "id": "text",
                "name": "Text",
                "description": "Paragraph text content",
                "content_fields": ["text"],
            },
            {
                "id": "image",
                "name": "Image",
                "description": "Image with optional alt text",
                "content_fields": ["url", "alt"],
            },
            {
                "id": "button",
                "name": "Button",
                "description": "Call-to-action button",
                "content_fields": ["text", "url"],
            },
            {
                "id": "divider",
                "name": "Divider",
                "description": "Horizontal separator line",
                "content_fields": [],
            },
            {
                "id": "columns",
                "name": "Columns",
                "description": "Multi-column layout",
                "content_fields": ["columns"],
            },
            {
                "id": "product_grid",
                "name": "Product Grid",
                "description": "Grid of menu items",
                "content_fields": ["items"],
            },
            {
                "id": "coupon",
                "name": "Coupon",
                "description": "Discount code display",
                "content_fields": ["code", "discount", "description", "expires"],
            },
            {
                "id": "social",
                "name": "Social Links",
                "description": "Social media links",
                "content_fields": ["facebook", "instagram", "twitter"],
            },
            {
                "id": "footer",
                "name": "Footer",
                "description": "Address and unsubscribe link",
                "content_fields": ["address", "phone", "unsubscribe_url"],
            },
        ],
        "variables": [
            {"name": "customer_name", "description": "Recipient's name"},
            {"name": "customer_email", "description": "Recipient's email"},
            {"name": "venue_name", "description": "Restaurant name"},
            {"name": "venue_address", "description": "Restaurant address"},
            {"name": "venue_phone", "description": "Restaurant phone"},
            {"name": "logo_url", "description": "Restaurant logo URL"},
            {"name": "order_url", "description": "Online ordering URL"},
            {"name": "reservation_url", "description": "Reservation URL"},
            {"name": "unsubscribe_url", "description": "Unsubscribe URL"},
        ],
    }


# ============================================================================
# Helper Functions
# ============================================================================

def _template_to_response(template) -> TemplateResponse:
    """Convert template to response model."""
    return TemplateResponse(
        template_id=template.template_id,
        name=template.name,
        subject=template.subject,
        preview_text=template.preview_text,
        blocks=[
            {
                "block_id": b.block_id,
                "type": b.type.value,
                "content": b.content,
                "styles": b.styles,
                "order": b.order,
            }
            for b in template.blocks
        ],
        global_styles=template.global_styles,
        created_at=template.created_at.isoformat(),
        updated_at=template.updated_at.isoformat(),
    )


def _segment_to_response(segment) -> SegmentResponse:
    """Convert segment to response model."""
    return SegmentResponse(
        segment_id=segment.segment_id,
        name=segment.name,
        description=segment.description,
        rules=[
            {
                "field": r.field,
                "operator": r.operator.value,
                "value": r.value,
            }
            for r in segment.rules
        ],
        rule_logic=segment.rule_logic,
        customer_count=segment.customer_count,
        created_at=segment.created_at.isoformat(),
    )


def _campaign_to_response(campaign) -> CampaignResponse:
    """Convert campaign to response model."""
    return CampaignResponse(
        campaign_id=campaign.campaign_id,
        name=campaign.name,
        subject=campaign.subject,
        preview_text=campaign.preview_text,
        template_id=campaign.template_id,
        segment_id=campaign.segment_id,
        venue_id=campaign.venue_id,
        status=campaign.status.value,
        scheduled_at=campaign.scheduled_at.isoformat() if campaign.scheduled_at else None,
        sent_at=campaign.sent_at.isoformat() if campaign.sent_at else None,
        total_recipients=campaign.total_recipients,
        sent_count=campaign.sent_count,
        opened_count=campaign.opened_count,
        clicked_count=campaign.clicked_count,
        created_at=campaign.created_at.isoformat(),
        updated_at=campaign.updated_at.isoformat(),
    )

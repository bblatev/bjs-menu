"""Email Campaign Builder Service.

Visual email campaign builder with customer segmentation,
scheduling, and tracking capabilities.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import uuid
import json

logger = logging.getLogger(__name__)


class CampaignStatus(str, Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENDING = "sending"
    SENT = "sent"
    PAUSED = "paused"
    CANCELED = "canceled"


class SegmentOperator(str, Enum):
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    CONTAINS = "contains"
    IN_LIST = "in_list"
    BETWEEN = "between"


class TemplateBlockType(str, Enum):
    HEADER = "header"
    TEXT = "text"
    IMAGE = "image"
    BUTTON = "button"
    DIVIDER = "divider"
    COLUMNS = "columns"
    PRODUCT_GRID = "product_grid"
    COUPON = "coupon"
    SOCIAL = "social"
    FOOTER = "footer"


@dataclass
class TemplateBlock:
    """A block in an email template."""
    block_id: str
    type: TemplateBlockType
    content: Dict[str, Any]
    styles: Dict[str, str] = field(default_factory=dict)
    order: int = 0


@dataclass
class EmailTemplate:
    """An email template with visual blocks."""
    template_id: str
    name: str
    subject: str
    preview_text: str = ""
    blocks: List[TemplateBlock] = field(default_factory=list)
    global_styles: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SegmentRule:
    """A rule for customer segmentation."""
    field: str  # last_order_date, total_spent, visit_count, etc.
    operator: SegmentOperator
    value: Any


@dataclass
class CustomerSegment:
    """A customer segment definition."""
    segment_id: str
    name: str
    description: str = ""
    rules: List[SegmentRule] = field(default_factory=list)
    rule_logic: str = "AND"  # AND or OR
    customer_count: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Campaign:
    """An email campaign."""
    campaign_id: str
    name: str
    subject: str
    preview_text: str = ""
    template_id: Optional[str] = None
    segment_id: Optional[str] = None
    status: CampaignStatus = CampaignStatus.DRAFT
    scheduled_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    venue_id: Optional[int] = None

    # Stats
    total_recipients: int = 0
    sent_count: int = 0
    delivered_count: int = 0
    opened_count: int = 0
    clicked_count: int = 0
    bounced_count: int = 0
    unsubscribed_count: int = 0

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CampaignRecipient:
    """A campaign recipient record."""
    recipient_id: str
    campaign_id: str
    customer_id: int
    email: str
    status: str = "pending"  # pending, sent, delivered, opened, clicked, bounced
    sent_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    clicked_at: Optional[datetime] = None


class EmailCampaignService:
    """Service for managing email campaigns."""

    def __init__(self, notification_service=None):
        self.notification_service = notification_service

        # In-memory storage (use database in production)
        self._templates: Dict[str, EmailTemplate] = {}
        self._segments: Dict[str, CustomerSegment] = {}
        self._campaigns: Dict[str, Campaign] = {}
        self._recipients: Dict[str, List[CampaignRecipient]] = {}

        # Create default templates
        self._create_default_templates()

    # =========================================================================
    # Templates
    # =========================================================================

    def _create_default_templates(self):
        """Create default email templates."""
        # Welcome template
        welcome = EmailTemplate(
            template_id="tpl-welcome",
            name="Welcome Email",
            subject="Welcome to {{venue_name}}!",
            preview_text="Thank you for joining us",
            blocks=[
                TemplateBlock(
                    block_id="b1",
                    type=TemplateBlockType.HEADER,
                    content={"logo_url": "{{logo_url}}", "title": "Welcome!"},
                    order=0,
                ),
                TemplateBlock(
                    block_id="b2",
                    type=TemplateBlockType.TEXT,
                    content={
                        "text": "Dear {{customer_name}},\n\nThank you for joining {{venue_name}}! We're excited to have you as part of our community.",
                    },
                    order=1,
                ),
                TemplateBlock(
                    block_id="b3",
                    type=TemplateBlockType.COUPON,
                    content={
                        "code": "WELCOME10",
                        "discount": "10% OFF",
                        "description": "Your first order",
                        "expires": "{{expiry_date}}",
                    },
                    order=2,
                ),
                TemplateBlock(
                    block_id="b4",
                    type=TemplateBlockType.BUTTON,
                    content={"text": "Make a Reservation", "url": "{{reservation_url}}"},
                    order=3,
                ),
                TemplateBlock(
                    block_id="b5",
                    type=TemplateBlockType.FOOTER,
                    content={
                        "address": "{{venue_address}}",
                        "phone": "{{venue_phone}}",
                        "unsubscribe_url": "{{unsubscribe_url}}",
                    },
                    order=4,
                ),
            ],
        )
        self._templates["tpl-welcome"] = welcome

        # Promotion template
        promo = EmailTemplate(
            template_id="tpl-promotion",
            name="Promotional Email",
            subject="{{promo_title}} - Limited Time Offer!",
            preview_text="Don't miss out on this special deal",
            blocks=[
                TemplateBlock(
                    block_id="b1",
                    type=TemplateBlockType.HEADER,
                    content={"logo_url": "{{logo_url}}", "title": "{{promo_title}}"},
                    order=0,
                ),
                TemplateBlock(
                    block_id="b2",
                    type=TemplateBlockType.IMAGE,
                    content={"url": "{{promo_image}}", "alt": "Promotion"},
                    order=1,
                ),
                TemplateBlock(
                    block_id="b3",
                    type=TemplateBlockType.TEXT,
                    content={"text": "{{promo_description}}"},
                    order=2,
                ),
                TemplateBlock(
                    block_id="b4",
                    type=TemplateBlockType.BUTTON,
                    content={"text": "Order Now", "url": "{{order_url}}"},
                    order=3,
                ),
                TemplateBlock(
                    block_id="b5",
                    type=TemplateBlockType.FOOTER,
                    content={
                        "address": "{{venue_address}}",
                        "unsubscribe_url": "{{unsubscribe_url}}",
                    },
                    order=4,
                ),
            ],
        )
        self._templates["tpl-promotion"] = promo

    def create_template(
        self,
        name: str,
        subject: str,
        preview_text: str = "",
        blocks: Optional[List[Dict[str, Any]]] = None,
        global_styles: Optional[Dict[str, str]] = None,
    ) -> EmailTemplate:
        """Create a new email template."""
        template_id = f"tpl-{uuid.uuid4().hex[:8]}"

        template_blocks = []
        if blocks:
            for i, block in enumerate(blocks):
                template_blocks.append(TemplateBlock(
                    block_id=block.get("block_id", f"b{i}"),
                    type=TemplateBlockType(block.get("type", "text")),
                    content=block.get("content", {}),
                    styles=block.get("styles", {}),
                    order=block.get("order", i),
                ))

        template = EmailTemplate(
            template_id=template_id,
            name=name,
            subject=subject,
            preview_text=preview_text,
            blocks=template_blocks,
            global_styles=global_styles or {},
        )

        self._templates[template_id] = template
        logger.info(f"Created template {template_id}: {name}")

        return template

    def update_template(
        self,
        template_id: str,
        **updates,
    ) -> Optional[EmailTemplate]:
        """Update a template."""
        template = self._templates.get(template_id)
        if not template:
            return None

        for key, value in updates.items():
            if hasattr(template, key) and value is not None:
                if key == "blocks" and isinstance(value, list):
                    template_blocks = []
                    for i, block in enumerate(value):
                        template_blocks.append(TemplateBlock(
                            block_id=block.get("block_id", f"b{i}"),
                            type=TemplateBlockType(block.get("type", "text")),
                            content=block.get("content", {}),
                            styles=block.get("styles", {}),
                            order=block.get("order", i),
                        ))
                    template.blocks = template_blocks
                else:
                    setattr(template, key, value)

        template.updated_at = datetime.now(timezone.utc)
        return template

    def get_template(self, template_id: str) -> Optional[EmailTemplate]:
        """Get a template."""
        return self._templates.get(template_id)

    def list_templates(self) -> List[EmailTemplate]:
        """List all templates."""
        return list(self._templates.values())

    def delete_template(self, template_id: str) -> bool:
        """Delete a template."""
        if template_id in self._templates:
            del self._templates[template_id]
            return True
        return False

    def render_template(
        self,
        template_id: str,
        variables: Dict[str, str],
    ) -> str:
        """Render a template to HTML."""
        template = self._templates.get(template_id)
        if not template:
            return ""

        html = self._build_html(template, variables)
        return html

    def _build_html(
        self,
        template: EmailTemplate,
        variables: Dict[str, str],
    ) -> str:
        """Build HTML from template blocks."""
        # Simple HTML builder - in production use a proper template engine
        html_parts = [
            "<!DOCTYPE html>",
            '<html lang="en">',
            "<head>",
            '<meta charset="UTF-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
            f"<title>{self._replace_vars(template.subject, variables)}</title>",
            "<style>",
            "body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f4f4f4; }",
            ".container { max-width: 600px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }",
            ".header { text-align: center; padding: 20px 0; }",
            ".button { display: inline-block; padding: 12px 24px; background: #3b82f6; color: white; text-decoration: none; border-radius: 6px; }",
            ".footer { text-align: center; padding: 20px 0; color: #666; font-size: 12px; }",
            ".coupon { border: 2px dashed #f59e0b; padding: 15px; text-align: center; background: #fef3c7; border-radius: 8px; }",
            "</style>",
            "</head>",
            "<body>",
            '<div class="container">',
        ]

        sorted_blocks = sorted(template.blocks, key=lambda b: b.order)

        for block in sorted_blocks:
            content = block.content
            block_html = ""

            if block.type == TemplateBlockType.HEADER:
                logo = self._replace_vars(content.get("logo_url", ""), variables)
                title = self._replace_vars(content.get("title", ""), variables)
                block_html = f'<div class="header">'
                if logo:
                    block_html += f'<img src="{logo}" alt="Logo" style="max-width: 150px;">'
                if title:
                    block_html += f'<h1>{title}</h1>'
                block_html += '</div>'

            elif block.type == TemplateBlockType.TEXT:
                text = self._replace_vars(content.get("text", ""), variables)
                text = text.replace("\n", "<br>")
                block_html = f'<div style="padding: 10px 0;">{text}</div>'

            elif block.type == TemplateBlockType.IMAGE:
                url = self._replace_vars(content.get("url", ""), variables)
                alt = content.get("alt", "Image")
                block_html = f'<div style="text-align: center; padding: 10px 0;"><img src="{url}" alt="{alt}" style="max-width: 100%;"></div>'

            elif block.type == TemplateBlockType.BUTTON:
                text = self._replace_vars(content.get("text", "Click Here"), variables)
                url = self._replace_vars(content.get("url", "#"), variables)
                block_html = f'<div style="text-align: center; padding: 20px 0;"><a href="{url}" class="button">{text}</a></div>'

            elif block.type == TemplateBlockType.DIVIDER:
                block_html = '<hr style="border: none; border-top: 1px solid #e5e7eb; margin: 20px 0;">'

            elif block.type == TemplateBlockType.COUPON:
                code = self._replace_vars(content.get("code", ""), variables)
                discount = self._replace_vars(content.get("discount", ""), variables)
                description = self._replace_vars(content.get("description", ""), variables)
                expires = self._replace_vars(content.get("expires", ""), variables)
                block_html = f'''
                <div class="coupon">
                    <div style="font-size: 24px; font-weight: bold; color: #f59e0b;">{discount}</div>
                    <div style="margin: 10px 0;">{description}</div>
                    <div style="font-size: 18px; font-weight: bold; letter-spacing: 2px; background: white; padding: 10px; border-radius: 4px;">{code}</div>
                    <div style="font-size: 12px; margin-top: 10px; color: #666;">Expires: {expires}</div>
                </div>
                '''

            elif block.type == TemplateBlockType.FOOTER:
                address = self._replace_vars(content.get("address", ""), variables)
                phone = self._replace_vars(content.get("phone", ""), variables)
                unsubscribe = self._replace_vars(content.get("unsubscribe_url", "#"), variables)
                block_html = f'''
                <div class="footer">
                    <p>{address}</p>
                    <p>{phone}</p>
                    <p><a href="{unsubscribe}">Unsubscribe</a></p>
                </div>
                '''

            html_parts.append(block_html)

        html_parts.extend([
            "</div>",
            "</body>",
            "</html>",
        ])

        return "\n".join(html_parts)

    def _replace_vars(self, text: str, variables: Dict[str, str]) -> str:
        """Replace {{variable}} placeholders."""
        for key, value in variables.items():
            text = text.replace(f"{{{{{key}}}}}", str(value))
        return text

    # =========================================================================
    # Segments
    # =========================================================================

    def create_segment(
        self,
        name: str,
        description: str = "",
        rules: Optional[List[Dict[str, Any]]] = None,
        rule_logic: str = "AND",
    ) -> CustomerSegment:
        """Create a customer segment."""
        segment_id = f"seg-{uuid.uuid4().hex[:8]}"

        segment_rules = []
        if rules:
            for rule in rules:
                segment_rules.append(SegmentRule(
                    field=rule.get("field", ""),
                    operator=SegmentOperator(rule.get("operator", "equals")),
                    value=rule.get("value"),
                ))

        segment = CustomerSegment(
            segment_id=segment_id,
            name=name,
            description=description,
            rules=segment_rules,
            rule_logic=rule_logic,
        )

        self._segments[segment_id] = segment
        logger.info(f"Created segment {segment_id}: {name}")

        return segment

    def get_segment(self, segment_id: str) -> Optional[CustomerSegment]:
        """Get a segment."""
        return self._segments.get(segment_id)

    def list_segments(self) -> List[CustomerSegment]:
        """List all segments."""
        return list(self._segments.values())

    def delete_segment(self, segment_id: str) -> bool:
        """Delete a segment."""
        if segment_id in self._segments:
            del self._segments[segment_id]
            return True
        return False

    # =========================================================================
    # Campaigns
    # =========================================================================

    def create_campaign(
        self,
        name: str,
        subject: str,
        preview_text: str = "",
        template_id: Optional[str] = None,
        segment_id: Optional[str] = None,
        venue_id: Optional[int] = None,
    ) -> Campaign:
        """Create a new campaign."""
        campaign_id = f"camp-{uuid.uuid4().hex[:8]}"

        campaign = Campaign(
            campaign_id=campaign_id,
            name=name,
            subject=subject,
            preview_text=preview_text,
            template_id=template_id,
            segment_id=segment_id,
            venue_id=venue_id,
        )

        self._campaigns[campaign_id] = campaign
        logger.info(f"Created campaign {campaign_id}: {name}")

        return campaign

    def update_campaign(
        self,
        campaign_id: str,
        **updates,
    ) -> Optional[Campaign]:
        """Update a campaign."""
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            return None

        for key, value in updates.items():
            if hasattr(campaign, key) and value is not None:
                setattr(campaign, key, value)

        campaign.updated_at = datetime.now(timezone.utc)
        return campaign

    def get_campaign(self, campaign_id: str) -> Optional[Campaign]:
        """Get a campaign."""
        return self._campaigns.get(campaign_id)

    def list_campaigns(
        self,
        status: Optional[CampaignStatus] = None,
        venue_id: Optional[int] = None,
    ) -> List[Campaign]:
        """List campaigns."""
        campaigns = list(self._campaigns.values())

        if status:
            campaigns = [c for c in campaigns if c.status == status]

        if venue_id:
            campaigns = [c for c in campaigns if c.venue_id == venue_id]

        return sorted(campaigns, key=lambda c: c.created_at, reverse=True)

    def delete_campaign(self, campaign_id: str) -> bool:
        """Delete a campaign."""
        if campaign_id in self._campaigns:
            del self._campaigns[campaign_id]
            return True
        return False

    def schedule_campaign(
        self,
        campaign_id: str,
        scheduled_at: datetime,
    ) -> Optional[Campaign]:
        """Schedule a campaign for sending."""
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            return None

        campaign.scheduled_at = scheduled_at
        campaign.status = CampaignStatus.SCHEDULED
        campaign.updated_at = datetime.now(timezone.utc)

        return campaign

    async def send_campaign(
        self,
        campaign_id: str,
        test_emails: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Send a campaign (or test send)."""
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            return {"success": False, "error": "Campaign not found"}

        # If test emails provided, send only to those
        recipients = test_emails if test_emails else []

        # In production, you would:
        # 1. Query customers based on segment
        # 2. Render template for each recipient
        # 3. Send emails via notification service
        # 4. Track delivery status

        if not test_emails:
            campaign.status = CampaignStatus.SENDING
            # ... send to all segment recipients

        campaign.sent_count = len(recipients)
        campaign.sent_at = datetime.now(timezone.utc)

        if not test_emails:
            campaign.status = CampaignStatus.SENT

        return {
            "success": True,
            "campaign_id": campaign_id,
            "recipients_count": len(recipients),
            "is_test": bool(test_emails),
        }

    def get_campaign_stats(self, campaign_id: str) -> Dict[str, Any]:
        """Get campaign statistics."""
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            return {}

        open_rate = (campaign.opened_count / campaign.sent_count * 100) if campaign.sent_count > 0 else 0
        click_rate = (campaign.clicked_count / campaign.sent_count * 100) if campaign.sent_count > 0 else 0

        return {
            "campaign_id": campaign_id,
            "status": campaign.status.value,
            "total_recipients": campaign.total_recipients,
            "sent_count": campaign.sent_count,
            "delivered_count": campaign.delivered_count,
            "opened_count": campaign.opened_count,
            "clicked_count": campaign.clicked_count,
            "bounced_count": campaign.bounced_count,
            "unsubscribed_count": campaign.unsubscribed_count,
            "open_rate": round(open_rate, 2),
            "click_rate": round(click_rate, 2),
        }


# Singleton instance
_campaign_service: Optional[EmailCampaignService] = None


def get_email_campaign_service() -> EmailCampaignService:
    """Get the email campaign service singleton."""
    global _campaign_service
    if _campaign_service is None:
        _campaign_service = EmailCampaignService()
    return _campaign_service

"""WhatsApp Business API Integration Service.

Provides WhatsApp Cloud API integration for:
- Sending order confirmations, reservation confirmations, and receipts
- Waitlist notifications with queue position
- Customer messaging (promotional, transactional)
- Template message management
- Interactive message support (buttons, lists)
- Webhook processing for incoming messages
- Automated chatbot for ordering
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

WHATSAPP_API_BASE = "https://graph.facebook.com/v21.0"


class WhatsAppService:
    """WhatsApp Cloud API integration."""

    def __init__(
        self,
        phone_number_id: Optional[str] = None,
        access_token: Optional[str] = None,
        verify_token: Optional[str] = None,
        business_account_id: Optional[str] = None,
    ):
        self._phone_number_id = phone_number_id or getattr(settings, "whatsapp_phone_number_id", "")
        self._access_token = access_token or getattr(settings, "whatsapp_access_token", "")
        self._verify_token = verify_token or getattr(settings, "whatsapp_verify_token", "")
        self._business_account_id = business_account_id or getattr(settings, "whatsapp_business_account_id", "")
        self._configured = bool(self._phone_number_id and self._access_token)
        self._message_log: List[Dict[str, Any]] = []

        if not self._configured:
            logger.warning(
                "WhatsApp not configured. Set WHATSAPP_PHONE_NUMBER_ID and "
                "WHATSAPP_ACCESS_TOKEN environment variables."
            )

    @property
    def is_configured(self) -> bool:
        return self._configured

    def _require_configured(self) -> None:
        if not self._configured:
            raise RuntimeError("WhatsApp is not configured.")

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

    @property
    def _messages_url(self) -> str:
        return f"{WHATSAPP_API_BASE}/{self._phone_number_id}/messages"

    # ------------------------------------------------------------------
    # Text Messages
    # ------------------------------------------------------------------

    async def send_text(
        self,
        to: str,
        text: str,
        preview_url: bool = False,
    ) -> Dict[str, Any]:
        """Send a plain text message."""
        self._require_configured()
        body = {
            "messaging_product": "whatsapp",
            "to": self._normalize_phone(to),
            "type": "text",
            "text": {"preview_url": preview_url, "body": text},
        }
        return await self._send(body)

    # ------------------------------------------------------------------
    # Template Messages
    # ------------------------------------------------------------------

    async def send_template(
        self,
        to: str,
        template_name: str,
        language_code: str = "en",
        components: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Send a pre-approved template message."""
        self._require_configured()
        template: Dict[str, Any] = {
            "name": template_name,
            "language": {"code": language_code},
        }
        if components:
            template["components"] = components

        body = {
            "messaging_product": "whatsapp",
            "to": self._normalize_phone(to),
            "type": "template",
            "template": template,
        }
        return await self._send(body)

    # ------------------------------------------------------------------
    # Interactive Messages (Buttons & Lists)
    # ------------------------------------------------------------------

    async def send_button_message(
        self,
        to: str,
        body_text: str,
        buttons: List[Dict[str, str]],
        header: Optional[str] = None,
        footer: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a message with reply buttons (max 3)."""
        self._require_configured()
        action_buttons = [
            {"type": "reply", "reply": {"id": b["id"], "title": b["title"][:20]}}
            for b in buttons[:3]
        ]
        interactive: Dict[str, Any] = {
            "type": "button",
            "body": {"text": body_text},
            "action": {"buttons": action_buttons},
        }
        if header:
            interactive["header"] = {"type": "text", "text": header}
        if footer:
            interactive["footer"] = {"text": footer}

        body = {
            "messaging_product": "whatsapp",
            "to": self._normalize_phone(to),
            "type": "interactive",
            "interactive": interactive,
        }
        return await self._send(body)

    async def send_list_message(
        self,
        to: str,
        body_text: str,
        button_text: str,
        sections: List[Dict[str, Any]],
        header: Optional[str] = None,
        footer: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a list selection message (menu browsing)."""
        self._require_configured()
        interactive: Dict[str, Any] = {
            "type": "list",
            "body": {"text": body_text},
            "action": {
                "button": button_text[:20],
                "sections": sections,
            },
        }
        if header:
            interactive["header"] = {"type": "text", "text": header}
        if footer:
            interactive["footer"] = {"text": footer}

        body = {
            "messaging_product": "whatsapp",
            "to": self._normalize_phone(to),
            "type": "interactive",
            "interactive": interactive,
        }
        return await self._send(body)

    # ------------------------------------------------------------------
    # Media Messages
    # ------------------------------------------------------------------

    async def send_image(
        self,
        to: str,
        image_url: str,
        caption: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send an image message (e.g., receipt, menu item photo)."""
        self._require_configured()
        image: Dict[str, Any] = {"link": image_url}
        if caption:
            image["caption"] = caption

        body = {
            "messaging_product": "whatsapp",
            "to": self._normalize_phone(to),
            "type": "image",
            "image": image,
        }
        return await self._send(body)

    async def send_document(
        self,
        to: str,
        document_url: str,
        filename: str,
        caption: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a document (PDF receipt, invoice)."""
        self._require_configured()
        document: Dict[str, Any] = {"link": document_url, "filename": filename}
        if caption:
            document["caption"] = caption

        body = {
            "messaging_product": "whatsapp",
            "to": self._normalize_phone(to),
            "type": "document",
            "document": document,
        }
        return await self._send(body)

    # ------------------------------------------------------------------
    # Location Messages
    # ------------------------------------------------------------------

    async def send_location(
        self,
        to: str,
        latitude: float,
        longitude: float,
        name: Optional[str] = None,
        address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a location message (restaurant location)."""
        self._require_configured()
        location: Dict[str, Any] = {
            "latitude": latitude,
            "longitude": longitude,
        }
        if name:
            location["name"] = name
        if address:
            location["address"] = address

        body = {
            "messaging_product": "whatsapp",
            "to": self._normalize_phone(to),
            "type": "location",
            "location": location,
        }
        return await self._send(body)

    # ------------------------------------------------------------------
    # Business-Specific Messages
    # ------------------------------------------------------------------

    async def send_order_confirmation(
        self,
        to: str,
        order_id: int,
        items: List[Dict[str, Any]],
        total: float,
        estimated_time: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Send order confirmation with details."""
        lines = [f"Order #{order_id} Confirmed!"]
        lines.append("")
        for item in items:
            qty = item.get("quantity", 1)
            name = item.get("name", "Item")
            price = item.get("price", 0)
            lines.append(f"  {qty}x {name} - ${price:.2f}")
        lines.append(f"\nTotal: ${total:.2f}")
        if estimated_time:
            lines.append(f"Estimated ready in: {estimated_time} min")
        lines.append("\nThank you for your order!")

        return await self.send_text(to, "\n".join(lines))

    async def send_reservation_confirmation(
        self,
        to: str,
        guest_name: str,
        date: str,
        time: str,
        party_size: int,
        confirmation_code: str,
    ) -> Dict[str, Any]:
        """Send reservation confirmation."""
        text = (
            f"Reservation Confirmed!\n\n"
            f"Name: {guest_name}\n"
            f"Date: {date}\n"
            f"Time: {time}\n"
            f"Party size: {party_size}\n"
            f"Confirmation: {confirmation_code}\n\n"
            f"Reply CANCEL to cancel."
        )
        return await self.send_text(to, text)

    async def send_waitlist_update(
        self,
        to: str,
        guest_name: str,
        position: int,
        estimated_wait: int,
    ) -> Dict[str, Any]:
        """Send waitlist position update."""
        text = (
            f"Hi {guest_name}!\n\n"
            f"Your position in queue: #{position}\n"
            f"Estimated wait: {estimated_wait} min\n\n"
            f"We'll notify you when your table is ready!"
        )
        return await self.send_text(to, text)

    async def send_table_ready(
        self,
        to: str,
        guest_name: str,
        table_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Notify guest their table is ready."""
        text = f"Hi {guest_name}, your table is ready!"
        if table_number:
            text += f"\nTable: {table_number}"
        text += "\n\nPlease check in with the host."

        return await self.send_button_message(
            to=to,
            body_text=text,
            buttons=[
                {"id": "on_my_way", "title": "On my way!"},
                {"id": "need_more_time", "title": "5 more minutes"},
                {"id": "cancel", "title": "Cancel"},
            ],
        )

    async def send_menu(
        self,
        to: str,
        categories: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Send interactive menu for WhatsApp ordering."""
        sections = []
        for cat in categories[:10]:
            rows = []
            for item in cat.get("items", [])[:10]:
                rows.append({
                    "id": str(item.get("id", "")),
                    "title": item.get("name", "")[:24],
                    "description": f"${item.get('price', 0):.2f} - {item.get('description', '')[:72]}",
                })
            if rows:
                sections.append({
                    "title": cat.get("name", "Menu")[:24],
                    "rows": rows,
                })

        return await self.send_list_message(
            to=to,
            body_text="Browse our menu and select items to order:",
            button_text="View Menu",
            sections=sections,
            header="Our Menu",
            footer="Select items to add to your order",
        )

    # ------------------------------------------------------------------
    # Webhook Handling
    # ------------------------------------------------------------------

    def verify_webhook(self, mode: str, token: str, challenge: str) -> Optional[str]:
        """Verify webhook subscription (GET request from Meta)."""
        if mode == "subscribe" and token == self._verify_token:
            return challenge
        return None

    def parse_webhook(self, body: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse incoming webhook events from WhatsApp."""
        messages = []
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for msg in value.get("messages", []):
                    parsed = {
                        "from": msg.get("from"),
                        "message_id": msg.get("id"),
                        "timestamp": msg.get("timestamp"),
                        "type": msg.get("type"),
                    }
                    if msg.get("type") == "text":
                        parsed["text"] = msg.get("text", {}).get("body", "")
                    elif msg.get("type") == "interactive":
                        interactive = msg.get("interactive", {})
                        itype = interactive.get("type")
                        if itype == "button_reply":
                            parsed["button_id"] = interactive.get("button_reply", {}).get("id")
                            parsed["button_title"] = interactive.get("button_reply", {}).get("title")
                        elif itype == "list_reply":
                            parsed["list_id"] = interactive.get("list_reply", {}).get("id")
                            parsed["list_title"] = interactive.get("list_reply", {}).get("title")
                    elif msg.get("type") == "location":
                        loc = msg.get("location", {})
                        parsed["latitude"] = loc.get("latitude")
                        parsed["longitude"] = loc.get("longitude")

                    messages.append(parsed)

                # Status updates
                for status in value.get("statuses", []):
                    messages.append({
                        "type": "status",
                        "message_id": status.get("id"),
                        "status": status.get("status"),
                        "recipient": status.get("recipient_id"),
                        "timestamp": status.get("timestamp"),
                    })

        return messages

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _send(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Send a message via WhatsApp API."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                self._messages_url,
                json=body,
                headers=self._headers(),
            )
            data = resp.json()

            log_entry = {
                "to": body.get("to"),
                "type": body.get("type"),
                "status_code": resp.status_code,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message_id": None,
            }

            if resp.status_code == 200:
                messages = data.get("messages", [])
                if messages:
                    log_entry["message_id"] = messages[0].get("id")
            else:
                log_entry["error"] = data.get("error", {}).get("message", "Unknown error")
                logger.error(f"WhatsApp send failed: {data}")

            self._message_log.append(log_entry)
            if len(self._message_log) > 1000:
                self._message_log = self._message_log[-500:]

            if resp.status_code != 200:
                return {"success": False, "error": log_entry.get("error")}

            return {
                "success": True,
                "message_id": log_entry["message_id"],
            }

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        """Normalize phone number to E.164 format."""
        phone = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        if not phone.startswith("+"):
            phone = "+" + phone
        return phone.lstrip("+")

    def get_message_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._message_log[-limit:]


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_service: Optional[WhatsAppService] = None


def get_whatsapp_service() -> WhatsAppService:
    global _service
    if _service is None:
        _service = WhatsAppService()
    return _service

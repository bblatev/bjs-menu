"""Customer-Facing Display Service.

Supports:
- Pole displays (VFD/LCD line displays via serial/USB)
- Secondary screen displays (tablet/monitor showing order details)
- Tip prompt screens
- Promotional content display
- Order progress display for pickup

Connection types: Serial, USB, Network, WebSocket (for tablet displays).
"""

import json
import logging
import socket
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Display Protocols
# ---------------------------------------------------------------------------

class PoleDisplayProtocol:
    """VFD/LCD Pole Display protocol (serial ESC/POS-compatible)."""

    # Common ESC/POS commands for customer displays
    INIT = b"\x1b\x40"             # Initialize
    CLEAR = b"\x0c"                # Clear display
    HOME = b"\x1b\x5b\x48"        # Cursor home
    LINE1 = b"\x1b\x51\x41"       # Move to line 1
    LINE2 = b"\x1b\x51\x42"       # Move to line 2
    BRIGHTNESS_HIGH = b"\x1b\x2a\x04"
    BRIGHTNESS_LOW = b"\x1b\x2a\x01"

    @staticmethod
    def format_two_line(line1: str, line2: str, width: int = 20) -> bytes:
        """Format text for a 2-line VFD display."""
        l1 = line1[:width].ljust(width)
        l2 = line2[:width].ljust(width)
        return (
            PoleDisplayProtocol.CLEAR
            + PoleDisplayProtocol.LINE1
            + l1.encode("ascii", errors="replace")
            + PoleDisplayProtocol.LINE2
            + l2.encode("ascii", errors="replace")
        )

    @staticmethod
    def format_item_price(item_name: str, price: float, width: int = 20) -> bytes:
        """Format item name and price on two lines."""
        price_str = f"${price:.2f}"
        line1 = item_name[:width].ljust(width)
        line2 = price_str.rjust(width)
        return (
            PoleDisplayProtocol.CLEAR
            + PoleDisplayProtocol.LINE1
            + line1.encode("ascii", errors="replace")
            + PoleDisplayProtocol.LINE2
            + line2.encode("ascii", errors="replace")
        )

    @staticmethod
    def format_total(label: str, amount: float, width: int = 20) -> bytes:
        """Format total display."""
        amount_str = f"${amount:.2f}"
        line1 = label[:width].ljust(width)
        line2 = amount_str.rjust(width)
        return (
            PoleDisplayProtocol.CLEAR
            + PoleDisplayProtocol.LINE1
            + line1.encode("ascii", errors="replace")
            + PoleDisplayProtocol.LINE2
            + line2.encode("ascii", errors="replace")
        )


class SecondScreenDisplay:
    """Data model for tablet/monitor second screen display."""

    @staticmethod
    def order_view(
        items: List[Dict[str, Any]],
        subtotal: float,
        tax: float,
        total: float,
        tip: float = 0,
        discount: float = 0,
    ) -> Dict[str, Any]:
        """Generate order view data for second screen."""
        return {
            "type": "order",
            "items": [
                {
                    "name": i.get("name", ""),
                    "quantity": i.get("quantity", 1),
                    "price": i.get("price", 0),
                    "modifiers": i.get("modifiers", []),
                }
                for i in items
            ],
            "subtotal": subtotal,
            "discount": discount,
            "tax": tax,
            "tip": tip,
            "total": total,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def tip_prompt(
        total: float,
        presets: Optional[List[int]] = None,
        allow_custom: bool = True,
        allow_no_tip: bool = True,
    ) -> Dict[str, Any]:
        """Generate tip prompt screen data."""
        tip_presets = presets or [15, 18, 20, 25]
        options = [
            {"percentage": p, "amount": round(total * p / 100, 2)}
            for p in tip_presets
        ]
        return {
            "type": "tip_prompt",
            "total": total,
            "presets": options,
            "allow_custom": allow_custom,
            "allow_no_tip": allow_no_tip,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def welcome_screen(
        venue_name: str,
        message: str = "Welcome!",
        logo_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate welcome/idle screen data."""
        return {
            "type": "welcome",
            "venue_name": venue_name,
            "message": message,
            "logo_url": logo_url,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def promotional_content(
        slides: List[Dict[str, Any]],
        interval_seconds: int = 10,
    ) -> Dict[str, Any]:
        """Generate promotional slideshow data."""
        return {
            "type": "promotional",
            "slides": slides,
            "interval_seconds": interval_seconds,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def order_ready(
        order_number: str,
        customer_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate order-ready pickup display."""
        return {
            "type": "order_ready",
            "order_number": order_number,
            "customer_name": customer_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def thank_you(
        message: str = "Thank you for your visit!",
        survey_url: Optional[str] = None,
        survey_qr: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate thank-you / post-payment screen."""
        return {
            "type": "thank_you",
            "message": message,
            "survey_url": survey_url,
            "survey_qr": survey_qr,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class CustomerDisplayService:
    """Customer-facing display management service."""

    def __init__(self):
        self._displays: Dict[str, Dict[str, Any]] = {}
        self._display_log: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Display Registration
    # ------------------------------------------------------------------

    def register_display(
        self,
        display_id: str,
        name: str,
        display_type: str = "pole",
        connection_type: str = "serial",
        host: Optional[str] = None,
        port: Optional[int] = None,
        serial_port: Optional[str] = None,
        baud_rate: int = 9600,
        width: int = 20,
        lines: int = 2,
    ) -> Dict[str, Any]:
        """Register a customer-facing display.

        display_type: pole (VFD/LCD), tablet, monitor, kiosk
        connection_type: serial, usb, network, websocket
        """
        display = {
            "id": display_id,
            "name": name,
            "display_type": display_type,
            "connection_type": connection_type,
            "host": host,
            "port": port or (9100 if connection_type == "network" else None),
            "serial_port": serial_port,
            "baud_rate": baud_rate,
            "width": width,
            "lines": lines,
            "status": "registered",
            "current_content": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._displays[display_id] = display
        return display

    def get_display(self, display_id: str) -> Optional[Dict[str, Any]]:
        return self._displays.get(display_id)

    def list_displays(self) -> List[Dict[str, Any]]:
        return list(self._displays.values())

    def remove_display(self, display_id: str) -> Dict[str, Any]:
        d = self._displays.pop(display_id, None)
        if d:
            return {"deleted": True, "id": display_id}
        return {"error": "Display not found"}

    # ------------------------------------------------------------------
    # Pole Display Operations
    # ------------------------------------------------------------------

    def show_item(
        self, display_id: str, item_name: str, price: float
    ) -> Dict[str, Any]:
        """Show an item being scanned/added on pole display."""
        display = self._displays.get(display_id)
        if not display:
            return {"error": "Display not found"}

        data = PoleDisplayProtocol.format_item_price(item_name, price, display.get("width", 20))
        return self._send_to_pole(display, data, "item_added")

    def show_total(
        self, display_id: str, label: str, amount: float
    ) -> Dict[str, Any]:
        """Show subtotal/total on pole display."""
        display = self._displays.get(display_id)
        if not display:
            return {"error": "Display not found"}

        data = PoleDisplayProtocol.format_total(label, amount, display.get("width", 20))
        return self._send_to_pole(display, data, "total")

    def show_message(
        self, display_id: str, line1: str, line2: str = ""
    ) -> Dict[str, Any]:
        """Show a custom message on pole display."""
        display = self._displays.get(display_id)
        if not display:
            return {"error": "Display not found"}

        data = PoleDisplayProtocol.format_two_line(line1, line2, display.get("width", 20))
        return self._send_to_pole(display, data, "message")

    def clear_display(self, display_id: str) -> Dict[str, Any]:
        """Clear the pole display."""
        display = self._displays.get(display_id)
        if not display:
            return {"error": "Display not found"}

        return self._send_to_pole(display, PoleDisplayProtocol.CLEAR, "clear")

    def _send_to_pole(
        self, display: Dict[str, Any], data: bytes, content_type: str
    ) -> Dict[str, Any]:
        """Send data to a pole display via its connection."""
        conn_type = display.get("connection_type")

        if conn_type == "network":
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                sock.connect((display["host"], display["port"]))
                sock.sendall(data)
                sock.close()
                display["status"] = "online"
                display["current_content"] = content_type
                self._log(display["id"], content_type, True)
                return {"success": True}
            except (socket.error, socket.timeout) as e:
                display["status"] = "error"
                self._log(display["id"], content_type, False, str(e))
                return {"success": False, "error": str(e)}
        else:
            # For serial/USB, we log the command and mark as sent
            # Actual serial communication would use pyserial
            display["current_content"] = content_type
            self._log(display["id"], content_type, True, "queued for local driver")
            return {"success": True, "message": "Command queued for local driver"}

    # ------------------------------------------------------------------
    # Second Screen Operations
    # ------------------------------------------------------------------

    def set_screen_content(
        self, display_id: str, content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Set content for a tablet/monitor second screen.

        Content is stored and served via WebSocket or polling endpoint.
        """
        display = self._displays.get(display_id)
        if not display:
            return {"error": "Display not found"}

        display["current_content"] = content
        display["status"] = "active"
        self._log(display["id"], content.get("type", "unknown"), True)
        return {"success": True, "content_type": content.get("type")}

    def get_screen_content(self, display_id: str) -> Dict[str, Any]:
        """Get current content for a second screen (polling endpoint)."""
        display = self._displays.get(display_id)
        if not display:
            return {"error": "Display not found"}
        return display.get("current_content") or SecondScreenDisplay.welcome_screen("BJS Bar")

    # ------------------------------------------------------------------
    # Convenience Methods
    # ------------------------------------------------------------------

    def display_order(
        self, display_id: str, items: List[Dict[str, Any]],
        subtotal: float, tax: float, total: float,
        tip: float = 0, discount: float = 0,
    ) -> Dict[str, Any]:
        """Show full order on second screen."""
        content = SecondScreenDisplay.order_view(items, subtotal, tax, total, tip, discount)
        return self.set_screen_content(display_id, content)

    def display_tip_prompt(
        self, display_id: str, total: float,
        presets: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """Show tip selection screen."""
        content = SecondScreenDisplay.tip_prompt(total, presets)
        return self.set_screen_content(display_id, content)

    def display_welcome(
        self, display_id: str, venue_name: str,
        message: str = "Welcome!", logo_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Show welcome/idle screen."""
        content = SecondScreenDisplay.welcome_screen(venue_name, message, logo_url)
        return self.set_screen_content(display_id, content)

    def display_promotional(
        self, display_id: str, slides: List[Dict[str, Any]],
        interval: int = 10,
    ) -> Dict[str, Any]:
        """Show promotional slideshow."""
        content = SecondScreenDisplay.promotional_content(slides, interval)
        return self.set_screen_content(display_id, content)

    def display_thank_you(
        self, display_id: str,
        message: str = "Thank you!",
        survey_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Show thank-you screen after payment."""
        content = SecondScreenDisplay.thank_you(message, survey_url)
        return self.set_screen_content(display_id, content)

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _log(
        self, display_id: str, content_type: str, success: bool, error: Optional[str] = None
    ) -> None:
        entry = {
            "display_id": display_id,
            "content_type": content_type,
            "success": success,
            "error": error,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._display_log.append(entry)
        if len(self._display_log) > 1000:
            self._display_log = self._display_log[-500:]

    def get_display_log(self, display_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        log = self._display_log
        if display_id:
            log = [e for e in log if e["display_id"] == display_id]
        return log[-limit:]


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_service: Optional[CustomerDisplayService] = None


def get_customer_display_service() -> CustomerDisplayService:
    global _service
    if _service is None:
        _service = CustomerDisplayService()
    return _service

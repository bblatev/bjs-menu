"""Label Printer Service (ZPL/EPL).

Provides label printing for:
- Product pricing labels
- Inventory barcode labels
- Shelf labels with product info
- Date/expiry labels (prep labels)
- Shipping labels
- Custom labels with templates

Supports Zebra printers (ZPL), Eltron (EPL), and generic ESC/POS label printers.
"""

import logging
import socket
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ZPL Label Templates
# ---------------------------------------------------------------------------

class ZPLBuilder:
    """Zebra Programming Language command builder."""

    def __init__(self, width: int = 400, height: int = 200, dpi: int = 203):
        self.width = width
        self.height = height
        self.dpi = dpi
        self._commands: List[str] = []

    def start(self) -> "ZPLBuilder":
        self._commands = ["^XA"]
        self._commands.append(f"^PW{self.width}")
        self._commands.append(f"^LL{self.height}")
        return self

    def text(
        self, x: int, y: int, text: str,
        font: str = "0", font_size: int = 30,
        orientation: str = "N",
    ) -> "ZPLBuilder":
        self._commands.append(f"^FO{x},{y}")
        self._commands.append(f"^A{font}{orientation},{font_size},{font_size}")
        self._commands.append(f"^FD{text}^FS")
        return self

    def barcode_128(
        self, x: int, y: int, data: str,
        height: int = 50, show_text: bool = True,
    ) -> "ZPLBuilder":
        self._commands.append(f"^FO{x},{y}")
        interpret = "Y" if show_text else "N"
        self._commands.append(f"^BCN,{height},{interpret},N,N")
        self._commands.append(f"^FD{data}^FS")
        return self

    def barcode_ean13(
        self, x: int, y: int, data: str,
        height: int = 50, show_text: bool = True,
    ) -> "ZPLBuilder":
        self._commands.append(f"^FO{x},{y}")
        interpret = "Y" if show_text else "N"
        self._commands.append(f"^BEN,{height},{interpret},N")
        self._commands.append(f"^FD{data}^FS")
        return self

    def qr_code(
        self, x: int, y: int, data: str,
        magnification: int = 4,
    ) -> "ZPLBuilder":
        self._commands.append(f"^FO{x},{y}")
        self._commands.append(f"^BQN,2,{magnification}")
        self._commands.append(f"^FDQA,{data}^FS")
        return self

    def line(
        self, x: int, y: int, width: int, height: int = 2,
    ) -> "ZPLBuilder":
        self._commands.append(f"^FO{x},{y}")
        self._commands.append(f"^GB{width},{height},{height}^FS")
        return self

    def box(
        self, x: int, y: int, width: int, height: int, thickness: int = 2,
    ) -> "ZPLBuilder":
        self._commands.append(f"^FO{x},{y}")
        self._commands.append(f"^GB{width},{height},{thickness}^FS")
        return self

    def end(self) -> "ZPLBuilder":
        self._commands.append("^XZ")
        return self

    def build(self) -> str:
        return "\n".join(self._commands)


# ---------------------------------------------------------------------------
# EPL Label Templates
# ---------------------------------------------------------------------------

class EPLBuilder:
    """Eltron Programming Language command builder."""

    def __init__(self, width: int = 400, height: int = 200):
        self.width = width
        self.height = height
        self._commands: List[str] = []

    def start(self) -> "EPLBuilder":
        self._commands = ["N"]  # Clear buffer
        self._commands.append(f"q{self.width}")  # Set width
        self._commands.append(f"Q{self.height},24")  # Set height with gap
        return self

    def text(
        self, x: int, y: int, text: str,
        font: int = 3, h_mult: int = 1, v_mult: int = 1,
        rotation: int = 0,
    ) -> "EPLBuilder":
        self._commands.append(f"A{x},{y},{rotation},{font},{h_mult},{v_mult},N,\"{text}\"")
        return self

    def barcode(
        self, x: int, y: int, data: str,
        barcode_type: str = "1",
        narrow_width: int = 2,
        wide_width: int = 4,
        height: int = 50,
        human_readable: str = "B",
    ) -> "EPLBuilder":
        self._commands.append(
            f"B{x},{y},{rotation if hasattr(self, 'rotation') else 0},"
            f"{barcode_type},{narrow_width},{wide_width},{height},{human_readable},\"{data}\""
        )
        return self

    def line(
        self, x: int, y: int, width: int, height: int = 2,
    ) -> "EPLBuilder":
        self._commands.append(f"LO{x},{y},{width},{height}")
        return self

    def end(self, copies: int = 1) -> "EPLBuilder":
        self._commands.append(f"P{copies}")
        return self

    def build(self) -> str:
        return "\n".join(self._commands)


# ---------------------------------------------------------------------------
# Label Templates
# ---------------------------------------------------------------------------

LABEL_TEMPLATES = {
    "product_price": {
        "name": "Product Price Label",
        "description": "Standard shelf price label with barcode",
        "width": 400, "height": 200,
        "fields": ["product_name", "price", "barcode", "unit"],
    },
    "inventory_barcode": {
        "name": "Inventory Barcode Label",
        "description": "Simple barcode label for inventory tracking",
        "width": 400, "height": 120,
        "fields": ["sku", "product_name", "barcode"],
    },
    "prep_date": {
        "name": "Prep Date Label",
        "description": "Food preparation date/expiry label",
        "width": 400, "height": 250,
        "fields": ["product_name", "prep_date", "expiry_date", "prepared_by", "storage_instructions"],
    },
    "shelf_label": {
        "name": "Shelf Label",
        "description": "Shelf tag with product info and allergens",
        "width": 400, "height": 180,
        "fields": ["product_name", "price", "allergens", "category"],
    },
    "shipping": {
        "name": "Shipping Label",
        "description": "Shipping/receiving label with QR code",
        "width": 400, "height": 300,
        "fields": ["from_name", "to_name", "to_address", "order_id", "qr_data"],
    },
}


class LabelPrinterService:
    """Label printer management and printing service."""

    def __init__(self):
        self._printers: Dict[str, Dict[str, Any]] = {}
        self._print_history: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Printer Management
    # ------------------------------------------------------------------

    def register_printer(
        self,
        printer_id: str,
        name: str,
        host: str,
        port: int = 9100,
        protocol: str = "zpl",
        connection_type: str = "network",
        dpi: int = 203,
        label_width_mm: int = 50,
        label_height_mm: int = 25,
    ) -> Dict[str, Any]:
        """Register a label printer."""
        printer = {
            "id": printer_id,
            "name": name,
            "host": host,
            "port": port,
            "protocol": protocol,  # zpl, epl, escpos
            "connection_type": connection_type,  # network, usb, serial
            "dpi": dpi,
            "label_width_mm": label_width_mm,
            "label_height_mm": label_height_mm,
            "status": "registered",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_used": None,
            "print_count": 0,
        }
        self._printers[printer_id] = printer
        return printer

    def get_printer(self, printer_id: str) -> Optional[Dict[str, Any]]:
        return self._printers.get(printer_id)

    def list_printers(self) -> List[Dict[str, Any]]:
        return list(self._printers.values())

    def remove_printer(self, printer_id: str) -> Dict[str, Any]:
        printer = self._printers.pop(printer_id, None)
        if printer:
            return {"deleted": True, "id": printer_id}
        return {"error": "Printer not found"}

    def test_connection(self, printer_id: str) -> Dict[str, Any]:
        """Test printer connectivity."""
        printer = self._printers.get(printer_id)
        if not printer:
            return {"error": "Printer not found"}

        if printer["connection_type"] == "network":
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                sock.connect((printer["host"], printer["port"]))
                sock.close()
                printer["status"] = "online"
                return {"connected": True, "status": "online"}
            except (socket.error, socket.timeout) as e:
                printer["status"] = "offline"
                return {"connected": False, "status": "offline", "error": str(e)}
        else:
            printer["status"] = "unknown"
            return {"connected": None, "status": "unknown", "message": "USB/Serial test not supported remotely"}

    # ------------------------------------------------------------------
    # Label Generation
    # ------------------------------------------------------------------

    def generate_price_label(
        self,
        product_name: str,
        price: float,
        barcode: str,
        unit: str = "each",
        currency: str = "$",
        protocol: str = "zpl",
    ) -> str:
        """Generate a product price label."""
        if protocol == "zpl":
            zpl = ZPLBuilder(width=400, height=200).start()
            zpl.text(20, 10, product_name, font_size=35)
            zpl.line(20, 50, 360)
            zpl.text(20, 60, f"{currency}{price:.2f}", font_size=50)
            zpl.text(280, 80, f"/{unit}", font_size=20)
            zpl.barcode_128(50, 120, barcode, height=50)
            zpl.end()
            return zpl.build()
        else:
            epl = EPLBuilder(width=400, height=200).start()
            epl.text(20, 10, product_name, font=3)
            epl.line(20, 40, 360)
            epl.text(20, 50, f"{currency}{price:.2f}", font=4, h_mult=2, v_mult=2)
            epl.barcode(50, 120, barcode, height=50)
            epl.end()
            return epl.build()

    def generate_prep_label(
        self,
        product_name: str,
        prep_date: str,
        expiry_date: str,
        prepared_by: str = "",
        storage_instructions: str = "",
        protocol: str = "zpl",
    ) -> str:
        """Generate a food preparation date label."""
        if protocol == "zpl":
            zpl = ZPLBuilder(width=400, height=250).start()
            zpl.text(20, 10, product_name, font_size=30)
            zpl.line(20, 45, 360)
            zpl.text(20, 55, f"Prepared: {prep_date}", font_size=22)
            zpl.text(20, 85, f"Expires:  {expiry_date}", font_size=22)
            if prepared_by:
                zpl.text(20, 115, f"By: {prepared_by}", font_size=20)
            if storage_instructions:
                zpl.text(20, 145, storage_instructions[:40], font_size=18)
            zpl.box(5, 5, 390, 240, thickness=3)
            zpl.end()
            return zpl.build()
        else:
            epl = EPLBuilder(width=400, height=250).start()
            epl.text(20, 10, product_name, font=3)
            epl.text(20, 45, f"Prepared: {prep_date}")
            epl.text(20, 70, f"Expires:  {expiry_date}")
            if prepared_by:
                epl.text(20, 95, f"By: {prepared_by}")
            epl.end()
            return epl.build()

    def generate_inventory_label(
        self,
        sku: str,
        product_name: str,
        barcode: str,
        protocol: str = "zpl",
    ) -> str:
        """Generate an inventory barcode label."""
        if protocol == "zpl":
            zpl = ZPLBuilder(width=400, height=120).start()
            zpl.text(20, 5, product_name[:30], font_size=22)
            zpl.text(20, 30, f"SKU: {sku}", font_size=18)
            zpl.barcode_128(50, 55, barcode, height=40)
            zpl.end()
            return zpl.build()
        else:
            epl = EPLBuilder(width=400, height=120).start()
            epl.text(20, 5, product_name[:30])
            epl.text(20, 30, f"SKU: {sku}")
            epl.barcode(50, 55, barcode, height=40)
            epl.end()
            return epl.build()

    def generate_shelf_label(
        self,
        product_name: str,
        price: float,
        allergens: str = "",
        category: str = "",
        currency: str = "$",
        protocol: str = "zpl",
    ) -> str:
        """Generate a shelf tag with allergen info."""
        if protocol == "zpl":
            zpl = ZPLBuilder(width=400, height=180).start()
            if category:
                zpl.text(20, 5, category.upper(), font_size=16)
            zpl.text(20, 25, product_name, font_size=28)
            zpl.line(20, 58, 360)
            zpl.text(20, 65, f"{currency}{price:.2f}", font_size=45)
            if allergens:
                zpl.text(20, 120, f"Allergens: {allergens}", font_size=16)
            zpl.end()
            return zpl.build()
        else:
            epl = EPLBuilder(width=400, height=180).start()
            epl.text(20, 5, product_name, font=3)
            epl.text(20, 40, f"{currency}{price:.2f}", font=4, h_mult=2, v_mult=2)
            if allergens:
                epl.text(20, 100, f"Allergens: {allergens}")
            epl.end()
            return epl.build()

    def generate_shipping_label(
        self,
        from_name: str,
        to_name: str,
        to_address: str,
        order_id: str,
        qr_data: Optional[str] = None,
        protocol: str = "zpl",
    ) -> str:
        """Generate a shipping/receiving label."""
        if protocol == "zpl":
            zpl = ZPLBuilder(width=400, height=300).start()
            zpl.text(20, 10, f"FROM: {from_name}", font_size=20)
            zpl.line(20, 35, 360, 3)
            zpl.text(20, 45, f"TO: {to_name}", font_size=28)
            zpl.text(20, 80, to_address[:40], font_size=22)
            zpl.line(20, 110, 360)
            zpl.text(20, 120, f"Order: {order_id}", font_size=24)
            if qr_data:
                zpl.qr_code(280, 140, qr_data or order_id, magnification=3)
            zpl.barcode_128(20, 220, order_id, height=50)
            zpl.end()
            return zpl.build()
        else:
            epl = EPLBuilder(width=400, height=300).start()
            epl.text(20, 10, f"FROM: {from_name}")
            epl.text(20, 40, f"TO: {to_name}", font=3)
            epl.text(20, 70, to_address[:40])
            epl.text(20, 100, f"Order: {order_id}")
            epl.barcode(20, 180, order_id, height=50)
            epl.end()
            return epl.build()

    # ------------------------------------------------------------------
    # Print Execution
    # ------------------------------------------------------------------

    def print_label(
        self,
        printer_id: str,
        label_data: str,
        copies: int = 1,
    ) -> Dict[str, Any]:
        """Send label data to a printer."""
        printer = self._printers.get(printer_id)
        if not printer:
            return {"error": "Printer not found"}

        if printer["connection_type"] == "network":
            try:
                for _ in range(copies):
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(10)
                    sock.connect((printer["host"], printer["port"]))
                    sock.sendall(label_data.encode("utf-8"))
                    sock.close()

                printer["last_used"] = datetime.now(timezone.utc).isoformat()
                printer["print_count"] += copies
                printer["status"] = "online"

                log_entry = {
                    "printer_id": printer_id,
                    "copies": copies,
                    "protocol": printer["protocol"],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "success": True,
                }
                self._print_history.append(log_entry)
                return {"success": True, "copies_printed": copies}

            except (socket.error, socket.timeout) as e:
                printer["status"] = "error"
                return {"success": False, "error": str(e)}
        else:
            return {"success": False, "error": f"Connection type '{printer['connection_type']}' requires local driver"}

    def get_templates(self) -> Dict[str, Dict[str, Any]]:
        """Get available label templates."""
        return LABEL_TEMPLATES

    def get_print_history(self, printer_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        history = self._print_history
        if printer_id:
            history = [h for h in history if h["printer_id"] == printer_id]
        return history[-limit:]


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_service: Optional[LabelPrinterService] = None


def get_label_printer_service() -> LabelPrinterService:
    global _service
    if _service is None:
        _service = LabelPrinterService()
    return _service

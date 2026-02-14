"""ESC/POS Receipt Printer Service.

Supports Epson, Star Micronics, and other ESC/POS compatible printers.
Connections: Network (TCP/IP), USB (via system print queue).
"""

import logging
import socket
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from io import BytesIO

logger = logging.getLogger(__name__)


# ============================================================================
# ESC/POS Command Constants
# ============================================================================

class ESC:
    """ESC/POS command bytes."""
    # Basic commands
    ESC = b'\x1b'
    GS = b'\x1d'
    FS = b'\x1c'
    DLE = b'\x10'
    EOT = b'\x04'
    NUL = b'\x00'

    # Printer control
    INIT = b'\x1b\x40'  # Initialize printer
    CUT = b'\x1d\x56\x00'  # Full cut
    CUT_PARTIAL = b'\x1d\x56\x01'  # Partial cut
    FEED_LINES = b'\x1b\x64'  # Feed n lines
    BEEP = b'\x1b\x42'  # Beep

    # Text formatting
    BOLD_ON = b'\x1b\x45\x01'
    BOLD_OFF = b'\x1b\x45\x00'
    UNDERLINE_ON = b'\x1b\x2d\x01'
    UNDERLINE_OFF = b'\x1b\x2d\x00'
    DOUBLE_HEIGHT_ON = b'\x1b\x21\x10'
    DOUBLE_WIDTH_ON = b'\x1b\x21\x20'
    DOUBLE_SIZE_ON = b'\x1b\x21\x30'
    NORMAL_SIZE = b'\x1b\x21\x00'
    INVERT_ON = b'\x1b\x42\x01'
    INVERT_OFF = b'\x1b\x42\x00'

    # Text alignment
    ALIGN_LEFT = b'\x1b\x61\x00'
    ALIGN_CENTER = b'\x1b\x61\x01'
    ALIGN_RIGHT = b'\x1b\x61\x02'

    # Character sets
    CHARSET_PC437 = b'\x1b\x74\x00'  # USA
    CHARSET_PC850 = b'\x1b\x74\x02'  # Multilingual
    CHARSET_PC852 = b'\x1b\x74\x12'  # Latin 2
    CHARSET_PC866 = b'\x1b\x74\x11'  # Cyrillic #2
    CHARSET_WPC1252 = b'\x1b\x74\x10'  # Windows 1252

    # Cash drawer
    DRAWER_KICK_2 = b'\x1b\x70\x00\x19\xfa'  # Pin 2
    DRAWER_KICK_5 = b'\x1b\x70\x01\x19\xfa'  # Pin 5


class PrinterType(str, Enum):
    EPSON = "epson"
    STAR = "star"
    GENERIC = "generic"


class ConnectionType(str, Enum):
    NETWORK = "network"
    USB = "usb"
    SERIAL = "serial"


@dataclass
class PrinterConfig:
    """Configuration for a receipt printer."""
    name: str
    printer_type: PrinterType = PrinterType.EPSON
    connection_type: ConnectionType = ConnectionType.NETWORK
    # Network settings
    ip_address: Optional[str] = None
    port: int = 9100
    # USB settings (print queue name)
    usb_device: Optional[str] = None
    # Paper settings
    paper_width: int = 80  # mm (80 or 58)
    chars_per_line: int = 48  # characters per line
    # Options
    auto_cut: bool = True
    beep_on_print: bool = False
    open_drawer: bool = False
    charset: str = "PC850"


@dataclass
class ReceiptLine:
    """A line on a receipt."""
    text: str = ""
    bold: bool = False
    double_height: bool = False
    double_width: bool = False
    underline: bool = False
    align: str = "left"  # left, center, right


@dataclass
class ReceiptItem:
    """An item on a receipt."""
    name: str
    quantity: float
    price: float
    modifiers: List[str] = field(default_factory=list)


@dataclass
class Receipt:
    """A receipt to print."""
    # Header
    venue_name: str = ""
    venue_address: str = ""
    venue_phone: str = ""
    venue_tax_id: str = ""

    # Order info
    order_number: str = ""
    table_number: str = ""
    waiter_name: str = ""
    order_type: str = ""  # Dine-in, Takeout, Delivery
    timestamp: Optional[datetime] = None

    # Items
    items: List[ReceiptItem] = field(default_factory=list)

    # Totals
    subtotal: float = 0.0
    tax: float = 0.0
    tax_rate: float = 0.0
    discount: float = 0.0
    discount_name: str = ""
    tip: float = 0.0
    total: float = 0.0

    # Payment
    payment_method: str = ""
    amount_paid: float = 0.0
    change: float = 0.0

    # Footer
    footer_message: str = ""
    qr_code_data: str = ""  # For fiscal QR code

    # Metadata
    receipt_type: str = "customer"  # customer, kitchen, bar


class PrinterService:
    """Service for printing receipts via ESC/POS printers."""

    def __init__(self, config: PrinterConfig):
        self.config = config
        self._socket: Optional[socket.socket] = None

    def _get_charset_command(self) -> bytes:
        """Get the charset command based on config."""
        charsets = {
            "PC437": ESC.CHARSET_PC437,
            "PC850": ESC.CHARSET_PC850,
            "PC852": ESC.CHARSET_PC852,
            "PC866": ESC.CHARSET_PC866,
            "WPC1252": ESC.CHARSET_WPC1252,
        }
        return charsets.get(self.config.charset, ESC.CHARSET_PC850)

    def _build_line(self, line: ReceiptLine) -> bytes:
        """Build ESC/POS commands for a receipt line."""
        data = BytesIO()

        # Alignment
        if line.align == "center":
            data.write(ESC.ALIGN_CENTER)
        elif line.align == "right":
            data.write(ESC.ALIGN_RIGHT)
        else:
            data.write(ESC.ALIGN_LEFT)

        # Formatting
        if line.bold:
            data.write(ESC.BOLD_ON)
        if line.underline:
            data.write(ESC.UNDERLINE_ON)
        if line.double_height and line.double_width:
            data.write(ESC.DOUBLE_SIZE_ON)
        elif line.double_height:
            data.write(ESC.DOUBLE_HEIGHT_ON)
        elif line.double_width:
            data.write(ESC.DOUBLE_WIDTH_ON)

        # Text (encode to correct charset)
        try:
            text_bytes = line.text.encode('cp850')
        except UnicodeEncodeError:
            text_bytes = line.text.encode('utf-8', errors='replace')

        data.write(text_bytes)
        data.write(b'\n')

        # Reset formatting
        if line.bold:
            data.write(ESC.BOLD_OFF)
        if line.underline:
            data.write(ESC.UNDERLINE_OFF)
        if line.double_height or line.double_width:
            data.write(ESC.NORMAL_SIZE)

        return data.getvalue()

    def _format_item_line(self, name: str, qty: float, price: float) -> str:
        """Format an item line with proper spacing."""
        qty_str = f"{qty:.0f}x" if qty == int(qty) else f"{qty:.1f}x"
        price_str = f"{price:.2f}"

        # Calculate available space for name
        max_name_len = self.config.chars_per_line - len(qty_str) - len(price_str) - 2

        # Truncate name if needed
        if len(name) > max_name_len:
            name = name[:max_name_len - 2] + ".."

        # Build line with proper spacing
        spaces = self.config.chars_per_line - len(qty_str) - len(name) - len(price_str)
        return f"{qty_str} {name}{' ' * spaces}{price_str}"

    def _format_total_line(self, label: str, amount: float) -> str:
        """Format a totals line with proper spacing."""
        amount_str = f"{amount:.2f}"
        spaces = self.config.chars_per_line - len(label) - len(amount_str)
        return f"{label}{' ' * spaces}{amount_str}"

    def _build_divider(self, char: str = "-") -> bytes:
        """Build a divider line."""
        return (char * self.config.chars_per_line + "\n").encode('cp850')

    def build_receipt(self, receipt: Receipt) -> bytes:
        """Build the complete receipt as ESC/POS commands."""
        data = BytesIO()

        # Initialize printer
        data.write(ESC.INIT)
        data.write(self._get_charset_command())

        # Header - Venue info
        if receipt.venue_name:
            data.write(self._build_line(ReceiptLine(
                text=receipt.venue_name,
                bold=True,
                double_height=True,
                align="center"
            )))
        if receipt.venue_address:
            data.write(self._build_line(ReceiptLine(
                text=receipt.venue_address,
                align="center"
            )))
        if receipt.venue_phone:
            data.write(self._build_line(ReceiptLine(
                text=f"Tel: {receipt.venue_phone}",
                align="center"
            )))
        if receipt.venue_tax_id:
            data.write(self._build_line(ReceiptLine(
                text=f"Tax ID: {receipt.venue_tax_id}",
                align="center"
            )))

        data.write(self._build_divider("="))

        # Order info
        timestamp = receipt.timestamp or datetime.now()
        data.write(self._build_line(ReceiptLine(
            text=timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            align="center"
        )))

        if receipt.order_number:
            data.write(self._build_line(ReceiptLine(
                text=f"Order: #{receipt.order_number}",
                bold=True,
                align="center"
            )))

        info_parts = []
        if receipt.table_number:
            info_parts.append(f"Table: {receipt.table_number}")
        if receipt.waiter_name:
            info_parts.append(f"Server: {receipt.waiter_name}")
        if receipt.order_type:
            info_parts.append(receipt.order_type)

        if info_parts:
            data.write(self._build_line(ReceiptLine(
                text=" | ".join(info_parts),
                align="center"
            )))

        data.write(self._build_divider("-"))

        # Items
        for item in receipt.items:
            line = self._format_item_line(item.name, item.quantity, item.price * item.quantity)
            data.write(self._build_line(ReceiptLine(text=line)))

            # Print modifiers
            for mod in item.modifiers:
                data.write(self._build_line(ReceiptLine(text=f"  + {mod}")))

        data.write(self._build_divider("-"))

        # Totals
        data.write(self._build_line(ReceiptLine(
            text=self._format_total_line("Subtotal:", receipt.subtotal)
        )))

        if receipt.tax > 0:
            tax_label = f"Tax ({receipt.tax_rate:.0f}%):" if receipt.tax_rate else "Tax:"
            data.write(self._build_line(ReceiptLine(
                text=self._format_total_line(tax_label, receipt.tax)
            )))

        if receipt.discount > 0:
            discount_label = f"Discount ({receipt.discount_name}):" if receipt.discount_name else "Discount:"
            data.write(self._build_line(ReceiptLine(
                text=self._format_total_line(discount_label, -receipt.discount)
            )))

        if receipt.tip > 0:
            data.write(self._build_line(ReceiptLine(
                text=self._format_total_line("Tip:", receipt.tip)
            )))

        data.write(self._build_divider("="))

        # Total
        data.write(self._build_line(ReceiptLine(
            text=self._format_total_line("TOTAL:", receipt.total),
            bold=True,
            double_height=True
        )))

        data.write(self._build_divider("="))

        # Payment info
        if receipt.payment_method:
            data.write(self._build_line(ReceiptLine(
                text=self._format_total_line(f"Paid ({receipt.payment_method}):", receipt.amount_paid)
            )))

        if receipt.change > 0:
            data.write(self._build_line(ReceiptLine(
                text=self._format_total_line("Change:", receipt.change)
            )))

        # QR Code (fiscal)
        if receipt.qr_code_data:
            data.write(b'\n')
            # QR Code commands (GS ( k - for QR code)
            qr_data = receipt.qr_code_data.encode('utf-8')
            qr_len = len(qr_data) + 3

            # Set QR model
            data.write(b'\x1d\x28\x6b\x04\x00\x31\x41\x32\x00')
            # Set QR size (module size 4)
            data.write(b'\x1d\x28\x6b\x03\x00\x31\x43\x04')
            # Set error correction level (L)
            data.write(b'\x1d\x28\x6b\x03\x00\x31\x45\x30')
            # Store data
            pL = (qr_len) % 256
            pH = (qr_len) // 256
            data.write(bytes([0x1d, 0x28, 0x6b, pL, pH, 0x31, 0x50, 0x30]))
            data.write(qr_data)
            # Print QR
            data.write(b'\x1d\x28\x6b\x03\x00\x31\x51\x30')

        # Footer
        data.write(b'\n')
        if receipt.footer_message:
            data.write(self._build_line(ReceiptLine(
                text=receipt.footer_message,
                align="center"
            )))
        else:
            data.write(self._build_line(ReceiptLine(
                text="Thank you for your visit!",
                align="center"
            )))

        data.write(b'\n\n')

        # Beep if configured
        if self.config.beep_on_print:
            data.write(ESC.BEEP + b'\x02\x02')

        # Cut paper if configured
        if self.config.auto_cut:
            data.write(ESC.FEED_LINES + b'\x03')  # Feed 3 lines
            data.write(ESC.CUT_PARTIAL)

        # Open cash drawer if configured
        if self.config.open_drawer:
            data.write(ESC.DRAWER_KICK_2)

        return data.getvalue()

    def build_kitchen_ticket(
        self,
        order_number: str,
        table_number: str,
        items: List[ReceiptItem],
        waiter_name: str = "",
        order_type: str = "",
        notes: str = "",
        is_rush: bool = False,
        is_vip: bool = False,
        station: str = "",
    ) -> bytes:
        """Build a kitchen ticket."""
        data = BytesIO()

        # Initialize printer
        data.write(ESC.INIT)
        data.write(self._get_charset_command())

        # Station header
        if station:
            data.write(self._build_line(ReceiptLine(
                text=f"*** {station.upper()} ***",
                bold=True,
                double_height=True,
                align="center"
            )))
            data.write(self._build_divider("="))

        # Priority flags
        if is_rush or is_vip:
            flags = []
            if is_rush:
                flags.append("RUSH")
            if is_vip:
                flags.append("VIP")
            data.write(self._build_line(ReceiptLine(
                text=f"!!! {' / '.join(flags)} !!!",
                bold=True,
                double_height=True,
                double_width=True,
                align="center"
            )))

        # Order info
        data.write(self._build_line(ReceiptLine(
            text=f"Order #{order_number}",
            bold=True,
            double_height=True,
            align="center"
        )))

        info_line = f"Table: {table_number}"
        if order_type:
            info_line += f" ({order_type})"
        data.write(self._build_line(ReceiptLine(
            text=info_line,
            bold=True,
            align="center"
        )))

        if waiter_name:
            data.write(self._build_line(ReceiptLine(
                text=f"Server: {waiter_name}",
                align="center"
            )))

        # Timestamp
        data.write(self._build_line(ReceiptLine(
            text=datetime.now().strftime("%H:%M:%S"),
            align="center"
        )))

        data.write(self._build_divider("="))

        # Items
        for item in items:
            qty_str = f"{item.quantity:.0f}x" if item.quantity == int(item.quantity) else f"{item.quantity:.1f}x"
            data.write(self._build_line(ReceiptLine(
                text=f"{qty_str} {item.name}",
                bold=True,
                double_height=True
            )))

            # Modifiers
            for mod in item.modifiers:
                data.write(self._build_line(ReceiptLine(
                    text=f"    >> {mod}",
                    bold=True
                )))

        # Notes
        if notes:
            data.write(self._build_divider("-"))
            data.write(self._build_line(ReceiptLine(
                text=f"NOTE: {notes}",
                bold=True,
                underline=True
            )))

        data.write(b'\n\n')

        # Cut
        if self.config.auto_cut:
            data.write(ESC.FEED_LINES + b'\x02')
            data.write(ESC.CUT_PARTIAL)

        # Beep for kitchen
        data.write(ESC.BEEP + b'\x03\x03')

        return data.getvalue()

    async def connect(self) -> bool:
        """Connect to the printer."""
        if self.config.connection_type == ConnectionType.NETWORK:
            if not self.config.ip_address:
                logger.error("No IP address configured for network printer")
                return False

            try:
                self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._socket.settimeout(5.0)
                self._socket.connect((self.config.ip_address, self.config.port))
                logger.info(f"Connected to printer at {self.config.ip_address}:{self.config.port}")
                return True
            except Exception as e:
                logger.error(f"Failed to connect to printer: {e}")
                self._socket = None
                return False
        else:
            # USB/serial would use system print queue
            logger.info(f"USB printer configured: {self.config.usb_device}")
            return True

    async def disconnect(self):
        """Disconnect from the printer."""
        if self._socket:
            try:
                self._socket.close()
            except Exception as e:
                logger.warning(f"Failed to close printer socket for {self.config.name}: {e}")
            self._socket = None

    async def print_raw(self, data: bytes) -> bool:
        """Send raw data to the printer."""
        if self.config.connection_type == ConnectionType.NETWORK:
            if not self._socket:
                if not await self.connect():
                    return False

            try:
                self._socket.sendall(data)
                return True
            except Exception as e:
                logger.error(f"Failed to send data to printer: {e}")
                await self.disconnect()
                return False

        elif self.config.connection_type == ConnectionType.USB:
            if not self.config.usb_device:
                logger.error("No USB device configured")
                return False

            try:
                # Write to USB device or use lp command
                import subprocess
                process = await asyncio.create_subprocess_exec(
                    "lp", "-d", self.config.usb_device, "-o", "raw", "-",
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await process.communicate(data)

                if process.returncode == 0:
                    return True
                else:
                    logger.error(f"lp command failed: {stderr.decode()}")
                    return False

            except Exception as e:
                logger.error(f"Failed to print via USB: {e}")
                return False

        return False

    async def print_receipt(self, receipt: Receipt) -> bool:
        """Print a receipt."""
        data = self.build_receipt(receipt)
        return await self.print_raw(data)

    async def print_kitchen_ticket(
        self,
        order_number: str,
        table_number: str,
        items: List[ReceiptItem],
        **kwargs
    ) -> bool:
        """Print a kitchen ticket."""
        data = self.build_kitchen_ticket(
            order_number=order_number,
            table_number=table_number,
            items=items,
            **kwargs
        )
        return await self.print_raw(data)

    async def open_cash_drawer(self) -> bool:
        """Open the cash drawer."""
        return await self.print_raw(ESC.DRAWER_KICK_2)

    async def test_print(self) -> bool:
        """Print a test page."""
        data = BytesIO()
        data.write(ESC.INIT)
        data.write(self._get_charset_command())

        data.write(self._build_line(ReceiptLine(
            text="*** PRINTER TEST ***",
            bold=True,
            double_height=True,
            align="center"
        )))
        data.write(self._build_line(ReceiptLine(
            text=f"Printer: {self.config.name}",
            align="center"
        )))
        data.write(self._build_line(ReceiptLine(
            text=f"Type: {self.config.printer_type.value}",
            align="center"
        )))
        data.write(self._build_line(ReceiptLine(
            text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            align="center"
        )))
        data.write(self._build_divider("-"))
        data.write(self._build_line(ReceiptLine(text="Normal text")))
        data.write(self._build_line(ReceiptLine(text="Bold text", bold=True)))
        data.write(self._build_line(ReceiptLine(text="Double height", double_height=True)))
        data.write(self._build_line(ReceiptLine(text="Double width", double_width=True)))
        data.write(self._build_line(ReceiptLine(text="Underlined", underline=True)))
        data.write(self._build_divider("-"))
        data.write(self._build_line(ReceiptLine(text="Left aligned", align="left")))
        data.write(self._build_line(ReceiptLine(text="Center aligned", align="center")))
        data.write(self._build_line(ReceiptLine(text="Right aligned", align="right")))
        data.write(self._build_divider("="))
        data.write(self._build_line(ReceiptLine(
            text="Test complete!",
            bold=True,
            align="center"
        )))

        data.write(b'\n\n')
        if self.config.auto_cut:
            data.write(ESC.FEED_LINES + b'\x03')
            data.write(ESC.CUT_PARTIAL)

        return await self.print_raw(data.getvalue())


# ============================================================================
# Printer Manager (for multiple printers)
# ============================================================================

class PrinterManager:
    """Manage multiple printers."""

    def __init__(self):
        self.printers: Dict[str, PrinterService] = {}

    def add_printer(self, printer_id: str, config: PrinterConfig) -> PrinterService:
        """Add a printer."""
        service = PrinterService(config)
        self.printers[printer_id] = service
        return service

    def get_printer(self, printer_id: str) -> Optional[PrinterService]:
        """Get a printer by ID."""
        return self.printers.get(printer_id)

    def remove_printer(self, printer_id: str):
        """Remove a printer."""
        if printer_id in self.printers:
            del self.printers[printer_id]

    def list_printers(self) -> List[Dict[str, Any]]:
        """List all configured printers."""
        return [
            {
                "id": pid,
                "name": p.config.name,
                "type": p.config.printer_type.value,
                "connection": p.config.connection_type.value,
                "ip_address": p.config.ip_address,
                "port": p.config.port,
            }
            for pid, p in self.printers.items()
        ]

    async def close_all(self):
        """Close all printer connections."""
        for printer in self.printers.values():
            await printer.disconnect()


# Singleton manager
_printer_manager: Optional[PrinterManager] = None


def get_printer_manager() -> PrinterManager:
    """Get the printer manager singleton."""
    global _printer_manager
    if _printer_manager is None:
        _printer_manager = PrinterManager()
    return _printer_manager

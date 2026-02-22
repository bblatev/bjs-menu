"""
Unified Datecs Fiscal Printer Service
Supports all Datecs printer models with multiple connection methods

Supported Printers:
- Datecs FP-650, FP-700, FP-800, FP-2000 (desktop fiscal printers)
- Datecs DP-05, DP-15, DP-25, DP-35, DP-50, DP-150, DP-500 PLUS (legacy)
- Datecs Blue Cash 50 / BC 50MX (with integrated PinPad)
- Datecs WP-50 (wireless)
- Datecs FMP-10 (mobile)

Connection Methods:
- FPGate REST API (recommended for most setups)
- ErpNet.FP REST API (alternative)
- POS Fiscal Bridge WebSocket (for BC 50MX)
- Direct Serial/USB (for legacy printers)
"""
import asyncio
import logging
from enum import Enum
from typing import Dict, Any, List, Optional, Union
from decimal import Decimal
from dataclasses import dataclass
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class DatecsModel(str, Enum):
    """Supported Datecs printer models"""
    # Modern desktop fiscal printers
    FP650 = "FP-650"
    FP700 = "FP-700"
    FP800 = "FP-800"
    FP2000 = "FP-2000"

    # Blue Cash series (with PinPad)
    BC50 = "BC-50"
    BC50MX = "BC-50MX"

    # Legacy desktop printers
    DP05 = "DP-05"
    DP15 = "DP-15"
    DP25 = "DP-25"
    DP35 = "DP-35"
    DP50 = "DP-50"
    DP150 = "DP-150"
    DP500_PLUS = "DP-500 PLUS"

    # Mobile/Wireless
    WP50 = "WP-50"
    FMP10 = "FMP-10"

    # Auto-detect
    AUTO = "auto"


class ConnectionMethod(str, Enum):
    """Connection methods for Datecs printers"""
    FPGATE = "fpgate"           # FPGate REST API
    ERPNET_FP = "erpnet_fp"     # ErpNet.FP REST API
    POS_BRIDGE = "pos_bridge"   # POS Fiscal Bridge WebSocket
    SERIAL = "serial"           # Direct serial connection
    USB = "usb"                 # USB connection
    NETWORK = "network"         # Network TCP/IP
    AUTO = "auto"               # Auto-detect


class VATGroup(str, Enum):
    """Bulgarian VAT groups"""
    A = "A"  # 20% standard rate
    B = "B"  # 20% standard rate (alternative)
    C = "C"  # 9% reduced rate (food/drinks)
    D = "D"  # 0% zero rate
    E = "E"  # Exempt


@dataclass
class PrinterConfig:
    """Configuration for a Datecs printer"""
    model: DatecsModel = DatecsModel.AUTO
    connection: ConnectionMethod = ConnectionMethod.AUTO

    # FPGate settings
    fpgate_url: str = None  # Resolved from settings at runtime
    fpgate_printer_id: str = "FP1"

    # ErpNet.FP settings
    erpnet_host: str = None  # Resolved from settings at runtime
    erpnet_port: int = None  # Resolved from settings at runtime

    # POS Fiscal Bridge settings
    pos_bridge_host: str = None  # Resolved from settings at runtime
    pos_bridge_port: int = 443
    pos_bridge_ssl: bool = True

    # Serial/USB settings
    serial_port: str = "/dev/ttyUSB0"
    baudrate: int = 115200

    # Network settings
    network_host: str = ""
    network_port: int = 4999

    # Operator settings
    operator: str = "1"
    operator_password: str = "0000"

    # Timeout
    timeout: float = 30.0

    def __post_init__(self):
        """Resolve None defaults from centralized settings."""
        from app.core.config import settings
        if self.fpgate_url is None:
            self.fpgate_url = settings.fpgate_url
        if self.erpnet_host is None:
            self.erpnet_host = settings.erpnet_fp_host
        if self.erpnet_port is None:
            self.erpnet_port = settings.erpnet_fp_port
        if self.pos_bridge_host is None:
            self.pos_bridge_host = settings.pos_bridge_host


class DatecsPrinterDriver(ABC):
    """Abstract base class for Datecs printer drivers"""

    @abstractmethod
    async def check_status(self) -> Dict[str, Any]:
        """Check printer status"""
        raise NotImplementedError("Subclasses must implement check_status")

    @abstractmethod
    async def print_fiscal_receipt(
        self,
        items: List[Dict[str, Any]],
        payments: List[Dict[str, Any]],
        operator: str = "1"
    ) -> Dict[str, Any]:
        """Print fiscal receipt"""
        raise NotImplementedError("Subclasses must implement print_fiscal_receipt")

    @abstractmethod
    async def print_x_report(self) -> Dict[str, Any]:
        """Print X report"""
        raise NotImplementedError("Subclasses must implement print_x_report")

    @abstractmethod
    async def print_z_report(self) -> Dict[str, Any]:
        """Print Z report"""
        raise NotImplementedError("Subclasses must implement print_z_report")

    @abstractmethod
    async def void_receipt(self) -> Dict[str, Any]:
        """Void current receipt"""
        raise NotImplementedError("Subclasses must implement void_receipt")

    @abstractmethod
    async def print_non_fiscal(self, lines: List[str], title: str = "") -> Dict[str, Any]:
        """Print non-fiscal text"""
        raise NotImplementedError("Subclasses must implement print_non_fiscal")


class FPGateDriver(DatecsPrinterDriver):
    """FPGate REST API driver for Datecs printers"""

    def __init__(self, config: PrinterConfig):
        self.config = config
        self.base_url = config.fpgate_url.rstrip("/")
        self.printer_id = config.fpgate_printer_id

    async def _request(self, command: Union[str, Dict], params: Dict = None) -> Dict[str, Any]:
        import httpx
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                if isinstance(command, str):
                    payload = {
                        "printer": self.printer_id,
                        "command": command
                    }
                    if params:
                        payload["params"] = params
                else:
                    payload = {
                        "printer": self.printer_id,
                        **command
                    }

                response = await client.post(f"{self.base_url}/print/", json=payload)
                return response.json()
        except Exception as e:
            logger.error(f"FPGate request failed: {e}")
            return {"success": False, "error": str(e)}

    async def check_status(self) -> Dict[str, Any]:
        result = await self._request("PrinterStatus")
        return {
            "connected": "error" not in result,
            "status": result.get("status", "unknown"),
            "model": result.get("model"),
            "serial": result.get("serialNumber"),
            "fiscal_number": result.get("fiscalNumber"),
            "raw": result
        }

    async def print_fiscal_receipt(
        self,
        items: List[Dict[str, Any]],
        payments: List[Dict[str, Any]],
        operator: str = "1"
    ) -> Dict[str, Any]:
        commands = [
            {
                "command": "OpenFiscalReceipt",
                "params": {
                    "operator": operator,
                    "password": self.config.operator_password
                }
            }
        ]

        # Add items
        for item in items:
            name = item.get("name", "Item")
            if isinstance(name, dict):
                name = name.get("bg") or name.get("en") or "Item"

            commands.append({
                "command": "SellPLU",
                "params": {
                    "text": str(name)[:32],
                    "vatGroup": item.get("vat_group", "B"),
                    "price": float(item.get("price", 0)),
                    "quantity": float(item.get("quantity", 1))
                }
            })

        # Add payments
        for payment in payments:
            payment_type = payment.get("type", "cash")
            payment_code = {"cash": 0, "card": 1, "check": 2, "voucher": 3}.get(payment_type, 0)

            commands.append({
                "command": "Payment",
                "params": {
                    "type": payment_code,
                    "amount": float(payment.get("amount", 0))
                }
            })

        commands.append({"command": "CloseFiscalReceipt"})

        result = await self._request({"commands": commands})

        return {
            "success": "error" not in result,
            "receipt_number": result.get("receiptNumber"),
            "fiscal_number": result.get("fiscalNumber"),
            "error": result.get("error")
        }

    async def print_x_report(self) -> Dict[str, Any]:
        result = await self._request("PrintXReport")
        return {"success": "error" not in result, "raw": result}

    async def print_z_report(self) -> Dict[str, Any]:
        result = await self._request("PrintDailyReport")
        return {"success": "error" not in result, "raw": result}

    async def void_receipt(self) -> Dict[str, Any]:
        result = await self._request("CancelFiscalReceipt")
        return {"success": "error" not in result}

    async def print_non_fiscal(self, lines: List[str], title: str = "") -> Dict[str, Any]:
        commands = [{"command": "OpenNonFiscalReceipt"}]

        if title:
            commands.append({
                "command": "PrintNonFiscalText",
                "params": {"text": title.center(32)}
            })
            commands.append({
                "command": "PrintNonFiscalText",
                "params": {"text": "-" * 32}
            })

        for line in lines:
            commands.append({
                "command": "PrintNonFiscalText",
                "params": {"text": line[:32]}
            })

        commands.append({"command": "CloseNonFiscalReceipt"})

        result = await self._request({"commands": commands})
        return {"success": "error" not in result}

    async def process_card_payment(self, amount: Decimal, reference: str = "") -> Dict[str, Any]:
        """Process card payment via PLINK (BC 50MX only)"""
        import httpx
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/print/",
                    json={
                        "printer": self.printer_id,
                        "command": "StartPayment",
                        "params": {
                            "amount": float(amount) * 100,
                            "currency": "BGN",
                            "transactionType": "SALE",
                            "reference": reference
                        }
                    }
                )
                result = response.json()

                return {
                    "success": result.get("status") == "approved",
                    "approved": result.get("status") == "approved",
                    "transaction_id": result.get("transactionId"),
                    "auth_code": result.get("authCode"),
                    "card_type": result.get("cardType"),
                    "last_four": result.get("cardLastFour"),
                    "error": result.get("error") if result.get("status") != "approved" else None
                }
        except Exception as e:
            return {"success": False, "approved": False, "error": str(e)}


class ErpNetFPDriver(DatecsPrinterDriver):
    """ErpNet.FP REST API driver"""

    def __init__(self, config: PrinterConfig):
        self.config = config
        self.base_url = f"http://{config.erpnet_host}:{config.erpnet_port}"
        self.printer_id: Optional[str] = None

    async def _request(self, method: str, endpoint: str, data: Dict = None) -> Dict[str, Any]:
        import httpx
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                if method == "GET":
                    response = await client.get(f"{self.base_url}{endpoint}")
                else:
                    response = await client.post(f"{self.base_url}{endpoint}", json=data or {})
                return response.json()
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def _ensure_printer(self):
        if not self.printer_id:
            printers = await self._request("GET", "/printers")
            for key in printers:
                if key not in ["ok", "error"]:
                    self.printer_id = key
                    break

    async def check_status(self) -> Dict[str, Any]:
        await self._ensure_printer()
        if not self.printer_id:
            return {"connected": False, "error": "No printer found"}

        result = await self._request("GET", f"/printers/{self.printer_id}")
        return {
            "connected": result.get("ok", True) and "error" not in result,
            "printer_id": self.printer_id,
            "raw": result
        }

    async def print_fiscal_receipt(
        self,
        items: List[Dict[str, Any]],
        payments: List[Dict[str, Any]],
        operator: str = "1"
    ) -> Dict[str, Any]:
        await self._ensure_printer()
        if not self.printer_id:
            return {"success": False, "error": "No printer available"}

        # Convert items to ErpNet.FP format
        erpnet_items = []
        for item in items:
            name = item.get("name", "Item")
            if isinstance(name, dict):
                name = name.get("bg") or name.get("en") or "Item"

            erpnet_items.append({
                "text": str(name)[:32],
                "quantity": float(item.get("quantity", 1)),
                "unitPrice": float(item.get("price", 0)),
                "taxGroup": self._vat_to_tax_group(item.get("vat_group", "B"))
            })

        # Convert payments
        erpnet_payments = []
        for payment in payments:
            erpnet_payments.append({
                "amount": float(payment.get("amount", 0)),
                "paymentType": payment.get("type", "cash")
            })

        result = await self._request(
            "POST",
            f"/printers/{self.printer_id}/receipt",
            {"items": erpnet_items, "payments": erpnet_payments}
        )

        return {
            "success": result.get("ok", False),
            "receipt_number": result.get("receiptNumber"),
            "fiscal_number": result.get("fiscalMemorySerialNumber"),
            "error": result.get("error")
        }

    async def print_x_report(self) -> Dict[str, Any]:
        await self._ensure_printer()
        if not self.printer_id:
            return {"success": False, "error": "No printer available"}

        result = await self._request("POST", f"/printers/{self.printer_id}/xreport", {})
        return {"success": result.get("ok", False), "raw": result}

    async def print_z_report(self) -> Dict[str, Any]:
        await self._ensure_printer()
        if not self.printer_id:
            return {"success": False, "error": "No printer available"}

        result = await self._request("POST", f"/printers/{self.printer_id}/zreport", {})
        return {"success": result.get("ok", False), "raw": result}

    async def void_receipt(self) -> Dict[str, Any]:
        # ErpNet.FP doesn't have direct void - need to print reversal
        return {"success": False, "error": "Use reversal receipt instead"}

    async def print_non_fiscal(self, lines: List[str], title: str = "") -> Dict[str, Any]:
        # ErpNet.FP might not support non-fiscal directly
        return {"success": False, "error": "Non-fiscal printing not supported via ErpNet.FP"}

    def _vat_to_tax_group(self, vat_group: str) -> int:
        """Convert VAT group letter to tax group number"""
        mapping = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5}
        return mapping.get(vat_group.upper(), 2)


class DatecsUnifiedService:
    """
    Unified service for all Datecs fiscal printers

    Automatically selects the best driver based on configuration
    and printer model.
    """

    def __init__(self, config: PrinterConfig = None):
        self.config = config or PrinterConfig()
        self.driver: Optional[DatecsPrinterDriver] = None
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize the printer connection"""
        if self._initialized:
            return True

        # Select driver based on connection method
        if self.config.connection == ConnectionMethod.AUTO:
            # Try to auto-detect best connection
            self.driver = await self._auto_detect_driver()
        elif self.config.connection == ConnectionMethod.FPGATE:
            self.driver = FPGateDriver(self.config)
        elif self.config.connection == ConnectionMethod.ERPNET_FP:
            self.driver = ErpNetFPDriver(self.config)
        elif self.config.connection == ConnectionMethod.POS_BRIDGE:
            from app.services.pos_fiscal_bridge_service import POSFiscalBridgeService
            # Wrap POS Bridge in driver interface
            self.driver = self._create_pos_bridge_driver()
        else:
            self.driver = FPGateDriver(self.config)

        if self.driver:
            status = await self.driver.check_status()
            self._initialized = status.get("connected", False)
            return self._initialized

        return False

    async def _auto_detect_driver(self) -> Optional[DatecsPrinterDriver]:
        """Auto-detect the best available driver"""
        # Try FPGate first (most common)
        fpgate_driver = FPGateDriver(self.config)
        status = await fpgate_driver.check_status()
        if status.get("connected"):
            logger.info("Auto-detected FPGate connection")
            return fpgate_driver

        # Try ErpNet.FP
        erpnet_driver = ErpNetFPDriver(self.config)
        status = await erpnet_driver.check_status()
        if status.get("connected"):
            logger.info("Auto-detected ErpNet.FP connection")
            return erpnet_driver

        # Fall back to FPGate (will show connection error)
        logger.warning("No printer connection detected, defaulting to FPGate")
        return fpgate_driver

    def _create_pos_bridge_driver(self):
        """Create a wrapper driver for POS Fiscal Bridge"""
        # This would need a proper adapter implementation
        return FPGateDriver(self.config)  # Fallback for now

    async def get_status(self) -> Dict[str, Any]:
        """Get printer status"""
        if not await self.initialize():
            return {"connected": False, "error": "Printer not initialized"}
        return await self.driver.check_status()

    async def print_receipt(
        self,
        items: List[Dict[str, Any]],
        payment_type: str = "cash",
        payment_amount: float = None,
        operator: str = None
    ) -> Dict[str, Any]:
        """
        Print a fiscal receipt

        Args:
            items: List of items with name, price, quantity, vat_group
            payment_type: "cash", "card", "voucher"
            payment_amount: Amount paid (for change calculation)
            operator: Operator ID
        """
        if not await self.initialize():
            return {"success": False, "error": "Printer not initialized"}

        # Calculate total if payment_amount not provided
        if payment_amount is None:
            payment_amount = sum(
                float(item.get("price", 0)) * float(item.get("quantity", 1))
                for item in items
            )

        payments = [{
            "type": payment_type,
            "amount": payment_amount
        }]

        return await self.driver.print_fiscal_receipt(
            items=items,
            payments=payments,
            operator=operator or self.config.operator
        )

    async def print_x_report(self) -> Dict[str, Any]:
        """Print X report (current day summary)"""
        if not await self.initialize():
            return {"success": False, "error": "Printer not initialized"}
        return await self.driver.print_x_report()

    async def print_z_report(self) -> Dict[str, Any]:
        """Print Z report (daily closing)"""
        if not await self.initialize():
            return {"success": False, "error": "Printer not initialized"}
        return await self.driver.print_z_report()

    async def void_receipt(self) -> Dict[str, Any]:
        """Void current open receipt"""
        if not await self.initialize():
            return {"success": False, "error": "Printer not initialized"}
        return await self.driver.void_receipt()

    async def print_non_fiscal(
        self,
        lines: List[str],
        title: str = ""
    ) -> Dict[str, Any]:
        """Print non-fiscal text (kitchen ticket, etc.)"""
        if not await self.initialize():
            return {"success": False, "error": "Printer not initialized"}
        return await self.driver.print_non_fiscal(lines, title)

    async def print_kitchen_ticket(
        self,
        order_number: str,
        table: str,
        items: List[Dict[str, Any]],
        notes: str = ""
    ) -> Dict[str, Any]:
        """Print a kitchen ticket"""
        lines = [
            f"Order: {order_number}",
            f"Table: {table}",
            "-" * 32
        ]

        for item in items:
            name = item.get("name", "Item")
            if isinstance(name, dict):
                name = name.get("bg") or name.get("en") or "Item"
            qty = item.get("quantity", 1)
            lines.append(f"{qty}x {str(name)[:28]}")

            if item.get("notes"):
                lines.append(f"  -> {item['notes'][:28]}")

        if notes:
            lines.append("-" * 32)
            lines.append(f"Note: {notes[:30]}")

        lines.append("-" * 32)
        from datetime import datetime, timezone
        lines.append(datetime.now(timezone.utc).strftime("%H:%M:%S"))

        return await self.print_non_fiscal(lines, "KITCHEN ORDER")

    async def process_card_payment(
        self,
        amount: Decimal,
        reference: str = ""
    ) -> Dict[str, Any]:
        """
        Process card payment via integrated PinPad (BC 50MX only)
        """
        if not await self.initialize():
            return {"success": False, "error": "Printer not initialized"}

        if isinstance(self.driver, FPGateDriver):
            return await self.driver.process_card_payment(amount, reference)

        return {"success": False, "error": "Card payments not supported for this printer model"}

    async def cash_in(self, amount: Decimal) -> Dict[str, Any]:
        """Cash in (service deposit)"""
        if not await self.initialize():
            return {"success": False, "error": "Printer not initialized"}

        if isinstance(self.driver, ErpNetFPDriver):
            await self.driver._ensure_printer()
            return await self.driver._request(
                "POST",
                f"/printers/{self.driver.printer_id}/deposit",
                {"amount": float(amount)}
            )

        # FPGate implementation
        if isinstance(self.driver, FPGateDriver):
            return await self.driver._request("CashIn", {"amount": float(amount)})

        return {"success": False, "error": "Cash operations not supported"}

    async def cash_out(self, amount: Decimal) -> Dict[str, Any]:
        """Cash out (service withdrawal)"""
        if not await self.initialize():
            return {"success": False, "error": "Printer not initialized"}

        if isinstance(self.driver, ErpNetFPDriver):
            await self.driver._ensure_printer()
            return await self.driver._request(
                "POST",
                f"/printers/{self.driver.printer_id}/withdraw",
                {"amount": float(amount)}
            )

        if isinstance(self.driver, FPGateDriver):
            return await self.driver._request("CashOut", {"amount": float(amount)})

        return {"success": False, "error": "Cash operations not supported"}

    async def print_duplicate(self) -> Dict[str, Any]:
        """Print duplicate of last receipt"""
        if not await self.initialize():
            return {"success": False, "error": "Printer not initialized"}

        if isinstance(self.driver, FPGateDriver):
            return await self.driver._request("PrintDuplicate")

        if isinstance(self.driver, ErpNetFPDriver):
            await self.driver._ensure_printer()
            return await self.driver._request(
                "POST",
                f"/printers/{self.driver.printer_id}/duplicate",
                {}
            )

        return {"success": False, "error": "Duplicate printing not supported"}

    async def get_last_receipt_info(self) -> Dict[str, Any]:
        """Get information about last printed receipt"""
        if not await self.initialize():
            return {"success": False, "error": "Printer not initialized"}

        if isinstance(self.driver, FPGateDriver):
            return await self.driver._request("GetLastReceiptInfo")

        return {"success": False, "error": "Not supported for this connection method"}


# Singleton instance
_datecs_service: Optional[DatecsUnifiedService] = None


def get_datecs_service(config: PrinterConfig = None) -> DatecsUnifiedService:
    """Get or create unified Datecs printer service"""
    global _datecs_service

    if _datecs_service is None or config is not None:
        if config is None:
            from app.core.config import settings
            config = PrinterConfig(
                fpgate_url=settings.fpgate_url,
                fpgate_printer_id=getattr(settings, "FPGATE_PRINTER_ID", "FP1"),
                erpnet_host=settings.erpnet_fp_host,
                erpnet_port=settings.erpnet_fp_port,
                operator=getattr(settings, "FPGATE_OPERATOR", "1"),
                operator_password=getattr(settings, "FPGATE_OPERATOR_PASSWORD", "0000")
            )
        _datecs_service = DatecsUnifiedService(config)

    return _datecs_service


# Convenience functions for common operations
async def print_fiscal_receipt(
    items: List[Dict[str, Any]],
    payment_type: str = "cash",
    payment_amount: float = None
) -> Dict[str, Any]:
    """Quick function to print a fiscal receipt"""
    service = get_datecs_service()
    return await service.print_receipt(items, payment_type, payment_amount)


async def print_kitchen_ticket(
    order_number: str,
    table: str,
    items: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Quick function to print a kitchen ticket"""
    service = get_datecs_service()
    return await service.print_kitchen_ticket(order_number, table, items)


async def check_printer_status() -> Dict[str, Any]:
    """Quick function to check printer status"""
    service = get_datecs_service()
    return await service.get_status()

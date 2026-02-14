"""
Unified Fiscal Printer Service
Provides a single interface to work with all supported fiscal printers
"""

import asyncio
import httpx
import json
import logging
from typing import List, Dict, Any, Optional
from decimal import Decimal
from datetime import datetime

from .base import (
    FiscalPrinterDriver,
    PrinterConfig,
    PrinterStatus,
    PrintResult,
    ReceiptItem,
    PaymentType,
    VATGroup,
    PrinterDriverFactory
)
from .registry import (
    PrinterRegistry,
    PrinterManufacturer,
    PrinterModel,
    ConnectionType,
    get_printer_registry,
    get_printer_by_model
)
from app.core.config import settings

logger = logging.getLogger(__name__)


# =============================================================================
# DATECS DRIVERS
# =============================================================================

class DatecsFPGateDriver(FiscalPrinterDriver):
    """DATECS driver using FPGate REST API"""

    def __init__(self, config: PrinterConfig):
        super().__init__(config)
        self.base_url = config.api_url or settings.FPGATE_URL
        self.printer_id = config.printer_id or settings.FPGATE_PRINTER_ID
        self._client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> bool:
        try:
            self._client = httpx.AsyncClient(timeout=30.0)
            status = await self.get_status()
            self._connected = status.is_online
            return self._connected
        except Exception as e:
            logger.error(f"FPGate connection failed: {e}")
            self._connected = False
            return False

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
        self._connected = False

    async def _send_command(self, command: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send command to FPGate"""
        if not self._client:
            raise RuntimeError("Not connected to FPGate")

        url = f"{self.base_url}/printers/{self.printer_id}/{command}"
        try:
            if data:
                response = await self._client.post(url, json=data)
            else:
                response = await self._client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"FPGate command {command} failed: {e}")
            raise

    async def get_status(self) -> PrinterStatus:
        try:
            data = await self._send_command("status")
            return PrinterStatus(
                is_online=True,
                is_ready=data.get("ready", False),
                has_paper=not data.get("paper_out", False),
                cover_open=data.get("cover_open", False),
                fiscal_memory_full=data.get("fm_full", False),
                serial_number=data.get("serial_number"),
                firmware_version=data.get("firmware"),
                current_receipt_number=data.get("last_receipt_number"),
                daily_turnover=Decimal(str(data.get("daily_turnover", 0)))
            )
        except Exception as e:
            return PrinterStatus(
                is_online=False,
                error_message=str(e)
            )

    async def print_fiscal_receipt(
        self,
        items: List[ReceiptItem],
        payments: List[tuple[PaymentType, Decimal]],
        operator_id: Optional[str] = None,
        unique_receipt_number: Optional[str] = None
    ) -> PrintResult:
        try:
            receipt_data = {
                "operator": operator_id or self.config.operator_id,
                "password": self.config.operator_password,
                "items": [
                    {
                        "name": item.name[:36],
                        "quantity": float(item.quantity),
                        "price": float(item.unit_price),
                        "vat_group": item.vat_group.value,
                        "discount_percent": float(item.discount_percent) if item.discount_percent else None
                    }
                    for item in items
                ],
                "payments": [
                    {
                        "type": self._map_payment_type(pt),
                        "amount": float(amount)
                    }
                    for pt, amount in payments
                ]
            }
            if unique_receipt_number:
                receipt_data["unp"] = unique_receipt_number

            result = await self._send_command("receipt", receipt_data)
            return PrintResult(
                success=result.get("success", False),
                receipt_number=result.get("receipt_number"),
                fiscal_memory_number=result.get("fiscal_number"),
                timestamp=datetime.now(),
                raw_response=json.dumps(result)
            )
        except Exception as e:
            return PrintResult(success=False, error_message=str(e))

    async def print_reversal_receipt(
        self,
        original_receipt_number: str,
        original_receipt_date: datetime,
        items: List[ReceiptItem],
        reason: str = "Грешка на оператора"
    ) -> PrintResult:
        try:
            data = {
                "operator": self.config.operator_id,
                "password": self.config.operator_password,
                "original_receipt": original_receipt_number,
                "original_date": original_receipt_date.strftime("%Y-%m-%d"),
                "reason": reason,
                "items": [
                    {
                        "name": item.name[:36],
                        "quantity": float(item.quantity),
                        "price": float(item.unit_price),
                        "vat_group": item.vat_group.value
                    }
                    for item in items
                ]
            }
            result = await self._send_command("reversal", data)
            return PrintResult(
                success=result.get("success", False),
                receipt_number=result.get("receipt_number"),
                timestamp=datetime.now()
            )
        except Exception as e:
            return PrintResult(success=False, error_message=str(e))

    async def void_receipt(self) -> PrintResult:
        try:
            result = await self._send_command("void")
            return PrintResult(success=result.get("success", False))
        except Exception as e:
            return PrintResult(success=False, error_message=str(e))

    async def print_x_report(self) -> PrintResult:
        try:
            result = await self._send_command("report/x")
            return PrintResult(
                success=result.get("success", False),
                additional_data=result
            )
        except Exception as e:
            return PrintResult(success=False, error_message=str(e))

    async def print_z_report(self) -> PrintResult:
        try:
            result = await self._send_command("report/z")
            return PrintResult(
                success=result.get("success", False),
                receipt_number=result.get("z_number"),
                additional_data=result
            )
        except Exception as e:
            return PrintResult(success=False, error_message=str(e))

    async def print_periodic_report(
        self,
        start_date: datetime,
        end_date: datetime,
        detailed: bool = False
    ) -> PrintResult:
        try:
            data = {
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "detailed": detailed
            }
            result = await self._send_command("report/periodic", data)
            return PrintResult(success=result.get("success", False))
        except Exception as e:
            return PrintResult(success=False, error_message=str(e))

    async def open_drawer(self) -> PrintResult:
        try:
            result = await self._send_command("drawer")
            return PrintResult(success=result.get("success", False))
        except Exception as e:
            return PrintResult(success=False, error_message=str(e))

    async def cash_in(self, amount: Decimal, description: str = "") -> PrintResult:
        try:
            data = {"amount": float(amount), "description": description}
            result = await self._send_command("cash/in", data)
            return PrintResult(success=result.get("success", False))
        except Exception as e:
            return PrintResult(success=False, error_message=str(e))

    async def cash_out(self, amount: Decimal, description: str = "") -> PrintResult:
        try:
            data = {"amount": float(amount), "description": description}
            result = await self._send_command("cash/out", data)
            return PrintResult(success=result.get("success", False))
        except Exception as e:
            return PrintResult(success=False, error_message=str(e))

    async def print_non_fiscal(self, lines: List[str]) -> PrintResult:
        try:
            data = {"lines": lines}
            result = await self._send_command("print", data)
            return PrintResult(success=result.get("success", False))
        except Exception as e:
            return PrintResult(success=False, error_message=str(e))

    async def feed_paper(self, lines: int = 3) -> PrintResult:
        try:
            data = {"lines": lines}
            result = await self._send_command("feed", data)
            return PrintResult(success=result.get("success", False))
        except Exception as e:
            return PrintResult(success=False, error_message=str(e))

    async def cut_paper(self) -> PrintResult:
        try:
            result = await self._send_command("cut")
            return PrintResult(success=result.get("success", False))
        except Exception as e:
            return PrintResult(success=False, error_message=str(e))

    def _map_payment_type(self, pt: PaymentType) -> str:
        mapping = {
            PaymentType.CASH: "cash",
            PaymentType.CARD: "card",
            PaymentType.CHECK: "check",
            PaymentType.VOUCHER: "voucher",
            PaymentType.CREDIT: "credit",
            PaymentType.DEBIT_CARD: "card",
            PaymentType.BANK_TRANSFER: "bank",
            PaymentType.MIXED: "mixed"
        }
        return mapping.get(pt, "cash")


class DatecsErpNetDriver(FiscalPrinterDriver):
    """DATECS driver using ErpNet.FP REST API"""

    def __init__(self, config: PrinterConfig):
        super().__init__(config)
        host = config.host or settings.ERPNET_FP_HOST
        port = config.port or settings.ERPNET_FP_PORT
        self.base_url = f"http://{host}:{port}"
        self._client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> bool:
        try:
            self._client = httpx.AsyncClient(timeout=30.0)
            response = await self._client.get(f"{self.base_url}/printers")
            self._connected = response.status_code == 200
            return self._connected
        except Exception as e:
            logger.error(f"ErpNet.FP connection failed: {e}")
            self._connected = False
            return False

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
        self._connected = False

    async def _send_task(self, task_type: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send task to ErpNet.FP"""
        if not self._client:
            raise RuntimeError("Not connected")

        task = {"taskType": task_type}
        if data:
            task.update(data)

        response = await self._client.post(
            f"{self.base_url}/printers/{self.config.printer_id}/task",
            json=task
        )
        response.raise_for_status()
        return response.json()

    async def get_status(self) -> PrinterStatus:
        try:
            result = await self._send_task("rawRequest", {"rawRequest": ["\x1bI"]})
            return PrinterStatus(
                is_online=True,
                is_ready=True,
                additional_info=result
            )
        except Exception as e:
            return PrinterStatus(is_online=False, error_message=str(e))

    async def print_fiscal_receipt(
        self,
        items: List[ReceiptItem],
        payments: List[tuple[PaymentType, Decimal]],
        operator_id: Optional[str] = None,
        unique_receipt_number: Optional[str] = None
    ) -> PrintResult:
        try:
            receipt_items = []
            for item in items:
                receipt_items.append({
                    "text": item.name[:36],
                    "quantity": float(item.quantity),
                    "unitPrice": float(item.unit_price),
                    "taxGroup": ord(item.vat_group.value) - ord('A') + 1
                })

            payment_data = []
            for pt, amount in payments:
                payment_data.append({
                    "paymentType": self._map_payment_type(pt),
                    "amount": float(amount)
                })

            data = {
                "receipt": {
                    "receiptType": "sale",
                    "operator": operator_id or self.config.operator_id,
                    "operatorPassword": self.config.operator_password,
                    "items": receipt_items,
                    "payments": payment_data
                }
            }
            if unique_receipt_number:
                data["receipt"]["uniqueSaleNumber"] = unique_receipt_number

            result = await self._send_task("receipt", data)
            return PrintResult(
                success=result.get("ok", False),
                receipt_number=result.get("receiptNumber"),
                timestamp=datetime.now()
            )
        except Exception as e:
            return PrintResult(success=False, error_message=str(e))

    async def print_reversal_receipt(
        self,
        original_receipt_number: str,
        original_receipt_date: datetime,
        items: List[ReceiptItem],
        reason: str = "Грешка на оператора"
    ) -> PrintResult:
        try:
            receipt_items = [{
                "text": item.name[:36],
                "quantity": float(item.quantity),
                "unitPrice": float(item.unit_price),
                "taxGroup": ord(item.vat_group.value) - ord('A') + 1
            } for item in items]

            data = {
                "receipt": {
                    "receiptType": "reversal",
                    "operator": self.config.operator_id,
                    "operatorPassword": self.config.operator_password,
                    "items": receipt_items,
                    "reversalInfo": {
                        "receiptNumber": original_receipt_number,
                        "receiptDate": original_receipt_date.strftime("%Y-%m-%d"),
                        "reason": reason
                    }
                }
            }
            result = await self._send_task("receipt", data)
            return PrintResult(
                success=result.get("ok", False),
                receipt_number=result.get("receiptNumber")
            )
        except Exception as e:
            return PrintResult(success=False, error_message=str(e))

    async def void_receipt(self) -> PrintResult:
        try:
            result = await self._send_task("voidReceipt")
            return PrintResult(success=result.get("ok", False))
        except Exception as e:
            return PrintResult(success=False, error_message=str(e))

    async def print_x_report(self) -> PrintResult:
        try:
            result = await self._send_task("report", {"reportType": "X"})
            return PrintResult(success=result.get("ok", False))
        except Exception as e:
            return PrintResult(success=False, error_message=str(e))

    async def print_z_report(self) -> PrintResult:
        try:
            result = await self._send_task("report", {"reportType": "Z"})
            return PrintResult(success=result.get("ok", False))
        except Exception as e:
            return PrintResult(success=False, error_message=str(e))

    async def print_periodic_report(
        self,
        start_date: datetime,
        end_date: datetime,
        detailed: bool = False
    ) -> PrintResult:
        try:
            data = {
                "reportType": "periodicByDate" if detailed else "periodicByDateShort",
                "startDate": start_date.strftime("%Y-%m-%d"),
                "endDate": end_date.strftime("%Y-%m-%d")
            }
            result = await self._send_task("report", data)
            return PrintResult(success=result.get("ok", False))
        except Exception as e:
            return PrintResult(success=False, error_message=str(e))

    async def open_drawer(self) -> PrintResult:
        try:
            result = await self._send_task("openDrawer")
            return PrintResult(success=result.get("ok", False))
        except Exception as e:
            return PrintResult(success=False, error_message=str(e))

    async def cash_in(self, amount: Decimal, description: str = "") -> PrintResult:
        try:
            data = {"amount": float(amount), "text": description}
            result = await self._send_task("cashIn", data)
            return PrintResult(success=result.get("ok", False))
        except Exception as e:
            return PrintResult(success=False, error_message=str(e))

    async def cash_out(self, amount: Decimal, description: str = "") -> PrintResult:
        try:
            data = {"amount": float(amount), "text": description}
            result = await self._send_task("cashOut", data)
            return PrintResult(success=result.get("ok", False))
        except Exception as e:
            return PrintResult(success=False, error_message=str(e))

    async def print_non_fiscal(self, lines: List[str]) -> PrintResult:
        try:
            result = await self._send_task("printText", {"lines": lines})
            return PrintResult(success=result.get("ok", False))
        except Exception as e:
            return PrintResult(success=False, error_message=str(e))

    async def feed_paper(self, lines: int = 3) -> PrintResult:
        return await self.print_non_fiscal([""] * lines)

    async def cut_paper(self) -> PrintResult:
        try:
            result = await self._send_task("rawRequest", {"rawRequest": ["\x1dV\x00"]})
            return PrintResult(success=True)
        except Exception as e:
            return PrintResult(success=False, error_message=str(e))

    def _map_payment_type(self, pt: PaymentType) -> int:
        mapping = {
            PaymentType.CASH: 0,
            PaymentType.CARD: 1,
            PaymentType.CHECK: 2,
            PaymentType.VOUCHER: 3,
            PaymentType.CREDIT: 4,
            PaymentType.DEBIT_CARD: 1,
            PaymentType.BANK_TRANSFER: 5,
            PaymentType.MIXED: 0
        }
        return mapping.get(pt, 0)


# =============================================================================
# TREMOL DRIVERS
# =============================================================================

class TremolZFPLabDriver(FiscalPrinterDriver):
    """Tremol driver using ZFPLabServer API"""

    def __init__(self, config: PrinterConfig):
        super().__init__(config)
        self.base_url = config.api_url or "http://localhost:4444"
        self._client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> bool:
        try:
            self._client = httpx.AsyncClient(timeout=30.0)
            response = await self._client.get(f"{self.base_url}/api/status")
            self._connected = response.status_code == 200
            return self._connected
        except Exception as e:
            logger.error(f"Tremol ZFPLab connection failed: {e}")
            self._connected = False
            return False

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()
        self._connected = False

    async def get_status(self) -> PrinterStatus:
        try:
            response = await self._client.get(f"{self.base_url}/api/status")
            data = response.json()
            return PrinterStatus(
                is_online=True,
                is_ready=data.get("ready", False),
                has_paper=not data.get("paper_end", False),
                serial_number=data.get("serial_number")
            )
        except Exception as e:
            logger.warning(f"Failed to get Tremol printer status: {e}")
            return PrinterStatus(is_online=False)

    async def print_fiscal_receipt(
        self,
        items: List[ReceiptItem],
        payments: List[tuple[PaymentType, Decimal]],
        operator_id: Optional[str] = None,
        unique_receipt_number: Optional[str] = None
    ) -> PrintResult:
        try:
            data = {
                "operator": operator_id or self.config.operator_id,
                "items": [
                    {
                        "name": item.name[:30],
                        "qty": float(item.quantity),
                        "price": float(item.unit_price),
                        "vatGroup": item.vat_group.value
                    }
                    for item in items
                ],
                "payments": [
                    {"type": pt.value, "amount": float(amount)}
                    for pt, amount in payments
                ]
            }
            response = await self._client.post(f"{self.base_url}/api/receipt", json=data)
            result = response.json()
            return PrintResult(
                success=result.get("success", False),
                receipt_number=result.get("receiptNumber")
            )
        except Exception as e:
            return PrintResult(success=False, error_message=str(e))

    async def print_reversal_receipt(
        self,
        original_receipt_number: str,
        original_receipt_date: datetime,
        items: List[ReceiptItem],
        reason: str = "Грешка на оператора"
    ) -> PrintResult:
        return PrintResult(success=False, error_message="Not implemented for Tremol")

    async def void_receipt(self) -> PrintResult:
        try:
            response = await self._client.post(f"{self.base_url}/api/void")
            return PrintResult(success=response.status_code == 200)
        except Exception as e:
            return PrintResult(success=False, error_message=str(e))

    async def print_x_report(self) -> PrintResult:
        try:
            response = await self._client.post(f"{self.base_url}/api/report/x")
            return PrintResult(success=response.status_code == 200)
        except Exception as e:
            return PrintResult(success=False, error_message=str(e))

    async def print_z_report(self) -> PrintResult:
        try:
            response = await self._client.post(f"{self.base_url}/api/report/z")
            return PrintResult(success=response.status_code == 200)
        except Exception as e:
            return PrintResult(success=False, error_message=str(e))

    async def print_periodic_report(
        self,
        start_date: datetime,
        end_date: datetime,
        detailed: bool = False
    ) -> PrintResult:
        return PrintResult(success=False, error_message="Not implemented for Tremol")

    async def open_drawer(self) -> PrintResult:
        try:
            response = await self._client.post(f"{self.base_url}/api/drawer")
            return PrintResult(success=response.status_code == 200)
        except Exception as e:
            return PrintResult(success=False, error_message=str(e))

    async def cash_in(self, amount: Decimal, description: str = "") -> PrintResult:
        try:
            response = await self._client.post(
                f"{self.base_url}/api/cash/in",
                json={"amount": float(amount)}
            )
            return PrintResult(success=response.status_code == 200)
        except Exception as e:
            return PrintResult(success=False, error_message=str(e))

    async def cash_out(self, amount: Decimal, description: str = "") -> PrintResult:
        try:
            response = await self._client.post(
                f"{self.base_url}/api/cash/out",
                json={"amount": float(amount)}
            )
            return PrintResult(success=response.status_code == 200)
        except Exception as e:
            return PrintResult(success=False, error_message=str(e))

    async def print_non_fiscal(self, lines: List[str]) -> PrintResult:
        try:
            response = await self._client.post(
                f"{self.base_url}/api/print",
                json={"lines": lines}
            )
            return PrintResult(success=response.status_code == 200)
        except Exception as e:
            return PrintResult(success=False, error_message=str(e))

    async def feed_paper(self, lines: int = 3) -> PrintResult:
        return await self.print_non_fiscal([""] * lines)

    async def cut_paper(self) -> PrintResult:
        try:
            response = await self._client.post(f"{self.base_url}/api/cut")
            return PrintResult(success=response.status_code == 200)
        except Exception as e:
            return PrintResult(success=False, error_message=str(e))


# =============================================================================
# DAISY DRIVERS
# =============================================================================

class DaisyFiscalDriver(FiscalPrinterDriver):
    """Daisy driver using Daisy Fiscal Server API"""

    def __init__(self, config: PrinterConfig):
        super().__init__(config)
        self.base_url = config.api_url or "http://localhost:9999"
        self._client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> bool:
        try:
            self._client = httpx.AsyncClient(timeout=30.0)
            response = await self._client.get(f"{self.base_url}/status")
            self._connected = response.status_code == 200
            return self._connected
        except Exception as e:
            logger.error(f"Daisy connection failed: {e}")
            self._connected = False
            return False

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()
        self._connected = False

    async def get_status(self) -> PrinterStatus:
        try:
            response = await self._client.get(f"{self.base_url}/status")
            data = response.json()
            return PrinterStatus(
                is_online=True,
                is_ready=data.get("ready", False),
                has_paper=data.get("paper", True),
                serial_number=data.get("sn")
            )
        except Exception as e:
            logger.warning(f"Failed to get Daisy printer status: {e}")
            return PrinterStatus(is_online=False)

    async def print_fiscal_receipt(
        self,
        items: List[ReceiptItem],
        payments: List[tuple[PaymentType, Decimal]],
        operator_id: Optional[str] = None,
        unique_receipt_number: Optional[str] = None
    ) -> PrintResult:
        try:
            data = {
                "operator": operator_id or "1",
                "items": [
                    {
                        "name": item.name[:32],
                        "qty": float(item.quantity),
                        "price": float(item.unit_price),
                        "vat": item.vat_group.value
                    }
                    for item in items
                ],
                "payments": [
                    {"type": pt.value, "amount": float(amount)}
                    for pt, amount in payments
                ]
            }
            response = await self._client.post(f"{self.base_url}/receipt", json=data)
            result = response.json()
            return PrintResult(
                success=result.get("ok", False),
                receipt_number=result.get("num")
            )
        except Exception as e:
            return PrintResult(success=False, error_message=str(e))

    async def print_reversal_receipt(
        self,
        original_receipt_number: str,
        original_receipt_date: datetime,
        items: List[ReceiptItem],
        reason: str = "Грешка на оператора"
    ) -> PrintResult:
        return PrintResult(success=False, error_message="Not implemented for Daisy")

    async def void_receipt(self) -> PrintResult:
        try:
            response = await self._client.post(f"{self.base_url}/void")
            return PrintResult(success=response.status_code == 200)
        except Exception as e:
            return PrintResult(success=False, error_message=str(e))

    async def print_x_report(self) -> PrintResult:
        try:
            response = await self._client.post(f"{self.base_url}/report/x")
            return PrintResult(success=response.status_code == 200)
        except Exception as e:
            return PrintResult(success=False, error_message=str(e))

    async def print_z_report(self) -> PrintResult:
        try:
            response = await self._client.post(f"{self.base_url}/report/z")
            return PrintResult(success=response.status_code == 200)
        except Exception as e:
            return PrintResult(success=False, error_message=str(e))

    async def print_periodic_report(
        self,
        start_date: datetime,
        end_date: datetime,
        detailed: bool = False
    ) -> PrintResult:
        return PrintResult(success=False, error_message="Not implemented for Daisy")

    async def open_drawer(self) -> PrintResult:
        try:
            response = await self._client.post(f"{self.base_url}/drawer")
            return PrintResult(success=response.status_code == 200)
        except Exception as e:
            return PrintResult(success=False, error_message=str(e))

    async def cash_in(self, amount: Decimal, description: str = "") -> PrintResult:
        try:
            response = await self._client.post(
                f"{self.base_url}/cash/in",
                json={"amount": float(amount)}
            )
            return PrintResult(success=response.status_code == 200)
        except Exception as e:
            return PrintResult(success=False, error_message=str(e))

    async def cash_out(self, amount: Decimal, description: str = "") -> PrintResult:
        try:
            response = await self._client.post(
                f"{self.base_url}/cash/out",
                json={"amount": float(amount)}
            )
            return PrintResult(success=response.status_code == 200)
        except Exception as e:
            return PrintResult(success=False, error_message=str(e))

    async def print_non_fiscal(self, lines: List[str]) -> PrintResult:
        try:
            response = await self._client.post(
                f"{self.base_url}/print",
                json={"text": "\n".join(lines)}
            )
            return PrintResult(success=response.status_code == 200)
        except Exception as e:
            return PrintResult(success=False, error_message=str(e))

    async def feed_paper(self, lines: int = 3) -> PrintResult:
        return await self.print_non_fiscal([""] * lines)

    async def cut_paper(self) -> PrintResult:
        try:
            response = await self._client.post(f"{self.base_url}/cut")
            return PrintResult(success=response.status_code == 200)
        except Exception as e:
            return PrintResult(success=False, error_message=str(e))


# =============================================================================
# ELTRADE DRIVERS
# =============================================================================

class EltradeSerialDriver(FiscalPrinterDriver):
    """Eltrade driver using serial connection (placeholder)"""

    def __init__(self, config: PrinterConfig):
        super().__init__(config)
        # Eltrade typically uses direct serial or proprietary software

    async def connect(self) -> bool:
        # Would implement serial connection here
        return False

    async def disconnect(self) -> None:
        pass

    async def get_status(self) -> PrinterStatus:
        return PrinterStatus(is_online=False, error_message="Serial driver not implemented")

    async def print_fiscal_receipt(
        self,
        items: List[ReceiptItem],
        payments: List[tuple[PaymentType, Decimal]],
        operator_id: Optional[str] = None,
        unique_receipt_number: Optional[str] = None
    ) -> PrintResult:
        return PrintResult(success=False, error_message="Serial driver not implemented")

    async def print_reversal_receipt(
        self,
        original_receipt_number: str,
        original_receipt_date: datetime,
        items: List[ReceiptItem],
        reason: str = ""
    ) -> PrintResult:
        return PrintResult(success=False, error_message="Serial driver not implemented")

    async def void_receipt(self) -> PrintResult:
        return PrintResult(success=False, error_message="Serial driver not implemented")

    async def print_x_report(self) -> PrintResult:
        return PrintResult(success=False, error_message="Serial driver not implemented")

    async def print_z_report(self) -> PrintResult:
        return PrintResult(success=False, error_message="Serial driver not implemented")

    async def print_periodic_report(
        self,
        start_date: datetime,
        end_date: datetime,
        detailed: bool = False
    ) -> PrintResult:
        return PrintResult(success=False, error_message="Serial driver not implemented")

    async def open_drawer(self) -> PrintResult:
        return PrintResult(success=False, error_message="Serial driver not implemented")

    async def cash_in(self, amount: Decimal, description: str = "") -> PrintResult:
        return PrintResult(success=False, error_message="Serial driver not implemented")

    async def cash_out(self, amount: Decimal, description: str = "") -> PrintResult:
        return PrintResult(success=False, error_message="Serial driver not implemented")

    async def print_non_fiscal(self, lines: List[str]) -> PrintResult:
        return PrintResult(success=False, error_message="Serial driver not implemented")

    async def feed_paper(self, lines: int = 3) -> PrintResult:
        return PrintResult(success=False, error_message="Serial driver not implemented")

    async def cut_paper(self) -> PrintResult:
        return PrintResult(success=False, error_message="Serial driver not implemented")


# =============================================================================
# REGISTER DRIVERS
# =============================================================================

# Register DATECS drivers
PrinterDriverFactory.register("DATECS", "fpgate", DatecsFPGateDriver)
PrinterDriverFactory.register("DATECS", "erpnet_fp", DatecsErpNetDriver)

# Register Tremol drivers
PrinterDriverFactory.register("Tremol", "tremol_api", TremolZFPLabDriver)

# Register Daisy drivers
PrinterDriverFactory.register("Daisy", "daisy_api", DaisyFiscalDriver)

# Register Eltrade drivers
PrinterDriverFactory.register("Eltrade", "serial", EltradeSerialDriver)


# =============================================================================
# UNIFIED SERVICE
# =============================================================================

class UnifiedFiscalPrinterService:
    """
    Unified service for managing and using fiscal printers
    Handles printer discovery, configuration, and operation
    """

    def __init__(self):
        self.registry = get_printer_registry()
        self._active_drivers: Dict[str, FiscalPrinterDriver] = {}
        self._configs: Dict[str, PrinterConfig] = {}

    def get_all_printers(self) -> List[Dict[str, Any]]:
        """Get all available printer models"""
        return [
            {
                "id": p.id,
                "name": p.name,
                "manufacturer": p.manufacturer.value,
                "description": p.description,
                "connections": [c.value for c in p.connections],
                "features": [f.value for f in p.features],
                "paper_width": p.paper_width,
                "max_chars_per_line": p.max_chars_per_line,
                "is_mobile": p.is_mobile,
                "has_battery": p.has_battery,
                "has_display": p.has_display
            }
            for p in self.registry.get_all()
        ]

    def get_printers_by_manufacturer(self, manufacturer: str) -> List[Dict[str, Any]]:
        """Get printers by manufacturer"""
        try:
            mfr = PrinterManufacturer(manufacturer)
            printers = self.registry.get_by_manufacturer(mfr)
            return [
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "connections": [c.value for c in p.connections],
                    "features": [f.value for f in p.features]
                }
                for p in printers
            ]
        except ValueError:
            return []

    def get_manufacturers(self) -> List[Dict[str, Any]]:
        """Get list of manufacturers with printer counts"""
        return [
            {
                "id": m.value,
                "name": m.value,
                "printer_count": len(self.registry.get_by_manufacturer(m))
            }
            for m in PrinterManufacturer
        ]

    async def configure_printer(
        self,
        config_id: str,
        model_id: str,
        connection_type: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Configure a printer for use"""
        printer_model = get_printer_by_model(model_id)
        if not printer_model:
            return {"success": False, "error": f"Unknown printer model: {model_id}"}

        # Check if connection type is supported
        try:
            conn_type = ConnectionType(connection_type)
            if conn_type not in printer_model.connections:
                return {
                    "success": False,
                    "error": f"Connection type {connection_type} not supported for {printer_model.name}"
                }
        except ValueError:
            return {"success": False, "error": f"Unknown connection type: {connection_type}"}

        # Create config
        config = PrinterConfig(
            printer_id=config_id,
            model_id=model_id,
            connection_type=connection_type,
            **kwargs
        )

        # Create driver
        driver = PrinterDriverFactory.create(
            printer_model.manufacturer.value,
            connection_type,
            config
        )

        if not driver:
            return {
                "success": False,
                "error": f"No driver available for {printer_model.manufacturer.value}/{connection_type}"
            }

        # Try to connect
        connected = await driver.connect()
        if not connected:
            return {
                "success": False,
                "error": "Failed to connect to printer"
            }

        # Store config and driver
        self._configs[config_id] = config
        self._active_drivers[config_id] = driver

        return {
            "success": True,
            "config_id": config_id,
            "model": printer_model.name,
            "manufacturer": printer_model.manufacturer.value,
            "connection": connection_type
        }

    async def get_driver(self, config_id: str) -> Optional[FiscalPrinterDriver]:
        """Get active driver by config ID"""
        return self._active_drivers.get(config_id)

    async def get_status(self, config_id: str) -> Dict[str, Any]:
        """Get printer status"""
        driver = self._active_drivers.get(config_id)
        if not driver:
            return {"online": False, "error": "Printer not configured"}

        status = await driver.get_status()
        return {
            "online": status.is_online,
            "ready": status.is_ready,
            "has_paper": status.has_paper,
            "cover_open": status.cover_open,
            "serial_number": status.serial_number,
            "firmware": status.firmware_version,
            "error": status.error_message
        }

    async def print_receipt(
        self,
        config_id: str,
        items: List[Dict[str, Any]],
        payments: List[Dict[str, Any]],
        operator_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Print a fiscal receipt"""
        driver = self._active_drivers.get(config_id)
        if not driver:
            return {"success": False, "error": "Printer not configured"}

        # Convert items
        receipt_items = [
            ReceiptItem(
                name=item["name"],
                quantity=Decimal(str(item["quantity"])),
                unit_price=Decimal(str(item["price"])),
                vat_group=VATGroup(item.get("vat_group", "B"))
            )
            for item in items
        ]

        # Convert payments
        payment_list = [
            (PaymentType(p["type"]), Decimal(str(p["amount"])))
            for p in payments
        ]

        result = await driver.print_fiscal_receipt(receipt_items, payment_list, operator_id)
        return {
            "success": result.success,
            "receipt_number": result.receipt_number,
            "error": result.error_message
        }

    async def print_x_report(self, config_id: str) -> Dict[str, Any]:
        """Print X report"""
        driver = self._active_drivers.get(config_id)
        if not driver:
            return {"success": False, "error": "Printer not configured"}

        result = await driver.print_x_report()
        return {"success": result.success, "error": result.error_message}

    async def print_z_report(self, config_id: str) -> Dict[str, Any]:
        """Print Z report"""
        driver = self._active_drivers.get(config_id)
        if not driver:
            return {"success": False, "error": "Printer not configured"}

        result = await driver.print_z_report()
        return {"success": result.success, "error": result.error_message}

    async def open_drawer(self, config_id: str) -> Dict[str, Any]:
        """Open cash drawer"""
        driver = self._active_drivers.get(config_id)
        if not driver:
            return {"success": False, "error": "Printer not configured"}

        result = await driver.open_drawer()
        return {"success": result.success, "error": result.error_message}

    async def print_non_fiscal(self, config_id: str, lines: List[str]) -> Dict[str, Any]:
        """Print non-fiscal text"""
        driver = self._active_drivers.get(config_id)
        if not driver:
            return {"success": False, "error": "Printer not configured"}

        result = await driver.print_non_fiscal(lines)
        return {"success": result.success, "error": result.error_message}

    async def disconnect_all(self) -> None:
        """Disconnect all active printers"""
        for driver in self._active_drivers.values():
            await driver.disconnect()
        self._active_drivers.clear()


# Singleton instance
_service: Optional[UnifiedFiscalPrinterService] = None


def get_fiscal_printer_service() -> UnifiedFiscalPrinterService:
    """Get the unified fiscal printer service singleton"""
    global _service
    if _service is None:
        _service = UnifiedFiscalPrinterService()
    return _service

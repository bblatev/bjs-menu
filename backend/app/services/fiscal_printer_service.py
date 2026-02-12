"""
Fiscal Printer Service
Integration with FPGate for Datecs BC 50MX and other Bulgarian fiscal printers
"""
import httpx
from typing import Dict, Any, List, Optional
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class FiscalPrinterService:
    """
    Service for printing fiscal receipts via FPGate

    FPGate is a middleware that provides REST API access to fiscal printers.
    Download from: https://github.com/edabg/fpgate
    """

    def __init__(
        self,
        fpgate_url: str = None,
        printer_id: str = None,
        operator: str = None,
        operator_password: str = None
    ):
        from app.core.config import settings
        self.fpgate_url = (fpgate_url or settings.FPGATE_URL).rstrip("/")
        self.printer_id = printer_id or settings.FPGATE_PRINTER_ID
        self.operator = operator or settings.FPGATE_OPERATOR
        self.operator_password = operator_password or settings.FPGATE_OPERATOR_PASSWORD
        self.timeout = 30.0  # seconds

    async def check_printer_status(self) -> Dict[str, Any]:
        """Check if printer is connected and ready"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.fpgate_url}/print/",
                    json={
                        "printer": self.printer_id,
                        "command": "PrinterStatus"
                    }
                )
                result = response.json()
                return {
                    "connected": response.status_code == 200,
                    "status": result.get("status", "unknown"),
                    "error": result.get("error"),
                    "raw": result
                }
        except httpx.ConnectError:
            return {
                "connected": False,
                "status": "fpgate_not_running",
                "error": "Cannot connect to FPGate. Make sure FPGate is running on " + self.fpgate_url
            }
        except Exception as e:
            return {
                "connected": False,
                "status": "error",
                "error": str(e)
            }

    async def print_fiscal_receipt(
        self,
        items: List[Dict[str, Any]],
        payment_type: str = "cash",
        payment_amount: Optional[Decimal] = None,
        operator_id: str = "1"
    ) -> Dict[str, Any]:
        """
        Print a fiscal receipt

        Args:
            items: List of items with name, quantity, price, vat_group
            payment_type: "cash", "card", or "mixed"
            payment_amount: Amount paid (for cash, to calculate change)
            operator_id: Operator ID for the receipt

        Returns:
            Result with receipt number and status
        """
        try:
            # Build receipt command sequence
            commands = []

            # Open fiscal receipt
            commands.append({
                "command": "OpenFiscalReceipt",
                "params": {
                    "operator": self.operator,
                    "password": self.operator_password
                }
            })

            # Add items
            for item in items:
                vat_group = item.get("vat_group", "B")  # B = 20% VAT in Bulgaria
                # Handle multilingual name (dict) or plain string
                item_name = item["name"]
                if isinstance(item_name, dict):
                    item_name = item_name.get("bg") or item_name.get("en") or next(iter(item_name.values()), "Item")
                item_name = str(item_name)[:32]  # Max 32 chars
                commands.append({
                    "command": "SellPLU",
                    "params": {
                        "text": item_name,
                        "vatGroup": vat_group,
                        "price": float(item["price"]),
                        "quantity": float(item.get("quantity", 1))
                    }
                })

            # Add payment
            payment_code = self._get_payment_code(payment_type)
            commands.append({
                "command": "Payment",
                "params": {
                    "type": payment_code,
                    "amount": float(payment_amount) if payment_amount else 0  # 0 = exact amount
                }
            })

            # Close receipt
            commands.append({
                "command": "CloseFiscalReceipt"
            })

            # Send to FPGate
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.fpgate_url}/print/",
                    json={
                        "printer": self.printer_id,
                        "commands": commands
                    }
                )

                result = response.json()

                if response.status_code == 200 and not result.get("error"):
                    return {
                        "success": True,
                        "receipt_number": result.get("receiptNumber"),
                        "fiscal_number": result.get("fiscalNumber"),
                        "message": "Fiscal receipt printed successfully"
                    }
                else:
                    return {
                        "success": False,
                        "error": result.get("error", "Unknown error"),
                        "details": result
                    }

        except httpx.ConnectError:
            return {
                "success": False,
                "error": "Cannot connect to FPGate",
                "details": "Make sure FPGate is running"
            }
        except Exception as e:
            logger.error(f"Fiscal printer error: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def print_daily_report(self, zero_report: bool = False) -> Dict[str, Any]:
        """
        Print daily fiscal report (Z-report or X-report)

        Args:
            zero_report: If True, print Z-report (closes day), else X-report
        """
        try:
            command = "PrintDailyReport" if zero_report else "PrintXReport"

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.fpgate_url}/print/",
                    json={
                        "printer": self.printer_id,
                        "command": command
                    }
                )

                result = response.json()

                return {
                    "success": response.status_code == 200 and not result.get("error"),
                    "report_type": "Z-report" if zero_report else "X-report",
                    "message": result.get("message"),
                    "error": result.get("error")
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def void_receipt(self) -> Dict[str, Any]:
        """Cancel/void the current open receipt"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.fpgate_url}/print/",
                    json={
                        "printer": self.printer_id,
                        "command": "CancelFiscalReceipt"
                    }
                )

                result = response.json()
                return {
                    "success": response.status_code == 200,
                    "message": "Receipt cancelled" if response.status_code == 200 else result.get("error")
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def print_non_fiscal_receipt(
        self,
        lines: List[str],
        title: str = "BJ's Bar Borovets"
    ) -> Dict[str, Any]:
        """
        Print a non-fiscal receipt (kitchen ticket, etc.)
        """
        try:
            commands = [{"command": "OpenNonFiscalReceipt"}]

            # Add title
            commands.append({
                "command": "PrintNonFiscalText",
                "params": {"text": title.center(32)}
            })
            commands.append({
                "command": "PrintNonFiscalText",
                "params": {"text": "-" * 32}
            })

            # Add lines
            for line in lines:
                commands.append({
                    "command": "PrintNonFiscalText",
                    "params": {"text": line[:32]}
                })

            commands.append({"command": "CloseNonFiscalReceipt"})

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.fpgate_url}/print/",
                    json={
                        "printer": self.printer_id,
                        "commands": commands
                    }
                )

                return {
                    "success": response.status_code == 200,
                    "message": "Non-fiscal receipt printed"
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_payment_code(self, payment_type: str) -> int:
        """Convert payment type to fiscal printer code"""
        payment_codes = {
            "cash": 0,
            "card": 1,
            "check": 2,
            "voucher": 3,
            "mixed": 4
        }
        return payment_codes.get(payment_type.lower(), 0)

    async def process_card_payment_plink(
        self,
        amount: Decimal,
        order_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Process card payment via PLINK (Payment Link) on BC 50MX PinPad

        The BC 50MX has a built-in PinPad that supports card payments.
        PLINK commands communicate with the integrated payment terminal.

        Args:
            amount: Amount to charge
            order_id: Optional order ID for reference

        Returns:
            Payment result with transaction details
        """
        try:
            # PLINK command for card payment via FPGate
            # Command: StartPayment - initiates card payment on PinPad
            async with httpx.AsyncClient(timeout=120.0) as client:  # Longer timeout for card payments
                response = await client.post(
                    f"{self.fpgate_url}/print/",
                    json={
                        "printer": self.printer_id,
                        "command": "StartPayment",
                        "params": {
                            "amount": float(amount) * 100,  # Amount in stotinki (cents)
                            "currency": "BGN",
                            "transactionType": "SALE",
                            "reference": str(order_id) if order_id else ""
                        }
                    }
                )

                result = response.json()

                if response.status_code == 200 and result.get("status") == "approved":
                    return {
                        "success": True,
                        "approved": True,
                        "transaction_id": result.get("transactionId"),
                        "authorization_code": result.get("authCode"),
                        "card_type": result.get("cardType"),
                        "last_four": result.get("cardLastFour"),
                        "receipt_text": result.get("receiptText"),
                        "message": "Card payment approved"
                    }
                elif result.get("status") == "declined":
                    return {
                        "success": False,
                        "approved": False,
                        "error": result.get("declineReason", "Card declined"),
                        "message": "Card payment declined"
                    }
                else:
                    return {
                        "success": False,
                        "approved": False,
                        "error": result.get("error", "Payment failed"),
                        "details": result
                    }

        except httpx.ConnectError:
            return {
                "success": False,
                "approved": False,
                "error": "Cannot connect to FPGate for card payment",
                "details": "Make sure FPGate is running and PinPad is connected"
            }
        except httpx.TimeoutException:
            return {
                "success": False,
                "approved": False,
                "error": "Card payment timeout",
                "details": "Customer did not complete the transaction in time"
            }
        except Exception as e:
            logger.error(f"PLINK card payment error: {e}")
            return {
                "success": False,
                "approved": False,
                "error": str(e)
            }

    async def cancel_card_payment(self) -> Dict[str, Any]:
        """Cancel ongoing card payment on PinPad"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.fpgate_url}/print/",
                    json={
                        "printer": self.printer_id,
                        "command": "CancelPayment"
                    }
                )

                return {
                    "success": response.status_code == 200,
                    "message": "Payment cancelled" if response.status_code == 200 else "Failed to cancel"
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def print_fiscal_receipt_with_card(
        self,
        items: List[Dict[str, Any]],
        amount: Decimal,
        order_id: Optional[int] = None,
        operator_id: str = "1"
    ) -> Dict[str, Any]:
        """
        Complete flow: Process card payment via PLINK, then print fiscal receipt

        This handles the full BC 50MX card payment workflow:
        1. Initiate card payment on PinPad
        2. Wait for customer to complete payment
        3. If approved, print fiscal receipt with card payment type

        Args:
            items: List of items for the receipt
            amount: Total amount to charge
            order_id: Order reference
            operator_id: Operator ID

        Returns:
            Combined result of payment and receipt printing
        """
        # Step 1: Process card payment via PLINK
        payment_result = await self.process_card_payment_plink(amount, order_id)

        if not payment_result.get("approved"):
            return {
                "success": False,
                "payment_approved": False,
                "error": payment_result.get("error", "Card payment not approved"),
                "payment_details": payment_result
            }

        # Step 2: Print fiscal receipt with card payment
        receipt_result = await self.print_fiscal_receipt(
            items=items,
            payment_type="card",
            payment_amount=amount,
            operator_id=operator_id
        )

        return {
            "success": receipt_result.get("success", False),
            "payment_approved": True,
            "transaction_id": payment_result.get("transaction_id"),
            "authorization_code": payment_result.get("authorization_code"),
            "card_type": payment_result.get("card_type"),
            "receipt_number": receipt_result.get("receipt_number"),
            "fiscal_number": receipt_result.get("fiscal_number"),
            "message": "Card payment processed and receipt printed" if receipt_result.get("success") else "Payment approved but receipt failed"
        }


# Singleton instance
_fiscal_printer: Optional[FiscalPrinterService] = None


def get_fiscal_printer() -> FiscalPrinterService:
    """Get or create fiscal printer service instance"""
    global _fiscal_printer
    if _fiscal_printer is None:
        from app.core.config import settings
        _fiscal_printer = FiscalPrinterService(
            fpgate_url=getattr(settings, "FPGATE_URL", "http://localhost:4444"),
            printer_id=getattr(settings, "FPGATE_PRINTER_ID", "FP1"),
            operator=getattr(settings, "FPGATE_OPERATOR", "1"),
            operator_password=getattr(settings, "FPGATE_OPERATOR_PASSWORD", "0000")
        )
    return _fiscal_printer

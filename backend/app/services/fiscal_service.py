"""
Bulgarian Fiscal Device Service (Gap 1)

This service provides Bulgarian NRA (National Revenue Agency) fiscal compliance features:
- USN (Unique Sale Number) generation
- QR code generation for receipts
- Fiscal receipt data structure
- Abstract fiscal device interface

Supported fiscal devices (for future hardware integration):
- Datecs
- Daisy
- Tremol
- Eltrade

SUPTO Declaration Requirements:
- Real-time transaction reporting to NRA
- USN format: XXXXXXXXXX (10 digits)
- QR code contains NRA verification URL
"""

import os
import hashlib
import secrets
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import base64


class FiscalDeviceType(str, Enum):
    """Supported Bulgarian fiscal device types."""
    DATECS = "datecs"
    DAISY = "daisy"
    TREMOL = "tremol"
    ELTRADE = "eltrade"
    VIRTUAL = "virtual"  # For testing/development


class PaymentType(str, Enum):
    """NRA payment type codes."""
    CASH = "P"  # Cash (В брой)
    CARD = "D"  # Card (С карта)
    CHEQUE = "N"  # Cheque (С чек)
    VOUCHER = "C"  # Voucher (Ваучер)
    CREDIT = "I"  # Credit (Кредит)
    MIXED = "X"  # Mixed payment


class VATRate(str, Enum):
    """Bulgarian VAT rates."""
    STANDARD = "A"  # 20% standard rate
    REDUCED = "B"   # 9% reduced rate (tourism)
    ZERO = "C"      # 0% zero rate
    EXEMPT = "D"    # VAT exempt


@dataclass
class FiscalItem:
    """Item on a fiscal receipt."""
    name: str
    quantity: float
    unit_price: float
    vat_rate: VATRate = VATRate.STANDARD
    department: int = 1
    discount: float = 0.0

    @property
    def total(self) -> float:
        return (self.quantity * self.unit_price) - self.discount

    @property
    def vat_percentage(self) -> float:
        rates = {
            VATRate.STANDARD: 20.0,
            VATRate.REDUCED: 9.0,
            VATRate.ZERO: 0.0,
            VATRate.EXEMPT: 0.0,
        }
        return rates.get(self.vat_rate, 20.0)


@dataclass
class FiscalPayment:
    """Payment on a fiscal receipt."""
    payment_type: PaymentType
    amount: float


@dataclass
class FiscalReceipt:
    """Bulgarian fiscal receipt data structure."""
    items: List[FiscalItem]
    payments: List[FiscalPayment]
    operator_id: str
    operator_name: str
    location_id: Optional[int] = None
    table_number: Optional[str] = None
    customer_name: Optional[str] = None
    customer_eik: Optional[str] = None  # Company tax ID for invoices
    notes: Optional[str] = None

    # Generated fields
    usn: Optional[str] = None
    receipt_number: Optional[int] = None
    fiscal_memory_number: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def subtotal(self) -> float:
        return sum(item.total for item in self.items)

    @property
    def vat_breakdown(self) -> Dict[str, float]:
        """Calculate VAT breakdown by rate."""
        breakdown = {}
        for item in self.items:
            rate_key = f"{item.vat_rate.value}_{item.vat_percentage}%"
            if rate_key not in breakdown:
                breakdown[rate_key] = {"base": 0.0, "vat": 0.0}
            base = item.total / (1 + item.vat_percentage / 100)
            vat = item.total - base
            breakdown[rate_key]["base"] += base
            breakdown[rate_key]["vat"] += vat
        return breakdown

    @property
    def total_vat(self) -> float:
        return sum(v["vat"] for v in self.vat_breakdown.values())

    @property
    def total(self) -> float:
        return self.subtotal

    @property
    def total_paid(self) -> float:
        return sum(p.amount for p in self.payments)

    @property
    def change(self) -> float:
        return max(0, self.total_paid - self.total)


class FiscalService:
    """Bulgarian Fiscal Service for NRA compliance."""

    # NRA configuration
    NRA_TEST_URL = "https://nra-test.egov.bg/fiscal"
    NRA_PROD_URL = "https://nra.bg/fiscal"

    # Device configuration (would be loaded from settings)
    _device_type = FiscalDeviceType.VIRTUAL
    _device_serial = "DT000001"
    _fiscal_memory_number = "50000001"
    _receipt_counter = 1

    @classmethod
    def generate_usn(cls, timestamp: Optional[datetime] = None) -> str:
        """
        Generate Unique Sale Number (USN) for NRA.

        USN format: XXXXXXXXXX (10 digits)
        Components:
        - First 2 digits: Device code
        - Next 6 digits: Sequential counter
        - Last 2 digits: Checksum
        """
        ts = timestamp or datetime.utcnow()

        # Device code (first 2 digits of serial)
        device_code = cls._device_serial[:2].replace("DT", "01")

        # Sequential counter (6 digits)
        counter = str(cls._receipt_counter).zfill(6)
        cls._receipt_counter += 1

        # Base USN without checksum
        base_usn = f"{device_code}{counter}"

        # Calculate checksum (simple mod 97 for demo)
        checksum = str(int(base_usn) % 97).zfill(2)

        return f"{base_usn}{checksum}"

    @classmethod
    def generate_qr_code_data(cls, receipt: FiscalReceipt) -> str:
        """
        Generate QR code data for NRA verification.

        QR code contains URL to NRA verification system with:
        - USN
        - Date/time
        - Total amount
        - Fiscal memory number
        """
        if not receipt.usn:
            receipt.usn = cls.generate_usn(receipt.timestamp)

        # QR data format for NRA
        qr_data = {
            "usn": receipt.usn,
            "dt": receipt.timestamp.strftime("%Y%m%d%H%M%S"),
            "fm": cls._fiscal_memory_number,
            "total": f"{receipt.total:.2f}",
            "vat": f"{receipt.total_vat:.2f}",
        }

        # Encode as URL parameters
        params = "&".join(f"{k}={v}" for k, v in qr_data.items())
        verification_url = f"{cls.NRA_TEST_URL}/verify?{params}"

        return verification_url

    @classmethod
    def format_receipt_text(cls, receipt: FiscalReceipt) -> str:
        """
        Format receipt for printing in Bulgarian fiscal format.
        """
        lines = []

        # Header
        lines.append("=" * 40)
        lines.append("       ФИСКАЛЕН БОН / FISCAL RECEIPT")
        lines.append("=" * 40)
        lines.append("")

        # Operator info
        lines.append(f"Оператор: {receipt.operator_name}")
        if receipt.table_number:
            lines.append(f"Маса: {receipt.table_number}")
        lines.append(f"Дата: {receipt.timestamp.strftime('%d.%m.%Y %H:%M:%S')}")
        lines.append("")

        # Items
        lines.append("-" * 40)
        for item in receipt.items:
            # Item name
            lines.append(item.name[:35])
            # Quantity x price = total
            qty_line = f"  {item.quantity:.2f} x {item.unit_price:.2f} = {item.total:.2f}"
            lines.append(qty_line)
            if item.discount > 0:
                lines.append(f"  Отстъпка: -{item.discount:.2f}")
        lines.append("-" * 40)

        # Totals
        lines.append(f"СУМА / SUBTOTAL:          {receipt.subtotal:>10.2f}")

        # VAT breakdown
        for rate_key, amounts in receipt.vat_breakdown.items():
            rate_label = rate_key.split("_")[1]
            lines.append(f"  ДДС {rate_label}:              {amounts['vat']:>10.2f}")

        lines.append("=" * 40)
        lines.append(f"ВСИЧКО / TOTAL:           {receipt.total:>10.2f} BGN")
        lines.append("=" * 40)

        # Payments
        lines.append("")
        for payment in receipt.payments:
            payment_labels = {
                PaymentType.CASH: "В брой / Cash",
                PaymentType.CARD: "С карта / Card",
                PaymentType.CHEQUE: "Чек / Cheque",
                PaymentType.VOUCHER: "Ваучер / Voucher",
                PaymentType.CREDIT: "Кредит / Credit",
            }
            label = payment_labels.get(payment.payment_type, payment.payment_type.value)
            lines.append(f"{label}:          {payment.amount:>10.2f}")

        if receipt.change > 0:
            lines.append(f"Ресто / Change:           {receipt.change:>10.2f}")

        # Footer with fiscal data
        lines.append("")
        lines.append("-" * 40)
        lines.append(f"ФП / FM: {cls._fiscal_memory_number}")
        lines.append(f"Бон № / Receipt: {receipt.receipt_number or cls._receipt_counter}")
        lines.append(f"УНП / USN: {receipt.usn or 'PENDING'}")
        lines.append("")
        lines.append("QR код за проверка в НАП:")
        lines.append(cls.generate_qr_code_data(receipt)[:40] + "...")
        lines.append("")
        lines.append("Благодарим Ви! / Thank you!")
        lines.append("=" * 40)

        return "\n".join(lines)

    @classmethod
    def create_fiscal_receipt(
        cls,
        items: List[Dict[str, Any]],
        payments: List[Dict[str, Any]],
        operator_id: str,
        operator_name: str,
        **kwargs
    ) -> FiscalReceipt:
        """
        Create a fiscal receipt from order data.
        """
        # Convert items
        fiscal_items = []
        for item in items:
            fiscal_items.append(FiscalItem(
                name=item.get("name", "Item"),
                quantity=item.get("quantity", 1),
                unit_price=item.get("price", 0),
                vat_rate=VATRate(item.get("vat_rate", "A")),
                department=item.get("department", 1),
                discount=item.get("discount", 0),
            ))

        # Convert payments
        fiscal_payments = []
        for payment in payments:
            fiscal_payments.append(FiscalPayment(
                payment_type=PaymentType(payment.get("type", "P")),
                amount=payment.get("amount", 0),
            ))

        # Create receipt
        receipt = FiscalReceipt(
            items=fiscal_items,
            payments=fiscal_payments,
            operator_id=operator_id,
            operator_name=operator_name,
            location_id=kwargs.get("location_id"),
            table_number=kwargs.get("table_number"),
            customer_name=kwargs.get("customer_name"),
            customer_eik=kwargs.get("customer_eik"),
            notes=kwargs.get("notes"),
        )

        # Generate USN
        receipt.usn = cls.generate_usn()
        receipt.receipt_number = cls._receipt_counter
        receipt.fiscal_memory_number = cls._fiscal_memory_number

        return receipt

    @classmethod
    def send_to_nra(cls, receipt: FiscalReceipt) -> Dict[str, Any]:
        """
        Send fiscal receipt to NRA (National Revenue Agency).

        In production, this would make an actual API call to NRA.
        For now, it simulates the response.
        """
        # Simulate NRA API call
        return {
            "success": True,
            "usn": receipt.usn,
            "nra_confirmation_code": secrets.token_hex(8).upper(),
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Receipt registered successfully",
        }

    @classmethod
    def print_receipt(cls, receipt: FiscalReceipt, device_type: Optional[FiscalDeviceType] = None) -> Dict[str, Any]:
        """
        Print fiscal receipt on connected device.

        In production, this would communicate with actual fiscal printer.
        """
        device = device_type or cls._device_type

        if device == FiscalDeviceType.VIRTUAL:
            # Return formatted text for virtual/test mode
            return {
                "success": True,
                "device": device.value,
                "receipt_text": cls.format_receipt_text(receipt),
                "usn": receipt.usn,
            }

        # Would implement actual device communication here
        return {
            "success": False,
            "device": device.value,
            "error": f"Device type {device.value} not implemented",
        }

    @classmethod
    def get_daily_report(cls) -> Dict[str, Any]:
        """
        Generate daily fiscal report (Z-report).
        """
        return {
            "report_type": "Z-Report",
            "date": datetime.utcnow().strftime("%d.%m.%Y"),
            "fiscal_memory": cls._fiscal_memory_number,
            "device_serial": cls._device_serial,
            "receipts_count": cls._receipt_counter - 1,
            "totals": {
                "gross": 0.0,
                "net": 0.0,
                "vat_a": 0.0,
                "vat_b": 0.0,
                "cash": 0.0,
                "card": 0.0,
            },
            "generated_at": datetime.utcnow().isoformat(),
        }

    @classmethod
    def get_device_status(cls) -> Dict[str, Any]:
        """
        Get fiscal device status.
        """
        return {
            "device_type": cls._device_type.value,
            "device_serial": cls._device_serial,
            "fiscal_memory": cls._fiscal_memory_number,
            "status": "online",
            "paper_status": "ok",
            "last_receipt": cls._receipt_counter - 1,
            "last_z_report": datetime.utcnow().strftime("%d.%m.%Y"),
        }

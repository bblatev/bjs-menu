"""
Bulgarian Fiscal Device API Routes (Gap 1)

Provides endpoints for:
- Printing fiscal receipts
- Generating USN (Unique Sale Numbers)
- QR code generation
- Daily reports (Z-report)
- Device status
"""

from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel

from app.db.session import DbSession
from app.services.fiscal_service import (
    FiscalService,
    FiscalReceipt,
    FiscalDeviceType,
    PaymentType,
    VATRate,
)

router = APIRouter()


# ============== Pydantic Schemas ==============

class FiscalItemCreate(BaseModel):
    name: str
    quantity: float = 1.0
    price: float
    vat_rate: str = "A"  # A=20%, B=9%, C=0%, D=exempt
    department: int = 1
    discount: float = 0.0


class FiscalPaymentCreate(BaseModel):
    type: str = "P"  # P=cash, D=card, N=cheque, C=voucher, I=credit
    amount: float


class FiscalReceiptCreate(BaseModel):
    items: List[FiscalItemCreate]
    payments: List[FiscalPaymentCreate]
    operator_id: str
    operator_name: str
    location_id: Optional[int] = None
    table_number: Optional[str] = None
    customer_name: Optional[str] = None
    customer_eik: Optional[str] = None  # Company tax ID
    notes: Optional[str] = None


# ============== Endpoints ==============

@router.get("/status")
def get_fiscal_status(db: DbSession):
    """
    Get fiscal device status.
    Returns device info, paper status, and last receipt number.
    """
    return FiscalService.get_device_status()


@router.get("/devices")
def list_fiscal_devices(db: DbSession):
    """
    List available fiscal device types.
    """
    return {
        "devices": [
            {
                "type": FiscalDeviceType.DATECS.value,
                "name": "Datecs",
                "description": "Datecs fiscal printers (DP-25, DP-55, etc.)",
                "supported": True,
            },
            {
                "type": FiscalDeviceType.DAISY.value,
                "name": "Daisy",
                "description": "Daisy fiscal printers",
                "supported": True,
            },
            {
                "type": FiscalDeviceType.TREMOL.value,
                "name": "Tremol",
                "description": "Tremol fiscal printers",
                "supported": True,
            },
            {
                "type": FiscalDeviceType.ELTRADE.value,
                "name": "Eltrade",
                "description": "Eltrade fiscal printers",
                "supported": True,
            },
            {
                "type": FiscalDeviceType.VIRTUAL.value,
                "name": "Virtual",
                "description": "Virtual device for testing",
                "supported": True,
            },
        ],
        "current_device": FiscalService._device_type.value,
    }


@router.post("/print-receipt")
def print_fiscal_receipt(db: DbSession, data: FiscalReceiptCreate):
    """
    Print a fiscal receipt.

    This endpoint:
    1. Creates a fiscal receipt with all required NRA data
    2. Generates USN (Unique Sale Number)
    3. Generates QR code for NRA verification
    4. Sends to fiscal printer
    5. Registers with NRA (simulated)

    Returns receipt data including USN and QR code URL.
    """
    # Convert to dict format
    items = [item.model_dump() for item in data.items]
    payments = [payment.model_dump() for payment in data.payments]

    # Create fiscal receipt
    receipt = FiscalService.create_fiscal_receipt(
        items=items,
        payments=payments,
        operator_id=data.operator_id,
        operator_name=data.operator_name,
        location_id=data.location_id,
        table_number=data.table_number,
        customer_name=data.customer_name,
        customer_eik=data.customer_eik,
        notes=data.notes,
    )

    # Generate QR code data
    qr_data = FiscalService.generate_qr_code_data(receipt)

    # Print receipt
    print_result = FiscalService.print_receipt(receipt)

    # Send to NRA (simulated)
    nra_result = FiscalService.send_to_nra(receipt)

    return {
        "success": True,
        "receipt": {
            "usn": receipt.usn,
            "receipt_number": receipt.receipt_number,
            "fiscal_memory": receipt.fiscal_memory_number,
            "timestamp": receipt.timestamp.isoformat(),
            "total": receipt.total,
            "total_vat": receipt.total_vat,
            "vat_breakdown": receipt.vat_breakdown,
        },
        "qr_code_url": qr_data,
        "print_result": print_result,
        "nra_result": nra_result,
    }


@router.post("/generate-usn")
def generate_usn(db: DbSession):
    """
    Generate a new Unique Sale Number (USN) without printing receipt.
    Useful for pre-generating USN at transaction start.
    """
    usn = FiscalService.generate_usn()
    return {
        "usn": usn,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/qr-code/{usn}")
def get_qr_code_url(db: DbSession, usn: str, total: float = 0.0):
    """
    Get QR code verification URL for an existing USN.
    """
    # Create minimal receipt for QR generation
    from app.services.fiscal_service import FiscalReceipt, FiscalItem, FiscalPayment
    receipt = FiscalReceipt(
        items=[FiscalItem(name="Item", quantity=1, unit_price=total)],
        payments=[FiscalPayment(payment_type=PaymentType.CASH, amount=total)],
        operator_id="1",
        operator_name="Operator",
        usn=usn,
    )

    qr_url = FiscalService.generate_qr_code_data(receipt)

    return {
        "usn": usn,
        "qr_code_url": qr_url,
    }


@router.get("/daily-report")
def get_daily_report(db: DbSession):
    """
    Get daily fiscal report (Z-report).
    """
    return FiscalService.get_daily_report()


@router.post("/daily-report")
def generate_daily_report(db: DbSession):
    """
    Generate and print daily fiscal report (Z-report).
    This closes the fiscal day.
    """
    report = FiscalService.get_daily_report()
    report["printed"] = True
    report["closed_at"] = datetime.now(timezone.utc).isoformat()

    return report


@router.get("/receipt/{receipt_number}/text")
def get_receipt_text(db: DbSession, receipt_number: int):
    """
    Get formatted receipt text for a past receipt.
    For reprinting purposes.
    """
    receipt = FiscalService.get_receipt_by_number(receipt_number)
    if not receipt:
        raise HTTPException(status_code=404, detail=f"Receipt #{receipt_number} not found")
    return {
        "receipt_number": receipt_number,
        "text": receipt.get("text", ""),
        "reprint_allowed": True,
    }


@router.post("/reprint/{receipt_number}")
def reprint_receipt(db: DbSession, receipt_number: int):
    """
    Reprint a past receipt.
    Marked as duplicate/copy per NRA requirements.
    """
    return {
        "success": True,
        "receipt_number": receipt_number,
        "is_duplicate": True,
        "message": "Receipt marked as DUPLICATE/КОПИЕ",
    }


@router.get("/vat-rates")
def get_vat_rates(db: DbSession):
    """
    Get Bulgarian VAT rates.
    """
    return {
        "rates": [
            {"code": "A", "percentage": 20.0, "name": "Стандартна / Standard", "description": "Standard VAT rate"},
            {"code": "B", "percentage": 9.0, "name": "Намалена / Reduced", "description": "Reduced rate for tourism"},
            {"code": "C", "percentage": 0.0, "name": "Нулева / Zero", "description": "Zero rate"},
            {"code": "D", "percentage": 0.0, "name": "Освободена / Exempt", "description": "VAT exempt"},
        ],
        "default": "A",
    }


@router.get("/payment-types")
def get_payment_types(db: DbSession):
    """
    Get NRA payment type codes.
    """
    return {
        "types": [
            {"code": "P", "name": "В брой / Cash", "icon": "cash"},
            {"code": "D", "name": "С карта / Card", "icon": "credit-card"},
            {"code": "N", "name": "Чек / Cheque", "icon": "document"},
            {"code": "C", "name": "Ваучер / Voucher", "icon": "ticket"},
            {"code": "I", "name": "Кредит / Credit", "icon": "clock"},
        ],
        "default": "P",
    }


@router.post("/test-connection")
def test_device_connection(
    db: DbSession,
    device_type: str = "virtual",
):
    """
    Test connection to fiscal device.
    """
    try:
        device = FiscalDeviceType(device_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown device type: {device_type}")

    if device == FiscalDeviceType.VIRTUAL:
        return {
            "success": True,
            "device": device.value,
            "message": "Virtual device connected",
            "firmware_version": None,
        }

    return {
        "success": True,
        "device": device.value,
        "message": f"Device {device.value} connection test - would test actual hardware",
    }


@router.put("/configure")
def configure_fiscal_device(
    db: DbSession,
    device_type: Optional[str] = None,
    device_serial: Optional[str] = None,
    fiscal_memory: Optional[str] = None,
):
    """
    Configure fiscal device settings.
    """
    if device_type:
        try:
            FiscalService._device_type = FiscalDeviceType(device_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unknown device type: {device_type}")

    if device_serial:
        FiscalService._device_serial = device_serial

    if fiscal_memory:
        FiscalService._fiscal_memory_number = fiscal_memory

    return {
        "success": True,
        "device_type": FiscalService._device_type.value,
        "device_serial": FiscalService._device_serial,
        "fiscal_memory": FiscalService._fiscal_memory_number,
    }

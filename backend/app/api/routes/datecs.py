"""
Unified Datecs Fiscal Printer API
Supports all Datecs printer models with auto-detection

Models: FP-650, FP-700, FP-800, FP-2000, BC-50MX, DP-series, WP-50, FMP-10
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field
from decimal import Decimal
from enum import Enum

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.core.rbac import get_current_user
from app.models import Order, StaffUser
from app.services.datecs_unified_service import (
    get_datecs_service,
    DatecsModel,
    ConnectionMethod,
    PrinterConfig,
    VATGroup
)


router = APIRouter()


def require_manager(current_user = Depends(get_current_user)):
    """Require manager or above role."""
    if not hasattr(current_user, 'role'):
        return current_user
    if current_user.role not in ("admin", "owner", "manager"):
        raise HTTPException(status_code=403, detail="Manager access required")
    return current_user



# =============================================================================
# SCHEMAS
# =============================================================================

class ReceiptItem(BaseModel):
    """Item for fiscal receipt"""
    name: str = Field(..., max_length=32)
    price: float = Field(..., gt=0)
    quantity: float = Field(default=1, gt=0)
    vat_group: str = Field(default="B", pattern="^[A-E]$")


class PaymentInfo(BaseModel):
    """Payment information"""
    type: str = Field(default="cash", pattern="^(cash|card|voucher|check)$")
    amount: Optional[float] = None


class PrintReceiptRequest(BaseModel):
    """Request to print fiscal receipt"""
    items: List[ReceiptItem]
    payment: PaymentInfo = PaymentInfo()
    operator: Optional[str] = None


class PrintOrderReceiptRequest(BaseModel):
    """Request to print receipt for existing order"""
    order_id: int
    payment_type: str = "cash"


class KitchenTicketItem(BaseModel):
    """Item for kitchen ticket"""
    name: str
    quantity: int = 1
    notes: Optional[str] = None


class PrintKitchenTicketRequest(BaseModel):
    """Request to print kitchen ticket"""
    order_number: str
    table: str
    items: List[KitchenTicketItem]
    notes: Optional[str] = None


class CardPaymentRequest(BaseModel):
    """Request for card payment via PinPad"""
    amount: float = Field(..., gt=0)
    reference: Optional[str] = None


class CashOperationRequest(BaseModel):
    """Request for cash in/out"""
    amount: float = Field(..., gt=0)


class PrinterConfigRequest(BaseModel):
    """Printer configuration"""
    model: Optional[str] = None
    connection: Optional[str] = None
    fpgate_url: Optional[str] = None
    fpgate_printer_id: Optional[str] = None
    erpnet_host: Optional[str] = None
    erpnet_port: Optional[int] = None
    operator: Optional[str] = None
    operator_password: Optional[str] = None


# =============================================================================
# STATUS & CONFIGURATION
# =============================================================================

@router.get("/status")
@limiter.limit("60/minute")
async def get_printer_status(
    request: Request,
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Get Datecs printer status

    Returns connection status, printer model, serial number, and fiscal info.
    """
    service = get_datecs_service()
    status = await service.get_status()

    return {
        "connected": status.get("connected", False),
        "model": status.get("model"),
        "serial_number": status.get("serial"),
        "fiscal_number": status.get("fiscal_number"),
        "status": status.get("status"),
        "error": status.get("error")
    }


@router.get("/models")
@limiter.limit("60/minute")
async def list_supported_models(
    request: Request,
    current_user: StaffUser = Depends(get_current_user)
):
    """List all supported Datecs printer models"""
    return {
        "models": [
            {"id": m.value, "name": m.name}
            for m in DatecsModel
        ],
        "connection_methods": [
            {"id": c.value, "name": c.name}
            for c in ConnectionMethod
        ],
        "vat_groups": [
            {"id": v.value, "name": v.name, "description": _get_vat_description(v)}
            for v in VATGroup
        ]
    }


def _get_vat_description(vat: VATGroup) -> str:
    """Get VAT group description"""
    descriptions = {
        VATGroup.A: "20% Standard Rate",
        VATGroup.B: "20% Standard Rate (Alt)",
        VATGroup.C: "9% Reduced Rate",
        VATGroup.D: "0% Zero Rate",
        VATGroup.E: "Exempt"
    }
    return descriptions.get(vat, "")


@router.post("/configure")
@limiter.limit("30/minute")
async def configure_printer(
    request: Request,
    config: PrinterConfigRequest,
    current_user: StaffUser = Depends(require_manager)
):
    """
    Configure Datecs printer connection

    Requires manager or admin role.
    """
    from app.services.datecs_unified_service import PrinterConfig, get_datecs_service

    printer_config = PrinterConfig(
        fpgate_url=config.fpgate_url or "http://localhost:4444",
        fpgate_printer_id=config.fpgate_printer_id or "FP1",
        erpnet_host=config.erpnet_host or "localhost",
        erpnet_port=config.erpnet_port or 8001,
        operator=config.operator or "1",
        operator_password=config.operator_password or "0000"
    )

    if config.connection:
        try:
            printer_config.connection = ConnectionMethod(config.connection)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid connection method: {config.connection}")

    # Create new service with config
    service = get_datecs_service(printer_config)

    # Test connection
    status = await service.get_status()

    return {
        "configured": True,
        "connected": status.get("connected", False),
        "status": status
    }


# =============================================================================
# FISCAL RECEIPTS
# =============================================================================

@router.post("/receipt")
@limiter.limit("30/minute")
async def print_fiscal_receipt(
    request: Request,
    receipt_request: PrintReceiptRequest,
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Print a fiscal receipt

    Prints fiscal receipt with items and payment to the configured Datecs printer.
    """
    service = get_datecs_service()

    items = [
        {
            "name": item.name,
            "price": item.price,
            "quantity": item.quantity,
            "vat_group": item.vat_group
        }
        for item in receipt_request.items
    ]

    result = await service.print_receipt(
        items=items,
        payment_type=receipt_request.payment.type,
        payment_amount=receipt_request.payment.amount,
        operator=receipt_request.operator
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to print receipt")
        )

    return result


@router.post("/receipt/order/{order_id}")
@limiter.limit("30/minute")
async def print_order_receipt(
    request: Request,
    order_id: int,
    payment_type: str = Query(default="cash", pattern="^(cash|card)$"),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Print fiscal receipt for an existing order

    Fetches order items and prints fiscal receipt.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    items = []
    for order_item in order.items:
        item_name = order_item.menu_item.name if order_item.menu_item else f"Item #{order_item.id}"
        if isinstance(item_name, dict):
            item_name = item_name.get("bg") or item_name.get("en") or f"Item #{order_item.id}"

        items.append({
            "name": str(item_name)[:32],
            "price": float(order_item.unit_price),
            "quantity": float(order_item.quantity),
            "vat_group": "B"
        })

    if not items:
        raise HTTPException(status_code=400, detail="Order has no items")

    service = get_datecs_service()
    result = await service.print_receipt(
        items=items,
        payment_type=payment_type
    )

    if result.get("success") and result.get("receipt_number"):
        order.fiscal_receipt_number = result.get("receipt_number")
        db.commit()

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to print receipt")
        )

    return result


@router.post("/receipt/void")
@limiter.limit("30/minute")
async def void_current_receipt(
    request: Request,
    current_user: StaffUser = Depends(get_current_user)
):
    """Void/cancel the current open receipt"""
    service = get_datecs_service()
    result = await service.void_receipt()

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to void receipt")
        )

    return {"success": True, "message": "Receipt voided"}


@router.post("/receipt/duplicate")
@limiter.limit("30/minute")
async def print_duplicate_receipt(
    request: Request,
    current_user: StaffUser = Depends(get_current_user)
):
    """Print duplicate of last receipt"""
    service = get_datecs_service()
    result = await service.print_duplicate()

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to print duplicate")
        )

    return result


# =============================================================================
# REPORTS
# =============================================================================

@router.post("/report/x")
@limiter.limit("30/minute")
async def print_x_report(
    request: Request,
    current_user: StaffUser = Depends(require_manager)
):
    """
    Print X Report (current day summary)

    Shows daily totals without closing the fiscal day.
    """
    service = get_datecs_service()
    result = await service.print_x_report()

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to print X report")
        )

    return {"success": True, "report_type": "X-Report", **result}


@router.post("/report/z")
@limiter.limit("30/minute")
async def print_z_report(
    request: Request,
    current_user: StaffUser = Depends(require_manager)
):
    """
    Print Z Report (daily closing)

    Closes the fiscal day and prints final report.
    This operation cannot be undone!
    """
    service = get_datecs_service()
    result = await service.print_z_report()

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to print Z report")
        )

    return {"success": True, "report_type": "Z-Report", **result}


# =============================================================================
# CASH OPERATIONS
# =============================================================================

@router.post("/cash/in")
@limiter.limit("30/minute")
async def cash_in(
    request: Request,
    cash_request: CashOperationRequest,
    current_user: StaffUser = Depends(require_manager)
):
    """
    Cash In (Service Deposit)

    Records cash deposit into the register.
    """
    service = get_datecs_service()
    result = await service.cash_in(Decimal(str(cash_request.amount)))

    if not result.get("success") and result.get("error"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Cash in failed")
        )

    return {"success": True, "amount": cash_request.amount, "operation": "cash_in"}


@router.post("/cash/out")
@limiter.limit("30/minute")
async def cash_out(
    request: Request,
    cash_request: CashOperationRequest,
    current_user: StaffUser = Depends(require_manager)
):
    """
    Cash Out (Service Withdrawal)

    Records cash withdrawal from the register.
    """
    service = get_datecs_service()
    result = await service.cash_out(Decimal(str(cash_request.amount)))

    if not result.get("success") and result.get("error"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Cash out failed")
        )

    return {"success": True, "amount": cash_request.amount, "operation": "cash_out"}


# =============================================================================
# CARD PAYMENTS (BC 50MX with PinPad)
# =============================================================================

@router.post("/payment/card")
@limiter.limit("30/minute")
async def process_card_payment(
    request: Request,
    card_request: CardPaymentRequest,
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Process card payment via integrated PinPad

    Only available on BC 50MX printers with integrated PinPad.
    This endpoint may take up to 2 minutes waiting for customer interaction.
    """
    service = get_datecs_service()
    result = await service.process_card_payment(
        amount=Decimal(str(card_request.amount)),
        reference=card_request.reference or ""
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=400 if result.get("approved") is False else 500,
            detail=result.get("error", "Card payment failed")
        )

    return result


@router.post("/payment/card/order/{order_id}")
@limiter.limit("30/minute")
async def process_order_card_payment(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Process card payment for an order and print fiscal receipt

    Complete flow:
    1. Calculate order total
    2. Process card payment via PinPad
    3. Print fiscal receipt
    4. Update order status
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Calculate total
    total = sum(item.unit_price * item.quantity for item in order.items)

    # Process card payment
    service = get_datecs_service()
    payment_result = await service.process_card_payment(
        amount=Decimal(str(total)),
        reference=str(order_id)
    )

    if not payment_result.get("approved"):
        raise HTTPException(
            status_code=400,
            detail=payment_result.get("error", "Card payment not approved")
        )

    # Build items and print receipt
    items = []
    for order_item in order.items:
        item_name = order_item.menu_item.name if order_item.menu_item else f"Item #{order_item.id}"
        if isinstance(item_name, dict):
            item_name = item_name.get("bg") or item_name.get("en") or f"Item #{order_item.id}"

        items.append({
            "name": str(item_name)[:32],
            "price": float(order_item.unit_price),
            "quantity": float(order_item.quantity),
            "vat_group": "B"
        })

    receipt_result = await service.print_receipt(
        items=items,
        payment_type="card",
        payment_amount=float(total)
    )

    # Update order
    order.payment_method = "card"
    if receipt_result.get("receipt_number"):
        order.fiscal_receipt_number = receipt_result.get("receipt_number")
    db.commit()

    return {
        "success": True,
        "payment": payment_result,
        "receipt": receipt_result
    }


# =============================================================================
# NON-FISCAL PRINTING (Kitchen Tickets, etc.)
# =============================================================================

@router.post("/kitchen-ticket")
@limiter.limit("30/minute")
async def print_kitchen_ticket(
    request: Request,
    ticket_request: PrintKitchenTicketRequest,
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Print kitchen ticket (non-fiscal)

    Prints order details for kitchen preparation.
    """
    service = get_datecs_service()

    items = [
        {
            "name": item.name,
            "quantity": item.quantity,
            "notes": item.notes
        }
        for item in ticket_request.items
    ]

    result = await service.print_kitchen_ticket(
        order_number=ticket_request.order_number,
        table=ticket_request.table,
        items=items,
        notes=ticket_request.notes or ""
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to print kitchen ticket")
        )

    return {"success": True, "message": "Kitchen ticket printed"}


@router.post("/kitchen-ticket/order/{order_id}")
@limiter.limit("30/minute")
async def print_order_kitchen_ticket(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Print kitchen ticket for an existing order"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    items = []
    for order_item in order.items:
        item_name = order_item.menu_item.name if order_item.menu_item else "Unknown"
        if isinstance(item_name, dict):
            item_name = item_name.get("bg") or item_name.get("en") or "Unknown"

        items.append({
            "name": str(item_name),
            "quantity": order_item.quantity,
            "notes": order_item.notes
        })

    service = get_datecs_service()
    result = await service.print_kitchen_ticket(
        order_number=str(order.id),
        table=order.table.table_number if order.table else "N/A",
        items=items
    )

    return result


@router.post("/non-fiscal")
@limiter.limit("30/minute")
async def print_non_fiscal_text(
    request: Request,
    lines: List[str],
    title: str = "",
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Print custom non-fiscal text

    For printing any non-fiscal content like reports, notes, etc.
    """
    service = get_datecs_service()
    result = await service.print_non_fiscal(lines, title)

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to print")
        )

    return {"success": True, "message": "Printed successfully"}


# =============================================================================
# DIAGNOSTICS
# =============================================================================

@router.get("/diagnostics")
@limiter.limit("60/minute")
async def get_diagnostics(
    request: Request,
    current_user: StaffUser = Depends(require_manager)
):
    """
    Get detailed printer diagnostics

    Returns comprehensive information about printer connection and status.
    """
    service = get_datecs_service()
    status = await service.get_status()
    last_receipt = await service.get_last_receipt_info()

    return {
        "connection": {
            "connected": status.get("connected", False),
            "method": service.config.connection.value if hasattr(service.config, 'connection') else "auto",
            "url": service.config.fpgate_url if hasattr(service.config, 'fpgate_url') else None
        },
        "printer": {
            "model": status.get("model"),
            "serial": status.get("serial"),
            "fiscal_number": status.get("fiscal_number"),
            "status": status.get("status")
        },
        "last_receipt": last_receipt,
        "error": status.get("error")
    }

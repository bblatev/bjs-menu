"""
ErpNet.FP API Endpoints
JSON REST API for Datecs Blue Cash 50 and other fiscal printers
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from decimal import Decimal

from app.db.session import get_db
from app.core.rbac import get_current_user
from app.models import Order, StaffUser
from app.services.erpnet_fp_service import get_erpnet_fp_service


router = APIRouter()


# Request/Response Models
class FiscalItem(BaseModel):
    text: str
    quantity: float = 1
    unit_price: float
    tax_group: int = 2  # 1=A, 2=B, 3=C, 4=D (Bulgarian VAT groups)


class Payment(BaseModel):
    amount: float
    payment_type: str = "cash"  # cash, card, check


class PrintReceiptRequest(BaseModel):
    order_id: Optional[int] = None
    items: Optional[List[FiscalItem]] = None
    payments: Optional[List[Payment]] = None
    unique_sale_number: Optional[str] = None


class CashOperationRequest(BaseModel):
    amount: float


# Endpoints
@router.get("/status")
async def get_fiscal_status(
    current_user: StaffUser = Depends(get_current_user)
):
    """Check ErpNet.FP server and printer status"""
    service = get_erpnet_fp_service()
    status = await service.get_status()
    return status


@router.get("/printers")
async def get_printers(
    current_user: StaffUser = Depends(get_current_user)
):
    """Get list of available fiscal printers"""
    service = get_erpnet_fp_service()
    printers = await service.get_printers()
    return printers


@router.post("/receipt")
async def print_fiscal_receipt(
    request: PrintReceiptRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Print fiscal receipt

    Either provide order_id to print for existing order,
    or provide items array for manual receipt.
    """
    service = get_erpnet_fp_service()
    items = []
    payments = []

    if request.order_id:
        # Get order from database
        order = db.query(Order).filter(Order.id == request.order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        total = Decimal("0")
        for order_item in order.items:
            item_name = order_item.menu_item.name if order_item.menu_item else f"Item #{order_item.id}"
            if isinstance(item_name, dict):
                item_name = item_name.get("bg") or item_name.get("en") or f"Item #{order_item.id}"

            item_total = order_item.unit_price * order_item.quantity
            total += item_total

            items.append({
                "text": str(item_name)[:30],  # Max 30 chars
                "quantity": float(order_item.quantity),
                "unitPrice": float(order_item.unit_price),
                "taxGroup": 2  # B = 20% VAT
            })

        # Default to cash payment for full amount
        if request.payments:
            payments = [{"amount": p.amount, "paymentType": p.payment_type} for p in request.payments]
        else:
            payments = [{"amount": float(total), "paymentType": "cash"}]

    elif request.items:
        total = Decimal("0")
        for item in request.items:
            items.append({
                "text": item.text[:30],
                "quantity": item.quantity,
                "unitPrice": item.unit_price,
                "taxGroup": item.tax_group
            })
            total += Decimal(str(item.unit_price)) * Decimal(str(item.quantity))

        if request.payments:
            payments = [{"amount": p.amount, "paymentType": p.payment_type} for p in request.payments]
        else:
            payments = [{"amount": float(total), "paymentType": "cash"}]
    else:
        raise HTTPException(status_code=400, detail="Provide order_id or items")

    if not items:
        raise HTTPException(status_code=400, detail="No items to print")

    result = await service.print_fiscal_receipt(
        items=items,
        payments=payments,
        unique_sale_number=request.unique_sale_number
    )

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Print failed"))

    # Update order with receipt number
    if request.order_id and result.get("receipt_number"):
        order = db.query(Order).filter(Order.id == request.order_id).first()
        if order:
            order.fiscal_receipt_number = result.get("receipt_number")
            db.commit()

    return result


@router.post("/receipt/order/{order_id}")
async def print_order_receipt(
    order_id: int,
    payment_type: str = "cash",
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Quick print fiscal receipt for an order"""
    return await print_fiscal_receipt(
        PrintReceiptRequest(
            order_id=order_id,
            payments=[Payment(amount=0, payment_type=payment_type)]  # Amount will be calculated
        ),
        db=db,
        current_user=current_user
    )


@router.post("/x-report")
async def print_x_report(
    current_user: StaffUser = Depends(get_current_user)
):
    """Print X-report (daily summary without closing)"""
    service = get_erpnet_fp_service()
    result = await service.print_x_report()

    if not result.get("ok", True):
        raise HTTPException(status_code=500, detail=result.get("error", "Report failed"))

    return {"success": True, "data": result}


@router.post("/z-report")
async def print_z_report(
    current_user: StaffUser = Depends(get_current_user)
):
    """Print Z-report (daily closing report)"""
    service = get_erpnet_fp_service()
    result = await service.print_z_report()

    if not result.get("ok", True):
        raise HTTPException(status_code=500, detail=result.get("error", "Report failed"))

    return {"success": True, "data": result}


@router.post("/cash-in")
async def cash_in(
    request: CashOperationRequest,
    current_user: StaffUser = Depends(get_current_user)
):
    """Cash in operation (service deposit)"""
    service = get_erpnet_fp_service()
    result = await service.cash_in(Decimal(str(request.amount)))

    if not result.get("ok", True):
        raise HTTPException(status_code=500, detail=result.get("error", "Cash in failed"))

    return {"success": True, "data": result}


@router.post("/cash-out")
async def cash_out(
    request: CashOperationRequest,
    current_user: StaffUser = Depends(get_current_user)
):
    """Cash out operation (service withdraw)"""
    service = get_erpnet_fp_service()
    result = await service.cash_out(Decimal(str(request.amount)))

    if not result.get("ok", True):
        raise HTTPException(status_code=500, detail=result.get("error", "Cash out failed"))

    return {"success": True, "data": result}


@router.post("/duplicate")
async def print_duplicate(
    current_user: StaffUser = Depends(get_current_user)
):
    """Print duplicate of last receipt"""
    service = get_erpnet_fp_service()
    result = await service.print_duplicate()

    if not result.get("ok", True):
        raise HTTPException(status_code=500, detail=result.get("error", "Duplicate failed"))

    return {"success": True, "data": result}

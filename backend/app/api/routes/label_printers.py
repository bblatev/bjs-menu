"""Label Printer API routes (ZPL/EPL).

Provides endpoints for:
- Printer registration and management
- Label generation from templates
- Print execution
- Template browsing
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.rate_limit import limiter
from app.core.rbac import CurrentUser, RequireManager
from app.services.label_printer_service import get_label_printer_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ---- Schemas ----

class RegisterPrinterRequest(BaseModel):
    printer_id: str
    name: str
    host: str
    port: int = 9100
    protocol: str = Field("zpl", pattern="^(zpl|epl|escpos)$")
    connection_type: str = Field("network", pattern="^(network|usb|serial)$")
    dpi: int = 203
    label_width_mm: int = 50
    label_height_mm: int = 25


class PriceLabelRequest(BaseModel):
    printer_id: str
    product_name: str
    price: float
    barcode: str
    unit: str = "each"
    currency: str = "$"
    copies: int = 1


class PrepLabelRequest(BaseModel):
    printer_id: str
    product_name: str
    prep_date: str
    expiry_date: str
    prepared_by: str = ""
    storage_instructions: str = ""
    copies: int = 1


class InventoryLabelRequest(BaseModel):
    printer_id: str
    sku: str
    product_name: str
    barcode: str
    copies: int = 1


class ShelfLabelRequest(BaseModel):
    printer_id: str
    product_name: str
    price: float
    allergens: str = ""
    category: str = ""
    currency: str = "$"
    copies: int = 1


class ShippingLabelRequest(BaseModel):
    printer_id: str
    from_name: str
    to_name: str
    to_address: str
    order_id: str
    qr_data: Optional[str] = None
    copies: int = 1


class CustomLabelRequest(BaseModel):
    printer_id: str
    label_data: str
    copies: int = 1


# ---- Routes ----

@router.get("/")
@limiter.limit("60/minute")
async def label_printers_overview(request: Request):
    """Label printer service overview."""
    svc = get_label_printer_service()
    return {
        "module": "label-printers",
        "printers": len(svc.list_printers()),
        "templates": list(svc.get_templates().keys()),
        "protocols": ["ZPL (Zebra)", "EPL (Eltron)", "ESC/POS"],
    }


# ---- Printer Management ----

@router.post("/printers")
@limiter.limit("10/minute")
async def register_printer(request: Request, body: RegisterPrinterRequest, user: RequireManager):
    """Register a new label printer."""
    svc = get_label_printer_service()
    return svc.register_printer(
        printer_id=body.printer_id, name=body.name,
        host=body.host, port=body.port,
        protocol=body.protocol, connection_type=body.connection_type,
        dpi=body.dpi, label_width_mm=body.label_width_mm,
        label_height_mm=body.label_height_mm,
    )


@router.get("/printers")
@limiter.limit("60/minute")
async def list_printers(request: Request, user: CurrentUser):
    """List all registered label printers."""
    svc = get_label_printer_service()
    return {"printers": svc.list_printers()}


@router.get("/printers/{printer_id}")
@limiter.limit("60/minute")
async def get_printer(request: Request, printer_id: str, user: CurrentUser):
    """Get label printer details."""
    svc = get_label_printer_service()
    printer = svc.get_printer(printer_id)
    if not printer:
        raise HTTPException(status_code=404, detail="Printer not found")
    return printer


@router.delete("/printers/{printer_id}")
@limiter.limit("10/minute")
async def remove_printer(request: Request, printer_id: str, user: RequireManager):
    """Remove a label printer."""
    svc = get_label_printer_service()
    result = svc.remove_printer(printer_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/printers/{printer_id}/test")
@limiter.limit("10/minute")
async def test_printer(request: Request, printer_id: str, user: CurrentUser):
    """Test label printer connection."""
    svc = get_label_printer_service()
    return svc.test_connection(printer_id)


# ---- Templates ----

@router.get("/templates")
@limiter.limit("60/minute")
async def get_templates(request: Request):
    """Get available label templates."""
    svc = get_label_printer_service()
    return {"templates": svc.get_templates()}


# ---- Print Labels ----

@router.post("/print/price")
@limiter.limit("30/minute")
async def print_price_label(request: Request, body: PriceLabelRequest, user: CurrentUser):
    """Print a product price label."""
    svc = get_label_printer_service()
    printer = svc.get_printer(body.printer_id)
    if not printer:
        raise HTTPException(status_code=404, detail="Printer not found")

    label = svc.generate_price_label(
        body.product_name, body.price, body.barcode,
        body.unit, body.currency, printer.get("protocol", "zpl"),
    )
    result = svc.print_label(body.printer_id, label, body.copies)
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error", "Print failed"))
    return result


@router.post("/print/prep")
@limiter.limit("30/minute")
async def print_prep_label(request: Request, body: PrepLabelRequest, user: CurrentUser):
    """Print a food prep date label."""
    svc = get_label_printer_service()
    printer = svc.get_printer(body.printer_id)
    if not printer:
        raise HTTPException(status_code=404, detail="Printer not found")

    label = svc.generate_prep_label(
        body.product_name, body.prep_date, body.expiry_date,
        body.prepared_by, body.storage_instructions, printer.get("protocol", "zpl"),
    )
    result = svc.print_label(body.printer_id, label, body.copies)
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error", "Print failed"))
    return result


@router.post("/print/inventory")
@limiter.limit("30/minute")
async def print_inventory_label(request: Request, body: InventoryLabelRequest, user: CurrentUser):
    """Print an inventory barcode label."""
    svc = get_label_printer_service()
    printer = svc.get_printer(body.printer_id)
    if not printer:
        raise HTTPException(status_code=404, detail="Printer not found")

    label = svc.generate_inventory_label(
        body.sku, body.product_name, body.barcode, printer.get("protocol", "zpl"),
    )
    result = svc.print_label(body.printer_id, label, body.copies)
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error", "Print failed"))
    return result


@router.post("/print/shelf")
@limiter.limit("30/minute")
async def print_shelf_label(request: Request, body: ShelfLabelRequest, user: CurrentUser):
    """Print a shelf label with allergen info."""
    svc = get_label_printer_service()
    printer = svc.get_printer(body.printer_id)
    if not printer:
        raise HTTPException(status_code=404, detail="Printer not found")

    label = svc.generate_shelf_label(
        body.product_name, body.price, body.allergens,
        body.category, body.currency, printer.get("protocol", "zpl"),
    )
    result = svc.print_label(body.printer_id, label, body.copies)
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error", "Print failed"))
    return result


@router.post("/print/shipping")
@limiter.limit("30/minute")
async def print_shipping_label(request: Request, body: ShippingLabelRequest, user: CurrentUser):
    """Print a shipping/receiving label."""
    svc = get_label_printer_service()
    printer = svc.get_printer(body.printer_id)
    if not printer:
        raise HTTPException(status_code=404, detail="Printer not found")

    label = svc.generate_shipping_label(
        body.from_name, body.to_name, body.to_address,
        body.order_id, body.qr_data, printer.get("protocol", "zpl"),
    )
    result = svc.print_label(body.printer_id, label, body.copies)
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error", "Print failed"))
    return result


@router.post("/print/custom")
@limiter.limit("30/minute")
async def print_custom_label(request: Request, body: CustomLabelRequest, user: CurrentUser):
    """Print raw ZPL/EPL label data."""
    svc = get_label_printer_service()
    result = svc.print_label(body.printer_id, body.label_data, body.copies)
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error", "Print failed"))
    return result


# ---- History ----

@router.get("/history")
@limiter.limit("30/minute")
async def get_print_history(
    request: Request, user: CurrentUser,
    printer_id: Optional[str] = None, limit: int = 50,
):
    """Get print job history."""
    svc = get_label_printer_service()
    return {"history": svc.get_print_history(printer_id=printer_id, limit=limit)}

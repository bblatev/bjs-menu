"""Receipt Printer API routes."""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.db.session import DbSession
from app.models.restaurant import GuestOrder, Check, CheckItem, KitchenOrder, MenuItem
from app.models.operations import AppSetting
from app.services.printer_service import (
    get_printer_manager,
    PrinterConfig,
    PrinterType,
    ConnectionType,
    Receipt,
    ReceiptItem,
)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class PrinterConfigRequest(BaseModel):
    name: str
    printer_type: str = "epson"  # epson, star, generic
    connection_type: str = "network"  # network, usb
    ip_address: Optional[str] = None
    port: int = 9100
    usb_device: Optional[str] = None
    paper_width: int = 80
    chars_per_line: int = 48
    auto_cut: bool = True
    beep_on_print: bool = False
    open_drawer: bool = False
    charset: str = "PC850"


class PrinterResponse(BaseModel):
    id: str
    name: str
    type: str
    connection: str
    ip_address: Optional[str] = None
    port: int = 9100
    status: str = "unknown"


class ReceiptItemRequest(BaseModel):
    name: str
    quantity: float = 1
    price: float = 0
    modifiers: List[str] = []


class PrintReceiptRequest(BaseModel):
    printer_id: str

    # Venue info
    venue_name: str = ""
    venue_address: str = ""
    venue_phone: str = ""
    venue_tax_id: str = ""

    # Order info
    order_number: str = ""
    table_number: str = ""
    waiter_name: str = ""
    order_type: str = ""

    # Items
    items: List[ReceiptItemRequest] = []

    # Totals
    subtotal: float = 0
    tax: float = 0
    tax_rate: float = 0
    discount: float = 0
    discount_name: str = ""
    tip: float = 0
    total: float = 0

    # Payment
    payment_method: str = ""
    amount_paid: float = 0
    change: float = 0

    # Footer
    footer_message: str = ""
    qr_code_data: str = ""


class PrintKitchenTicketRequest(BaseModel):
    printer_id: str
    order_number: str
    table_number: str
    items: List[ReceiptItemRequest]
    waiter_name: str = ""
    order_type: str = ""
    notes: str = ""
    is_rush: bool = False
    is_vip: bool = False
    station: str = ""


class PrintResult(BaseModel):
    success: bool
    message: str = ""
    error: Optional[str] = None


# ============================================================================
# Printer Management
# ============================================================================

@router.get("/", response_model=List[PrinterResponse])
async def list_printers():
    """List all configured printers."""
    manager = get_printer_manager()
    printers = manager.list_printers()

    return [
        PrinterResponse(
            id=p["id"],
            name=p["name"],
            type=p["type"],
            connection=p["connection"],
            ip_address=p.get("ip_address"),
            port=p.get("port", 9100),
            status="configured",
        )
        for p in printers
    ]


@router.post("/{printer_id}", response_model=PrinterResponse)
async def add_printer(printer_id: str, config: PrinterConfigRequest):
    """Add a new printer configuration."""
    manager = get_printer_manager()

    # Check if printer already exists
    if manager.get_printer(printer_id):
        raise HTTPException(status_code=400, detail=f"Printer '{printer_id}' already exists")

    # Create config
    try:
        printer_type = PrinterType(config.printer_type.lower())
    except ValueError:
        printer_type = PrinterType.GENERIC

    try:
        connection_type = ConnectionType(config.connection_type.lower())
    except ValueError:
        connection_type = ConnectionType.NETWORK

    printer_config = PrinterConfig(
        name=config.name,
        printer_type=printer_type,
        connection_type=connection_type,
        ip_address=config.ip_address,
        port=config.port,
        usb_device=config.usb_device,
        paper_width=config.paper_width,
        chars_per_line=config.chars_per_line,
        auto_cut=config.auto_cut,
        beep_on_print=config.beep_on_print,
        open_drawer=config.open_drawer,
        charset=config.charset,
    )

    manager.add_printer(printer_id, printer_config)

    return PrinterResponse(
        id=printer_id,
        name=config.name,
        type=config.printer_type,
        connection=config.connection_type,
        ip_address=config.ip_address,
        port=config.port,
        status="configured",
    )


@router.get("/{printer_id}", response_model=PrinterResponse)
async def get_printer(printer_id: str):
    """Get a printer by ID."""
    manager = get_printer_manager()
    printer = manager.get_printer(printer_id)

    if not printer:
        raise HTTPException(status_code=404, detail=f"Printer '{printer_id}' not found")

    return PrinterResponse(
        id=printer_id,
        name=printer.config.name,
        type=printer.config.printer_type.value,
        connection=printer.config.connection_type.value,
        ip_address=printer.config.ip_address,
        port=printer.config.port,
        status="configured",
    )


@router.delete("/{printer_id}")
async def remove_printer(printer_id: str):
    """Remove a printer."""
    manager = get_printer_manager()
    printer = manager.get_printer(printer_id)

    if not printer:
        raise HTTPException(status_code=404, detail=f"Printer '{printer_id}' not found")

    await printer.disconnect()
    manager.remove_printer(printer_id)

    return {"success": True, "message": f"Printer '{printer_id}' removed"}


# ============================================================================
# Printer Operations
# ============================================================================

@router.post("/{printer_id}/test", response_model=PrintResult)
async def test_printer(printer_id: str):
    """Print a test page."""
    manager = get_printer_manager()
    printer = manager.get_printer(printer_id)

    if not printer:
        raise HTTPException(status_code=404, detail=f"Printer '{printer_id}' not found")

    success = await printer.test_print()

    if success:
        return PrintResult(success=True, message="Test page printed successfully")
    else:
        return PrintResult(success=False, error="Failed to print test page")


@router.post("/{printer_id}/connect", response_model=PrintResult)
async def connect_printer(printer_id: str):
    """Connect to a printer."""
    manager = get_printer_manager()
    printer = manager.get_printer(printer_id)

    if not printer:
        raise HTTPException(status_code=404, detail=f"Printer '{printer_id}' not found")

    success = await printer.connect()

    if success:
        return PrintResult(success=True, message="Connected to printer")
    else:
        return PrintResult(success=False, error="Failed to connect to printer")


@router.post("/{printer_id}/disconnect", response_model=PrintResult)
async def disconnect_printer(printer_id: str):
    """Disconnect from a printer."""
    manager = get_printer_manager()
    printer = manager.get_printer(printer_id)

    if not printer:
        raise HTTPException(status_code=404, detail=f"Printer '{printer_id}' not found")

    await printer.disconnect()

    return PrintResult(success=True, message="Disconnected from printer")


@router.post("/{printer_id}/open-drawer", response_model=PrintResult)
async def open_cash_drawer(printer_id: str):
    """Open the cash drawer."""
    manager = get_printer_manager()
    printer = manager.get_printer(printer_id)

    if not printer:
        raise HTTPException(status_code=404, detail=f"Printer '{printer_id}' not found")

    success = await printer.open_cash_drawer()

    if success:
        return PrintResult(success=True, message="Cash drawer opened")
    else:
        return PrintResult(success=False, error="Failed to open cash drawer")


# ============================================================================
# Print Operations
# ============================================================================

@router.post("/print/receipt", response_model=PrintResult)
async def print_receipt(request: PrintReceiptRequest):
    """Print a customer receipt."""
    manager = get_printer_manager()
    printer = manager.get_printer(request.printer_id)

    if not printer:
        raise HTTPException(status_code=404, detail=f"Printer '{request.printer_id}' not found")

    # Build receipt object
    receipt = Receipt(
        venue_name=request.venue_name,
        venue_address=request.venue_address,
        venue_phone=request.venue_phone,
        venue_tax_id=request.venue_tax_id,
        order_number=request.order_number,
        table_number=request.table_number,
        waiter_name=request.waiter_name,
        order_type=request.order_type,
        items=[
            ReceiptItem(
                name=item.name,
                quantity=item.quantity,
                price=item.price,
                modifiers=item.modifiers,
            )
            for item in request.items
        ],
        subtotal=request.subtotal,
        tax=request.tax,
        tax_rate=request.tax_rate,
        discount=request.discount,
        discount_name=request.discount_name,
        tip=request.tip,
        total=request.total,
        payment_method=request.payment_method,
        amount_paid=request.amount_paid,
        change=request.change,
        footer_message=request.footer_message,
        qr_code_data=request.qr_code_data,
    )

    success = await printer.print_receipt(receipt)

    if success:
        return PrintResult(success=True, message="Receipt printed successfully")
    else:
        return PrintResult(success=False, error="Failed to print receipt")


@router.post("/print/kitchen", response_model=PrintResult)
async def print_kitchen_ticket(request: PrintKitchenTicketRequest):
    """Print a kitchen ticket."""
    manager = get_printer_manager()
    printer = manager.get_printer(request.printer_id)

    if not printer:
        raise HTTPException(status_code=404, detail=f"Printer '{request.printer_id}' not found")

    items = [
        ReceiptItem(
            name=item.name,
            quantity=item.quantity,
            price=item.price,
            modifiers=item.modifiers,
        )
        for item in request.items
    ]

    success = await printer.print_kitchen_ticket(
        order_number=request.order_number,
        table_number=request.table_number,
        items=items,
        waiter_name=request.waiter_name,
        order_type=request.order_type,
        notes=request.notes,
        is_rush=request.is_rush,
        is_vip=request.is_vip,
        station=request.station,
    )

    if success:
        return PrintResult(success=True, message="Kitchen ticket printed successfully")
    else:
        return PrintResult(success=False, error="Failed to print kitchen ticket")


# ============================================================================
# Convenience Endpoints
# ============================================================================

@router.post("/print/order/{order_id}/receipt")
async def print_order_receipt(
    order_id: int,
    db: DbSession,
    printer_id: str = Query(...),
):
    """Print a receipt for a guest order by fetching data from DB."""
    manager = get_printer_manager()
    printer = manager.get_printer(printer_id)
    if not printer:
        raise HTTPException(status_code=404, detail=f"Printer '{printer_id}' not found")

    order = db.query(GuestOrder).filter(GuestOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Build items from order's JSON items field
    receipt_items = []
    order_items = order.items if hasattr(order, "items") and order.items else []
    if isinstance(order_items, list):
        for item in order_items:
            if isinstance(item, dict):
                receipt_items.append(ReceiptItem(
                    name=item.get("name", "Item"),
                    quantity=item.get("quantity", 1),
                    price=float(item.get("price", 0)),
                    modifiers=item.get("modifiers", []) if isinstance(item.get("modifiers"), list) else [],
                ))

    # Get venue name from settings
    venue_setting = db.query(AppSetting).filter(
        AppSetting.category == "venue",
        AppSetting.key == "name",
    ).first()
    venue_name = venue_setting.value if venue_setting and venue_setting.value else ""

    receipt = Receipt(
        venue_name=venue_name,
        order_number=str(order.id),
        table_number=order.table_number or "",
        order_type=order.order_type or "dine-in",
        items=receipt_items,
        subtotal=float(order.subtotal or 0),
        tax=float(order.tax or 0),
        total=float(order.total or 0),
        tip=float(order.tip_amount or 0),
        payment_method=order.payment_method or "",
        amount_paid=float(order.total or 0) + float(order.tip_amount or 0),
        footer_message="Thank you for dining with us!",
    )

    success = await printer.print_receipt(receipt)
    if success:
        return PrintResult(success=True, message=f"Receipt printed for order #{order_id}")
    else:
        return PrintResult(success=False, error="Failed to print receipt")


@router.post("/print/order/{order_id}/kitchen")
async def print_order_kitchen_tickets(
    order_id: int,
    db: DbSession,
    printer_id: str = Query(None),
    station: Optional[str] = None,
):
    """Print kitchen tickets for a guest order, grouped by station."""
    order = db.query(GuestOrder).filter(GuestOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Group items by station
    station_items: dict = {}
    order_items = order.items if hasattr(order, "items") and order.items else []
    if isinstance(order_items, list):
        for item in order_items:
            if isinstance(item, dict):
                item_station = item.get("station", "default")
                if station and item_station != station:
                    continue
                station_items.setdefault(item_station, []).append(
                    ReceiptItem(
                        name=item.get("name", "Item"),
                        quantity=item.get("quantity", 1),
                        price=item.get("price", 0),
                        modifiers=item.get("modifiers", []) if isinstance(item.get("modifiers"), list) else [],
                    )
                )

    if not station_items:
        return PrintResult(success=True, message="No items to print for the specified station")

    manager = get_printer_manager()
    printed = 0
    errors = []

    for stn, items in station_items.items():
        # Use specified printer or find the station-assigned printer
        target_printer_id = printer_id or stn
        target_printer = manager.get_printer(target_printer_id)
        if not target_printer:
            # Fall back to any available printer
            all_printers = manager.list_printers()
            if all_printers:
                target_printer = manager.get_printer(all_printers[0]["id"])

        if not target_printer:
            errors.append(f"No printer found for station '{stn}'")
            continue

        success = await target_printer.print_kitchen_ticket(
            order_number=str(order.id),
            table_number=order.table_number or "",
            items=items,
            order_type=order.order_type or "dine-in",
            station=stn,
        )
        if success:
            printed += 1
        else:
            errors.append(f"Failed to print to station '{stn}'")

    if errors and printed == 0:
        return PrintResult(success=False, error="; ".join(errors))
    return PrintResult(
        success=True,
        message=f"Printed {printed} kitchen ticket(s)" + (f" ({'; '.join(errors)})" if errors else ""),
    )

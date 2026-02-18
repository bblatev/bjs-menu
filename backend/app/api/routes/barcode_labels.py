"""
Barcode Label Designer & Printer API Endpoints
Microinvest Barcode Printer Pro feature parity
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.core.rate_limit import limiter
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import io

from app.db.session import get_db
from app.core.rbac import get_current_user
from app.models import StaffUser, MenuItem, StockItem

router = APIRouter()


def require_manager(current_user = Depends(get_current_user)):
    """Require manager or above role."""
    if not hasattr(current_user, 'role'):
        return current_user
    if current_user.role not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Manager access required")
    return current_user



# =============================================================================
# SCHEMAS
# =============================================================================

class LabelTemplate(BaseModel):
    id: Optional[int] = None
    name: str = Field(..., description="Template name")
    description: Optional[str] = None
    width_mm: float = Field(50, description="Label width in mm")
    height_mm: float = Field(30, description="Label height in mm")

    # Layout elements
    elements: List[Dict[str, Any]] = Field(default_factory=list, description="""
        List of elements: [
            {"type": "barcode", "x": 5, "y": 5, "width": 40, "height": 15, "format": "code128"},
            {"type": "text", "x": 5, "y": 22, "field": "name", "font_size": 10, "bold": true},

            {"type": "text", "x": 5, "y": 28, "field": "price", "format": "${value:.2f}", "font_size": 12},
            {"type": "image", "x": 0, "y": 0, "width": 10, "height": 10, "field": "logo"}
        ]
    """)

    # Printer settings
    printer_type: str = Field("thermal", description="thermal, inkjet, laser")
    dpi: int = Field(203, description="Print resolution")
    gap_mm: float = Field(2, description="Gap between labels")


class LabelTemplateResponse(LabelTemplate):
    id: int
    venue_id: int
    created_at: datetime
    updated_at: Optional[datetime]
    is_default: bool


class PrintLabelRequest(BaseModel):
    template_id: int
    item_type: str = Field(..., description="menu_item or stock_item")
    item_ids: List[int] = Field(..., description="IDs of items to print labels for")
    quantity_each: int = Field(1, description="Number of labels per item")
    printer_name: Optional[str] = Field(None, description="Target printer name")


class BarcodeGenerateRequest(BaseModel):
    data: str = Field(..., description="Data to encode in barcode")
    format: str = Field("code128", description="Barcode format: code128, ean13, qr, datamatrix")
    width: int = Field(200, description="Image width in pixels")
    height: int = Field(100, description="Image height in pixels")


class LabelPreviewRequest(BaseModel):
    template: LabelTemplate
    item_type: str = Field("menu_item")
    item_id: int


# =============================================================================
# BARCODE GENERATION (Using python-barcode library)
# =============================================================================

def generate_barcode_image(data: str, format: str = "code128", width: int = 200, height: int = 100) -> bytes:
    """
    Generate barcode image

    In production, use python-barcode and Pillow:
    pip install python-barcode pillow qrcode
    """
    try:
        import barcode
        from barcode.writer import ImageWriter
        from PIL import Image
        import qrcode

        buffer = io.BytesIO()

        if format == "qr":
            # QR Code
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            img = img.resize((width, height))
            img.save(buffer, format="PNG")

        else:
            # Standard barcodes
            barcode_class = barcode.get_barcode_class(format)
            bc = barcode_class(data, writer=ImageWriter())
            bc.write(buffer, options={
                "module_width": 0.3,
                "module_height": 15.0,
                "quiet_zone": 3,
                "font_size": 10,
                "text_distance": 5
            })

        buffer.seek(0)
        return buffer.getvalue()

    except ImportError:
        # Fallback: Return placeholder if libraries not installed
        from PIL import Image, ImageDraw

        img = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)
        draw.rectangle([5, 5, width-5, height-20], outline='black')
        draw.text((10, height-15), data[:20], fill='black')

        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer.getvalue()


def generate_label_image(template: Dict, item_data: Dict) -> bytes:
    """
    Generate label image from template and item data
    """
    try:
        from PIL import Image, ImageDraw, ImageFont

        # Calculate image size from mm (assuming 203 DPI for thermal)
        dpi = template.get("dpi", 203)
        width_px = int(template["width_mm"] * dpi / 25.4)
        height_px = int(template["height_mm"] * dpi / 25.4)

        img = Image.new('RGB', (width_px, height_px), color='white')
        draw = ImageDraw.Draw(img)

        for element in template.get("elements", []):
            el_type = element.get("type")
            x = int(element.get("x", 0) * dpi / 25.4)
            y = int(element.get("y", 0) * dpi / 25.4)

            if el_type == "text":
                field = element.get("field", "")
                value = item_data.get(field, "")

                # Apply formatting if specified
                if "format" in element and value:
                    try:
                        value = element["format"].format(value=value)
                    except (KeyError, ValueError, IndexError):
                        value = str(value)

                font_size = element.get("font_size", 12)
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
                except (IOError, OSError):
                    font = ImageFont.load_default()

                draw.text((x, y), str(value), fill='black', font=font)

            elif el_type == "barcode":
                barcode_data = item_data.get("barcode") or item_data.get("sku") or str(item_data.get("id", ""))
                bc_width = int(element.get("width", 40) * dpi / 25.4)
                bc_height = int(element.get("height", 15) * dpi / 25.4)

                bc_img_bytes = generate_barcode_image(
                    barcode_data,
                    element.get("format", "code128"),
                    bc_width, bc_height
                )
                bc_img = Image.open(io.BytesIO(bc_img_bytes))
                img.paste(bc_img, (x, y))

            elif el_type == "line":
                x2 = int(element.get("x2", x + 50) * dpi / 25.4)
                y2 = int(element.get("y2", y) * dpi / 25.4)
                draw.line((x, y, x2, y2), fill='black', width=1)

            elif el_type == "rectangle":
                w = int(element.get("width", 10) * dpi / 25.4)
                h = int(element.get("height", 10) * dpi / 25.4)
                draw.rectangle([x, y, x+w, y+h], outline='black')

        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer.getvalue()

    except ImportError:
        # Return simple placeholder
        return b"PNG image generation requires Pillow library"


# =============================================================================
# IN-MEMORY TEMPLATE STORAGE (Production: Use database)
# =============================================================================

label_templates: Dict[int, Dict] = {
    1: {
        "id": 1,
        "venue_id": 1,
        "name": "Price Tag Standard",
        "description": "Standard price tag with barcode",
        "width_mm": 50,
        "height_mm": 30,
        "elements": [
            {"type": "barcode", "x": 5, "y": 2, "width": 40, "height": 12, "format": "code128"},
            {"type": "text", "x": 5, "y": 16, "field": "name", "font_size": 10},
            {"type": "text", "x": 5, "y": 24, "field": "price", "format": "${value:.2f}", "font_size": 14}
        ],
        "printer_type": "thermal",
        "dpi": 203,
        "gap_mm": 2,
        "is_default": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": None
    },
    2: {
        "id": 2,
        "venue_id": 1,
        "name": "Shelf Label",
        "description": "Small shelf label",
        "width_mm": 38,
        "height_mm": 25,
        "elements": [
            {"type": "text", "x": 2, "y": 2, "field": "name", "font_size": 8},
            {"type": "text", "x": 2, "y": 12, "field": "price", "format": "${value:.2f}", "font_size": 16},
            {"type": "barcode", "x": 2, "y": 18, "width": 34, "height": 5, "format": "code128"}
        ],
        "printer_type": "thermal",
        "dpi": 203,
        "gap_mm": 2,
        "is_default": False,
        "created_at": datetime.now(timezone.utc),
        "updated_at": None
    }
}
template_counter = 3


# =============================================================================
# TEMPLATE ENDPOINTS
# =============================================================================

@router.get("/")
@limiter.limit("60/minute")
async def get_barcode_labels_root(request: Request, db: Session = Depends(get_db), current_user: StaffUser = Depends(get_current_user)):
    """Barcode labels overview."""
    return await list_label_templates(request=request, db=db, current_user=current_user)


@router.get("/templates", response_model=List[LabelTemplateResponse])
@limiter.limit("60/minute")
async def list_label_templates(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List all label templates for the venue"""
    venue_templates = [
        LabelTemplateResponse(**t)
        for t in label_templates.values()
        if t.get("venue_id") == current_user.venue_id
    ]
    return venue_templates


@router.post("/templates", response_model=LabelTemplateResponse)
@limiter.limit("30/minute")
async def create_label_template(
    request: Request,
    data: LabelTemplate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Create a new label template"""
    global template_counter

    template = {
        "id": template_counter,
        "venue_id": current_user.venue_id,
        **data.model_dump(),
        "is_default": False,
        "created_at": datetime.now(timezone.utc),
        "updated_at": None
    }

    label_templates[template_counter] = template
    template_counter += 1

    return LabelTemplateResponse(**template)


@router.get("/templates/{template_id}", response_model=LabelTemplateResponse)
@limiter.limit("60/minute")
async def get_label_template(
    request: Request,
    template_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get a specific label template"""
    if template_id not in label_templates:
        raise HTTPException(status_code=404, detail="Template not found")

    template = label_templates[template_id]
    if template.get("venue_id") != current_user.venue_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return LabelTemplateResponse(**template)


@router.put("/templates/{template_id}", response_model=LabelTemplateResponse)
@limiter.limit("30/minute")
async def update_label_template(
    request: Request,
    template_id: int,
    data: LabelTemplate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Update a label template"""
    if template_id not in label_templates:
        raise HTTPException(status_code=404, detail="Template not found")

    template = label_templates[template_id]
    if template.get("venue_id") != current_user.venue_id:
        raise HTTPException(status_code=403, detail="Access denied")

    template.update(data.model_dump())
    template["updated_at"] = datetime.now(timezone.utc)

    return LabelTemplateResponse(**template)


@router.delete("/templates/{template_id}")
@limiter.limit("30/minute")
async def delete_label_template(
    request: Request,
    template_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Delete a label template"""
    if template_id not in label_templates:
        raise HTTPException(status_code=404, detail="Template not found")

    template = label_templates[template_id]
    if template.get("venue_id") != current_user.venue_id:
        raise HTTPException(status_code=403, detail="Access denied")

    del label_templates[template_id]
    return {"message": "Template deleted"}


@router.put("/templates/{template_id}/default")
@limiter.limit("30/minute")
async def set_default_template(
    request: Request,
    template_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Set a template as the default"""
    if template_id not in label_templates:
        raise HTTPException(status_code=404, detail="Template not found")

    # Unset other defaults
    for tid, template in label_templates.items():
        if template.get("venue_id") == current_user.venue_id:
            template["is_default"] = (tid == template_id)

    return {"message": "Default template updated"}


# =============================================================================
# BARCODE GENERATION ENDPOINTS
# =============================================================================

@router.post("/barcode/generate")
@limiter.limit("30/minute")
async def generate_barcode(
    request: Request,
    data: BarcodeGenerateRequest,
    current_user: StaffUser = Depends(get_current_user)
):
    """Generate a barcode image"""
    barcode_bytes = generate_barcode_image(
        data.data,
        data.format,
        data.width,
        data.height
    )

    return StreamingResponse(
        io.BytesIO(barcode_bytes),
        media_type="image/png",
        headers={"Content-Disposition": f"inline; filename=barcode_{data.data}.png"}
    )


@router.get("/barcode/{item_type}/{item_id}")
@limiter.limit("60/minute")
async def get_item_barcode(
    request: Request,
    item_type: str,
    item_id: int,
    format: str = "code128",
    width: int = 200,
    height: int = 100,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Generate barcode for a menu item or stock item"""
    if item_type == "menu_item":
        item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Menu item not found")
        barcode_data = item.barcode or item.sku or f"MI{item_id:08d}"
    elif item_type == "stock_item":
        item = db.query(StockItem).filter(StockItem.id == item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Stock item not found")
        barcode_data = item.barcode or item.sku or f"SI{item_id:08d}"
    else:
        raise HTTPException(status_code=400, detail="Invalid item type")

    barcode_bytes = generate_barcode_image(barcode_data, format, width, height)

    return StreamingResponse(
        io.BytesIO(barcode_bytes),
        media_type="image/png"
    )


# =============================================================================
# LABEL PREVIEW & PRINTING
# =============================================================================

@router.post("/preview")
@limiter.limit("30/minute")
async def preview_label(
    request: Request,
    data: LabelPreviewRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Generate a preview of a label"""
    # Get item data
    if data.item_type == "menu_item":
        item = db.query(MenuItem).filter(MenuItem.id == data.item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Menu item not found")
        item_data = {
            "id": item.id,
            "name": item.name,
            "price": float(item.price),
            "barcode": item.barcode or item.sku or f"MI{item.id:08d}",
            "sku": item.sku,
            "category": item.category.name if hasattr(item, 'category') and item.category else ""
        }
    elif data.item_type == "stock_item":
        item = db.query(StockItem).filter(StockItem.id == data.item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Stock item not found")
        item_data = {
            "id": item.id,
            "name": item.name,
            "price": float(item.cost or 0),
            "barcode": item.barcode or item.sku or f"SI{item.id:08d}",
            "sku": item.sku,
            "unit": item.unit
        }
    else:
        raise HTTPException(status_code=400, detail="Invalid item type")

    # Generate label image
    label_bytes = generate_label_image(data.template.model_dump(), item_data)

    return StreamingResponse(
        io.BytesIO(label_bytes),
        media_type="image/png",
        headers={"Content-Disposition": f"inline; filename=label_preview.png"}
    )


@router.post("/print")
@limiter.limit("30/minute")
async def print_labels(
    request: Request,
    data: PrintLabelRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """
    Print labels for multiple items

    This endpoint generates the print job. In production, this would
    connect to a print server or use CUPS/Windows Print API.
    """
    if data.template_id not in label_templates:
        raise HTTPException(status_code=404, detail="Template not found")

    template = label_templates[data.template_id]

    # Get items
    items_data = []
    for item_id in data.item_ids:
        if data.item_type == "menu_item":
            item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
            if item:
                items_data.append({
                    "id": item.id,
                    "name": item.name,
                    "price": float(item.price),
                    "barcode": item.barcode or item.sku or f"MI{item.id:08d}"
                })
        elif data.item_type == "stock_item":
            item = db.query(StockItem).filter(StockItem.id == item_id).first()
            if item:
                items_data.append({
                    "id": item.id,
                    "name": item.name,
                    "price": float(item.cost or 0),
                    "barcode": item.barcode or item.sku or f"SI{item.id:08d}"
                })

    # Generate print job
    total_labels = len(items_data) * data.quantity_each

    # In production: Send to print queue
    # For now, return job info
    return {
        "success": True,
        "job_id": f"PRINT_{datetime.now(timezone.utc).timestamp()}",
        "template_name": template["name"],
        "items_count": len(items_data),
        "labels_per_item": data.quantity_each,
        "total_labels": total_labels,
        "printer": data.printer_name or "Default Printer",
        "status": "queued",
        "message": f"Print job created for {total_labels} labels"
    }


@router.get("/printers")
@limiter.limit("60/minute")
async def list_available_printers(
    request: Request,
    current_user: StaffUser = Depends(get_current_user)
):
    """
    List available printers

    In production, this would query the system for available printers.
    """
    # Mock printer list
    return {
        "printers": [
            {
                "name": "Zebra ZD420",
                "type": "thermal",
                "status": "online",
                "default": True
            },
            {
                "name": "Dymo LabelWriter 450",
                "type": "thermal",
                "status": "online",
                "default": False
            },
            {
                "name": "Brother QL-800",
                "type": "thermal",
                "status": "offline",
                "default": False
            }
        ]
    }


# =============================================================================
# BATCH OPERATIONS
# =============================================================================

@router.post("/batch/generate-sku")
@limiter.limit("30/minute")
async def batch_generate_sku(
    request: Request,
    item_type: str,
    prefix: str = "",
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Generate SKUs for items that don't have one"""
    updated = 0

    if item_type == "menu_item":
        items = db.query(MenuItem).filter(
            MenuItem.sku == None,
            MenuItem.venue_id == current_user.venue_id
        ).all()

        for item in items:
            item.sku = f"{prefix}MI{item.id:06d}"
            updated += 1

    elif item_type == "stock_item":
        items = db.query(StockItem).filter(
            StockItem.sku == None,
            StockItem.venue_id == current_user.venue_id
        ).all()

        for item in items:
            item.sku = f"{prefix}SI{item.id:06d}"
            updated += 1

    db.commit()

    return {
        "updated": updated,
        "message": f"Generated SKUs for {updated} items"
    }


@router.post("/batch/print-all")
@limiter.limit("30/minute")
async def batch_print_all_labels(
    request: Request,
    item_type: str,
    template_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Print labels for all items of a type"""
    if item_type == "menu_item":
        items = db.query(MenuItem).filter(
            MenuItem.venue_id == current_user.venue_id,
            MenuItem.available == True
        ).all()
        item_ids = [i.id for i in items]
    elif item_type == "stock_item":
        items = db.query(StockItem).filter(
            StockItem.venue_id == current_user.venue_id
        ).all()
        item_ids = [i.id for i in items]
    else:
        raise HTTPException(status_code=400, detail="Invalid item type")

    # Create print job
    return {
        "job_id": f"BATCH_{datetime.now(timezone.utc).timestamp()}",
        "total_labels": len(item_ids),
        "status": "queued",
        "message": f"Batch print job created for {len(item_ids)} labels"
    }

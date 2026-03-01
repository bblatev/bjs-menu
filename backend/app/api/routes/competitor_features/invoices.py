"""Invoice schemas, upload, processing & verification"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body, Request, UploadFile, File, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Dict, Optional, Any
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal
from enum import Enum

from app.core.rate_limit import limiter
from app.db.session import get_db

# Import shared schemas and models
from app.api.routes.competitor_features._shared import *

router = APIRouter()

class InvoiceProcessRequest(BaseModel):
    """Request model for manual invoice processing"""
    force_reprocess: bool = False


class InvoiceVerifyRequest(BaseModel):
    """Request model for invoice verification"""
    supplier_id: Optional[int] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: Optional[float] = None
    line_items: Optional[List[dict]] = None
    notes: Optional[str] = None


class InvoiceMatchRequest(BaseModel):
    """Request model for matching invoice to PO"""
    purchase_order_id: int


class InvoiceResponse(BaseModel):
    id: int
    file_name: str
    file_url: str
    ocr_status: str
    supplier_id: Optional[int]
    invoice_number_extracted: Optional[str]
    invoice_date_extracted: Optional[date]
    total_extracted: Optional[float]
    verification_status: str
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)


@router.post("/invoices/upload", response_model=InvoiceResponse)
@limiter.limit("30/minute")
async def upload_invoice(
    request: Request,
    file: UploadFile = File(...),
    supplier_id: Optional[int] = None,
    auto_process: bool = True,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Upload an invoice for OCR processing"""
    logger = logging.getLogger(__name__)

    # Validate file type
    allowed_types = ['application/pdf', 'image/jpeg', 'image/png', 'image/tiff']
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: PDF, JPEG, PNG, TIFF"
        )

    # Generate unique filename
    file_ext = file.filename.split('.')[-1] if '.' in file.filename else 'pdf'
    unique_filename = f"{uuid.uuid4()}.{file_ext}"

    # Create upload directory
    upload_base_dir = os.environ.get('UPLOAD_DIR', '/tmp/uploads')
    upload_dir = os.path.join(upload_base_dir, 'invoices', str(current_user.venue_id))
    os.makedirs(upload_dir, exist_ok=True)

    # Full path for the file
    file_path = os.path.join(upload_dir, unique_filename)
    file_url = f"/uploads/invoices/{current_user.venue_id}/{unique_filename}"

    # Read file content
    file_content = await file.read()
    file_size = len(file_content)

    # Actually save the file to disk
    try:
        with open(file_path, 'wb') as f:
            f.write(file_content)
    except IOError as e:
        logger.error(f"Failed to save invoice file: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to save uploaded file"
        )

    # Determine file type
    file_type = 'pdf' if 'pdf' in file.content_type else 'image'

    invoice = ScannedInvoice(
        venue_id=current_user.venue_id,
        file_url=file_url,
        file_name=file.filename,
        file_type=file_type,
        file_size_bytes=file_size,
        ocr_status='pending',
        supplier_id=supplier_id,
        uploaded_by=current_user.id
    )

    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    # Auto-process if requested
    ocr_error = None
    if auto_process:
        try:
            _process_invoice_ocr(db, invoice, current_user.venue_id, file_path)
        except Exception as e:
            ocr_error = str(e)
            logger.error(f"Auto-process failed for invoice {invoice.id}: {e}")
            # Update invoice with error status
            invoice.ocr_status = 'failed'
            invoice.ocr_error = ocr_error
            db.commit()
            db.refresh(invoice)

    return invoice


def _process_invoice_ocr(db: Session, invoice: ScannedInvoice, venue_id: int, file_path: Optional[str] = None) -> ScannedInvoice:
    """
    Process invoice OCR using available OCR backend.

    Supports multiple OCR backends with fallback:
    1. pytesseract (local, free) - requires tesseract-ocr installed
    2. pdf2image + pytesseract for PDFs
    3. Falls back to manual extraction if no OCR available
    """
    logger = logging.getLogger(__name__)

    # Update status to processing
    invoice.ocr_status = 'processing'
    db.commit()

    extracted_text = ""
    ocr_confidence = 0.0

    try:
        # Try to extract text from the file
        if file_path and os.path.exists(file_path):
            extracted_text, ocr_confidence = _extract_text_from_file(file_path, invoice.file_type)

        if not extracted_text:
            # No text extracted - mark for manual processing
            invoice.ocr_status = 'pending_manual'
            invoice.ocr_error = 'OCR extraction returned no text. Manual entry required.'
            invoice.ocr_confidence = 0.0
            db.commit()
            return invoice

        # Store raw OCR text
        invoice.ocr_raw_text = extracted_text
        invoice.ocr_confidence = ocr_confidence

        # Parse extracted text for invoice data
        parsed_data = _parse_invoice_text(extracted_text)

        # Apply parsed data to invoice
        if parsed_data.get('supplier_name'):
            invoice.supplier_name_extracted = parsed_data['supplier_name']
        if parsed_data.get('invoice_number'):
            invoice.invoice_number_extracted = parsed_data['invoice_number']
        if parsed_data.get('invoice_date'):
            invoice.invoice_date_extracted = parsed_data['invoice_date']
        if parsed_data.get('due_date'):
            invoice.due_date_extracted = parsed_data['due_date']
        if parsed_data.get('subtotal'):
            invoice.subtotal_extracted = parsed_data['subtotal']
        if parsed_data.get('tax'):
            invoice.tax_extracted = parsed_data['tax']
        if parsed_data.get('total'):
            invoice.total_extracted = parsed_data['total']
        if parsed_data.get('line_items'):
            invoice.line_items_extracted = parsed_data['line_items']

        # Try to match supplier if not already set
        if not invoice.supplier_id and invoice.supplier_name_extracted:
            supplier = db.query(Supplier).filter(
                Supplier.venue_id == venue_id,
                Supplier.name.ilike(f"%{invoice.supplier_name_extracted}%")
            ).first()
            if supplier:
                invoice.supplier_id = supplier.id

        # Try to match line items to stock items using matching rules
        if invoice.line_items_extracted:
            matched_items = []
            for item in invoice.line_items_extracted:
                matched_item = _match_invoice_item_to_stock(
                    db, venue_id, item, invoice.supplier_id
                )
                matched_items.append(matched_item)
            invoice.line_items_extracted = matched_items

        invoice.ocr_status = 'completed'
        invoice.verification_status = 'unverified'

    except Exception as e:
        logger.exception(f"OCR processing failed for invoice {invoice.id}")
        invoice.ocr_status = 'failed'
        invoice.ocr_error = str(e)

    db.commit()
    return invoice


def _extract_text_from_file(file_path: str, file_type: str) -> tuple:
    """
    Extract text from file using available OCR libraries.
    Returns (extracted_text, confidence_score)
    """
    logger = logging.getLogger(__name__)
    extracted_text = ""
    confidence = 0.0

    try:
        if file_type == 'pdf':
            # Try to extract text from PDF
            try:
                # First try direct PDF text extraction (for digital PDFs)
                import PyPDF2
                with open(file_path, 'rb') as pdf_file:
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    for page in pdf_reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            extracted_text += page_text + "\n"

                if extracted_text.strip():
                    confidence = 0.95  # High confidence for digital PDFs
                    return extracted_text, confidence
            except ImportError:
                logger.debug("PyPDF2 not available, trying OCR")
            except Exception as e:
                logger.debug(f"PDF text extraction failed: {e}, trying OCR")

            # If no text extracted, try OCR on PDF pages
            try:
                from pdf2image import convert_from_path
                import pytesseract

                images = convert_from_path(file_path, dpi=300)
                for i, image in enumerate(images):
                    page_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
                    page_text = pytesseract.image_to_string(image)
                    extracted_text += page_text + "\n"

                    # Calculate average confidence from word confidences
                    confidences = [int(c) for c in page_data['conf'] if int(c) > 0]
                    if confidences:
                        confidence = sum(confidences) / len(confidences) / 100

            except ImportError:
                logger.warning("pdf2image or pytesseract not available for PDF OCR")
            except Exception as e:
                logger.error(f"PDF OCR failed: {e}")

        else:  # Image file
            try:
                import pytesseract
                from PIL import Image

                image = Image.open(file_path)

                # Get OCR data with confidence scores
                ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
                extracted_text = pytesseract.image_to_string(image)

                # Calculate average confidence
                confidences = [int(c) for c in ocr_data['conf'] if int(c) > 0]
                if confidences:
                    confidence = sum(confidences) / len(confidences) / 100

            except ImportError:
                logger.warning("pytesseract or PIL not available for image OCR")
            except Exception as e:
                logger.error(f"Image OCR failed: {e}")

    except Exception as e:
        logger.error(f"Text extraction failed: {e}")

    return extracted_text, confidence


def _parse_invoice_text(text: str) -> dict:
    """
    Parse extracted OCR text to identify invoice fields.
    Uses regex patterns to find common invoice elements.
    """
    result = {
        'supplier_name': None,
        'invoice_number': None,
        'invoice_date': None,
        'due_date': None,
        'subtotal': None,
        'tax': None,
        'total': None,
        'line_items': []
    }

    if not text:
        return result

    lines = text.split('\n')
    text_lower = text.lower()

    # Extract invoice number
    invoice_num_patterns = [
        r'invoice\s*#?\s*:?\s*([A-Z0-9-]+)',
        r'inv\s*#?\s*:?\s*([A-Z0-9-]+)',
        r'invoice\s+number\s*:?\s*([A-Z0-9-]+)',
        r'bill\s*#?\s*:?\s*([A-Z0-9-]+)',
    ]
    for pattern in invoice_num_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result['invoice_number'] = match.group(1).strip()
            break

    # Extract dates
    date_patterns = [
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',  # DD/MM/YYYY or MM/DD/YYYY
        r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})',    # YYYY-MM-DD
        r'(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{2,4})',  # DD Month YYYY
    ]

    dates_found = []
    for pattern in date_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        dates_found.extend(matches)

    if dates_found:
        # First date is usually invoice date
        try:
            from dateutil import parser as date_parser
            result['invoice_date'] = date_parser.parse(dates_found[0], dayfirst=True).date()
            if len(dates_found) > 1:
                result['due_date'] = date_parser.parse(dates_found[1], dayfirst=True).date()
        except (ValueError, TypeError, OverflowError):
            pass

    # Extract monetary amounts
    money_pattern = r'[\$\£\€]?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'

    # Look for total
    total_patterns = [
        r'total\s*:?\s*[\$\£\€]?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        r'amount\s+due\s*:?\s*[\$\£\€]?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        r'balance\s+due\s*:?\s*[\$\£\€]?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        r'grand\s+total\s*:?\s*[\$\£\€]?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
    ]
    for pattern in total_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result['total'] = float(match.group(1).replace(',', ''))
            break

    # Look for subtotal
    subtotal_patterns = [
        r'subtotal\s*:?\s*[\$\£\€]?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        r'sub\s*-?\s*total\s*:?\s*[\$\£\€]?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
    ]
    for pattern in subtotal_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result['subtotal'] = float(match.group(1).replace(',', ''))
            break

    # Look for tax
    tax_patterns = [
        r'(?:tax|vat|gst)\s*:?\s*[\$\£\€]?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        r'(?:tax|vat|gst)\s*\(\d+%?\)\s*:?\s*[\$\£\€]?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
    ]
    for pattern in tax_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result['tax'] = float(match.group(1).replace(',', ''))
            break

    # Extract line items (simplified - looks for lines with quantity and price)
    line_item_pattern = r'^(.+?)\s+(\d+(?:\.\d+)?)\s*(?:x|@)?\s*[\$\£\€]?\s*(\d+(?:\.\d+)?)\s*[\$\£\€]?\s*(\d+(?:\.\d+)?)?$'

    for line in lines:
        line = line.strip()
        if len(line) > 10:  # Skip very short lines
            match = re.match(line_item_pattern, line, re.IGNORECASE)
            if match:
                item = {
                    'description': match.group(1).strip(),
                    'quantity': float(match.group(2)),
                    'unit_price': float(match.group(3)),
                    'total': float(match.group(4)) if match.group(4) else float(match.group(2)) * float(match.group(3))
                }
                result['line_items'].append(item)

    # Try to extract supplier name (usually at the top of invoice)
    # Take first non-empty line that looks like a company name
    for line in lines[:10]:  # Check first 10 lines
        line = line.strip()
        if len(line) > 3 and not any(keyword in line.lower() for keyword in ['invoice', 'bill', 'date', 'number', '#', 'to:', 'from:']):
            # Check if line looks like a company name (contains letters, maybe some punctuation)
            if re.match(r'^[A-Za-z][A-Za-z0-9\s&.,\'-]+$', line):
                result['supplier_name'] = line
                break

    return result


def _match_invoice_item_to_stock(
    db: Session,
    venue_id: int,
    item: dict,
    supplier_id: Optional[int]
) -> dict:
    """Match an invoice line item to a stock item using matching rules"""
    description = item.get('description', '')

    # First, try matching rules
    rules_query = db.query(InvoiceMatchingRule).filter(
        InvoiceMatchingRule.venue_id == venue_id,
        InvoiceMatchingRule.is_active == True
    ).order_by(InvoiceMatchingRule.priority.desc())

    if supplier_id:
        # Try supplier-specific rules first
        supplier_rules = rules_query.filter(
            InvoiceMatchingRule.supplier_id == supplier_id
        ).all()

        for rule in supplier_rules:
            if rule.invoice_description_pattern.lower() in description.lower():
                item['matched_stock_item_id'] = rule.stock_item_id
                item['conversion_factor'] = rule.conversion_factor
                return item

    # Try general rules
    general_rules = rules_query.filter(
        InvoiceMatchingRule.supplier_id.is_(None)
    ).all()

    for rule in general_rules:
        if rule.invoice_description_pattern.lower() in description.lower():
            item['matched_stock_item_id'] = rule.stock_item_id
            item['conversion_factor'] = rule.conversion_factor
            return item

    # Fallback: try to find stock item by name similarity
    stock_item = db.query(StockItem).filter(
        StockItem.venue_id == venue_id,
        StockItem.name.ilike(f"%{description[:50]}%")
    ).first()

    if stock_item:
        item['matched_stock_item_id'] = stock_item.id
        item['match_confidence'] = 'low'

    return item


@router.post("/invoices/{invoice_id}/process", response_model=InvoiceResponse)
@limiter.limit("30/minute")
async def process_invoice(
    request: Request,
    invoice_id: int,
    body: InvoiceProcessRequest = InvoiceProcessRequest(),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Manually trigger OCR processing for an invoice"""
    invoice = db.query(ScannedInvoice).filter(
        ScannedInvoice.id == invoice_id,
        ScannedInvoice.venue_id == current_user.venue_id
    ).first()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Check if already processed
    if invoice.ocr_status == 'completed' and not body.force_reprocess:
        raise HTTPException(
            status_code=400,
            detail="Invoice already processed. Set force_reprocess=true to reprocess."
        )

    # Reconstruct file path from URL
    upload_base_dir = os.environ.get('UPLOAD_DIR', '/tmp/uploads')
    # file_url format: /uploads/invoices/{venue_id}/{filename}
    relative_path = invoice.file_url.lstrip('/')
    file_path = os.path.join(upload_base_dir, relative_path.replace('uploads/', '', 1))

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail="Invoice file not found on disk. Please re-upload the invoice."
        )

    # Process the invoice
    invoice = _process_invoice_ocr(db, invoice, current_user.venue_id, file_path)

    return invoice


@router.post("/invoices/{invoice_id}/verify", response_model=InvoiceResponse)
@limiter.limit("30/minute")
async def verify_invoice(
    request: Request,
    invoice_id: int,
    body: InvoiceVerifyRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Verify and correct OCR-extracted invoice data"""
    invoice = db.query(ScannedInvoice).filter(
        ScannedInvoice.id == invoice_id,
        ScannedInvoice.venue_id == current_user.venue_id
    ).first()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Update with verified data
    if body.supplier_id is not None:
        invoice.supplier_id = body.supplier_id
    if body.invoice_number is not None:
        invoice.invoice_number_extracted = body.invoice_number
    if body.invoice_date is not None:
        invoice.invoice_date_extracted = body.invoice_date
    if body.subtotal is not None:
        invoice.subtotal_extracted = body.subtotal
    if body.tax is not None:
        invoice.tax_extracted = body.tax
    if body.total is not None:
        invoice.total_extracted = body.total
    if body.line_items is not None:
        invoice.line_items_extracted = body.line_items
    if body.notes is not None:
        invoice.notes = body.notes

    invoice.verification_status = 'verified'
    invoice.verified_by = current_user.id
    invoice.verified_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(invoice)

    return invoice


@router.post("/invoices/{invoice_id}/match-po")
@limiter.limit("30/minute")
async def match_invoice_to_po(
    request: Request,
    invoice_id: int,
    body: InvoiceMatchRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Match a scanned invoice to a purchase order"""
    invoice = db.query(ScannedInvoice).filter(
        ScannedInvoice.id == invoice_id,
        ScannedInvoice.venue_id == current_user.venue_id
    ).first()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    po = db.query(PurchaseOrder).filter(
        PurchaseOrder.id == body.purchase_order_id,
        PurchaseOrder.location_id == current_user.venue_id
    ).first()

    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    # Compare invoice to PO
    po_items = db.query(PurchaseOrderItem).filter(
        PurchaseOrderItem.purchase_order_id == po.id
    ).all()

    discrepancies = []
    invoice_items = invoice.line_items_extracted or []

    # Track matched invoice items
    matched_invoice_item_indices = set()

    # Check for quantity/price discrepancies
    for po_item in po_items:
        matching_invoice_item = None
        matching_index = None
        for idx, inv_item in enumerate(invoice_items):
            if inv_item.get('matched_stock_item_id') == po_item.stock_item_id:
                matching_invoice_item = inv_item
                matching_index = idx
                break

        if matching_invoice_item:
            matched_invoice_item_indices.add(matching_index)
            inv_qty = matching_invoice_item.get('quantity', 0)
            inv_price = matching_invoice_item.get('unit_price', 0)

            if inv_qty != po_item.quantity_ordered:
                discrepancies.append({
                    'type': 'quantity',
                    'stock_item_id': po_item.stock_item_id,
                    'item_name': po_item.item_name,
                    'po_quantity': po_item.quantity_ordered,
                    'invoice_quantity': inv_qty
                })

            if inv_price and abs(inv_price - float(po_item.unit_price)) > 0.01:
                discrepancies.append({
                    'type': 'price',
                    'stock_item_id': po_item.stock_item_id,
                    'item_name': po_item.item_name,
                    'po_price': float(po_item.unit_price),
                    'invoice_price': inv_price
                })
        else:
            discrepancies.append({
                'type': 'missing_on_invoice',
                'stock_item_id': po_item.stock_item_id,
                'item_name': po_item.item_name
            })

    # Check for extra items on invoice that are not on PO
    for idx, inv_item in enumerate(invoice_items):
        if idx not in matched_invoice_item_indices:
            discrepancies.append({
                'type': 'extra_on_invoice',
                'description': inv_item.get('description', 'Unknown item'),
                'stock_item_id': inv_item.get('matched_stock_item_id'),
                'quantity': inv_item.get('quantity'),
                'unit_price': inv_item.get('unit_price')
            })

    # Update invoice with match
    invoice.matched_po_id = po.id

    if discrepancies:
        invoice.verification_status = 'discrepancy'
    else:
        invoice.verification_status = 'verified'

    db.commit()

    return {
        "invoice_id": invoice.id,
        "purchase_order_id": po.id,
        "match_status": "discrepancy" if discrepancies else "matched",
        "discrepancies": discrepancies
    }


@router.post("/invoices/{invoice_id}/create-matching-rule")
@limiter.limit("30/minute")
async def create_matching_rule_from_invoice(
    request: Request,
    invoice_id: int,
    line_item_index: int,
    stock_item_id: int,
    conversion_factor: float = 1.0,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Create a matching rule from an invoice line item for future auto-matching"""
    invoice = db.query(ScannedInvoice).filter(
        ScannedInvoice.id == invoice_id,
        ScannedInvoice.venue_id == current_user.venue_id
    ).first()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if not invoice.line_items_extracted:
        raise HTTPException(status_code=400, detail="Invoice has no extracted line items")

    if line_item_index >= len(invoice.line_items_extracted):
        raise HTTPException(status_code=400, detail="Invalid line item index")

    line_item = invoice.line_items_extracted[line_item_index]
    description = line_item.get('description', '')

    if not description:
        raise HTTPException(status_code=400, detail="Line item has no description")

    # Create matching rule
    rule = InvoiceMatchingRule(
        venue_id=current_user.venue_id,
        supplier_id=invoice.supplier_id,
        invoice_description_pattern=description,
        stock_item_id=stock_item_id,
        invoice_unit=line_item.get('unit'),
        conversion_factor=conversion_factor,
        priority=10  # Default priority
    )

    db.add(rule)
    db.commit()
    db.refresh(rule)

    # Update the line item with the match - need to create a new list to flag as modified
    updated_items = list(invoice.line_items_extracted)
    updated_items[line_item_index]['matched_stock_item_id'] = stock_item_id
    updated_items[line_item_index]['conversion_factor'] = conversion_factor
    invoice.line_items_extracted = updated_items
    db.commit()

    return {
        "rule_id": rule.id,
        "pattern": description,
        "stock_item_id": stock_item_id,
        "message": "Matching rule created successfully"
    }


@router.get("/invoices")
@limiter.limit("60/minute")
async def list_invoices(
    request: Request,
    status_filter: Optional[str] = None,
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List scanned invoices"""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    query = db.query(ScannedInvoice).filter(
        ScannedInvoice.venue_id == current_user.venue_id,
        ScannedInvoice.uploaded_at >= start_date
    )

    if status_filter:
        query = query.filter(ScannedInvoice.ocr_status == status_filter)

    return query.order_by(ScannedInvoice.uploaded_at.desc()).all()


@router.get("/invoices/{invoice_id}")
@limiter.limit("60/minute")
async def get_invoice(
    request: Request,
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get invoice details with extracted data"""
    invoice = db.query(ScannedInvoice).filter(
        ScannedInvoice.id == invoice_id,
        ScannedInvoice.venue_id == current_user.venue_id
    ).first()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return invoice

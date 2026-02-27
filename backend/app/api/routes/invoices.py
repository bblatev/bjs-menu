"""Invoice OCR & AP Automation routes - Toast xtraCHEF style."""

from typing import List, Optional
from datetime import date, timezone
from fastapi import APIRouter, HTTPException, UploadFile, File, Query, Request

from app.db.session import DbSession
from app.core.rate_limit import limiter
from app.core.responses import list_response, paginated_response
from app.models.invoice import Invoice, InvoiceLine, GLCode, PriceAlert, PriceHistory
from app.services.invoice_service import InvoiceOCRService, APAutomationService, PriceTrackingService
from app.schemas.invoice import (
    InvoiceCreate, InvoiceUpdate, InvoiceResponse, InvoiceOCRResponse,
    GLCodeCreate, GLCodeResponse, APApprovalResponse,
    PriceAlertResponse, PriceTrendResponse, PriceHistoryResponse
)

router = APIRouter()


# ==================== Stats & Summary ====================

@router.get("/stats")
@limiter.limit("60/minute")
def get_invoice_stats(request: Request, db: DbSession):
    """Get invoice statistics for dashboard."""
    from sqlalchemy import func
    from datetime import datetime

    try:
        today = datetime.now(timezone.utc).date()
        month_start = today.replace(day=1)

        total_invoices = db.query(func.count(Invoice.id)).scalar() or 0
        total_amount = db.query(func.sum(Invoice.total_amount)).scalar() or 0

        # Get all invoices and count by status
        all_invoices = db.query(Invoice).all()
        pending_count = sum(1 for inv in all_invoices if inv.status and inv.status.value in ["pending", "needs_review", "processing"])
        paid_count = sum(1 for inv in all_invoices if inv.status and inv.status.value == "paid")
        overdue_count = sum(1 for inv in all_invoices if inv.due_date and inv.due_date < today and (not inv.status or inv.status.value != "paid"))

        # This month total
        this_month_invoices = [inv for inv in all_invoices if inv.invoice_date and inv.invoice_date >= month_start]
        this_month_total = sum(inv.total_amount or 0 for inv in this_month_invoices)

        pending_invoices = [inv for inv in all_invoices if inv.status and inv.status.value in ["pending", "needs_review", "processing"]]
        pending_amount = sum(float(inv.total_amount or 0) for inv in pending_invoices)
        overdue_invoices = [inv for inv in all_invoices if inv.due_date and inv.due_date < today and (not inv.status or inv.status.value != "paid")]
        overdue_amount = sum(float(inv.total_amount or 0) for inv in overdue_invoices)

        return {
            "total_invoices": total_invoices,
            "total_amount": float(total_amount) if total_amount else 0.0,
            "pending_count": pending_count,
            "pending_amount": pending_amount,
            "paid_count": paid_count,
            "overdue_count": overdue_count,
            "overdue_amount": overdue_amount,
            "this_month_total": float(this_month_total),
            "avg_processing_time_days": 0,
            "ocr_accuracy_rate": 0,
        }
    except Exception as e:
        # Return default stats if database query fails
        return {
            "total_invoices": 0,
            "total_amount": 0.0,
            "pending_count": 0,
            "pending_amount": 0.0,
            "paid_count": 0,
            "overdue_count": 0,
            "overdue_amount": 0.0,
            "this_month_total": 0.0,
            "avg_processing_time_days": 0,
            "ocr_accuracy_rate": 0,
        }


@router.get("/suppliers")
@limiter.limit("60/minute")
def get_invoice_suppliers(request: Request, db: DbSession):
    """Get suppliers that have invoices."""
    from sqlalchemy import func
    from app.models.supplier import Supplier

    # Get suppliers with invoice counts
    supplier_stats = db.query(
        Invoice.supplier_id,
        func.count(Invoice.id).label("invoice_count"),
        func.sum(Invoice.total_amount).label("total_amount")
    ).group_by(Invoice.supplier_id).all()

    suppliers = []
    for supplier_id, count, total in supplier_stats:
        if supplier_id:
            supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
            if supplier:
                suppliers.append({
                    "id": supplier.id,
                    "name": supplier.name,
                    "invoice_count": count,
                    "total_amount": float(total or 0),
                })

    return suppliers


# ==================== Invoice CRUD ====================

@router.get("/")
@limiter.limit("60/minute")
def list_invoices(
    request: Request,
    db: DbSession,
    supplier_id: Optional[int] = None,
    status: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    skip: int = 0,
    limit: int = 100,
):
    """List all invoices with optional filters."""
    query = db.query(Invoice)

    if supplier_id:
        query = query.filter(Invoice.supplier_id == supplier_id)
    if status:
        query = query.filter(Invoice.status == status)
    if start_date:
        query = query.filter(Invoice.invoice_date >= start_date)
    if end_date:
        query = query.filter(Invoice.invoice_date <= end_date)

    total = query.count()
    items = query.offset(skip).limit(limit).all()
    return paginated_response(
        items=[InvoiceResponse.model_validate(i) for i in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/pending", response_model=List[InvoiceResponse])
@limiter.limit("60/minute")
def list_pending_invoices(
    request: Request,
    db: DbSession,
    skip: int = 0,
    limit: int = 100,
):
    """List invoices pending approval."""
    from app.models.invoice import InvoiceStatus
    return db.query(Invoice).filter(
        Invoice.status.in_([InvoiceStatus.PENDING, InvoiceStatus.NEEDS_REVIEW])
    ).offset(skip).limit(limit).all()


@router.get("/overdue", response_model=List[InvoiceResponse])
@limiter.limit("60/minute")
def list_overdue_invoices(
    request: Request,
    db: DbSession,
    skip: int = 0,
    limit: int = 100,
):
    """List overdue invoices (past due date and not paid)."""
    from app.models.invoice import InvoiceStatus
    from datetime import date
    today = date.today()
    return db.query(Invoice).filter(
        Invoice.due_date < today,
        Invoice.status != InvoiceStatus.PAID
    ).offset(skip).limit(limit).all()


@router.get("/{invoice_id}", response_model=InvoiceResponse)
@limiter.limit("60/minute")
def get_invoice(request: Request, db: DbSession, invoice_id: int):
    """Get invoice by ID."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.post("/", response_model=InvoiceResponse)
@limiter.limit("30/minute")
def create_invoice(request: Request, db: DbSession, invoice: InvoiceCreate):
    """Create a new invoice manually."""
    # Map schema fields to model fields
    invoice_data = invoice.model_dump(exclude={"lines"})
    invoice_data["tax_amount"] = invoice_data.pop("tax", 0)
    invoice_data["total_amount"] = invoice_data.pop("total", 0)

    db_invoice = Invoice(**invoice_data)
    db.add(db_invoice)
    db.flush()

    for line in invoice.lines:
        line_data = line.model_dump()
        # Map line schema fields to model fields
        line_data["item_description"] = line_data.pop("description", "")
        line_data["line_total"] = line_data.pop("total_price", 0)
        line_data.pop("line_number", None)  # Model doesn't have line_number
        line_data.pop("gl_code_id", None)  # Model uses gl_code string, not id
        db_line = InvoiceLine(invoice_id=db_invoice.id, **line_data)
        db.add(db_line)

    db.commit()
    db.refresh(db_invoice)
    return db_invoice


@router.put("/{invoice_id}", response_model=InvoiceResponse)
@limiter.limit("30/minute")
def update_invoice(
    request: Request,
    db: DbSession,
    invoice_id: int,
    invoice: InvoiceUpdate,
):
    """Update an invoice."""
    db_invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not db_invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    for key, value in invoice.model_dump(exclude_unset=True).items():
        setattr(db_invoice, key, value)

    db.commit()
    db.refresh(db_invoice)
    return db_invoice


@router.delete("/{invoice_id}")
@limiter.limit("30/minute")
def delete_invoice(request: Request, db: DbSession, invoice_id: int):
    """Delete an invoice."""
    db_invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not db_invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    db.delete(db_invoice)
    db.commit()
    return {"status": "deleted"}


# Invoice OCR

@router.post("/ocr/upload", response_model=InvoiceOCRResponse)
@limiter.limit("30/minute")
async def upload_invoice_image(
    request: Request,
    db: DbSession,
    file: UploadFile = File(...),
    supplier_id: Optional[int] = None,
):
    """Upload and process an invoice image with OCR."""
    import base64

    contents = await file.read()
    image_base64 = base64.b64encode(contents).decode()

    service = InvoiceOCRService(db)
    result = await service.process_invoice_image(
        image_data=image_base64,
        supplier_id=supplier_id
    )

    return InvoiceOCRResponse(
        invoice_id=result["invoice_id"],
        confidence=result["confidence"],
        extracted_data=result["extracted_data"],
        needs_review=result["needs_review"],
        flagged_items=result["flagged_items"]
    )


@router.post("/ocr/url", response_model=InvoiceOCRResponse)
@limiter.limit("30/minute")
async def process_invoice_url(
    request: Request,
    db: DbSession,
    image_url: str,
    supplier_id: Optional[int] = None,
):
    """Process an invoice from URL."""
    service = InvoiceOCRService(db)
    result = await service.process_invoice_image(
        image_url=image_url,
        supplier_id=supplier_id
    )

    return InvoiceOCRResponse(
        invoice_id=result["invoice_id"],
        confidence=result["confidence"],
        extracted_data=result["extracted_data"],
        needs_review=result["needs_review"],
        flagged_items=result["flagged_items"]
    )


# AP Approval Workflow

@router.post("/{invoice_id}/approve", response_model=InvoiceResponse)
@limiter.limit("30/minute")
def approve_invoice(
    request: Request,
    db: DbSession,
    invoice_id: int,
    approver_id: int = Query(default=1),
    notes: Optional[str] = None,
):
    """Approve an invoice."""
    service = APAutomationService(db)
    result = service.process_approval(invoice_id, approver_id, "approve", notes)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result["invoice"]


@router.post("/{invoice_id}/reject", response_model=InvoiceResponse)
@limiter.limit("30/minute")
def reject_invoice(
    request: Request,
    db: DbSession,
    invoice_id: int,
    approver_id: int = Query(default=1),
    notes: Optional[str] = None,
):
    """Reject an invoice."""
    service = APAutomationService(db)
    result = service.process_approval(invoice_id, approver_id, "reject", notes)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result["invoice"]


@router.get("/{invoice_id}/approvals", response_model=List[APApprovalResponse])
@limiter.limit("60/minute")
def get_invoice_approvals(request: Request, db: DbSession, invoice_id: int):
    """Get approval history for an invoice."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    approvals = []
    # If invoice has been approved or rejected, return that as the approval record
    if invoice.approved_by and invoice.approved_at:
        from app.schemas.invoice import APApprovalResponse
        approvals.append(APApprovalResponse(
            id=invoice.id,
            invoice_id=invoice.id,
            step_number=1,
            approver_id=invoice.approved_by,
            approver_name=None,
            status=invoice.status.value if hasattr(invoice.status, 'value') else str(invoice.status),
            notes=invoice.rejection_reason if invoice.status == "rejected" else invoice.notes,
            created_at=invoice.created_at or invoice.approved_at,
            completed_at=invoice.approved_at,
        ))

    return approvals


# GL Codes

@router.get("/gl-codes/", response_model=List[GLCodeResponse])
@limiter.limit("60/minute")
def list_gl_codes(request: Request, db: DbSession):
    """List all GL codes."""
    return db.query(GLCode).filter(GLCode.is_active == True).all()


@router.post("/gl-codes/", response_model=GLCodeResponse)
@limiter.limit("30/minute")
def create_gl_code(request: Request, db: DbSession, gl_code: GLCodeCreate):
    """Create a new GL code."""
    existing = db.query(GLCode).filter(GLCode.code == gl_code.code).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"GL code '{gl_code.code}' already exists")
    db_gl = GLCode(**gl_code.model_dump())
    db.add(db_gl)
    db.commit()
    db.refresh(db_gl)
    return db_gl


# Price Tracking

@router.get("/price-alerts/", response_model=List[PriceAlertResponse])
@limiter.limit("60/minute")
def list_price_alerts(
    request: Request,
    db: DbSession,
    active: Optional[bool] = None,
):
    """List price alerts."""
    query = db.query(PriceAlert)
    if active is not None:
        query = query.filter(PriceAlert.is_active == active)
    return query.order_by(PriceAlert.created_at.desc()).limit(100).all()


@router.post("/price-alerts/{alert_id}/acknowledge")
@limiter.limit("30/minute")
def acknowledge_price_alert(
    request: Request,
    db: DbSession,
    alert_id: int,
    user_id: int = Query(...),
):
    """Acknowledge a price alert by deactivating it."""
    alert = db.query(PriceAlert).filter(PriceAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Deactivate the alert to mark it as acknowledged
    alert.is_active = False
    db.commit()

    return {"status": "acknowledged"}


@router.get("/price-history/{product_id}", response_model=List[PriceHistoryResponse])
@limiter.limit("60/minute")
def get_price_history(
    request: Request,
    db: DbSession,
    product_id: int,
    supplier_id: Optional[int] = None,
    days: int = 90,
):
    """Get price history for a product."""
    service = PriceTrackingService(db)
    return service.get_price_history(product_id, supplier_id, days)


@router.get("/price-trends/{product_id}", response_model=PriceTrendResponse)
@limiter.limit("60/minute")
def get_price_trends(
    request: Request,
    db: DbSession,
    product_id: int,
    days: int = 30,
):
    """Get price trends for a product."""
    service = PriceTrackingService(db)
    results = service.get_price_trends(product_ids=[product_id], days=days)

    # Get product name
    from app.models.stock_item import StockItem
    product = db.query(StockItem).filter(StockItem.id == product_id).first()
    product_name = product.name if product else f"Product {product_id}"

    # Get price history
    history = service.get_price_history(product_id, days=days)
    price_history = [
        {"date": h.recorded_at.isoformat(), "price": float(h.price), "supplier_id": h.supplier_id}
        for h in history
    ] if history else []

    if not results:
        return {
            "product_id": product_id,
            "product_name": product_name,
            "current_price": 0,
            "avg_price_30d": 0,
            "min_price_30d": 0,
            "max_price_30d": 0,
            "trend": "stable",
            "price_history": price_history
        }

    r = results[0]
    return {
        "product_id": product_id,
        "product_name": product_name,
        "current_price": r.get("current_price") or 0,
        "avg_price_30d": r.get("avg_price") or 0,
        "min_price_30d": r.get("min_price") or 0,
        "max_price_30d": r.get("max_price") or 0,
        "trend": r.get("trend", "stable"),
        "price_history": price_history
    }

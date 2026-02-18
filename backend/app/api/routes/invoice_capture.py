"""Invoice Capture API routes.

Endpoints for OCR-based invoice processing: upload, review, approve/reject,
and PO generation from captured invoices.
"""

from typing import Optional

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile, status
from pydantic import BaseModel, Field

from app.core.rbac import CurrentUser, RequireManager
from app.core.rate_limit import limiter
from app.db.session import DbSession
from app.services.invoice_capture_service import InvoiceCaptureService

router = APIRouter()


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class RejectRequest(BaseModel):
    """Request body for rejecting a captured invoice."""
    reason: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Reason for rejecting the invoice",
    )


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

@router.post("/upload")
@limiter.limit("30/minute")
async def upload_invoice(
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
    file: UploadFile = File(..., description="Invoice image (JPEG, PNG, PDF)"),
    location_id: int = Query(default=1, description="Location this invoice belongs to"),
):
    """Upload an invoice image for OCR processing.

    The full pipeline runs synchronously:
    1. Save the uploaded file to disk.
    2. Run Tesseract OCR to extract text.
    3. Parse supplier name, invoice number, date, line items, total.
    4. Fuzzy-match supplier and products to existing records.
    5. Return the captured invoice with match results.

    Supported formats: JPEG, PNG, TIFF, PDF (first page only).
    """
    # Validate file type
    allowed_types = {
        "image/jpeg", "image/png", "image/tiff",
        "application/pdf", "image/jpg",
    }
    content_type = file.content_type or ""
    filename = file.filename or "invoice.jpg"

    # Accept by extension if content_type is missing
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    ext_ok = ext in {"jpg", "jpeg", "png", "tiff", "tif", "pdf"}

    if content_type not in allowed_types and not ext_ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {content_type}. Upload JPEG, PNG, TIFF, or PDF.",
        )

    # Read file data
    data = await file.read()
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file uploaded",
        )

    # Size check (max 10 MB)
    max_bytes = 10 * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large. Maximum size is 10 MB.",
        )

    svc = InvoiceCaptureService(db)
    result = svc.capture_invoice(
        image_data=data,
        filename=filename,
        location_id=location_id,
        user_id=current_user.user_id,
    )
    return result


# ---------------------------------------------------------------------------
# Get invoice details
# ---------------------------------------------------------------------------

@router.get("/list")
@limiter.limit("60/minute")
def list_invoices(
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
    location_id: Optional[int] = Query(default=None, description="Filter by location"),
    status_filter: Optional[str] = Query(
        default=None,
        alias="status",
        description="Filter by status: pending, matched, approved, rejected",
    ),
    supplier_id: Optional[int] = Query(default=None, description="Filter by supplier"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """List captured invoices with optional filters and pagination."""
    svc = InvoiceCaptureService(db)
    return svc.list_invoices(
        location_id=location_id,
        status_filter=status_filter,
        supplier_id=supplier_id,
        limit=limit,
        offset=offset,
    )


@router.get("/dashboard")
@limiter.limit("30/minute")
def get_dashboard(
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
):
    """Invoice capture statistics dashboard.

    Returns:
    - Status breakdown (pending, matched, approved, rejected)
    - Average OCR confidence score
    - Line-item match rate
    - Recent invoices
    """
    svc = InvoiceCaptureService(db)
    return svc.get_dashboard()


@router.get("/{invoice_id}")
@limiter.limit("60/minute")
def get_invoice(
    request: Request,
    invoice_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Get full details of a captured invoice including line items and match data."""
    svc = InvoiceCaptureService(db)
    result = svc.get_invoice(invoice_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Captured invoice {invoice_id} not found",
        )
    return result


# ---------------------------------------------------------------------------
# Approve / Reject
# ---------------------------------------------------------------------------

@router.post("/{invoice_id}/approve")
@limiter.limit("30/minute")
def approve_invoice(
    request: Request,
    invoice_id: int,
    db: DbSession,
    current_user: RequireManager,
):
    """Approve a captured invoice (manager or owner only).

    Marks the invoice as approved and records the reviewer. This is
    typically done after verifying the OCR results and product matches.
    """
    svc = InvoiceCaptureService(db)
    try:
        result = svc.approve_invoice(
            invoice_id=invoice_id,
            user_id=current_user.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return result


@router.post("/{invoice_id}/reject")
@limiter.limit("30/minute")
def reject_invoice(
    request: Request,
    invoice_id: int,
    body: RejectRequest,
    db: DbSession,
    current_user: RequireManager,
):
    """Reject a captured invoice (manager or owner only).

    Marks the invoice as rejected. Optionally include a reason.
    """
    svc = InvoiceCaptureService(db)
    try:
        result = svc.reject_invoice(
            invoice_id=invoice_id,
            user_id=current_user.user_id,
            reason=body.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return result


# ---------------------------------------------------------------------------
# PO creation
# ---------------------------------------------------------------------------

@router.post("/{invoice_id}/create-po")
@limiter.limit("15/minute")
def create_po_from_invoice(
    request: Request,
    invoice_id: int,
    db: DbSession,
    current_user: RequireManager,
):
    """Create a draft Purchase Order from a captured invoice.

    Only matched line items (those with a product match) will be included
    in the PO.  The PO is created in DRAFT status for review.
    Requires the invoice to have a matched supplier.
    """
    svc = InvoiceCaptureService(db)
    try:
        result = svc.create_draft_po(
            invoice_id=invoice_id,
            user_id=current_user.user_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    return result



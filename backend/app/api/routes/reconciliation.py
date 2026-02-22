"""Reconciliation, reorder, and export routes."""


from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import FileResponse

from app.core.rate_limit import limiter

from app.core.rbac import CurrentUser
from app.db.session import DbSession
from app.models.inventory import InventorySession, SessionStatus
from app.models.reconciliation import (
    ReconciliationResult,
    ReorderProposal,
    SupplierOrderDraft,
    OrderDraftStatus,
)
from app.schemas.reconciliation import (
    ReconciliationResultResponse,
    ReconciliationSummary,
    ReorderProposalResponse,
    ReorderProposalUpdate,
    ReorderSummary,
    SupplierOrderDraftResponse,
    SupplierOrderDraftDetail,
    SupplierOrderDraftUpdate,
    ReconcileRequest,
    GenerateReordersRequest,
    GenerateOrderDraftsRequest,
    ExportOrderRequest,
    ExportOrderResponse,
    EmailTemplateResponse,
)
from app.services.reconciliation_service import ReconciliationService, ReconciliationConfig
from app.services.reorder_service import ReorderService, ReorderConfig
from app.services.export_service import ExportService

router = APIRouter()


# ==================== Reconciliation Endpoints ====================

@router.get("/")
@limiter.limit("60/minute")
def get_reconciliation_root(request: Request, db: DbSession):
    """Reconciliation overview."""
    return get_reconciliation_results(request=request, db=db)


@router.get("/results")
@limiter.limit("60/minute")
def get_reconciliation_results(
    request: Request,
    db: DbSession,
    limit: int = 20,
):
    """Get recent reconciliation results."""
    results = db.query(ReconciliationResult).order_by(
        ReconciliationResult.created_at.desc()
    ).limit(limit).all()
    return {
        "results": [
            {
                "id": r.id,
                "session_id": r.session_id,
                "product_id": r.product_id,
                "expected_qty": float(r.expected_qty) if r.expected_qty else 0,
                "counted_qty": float(r.counted_qty) if r.counted_qty else 0,
                "variance_qty": float(r.variance_qty) if r.variance_qty else 0,
                "severity": r.severity.value if r.severity else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in results
        ],
        "total": len(results),
    }


@router.post("/reconcile", response_model=ReconciliationSummary)
@limiter.limit("30/minute")
def run_reconciliation(
    request: Request,
    body: ReconcileRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Run reconciliation on an inventory session.
    Compares counted quantities against expected (POS) stock.
    """
    # Verify session exists and is committed
    session = db.query(InventorySession).filter(
        InventorySession.id == body.session_id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    if session.status != SessionStatus.COMMITTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session must be committed before reconciliation"
        )

    # Configure and run reconciliation
    config = ReconciliationConfig(
        critical_threshold_qty=body.critical_threshold_qty,
        critical_threshold_percent=body.critical_threshold_percent,
        warning_threshold_qty=body.warning_threshold_qty,
        warning_threshold_percent=body.warning_threshold_percent,
    )

    service = ReconciliationService(db, config)
    service.reconcile_session(body.session_id, body.expected_source)

    db.commit()

    # Return summary
    summary = service.get_reconciliation_summary(body.session_id)

    return ReconciliationSummary(
        session_id=summary["session_id"],
        total_products=summary["total_products"],
        products_ok=summary["products_ok"],
        products_warning=summary["products_warning"],
        products_critical=summary["products_critical"],
        total_delta_value=Decimal(str(summary["total_delta_value"])) if summary["total_delta_value"] else None,
        results=[
            ReconciliationResultResponse(
                id=r["id"],
                session_id=body.session_id,
                product_id=r["product_id"],
                product_name=r["product_name"],
                product_barcode=r["product_barcode"],
                expected_qty=Decimal(str(r["expected_qty"])),
                counted_qty=Decimal(str(r["counted_qty"])),
                delta_qty=Decimal(str(r["delta_qty"])),
                delta_value=Decimal(str(r["delta_value"])) if r["delta_value"] else None,
                delta_percent=Decimal(str(r["delta_percent"])) if r["delta_percent"] else None,
                severity=r["severity"],
                reason=r["reason"],
                confidence=Decimal(str(r["confidence"])) if r["confidence"] else None,
                created_at=datetime.now(timezone.utc),  # Will be overwritten by actual value
            )
            for r in summary.get("results", [])
        ],
    )


@router.get("/sessions/{session_id}/reconciliation", response_model=ReconciliationSummary)
@limiter.limit("60/minute")
def get_session_reconciliation_results(
    request: Request,
    session_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Get reconciliation results for a session."""
    session = db.query(InventorySession).filter(
        InventorySession.id == session_id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    service = ReconciliationService(db)
    summary = service.get_reconciliation_summary(session_id)

    if summary["total_products"] == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No reconciliation results found for this session"
        )

    return ReconciliationSummary(
        session_id=summary["session_id"],
        total_products=summary["total_products"],
        products_ok=summary["products_ok"],
        products_warning=summary["products_warning"],
        products_critical=summary["products_critical"],
        total_delta_value=Decimal(str(summary["total_delta_value"])) if summary["total_delta_value"] else None,
        results=[
            ReconciliationResultResponse(
                id=r["id"],
                session_id=session_id,
                product_id=r["product_id"],
                product_name=r["product_name"],
                product_barcode=r["product_barcode"],
                expected_qty=Decimal(str(r["expected_qty"])),
                counted_qty=Decimal(str(r["counted_qty"])),
                delta_qty=Decimal(str(r["delta_qty"])),
                delta_value=Decimal(str(r["delta_value"])) if r["delta_value"] else None,
                delta_percent=Decimal(str(r["delta_percent"])) if r["delta_percent"] else None,
                severity=r["severity"],
                reason=r["reason"],
                confidence=Decimal(str(r["confidence"])) if r["confidence"] else None,
                created_at=datetime.now(timezone.utc),
            )
            for r in summary.get("results", [])
        ],
    )


# ==================== Reorder Endpoints ====================

@router.post("/reorders/generate", response_model=ReorderSummary)
@limiter.limit("30/minute")
def generate_reorders(
    request: Request,
    body: GenerateReordersRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Generate reorder proposals based on an inventory session.
    Calculates needed quantities based on target stock and current levels.
    """
    # Verify session exists
    session = db.query(InventorySession).filter(
        InventorySession.id == body.session_id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Configure and generate proposals
    config = ReorderConfig(
        coverage_days=body.coverage_days,
        use_par_level=body.use_par_level,
        round_to_case=body.round_to_case,
    )

    service = ReorderService(db, config)
    service.generate_proposals(body.session_id)

    db.commit()

    # Return summary
    summary = service.get_reorder_summary(body.session_id)

    return ReorderSummary(
        session_id=summary["session_id"],
        total_products=summary["total_products"],
        total_qty=Decimal(str(summary["total_qty"])),
        total_value=Decimal(str(summary["total_value"])) if summary["total_value"] else None,
        suppliers_count=summary["suppliers_count"],
        proposals=[],  # Will be populated from proposals_by_supplier
    )


@router.get("/sessions/{session_id}/reorders", response_model=ReorderSummary)
@limiter.limit("60/minute")
def get_reorder_proposals(
    request: Request,
    session_id: int,
    db: DbSession,
    current_user: CurrentUser,
    include_excluded: bool = Query(False),
):
    """Get reorder proposals for a session."""
    session = db.query(InventorySession).filter(
        InventorySession.id == session_id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    service = ReorderService(db)
    summary = service.get_reorder_summary(session_id)

    # Get proposals from database for full response
    query = db.query(ReorderProposal).filter(
        ReorderProposal.session_id == session_id
    )
    if not include_excluded:
        query = query.filter(ReorderProposal.included == True)

    proposals = query.all()

    return ReorderSummary(
        session_id=summary["session_id"],
        total_products=summary["total_products"],
        total_qty=Decimal(str(summary["total_qty"])),
        total_value=Decimal(str(summary["total_value"])) if summary["total_value"] else None,
        suppliers_count=summary["suppliers_count"],
        proposals=[
            ReorderProposalResponse(
                id=p.id,
                session_id=p.session_id,
                product_id=p.product_id,
                product_name=p.product.name if p.product else None,
                product_barcode=p.product.barcode if p.product else None,
                supplier_id=p.supplier_id,
                supplier_name=p.supplier.name if p.supplier else None,
                current_stock=p.current_stock,
                target_stock=p.target_stock,
                in_transit=p.in_transit,
                recommended_qty=p.recommended_qty,
                rounded_qty=p.rounded_qty,
                pack_size=p.pack_size,
                unit_cost=p.unit_cost,
                line_total=p.line_total,
                rationale_json=p.rationale_json,
                user_qty=p.user_qty,
                included=p.included,
                created_at=p.created_at,
            )
            for p in proposals
        ],
    )


@router.put("/reorders/{proposal_id}", response_model=ReorderProposalResponse)
@limiter.limit("30/minute")
def update_reorder_proposal(
    request: Request,
    proposal_id: int,
    body: ReorderProposalUpdate,
    db: DbSession,
    current_user: CurrentUser,
):
    """Update a reorder proposal (change quantity or include/exclude)."""
    service = ReorderService(db)

    try:
        proposal = service.update_proposal(
            proposal_id=proposal_id,
            user_qty=body.user_qty,
            included=body.included,
        )
        db.commit()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    return ReorderProposalResponse(
        id=proposal.id,
        session_id=proposal.session_id,
        product_id=proposal.product_id,
        product_name=proposal.product.name if proposal.product else None,
        product_barcode=proposal.product.barcode if proposal.product else None,
        supplier_id=proposal.supplier_id,
        supplier_name=proposal.supplier.name if proposal.supplier else None,
        current_stock=proposal.current_stock,
        target_stock=proposal.target_stock,
        in_transit=proposal.in_transit,
        recommended_qty=proposal.recommended_qty,
        rounded_qty=proposal.rounded_qty,
        pack_size=proposal.pack_size,
        unit_cost=proposal.unit_cost,
        line_total=proposal.line_total,
        rationale_json=proposal.rationale_json,
        user_qty=proposal.user_qty,
        included=proposal.included,
        created_at=proposal.created_at,
    )


# ==================== Order Draft Endpoints ====================

@router.post("/order-drafts/generate", response_model=List[SupplierOrderDraftResponse])
@limiter.limit("30/minute")
def generate_order_drafts(
    request: Request,
    body: GenerateOrderDraftsRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Create supplier order drafts from reorder proposals.
    Groups proposals by supplier.
    """
    session = db.query(InventorySession).filter(
        InventorySession.id == body.session_id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    service = ExportService(db)
    drafts = service.create_order_drafts(
        session_id=body.session_id,
        requested_delivery_date=body.requested_delivery_date,
    )

    db.commit()

    return [
        SupplierOrderDraftResponse(
            id=d.id,
            session_id=d.session_id,
            supplier_id=d.supplier_id,
            supplier_name=d.supplier.name if d.supplier else None,
            supplier_email=d.supplier.contact_email if d.supplier else None,
            status=d.status,
            line_count=d.line_count,
            total_qty=d.total_qty,
            total_value=d.total_value,
            requested_delivery_date=d.requested_delivery_date,
            notes=d.notes,
            exported_csv_path=d.exported_csv_path,
            exported_pdf_path=d.exported_pdf_path,
            email_sent_at=d.email_sent_at,
            purchase_order_id=d.purchase_order_id,
            created_at=d.created_at,
            updated_at=d.updated_at,
        )
        for d in drafts
    ]


@router.get("/sessions/{session_id}/order-drafts", response_model=List[SupplierOrderDraftResponse])
@limiter.limit("60/minute")
def list_order_drafts(
    request: Request,
    session_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """List order drafts for a session."""
    session = db.query(InventorySession).filter(
        InventorySession.id == session_id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    drafts = db.query(SupplierOrderDraft).filter(
        SupplierOrderDraft.session_id == session_id
    ).all()

    return [
        SupplierOrderDraftResponse(
            id=d.id,
            session_id=d.session_id,
            supplier_id=d.supplier_id,
            supplier_name=d.supplier.name if d.supplier else None,
            supplier_email=d.supplier.contact_email if d.supplier else None,
            status=d.status,
            line_count=d.line_count,
            total_qty=d.total_qty,
            total_value=d.total_value,
            requested_delivery_date=d.requested_delivery_date,
            notes=d.notes,
            exported_csv_path=d.exported_csv_path,
            exported_pdf_path=d.exported_pdf_path,
            email_sent_at=d.email_sent_at,
            purchase_order_id=d.purchase_order_id,
            created_at=d.created_at,
            updated_at=d.updated_at,
        )
        for d in drafts
    ]


@router.get("/order-drafts/{draft_id}", response_model=SupplierOrderDraftDetail)
@limiter.limit("60/minute")
def get_order_draft(
    request: Request,
    draft_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Get detailed order draft with line items."""
    import json

    draft = db.query(SupplierOrderDraft).filter(
        SupplierOrderDraft.id == draft_id
    ).first()

    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found"
        )

    line_items = json.loads(draft.payload_json) if draft.payload_json else []

    return SupplierOrderDraftDetail(
        id=draft.id,
        session_id=draft.session_id,
        supplier_id=draft.supplier_id,
        supplier_name=draft.supplier.name if draft.supplier else None,
        supplier_email=draft.supplier.contact_email if draft.supplier else None,
        status=draft.status,
        line_count=draft.line_count,
        total_qty=draft.total_qty,
        total_value=draft.total_value,
        requested_delivery_date=draft.requested_delivery_date,
        notes=draft.notes,
        exported_csv_path=draft.exported_csv_path,
        exported_pdf_path=draft.exported_pdf_path,
        email_sent_at=draft.email_sent_at,
        purchase_order_id=draft.purchase_order_id,
        created_at=draft.created_at,
        updated_at=draft.updated_at,
        line_items=line_items,
    )


@router.put("/order-drafts/{draft_id}", response_model=SupplierOrderDraftResponse)
@limiter.limit("30/minute")
def update_order_draft(
    request: Request,
    draft_id: int,
    body: SupplierOrderDraftUpdate,
    db: DbSession,
    current_user: CurrentUser,
):
    """Update an order draft."""
    draft = db.query(SupplierOrderDraft).filter(
        SupplierOrderDraft.id == draft_id
    ).first()

    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found"
        )

    # Don't allow updates to sent orders
    if draft.status == OrderDraftStatus.SENT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update a sent order"
        )

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(draft, field, value)

    db.commit()
    db.refresh(draft)

    return SupplierOrderDraftResponse(
        id=draft.id,
        session_id=draft.session_id,
        supplier_id=draft.supplier_id,
        supplier_name=draft.supplier.name if draft.supplier else None,
        supplier_email=draft.supplier.contact_email if draft.supplier else None,
        status=draft.status,
        line_count=draft.line_count,
        total_qty=draft.total_qty,
        total_value=draft.total_value,
        requested_delivery_date=draft.requested_delivery_date,
        notes=draft.notes,
        exported_csv_path=draft.exported_csv_path,
        exported_pdf_path=draft.exported_pdf_path,
        email_sent_at=draft.email_sent_at,
        purchase_order_id=draft.purchase_order_id,
        created_at=draft.created_at,
        updated_at=draft.updated_at,
    )


# ==================== Export Endpoints ====================

@router.post("/order-drafts/{draft_id}/export", response_model=ExportOrderResponse)
@limiter.limit("30/minute")
def export_order_draft(
    request: Request,
    draft_id: int,
    body: ExportOrderRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    """Export an order draft to CSV or PDF."""
    draft = db.query(SupplierOrderDraft).filter(
        SupplierOrderDraft.id == draft_id
    ).first()

    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found"
        )

    service = ExportService(db)

    if body.format.lower() == "csv":
        file_path = service.export_to_csv(draft_id)
    elif body.format.lower() == "pdf":
        file_path = service.export_to_pdf(draft_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format: {body.format}. Use 'csv' or 'pdf'."
        )

    db.commit()

    return ExportOrderResponse(
        draft_id=draft_id,
        format=body.format,
        file_path=file_path,
        download_url=f"/api/reconciliation/order-drafts/{draft_id}/download/{body.format}",
    )


@router.get("/order-drafts/{draft_id}/download/{format}")
@limiter.limit("60/minute")
def download_export(
    request: Request,
    draft_id: int,
    format: str,
    db: DbSession,
    current_user: CurrentUser,
):
    """Download the exported file."""
    draft = db.query(SupplierOrderDraft).filter(
        SupplierOrderDraft.id == draft_id
    ).first()

    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found"
        )

    if format.lower() == "csv":
        file_path = draft.exported_csv_path
        media_type = "text/csv"
    elif format.lower() == "pdf":
        file_path = draft.exported_pdf_path
        media_type = "application/pdf"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format: {format}"
        )

    if not file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No {format.upper()} export found for this draft. Export first."
        )

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=file_path.split("/")[-1],
    )


@router.get("/order-drafts/{draft_id}/email-template", response_model=EmailTemplateResponse)
@limiter.limit("60/minute")
def get_email_template(
    request: Request,
    draft_id: int,
    db: DbSession,
    current_user: CurrentUser,
    business_name: str = Query("Our Business"),
):
    """Generate email template for a supplier order."""
    draft = db.query(SupplierOrderDraft).filter(
        SupplierOrderDraft.id == draft_id
    ).first()

    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found"
        )

    service = ExportService(db)
    template = service.generate_email_template(draft_id, business_name)

    return EmailTemplateResponse(
        draft_id=template["draft_id"],
        supplier_name=template["supplier_name"],
        supplier_email=template["supplier_email"],
        subject=template["subject"],
        body=template["body"],
        attachment_paths=template["attachment_paths"],
    )


@router.get("/order-drafts/{draft_id}/whatsapp")
@limiter.limit("60/minute")
def get_whatsapp_text(
    request: Request,
    draft_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Generate WhatsApp-ready text for a supplier order."""
    draft = db.query(SupplierOrderDraft).filter(
        SupplierOrderDraft.id == draft_id
    ).first()

    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found"
        )

    service = ExportService(db)
    text = service.generate_whatsapp_text(draft_id)

    return {"text": text}


@router.post("/order-drafts/{draft_id}/finalize", response_model=SupplierOrderDraftResponse)
@limiter.limit("30/minute")
def finalize_order_draft(
    request: Request,
    draft_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Mark an order draft as finalized."""
    service = ExportService(db)

    try:
        draft = service.finalize_draft(draft_id)
        db.commit()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    return SupplierOrderDraftResponse(
        id=draft.id,
        session_id=draft.session_id,
        supplier_id=draft.supplier_id,
        supplier_name=draft.supplier.name if draft.supplier else None,
        supplier_email=draft.supplier.contact_email if draft.supplier else None,
        status=draft.status,
        line_count=draft.line_count,
        total_qty=draft.total_qty,
        total_value=draft.total_value,
        requested_delivery_date=draft.requested_delivery_date,
        notes=draft.notes,
        exported_csv_path=draft.exported_csv_path,
        exported_pdf_path=draft.exported_pdf_path,
        email_sent_at=draft.email_sent_at,
        purchase_order_id=draft.purchase_order_id,
        created_at=draft.created_at,
        updated_at=draft.updated_at,
    )


@router.post("/order-drafts/{draft_id}/mark-sent", response_model=SupplierOrderDraftResponse)
@limiter.limit("30/minute")
def mark_order_sent(
    request: Request,
    draft_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Mark an order draft as sent to supplier."""
    service = ExportService(db)

    try:
        draft = service.mark_as_sent(draft_id)
        db.commit()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    return SupplierOrderDraftResponse(
        id=draft.id,
        session_id=draft.session_id,
        supplier_id=draft.supplier_id,
        supplier_name=draft.supplier.name if draft.supplier else None,
        supplier_email=draft.supplier.contact_email if draft.supplier else None,
        status=draft.status,
        line_count=draft.line_count,
        total_qty=draft.total_qty,
        total_value=draft.total_value,
        requested_delivery_date=draft.requested_delivery_date,
        notes=draft.notes,
        exported_csv_path=draft.exported_csv_path,
        exported_pdf_path=draft.exported_pdf_path,
        email_sent_at=draft.email_sent_at,
        purchase_order_id=draft.purchase_order_id,
        created_at=draft.created_at,
        updated_at=draft.updated_at,
    )

"""
Advanced Purchase Order Management API Endpoints
Complete REST API for:
- Returns to Suppliers & Credit Notes
- PO Amendments & Change Orders
- Blanket/Standing Purchase Orders
- Purchase Requisitions
- Landed Cost Calculation
- Financial Integration (AP, Aging)
- Consolidated Multi-Location Purchasing
- Enhanced Quality Control
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date

from app.db.session import get_db
from app.core.rbac import get_current_user
from app.models import StaffUser

from app.models.purchase_order_advanced import (
    ReturnStatus, CreditNoteStatus, RequisitionStatus, BlanketOrderStatus,
    QCStatus, ConsolidatedOrderStatus
)

from app.schemas.purchase_order_advanced import (
    # Returns
    SupplierReturnCreate, SupplierReturnUpdate, SupplierReturnResponse,
    SupplierReturnShip, SupplierReturnConfirmReceipt,
    # Credit Notes
    SupplierCreditNoteCreate, SupplierCreditNoteUpdate, SupplierCreditNoteResponse,
    CreditNoteApplicationCreate, CreditNoteApplicationResponse,
    # Amendments
    PurchaseOrderAmendmentCreate, PurchaseOrderAmendmentResponse, POVersionHistoryResponse,
    # Blanket Orders
    BlanketPurchaseOrderCreate, BlanketPurchaseOrderUpdate, BlanketPurchaseOrderResponse,
    BlanketReleaseCreate, BlanketReleaseResponse,
    # Requisitions
    PurchaseRequisitionCreate, PurchaseRequisitionUpdate, PurchaseRequisitionResponse,
    RequisitionApprovalAction, RequisitionToPOConvert,
    # Landed Cost
    PurchaseOrderLandedCostCreate, PurchaseOrderLandedCostUpdate, PurchaseOrderLandedCostResponse,
    # Financial
    SupplierPaymentCreate, SupplierPaymentResponse,
    SupplierAccountBalanceResponse, InvoiceAgingSnapshotResponse,
    PaymentTermsConfigCreate, PaymentTermsConfigResponse,
    # Consolidated
    ConsolidatedPurchaseOrderCreate, ConsolidatedPurchaseOrderResponse,
    # Quality Control
    QualityControlChecklistCreate, QualityControlChecklistResponse,
    QualityControlInspectionCreate, QualityControlInspectionUpdate, QualityControlInspectionResponse,
    QualityIssueCreate, QualityIssueUpdate, QualityIssueResponse,
    # Reorder
    StockReorderConfigCreate, StockReorderConfigUpdate, StockReorderConfigResponse,
    ReorderAlertResponse,
    # Partial Delivery
    PartialDeliveryScheduleCreate, PartialDeliveryScheduleResponse,
    BackorderTrackingCreate, BackorderTrackingUpdate, BackorderTrackingResponse,
    # Debit Note
    SupplierDebitNoteCreate, SupplierDebitNoteResponse,
)

from app.services.purchase_order_advanced_service import (
    SupplierReturnService,
    SupplierCreditNoteService,
    PurchaseOrderAmendmentService,
    BlanketPurchaseOrderService,
    PurchaseRequisitionService,
    LandedCostService,
    FinancialIntegrationService,
    QualityControlService,
    StockReorderService,
    PartialDeliveryService,
    ConsolidatedPurchasingService,
)
from app.core.rate_limit import limiter


router = APIRouter()


# =============================================================================
# SUPPLIER RETURNS ENDPOINTS
# =============================================================================

@router.get("/")
@limiter.limit("60/minute")
async def get_purchase_order_advanced_root(request: Request, db: Session = Depends(get_db)):
    """Advanced purchase order features."""
    return {"module": "purchase-order-advanced", "status": "active", "endpoints": ["/returns", "/credit-notes", "/blanket-orders"]}


@router.post("/returns", response_model=SupplierReturnResponse)
@limiter.limit("30/minute")
def create_supplier_return(
    request: Request,
    data: SupplierReturnCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Create a new supplier return (RMA)"""
    return SupplierReturnService.create_return(db, data, current_user.id)


@router.get("/returns", response_model=List[SupplierReturnResponse])
@limiter.limit("60/minute")
def list_supplier_returns(
    request: Request,
    venue_id: int,
    supplier_id: Optional[int] = None,
    status: Optional[ReturnStatus] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List supplier returns with filters"""
    return SupplierReturnService.get_returns(db, venue_id, supplier_id, status, skip, limit)


@router.get("/returns/{return_id}", response_model=SupplierReturnResponse)
@limiter.limit("60/minute")
def get_supplier_return(
    request: Request,
    return_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get a specific supplier return"""
    from app.models.purchase_order_advanced import SupplierReturn
    result = db.query(SupplierReturn).filter(SupplierReturn.id == return_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Return not found")
    return result


@router.post("/returns/{return_id}/submit")
@limiter.limit("30/minute")
def submit_return_for_approval(
    request: Request,
    return_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Submit return for approval"""
    result = SupplierReturnService.submit_for_approval(db, return_id)
    if not result:
        raise HTTPException(status_code=404, detail="Return not found or invalid status")
    return {"status": "submitted", "return_id": return_id}


@router.post("/returns/{return_id}/approve")
@limiter.limit("30/minute")
def approve_return(
    request: Request,
    return_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Approve a supplier return"""
    result = SupplierReturnService.approve_return(db, return_id, current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="Return not found or invalid status")
    return {"status": "approved", "return_id": return_id}


@router.post("/returns/{return_id}/ship")
@limiter.limit("30/minute")
def ship_return(
    request: Request,
    return_id: int,
    data: SupplierReturnShip,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Mark return as shipped"""
    result = SupplierReturnService.ship_return(db, return_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Return not found or invalid status")
    return {"status": "shipped", "return_id": return_id}


@router.post("/returns/{return_id}/confirm-receipt")
@limiter.limit("30/minute")
def confirm_supplier_receipt(
    request: Request,
    return_id: int,
    data: SupplierReturnConfirmReceipt,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Confirm supplier received the returned goods"""
    result = SupplierReturnService.confirm_supplier_receipt(db, return_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Return not found or invalid status")
    return {"status": "received_by_supplier", "return_id": return_id}


# =============================================================================
# SUPPLIER CREDIT NOTES ENDPOINTS
# =============================================================================

@router.post("/credit-notes", response_model=SupplierCreditNoteResponse)
@limiter.limit("30/minute")
def create_credit_note(
    request: Request,
    data: SupplierCreditNoteCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Create a supplier credit note"""
    return SupplierCreditNoteService.create_credit_note(db, data, current_user.id)


@router.get("/credit-notes", response_model=List[SupplierCreditNoteResponse])
@limiter.limit("60/minute")
def list_credit_notes(
    request: Request,
    venue_id: int,
    supplier_id: Optional[int] = None,
    status: Optional[CreditNoteStatus] = None,
    with_balance_only: bool = False,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List supplier credit notes with filters"""
    return SupplierCreditNoteService.get_credit_notes(
        db, venue_id, supplier_id, status, with_balance_only, skip, limit
    )


@router.post("/credit-notes/{credit_note_id}/apply", response_model=CreditNoteApplicationResponse)
@limiter.limit("30/minute")
def apply_credit_note(
    request: Request,
    credit_note_id: int,
    data: CreditNoteApplicationCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Apply credit note to an invoice or payment"""
    data.credit_note_id = credit_note_id
    try:
        return SupplierCreditNoteService.apply_credit(db, data, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# PO AMENDMENTS ENDPOINTS
# =============================================================================

@router.post("/amendments", response_model=PurchaseOrderAmendmentResponse)
@limiter.limit("30/minute")
def create_amendment(
    request: Request,
    data: PurchaseOrderAmendmentCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Create a PO amendment request"""
    try:
        return PurchaseOrderAmendmentService.create_amendment(db, data, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/amendments/{amendment_id}/approve")
@limiter.limit("30/minute")
def approve_amendment(
    request: Request,
    amendment_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Approve a PO amendment"""
    result = PurchaseOrderAmendmentService.approve_amendment(db, amendment_id, current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="Amendment not found")
    return {"status": "approved", "amendment_id": amendment_id}


@router.post("/amendments/{amendment_id}/apply")
@limiter.limit("30/minute")
def apply_amendment(
    request: Request,
    amendment_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Apply an approved amendment to the PO"""
    try:
        result = PurchaseOrderAmendmentService.apply_amendment(db, amendment_id, current_user.id)
        return {"status": "applied", "amendment_id": amendment_id, "new_total": result.new_total}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/purchase-orders/{po_id}/history", response_model=List[POVersionHistoryResponse])
@limiter.limit("60/minute")
def get_po_version_history(
    request: Request,
    po_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get version history for a purchase order"""
    return PurchaseOrderAmendmentService.get_version_history(db, po_id)


# =============================================================================
# BLANKET PURCHASE ORDERS ENDPOINTS
# =============================================================================

@router.post("/blanket-orders", response_model=BlanketPurchaseOrderResponse)
@limiter.limit("30/minute")
def create_blanket_order(
    request: Request,
    data: BlanketPurchaseOrderCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Create a blanket/standing purchase order"""
    return BlanketPurchaseOrderService.create_blanket_order(db, data, current_user.id)


@router.get("/blanket-orders", response_model=List[BlanketPurchaseOrderResponse])
@limiter.limit("60/minute")
def list_blanket_orders(
    request: Request,
    venue_id: int,
    supplier_id: Optional[int] = None,
    status: Optional[BlanketOrderStatus] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List blanket purchase orders"""
    from app.models.purchase_order_advanced import BlanketPurchaseOrder
    query = db.query(BlanketPurchaseOrder).filter(BlanketPurchaseOrder.venue_id == venue_id)
    if supplier_id:
        query = query.filter(BlanketPurchaseOrder.supplier_id == supplier_id)
    if status:
        query = query.filter(BlanketPurchaseOrder.status == status)
    return query.order_by(BlanketPurchaseOrder.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/blanket-orders/{blanket_id}", response_model=BlanketPurchaseOrderResponse)
@limiter.limit("60/minute")
def get_blanket_order(
    request: Request,
    blanket_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get a specific blanket order"""
    from app.models.purchase_order_advanced import BlanketPurchaseOrder
    result = db.query(BlanketPurchaseOrder).filter(BlanketPurchaseOrder.id == blanket_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Blanket order not found")
    return result


@router.post("/blanket-orders/{blanket_id}/activate")
@limiter.limit("30/minute")
def activate_blanket_order(
    request: Request,
    blanket_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Activate a blanket order"""
    from app.models.purchase_order_advanced import BlanketPurchaseOrder
    blanket = db.query(BlanketPurchaseOrder).filter(BlanketPurchaseOrder.id == blanket_id).first()
    if not blanket:
        raise HTTPException(status_code=404, detail="Blanket order not found")
    blanket.status = BlanketOrderStatus.ACTIVE
    blanket.approved_by = current_user.id
    from datetime import datetime, timezone
    blanket.approved_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "active", "blanket_id": blanket_id}


@router.post("/blanket-orders/{blanket_id}/releases", response_model=BlanketReleaseResponse)
@limiter.limit("30/minute")
def create_blanket_release(
    request: Request,
    blanket_id: int,
    data: BlanketReleaseCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Create a release order against a blanket PO"""
    data.blanket_order_id = blanket_id
    try:
        return BlanketPurchaseOrderService.create_release(db, data, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/blanket-orders/releases/{release_id}/convert-to-po")
@limiter.limit("30/minute")
def convert_release_to_po(
    request: Request,
    release_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Convert a blanket order release to an actual PO"""
    try:
        po = BlanketPurchaseOrderService.convert_release_to_po(db, release_id, current_user.id)
        return {"status": "converted", "purchase_order_id": po.id, "order_number": po.order_number}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# PURCHASE REQUISITIONS ENDPOINTS
# =============================================================================

@router.post("/requisitions", response_model=PurchaseRequisitionResponse)
@limiter.limit("30/minute")
def create_requisition(
    request: Request,
    data: PurchaseRequisitionCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Create a purchase requisition"""
    return PurchaseRequisitionService.create_requisition(db, data, current_user.id)


@router.get("/requisitions", response_model=List[PurchaseRequisitionResponse])
@limiter.limit("60/minute")
def list_requisitions(
    request: Request,
    venue_id: int,
    status: Optional[RequisitionStatus] = None,
    requested_by: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List purchase requisitions"""
    from app.models.purchase_order_advanced import PurchaseRequisition
    query = db.query(PurchaseRequisition).filter(PurchaseRequisition.venue_id == venue_id)
    if status:
        query = query.filter(PurchaseRequisition.status == status)
    if requested_by:
        query = query.filter(PurchaseRequisition.requested_by == requested_by)
    return query.order_by(PurchaseRequisition.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/requisitions/{requisition_id}", response_model=PurchaseRequisitionResponse)
@limiter.limit("60/minute")
def get_requisition(
    request: Request,
    requisition_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get a specific requisition"""
    from app.models.purchase_order_advanced import PurchaseRequisition
    result = db.query(PurchaseRequisition).filter(PurchaseRequisition.id == requisition_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Requisition not found")
    return result


@router.post("/requisitions/{requisition_id}/submit")
@limiter.limit("30/minute")
def submit_requisition(
    request: Request,
    requisition_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Submit requisition for approval"""
    result = PurchaseRequisitionService.submit_requisition(db, requisition_id)
    if not result:
        raise HTTPException(status_code=404, detail="Requisition not found")
    return {"status": "submitted", "requisition_id": requisition_id}


@router.post("/requisitions/{requisition_id}/approve")
@limiter.limit("30/minute")
def approve_requisition(
    request: Request,
    requisition_id: int,
    action: RequisitionApprovalAction,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Approve or reject a requisition"""
    if action.action == "approve":
        result = PurchaseRequisitionService.approve_requisition(db, requisition_id, current_user.id, action.comments)
        return {"status": "approved", "requisition_id": requisition_id}
    else:
        from app.models.purchase_order_advanced import PurchaseRequisition
        req = db.query(PurchaseRequisition).filter(PurchaseRequisition.id == requisition_id).first()
        if req:
            req.status = RequisitionStatus.REJECTED
            req.internal_notes = action.comments
            db.commit()
        return {"status": "rejected", "requisition_id": requisition_id}


@router.post("/requisitions/{requisition_id}/convert-to-po")
@limiter.limit("30/minute")
def convert_requisition_to_po(
    request: Request,
    requisition_id: int,
    data: RequisitionToPOConvert,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Convert approved requisition to purchase order"""
    data.requisition_id = requisition_id
    try:
        po = PurchaseRequisitionService.convert_to_po(db, data, current_user.id)
        return {"status": "converted", "purchase_order_id": po.id, "order_number": po.order_number}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# LANDED COST ENDPOINTS
# =============================================================================

@router.post("/landed-costs", response_model=PurchaseOrderLandedCostResponse)
@limiter.limit("30/minute")
def create_landed_cost(
    request: Request,
    data: PurchaseOrderLandedCostCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Create a landed cost record for a PO"""
    return LandedCostService.create_landed_cost(db, data, current_user.id)


@router.get("/landed-costs/{landed_cost_id}", response_model=PurchaseOrderLandedCostResponse)
@limiter.limit("60/minute")
def get_landed_cost(
    request: Request,
    landed_cost_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get a landed cost record"""
    from app.models.purchase_order_advanced import PurchaseOrderLandedCost
    result = db.query(PurchaseOrderLandedCost).filter(PurchaseOrderLandedCost.id == landed_cost_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Landed cost record not found")
    return result


@router.post("/landed-costs/{landed_cost_id}/calculate")
@limiter.limit("30/minute")
def calculate_landed_cost(
    request: Request,
    landed_cost_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Calculate and allocate landed costs to items"""
    try:
        result = LandedCostService.calculate_allocations(db, landed_cost_id, current_user.id)
        return {"status": "calculated", "landed_cost_id": landed_cost_id, "average_increase": result.average_cost_increase_pct}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/landed-costs/{landed_cost_id}/apply")
@limiter.limit("30/minute")
def apply_landed_cost(
    request: Request,
    landed_cost_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Apply landed costs to inventory"""
    try:
        result = LandedCostService.apply_to_inventory(db, landed_cost_id, current_user.id)
        return {"status": "applied", "landed_cost_id": landed_cost_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# FINANCIAL INTEGRATION ENDPOINTS
# =============================================================================

@router.post("/payments", response_model=SupplierPaymentResponse)
@limiter.limit("30/minute")
def create_supplier_payment(
    request: Request,
    data: SupplierPaymentCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Create a supplier payment"""
    return FinancialIntegrationService.create_payment(db, data, current_user.id)


@router.get("/payments", response_model=List[SupplierPaymentResponse])
@limiter.limit("60/minute")
def list_supplier_payments(
    request: Request,
    venue_id: int,
    supplier_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List supplier payments"""
    from app.models.purchase_order_advanced import SupplierPayment
    query = db.query(SupplierPayment).filter(SupplierPayment.venue_id == venue_id)
    if supplier_id:
        query = query.filter(SupplierPayment.supplier_id == supplier_id)
    if status:
        query = query.filter(SupplierPayment.status == status)
    return query.order_by(SupplierPayment.payment_date.desc()).offset(skip).limit(limit).all()


@router.get("/supplier-balances/{supplier_id}", response_model=SupplierAccountBalanceResponse)
@limiter.limit("60/minute")
def get_supplier_balance(
    request: Request,
    supplier_id: int,
    venue_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get supplier account balance and aging"""
    balance = FinancialIntegrationService.update_supplier_balance(db, venue_id, supplier_id)
    return balance


@router.get("/aging-report", response_model=InvoiceAgingSnapshotResponse)
@limiter.limit("60/minute")
def get_aging_report(
    request: Request,
    venue_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get or create current aging snapshot"""
    return FinancialIntegrationService.create_aging_snapshot(db, venue_id)


@router.post("/payment-terms", response_model=PaymentTermsConfigResponse)
@limiter.limit("30/minute")
def create_payment_terms(
    request: Request,
    data: PaymentTermsConfigCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Create payment terms configuration"""
    from app.models.purchase_order_advanced import PaymentTermsConfig
    terms = PaymentTermsConfig(
        venue_id=data.venue_id,
        name=data.name,
        code=data.code,
        due_days=data.due_days,
        due_from=data.due_from,
        discount_days=data.discount_days,
        discount_percent=data.discount_percent,
        late_fee_percent=data.late_fee_percent,
        late_fee_grace_days=data.late_fee_grace_days,
        is_default=data.is_default
    )
    db.add(terms)
    db.commit()
    db.refresh(terms)
    return terms


@router.get("/payment-terms", response_model=List[PaymentTermsConfigResponse])
@limiter.limit("60/minute")
def list_payment_terms(
    request: Request,
    venue_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List payment terms configurations"""
    from app.models.purchase_order_advanced import PaymentTermsConfig
    return db.query(PaymentTermsConfig).filter(
        PaymentTermsConfig.venue_id == venue_id,
        PaymentTermsConfig.is_active == True
    ).all()


# =============================================================================
# QUALITY CONTROL ENDPOINTS
# =============================================================================

@router.post("/qc/checklists", response_model=QualityControlChecklistResponse)
@limiter.limit("30/minute")
def create_qc_checklist(
    request: Request,
    data: QualityControlChecklistCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Create a QC checklist"""
    return QualityControlService.create_checklist(db, data)


@router.get("/qc/checklists", response_model=List[QualityControlChecklistResponse])
@limiter.limit("60/minute")
def list_qc_checklists(
    request: Request,
    venue_id: int,
    category: Optional[str] = None,
    supplier_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List QC checklists"""
    from app.models.purchase_order_advanced import QualityControlChecklist
    query = db.query(QualityControlChecklist).filter(
        QualityControlChecklist.venue_id == venue_id,
        QualityControlChecklist.is_active == True
    )
    if category:
        query = query.filter(QualityControlChecklist.applies_to_category == category)
    if supplier_id:
        query = query.filter(QualityControlChecklist.applies_to_supplier_id == supplier_id)
    return query.all()


@router.post("/qc/inspections", response_model=QualityControlInspectionResponse)
@limiter.limit("30/minute")
def create_qc_inspection(
    request: Request,
    data: QualityControlInspectionCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Create a QC inspection"""
    return QualityControlService.create_inspection(db, data, current_user.id)


@router.get("/qc/inspections", response_model=List[QualityControlInspectionResponse])
@limiter.limit("60/minute")
def list_qc_inspections(
    request: Request,
    venue_id: int,
    grn_id: Optional[int] = None,
    status: Optional[QCStatus] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List QC inspections"""
    from app.models.purchase_order_advanced import QualityControlInspection
    query = db.query(QualityControlInspection).filter(QualityControlInspection.venue_id == venue_id)
    if grn_id:
        query = query.filter(QualityControlInspection.grn_id == grn_id)
    if status:
        query = query.filter(QualityControlInspection.status == status)
    return query.order_by(QualityControlInspection.created_at.desc()).offset(skip).limit(limit).all()


@router.put("/qc/inspections/{inspection_id}", response_model=QualityControlInspectionResponse)
@limiter.limit("30/minute")
def update_qc_inspection(
    request: Request,
    inspection_id: int,
    data: QualityControlInspectionUpdate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Update/complete a QC inspection"""
    try:
        return QualityControlService.complete_inspection(db, inspection_id, data, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/qc/issues", response_model=QualityIssueResponse)
@limiter.limit("30/minute")
def create_quality_issue(
    request: Request,
    data: QualityIssueCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Create a quality issue"""
    return QualityControlService.create_quality_issue(db, data, current_user.id)


@router.get("/qc/issues", response_model=List[QualityIssueResponse])
@limiter.limit("60/minute")
def list_quality_issues(
    request: Request,
    venue_id: int,
    supplier_id: Optional[int] = None,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List quality issues"""
    from app.models.purchase_order_advanced import QualityIssue
    query = db.query(QualityIssue).filter(QualityIssue.venue_id == venue_id)
    if supplier_id:
        query = query.filter(QualityIssue.supplier_id == supplier_id)
    if status:
        query = query.filter(QualityIssue.status == status)
    if severity:
        query = query.filter(QualityIssue.severity == severity)
    return query.order_by(QualityIssue.created_at.desc()).offset(skip).limit(limit).all()


@router.put("/qc/issues/{issue_id}", response_model=QualityIssueResponse)
@limiter.limit("30/minute")
def update_quality_issue(
    request: Request,
    issue_id: int,
    data: QualityIssueUpdate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Update a quality issue"""
    from app.models.purchase_order_advanced import QualityIssue
    issue = db.query(QualityIssue).filter(QualityIssue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Quality issue not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(issue, field, value)

    if data.status == "resolved" and not issue.resolved_by:
        issue.resolved_by = current_user.id
        issue.resolution_date = date.today()

    db.commit()
    db.refresh(issue)
    return issue


# =============================================================================
# STOCK REORDER ENDPOINTS
# =============================================================================

@router.post("/reorder-configs", response_model=StockReorderConfigResponse)
@limiter.limit("30/minute")
def create_reorder_config(
    request: Request,
    data: StockReorderConfigCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Create stock reorder configuration"""
    return StockReorderService.create_reorder_config(db, data)


@router.get("/reorder-configs", response_model=List[StockReorderConfigResponse])
@limiter.limit("60/minute")
def list_reorder_configs(
    request: Request,
    venue_id: int,
    stock_item_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List stock reorder configurations"""
    from app.models.purchase_order_advanced import StockReorderConfig
    query = db.query(StockReorderConfig).filter(
        StockReorderConfig.venue_id == venue_id,
        StockReorderConfig.is_active == True
    )
    if stock_item_id:
        query = query.filter(StockReorderConfig.stock_item_id == stock_item_id)
    return query.all()


@router.put("/reorder-configs/{config_id}", response_model=StockReorderConfigResponse)
@limiter.limit("30/minute")
def update_reorder_config(
    request: Request,
    config_id: int,
    data: StockReorderConfigUpdate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Update stock reorder configuration"""
    from app.models.purchase_order_advanced import StockReorderConfig
    config = db.query(StockReorderConfig).filter(StockReorderConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Reorder config not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(config, field, value)

    db.commit()
    db.refresh(config)
    return config


@router.post("/reorder-check")
@limiter.limit("30/minute")
def check_reorder_levels(
    request: Request,
    venue_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Check all items against reorder levels and generate alerts"""
    alerts = StockReorderService.check_reorder_levels(db, venue_id)
    return {"alerts_created": len(alerts), "alerts": [a.id for a in alerts]}


@router.get("/reorder-alerts", response_model=List[ReorderAlertResponse])
@limiter.limit("60/minute")
def list_reorder_alerts(
    request: Request,
    venue_id: int,
    priority: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List active reorder alerts"""
    from app.models.purchase_order_advanced import ReorderAlert
    query = db.query(ReorderAlert).filter(
        ReorderAlert.venue_id == venue_id,
        ReorderAlert.status == "active"
    )
    if priority:
        query = query.filter(ReorderAlert.priority == priority)
    return query.order_by(ReorderAlert.priority.desc(), ReorderAlert.created_at.desc()).all()


@router.post("/reorder-alerts/{alert_id}/acknowledge")
@limiter.limit("30/minute")
def acknowledge_reorder_alert(
    request: Request,
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Acknowledge a reorder alert"""
    from app.models.purchase_order_advanced import ReorderAlert
    from datetime import datetime
    alert = db.query(ReorderAlert).filter(ReorderAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = "acknowledged"
    alert.acknowledged_by = current_user.id
    alert.acknowledged_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "acknowledged", "alert_id": alert_id}


# =============================================================================
# PARTIAL DELIVERY ENDPOINTS
# =============================================================================

@router.post("/delivery-schedules", response_model=PartialDeliveryScheduleResponse)
@limiter.limit("30/minute")
def create_delivery_schedule(
    request: Request,
    data: PartialDeliveryScheduleCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Create a partial delivery schedule"""
    return PartialDeliveryService.create_delivery_schedule(db, data)


@router.get("/delivery-schedules", response_model=List[PartialDeliveryScheduleResponse])
@limiter.limit("60/minute")
def list_delivery_schedules(
    request: Request,
    purchase_order_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List delivery schedules for a PO"""
    from app.models.purchase_order_advanced import PartialDeliverySchedule
    return db.query(PartialDeliverySchedule).filter(
        PartialDeliverySchedule.purchase_order_id == purchase_order_id
    ).order_by(PartialDeliverySchedule.delivery_number).all()


@router.post("/backorders", response_model=BackorderTrackingResponse)
@limiter.limit("30/minute")
def create_backorder(
    request: Request,
    data: BackorderTrackingCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Create a backorder tracking record"""
    return PartialDeliveryService.create_backorder(db, data)


@router.get("/backorders", response_model=List[BackorderTrackingResponse])
@limiter.limit("60/minute")
def list_backorders(
    request: Request,
    venue_id: int,
    status: Optional[str] = None,
    purchase_order_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List backorders"""
    from app.models.purchase_order_advanced import BackorderTracking
    query = db.query(BackorderTracking).filter(BackorderTracking.venue_id == venue_id)
    if status:
        query = query.filter(BackorderTracking.status == status)
    if purchase_order_id:
        query = query.filter(BackorderTracking.purchase_order_id == purchase_order_id)
    return query.order_by(BackorderTracking.created_at.desc()).all()


@router.put("/backorders/{backorder_id}", response_model=BackorderTrackingResponse)
@limiter.limit("30/minute")
def update_backorder(
    request: Request,
    backorder_id: int,
    data: BackorderTrackingUpdate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Update a backorder"""
    try:
        return PartialDeliveryService.update_backorder(db, backorder_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# CONSOLIDATED PURCHASING ENDPOINTS
# =============================================================================

@router.post("/consolidated-orders", response_model=ConsolidatedPurchaseOrderResponse)
@limiter.limit("30/minute")
def create_consolidated_order(
    request: Request,
    data: ConsolidatedPurchaseOrderCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Create a consolidated purchase order across venues"""
    return ConsolidatedPurchasingService.create_consolidated_order(db, data, current_user.id)


@router.get("/consolidated-orders", response_model=List[ConsolidatedPurchaseOrderResponse])
@limiter.limit("60/minute")
def list_consolidated_orders(
    request: Request,
    tenant_id: int,
    status: Optional[ConsolidatedOrderStatus] = None,
    supplier_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List consolidated orders"""
    from app.models.purchase_order_advanced import ConsolidatedPurchaseOrder
    query = db.query(ConsolidatedPurchaseOrder).filter(ConsolidatedPurchaseOrder.tenant_id == tenant_id)
    if status:
        query = query.filter(ConsolidatedPurchaseOrder.status == status)
    if supplier_id:
        query = query.filter(ConsolidatedPurchaseOrder.supplier_id == supplier_id)
    return query.order_by(ConsolidatedPurchaseOrder.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/consolidated-orders/{consolidated_id}", response_model=ConsolidatedPurchaseOrderResponse)
@limiter.limit("60/minute")
def get_consolidated_order(
    request: Request,
    consolidated_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get a consolidated order"""
    from app.models.purchase_order_advanced import ConsolidatedPurchaseOrder
    result = db.query(ConsolidatedPurchaseOrder).filter(
        ConsolidatedPurchaseOrder.id == consolidated_id
    ).first()
    if not result:
        raise HTTPException(status_code=404, detail="Consolidated order not found")
    return result


@router.post("/consolidated-orders/{consolidated_id}/submit")
@limiter.limit("30/minute")
def submit_consolidated_order(
    request: Request,
    consolidated_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Submit consolidated order to supplier"""
    from app.models.purchase_order_advanced import ConsolidatedPurchaseOrder
    from datetime import datetime
    consolidated = db.query(ConsolidatedPurchaseOrder).filter(
        ConsolidatedPurchaseOrder.id == consolidated_id
    ).first()
    if not consolidated:
        raise HTTPException(status_code=404, detail="Consolidated order not found")

    consolidated.status = ConsolidatedOrderStatus.ORDERED
    consolidated.order_date = datetime.now(timezone.utc)
    db.commit()
    return {"status": "ordered", "consolidated_id": consolidated_id}


@router.post("/consolidated-orders/{consolidated_id}/distribute")
@limiter.limit("30/minute")
def distribute_consolidated_order(
    request: Request,
    consolidated_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Distribute consolidated order to individual venue POs"""
    try:
        pos = ConsolidatedPurchasingService.distribute_to_venues(db, consolidated_id, current_user.id)
        return {
            "status": "distributing",
            "consolidated_id": consolidated_id,
            "purchase_orders_created": [{"id": po.id, "order_number": po.order_number} for po in pos]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# DEBIT NOTE ENDPOINTS
# =============================================================================

@router.post("/debit-notes", response_model=SupplierDebitNoteResponse)
@limiter.limit("30/minute")
def create_debit_note(
    request: Request,
    data: SupplierDebitNoteCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Create a supplier debit note"""
    from app.models.purchase_order_advanced import SupplierDebitNote

    # Generate number
    prefix = f"DN-{data.venue_id}-{date.today().strftime('%Y%m%d')}"
    count = db.query(SupplierDebitNote).filter(
        SupplierDebitNote.debit_note_number.like(f"{prefix}%")
    ).count()
    debit_note_number = f"{prefix}-{count + 1:04d}"

    debit_note = SupplierDebitNote(
        venue_id=data.venue_id,
        supplier_id=data.supplier_id,
        debit_note_number=debit_note_number,
        invoice_id=data.invoice_id,
        purchase_order_id=data.purchase_order_id,
        debit_date=data.debit_date,
        subtotal=data.subtotal,
        tax_amount=data.tax_amount,
        total_amount=data.total_amount,
        reason=data.reason,
        document_url=data.document_url,
        created_by=current_user.id,
        status="draft"
    )
    db.add(debit_note)
    db.commit()
    db.refresh(debit_note)
    return debit_note


@router.get("/debit-notes", response_model=List[SupplierDebitNoteResponse])
@limiter.limit("60/minute")
def list_debit_notes(
    request: Request,
    venue_id: int,
    supplier_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List supplier debit notes"""
    from app.models.purchase_order_advanced import SupplierDebitNote
    query = db.query(SupplierDebitNote).filter(SupplierDebitNote.venue_id == venue_id)
    if supplier_id:
        query = query.filter(SupplierDebitNote.supplier_id == supplier_id)
    if status:
        query = query.filter(SupplierDebitNote.status == status)
    return query.order_by(SupplierDebitNote.created_at.desc()).offset(skip).limit(limit).all()

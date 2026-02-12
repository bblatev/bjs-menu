"""Advanced Purchase Order schemas - Supplier Returns, Credit Notes, Amendments,
Blanket Orders, Requisitions, Landed Cost, Financial, Consolidated, QC,
Reorder, Partial Delivery, and Debit Notes."""

from __future__ import annotations

from datetime import datetime, date
from enum import Enum
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SupplierReturnStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    SHIPPED = "shipped"
    RECEIVED = "received"
    CREDITED = "credited"
    CANCELLED = "cancelled"


class CreditNoteStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    APPLIED = "applied"
    PARTIALLY_APPLIED = "partially_applied"
    REJECTED = "rejected"


class AmendmentStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    APPLIED = "applied"
    REJECTED = "rejected"


class RequisitionStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    PARTIALLY_FULFILLED = "partially_fulfilled"
    FULFILLED = "fulfilled"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class BlanketOrderStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    EXPIRED = "expired"
    EXHAUSTED = "exhausted"
    CANCELLED = "cancelled"


class QCInspectionResult(str, Enum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    PARTIAL_PASS = "partial_pass"


class ConsolidatedOrderStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    PARTIALLY_RECEIVED = "partially_received"
    RECEIVED = "received"
    CANCELLED = "cancelled"


# ===========================================================================
# SUPPLIER RETURNS
# ===========================================================================

class SupplierReturnLineCreate(BaseModel):
    """Line item for a supplier return."""
    product_id: int
    quantity: float = Field(..., gt=0)
    reason: str
    unit_cost: Optional[float] = None


class SupplierReturnCreate(BaseModel):
    """Create a supplier return."""
    supplier_id: int
    venue_id: int
    purchase_order_id: Optional[int] = None
    return_reason: str
    notes: Optional[str] = None
    lines: List[SupplierReturnLineCreate] = []


class SupplierReturnUpdate(BaseModel):
    """Update a supplier return."""
    status: Optional[SupplierReturnStatus] = None
    return_reason: Optional[str] = None
    notes: Optional[str] = None
    shipped_at: Optional[datetime] = None
    tracking_number: Optional[str] = None


class SupplierReturnShip(BaseModel):
    """Ship a supplier return."""
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    shipped_at: Optional[datetime] = None
    notes: Optional[str] = None


class SupplierReturnConfirmReceipt(BaseModel):
    """Confirm supplier received the returned goods."""
    received_at: Optional[datetime] = None
    received_by_name: Optional[str] = None
    notes: Optional[str] = None
    create_credit_note: bool = False


class SupplierReturnLineResponse(BaseModel):
    """Supplier return line response."""
    id: int
    supplier_return_id: int
    product_id: int
    quantity: float
    reason: str
    unit_cost: Optional[float] = None

    model_config = {"from_attributes": True}


class SupplierReturnResponse(BaseModel):
    """Supplier return response."""
    id: int
    supplier_id: int
    venue_id: int
    purchase_order_id: Optional[int] = None
    status: SupplierReturnStatus
    return_reason: str
    notes: Optional[str] = None
    reference_number: Optional[str] = None
    total_amount: float = 0.0
    shipped_at: Optional[datetime] = None
    tracking_number: Optional[str] = None
    received_by_supplier_at: Optional[datetime] = None
    credit_note_id: Optional[int] = None
    lines: List[SupplierReturnLineResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ===========================================================================
# SUPPLIER CREDIT NOTES
# ===========================================================================

class SupplierCreditNoteLineCreate(BaseModel):
    """Line item for a supplier credit note."""
    product_id: Optional[int] = None
    description: str
    quantity: float = Field(..., gt=0)
    unit_amount: float


class SupplierCreditNoteCreate(BaseModel):
    """Create a supplier credit note."""
    venue_id: int
    supplier_id: int
    supplier_return_id: Optional[int] = None
    invoice_id: Optional[int] = None
    reason: str
    notes: Optional[str] = None
    lines: List[SupplierCreditNoteLineCreate] = []


class SupplierCreditNoteUpdate(BaseModel):
    """Update a supplier credit note."""
    status: Optional[CreditNoteStatus] = None
    reason: Optional[str] = None
    notes: Optional[str] = None


class SupplierCreditNoteLineResponse(BaseModel):
    """Supplier credit note line response."""
    id: int
    credit_note_id: int
    product_id: Optional[int] = None
    description: str
    quantity: float
    unit_amount: float
    line_total: float

    model_config = {"from_attributes": True}


class SupplierCreditNoteResponse(BaseModel):
    """Supplier credit note response."""
    id: int
    venue_id: int
    supplier_id: int
    supplier_return_id: Optional[int] = None
    invoice_id: Optional[int] = None
    status: CreditNoteStatus
    credit_note_number: Optional[str] = None
    reason: str
    notes: Optional[str] = None
    total_amount: float = 0.0
    amount_applied: float = 0.0
    balance_remaining: float = 0.0
    lines: List[SupplierCreditNoteLineResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CreditNoteApplicationCreate(BaseModel):
    """Apply a credit note to an invoice or payment."""
    credit_note_id: Optional[int] = None
    invoice_id: Optional[int] = None
    purchase_order_id: Optional[int] = None
    amount: float = Field(..., gt=0)
    notes: Optional[str] = None


class CreditNoteApplicationResponse(BaseModel):
    """Credit note application response."""
    id: int
    credit_note_id: int
    invoice_id: Optional[int] = None
    purchase_order_id: Optional[int] = None
    amount: float
    applied_at: datetime
    applied_by: Optional[int] = None
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


# ===========================================================================
# PO AMENDMENTS
# ===========================================================================

class AmendmentLineChange(BaseModel):
    """A single line-level change in an amendment."""
    line_id: Optional[int] = None
    product_id: Optional[int] = None
    action: str = "update"  # add, update, remove
    new_quantity: Optional[float] = None
    new_unit_price: Optional[float] = None
    reason: Optional[str] = None


class PurchaseOrderAmendmentCreate(BaseModel):
    """Create a PO amendment."""
    purchase_order_id: int
    reason: str
    new_expected_date: Optional[date] = None
    line_changes: List[AmendmentLineChange] = []
    notes: Optional[str] = None


class PurchaseOrderAmendmentResponse(BaseModel):
    """PO amendment response."""
    id: int
    purchase_order_id: int
    amendment_number: Optional[str] = None
    version: int = 1
    status: AmendmentStatus
    reason: str
    new_expected_date: Optional[date] = None
    old_total: Optional[float] = None
    new_total: Optional[float] = None
    line_changes: List[Dict[str, Any]] = []
    notes: Optional[str] = None
    requested_by: Optional[int] = None
    approved_by: Optional[int] = None
    applied_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class POVersionHistoryResponse(BaseModel):
    """PO version history entry."""
    id: int
    purchase_order_id: int
    version: int
    amendment_id: Optional[int] = None
    snapshot: Optional[Dict[str, Any]] = None
    changed_by: Optional[int] = None
    changed_at: datetime
    change_summary: Optional[str] = None

    model_config = {"from_attributes": True}


# ===========================================================================
# BLANKET PURCHASE ORDERS
# ===========================================================================

class BlanketPurchaseOrderLineCreate(BaseModel):
    """Line item for a blanket purchase order."""
    product_id: int
    agreed_unit_price: float
    min_quantity: Optional[float] = None
    max_quantity: Optional[float] = None


class BlanketPurchaseOrderCreate(BaseModel):
    """Create a blanket purchase order."""
    venue_id: int
    supplier_id: int
    start_date: date
    end_date: date
    total_budget: Optional[float] = None
    payment_terms: Optional[str] = None
    notes: Optional[str] = None
    lines: List[BlanketPurchaseOrderLineCreate] = []


class BlanketPurchaseOrderUpdate(BaseModel):
    """Update a blanket purchase order."""
    end_date: Optional[date] = None
    total_budget: Optional[float] = None
    payment_terms: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[BlanketOrderStatus] = None


class BlanketPurchaseOrderLineResponse(BaseModel):
    """Blanket purchase order line response."""
    id: int
    blanket_order_id: int
    product_id: int
    agreed_unit_price: float
    min_quantity: Optional[float] = None
    max_quantity: Optional[float] = None
    quantity_released: float = 0.0

    model_config = {"from_attributes": True}


class BlanketPurchaseOrderResponse(BaseModel):
    """Blanket purchase order response."""
    id: int
    venue_id: int
    supplier_id: int
    status: BlanketOrderStatus
    reference_number: Optional[str] = None
    start_date: date
    end_date: date
    total_budget: Optional[float] = None
    total_spent: float = 0.0
    payment_terms: Optional[str] = None
    notes: Optional[str] = None
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    lines: List[BlanketPurchaseOrderLineResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BlanketReleaseLineCreate(BaseModel):
    """Line item for a blanket release."""
    product_id: int
    quantity: float = Field(..., gt=0)
    unit_price: Optional[float] = None


class BlanketReleaseCreate(BaseModel):
    """Create a release against a blanket order."""
    blanket_order_id: Optional[int] = None
    delivery_date: Optional[date] = None
    notes: Optional[str] = None
    lines: List[BlanketReleaseLineCreate] = []


class BlanketReleaseResponse(BaseModel):
    """Blanket release response."""
    id: int
    blanket_order_id: int
    release_number: Optional[str] = None
    purchase_order_id: Optional[int] = None
    status: str = "draft"
    delivery_date: Optional[date] = None
    total_amount: float = 0.0
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ===========================================================================
# PURCHASE REQUISITIONS
# ===========================================================================

class PurchaseRequisitionLineCreate(BaseModel):
    """Line item for a purchase requisition."""
    product_id: int
    quantity_requested: float = Field(..., gt=0)
    preferred_supplier_id: Optional[int] = None
    estimated_unit_cost: Optional[float] = None
    notes: Optional[str] = None


class PurchaseRequisitionCreate(BaseModel):
    """Create a purchase requisition."""
    venue_id: int
    needed_by_date: Optional[date] = None
    priority: str = "normal"
    justification: Optional[str] = None
    notes: Optional[str] = None
    lines: List[PurchaseRequisitionLineCreate] = []


class PurchaseRequisitionUpdate(BaseModel):
    """Update a purchase requisition."""
    needed_by_date: Optional[date] = None
    priority: Optional[str] = None
    justification: Optional[str] = None
    notes: Optional[str] = None
    internal_notes: Optional[str] = None


class PurchaseRequisitionLineResponse(BaseModel):
    """Purchase requisition line response."""
    id: int
    requisition_id: int
    product_id: int
    quantity_requested: float
    quantity_approved: Optional[float] = None
    quantity_fulfilled: float = 0.0
    preferred_supplier_id: Optional[int] = None
    estimated_unit_cost: Optional[float] = None
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class PurchaseRequisitionResponse(BaseModel):
    """Purchase requisition response."""
    id: int
    venue_id: int
    requested_by: Optional[int] = None
    approved_by: Optional[int] = None
    status: RequisitionStatus
    requisition_number: Optional[str] = None
    needed_by_date: Optional[date] = None
    priority: str
    justification: Optional[str] = None
    notes: Optional[str] = None
    internal_notes: Optional[str] = None
    approved_at: Optional[datetime] = None
    fulfilled_at: Optional[datetime] = None
    lines: List[PurchaseRequisitionLineResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RequisitionApprovalAction(BaseModel):
    """Approve or reject a requisition."""
    action: str = "approve"  # approve or reject
    comments: Optional[str] = None


class RequisitionToPOConvert(BaseModel):
    """Convert an approved requisition to a purchase order."""
    requisition_id: Optional[int] = None
    supplier_id: int
    expected_delivery_date: Optional[date] = None
    notes: Optional[str] = None


# ===========================================================================
# LANDED COST
# ===========================================================================

class LandedCostComponentCreate(BaseModel):
    """A single cost component (freight, duty, etc.)."""
    cost_type: str  # freight, customs_duty, insurance, handling, etc.
    description: Optional[str] = None
    amount: float = Field(..., ge=0)
    allocation_method: str = "by_value"  # by_value, by_weight, by_quantity


class PurchaseOrderLandedCostCreate(BaseModel):
    """Create a landed cost record for a PO."""
    purchase_order_id: int
    venue_id: int
    currency: str = "USD"
    components: List[LandedCostComponentCreate] = []
    notes: Optional[str] = None


class PurchaseOrderLandedCostUpdate(BaseModel):
    """Update a landed cost record."""
    currency: Optional[str] = None
    components: Optional[List[LandedCostComponentCreate]] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class LandedCostComponentResponse(BaseModel):
    """Landed cost component response."""
    id: int
    landed_cost_id: int
    cost_type: str
    description: Optional[str] = None
    amount: float
    allocation_method: str

    model_config = {"from_attributes": True}


class PurchaseOrderLandedCostResponse(BaseModel):
    """Landed cost response."""
    id: int
    purchase_order_id: int
    venue_id: int
    status: str = "draft"
    currency: str = "USD"
    total_landed_cost: float = 0.0
    average_cost_increase_pct: Optional[float] = None
    components: List[LandedCostComponentResponse] = []
    notes: Optional[str] = None
    calculated_at: Optional[datetime] = None
    applied_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ===========================================================================
# FINANCIAL - Payments, Balances, Aging, Payment Terms
# ===========================================================================

class SupplierPaymentCreate(BaseModel):
    """Create a supplier payment."""
    venue_id: int
    supplier_id: int
    invoice_id: Optional[int] = None
    purchase_order_id: Optional[int] = None
    payment_method: str = "bank_transfer"
    amount: float = Field(..., gt=0)
    currency: str = "USD"
    payment_date: Optional[date] = None
    reference_number: Optional[str] = None
    notes: Optional[str] = None


class SupplierPaymentResponse(BaseModel):
    """Supplier payment response."""
    id: int
    venue_id: int
    supplier_id: int
    invoice_id: Optional[int] = None
    purchase_order_id: Optional[int] = None
    payment_number: Optional[str] = None
    payment_method: str
    amount: float
    currency: str = "USD"
    payment_date: Optional[date] = None
    status: str = "pending"
    reference_number: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SupplierAccountBalanceResponse(BaseModel):
    """Supplier account balance and aging summary."""
    id: int
    venue_id: int
    supplier_id: int
    total_outstanding: float = 0.0
    total_overdue: float = 0.0
    current_balance: float = 0.0
    aging_0_30: float = 0.0
    aging_31_60: float = 0.0
    aging_61_90: float = 0.0
    aging_over_90: float = 0.0
    last_payment_date: Optional[date] = None
    last_payment_amount: Optional[float] = None
    updated_at: datetime

    model_config = {"from_attributes": True}


class InvoiceAgingDetailResponse(BaseModel):
    """Individual invoice aging detail."""
    invoice_id: int
    invoice_number: Optional[str] = None
    supplier_id: int
    amount: float
    days_outstanding: int
    aging_bucket: str

    model_config = {"from_attributes": True}


class InvoiceAgingSnapshotResponse(BaseModel):
    """Invoice aging snapshot response."""
    id: int
    venue_id: int
    snapshot_date: date
    total_outstanding: float = 0.0
    total_current: float = 0.0
    total_overdue: float = 0.0
    aging_0_30: float = 0.0
    aging_31_60: float = 0.0
    aging_61_90: float = 0.0
    aging_over_90: float = 0.0
    details: List[InvoiceAgingDetailResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class PaymentTermsConfigCreate(BaseModel):
    """Create payment terms configuration."""
    venue_id: int
    name: str
    code: str
    due_days: int = 30
    due_from: str = "invoice_date"  # invoice_date, receipt_date, month_end
    discount_days: Optional[int] = None
    discount_percent: Optional[float] = None
    late_fee_percent: Optional[float] = None
    late_fee_grace_days: Optional[int] = None
    is_default: bool = False


class PaymentTermsConfigResponse(BaseModel):
    """Payment terms configuration response."""
    id: int
    venue_id: int
    name: str
    code: str
    due_days: int
    due_from: str
    discount_days: Optional[int] = None
    discount_percent: Optional[float] = None
    late_fee_percent: Optional[float] = None
    late_fee_grace_days: Optional[int] = None
    is_default: bool = False
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ===========================================================================
# CONSOLIDATED PURCHASING
# ===========================================================================

class ConsolidatedLineCreate(BaseModel):
    """Line item for a consolidated purchase order."""
    product_id: int
    venue_id: int
    quantity: float = Field(..., gt=0)
    unit_price: Optional[float] = None


class ConsolidatedPurchaseOrderCreate(BaseModel):
    """Create a consolidated purchase order across venues."""
    tenant_id: int
    supplier_id: int
    expected_delivery_date: Optional[date] = None
    notes: Optional[str] = None
    lines: List[ConsolidatedLineCreate] = []


class ConsolidatedLineResponse(BaseModel):
    """Consolidated line response."""
    id: int
    consolidated_order_id: int
    product_id: int
    venue_id: int
    quantity: float
    unit_price: Optional[float] = None
    quantity_received: float = 0.0

    model_config = {"from_attributes": True}


class ConsolidatedPurchaseOrderResponse(BaseModel):
    """Consolidated purchase order response."""
    id: int
    tenant_id: int
    supplier_id: int
    status: ConsolidatedOrderStatus
    reference_number: Optional[str] = None
    total_amount: float = 0.0
    expected_delivery_date: Optional[date] = None
    order_date: Optional[datetime] = None
    notes: Optional[str] = None
    lines: List[ConsolidatedLineResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ===========================================================================
# QUALITY CONTROL
# ===========================================================================

class QCChecklistItemCreate(BaseModel):
    """A single checklist item."""
    check_name: str
    description: Optional[str] = None
    is_required: bool = True
    check_type: str = "pass_fail"  # pass_fail, numeric, text


class QualityControlChecklistCreate(BaseModel):
    """Create a QC checklist template."""
    venue_id: int
    name: str
    applies_to_category: Optional[str] = None
    applies_to_supplier_id: Optional[int] = None
    items: List[QCChecklistItemCreate] = []


class QCChecklistItemResponse(BaseModel):
    """QC checklist item response."""
    id: int
    checklist_id: int
    check_name: str
    description: Optional[str] = None
    is_required: bool
    check_type: str

    model_config = {"from_attributes": True}


class QualityControlChecklistResponse(BaseModel):
    """QC checklist response."""
    id: int
    venue_id: int
    name: str
    applies_to_category: Optional[str] = None
    applies_to_supplier_id: Optional[int] = None
    is_active: bool = True
    items: List[QCChecklistItemResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class QCInspectionItemCreate(BaseModel):
    """A single inspection result item."""
    checklist_item_id: Optional[int] = None
    product_id: int
    quantity_inspected: float = Field(..., gt=0)
    quantity_accepted: float = 0.0
    quantity_rejected: float = 0.0
    result: Optional[str] = None
    defect_type: Optional[str] = None
    notes: Optional[str] = None


class QualityControlInspectionCreate(BaseModel):
    """Create a QC inspection."""
    venue_id: int
    purchase_order_id: Optional[int] = None
    grn_id: Optional[int] = None
    checklist_id: Optional[int] = None
    inspection_date: Optional[datetime] = None
    notes: Optional[str] = None
    items: List[QCInspectionItemCreate] = []


class QualityControlInspectionUpdate(BaseModel):
    """Update / complete a QC inspection."""
    status: Optional[str] = None
    overall_result: Optional[QCInspectionResult] = None
    overall_pass_rate: Optional[float] = None
    notes: Optional[str] = None
    items: Optional[List[QCInspectionItemCreate]] = None


class QCInspectionItemResponse(BaseModel):
    """QC inspection item response."""
    id: int
    inspection_id: int
    checklist_item_id: Optional[int] = None
    product_id: int
    quantity_inspected: float
    quantity_accepted: float
    quantity_rejected: float
    result: Optional[str] = None
    defect_type: Optional[str] = None
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class QualityControlInspectionResponse(BaseModel):
    """QC inspection response."""
    id: int
    venue_id: int
    purchase_order_id: Optional[int] = None
    grn_id: Optional[int] = None
    checklist_id: Optional[int] = None
    inspector_id: Optional[int] = None
    status: str = "pending"
    overall_result: Optional[QCInspectionResult] = None
    overall_pass_rate: Optional[float] = None
    inspection_date: Optional[datetime] = None
    notes: Optional[str] = None
    items: List[QCInspectionItemResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class QualityIssueCreate(BaseModel):
    """Create a quality issue."""
    venue_id: int
    supplier_id: int
    purchase_order_id: Optional[int] = None
    inspection_id: Optional[int] = None
    product_id: Optional[int] = None
    severity: str = "medium"  # low, medium, high, critical
    issue_type: str = "defect"
    description: str
    corrective_action: Optional[str] = None


class QualityIssueUpdate(BaseModel):
    """Update a quality issue."""
    status: Optional[str] = None
    severity: Optional[str] = None
    description: Optional[str] = None
    corrective_action: Optional[str] = None
    resolution_notes: Optional[str] = None


class QualityIssueResponse(BaseModel):
    """Quality issue response."""
    id: int
    venue_id: int
    supplier_id: int
    purchase_order_id: Optional[int] = None
    inspection_id: Optional[int] = None
    product_id: Optional[int] = None
    issue_number: Optional[str] = None
    severity: str
    issue_type: str
    status: str = "open"
    description: str
    corrective_action: Optional[str] = None
    resolution_notes: Optional[str] = None
    reported_by: Optional[int] = None
    resolved_by: Optional[int] = None
    resolution_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ===========================================================================
# STOCK REORDER
# ===========================================================================

class StockReorderConfigCreate(BaseModel):
    """Create stock reorder configuration."""
    venue_id: int
    stock_item_id: int
    supplier_id: Optional[int] = None
    reorder_point: float
    reorder_quantity: float
    max_stock_level: Optional[float] = None
    min_stock_level: Optional[float] = None
    lead_time_days: int = 7
    auto_create_po: bool = False


class StockReorderConfigUpdate(BaseModel):
    """Update stock reorder configuration."""
    reorder_point: Optional[float] = None
    reorder_quantity: Optional[float] = None
    max_stock_level: Optional[float] = None
    min_stock_level: Optional[float] = None
    lead_time_days: Optional[int] = None
    supplier_id: Optional[int] = None
    auto_create_po: Optional[bool] = None
    is_active: Optional[bool] = None


class StockReorderConfigResponse(BaseModel):
    """Stock reorder configuration response."""
    id: int
    venue_id: int
    stock_item_id: int
    supplier_id: Optional[int] = None
    reorder_point: float
    reorder_quantity: float
    max_stock_level: Optional[float] = None
    min_stock_level: Optional[float] = None
    lead_time_days: int
    auto_create_po: bool = False
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReorderAlertResponse(BaseModel):
    """Reorder alert response."""
    id: int
    venue_id: int
    stock_item_id: int
    reorder_config_id: Optional[int] = None
    current_stock: float
    reorder_point: float
    suggested_quantity: float
    priority: str = "normal"
    status: str = "active"
    acknowledged_by: Optional[int] = None
    acknowledged_at: Optional[datetime] = None
    purchase_order_id: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ===========================================================================
# PARTIAL DELIVERY & BACKORDERS
# ===========================================================================

class DeliveryScheduleLineCreate(BaseModel):
    """Line item for a delivery schedule."""
    product_id: int
    quantity: float = Field(..., gt=0)


class PartialDeliveryScheduleCreate(BaseModel):
    """Create a partial delivery schedule."""
    purchase_order_id: int
    delivery_number: int = 1
    scheduled_date: date
    notes: Optional[str] = None
    lines: List[DeliveryScheduleLineCreate] = []


class DeliveryScheduleLineResponse(BaseModel):
    """Delivery schedule line response."""
    id: int
    schedule_id: int
    product_id: int
    quantity: float
    quantity_received: float = 0.0

    model_config = {"from_attributes": True}


class PartialDeliveryScheduleResponse(BaseModel):
    """Partial delivery schedule response."""
    id: int
    purchase_order_id: int
    delivery_number: int
    scheduled_date: date
    actual_date: Optional[date] = None
    status: str = "scheduled"
    notes: Optional[str] = None
    lines: List[DeliveryScheduleLineResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BackorderTrackingCreate(BaseModel):
    """Create a backorder tracking record."""
    venue_id: int
    purchase_order_id: int
    product_id: int
    quantity_backordered: float = Field(..., gt=0)
    original_expected_date: Optional[date] = None
    revised_expected_date: Optional[date] = None
    reason: Optional[str] = None


class BackorderTrackingUpdate(BaseModel):
    """Update a backorder tracking record."""
    status: Optional[str] = None
    revised_expected_date: Optional[date] = None
    quantity_received: Optional[float] = None
    reason: Optional[str] = None
    notes: Optional[str] = None


class BackorderTrackingResponse(BaseModel):
    """Backorder tracking response."""
    id: int
    venue_id: int
    purchase_order_id: int
    product_id: int
    quantity_backordered: float
    quantity_received: float = 0.0
    status: str = "pending"
    original_expected_date: Optional[date] = None
    revised_expected_date: Optional[date] = None
    reason: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ===========================================================================
# SUPPLIER DEBIT NOTES
# ===========================================================================

class SupplierDebitNoteLineCreate(BaseModel):
    """Line item for a debit note."""
    product_id: Optional[int] = None
    description: Optional[str] = None
    quantity: float = Field(default=1, gt=0)
    unit_amount: float = 0.0


class SupplierDebitNoteCreate(BaseModel):
    """Create a supplier debit note."""
    venue_id: int
    supplier_id: int
    invoice_id: Optional[int] = None
    purchase_order_id: Optional[int] = None
    debit_date: Optional[date] = None
    subtotal: float = 0.0
    tax_amount: float = 0.0
    total_amount: float = 0.0
    reason: str
    document_url: Optional[str] = None
    lines: List[SupplierDebitNoteLineCreate] = []


class SupplierDebitNoteLineResponse(BaseModel):
    """Debit note line response."""
    id: int
    debit_note_id: int
    product_id: Optional[int] = None
    description: Optional[str] = None
    quantity: float
    unit_amount: float
    line_total: float

    model_config = {"from_attributes": True}


class SupplierDebitNoteResponse(BaseModel):
    """Supplier debit note response."""
    id: int
    venue_id: int
    supplier_id: int
    debit_note_number: Optional[str] = None
    invoice_id: Optional[int] = None
    purchase_order_id: Optional[int] = None
    debit_date: Optional[date] = None
    subtotal: float = 0.0
    tax_amount: float = 0.0
    total_amount: float = 0.0
    reason: str
    status: str = "draft"
    document_url: Optional[str] = None
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

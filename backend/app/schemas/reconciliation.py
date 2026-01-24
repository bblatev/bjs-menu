"""Schemas for reconciliation, reorder, and supplier order functionality."""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Any
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class DeltaSeverity(str, Enum):
    """Severity level of stock discrepancy."""
    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"


class OrderDraftStatus(str, Enum):
    """Status of a supplier order draft."""
    DRAFT = "draft"
    FINALIZED = "finalized"
    EXPORTED = "exported"
    SENT = "sent"
    CANCELLED = "cancelled"


# ============== Reconciliation ==============

class ReconciliationResultBase(BaseModel):
    """Base schema for reconciliation result."""
    product_id: int
    expected_qty: Decimal
    counted_qty: Decimal
    delta_qty: Decimal
    delta_value: Optional[Decimal] = None
    delta_percent: Optional[Decimal] = None
    severity: DeltaSeverity = DeltaSeverity.OK
    reason: Optional[str] = None
    expected_source: Optional[str] = None
    confidence: Optional[Decimal] = None


class ReconciliationResultCreate(ReconciliationResultBase):
    """Schema for creating a reconciliation result."""
    session_id: int


class ReconciliationResultResponse(ReconciliationResultBase):
    """Schema for reconciliation result response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    product_name: Optional[str] = None
    product_barcode: Optional[str] = None
    created_at: datetime


class ReconciliationSummary(BaseModel):
    """Summary of reconciliation for a session."""
    session_id: int
    total_products: int
    products_ok: int
    products_warning: int
    products_critical: int
    total_delta_value: Optional[Decimal] = None
    results: List[ReconciliationResultResponse]


# ============== Reorder Proposal ==============

class ReorderProposalBase(BaseModel):
    """Base schema for reorder proposal."""
    product_id: int
    supplier_id: Optional[int] = None
    current_stock: Decimal
    target_stock: Decimal
    in_transit: Decimal = Decimal("0")
    recommended_qty: Decimal
    rounded_qty: Decimal
    pack_size: int = 1
    unit_cost: Optional[Decimal] = None
    line_total: Optional[Decimal] = None
    rationale_json: Optional[str] = None
    user_qty: Optional[Decimal] = None
    included: bool = True


class ReorderProposalCreate(ReorderProposalBase):
    """Schema for creating a reorder proposal."""
    session_id: int


class ReorderProposalUpdate(BaseModel):
    """Schema for updating a reorder proposal."""
    user_qty: Optional[Decimal] = None
    included: Optional[bool] = None


class ReorderProposalResponse(ReorderProposalBase):
    """Schema for reorder proposal response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    product_name: Optional[str] = None
    product_barcode: Optional[str] = None
    supplier_name: Optional[str] = None
    created_at: datetime


class ReorderSummary(BaseModel):
    """Summary of reorder proposals for a session."""
    session_id: int
    total_products: int
    total_qty: Decimal
    total_value: Optional[Decimal] = None
    suppliers_count: int
    proposals: List[ReorderProposalResponse]


# ============== Supplier Order Draft ==============

class OrderDraftLineItem(BaseModel):
    """Line item in a supplier order draft."""
    product_id: int
    product_name: str
    barcode: Optional[str] = None
    sku: Optional[str] = None
    qty: Decimal
    pack_size: int = 1
    unit_cost: Optional[Decimal] = None
    line_total: Optional[Decimal] = None


class SupplierOrderDraftBase(BaseModel):
    """Base schema for supplier order draft."""
    supplier_id: int
    status: OrderDraftStatus = OrderDraftStatus.DRAFT
    line_count: int = 0
    total_qty: Decimal = Decimal("0")
    total_value: Optional[Decimal] = None
    requested_delivery_date: Optional[datetime] = None
    notes: Optional[str] = None


class SupplierOrderDraftCreate(SupplierOrderDraftBase):
    """Schema for creating a supplier order draft."""
    session_id: int
    payload_json: Optional[str] = None


class SupplierOrderDraftUpdate(BaseModel):
    """Schema for updating a supplier order draft."""
    status: Optional[OrderDraftStatus] = None
    requested_delivery_date: Optional[datetime] = None
    notes: Optional[str] = None


class SupplierOrderDraftResponse(SupplierOrderDraftBase):
    """Schema for supplier order draft response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    supplier_name: Optional[str] = None
    supplier_email: Optional[str] = None
    exported_csv_path: Optional[str] = None
    exported_pdf_path: Optional[str] = None
    email_sent_at: Optional[datetime] = None
    purchase_order_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class SupplierOrderDraftDetail(SupplierOrderDraftResponse):
    """Detailed supplier order draft with line items."""
    line_items: List[Any] = []  # Line items from JSON, may have variable structure


# ============== Request/Response for Actions ==============

class ReconcileRequest(BaseModel):
    """Request to run reconciliation on a session."""
    session_id: int
    expected_source: str = "pos_stock"  # pos_stock, calculated, manual
    critical_threshold_qty: Decimal = Decimal("5")
    critical_threshold_percent: Decimal = Decimal("20")
    warning_threshold_qty: Decimal = Decimal("2")
    warning_threshold_percent: Decimal = Decimal("10")


class GenerateReordersRequest(BaseModel):
    """Request to generate reorder proposals."""
    session_id: int
    coverage_days: int = 14  # How many days of stock to target
    use_par_level: bool = True  # Use par level if available
    round_to_case: bool = True  # Round up to case pack


class GenerateOrderDraftsRequest(BaseModel):
    """Request to generate supplier order drafts from proposals."""
    session_id: int
    requested_delivery_date: Optional[datetime] = None


class ExportOrderRequest(BaseModel):
    """Request to export a supplier order draft."""
    format: str = "csv"  # csv, pdf


class ExportOrderResponse(BaseModel):
    """Response from exporting an order."""
    draft_id: int
    format: str
    file_path: str
    download_url: Optional[str] = None


class EmailTemplateResponse(BaseModel):
    """Email template for a supplier order."""
    draft_id: int
    supplier_name: str
    supplier_email: Optional[str]
    subject: str
    body: str
    attachment_paths: List[str] = []

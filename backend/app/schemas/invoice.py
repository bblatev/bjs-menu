"""Invoice OCR & AP Automation schemas - Toast xtraCHEF style."""

from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field

from app.models.invoice import InvoiceStatus, InvoiceCaptureMethod


class InvoiceLineBase(BaseModel):
    """Base invoice line schema."""
    line_number: int
    product_id: Optional[int] = None
    description: str
    quantity: Decimal
    unit_price: Decimal
    total_price: Decimal
    unit_of_measure: Optional[str] = None
    gl_code_id: Optional[int] = None


class InvoiceLineCreate(InvoiceLineBase):
    """Create invoice line schema."""
    pass


class InvoiceLineResponse(BaseModel):
    """Invoice line response schema."""
    id: int
    product_id: Optional[int] = None
    description: Optional[str] = Field(default=None, alias="item_description")
    quantity: Decimal = Decimal("0")
    unit_price: Decimal = Decimal("0")
    total_price: Decimal = Field(default=Decimal("0"), alias="line_total")
    unit_of_measure: Optional[str] = None
    gl_code: Optional[str] = None
    matched_product_name: Optional[str] = None
    price_change_percent: Optional[float] = None
    is_price_flagged: bool = Field(default=False, alias="price_alert_triggered")

    model_config = {"from_attributes": True, "populate_by_name": True}


class InvoiceBase(BaseModel):
    """Base invoice schema."""
    supplier_id: int
    location_id: Optional[int] = None
    invoice_number: str
    invoice_date: date
    due_date: Optional[date] = None
    subtotal: Decimal = Decimal("0")
    tax: Decimal = Decimal("0")
    total: Decimal = Decimal("0")
    notes: Optional[str] = None


class InvoiceCreate(InvoiceBase):
    """Create invoice schema."""
    lines: List[InvoiceLineCreate] = []


class InvoiceUpdate(BaseModel):
    """Update invoice schema."""
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    subtotal: Optional[Decimal] = None
    tax: Optional[Decimal] = None
    total: Optional[Decimal] = None
    status: Optional[InvoiceStatus] = None
    notes: Optional[str] = None


class InvoiceResponse(BaseModel):
    """Invoice response schema."""
    id: int
    supplier_id: int
    location_id: Optional[int] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    subtotal: Decimal = Decimal("0")
    tax: Decimal = Field(default=Decimal("0"), alias="tax_amount")
    total: Decimal = Field(default=Decimal("0"), alias="total_amount")
    notes: Optional[str] = None
    status: InvoiceStatus
    capture_method: InvoiceCaptureMethod
    ocr_confidence: Optional[float] = None
    original_image_url: Optional[str] = Field(default=None, alias="original_image_path")
    processed_at: Optional[datetime] = Field(default=None, alias="ocr_processed_at")
    approved_by_id: Optional[int] = Field(default=None, alias="approved_by")
    approved_at: Optional[datetime] = None
    created_at: datetime
    lines: List[InvoiceLineResponse] = []

    model_config = {"from_attributes": True, "populate_by_name": True}


class InvoiceOCRRequest(BaseModel):
    """Request to process invoice image."""
    image_base64: Optional[str] = None
    image_url: Optional[str] = None
    supplier_id: Optional[int] = None


class InvoiceOCRResponse(BaseModel):
    """Response from OCR processing."""
    invoice_id: int
    confidence: float
    extracted_data: Dict[str, Any]
    needs_review: bool
    flagged_items: List[Dict[str, Any]]


# Price History & Alerts

class PriceHistoryResponse(BaseModel):
    """Price history entry."""
    id: int
    product_id: int
    supplier_id: int
    price: Decimal
    unit_of_measure: Optional[str] = None
    recorded_at: datetime
    invoice_id: Optional[int] = None

    model_config = {"from_attributes": True}


class PriceAlertResponse(BaseModel):
    """Price alert schema."""
    id: int
    product_id: Optional[int] = None
    supplier_id: Optional[int] = None
    alert_type: str
    threshold_percent: Optional[float] = None
    threshold_amount: Optional[float] = None
    max_price: Optional[float] = None
    is_active: bool = True
    last_triggered_at: Optional[datetime] = None
    trigger_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class PriceTrendResponse(BaseModel):
    """Price trend analysis."""
    product_id: int
    product_name: str
    current_price: Decimal
    avg_price_30d: Decimal
    min_price_30d: Decimal
    max_price_30d: Decimal
    trend: str  # "rising", "falling", "stable"
    price_history: List[Dict[str, Any]]


# GL Codes

class GLCodeBase(BaseModel):
    """Base GL code schema."""
    code: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None


class GLCodeCreate(GLCodeBase):
    """Create GL code schema."""
    pass


class GLCodeResponse(GLCodeBase):
    """GL code response schema."""
    id: int
    is_active: bool

    model_config = {"from_attributes": True}


# AP Approval Workflow

class APApprovalCreate(BaseModel):
    """Create AP approval workflow."""
    invoice_id: int
    approver_id: int
    notes: Optional[str] = None


class APApprovalResponse(BaseModel):
    """AP approval workflow response."""
    id: int
    invoice_id: int
    step_number: int
    approver_id: int
    approver_name: Optional[str] = None
    status: str
    notes: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class APApprovalAction(BaseModel):
    """Action on AP approval."""
    action: str = Field(..., pattern="^(approve|reject)$")
    notes: Optional[str] = None

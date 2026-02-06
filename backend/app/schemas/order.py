"""Purchase order schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict

from pydantic import BaseModel, Field, model_validator

from app.models.order import POStatus


class PurchaseOrderLineCreate(BaseModel):
    """Purchase order line creation schema."""

    product_id: int
    qty: Optional[Decimal] = Field(default=None, gt=0)
    quantity: Optional[Decimal] = Field(default=None, gt=0)
    unit_cost: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None

    @property
    def effective_qty(self) -> Decimal:
        return self.qty or self.quantity or Decimal("1")

    @property
    def effective_cost(self) -> Optional[Decimal]:
        return self.unit_cost or self.unit_price


class PurchaseOrderLineResponse(BaseModel):
    """Purchase order line response schema."""

    id: int
    po_id: int
    product_id: int
    qty: Decimal
    unit_cost: Optional[Decimal] = None

    model_config = {"from_attributes": True}


class PurchaseOrderCreate(BaseModel):
    """Purchase order creation schema."""

    supplier_id: int
    location_id: int
    lines: Optional[List[PurchaseOrderLineCreate]] = None
    items: Optional[List[PurchaseOrderLineCreate]] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def normalize_lines(self):
        """Accept both 'lines' and 'items' as the line items field."""
        if not self.lines and self.items:
            self.lines = self.items
        if not self.lines:
            self.lines = []
        return self


class PurchaseOrderResponse(BaseModel):
    """Purchase order response schema."""

    id: int
    supplier_id: int
    location_id: int
    status: POStatus
    created_at: datetime
    sent_at: Optional[datetime] = None
    received_at: Optional[datetime] = None
    created_by: Optional[int] = None
    notes: Optional[str] = None
    lines: List[PurchaseOrderLineResponse] = []

    model_config = {"from_attributes": True}


class OrderSuggestion(BaseModel):
    """Order suggestion for a product."""

    product_id: int
    product_name: str
    barcode: Optional[str] = None
    supplier_id: Optional[int] = None
    supplier_name: Optional[str] = None
    current_stock: Decimal
    min_stock: Decimal
    target_stock: Decimal
    suggested_qty: Decimal
    unit: str
    pack_size: int
    lead_time_days: int


class OrderSuggestionsResponse(BaseModel):
    """Response with all order suggestions grouped by supplier."""

    location_id: int
    suggestions: List[OrderSuggestion]
    by_supplier: Dict[int, List[OrderSuggestion]]


class CreateOrdersFromSuggestions(BaseModel):
    """Request to create POs from suggestions."""

    location_id: int
    supplier_ids: Optional[List[int]] = None  # If None, create for all suppliers with suggestions

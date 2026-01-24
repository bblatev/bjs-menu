"""Purchase order schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict

from pydantic import BaseModel, Field

from app.models.order import POStatus


class PurchaseOrderLineCreate(BaseModel):
    """Purchase order line creation schema."""

    product_id: int
    qty: Decimal = Field(gt=0)
    unit_cost: Optional[Decimal] = None


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
    lines: List[PurchaseOrderLineCreate]
    notes: Optional[str] = None


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

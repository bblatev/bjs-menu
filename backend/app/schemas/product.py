"""Product schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class ProductBase(BaseModel):
    """Base product schema."""

    name: str
    barcode: Optional[str] = None
    supplier_id: Optional[int] = None
    pack_size: int = 1
    unit: str = "pcs"
    min_stock: Decimal = Decimal("0")
    target_stock: Decimal = Decimal("0")
    lead_time_days: int = 1
    cost_price: Optional[Decimal] = None
    sku: Optional[str] = None
    ai_label: Optional[str] = None


class ProductCreate(ProductBase):
    """Product creation schema."""

    pass


class ProductUpdate(BaseModel):
    """Product update schema."""

    name: Optional[str] = None
    barcode: Optional[str] = None
    supplier_id: Optional[int] = None
    pack_size: Optional[int] = None
    unit: Optional[str] = None
    min_stock: Optional[Decimal] = None
    target_stock: Optional[Decimal] = None
    lead_time_days: Optional[int] = None
    cost_price: Optional[Decimal] = None
    sku: Optional[str] = None
    ai_label: Optional[str] = None
    active: Optional[bool] = None


class ProductResponse(ProductBase):
    """Product response schema."""

    id: int
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductImportRow(BaseModel):
    """Schema for a single row in product CSV import."""

    name: str
    barcode: Optional[str] = None
    supplier_name: Optional[str] = None
    pack_size: int = Field(default=1, ge=1)
    unit: str = "pcs"
    min_stock: Decimal = Decimal("0")
    target_stock: Decimal = Decimal("0")
    lead_time_days: int = Field(default=1, ge=1)
    cost_price: Optional[Decimal] = None
    sku: Optional[str] = None
    ai_label: Optional[str] = None

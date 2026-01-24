"""Supplier schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class SupplierBase(BaseModel):
    """Base supplier schema."""

    name: str
    contact_phone: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    address: Optional[str] = None
    notes: Optional[str] = None


class SupplierCreate(SupplierBase):
    """Supplier creation schema."""

    pass


class SupplierUpdate(BaseModel):
    """Supplier update schema."""

    name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    address: Optional[str] = None
    notes: Optional[str] = None


class SupplierResponse(SupplierBase):
    """Supplier response schema."""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

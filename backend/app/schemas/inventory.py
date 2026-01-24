"""Inventory session and line schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel, Field

from app.models.inventory import CountMethod, SessionStatus


class InventoryLineCreate(BaseModel):
    """Inventory line creation schema."""

    product_id: int
    counted_qty: Decimal = Field(ge=0)
    method: CountMethod = CountMethod.MANUAL
    confidence: Optional[Decimal] = Field(default=None, ge=0, le=1)
    photo_id: Optional[int] = None


class InventoryLineUpdate(BaseModel):
    """Inventory line update schema."""

    counted_qty: Optional[Decimal] = Field(default=None, ge=0)
    method: Optional[CountMethod] = None
    confidence: Optional[Decimal] = Field(default=None, ge=0, le=1)


class InventoryLineResponse(BaseModel):
    """Inventory line response schema."""

    id: int
    session_id: int
    product_id: int
    counted_qty: Decimal
    method: CountMethod
    confidence: Optional[Decimal] = None
    photo_id: Optional[int] = None
    counted_at: datetime

    model_config = {"from_attributes": True}


class InventorySessionCreate(BaseModel):
    """Inventory session creation schema."""

    location_id: int
    notes: Optional[str] = None


class InventorySessionResponse(BaseModel):
    """Inventory session response schema."""

    id: int
    location_id: int
    status: SessionStatus
    started_at: datetime
    committed_at: Optional[datetime] = None
    created_by: Optional[int] = None
    notes: Optional[str] = None
    lines: List[InventoryLineResponse] = []

    model_config = {"from_attributes": True}


class InventorySessionCommitResponse(BaseModel):
    """Response after committing an inventory session."""

    session_id: int
    status: SessionStatus
    committed_at: datetime
    movements_created: int
    stock_adjustments: List[dict]

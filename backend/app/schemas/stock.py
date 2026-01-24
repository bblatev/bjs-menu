"""Stock schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class StockOnHandResponse(BaseModel):
    """Stock on hand response schema."""

    id: int
    product_id: int
    location_id: int
    qty: Decimal
    updated_at: datetime

    model_config = {"from_attributes": True}


class StockMovementResponse(BaseModel):
    """Stock movement response schema."""

    id: int
    ts: datetime
    product_id: int
    location_id: int
    qty_delta: Decimal
    reason: str
    ref_type: Optional[str] = None
    ref_id: Optional[int] = None
    notes: Optional[str] = None
    created_by: Optional[int] = None

    model_config = {"from_attributes": True}


class StockAdjustmentRequest(BaseModel):
    """Manual stock adjustment request."""

    product_id: int
    location_id: int
    qty_delta: Decimal
    reason: str = "adjustment"
    notes: Optional[str] = None

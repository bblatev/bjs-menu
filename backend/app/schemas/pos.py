"""POS integration schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel


class PosSalesLineResponse(BaseModel):
    """POS sales line response schema."""

    id: int
    ts: datetime
    pos_item_id: Optional[str] = None
    name: str
    qty: Decimal
    is_refund: bool
    location_id: Optional[int] = None
    processed: bool

    model_config = {"from_attributes": True}


class PosImportResult(BaseModel):
    """Result of POS data import."""

    source: str
    rows_imported: int
    rows_skipped: int
    errors: List[str]


class PosConsumeResult(BaseModel):
    """Result of converting POS sales to stock movements."""

    sales_processed: int
    movements_created: int
    unmatched_items: List[str]
    errors: List[str]

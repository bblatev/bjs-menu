"""Sync schemas for mobile offline-first synchronization."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict

from pydantic import BaseModel

from app.models.inventory import CountMethod, SessionStatus


class SyncProductData(BaseModel):
    """Product data for sync."""

    id: int
    name: str
    barcode: Optional[str] = None
    supplier_id: Optional[int] = None
    pack_size: int
    unit: str
    min_stock: Decimal
    target_stock: Decimal
    ai_label: Optional[str] = None
    active: bool
    updated_at: Optional[datetime] = None


class SyncSupplierData(BaseModel):
    """Supplier data for sync."""

    id: int
    name: str
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    updated_at: Optional[datetime] = None


class SyncLocationData(BaseModel):
    """Location data for sync."""

    id: int
    name: str
    is_default: bool
    active: bool
    updated_at: Optional[datetime] = None


class SyncStockData(BaseModel):
    """Stock on hand data for sync."""

    product_id: int
    location_id: int
    qty: Decimal
    updated_at: datetime


class SyncPullResponse(BaseModel):
    """Response for sync pull request."""

    products: List[SyncProductData]
    suppliers: List[SyncSupplierData]
    locations: List[SyncLocationData]
    stock: List[SyncStockData]
    server_timestamp: datetime


class SyncInventoryLine(BaseModel):
    """Inventory line for sync push."""

    local_id: str  # Client-side UUID
    product_id: int
    counted_qty: Decimal
    method: CountMethod
    confidence: Optional[Decimal] = None
    counted_at: datetime


class SyncInventorySession(BaseModel):
    """Inventory session for sync push."""

    local_id: str  # Client-side UUID
    location_id: int
    status: SessionStatus
    started_at: datetime
    committed_at: Optional[datetime] = None
    notes: Optional[str] = None
    lines: List[SyncInventoryLine]


class SyncPushRequest(BaseModel):
    """Request for sync push."""

    sessions: List[SyncInventorySession]
    client_timestamp: datetime


class SyncPushResponse(BaseModel):
    """Response for sync push."""

    sessions_created: int
    lines_created: int
    conflicts: List[dict]  # Any conflicts that need resolution
    server_timestamp: datetime
    id_mappings: Dict[str, int]  # local_id -> server_id mappings

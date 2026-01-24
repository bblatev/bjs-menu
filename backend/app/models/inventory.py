"""Inventory session and line models."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SessionStatus(str, Enum):
    """Status of an inventory session."""

    DRAFT = "draft"
    COMMITTED = "committed"
    CANCELLED = "cancelled"


class CountMethod(str, Enum):
    """Method used to count inventory."""

    BARCODE = "barcode"
    AI = "ai"
    MANUAL = "manual"


class InventorySession(Base):
    """An inventory counting session."""

    __tablename__ = "inventory_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    shelf_zone: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # e.g., "Bar Back", "Fridge 1"
    status: Mapped[SessionStatus] = mapped_column(
        SQLEnum(SessionStatus), default=SessionStatus.DRAFT, nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    committed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # Relationships
    location: Mapped["Location"] = relationship("Location", back_populates="inventory_sessions")
    lines: Mapped[list["InventoryLine"]] = relationship(
        "InventoryLine", back_populates="session", cascade="all, delete-orphan"
    )
    reconciliation_results: Mapped[list["ReconciliationResult"]] = relationship(
        "ReconciliationResult", back_populates="session", cascade="all, delete-orphan"
    )
    reorder_proposals: Mapped[list["ReorderProposal"]] = relationship(
        "ReorderProposal", back_populates="session", cascade="all, delete-orphan"
    )
    order_drafts: Mapped[list["SupplierOrderDraft"]] = relationship(
        "SupplierOrderDraft", back_populates="session", cascade="all, delete-orphan"
    )


class InventoryLine(Base):
    """A single product count in an inventory session."""

    __tablename__ = "inventory_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("inventory_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    barcode: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # Barcode if scanned
    counted_qty: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    method: Mapped[CountMethod] = mapped_column(
        SQLEnum(CountMethod), default=CountMethod.MANUAL, nullable=False
    )
    confidence: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(3, 2), nullable=True
    )  # For AI counts: 0.00-1.00
    photo_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("ai_photos.id", ondelete="SET NULL"), nullable=True
    )
    counted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # User notes on this line

    # Relationships
    session: Mapped["InventorySession"] = relationship("InventorySession", back_populates="lines")
    product: Mapped["Product"] = relationship("Product", back_populates="inventory_lines")
    # Note: AIPhoto relationship simplified for main V99 database compatibility


# Forward references
from app.models.location import Location
from app.models.product import Product
from app.models.ai import AIPhoto
from app.models.reconciliation import ReconciliationResult, ReorderProposal, SupplierOrderDraft

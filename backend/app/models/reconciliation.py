"""Reconciliation, reorder, and supplier order draft models."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DeltaSeverity(str, Enum):
    """Severity level of stock discrepancy."""

    OK = "ok"           # Within acceptable tolerance
    WARNING = "warning"  # Minor discrepancy or low confidence
    CRITICAL = "critical"  # Significant discrepancy requires attention


class ReconciliationResult(Base):
    """Result of comparing expected vs counted quantities for a product."""

    __tablename__ = "reconciliation_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("inventory_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Quantities
    expected_qty: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    counted_qty: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    delta_qty: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)  # expected - counted
    delta_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)  # $ value of delta
    delta_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)  # % of expected

    # Assessment
    severity: Mapped[DeltaSeverity] = mapped_column(
        SQLEnum(DeltaSeverity), default=DeltaSeverity.OK, nullable=False
    )
    reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # Explanation

    # Source info
    expected_source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # pos_stock, calculated, manual
    confidence: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 2), nullable=True)  # From AI if applicable

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    session: Mapped["InventorySession"] = relationship("InventorySession", back_populates="reconciliation_results")
    product: Mapped["Product"] = relationship("Product")


class ReorderProposal(Base):
    """Suggested reorder for a product based on stock analysis."""

    __tablename__ = "reorder_proposals"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("inventory_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    supplier_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("suppliers.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Quantities
    current_stock: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    target_stock: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    in_transit: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    recommended_qty: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)  # Raw calculation
    rounded_qty: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)  # After pack/case rounding
    pack_size: Mapped[int] = mapped_column(default=1, nullable=False)

    # Cost
    unit_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    line_total: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)

    # Rationale
    rationale_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON with calculation details

    # User edits
    user_qty: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)  # Manual override
    included: Mapped[bool] = mapped_column(default=True, nullable=False)  # Include in order

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    session: Mapped["InventorySession"] = relationship("InventorySession", back_populates="reorder_proposals")
    product: Mapped["Product"] = relationship("Product")
    supplier: Mapped[Optional["Supplier"]] = relationship("Supplier")


class OrderDraftStatus(str, Enum):
    """Status of a supplier order draft."""

    DRAFT = "draft"
    FINALIZED = "finalized"
    EXPORTED = "exported"
    SENT = "sent"
    CANCELLED = "cancelled"


class SupplierOrderDraft(Base):
    """Draft order to a supplier, generated from reorder proposals."""

    __tablename__ = "supplier_order_drafts"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("inventory_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Status tracking
    status: Mapped[OrderDraftStatus] = mapped_column(
        SQLEnum(OrderDraftStatus), default=OrderDraftStatus.DRAFT, nullable=False
    )

    # Order content
    payload_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Full order data as JSON
    line_count: Mapped[int] = mapped_column(default=0, nullable=False)
    total_qty: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    total_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)

    # Delivery
    requested_delivery_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # Export tracking
    exported_csv_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    exported_pdf_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    email_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Purchase order link (when converted to actual PO)
    purchase_order_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("purchase_orders.id", ondelete="SET NULL"),
        nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    created_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    session: Mapped["InventorySession"] = relationship("InventorySession", back_populates="order_drafts")
    supplier: Mapped["Supplier"] = relationship("Supplier")
    purchase_order: Mapped[Optional["PurchaseOrder"]] = relationship("PurchaseOrder")


# Forward references
from app.models.inventory import InventorySession
from app.models.product import Product
from app.models.supplier import Supplier
from app.models.order import PurchaseOrder

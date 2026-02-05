"""Stock models: StockOnHand and StockMovement."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MovementReason(str, Enum):
    """Reasons for stock movements."""

    INVENTORY_COUNT = "inventory_count"  # From inventory session commit
    SALE = "sale"  # From POS sale
    REFUND = "refund"  # From POS refund/void
    TRANSFER_IN = "transfer_in"  # Transfer from another location
    TRANSFER_OUT = "transfer_out"  # Transfer to another location
    WASTE = "waste"  # Spoilage, breakage
    ADJUSTMENT = "adjustment"  # Manual adjustment
    PURCHASE = "purchase"  # Goods received
    RESERVATION = "reservation"  # Stock reserved for in-progress order
    RESERVATION_RELEASE = "reservation_release"  # Reserved stock released (order cancelled/fulfilled)


class StockOnHand(Base):
    """Current stock level per product per location."""

    __tablename__ = "stock_on_hand"
    __table_args__ = (
        UniqueConstraint("product_id", "location_id", name="uq_stock_product_location"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    qty: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    reserved_qty: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False, server_default="0")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="stock_on_hand")
    location: Mapped["Location"] = relationship("Location", back_populates="stock_on_hand")


class StockMovement(Base):
    """Ledger of all stock changes (single source of truth)."""

    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    qty_delta: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    reason: Mapped[str] = mapped_column(String(50), nullable=False)
    ref_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # inventory_session, pos_sale, transfer
    ref_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="stock_movements")
    location: Mapped["Location"] = relationship("Location", back_populates="stock_movements")


# Forward references
from app.models.product import Product
from app.models.location import Location

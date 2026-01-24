"""Location model."""

from __future__ import annotations

from typing import Optional, List

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Location(Base, TimestampMixin):
    """Physical location for stock (warehouse, bar, fridge, etc.)."""

    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    stock_on_hand: Mapped[list["StockOnHand"]] = relationship(
        "StockOnHand", back_populates="location"
    )
    stock_movements: Mapped[list["StockMovement"]] = relationship(
        "StockMovement", back_populates="location"
    )
    inventory_sessions: Mapped[list["InventorySession"]] = relationship(
        "InventorySession", back_populates="location"
    )
    purchase_orders: Mapped[list["PurchaseOrder"]] = relationship(
        "PurchaseOrder", back_populates="location"
    )
    pos_sales_lines: Mapped[list["PosSalesLine"]] = relationship(
        "PosSalesLine", back_populates="location"
    )


# Forward references
from app.models.stock import StockOnHand, StockMovement
from app.models.inventory import InventorySession
from app.models.order import PurchaseOrder
from app.models.pos import PosSalesLine

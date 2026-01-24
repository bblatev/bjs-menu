"""StockItem model - maps to main V99 database stock_items table."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import Boolean, Float, Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.ai import TrainingImage


class StockItem(Base):
    """Stock item from main V99 database.

    Maps to the stock_items table in the main bjsbar.db database.
    Used for AI bottle training and recognition.
    """

    __tablename__ = "stock_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    venue_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    menu_item_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    sku: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    quantity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), default="pcs", nullable=False)
    low_stock_threshold: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    cost_per_unit: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships - use explicit primaryjoin for cross-table reference
    training_images: Mapped[list["TrainingImage"]] = relationship(
        "TrainingImage",
        back_populates="stock_item",
        primaryjoin="StockItem.id == TrainingImage.stock_item_id",
        foreign_keys="TrainingImage.stock_item_id",
        cascade="all, delete-orphan"
    )

    @property
    def active(self) -> bool:
        """Compatibility property for code expecting 'active' instead of 'is_active'."""
        return self.is_active if self.is_active is not None else True

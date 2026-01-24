"""Product model."""

from __future__ import annotations

from decimal import Decimal
from typing import Optional, List

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Product(Base, TimestampMixin):
    """Product in the catalog."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    barcode: Mapped[Optional[str]] = mapped_column(String(50), unique=True, index=True, nullable=True)
    supplier_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("suppliers.id"), nullable=True, index=True
    )
    pack_size: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), default="pcs", nullable=False)  # pcs, ml, L, kg
    min_stock: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    par_level: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)  # PAR level for automatic replenishment
    target_stock: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    lead_time_days: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    cost_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    sku: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    ai_label: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Label for AI detection
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    supplier: Mapped[Optional["Supplier"]] = relationship("Supplier", back_populates="products")
    stock_on_hand: Mapped[list["StockOnHand"]] = relationship(
        "StockOnHand", back_populates="product"
    )
    stock_movements: Mapped[list["StockMovement"]] = relationship(
        "StockMovement", back_populates="product"
    )
    inventory_lines: Mapped[list["InventoryLine"]] = relationship(
        "InventoryLine", back_populates="product"
    )
    purchase_order_lines: Mapped[list["PurchaseOrderLine"]] = relationship(
        "PurchaseOrderLine", back_populates="product"
    )
    recipe_lines: Mapped[list["RecipeLine"]] = relationship("RecipeLine", back_populates="product")
    # Note: training_images now linked to StockItem in main V99 database


# Forward references
from app.models.supplier import Supplier
from app.models.stock import StockOnHand, StockMovement
from app.models.inventory import InventoryLine
from app.models.order import PurchaseOrderLine
from app.models.recipe import RecipeLine

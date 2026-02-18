"""Location model."""

from __future__ import annotations

from typing import Optional, List

from sqlalchemy import Boolean, String, Integer, Text, JSON, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Location(Base, TimestampMixin):
    """Physical location for stock (warehouse, bar, fridge, etc.)."""

    __tablename__ = "locations"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, unique=True)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Multi-location fields
    location_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(50), default="active", nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Address
    street: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    region: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    postal_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Contact
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Settings
    timezone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    operating_hours: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)
    features: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)
    settings: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)

    # Menu sync
    menu_source_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    menu_sync_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

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

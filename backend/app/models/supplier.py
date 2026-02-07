"""Supplier model."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Integer, ForeignKey, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Supplier(Base, TimestampMixin):
    """Supplier for products."""

    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # Relationships
    products: Mapped[list["Product"]] = relationship("Product", back_populates="supplier")
    purchase_orders: Mapped[list["PurchaseOrder"]] = relationship(
        "PurchaseOrder", back_populates="supplier"
    )
    documents: Mapped[list["SupplierDocument"]] = relationship(
        "SupplierDocument", back_populates="supplier"
    )


class SupplierDocument(Base, TimestampMixin):
    """Document attached to a supplier (contracts, certificates, etc)."""

    __tablename__ = "supplier_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(Integer, ForeignKey("suppliers.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    document_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # contract, certificate, license, insurance, other
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    expiration_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    supplier: Mapped["Supplier"] = relationship("Supplier", back_populates="documents")


# Forward references
from app.models.product import Product
from app.models.order import PurchaseOrder

"""Recipe (Bill of Materials) models."""

from __future__ import annotations

from decimal import Decimal
from typing import Optional, List

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Recipe(Base, TimestampMixin):
    """A recipe that maps a POS item to stock consumption."""

    __tablename__ = "recipes"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    pos_item_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )  # Maps to POS system item ID
    pos_item_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    lines: Mapped[list["RecipeLine"]] = relationship(
        "RecipeLine", back_populates="recipe", cascade="all, delete-orphan"
    )


class RecipeLine(Base):
    """A single ingredient/component in a recipe."""

    __tablename__ = "recipe_lines"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(
        ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    qty: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), default="pcs", nullable=False)  # pcs, ml, L, kg, g

    # Relationships
    recipe: Mapped["Recipe"] = relationship("Recipe", back_populates="lines")
    product: Mapped["Product"] = relationship("Product", back_populates="recipe_lines")


# Forward references
from app.models.product import Product

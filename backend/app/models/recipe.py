"""Recipe (Bill of Materials) models."""

from __future__ import annotations

from decimal import Decimal
from typing import Optional, List

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text, JSON
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

    # Production module fields
    menu_item_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("menu_items.id"), nullable=True, index=True
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    yield_quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    yield_unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    preparation_time: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    difficulty: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # easy, medium, hard
    instructions: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)

    # Relationships
    lines: Mapped[list["RecipeLine"]] = relationship(
        "RecipeLine", back_populates="recipe", cascade="all, delete-orphan"
    )
    menu_item = relationship(
        "MenuItem", foreign_keys=[menu_item_id], backref="production_recipes"
    )
    # Note: 'ingredients' relationship is added via backref from RecipeIngredient in complete_modules.py


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

"""Recipe (BOM) schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel, Field


class RecipeLineCreate(BaseModel):
    """Recipe line creation schema."""

    product_id: int
    qty: Decimal = Field(gt=0)
    unit: str = "pcs"


class RecipeLineResponse(BaseModel):
    """Recipe line response schema."""

    id: int
    recipe_id: int
    product_id: int
    qty: Decimal
    unit: str

    model_config = {"from_attributes": True}


class RecipeBase(BaseModel):
    """Base recipe schema."""

    name: str
    pos_item_id: Optional[str] = None
    pos_item_name: Optional[str] = None


class RecipeCreate(RecipeBase):
    """Recipe creation schema."""

    lines: List[RecipeLineCreate]


class RecipeUpdate(BaseModel):
    """Recipe update schema."""

    name: Optional[str] = None
    pos_item_id: Optional[str] = None
    pos_item_name: Optional[str] = None
    lines: Optional[List[RecipeLineCreate]] = None


class RecipeResponse(RecipeBase):
    """Recipe response schema."""

    id: int
    created_at: datetime
    updated_at: datetime
    lines: List[RecipeLineResponse] = []

    model_config = {"from_attributes": True}

"""Location schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class LocationBase(BaseModel):
    """Base location schema."""

    name: str
    description: Optional[str] = None
    is_default: bool = False


class LocationCreate(LocationBase):
    """Location creation schema."""

    pass


class LocationUpdate(BaseModel):
    """Location update schema."""

    name: Optional[str] = None
    description: Optional[str] = None
    is_default: Optional[bool] = None
    active: Optional[bool] = None


class LocationResponse(LocationBase):
    """Location response schema."""

    id: int
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

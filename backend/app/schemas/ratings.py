"""Rating schemas"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class ItemRatingCreate(BaseModel):
    """Create an item rating"""
    order_item_id: int
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


class ItemRatingResponse(BaseModel):
    """Item rating response"""
    id: int
    order_item_id: int
    menu_item_id: int
    rating: int
    comment: Optional[str]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ServiceRatingCreate(BaseModel):
    """Create a service rating"""
    table_token: str
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None
    tip_amount: Optional[float] = None


class ServiceRatingResponse(BaseModel):
    """Service rating response"""
    id: int
    table_id: int
    staff_user_id: Optional[int]
    rating: int
    comment: Optional[str]
    tip_amount: Optional[float]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


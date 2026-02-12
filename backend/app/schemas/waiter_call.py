"""Waiter call schemas"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from enum import Enum


class WaiterCallReason(str, Enum):
    BILL = "bill"
    HELP = "help"
    COMPLAINT = "complaint"
    WATER = "water"
    OTHER = "other"


class WaiterCallStatus(str, Enum):
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SPAM = "spam"


class WaiterCallCreate(BaseModel):
    table_id: int
    reason: WaiterCallReason
    message: Optional[str] = None


class WaiterCallUpdate(BaseModel):
    status: WaiterCallStatus
    notes: Optional[str] = None


class WaiterCallResponse(BaseModel):
    id: int
    table_id: int
    reason: str
    status: str
    message: Optional[str]
    created_at: datetime
    acknowledged_at: Optional[datetime]
    resolved_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)



# Alias for backwards compatibility
WaiterCallStatusUpdate = WaiterCallUpdate


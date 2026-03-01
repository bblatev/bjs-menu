"""
Waiter Terminal API Endpoints
Comprehensive waiter/bartender POS functionality including:
- Order creation with seats and courses
- Bar tab management with pre-authorization
- Bill splitting (by item, seat, even, portions)
- Check merge and transfer
- Payment processing (cash, card, split tender)
- Table management and floor plan
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pydantic import BaseModel, Field
from enum import Enum

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.core.rbac import get_current_user
from app.core.rbac import RequireManager
from app.models import (
    StaffUser, StaffRole, Order, OrderItem, Table, MenuItem,
    TableSession, Payment, Customer, VenueStation
)
from app.core.security import verify_pin
from app.services.stock_deduction_service import StockDeductionService
from app.schemas.pagination import paginate_query, PaginatedResponse

import logging
logger = logging.getLogger(__name__)




# ============================================================================
# ENUMS
# ============================================================================

class CourseType(str, Enum):
    DRINKS = "drinks"
    APPETIZER = "appetizer"
    SOUP_SALAD = "soup_salad"
    MAIN = "main"
    DESSERT = "dessert"
    AFTER_DINNER = "after_dinner"


class CheckStatus(str, Enum):
    OPEN = "open"
    PRINTED = "printed"
    PAID = "paid"
    VOIDED = "voided"


class TabStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    TRANSFERRED = "transferred"


class PaymentMethod(str, Enum):
    CASH = "cash"
    CARD = "card"
    MOBILE = "mobile"
    TAB = "tab"
    GIFT_CARD = "gift_card"
    COMP = "comp"


class SplitType(str, Enum):
    BY_ITEM = "by_item"
    BY_SEAT = "by_seat"
    EVEN = "even"
    CUSTOM = "custom"


# ============================================================================
# REQUEST/RESPONSE SCHEMAS
# ============================================================================

class OrderItemCreate(BaseModel):
    """Single item in an order"""
    menu_item_id: int
    quantity: int = 1
    seat_number: Optional[int] = None
    course: Optional[CourseType] = None
    modifiers: Optional[List[str]] = []
    special_instructions: Optional[str] = None
    price_override: Optional[float] = None


class WaiterOrderCreate(BaseModel):
    """Create order from waiter terminal"""
    table_id: int
    items: List[OrderItemCreate]
    guest_count: int = 1
    notes: Optional[str] = None
    send_to_kitchen: bool = True
    fire_immediately: bool = False


class WaiterOrderResponse(BaseModel):
    """Response for waiter order"""
    order_id: int
    order_number: str
    table_id: int
    table_name: str
    items: List[Dict[str, Any]]
    subtotal: float
    tax: float
    total: float
    status: str
    created_at: datetime
    waiter_name: str


class AddItemsRequest(BaseModel):
    """Add items to existing order"""
    items: List[OrderItemCreate]
    send_to_kitchen: bool = True


class FireCourseRequest(BaseModel):
    """Fire a specific course to kitchen"""
    course: CourseType
    notes: Optional[str] = None


class HoldCourseRequest(BaseModel):
    """Hold a course from firing"""
    course: CourseType
    reason: Optional[str] = None


# --- Bar Tab Schemas ---

class OpenTabRequest(BaseModel):
    """Open a new bar tab"""
    customer_name: str
    card_last_four: Optional[str] = None
    pre_auth_amount: float = 50.0
    phone: Optional[str] = None
    notes: Optional[str] = None


class TabResponse(BaseModel):
    """Bar tab response"""
    tab_id: int
    customer_name: str
    card_last_four: Optional[str]
    pre_auth_amount: float
    current_total: float
    items: List[Dict[str, Any]]
    status: str
    opened_at: datetime
    opened_by: str


class AddToTabRequest(BaseModel):
    """Add items to bar tab"""
    items: List[OrderItemCreate]


class TransferTabRequest(BaseModel):
    """Transfer tab to table"""
    table_id: int
    seat_number: Optional[int] = None


class CloseTabRequest(BaseModel):
    """Close bar tab"""
    tip_amount: float = 0.0
    payment_method: PaymentMethod = PaymentMethod.TAB


# --- Bill/Check Schemas ---

class CheckResponse(BaseModel):
    """Check/bill response"""
    check_id: int
    check_number: str
    table_id: int
    seat_numbers: List[int]
    items: List[Dict[str, Any]]
    subtotal: float
    tax: float
    discount: float
    tip: float
    total: float
    status: str
    payments: List[Dict[str, Any]]
    balance_due: float


class SplitByItemRequest(BaseModel):
    """Split check by moving items"""
    item_ids: List[int]
    to_check_id: Optional[int] = None  # None = create new check


class SplitBySeatRequest(BaseModel):
    """Split check by seat"""
    pass  # Will create one check per seat


class SplitEvenRequest(BaseModel):
    """Split check evenly"""
    num_ways: int = Field(..., ge=2, le=20)


class SplitItemPortionRequest(BaseModel):
    """Split single item into portions"""
    item_id: int
    portions: int = Field(..., ge=2, le=10)


class MergeChecksRequest(BaseModel):
    """Merge multiple checks"""
    check_ids: List[int] = Field(..., min_length=2)


class TransferItemsRequest(BaseModel):
    """Transfer items between checks"""
    item_ids: List[int]
    to_check_id: int


# --- Payment Schemas ---

class PaymentRequest(BaseModel):
    """Process payment"""
    check_id: int
    amount: float
    payment_method: PaymentMethod
    tip_amount: float = 0.0
    card_last_four: Optional[str] = None
    auth_code: Optional[str] = None


class SplitTenderRequest(BaseModel):
    """Split payment across multiple tenders"""
    check_id: int
    payments: List[PaymentRequest]


class ApplyDiscountRequest(BaseModel):
    """Apply discount to check"""
    discount_type: str = "percent"  # percent or amount
    discount_value: float
    reason: str
    manager_pin: Optional[str] = None


class AutoGratuityRequest(BaseModel):
    """Apply auto-gratuity"""
    gratuity_percent: float = 18.0


class VoidItemRequest(BaseModel):
    """Void an item"""
    reason: str
    manager_pin: Optional[str] = None


class CompItemRequest(BaseModel):
    """Comp an item"""
    reason: str
    manager_pin: Optional[str] = None


# --- Table Management Schemas ---

class TableStatusResponse(BaseModel):
    """Table status for floor plan"""
    table_id: int
    table_name: str
    capacity: int
    status: str  # available, occupied, reserved, dirty
    current_check_id: Optional[int]
    guest_count: Optional[int]
    server_name: Optional[str]
    seated_at: Optional[datetime]
    time_seated_minutes: Optional[int]
    current_total: Optional[float]


class TransferTableRequest(BaseModel):
    """Transfer table to another server"""
    to_waiter_id: int


class QuickActionResponse(BaseModel):
    """Response for quick actions"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


# ============================================================================
# ORDER MANAGEMENT ENDPOINTS
# ============================================================================


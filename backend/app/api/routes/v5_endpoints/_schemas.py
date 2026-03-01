"""V5 API Endpoints - TouchBistro/iiko/Toast Feature Parity
33 New Features, ~150 Endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Optional
from datetime import datetime, date, timezone, time, timedelta
from decimal import Decimal
from pydantic import BaseModel
import secrets

from app.db.session import get_db
from app.models import (
    MarketingCampaign, Customer, Order, MenuItem, StaffUser, OrderItem,
    Reservation, ReservationDeposit, DepositStatus, VenueSettings,
    Promotion, PromotionUsage, Table, StaffShift
)
from app.models.missing_features_models import (
    CateringEvent, CateringEventStatus, CateringOrderItem, CateringInvoice,
    CustomerReferral, VIPTier, CustomerVIPStatus, GuestbookEntry,
    Chargeback, ChargebackStatus, TaxReport, MenuPairing,
    CustomerDisplay, CustomerDisplayContent, FundraisingCampaign, FundraisingDonation,
    TableBlock, EmployeeBreak,
    ShiftTradeRequest as ShiftTradeRequestModel, EmployeeOnboarding,
    OnboardingChecklist, OnboardingTask, OnboardingTaskCompletion,
    IngredientPriceHistory, PriceAlertNotification, MenuItemReview,
    PrepTimePrediction
)
from app.models.operations import ReferralProgram
from app.models.invoice import PriceAlert
from app.models.core_business_models import SMSMessage
from app.models import StockItem
from dateutil.relativedelta import relativedelta
from calendar import monthrange
from app.core.rate_limit import limiter



# ==================== PYDANTIC MODELS ====================

class SMSCampaignCreate(BaseModel):
    name: str
    message: str
    target_segment: str = "all"
    scheduled_at: Optional[datetime] = None

class CateringEventCreate(BaseModel):
    event_name: str
    event_type: str
    event_date: datetime
    guest_count: int
    contact_name: str
    contact_phone: str
    contact_email: Optional[str] = None
    location: Optional[str] = None

class DepositRequest(BaseModel):
    reservation_id: int
    amount: float
    currency: str = "BGN"

class ReferralCodeValidation(BaseModel):
    code: str
    referee_customer_id: int

class ShiftTradeRequest(BaseModel):
    original_shift_id: int
    trade_type: str
    target_staff_id: Optional[int] = None
    offered_shift_id: Optional[int] = None
    reason: Optional[str] = None

class PromoCodeGenerate(BaseModel):
    count: int = 10
    discount_type: str
    discount_value: float
    valid_days: int = 30
    minimum_order: Optional[float] = None

class TableBlockCreate(BaseModel):
    venue_id: int
    table_id: int
    block_date: date
    start_time: str
    end_time: str
    block_type: str = "manual"  # reservation, private_event, maintenance, manual
    reason: Optional[str] = None
    is_recurring: bool = False
    recurrence_pattern: Optional[str] = None  # daily, weekly, etc.
    recurrence_end_date: Optional[date] = None
    reservation_id: Optional[int] = None
    event_id: Optional[int] = None

class MenuPairingCreate(BaseModel):
    primary_item_id: int
    paired_item_id: int
    pairing_type: str
    pairing_reason: Optional[str] = None

class CharityDonation(BaseModel):
    campaign_id: int
    amount: float
    donation_type: str = "flat"
    order_id: Optional[int] = None

class ChargebackCreate(BaseModel):
    order_id: Optional[int] = None
    payment_id: Optional[int] = None
    amount: float
    currency: str = "BGN"
    reason_code: str
    reason: Optional[str] = None
    provider: Optional[str] = None
    provider_case_id: Optional[str] = None

class ChargebackResponse(BaseModel):
    evidence_documents: List[str] = []
    response_notes: str


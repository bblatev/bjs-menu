from app.models.operations import ReferralProgram
from app.models.core_business_models import SMSMessage
"""
BJS V7 API Endpoints - Complete Missing Features (150+ endpoints)
"""

from fastapi import APIRouter, HTTPException, Query, Body, Depends, Path, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional, Dict
from datetime import datetime, timedelta, timezone
from enum import Enum
from decimal import Decimal

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.missing_features_models import (
    SMSCampaign, SMSOptOut, CustomerRFMScore, RFMSegmentDefinition, CustomerVIPStatus, VIPTier as VIPTierModel, IngredientPriceHistory, EmployeeBreak, BreakPolicy, ShiftTradeRequest, SingleUsePromoCode, PromoCodeCampaign, CustomerReferral, MenuItemReview, MenuItemRatingAggregate, CustomerDisplay, CateringEvent, CateringInvoice, CateringOrderItem, DepositPolicy, PrepTimeModel, )
from app.models.invoice import PriceAlert
from app.models import Customer, ReservationDeposit


router = APIRouter(tags=["V7 Features"])

from app.core.rbac import get_current_user

def require_manager(current_user = Depends(get_current_user)):
    """Require manager or above role."""
    if not hasattr(current_user, 'role'):
        return current_user
    if current_user.role not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Manager access required")
    return current_user


def verify_venue_access(venue_id: int, current_user) -> None:
    """Verify the user has access to the specified venue.

    Admins and owners can access any venue. Other roles are checked
    against their assigned venue_id.
    """
    if not hasattr(current_user, 'role'):
        return
    if current_user.role in ("admin", "owner"):
        return
    user_venue = getattr(current_user, 'venue_id', None)
    if user_venue is not None and user_venue != venue_id:
        raise HTTPException(status_code=403, detail="Access denied for this venue")


# Enums
class DepositPolicyType(str, Enum):
    per_person = "per_person"
    flat_rate = "flat_rate"
    percentage = "percentage"
    tiered = "tiered"

class CampaignType(str, Enum):
    promotional = "promotional"
    transactional = "transactional"
    reminder = "reminder"
    loyalty = "loyalty"
    birthday = "birthday"
    win_back = "win_back"
    flash_sale = "flash_sale"

class EventType(str, Enum):
    wedding = "wedding"
    corporate = "corporate"
    birthday = "birthday"
    private_dining = "private_dining"
    other = "other"

class PromoCodeType(str, Enum):
    percentage = "percentage"
    fixed_amount = "fixed_amount"
    free_item = "free_item"
    free_delivery = "free_delivery"

class VIPTier(str, Enum):
    silver = "silver"
    gold = "gold"
    platinum = "platinum"
    diamond = "diamond"

class ChargebackReason(str, Enum):
    fraud = "fraud"
    not_received = "product_not_received"
    not_as_described = "product_not_as_described"
    duplicate = "duplicate_charge"
    other = "other"

class BlockType(str, Enum):
    reserved = "reserved"
    maintenance = "maintenance"
    vip = "vip"
    event = "event"
    cleaning = "cleaning"



"""V7 Breaks, shift trades & VIP"""
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
    SMSCampaign, SMSOptOut, CustomerRFMScore, RFMSegmentDefinition,
    CustomerVIPStatus, VIPTier as VIPTierModel, IngredientPriceHistory,
    EmployeeBreak, BreakPolicy, ShiftTradeRequest, SingleUsePromoCode,
    PromoCodeCampaign, CustomerReferral, MenuItemReview,
    MenuItemRatingAggregate, CustomerDisplay, CateringEvent,
    CateringInvoice, CateringOrderItem, DepositPolicy, PrepTimeModel,
)
from app.models.invoice import PriceAlert
from app.models import Customer, ReservationDeposit
from app.models.operations import ReferralProgram
from app.models.core_business_models import SMSMessage

from app.core.rbac import get_current_user
from app.api.routes.v7_endpoints._helpers import (
    require_manager, verify_venue_access,
    DepositPolicyType, CampaignType, EventType, PromoCodeType,
    VIPTier, ChargebackReason, BlockType,
)

router = APIRouter()

# ============================================================================
# TIER 2: BREAK MANAGEMENT (5 endpoints)
# ============================================================================

@router.post("/{venue_id}/breaks/policy")
@limiter.limit("30/minute")
async def configure_break_policy(
    request: Request,
    venue_id: int,
    min_shift_for_break: int = Body(4),
    meal_break_duration: int = Body(30),
    rest_break_duration: int = Body(10),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Configure break policy in database"""
    verify_venue_access(venue_id, current_user)
    # Check for existing policy
    policy = db.query(BreakPolicy).filter(
        BreakPolicy.venue_id == venue_id
    ).first()

    if policy:
        policy.min_shift_hours_for_break = min_shift_for_break
        policy.meal_break_duration_minutes = meal_break_duration
        policy.rest_break_duration_minutes = rest_break_duration
    else:
        policy = BreakPolicy(
            venue_id=venue_id,
            min_shift_hours_for_break=min_shift_for_break,
            meal_break_duration_minutes=meal_break_duration,
            rest_break_duration_minutes=rest_break_duration,
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        db.add(policy)

    db.commit()
    db.refresh(policy)

    return {
        "policy_id": policy.id,
        "min_shift_for_break": policy.min_shift_hours_for_break,
        "meal_break_duration": policy.meal_break_duration_minutes,
        "rest_break_duration": policy.rest_break_duration_minutes
    }

@router.post("/{venue_id}/breaks/schedule")
@limiter.limit("30/minute")
async def schedule_breaks(
    request: Request,
    venue_id: int,
    employee_id: str = Body(...),
    shift_id: str = Body(...),
    shift_start: datetime = Body(...),
    shift_end: datetime = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Schedule breaks for a shift in database"""
    verify_venue_access(venue_id, current_user)
    try:
        employee_id_int = int(employee_id)
        shift_id_int = int(shift_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    # Get break policy
    policy = db.query(BreakPolicy).filter(
        BreakPolicy.venue_id == venue_id,
        BreakPolicy.is_active == True
    ).first()

    shift_duration = (shift_end - shift_start).total_seconds() / 3600
    min_hours = policy.min_shift_hours_for_break if policy else 4
    meal_duration = policy.meal_break_duration_minutes if policy else 30
    rest_duration = policy.rest_break_duration_minutes if policy else 10

    breaks = []

    if shift_duration >= min_hours:
        # Schedule meal break at midpoint
        midpoint = shift_start + (shift_end - shift_start) / 2
        meal_break = EmployeeBreak(
            venue_id=venue_id,
            staff_id=employee_id_int,
            shift_id=shift_id_int,
            break_type="meal",
            scheduled_start=midpoint,
            scheduled_end=midpoint + timedelta(minutes=meal_duration),
            scheduled_duration_minutes=meal_duration,
            status="scheduled",
            created_at=datetime.now(timezone.utc)
        )
        db.add(meal_break)
        breaks.append(meal_break)

    if shift_duration >= 6:
        # Schedule rest break before meal
        rest_time = shift_start + timedelta(hours=2)
        rest_break = EmployeeBreak(
            venue_id=venue_id,
            staff_id=employee_id_int,
            shift_id=shift_id_int,
            break_type="rest",
            scheduled_start=rest_time,
            scheduled_end=rest_time + timedelta(minutes=rest_duration),
            scheduled_duration_minutes=rest_duration,
            status="scheduled",
            created_at=datetime.now(timezone.utc)
        )
        db.add(rest_break)
        breaks.append(rest_break)

    db.commit()

    return {
        "breaks": [
            {
                "id": b.id,
                "type": b.break_type,
                "scheduled_start": b.scheduled_start.isoformat()
            }
            for b in breaks
        ]
    }

@router.post("/{venue_id}/breaks/{break_id}/start")
@limiter.limit("30/minute")
async def start_break(
    request: Request,
    venue_id: int,
    break_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Start a break in database"""
    verify_venue_access(venue_id, current_user)
    try:
        break_id_int = int(break_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid break_id format")

    brk = db.query(EmployeeBreak).filter(
        EmployeeBreak.id == break_id_int
    ).first()

    if not brk:
        raise HTTPException(status_code=404, detail="Break not found")

    brk.status = "in_progress"
    brk.actual_start = datetime.now(timezone.utc)

    db.commit()
    db.refresh(brk)

    return {"break_id": brk.id, "status": brk.status}

@router.post("/{venue_id}/breaks/{break_id}/end")
@limiter.limit("30/minute")
async def end_break(
    request: Request,
    venue_id: int,
    break_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """End a break in database"""
    verify_venue_access(venue_id, current_user)
    try:
        break_id_int = int(break_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid break_id format")

    brk = db.query(EmployeeBreak).filter(
        EmployeeBreak.id == break_id_int
    ).first()

    if not brk:
        raise HTTPException(status_code=404, detail="Break not found")

    brk.status = "completed"
    brk.actual_end = datetime.now(timezone.utc)

    if brk.actual_start:
        brk.actual_duration_minutes = int((brk.actual_end - brk.actual_start).total_seconds() / 60)

    db.commit()
    db.refresh(brk)

    return {"break_id": brk.id, "status": brk.status}

@router.get("/{venue_id}/breaks/employee/{employee_id}")
@limiter.limit("60/minute")
async def get_employee_breaks(request: Request, venue_id: int, employee_id: str, date: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """Get employee breaks for a date from database"""
    try:
        employee_id_int = int(employee_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid venue_id or employee_id format")

    dt = datetime.fromisoformat(date) if date else datetime.now(timezone.utc)
    start_of_day = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)

    # Query breaks from database
    breaks = db.query(EmployeeBreak).filter(
        EmployeeBreak.venue_id == venue_id,
        EmployeeBreak.staff_id == employee_id_int,
        EmployeeBreak.scheduled_start >= start_of_day,
        EmployeeBreak.scheduled_start < end_of_day
    ).order_by(EmployeeBreak.scheduled_start).all()

    return [
        {
            "id": b.id,
            "break_type": b.break_type,
            "scheduled_start": b.scheduled_start.isoformat() if b.scheduled_start else None,
            "scheduled_end": b.scheduled_end.isoformat() if b.scheduled_end else None,
            "actual_start": b.actual_start.isoformat() if b.actual_start else None,
            "actual_end": b.actual_end.isoformat() if b.actual_end else None,
            "status": b.status,
            "duration_minutes": b.actual_duration_minutes or b.scheduled_duration_minutes
        }
        for b in breaks
    ]


# ============================================================================
# TIER 2: SHIFT TRADING (5 endpoints)
# ============================================================================

@router.post("/{venue_id}/shift-trades/configure")
@limiter.limit("30/minute")
async def configure_shift_trading(
    request: Request,
    venue_id: int,
    allow_trading: bool = Body(True),
    require_manager_approval: bool = Body(True),
    min_notice_hours: int = Body(24),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Configure shift trading settings in database"""
    verify_venue_access(venue_id, current_user)
    from app.models.missing_features_models import ShiftTradingConfig

    config = db.query(ShiftTradingConfig).filter(
        ShiftTradingConfig.venue_id == venue_id
    ).first()

    if config:
        config.allow_trading = allow_trading
        config.require_manager_approval = require_manager_approval
        config.min_notice_hours = min_notice_hours
    else:
        config = ShiftTradingConfig(
            venue_id=venue_id,
            allow_trading=allow_trading,
            require_manager_approval=require_manager_approval,
            min_notice_hours=min_notice_hours,
            is_active=True
        )
        db.add(config)

    db.commit()
    db.refresh(config)

    return {
        "config_id": config.id,
        "allow_trading": config.allow_trading,
        "require_manager_approval": config.require_manager_approval,
        "min_notice_hours": config.min_notice_hours
    }

@router.post("/{venue_id}/shift-trades")
@limiter.limit("30/minute")
async def request_shift_trade(
    request: Request,
    venue_id: int,
    requesting_employee_id: str = Body(...),
    target_employee_id: str = Body(...),
    shift_id: str = Body(...),
    shift_date: datetime = Body(...),
    shift_start: datetime = Body(...),
    shift_end: datetime = Body(...),
    reason: str = Body(""),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Request shift trade in database"""
    verify_venue_access(venue_id, current_user)
    try:
        requester_id_int = int(requesting_employee_id)
        target_id_int = int(target_employee_id)
        shift_id_int = int(shift_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    # Check trading config
    from app.models.missing_features_models import ShiftTradingConfig
    config = db.query(ShiftTradingConfig).filter(
        ShiftTradingConfig.venue_id == venue_id,
        ShiftTradingConfig.is_active == True
    ).first()

    requires_approval = config.require_manager_approval if config else True

    trade = ShiftTradeRequest(
        venue_id=venue_id,
        requester_id=requester_id_int,
        target_employee_id=target_id_int,
        original_shift_id=shift_id_int,
        trade_type="swap",
        status="pending",
        requires_approval=requires_approval,
        reason=reason,
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=48)
    )

    db.add(trade)
    db.commit()
    db.refresh(trade)

    return {"trade_id": trade.id, "status": trade.status}

@router.post("/{venue_id}/shift-trades/{trade_id}/respond")
@limiter.limit("30/minute")
async def respond_to_trade(
    request: Request,
    venue_id: int,
    trade_id: str,
    employee_id: str = Body(...),
    accept: bool = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Respond to shift trade in database"""
    verify_venue_access(venue_id, current_user)
    try:
        trade_id_int = int(trade_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid trade_id format")

    trade = db.query(ShiftTradeRequest).filter(
        ShiftTradeRequest.id == trade_id_int
    ).first()

    if not trade:
        raise HTTPException(status_code=404, detail="Trade request not found")

    if accept:
        if trade.requires_approval:
            trade.status = "pending_approval"
        else:
            trade.status = "approved"
    else:
        trade.status = "rejected"

    trade.responded_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(trade)

    return {"trade_id": trade.id, "status": trade.status}

@router.post("/{venue_id}/shift-trades/{trade_id}/manager-decision")
@limiter.limit("30/minute")
async def manager_trade_decision(
    request: Request,
    venue_id: int,
    trade_id: str,
    manager_id: str = Body(...),
    approve: bool = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Manager decision on shift trade in database"""
    verify_venue_access(venue_id, current_user)
    try:
        trade_id_int = int(trade_id)
        manager_id_int = int(manager_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    trade = db.query(ShiftTradeRequest).filter(
        ShiftTradeRequest.id == trade_id_int
    ).first()

    if not trade:
        raise HTTPException(status_code=404, detail="Trade request not found")

    trade.status = "approved" if approve else "rejected"
    trade.approved_by_id = manager_id_int
    trade.approved_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(trade)

    return {"trade_id": trade.id, "status": trade.status}

@router.get("/{venue_id}/shift-trades/pending")
@limiter.limit("60/minute")
async def get_pending_trades(request: Request, venue_id: int, employee_id: Optional[str] = Query(None), for_manager: bool = Query(False), db: Session = Depends(get_db)):
    """Get pending shift trades from database"""
    # Build query for pending trades
    query = db.query(ShiftTradeRequest).filter(
        ShiftTradeRequest.venue_id == venue_id,
        ShiftTradeRequest.status == "pending"
    )

    if for_manager:
        # Manager sees trades requiring approval
        query = query.filter(ShiftTradeRequest.requires_approval == True)
    elif employee_id:
        # Employee sees their own requests or requests directed to them
        try:
            employee_id_int = int(employee_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid employee_id format")
        query = query.filter(
            (ShiftTradeRequest.requester_id == employee_id_int) |
            (ShiftTradeRequest.target_employee_id == employee_id_int)
        )

    trades = query.order_by(ShiftTradeRequest.created_at.desc()).limit(50).all()

    return [
        {
            "id": t.id,
            "requester_id": t.requester_id,
            "target_employee_id": t.target_employee_id,
            "original_shift_id": t.original_shift_id,
            "trade_type": t.trade_type,
            "status": t.status,
            "requires_approval": t.requires_approval,
            "reason": t.reason,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "expires_at": t.expires_at.isoformat() if t.expires_at else None
        }
        for t in trades
    ]


# ============================================================================
# TIER 2: VIP MANAGEMENT (5 endpoints)
# ============================================================================

@router.post("/{venue_id}/vip/configure")
@limiter.limit("30/minute")
async def configure_vip_program(
    request: Request,
    venue_id: int,
    tiers: Optional[Dict] = Body(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Configure VIP program tiers in database"""
    verify_venue_access(venue_id, current_user)
    default_tiers = tiers or {
        "silver": {"min_spend": 500, "min_visits": 5, "discount": 5},
        "gold": {"min_spend": 1500, "min_visits": 15, "discount": 10},
        "platinum": {"min_spend": 5000, "min_visits": 30, "discount": 15},
        "diamond": {"min_spend": 15000, "min_visits": 50, "discount": 20}
    }

    created_tiers = []
    for tier_name, tier_config in default_tiers.items():
        existing = db.query(VIPTierModel).filter(
            VIPTierModel.venue_id == venue_id,
            VIPTierModel.name == tier_name
        ).first()

        if existing:
            existing.min_spend_required = Decimal(str(tier_config.get("min_spend", 0)))
            existing.min_visits_required = tier_config.get("min_visits", 0)
            existing.discount_percentage = Decimal(str(tier_config.get("discount", 0)))
            created_tiers.append(existing)
        else:
            tier = VIPTierModel(
                venue_id=venue_id,
                name=tier_name,
                min_spend_required=Decimal(str(tier_config.get("min_spend", 0))),
                min_visits_required=tier_config.get("min_visits", 0),
                discount_percentage=Decimal(str(tier_config.get("discount", 0))),
                priority_reservations=tier_name in ["gold", "platinum", "diamond"],
                special_events_access=tier_name in ["platinum", "diamond"],
                dedicated_contact=tier_name == "diamond",
                is_active=True
            )
            db.add(tier)
            created_tiers.append(tier)

    db.commit()

    return {
        "venue_id": venue_id,
        "tiers_configured": len(created_tiers),
        "tiers": list(default_tiers.keys())
    }

@router.post("/{venue_id}/vip/assign")
@limiter.limit("30/minute")
async def assign_vip_status(
    request: Request,
    venue_id: int,
    customer_id: str = Body(...),
    tier: VIPTier = Body(...),
    assigned_by: str = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Assign VIP status to customer in database"""
    verify_venue_access(venue_id, current_user)
    try:
        customer_id_int = int(customer_id)
        assigned_by_int = int(assigned_by)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    # Get tier model
    tier_model = db.query(VIPTierModel).filter(
        VIPTierModel.venue_id == venue_id,
        VIPTierModel.name == tier.value
    ).first()

    if not tier_model:
        raise HTTPException(status_code=404, detail=f"VIP tier {tier.value} not configured")

    # Check for existing VIP status
    existing = db.query(CustomerVIPStatus).filter(
        CustomerVIPStatus.venue_id == venue_id,
        CustomerVIPStatus.customer_id == customer_id_int
    ).first()

    if existing:
        existing.vip_tier_id = tier_model.id
        existing.assigned_by_id = assigned_by_int
        existing.assigned_date = datetime.now(timezone.utc)
        existing.is_active = True
    else:
        vip_status = CustomerVIPStatus(
            venue_id=venue_id,
            customer_id=customer_id_int,
            vip_tier_id=tier_model.id,
            assigned_by_id=assigned_by_int,
            assigned_date=datetime.now(timezone.utc),
            is_active=True
        )
        db.add(vip_status)

    db.commit()

    return {"customer_id": customer_id, "tier": tier.value}

@router.put("/{venue_id}/vip/{customer_id}/preferences")
@limiter.limit("30/minute")
async def update_vip_preferences(
    request: Request,
    venue_id: int,
    customer_id: str,
    preferences: Optional[Dict] = Body(None),
    preferred_server: Optional[str] = Body(None),
    preferred_table: Optional[str] = Body(None),
    allergies: Optional[List[str]] = Body(None),
    notes: Optional[str] = Body(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Update VIP preferences in database"""
    verify_venue_access(venue_id, current_user)
    try:
        customer_id_int = int(customer_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    vip_status = db.query(CustomerVIPStatus).filter(
        CustomerVIPStatus.venue_id == venue_id,
        CustomerVIPStatus.customer_id == customer_id_int,
        CustomerVIPStatus.is_active == True
    ).first()

    if not vip_status:
        raise HTTPException(status_code=404, detail="VIP status not found")

    if preferences:
        vip_status.preferences = preferences
    if preferred_server:
        if not vip_status.preferences:
            vip_status.preferences = {}
        vip_status.preferences["preferred_server"] = preferred_server
    if preferred_table:
        if not vip_status.preferences:
            vip_status.preferences = {}
        vip_status.preferences["preferred_table"] = preferred_table
    if allergies:
        if not vip_status.preferences:
            vip_status.preferences = {}
        vip_status.preferences["allergies"] = allergies
    if notes:
        vip_status.notes = notes

    db.commit()
    db.refresh(vip_status)

    return {"customer_id": customer_id, "updated": True}

@router.get("/{venue_id}/vip/{customer_id}")
@limiter.limit("60/minute")
async def check_vip_status(request: Request, venue_id: int, customer_id: str, db: Session = Depends(get_db)):
    """Check if customer is VIP and get their info from database"""
    try:
        customer_id_int = int(customer_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid venue_id or customer_id format")

    # Query VIP status from database
    vip_status = db.query(CustomerVIPStatus).filter(
        CustomerVIPStatus.venue_id == venue_id,
        CustomerVIPStatus.customer_id == customer_id_int,
        CustomerVIPStatus.is_active == True
    ).first()

    if not vip_status:
        return {"is_vip": False}

    # Get tier details
    tier = db.query(VIPTierModel).filter(
        VIPTierModel.id == vip_status.vip_tier_id
    ).first()

    benefits = []
    if tier:
        if tier.discount_percentage:
            benefits.append(f"{tier.discount_percentage}% discount")
        if tier.priority_reservations:
            benefits.append("Priority reservations")
        if tier.dedicated_contact:
            benefits.append("Dedicated contact")
        if tier.special_events_access:
            benefits.append("Special events access")

    return {
        "is_vip": True,
        "tier": tier.name if tier else None,
        "benefits": benefits,
        "deposit_exempt": tier.is_invite_only if tier else False,
        "preferences": vip_status.preferences or {},
        "notes": vip_status.notes,
        "assigned_date": vip_status.assigned_date.isoformat() if vip_status.assigned_date else None,
        "valid_until": vip_status.valid_until.isoformat() if vip_status.valid_until else None
    }

@router.post("/{venue_id}/vip/auto-upgrade")
@limiter.limit("30/minute")
async def auto_upgrade_vip(
    request: Request,
    venue_id: int,
    customer_id: str = Body(...),
    current_spend: float = Body(...),
    current_visits: int = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Auto-upgrade VIP tier based on spend/visits in database"""
    verify_venue_access(venue_id, current_user)
    try:
        customer_id_int = int(customer_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    # Get all tiers ordered by min spend
    tiers = db.query(VIPTierModel).filter(
        VIPTierModel.venue_id == venue_id,
        VIPTierModel.is_active == True
    ).order_by(VIPTierModel.min_spend_required.desc()).all()

    if not tiers:
        return {"customer_id": customer_id, "new_tier": None, "upgraded": False, "reason": "No VIP tiers configured"}

    # Find highest qualifying tier
    new_tier = None
    for tier in tiers:
        if (current_spend >= float(tier.min_spend_required or 0) and
            current_visits >= (tier.min_visits_required or 0)):
            new_tier = tier
            break

    if not new_tier:
        return {"customer_id": customer_id, "new_tier": None, "upgraded": False, "reason": "Does not qualify for any tier"}

    # Check current VIP status
    current_status = db.query(CustomerVIPStatus).filter(
        CustomerVIPStatus.venue_id == venue_id,
        CustomerVIPStatus.customer_id == customer_id_int,
        CustomerVIPStatus.is_active == True
    ).first()

    if current_status:
        current_tier = db.query(VIPTierModel).filter(
            VIPTierModel.id == current_status.vip_tier_id
        ).first()

        # Only upgrade if new tier is higher
        if current_tier and float(current_tier.min_spend_required or 0) >= float(new_tier.min_spend_required or 0):
            return {
                "customer_id": customer_id,
                "new_tier": current_tier.name,
                "upgraded": False,
                "reason": "Already at same or higher tier"
            }

        current_status.vip_tier_id = new_tier.id
        current_status.assigned_date = datetime.now(timezone.utc)
    else:
        vip_status = CustomerVIPStatus(
            venue_id=venue_id,
            customer_id=customer_id_int,
            vip_tier_id=new_tier.id,
            assigned_date=datetime.now(timezone.utc),
            is_active=True
        )
        db.add(vip_status)

    db.commit()

    return {
        "customer_id": customer_id,
        "new_tier": new_tier.name,
        "upgraded": True
    }

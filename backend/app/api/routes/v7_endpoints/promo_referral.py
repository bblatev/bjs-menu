"""V7 Promo codes & referrals"""
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
# TIER 2: SINGLE-USE PROMO CODES (5 endpoints)
# ============================================================================

@router.post("/{venue_id}/promo-codes")
@limiter.limit("30/minute")
async def create_promo_code(
    request: Request,
    venue_id: int,
    code_type: PromoCodeType = Body(...),
    value: float = Body(...),
    code: Optional[str] = Body(None),
    min_order: float = Body(0),
    valid_days: int = Body(30),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Create single-use promo code in database"""
    verify_venue_access(venue_id, current_user)
    import secrets
    promo_code = code.upper() if code else secrets.token_hex(4).upper()

    promo = SingleUsePromoCode(
        venue_id=venue_id,
        code=promo_code,
        discount_type=code_type.value if code_type in [PromoCodeType.percentage, PromoCodeType.fixed_amount] else "percentage",
        discount_value=Decimal(str(value)),
        min_order_value=Decimal(str(min_order)) if min_order > 0 else None,
        valid_from=datetime.now(timezone.utc),
        valid_until=datetime.now(timezone.utc) + timedelta(days=valid_days),
        is_used=False,
        created_at=datetime.now(timezone.utc)
    )

    db.add(promo)
    db.commit()
    db.refresh(promo)

    return {
        "code_id": promo.id,
        "code": promo.code,
        "value": float(promo.discount_value)
    }

@router.post("/{venue_id}/promo-codes/batch")
@limiter.limit("30/minute")
async def generate_promo_batch(
    request: Request,
    venue_id: int,
    name: str = Body(...),
    code_type: PromoCodeType = Body(...),
    value: float = Body(...),
    quantity: int = Body(...),
    prefix: str = Body(""),
    valid_days: int = Body(30),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Generate batch of promo codes in database"""
    verify_venue_access(venue_id, current_user)
    if quantity > 1000:
        raise HTTPException(status_code=400, detail="Maximum 1000 codes per batch")

    # Create batch campaign
    campaign = PromoCodeCampaign(
        venue_id=venue_id,
        name=name,
        discount_type=code_type.value,
        discount_value=Decimal(str(value)),
        valid_from=datetime.now(timezone.utc),
        valid_until=datetime.now(timezone.utc) + timedelta(days=valid_days),
        total_codes=quantity,
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )

    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    import secrets
    codes_generated = []

    for i in range(quantity):
        code_suffix = secrets.token_hex(3).upper()
        promo_code = f"{prefix}{code_suffix}" if prefix else code_suffix

        promo = SingleUsePromoCode(
            venue_id=venue_id,
            campaign_id=campaign.id,
            code=promo_code,
            discount_type=code_type.value if code_type in [PromoCodeType.percentage, PromoCodeType.fixed_amount] else "percentage",
            discount_value=Decimal(str(value)),
            valid_from=datetime.now(timezone.utc),
            valid_until=datetime.now(timezone.utc) + timedelta(days=valid_days),
            is_used=False,
            created_at=datetime.now(timezone.utc)
        )
        db.add(promo)
        codes_generated.append(promo_code)

    db.commit()

    return {
        "batch_id": campaign.id,
        "codes_generated": len(codes_generated),
        "sample_codes": codes_generated[:5]
    }

@router.post("/{venue_id}/promo-codes/validate")
@limiter.limit("30/minute")
async def validate_promo_code(request: Request, venue_id: int, code: str = Body(...), customer_id: Optional[str] = Body(None), order_total: float = Body(0), db: Session = Depends(get_db), current_user=Depends(require_manager)):
    """Validate a promo code from database"""
    verify_venue_access(venue_id, current_user)
    # Query the promo code from database
    promo = db.query(SingleUsePromoCode).filter(
        SingleUsePromoCode.venue_id == venue_id,
        SingleUsePromoCode.code == code.upper()
    ).first()

    if not promo:
        return {"valid": False, "error": "Code not found"}

    # Check if already used
    if promo.is_used:
        return {"valid": False, "error": "Code has already been used"}

    # Check validity dates
    now = datetime.now(timezone.utc)
    if promo.valid_from and now < promo.valid_from:
        return {"valid": False, "error": "Code is not yet valid"}
    if promo.valid_until and now > promo.valid_until:
        return {"valid": False, "error": "Code has expired"}

    # Check minimum order value
    if promo.min_order_value and order_total < float(promo.min_order_value):
        return {"valid": False, "error": f"Minimum order of {promo.min_order_value} required"}

    # Check if code is assigned to specific customer
    if promo.customer_id and customer_id:
        try:
            customer_id_int = int(customer_id)
            if promo.customer_id != customer_id_int:
                return {"valid": False, "error": "This code is assigned to a different customer"}
        except ValueError:
            pass

    # Calculate discount
    discount_amount = 0
    if promo.discount_type == "percentage":
        discount_amount = order_total * (float(promo.discount_value) / 100)
        if promo.max_discount:
            discount_amount = min(discount_amount, float(promo.max_discount))
    elif promo.discount_type == "fixed":
        discount_amount = float(promo.discount_value)

    return {
        "valid": True,
        "code_id": promo.id,
        "discount_type": promo.discount_type,
        "discount_value": float(promo.discount_value),
        "discount_amount": round(discount_amount, 2),
        "min_order_value": float(promo.min_order_value) if promo.min_order_value else None,
        "valid_until": promo.valid_until.isoformat() if promo.valid_until else None
    }

@router.post("/{venue_id}/promo-codes/{code_id}/redeem")
@limiter.limit("30/minute")
async def redeem_promo_code(
    request: Request,
    venue_id: int,
    code_id: str,
    customer_id: str = Body(...),
    order_id: str = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Redeem promo code in database"""
    verify_venue_access(venue_id, current_user)
    try:
        code_id_int = int(code_id)
        customer_id_int = int(customer_id)
        order_id_int = int(order_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    promo = db.query(SingleUsePromoCode).filter(
        SingleUsePromoCode.id == code_id_int
    ).first()

    if not promo:
        raise HTTPException(status_code=404, detail="Promo code not found")

    if promo.is_used:
        raise HTTPException(status_code=400, detail="Code has already been used")

    promo.is_used = True
    promo.used_by_customer_id = customer_id_int
    promo.used_on_order_id = order_id_int
    promo.used_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(promo)

    return {"code_id": promo.id, "status": "redeemed"}

@router.get("/{venue_id}/promo-codes/batch/{batch_id}/stats")
@limiter.limit("60/minute")
async def get_batch_stats(
    request: Request,
    venue_id: int,
    batch_id: str,
    db: Session = Depends(get_db)
):
    """Get batch statistics from database"""
    try:
        batch_id_int = int(batch_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid batch_id format")

    campaign = db.query(PromoCodeCampaign).filter(
        PromoCodeCampaign.id == batch_id_int
    ).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="Batch not found")

    # Count codes
    total_codes = db.query(func.count(SingleUsePromoCode.id)).filter(
        SingleUsePromoCode.campaign_id == batch_id_int
    ).scalar() or 0

    used_codes = db.query(func.count(SingleUsePromoCode.id)).filter(
        SingleUsePromoCode.campaign_id == batch_id_int,
        SingleUsePromoCode.is_used == True
    ).scalar() or 0

    return {
        "batch_id": campaign.id,
        "name": campaign.name,
        "total_codes": total_codes,
        "used_codes": used_codes,
        "unused_codes": total_codes - used_codes,
        "redemption_rate": round(used_codes / max(1, total_codes) * 100, 1),
        "discount_type": campaign.discount_type,
        "discount_value": float(campaign.discount_value) if campaign.discount_value else 0
    }


# ============================================================================
# TIER 2: REFERRAL PROGRAM (5 endpoints)
# ============================================================================

@router.post("/{venue_id}/referrals/configure")
@limiter.limit("30/minute")
async def configure_referral_program(
    request: Request,
    venue_id: int,
    referrer_reward: float = Body(10.0),
    referee_reward: float = Body(10.0),
    min_order: float = Body(20.0),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Configure referral program in database"""
    verify_venue_access(venue_id, current_user)
    # Check if program exists
    program = db.query(ReferralProgram).filter(
        ReferralProgram.venue_id == venue_id
    ).first()

    if program:
        program.referrer_reward_value = Decimal(str(referrer_reward))
        program.referee_reward_value = Decimal(str(referee_reward))
        program.minimum_order_value = Decimal(str(min_order))
        program.is_active = True
    else:
        program = ReferralProgram(
            venue_id=venue_id,
            referrer_reward_type="credit",
            referrer_reward_value=Decimal(str(referrer_reward)),
            referee_reward_type="credit",
            referee_reward_value=Decimal(str(referee_reward)),
            minimum_order_value=Decimal(str(min_order)),
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        db.add(program)

    db.commit()
    db.refresh(program)

    return {
        "program_id": program.id,
        "referrer_reward": float(program.referrer_reward_value),
        "referee_reward": float(program.referee_reward_value),
        "min_order": float(program.minimum_order_value)
    }

@router.get("/{venue_id}/referrals/code/{customer_id}")
@limiter.limit("60/minute")
async def get_referral_code(
    request: Request,
    venue_id: int,
    customer_id: str,
    db: Session = Depends(get_db)
):
    """Get or create referral code in database"""
    try:
        customer_id_int = int(customer_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    # Check for existing referral code
    existing = db.query(CustomerReferral).filter(
        CustomerReferral.venue_id == venue_id,
        CustomerReferral.referrer_id == customer_id_int
    ).first()

    # Get program details
    program = db.query(ReferralProgram).filter(
        ReferralProgram.venue_id == venue_id,
        ReferralProgram.is_active == True
    ).first()

    referrer_reward = float(program.referrer_reward_value) if program else 10.0
    referee_reward = float(program.referee_reward_value) if program else 10.0

    if existing and existing.referral_code:
        return {
            "code": existing.referral_code,
            "referrer_reward": referrer_reward,
            "referee_reward": referee_reward
        }

    # Generate new code
    import secrets
    code = f"REF{customer_id_int}{secrets.token_hex(2).upper()}"

    return {
        "code": code,
        "referrer_reward": referrer_reward,
        "referee_reward": referee_reward
    }

@router.post("/{venue_id}/referrals/apply")
@limiter.limit("30/minute")
async def apply_referral_code(
    request: Request,
    venue_id: int,
    referee_id: str = Body(...),
    referee_email: str = Body(...),
    code: str = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Apply referral code in database"""
    verify_venue_access(venue_id, current_user)
    try:
        referee_id_int = int(referee_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    # Find the referrer by code pattern (REF{customer_id}{random})
    if code.startswith("REF") and len(code) >= 5:
        try:
            referrer_id_str = code[3:-4]  # Extract customer ID from code
            referrer_id_int = int(referrer_id_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid referral code")
    else:
        raise HTTPException(status_code=400, detail="Invalid referral code format")

    # Create referral record
    referral = CustomerReferral(
        venue_id=venue_id,
        referrer_id=referrer_id_int,
        referee_id=referee_id_int,
        referee_email=referee_email,
        referral_code=code,
        status="pending",
        created_at=datetime.now(timezone.utc)
    )

    db.add(referral)
    db.commit()
    db.refresh(referral)

    return {
        "referral_id": referral.id,
        "status": referral.status
    }

@router.post("/{venue_id}/referrals/{referral_id}/complete")
@limiter.limit("30/minute")
async def complete_referral(
    request: Request,
    venue_id: int,
    referral_id: str,
    order_id: str = Body(...),
    order_amount: float = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Complete referral in database"""
    verify_venue_access(venue_id, current_user)
    try:
        referral_id_int = int(referral_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    referral = db.query(CustomerReferral).filter(
        CustomerReferral.id == referral_id_int
    ).first()

    if not referral:
        raise HTTPException(status_code=404, detail="Referral not found")

    # Get program minimum order
    program = db.query(ReferralProgram).filter(
        ReferralProgram.venue_id == venue_id,
        ReferralProgram.is_active == True
    ).first()

    min_order = float(program.minimum_order_value) if program else 20.0

    if order_amount < min_order:
        return {
            "referral_id": referral.id,
            "status": "pending",
            "message": f"Order amount {order_amount} is below minimum {min_order}"
        }

    referral.status = "rewarded"
    referral.rewarded_at = datetime.now(timezone.utc)
    referral.qualifying_order_id = int(order_id)

    db.commit()
    db.refresh(referral)

    return {
        "referral_id": referral.id,
        "status": referral.status,
        "rewarded": True
    }

@router.get("/{venue_id}/referrals/stats/{customer_id}")
@limiter.limit("60/minute")
async def get_referral_stats(request: Request, venue_id: int, customer_id: str, db: Session = Depends(get_db)):
    """Get referral statistics for a customer from database"""
    try:
        customer_id_int = int(customer_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid venue_id or customer_id format")

    # Get the customer's referral code
    referral_code = db.query(CustomerReferral).filter(
        CustomerReferral.venue_id == venue_id,
        CustomerReferral.referrer_id == customer_id_int
    ).first()

    # Count referrals by this customer
    referrals = db.query(CustomerReferral).filter(
        CustomerReferral.venue_id == venue_id,
        CustomerReferral.referrer_id == customer_id_int
    ).all()

    total_referrals = len(referrals)
    completed_referrals = len([r for r in referrals if r.status == "rewarded"])
    pending_referrals = len([r for r in referrals if r.status in ["pending", "registered"]])

    # Get program details
    program = db.query(ReferralProgram).filter(
        ReferralProgram.venue_id == venue_id,
        ReferralProgram.is_active == True
    ).first()

    referrer_reward = float(program.referrer_reward_value) if program and program.referrer_reward_value else 10.0
    total_earned = completed_referrals * referrer_reward

    return {
        "customer_id": customer_id,
        "referral_code": referral_code.referral_code if referral_code else None,
        "total_referrals": total_referrals,
        "completed_referrals": completed_referrals,
        "pending_referrals": pending_referrals,
        "total_earned": round(total_earned, 2),
        "reward_per_referral": referrer_reward,
        "referrals": [
            {
                "id": r.id,
                "referee_email": r.referee_email,
                "status": r.status,
                "registered_at": r.registered_at.isoformat() if r.registered_at else None,
                "rewarded_at": r.rewarded_at.isoformat() if r.rewarded_at else None
            }
            for r in referrals[:20]  # Limit to last 20
        ]
    }


# ============================================================================
# TIER 2: RFM ANALYTICS (5 endpoints)
# ============================================================================


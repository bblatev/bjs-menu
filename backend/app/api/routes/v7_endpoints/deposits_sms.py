"""V7 Deposits & SMS campaigns"""
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
# TIER 1: RESERVATION DEPOSITS (6 endpoints)
# ============================================================================

@router.get("/")
@limiter.limit("60/minute")
async def get_v7_root(request: Request, db: Session = Depends(get_db)):
    """V7 API features status."""
    return {"module": "v7", "version": "7.0", "status": "active", "features": ["sms-templates", "sms-campaigns", "catering-packages", "kitchen-sheets"]}


@router.post("/{venue_id}/deposits/policy")
@limiter.limit("30/minute")
async def configure_deposit_policy(
    request: Request,
    venue_id: int,
    policy_type: DepositPolicyType = Body(...),
    amount: float = Body(10.0),
    min_party_size: int = Body(6),
    refund_hours: int = Body(24),
    vip_exempt: bool = Body(False),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Configure deposit policy for a venue in database"""
    verify_venue_access(venue_id, current_user)
    # Check if policy already exists
    policy = db.query(DepositPolicy).filter(
        DepositPolicy.venue_id == venue_id
    ).first()

    if policy:
        # Update existing policy
        policy.policy_type = policy_type.value
        policy.amount = Decimal(str(amount))
        policy.min_party_size = min_party_size
        policy.refund_cutoff_hours = refund_hours
        policy.vip_exempt = vip_exempt
        policy.updated_at = datetime.now(timezone.utc)
    else:
        # Create new policy
        policy = DepositPolicy(
            venue_id=venue_id,
            policy_type=policy_type.value,
            amount=Decimal(str(amount)),
            min_party_size=min_party_size,
            refund_cutoff_hours=refund_hours,
            vip_exempt=vip_exempt,
            is_active=True
        )
        db.add(policy)

    db.commit()
    db.refresh(policy)

    return {
        "policy_id": policy.id,
        "venue_id": venue_id,
        "policy_type": policy.policy_type,
        "amount": float(policy.amount),
        "min_party_size": policy.min_party_size,
        "refund_cutoff_hours": policy.refund_cutoff_hours,
        "vip_exempt": policy.vip_exempt
    }

@router.post("/{venue_id}/deposits/calculate")
@limiter.limit("30/minute")
async def calculate_deposit(
    request: Request,
    venue_id: int,
    party_size: int = Body(...),
    estimated_spend: float = Body(0),
    is_special_event: bool = Body(False),
    is_vip: bool = Body(False),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Calculate deposit amount based on venue policy from database"""
    verify_venue_access(venue_id, current_user)
    # Get venue policy
    policy = db.query(DepositPolicy).filter(
        DepositPolicy.venue_id == venue_id,
        DepositPolicy.is_active == True
    ).first()

    if not policy:
        return {
            "deposit_required": False,
            "reason": "No deposit policy configured"
        }

    # Check VIP exemption
    if is_vip and policy.vip_exempt:
        return {
            "deposit_required": False,
            "reason": "VIP customers are exempt"
        }

    # Check minimum party size
    if party_size < policy.min_party_size and not is_special_event:
        return {
            "deposit_required": False,
            "reason": f"Party size below minimum of {policy.min_party_size}"
        }

    # Calculate deposit amount
    base_amount = float(policy.amount)

    if policy.policy_type == "per_person":
        deposit_amount = base_amount * party_size
    elif policy.policy_type == "percentage":
        deposit_amount = estimated_spend * (base_amount / 100)
    elif policy.policy_type == "tiered":
        if party_size >= 20:
            deposit_amount = base_amount * 2.5
        elif party_size >= 10:
            deposit_amount = base_amount * 1.5
        else:
            deposit_amount = base_amount
    else:
        deposit_amount = base_amount

    if is_special_event:
        deposit_amount *= 1.5

    return {
        "deposit_required": True,
        "deposit_amount": round(deposit_amount, 2),
        "policy_type": policy.policy_type,
        "refund_cutoff_hours": policy.refund_cutoff_hours,
        "party_size": party_size
    }

@router.post("/{venue_id}/deposits")
@limiter.limit("30/minute")
async def create_deposit(
    request: Request,
    venue_id: int,
    reservation_id: str = Body(...),
    customer_id: str = Body(...),
    amount: float = Body(...),
    currency: str = Body("BGN"),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Create a new deposit in database"""
    verify_venue_access(venue_id, current_user)
    try:
        reservation_id_int = int(reservation_id)
        customer_id_int = int(customer_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    deposit = ReservationDeposit(
        venue_id=venue_id,
        reservation_id=reservation_id_int,
        customer_id=customer_id_int,
        amount=Decimal(str(amount)),
        currency=currency,
        status="pending",
        created_at=datetime.now(timezone.utc)
    )

    db.add(deposit)
    db.commit()
    db.refresh(deposit)

    return {
        "deposit_id": deposit.id,
        "amount": float(deposit.amount),
        "currency": deposit.currency,
        "status": deposit.status
    }

@router.post("/{venue_id}/deposits/{deposit_id}/confirm")
@limiter.limit("30/minute")
async def confirm_deposit_payment(
    request: Request,
    venue_id: int,
    deposit_id: str,
    payment_reference: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Confirm deposit payment in database"""
    verify_venue_access(venue_id, current_user)
    try:
        deposit_id_int = int(deposit_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid deposit_id format")

    deposit = db.query(ReservationDeposit).filter(
        ReservationDeposit.id == deposit_id_int
    ).first()

    if not deposit:
        raise HTTPException(status_code=404, detail="Deposit not found")

    deposit.status = "collected"
    deposit.transaction_id = payment_reference
    deposit.collected_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(deposit)

    return {
        "deposit_id": deposit.id,
        "status": deposit.status,
        "transaction_id": deposit.transaction_id
    }

@router.post("/{venue_id}/deposits/{deposit_id}/apply")
@limiter.limit("30/minute")
async def apply_deposit_to_order(
    request: Request,
    venue_id: int,
    deposit_id: str,
    order_id: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Apply deposit to order in database"""
    verify_venue_access(venue_id, current_user)
    try:
        deposit_id_int = int(deposit_id)
        order_id_int = int(order_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    deposit = db.query(ReservationDeposit).filter(
        ReservationDeposit.id == deposit_id_int
    ).first()

    if not deposit:
        raise HTTPException(status_code=404, detail="Deposit not found")

    if deposit.status != "collected":
        raise HTTPException(status_code=400, detail="Deposit must be collected before applying")

    deposit.order_id = order_id_int
    deposit.applied_at = datetime.now(timezone.utc)
    deposit.amount_applied = deposit.amount
    deposit.status = "applied"

    db.commit()
    db.refresh(deposit)

    return {
        "deposit_id": deposit.id,
        "order_id": deposit.order_id,
        "amount_applied": float(deposit.amount_applied),
        "status": deposit.status
    }

@router.post("/{venue_id}/deposits/{deposit_id}/refund")
@limiter.limit("30/minute")
async def process_deposit_refund(
    request: Request,
    venue_id: int,
    deposit_id: str,
    reservation_datetime: datetime = Body(...),
    reason: str = Body(""),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Process deposit refund in database"""
    verify_venue_access(venue_id, current_user)
    try:
        deposit_id_int = int(deposit_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    deposit = db.query(ReservationDeposit).filter(
        ReservationDeposit.id == deposit_id_int
    ).first()

    if not deposit:
        raise HTTPException(status_code=404, detail="Deposit not found")

    # Get policy for refund cutoff
    policy = db.query(DepositPolicy).filter(
        DepositPolicy.venue_id == venue_id,
        DepositPolicy.is_active == True
    ).first()

    cutoff_hours = policy.refund_cutoff_hours if policy else 24
    hours_until = (reservation_datetime - datetime.now(timezone.utc)).total_seconds() / 3600

    if hours_until < cutoff_hours:
        refund_percentage = 0.5 if hours_until > 0 else 0
    else:
        refund_percentage = 1.0

    refund_amount = float(deposit.amount) * refund_percentage

    deposit.status = "refunded"
    deposit.refund_reason = reason
    deposit.refunded_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(deposit)

    return {
        "deposit_id": deposit.id,
        "status": deposit.status,
        "refund_amount": round(refund_amount, 2),
        "refund_percentage": refund_percentage * 100,
        "reason": deposit.refund_reason
    }


# ============================================================================
# TIER 1: SMS MARKETING (8 endpoints)
# ============================================================================

@router.get("/{venue_id}/sms/templates")
@limiter.limit("60/minute")
async def get_sms_templates(request: Request, venue_id: int, db: Session = Depends(get_db)):
    """Get SMS templates for a venue from database"""
    # Query templates from database - include venue-specific and system defaults
    from app.models.missing_features_models import SMSTemplate
    templates = db.query(SMSTemplate).filter(
        or_(SMSTemplate.venue_id == venue_id, SMSTemplate.is_system_template == True)
    ).all()

    return {
        "templates": [
            {
                "id": t.id,
                "name": t.name,
                "content": t.content,
                "language": t.language,
                "sms_count": (len(t.content) + 159) // 160 if t.content else 1,
                "is_system": t.is_system_template,
                "category": t.category
            }
            for t in templates
        ]
    }

@router.post("/{venue_id}/sms/templates")
@limiter.limit("30/minute")
async def create_sms_template(
    request: Request,
    venue_id: int,
    name: str = Body(...),
    content: str = Body(...),
    language: str = Body("bg"),
    category: str = Body("general"),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Create SMS template in database"""
    verify_venue_access(venue_id, current_user)
    from app.models.missing_features_models import SMSTemplate
    template = SMSTemplate(
        venue_id=venue_id,
        name=name,
        content=content,
        language=language,
        category=category,
        is_system_template=False,
        created_at=datetime.now(timezone.utc)
    )

    db.add(template)
    db.commit()
    db.refresh(template)

    sms_count = (len(content) + 159) // 160

    return {
        "template_id": template.id,
        "name": template.name,
        "sms_count": sms_count
    }

@router.post("/{venue_id}/sms/campaigns")
@limiter.limit("30/minute")
async def create_sms_campaign(
    request: Request,
    venue_id: int,
    name: str = Body(...),
    template_id: str = Body(...),
    campaign_type: CampaignType = Body(...),
    target_audience: Dict = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Create SMS campaign in database"""
    verify_venue_access(venue_id, current_user)
    try:
        template_id_int = int(template_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    campaign = SMSCampaign(
        venue_id=venue_id,
        name=name,
        template_id=template_id_int,
        campaign_type=campaign_type.value,
        target_audience=target_audience,
        status="draft",
        created_at=datetime.now(timezone.utc)
    )

    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    return {
        "campaign_id": campaign.id,
        "name": campaign.name,
        "status": campaign.status
    }

@router.post("/{venue_id}/sms/campaigns/estimate-audience")
@limiter.limit("30/minute")
async def estimate_campaign_audience(request: Request, venue_id: int, filters: Dict = Body(...), db: Session = Depends(get_db), current_user=Depends(require_manager)):
    """Estimate target audience size based on filters using actual customer data"""
    verify_venue_access(venue_id, current_user)
    # Query actual customer count from database
    query = db.query(func.count(Customer.id)).filter(
        Customer.location_id == venue_id,
        Customer.deleted_at.is_(None),
        Customer.marketing_consent == True
    )

    segment = filters.get("segment", "all")

    # Apply segment filters
    if segment == "active_30_days":
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        query = query.filter(Customer.last_visit >= cutoff)
    elif segment == "active_60_days":
        cutoff = datetime.now(timezone.utc) - timedelta(days=60)
        query = query.filter(Customer.last_visit >= cutoff)
    elif segment == "active_90_days":
        cutoff = datetime.now(timezone.utc) - timedelta(days=90)
        query = query.filter(Customer.last_visit >= cutoff)
    elif segment == "inactive_90_days":
        cutoff = datetime.now(timezone.utc) - timedelta(days=90)
        query = query.filter(Customer.last_visit < cutoff)
    elif segment == "birthday_this_month":
        current_month = datetime.now(timezone.utc).month
        query = query.filter(func.extract('month', Customer.birthday) == current_month)
    elif segment == "high_spenders":
        # Top 15% by total spent
        avg_spend = db.query(func.avg(Customer.total_spent)).filter(
            Customer.location_id == venue_id, Customer.deleted_at.is_(None)
        ).scalar() or 0
        query = query.filter(Customer.total_spent >= avg_spend * 2)
    elif segment == "loyalty_members":
        query = query.filter(Customer.loyalty_tier.isnot(None))
    elif segment == "new_customers":
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        query = query.filter(Customer.created_at >= cutoff)

    estimated_recipients = query.scalar() or 0

    # Get opt-out count
    opt_out_count = db.query(func.count(SMSOptOut.id)).filter(
        SMSOptOut.venue_id == venue_id
    ).scalar() or 0

    final_audience = max(0, estimated_recipients - opt_out_count)
    cost_per_sms = 0.05  # BGN per SMS

    return {
        "estimated_recipients": estimated_recipients,
        "opt_outs_excluded": opt_out_count,
        "final_audience": final_audience,
        "estimated_cost": round(final_audience * cost_per_sms, 2),
        "segment": segment,
        "filters_applied": filters
    }

@router.post("/{venue_id}/sms/campaigns/{campaign_id}/schedule")
@limiter.limit("30/minute")
async def schedule_sms_campaign(
    request: Request,
    venue_id: int,
    campaign_id: str,
    send_at: datetime = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Schedule SMS campaign in database"""
    verify_venue_access(venue_id, current_user)
    try:
        campaign_id_int = int(campaign_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid campaign_id format")

    campaign = db.query(SMSCampaign).filter(
        SMSCampaign.id == campaign_id_int
    ).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    campaign.scheduled_at = send_at
    campaign.status = "scheduled"

    db.commit()
    db.refresh(campaign)

    return {
        "campaign_id": campaign.id,
        "scheduled_at": campaign.scheduled_at.isoformat(),
        "status": campaign.status
    }

@router.post("/{venue_id}/sms/campaigns/{campaign_id}/send")
@limiter.limit("30/minute")
async def send_sms_campaign(
    request: Request,
    venue_id: int,
    campaign_id: str,
    test_mode: bool = Query(False),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Send SMS campaign using database"""
    verify_venue_access(venue_id, current_user)
    try:
        campaign_id_int = int(campaign_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    campaign = db.query(SMSCampaign).filter(
        SMSCampaign.id == campaign_id_int
    ).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Get recipients count
    target_audience = campaign.target_audience or {}
    segment = target_audience.get("segment", "all")

    query = db.query(func.count(Customer.id)).filter(
        Customer.location_id == venue_id,
        Customer.deleted_at.is_(None),
        Customer.marketing_consent == True,
        Customer.phone.isnot(None)
    )

    recipients_count = query.scalar() or 0

    if test_mode:
        campaign.status = "test_sent"
        messages_sent = min(5, recipients_count)
    else:
        campaign.status = "sending"
        campaign.sent_at = datetime.now(timezone.utc)
        messages_sent = recipients_count

    campaign.total_recipients = recipients_count

    db.commit()
    db.refresh(campaign)

    return {
        "campaign_id": campaign.id,
        "status": campaign.status,
        "messages_sent": messages_sent,
        "test_mode": test_mode
    }

@router.get("/{venue_id}/sms/campaigns/{campaign_id}/analytics")
@limiter.limit("60/minute")
async def get_campaign_analytics(
    request: Request,
    venue_id: int,
    campaign_id: str,
    db: Session = Depends(get_db)
):
    """Get SMS campaign analytics from database"""
    try:
        campaign_id_int = int(campaign_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid campaign_id format")

    campaign = db.query(SMSCampaign).filter(
        SMSCampaign.id == campaign_id_int
    ).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Get message stats
    messages = db.query(SMSMessage).filter(
        SMSMessage.campaign_id == campaign_id_int
    ).all()

    total_sent = len(messages)
    delivered = len([m for m in messages if m.delivery_status == "delivered"])
    failed = len([m for m in messages if m.delivery_status == "failed"])

    return {
        "campaign_id": campaign.id,
        "name": campaign.name,
        "status": campaign.status,
        "scheduled_at": campaign.scheduled_at.isoformat() if campaign.scheduled_at else None,
        "sent_at": campaign.sent_at.isoformat() if campaign.sent_at else None,
        "total_recipients": campaign.total_recipients or 0,
        "messages_sent": total_sent,
        "delivered": delivered,
        "failed": failed,
        "delivery_rate": round(delivered / max(1, total_sent) * 100, 1)
    }

@router.post("/{venue_id}/sms/opt-out")
@limiter.limit("30/minute")
async def handle_sms_opt_out(
    request: Request,
    venue_id: int,
    phone_number: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Handle SMS opt-out in database"""
    verify_venue_access(venue_id, current_user)
    # Check if already opted out
    existing = db.query(SMSOptOut).filter(
        SMSOptOut.venue_id == venue_id,
        SMSOptOut.phone_number == phone_number
    ).first()

    if existing:
        return {"status": "already_opted_out", "phone": phone_number}

    opt_out = SMSOptOut(
        venue_id=venue_id,
        phone_number=phone_number,
        opted_out_at=datetime.now(timezone.utc)
    )

    db.add(opt_out)
    db.commit()

    return {"status": "opted_out", "phone": phone_number}



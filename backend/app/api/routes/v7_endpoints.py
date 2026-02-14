from app.models.operations import ReferralProgram
from app.models.core_business_models import SMSMessage
"""
BJS V7 API Endpoints - Complete Missing Features (150+ endpoints)
"""

from fastapi import APIRouter, HTTPException, Query, Body, Depends, Path, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional, Dict
from datetime import datetime, timedelta
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
    if current_user.role not in ("admin", "owner", "manager"):
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


# ============================================================================
# TIER 1: RESERVATION DEPOSITS (6 endpoints)
# ============================================================================

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
        policy.updated_at = datetime.utcnow()
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
        created_at=datetime.utcnow()
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
    deposit.collected_at = datetime.utcnow()

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
    deposit.applied_at = datetime.utcnow()
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
    hours_until = (reservation_datetime - datetime.utcnow()).total_seconds() / 3600

    if hours_until < cutoff_hours:
        refund_percentage = 0.5 if hours_until > 0 else 0
    else:
        refund_percentage = 1.0

    refund_amount = float(deposit.amount) * refund_percentage

    deposit.status = "refunded"
    deposit.refund_reason = reason
    deposit.refunded_at = datetime.utcnow()

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
        created_at=datetime.utcnow()
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
        created_at=datetime.utcnow()
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
        Customer.venue_id == venue_id,
        Customer.is_active == True,
        Customer.marketing_consent == True
    )

    segment = filters.get("segment", "all")

    # Apply segment filters
    if segment == "active_30_days":
        cutoff = datetime.utcnow() - timedelta(days=30)
        query = query.filter(Customer.last_visit >= cutoff)
    elif segment == "active_60_days":
        cutoff = datetime.utcnow() - timedelta(days=60)
        query = query.filter(Customer.last_visit >= cutoff)
    elif segment == "active_90_days":
        cutoff = datetime.utcnow() - timedelta(days=90)
        query = query.filter(Customer.last_visit >= cutoff)
    elif segment == "inactive_90_days":
        cutoff = datetime.utcnow() - timedelta(days=90)
        query = query.filter(Customer.last_visit < cutoff)
    elif segment == "birthday_this_month":
        current_month = datetime.utcnow().month
        query = query.filter(func.extract('month', Customer.birthday) == current_month)
    elif segment == "high_spenders":
        # Top 15% by total spent
        avg_spend = db.query(func.avg(Customer.total_spent)).filter(
            Customer.venue_id == venue_id, Customer.is_active == True
        ).scalar() or 0
        query = query.filter(Customer.total_spent >= avg_spend * 2)
    elif segment == "loyalty_members":
        query = query.filter(Customer.loyalty_tier.isnot(None))
    elif segment == "new_customers":
        cutoff = datetime.utcnow() - timedelta(days=30)
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
        Customer.venue_id == venue_id,
        Customer.is_active == True,
        Customer.marketing_consent == True,
        Customer.phone.isnot(None)
    )

    recipients_count = query.scalar() or 0

    if test_mode:
        campaign.status = "test_sent"
        messages_sent = min(5, recipients_count)
    else:
        campaign.status = "sending"
        campaign.sent_at = datetime.utcnow()
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
        opted_out_at=datetime.utcnow()
    )

    db.add(opt_out)
    db.commit()

    return {"status": "opted_out", "phone": phone_number}


# ============================================================================
# TIER 1: CATERING & EVENTS (8 endpoints)
# ============================================================================

@router.get("/{venue_id}/catering/packages")
@limiter.limit("60/minute")
async def get_catering_packages(request: Request, venue_id: int, db: Session = Depends(get_db)):
    """Get catering packages from database"""
    from app.models.missing_features_models import CateringPackage
    packages = db.query(CateringPackage).filter(
        CateringPackage.venue_id == venue_id,
        CateringPackage.is_active == True
    ).all()

    return {
        "packages": [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "price_per_person": float(p.price_per_person) if p.price_per_person else None,
                "min_guests": p.min_guests,
                "max_guests": p.max_guests,
                "included_items": p.included_items or []
            }
            for p in packages
        ]
    }

@router.post("/{venue_id}/catering/inquiries")
@limiter.limit("30/minute")
async def create_catering_inquiry(
    request: Request,
    venue_id: int,
    customer_id: str = Body(...),
    event_type: EventType = Body(...),
    event_name: str = Body(...),
    event_date: datetime = Body(...),
    duration_hours: float = Body(4.0),
    location: str = Body(...),
    guest_count: int = Body(...),
    contact_name: str = Body(...),
    contact_phone: str = Body(...),
    contact_email: str = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Create catering inquiry in database"""
    verify_venue_access(venue_id, current_user)
    try:
        customer_id_int = int(customer_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    event = CateringEvent(
        venue_id=venue_id,
        customer_id=customer_id_int,
        event_type=event_type.value,
        event_name=event_name,
        event_date=event_date,
        duration_hours=duration_hours,
        location=location,
        guest_count=guest_count,
        contact_name=contact_name,
        contact_phone=contact_phone,
        contact_email=contact_email,
        status="inquiry",
        created_at=datetime.utcnow()
    )

    db.add(event)
    db.commit()
    db.refresh(event)

    return {"event_id": event.id, "status": event.status}

@router.post("/{venue_id}/catering/events/{event_id}/quote")
@limiter.limit("30/minute")
async def generate_catering_quote(
    request: Request,
    venue_id: int,
    event_id: str,
    package_id: Optional[str] = Body(None),
    custom_items: Optional[List[Dict]] = Body(None),
    staff_count: int = Body(0),
    delivery_fee: float = Body(0),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Generate catering quote in database"""
    verify_venue_access(venue_id, current_user)
    try:
        event_id_int = int(event_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid event_id format")

    event = db.query(CateringEvent).filter(
        CateringEvent.id == event_id_int
    ).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Calculate quote
    food_total = 0.0
    items_list = []

    if package_id:
        try:
            package_id_int = int(package_id)
            from app.models.missing_features_models import CateringPackage
            package = db.query(CateringPackage).filter(
                CateringPackage.id == package_id_int
            ).first()
            if package and package.price_per_person:
                food_total = float(package.price_per_person) * event.guest_count
                items_list.append({"name": package.name, "quantity": event.guest_count, "price": float(package.price_per_person)})
        except ValueError:
            pass

    if custom_items:
        for item in custom_items:
            item_total = item.get("price", 0) * item.get("quantity", 1)
            food_total += item_total
            items_list.append(item)

    staff_cost = staff_count * 150.0  # 150 BGN per staff member
    total = food_total + staff_cost + delivery_fee

    # Update event with quote
    event.quoted_amount = Decimal(str(total))
    event.status = "quoted"

    db.commit()
    db.refresh(event)

    return {
        "event_id": event.id,
        "quote": {
            "food_total": round(food_total, 2),
            "staff_cost": round(staff_cost, 2),
            "delivery_fee": round(delivery_fee, 2),
            "total": round(total, 2),
            "guest_count": event.guest_count,
            "items": items_list
        }
    }

@router.get("/{venue_id}/catering/events/{event_id}/kitchen-sheet")
@limiter.limit("60/minute")
async def get_kitchen_sheet(
    request: Request,
    venue_id: int,
    event_id: str,
    db: Session = Depends(get_db)
):
    """Generate kitchen sheet from database"""
    try:
        event_id_int = int(event_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid event_id format")

    event = db.query(CateringEvent).filter(
        CateringEvent.id == event_id_int
    ).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Get order items
    items = db.query(CateringOrderItem).filter(
        CateringOrderItem.catering_event_id == event_id_int
    ).all()

    return {
        "event_id": event.id,
        "event_name": event.event_name,
        "event_date": event.event_date.isoformat() if event.event_date else None,
        "guest_count": event.guest_count,
        "items": [
            {
                "name": item.item_name,
                "quantity": item.quantity,
                "notes": item.special_instructions
            }
            for item in items
        ],
        "generated_at": datetime.utcnow().isoformat()
    }

@router.get("/{venue_id}/catering/events/{event_id}/labels")
@limiter.limit("60/minute")
async def get_catering_labels(
    request: Request,
    venue_id: int,
    event_id: str,
    db: Session = Depends(get_db)
):
    """Generate catering labels from database"""
    try:
        event_id_int = int(event_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid event_id format")

    event = db.query(CateringEvent).filter(
        CateringEvent.id == event_id_int
    ).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    items = db.query(CateringOrderItem).filter(
        CateringOrderItem.catering_event_id == event_id_int
    ).all()

    labels = []
    for item in items:
        labels.append({
            "item_name": item.item_name,
            "quantity": item.quantity,
            "event_name": event.event_name,
            "event_date": event.event_date.strftime("%d/%m/%Y") if event.event_date else "",
            "allergens": item.allergens or [],
            "dietary_info": item.dietary_info or []
        })

    return {"labels": labels}

@router.post("/{venue_id}/catering/events/{event_id}/invoice")
@limiter.limit("30/minute")
async def create_catering_invoice(
    request: Request,
    venue_id: int,
    event_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Create catering invoice in database"""
    verify_venue_access(venue_id, current_user)
    try:
        event_id_int = int(event_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    event = db.query(CateringEvent).filter(
        CateringEvent.id == event_id_int
    ).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Generate invoice number
    invoice_count = db.query(func.count(CateringInvoice.id)).filter(
        CateringInvoice.venue_id == venue_id
    ).scalar() or 0
    invoice_number = f"CAT-{venue_id}-{invoice_count + 1:05d}"

    invoice = CateringInvoice(
        venue_id=venue_id,
        catering_event_id=event_id_int,
        invoice_number=invoice_number,
        subtotal=event.quoted_amount or Decimal("0"),
        tax_amount=Decimal(str(float(event.quoted_amount or 0) * 0.2)),  # 20% VAT
        total_amount=Decimal(str(float(event.quoted_amount or 0) * 1.2)),
        status="issued",
        issued_date=datetime.utcnow().date(),
        due_date=(datetime.utcnow() + timedelta(days=14)).date()
    )

    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    return {
        "invoice_id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "total": float(invoice.total_amount)
    }


# ============================================================================
# TIER 1: CUSTOMER DISPLAY (5 endpoints)
# ============================================================================

@router.post("/{venue_id}/displays")
@limiter.limit("30/minute")
async def register_customer_display(
    request: Request,
    venue_id: int,
    terminal_id: str = Body(...),
    name: str = Body(...),
    language: str = Body("bg"),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Register customer display in database"""
    verify_venue_access(venue_id, current_user)
    # Check if display already exists
    existing = db.query(CustomerDisplay).filter(
        CustomerDisplay.venue_id == venue_id,
        CustomerDisplay.terminal_id == terminal_id
    ).first()

    if existing:
        existing.name = name
        existing.language = language
        existing.is_active = True
        existing.last_seen_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return {"display_id": existing.id, "name": existing.name}

    display = CustomerDisplay(
        venue_id=venue_id,
        terminal_id=terminal_id,
        name=name,
        language=language,
        display_mode="idle",
        is_active=True,
        created_at=datetime.utcnow(),
        last_seen_at=datetime.utcnow()
    )

    db.add(display)
    db.commit()
    db.refresh(display)

    return {"display_id": display.id, "name": display.name}

@router.post("/{venue_id}/displays/{display_id}/order")
@limiter.limit("30/minute")
async def update_display_order(
    request: Request,
    venue_id: int,
    display_id: str,
    order_data: Dict = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Update customer display with order info in database"""
    verify_venue_access(venue_id, current_user)
    try:
        display_id_int = int(display_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid display_id format")

    display = db.query(CustomerDisplay).filter(
        CustomerDisplay.id == display_id_int
    ).first()

    if not display:
        raise HTTPException(status_code=404, detail="Display not found")

    display.display_mode = "order"
    display.current_order_data = order_data
    display.last_seen_at = datetime.utcnow()

    db.commit()

    return {
        "display_id": display.id,
        "mode": "order",
        "order_data": order_data
    }

@router.post("/{venue_id}/displays/{display_id}/payment")
@limiter.limit("30/minute")
async def show_payment_screen(
    request: Request,
    venue_id: int,
    display_id: str,
    total: float = Body(...),
    payment_method: str = Body("card"),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Show payment screen on display in database"""
    verify_venue_access(venue_id, current_user)
    try:
        display_id_int = int(display_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid display_id format")

    display = db.query(CustomerDisplay).filter(
        CustomerDisplay.id == display_id_int
    ).first()

    if not display:
        raise HTTPException(status_code=404, detail="Display not found")

    display.display_mode = "payment"
    display.last_seen_at = datetime.utcnow()

    db.commit()

    return {
        "display_id": display.id,
        "mode": "payment",
        "total": total,
        "payment_method": payment_method
    }

@router.post("/{venue_id}/displays/{display_id}/survey")
@limiter.limit("30/minute")
async def show_survey(
    request: Request,
    venue_id: int,
    display_id: str,
    order_id: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Show survey on display in database"""
    verify_venue_access(venue_id, current_user)
    try:
        display_id_int = int(display_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid display_id format")

    display = db.query(CustomerDisplay).filter(
        CustomerDisplay.id == display_id_int
    ).first()

    if not display:
        raise HTTPException(status_code=404, detail="Display not found")

    display.display_mode = "survey"
    display.last_seen_at = datetime.utcnow()

    db.commit()

    return {
        "display_id": display.id,
        "mode": "survey",
        "order_id": order_id
    }

@router.post("/{venue_id}/displays/{display_id}/idle")
@limiter.limit("30/minute")
async def show_idle_screen(request: Request, venue_id: int, display_id: str, db: Session = Depends(get_db), current_user=Depends(require_manager)):
    """Show idle screen on customer display from database"""
    verify_venue_access(venue_id, current_user)
    try:
        display_id_int = int(display_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid venue_id or display_id format")

    # Query display from database
    display = db.query(CustomerDisplay).filter(
        CustomerDisplay.venue_id == venue_id,
        CustomerDisplay.id == display_id_int,
        CustomerDisplay.is_active == True
    ).first()

    if not display:
        raise HTTPException(status_code=404, detail="Display not found")

    # Update display mode to idle
    display.display_mode = "idle"
    display.last_seen_at = datetime.utcnow()
    db.commit()

    return {
        "display_id": display.id,
        "mode": "idle",
        "idle_content_type": display.idle_content_type,
        "idle_content_config": display.idle_content_config,
        "theme": display.theme,
        "language": display.language
    }


# ============================================================================
# TIER 1: MENU ITEM REVIEWS (6 endpoints)
# ============================================================================

@router.post("/{venue_id}/reviews")
@limiter.limit("30/minute")
async def create_menu_review(
    request: Request,
    venue_id: int,
    menu_item_id: str = Body(...),
    customer_id: str = Body(...),
    order_id: str = Body(...),
    rating: int = Body(...),
    review_text: str = Body(""),
    would_order_again: bool = Body(True),
    taste_rating: Optional[int] = Body(None),
    presentation_rating: Optional[int] = Body(None),
    portion_rating: Optional[int] = Body(None),
    value_rating: Optional[int] = Body(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Create menu item review in database"""
    verify_venue_access(venue_id, current_user)
    try:
        menu_item_id_int = int(menu_item_id)
        customer_id_int = int(customer_id)
        order_id_int = int(order_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    # Validate rating
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    review = MenuItemReview(
        venue_id=venue_id,
        menu_item_id=menu_item_id_int,
        customer_id=customer_id_int,
        order_id=order_id_int,
        rating=rating,
        review_text=review_text,
        would_order_again=would_order_again,
        taste_rating=taste_rating,
        presentation_rating=presentation_rating,
        portion_rating=portion_rating,
        value_rating=value_rating,
        status="pending",
        verified_purchase=True,
        created_at=datetime.utcnow()
    )

    db.add(review)
    db.commit()
    db.refresh(review)

    # Update aggregate stats
    aggregate = db.query(MenuItemRatingAggregate).filter(
        MenuItemRatingAggregate.menu_item_id == menu_item_id_int
    ).first()

    if aggregate:
        total = aggregate.total_reviews or 0
        avg = aggregate.average_rating or 0
        new_avg = ((avg * total) + rating) / (total + 1)
        aggregate.average_rating = round(new_avg, 2)
        aggregate.total_reviews = total + 1
    else:
        aggregate = MenuItemRatingAggregate(
            menu_item_id=menu_item_id_int,
            average_rating=float(rating),
            total_reviews=1
        )
        db.add(aggregate)

    db.commit()

    return {"review_id": review.id, "rating": review.rating}

@router.get("/{venue_id}/reviews/item/{menu_item_id}")
@limiter.limit("60/minute")
async def get_item_reviews(request: Request, venue_id: int, menu_item_id: str, page: int = Query(1), limit: int = Query(10), db: Session = Depends(get_db)):
    """Get reviews for a menu item from database"""
    try:
        menu_item_id_int = int(menu_item_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid venue_id or menu_item_id format")

    offset = (page - 1) * limit

    # Query reviews from database
    reviews = db.query(MenuItemReview).filter(
        MenuItemReview.venue_id == venue_id,
        MenuItemReview.menu_item_id == menu_item_id_int,
        MenuItemReview.status == "approved"
    ).order_by(MenuItemReview.created_at.desc()).offset(offset).limit(limit).all()

    # Get total count
    total = db.query(func.count(MenuItemReview.id)).filter(
        MenuItemReview.venue_id == venue_id,
        MenuItemReview.menu_item_id == menu_item_id_int,
        MenuItemReview.status == "approved"
    ).scalar() or 0

    # Get aggregate stats
    aggregate = db.query(MenuItemRatingAggregate).filter(
        MenuItemRatingAggregate.menu_item_id == menu_item_id_int
    ).first()

    return {
        "reviews": [
            {
                "id": r.id,
                "customer_id": r.customer_id,
                "rating": r.rating,
                "review_text": r.review_text,
                "taste_rating": r.taste_rating,
                "presentation_rating": r.presentation_rating,
                "portion_rating": r.portion_rating,
                "value_rating": r.value_rating,
                "photo_urls": r.photo_urls or [],
                "helpful_count": r.helpful_count,
                "response_text": r.response_text,
                "verified_purchase": r.verified_purchase,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in reviews
        ],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
        "average_rating": aggregate.average_rating if aggregate else None,
        "total_reviews": aggregate.total_reviews if aggregate else 0
    }

@router.post("/{venue_id}/reviews/{review_id}/approve")
@limiter.limit("30/minute")
async def approve_review(
    request: Request,
    venue_id: int,
    review_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Approve a review in database"""
    verify_venue_access(venue_id, current_user)
    try:
        review_id_int = int(review_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid review_id format")

    review = db.query(MenuItemReview).filter(
        MenuItemReview.id == review_id_int
    ).first()

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    review.status = "approved"
    review.approved_at = datetime.utcnow()

    db.commit()
    db.refresh(review)

    return {"review_id": review.id, "is_approved": True}

@router.post("/{venue_id}/reviews/{review_id}/respond")
@limiter.limit("30/minute")
async def respond_to_review(
    request: Request,
    venue_id: int,
    review_id: str,
    response: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Respond to a review in database"""
    verify_venue_access(venue_id, current_user)
    try:
        review_id_int = int(review_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid review_id format")

    review = db.query(MenuItemReview).filter(
        MenuItemReview.id == review_id_int
    ).first()

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    review.response_text = response
    review.response_at = datetime.utcnow()

    db.commit()
    db.refresh(review)

    return {"review_id": review.id, "response": review.response_text}

@router.post("/{venue_id}/reviews/{review_id}/helpful")
@limiter.limit("30/minute")
async def vote_review_helpful(
    request: Request,
    venue_id: int,
    review_id: str,
    customer_id: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Vote review as helpful in database"""
    verify_venue_access(venue_id, current_user)
    try:
        review_id_int = int(review_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid review_id format")

    review = db.query(MenuItemReview).filter(
        MenuItemReview.id == review_id_int
    ).first()

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    review.helpful_count = (review.helpful_count or 0) + 1

    db.commit()
    db.refresh(review)

    return {"review_id": review.id, "helpful_votes": review.helpful_count}

@router.post("/{venue_id}/reviews/prompts")
@limiter.limit("30/minute")
async def get_review_prompts(
    request: Request,
    venue_id: int,
    order_id: str = Body(...),
    order_items: List[Dict] = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Get review prompts for order items"""
    verify_venue_access(venue_id, current_user)
    prompts = []
    for item in order_items:
        item_id = item.get("menu_item_id")
        item_name = item.get("name", "this item")
        prompts.append({
            "menu_item_id": item_id,
            "name": item_name,
            "questions": [
                "How was the taste?",
                "Was the portion size adequate?",
                "Would you order this again?"
            ]
        })
    return {"prompts": prompts}


# ============================================================================
# TIER 1: SMART PREP TIME (3 endpoints)
# ============================================================================

@router.post("/{venue_id}/prep-time/record")
@limiter.limit("30/minute")
async def record_prep_time(
    request: Request,
    venue_id: int,
    menu_item_id: str = Body(...),
    actual_time: int = Body(...),
    order_complexity: int = Body(1),
    kitchen_load: float = Body(0.5),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Record actual prep time in database"""
    verify_venue_access(venue_id, current_user)
    try:
        menu_item_id_int = int(menu_item_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    # Record the prep time
    record = PrepTimeModel(
        venue_id=venue_id,
        menu_item_id=menu_item_id_int,
        actual_time_seconds=actual_time,
        order_complexity=order_complexity,
        kitchen_load_factor=kitchen_load,
        recorded_at=datetime.utcnow()
    )

    db.add(record)
    db.commit()

    return {"recorded": True, "record_id": record.id}

@router.post("/{venue_id}/prep-time/estimate")
@limiter.limit("30/minute")
async def estimate_prep_time(
    request: Request,
    venue_id: int,
    order_items: List[Dict] = Body(...),
    is_delivery: bool = Body(False),
    is_priority: bool = Body(False),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Estimate prep time from database historical data"""
    verify_venue_access(venue_id, current_user)
    total_time = 0
    item_estimates = []

    for item in order_items:
        item_id = item.get("menu_item_id")
        quantity = item.get("quantity", 1)

        if item_id:
            try:
                item_id_int = int(item_id)
                # Get average prep time from history
                avg_time = db.query(func.avg(PrepTimeModel.actual_time_seconds)).filter(
                    PrepTimeModel.venue_id == venue_id,
                    PrepTimeModel.menu_item_id == item_id_int
                ).scalar()

                if avg_time:
                    item_time = int(avg_time) * quantity
                else:
                    item_time = 300 * quantity  # Default 5 min per item
            except ValueError:
                item_time = 300 * quantity
        else:
            item_time = 300 * quantity

        total_time += item_time
        item_estimates.append({
            "menu_item_id": item_id,
            "quantity": quantity,
            "estimated_seconds": item_time
        })

    # Apply modifiers
    if is_delivery:
        total_time = int(total_time * 1.1)  # 10% buffer for delivery
    if is_priority:
        total_time = int(total_time * 0.85)  # Priority orders faster

    return {
        "total_estimated_seconds": total_time,
        "estimated_minutes": round(total_time / 60, 1),
        "items": item_estimates,
        "is_delivery": is_delivery,
        "is_priority": is_priority
    }

@router.post("/{venue_id}/prep-time/kitchen-load")
@limiter.limit("30/minute")
async def update_kitchen_load(
    request: Request,
    venue_id: int,
    active_orders: int = Body(...),
    max_capacity: int = Body(20),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Update kitchen load in database"""
    verify_venue_access(venue_id, current_user)
    load_factor = min(1.0, active_orders / max(1, max_capacity))

    # Calculate delay based on load
    if load_factor > 0.9:
        delay_multiplier = 1.5
        status = "overloaded"
    elif load_factor > 0.7:
        delay_multiplier = 1.25
        status = "busy"
    elif load_factor > 0.5:
        delay_multiplier = 1.1
        status = "moderate"
    else:
        delay_multiplier = 1.0
        status = "normal"

    return {
        "venue_id": venue_id,
        "active_orders": active_orders,
        "max_capacity": max_capacity,
        "load_factor": round(load_factor, 2),
        "status": status,
        "delay_multiplier": delay_multiplier
    }


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
        valid_from=datetime.utcnow(),
        valid_until=datetime.utcnow() + timedelta(days=valid_days),
        is_used=False,
        created_at=datetime.utcnow()
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
        valid_from=datetime.utcnow(),
        valid_until=datetime.utcnow() + timedelta(days=valid_days),
        total_codes=quantity,
        is_active=True,
        created_at=datetime.utcnow()
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
            valid_from=datetime.utcnow(),
            valid_until=datetime.utcnow() + timedelta(days=valid_days),
            is_used=False,
            created_at=datetime.utcnow()
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
    now = datetime.utcnow()
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
    promo.used_at = datetime.utcnow()

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
            created_at=datetime.utcnow()
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
        created_at=datetime.utcnow()
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
    referral.rewarded_at = datetime.utcnow()
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

@router.post("/{venue_id}/rfm/configure")
@limiter.limit("30/minute")
async def configure_rfm(
    request: Request,
    venue_id: int,
    recency_bins: List[int] = Body(None),
    frequency_bins: List[int] = Body(None),
    monetary_bins: List[float] = Body(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Configure RFM settings in database"""
    verify_venue_access(venue_id, current_user)
    # Default bins
    default_recency = recency_bins or [7, 30, 60, 90, 180]
    default_frequency = frequency_bins or [1, 3, 5, 10, 20]
    default_monetary = monetary_bins or [50, 100, 250, 500, 1000]

    # Check for existing segment definitions
    existing = db.query(RFMSegmentDefinition).filter(
        RFMSegmentDefinition.venue_id == venue_id
    ).first()

    if existing:
        existing.recency_bins = default_recency
        existing.frequency_bins = default_frequency
        existing.monetary_bins = default_monetary
    else:
        config = RFMSegmentDefinition(
            venue_id=venue_id,
            segment_name="default",
            recency_bins=default_recency,
            frequency_bins=default_frequency,
            monetary_bins=default_monetary,
            is_active=True
        )
        db.add(config)

    db.commit()

    return {
        "venue_id": venue_id,
        "recency_bins": default_recency,
        "frequency_bins": default_frequency,
        "monetary_bins": default_monetary,
        "configured": True
    }

@router.post("/{venue_id}/rfm/calculate/{customer_id}")
@limiter.limit("30/minute")
async def calculate_customer_rfm(
    request: Request,
    venue_id: int,
    customer_id: str,
    orders: List[Dict] = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Calculate and store customer RFM score in database"""
    verify_venue_access(venue_id, current_user)
    try:
        customer_id_int = int(customer_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    if not orders:
        return {"customer_id": customer_id, "error": "No orders provided"}

    # Calculate RFM metrics
    now = datetime.utcnow()
    order_dates = [datetime.fromisoformat(o.get("order_date", o.get("date", now.isoformat()))) for o in orders if o.get("order_date") or o.get("date")]
    order_amounts = [float(o.get("total", o.get("amount", 0))) for o in orders]

    if order_dates:
        most_recent = max(order_dates)
        recency_days = (now - most_recent).days
    else:
        recency_days = 999

    frequency = len(orders)
    monetary = sum(order_amounts)

    # Calculate RFM scores (1-5 scale)
    def score_recency(days):
        if days <= 7: return 5
        if days <= 30: return 4
        if days <= 60: return 3
        if days <= 90: return 2
        return 1

    def score_frequency(count):
        if count >= 20: return 5
        if count >= 10: return 4
        if count >= 5: return 3
        if count >= 3: return 2
        return 1

    def score_monetary(amount):
        if amount >= 1000: return 5
        if amount >= 500: return 4
        if amount >= 250: return 3
        if amount >= 100: return 2
        return 1

    r_score = score_recency(recency_days)
    f_score = score_frequency(frequency)
    m_score = score_monetary(monetary)

    rfm_score = f"{r_score}{f_score}{m_score}"

    # Determine segment
    total_score = r_score + f_score + m_score
    if total_score >= 13:
        segment = "champions"
    elif total_score >= 10:
        segment = "loyal_customers"
    elif r_score >= 4:
        segment = "potential_loyalists"
    elif r_score <= 2 and f_score >= 3:
        segment = "at_risk"
    elif r_score <= 2:
        segment = "hibernating"
    else:
        segment = "promising"

    # Store in database
    existing = db.query(CustomerRFMScore).filter(
        CustomerRFMScore.venue_id == venue_id,
        CustomerRFMScore.customer_id == customer_id_int
    ).first()

    if existing:
        existing.recency_score = r_score
        existing.frequency_score = f_score
        existing.monetary_score = m_score
        existing.rfm_score = rfm_score
        existing.segment = segment
        existing.days_since_last_order = recency_days
        existing.total_orders = frequency
        existing.total_revenue = Decimal(str(monetary))
        existing.calculated_at = now
    else:
        rfm = CustomerRFMScore(
            venue_id=venue_id,
            customer_id=customer_id_int,
            recency_score=r_score,
            frequency_score=f_score,
            monetary_score=m_score,
            rfm_score=rfm_score,
            segment=segment,
            days_since_last_order=recency_days,
            total_orders=frequency,
            total_revenue=Decimal(str(monetary)),
            calculated_at=now
        )
        db.add(rfm)

    db.commit()

    return {
        "customer_id": customer_id,
        "rfm_score": rfm_score,
        "segment": segment,
        "recency_days": recency_days,
        "frequency": frequency,
        "monetary": round(monetary, 2)
    }

@router.get("/{venue_id}/rfm/segments")
@limiter.limit("60/minute")
async def get_rfm_segments(request: Request, venue_id: int, db: Session = Depends(get_db)):
    """Get distribution of customers across RFM segments from database"""
    # Query segment distribution from database
    segment_counts = db.query(
        CustomerRFMScore.segment,
        func.count(CustomerRFMScore.id).label('count')
    ).filter(
        CustomerRFMScore.venue_id == venue_id
    ).group_by(CustomerRFMScore.segment).all()

    total_customers = sum(count for _, count in segment_counts)

    if total_customers == 0:
        return {"total_customers": 0, "segments": {}}

    segments = {}
    for segment, count in segment_counts:
        segments[segment] = {
            "count": count,
            "percentage": round(count / total_customers * 100, 1)
        }

    return {
        "total_customers": total_customers,
        "segments": segments,
        "calculated_at": datetime.utcnow().isoformat()
    }

@router.get("/{venue_id}/rfm/segments/{segment}/customers")
@limiter.limit("60/minute")
async def get_segment_customers(request: Request, venue_id: int, segment: str, limit: int = Query(100), db: Session = Depends(get_db)):
    """Get customers in a specific RFM segment from database"""
    # Query customers in segment from database
    customers = db.query(CustomerRFMScore).filter(
        CustomerRFMScore.venue_id == venue_id,
        CustomerRFMScore.segment == segment
    ).order_by(CustomerRFMScore.total_revenue.desc()).limit(limit).all()

    return [
        {
            "customer_id": c.customer_id,
            "recency_days": c.days_since_last_order,
            "frequency": c.total_orders,
            "monetary": float(c.total_revenue) if c.total_revenue else 0,
            "rfm_score": c.rfm_score
        }
        for c in customers
    ]

@router.get("/{venue_id}/rfm/segments/{segment}/recommendations")
@limiter.limit("60/minute")
async def get_segment_recommendations(
    request: Request,
    venue_id: int,
    segment: str,
    db: Session = Depends(get_db)
):
    """Get marketing recommendations for RFM segment"""
    recommendations = {
        "champions": {
            "segment": "champions",
            "description": "Best customers - highest value, most engaged",
            "actions": [
                "Offer exclusive VIP benefits",
                "Early access to new menu items",
                "Personal thank you notes",
                "Invite to exclusive events"
            ],
            "discount_recommendation": "5-10% loyalty rewards"
        },
        "loyal_customers": {
            "segment": "loyal_customers",
            "description": "Regular customers with high value",
            "actions": [
                "Upsell premium items",
                "Loyalty program bonuses",
                "Birthday special offers"
            ],
            "discount_recommendation": "10-15% on special occasions"
        },
        "potential_loyalists": {
            "segment": "potential_loyalists",
            "description": "Recent customers with growth potential",
            "actions": [
                "Send personalized recommendations",
                "Invite to loyalty program",
                "Offer incentives for repeat visits"
            ],
            "discount_recommendation": "15% next visit discount"
        },
        "at_risk": {
            "segment": "at_risk",
            "description": "Previously active customers showing decline",
            "actions": [
                "Win-back campaign",
                "Survey for feedback",
                "Strong discount incentive"
            ],
            "discount_recommendation": "25-30% win-back offer"
        },
        "hibernating": {
            "segment": "hibernating",
            "description": "Inactive customers",
            "actions": [
                "Re-engagement email campaign",
                "Major promotional offer",
                "New menu announcements"
            ],
            "discount_recommendation": "30-40% reactivation offer"
        },
        "promising": {
            "segment": "promising",
            "description": "New or occasional customers",
            "actions": [
                "Welcome series",
                "Loyalty program invitation",
                "First purchase follow-up"
            ],
            "discount_recommendation": "20% second visit discount"
        }
    }

    return recommendations.get(segment, {
        "segment": segment,
        "description": "Unknown segment",
        "actions": ["Review customer data"],
        "discount_recommendation": "Standard promotions"
    })


# ============================================================================
# TIER 2: PRICE TRACKER (4 endpoints)
# ============================================================================

@router.post("/{venue_id}/price-tracker/record")
@limiter.limit("30/minute")
async def record_ingredient_price(
    request: Request,
    venue_id: int,
    ingredient_id: str = Body(...),
    supplier_id: str = Body(...),
    unit_price: float = Body(...),
    quantity: float = Body(1),
    unit: str = Body("kg"),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Record ingredient price in database"""
    verify_venue_access(venue_id, current_user)
    try:
        ingredient_id_int = int(ingredient_id)
        supplier_id_int = int(supplier_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    record = IngredientPriceHistory(
        venue_id=venue_id,
        stock_item_id=ingredient_id_int,
        supplier_id=supplier_id_int,
        price=Decimal(str(unit_price)),
        quantity=Decimal(str(quantity)),
        unit=unit,
        recorded_date=datetime.utcnow().date()
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return {"record_id": record.id, "unit_price": float(record.price)}

@router.post("/{venue_id}/price-tracker/alerts")
@limiter.limit("30/minute")
async def create_price_alert(
    request: Request,
    venue_id: int,
    ingredient_id: str = Body(...),
    alert_type: str = Body(...),
    threshold_percentage: float = Body(10.0),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Create price alert in database"""
    verify_venue_access(venue_id, current_user)
    try:
        ingredient_id_int = int(ingredient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    alert = PriceAlert(
        venue_id=venue_id,
        stock_item_id=ingredient_id_int,
        alert_type=alert_type,
        threshold_percentage=Decimal(str(threshold_percentage)),
        is_active=True,
        created_at=datetime.utcnow()
    )

    db.add(alert)
    db.commit()
    db.refresh(alert)

    return {"alert_id": alert.id}

@router.get("/{venue_id}/price-tracker/{ingredient_id}/history")
@limiter.limit("60/minute")
async def get_price_history(request: Request, venue_id: int, ingredient_id: str, days: int = Query(90), db: Session = Depends(get_db)):
    """Get price history for an ingredient from database"""
    try:
        ingredient_id_int = int(ingredient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid venue_id or ingredient_id format")

    cutoff = datetime.utcnow() - timedelta(days=days)

    # Query price history from database
    records = db.query(IngredientPriceHistory).filter(
        IngredientPriceHistory.venue_id == venue_id,
        IngredientPriceHistory.stock_item_id == ingredient_id_int,
        IngredientPriceHistory.recorded_date >= cutoff.date()
    ).order_by(IngredientPriceHistory.recorded_date.asc()).all()

    if not records:
        return {
            "ingredient_id": ingredient_id,
            "records": [],
            "statistics": None
        }

    prices = [float(r.price) for r in records]

    # Calculate statistics
    current_price = prices[-1] if prices else 0
    avg_price = sum(prices) / len(prices) if prices else 0
    min_price = min(prices) if prices else 0
    max_price = max(prices) if prices else 0

    # Calculate price changes
    def calculate_change(days_back: int) -> Optional[float]:
        if len(records) < 2:
            return None
        cutoff_date = datetime.utcnow().date() - timedelta(days=days_back)
        old_records = [r for r in records if r.recorded_date >= cutoff_date]
        if len(old_records) < 2:
            return None
        old_price = float(old_records[0].price)
        new_price = float(old_records[-1].price)
        if old_price == 0:
            return None
        return round(((new_price - old_price) / old_price) * 100, 2)

    # Calculate volatility (standard deviation)
    if len(prices) > 1:
        mean = sum(prices) / len(prices)
        variance = sum((p - mean) ** 2 for p in prices) / len(prices)
        volatility = variance ** 0.5
    else:
        volatility = 0

    return {
        "ingredient_id": ingredient_id,
        "records": [
            {
                "price": float(r.price),
                "supplier_id": r.supplier_id,
                "date": r.recorded_date.isoformat()
            }
            for r in records
        ],
        "statistics": {
            "current_price": round(current_price, 2),
            "average_price": round(avg_price, 2),
            "min_price": round(min_price, 2),
            "max_price": round(max_price, 2),
            "price_change_30d": calculate_change(30),
            "price_change_90d": calculate_change(90),
            "volatility": round(volatility, 2)
        }
    }

@router.get("/{venue_id}/price-tracker/{ingredient_id}/compare")
@limiter.limit("60/minute")
async def compare_supplier_prices(
    request: Request,
    venue_id: int,
    ingredient_id: str,
    db: Session = Depends(get_db)
):
    """Compare prices across suppliers from database"""
    try:
        ingredient_id_int = int(ingredient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    # Get most recent prices by supplier
    from sqlalchemy import distinct

    # Get all suppliers for this ingredient
    supplier_ids = db.query(distinct(IngredientPriceHistory.supplier_id)).filter(
        IngredientPriceHistory.venue_id == venue_id,
        IngredientPriceHistory.stock_item_id == ingredient_id_int
    ).all()

    comparisons = []
    for (supplier_id,) in supplier_ids:
        # Get most recent price for this supplier
        latest = db.query(IngredientPriceHistory).filter(
            IngredientPriceHistory.venue_id == venue_id,
            IngredientPriceHistory.stock_item_id == ingredient_id_int,
            IngredientPriceHistory.supplier_id == supplier_id
        ).order_by(IngredientPriceHistory.recorded_date.desc()).first()

        if latest:
            comparisons.append({
                "supplier_id": supplier_id,
                "price": float(latest.price),
                "unit": latest.unit,
                "last_updated": latest.recorded_date.isoformat()
            })

    # Sort by price
    comparisons.sort(key=lambda x: x["price"])

    best_price = comparisons[0]["price"] if comparisons else 0

    return {
        "ingredient_id": ingredient_id,
        "comparisons": comparisons,
        "best_price": best_price,
        "recommended_supplier_id": comparisons[0]["supplier_id"] if comparisons else None
    }


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
            created_at=datetime.utcnow()
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
            created_at=datetime.utcnow()
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
            created_at=datetime.utcnow()
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
    brk.actual_start = datetime.utcnow()

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
    brk.actual_end = datetime.utcnow()

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

    dt = datetime.fromisoformat(date) if date else datetime.utcnow()
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
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(hours=48)
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

    trade.responded_at = datetime.utcnow()

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
    trade.approved_at = datetime.utcnow()

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
        existing.assigned_date = datetime.utcnow()
        existing.is_active = True
    else:
        vip_status = CustomerVIPStatus(
            venue_id=venue_id,
            customer_id=customer_id_int,
            vip_tier_id=tier_model.id,
            assigned_by_id=assigned_by_int,
            assigned_date=datetime.utcnow(),
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
        current_status.assigned_date = datetime.utcnow()
    else:
        vip_status = CustomerVIPStatus(
            venue_id=venue_id,
            customer_id=customer_id_int,
            vip_tier_id=new_tier.id,
            assigned_date=datetime.utcnow(),
            is_active=True
        )
        db.add(vip_status)

    db.commit()

    return {
        "customer_id": customer_id,
        "new_tier": new_tier.name,
        "upgraded": True
    }

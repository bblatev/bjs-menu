"""
BJS V7 API Endpoints - Tier 3 Enhancement Features
"""

from fastapi import APIRouter, HTTPException, Query, Body, Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from enum import Enum

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.missing_features_models import (
    GuestbookEntry, GuestbookVisit,
    FundraisingCampaign, FundraisingDonation,
    ChargebackCase, ChargebackEvidence,
    TaxConfiguration, TaxSummary,
    EmployeeOnboarding, MenuPairingRule,
    ThirdPartyGiftCardConfig, ThirdPartyGiftCardTransaction,
    TableBlock,
)


router = APIRouter(tags=["V7 Tier 3"])

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
# TIER 3: GUESTBOOK (4 endpoints)
# ============================================================================

@router.get("/")
@limiter.limit("60/minute")
async def get_v7_tier3_root(request: Request, db: Session = Depends(get_db)):
    """V7 Tier 3 API features status."""
    return {"module": "v7-tier3", "version": "7.0-tier3", "status": "active", "features": ["guestbook", "fundraising", "chargebacks", "analytics"]}


@router.post("/{venue_id}/guestbook")
@limiter.limit("30/minute")
async def create_guest(
    request: Request,
    venue_id: int,
    first_name: str = Body(...),
    last_name: str = Body(...),
    email: str = Body(...),
    phone: str = Body(""),
    birthday: Optional[datetime] = Body(None),
    dietary_preferences: List[str] = Body([]),
    allergies: List[str] = Body([]),
    db: Session = Depends(get_db)
):
    """Create guest entry in database"""
    guest = GuestbookEntry(
        venue_id=venue_id,
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone,
        birthday=birthday.date() if birthday else None,
        dietary_preferences=dietary_preferences,
        allergies=allergies,
        visit_count=0,
        created_at=datetime.now(timezone.utc)
    )

    db.add(guest)
    db.commit()
    db.refresh(guest)

    return {"guest_id": guest.id, "name": f"{guest.first_name} {guest.last_name}"}

@router.post("/{venue_id}/guestbook/{guest_id}/visit")
@limiter.limit("30/minute")
async def record_guest_visit(
    request: Request,
    venue_id: int,
    guest_id: str,
    party_size: int = Body(...),
    table_number: Optional[str] = Body(None),
    spend_amount: float = Body(0),
    db: Session = Depends(get_db)
):
    """Record guest visit in database"""
    try:
        guest_id_int = int(guest_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    guest = db.query(GuestbookEntry).filter(
        GuestbookEntry.id == guest_id_int
    ).first()

    if not guest:
        raise HTTPException(status_code=404, detail="Guest not found")

    visit = GuestbookVisit(
        guestbook_entry_id=guest_id_int,
        venue_id=venue_id,
        visit_date=datetime.now(timezone.utc),
        party_size=party_size,
        table_number=table_number,
        spend_amount=Decimal(str(spend_amount))
    )

    db.add(visit)

    # Update guest stats
    guest.visit_count = (guest.visit_count or 0) + 1
    guest.last_visit_date = datetime.now(timezone.utc)
    guest.total_spend = (guest.total_spend or Decimal("0")) + Decimal(str(spend_amount))

    db.commit()
    db.refresh(visit)

    return {"visit_id": visit.id}

@router.get("/{venue_id}/guestbook/search")
@limiter.limit("60/minute")
async def search_guests(
    request: Request,
    venue_id: int,
    query: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    min_visits: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Search guests in database"""
    q = db.query(GuestbookEntry).filter(GuestbookEntry.venue_id == venue_id)

    if query:
        search_term = f"%{query}%"
        q = q.filter(
            (GuestbookEntry.guest_name.ilike(search_term)) |
            (GuestbookEntry.guest_email.ilike(search_term)) |
            (GuestbookEntry.message.ilike(search_term))
        )

    if min_visits:
        q = q.filter(GuestbookEntry.rating >= min_visits)

    guests = q.order_by(GuestbookEntry.visit_date.desc()).limit(50).all()

    return {
        "guests": [
            {
                "id": g.id,
                "name": g.guest_name or "Unknown",
                "email": g.guest_email,
                "visit_count": g.rating or 0
            }
            for g in guests
        ]
    }

@router.get("/{venue_id}/guestbook/{guest_id}")
@limiter.limit("60/minute")
async def get_guest_history(
    request: Request,
    venue_id: int,
    guest_id: str,
    db: Session = Depends(get_db)
):
    """Get guest history from database"""
    try:
        guest_id_int = int(guest_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid guest_id format")

    guest = db.query(GuestbookEntry).filter(
        GuestbookEntry.id == guest_id_int
    ).first()

    if not guest:
        raise HTTPException(status_code=404, detail="Guest not found")

    visits = db.query(GuestbookVisit).filter(
        GuestbookVisit.guestbook_entry_id == guest_id_int
    ).order_by(GuestbookVisit.visit_date.desc()).limit(20).all()

    return {
        "guest": {
            "id": guest.id,
            "first_name": guest.first_name,
            "last_name": guest.last_name,
            "email": guest.email,
            "phone": guest.phone,
            "birthday": guest.birthday.isoformat() if guest.birthday else None,
            "dietary_preferences": guest.dietary_preferences or [],
            "allergies": guest.allergies or [],
            "visit_count": guest.visit_count or 0,
            "total_spend": float(guest.total_spend) if guest.total_spend else 0
        },
        "visits": [
            {
                "id": v.id,
                "date": v.visit_date.isoformat() if v.visit_date else None,
                "party_size": v.party_size,
                "table_number": v.table_number,
                "spend_amount": float(v.spend_amount) if v.spend_amount else 0
            }
            for v in visits
        ]
    }


# ============================================================================
# TIER 3: FUNDRAISING (5 endpoints)
# ============================================================================

@router.post("/{venue_id}/fundraising/campaigns")
@limiter.limit("30/minute")
async def create_fundraising_campaign(
    request: Request,
    venue_id: int,
    charity_name: str = Body(...),
    charity_description: str = Body(...),
    charity_ein: str = Body(...),
    goal_amount: float = Body(...),
    duration_days: int = Body(30),
    matching_enabled: bool = Body(False),
    db: Session = Depends(get_db)
):
    """Create fundraising campaign in database"""
    campaign = FundraisingCampaign(
        venue_id=venue_id,
        charity_name=charity_name,
        charity_description=charity_description,
        charity_ein=charity_ein,
        goal_amount=Decimal(str(goal_amount)),
        start_date=datetime.now(timezone.utc),
        end_date=datetime.now(timezone.utc) + timedelta(days=duration_days),
        matching_enabled=matching_enabled,
        status="draft",
        raised_amount=Decimal("0"),
        created_at=datetime.now(timezone.utc)
    )

    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    return {"campaign_id": campaign.id, "charity": campaign.charity_name}

@router.post("/{venue_id}/fundraising/campaigns/{campaign_id}/activate")
@limiter.limit("30/minute")
async def activate_campaign(
    request: Request,
    venue_id: int,
    campaign_id: str,
    db: Session = Depends(get_db)
):
    """Activate fundraising campaign in database"""
    try:
        campaign_id_int = int(campaign_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid campaign_id format")

    campaign = db.query(FundraisingCampaign).filter(
        FundraisingCampaign.id == campaign_id_int
    ).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    campaign.status = "active"

    db.commit()
    db.refresh(campaign)

    return {"campaign_id": campaign.id, "status": campaign.status}

@router.post("/{venue_id}/fundraising/roundup")
@limiter.limit("30/minute")
async def calculate_roundup(
    request: Request,
    venue_id: int,
    order_total: float = Body(...),
    db: Session = Depends(get_db)
):
    """Calculate roundup donation amount"""
    import math
    rounded_up = math.ceil(order_total)
    roundup_amount = rounded_up - order_total

    # If roundup is less than 0.01, round to next dollar
    if roundup_amount < 0.01:
        roundup_amount = 1.0

    return {
        "order_total": round(order_total, 2),
        "rounded_up_total": round(rounded_up, 2),
        "donation_amount": round(roundup_amount, 2)
    }

@router.post("/{venue_id}/fundraising/donate")
@limiter.limit("30/minute")
async def process_donation(
    request: Request,
    venue_id: int,
    order_id: str = Body(...),
    order_total: float = Body(...),
    donation_type: str = Body("roundup"),
    custom_amount: Optional[float] = Body(None),
    db: Session = Depends(get_db)
):
    """Process donation in database"""
    try:
        order_id_int = int(order_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    # Get active campaign
    campaign = db.query(FundraisingCampaign).filter(
        FundraisingCampaign.venue_id == venue_id,
        FundraisingCampaign.status == "active"
    ).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="No active fundraising campaign")

    # Calculate donation amount
    import math
    if donation_type == "roundup":
        rounded = math.ceil(order_total)
        donation_amount = rounded - order_total
        if donation_amount < 0.01:
            donation_amount = 1.0
    else:
        donation_amount = custom_amount or 0

    donation = FundraisingDonation(
        venue_id=venue_id,
        campaign_id=campaign.id,
        order_id=order_id_int,
        donation_amount=Decimal(str(donation_amount)),
        donation_type=donation_type,
        order_total=Decimal(str(order_total)),
        created_at=datetime.now(timezone.utc)
    )

    db.add(donation)

    # Update campaign total
    campaign.raised_amount = (campaign.raised_amount or Decimal("0")) + Decimal(str(donation_amount))

    db.commit()
    db.refresh(donation)

    return {"donation_id": donation.id, "amount": float(donation.donation_amount)}

@router.get("/{venue_id}/fundraising/campaigns/{campaign_id}/stats")
@limiter.limit("60/minute")
async def get_campaign_stats(
    request: Request,
    venue_id: int,
    campaign_id: str,
    db: Session = Depends(get_db)
):
    """Get campaign statistics from database"""
    try:
        campaign_id_int = int(campaign_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid campaign_id format")

    campaign = db.query(FundraisingCampaign).filter(
        FundraisingCampaign.id == campaign_id_int
    ).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Count donations
    donation_count = db.query(func.count(FundraisingDonation.id)).filter(
        FundraisingDonation.campaign_id == campaign_id_int
    ).scalar() or 0

    avg_donation = db.query(func.avg(FundraisingDonation.donation_amount)).filter(
        FundraisingDonation.campaign_id == campaign_id_int
    ).scalar() or 0

    return {
        "campaign_id": campaign.id,
        "charity_name": campaign.charity_name,
        "goal_amount": float(campaign.goal_amount),
        "raised_amount": float(campaign.raised_amount or 0),
        "progress_percentage": round(float(campaign.raised_amount or 0) / max(1, float(campaign.goal_amount)) * 100, 1),
        "donation_count": donation_count,
        "average_donation": round(float(avg_donation), 2),
        "status": campaign.status,
        "days_remaining": max(0, (campaign.end_date - datetime.now(timezone.utc)).days) if campaign.end_date else None
    }


# ============================================================================
# TIER 3: CHARGEBACK MANAGEMENT (5 endpoints)
# ============================================================================

@router.post("/{venue_id}/chargebacks")
@limiter.limit("30/minute")
async def record_chargeback(
    request: Request,
    venue_id: int,
    order_id: str = Body(...),
    transaction_id: str = Body(...),
    amount: float = Body(...),
    reason: ChargebackReason = Body(...),
    reason_detail: str = Body(""),
    processor_case_id: str = Body(...),
    card_brand: str = Body(...),
    last_four: str = Body(...),
    db: Session = Depends(get_db)
):
    """Record chargeback in database"""
    try:
        order_id_int = int(order_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    # Response due in 7 days
    response_due = datetime.now(timezone.utc) + timedelta(days=7)

    cb = ChargebackCase(
        venue_id=venue_id,
        order_id=order_id_int,
        transaction_id=transaction_id,
        amount=Decimal(str(amount)),
        reason=reason.value,
        reason_detail=reason_detail,
        processor_case_id=processor_case_id,
        card_brand=card_brand,
        last_four_digits=last_four,
        status="received",
        response_due_date=response_due,
        created_at=datetime.now(timezone.utc)
    )

    db.add(cb)
    db.commit()
    db.refresh(cb)

    return {
        "chargeback_id": cb.id,
        "status": cb.status,
        "response_due": cb.response_due_date.isoformat()
    }

@router.get("/{venue_id}/chargebacks/evidence-required/{reason}")
@limiter.limit("60/minute")
async def get_required_evidence(
    request: Request,
    venue_id: int,
    reason: ChargebackReason,
    db: Session = Depends(get_db)
):
    """Get required evidence for chargeback reason"""
    evidence_requirements = {
        "fraud": [
            {"type": "customer_signature", "required": True, "description": "Signed receipt or delivery confirmation"},
            {"type": "avs_cvv_results", "required": True, "description": "Address and CVV verification results"},
            {"type": "ip_address", "required": False, "description": "Customer IP address for online orders"},
            {"type": "order_details", "required": True, "description": "Full order details with timestamps"}
        ],
        "product_not_received": [
            {"type": "delivery_confirmation", "required": True, "description": "Proof of delivery with signature"},
            {"type": "tracking_info", "required": True, "description": "Tracking number and carrier info"},
            {"type": "communication_logs", "required": False, "description": "Customer communication regarding delivery"}
        ],
        "product_not_as_described": [
            {"type": "product_description", "required": True, "description": "Menu item description shown to customer"},
            {"type": "photos", "required": False, "description": "Photos of actual product served"},
            {"type": "refund_policy", "required": True, "description": "Your posted refund/return policy"}
        ],
        "duplicate_charge": [
            {"type": "transaction_records", "required": True, "description": "All related transaction records"},
            {"type": "refund_evidence", "required": False, "description": "Evidence of any refunds issued"}
        ],
        "other": [
            {"type": "order_details", "required": True, "description": "Full order details"},
            {"type": "supporting_docs", "required": False, "description": "Any supporting documentation"}
        ]
    }

    return {
        "reason": reason.value,
        "required_evidence": evidence_requirements.get(reason.value, evidence_requirements["other"])
    }

@router.post("/{venue_id}/chargebacks/{chargeback_id}/evidence")
@limiter.limit("30/minute")
async def submit_chargeback_evidence(
    request: Request,
    venue_id: int,
    chargeback_id: str,
    evidence: List[Dict] = Body(...),
    db: Session = Depends(get_db)
):
    """Submit evidence for chargeback in database"""
    try:
        chargeback_id_int = int(chargeback_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid chargeback_id format")

    cb = db.query(ChargebackCase).filter(
        ChargebackCase.id == chargeback_id_int
    ).first()

    if not cb:
        raise HTTPException(status_code=404, detail="Chargeback case not found")

    for ev in evidence:
        evidence_record = ChargebackEvidence(
            chargeback_case_id=chargeback_id_int,
            evidence_type=ev.get("type"),
            description=ev.get("description"),
            file_url=ev.get("file_url"),
            submitted_at=datetime.now(timezone.utc)
        )
        db.add(evidence_record)

    cb.status = "evidence_submitted"
    cb.evidence_submitted_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(cb)

    return {"chargeback_id": cb.id, "status": cb.status}

@router.post("/{venue_id}/chargebacks/{chargeback_id}/resolve")
@limiter.limit("30/minute")
async def resolve_chargeback(
    request: Request,
    venue_id: int,
    chargeback_id: str,
    won: bool = Body(...),
    notes: str = Body(""),
    db: Session = Depends(get_db)
):
    """Resolve chargeback in database"""
    try:
        chargeback_id_int = int(chargeback_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid chargeback_id format")

    cb = db.query(ChargebackCase).filter(
        ChargebackCase.id == chargeback_id_int
    ).first()

    if not cb:
        raise HTTPException(status_code=404, detail="Chargeback case not found")

    cb.status = "won" if won else "lost"
    cb.resolution_notes = notes
    cb.resolved_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(cb)

    return {"chargeback_id": cb.id, "status": cb.status}

@router.get("/{venue_id}/chargebacks/analytics")
@limiter.limit("60/minute")
async def get_chargeback_analytics(
    request: Request,
    venue_id: int,
    days: int = Query(90),
    db: Session = Depends(get_db)
):
    """Get chargeback analytics from database"""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    chargebacks = db.query(ChargebackCase).filter(
        ChargebackCase.venue_id == venue_id,
        ChargebackCase.created_at >= cutoff
    ).all()

    total_count = len(chargebacks)
    total_amount = sum(float(cb.amount or 0) for cb in chargebacks)
    won_count = len([cb for cb in chargebacks if cb.status == "won"])
    lost_count = len([cb for cb in chargebacks if cb.status == "lost"])
    pending_count = len([cb for cb in chargebacks if cb.status not in ["won", "lost"]])

    reason_breakdown = {}
    for cb in chargebacks:
        reason = cb.reason or "unknown"
        reason_breakdown[reason] = reason_breakdown.get(reason, 0) + 1

    return {
        "period_days": days,
        "total_chargebacks": total_count,
        "total_amount": round(total_amount, 2),
        "won": won_count,
        "lost": lost_count,
        "pending": pending_count,
        "win_rate": round(won_count / max(1, won_count + lost_count) * 100, 1),
        "by_reason": reason_breakdown
    }


# ============================================================================
# TIER 3: TAX CENTER (4 endpoints)
# ============================================================================

@router.post("/{venue_id}/tax/configure")
@limiter.limit("30/minute")
async def configure_taxes(
    request: Request,
    venue_id: int,
    rates: Dict[str, float] = Body(...),
    db: Session = Depends(get_db)
):
    """Configure tax rates in database"""
    # Check for existing config
    config = db.query(TaxConfiguration).filter(
        TaxConfiguration.venue_id == venue_id
    ).first()

    if config:
        config.tax_rates = rates
        config.updated_at = datetime.now(timezone.utc)
    else:
        config = TaxConfiguration(
            venue_id=venue_id,
            tax_rates=rates,
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        db.add(config)

    db.commit()
    db.refresh(config)

    return {
        "config_id": config.id,
        "rates": config.tax_rates
    }

@router.post("/{venue_id}/tax/summary")
@limiter.limit("30/minute")
async def generate_tax_summary(
    request: Request,
    venue_id: int,
    period_type: str = Body(...),
    period_start: datetime = Body(...),
    period_end: datetime = Body(...),
    sales_data: List[Dict] = Body(...),
    db: Session = Depends(get_db)
):
    """Generate tax summary in database"""
    # Calculate totals from sales data
    gross_sales = sum(float(s.get("total", 0)) for s in sales_data)
    tax_collected = sum(float(s.get("tax", 0)) for s in sales_data)
    net_sales = gross_sales - tax_collected

    summary = TaxSummary(
        venue_id=venue_id,
        period_type=period_type,
        period_start=period_start,
        period_end=period_end,
        gross_sales=Decimal(str(gross_sales)),
        net_sales=Decimal(str(net_sales)),
        tax_collected=Decimal(str(tax_collected)),
        created_at=datetime.now(timezone.utc)
    )

    db.add(summary)
    db.commit()
    db.refresh(summary)

    return {
        "summary_id": summary.id,
        "net_sales": float(summary.net_sales),
        "tax_collected": float(summary.tax_collected)
    }

@router.get("/{venue_id}/tax/vat-return")
@limiter.limit("60/minute")
async def generate_vat_return(
    request: Request,
    venue_id: int,
    period_start: Optional[datetime] = Query(None, description="Period start datetime"),
    period_end: Optional[datetime] = Query(None, description="Period end datetime"),
    db: Session = Depends(get_db)
):
    """Generate VAT return data from database"""
    if period_start is None:
        period_start = datetime.now(timezone.utc) - timedelta(days=90)
    if period_end is None:
        period_end = datetime.now(timezone.utc)

    # Get summaries for the period
    summaries = db.query(TaxSummary).filter(
        TaxSummary.venue_id == venue_id,
        TaxSummary.period_start >= period_start,
        TaxSummary.period_end <= period_end
    ).all()

    total_output_vat = sum(float(s.tax_collected or 0) for s in summaries)
    total_sales = sum(float(s.net_sales or 0) for s in summaries)

    return {
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "box1_vat_due_sales": round(total_output_vat, 2),
        "box6_total_sales": round(total_sales, 2),
        "box7_total_purchases": 0,  # Would need purchase data
        "vat_payable": round(total_output_vat, 2)
    }

@router.get("/{venue_id}/tax/export/{year}")
@limiter.limit("60/minute")
async def export_tax_data(
    request: Request,
    venue_id: int,
    year: int,
    db: Session = Depends(get_db)
):
    """Export tax data for year from database"""
    year_start = datetime(year, 1, 1)
    year_end = datetime(year, 12, 31, 23, 59, 59)

    summaries = db.query(TaxSummary).filter(
        TaxSummary.venue_id == venue_id,
        TaxSummary.period_start >= year_start,
        TaxSummary.period_end <= year_end
    ).order_by(TaxSummary.period_start).all()

    monthly_data = []
    for s in summaries:
        monthly_data.append({
            "period": s.period_start.strftime("%Y-%m") if s.period_start else None,
            "gross_sales": float(s.gross_sales or 0),
            "net_sales": float(s.net_sales or 0),
            "tax_collected": float(s.tax_collected or 0)
        })

    total_gross = sum(float(s.gross_sales or 0) for s in summaries)
    total_net = sum(float(s.net_sales or 0) for s in summaries)
    total_tax = sum(float(s.tax_collected or 0) for s in summaries)

    return {
        "year": year,
        "monthly_data": monthly_data,
        "annual_totals": {
            "gross_sales": round(total_gross, 2),
            "net_sales": round(total_net, 2),
            "tax_collected": round(total_tax, 2)
        }
    }


# ============================================================================
# TIER 3: EMPLOYEE ONBOARDING (3 endpoints)
# ============================================================================

@router.post("/{venue_id}/onboarding")
@limiter.limit("30/minute")
async def start_onboarding(
    request: Request,
    venue_id: int,
    employee_id: str = Body(...),
    employee_name: str = Body(...),
    position: str = Body(...),
    start_date: datetime = Body(...),
    mentor_id: Optional[str] = Body(None),
    db: Session = Depends(get_db)
):
    """Start employee onboarding in database"""
    try:
        employee_id_int = int(employee_id)
        mentor_id_int = int(mentor_id) if mentor_id else None
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    # Define default tasks based on position
    default_tasks = [
        {"name": "Complete HR paperwork", "category": "admin", "order": 1},
        {"name": "Review employee handbook", "category": "admin", "order": 2},
        {"name": "System login training", "category": "technical", "order": 3},
        {"name": "Safety training", "category": "safety", "order": 4},
        {"name": "Meet the team", "category": "social", "order": 5},
    ]

    if position.lower() in ["server", "waiter", "waitress"]:
        default_tasks.extend([
            {"name": "Menu knowledge training", "category": "product", "order": 6},
            {"name": "POS system training", "category": "technical", "order": 7},
            {"name": "Shadow experienced server", "category": "practical", "order": 8},
        ])
    elif position.lower() in ["cook", "chef", "kitchen"]:
        default_tasks.extend([
            {"name": "Food safety certification", "category": "safety", "order": 6},
            {"name": "Kitchen equipment training", "category": "technical", "order": 7},
            {"name": "Recipe review", "category": "product", "order": 8},
        ])

    onboarding = EmployeeOnboarding(
        venue_id=venue_id,
        employee_id=employee_id_int,
        employee_name=employee_name,
        position=position,
        start_date=start_date,
        mentor_id=mentor_id_int,
        status="in_progress",
        assigned_tasks=default_tasks,
        completed_tasks=[],
        created_at=datetime.now(timezone.utc)
    )

    db.add(onboarding)
    db.commit()
    db.refresh(onboarding)

    return {"onboarding_id": onboarding.id, "tasks": len(onboarding.assigned_tasks)}

@router.post("/{venue_id}/onboarding/{onboarding_id}/complete-task")
@limiter.limit("30/minute")
async def complete_onboarding_task(
    request: Request,
    venue_id: int,
    onboarding_id: str,
    task_id: str = Body(...),
    data: Optional[Dict] = Body(None),
    db: Session = Depends(get_db)
):
    """Complete onboarding task in database"""
    try:
        onboarding_id_int = int(onboarding_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid onboarding_id format")

    onboarding = db.query(EmployeeOnboarding).filter(
        EmployeeOnboarding.id == onboarding_id_int
    ).first()

    if not onboarding:
        raise HTTPException(status_code=404, detail="Onboarding not found")

    # Add task to completed list
    completed = onboarding.completed_tasks or []
    if task_id not in completed:
        completed.append(task_id)
        onboarding.completed_tasks = completed

    # Check if all tasks complete
    assigned = onboarding.assigned_tasks or []
    if len(completed) >= len(assigned):
        onboarding.status = "completed"
        onboarding.completed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(onboarding)

    return {
        "onboarding_id": onboarding.id,
        "status": onboarding.status,
        "completed_tasks": len(onboarding.completed_tasks or [])
    }

@router.get("/{venue_id}/onboarding/{onboarding_id}/progress")
@limiter.limit("60/minute")
async def get_onboarding_progress(
    request: Request,
    venue_id: int,
    onboarding_id: str,
    db: Session = Depends(get_db)
):
    """Get onboarding progress from database"""
    try:
        onboarding_id_int = int(onboarding_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid onboarding_id format")

    onboarding = db.query(EmployeeOnboarding).filter(
        EmployeeOnboarding.id == onboarding_id_int
    ).first()

    if not onboarding:
        raise HTTPException(status_code=404, detail="Onboarding not found")

    assigned = onboarding.assigned_tasks or []
    completed = onboarding.completed_tasks or []

    return {
        "onboarding_id": onboarding.id,
        "employee_name": onboarding.employee_name,
        "position": onboarding.position,
        "status": onboarding.status,
        "start_date": onboarding.start_date.isoformat() if onboarding.start_date else None,
        "total_tasks": len(assigned),
        "completed_tasks": len(completed),
        "progress_percentage": round(len(completed) / max(1, len(assigned)) * 100, 1),
        "tasks": [
            {
                **task,
                "completed": task.get("name") in completed or str(i) in completed
            }
            for i, task in enumerate(assigned)
        ]
    }


# ============================================================================
# TIER 3: MENU PAIRING (3 endpoints)
# ============================================================================

@router.post("/{venue_id}/menu-pairing/analyze")
@limiter.limit("30/minute")
async def analyze_menu_item(
    request: Request,
    venue_id: int,
    item_id: str = Body(...),
    name: str = Body(...),
    category: str = Body(...),
    ingredients: List[str] = Body([]),
    flavor_profile: Optional[Dict] = Body(None),
    db: Session = Depends(get_db)
):
    """Analyze menu item for pairings"""
    # Determine complementary categories based on item category
    pairing_recommendations = {
        "appetizer": ["wine", "cocktail", "beer"],
        "main_course": ["wine", "side_dish", "dessert"],
        "dessert": ["dessert_wine", "coffee", "digestif"],
        "salad": ["wine", "soup", "bread"],
        "soup": ["bread", "salad", "wine"],
        "beverage": ["appetizer", "main_course"],
    }

    # Analyze flavor profile
    default_profile = {
        "sweet": 0,
        "salty": 0,
        "sour": 0,
        "bitter": 0,
        "umami": 0,
        "spicy": 0
    }

    return {
        "item_id": item_id,
        "name": name,
        "category": category,
        "flavor_profile": flavor_profile or default_profile,
        "recommended_pairing_categories": pairing_recommendations.get(category.lower(), ["wine", "beverage"]),
        "ingredients_analyzed": len(ingredients)
    }

@router.post("/{venue_id}/menu-pairing/suggest")
@limiter.limit("30/minute")
async def get_pairing_suggestions(
    request: Request,
    venue_id: int,
    item_id: str = Body(...),
    available_items: List[Dict] = Body(...),
    max_suggestions: int = Body(5),
    db: Session = Depends(get_db)
):
    """Get pairing suggestions for menu item"""
    try:
        item_id_int = int(item_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    # Check for manual pairings first
    manual_pairings = db.query(MenuPairingRule).filter(
        MenuPairingRule.venue_id == venue_id,
        MenuPairingRule.primary_item_id == item_id_int,
        MenuPairingRule.is_active == True
    ).all()

    suggestions = []

    # Add manual pairings
    for pairing in manual_pairings[:max_suggestions]:
        suggestions.append({
            "item_id": pairing.paired_item_id,
            "pairing_type": pairing.pairing_type,
            "reason": pairing.reason,
            "score": 100,
            "source": "manual"
        })

    # Fill with algorithmic suggestions from available items
    remaining = max_suggestions - len(suggestions)
    if remaining > 0:
        for item in available_items[:remaining]:
            suggestions.append({
                "item_id": item.get("id"),
                "name": item.get("name"),
                "category": item.get("category"),
                "score": 75,
                "source": "algorithm"
            })

    return {"suggestions": suggestions[:max_suggestions]}

@router.post("/{venue_id}/menu-pairing/manual")
@limiter.limit("30/minute")
async def create_manual_pairing(
    request: Request,
    venue_id: int,
    item_id: str = Body(...),
    paired_item_id: str = Body(...),
    pairing_type: str = Body(...),
    reason: str = Body(...),
    db: Session = Depends(get_db)
):
    """Create manual menu pairing in database"""
    try:
        item_id_int = int(item_id)
        paired_item_id_int = int(paired_item_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    rule = MenuPairingRule(
        venue_id=venue_id,
        primary_item_id=item_id_int,
        paired_item_id=paired_item_id_int,
        pairing_type=pairing_type,
        reason=reason,
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )

    db.add(rule)
    db.commit()
    db.refresh(rule)

    return {"rule_id": rule.id}


# ============================================================================
# TIER 3: THIRD-PARTY GIFT CARDS (3 endpoints)
# ============================================================================

@router.post("/{venue_id}/third-party-gift-cards/configure")
@limiter.limit("30/minute")
async def configure_third_party_cards(
    request: Request,
    venue_id: int,
    accepted_providers: List[str] = Body(...),
    exchange_rates: Optional[Dict[str, float]] = Body(None),
    db: Session = Depends(get_db)
):
    """Configure third-party gift card providers in database"""
    # Check for existing config
    config = db.query(ThirdPartyGiftCardConfig).filter(
        ThirdPartyGiftCardConfig.venue_id == venue_id
    ).first()

    rates = exchange_rates or {p: 1.0 for p in accepted_providers}

    if config:
        config.accepted_providers = accepted_providers
        config.exchange_rates = rates
    else:
        config = ThirdPartyGiftCardConfig(
            venue_id=venue_id,
            accepted_providers=accepted_providers,
            exchange_rates=rates,
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        db.add(config)

    db.commit()
    db.refresh(config)

    return {
        "config_id": config.id,
        "providers": config.accepted_providers,
        "exchange_rates": config.exchange_rates
    }

@router.post("/{venue_id}/third-party-gift-cards/verify")
@limiter.limit("30/minute")
async def verify_third_party_card(
    request: Request,
    venue_id: int,
    provider: str = Body(...),
    card_number: str = Body(...),
    pin: Optional[str] = Body(None),
    db: Session = Depends(get_db)
):
    """Verify third-party gift card"""
    # Check if provider is configured
    config = db.query(ThirdPartyGiftCardConfig).filter(
        ThirdPartyGiftCardConfig.venue_id == venue_id,
        ThirdPartyGiftCardConfig.is_active == True
    ).first()

    if not config or provider not in (config.accepted_providers or []):
        return {
            "valid": False,
            "error": f"Provider {provider} not accepted"
        }

    # In production, this would call the provider's API
    # For now, simulate verification
    balance = 50.00  # Simulated balance

    exchange_rate = (config.exchange_rates or {}).get(provider, 1.0)

    return {
        "valid": True,
        "provider": provider,
        "card_number_masked": f"****{card_number[-4:]}",
        "balance": balance,
        "exchange_rate": exchange_rate,
        "effective_balance": round(balance * exchange_rate, 2)
    }

@router.post("/{venue_id}/third-party-gift-cards/redeem")
@limiter.limit("30/minute")
async def redeem_third_party_card(
    request: Request,
    venue_id: int,
    provider: str = Body(...),
    card_number: str = Body(...),
    pin: Optional[str] = Body(None),
    order_id: str = Body(...),
    amount_to_apply: float = Body(...),
    db: Session = Depends(get_db)
):
    """Redeem third-party gift card in database"""
    try:
        order_id_int = int(order_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    transaction = ThirdPartyGiftCardTransaction(
        venue_id=venue_id,
        provider=provider,
        card_number_masked=f"****{card_number[-4:]}",
        order_id=order_id_int,
        amount_applied=Decimal(str(amount_to_apply)),
        status="completed",
        transaction_date=datetime.now(timezone.utc)
    )

    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    return {
        "transaction_id": transaction.id,
        "amount_applied": float(transaction.amount_applied),
        "status": transaction.status
    }


# ============================================================================
# TIER 3: TABLE TIME BLOCKING (5 endpoints)
# ============================================================================

@router.post("/{venue_id}/table-blocks")
@limiter.limit("30/minute")
async def create_table_block(
    request: Request,
    venue_id: int,
    table_id: str = Body(...),
    block_type: BlockType = Body(...),
    start_time: datetime = Body(...),
    end_time: datetime = Body(...),
    reason: str = Body(...),
    created_by: str = Body(...),
    recurring: bool = Body(False),
    db: Session = Depends(get_db)
):
    """Create table block in database"""
    try:
        table_id_int = int(table_id)
        created_by_int = int(created_by)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    block = TableBlock(
        venue_id=venue_id,
        table_id=table_id_int,
        block_type=block_type.value,
        start_time=start_time,
        end_time=end_time,
        reason=reason,
        created_by_id=created_by_int,
        is_recurring=recurring,
        status="active",
        created_at=datetime.now(timezone.utc)
    )

    db.add(block)
    db.commit()
    db.refresh(block)

    return {"block_id": block.id}

@router.get("/{venue_id}/table-blocks/{table_id}/availability")
@limiter.limit("60/minute")
async def get_table_availability(
    request: Request,
    venue_id: int,
    table_id: str,
    date: Optional[str] = Query(None, description="Date string (defaults to today)"),
    db: Session = Depends(get_db)
):
    """Get table availability for a date from database"""
    if date is None:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    try:
        table_id_int = int(table_id)
        dt = datetime.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid format")

    day_start = dt.replace(hour=0, minute=0, second=0)
    day_end = dt.replace(hour=23, minute=59, second=59)

    blocks = db.query(TableBlock).filter(
        TableBlock.venue_id == venue_id,
        TableBlock.table_id == table_id_int,
        TableBlock.start_time <= day_end,
        TableBlock.end_time >= day_start
    ).all()

    blocked_times = [
        {
            "start": b.start_time.isoformat(),
            "end": b.end_time.isoformat(),
            "type": b.block_type,
            "reason": b.reason
        }
        for b in blocks
    ]

    return {
        "table_id": table_id,
        "date": date,
        "blocked_times": blocked_times,
        "has_blocks": len(blocked_times) > 0
    }

@router.post("/{venue_id}/table-blocks/check-conflicts")
@limiter.limit("30/minute")
async def check_table_conflicts(
    request: Request,
    venue_id: int,
    table_id: str = Body(...),
    start_time: datetime = Body(...),
    end_time: datetime = Body(...),
    db: Session = Depends(get_db)
):
    """Check for table blocking conflicts in database"""
    try:
        table_id_int = int(table_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    conflicts = db.query(TableBlock).filter(
        TableBlock.venue_id == venue_id,
        TableBlock.table_id == table_id_int,
        TableBlock.start_time < end_time,
        TableBlock.end_time > start_time
    ).all()

    return {
        "conflicts": [
            {
                "block_id": c.id,
                "type": c.block_type,
                "start": c.start_time.isoformat(),
                "end": c.end_time.isoformat(),
                "reason": c.reason
            }
            for c in conflicts
        ],
        "has_conflicts": len(conflicts) > 0
    }

@router.delete("/{venue_id}/table-blocks/{block_id}")
@limiter.limit("30/minute")
async def cancel_table_block(
    request: Request,
    venue_id: int,
    block_id: str,
    db: Session = Depends(get_db)
):
    """Cancel table block in database"""
    try:
        block_id_int = int(block_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid block_id format")

    block = db.query(TableBlock).filter(
        TableBlock.id == block_id_int
    ).first()

    if not block:
        raise HTTPException(status_code=404, detail="Block not found")

    db.delete(block)
    db.commit()

    return {"block_id": block_id_int, "cancelled": True}

@router.get("/{venue_id}/table-blocks")
@limiter.limit("60/minute")
async def get_all_table_blocks(
    request: Request,
    venue_id: int,
    start_date: Optional[datetime] = Query(None, description="Start datetime"),
    end_date: Optional[datetime] = Query(None, description="End datetime"),
    db: Session = Depends(get_db)
):
    """Get all table blocks for a date range from database"""
    if start_date is None:
        start_date = datetime.now(timezone.utc) - timedelta(days=7)
    if end_date is None:
        end_date = datetime.now(timezone.utc)

    blocks = db.query(TableBlock).filter(
        TableBlock.venue_id == venue_id,
        TableBlock.start_time <= end_date,
        TableBlock.end_time >= start_date
    ).order_by(TableBlock.start_time).all()

    return {
        "blocks": [
            {
                "id": b.id,
                "table_id": b.table_id,
                "type": b.block_type,
                "start": b.start_time.isoformat(),
                "end": b.end_time.isoformat(),
                "reason": b.reason,
                "is_recurring": b.is_recurring
            }
            for b in blocks
        ],
        "total": len(blocks)
    }

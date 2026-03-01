"""V5 sub-module: Tax Center & Chargebacks"""
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
from app.api.routes.v5_endpoints._schemas import *

router = APIRouter()

# ==================== TAX CENTER ====================

def calculate_tax_from_orders(db: Session, venue_id: int, start_date: date, end_date: date) -> Dict:
    """
    Calculate tax data from orders within a date range.
    Uses 20% VAT rate (Bulgarian standard rate).
    Tax is calculated as: order_total / 1.20 * 0.20 (tax is included in total)
    """
    VAT_RATE = Decimal("0.20")

    # Query orders within the period for the venue
    orders = db.query(Order).filter(
        Order.venue_id == venue_id,
        Order.created_at >= datetime.combine(start_date, time.min),
        Order.created_at <= datetime.combine(end_date, time.max),
        Order.payment_status == "paid"
    ).all()

    gross_revenue = Decimal("0")
    for order in orders:
        if order.total:
            gross_revenue += Decimal(str(order.total))

    # Calculate net revenue and tax (VAT is included in the total)
    # net_revenue = gross_revenue / 1.20
    # tax_collected = gross_revenue - net_revenue = gross_revenue * 0.20 / 1.20
    net_revenue = gross_revenue / (1 + VAT_RATE)
    tax_collected = gross_revenue - net_revenue

    return {
        "gross_revenue": float(round(gross_revenue, 2)),
        "net_revenue": float(round(net_revenue, 2)),
        "tax_collected": float(round(tax_collected, 2)),
        "order_count": len(orders),
        "vat_rate": float(VAT_RATE)
    }


@router.post("/tax/filings")
@limiter.limit("30/minute")
async def generate_tax_filing(
    request: Request,
    venue_id: int = Query(1),
    period_type: str = Body(...),
    period_start: date = Body(...),
    period_end: date = Body(...),
    db: Session = Depends(get_db)
):
    """Generate tax filing based on actual order data"""
    # Calculate tax from orders
    tax_data = calculate_tax_from_orders(db, venue_id, period_start, period_end)

    # Create TaxReport record
    tax_report = TaxReport(
        venue_id=venue_id,
        report_type="vat",
        period_type=period_type,
        period_start=period_start,
        period_end=period_end,
        gross_revenue=Decimal(str(tax_data["gross_revenue"])),
        net_revenue=Decimal(str(tax_data["net_revenue"])),
        total_tax_collected=Decimal(str(tax_data["tax_collected"])),
        total_tax_owed=Decimal(str(tax_data["tax_collected"])),
        tax_breakdown={"20%": tax_data["tax_collected"]},
        status="draft"
    )

    db.add(tax_report)
    db.commit()
    db.refresh(tax_report)

    return {
        "id": tax_report.id,
        "tax_period": f"{period_type}_{period_start.strftime('%Y_%m')}",
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "gross_revenue": tax_data["gross_revenue"],
        "net_revenue": tax_data["net_revenue"],
        "tax_due": tax_data["tax_collected"],
        "order_count": tax_data["order_count"],
        "vat_rate": tax_data["vat_rate"],
        "status": "draft"
    }


@router.get("/tax/filings")
@limiter.limit("60/minute")
async def get_tax_filings(
    request: Request,
    venue_id: int = Query(1),
    year: int = Query(2025),
    db: Session = Depends(get_db)
):
    """Get tax filings for a venue and year from database"""
    year_start = date(year, 1, 1)
    year_end = date(year, 12, 31)

    filings = db.query(TaxReport).filter(
        TaxReport.venue_id == venue_id,
        TaxReport.period_start >= year_start,
        TaxReport.period_end <= year_end
    ).order_by(TaxReport.period_start.desc()).all()

    return {
        "filings": [
            {
                "id": f.id,
                "report_type": f.report_type,
                "period_type": f.period_type,
                "period_start": f.period_start.isoformat() if f.period_start else None,
                "period_end": f.period_end.isoformat() if f.period_end else None,
                "gross_revenue": float(f.gross_revenue) if f.gross_revenue else 0,
                "net_revenue": float(f.net_revenue) if f.net_revenue else 0,
                "tax_collected": float(f.total_tax_collected) if f.total_tax_collected else 0,
                "tax_owed": float(f.total_tax_owed) if f.total_tax_owed else 0,
                "tax_breakdown": f.tax_breakdown or {},
                "status": f.status,
                "filing_reference": f.filing_reference,
                "submitted_at": f.submitted_at.isoformat() if f.submitted_at else None
            }
            for f in filings
        ],
        "year": year,
        "venue_id": venue_id,
        "total_filings": len(filings)
    }


@router.post("/tax/filings/{filing_id}/submit")
@limiter.limit("30/minute")
async def submit_tax_filing(
    request: Request,
    filing_id: int,
    db: Session = Depends(get_db)
):
    """Submit tax filing - updates status in database"""
    tax_report = db.query(TaxReport).filter(TaxReport.id == filing_id).first()

    if not tax_report:
        raise HTTPException(status_code=404, detail="Tax filing not found")

    if tax_report.status == "submitted":
        raise HTTPException(status_code=400, detail="Tax filing already submitted")

    # Update status and submission info
    tax_report.status = "submitted"
    tax_report.submitted_at = datetime.now(timezone.utc)
    tax_report.filing_reference = f"NRA-{filing_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

    db.commit()
    db.refresh(tax_report)

    return {
        "filing_id": tax_report.id,
        "status": tax_report.status,
        "filing_reference": tax_report.filing_reference,
        "submitted_at": tax_report.submitted_at.isoformat()
    }


@router.get("/tax/summary")
@limiter.limit("60/minute")
async def get_tax_summary(
    request: Request,
    venue_id: int = Query(1),
    year: int = Query(2025),
    db: Session = Depends(get_db)
):
    """Get annual tax summary calculated from actual order data"""
    year_start = date(year, 1, 1)
    year_end = date(year, 12, 31)

    # Calculate total tax from orders for the year
    tax_data = calculate_tax_from_orders(db, venue_id, year_start, year_end)

    # Get submitted filings to calculate what's been paid
    submitted_filings = db.query(TaxReport).filter(
        TaxReport.venue_id == venue_id,
        TaxReport.period_start >= year_start,
        TaxReport.period_end <= year_end,
        TaxReport.status == "submitted"
    ).all()

    total_tax_paid = sum(
        float(f.total_tax_owed) if f.total_tax_owed else 0
        for f in submitted_filings
    )

    total_tax_collected = tax_data["tax_collected"]
    outstanding = total_tax_collected - total_tax_paid

    # Calculate quarterly breakdown
    quarterly_breakdown = []
    for quarter in range(1, 5):
        q_start_month = (quarter - 1) * 3 + 1
        q_end_month = quarter * 3
        q_start = date(year, q_start_month, 1)
        if q_end_month == 12:
            q_end = date(year, 12, 31)
        else:
            q_end = date(year, q_end_month + 1, 1) - timedelta(days=1)

        q_data = calculate_tax_from_orders(db, venue_id, q_start, q_end)
        quarterly_breakdown.append({
            "quarter": f"Q{quarter}",
            "period": f"{q_start.isoformat()} to {q_end.isoformat()}",
            "gross_revenue": q_data["gross_revenue"],
            "tax_collected": q_data["tax_collected"],
            "order_count": q_data["order_count"]
        })

    return {
        "year": year,
        "venue_id": venue_id,
        "total_gross_revenue": tax_data["gross_revenue"],
        "total_net_revenue": tax_data["net_revenue"],
        "total_tax_collected": total_tax_collected,
        "total_tax_paid": total_tax_paid,
        "outstanding": round(outstanding, 2),
        "total_orders": tax_data["order_count"],
        "vat_rate": tax_data["vat_rate"],
        "quarterly_breakdown": quarterly_breakdown,
        "filings_submitted": len(submitted_filings)
    }

# ==================== CHARGEBACKS ====================

@router.post("/chargebacks")
@limiter.limit("30/minute")
async def record_chargeback(
    request: Request,
    chargeback_data: ChargebackCreate,
    venue_id: int = Query(1),
    db: Session = Depends(get_db)
):
    """Record a new chargeback dispute from payment processor"""
    # Calculate response due date (typically 7-21 days depending on provider)
    due_date = datetime.now(timezone.utc) + timedelta(days=10)

    db_chargeback = Chargeback(
        venue_id=venue_id,
        order_id=chargeback_data.order_id,
        payment_id=chargeback_data.payment_id,
        amount=chargeback_data.amount,
        currency=chargeback_data.currency,
        reason_code=chargeback_data.reason_code,
        reason=chargeback_data.reason,
        provider=chargeback_data.provider,
        provider_case_id=chargeback_data.provider_case_id,
        status=ChargebackStatus.RECEIVED.value,
        received_at=datetime.now(timezone.utc),
        due_date=due_date
    )

    db.add(db_chargeback)
    db.commit()
    db.refresh(db_chargeback)

    return {
        "id": db_chargeback.id,
        "venue_id": db_chargeback.venue_id,
        "order_id": db_chargeback.order_id,
        "amount": float(db_chargeback.amount),
        "currency": db_chargeback.currency,
        "reason_code": db_chargeback.reason_code,
        "reason": db_chargeback.reason,
        "status": db_chargeback.status,
        "received_at": db_chargeback.received_at.isoformat() if db_chargeback.received_at else None,
        "response_due": db_chargeback.due_date.isoformat() if db_chargeback.due_date else None,
        "created_at": db_chargeback.created_at.isoformat() if db_chargeback.created_at else None
    }

@router.get("/chargebacks/stats")
@limiter.limit("60/minute")
async def get_chargeback_stats(
    request: Request,
    venue_id: int = Query(1),
    db: Session = Depends(get_db)
):
    """Get chargeback statistics for a venue"""
    total = db.query(Chargeback).filter(Chargeback.venue_id == venue_id).count()

    won = db.query(Chargeback).filter(
        Chargeback.venue_id == venue_id,
        Chargeback.status == ChargebackStatus.WON.value
    ).count()

    lost = db.query(Chargeback).filter(
        Chargeback.venue_id == venue_id,
        Chargeback.status == ChargebackStatus.LOST.value
    ).count()

    pending_statuses = [
        ChargebackStatus.RECEIVED.value,
        ChargebackStatus.UNDER_REVIEW.value,
        ChargebackStatus.EVIDENCE_SUBMITTED.value
    ]
    pending = db.query(Chargeback).filter(
        Chargeback.venue_id == venue_id,
        Chargeback.status.in_(pending_statuses)
    ).count()

    total_amount = db.query(func.sum(Chargeback.amount)).filter(
        Chargeback.venue_id == venue_id
    ).scalar() or 0

    recovered_amount = db.query(func.sum(Chargeback.amount_recovered)).filter(
        Chargeback.venue_id == venue_id,
        Chargeback.won == True
    ).scalar() or 0

    lost_amount = db.query(func.sum(Chargeback.amount)).filter(
        Chargeback.venue_id == venue_id,
        Chargeback.status == ChargebackStatus.LOST.value
    ).scalar() or 0

    resolved = won + lost
    win_rate = (won / resolved * 100) if resolved > 0 else 0

    return {
        "total": total,
        "won": won,
        "lost": lost,
        "pending": pending,
        "win_rate": round(win_rate, 1),
        "total_amount": float(total_amount),
        "recovered_amount": float(recovered_amount),
        "lost_amount": float(lost_amount)
    }

@router.get("/chargebacks/overdue")
@limiter.limit("60/minute")
async def get_overdue_chargebacks(
    request: Request,
    venue_id: int = Query(1),
    db: Session = Depends(get_db)
):
    """Get chargebacks that are past their response due date"""
    pending_statuses = [
        ChargebackStatus.RECEIVED.value,
        ChargebackStatus.UNDER_REVIEW.value
    ]

    overdue = db.query(Chargeback).filter(
        Chargeback.venue_id == venue_id,
        Chargeback.status.in_(pending_statuses),
        Chargeback.due_date < datetime.now(timezone.utc)
    ).all()

    return {
        "count": len(overdue),
        "chargebacks": [
            {
                "id": cb.id,
                "order_id": cb.order_id,
                "amount": float(cb.amount) if cb.amount else 0,
                "reason_code": cb.reason_code,
                "due_date": cb.due_date.isoformat() if cb.due_date else None,
                "days_overdue": (datetime.now(timezone.utc) - cb.due_date).days if cb.due_date else 0,
                "assigned_to": cb.assigned_to
            }
            for cb in overdue
        ]
    }

@router.get("/chargebacks/{chargeback_id}")
@limiter.limit("60/minute")
async def get_chargeback(
    request: Request,
    chargeback_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific chargeback by ID"""
    chargeback = db.query(Chargeback).filter(Chargeback.id == chargeback_id).first()

    if not chargeback:
        raise HTTPException(status_code=404, detail="Chargeback not found")

    return {
        "id": chargeback.id,
        "venue_id": chargeback.venue_id,
        "order_id": chargeback.order_id,
        "payment_id": chargeback.payment_id,
        "amount": float(chargeback.amount) if chargeback.amount else 0,
        "currency": chargeback.currency,
        "reason_code": chargeback.reason_code,
        "reason": chargeback.reason,
        "provider": chargeback.provider,
        "provider_case_id": chargeback.provider_case_id,
        "status": chargeback.status,
        "received_at": chargeback.received_at.isoformat() if chargeback.received_at else None,
        "due_date": chargeback.due_date.isoformat() if chargeback.due_date else None,
        "resolved_at": chargeback.resolved_at.isoformat() if chargeback.resolved_at else None,
        "evidence_submitted": chargeback.evidence_submitted,
        "evidence_submitted_at": chargeback.evidence_submitted_at.isoformat() if chargeback.evidence_submitted_at else None,
        "evidence_documents": chargeback.evidence_documents,
        "response_notes": chargeback.response_notes,
        "won": chargeback.won,
        "amount_recovered": float(chargeback.amount_recovered) if chargeback.amount_recovered else None,
        "assigned_to": chargeback.assigned_to,
        "created_at": chargeback.created_at.isoformat() if chargeback.created_at else None,
        "updated_at": chargeback.updated_at.isoformat() if chargeback.updated_at else None
    }

@router.post("/chargebacks/{chargeback_id}/respond")
@limiter.limit("30/minute")
async def respond_to_chargeback(
    request: Request,
    chargeback_id: int,
    response_data: ChargebackResponse,
    db: Session = Depends(get_db)
):
    """Submit evidence and response to a chargeback dispute"""
    chargeback = db.query(Chargeback).filter(Chargeback.id == chargeback_id).first()

    if not chargeback:
        raise HTTPException(status_code=404, detail="Chargeback not found")

    if chargeback.status in [ChargebackStatus.WON.value, ChargebackStatus.LOST.value]:
        raise HTTPException(status_code=400, detail="Chargeback is already resolved")

    # Update chargeback with evidence
    chargeback.evidence_documents = response_data.evidence_documents
    chargeback.response_notes = response_data.response_notes
    chargeback.evidence_submitted = True
    chargeback.evidence_submitted_at = datetime.now(timezone.utc)
    chargeback.status = ChargebackStatus.EVIDENCE_SUBMITTED.value

    db.commit()
    db.refresh(chargeback)

    return {
        "chargeback_id": chargeback.id,
        "status": chargeback.status,
        "evidence_submitted": chargeback.evidence_submitted,
        "evidence_submitted_at": chargeback.evidence_submitted_at.isoformat() if chargeback.evidence_submitted_at else None,
        "message": "Evidence submitted successfully"
    }

@router.put("/chargebacks/{chargeback_id}/resolve")
@limiter.limit("30/minute")
async def resolve_chargeback(
    request: Request,
    chargeback_id: int,
    won: bool = Body(...),
    amount_recovered: Optional[float] = Body(None),
    db: Session = Depends(get_db)
):
    """Mark a chargeback as resolved (won or lost)"""
    chargeback = db.query(Chargeback).filter(Chargeback.id == chargeback_id).first()

    if not chargeback:
        raise HTTPException(status_code=404, detail="Chargeback not found")

    chargeback.won = won
    chargeback.status = ChargebackStatus.WON.value if won else ChargebackStatus.LOST.value
    chargeback.resolved_at = datetime.now(timezone.utc)

    if amount_recovered is not None:
        chargeback.amount_recovered = amount_recovered
    elif won:
        chargeback.amount_recovered = chargeback.amount

    db.commit()
    db.refresh(chargeback)

    return {
        "chargeback_id": chargeback.id,
        "status": chargeback.status,
        "won": chargeback.won,
        "amount_recovered": float(chargeback.amount_recovered) if chargeback.amount_recovered else None,
        "resolved_at": chargeback.resolved_at.isoformat() if chargeback.resolved_at else None
    }

@router.put("/chargebacks/{chargeback_id}/assign")
@limiter.limit("30/minute")
async def assign_chargeback(
    request: Request,
    chargeback_id: int,
    staff_id: int = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """Assign a chargeback to a staff member for handling"""
    chargeback = db.query(Chargeback).filter(Chargeback.id == chargeback_id).first()

    if not chargeback:
        raise HTTPException(status_code=404, detail="Chargeback not found")

    chargeback.assigned_to = staff_id
    chargeback.status = ChargebackStatus.UNDER_REVIEW.value

    db.commit()
    db.refresh(chargeback)

    return {
        "chargeback_id": chargeback.id,
        "assigned_to": chargeback.assigned_to,
        "status": chargeback.status
    }

@router.get("/chargebacks")
@limiter.limit("60/minute")
async def get_chargebacks(
    request: Request,
    venue_id: int = Query(1),
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get all chargebacks for a venue with optional status filter"""
    query = db.query(Chargeback).filter(Chargeback.venue_id == venue_id)

    if status:
        query = query.filter(Chargeback.status == status)

    total = query.count()
    chargebacks = query.order_by(Chargeback.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "chargebacks": [
            {
                "id": cb.id,
                "order_id": cb.order_id,
                "amount": float(cb.amount) if cb.amount else 0,
                "currency": cb.currency,
                "reason_code": cb.reason_code,
                "reason": cb.reason,
                "status": cb.status,
                "received_at": cb.received_at.isoformat() if cb.received_at else None,
                "due_date": cb.due_date.isoformat() if cb.due_date else None,
                "evidence_submitted": cb.evidence_submitted,
                "won": cb.won,
                "assigned_to": cb.assigned_to,
                "created_at": cb.created_at.isoformat() if cb.created_at else None
            }
            for cb in chargebacks
        ]
    }


"""
Cash Drawer Management API
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta, timezone, date
from pydantic import BaseModel, ConfigDict

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.core.rbac import get_current_user
from app.models import (
    CashDrawer, CashDrawerTransaction, StaffUser
)


router = APIRouter()


# Schemas
class CashDrawerOpen(BaseModel):
    opening_balance: float
    notes: Optional[str] = None


class CashTransactionCreate(BaseModel):
    amount: float
    transaction_type: str  # cash_in, cash_out, adjustment, paid_in, paid_out
    reason: str
    reference_id: Optional[int] = None  # Order ID if related to order


class CashDrawerClose(BaseModel):
    counted_amount: float
    notes: Optional[str] = None


class CashDrawerResponse(BaseModel):
    id: int
    venue_id: int
    staff_user_id: int
    opened_at: datetime
    opening_balance: float
    expected_balance: Optional[float]
    closed_at: Optional[datetime]
    actual_balance: Optional[float]
    variance: Optional[float]
    status: str
    notes: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class TransactionResponse(BaseModel):
    id: int
    drawer_id: int
    staff_user_id: int
    amount: float
    transaction_type: str
    reason: str
    reference_id: Optional[int]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Cash Drawer Operations

@router.get("/")
@limiter.limit("60/minute")
def get_cash_drawers_root(request: Request, db: Session = Depends(get_db), current_user: StaffUser = Depends(get_current_user)):
    """Cash drawers overview."""
    drawers = db.query(CashDrawer).filter(
        CashDrawer.venue_id == current_user.venue_id,
    ).order_by(CashDrawer.opened_at.desc()).limit(20).all()
    return {"items": drawers, "total": len(drawers)}


@router.post("/open", response_model=CashDrawerResponse)
@limiter.limit("30/minute")
def open_drawer(
    request: Request,
    data: CashDrawerOpen,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Open a cash drawer for the shift"""
    # Check for existing open drawer
    existing = db.query(CashDrawer).filter(
        CashDrawer.venue_id == current_user.venue_id,
        CashDrawer.status == "open"
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Drawer already open (ID: {existing.id}). Close it first."
        )

    drawer = CashDrawer(
        venue_id=current_user.venue_id,
        staff_user_id=current_user.id,
        opening_balance=data.opening_balance,
        expected_balance=data.opening_balance,
        status="open",
        notes=data.notes
    )
    db.add(drawer)
    db.commit()
    db.refresh(drawer)

    return drawer


@router.get("/current", response_model=CashDrawerResponse)
@limiter.limit("60/minute")
def get_current_drawer(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get currently open cash drawer"""
    drawer = db.query(CashDrawer).filter(
        CashDrawer.venue_id == current_user.venue_id,
        CashDrawer.status == "open"
    ).first()

    if not drawer:
        return {"id": 0, "venue_id": current_user.venue_id, "staff_user_id": current_user.id,
                "opened_at": datetime.now(timezone.utc), "opening_balance": 0, "expected_balance": 0,
                "closed_at": None, "actual_balance": None, "variance": None,
                "status": "closed", "notes": "No open drawer"}

    return drawer


@router.post("/current/transaction", response_model=TransactionResponse)
@limiter.limit("30/minute")
def add_transaction(
    request: Request,
    data: CashTransactionCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Add a transaction to the current drawer"""
    drawer = db.query(CashDrawer).filter(
        CashDrawer.venue_id == current_user.venue_id,
        CashDrawer.status == "open"
    ).first()

    if not drawer:
        raise HTTPException(status_code=404, detail="No open drawer found")

    # Validate transaction type
    valid_types = ["cash_in", "cash_out", "adjustment", "paid_in", "paid_out"]
    if data.transaction_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid transaction type. Must be one of: {valid_types}"
        )

    transaction = CashDrawerTransaction(
        drawer_id=drawer.id,
        staff_user_id=current_user.id,
        amount=data.amount,
        transaction_type=data.transaction_type,
        reason=data.reason,
        reference_id=data.reference_id
    )
    db.add(transaction)

    # Update drawer amounts
    if data.transaction_type in ["cash_in", "paid_in"]:
        drawer.expected_balance += abs(data.amount)
    elif data.transaction_type in ["cash_out", "paid_out"]:
        drawer.expected_balance -= abs(data.amount)
    elif data.transaction_type == "adjustment":
        drawer.expected_balance += data.amount  # Can be positive or negative

    db.commit()
    db.refresh(transaction)

    return transaction


@router.post("/current/close")
@limiter.limit("30/minute")
def close_drawer(
    request: Request,
    data: CashDrawerClose,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Close the current cash drawer"""
    drawer = db.query(CashDrawer).filter(
        CashDrawer.venue_id == current_user.venue_id,
        CashDrawer.status == "open"
    ).first()

    if not drawer:
        raise HTTPException(status_code=404, detail="No open drawer found")

    # Calculate variance
    variance = data.counted_amount - drawer.expected_balance

    drawer.closed_at = datetime.now(timezone.utc)
    drawer.actual_balance = data.counted_amount
    drawer.variance = variance
    drawer.status = "closed"
    if data.notes:
        drawer.notes = (drawer.notes or "") + f" | Close: {data.notes}"

    db.commit()

    return {
        "message": "Drawer closed",
        "drawer_id": drawer.id,
        "opening_balance": drawer.opening_balance,
        "expected_balance": drawer.expected_balance,
        "counted_amount": data.counted_amount,
        "variance": variance,
        "status": "over" if variance > 0 else ("short" if variance < 0 else "balanced")
    }


@router.get("/transactions", response_model=List[TransactionResponse])
@limiter.limit("60/minute")
def list_transactions(
    request: Request,
    drawer_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List transactions for a drawer"""
    if drawer_id:
        drawer = db.query(CashDrawer).filter(
            CashDrawer.id == drawer_id,
            CashDrawer.venue_id == current_user.venue_id
        ).first()
        if not drawer:
            raise HTTPException(status_code=404, detail="Drawer not found")
        query = db.query(CashDrawerTransaction).filter(
            CashDrawerTransaction.drawer_id == drawer_id
        )
    else:
        # Get transactions from current open drawer
        drawer = db.query(CashDrawer).filter(
            CashDrawer.venue_id == current_user.venue_id,
            CashDrawer.status == "open"
        ).first()
        if not drawer:
            return []
        query = db.query(CashDrawerTransaction).filter(
            CashDrawerTransaction.drawer_id == drawer.id
        )

    return query.order_by(CashDrawerTransaction.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/history", response_model=List[CashDrawerResponse])
@limiter.limit("60/minute")
def get_drawer_history(
    request: Request,
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get cash drawer history"""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    drawers = db.query(CashDrawer).filter(
        CashDrawer.venue_id == current_user.venue_id,
        CashDrawer.opened_at >= since
    ).order_by(CashDrawer.opened_at.desc()).all()

    return drawers


@router.get("/report/daily")
@limiter.limit("60/minute")
def get_daily_cash_report(
    request: Request,
    report_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get daily cash report"""
    if not report_date:
        report_date = date.today()

    start = datetime.combine(report_date, datetime.min.time())
    end = datetime.combine(report_date, datetime.max.time())

    drawers = db.query(CashDrawer).filter(
        CashDrawer.venue_id == current_user.venue_id,
        CashDrawer.opened_at >= start,
        CashDrawer.opened_at <= end
    ).all()

    # Calculate totals
    total_opening = sum(d.opening_balance for d in drawers)
    total_closing = sum(d.actual_balance or 0 for d in drawers)
    total_variance = sum(d.variance or 0 for d in drawers)

    # Get all transactions for the day
    drawer_ids = [d.id for d in drawers]
    transactions = db.query(CashDrawerTransaction).filter(
        CashDrawerTransaction.drawer_id.in_(drawer_ids)
    ).all()

    cash_in = sum(t.amount for t in transactions if t.transaction_type == "cash_in")
    cash_out = sum(abs(t.amount) for t in transactions if t.transaction_type == "cash_out")
    paid_in = sum(t.amount for t in transactions if t.transaction_type == "paid_in")
    paid_out = sum(abs(t.amount) for t in transactions if t.transaction_type == "paid_out")

    return {
        "date": report_date.isoformat(),
        "drawers_count": len(drawers),
        "total_opening": total_opening,
        "total_closing": total_closing,
        "total_variance": total_variance,
        "cash_in": cash_in,
        "cash_out": cash_out,
        "paid_in": paid_in,
        "paid_out": paid_out,
        "net_cash_flow": cash_in + paid_in - cash_out - paid_out,
        "drawers": [
            {
                "id": d.id,
                "staff_user_id": d.staff_user_id,
                "opened_at": d.opened_at,
                "closed_at": d.closed_at,
                "opening_balance": d.opening_balance,
                "actual_balance": d.actual_balance,
                "variance": d.variance,
                "status": d.status
            } for d in drawers
        ]
    }


@router.get("/variances")
@limiter.limit("60/minute")
def get_variance_report(
    request: Request,
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get cash variance report by staff"""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Get closed drawers with variances
    drawers = db.query(CashDrawer).filter(
        CashDrawer.venue_id == current_user.venue_id,
        CashDrawer.opened_at >= since,
        CashDrawer.status == "closed"
    ).all()

    # Group by staff
    staff_variances = {}
    for drawer in drawers:
        staff_id = drawer.staff_user_id
        if staff_id not in staff_variances:
            staff_variances[staff_id] = {
                "drawer_count": 0,
                "total_variance": 0,
                "over_count": 0,
                "short_count": 0,
                "balanced_count": 0
            }

        staff_variances[staff_id]["drawer_count"] += 1
        variance = drawer.variance or 0
        staff_variances[staff_id]["total_variance"] += variance

        if variance > 0:
            staff_variances[staff_id]["over_count"] += 1
        elif variance < 0:
            staff_variances[staff_id]["short_count"] += 1
        else:
            staff_variances[staff_id]["balanced_count"] += 1

    # Get staff names
    result = []
    for staff_id, data in staff_variances.items():
        staff = db.query(StaffUser).filter(StaffUser.id == staff_id).first()
        result.append({
            "staff_id": staff_id,
            "staff_name": staff.full_name if staff else "Unknown",
            **data,
            "avg_variance": data["total_variance"] / data["drawer_count"] if data["drawer_count"] > 0 else 0
        })

    # Sort by total variance (most negative first)
    result.sort(key=lambda x: x["total_variance"])

    return {
        "period_days": days,
        "total_drawers": len(drawers),
        "total_variance": sum(d.variance or 0 for d in drawers),
        "staff_variances": result
    }

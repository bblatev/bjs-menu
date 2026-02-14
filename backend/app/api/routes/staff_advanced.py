"""
Staff Advanced Features API Endpoints
Shift swapping, time-off, labor forecasting, commissions, training, performance
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
from datetime import datetime, timedelta, date
from pydantic import BaseModel, ConfigDict

from app.db.session import get_db
from app.core.rbac import get_current_user
from app.core.rate_limit import limiter
from app.models import (
    StaffUser, StaffShift, ShiftStatus,
    ShiftTradeRequest, StaffRole
)
from app.models.staff import TimeOffRequest as TimeOffRequestModel


router = APIRouter()


def require_manager(current_user = Depends(get_current_user)):
    """Require manager or above role."""
    if not hasattr(current_user, 'role'):
        return current_user
    if current_user.role not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Manager access required")
    return current_user



# ========== SCHEMAS ==========

class ShiftTradeCreate(BaseModel):
    original_shift_id: int
    trade_type: str  # swap, giveaway, pickup
    offered_shift_id: Optional[int] = None
    target_employee_id: Optional[int] = None
    is_open_to_all: bool = True
    reason: Optional[str] = None
    expires_at: Optional[datetime] = None


class ShiftTradeResponse(BaseModel):
    id: int
    original_shift_id: int
    requester_id: int
    requester_name: str
    trade_type: str
    offered_shift_id: Optional[int]
    target_employee_id: Optional[int]
    is_open_to_all: bool
    status: str
    accepted_by_id: Optional[int]
    accepted_by_name: Optional[str]
    accepted_at: Optional[datetime]
    approved_by_id: Optional[int]
    approved_at: Optional[datetime]
    rejection_reason: Optional[str]
    expires_at: Optional[datetime]
    reason: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TimeOffRequestCreate(BaseModel):
    start_date: date
    end_date: date
    request_type: str  # vacation, sick, personal, unpaid
    reason: Optional[str] = None
    is_paid: bool = True


class TimeOffResponse(BaseModel):
    id: int
    staff_user_id: int
    staff_name: str
    start_date: date
    end_date: date
    request_type: str
    status: str  # pending, approved, rejected
    reason: Optional[str]
    is_paid: bool
    approved_by_id: Optional[int]
    approved_at: Optional[datetime]
    rejection_reason: Optional[str]
    created_at: datetime


class LaborForecast(BaseModel):
    date: date
    forecasted_sales: float
    labor_budget_percentage: float
    scheduled_hours: float
    estimated_labor_cost: float
    status: str  # under, optimal, over


class CommissionEntry(BaseModel):
    staff_user_id: int
    period_start: date
    period_end: date
    sales_amount: float
    commission_rate: float
    commission_earned: float
    is_paid: bool = False


class PerformanceGoal(BaseModel):
    staff_user_id: int
    goal_type: str  # sales, upsell_rate, customer_rating, attendance
    target_value: float
    period_start: date
    period_end: date
    current_value: Optional[float] = 0
    notes: Optional[str] = None


class TrainingModule(BaseModel):
    title: str
    description: str
    category: str  # onboarding, safety, customer_service, menu_knowledge
    duration_minutes: int
    is_required: bool = False
    required_for_roles: Optional[List[str]] = None


class TrainingProgress(BaseModel):
    module_id: int
    staff_user_id: int
    status: str  # not_started, in_progress, completed
    progress_percentage: int = 0
    completed_at: Optional[datetime] = None
    score: Optional[float] = None


# ========== SHIFT SWAPPING ENDPOINTS ==========

@router.post("/shift-trades", response_model=ShiftTradeResponse)
@limiter.limit("30/minute")
async def create_shift_trade_request(
    request: Request,
    data: ShiftTradeCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Create a shift trade request"""
    # Verify original shift exists and belongs to requester
    original_shift = db.query(StaffShift).filter(
        StaffShift.id == data.original_shift_id,
        StaffShift.staff_user_id == current_user.id,
        StaffShift.venue_id == current_user.venue_id
    ).first()

    if not original_shift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shift not found or not yours"
        )

    # Cannot trade completed or cancelled shifts
    if original_shift.status in [ShiftStatus.COMPLETED, ShiftStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot trade completed or cancelled shifts"
        )

    # For swaps, verify offered shift
    if data.trade_type == "swap":
        if not data.offered_shift_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Offered shift required for swap"
            )

        offered_shift = db.query(StaffShift).filter(
            StaffShift.id == data.offered_shift_id,
            StaffShift.venue_id == current_user.venue_id
        ).first()

        if not offered_shift:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Offered shift not found"
            )

    # Set default expiration (7 days)
    expires_at = data.expires_at or datetime.utcnow() + timedelta(days=7)

    # Create trade request
    trade_request = ShiftTradeRequest(
        venue_id=current_user.venue_id,
        original_shift_id=data.original_shift_id,
        requester_id=current_user.id,
        trade_type=data.trade_type,
        offered_shift_id=data.offered_shift_id,
        target_employee_id=data.target_employee_id,
        is_open_to_all=data.is_open_to_all,
        reason=data.reason,
        expires_at=expires_at,
        status="pending"
    )

    db.add(trade_request)
    db.commit()
    db.refresh(trade_request)

    return _format_trade_response(trade_request, db)


@router.get("/shift-trades", response_model=List[ShiftTradeResponse])
@limiter.limit("60/minute")
async def list_shift_trades(
    request: Request,
    status_filter: Optional[str] = None,
    my_requests: bool = False,
    available_for_me: bool = False,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List shift trade requests"""
    query = db.query(ShiftTradeRequest).filter(
        ShiftTradeRequest.venue_id == current_user.venue_id
    )

    if my_requests:
        query = query.filter(ShiftTradeRequest.requester_id == current_user.id)

    if available_for_me:
        # Show trades that are open to all or targeted to me
        query = query.filter(
            and_(
                ShiftTradeRequest.status == "pending",
                or_(
                    ShiftTradeRequest.is_open_to_all == True,
                    ShiftTradeRequest.target_employee_id == current_user.id
                )
            )
        )

    if status_filter:
        query = query.filter(ShiftTradeRequest.status == status_filter)

    # Filter out expired
    query = query.filter(
        or_(
            ShiftTradeRequest.expires_at.is_(None),
            ShiftTradeRequest.expires_at > datetime.utcnow()
        )
    )

    trades = query.order_by(ShiftTradeRequest.created_at.desc()).all()

    return [_format_trade_response(trade, db) for trade in trades]


@router.post("/shift-trades/{trade_id}/accept")
@limiter.limit("30/minute")
async def accept_shift_trade(
    request: Request,
    trade_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Accept a shift trade request"""
    trade = db.query(ShiftTradeRequest).filter(
        ShiftTradeRequest.id == trade_id,
        ShiftTradeRequest.venue_id == current_user.venue_id
    ).first()

    if not trade:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trade not found")

    if trade.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Trade already processed")

    # Cannot accept your own trade
    if trade.requester_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot accept your own trade")

    # Check if targeted to specific employee
    if trade.target_employee_id and trade.target_employee_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Trade not available for you")

    trade.accepted_by_id = current_user.id
    trade.accepted_at = datetime.utcnow()
    trade.status = "accepted" if not trade.requires_approval else "pending_approval"

    # If no manager approval required, swap shifts now
    if not trade.requires_approval:
        _execute_shift_trade(trade, db)

    db.commit()

    return {"message": "Trade accepted" + (" - pending manager approval" if trade.requires_approval else "")}


@router.post("/shift-trades/{trade_id}/approve")
@limiter.limit("30/minute")
async def approve_shift_trade(
    request: Request,
    trade_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Approve shift trade (managers only)"""
    trade = db.query(ShiftTradeRequest).filter(
        ShiftTradeRequest.id == trade_id,
        ShiftTradeRequest.venue_id == current_user.venue_id
    ).first()

    if not trade:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trade not found")

    if trade.status not in ["pending_approval", "accepted"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Trade not awaiting approval")

    trade.approved_by_id = current_user.id
    trade.approved_at = datetime.utcnow()
    trade.status = "approved"

    # Execute the trade
    _execute_shift_trade(trade, db)

    db.commit()

    return {"message": "Trade approved and executed"}


@router.post("/shift-trades/{trade_id}/reject")
@limiter.limit("30/minute")
async def reject_shift_trade(
    request: Request,
    trade_id: int,
    reason: str,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Reject shift trade (managers only)"""
    trade = db.query(ShiftTradeRequest).filter(
        ShiftTradeRequest.id == trade_id,
        ShiftTradeRequest.venue_id == current_user.venue_id
    ).first()

    if not trade:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trade not found")

    trade.status = "rejected"
    trade.rejection_reason = reason
    trade.approved_by_id = current_user.id
    trade.approved_at = datetime.utcnow()

    db.commit()

    return {"message": "Trade rejected"}


@router.delete("/shift-trades/{trade_id}")
@limiter.limit("30/minute")
async def cancel_shift_trade(
    request: Request,
    trade_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Cancel own shift trade request"""
    trade = db.query(ShiftTradeRequest).filter(
        ShiftTradeRequest.id == trade_id,
        ShiftTradeRequest.requester_id == current_user.id,
        ShiftTradeRequest.venue_id == current_user.venue_id
    ).first()

    if not trade:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trade not found")

    if trade.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Can only cancel pending trades")

    trade.status = "cancelled"
    db.commit()

    return {"message": "Trade cancelled"}


# ========== TIME-OFF MANAGEMENT ==========

@router.post("/time-off")
@limiter.limit("30/minute")
async def request_time_off(
    request: Request,
    data: TimeOffRequestCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Request time off"""
    # Calculate total hours (assuming 8-hour days)
    days = (data.end_date - data.start_date).days + 1
    total_hours = days * 8.0

    time_off = TimeOffRequestModel(
        staff_id=current_user.id,
        type=data.request_type,
        start_date=data.start_date,
        end_date=data.end_date,
        notes=data.reason,
        status="pending"
    )
    db.add(time_off)
    db.commit()
    db.refresh(time_off)

    return {
        "message": "Time off request created",
        "id": time_off.id,
        "status": time_off.status,
        "start_date": time_off.start_date.isoformat(),
        "end_date": time_off.end_date.isoformat(),
        "total_hours": total_hours
    }


@router.get("/time-off")
@limiter.limit("60/minute")
async def list_time_off_requests(
    request: Request,
    staff_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List time off requests"""
    query = db.query(TimeOffRequestModel)

    # Filter by staff if specified
    if staff_id:
        query = query.filter(TimeOffRequestModel.staff_id == staff_id)
    else:
        # Non-managers can only see their own requests
        if current_user.role not in ["owner", "manager"]:
            query = query.filter(TimeOffRequestModel.staff_id == current_user.id)

    if status_filter:
        query = query.filter(TimeOffRequestModel.status == status_filter)

    requests = query.order_by(TimeOffRequestModel.created_at.desc()).all()

    return [
        {
            "id": r.id,
            "staff_id": r.staff_id,
            "request_type": r.type,
            "start_date": r.start_date.isoformat() if r.start_date else None,
            "end_date": r.end_date.isoformat() if r.end_date else None,
            "total_hours": ((r.end_date - r.start_date).days + 1) * 8.0 if r.start_date and r.end_date else None,
            "status": r.status,
            "reason": r.notes,
            "reviewed_by": r.reviewed_by,
            "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None
        }
        for r in requests
    ]


@router.post("/time-off/{request_id}/approve")
@limiter.limit("30/minute")
async def approve_time_off(
    request: Request,
    request_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Approve a time off request"""
    time_off = db.query(TimeOffRequestModel).filter(
        TimeOffRequestModel.id == request_id
    ).first()

    if not time_off:
        raise HTTPException(status_code=404, detail="Time off request not found")

    if time_off.status != "pending":
        raise HTTPException(status_code=400, detail="Request already processed")

    time_off.status = "approved"
    time_off.reviewed_by = current_user.id
    time_off.reviewed_at = datetime.utcnow()
    db.commit()

    return {"message": "Time off request approved", "id": request_id}


@router.post("/time-off/{request_id}/deny")
@limiter.limit("30/minute")
async def deny_time_off(
    request: Request,
    request_id: int,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Deny a time off request"""
    time_off = db.query(TimeOffRequestModel).filter(
        TimeOffRequestModel.id == request_id
    ).first()

    if not time_off:
        raise HTTPException(status_code=404, detail="Time off request not found")

    if time_off.status != "pending":
        raise HTTPException(status_code=400, detail="Request already processed")

    time_off.status = "denied"
    time_off.reviewed_by = current_user.id
    time_off.reviewed_at = datetime.utcnow()
    time_off.notes = reason
    db.commit()

    return {"message": "Time off request denied", "id": request_id}


# ========== LABOR COST FORECASTING ==========

@router.get("/labor-forecast")
@limiter.limit("60/minute")
async def get_labor_forecast(
    request: Request,
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Get labor cost forecast for date range"""
    forecasts = []
    current_date = start_date

    while current_date <= end_date:
        # Get scheduled shifts for this date
        day_start = datetime.combine(current_date, datetime.min.time())
        day_end = datetime.combine(current_date, datetime.max.time())

        shifts = db.query(StaffShift).filter(
            StaffShift.venue_id == current_user.venue_id,
            StaffShift.scheduled_start >= day_start,
            StaffShift.scheduled_start <= day_end
        ).all()

        # Calculate total scheduled hours
        total_hours = 0
        total_labor_cost = 0

        for shift in shifts:
            staff = db.query(StaffUser).filter(StaffUser.id == shift.staff_user_id).first()
            if staff and shift.scheduled_start and shift.scheduled_end:
                hours = (shift.scheduled_end - shift.scheduled_start).total_seconds() / 3600
                total_hours += hours

                # Default hourly rates by role
                hourly_rate = {
                    "admin": 25.0,
                    "manager": 20.0,
                    "waiter": 12.0,
                    "kitchen": 14.0,
                    "bar": 13.0
                }.get(staff.role, 12.0)

                total_labor_cost += hours * hourly_rate

        # Mock forecasted sales (in production, use historical data)
        forecasted_sales = 1500.0  # Default forecast
        labor_percentage = (total_labor_cost / forecasted_sales * 100) if forecasted_sales > 0 else 0

        # Determine status
        if labor_percentage < 25:
            status = "under"
        elif labor_percentage <= 35:
            status = "optimal"
        else:
            status = "over"

        forecasts.append({
            "date": current_date.isoformat(),
            "forecasted_sales": forecasted_sales,
            "labor_budget_percentage": 30.0,  # Target
            "scheduled_hours": total_hours,
            "estimated_labor_cost": round(total_labor_cost, 2),
            "actual_labor_percentage": round(labor_percentage, 2),
            "status": status,
            "shift_count": len(shifts)
        })

        current_date += timedelta(days=1)

    return forecasts


# ========== HELPER FUNCTIONS ==========

def _format_trade_response(trade: ShiftTradeRequest, db: Session) -> ShiftTradeResponse:
    """Format trade request for response"""
    requester = db.query(StaffUser).filter(StaffUser.id == trade.requester_id).first()
    accepted_by = None
    if trade.accepted_by_id:
        accepted_by = db.query(StaffUser).filter(StaffUser.id == trade.accepted_by_id).first()

    return ShiftTradeResponse(
        id=trade.id,
        original_shift_id=trade.original_shift_id,
        requester_id=trade.requester_id,
        requester_name=requester.full_name if requester else "Unknown",
        trade_type=trade.trade_type,
        offered_shift_id=trade.offered_shift_id,
        target_employee_id=trade.target_employee_id,
        is_open_to_all=trade.is_open_to_all,
        status=trade.status,
        accepted_by_id=trade.accepted_by_id,
        accepted_by_name=accepted_by.full_name if accepted_by else None,
        accepted_at=trade.accepted_at,
        approved_by_id=trade.approved_by_id,
        approved_at=trade.approved_at,
        rejection_reason=trade.rejection_reason,
        expires_at=trade.expires_at,
        reason=trade.reason,
        created_at=trade.created_at
    )


def _execute_shift_trade(trade: ShiftTradeRequest, db: Session):
    """Execute the actual shift swap/trade"""
    original_shift = db.query(StaffShift).filter(StaffShift.id == trade.original_shift_id).first()

    if trade.trade_type == "swap" and trade.offered_shift_id:
        # Swap shifts between two employees
        offered_shift = db.query(StaffShift).filter(StaffShift.id == trade.offered_shift_id).first()
        if original_shift and offered_shift:
            # Swap the staff assignments
            original_staff_id = original_shift.staff_user_id
            original_shift.staff_user_id = offered_shift.staff_user_id
            offered_shift.staff_user_id = original_staff_id

    elif trade.trade_type == "giveaway" and trade.accepted_by_id:
        # Transfer shift to accepting employee
        if original_shift:
            original_shift.staff_user_id = trade.accepted_by_id

    # Add notes about the trade
    if original_shift:
        note = f"Traded via request #{trade.id}"
        original_shift.notes = (original_shift.notes + " | " + note) if original_shift.notes else note

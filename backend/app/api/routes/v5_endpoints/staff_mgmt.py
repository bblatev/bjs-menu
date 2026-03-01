"""V5 sub-module: Staff Breaks, Shift Trading & Onboarding"""
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

# ==================== STAFF MANAGEMENT V5 ====================

@router.post("/staff/{staff_id}/breaks")
@limiter.limit("30/minute")
async def schedule_break(
    request: Request,
    staff_id: int,
    shift_id: int = Body(...),
    break_type: str = Body(...),
    scheduled_start: datetime = Body(...),
    duration_minutes: int = Body(...),
    venue_id: int = Query(1),
    db: Session = Depends(get_db)
):
    """Schedule employee break"""
    # Verify staff exists
    staff = db.query(StaffUser).filter(
        StaffUser.id == staff_id,
        StaffUser.location_id == venue_id
    ).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found")

    # Verify shift exists and belongs to this staff member
    shift = db.query(StaffShift).filter(
        StaffShift.id == shift_id,
        StaffShift.staff_user_id == staff_id
    ).first()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found for this staff member")

    # Calculate scheduled end time
    scheduled_end = scheduled_start + timedelta(minutes=duration_minutes)

    # Create the break record
    employee_break = EmployeeBreak(
        venue_id=venue_id,
        staff_id=staff_id,
        shift_id=shift_id,
        break_type=break_type,
        scheduled_start=scheduled_start,
        scheduled_end=scheduled_end,
        scheduled_duration_minutes=duration_minutes,
        status="scheduled"
    )
    db.add(employee_break)
    db.commit()
    db.refresh(employee_break)

    return {
        "id": employee_break.id,
        "staff_id": staff_id,
        "shift_id": shift_id,
        "break_type": break_type,
        "scheduled_start": scheduled_start.isoformat(),
        "scheduled_end": scheduled_end.isoformat(),
        "duration_minutes": duration_minutes,
        "status": "scheduled"
    }

@router.post("/breaks/{break_id}/start")
@limiter.limit("30/minute")
async def start_break(request: Request, break_id: int, db: Session = Depends(get_db)):
    """Clock in for break"""
    # Find the break record
    employee_break = db.query(EmployeeBreak).filter(
        EmployeeBreak.id == break_id
    ).first()
    if not employee_break:
        raise HTTPException(status_code=404, detail="Break not found")

    if employee_break.status != "scheduled":
        raise HTTPException(status_code=400, detail=f"Break cannot be started - current status: {employee_break.status}")

    # Update break status and actual start time
    employee_break.status = "in_progress"
    employee_break.actual_start = datetime.now(timezone.utc)
    db.commit()
    db.refresh(employee_break)

    return {
        "break_id": break_id,
        "status": "in_progress",
        "started_at": employee_break.actual_start.isoformat(),
        "staff_id": employee_break.staff_id
    }

@router.post("/breaks/{break_id}/end")
@limiter.limit("30/minute")
async def end_break(request: Request, break_id: int, db: Session = Depends(get_db)):
    """Clock out from break"""
    # Find the break record
    employee_break = db.query(EmployeeBreak).filter(
        EmployeeBreak.id == break_id
    ).first()
    if not employee_break:
        raise HTTPException(status_code=404, detail="Break not found")

    if employee_break.status != "in_progress":
        raise HTTPException(status_code=400, detail=f"Break cannot be ended - current status: {employee_break.status}")

    # Update break status, actual end time, and calculate duration
    employee_break.status = "completed"
    employee_break.actual_end = datetime.now(timezone.utc)

    # Calculate actual duration if we have start time
    if employee_break.actual_start:
        duration = employee_break.actual_end - employee_break.actual_start
        employee_break.actual_duration_minutes = int(duration.total_seconds() / 60)
    else:
        employee_break.actual_duration_minutes = employee_break.scheduled_duration_minutes

    db.commit()
    db.refresh(employee_break)

    return {
        "break_id": break_id,
        "status": "completed",
        "ended_at": employee_break.actual_end.isoformat(),
        "duration_minutes": employee_break.actual_duration_minutes,
        "staff_id": employee_break.staff_id
    }

@router.post("/shifts/trade-requests")
@limiter.limit("30/minute")
async def create_shift_trade(
    request: Request,
    body_data: ShiftTradeRequest,
    requesting_staff_id: int = Query(...),
    venue_id: int = Query(1),
    db: Session = Depends(get_db)
):
    """Create shift trade body_data"""
    # Verify requesting staff exists
    requester = db.query(StaffUser).filter(
        StaffUser.id == requesting_staff_id,
        StaffUser.location_id == venue_id
    ).first()
    if not requester:
        raise HTTPException(status_code=404, detail="Requesting staff member not found")

    # Verify original shift exists and belongs to requester
    original_shift = db.query(StaffShift).filter(
        StaffShift.id == body_data.original_shift_id,
        StaffShift.staff_user_id == requesting_staff_id
    ).first()
    if not original_shift:
        raise HTTPException(status_code=404, detail="Original shift not found for this staff member")

    # Verify offered shift if provided
    if body_data.offered_shift_id:
        offered_shift = db.query(StaffShift).filter(
            StaffShift.id == body_data.offered_shift_id
        ).first()
        if not offered_shift:
            raise HTTPException(status_code=404, detail="Offered shift not found")

    # Create the trade body_data
    trade_request = ShiftTradeRequestModel(
        venue_id=venue_id,
        original_shift_id=body_data.original_shift_id,
        requester_id=requesting_staff_id,
        trade_type=body_data.trade_type,
        offered_shift_id=body_data.offered_shift_id,
        target_employee_id=body_data.target_staff_id,
        is_open_to_all=body_data.target_staff_id is None,
        status="pending",
        reason=body_data.reason,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7)  # Default 7 day expiry
    )
    db.add(trade_request)
    db.commit()
    db.refresh(trade_request)

    return {
        "id": trade_request.id,
        "original_shift_id": trade_request.original_shift_id,
        "trade_type": trade_request.trade_type,
        "target_staff_id": trade_request.target_employee_id,
        "offered_shift_id": trade_request.offered_shift_id,
        "requesting_staff_id": requesting_staff_id,
        "status": "pending",
        "expires_at": trade_request.expires_at.isoformat() if trade_request.expires_at else None
    }

@router.post("/shifts/trade-requests/{request_id}/respond")
@limiter.limit("30/minute")
async def respond_to_trade(
    request: Request,
    request_id: int,
    response: str = Body(...),
    staff_id: int = Body(...),
    db: Session = Depends(get_db)
):
    """Respond to shift trade request"""
    # Find the trade request
    trade_request = db.query(ShiftTradeRequestModel).filter(
        ShiftTradeRequestModel.id == request_id
    ).first()
    if not trade_request:
        raise HTTPException(status_code=404, detail="Trade request not found")

    if trade_request.status != "pending":
        raise HTTPException(status_code=400, detail=f"Trade request cannot be responded to - current status: {trade_request.status}")

    # Validate response value
    if response not in ["accepted", "rejected"]:
        raise HTTPException(status_code=400, detail="Response must be 'accepted' or 'rejected'")

    # Update trade request
    if response == "accepted":
        trade_request.status = "accepted"
        trade_request.accepted_by_id = staff_id
        trade_request.accepted_at = datetime.now(timezone.utc)
    else:
        trade_request.status = "rejected"

    db.commit()
    db.refresh(trade_request)

    return {
        "request_id": request_id,
        "status": trade_request.status,
        "responded_by": staff_id,
        "responded_at": datetime.now(timezone.utc).isoformat()
    }

@router.post("/shifts/trade-requests/{request_id}/approve")
@limiter.limit("30/minute")
async def approve_trade(
    request: Request,
    request_id: int,
    manager_id: int = Body(...),
    approved: bool = Body(...),
    rejection_reason: Optional[str] = Body(None),
    db: Session = Depends(get_db)
):
    """Manager approval for trade"""
    # Find the trade request
    trade_request = db.query(ShiftTradeRequestModel).filter(
        ShiftTradeRequestModel.id == request_id
    ).first()
    if not trade_request:
        raise HTTPException(status_code=404, detail="Trade request not found")

    if trade_request.status != "accepted":
        raise HTTPException(status_code=400, detail="Trade request must be accepted before manager approval")

    # Update with manager decision
    trade_request.approved_by_id = manager_id
    trade_request.approved_at = datetime.now(timezone.utc)

    if approved:
        trade_request.status = "approved"

        # Actually swap the shifts in StaffShift table
        original_shift = db.query(StaffShift).filter(
            StaffShift.id == trade_request.original_shift_id
        ).first()

        if original_shift:
            if trade_request.trade_type == "swap" and trade_request.offered_shift_id:
                # For swaps: exchange staff_user_id between the two shifts
                offered_shift = db.query(StaffShift).filter(
                    StaffShift.id == trade_request.offered_shift_id
                ).first()
                if offered_shift:
                    # Swap the staff assignments
                    original_staff_id = original_shift.staff_user_id
                    offered_staff_id = offered_shift.staff_user_id
                    original_shift.staff_user_id = offered_staff_id
                    offered_shift.staff_user_id = original_staff_id
            elif trade_request.trade_type in ["giveaway", "pickup"] and trade_request.accepted_by_id:
                # For giveaways/pickups: transfer shift to the accepting staff
                original_shift.staff_user_id = trade_request.accepted_by_id
    else:
        trade_request.status = "rejected"
        trade_request.rejection_reason = rejection_reason

    db.commit()
    db.refresh(trade_request)

    return {
        "request_id": request_id,
        "approved": approved,
        "approved_by": manager_id,
        "status": trade_request.status
    }

@router.get("/shifts/open-requests")
@limiter.limit("60/minute")
async def get_open_shifts(request: Request, venue_id: int = Query(1), db: Session = Depends(get_db)):
    """Get open shift giveaway requests"""
    # Get all open trade requests (giveaways that are open to all)
    open_requests = db.query(ShiftTradeRequestModel).filter(
        ShiftTradeRequestModel.venue_id == venue_id,
        ShiftTradeRequestModel.trade_type == "giveaway",
        ShiftTradeRequestModel.is_open_to_all == True,
        ShiftTradeRequestModel.status == "pending"
    ).all()

    result = []
    for req in open_requests:
        # Get the shift details
        shift = db.query(StaffShift).filter(StaffShift.id == req.original_shift_id).first()
        requester = db.query(StaffUser).filter(StaffUser.id == req.requester_id).first()

        result.append({
            "request_id": req.id,
            "shift_id": req.original_shift_id,
            "shift_start": shift.scheduled_start.isoformat() if shift else None,
            "shift_end": shift.scheduled_end.isoformat() if shift else None,
            "requester_id": req.requester_id,
            "requester_name": requester.name if requester else None,
            "reason": req.reason,
            "expires_at": req.expires_at.isoformat() if req.expires_at else None
        })

    return {"open_shifts": result}

@router.post("/staff/{staff_id}/onboarding")
@limiter.limit("30/minute")
async def create_onboarding(
    request: Request,
    staff_id: int,
    venue_id: int = Query(1),
    start_date: date = Body(...),
    checklist_id: Optional[int] = Body(None),
    mentor_id: Optional[int] = Body(None),
    db: Session = Depends(get_db)
):
    """Create onboarding record"""
    # Verify staff exists
    staff = db.query(StaffUser).filter(
        StaffUser.id == staff_id,
        StaffUser.location_id == venue_id
    ).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found")

    # Check if staff already has an active onboarding
    existing = db.query(EmployeeOnboarding).filter(
        EmployeeOnboarding.staff_id == staff_id,
        EmployeeOnboarding.status == "in_progress"
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Staff member already has an active onboarding")

    # Get or find checklist
    if checklist_id:
        checklist = db.query(OnboardingChecklist).filter(
            OnboardingChecklist.id == checklist_id,
            OnboardingChecklist.venue_id == venue_id,
            OnboardingChecklist.is_active == True
        ).first()
        if not checklist:
            raise HTTPException(status_code=404, detail="Onboarding checklist not found")
    else:
        # Try to find a default checklist for this venue
        checklist = db.query(OnboardingChecklist).filter(
            OnboardingChecklist.venue_id == venue_id,
            OnboardingChecklist.is_active == True
        ).first()

    # Create onboarding record
    onboarding = EmployeeOnboarding(
        venue_id=venue_id,
        staff_id=staff_id,
        checklist_id=checklist.id if checklist else None,
        start_date=start_date,
        target_completion_date=start_date + timedelta(days=30),  # Default 30 day target
        status="in_progress",
        progress_percentage=0.0,
        assigned_mentor=mentor_id
    )
    db.add(onboarding)
    db.commit()
    db.refresh(onboarding)

    return {
        "id": onboarding.id,
        "staff_id": staff_id,
        "start_date": start_date.isoformat(),
        "target_completion_date": onboarding.target_completion_date.isoformat() if onboarding.target_completion_date else None,
        "status": "in_progress",
        "progress": 0,
        "checklist_id": onboarding.checklist_id,
        "mentor_id": mentor_id
    }

@router.get("/onboarding/{onboarding_id}")
@limiter.limit("60/minute")
async def get_onboarding_progress(request: Request, onboarding_id: int, db: Session = Depends(get_db)):
    """Get onboarding progress"""
    # Find the onboarding record
    onboarding = db.query(EmployeeOnboarding).filter(
        EmployeeOnboarding.id == onboarding_id
    ).first()
    if not onboarding:
        raise HTTPException(status_code=404, detail="Onboarding record not found")

    # Get all tasks for this onboarding's checklist
    tasks = []
    documents_completed = 0
    documents_total = 0
    training_completed = 0
    training_total = 0

    if onboarding.checklist_id:
        checklist_tasks = db.query(OnboardingTask).filter(
            OnboardingTask.checklist_id == onboarding.checklist_id
        ).all()

        for task in checklist_tasks:
            # Check completion status
            completion = db.query(OnboardingTaskCompletion).filter(
                OnboardingTaskCompletion.onboarding_id == onboarding_id,
                OnboardingTaskCompletion.task_id == task.id
            ).first()

            is_completed = completion and completion.status == "completed"

            if task.task_type == "document":
                documents_total += 1
                if is_completed:
                    documents_completed += 1
            elif task.task_type == "training":
                training_total += 1
                if is_completed:
                    training_completed += 1

            tasks.append({
                "id": task.id,
                "title": task.title,
                "type": task.task_type,
                "is_required": task.is_required,
                "status": completion.status if completion else "pending",
                "completed_at": completion.completed_at.isoformat() if completion and completion.completed_at else None
            })

    # Calculate overall progress
    total_tasks = len(tasks) if tasks else 1
    completed_tasks = sum(1 for t in tasks if t.get("status") == "completed")
    progress_percentage = round((completed_tasks / total_tasks) * 100, 1) if total_tasks > 0 else 0

    return {
        "onboarding_id": onboarding_id,
        "staff_id": onboarding.staff_id,
        "status": onboarding.status,
        "start_date": onboarding.start_date.isoformat() if onboarding.start_date else None,
        "target_completion_date": onboarding.target_completion_date.isoformat() if onboarding.target_completion_date else None,
        "progress_percentage": progress_percentage,
        "documents": {"completed": documents_completed, "total": documents_total},
        "training": {"completed": training_completed, "total": training_total},
        "tasks": tasks
    }

@router.patch("/onboarding/{onboarding_id}")
@limiter.limit("30/minute")
async def update_onboarding(
    request: Request,
    onboarding_id: int,
    task_id: int = Body(...),
    completed: bool = Body(...),
    notes: Optional[str] = Body(None),
    db: Session = Depends(get_db)
):
    """Update onboarding task completion"""
    # Find the onboarding record
    onboarding = db.query(EmployeeOnboarding).filter(
        EmployeeOnboarding.id == onboarding_id
    ).first()
    if not onboarding:
        raise HTTPException(status_code=404, detail="Onboarding record not found")

    # Find the task
    task = db.query(OnboardingTask).filter(
        OnboardingTask.id == task_id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Onboarding task not found")

    # Find or create completion record
    completion = db.query(OnboardingTaskCompletion).filter(
        OnboardingTaskCompletion.onboarding_id == onboarding_id,
        OnboardingTaskCompletion.task_id == task_id
    ).first()

    if not completion:
        completion = OnboardingTaskCompletion(
            onboarding_id=onboarding_id,
            task_id=task_id,
            status="pending"
        )
        db.add(completion)

    # Update completion status
    if completed:
        completion.status = "completed"
        completion.completed_at = datetime.now(timezone.utc)
    else:
        completion.status = "pending"
        completion.completed_at = None

    if notes:
        completion.notes = notes

    db.commit()
    db.refresh(completion)

    # Recalculate overall progress
    total_tasks = db.query(OnboardingTask).filter(
        OnboardingTask.checklist_id == onboarding.checklist_id
    ).count()

    completed_tasks = db.query(OnboardingTaskCompletion).filter(
        OnboardingTaskCompletion.onboarding_id == onboarding_id,
        OnboardingTaskCompletion.status == "completed"
    ).count()

    progress = round((completed_tasks / total_tasks) * 100, 1) if total_tasks > 0 else 0
    onboarding.progress_percentage = progress

    # Check if onboarding is complete
    if progress >= 100:
        onboarding.status = "completed"
        onboarding.actual_completion_date = date.today()

    db.commit()

    return {
        "onboarding_id": onboarding_id,
        "task_id": task_id,
        "updated": True,
        "task_status": completion.status,
        "overall_progress": progress
    }


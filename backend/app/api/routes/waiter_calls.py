from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, String
from typing import List, Optional
from datetime import datetime, date, timedelta, timezone
from app.db.session import get_db
from app.schemas.waiter_call import WaiterCallCreate, WaiterCallResponse, WaiterCallStatusUpdate
from app.services.waiter_call_service import WaiterCallService
from app.core.rbac import get_current_user, TokenData
from app.models.hardware import WaiterCall
from app.models.platform_compat import WaiterCallStatus
from pydantic import BaseModel
from app.core.rate_limit import limiter


router = APIRouter()


class WaiterCallHistory(BaseModel):
    calls: List[WaiterCallResponse]
    total: int


class WaiterCallStats(BaseModel):
    total_calls_today: int
    average_response_time_seconds: float
    calls_by_reason: dict
    calls_by_hour: dict


@router.get("/")
@limiter.limit("60/minute")
def get_waiter_calls_root(request: Request, db: Session = Depends(get_db)):
    """Waiter calls overview."""
    return get_active_calls(request=request, db=db)


@router.post("/", response_model=WaiterCallResponse, status_code=201)
@limiter.limit("30/minute")
def create_waiter_call(request: Request, call_data: WaiterCallCreate, db: Session = Depends(get_db)):
    """Create waiter call (public endpoint with table token)."""
    service = WaiterCallService(db)
    return service.create_call(call_data)


@router.get("/active", response_model=List[WaiterCallResponse])
@limiter.limit("60/minute")
def get_active_calls(
    request: Request,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """Get active waiter calls (staff only)."""
    service = WaiterCallService(db)
    return service.get_active_calls()


@router.get("/history", response_model=WaiterCallHistory)
@limiter.limit("60/minute")
def get_call_history(
    request: Request,
    table_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """Get waiter call history with filters (staff only)."""
    query = db.query(WaiterCall)

    if table_id:
        query = query.filter(WaiterCall.table_id == table_id)
    if start_date:
        query = query.filter(func.date(WaiterCall.created_at) >= start_date)
    if end_date:
        query = query.filter(func.date(WaiterCall.created_at) <= end_date)
    if status:
        query = query.filter(WaiterCall.status == status)

    total = query.count()
    calls = query.order_by(WaiterCall.created_at.desc()).offset(skip).limit(limit).all()

    return WaiterCallHistory(
        calls=[WaiterCallResponse(
            id=c.id,
            table_id=c.table_id,
            reason=c.call_type or "other",
            message=c.message,
            status=c.status if isinstance(c.status, str) else (c.status.value if hasattr(c.status, 'value') else str(c.status)),
            created_at=c.created_at,
            acknowledged_at=c.acknowledged_at,
            resolved_at=c.completed_at
        ) for c in calls],
        total=total
    )


@router.get("/stats", response_model=WaiterCallStats)
@limiter.limit("60/minute")
def get_call_stats(
    request: Request,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """Get waiter call statistics for today (staff only)."""
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    # Total calls today
    total_today = db.query(func.count(WaiterCall.id)).filter(
        WaiterCall.created_at >= today_start
    ).scalar() or 0

    # Average response time (from created to acknowledged)
    completed_calls = db.query(WaiterCall).filter(
        WaiterCall.created_at >= today_start,
        WaiterCall.acknowledged_at.isnot(None)
    ).all()

    if completed_calls:
        response_times = [
            (c.acknowledged_at - c.created_at).total_seconds()
            for c in completed_calls if c.acknowledged_at
        ]
        avg_response = sum(response_times) / len(response_times) if response_times else 0
    else:
        avg_response = 0

    # Calls by reason (call_type in DB)
    reason_counts = db.query(
        WaiterCall.call_type, func.count(WaiterCall.id)
    ).filter(
        WaiterCall.created_at >= today_start
    ).group_by(WaiterCall.call_type).all()
    calls_by_reason = {(r[0] or "other"): r[1] for r in reason_counts}

    # Calls by hour - PostgreSQL compatible
    hour_counts = db.query(
        cast(func.extract('hour', WaiterCall.created_at), String).label('hour'),
        func.count(WaiterCall.id)
    ).filter(
        WaiterCall.created_at >= today_start
    ).group_by(func.extract('hour', WaiterCall.created_at)).all()
    calls_by_hour = {h[0]: h[1] for h in hour_counts}

    return WaiterCallStats(
        total_calls_today=total_today,
        average_response_time_seconds=round(avg_response, 1),
        calls_by_reason=calls_by_reason,
        calls_by_hour=calls_by_hour
    )


@router.get("/table/{table_id}", response_model=List[WaiterCallResponse])
@limiter.limit("60/minute")
def get_calls_by_table(
    request: Request,
    table_id: int,
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """Get waiter calls for a specific table (staff only)."""
    query = db.query(WaiterCall).filter(WaiterCall.table_id == table_id)

    if active_only:
        query = query.filter(WaiterCall.status.in_([
            WaiterCallStatus.PENDING,
            WaiterCallStatus.ACKNOWLEDGED
        ]))

    calls = query.order_by(WaiterCall.created_at.desc()).all()

    return [WaiterCallResponse(
        id=c.id,
        table_id=c.table_id,
        reason=c.call_type or "other",
        message=c.message,
        status=c.status if isinstance(c.status, str) else (c.status.value if hasattr(c.status, 'value') else str(c.status)),
        created_at=c.created_at,
        acknowledged_at=c.acknowledged_at,
        resolved_at=c.completed_at
    ) for c in calls]


@router.get("/{call_id}", response_model=WaiterCallResponse)
@limiter.limit("60/minute")
def get_call_by_id(
    request: Request,
    call_id: int,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """Get a specific waiter call by ID (staff only)."""
    call = db.query(WaiterCall).filter(WaiterCall.id == call_id).first()

    if not call:
        raise HTTPException(status_code=404, detail="Waiter call not found")

    return WaiterCallResponse(
        id=call.id,
        table_id=call.table_id,
        reason=call.call_type or "other",
        message=call.message,
        status=call.status if isinstance(call.status, str) else (call.status.value if hasattr(call.status, 'value') else str(call.status)),
        created_at=call.created_at,
        acknowledged_at=call.acknowledged_at,
        resolved_at=call.completed_at
    )


@router.put("/{call_id}/status", response_model=WaiterCallResponse)
@limiter.limit("30/minute")
def update_call_status(
    request: Request,
    call_id: int,
    update: WaiterCallStatusUpdate,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """Update waiter call status (staff only)."""
    service = WaiterCallService(db)
    return service.update_call_status(call_id, update)


@router.delete("/{call_id}", status_code=204)
@limiter.limit("30/minute")
def delete_waiter_call(
    request: Request,
    call_id: int,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """Delete a waiter call (staff only). Usually used for cleanup of old calls."""
    call = db.query(WaiterCall).filter(WaiterCall.id == call_id).first()

    if not call:
        raise HTTPException(status_code=404, detail="Waiter call not found")

    db.delete(call)
    db.commit()
    return None


@router.delete("/cleanup/completed", status_code=200)
@limiter.limit("30/minute")
def cleanup_completed_calls(
    request: Request,
    older_than_days: int = Query(7, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """Delete old completed waiter calls for cleanup (staff only)."""
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=older_than_days)

    deleted = db.query(WaiterCall).filter(
        WaiterCall.status == "resolved",
        WaiterCall.created_at < cutoff_date
    ).delete(synchronize_session=False)

    db.commit()

    return {"deleted_count": deleted, "older_than_days": older_than_days}

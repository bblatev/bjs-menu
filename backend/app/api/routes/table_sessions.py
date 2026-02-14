"""
Table Sessions & Guest Duration Tracking API
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, ConfigDict

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.core.rbac import get_current_user
from app.models import (
    TableSession, TableSessionStatus, TableHistory,
    Table, StaffUser, Order
)


router = APIRouter()


# Schemas
class TableSessionCreate(BaseModel):
    table_id: int
    guest_count: int = 1
    notes: Optional[str] = None


class TableSessionResponse(BaseModel):
    id: int
    venue_id: int
    table_id: int
    guest_count: int
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    status: str
    guest_name: Optional[str] = None  # Using guest_name instead of notes
    total_orders: int = 0
    total_spent: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class GuestDurationStats(BaseModel):
    avg_duration_minutes: float
    min_duration_minutes: int
    max_duration_minutes: int
    avg_spending_per_guest: float
    total_sessions: int


# Session Management
@router.post("/", response_model=TableSessionResponse)
@limiter.limit("30/minute")
def start_session(
    request: Request,
    data: TableSessionCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Start a new table session when guests are seated"""
    # Verify table exists and is available
    table = db.query(Table).filter(
        Table.id == data.table_id,
        Table.venue_id == current_user.venue_id
    ).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    # Check for existing active session
    active = db.query(TableSession).filter(
        TableSession.table_id == data.table_id,
        TableSession.status == TableSessionStatus.ACTIVE
    ).first()
    if active:
        raise HTTPException(status_code=400, detail="Table already has an active session")

    session = TableSession(
        venue_id=current_user.venue_id,
        table_id=data.table_id,
        guest_count=data.guest_count,
        waiter_id=current_user.id,
        guest_name=data.notes,  # Store notes in guest_name field
        status=TableSessionStatus.ACTIVE
    )
    db.add(session)

    # Update table status
    table.status = "occupied"
    table.current_guests = data.guest_count

    db.commit()
    db.refresh(session)
    return session


@router.get("/", response_model=List[TableSessionResponse])
@limiter.limit("60/minute")
def list_sessions(
    request: Request,
    status: Optional[str] = None,
    table_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List table sessions"""
    query = db.query(TableSession).filter(TableSession.venue_id == current_user.venue_id)

    if status:
        query = query.filter(TableSession.status == status)
    if table_id:
        query = query.filter(TableSession.table_id == table_id)

    return query.order_by(TableSession.started_at.desc()).all()


@router.get("/active", response_model=List[TableSessionResponse])
@limiter.limit("60/minute")
def get_active_sessions(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get all currently active table sessions"""
    sessions = db.query(TableSession).filter(
        TableSession.venue_id == current_user.venue_id,
        TableSession.status == TableSessionStatus.ACTIVE
    ).all()

    # Calculate duration for active sessions
    for session in sessions:
        session.duration_minutes = int((datetime.utcnow() - session.started_at).total_seconds() / 60)

    return sessions


@router.get("/{session_id}", response_model=TableSessionResponse)
@limiter.limit("60/minute")
def get_session(
    request: Request,
    session_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get a specific session"""
    session = db.query(TableSession).filter(
        TableSession.id == session_id,
        TableSession.venue_id == current_user.venue_id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return session


@router.post("/{session_id}/end")
@limiter.limit("30/minute")
def end_session(
    request: Request,
    session_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """End a table session"""
    session = db.query(TableSession).filter(
        TableSession.id == session_id,
        TableSession.venue_id == current_user.venue_id,
        TableSession.status == TableSessionStatus.ACTIVE
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Active session not found")

    # End the session
    session.status = TableSessionStatus.CLOSED
    session.ended_at = datetime.utcnow()
    session.waiter_id = current_user.id  # Update to staff who ended it
    session.duration_minutes = int((session.ended_at - session.started_at).total_seconds() / 60)

    # Calculate total spent
    orders = db.query(Order).filter(
        Order.table_id == session.table_id,
        Order.created_at >= session.started_at,
        Order.created_at <= session.ended_at
    ).all()
    session.total_orders = len(orders)
    session.total_spent = sum(o.total for o in orders)

    # Update table status
    table = db.query(Table).filter(Table.id == session.table_id).first()
    if table:
        table.status = "available"
        table.current_guests = 0

    # Log to history
    history = TableHistory(
        table_id=session.table_id,
        session_id=session.id,
        event_type="session_ended",
        event_data={
            "guest_count": session.guest_count,
            "duration_minutes": session.duration_minutes,
            "total_spent": session.total_spent
        },
        created_by=current_user.id
    )
    db.add(history)

    db.commit()

    return {
        "message": "Session ended",
        "session_id": session.id,
        "duration_minutes": session.duration_minutes,
        "total_orders": session.total_orders,
        "total_spent": session.total_spent
    }


@router.patch("/{session_id}/guests")
@limiter.limit("30/minute")
def update_guest_count(
    request: Request,
    session_id: int,
    guest_count: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Update guest count for an active session"""
    session = db.query(TableSession).filter(
        TableSession.id == session_id,
        TableSession.venue_id == current_user.venue_id,
        TableSession.status == TableSessionStatus.ACTIVE
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Active session not found")

    session.guest_count = guest_count

    # Update table
    table = db.query(Table).filter(Table.id == session.table_id).first()
    if table:
        table.current_guests = guest_count

    db.commit()

    return {"message": "Guest count updated", "guest_count": guest_count}


@router.get("/stats/duration", response_model=GuestDurationStats)
@limiter.limit("60/minute")
def get_duration_stats(
    request: Request,
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get guest stay duration statistics"""
    since = datetime.utcnow() - timedelta(days=days)

    sessions = db.query(TableSession).filter(
        TableSession.venue_id == current_user.venue_id,
        TableSession.status == TableSessionStatus.CLOSED,
        TableSession.ended_at >= since
    ).all()

    if not sessions:
        return GuestDurationStats(
            avg_duration_minutes=0,
            min_duration_minutes=0,
            max_duration_minutes=0,
            avg_spending_per_guest=0,
            total_sessions=0
        )

    durations = [s.duration_minutes or 0 for s in sessions]
    total_guests = sum(s.guest_count for s in sessions)
    total_spent = sum(s.total_spent for s in sessions)

    return GuestDurationStats(
        avg_duration_minutes=sum(durations) / len(durations),
        min_duration_minutes=min(durations),
        max_duration_minutes=max(durations),
        avg_spending_per_guest=total_spent / total_guests if total_guests > 0 else 0,
        total_sessions=len(sessions)
    )


@router.get("/table/{table_id}/history")
@limiter.limit("60/minute")
def get_table_history(
    request: Request,
    table_id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get history for a specific table"""
    history = db.query(TableHistory).filter(
        TableHistory.table_id == table_id,
        TableHistory.venue_id == current_user.venue_id
    ).order_by(TableHistory.recorded_at.desc()).limit(limit).all()

    return history

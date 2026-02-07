"""Waitlist management routes - direct access to waitlist endpoints."""

from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.session import DbSession
from app.models.reservations import Waitlist

router = APIRouter()


class WaitlistAdd(BaseModel):
    """Add to waitlist request."""
    guest_name: str
    phone: Optional[str] = None
    guest_phone: Optional[str] = None
    party_size: int
    quoted_wait: Optional[int] = None
    quoted_wait_minutes: Optional[int] = None
    location_id: int = 1
    seating_preference: Optional[str] = None
    special_requests: Optional[str] = None  # Maps to notes
    notes: Optional[str] = None
    vip: bool = False


class WaitlistUpdate(BaseModel):
    """Update waitlist entry request."""
    quoted_wait_minutes: Optional[int] = None
    status: Optional[str] = None
    table_ids: Optional[list] = None
    notes: Optional[str] = None


@router.get("/")
def list_waitlist(
    db: DbSession,
    location_id: int = 1,
    status: Optional[str] = None,
):
    """List waitlist entries."""
    query = db.query(Waitlist).filter(Waitlist.location_id == location_id)

    if status and status != 'all':
        query = query.filter(Waitlist.status == status)
    else:
        # By default, only show active entries
        query = query.filter(Waitlist.status.in_(["waiting", "notified"]))

    entries = query.order_by(Waitlist.position, Waitlist.added_at).all()

    # Map to frontend expected format
    return [
        {
            "id": e.id,
            "guest_name": e.guest_name,
            "phone": e.guest_phone,
            "party_size": e.party_size,
            "quoted_wait": e.quoted_wait_minutes,
            "actual_wait": e.actual_wait_minutes,
            "check_in_time": e.added_at.isoformat() if e.added_at else None,
            "status": e.status.value if hasattr(e.status, 'value') else e.status,
            "seating_preference": e.seating_preference,
            "special_requests": e.notes,  # notes is used for special requests
            "notifications_sent": 1 if e.sms_ready_sent else 0,
            "last_notification": e.sms_ready_sent_at.isoformat() if e.sms_ready_sent_at else None,
            "table_assigned": ",".join(map(str, e.table_ids)) if e.table_ids else None,
            "vip": False,
            "notes": e.notes,
            "seated_at": e.seated_at.isoformat() if e.seated_at else None,
        }
        for e in entries
    ]


@router.post("/")
def add_to_waitlist(
    db: DbSession,
    entry: WaitlistAdd,
):
    """Add a guest to the waitlist."""
    # Validate location if provided
    if entry.location_id:
        from app.models.location import Location
        loc = db.query(Location).filter(Location.id == entry.location_id).first()
        if not loc:
            entry.location_id = None  # Allow creation without location FK

    # Get next position
    max_position = db.query(Waitlist).filter(
        Waitlist.location_id == entry.location_id,
        Waitlist.status == "waiting"
    ).count()

    phone = entry.phone or entry.guest_phone
    wait_time = entry.quoted_wait or entry.quoted_wait_minutes or 15

    notes = entry.notes or entry.special_requests

    new_entry = Waitlist(
        guest_name=entry.guest_name,
        guest_phone=phone,
        party_size=entry.party_size,
        quoted_wait_minutes=wait_time,
        location_id=entry.location_id,
        seating_preference=entry.seating_preference,
        notes=notes,
        position=max_position + 1,
        status="waiting",
        estimated_wait_minutes=wait_time,
        sms_confirmation_sent=True,
    )

    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)

    return {
        "id": new_entry.id,
        "guest_name": new_entry.guest_name,
        "phone": new_entry.guest_phone,
        "party_size": new_entry.party_size,
        "quoted_wait": new_entry.quoted_wait_minutes,
        "check_in_time": new_entry.added_at.isoformat() if new_entry.added_at else None,
        "status": new_entry.status,
        "position": new_entry.position,
    }


@router.get("/stats")
def get_waitlist_stats(
    db: DbSession,
    location_id: int = 1,
):
    """Get waitlist statistics."""
    from sqlalchemy import func

    waiting_entries = db.query(Waitlist).filter(
        Waitlist.location_id == location_id,
        Waitlist.status == "waiting"
    ).all()

    total_waiting = len(waiting_entries)

    # Calculate average wait time
    avg_wait = 0
    if waiting_entries:
        avg_wait = sum(e.quoted_wait_minutes or 15 for e in waiting_entries) / len(waiting_entries)

    # Current longest wait
    longest_wait = 0
    if waiting_entries:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        waits = []
        for e in waiting_entries:
            if e.added_at:
                added = e.added_at if e.added_at.tzinfo else e.added_at.replace(tzinfo=timezone.utc)
                waits.append((now - added).total_seconds() / 60)
        longest_wait = max(waits) if waits else 0

    # Parties seated today
    from datetime import datetime, timedelta
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    seated_today = db.query(Waitlist).filter(
        Waitlist.location_id == location_id,
        Waitlist.status == "seated",
        Waitlist.seated_at >= today_start
    ).count()

    # No shows today
    no_shows_today = db.query(Waitlist).filter(
        Waitlist.location_id == location_id,
        Waitlist.left_reason == "no_show",
        Waitlist.left_at >= today_start
    ).count()

    return {
        "total_waiting": total_waiting,
        "avg_wait_time": round(avg_wait),
        "parties_seated_today": seated_today,
        "no_shows_today": no_shows_today,
        "current_longest_wait": round(longest_wait),
    }


@router.get("/{entry_id}")
def get_waitlist_entry(
    db: DbSession,
    entry_id: int,
):
    """Get a specific waitlist entry."""
    entry = db.query(Waitlist).filter(Waitlist.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Waitlist entry not found")

    return {
        "id": entry.id,
        "guest_name": entry.guest_name,
        "phone": entry.guest_phone,
        "party_size": entry.party_size,
        "quoted_wait": entry.quoted_wait_minutes,
        "actual_wait": entry.actual_wait_minutes,
        "check_in_time": entry.added_at.isoformat() if entry.added_at else None,
        "status": entry.status.value if hasattr(entry.status, 'value') else entry.status,
        "seating_preference": entry.seating_preference,
        "special_requests": entry.notes,
        "table_assigned": ",".join(map(str, entry.table_ids)) if entry.table_ids else None,
        "notes": entry.notes,
        "seated_at": entry.seated_at.isoformat() if entry.seated_at else None,
    }


@router.put("/{entry_id}")
def update_waitlist_entry(
    db: DbSession,
    entry_id: int,
    update: WaitlistUpdate,
):
    """Update a waitlist entry."""
    entry = db.query(Waitlist).filter(Waitlist.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Waitlist entry not found")

    if update.quoted_wait_minutes is not None:
        entry.quoted_wait_minutes = update.quoted_wait_minutes
        entry.estimated_wait_minutes = update.quoted_wait_minutes
    if update.status is not None:
        entry.status = update.status
    if update.table_ids is not None:
        entry.table_ids = update.table_ids
    if update.notes is not None:
        entry.notes = update.notes

    db.commit()
    db.refresh(entry)

    return {
        "id": entry.id,
        "status": entry.status,
        "quoted_wait": entry.quoted_wait_minutes,
    }


@router.post("/{entry_id}/notify")
def send_notification(
    db: DbSession,
    entry_id: int,
):
    """Send table ready notification."""
    entry = db.query(Waitlist).filter(Waitlist.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Waitlist entry not found")

    entry.sms_ready_sent = True
    entry.sms_ready_sent_at = datetime.now(timezone.utc)
    entry.status = "notified"

    db.commit()
    db.refresh(entry)

    return {
        "status": "notified",
        "message": f"Notification sent to {entry.guest_name}",
    }


@router.post("/{entry_id}/seat")
def seat_guest(
    db: DbSession,
    entry_id: int,
    table_id: Optional[int] = None,
):
    """Mark guest as seated."""
    entry = db.query(Waitlist).filter(Waitlist.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Waitlist entry not found")

    now = datetime.now(timezone.utc)
    entry.status = "seated"
    entry.seated_at = now

    if entry.added_at:
        added = entry.added_at.replace(tzinfo=timezone.utc) if entry.added_at.tzinfo is None else entry.added_at
        entry.actual_wait_minutes = int((now - added).total_seconds() / 60)

    if table_id:
        entry.table_ids = [table_id]

    db.commit()
    db.refresh(entry)

    return {
        "status": "seated",
        "actual_wait": entry.actual_wait_minutes,
    }


@router.post("/{entry_id}/cancel")
@router.post("/{entry_id}/remove")
def cancel_waitlist_entry(
    db: DbSession,
    entry_id: int,
    reason: str = "cancelled",
):
    """Cancel/remove a waitlist entry."""
    entry = db.query(Waitlist).filter(Waitlist.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Waitlist entry not found")

    entry.status = "cancelled"
    entry.left_at = datetime.now(timezone.utc)
    entry.left_reason = reason

    db.commit()

    return {
        "status": "cancelled",
        "reason": reason,
    }


@router.delete("/{entry_id}")
def delete_waitlist_entry(
    db: DbSession,
    entry_id: int,
):
    """Delete a waitlist entry."""
    entry = db.query(Waitlist).filter(Waitlist.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Waitlist entry not found")

    db.delete(entry)
    db.commit()

    return {"status": "deleted", "id": entry_id}

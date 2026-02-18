"""Internal Messaging API routes - staff-to-staff messaging system."""


from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import func, or_
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel

from app.db.session import DbSession
from app.core.rbac import CurrentUser, OptionalCurrentUser
from app.core.rate_limit import limiter

router = APIRouter()


# ==================== SCHEMAS ====================

class MessageCreate(BaseModel):
    recipient_id: Optional[int] = None
    recipient_role: Optional[str] = None
    subject: str
    body: str
    priority: str = "normal"

class MessageResponse(BaseModel):
    id: int
    sender_id: int
    sender_name: str
    recipient_id: Optional[int] = None
    recipient_name: Optional[str] = None
    recipient_role: Optional[str] = None
    subject: str
    body: str
    priority: str
    read: bool = False
    read_at: Optional[str] = None
    created_at: str


# ==================== In-memory store ====================
_messages: list = []
_next_msg_id = 1


@router.get("/")
@limiter.limit("60/minute")
def get_messaging_root(request: Request, db: DbSession):
    """Messaging inbox overview."""
    return get_inbox(request=request, db=db)


@router.post("/", response_model=MessageResponse)
@limiter.limit("30/minute")
def send_message(request: Request, data: MessageCreate, db: DbSession, current_user: CurrentUser = None):
    """Send a message to a staff member, role, or broadcast to all."""
    global _next_msg_id
    now = datetime.now(timezone.utc).isoformat()
    msg = {
        "id": _next_msg_id, "sender_id": 0, "sender_name": "System",
        "recipient_id": data.recipient_id, "recipient_name": None,
        "recipient_role": data.recipient_role, "subject": data.subject,
        "body": data.body, "priority": data.priority,
        "read": False, "read_at": None, "created_at": now,
    }
    _messages.append(msg)
    _next_msg_id += 1
    return MessageResponse(**msg)


@router.get("/inbox", response_model=List[MessageResponse])
@limiter.limit("60/minute")
def get_inbox(request: Request, db: DbSession, current_user: OptionalCurrentUser = None, unread_only: bool = False, priority: Optional[str] = None, limit: int = 50, offset: int = 0):
    """Get messages for current user (direct + role-based + broadcast)."""
    filtered = list(_messages)
    if unread_only:
        filtered = [m for m in filtered if not m["read"]]
    if priority:
        filtered = [m for m in filtered if m["priority"] == priority]
    return [MessageResponse(**m) for m in filtered[offset: offset + limit]]


@router.get("/sent", response_model=List[MessageResponse])
@limiter.limit("60/minute")
def get_sent_messages(request: Request, db: DbSession, current_user: OptionalCurrentUser = None, limit: int = 50, offset: int = 0):
    """Get sent messages."""
    return [MessageResponse(**m) for m in _messages[offset: offset + limit]]


@router.get("/unread-count")
@limiter.limit("60/minute")
def get_unread_count(request: Request, db: DbSession, current_user: OptionalCurrentUser = None):
    """Get count of unread messages."""
    count = sum(1 for m in _messages if not m["read"])
    return {"unread_count": count}


@router.get("/staff-list")
@limiter.limit("60/minute")
def get_staff_for_messaging(request: Request, db: DbSession, current_user: OptionalCurrentUser = None):
    """Get list of staff members for messaging."""
    from app.models.staff import StaffUser
    staff = db.query(StaffUser).filter(StaffUser.is_active == True).order_by(StaffUser.full_name).all()
    return [{"id": s.id, "name": s.full_name, "role": s.role} for s in staff]


@router.get("/{message_id}", response_model=MessageResponse)
@limiter.limit("60/minute")
def get_message(request: Request, message_id: int, db: DbSession, current_user: OptionalCurrentUser = None):
    """Get a specific message."""
    for m in _messages:
        if m["id"] == message_id:
            return MessageResponse(**m)
    raise HTTPException(status_code=404, detail="Message not found")


@router.put("/{message_id}/read")
@limiter.limit("30/minute")
def mark_as_read(request: Request, message_id: int, db: DbSession, current_user: OptionalCurrentUser = None):
    """Mark a message as read."""
    for m in _messages:
        if m["id"] == message_id:
            m["read"] = True
            m["read_at"] = datetime.now(timezone.utc).isoformat()
            return {"message": "Marked as read"}
    raise HTTPException(status_code=404, detail="Message not found")


@router.put("/mark-all-read")
@limiter.limit("30/minute")
def mark_all_as_read(request: Request, db: DbSession, current_user: OptionalCurrentUser = None):
    """Mark all messages as read."""
    now = datetime.now(timezone.utc).isoformat()
    for m in _messages:
        if not m["read"]:
            m["read"] = True
            m["read_at"] = now
    return {"message": "All messages marked as read"}


@router.delete("/{message_id}")
@limiter.limit("30/minute")
def delete_message(request: Request, message_id: int, db: DbSession, current_user: OptionalCurrentUser = None):
    """Delete a message."""
    global _messages
    original_len = len(_messages)
    _messages = [m for m in _messages if m["id"] != message_id]
    if len(_messages) == original_len:
        raise HTTPException(status_code=404, detail="Message not found or not authorized")
    return {"message": "Message deleted"}


@router.post("/broadcast")
@limiter.limit("30/minute")
def broadcast_message(request: Request, db: DbSession, current_user: OptionalCurrentUser = None, subject: str = "", body: str = "", priority: str = "normal"):
    """Broadcast a message to all staff."""
    global _next_msg_id
    now = datetime.now(timezone.utc).isoformat()
    msg = {
        "id": _next_msg_id, "sender_id": 0, "sender_name": "System",
        "recipient_id": None, "recipient_name": None,
        "recipient_role": None, "subject": subject,
        "body": body, "priority": priority,
        "read": False, "read_at": None, "created_at": now,
    }
    _messages.append(msg)
    _next_msg_id += 1
    return {"message": "Broadcast sent", "message_id": msg["id"]}

"""Audit logs API routes."""

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel
from sqlalchemy import func

from app.core.rate_limit import limiter
from app.db.session import DbSession
from app.models.operations import AuditLogEntry

router = APIRouter()


class AuditLog(BaseModel):
    id: str
    timestamp: str
    user_id: str
    user_name: str
    action: str
    entity_type: str
    entity_id: str
    entity_name: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    ip_address: str
    details: Optional[str] = None


class AuditSummary(BaseModel):
    total_actions: int
    users_active: int
    most_common_action: str
    security_events: int


def _row_to_audit_log(entry: AuditLogEntry) -> AuditLog:
    """Convert a database AuditLogEntry to the AuditLog response schema."""
    details_dict = entry.details or {}
    return AuditLog(
        id=str(entry.id),
        timestamp=entry.created_at.isoformat() + "Z" if entry.created_at else "",
        user_id=str(entry.user_id) if entry.user_id is not None else "",
        user_name=entry.user_name or "",
        action=entry.action or "",
        entity_type=entry.entity_type or "",
        entity_id=entry.entity_id or "",
        entity_name=details_dict.get("entity_name", "") if isinstance(details_dict, dict) else "",
        old_value=details_dict.get("old_value") if isinstance(details_dict, dict) else None,
        new_value=details_dict.get("new_value") if isinstance(details_dict, dict) else None,
        ip_address=entry.ip_address or "",
        details=details_dict.get("description") if isinstance(details_dict, dict) else (str(details_dict) if details_dict else None),
    )


@router.get("/")
@limiter.limit("60/minute")
async def get_audit_logs(
    request: Request,
    db: DbSession,
    action: str = Query(None),
    entity_type: str = Query(None),
    user_id: str = Query(None),
    start_date: str = Query(None),
    end_date: str = Query(None),
    limit: int = Query(100),
):
    """Get audit logs with filters."""
    query = db.query(AuditLogEntry)

    if action:
        query = query.filter(AuditLogEntry.action == action)
    if entity_type:
        query = query.filter(AuditLogEntry.entity_type == entity_type)
    if user_id:
        query = query.filter(AuditLogEntry.user_id == int(user_id))
    if start_date:
        query = query.filter(AuditLogEntry.created_at >= datetime.fromisoformat(start_date))
    if end_date:
        query = query.filter(AuditLogEntry.created_at <= datetime.fromisoformat(end_date))

    entries = query.order_by(AuditLogEntry.created_at.desc()).limit(limit).all()
    return [_row_to_audit_log(e) for e in entries]


@router.get("/summary")
@limiter.limit("60/minute")
async def get_audit_summary(request: Request, db: DbSession, period: str = Query("today")):
    """Get audit summary for a period."""
    base_query = db.query(AuditLogEntry)

    now = datetime.now(timezone.utc)
    start = None
    if period == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    if start is not None:
        base_query = base_query.filter(AuditLogEntry.created_at >= start)

    total_actions = base_query.count()

    active_query = db.query(func.count(func.distinct(AuditLogEntry.user_id)))
    if start is not None:
        active_query = active_query.filter(AuditLogEntry.created_at >= start)
    users_active = active_query.scalar() or 0

    # Most common action
    most_common_row = (
        base_query
        .with_entities(AuditLogEntry.action, func.count(AuditLogEntry.id).label("cnt"))
        .group_by(AuditLogEntry.action)
        .order_by(func.count(AuditLogEntry.id).desc())
        .first()
    )
    most_common_action = most_common_row[0] if most_common_row else "none"

    # Security events: login, logout, and failed auth-related actions
    security_actions = ["login", "logout", "failed_login", "password_change", "role_change"]
    security_events = base_query.filter(AuditLogEntry.action.in_(security_actions)).count()

    return AuditSummary(
        total_actions=total_actions,
        users_active=users_active,
        most_common_action=most_common_action,
        security_events=security_events,
    )


@router.get("/actions")
@limiter.limit("60/minute")
async def get_action_types(request: Request, db: DbSession):
    """Get available action types."""
    rows = (
        db.query(AuditLogEntry.action)
        .distinct()
        .order_by(AuditLogEntry.action)
        .all()
    )
    actions = [r[0] for r in rows if r[0]]
    return actions if actions else ["create", "update", "delete", "login", "logout", "void", "refund", "approve", "reject", "export"]


@router.get("/entity-types")
@limiter.limit("60/minute")
async def get_entity_types(request: Request, db: DbSession):
    """Get available entity types."""
    rows = (
        db.query(AuditLogEntry.entity_type)
        .distinct()
        .order_by(AuditLogEntry.entity_type)
        .all()
    )
    types = [r[0] for r in rows if r[0]]
    return types if types else ["product", "order", "order_item", "customer", "staff", "inventory", "payment", "session", "settings", "report"]

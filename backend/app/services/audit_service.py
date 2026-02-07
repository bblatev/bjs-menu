"""Audit logging service.

Provides functions to write audit log entries for state-changing operations.
Used by the AuditLoggingMiddleware and can be called directly from route handlers
for more detailed logging (e.g., old/new values on updates).
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.operations import AuditLogEntry

logger = logging.getLogger("audit")


def log_action(
    action: str,
    entity_type: str = "",
    entity_id: str = "",
    user_id: Optional[int] = None,
    user_name: str = "",
    ip_address: str = "",
    details: Optional[dict[str, Any]] = None,
    db: Optional[Session] = None,
) -> None:
    """Write an audit log entry.

    Args:
        action: The action performed (create, update, delete, login, etc.)
        entity_type: Type of entity affected (order, menu_item, staff, etc.)
        entity_id: ID of the affected entity
        user_id: ID of the user performing the action
        user_name: Name/email of the user
        ip_address: Client IP address
        details: Additional details (old_value, new_value, description, etc.)
        db: Optional existing DB session. If None, creates a new one.
    """
    own_session = db is None
    if own_session:
        db = SessionLocal()

    try:
        entry = AuditLogEntry(
            user_id=user_id,
            user_name=user_name,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else "",
            details=details or {},
            ip_address=ip_address or "",
            created_at=datetime.now(timezone.utc),
        )
        db.add(entry)
        db.commit()
    except Exception:
        logger.exception("Failed to write audit log entry")
        if own_session:
            db.rollback()
    finally:
        if own_session:
            db.close()


def log_login(user_id: int, email: str, ip_address: str, success: bool = True) -> None:
    """Log a login attempt."""
    log_action(
        action="login" if success else "failed_login",
        entity_type="session",
        user_id=user_id if success else None,
        user_name=email,
        ip_address=ip_address,
        details={"description": f"{'Successful' if success else 'Failed'} login for {email}"},
    )


def log_entity_change(
    action: str,
    entity_type: str,
    entity_id: str,
    user_id: Optional[int] = None,
    user_name: str = "",
    ip_address: str = "",
    old_value: Any = None,
    new_value: Any = None,
    description: str = "",
    db: Optional[Session] = None,
) -> None:
    """Log a create/update/delete on an entity with old/new values."""
    details: dict[str, Any] = {}
    if description:
        details["description"] = description
    if old_value is not None:
        details["old_value"] = str(old_value)[:1000]
    if new_value is not None:
        details["new_value"] = str(new_value)[:1000]

    log_action(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=user_id,
        user_name=user_name,
        ip_address=ip_address,
        details=details,
        db=db,
    )

"""Audit logs API routes."""

from typing import List, Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel

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


@router.get("/")
async def get_audit_logs(
    action: str = Query(None),
    entity_type: str = Query(None),
    user_id: str = Query(None),
    start_date: str = Query(None),
    end_date: str = Query(None),
    limit: int = Query(100)
):
    """Get audit logs with filters."""
    return [
        AuditLog(id="1", timestamp="2026-02-01T17:45:00Z", user_id="1", user_name="Admin", action="update", entity_type="product", entity_id="5", entity_name="Margherita Pizza", old_value="12.99", new_value="14.99", ip_address="192.168.1.100", details="Price update"),
        AuditLog(id="2", timestamp="2026-02-01T17:30:00Z", user_id="2", user_name="Manager", action="create", entity_type="order", entity_id="1234", entity_name="Order #1234", ip_address="192.168.1.101"),
        AuditLog(id="3", timestamp="2026-02-01T17:15:00Z", user_id="1", user_name="Admin", action="delete", entity_type="product", entity_id="99", entity_name="Old Item", ip_address="192.168.1.100"),
        AuditLog(id="4", timestamp="2026-02-01T17:00:00Z", user_id="3", user_name="Staff", action="login", entity_type="session", entity_id="sess-123", entity_name="Login", ip_address="192.168.1.102"),
        AuditLog(id="5", timestamp="2026-02-01T16:45:00Z", user_id="2", user_name="Manager", action="void", entity_type="order_item", entity_id="item-456", entity_name="Beer Draft", ip_address="192.168.1.101", details="Customer complaint"),
    ]


@router.get("/summary")
async def get_audit_summary(period: str = Query("today")):
    """Get audit summary for a period."""
    return AuditSummary(
        total_actions=245,
        users_active=8,
        most_common_action="create",
        security_events=2
    )


@router.get("/actions")
async def get_action_types():
    """Get available action types."""
    return ["create", "update", "delete", "login", "logout", "void", "refund", "approve", "reject", "export"]


@router.get("/entity-types")
async def get_entity_types():
    """Get available entity types."""
    return ["product", "order", "order_item", "customer", "staff", "inventory", "payment", "session", "settings", "report"]

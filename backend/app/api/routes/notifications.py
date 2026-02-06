"""Notifications API routes."""

from typing import List, Optional, Dict
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class NotificationPreference(BaseModel):
    channel: str  # email, sms, push, slack
    enabled: bool
    categories: List[str]  # orders, inventory, staff, reports


class AlertConfig(BaseModel):
    id: str
    name: str
    type: str  # low_stock, high_sales, staff_clock, order_delay
    enabled: bool
    threshold: Optional[float] = None
    channels: List[str]
    recipients: List[str]


class Notification(BaseModel):
    id: str
    title: str
    message: str
    type: str
    priority: str  # low, medium, high, urgent
    read: bool
    created_at: str
    action_url: Optional[str] = None


@router.get("/preferences")
async def get_notification_preferences():
    """Get notification preferences."""
    return [
        NotificationPreference(channel="email", enabled=True, categories=["orders", "inventory", "reports"]),
        NotificationPreference(channel="sms", enabled=True, categories=["urgent", "staff"]),
        NotificationPreference(channel="push", enabled=True, categories=["orders", "inventory"]),
        NotificationPreference(channel="slack", enabled=False, categories=[]),
    ]


@router.put("/preferences")
async def update_notification_preferences(preferences: List[NotificationPreference]):
    """Update notification preferences."""
    return {"success": True}


@router.get("/alerts/config")
async def get_alert_configs():
    """Get alert configurations."""
    return [
        AlertConfig(id="1", name="Low Stock Alert", type="low_stock", enabled=True, threshold=10, channels=["email", "push"], recipients=["manager@bjsbar.com"]),
        AlertConfig(id="2", name="High Sales Alert", type="high_sales", enabled=True, threshold=5000, channels=["email"], recipients=["owner@bjsbar.com"]),
        AlertConfig(id="3", name="Order Delay Alert", type="order_delay", enabled=True, threshold=15, channels=["push"], recipients=["kitchen@bjsbar.com"]),
        AlertConfig(id="4", name="Staff Clock-in Reminder", type="staff_clock", enabled=False, channels=["sms"], recipients=[]),
    ]


@router.get("/alerts/config/{config_id}")
async def get_alert_config(config_id: str):
    """Get a specific alert configuration."""
    return AlertConfig(id=config_id, name="Low Stock Alert", type="low_stock", enabled=True, threshold=10, channels=["email", "push"], recipients=["manager@bjsbar.com"])


@router.put("/alerts/config/{config_id}")
async def update_alert_config(config_id: str, config: AlertConfig):
    """Update an alert configuration."""
    return {"success": True}


@router.api_route("/test/all-channels", methods=["GET", "POST"])
async def test_all_channels():
    """Send test notification to all channels."""
    return {"success": True, "sent_to": ["email", "sms", "push"]}


@router.get("/")
async def get_notifications():
    """Get user notifications."""
    return [
        Notification(id="1", title="Low Stock Alert", message="Vodka Premium is below reorder point", type="inventory", priority="high", read=False, created_at="2026-02-01T17:00:00Z", action_url="/stock"),
        Notification(id="2", title="New Review", message="You received a 5-star review on Google", type="feedback", priority="low", read=True, created_at="2026-02-01T16:00:00Z", action_url="/feedback"),
        Notification(id="3", title="Shift Reminder", message="John Doe's shift starts in 30 minutes", type="staff", priority="medium", read=False, created_at="2026-02-01T15:30:00Z"),
    ]


@router.post("/{notification_id}/read")
async def mark_notification_read(notification_id: str):
    """Mark a notification as read."""
    return {"success": True}

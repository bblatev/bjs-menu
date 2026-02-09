"""Notifications API routes."""

from typing import List, Optional, Dict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.db.session import DbSession
from app.models.operations import (
    Notification as NotificationModel,
    NotificationPreference as NotificationPreferenceModel,
    AlertConfig as AlertConfigModel,
)
from app.core.rbac import CurrentUser

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
async def get_notification_preferences(db: DbSession, current_user: CurrentUser):
    """Get notification preferences."""
    stmt = select(NotificationPreferenceModel).where(
        NotificationPreferenceModel.user_id == current_user.user_id
    )
    results = db.execute(stmt).scalars().all()
    return [
        NotificationPreference(
            channel=pref.channel,
            enabled=pref.enabled,
            categories=pref.categories or [],
        )
        for pref in results
    ]


@router.put("/preferences")
async def update_notification_preferences(
    preferences: List[NotificationPreference],
    db: DbSession,
    current_user: CurrentUser,
):
    """Update notification preferences."""
    # Delete existing preferences for this user
    stmt = select(NotificationPreferenceModel).where(
        NotificationPreferenceModel.user_id == current_user.user_id
    )
    existing = db.execute(stmt).scalars().all()
    for pref in existing:
        db.delete(pref)

    # Insert new preferences
    for pref in preferences:
        db_pref = NotificationPreferenceModel(
            user_id=current_user.user_id,
            channel=pref.channel,
            enabled=pref.enabled,
            categories=pref.categories,
        )
        db.add(db_pref)

    db.commit()
    return {"success": True}


@router.put("/alerts/config")
async def update_all_alert_config(data: dict, db: DbSession, current_user: CurrentUser):
    """Update overall alert configuration."""
    configs = db.query(AlertConfigModel).all()
    if not configs:
        # Create a default config
        cfg = AlertConfigModel(
            name="Default",
            type="general",
            enabled=data.get("email_enabled", True),
            channels=["email"] if data.get("email_enabled") else [],
        )
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
        return {"success": True, "id": cfg.id}
    for cfg in configs:
        if "email_enabled" in data:
            channels = cfg.channels or []
            if data["email_enabled"] and "email" not in channels:
                channels.append("email")
            elif not data["email_enabled"] and "email" in channels:
                channels.remove("email")
            cfg.channels = channels
        if "sms_enabled" in data:
            channels = cfg.channels or []
            if data["sms_enabled"] and "sms" not in channels:
                channels.append("sms")
            elif not data["sms_enabled"] and "sms" in channels:
                channels.remove("sms")
            cfg.channels = channels
    db.commit()
    return {"success": True}


@router.get("/alerts/config")
async def get_alert_configs(db: DbSession, current_user: CurrentUser):
    """Get alert configurations."""
    stmt = select(AlertConfigModel)
    results = db.execute(stmt).scalars().all()
    return [
        AlertConfig(
            id=str(cfg.id),
            name=cfg.name,
            type=cfg.type,
            enabled=cfg.enabled,
            threshold=cfg.threshold,
            channels=cfg.channels or [],
            recipients=cfg.recipients or [],
        )
        for cfg in results
    ]


@router.get("/alerts/config/{config_id}")
async def get_alert_config(config_id: str, db: DbSession, current_user: CurrentUser):
    """Get a specific alert configuration."""
    cfg = db.get(AlertConfigModel, int(config_id))
    if not cfg:
        raise HTTPException(status_code=404, detail="Alert config not found")
    return AlertConfig(
        id=str(cfg.id),
        name=cfg.name,
        type=cfg.type,
        enabled=cfg.enabled,
        threshold=cfg.threshold,
        channels=cfg.channels or [],
        recipients=cfg.recipients or [],
    )


@router.put("/alerts/config/{config_id}")
async def update_alert_config(
    config_id: str,
    config: AlertConfig,
    db: DbSession,
    current_user: CurrentUser,
):
    """Update an alert configuration."""
    cfg = db.get(AlertConfigModel, int(config_id))
    if not cfg:
        raise HTTPException(status_code=404, detail="Alert config not found")

    cfg.name = config.name
    cfg.type = config.type
    cfg.enabled = config.enabled
    cfg.threshold = config.threshold
    cfg.channels = config.channels
    cfg.recipients = config.recipients

    db.commit()
    db.refresh(cfg)
    return {"success": True}


@router.api_route("/test/all-channels", methods=["GET", "POST"])
async def test_all_channels(db: DbSession, current_user: CurrentUser):
    """Send test notification to all channels."""
    # Retrieve the user's enabled channels from their preferences
    stmt = select(NotificationPreferenceModel).where(
        NotificationPreferenceModel.user_id == current_user.user_id,
        NotificationPreferenceModel.enabled == True,
    )
    results = db.execute(stmt).scalars().all()
    sent_to = [pref.channel for pref in results]

    # Create a test notification record
    test_notification = NotificationModel(
        user_id=current_user.user_id,
        title="Test Notification",
        message="This is a test notification sent to all enabled channels.",
        type="info",
        category="test",
        read=False,
    )
    db.add(test_notification)
    db.commit()

    return {"success": True, "sent_to": sent_to}


@router.get("/")
async def get_notifications(db: DbSession, current_user: CurrentUser):
    """Get user notifications."""
    stmt = (
        select(NotificationModel)
        .where(NotificationModel.user_id == current_user.user_id)
        .order_by(NotificationModel.created_at.desc())
    )
    results = db.execute(stmt).scalars().all()
    return [
        Notification(
            id=str(n.id),
            title=n.title,
            message=n.message or "",
            type=n.type or "info",
            priority="medium",
            read=n.read or False,
            created_at=n.created_at.isoformat() if n.created_at else "",
            action_url=n.action_url,
        )
        for n in results
    ]


@router.post("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    db: DbSession,
    current_user: CurrentUser,
):
    """Mark a notification as read."""
    notification = db.get(NotificationModel, int(notification_id))
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    if notification.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    notification.read = True
    db.commit()
    return {"success": True}

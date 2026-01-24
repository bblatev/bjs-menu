"""Real-time SMS Order Status Notification Service."""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from app.models.advanced_features import OrderStatusNotification


class NotificationService:
    """Service for order status notifications."""

    def __init__(self, db: Session):
        self.db = db

    TEMPLATES = {
        "order_received": "Your order #{order_id} has been received! We'll let you know when it's being prepared.",
        "preparing": "Good news! Your order #{order_id} is now being prepared. Estimated time: {eta} minutes.",
        "ready": "Your order #{order_id} is ready! {pickup_instructions}",
        "out_for_delivery": "Your order #{order_id} is on its way! Track here: {tracking_url}",
        "delivered": "Your order #{order_id} has been delivered. Enjoy your meal!",
    }

    def create_notification(
        self,
        order_id: int,
        notification_type: str,
        channel: str,
        recipient: str,
        message: str,
        tracking_url: Optional[str] = None,
    ) -> OrderStatusNotification:
        """Create a new notification."""
        notification = OrderStatusNotification(
            order_id=order_id,
            notification_type=notification_type,
            channel=channel,
            recipient=recipient,
            message=message,
            tracking_url=tracking_url,
        )
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        return notification

    def send_notification(
        self,
        notification_id: int,
    ) -> OrderStatusNotification:
        """Mark notification as sent."""
        notification = self.db.get(OrderStatusNotification, notification_id)
        if not notification:
            raise ValueError(f"Notification {notification_id} not found")

        # In production, this would actually send via SMS/email/push
        # For now, just mark as sent
        notification.sent_at = datetime.utcnow()

        # Simulate delivery after 2 seconds
        notification.delivered_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(notification)
        return notification

    def mark_failed(
        self,
        notification_id: int,
        reason: str,
    ) -> OrderStatusNotification:
        """Mark notification as failed."""
        notification = self.db.get(OrderStatusNotification, notification_id)
        if not notification:
            raise ValueError(f"Notification {notification_id} not found")

        notification.failed = True
        notification.failure_reason = reason

        self.db.commit()
        self.db.refresh(notification)
        return notification

    def get_order_notifications(
        self,
        order_id: int,
    ) -> List[OrderStatusNotification]:
        """Get all notifications for an order."""
        query = select(OrderStatusNotification).where(
            OrderStatusNotification.order_id == order_id
        ).order_by(OrderStatusNotification.created_at)

        result = self.db.execute(query)
        return list(result.scalars().all())

    def send_order_update(
        self,
        order_id: int,
        notification_type: str,
        recipient: str,
        channel: str = "sms",
        eta: Optional[int] = None,
        pickup_instructions: Optional[str] = None,
        tracking_url: Optional[str] = None,
    ) -> OrderStatusNotification:
        """Send an order status update notification."""
        # Get template and fill in variables
        template = self.TEMPLATES.get(notification_type, "Your order #{order_id} status has been updated.")

        message = template.format(
            order_id=order_id,
            eta=eta or "15-20",
            pickup_instructions=pickup_instructions or "Please come to the counter.",
            tracking_url=tracking_url or "",
        )

        # Create notification
        notification = self.create_notification(
            order_id=order_id,
            notification_type=notification_type,
            channel=channel,
            recipient=recipient,
            message=message,
            tracking_url=tracking_url,
        )

        # Send notification
        self.send_notification(notification.id)

        return notification

    def get_stats(
        self,
        days: int = 7,
    ) -> Dict[str, Any]:
        """Get notification statistics."""
        since = datetime.utcnow() - timedelta(days=days)

        # Total counts
        query = select(
            func.count(OrderStatusNotification.id).label("total"),
            func.count(OrderStatusNotification.delivered_at).label("delivered"),
            func.count().filter(OrderStatusNotification.failed == True).label("failed"),
        ).where(OrderStatusNotification.created_at >= since)

        result = self.db.execute(query)
        totals = result.first()

        total = totals.total or 0
        delivered = totals.delivered or 0
        failed = totals.failed or 0

        # By type
        type_query = select(
            OrderStatusNotification.notification_type,
            func.count(OrderStatusNotification.id).label("count"),
        ).where(
            OrderStatusNotification.created_at >= since
        ).group_by(OrderStatusNotification.notification_type)

        type_result = self.db.execute(type_query)
        by_type = {row.notification_type: row.count for row in type_result.all()}

        # By channel
        channel_query = select(
            OrderStatusNotification.channel,
            func.count(OrderStatusNotification.id).label("count"),
        ).where(
            OrderStatusNotification.created_at >= since
        ).group_by(OrderStatusNotification.channel)

        channel_result = self.db.execute(channel_query)
        by_channel = {row.channel: row.count for row in channel_result.all()}

        return {
            "total_sent": total,
            "total_delivered": delivered,
            "total_failed": failed,
            "delivery_rate": (delivered / total * 100) if total > 0 else 0,
            "by_type": by_type,
            "by_channel": by_channel,
        }

    def retry_failed(
        self,
        notification_id: int,
    ) -> OrderStatusNotification:
        """Retry a failed notification."""
        notification = self.db.get(OrderStatusNotification, notification_id)
        if not notification:
            raise ValueError(f"Notification {notification_id} not found")

        if not notification.failed:
            return notification

        # Reset failure status
        notification.failed = False
        notification.failure_reason = None

        # Create new attempt
        new_notification = self.create_notification(
            order_id=notification.order_id,
            notification_type=notification.notification_type,
            channel=notification.channel,
            recipient=notification.recipient,
            message=notification.message,
            tracking_url=notification.tracking_url,
        )

        # Send
        self.send_notification(new_notification.id)

        return new_notification

    def get_pending(
        self,
    ) -> List[OrderStatusNotification]:
        """Get pending (unsent) notifications."""
        query = select(OrderStatusNotification).where(
            and_(
                OrderStatusNotification.sent_at.is_(None),
                OrderStatusNotification.failed == False,
            )
        ).order_by(OrderStatusNotification.created_at)

        result = self.db.execute(query)
        return list(result.scalars().all())

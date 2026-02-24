"""Zapier / Make.com Automation Webhook Connector.

Provides a webhook-based automation platform integration:
- Trigger webhooks on system events (orders, payments, inventory, etc.)
- Receive actions from Zapier/Make via incoming webhooks
- Support for custom trigger definitions
- Event filtering and transformation
- HMAC signature verification for security
"""

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


# Event types that can trigger outgoing webhooks
TRIGGER_EVENTS = {
    "order.created": "Fires when a new order is placed",
    "order.completed": "Fires when an order is marked completed",
    "order.cancelled": "Fires when an order is cancelled",
    "order.modified": "Fires when an order is modified",
    "payment.received": "Fires when a payment is processed",
    "payment.refunded": "Fires when a refund is issued",
    "reservation.created": "Fires when a new reservation is made",
    "reservation.cancelled": "Fires when a reservation is cancelled",
    "reservation.seated": "Fires when a reservation party is seated",
    "waitlist.added": "Fires when a guest joins the waitlist",
    "waitlist.seated": "Fires when a waitlist guest is seated",
    "inventory.low_stock": "Fires when stock falls below threshold",
    "inventory.received": "Fires when inventory is received",
    "inventory.counted": "Fires when an inventory count is completed",
    "staff.clocked_in": "Fires when staff clocks in",
    "staff.clocked_out": "Fires when staff clocks out",
    "review.received": "Fires when a customer review is received",
    "customer.created": "Fires when a new customer is registered",
    "customer.vip_status_changed": "Fires when VIP status changes",
    "daily.close": "Fires when daily close/reconciliation is completed",
    "table.status_changed": "Fires when a table status changes",
    "alert.triggered": "Fires when a system alert is triggered",
}

# Action types that can be received from Zapier/Make
ACTION_TYPES = {
    "create_reservation": "Create a new reservation",
    "update_menu_item": "Update menu item details or price",
    "send_notification": "Send notification to staff",
    "update_inventory": "Adjust inventory levels",
    "create_customer": "Create a new customer record",
    "apply_discount": "Apply discount to current/next order",
    "update_table_status": "Change table status",
    "send_sms": "Send SMS to customer",
    "send_email": "Send email to customer",
    "create_task": "Create a staff task",
}


class AutomationSubscription:
    """A webhook subscription for automation events."""

    def __init__(
        self,
        id: int,
        name: str,
        webhook_url: str,
        events: List[str],
        platform: str = "zapier",
        secret: Optional[str] = None,
        is_active: bool = True,
        filters: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        self.id = id
        self.name = name
        self.webhook_url = webhook_url
        self.events = events
        self.platform = platform
        self.secret = secret
        self.is_active = is_active
        self.filters = filters or {}
        self.headers = headers or {}
        self.created_at = datetime.now(timezone.utc)
        self.last_triggered_at: Optional[datetime] = None
        self.trigger_count = 0
        self.failure_count = 0
        self.last_error: Optional[str] = None


class ZapierAutomationService:
    """Webhook automation service for Zapier/Make.com integration."""

    def __init__(self):
        self._subscriptions: Dict[int, AutomationSubscription] = {}
        self._next_id = 1
        self._event_log: List[Dict[str, Any]] = []
        self._incoming_actions: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Subscription Management
    # ------------------------------------------------------------------

    def create_subscription(
        self,
        name: str,
        webhook_url: str,
        events: List[str],
        platform: str = "zapier",
        secret: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Register a new webhook subscription."""
        # Validate events
        invalid = [e for e in events if e not in TRIGGER_EVENTS]
        if invalid:
            return {"error": f"Invalid events: {invalid}", "valid_events": list(TRIGGER_EVENTS.keys())}

        sub = AutomationSubscription(
            id=self._next_id,
            name=name,
            webhook_url=webhook_url,
            events=events,
            platform=platform,
            secret=secret,
            filters=filters,
            headers=headers,
        )
        self._subscriptions[self._next_id] = sub
        self._next_id += 1
        return self._sub_to_dict(sub)

    def update_subscription(
        self,
        sub_id: int,
        name: Optional[str] = None,
        webhook_url: Optional[str] = None,
        events: Optional[List[str]] = None,
        is_active: Optional[bool] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Update an existing subscription."""
        sub = self._subscriptions.get(sub_id)
        if not sub:
            return {"error": "Subscription not found"}

        if name is not None:
            sub.name = name
        if webhook_url is not None:
            sub.webhook_url = webhook_url
        if events is not None:
            invalid = [e for e in events if e not in TRIGGER_EVENTS]
            if invalid:
                return {"error": f"Invalid events: {invalid}"}
            sub.events = events
        if is_active is not None:
            sub.is_active = is_active
        if filters is not None:
            sub.filters = filters

        return self._sub_to_dict(sub)

    def delete_subscription(self, sub_id: int) -> Dict[str, Any]:
        """Delete a webhook subscription."""
        sub = self._subscriptions.pop(sub_id, None)
        if not sub:
            return {"error": "Subscription not found"}
        return {"deleted": True, "id": sub_id}

    def get_subscription(self, sub_id: int) -> Dict[str, Any]:
        sub = self._subscriptions.get(sub_id)
        if not sub:
            return {"error": "Subscription not found"}
        return self._sub_to_dict(sub)

    def list_subscriptions(
        self,
        platform: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """List all webhook subscriptions."""
        subs = list(self._subscriptions.values())
        if platform:
            subs = [s for s in subs if s.platform == platform]
        if is_active is not None:
            subs = [s for s in subs if s.is_active == is_active]
        return [self._sub_to_dict(s) for s in subs]

    # ------------------------------------------------------------------
    # Event Triggering
    # ------------------------------------------------------------------

    async def trigger_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Trigger an event and send to all matching subscriptions."""
        if event_type not in TRIGGER_EVENTS:
            return {"error": f"Unknown event type: {event_type}"}

        matching_subs = [
            s for s in self._subscriptions.values()
            if s.is_active and event_type in s.events
        ]

        results = []
        for sub in matching_subs:
            if not self._passes_filters(sub.filters, payload):
                continue

            result = await self._send_webhook(sub, event_type, payload)
            results.append(result)

        log_entry = {
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload_keys": list(payload.keys()),
            "subscriptions_matched": len(matching_subs),
            "webhooks_sent": len(results),
            "results": results,
        }
        self._event_log.append(log_entry)
        if len(self._event_log) > 1000:
            self._event_log = self._event_log[-500:]

        return log_entry

    async def _send_webhook(
        self,
        sub: AutomationSubscription,
        event_type: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Send a webhook to a subscription endpoint."""
        body = json.dumps({
            "event": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": payload,
        })

        headers = {
            "Content-Type": "application/json",
            "X-BJS-Event": event_type,
            "X-BJS-Delivery-Id": f"{sub.id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            **sub.headers,
        }

        if sub.secret:
            signature = hmac.new(
                sub.secret.encode("utf-8"),
                body.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            headers["X-BJS-Signature"] = f"sha256={signature}"

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(sub.webhook_url, content=body, headers=headers)
                sub.last_triggered_at = datetime.now(timezone.utc)
                sub.trigger_count += 1

                if resp.status_code >= 400:
                    sub.failure_count += 1
                    sub.last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"

                return {
                    "subscription_id": sub.id,
                    "status_code": resp.status_code,
                    "success": resp.status_code < 400,
                }
        except Exception as e:
            sub.failure_count += 1
            sub.last_error = str(e)
            logger.error(f"Webhook delivery failed for sub {sub.id}: {e}")
            return {
                "subscription_id": sub.id,
                "status_code": 0,
                "success": False,
                "error": str(e),
            }

    @staticmethod
    def _passes_filters(filters: Dict[str, Any], payload: Dict[str, Any]) -> bool:
        """Check if a payload passes subscription filters."""
        if not filters:
            return True
        for key, expected in filters.items():
            actual = payload.get(key)
            if isinstance(expected, list):
                if actual not in expected:
                    return False
            elif actual != expected:
                return False
        return True

    # ------------------------------------------------------------------
    # Incoming Actions (from Zapier/Make)
    # ------------------------------------------------------------------

    def process_incoming_action(
        self,
        action_type: str,
        payload: Dict[str, Any],
        platform: str = "zapier",
    ) -> Dict[str, Any]:
        """Process an incoming action from Zapier/Make."""
        if action_type not in ACTION_TYPES:
            return {"error": f"Unknown action type: {action_type}", "valid_actions": list(ACTION_TYPES.keys())}

        action_log = {
            "action_type": action_type,
            "platform": platform,
            "payload": payload,
            "received_at": datetime.now(timezone.utc).isoformat(),
            "status": "processed",
        }
        self._incoming_actions.append(action_log)
        if len(self._incoming_actions) > 1000:
            self._incoming_actions = self._incoming_actions[-500:]

        return {
            "status": "accepted",
            "action_type": action_type,
            "message": f"Action '{action_type}' queued for processing",
        }

    def verify_incoming_webhook(
        self, body: bytes, signature: str, secret: str
    ) -> bool:
        """Verify HMAC signature on incoming webhooks."""
        expected = hmac.new(
            secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(f"sha256={expected}", signature)

    # ------------------------------------------------------------------
    # Event Log & Stats
    # ------------------------------------------------------------------

    def get_event_log(
        self, limit: int = 50, event_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        log = self._event_log
        if event_type:
            log = [e for e in log if e["event_type"] == event_type]
        return log[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        active = [s for s in self._subscriptions.values() if s.is_active]
        return {
            "total_subscriptions": len(self._subscriptions),
            "active_subscriptions": len(active),
            "total_events_triggered": len(self._event_log),
            "total_actions_received": len(self._incoming_actions),
            "available_trigger_events": TRIGGER_EVENTS,
            "available_action_types": ACTION_TYPES,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _sub_to_dict(sub: AutomationSubscription) -> Dict[str, Any]:
        return {
            "id": sub.id,
            "name": sub.name,
            "webhook_url": sub.webhook_url,
            "events": sub.events,
            "platform": sub.platform,
            "is_active": sub.is_active,
            "filters": sub.filters,
            "trigger_count": sub.trigger_count,
            "failure_count": sub.failure_count,
            "last_triggered_at": sub.last_triggered_at.isoformat() if sub.last_triggered_at else None,
            "last_error": sub.last_error,
            "created_at": sub.created_at.isoformat(),
        }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_service: Optional[ZapierAutomationService] = None


def get_zapier_service() -> ZapierAutomationService:
    global _service
    if _service is None:
        _service = ZapierAutomationService()
    return _service

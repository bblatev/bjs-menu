"""Integrations API routes."""

from typing import List, Optional
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class Integration(BaseModel):
    id: str
    name: str
    type: str  # accounting, payment, delivery, marketing, pms
    provider: str
    status: str  # connected, disconnected, error
    last_sync: Optional[str] = None
    config: dict = {}


class Webhook(BaseModel):
    id: str
    name: str
    url: str
    events: List[str]
    active: bool
    secret: Optional[str] = None
    last_triggered: Optional[str] = None
    failure_count: int = 0


@router.get("/")
async def get_integrations():
    """Get all integrations."""
    return [
        Integration(id="1", name="QuickBooks", type="accounting", provider="intuit", status="connected", last_sync="2026-02-01T12:00:00Z"),
        Integration(id="2", name="Stripe", type="payment", provider="stripe", status="connected", last_sync="2026-02-01T17:30:00Z"),
        Integration(id="3", name="Glovo", type="delivery", provider="glovo", status="connected", last_sync="2026-02-01T17:00:00Z"),
        Integration(id="4", name="Mailchimp", type="marketing", provider="mailchimp", status="disconnected"),
        Integration(id="5", name="Opera PMS", type="pms", provider="oracle", status="error"),
    ]


@router.get("/{integration_id}")
async def get_integration(integration_id: str):
    """Get a specific integration."""
    return Integration(id=integration_id, name="QuickBooks", type="accounting", provider="intuit", status="connected", last_sync="2026-02-01T12:00:00Z")


@router.post("/{integration_id}/connect")
async def connect_integration(integration_id: str, config: dict):
    """Connect an integration."""
    return {"success": True}


@router.post("/{integration_id}/disconnect")
async def disconnect_integration(integration_id: str):
    """Disconnect an integration."""
    return {"success": True}


@router.post("/{integration_id}/sync")
async def sync_integration(integration_id: str):
    """Trigger a sync for an integration."""
    return {"success": True, "synced_records": 42}


@router.get("/webhooks")
async def get_webhooks():
    """Get all webhooks."""
    return [
        Webhook(id="1", name="Order Webhook", url="https://api.example.com/orders", events=["order.created", "order.completed"], active=True, last_triggered="2026-02-01T17:30:00Z"),
        Webhook(id="2", name="Inventory Webhook", url="https://api.example.com/inventory", events=["stock.low", "stock.received"], active=True, last_triggered="2026-02-01T10:00:00Z"),
        Webhook(id="3", name="Test Webhook", url="https://test.example.com/hook", events=["*"], active=False, failure_count=3),
    ]


@router.post("/webhooks")
async def create_webhook(webhook: Webhook):
    """Create a webhook."""
    return {"success": True, "id": "new-id"}


@router.put("/webhooks/{webhook_id}")
async def update_webhook(webhook_id: str, webhook: Webhook):
    """Update a webhook."""
    return {"success": True}


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: str):
    """Delete a webhook."""
    return {"success": True}


@router.post("/webhooks/{webhook_id}/test")
async def test_webhook(webhook_id: str):
    """Test a webhook."""
    return {"success": True, "response_code": 200}

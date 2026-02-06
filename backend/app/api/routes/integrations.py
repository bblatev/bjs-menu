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
    id: Optional[str] = None
    name: Optional[str] = None
    url: str
    events: List[str] = []
    active: bool = True
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


@router.get("/integrations")
async def list_all_integrations():
    """List all available integrations (alias for frontend compatibility)."""
    return [
        Integration(id="1", name="QuickBooks", type="accounting", provider="intuit", status="connected", last_sync="2026-02-01T12:00:00Z"),
        Integration(id="2", name="Stripe", type="payment", provider="stripe", status="connected", last_sync="2026-02-01T17:30:00Z"),
        Integration(id="3", name="Glovo", type="delivery", provider="glovo", status="connected", last_sync="2026-02-01T17:00:00Z"),
        Integration(id="4", name="Mailchimp", type="marketing", provider="mailchimp", status="disconnected"),
        Integration(id="5", name="Opera PMS", type="pms", provider="oracle", status="error"),
    ]


@router.get("/integrations/categories")
async def get_integration_categories():
    """Get integration categories."""
    return [
        {"id": "accounting", "name": "Accounting", "count": 3, "icon": "calculator"},
        {"id": "payment", "name": "Payment Processing", "count": 4, "icon": "credit-card"},
        {"id": "delivery", "name": "Delivery Platforms", "count": 5, "icon": "truck"},
        {"id": "marketing", "name": "Marketing & CRM", "count": 3, "icon": "megaphone"},
        {"id": "pms", "name": "Hotel PMS", "count": 2, "icon": "building"},
        {"id": "pos", "name": "POS Hardware", "count": 3, "icon": "monitor"},
    ]


@router.get("/integrations/connect")
async def get_connectable_integrations():
    """Get list of integrations that can be connected."""
    return []


@router.get("/hardware/devices")
async def get_hardware_devices():
    """Get hardware devices."""
    return [
        {"id": "1", "name": "Kitchen Printer", "type": "printer", "status": "online", "ip": "192.168.1.100"},
        {"id": "2", "name": "Bar Printer", "type": "printer", "status": "online", "ip": "192.168.1.101"},
        {"id": "3", "name": "Card Terminal 1", "type": "card_reader", "status": "online", "serial": "CT-001"},
        {"id": "4", "name": "KDS Screen", "type": "display", "status": "offline", "ip": "192.168.1.110"},
    ]


@router.get("/api-keys")
async def get_api_keys():
    """Get API keys."""
    return [
        {"id": "1", "name": "POS Integration", "key_prefix": "bjs_live_****", "created_at": "2026-01-15", "last_used": "2026-02-06", "status": "active"},
        {"id": "2", "name": "Mobile App", "key_prefix": "bjs_mob_****", "created_at": "2026-01-20", "last_used": "2026-02-05", "status": "active"},
    ]


@router.get("/accounting/available")
async def get_accounting_integrations_available():
    """Get available accounting integrations."""
    return [
        {"id": "quickbooks", "name": "QuickBooks Online", "provider": "Intuit", "status": "available", "description": "Sync sales, expenses, and inventory with QuickBooks"},
        {"id": "xero", "name": "Xero", "provider": "Xero", "status": "available", "description": "Cloud accounting integration with Xero"},
        {"id": "sage", "name": "Sage", "provider": "Sage", "status": "coming_soon", "description": "Enterprise accounting with Sage"},
        {"id": "atoms3", "name": "AtomS3 Bulgaria", "provider": "AtomS3", "status": "available", "description": "Bulgarian accounting export format"},
    ]


@router.get("/accounting/status")
async def get_accounting_integration_status():
    """Get current accounting integration status."""
    return {
        "connected_provider": None,
        "last_sync": None,
        "sync_enabled": False,
        "auto_sync": False,
        "sync_interval_minutes": 60,
        "accounts_mapped": 0,
        "pending_transactions": 0,
    }


@router.post("/accounting/connect")
async def connect_accounting_integration():
    """Connect an accounting integration."""
    return {"success": True, "status": "connected"}


@router.get("/multi-location/sync-settings")
async def get_multi_location_sync_settings():
    """Get multi-location sync settings."""
    return {
        "auto_sync": True,
        "sync_interval_minutes": 15,
        "sync_menu": True,
        "sync_inventory": True,
        "sync_pricing": True,
        "sync_staff": False,
        "last_sync": "2026-02-06T10:00:00Z",
    }

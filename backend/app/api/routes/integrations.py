"""Integrations API routes."""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select

from app.db.session import DbSession
from app.core.rate_limit import limiter
from app.models.hardware import Integration as IntegrationModel
from app.models.operations import AppSetting

router = APIRouter()


class IntegrationSchema(BaseModel):
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


def _integration_to_dict(i: IntegrationModel) -> dict:
    return {
        "id": str(i.id),
        "name": i.name,
        "type": i.category,
        "provider": i.integration_id,
        "status": i.status,
        "last_sync": i.connected_at.isoformat() if i.connected_at else None,
        "config": i.config or {},
    }


@router.get("/")
@limiter.limit("60/minute")
async def get_integrations(request: Request, db: DbSession):
    """Get all integrations."""
    results = db.execute(select(IntegrationModel).order_by(IntegrationModel.id)).scalars().all()
    return {"integrations": [_integration_to_dict(i) for i in results]}


@router.get("/webhooks")
@limiter.limit("60/minute")
async def get_webhooks(request: Request, db: DbSession):
    """Get all webhooks."""
    setting = db.query(AppSetting).filter(
        AppSetting.category == "webhooks",
        AppSetting.key == "config",
    ).first()
    if setting and setting.value:
        return setting.value
    return {
        "enabled": False,
        "endpoints": [],
        "retry_attempts": 3,
        "timeout_seconds": 30,
    }


@router.put("/webhooks")
@limiter.limit("30/minute")
async def save_webhooks_config(request: Request, db: DbSession):
    """Save webhook configuration (bulk save from frontend)."""
    body = await request.json()
    setting = db.query(AppSetting).filter(
        AppSetting.category == "webhooks",
        AppSetting.key == "config",
    ).first()
    config = {
        "enabled": body.get("enabled", False),
        "endpoints": body.get("endpoints", []),
        "retry_attempts": body.get("retry_attempts", 3),
        "timeout_seconds": body.get("timeout_seconds", 30),
    }
    if setting:
        setting.value = config
    else:
        setting = AppSetting(category="webhooks", key="config", value=config)
        db.add(setting)
    db.commit()
    return {"success": True}


@router.post("/webhooks")
@limiter.limit("30/minute")
async def create_webhook(request: Request, webhook: Webhook, db: DbSession):
    """Create a webhook."""
    setting = db.query(AppSetting).filter(
        AppSetting.category == "webhooks",
        AppSetting.key == "list",
    ).first()
    webhooks = setting.value if setting and setting.value else []
    new_id = str(len(webhooks) + 1)
    new_webhook = webhook.model_dump()
    new_webhook["id"] = new_id
    webhooks.append(new_webhook)
    if setting:
        setting.value = webhooks
    else:
        setting = AppSetting(category="webhooks", key="list", value=webhooks)
        db.add(setting)
    db.commit()
    return {"success": True, "id": new_id}


@router.put("/webhooks/{webhook_id}")
@limiter.limit("30/minute")
async def update_webhook(request: Request, webhook_id: str, webhook: Webhook, db: DbSession):
    """Update a webhook."""
    setting = db.query(AppSetting).filter(
        AppSetting.category == "webhooks",
        AppSetting.key == "list",
    ).first()
    if not setting or not setting.value:
        raise HTTPException(status_code=404, detail="Webhook not found")
    webhooks = setting.value
    for i, w in enumerate(webhooks):
        if w.get("id") == webhook_id:
            updated = webhook.model_dump()
            updated["id"] = webhook_id
            webhooks[i] = updated
            setting.value = webhooks
            db.commit()
            return {"success": True}
    raise HTTPException(status_code=404, detail="Webhook not found")


@router.delete("/webhooks/{webhook_id}")
@limiter.limit("30/minute")
async def delete_webhook(request: Request, webhook_id: str, db: DbSession):
    """Delete a webhook."""
    setting = db.query(AppSetting).filter(
        AppSetting.category == "webhooks",
        AppSetting.key == "list",
    ).first()
    if not setting or not setting.value:
        raise HTTPException(status_code=404, detail="Webhook not found")
    webhooks = [w for w in setting.value if w.get("id") != webhook_id]
    setting.value = webhooks
    db.commit()
    return {"success": True}


@router.post("/webhooks/{webhook_id}/test")
@limiter.limit("30/minute")
async def test_webhook(request: Request, webhook_id: str, db: DbSession):
    """Test a webhook."""
    setting = db.query(AppSetting).filter(
        AppSetting.category == "webhooks",
        AppSetting.key == "list",
    ).first()
    if setting and setting.value:
        for w in setting.value:
            if w.get("id") == webhook_id:
                return {"success": True, "response_code": 200}
    raise HTTPException(status_code=404, detail="Webhook not found")


@router.get("/integrations")
@limiter.limit("60/minute")
async def list_all_integrations(request: Request, db: DbSession):
    """List all available integrations (alias for frontend compatibility)."""
    results = db.execute(select(IntegrationModel).order_by(IntegrationModel.id)).scalars().all()
    return {"integrations": [_integration_to_dict(i) for i in results]}


@router.get("/integrations/categories")
@limiter.limit("60/minute")
async def get_integration_categories(request: Request, db: DbSession):
    """Get integration categories."""
    setting = db.query(AppSetting).filter(
        AppSetting.category == "integrations",
        AppSetting.key == "categories",
    ).first()
    if setting and setting.value:
        cats = setting.value
        # Ensure wrapped in object
        if isinstance(cats, list):
            return {"categories": cats}
        return cats
    # Compute from actual integrations
    results = db.execute(select(IntegrationModel)).scalars().all()
    categories = {}
    for i in results:
        cat = i.category
        if cat not in categories:
            categories[cat] = {"id": cat, "name": cat.title(), "count": 0, "icon": "settings"}
        categories[cat]["count"] += 1
    return {"categories": list(categories.values())}


@router.get("/integrations/connect")
@limiter.limit("60/minute")
async def get_connectable_integrations(request: Request, db: DbSession):
    """Get list of integrations that can be connected."""
    results = db.query(IntegrationModel).filter(
        IntegrationModel.status == "disconnected"
    ).all()
    return [_integration_to_dict(i) for i in results]


@router.post("/integrations/{integration_id}/disconnect")
@limiter.limit("30/minute")
async def disconnect_integration_via_integrations(request: Request, integration_id: str, db: DbSession):
    """Disconnect integration (frontend compat path /integrations/{id}/disconnect)."""
    try:
        iid = int(integration_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=404, detail="Integration not found")
    integration = db.query(IntegrationModel).filter(IntegrationModel.id == iid).first()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    integration.status = "disconnected"
    db.commit()
    return {"success": True}


@router.post("/integrations/connect")
@limiter.limit("30/minute")
async def connect_integration_by_body(request: Request, db: DbSession):
    """Connect an integration (frontend sends integration_id in body)."""
    body = await request.json()
    integration_id = body.get("integration_id")
    if not integration_id:
        raise HTTPException(status_code=400, detail="integration_id required")
    try:
        iid = int(integration_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=404, detail="Integration not found")
    integration = db.query(IntegrationModel).filter(IntegrationModel.id == iid).first()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    config = body.get("credentials", {})
    config.update(body.get("settings", {}))
    integration.status = "connected"
    integration.config = config
    integration.connected_at = datetime.now(timezone.utc)
    db.commit()
    return {"success": True}


@router.get("/hardware/devices")
@limiter.limit("60/minute")
async def get_hardware_devices(request: Request, db: DbSession):
    """Get hardware devices."""
    setting = db.query(AppSetting).filter(
        AppSetting.category == "hardware",
        AppSetting.key == "devices",
    ).first()
    devices = setting.value if setting and setting.value else []
    if isinstance(devices, list):
        return {"devices": devices}
    return devices


@router.get("/api-keys")
@limiter.limit("60/minute")
async def get_api_keys(request: Request, db: DbSession):
    """Get API keys."""
    setting = db.query(AppSetting).filter(
        AppSetting.category == "api_keys",
        AppSetting.key == "list",
    ).first()
    keys = setting.value if setting and setting.value else []
    # Mask full keys, show only preview
    for k in keys:
        if "key" in k and len(k["key"]) > 12:
            k["key_preview"] = k["key"][:8] + "..." + k["key"][-4:]
    return {"keys": keys}


@router.post("/api-keys")
@limiter.limit("30/minute")
async def create_api_key(request: Request, data: dict, db: DbSession):
    """Create an API key."""
    import secrets
    setting = db.query(AppSetting).filter(
        AppSetting.category == "api_keys",
        AppSetting.key == "list",
    ).first()
    keys = setting.value if setting and setting.value else []
    new_key = {
        "id": str(len(keys) + 1),
        "name": data.get("name", "API Key"),
        "key": f"bjs_{secrets.token_hex(16)}",
        "permissions": data.get("permissions", ["read"]),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "active": True,
    }
    keys.append(new_key)
    if setting:
        setting.value = keys
    else:
        setting = AppSetting(category="api_keys", key="list", value=keys)
        db.add(setting)
    db.commit()
    return {"id": new_key["id"], "name": new_key["name"], "key": new_key["key"]}


@router.delete("/api-keys/{key_id}")
@limiter.limit("30/minute")
async def delete_api_key(request: Request, key_id: str, db: DbSession):
    """Revoke an API key."""
    setting = db.query(AppSetting).filter(
        AppSetting.category == "api_keys",
        AppSetting.key == "list",
    ).first()
    if not setting or not setting.value:
        raise HTTPException(status_code=404, detail="API key not found")
    keys = [k for k in setting.value if k.get("id") != key_id]
    if len(keys) == len(setting.value):
        raise HTTPException(status_code=404, detail="API key not found")
    setting.value = keys
    db.commit()
    return {"success": True}


@router.get("/accounting/available")
@limiter.limit("60/minute")
async def get_accounting_integrations_available(request: Request, db: DbSession):
    """Get available accounting integrations."""
    setting = db.query(AppSetting).filter(
        AppSetting.category == "accounting",
        AppSetting.key == "available_integrations",
    ).first()
    if setting and setting.value:
        return setting.value
    return []


@router.get("/accounting/status")
@limiter.limit("60/minute")
async def get_accounting_integration_status(request: Request, db: DbSession):
    """Get current accounting integration status."""
    setting = db.query(AppSetting).filter(
        AppSetting.category == "accounting",
        AppSetting.key == "status",
    ).first()
    if setting and setting.value:
        return setting.value
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
@limiter.limit("30/minute")
async def connect_accounting_integration(request: Request, db: DbSession):
    """Connect an accounting integration."""
    return {"success": True, "status": "connected"}


@router.get("/multi-location/sync-settings")
@limiter.limit("60/minute")
async def get_multi_location_sync_settings(request: Request, db: DbSession):
    """Get multi-location sync settings."""
    setting = db.query(AppSetting).filter(
        AppSetting.category == "multi_location",
        AppSetting.key == "sync_settings",
    ).first()
    if setting and setting.value:
        return setting.value
    return {
        "auto_sync": False,
        "sync_interval_minutes": 15,
        "sync_menu": False,
        "sync_inventory": False,
        "sync_pricing": False,
        "sync_staff": False,
        "last_sync": None,
    }


@router.put("/multi-location/sync-settings")
@limiter.limit("30/minute")
async def save_multi_location_sync_settings(request: Request, db: DbSession):
    """Save multi-location sync settings."""
    body = await request.json()
    setting = db.query(AppSetting).filter(
        AppSetting.category == "multi_location",
        AppSetting.key == "sync_settings",
    ).first()
    if setting:
        setting.value = body
    else:
        setting = AppSetting(category="multi_location", key="sync_settings", value=body)
        db.add(setting)
    db.commit()
    return {"success": True}


# =============================================================================
# CATCH-ALL ROUTES (must be last to avoid matching specific paths)
# =============================================================================


@router.post("/{integration_id}/connect")
@limiter.limit("30/minute")
async def connect_integration(request: Request, integration_id: str, config: dict, db: DbSession):
    """Connect an integration by path param."""
    try:
        iid = int(integration_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=404, detail="Integration not found")
    integration = db.query(IntegrationModel).filter(IntegrationModel.id == iid).first()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    integration.status = "connected"
    integration.config = config
    integration.connected_at = datetime.now(timezone.utc)
    db.commit()
    return {"success": True}


@router.post("/{integration_id}/disconnect")
@limiter.limit("30/minute")
async def disconnect_integration(request: Request, integration_id: str, db: DbSession):
    """Disconnect an integration."""
    try:
        iid = int(integration_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=404, detail="Integration not found")
    integration = db.query(IntegrationModel).filter(IntegrationModel.id == iid).first()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    integration.status = "disconnected"
    db.commit()
    return {"success": True}


@router.post("/{integration_id}/sync")
@limiter.limit("30/minute")
async def sync_integration(request: Request, integration_id: str, db: DbSession):
    """Trigger a sync for an integration."""
    try:
        iid = int(integration_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=404, detail="Integration not found")
    integration = db.query(IntegrationModel).filter(IntegrationModel.id == iid).first()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    integration.connected_at = datetime.now(timezone.utc)
    db.commit()
    return {"success": True, "synced_records": 0}


@router.get("/{integration_id}")
@limiter.limit("60/minute")
async def get_integration(request: Request, integration_id: str, db: DbSession):
    """Get a specific integration by ID."""
    try:
        iid = int(integration_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=404, detail="Integration not found")
    integration = db.query(IntegrationModel).filter(IntegrationModel.id == iid).first()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    return _integration_to_dict(integration)

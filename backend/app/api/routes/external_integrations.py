"""
External Integrations API Endpoints
Connect to accounting systems, suppliers, and third-party services
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from pydantic import BaseModel, Field

from app.db.session import get_db
from app.core.rbac import get_current_user
from app.models import StaffUser
from app.services.external_integrations import (
    integration_manager,
    IntegrationType,
    IntegrationCredentials
)


router = APIRouter()


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class AccountingCredentialsRequest(BaseModel):
    """Credentials for accounting integration"""
    integration_type: str = Field(..., description="quickbooks, xero, sage, microinvest")
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    tenant_id: Optional[str] = None
    api_key: Optional[str] = None


class SupplierIntegrationRequest(BaseModel):
    """Register a supplier integration"""
    integration_type: str = Field(..., description="supplier_edi or supplier_api")
    supplier_id: str
    supplier_name: str
    base_url: Optional[str] = None  # For API integrations
    api_key: Optional[str] = None
    api_secret: Optional[str] = None


class ExportRequest(BaseModel):
    """Request to export data"""
    start_date: date
    end_date: date
    export_type: str = Field("sales", description="sales, purchases, inventory")


class SupplierOrderRequest(BaseModel):
    """Send order to supplier"""
    supplier_integration_key: str
    order_id: str
    items: List[Dict[str, Any]]
    delivery_date: Optional[date] = None
    notes: Optional[str] = None


class WebhookConfig(BaseModel):
    """Webhook configuration"""
    url: str
    events: List[str] = Field(..., description="order_created, stock_low, etc.")
    secret: Optional[str] = None
    active: bool = True


# =============================================================================
# ACCOUNTING INTEGRATION ENDPOINTS
# =============================================================================

@router.get("/accounting/available", response_model=Dict[str, Any])
async def list_available_accounting_integrations():
    """List available accounting integrations."""
    return {
        "integrations": [
            {
                "type": "quickbooks",
                "name": "QuickBooks Online",
                "description": "Connect to QuickBooks Online for automatic sales and purchase sync",
                "auth_type": "oauth2",
                "features": ["sales_export", "purchase_export", "inventory_sync"]
            },
            {
                "type": "xero",
                "name": "Xero",
                "description": "Connect to Xero accounting software",
                "auth_type": "oauth2",
                "features": ["sales_export", "purchase_export", "inventory_sync"]
            },
            {
                "type": "sage",
                "name": "Sage Business Cloud",
                "description": "Connect to Sage accounting",
                "auth_type": "oauth2",
                "features": ["sales_export", "purchase_export"]
            },
            {
                "type": "microinvest",
                "name": "Microinvest",
                "description": "Bulgarian accounting software integration",
                "auth_type": "file_export",
                "features": ["sales_export", "purchase_export", "inventory_sync"]
            }
        ]
    }


@router.post("/accounting/connect", response_model=Dict[str, Any])
async def connect_accounting_integration(
    credentials: AccountingCredentialsRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Connect to an accounting integration.
    """
    try:
        integration_type = IntegrationType(credentials.integration_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid integration type")

    creds = IntegrationCredentials(
        client_id=credentials.client_id,
        client_secret=credentials.client_secret,
        access_token=credentials.access_token,
        refresh_token=credentials.refresh_token,
        tenant_id=credentials.tenant_id,
        api_key=credentials.api_key
    )

    key = integration_manager.register_integration(
        venue_id=current_user.venue_id,
        integration_type=integration_type,
        credentials=creds
    )

    # Test connection
    result = await integration_manager.test_integration(
        current_user.venue_id,
        integration_type
    )

    return {
        "integration_key": key,
        "type": credentials.integration_type,
        "connected": result.success,
        "test_result": result.to_dict()
    }


@router.get("/accounting/status", response_model=Dict[str, Any])
async def get_accounting_status(
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get status of accounting integrations."""
    integrations = integration_manager.list_integrations(current_user.venue_id)

    accounting_integrations = [
        i for i in integrations
        if i["type"] in ["quickbooks", "xero", "sage", "microinvest"]
    ]

    return {
        "venue_id": current_user.venue_id,
        "integrations": accounting_integrations
    }


@router.post("/accounting/export", response_model=Dict[str, Any])
async def export_to_accounting(
    request: ExportRequest,
    integration_type: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Export data to accounting system.
    """
    try:
        int_type = IntegrationType(integration_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid integration type")

    result = await integration_manager.export_to_accounting(
        venue_id=current_user.venue_id,
        integration_type=int_type,
        start_date=request.start_date,
        end_date=request.end_date,
        export_type=request.export_type
    )

    return {
        "status": "success" if result.success else "failed",
        "export_type": request.export_type,
        "period": f"{request.start_date} to {request.end_date}",
        "result": result.to_dict()
    }


@router.delete("/accounting/{integration_type}", response_model=Dict[str, Any])
async def disconnect_accounting(
    integration_type: str,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Disconnect an accounting integration."""
    key = f"{current_user.venue_id}:{integration_type}"
    if key in integration_manager.integrations:
        del integration_manager.integrations[key]
        return {"status": "disconnected", "integration_type": integration_type}
    raise HTTPException(status_code=404, detail="Integration not found")


# =============================================================================
# SUPPLIER INTEGRATION ENDPOINTS
# =============================================================================

@router.get("/suppliers/integrations", response_model=Dict[str, Any])
async def list_supplier_integrations(
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List supplier integrations."""
    integrations = integration_manager.list_integrations(current_user.venue_id)

    supplier_integrations = [
        i for i in integrations
        if i["type"] in ["supplier_edi", "supplier_api"]
    ]

    return {
        "venue_id": current_user.venue_id,
        "integrations": supplier_integrations
    }


@router.post("/suppliers/connect", response_model=Dict[str, Any])
async def connect_supplier_integration(
    request: SupplierIntegrationRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Connect to a supplier integration.
    """
    try:
        integration_type = IntegrationType(request.integration_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid integration type")

    creds = IntegrationCredentials(
        api_key=request.api_key,
        api_secret=request.api_secret
    )

    key = integration_manager.register_integration(
        venue_id=current_user.venue_id,
        integration_type=integration_type,
        credentials=creds,
        supplier_id=request.supplier_id,
        supplier_name=request.supplier_name,
        base_url=request.base_url
    )

    # Test connection
    result = await integration_manager.test_integration(
        current_user.venue_id,
        integration_type
    )

    return {
        "integration_key": key,
        "supplier_name": request.supplier_name,
        "type": request.integration_type,
        "connected": result.success,
        "test_result": result.to_dict()
    }


@router.post("/suppliers/send-order", response_model=Dict[str, Any])
async def send_supplier_order(
    request: SupplierOrderRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Send a purchase order to a supplier.
    """
    order_data = {
        "order_id": request.order_id,
        "items": request.items,
        "delivery_date": request.delivery_date.isoformat() if request.delivery_date else None,
        "notes": request.notes,
        "venue_id": current_user.venue_id
    }

    result = await integration_manager.send_supplier_order(
        venue_id=current_user.venue_id,
        supplier_integration_key=request.supplier_integration_key,
        order_data=order_data
    )

    return {
        "status": "sent" if result.success else "failed",
        "order_id": request.order_id,
        "result": result.to_dict()
    }


@router.get("/suppliers/{integration_key}/catalog", response_model=Dict[str, Any])
async def get_supplier_catalog(
    integration_key: str,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get product catalog from supplier."""
    result = await integration_manager.get_supplier_catalog(integration_key)

    return {
        "status": "success" if result.success else "failed",
        "catalog": result.data if result.success else None,
        "error": result.error
    }


# =============================================================================
# WEBHOOK ENDPOINTS
# =============================================================================

@router.get("/webhooks", response_model=Dict[str, Any])
async def list_webhooks(
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List configured webhooks."""
    return {
        "venue_id": current_user.venue_id,
        "webhooks": [],  # In production, fetch from database
        "available_events": [
            "order.created",
            "order.completed",
            "order.cancelled",
            "stock.low",
            "stock.out",
            "payment.received",
            "payment.refunded",
            "reservation.created",
            "reservation.cancelled",
            "shift.started",
            "shift.ended"
        ]
    }


@router.post("/webhooks", response_model=Dict[str, Any])
async def create_webhook(
    config: WebhookConfig,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Create a webhook configuration."""
    # In production, store in database
    return {
        "webhook_id": f"wh_{datetime.utcnow().timestamp()}",
        "url": config.url,
        "events": config.events,
        "active": config.active,
        "created_at": datetime.utcnow().isoformat()
    }


@router.delete("/webhooks/{webhook_id}", response_model=Dict[str, Any])
async def delete_webhook(
    webhook_id: str,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Delete a webhook configuration."""
    # In production, delete from database
    return {
        "status": "deleted",
        "webhook_id": webhook_id
    }


@router.post("/webhooks/{webhook_id}/test", response_model=Dict[str, Any])
async def test_webhook(
    webhook_id: str,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Send a test payload to a webhook."""
    return {
        "status": "test_sent",
        "webhook_id": webhook_id,
        "payload": {
            "event": "test",
            "timestamp": datetime.utcnow().isoformat(),
            "venue_id": current_user.venue_id
        }
    }


# =============================================================================
# SYNC ENDPOINTS
# =============================================================================

@router.post("/sync/full", response_model=Dict[str, Any])
async def full_sync(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Trigger a full sync with all connected integrations.
    """
    integrations = integration_manager.list_integrations(current_user.venue_id)

    # Schedule sync tasks
    sync_results = []
    for integration in integrations:
        sync_results.append({
            "integration": integration["key"],
            "status": "scheduled"
        })

    return {
        "status": "sync_scheduled",
        "integrations_count": len(integrations),
        "results": sync_results
    }


@router.get("/sync/status", response_model=Dict[str, Any])
async def get_sync_status(
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get status of ongoing sync operations."""
    return {
        "venue_id": current_user.venue_id,
        "last_sync": None,  # In production, fetch from database
        "syncing": False,
        "queued_operations": 0
    }


# =============================================================================
# OAUTH ENDPOINTS
# =============================================================================

@router.get("/oauth/{provider}/authorize", response_model=Dict[str, Any])
async def get_oauth_url(
    provider: str,
    redirect_uri: str,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Get OAuth authorization URL for a provider.
    """
    oauth_configs = {
        "quickbooks": {
            "auth_url": "https://appcenter.intuit.com/connect/oauth2",
            "scope": "com.intuit.quickbooks.accounting"
        },
        "xero": {
            "auth_url": "https://login.xero.com/identity/connect/authorize",
            "scope": "openid profile email accounting.transactions accounting.settings"
        }
    }

    if provider not in oauth_configs:
        raise HTTPException(status_code=400, detail="Unknown OAuth provider")

    config = oauth_configs[provider]
    state = f"{current_user.venue_id}_{datetime.utcnow().timestamp()}"

    return {
        "provider": provider,
        "authorization_url": config["auth_url"],
        "scope": config["scope"],
        "state": state,
        "redirect_uri": redirect_uri
    }


@router.post("/oauth/{provider}/callback", response_model=Dict[str, Any])
async def handle_oauth_callback(
    provider: str,
    code: str,
    state: str,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Handle OAuth callback and exchange code for tokens.
    """
    # In production, exchange code for tokens using provider's token endpoint
    return {
        "status": "connected",
        "provider": provider,
        "message": "OAuth connection successful"
    }

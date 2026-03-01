"""Mobile sync, push notifications & developer portal"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from app.core.rate_limit import limiter
from app.db.session import get_db

# Import shared schemas and helpers
from app.api.routes.gap_features._shared import *

router = APIRouter()

@router.get("/")
@limiter.limit("60/minute")
async def get_gap_features_root(request: Request, db: Session = Depends(get_db)):
    """Gap features overview."""
    return {"module": "gap-features", "status": "active", "features": ["mobile-sync", "push-notifications", "developer-api", "marketplace"], "endpoints": ["/mobile/sync", "/push/notifications", "/marketplace/apps"]}


@router.get("/mobile/sync")
@limiter.limit("60/minute")
async def get_sync_package(
    request: Request,
    device_id: str = Query("", description="Device ID"),
    last_sync: Optional[datetime] = Query(None, description="Last sync timestamp"),
    include_menu: bool = True,
    include_tables: bool = True,
    include_staff: bool = True,
    include_inventory: bool = False,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
    venue_id: int = Depends(get_current_venue)
):
    """Get sync package for offline operation."""
    from app.services.mobile_offline_service import MobileOfflineService

    service = MobileOfflineService(db)
    return await service.get_sync_package(
        venue_id=venue_id,
        device_id=device_id,
        last_sync=last_sync,
        include_menu=include_menu,
        include_tables=include_tables,
        include_staff=include_staff,
        include_inventory=include_inventory
    )


@router.post("/mobile/sync/transactions")
@limiter.limit("30/minute")
async def process_offline_transactions(
    request: Request,
    body: OfflineTransactionRequest,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
    venue_id: int = Depends(get_current_venue)
):
    """Process transactions created while offline."""
    from app.services.mobile_offline_service import MobileOfflineService

    service = MobileOfflineService(db)
    return await service.process_offline_transactions(
        venue_id=venue_id,
        device_id=body.device_id,
        transactions=body.transactions
    )


@router.post("/push/register")
@limiter.limit("30/minute")
async def register_push_token(
    request: Request,
    body: PushTokenRequest,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
    venue_id: int = Depends(get_current_venue)
):
    """Register a push notification token."""
    from app.services.mobile_offline_service import PushNotificationService

    service = PushNotificationService(db)
    token = await service.register_token(
        user_id=current_user.id,
        user_type="staff",
        venue_id=venue_id,
        token=body.token,
        platform=body.platform,
        device_info=body.device_info
    )
    return {"status": "registered", "token_id": str(token.id)}


@router.delete("/push/unregister")
@limiter.limit("30/minute")
async def unregister_push_token(
    request: Request,
    token: str,
    db: Session = Depends(get_db)
):
    """Unregister a push notification token."""
    from app.services.mobile_offline_service import PushNotificationService

    service = PushNotificationService(db)
    success = await service.unregister_token(token)
    return {"status": "unregistered" if success else "not_found"}


@router.post("/push/send")
@limiter.limit("30/minute")
async def send_push_notification(
    request: Request,
    user_id: str,
    body: NotificationRequest,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user)
):
    """Send a push notification to a user."""
    from app.services.mobile_offline_service import PushNotificationService

    service = PushNotificationService(db)
    notification = await service.send_notification(
        user_id=user_id,
        title=body.title,
        body=body.body,
        data=body.data,
        channel=body.channel
    )
    return {"status": notification.status, "notification_id": str(notification.id)}


@router.get("/push/notifications")
@limiter.limit("60/minute")
async def get_notifications(
    request: Request,
    limit: int = 50,
    include_read: bool = False,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user)
):
    """Get notifications for the current user."""
    from app.services.mobile_offline_service import PushNotificationService

    service = PushNotificationService(db)
    notifications = await service.get_user_notifications(
        user_id=current_user.id,
        limit=limit,
        include_read=include_read
    )
    return {"notifications": notifications}


# ==================== DEVELOPER PORTAL ENDPOINTS ====================

@router.post("/developers/register")
@limiter.limit("30/minute")
async def register_developer(
    request: Request,
    body: DeveloperRegistrationRequest,
    db: Session = Depends(get_db)
):
    """Register as a developer."""
    from app.services.developer_portal_service import DeveloperPortalService

    service = DeveloperPortalService(db)
    developer = await service.register_developer(
        email=body.email,
        company_name=body.company_name,
        contact_name=body.contact_name,
        website=body.website,
        use_case=body.use_case
    )
    return {
        "developer_id": str(developer.id),
        "email": developer.email,
        "tier": developer.tier,
        "status": "pending_verification"
    }


@router.post("/developers/{developer_id}/api-keys")
@limiter.limit("30/minute")
async def create_api_key(
    request: Request,
    developer_id: str,
    body: APIKeyRequest,
    db: Session = Depends(get_db)
):
    """Create a new API key."""
    from app.services.developer_portal_service import DeveloperPortalService

    service = DeveloperPortalService(db)
    api_key, raw_key = await service.create_api_key(
        developer_id=developer_id,
        name=body.name,
        scopes=body.scopes,
        expires_in_days=body.expires_in_days
    )
    return {
        "api_key_id": str(api_key.id),
        "name": api_key.name,
        "key": raw_key,  # Only shown once
        "scopes": api_key.scopes,
        "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
        "warning": "Save this key securely. It will not be shown again."
    }


@router.get("/developers/{developer_id}/api-keys")
@limiter.limit("60/minute")
async def list_api_keys(
    request: Request,
    developer_id: str,
    db: Session = Depends(get_db)
):
    """List all API keys for a developer."""
    from app.services.developer_portal_service import DeveloperPortalService

    service = DeveloperPortalService(db)
    keys = await service.list_api_keys(developer_id)
    return {
        "api_keys": [
            {
                "id": str(k.id),
                "name": k.name,
                "key_prefix": k.key_prefix,
                "scopes": k.scopes,
                "is_active": k.is_active,
                "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
                "expires_at": k.expires_at.isoformat() if k.expires_at else None
            }
            for k in keys
        ]
    }


@router.delete("/developers/{developer_id}/api-keys/{api_key_id}")
@limiter.limit("30/minute")
async def revoke_api_key(
    request: Request,
    developer_id: str,
    api_key_id: str,
    db: Session = Depends(get_db)
):
    """Revoke an API key."""
    from app.services.developer_portal_service import DeveloperPortalService

    service = DeveloperPortalService(db)
    success = await service.revoke_api_key(api_key_id, developer_id)
    return {"status": "revoked" if success else "not_found"}


@router.get("/developers/{developer_id}/usage")
@limiter.limit("60/minute")
async def get_api_usage(
    request: Request,
    developer_id: str,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get API usage statistics."""
    from app.services.developer_portal_service import DeveloperPortalService

    service = DeveloperPortalService(db)
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    stats = await service.get_api_usage_stats(developer_id, start_date, end_date)
    return stats


# ==================== MARKETPLACE ENDPOINTS ====================

@router.post("/marketplace/apps")
@limiter.limit("30/minute")
async def submit_app(
    request: Request,
    body: AppSubmissionRequest,
    developer_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """Submit a new app to the marketplace."""
    from app.services.developer_portal_service import MarketplaceService

    service = MarketplaceService(db)
    app = await service.submit_app(
        developer_id=developer_id,
        **body.model_dump()
    )
    return {
        "app_id": str(app.id),
        "slug": app.slug,
        "status": app.status.value
    }


@router.get("/marketplace/apps")
@limiter.limit("60/minute")
async def list_marketplace_apps(
    request: Request,
    category: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "popular",
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """List apps in the marketplace."""
    from app.services.developer_portal_service import MarketplaceService

    service = MarketplaceService(db)
    apps, total = await service.list_apps(
        category=category,
        search=search,
        sort_by=sort_by,
        limit=limit,
        offset=offset
    )
    return {
        "apps": [
            {
                "id": str(a.id),
                "name": a.name,
                "slug": a.slug,
                "short_description": a.short_description,
                "category": a.category,
                "icon_url": a.icon_url,
                "pricing_type": a.pricing_type.value,
                "price_monthly": a.price_monthly,
                "avg_rating": a.avg_rating,
                "install_count": a.install_count
            }
            for a in apps
        ],
        "total": total
    }


@router.get("/marketplace/apps/{app_slug}")
@limiter.limit("60/minute")
async def get_marketplace_app(
    request: Request,
    app_slug: str,
    db: Session = Depends(get_db)
):
    """Get app details by slug."""
    from app.services.developer_portal_service import MarketplaceService

    service = MarketplaceService(db)
    app = await service.get_app_by_slug(app_slug)
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    return app


@router.post("/marketplace/apps/{app_id}/install")
@limiter.limit("30/minute")
async def install_app(
    request: Request,
    app_id: str,
    granted_scopes: List[str] = Body(...),
    billing_cycle: str = "monthly",
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
    venue_id: int = Depends(get_current_venue)
):
    """Install an app."""
    from app.services.developer_portal_service import MarketplaceService

    service = MarketplaceService(db)
    installation = await service.install_app(
        app_id=app_id,
        venue_id=venue_id,
        installed_by=current_user.id,
        granted_scopes=granted_scopes,
        billing_cycle=billing_cycle
    )
    return {
        "installation_id": str(installation.id),
        "status": "installed"
    }


@router.delete("/marketplace/apps/{app_id}/install")
@limiter.limit("30/minute")
async def uninstall_app(
    request: Request,
    app_id: str,
    db: Session = Depends(get_db),
    venue_id: int = Depends(get_current_venue)
):
    """Uninstall an app."""
    from app.services.developer_portal_service import MarketplaceService

    service = MarketplaceService(db)
    success = await service.uninstall_app(app_id, venue_id)
    return {"status": "uninstalled" if success else "not_found"}


@router.get("/marketplace/installed")
@limiter.limit("60/minute")
async def get_installed_apps(
    request: Request,
    db: Session = Depends(get_db),
    venue_id: int = Depends(get_current_venue)
):
    """Get installed apps for the venue."""
    from app.services.developer_portal_service import MarketplaceService

    service = MarketplaceService(db)
    installations = await service.get_installed_apps(venue_id)
    return {
        "apps": [
            {
                "installation_id": str(inst.id),
                "app_id": str(app.id),
                "app_name": app.name,
                "app_slug": app.slug,
                "installed_at": inst.installed_at.isoformat()
            }
            for inst, app in installations
        ]
    }



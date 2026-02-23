"""
Mobile Native App API Routes
Mobile-optimized endpoints for the BJS Menu mobile app.
"""
from fastapi import APIRouter, Query, Request
from app.db.session import DbSession
from app.core.rate_limit import limiter
from datetime import datetime, timezone

router = APIRouter()


@router.post("/auth/login")
@limiter.limit("10/minute")
def mobile_login(request: Request, db: DbSession, data: dict = {}):
    """Mobile login with longer-lived token."""
    return {
        "status": "success",
        "message": "Use /api/v1/auth/login for authentication",
        "token_lifetime": "30d",
    }


@router.post("/auth/device-register")
@limiter.limit("10/minute")
def register_device(request: Request, db: DbSession, data: dict = {}):
    """Register mobile device for push notifications."""
    return {
        "device_id": data.get("device_id"),
        "platform": data.get("platform", "ios"),
        "push_token": data.get("push_token"),
        "registered": True,
        "registered_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/dashboard")
@limiter.limit("60/minute")
def mobile_dashboard(request: Request, db: DbSession, venue_id: int = Query(1)):
    """Compact dashboard data for mobile display."""
    return {
        "venue_id": venue_id,
        "today": {
            "revenue": 0,
            "orders": 0,
            "avg_ticket": 0,
            "labor_pct": 0,
            "food_cost_pct": 0,
        },
        "active_orders": 0,
        "pending_reservations": 0,
        "low_stock_alerts": 0,
        "staff_on_shift": 0,
    }


@router.get("/orders/active")
@limiter.limit("60/minute")
def mobile_active_orders(request: Request, db: DbSession, venue_id: int = Query(1)):
    """Active orders for mobile view."""
    return {"orders": [], "total": 0}


@router.post("/orders/{order_id}/status")
@limiter.limit("30/minute")
def update_order_status_mobile(
    request: Request, db: DbSession,
    order_id: int, data: dict = {}
):
    """Update order status from mobile."""
    return {
        "order_id": order_id,
        "new_status": data.get("status", "in_progress"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/notifications")
@limiter.limit("60/minute")
def get_mobile_notifications(request: Request, db: DbSession, venue_id: int = Query(1)):
    """Get push notification history."""
    return {"notifications": [], "unread": 0}


@router.get("/sync")
@limiter.limit("30/minute")
def sync_data(request: Request, db: DbSession, venue_id: int = Query(1), since: str = None):
    """Sync endpoint for offline-first mobile data."""
    return {
        "venue_id": venue_id,
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "menu_items": [],
        "categories": [],
        "tables": [],
        "staff": [],
    }


@router.post("/inventory/quick-count")
@limiter.limit("30/minute")
def mobile_quick_count(request: Request, db: DbSession, data: dict = {}):
    """Quick inventory count from mobile device."""
    items = data.get("items", [])
    return {
        "items_counted": len(items),
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "status": "submitted",
    }

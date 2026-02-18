"""Auto-86 API routes.

Endpoints for the automatic 86 system that marks menu items as
unavailable when stock runs out and restores them when replenished.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from app.core.rbac import CurrentUser, RequireManager
from app.core.rate_limit import limiter
from app.db.session import DbSession
from app.services.auto_86_service import Auto86Service

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class Auto86CheckRequest(BaseModel):
    """Trigger an 86-check after a stock change."""
    product_id: int = Field(..., description="Product whose stock changed")
    location_id: int = Field(..., description="Location where the change occurred")


class Manual86Request(BaseModel):
    """Manually 86 a menu item."""
    menu_item_id: int = Field(..., description="Menu item to 86")
    location_id: int = Field(..., description="Location to 86 at")
    reason: str = Field(
        default="Manager override",
        max_length=500,
        description="Reason for manually 86'ing the item",
    )


class ManualUn86Request(BaseModel):
    """Manually restore (un-86) a menu item."""
    menu_item_id: int = Field(..., description="Menu item to restore")
    location_id: int = Field(..., description="Location to restore at")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/status/{location_id}")
@limiter.limit("60/minute")
def get_86d_items(
    request: Request,
    location_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Get all currently 86'd menu items for a location.

    Returns a list of menu items that are currently marked as unavailable,
    along with the reason and timestamp of the 86 event.
    """
    svc = Auto86Service(db)
    items = svc.get_86d_items(location_id)
    return {
        "location_id": location_id,
        "count": len(items),
        "items": items,
    }


@router.post("/check")
@limiter.limit("120/minute")
def trigger_86_check(
    request: Request,
    body: Auto86CheckRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    """Trigger an 86 check after a stock change for a product/location.

    Call this after recording a stock movement (sale, waste, adjustment,
    purchase, transfer).  The service will check all recipes that use this
    product and 86 or un-86 linked menu items as needed.
    """
    svc = Auto86Service(db)
    result = svc.check_and_update_86_status(
        product_id=body.product_id,
        location_id=body.location_id,
        user_id=current_user.user_id,
    )
    return result


@router.post("/manual")
@limiter.limit("30/minute")
def manual_86(
    request: Request,
    body: Manual86Request,
    db: DbSession,
    current_user: RequireManager,
):
    """Manually 86 a menu item (manager or owner only).

    Use this for situations where the auto system wouldn't catch the issue,
    such as equipment failure, quality problems, or health concerns.
    """
    svc = Auto86Service(db)
    try:
        result = svc.manual_86(
            menu_item_id=body.menu_item_id,
            location_id=body.location_id,
            reason=body.reason,
            user_id=current_user.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return result


@router.post("/restore")
@limiter.limit("30/minute")
def manual_un86(
    request: Request,
    body: ManualUn86Request,
    db: DbSession,
    current_user: RequireManager,
):
    """Manually restore (un-86) a menu item (manager or owner only).

    Restores the item to available status and records an event in the
    86 history.
    """
    svc = Auto86Service(db)
    try:
        result = svc.manual_un86(
            menu_item_id=body.menu_item_id,
            location_id=body.location_id,
            user_id=current_user.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return result


@router.get("/history/{location_id}")
@limiter.limit("60/minute")
def get_86_history(
    request: Request,
    location_id: int,
    db: DbSession,
    current_user: CurrentUser,
    days: int = Query(default=7, ge=1, le=90, description="Number of days to look back"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """Get 86/un-86 event history for a location with pagination.

    Returns a paginated list of all 86 and un-86 events, including
    automatic and manual events.
    """
    svc = Auto86Service(db)
    return svc.get_86_history(
        location_id=location_id,
        days=days,
        limit=limit,
        offset=offset,
    )


@router.get("/dashboard/{location_id}")
@limiter.limit("30/minute")
def get_86_dashboard(
    request: Request,
    location_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Full 86 dashboard for a location.

    Includes:
    - Currently 86'd items
    - At-risk items (running low, < 3 servings remaining)
    - Recent events (last 24 hours)
    - Today's statistics
    """
    svc = Auto86Service(db)
    return svc.get_dashboard(location_id)

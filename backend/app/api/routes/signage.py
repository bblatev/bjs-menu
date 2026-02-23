"""
Digital Signage API Routes
Manage digital display content and scheduling.
"""
from fastapi import APIRouter, Query, Request
from app.db.session import DbSession
from app.core.rate_limit import limiter
from datetime import datetime, timezone

router = APIRouter()


@router.get("/displays")
@limiter.limit("60/minute")
def get_displays(request: Request, db: DbSession, venue_id: int = Query(1)):
    """List configured digital displays."""
    return {"displays": [], "total": 0}


@router.post("/displays")
@limiter.limit("30/minute")
def register_display(request: Request, db: DbSession, data: dict = {}):
    """Register a new digital display."""
    return {
        "id": 1,
        "name": data.get("name", "Display 1"),
        "location": data.get("location", ""),
        "resolution": data.get("resolution", "1920x1080"),
        "status": "active",
        "registered_at": datetime.now(timezone.utc).isoformat(),
    }


@router.put("/displays/{display_id}/content")
@limiter.limit("30/minute")
def update_display_content(request: Request, db: DbSession, display_id: int, data: dict = {}):
    """Update content shown on a display."""
    return {
        "display_id": display_id,
        "content_type": data.get("content_type", "menu"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/templates")
@limiter.limit("60/minute")
def get_display_templates(request: Request, db: DbSession):
    """Get available display templates."""
    return {
        "templates": [
            {"id": 1, "name": "Menu Board", "type": "menu", "description": "Full menu display"},
            {"id": 2, "name": "Daily Specials", "type": "specials", "description": "Today's specials highlight"},
            {"id": 3, "name": "Wait Time", "type": "wait_time", "description": "Current wait time display"},
            {"id": 4, "name": "Welcome", "type": "welcome", "description": "Welcome screen with branding"},
        ]
    }


@router.post("/displays/{display_id}/schedule")
@limiter.limit("30/minute")
def schedule_content(request: Request, db: DbSession, display_id: int, data: dict = {}):
    """Schedule content rotation for a display."""
    return {
        "display_id": display_id,
        "schedule": data.get("schedule", []),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

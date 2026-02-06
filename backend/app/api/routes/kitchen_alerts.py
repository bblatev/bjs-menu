"""Kitchen alerts routes."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def get_kitchen_alerts():
    """Get kitchen alerts."""
    return []


@router.get("/stats")
async def get_kitchen_alert_stats():
    """Get kitchen alert statistics."""
    return {"total_alerts": 0, "critical": 0, "warnings": 0, "resolved_today": 0}

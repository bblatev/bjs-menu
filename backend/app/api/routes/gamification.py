"""Gamification routes - badges, challenges, leaderboard."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/badges")
async def get_badges():
    """Get all badges."""
    return [
        {"id": "1", "name": "First Order", "description": "Complete your first order", "icon": "star", "points": 10, "active": True, "earned_count": 245},
        {"id": "2", "name": "Speed Demon", "description": "Complete 10 orders under 5 min avg", "icon": "lightning", "points": 50, "active": True, "earned_count": 12},
        {"id": "3", "name": "Perfect Week", "description": "No errors for 7 consecutive days", "icon": "trophy", "points": 100, "active": True, "earned_count": 5},
        {"id": "4", "name": "Upsell King", "description": "Achieve 30% upsell rate", "icon": "crown", "points": 75, "active": True, "earned_count": 8},
    ]


@router.post("/badges")
async def create_badge(data: dict):
    """Create a badge."""
    return {"success": True, "id": "new-id"}


@router.put("/badges/{badge_id}")
async def update_badge(badge_id: str, data: dict):
    """Update a badge."""
    return {"success": True}


@router.post("/badges/{badge_id}/toggle-active")
async def toggle_badge(badge_id: str):
    """Toggle badge active status."""
    return {"success": True}


@router.get("/challenges")
async def get_challenges():
    """Get active challenges."""
    return [
        {"id": "1", "name": "February Sales Sprint", "description": "Highest sales this month wins", "type": "sales", "start_date": "2026-02-01", "end_date": "2026-02-28", "reward": "50 BGN bonus", "participants": 8, "status": "active"},
        {"id": "2", "name": "Zero Waste Week", "description": "Minimize food waste", "type": "waste_reduction", "start_date": "2026-02-03", "end_date": "2026-02-09", "reward": "Day off", "participants": 12, "status": "active"},
    ]


@router.post("/challenges")
async def create_challenge(data: dict):
    """Create a challenge."""
    return {"success": True, "id": "new-id"}


@router.post("/challenges/{challenge_id}/toggle-active")
async def toggle_challenge(challenge_id: str):
    """Toggle challenge active status."""
    return {"success": True}


@router.get("/leaderboard")
async def get_leaderboard():
    """Get staff leaderboard."""
    return [
        {"rank": 1, "staff_id": "1", "name": "Sarah Johnson", "points": 450, "badges": 5, "streak": 12},
        {"rank": 2, "staff_id": "2", "name": "John Smith", "points": 380, "badges": 4, "streak": 8},
        {"rank": 3, "staff_id": "3", "name": "Mike Davis", "points": 320, "badges": 3, "streak": 5},
    ]


@router.get("/achievements/recent")
async def get_recent_achievements():
    """Get recent achievements."""
    return [
        {"id": "1", "staff_name": "Sarah Johnson", "badge": "Speed Demon", "earned_at": "2026-02-05T14:30:00Z"},
        {"id": "2", "staff_name": "John Smith", "badge": "Upsell King", "earned_at": "2026-02-04T18:00:00Z"},
    ]

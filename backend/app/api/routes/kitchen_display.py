"""Kitchen Display System display routes."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/stations")
async def get_display_stations():
    """Get KDS display stations."""
    return [
        {"id": "grill", "name": "Grill", "active": True, "pending_tickets": 3, "avg_time": 12},
        {"id": "fry", "name": "Fry", "active": True, "pending_tickets": 5, "avg_time": 8},
        {"id": "salad", "name": "Salad/Cold", "active": True, "pending_tickets": 2, "avg_time": 5},
        {"id": "dessert", "name": "Dessert", "active": False, "pending_tickets": 0, "avg_time": 0},
        {"id": "expo", "name": "Expo", "active": True, "pending_tickets": 4, "avg_time": 3},
    ]


@router.get("/tickets")
async def get_display_tickets():
    """Get KDS display tickets."""
    return []

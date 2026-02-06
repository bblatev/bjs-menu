"""Promotions routes."""

from typing import Optional
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def get_promotions():
    """Get active promotions."""
    return [
        {"id": "1", "name": "Happy Hour", "type": "discount", "value": 20, "status": "active", "start_date": "2026-01-01", "end_date": None, "applies_to": "drinks"},
        {"id": "2", "name": "Lunch Special", "type": "combo", "value": 15.99, "status": "active", "start_date": "2026-01-15", "end_date": None, "applies_to": "lunch_menu"},
        {"id": "3", "name": "Weekend Brunch", "type": "fixed_price", "value": 24.99, "status": "scheduled", "start_date": "2026-02-08", "end_date": "2026-02-09", "applies_to": "brunch_menu"},
    ]


@router.get("/{promotion_id}")
async def get_promotion(promotion_id: str):
    """Get a specific promotion."""
    return {"id": promotion_id, "name": "Happy Hour", "type": "discount", "value": 20, "status": "active"}


@router.post("/")
async def create_promotion(data: dict):
    """Create a promotion."""
    return {"success": True, "id": "new-id"}


@router.put("/{promotion_id}")
async def update_promotion(promotion_id: str, data: dict):
    """Update a promotion."""
    return {"success": True}


@router.delete("/{promotion_id}")
async def delete_promotion(promotion_id: str):
    """Delete a promotion."""
    return {"success": True}

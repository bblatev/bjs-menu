"""Roles management API routes."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def get_roles():
    """Get all user roles."""
    return {
        "roles": [
            {"id": "1", "name": "admin", "description": "Full system access"},
            {"id": "2", "name": "manager", "description": "Management access with reporting"},
            {"id": "3", "name": "cashier", "description": "POS and order management"},
            {"id": "4", "name": "waiter", "description": "Order taking and table management"},
            {"id": "5", "name": "bartender", "description": "Bar and drink management"},
            {"id": "6", "name": "chef", "description": "Kitchen display and prep"},
            {"id": "7", "name": "host", "description": "Reservations and seating"},
            {"id": "8", "name": "inventory", "description": "Stock and inventory management"},
        ]
    }

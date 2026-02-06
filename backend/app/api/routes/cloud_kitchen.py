"""Cloud kitchen, delivery, and drive-thru v6 routes."""

from fastapi import APIRouter

router = APIRouter()


# Cloud Kitchen
@router.get("/{venue_id}/cloud-kitchen/brands")
async def get_cloud_kitchen_brands(venue_id: str):
    """Get virtual brands for cloud kitchen."""
    return [
        {"id": "1", "name": "BJ's Wings", "status": "active", "platforms": ["glovo", "foodpanda"], "orders_today": 12, "revenue_today": 240.00},
        {"id": "2", "name": "Sofia Burgers", "status": "active", "platforms": ["glovo"], "orders_today": 8, "revenue_today": 180.00},
    ]


@router.get("/{venue_id}/cloud-kitchen/stations")
async def get_cloud_kitchen_stations(venue_id: str):
    """Get cloud kitchen stations."""
    return [
        {"id": "1", "name": "Wings Station", "brand": "BJ's Wings", "status": "active", "current_orders": 3},
        {"id": "2", "name": "Burger Station", "brand": "Sofia Burgers", "status": "active", "current_orders": 2},
    ]


# Delivery
@router.get("/{venue_id}/delivery/platforms")
async def get_delivery_platforms(venue_id: str):
    """Get delivery platform integrations."""
    return [
        {"id": "1", "name": "Glovo", "status": "connected", "orders_today": 15, "commission_pct": 25},
        {"id": "2", "name": "Foodpanda", "status": "connected", "orders_today": 8, "commission_pct": 30},
        {"id": "3", "name": "Wolt", "status": "disconnected", "orders_today": 0, "commission_pct": 0},
    ]


@router.get("/{venue_id}/delivery/orders")
async def get_delivery_orders(venue_id: str):
    """Get delivery orders."""
    return []


@router.get("/{venue_id}/delivery/zones")
async def get_delivery_zones(venue_id: str):
    """Get delivery zones."""
    return [
        {"id": "1", "name": "Zone 1 - City Center", "radius_km": 3, "delivery_fee": 2.99, "min_order": 15.00, "estimated_time": "25-35 min"},
        {"id": "2", "name": "Zone 2 - Extended", "radius_km": 7, "delivery_fee": 4.99, "min_order": 25.00, "estimated_time": "35-50 min"},
    ]


@router.get("/{venue_id}/delivery/drivers")
async def get_delivery_drivers(venue_id: str):
    """Get delivery drivers."""
    return []


# Drive-Thru
@router.get("/{venue_id}/drive-thru/lanes")
async def get_drive_thru_lanes(venue_id: str):
    """Get drive-thru lanes."""
    return [
        {"id": "1", "name": "Lane 1", "status": "active", "current_vehicle": None, "avg_service_time": 180},
        {"id": "2", "name": "Lane 2", "status": "inactive", "current_vehicle": None, "avg_service_time": 0},
    ]


@router.get("/{venue_id}/drive-thru/vehicles")
async def get_drive_thru_vehicles(venue_id: str):
    """Get vehicles in drive-thru queue."""
    return []

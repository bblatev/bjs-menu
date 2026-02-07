"""Cloud kitchen, delivery, and drive-thru v6 routes."""

from fastapi import APIRouter

from app.db.session import DbSession
from app.models.operations import AppSetting

router = APIRouter()


def _get_setting_list(db: DbSession, category: str, key: str = "default") -> list:
    """Return a list stored in AppSetting, or [] if not found."""
    row = db.query(AppSetting).filter(
        AppSetting.category == category,
        AppSetting.key == key,
    ).first()
    if row and isinstance(row.value, list):
        return row.value
    return []


# Cloud Kitchen
@router.get("/{venue_id}/cloud-kitchen/brands")
async def get_cloud_kitchen_brands(venue_id: str, db: DbSession):
    """Get virtual brands for cloud kitchen."""
    return _get_setting_list(db, "cloud_kitchen_brands", venue_id)


@router.get("/{venue_id}/cloud-kitchen/stations")
async def get_cloud_kitchen_stations(venue_id: str, db: DbSession):
    """Get cloud kitchen stations."""
    return _get_setting_list(db, "cloud_kitchen_stations", venue_id)


# Delivery
@router.get("/{venue_id}/delivery/platforms")
async def get_delivery_platforms(venue_id: str, db: DbSession):
    """Get delivery platform integrations."""
    return _get_setting_list(db, "delivery_platforms", venue_id)


@router.get("/{venue_id}/delivery/orders")
async def get_delivery_orders(venue_id: str):
    """Get delivery orders."""
    return []


@router.get("/{venue_id}/delivery/zones")
async def get_delivery_zones(venue_id: str, db: DbSession):
    """Get delivery zones."""
    return _get_setting_list(db, "delivery_zones", venue_id)


@router.get("/{venue_id}/delivery/drivers")
async def get_delivery_drivers(venue_id: str):
    """Get delivery drivers."""
    return []


# Drive-Thru
@router.get("/{venue_id}/drive-thru/lanes")
async def get_drive_thru_lanes(venue_id: str, db: DbSession):
    """Get drive-thru lanes."""
    return _get_setting_list(db, "drive_thru_lanes", venue_id)


@router.get("/{venue_id}/drive-thru/vehicles")
async def get_drive_thru_vehicles(venue_id: str):
    """Get vehicles in drive-thru queue."""
    return []

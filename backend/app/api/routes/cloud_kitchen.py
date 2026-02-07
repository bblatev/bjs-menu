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
async def get_delivery_orders(venue_id: str, db: DbSession):
    """Get delivery orders."""
    from app.models.delivery import DeliveryOrder
    orders = db.query(DeliveryOrder).order_by(DeliveryOrder.id.desc()).limit(50).all()
    return [
        {
            "id": o.id,
            "platform": o.platform.value if hasattr(o.platform, 'value') else str(o.platform),
            "status": o.status.value if hasattr(o.status, 'value') else str(o.status),
            "customer_name": o.customer_name,
            "total": float(o.total or 0),
            "created_at": o.received_at.isoformat() if o.received_at else None,
        }
        for o in orders
    ]


@router.get("/{venue_id}/delivery/zones")
async def get_delivery_zones(venue_id: str, db: DbSession):
    """Get delivery zones."""
    return _get_setting_list(db, "delivery_zones", venue_id)


@router.get("/{venue_id}/delivery/drivers")
async def get_delivery_drivers(venue_id: str, db: DbSession):
    """Get delivery drivers from staff with driver role."""
    from app.models.staff import StaffUser
    drivers = db.query(StaffUser).filter(
        StaffUser.role.in_(["driver", "delivery"]),
    ).all()
    return [
        {"id": d.id, "name": d.name, "role": d.role, "status": "available"}
        for d in drivers
    ]


# Drive-Thru
@router.get("/{venue_id}/drive-thru/lanes")
async def get_drive_thru_lanes(venue_id: str, db: DbSession):
    """Get drive-thru lanes."""
    return _get_setting_list(db, "drive_thru_lanes", venue_id)


@router.get("/{venue_id}/drive-thru/vehicles")
async def get_drive_thru_vehicles(venue_id: str, db: DbSession):
    """Get vehicles in drive-thru queue from app settings."""
    return _get_setting_list(db, "drive_thru_vehicles", venue_id)

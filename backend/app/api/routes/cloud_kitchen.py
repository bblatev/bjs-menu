"""Cloud kitchen, delivery, and drive-thru v6 routes."""

from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

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


class CreateCloudKitchenBrandRequest(BaseModel):
    name: str = Field(..., min_length=1)
    cuisine: str = Field(default="")
    active: Optional[bool] = True


@router.post("/{venue_id}/cloud-kitchen/brands")
async def create_cloud_kitchen_brand(venue_id: str, data: CreateCloudKitchenBrandRequest, db: DbSession):
    """Create a virtual brand for cloud kitchen."""
    row = db.query(AppSetting).filter(
        AppSetting.category == "cloud_kitchen_brands",
        AppSetting.key == venue_id,
    ).first()
    brands = row.value if row and isinstance(row.value, list) else []
    new_brand = {
        "id": len(brands) + 1,
        "name": data.name,
        "cuisine": data.cuisine,
        "active": data.active,
    }
    brands.append(new_brand)
    if row:
        row.value = brands
    else:
        row = AppSetting(category="cloud_kitchen_brands", key=venue_id, value=brands)
        db.add(row)
    db.commit()
    return new_brand


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


@router.get("/{venue_id}/drive-thru/stats")
async def get_drive_thru_stats(venue_id: str, db: DbSession, start: str = None, end: str = None):
    """Get drive-thru statistics from guest orders with drive-thru order_type."""
    from app.models.restaurant import GuestOrder
    from sqlalchemy import func as sqlfunc
    total = db.query(sqlfunc.count(GuestOrder.id)).filter(
        GuestOrder.order_type == "drive-thru"
    ).scalar() or 0
    return {
        "total_orders": total,
        "avg_service_time_seconds": 0,
        "avg_wait_time_seconds": 0,
        "orders_per_hour": 0,
        "peak_hour": None,
        "completion_rate": 100 if total > 0 else 0,
    }


@router.get("/{venue_id}/delivery/stats")
async def get_delivery_stats(venue_id: str, db: DbSession, start: str = None, end: str = None):
    """Get delivery statistics."""
    from app.models.delivery import DeliveryOrder
    from sqlalchemy import func as sqlfunc
    total = db.query(sqlfunc.count(DeliveryOrder.id)).scalar() or 0
    revenue = db.query(sqlfunc.sum(DeliveryOrder.total)).scalar() or 0
    # Orders by platform
    platform_stats = db.query(
        DeliveryOrder.platform,
        sqlfunc.count(DeliveryOrder.id).label("count"),
        sqlfunc.sum(DeliveryOrder.total).label("revenue"),
    ).group_by(DeliveryOrder.platform).all()
    by_platform = [
        {"platform": str(p.platform.value if hasattr(p.platform, 'value') else p.platform), "orders": p.count, "revenue": float(p.revenue or 0)}
        for p in platform_stats
    ]
    return {
        "total_orders": total,
        "avg_delivery_time_minutes": 0,
        "on_time_rate": 0,
        "active_drivers": 0,
        "revenue": float(revenue),
        "orders_by_platform": by_platform,
    }


@router.get("/{venue_id}/cloud-kitchen/performance")
async def get_cloud_kitchen_performance(venue_id: str, db: DbSession, start: str = None, end: str = None):
    """Get cloud kitchen performance metrics."""
    from app.models.delivery import DeliveryOrder
    from sqlalchemy import func as sqlfunc
    total = db.query(sqlfunc.count(DeliveryOrder.id)).scalar() or 0
    revenue = db.query(sqlfunc.sum(DeliveryOrder.total)).scalar() or 0
    # Brands from settings
    brands = _get_setting_list(db, "cloud_kitchen_brands", venue_id)
    stations = _get_setting_list(db, "cloud_kitchen_stations", venue_id)
    return {
        "total_orders": total,
        "revenue": float(revenue or 0),
        "avg_prep_time_minutes": 0,
        "utilization_rate": 0,
        "orders_by_brand": [{"brand": b.get("name", ""), "orders": 0} for b in brands] if isinstance(brands, list) and brands and isinstance(brands[0], dict) else [],
        "orders_by_station": [{"station": s.get("name", ""), "orders": 0} for s in stations] if isinstance(stations, list) and stations and isinstance(stations[0], dict) else [],
    }

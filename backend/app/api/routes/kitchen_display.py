"""Kitchen Display System display routes (backward compat for /kitchen-display/ prefix)."""

from fastapi import APIRouter
from sqlalchemy import func

from app.db.session import DbSession
from app.models.advanced_features import KitchenStation
from app.models.restaurant import KitchenOrder

router = APIRouter()


@router.get("/stations")
async def get_display_stations(db: DbSession):
    """Get KDS display stations."""
    stations = db.query(KitchenStation).filter(KitchenStation.is_active == True).order_by(KitchenStation.id).all()

    pending_counts = dict(
        db.query(KitchenOrder.station, func.count(KitchenOrder.id))
        .filter(KitchenOrder.status.in_(["pending", "cooking"]))
        .group_by(KitchenOrder.station)
        .all()
    )

    return [
        {
            "id": s.station_type,
            "station_id": s.station_type,
            "name": s.name,
            "type": s.station_type,
            "active": s.is_active,
            "current_load": pending_counts.get(s.station_type, 0),
            "max_capacity": s.max_capacity if hasattr(s, 'max_capacity') else 15,
            "pending_tickets": pending_counts.get(s.station_type, 0),
            "avg_time": s.avg_item_time_seconds // 60 if s.avg_item_time_seconds else 0,
            "avg_cook_time": s.avg_item_time_seconds // 60 if s.avg_item_time_seconds else 0,
        }
        for s in stations
    ]


@router.get("/tickets")
async def get_display_tickets(db: DbSession, station: str = None, status: str = None):
    """Get KDS display tickets."""
    query = db.query(KitchenOrder)
    if status:
        query = query.filter(KitchenOrder.status == status)
    else:
        query = query.filter(KitchenOrder.status.in_(["pending", "cooking"]))
    if station:
        query = query.filter(KitchenOrder.station == station)
    orders = query.order_by(KitchenOrder.priority.desc(), KitchenOrder.created_at).all()
    return [
        {
            "id": o.id,
            "ticket_id": str(o.id),
            "order_id": o.id,
            "table_number": str(o.table_number) if o.table_number else None,
            "station": o.station,
            "station_id": o.station,
            "status": o.status,
            "priority": o.priority,
            "items": o.items or [],
            "item_count": len(o.items) if o.items else 0,
            "notes": o.notes,
            "cook_time_seconds": None,
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "started_at": o.started_at.isoformat() if o.started_at else None,
        }
        for o in orders
    ]

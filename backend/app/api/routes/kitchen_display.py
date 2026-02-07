"""Kitchen Display System display routes."""

from fastapi import APIRouter

from app.db.session import DbSession
from app.models.advanced_features import KitchenStation
from app.models.restaurant import KitchenOrder

router = APIRouter()


@router.get("/stations")
async def get_display_stations(db: DbSession):
    """Get KDS display stations."""
    stations = db.query(KitchenStation).filter(KitchenStation.is_active == True).order_by(KitchenStation.id).all()
    return [
        {
            "id": s.station_type,
            "name": s.name,
            "active": s.is_active,
            "pending_tickets": 0,
            "avg_time": s.avg_item_time_seconds // 60 if s.avg_item_time_seconds else 0,
        }
        for s in stations
    ]


@router.get("/tickets")
async def get_display_tickets(db: DbSession, station: str = None):
    """Get KDS display tickets."""
    query = db.query(KitchenOrder).filter(
        KitchenOrder.status.in_(["pending", "cooking"])
    )
    if station:
        query = query.filter(KitchenOrder.station == station)
    orders = query.order_by(KitchenOrder.priority.desc(), KitchenOrder.created_at).all()
    return [
        {
            "id": o.id,
            "table_number": o.table_number,
            "station": o.station,
            "status": o.status,
            "priority": o.priority,
            "items": o.items or [],
            "notes": o.notes,
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "started_at": o.started_at.isoformat() if o.started_at else None,
        }
        for o in orders
    ]

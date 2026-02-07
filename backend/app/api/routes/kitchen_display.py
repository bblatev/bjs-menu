"""Kitchen Display System display routes."""

from fastapi import APIRouter

from app.db.session import DbSession
from app.models.advanced_features import KitchenStation

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
async def get_display_tickets():
    """Get KDS display tickets."""
    return []

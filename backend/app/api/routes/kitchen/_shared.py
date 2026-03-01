"""Kitchen Display System (KDS) routes - using database models."""

import logging
from datetime import timedelta
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import func

from app.core.rate_limit import limiter
from app.core.responses import list_response
from app.schemas.pagination import paginate_query, PaginatedResponse
from app.db.session import DbSession
from app.models.restaurant import KitchenOrder, GuestOrder, MenuItem, Table, Check

logger = logging.getLogger(__name__)



def _utc_aware(dt):
    """Make a datetime UTC-aware if it's naive (SQLite returns naive datetimes)."""
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def _sync_guest_order_status(db: DbSession, kitchen_order: KitchenOrder, new_status: str):
    """
    Sync the guest order status when kitchen order status changes.
    Maps kitchen statuses to guest order statuses.
    """
    # Status mapping: kitchen -> guest order
    status_map = {
        "pending": "received",
        "cooking": "preparing",
        "ready": "ready",
        "completed": "served",
        "cancelled": "cancelled",
    }

    guest_status = status_map.get(new_status)
    if not guest_status:
        return

    # Find the corresponding guest order by table_number and similar creation time
    # Guest orders are created just before kitchen orders, so find orders with matching table
    if kitchen_order.table_number:
        guest_order = db.query(GuestOrder).filter(
            GuestOrder.table_number == kitchen_order.table_number,
            GuestOrder.status.notin_(["completed", "cancelled", "paid"]),
        ).order_by(GuestOrder.created_at.desc()).first()

        if guest_order:
            guest_order.status = guest_status
            if new_status == "ready":
                guest_order.ready_at = datetime.now(timezone.utc)
            db.flush()


def _compute_avg_cook_time(db: DbSession, location_id: Optional[int] = None) -> float:
    """Compute average cook time in minutes from completed kitchen orders."""
    query = db.query(KitchenOrder).filter(
        KitchenOrder.status == "completed",
        KitchenOrder.started_at.isnot(None),
        KitchenOrder.completed_at.isnot(None),
    )
    if location_id:
        query = query.filter(KitchenOrder.location_id == location_id)
    completed = query.limit(10000).all()
    if not completed:
        return 0
    total_minutes = sum(
        (o.completed_at - o.started_at).total_seconds() / 60
        for o in completed
        if o.completed_at and o.started_at
    )
    return round(total_minutes / len(completed), 1)


class KitchenStats(BaseModel):
    """Kitchen statistics response."""
    active_alerts: int = 0
    orders_by_status: dict = {}
    items_86_count: int = 0
    rush_orders_today: int = 0
    vip_orders_today: int = 0
    avg_prep_time_minutes: Optional[float] = None
    orders_completed_today: int = 0



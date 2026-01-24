"""Curbside Pickup Service - "I'm Here" notifications."""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from app.models.advanced_features import CurbsideOrder


class CurbsideService:
    """Service for curbside pickup management."""

    def __init__(self, db: Session):
        self.db = db

    def create_curbside_order(
        self,
        order_id: int,
        location_id: int,
        customer_name: str,
        customer_phone: str,
        vehicle_description: Optional[str] = None,
        vehicle_color: Optional[str] = None,
        vehicle_make: Optional[str] = None,
        estimated_ready_time: Optional[datetime] = None,
    ) -> CurbsideOrder:
        """Create a new curbside pickup order."""
        order = CurbsideOrder(
            order_id=order_id,
            location_id=location_id,
            customer_name=customer_name,
            customer_phone=customer_phone,
            vehicle_description=vehicle_description,
            vehicle_color=vehicle_color,
            vehicle_make=vehicle_make,
            estimated_ready_time=estimated_ready_time,
        )
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order

    def get_order(
        self,
        order_id: int,
    ) -> Optional[CurbsideOrder]:
        """Get a curbside order by order ID."""
        query = select(CurbsideOrder).where(CurbsideOrder.order_id == order_id)
        result = self.db.execute(query)
        return result.scalar_one_or_none()

    def get_pending_orders(
        self,
        location_id: int,
    ) -> List[CurbsideOrder]:
        """Get all pending curbside orders (not yet delivered)."""
        query = select(CurbsideOrder).where(
            and_(
                CurbsideOrder.location_id == location_id,
                CurbsideOrder.order_delivered_at.is_(None),
            )
        ).order_by(CurbsideOrder.created_at)

        result = self.db.execute(query)
        return list(result.scalars().all())

    def get_arrived_orders(
        self,
        location_id: int,
    ) -> List[CurbsideOrder]:
        """Get orders where customer has arrived but not yet delivered."""
        query = select(CurbsideOrder).where(
            and_(
                CurbsideOrder.location_id == location_id,
                CurbsideOrder.customer_arrived_at.isnot(None),
                CurbsideOrder.order_delivered_at.is_(None),
            )
        ).order_by(CurbsideOrder.customer_arrived_at)

        result = self.db.execute(query)
        return list(result.scalars().all())

    def customer_arrived(
        self,
        order_id: int,
        parking_spot: Optional[str] = None,
    ) -> CurbsideOrder:
        """Mark customer as arrived ("I'm Here" notification)."""
        order = self.get_order(order_id)
        if not order:
            raise ValueError(f"Curbside order {order_id} not found")

        order.customer_arrived_at = datetime.utcnow()
        order.parking_spot = parking_spot
        order.arrival_notification_sent = True

        self.db.commit()
        self.db.refresh(order)
        return order

    def mark_ready(
        self,
        order_id: int,
    ) -> CurbsideOrder:
        """Mark order as ready for pickup."""
        order = self.get_order(order_id)
        if not order:
            raise ValueError(f"Curbside order {order_id} not found")

        order.ready_notification_sent = True
        self.db.commit()
        self.db.refresh(order)

        # In production, this would trigger SMS/push notification
        return order

    def mark_delivered(
        self,
        order_id: int,
    ) -> CurbsideOrder:
        """Mark order as delivered to customer."""
        order = self.get_order(order_id)
        if not order:
            raise ValueError(f"Curbside order {order_id} not found")

        order.order_delivered_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(order)
        return order

    def get_status(
        self,
        location_id: int,
    ) -> Dict[str, Any]:
        """Get curbside pickup status summary."""
        pending = self.get_pending_orders(location_id)
        arrived = self.get_arrived_orders(location_id)

        # Calculate average wait time for arrived customers
        avg_wait = None
        if arrived:
            total_wait = sum(
                (datetime.utcnow() - o.customer_arrived_at).total_seconds() / 60
                for o in arrived
            )
            avg_wait = total_wait / len(arrived)

        return {
            "pending_arrivals": len(pending) - len(arrived),
            "arrived_waiting": len(arrived),
            "avg_wait_time_minutes": avg_wait,
            "orders": [
                {
                    "id": o.id,
                    "order_id": o.order_id,
                    "customer_name": o.customer_name,
                    "vehicle_description": o.vehicle_description,
                    "vehicle_color": o.vehicle_color,
                    "parking_spot": o.parking_spot,
                    "arrived_at": o.customer_arrived_at.isoformat() if o.customer_arrived_at else None,
                    "wait_minutes": int((datetime.utcnow() - o.customer_arrived_at).total_seconds() / 60)
                        if o.customer_arrived_at else None,
                }
                for o in arrived
            ],
        }

    def get_stats(
        self,
        location_id: int,
        days: int = 7,
    ) -> Dict[str, Any]:
        """Get curbside pickup statistics."""
        start_date = datetime.utcnow() - timedelta(days=days)

        query = select(
            func.count(CurbsideOrder.id).label("total_orders"),
            func.avg(
                func.extract("epoch", CurbsideOrder.order_delivered_at - CurbsideOrder.customer_arrived_at) / 60
            ).label("avg_wait"),
        ).where(
            and_(
                CurbsideOrder.location_id == location_id,
                CurbsideOrder.created_at >= start_date,
                CurbsideOrder.order_delivered_at.isnot(None),
            )
        )

        result = self.db.execute(query)
        stats = result.first()

        # Count orders by wait time buckets
        quick_query = select(
            func.count(CurbsideOrder.id)
        ).where(
            and_(
                CurbsideOrder.location_id == location_id,
                CurbsideOrder.created_at >= start_date,
                CurbsideOrder.order_delivered_at.isnot(None),
                func.extract("epoch", CurbsideOrder.order_delivered_at - CurbsideOrder.customer_arrived_at) <= 300,  # 5 min
            )
        )
        quick_result = self.db.execute(quick_query)
        quick_count = quick_result.scalar() or 0

        return {
            "period_days": days,
            "total_orders": stats.total_orders or 0,
            "avg_wait_time_minutes": float(stats.avg_wait or 0),
            "orders_under_5_min": quick_count,
            "under_5_min_percent": (quick_count / stats.total_orders * 100) if stats.total_orders else 0,
        }

    def update_vehicle_info(
        self,
        order_id: int,
        vehicle_description: Optional[str] = None,
        vehicle_color: Optional[str] = None,
        vehicle_make: Optional[str] = None,
        parking_spot: Optional[str] = None,
    ) -> CurbsideOrder:
        """Update vehicle information for an order."""
        order = self.get_order(order_id)
        if not order:
            raise ValueError(f"Curbside order {order_id} not found")

        if vehicle_description is not None:
            order.vehicle_description = vehicle_description
        if vehicle_color is not None:
            order.vehicle_color = vehicle_color
        if vehicle_make is not None:
            order.vehicle_make = vehicle_make
        if parking_spot is not None:
            order.parking_spot = parking_spot

        self.db.commit()
        self.db.refresh(order)
        return order

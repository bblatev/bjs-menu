"""Order Throttling Service - Olo style kitchen capacity management."""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from app.models.advanced_features import KitchenCapacity, OrderThrottleEvent


class OrderThrottlingService:
    """Service for smart order throttling based on kitchen capacity."""

    def __init__(self, db: Session):
        self.db = db
        self._current_loads: Dict[int, int] = {}  # location_id -> current load

    def create_capacity_config(
        self,
        location_id: int,
        max_orders_per_15min: int = 20,
        max_items_per_15min: int = 100,
        station_capacities: Optional[Dict[str, int]] = None,
        peak_hour_multiplier: float = 1.0,
        off_peak_multiplier: float = 1.5,
        is_active: bool = True,
    ) -> KitchenCapacity:
        """Create kitchen capacity configuration."""
        config = KitchenCapacity(
            location_id=location_id,
            max_orders_per_15min=max_orders_per_15min,
            max_items_per_15min=max_items_per_15min,
            station_capacities=station_capacities,
            peak_hour_multiplier=peak_hour_multiplier,
            off_peak_multiplier=off_peak_multiplier,
            is_active=is_active,
        )
        self.db.add(config)
        self.db.commit()
        self.db.refresh(config)
        return config

    def get_capacity_config(
        self,
        location_id: int,
    ) -> Optional[KitchenCapacity]:
        """Get capacity config for a location."""
        query = select(KitchenCapacity).where(
            and_(
                KitchenCapacity.location_id == location_id,
                KitchenCapacity.is_active == True,
            )
        )
        result = self.db.execute(query)
        return result.scalar_one_or_none()

    def check_capacity(
        self,
        location_id: int,
        order_items_count: int,
    ) -> Dict[str, Any]:
        """Check if kitchen has capacity for a new order."""
        config = self.get_capacity_config(location_id)
        if not config:
            return {
                "can_accept": True,
                "current_load": 0,
                "max_capacity": 100,
                "load_percent": 0,
                "estimated_wait_minutes": 0,
            }

        # Get current load (orders in last 15 minutes)
        window_start = datetime.utcnow() - timedelta(minutes=15)
        current_load = self._current_loads.get(location_id, 0)

        # Apply time-based multiplier
        hour = datetime.utcnow().hour
        is_peak = 11 <= hour <= 14 or 18 <= hour <= 21
        multiplier = config.peak_hour_multiplier if is_peak else config.off_peak_multiplier

        effective_capacity = int(config.max_orders_per_15min * multiplier)
        load_percent = (current_load / effective_capacity * 100) if effective_capacity > 0 else 0

        can_accept = current_load < effective_capacity
        estimated_wait = 0

        if not can_accept:
            # Estimate wait time based on overflow
            overflow = current_load - effective_capacity
            estimated_wait = (overflow / max(1, effective_capacity / 15)) * 15  # minutes

        return {
            "can_accept": can_accept,
            "current_load": current_load,
            "max_capacity": effective_capacity,
            "load_percent": min(100, load_percent),
            "estimated_wait_minutes": int(estimated_wait),
        }

    def register_order(
        self,
        location_id: int,
        order_items_count: int,
    ) -> Dict[str, Any]:
        """Register a new order and check if throttling needed."""
        capacity_status = self.check_capacity(location_id, order_items_count)

        # Update current load
        self._current_loads[location_id] = self._current_loads.get(location_id, 0) + 1

        if not capacity_status["can_accept"]:
            # Log throttle event
            event = OrderThrottleEvent(
                location_id=location_id,
                event_time=datetime.utcnow(),
                throttle_type="delay" if capacity_status["estimated_wait_minutes"] < 30 else "reject",
                current_load=capacity_status["current_load"],
                max_capacity=capacity_status["max_capacity"],
                orders_affected=1,
                avg_delay_minutes=capacity_status["estimated_wait_minutes"],
            )
            self.db.add(event)
            self.db.commit()

        return capacity_status

    def complete_order(
        self,
        location_id: int,
    ) -> None:
        """Mark an order as completed to reduce load."""
        if location_id in self._current_loads:
            self._current_loads[location_id] = max(0, self._current_loads[location_id] - 1)

    def get_throttle_events(
        self,
        location_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[OrderThrottleEvent]:
        """Get throttle events for analysis."""
        query = select(OrderThrottleEvent).where(
            OrderThrottleEvent.location_id == location_id
        )

        if start_date:
            query = query.where(OrderThrottleEvent.event_time >= start_date)
        if end_date:
            query = query.where(OrderThrottleEvent.event_time <= end_date)

        query = query.order_by(OrderThrottleEvent.event_time.desc()).limit(limit)

        result = self.db.execute(query)
        return list(result.scalars().all())

    def get_throttle_stats(
        self,
        location_id: int,
        days: int = 7,
    ) -> Dict[str, Any]:
        """Get throttling statistics."""
        start_date = datetime.utcnow() - timedelta(days=days)

        query = select(
            func.count(OrderThrottleEvent.id).label("total_events"),
            func.sum(OrderThrottleEvent.orders_affected).label("total_affected"),
            func.avg(OrderThrottleEvent.avg_delay_minutes).label("avg_delay"),
        ).where(
            and_(
                OrderThrottleEvent.location_id == location_id,
                OrderThrottleEvent.event_time >= start_date,
            )
        )

        result = self.db.execute(query)
        stats = result.first()

        # Count by throttle type
        type_query = select(
            OrderThrottleEvent.throttle_type,
            func.count(OrderThrottleEvent.id).label("count"),
        ).where(
            and_(
                OrderThrottleEvent.location_id == location_id,
                OrderThrottleEvent.event_time >= start_date,
            )
        ).group_by(OrderThrottleEvent.throttle_type)

        type_result = self.db.execute(type_query)
        by_type = {row.throttle_type: row.count for row in type_result.all()}

        return {
            "total_events": stats.total_events or 0,
            "total_orders_affected": stats.total_affected or 0,
            "avg_delay_minutes": float(stats.avg_delay or 0),
            "by_type": by_type,
            "period_days": days,
        }

    def update_capacity_config(
        self,
        config_id: int,
        **updates,
    ) -> KitchenCapacity:
        """Update capacity configuration."""
        config = self.db.get(KitchenCapacity, config_id)
        if not config:
            raise ValueError(f"Config {config_id} not found")

        for key, value in updates.items():
            if hasattr(config, key):
                setattr(config, key, value)

        self.db.commit()
        self.db.refresh(config)
        return config

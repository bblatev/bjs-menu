"""Kitchen Load Balancing Service."""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from app.models.advanced_features import KitchenStation, StationLoadMetric


class KitchenLoadService:
    """Service for kitchen station load balancing."""

    def __init__(self, db: Session):
        self.db = db

    def create_station(
        self,
        location_id: int,
        name: str,
        station_type: str,
        max_concurrent_items: int = 10,
        avg_item_time_seconds: int = 300,
        equipment_ids: Optional[List[int]] = None,
        min_staff: int = 1,
        max_staff: int = 3,
        is_active: bool = True,
    ) -> KitchenStation:
        """Create a kitchen station."""
        station = KitchenStation(
            location_id=location_id,
            name=name,
            station_type=station_type,
            max_concurrent_items=max_concurrent_items,
            avg_item_time_seconds=avg_item_time_seconds,
            equipment_ids=equipment_ids,
            min_staff=min_staff,
            max_staff=max_staff,
            is_active=is_active,
        )
        self.db.add(station)
        self.db.commit()
        self.db.refresh(station)
        return station

    def get_stations(
        self,
        location_id: int,
        active_only: bool = True,
    ) -> List[KitchenStation]:
        """Get kitchen stations for a location."""
        query = select(KitchenStation).where(
            KitchenStation.location_id == location_id
        )

        if active_only:
            query = query.where(KitchenStation.is_active == True)

        query = query.order_by(KitchenStation.name)

        result = self.db.execute(query)
        return list(result.scalars().all())

    def record_load_metric(
        self,
        station_id: int,
        items_in_queue: int,
        items_in_progress: int,
        avg_wait_time_seconds: Optional[int] = None,
        avg_cook_time_seconds: Optional[int] = None,
    ) -> StationLoadMetric:
        """Record a load metric for a station."""
        station = self.db.get(KitchenStation, station_id)
        if not station:
            raise ValueError(f"Station {station_id} not found")

        total_items = items_in_queue + items_in_progress
        load_percent = (total_items / station.max_concurrent_items * 100) if station.max_concurrent_items > 0 else 0
        is_overloaded = load_percent > 100

        metric = StationLoadMetric(
            station_id=station_id,
            timestamp=datetime.utcnow(),
            items_in_queue=items_in_queue,
            items_in_progress=items_in_progress,
            avg_wait_time_seconds=avg_wait_time_seconds,
            avg_cook_time_seconds=avg_cook_time_seconds,
            load_percent=load_percent,
            is_overloaded=is_overloaded,
        )
        self.db.add(metric)
        self.db.commit()
        self.db.refresh(metric)
        return metric

    def get_current_load(
        self,
        station_id: int,
    ) -> Optional[StationLoadMetric]:
        """Get the most recent load metric for a station."""
        query = select(StationLoadMetric).where(
            StationLoadMetric.station_id == station_id
        ).order_by(StationLoadMetric.timestamp.desc()).limit(1)

        result = self.db.execute(query)
        return result.scalar_one_or_none()

    def get_load_history(
        self,
        station_id: int,
        hours: int = 4,
    ) -> List[StationLoadMetric]:
        """Get load history for a station."""
        since = datetime.utcnow() - timedelta(hours=hours)

        query = select(StationLoadMetric).where(
            and_(
                StationLoadMetric.station_id == station_id,
                StationLoadMetric.timestamp >= since,
            )
        ).order_by(StationLoadMetric.timestamp)

        result = self.db.execute(query)
        return list(result.scalars().all())

    def get_kitchen_summary(
        self,
        location_id: int,
    ) -> Dict[str, Any]:
        """Get kitchen load summary for all stations."""
        stations = self.get_stations(location_id)

        station_loads = []
        total_queue = 0
        total_progress = 0
        total_capacity = 0
        overloaded_count = 0
        bottleneck = None
        max_load = 0

        for station in stations:
            current = self.get_current_load(station.id)

            if current:
                load_data = {
                    "station_id": station.id,
                    "station_name": station.name,
                    "station_type": station.station_type,
                    "items_in_queue": current.items_in_queue,
                    "items_in_progress": current.items_in_progress,
                    "load_percent": current.load_percent,
                    "is_overloaded": current.is_overloaded,
                    "avg_wait_time_seconds": current.avg_wait_time_seconds,
                }

                total_queue += current.items_in_queue
                total_progress += current.items_in_progress

                if current.is_overloaded:
                    overloaded_count += 1

                if current.load_percent > max_load:
                    max_load = current.load_percent
                    bottleneck = station.name
            else:
                load_data = {
                    "station_id": station.id,
                    "station_name": station.name,
                    "station_type": station.station_type,
                    "items_in_queue": 0,
                    "items_in_progress": 0,
                    "load_percent": 0,
                    "is_overloaded": False,
                    "avg_wait_time_seconds": None,
                }

            total_capacity += station.max_concurrent_items
            station_loads.append(load_data)

        avg_load = (total_queue + total_progress) / total_capacity * 100 if total_capacity > 0 else 0

        return {
            "total_stations": len(stations),
            "overloaded_stations": overloaded_count,
            "total_items_in_queue": total_queue,
            "total_items_in_progress": total_progress,
            "avg_load_percent": avg_load,
            "station_loads": station_loads,
            "bottleneck_station": bottleneck,
        }

    def get_station_recommendations(
        self,
        location_id: int,
        order_items: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Get recommendations for routing items to stations."""
        stations = self.get_stations(location_id)
        station_by_type = {s.station_type: s for s in stations}

        recommendations = []

        for item in order_items:
            item_type = item.get("station_type", "grill")

            if item_type in station_by_type:
                station = station_by_type[item_type]
                current = self.get_current_load(station.id)

                if current and current.load_percent > 80:
                    # Look for alternative station
                    alt_station = None
                    min_load = current.load_percent

                    for s in stations:
                        if s.id != station.id:
                            s_load = self.get_current_load(s.id)
                            if s_load and s_load.load_percent < min_load:
                                alt_station = s
                                min_load = s_load.load_percent

                    if alt_station and min_load < 60:
                        recommendations.append({
                            "item_id": item.get("id"),
                            "recommended_station": alt_station.name,
                            "reason": f"Primary station overloaded ({current.load_percent:.0f}%)",
                            "alternative_load": min_load,
                        })
                    else:
                        recommendations.append({
                            "item_id": item.get("id"),
                            "recommended_station": station.name,
                            "reason": "Primary station (no better alternative)",
                            "warning": "High load - expect delays",
                        })
                else:
                    recommendations.append({
                        "item_id": item.get("id"),
                        "recommended_station": station.name,
                        "reason": "Primary station available",
                    })

        return {
            "recommendations": recommendations,
            "total_items": len(order_items),
        }

    def update_station(
        self,
        station_id: int,
        **updates,
    ) -> KitchenStation:
        """Update a kitchen station."""
        station = self.db.get(KitchenStation, station_id)
        if not station:
            raise ValueError(f"Station {station_id} not found")

        for key, value in updates.items():
            if hasattr(station, key):
                setattr(station, key, value)

        self.db.commit()
        self.db.refresh(station)
        return station

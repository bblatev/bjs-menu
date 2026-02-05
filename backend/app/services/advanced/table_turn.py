"""Table Turn Optimization Service."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional, Dict, Any

from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from app.models.advanced_features import TableTurnMetric, TableTurnForecast


class TableTurnService:
    """Service for table turn optimization."""

    def __init__(self, db: Session):
        self.db = db

    def start_turn(
        self,
        location_id: int,
        table_id: int,
        party_size: int,
        seated_at: Optional[datetime] = None,
    ) -> TableTurnMetric:
        """Start tracking a new table turn."""
        metric = TableTurnMetric(
            location_id=location_id,
            table_id=table_id,
            seated_at=seated_at or datetime.now(timezone.utc),
            party_size=party_size,
        )
        self.db.add(metric)
        self.db.commit()
        self.db.refresh(metric)

        # Create turn forecast
        self._create_forecast(metric)

        return metric

    def _create_forecast(
        self,
        metric: TableTurnMetric,
    ) -> TableTurnForecast:
        """Create a forecast for table availability."""
        # Get historical average for this table
        query = select(
            func.avg(TableTurnMetric.total_turn_time).label("avg_turn"),
        ).where(
            and_(
                TableTurnMetric.location_id == metric.location_id,
                TableTurnMetric.table_id == metric.table_id,
                TableTurnMetric.total_turn_time.isnot(None),
            )
        )
        result = self.db.execute(query)
        avg_turn = result.scalar() or 60  # Default 60 minutes

        # Adjust for party size
        if metric.party_size > 4:
            avg_turn *= 1.2
        elif metric.party_size <= 2:
            avg_turn *= 0.85

        predicted_available = metric.seated_at + timedelta(minutes=int(avg_turn))

        forecast = TableTurnForecast(
            location_id=metric.location_id,
            table_id=metric.table_id,
            current_party_seated_at=metric.seated_at,
            predicted_available_at=predicted_available,
            confidence=0.75,
        )
        self.db.add(forecast)
        self.db.commit()
        self.db.refresh(forecast)
        return forecast

    def update_milestone(
        self,
        turn_id: int,
        milestone: str,
        timestamp: Optional[datetime] = None,
    ) -> TableTurnMetric:
        """Update a milestone for a table turn."""
        metric = self.db.get(TableTurnMetric, turn_id)
        if not metric:
            raise ValueError(f"Turn {turn_id} not found")

        ts = timestamp or datetime.now(timezone.utc)

        if milestone == "order_placed":
            metric.order_placed_at = ts
            if metric.seated_at:
                metric.time_to_order = int((ts - metric.seated_at).total_seconds() / 60)
        elif milestone == "food_delivered":
            metric.food_delivered_at = ts
            if metric.order_placed_at:
                metric.time_to_food = int((ts - metric.order_placed_at).total_seconds() / 60)
        elif milestone == "check_requested":
            metric.check_requested_at = ts
            if metric.food_delivered_at:
                metric.dining_time = int((ts - metric.food_delivered_at).total_seconds() / 60)
        elif milestone == "check_paid":
            metric.check_paid_at = ts
        elif milestone == "table_cleared":
            metric.table_cleared_at = ts
            if metric.seated_at:
                metric.total_turn_time = int((ts - metric.seated_at).total_seconds() / 60)

            # Update forecast with actual
            self._update_forecast_actual(metric)

        self.db.commit()
        self.db.refresh(metric)
        return metric

    def _update_forecast_actual(
        self,
        metric: TableTurnMetric,
    ) -> None:
        """Update forecast with actual availability time."""
        query = select(TableTurnForecast).where(
            and_(
                TableTurnForecast.location_id == metric.location_id,
                TableTurnForecast.table_id == metric.table_id,
                TableTurnForecast.current_party_seated_at == metric.seated_at,
            )
        )
        result = self.db.execute(query)
        forecast = result.scalar_one_or_none()

        if forecast and metric.table_cleared_at:
            forecast.actual_available_at = metric.table_cleared_at
            forecast.prediction_error_minutes = int(
                (metric.table_cleared_at - forecast.predicted_available_at).total_seconds() / 60
            )
            self.db.commit()

    def set_check_total(
        self,
        turn_id: int,
        check_total: Decimal,
    ) -> TableTurnMetric:
        """Set the check total for a turn."""
        metric = self.db.get(TableTurnMetric, turn_id)
        if not metric:
            raise ValueError(f"Turn {turn_id} not found")

        metric.check_total = check_total

        if metric.total_turn_time and metric.total_turn_time > 0:
            metric.revenue_per_minute = check_total / metric.total_turn_time

        self.db.commit()
        self.db.refresh(metric)
        return metric

    def get_active_turns(
        self,
        location_id: int,
    ) -> List[TableTurnMetric]:
        """Get currently active table turns."""
        query = select(TableTurnMetric).where(
            and_(
                TableTurnMetric.location_id == location_id,
                TableTurnMetric.table_cleared_at.is_(None),
            )
        ).order_by(TableTurnMetric.seated_at)

        result = self.db.execute(query)
        return list(result.scalars().all())

    def get_available_tables(
        self,
        location_id: int,
        total_tables: int,
    ) -> Dict[str, Any]:
        """Get table availability status."""
        active = self.get_active_turns(location_id)
        occupied_tables = set(t.table_id for t in active)

        available = total_tables - len(occupied_tables)

        # Get forecasts for occupied tables
        forecasts = []
        for turn in active:
            query = select(TableTurnForecast).where(
                and_(
                    TableTurnForecast.location_id == location_id,
                    TableTurnForecast.table_id == turn.table_id,
                    TableTurnForecast.actual_available_at.is_(None),
                )
            ).order_by(TableTurnForecast.created_at.desc()).limit(1)

            result = self.db.execute(query)
            forecast = result.scalar_one_or_none()
            if forecast:
                forecasts.append(forecast)

        return {
            "total_tables": total_tables,
            "available_tables": available,
            "occupied_tables": len(occupied_tables),
            "predicted_next_availability": forecasts,
        }

    def get_summary(
        self,
        location_id: int,
        days: int = 7,
    ) -> Dict[str, Any]:
        """Get table turn summary."""
        since = datetime.now(timezone.utc) - timedelta(days=days)

        query = select(
            func.count(TableTurnMetric.id).label("count"),
            func.avg(TableTurnMetric.total_turn_time).label("avg_turn"),
            func.avg(TableTurnMetric.time_to_order).label("avg_order"),
            func.avg(TableTurnMetric.time_to_food).label("avg_food"),
            func.avg(TableTurnMetric.dining_time).label("avg_dining"),
            func.avg(TableTurnMetric.check_total).label("avg_check"),
            func.avg(TableTurnMetric.revenue_per_minute).label("avg_rpm"),
        ).where(
            and_(
                TableTurnMetric.location_id == location_id,
                TableTurnMetric.seated_at >= since,
                TableTurnMetric.total_turn_time.isnot(None),
            )
        )

        result = self.db.execute(query)
        stats = result.first()

        # Today's turns
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today_query = select(func.count(TableTurnMetric.id)).where(
            and_(
                TableTurnMetric.location_id == location_id,
                TableTurnMetric.seated_at >= today_start,
            )
        )
        today_result = self.db.execute(today_query)
        turns_today = today_result.scalar() or 0

        # Available tables (assuming 20 tables)
        active = self.get_active_turns(location_id)

        # Get forecasts for active turns
        forecasts = []
        for turn in active:
            query = select(TableTurnForecast).where(
                and_(
                    TableTurnForecast.location_id == location_id,
                    TableTurnForecast.table_id == turn.table_id,
                    TableTurnForecast.actual_available_at.is_(None),
                )
            ).order_by(TableTurnForecast.created_at.desc()).limit(1)

            result = self.db.execute(query)
            forecast = result.scalar_one_or_none()
            if forecast:
                forecasts.append(forecast)

        return {
            "avg_turn_time_minutes": float(stats.avg_turn or 0),
            "avg_time_to_order": float(stats.avg_order or 0),
            "avg_time_to_food": float(stats.avg_food or 0),
            "avg_dining_time": float(stats.avg_dining or 0),
            "avg_revenue_per_turn": float(stats.avg_check or 0),
            "avg_revenue_per_minute": float(stats.avg_rpm or 0),
            "turns_today": turns_today,
            "tables_available": 20 - len(active),  # Assuming 20 tables
            "predicted_next_availability": forecasts,
        }

    def get_turn_history(
        self,
        location_id: int,
        table_id: Optional[int] = None,
        limit: int = 50,
    ) -> List[TableTurnMetric]:
        """Get turn history."""
        query = select(TableTurnMetric).where(
            TableTurnMetric.location_id == location_id
        )

        if table_id:
            query = query.where(TableTurnMetric.table_id == table_id)

        query = query.order_by(TableTurnMetric.seated_at.desc()).limit(limit)

        result = self.db.execute(query)
        return list(result.scalars().all())

"""AI Food Waste Tracking Service - Leanpath/Winnow style."""

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any

from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from app.models.advanced_features import WasteTrackingEntry, WasteForecast, WasteCategory

logger = logging.getLogger(__name__)


class WasteTrackingService:
    """Service for AI-powered food waste tracking."""

    def __init__(self, db: Session):
        self.db = db

    def create_entry(
        self,
        location_id: int,
        category: WasteCategory,
        weight_kg: Decimal,
        cost_value: Decimal,
        product_id: Optional[int] = None,
        carbon_kg: Optional[Decimal] = None,
        image_url: Optional[str] = None,
        station: Optional[str] = None,
        shift: Optional[str] = None,
        reason: Optional[str] = None,
        recorded_by_id: Optional[int] = None,
    ) -> WasteTrackingEntry:
        """Create a new waste tracking entry and deduct from stock."""
        # Calculate carbon if not provided (avg 2.5 kg CO2 per kg food waste)
        if carbon_kg is None:
            carbon_kg = weight_kg * Decimal("2.5")

        entry = WasteTrackingEntry(
            location_id=location_id,
            product_id=product_id,
            category=category,
            weight_kg=weight_kg,
            cost_value=cost_value,
            carbon_kg=carbon_kg,
            image_url=image_url,
            station=station,
            shift=shift,
            reason=reason,
            recorded_by_id=recorded_by_id,
        )
        self.db.add(entry)
        self.db.flush()  # Get the entry ID before committing

        # Deduct from stock if a product is specified
        stock_result = None
        if product_id:
            try:
                from app.services.stock_deduction_service import StockDeductionService
                stock_service = StockDeductionService(self.db)
                stock_result = stock_service.deduct_for_waste(
                    product_id=product_id,
                    quantity=weight_kg,
                    unit="kg",
                    location_id=location_id,
                    waste_entry_id=entry.id,
                    reason=f"Waste ({category.value}): {reason or 'No reason specified'}",
                    created_by=recorded_by_id,
                )
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Stock deduction for waste failed: {e}")

        self.db.commit()
        self.db.refresh(entry)

        # Attach stock result to entry for API response
        entry._stock_result = stock_result
        return entry

    def get_entries(
        self,
        location_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category: Optional[WasteCategory] = None,
        station: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[WasteTrackingEntry]:
        """Get waste tracking entries with filters."""
        query = select(WasteTrackingEntry).where(
            WasteTrackingEntry.location_id == location_id
        )

        if start_date:
            query = query.where(WasteTrackingEntry.recorded_at >= datetime.combine(start_date, datetime.min.time()))
        if end_date:
            query = query.where(WasteTrackingEntry.recorded_at <= datetime.combine(end_date, datetime.max.time()))
        if category:
            query = query.where(WasteTrackingEntry.category == category)
        if station:
            query = query.where(WasteTrackingEntry.station == station)

        query = query.order_by(WasteTrackingEntry.recorded_at.desc()).limit(limit).offset(offset)
        result = self.db.execute(query)
        return list(result.scalars().all())

    def get_summary(
        self,
        location_id: int,
        start_date: date,
        end_date: date,
    ) -> Dict[str, Any]:
        """Get waste summary for a period."""
        query = select(
            func.sum(WasteTrackingEntry.weight_kg).label("total_weight"),
            func.sum(WasteTrackingEntry.cost_value).label("total_cost"),
            func.sum(WasteTrackingEntry.carbon_kg).label("total_carbon"),
        ).where(
            and_(
                WasteTrackingEntry.location_id == location_id,
                WasteTrackingEntry.recorded_at >= datetime.combine(start_date, datetime.min.time()),
                WasteTrackingEntry.recorded_at <= datetime.combine(end_date, datetime.max.time()),
            )
        )

        result = self.db.execute(query)
        totals = result.first()

        # Get breakdown by category
        category_query = select(
            WasteTrackingEntry.category,
            func.sum(WasteTrackingEntry.weight_kg).label("weight"),
        ).where(
            and_(
                WasteTrackingEntry.location_id == location_id,
                WasteTrackingEntry.recorded_at >= datetime.combine(start_date, datetime.min.time()),
                WasteTrackingEntry.recorded_at <= datetime.combine(end_date, datetime.max.time()),
            )
        ).group_by(WasteTrackingEntry.category)

        category_result = self.db.execute(category_query)
        by_category = {row.category.value: row.weight or Decimal("0") for row in category_result.all()}

        # Get breakdown by station
        station_query = select(
            WasteTrackingEntry.station,
            func.sum(WasteTrackingEntry.weight_kg).label("weight"),
        ).where(
            and_(
                WasteTrackingEntry.location_id == location_id,
                WasteTrackingEntry.recorded_at >= datetime.combine(start_date, datetime.min.time()),
                WasteTrackingEntry.recorded_at <= datetime.combine(end_date, datetime.max.time()),
                WasteTrackingEntry.station.isnot(None),
            )
        ).group_by(WasteTrackingEntry.station)

        station_result = self.db.execute(station_query)
        by_station = {row.station: row.weight or Decimal("0") for row in station_result.all()}

        # Calculate trend vs previous period
        period_length = (end_date - start_date).days
        prev_start = start_date - timedelta(days=period_length)
        prev_end = start_date - timedelta(days=1)

        prev_query = select(
            func.sum(WasteTrackingEntry.weight_kg).label("total_weight"),
        ).where(
            and_(
                WasteTrackingEntry.location_id == location_id,
                WasteTrackingEntry.recorded_at >= datetime.combine(prev_start, datetime.min.time()),
                WasteTrackingEntry.recorded_at <= datetime.combine(prev_end, datetime.max.time()),
            )
        )
        prev_result = self.db.execute(prev_query)
        prev_totals = prev_result.first()

        trend = None
        if prev_totals.total_weight and totals.total_weight:
            trend = float((totals.total_weight - prev_totals.total_weight) / prev_totals.total_weight * 100)

        return {
            "total_waste_kg": totals.total_weight or Decimal("0"),
            "total_cost": totals.total_cost or Decimal("0"),
            "total_carbon_kg": totals.total_carbon,
            "by_category": by_category,
            "by_station": by_station,
            "trend_vs_previous": trend,
        }

    def create_forecast(
        self,
        location_id: int,
        forecast_date: date,
        predicted_waste_kg: Decimal,
        predicted_cost: Decimal,
        confidence_interval: Optional[Dict[str, Any]] = None,
    ) -> WasteForecast:
        """Create a waste forecast."""
        forecast = WasteForecast(
            location_id=location_id,
            forecast_date=forecast_date,
            predicted_waste_kg=predicted_waste_kg,
            predicted_cost=predicted_cost,
            confidence_interval=confidence_interval,
        )
        self.db.add(forecast)
        self.db.commit()
        self.db.refresh(forecast)
        return forecast

    def generate_forecast(
        self,
        location_id: int,
        forecast_date: date,
    ) -> WasteForecast:
        """Generate AI-based waste forecast based on historical data."""
        # Get historical data for same day of week
        day_of_week = forecast_date.weekday()

        # Query without stddev for SQLite compatibility
        query = select(
            func.avg(WasteTrackingEntry.weight_kg).label("avg_weight"),
            func.avg(WasteTrackingEntry.cost_value).label("avg_cost"),
        ).where(
            and_(
                WasteTrackingEntry.location_id == location_id,
                func.extract("dow", WasteTrackingEntry.recorded_at) == day_of_week,
            )
        )

        result = self.db.execute(query)
        stats = result.first()

        predicted_waste = Decimal(str(stats.avg_weight or 10))
        predicted_cost = Decimal(str(stats.avg_cost or 50))

        # Calculate stddev manually for SQLite compatibility
        confidence_interval = None
        try:
            # Get all weights to calculate stddev in Python
            weights_query = select(WasteTrackingEntry.weight_kg).where(
                and_(
                    WasteTrackingEntry.location_id == location_id,
                    func.extract("dow", WasteTrackingEntry.recorded_at) == day_of_week,
                )
            )
            weights_result = self.db.execute(weights_query)
            weights = [float(row[0]) for row in weights_result.all() if row[0] is not None]

            if len(weights) > 1:
                import statistics
                stddev = statistics.stdev(weights)
                confidence_interval = {
                    "lower": float(predicted_waste) - 1.96 * stddev,
                    "upper": float(predicted_waste) + 1.96 * stddev,
                    "confidence_level": 0.95,
                }
        except Exception as e:
            logger.warning(f"Failed to calculate confidence interval for waste forecast at location {location_id}: {e}")

        return self.create_forecast(
            location_id=location_id,
            forecast_date=forecast_date,
            predicted_waste_kg=predicted_waste,
            predicted_cost=predicted_cost,
            confidence_interval=confidence_interval,
        )

    def analyze_image(
        self,
        entry_id: int,
        image_url: str,
    ) -> Dict[str, Any]:
        """Analyze waste image using AI (placeholder for actual AI integration)."""
        entry = self.db.get(WasteTrackingEntry, entry_id)
        if not entry:
            raise ValueError(f"Entry {entry_id} not found")

        # Placeholder AI detection - in production, integrate with vision AI
        detected_item = "food_waste"
        confidence = 0.85

        entry.image_url = image_url
        entry.ai_detected_item = detected_item
        entry.ai_confidence = confidence
        entry.ai_verified = False

        self.db.commit()

        return {
            "detected_item": detected_item,
            "confidence": confidence,
            "category_suggestion": WasteCategory.OTHER.value,
        }

    def verify_ai_detection(
        self,
        entry_id: int,
        verified: bool,
        corrected_item: Optional[str] = None,
    ) -> WasteTrackingEntry:
        """Verify or correct AI detection."""
        entry = self.db.get(WasteTrackingEntry, entry_id)
        if not entry:
            raise ValueError(f"Entry {entry_id} not found")

        entry.ai_verified = verified
        if corrected_item:
            entry.ai_detected_item = corrected_item

        self.db.commit()
        self.db.refresh(entry)
        return entry

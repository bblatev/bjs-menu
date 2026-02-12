"""
Demand Forecasting Service
Provides iiko-like AI-driven demand forecasting and auto-planning

Features:
- ML-based demand forecasting
- Weather and event integration
- Auto-schedule generation
- Auto-purchase plan generation
- Production planning
"""

from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc, extract
from datetime import datetime, timedelta, date
from decimal import Decimal
import logging
import math
import statistics

from app.models import Order, OrderItem, MenuItem, StaffUser
from app.models.gap_features_models import (
    AIDemandForecast as DemandForecast,
    AIItemDemandForecast as ItemDemandForecast,
    ScheduleProposal, PurchasePlanProposal
)

logger = logging.getLogger(__name__)


class DailyForecast:
    """Forecast for a single day"""
    def __init__(
        self,
        forecast_date: date,
        expected_covers: int,
        expected_revenue: float,
        confidence_low: float,
        confidence_high: float,
        factors: List[str]
    ):
        self.date = forecast_date
        self.expected_covers = expected_covers
        self.expected_revenue = expected_revenue
        self.confidence_low = confidence_low
        self.confidence_high = confidence_high
        self.factors = factors

    def to_dict(self) -> Dict:
        return {
            "date": self.date.isoformat(),
            "expected_covers": self.expected_covers,
            "expected_revenue": self.expected_revenue,
            "confidence_low": self.confidence_low,
            "confidence_high": self.confidence_high,
            "factors": self.factors
        }


class ItemForecast:
    """Forecast for a menu item"""
    def __init__(
        self,
        item_id: int,
        item_name: str,
        expected_quantity: int,
        confidence_low: int,
        confidence_high: int
    ):
        self.item_id = item_id
        self.item_name = item_name
        self.expected_quantity = expected_quantity
        self.confidence_low = confidence_low
        self.confidence_high = confidence_high

    def to_dict(self) -> Dict:
        return {
            "item_id": self.item_id,
            "item_name": self.item_name,
            "expected_quantity": self.expected_quantity,
            "confidence_low": self.confidence_low,
            "confidence_high": self.confidence_high
        }


class DemandForecastResult:
    """Complete forecast result"""
    def __init__(
        self,
        daily_forecasts: List[DailyForecast],
        item_forecasts: List[ItemForecast],
        confidence_level: float,
        model_version: str
    ):
        self.daily_forecasts = daily_forecasts
        self.item_forecasts = item_forecasts
        self.confidence_level = confidence_level
        self.model_version = model_version

    def to_dict(self) -> Dict:
        return {
            "daily_forecasts": [f.to_dict() for f in self.daily_forecasts],
            "item_forecasts": [f.to_dict() for f in self.item_forecasts],
            "confidence_level": self.confidence_level,
            "model_version": self.model_version
        }


class ShiftAssignment:
    """A shift assignment in a schedule"""
    def __init__(
        self,
        staff_id: int,
        staff_name: str,
        shift_date: date,
        start_time: str,
        end_time: str,
        role: str,
        hours: float
    ):
        self.staff_id = staff_id
        self.staff_name = staff_name
        self.date = shift_date
        self.start_time = start_time
        self.end_time = end_time
        self.role = role
        self.hours = hours

    def to_dict(self) -> Dict:
        return {
            "staff_id": self.staff_id,
            "staff_name": self.staff_name,
            "date": self.date.isoformat(),
            "start_time": self.start_time,
            "end_time": self.end_time,
            "role": self.role,
            "hours": self.hours
        }


class ScheduleProposalResult:
    """Result of auto-schedule generation"""
    def __init__(
        self,
        shifts: List[ShiftAssignment],
        total_hours: float,
        estimated_cost: float,
        coverage_score: float
    ):
        self.shifts = shifts
        self.total_hours = total_hours
        self.estimated_cost = estimated_cost
        self.coverage_score = coverage_score

    def to_dict(self) -> Dict:
        return {
            "shifts": [s.to_dict() for s in self.shifts],
            "total_hours": self.total_hours,
            "estimated_cost": self.estimated_cost,
            "coverage_score": self.coverage_score
        }


class PurchaseOrderSuggestion:
    """Suggested purchase order"""
    def __init__(
        self,
        supplier_id: Optional[int],
        supplier_name: str,
        items: List[Dict],
        total_cost: float,
        delivery_date: date
    ):
        self.supplier_id = supplier_id
        self.supplier_name = supplier_name
        self.items = items
        self.total_cost = total_cost
        self.delivery_date = delivery_date

    def to_dict(self) -> Dict:
        return {
            "supplier_id": self.supplier_id,
            "supplier_name": self.supplier_name,
            "items": self.items,
            "total_cost": self.total_cost,
            "delivery_date": self.delivery_date.isoformat()
        }


class DemandForecastingService:
    """
    AI-driven demand forecasting and auto-planning
    Competitor to iiko's forecasting features
    """

    # Day-of-week multipliers (empirical averages)
    DAY_MULTIPLIERS = {
        0: 0.85,   # Monday
        1: 0.90,   # Tuesday
        2: 0.95,   # Wednesday
        3: 1.00,   # Thursday
        4: 1.20,   # Friday
        5: 1.30,   # Saturday
        6: 1.10    # Sunday
    }

    # Weather impact on sales (ski resort specific)
    WEATHER_MULTIPLIERS = {
        "snow": 1.15,      # Good ski weather
        "clear": 1.10,     # Nice day
        "cloudy": 1.00,    # Neutral
        "rain": 0.85,      # Bad weather
        "storm": 0.70      # Very bad
    }

    def __init__(self, db: Session):
        self.db = db

    async def forecast_demand(
        self,
        venue_id: int,
        forecast_days: int = 7
    ) -> DemandForecastResult:
        """
        Generate demand forecast for next N days

        Uses:
        - Historical sales patterns
        - Day-of-week adjustments
        - Weather data (if available)
        - Local events (if available)
        - Trend analysis
        """
        # Get historical data
        history = await self._get_sales_history(venue_id, days=90)

        if not history:
            # Not enough data, return basic forecast
            return self._generate_basic_forecast(forecast_days)

        # Calculate baseline metrics
        baseline = self._calculate_baseline(history)

        # Generate daily forecasts
        daily_forecasts = []
        today = date.today()

        for i in range(1, forecast_days + 1):
            forecast_date = today + timedelta(days=i)
            forecast = await self._forecast_day(
                venue_id, forecast_date, baseline, history
            )
            daily_forecasts.append(forecast)

        # Generate item-level forecasts
        item_forecasts = await self._forecast_by_item(venue_id, daily_forecasts)

        return DemandForecastResult(
            daily_forecasts=daily_forecasts,
            item_forecasts=item_forecasts,
            confidence_level=self._calculate_confidence(history),
            model_version="v1.0-statistical"
        )

    async def _get_sales_history(
        self,
        venue_id: int,
        days: int = 90
    ) -> List[Dict]:
        """Get historical sales data"""
        start_date = date.today() - timedelta(days=days)

        # Daily aggregates
        daily_data = self.db.query(
            func.date(Order.created_at).label('order_date'),
            func.count(Order.id).label('order_count'),
            func.sum(Order.total).label('revenue'),
            func.sum(Order.guest_count).label('guests')
        ).filter(
            Order.venue_id == venue_id,
            func.date(Order.created_at) >= start_date,
            Order.status != 'cancelled'
        ).group_by(
            func.date(Order.created_at)
        ).order_by(
            func.date(Order.created_at)
        ).all()

        return [
            {
                "date": d.order_date,
                "orders": d.order_count,
                "revenue": float(d.revenue or 0),
                "guests": d.guests or 0,
                "day_of_week": d.order_date.weekday()
            }
            for d in daily_data
        ]

    def _calculate_baseline(self, history: List[Dict]) -> Dict:
        """Calculate baseline metrics from history"""
        if not history:
            return {"avg_revenue": 0, "avg_orders": 0, "avg_guests": 0, "std_dev": 0}

        revenues = [h["revenue"] for h in history if h["revenue"] > 0]
        orders = [h["orders"] for h in history if h["orders"] > 0]
        guests = [h["guests"] for h in history if h["guests"] > 0]

        avg_revenue = statistics.mean(revenues) if revenues else 0
        avg_orders = statistics.mean(orders) if orders else 0
        avg_guests = statistics.mean(guests) if guests else 0
        std_dev = statistics.stdev(revenues) if len(revenues) > 1 else avg_revenue * 0.2

        # Calculate day-of-week averages
        dow_revenue = {}
        for day in range(7):
            day_revenues = [h["revenue"] for h in history if h["day_of_week"] == day and h["revenue"] > 0]
            dow_revenue[day] = statistics.mean(day_revenues) if day_revenues else avg_revenue

        return {
            "avg_revenue": avg_revenue,
            "avg_orders": avg_orders,
            "avg_guests": avg_guests,
            "std_dev": std_dev,
            "dow_revenue": dow_revenue
        }

    async def _forecast_day(
        self,
        venue_id: int,
        forecast_date: date,
        baseline: Dict,
        history: List[Dict]
    ) -> DailyForecast:
        """Forecast for a specific day"""
        day_of_week = forecast_date.weekday()

        # Get day-of-week specific baseline
        dow_revenue = baseline["dow_revenue"].get(day_of_week, baseline["avg_revenue"])

        # Apply trend adjustment (last 4 weeks trend)
        trend_multiplier = self._calculate_trend(history, day_of_week)

        # Weather adjustment (placeholder - would integrate real weather API)
        weather_multiplier = 1.0
        weather_desc = "normal conditions"

        # Calculate expected values
        expected_revenue = dow_revenue * trend_multiplier * weather_multiplier

        # Calculate confidence interval
        std_dev = baseline["std_dev"]
        confidence_low = max(0, expected_revenue - 1.96 * std_dev)
        confidence_high = expected_revenue + 1.96 * std_dev

        # Estimate covers from revenue
        avg_ticket = baseline["avg_revenue"] / baseline["avg_orders"] if baseline["avg_orders"] > 0 else 30
        expected_covers = int(expected_revenue / avg_ticket) if avg_ticket > 0 else 0

        # Build factors list
        factors = [
            f"Day: {['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][day_of_week]}",
            f"Trend: {'↑' if trend_multiplier > 1 else '↓'} {abs((trend_multiplier - 1) * 100):.1f}%",
            f"Weather: {weather_desc}"
        ]

        return DailyForecast(
            forecast_date=forecast_date,
            expected_covers=expected_covers,
            expected_revenue=round(expected_revenue, 2),
            confidence_low=round(confidence_low, 2),
            confidence_high=round(confidence_high, 2),
            factors=factors
        )

    def _calculate_trend(self, history: List[Dict], day_of_week: int) -> float:
        """Calculate trend for specific day of week over last 4 weeks"""
        if len(history) < 14:
            return 1.0

        # Get last 4 occurrences of this day of week
        same_day_data = [h for h in history if h["day_of_week"] == day_of_week][-4:]

        if len(same_day_data) < 2:
            return 1.0

        # Simple linear trend
        revenues = [h["revenue"] for h in same_day_data]
        if revenues[0] == 0:
            return 1.0

        # Week-over-week average change
        changes = []
        for i in range(1, len(revenues)):
            if revenues[i-1] > 0:
                changes.append(revenues[i] / revenues[i-1])

        if changes:
            return statistics.mean(changes)
        return 1.0

    def _calculate_confidence(self, history: List[Dict]) -> float:
        """Calculate confidence level based on data availability"""
        if len(history) >= 60:
            return 0.90
        elif len(history) >= 30:
            return 0.80
        elif len(history) >= 14:
            return 0.70
        elif len(history) >= 7:
            return 0.60
        else:
            return 0.50

    async def _forecast_by_item(
        self,
        venue_id: int,
        daily_forecasts: List[DailyForecast]
    ) -> List[ItemForecast]:
        """Generate item-level forecasts"""
        # Get item sales distribution
        thirty_days_ago = date.today() - timedelta(days=30)

        item_sales = self.db.query(
            MenuItem.id,
            MenuItem.name,
            func.sum(OrderItem.quantity).label('total_qty'),
            func.count(func.distinct(Order.id)).label('order_count')
        ).join(
            OrderItem, MenuItem.id == OrderItem.menu_item_id
        ).join(
            Order, OrderItem.order_id == Order.id
        ).filter(
            Order.venue_id == venue_id,
            Order.created_at >= thirty_days_ago,
            Order.status != 'cancelled'
        ).group_by(
            MenuItem.id, MenuItem.name
        ).all()

        if not item_sales:
            return []

        # Calculate total forecasted covers
        total_covers = sum(f.expected_covers for f in daily_forecasts)

        # Get total historical covers for the same period
        total_historical_orders = sum(i.order_count for i in item_sales)

        if total_historical_orders == 0:
            return []

        # Scale factor
        scale = total_covers / total_historical_orders if total_historical_orders > 0 else 1

        forecasts = []
        for item in item_sales[:20]:  # Top 20 items
            name = item.name.get('en', item.name.get('bg', 'Unknown')) if isinstance(item.name, dict) else str(item.name)
            expected = int(item.total_qty * scale / 30 * len(daily_forecasts))

            forecasts.append(ItemForecast(
                item_id=item.id,
                item_name=name,
                expected_quantity=expected,
                confidence_low=max(0, int(expected * 0.7)),
                confidence_high=int(expected * 1.3)
            ))

        return forecasts

    def _generate_basic_forecast(self, days: int) -> DemandForecastResult:
        """Generate basic forecast when insufficient data"""
        today = date.today()
        forecasts = []

        for i in range(1, days + 1):
            forecast_date = today + timedelta(days=i)
            multiplier = self.DAY_MULTIPLIERS.get(forecast_date.weekday(), 1.0)
            base_revenue = 1000  # Default estimate

            forecasts.append(DailyForecast(
                forecast_date=forecast_date,
                expected_covers=int(30 * multiplier),
                expected_revenue=base_revenue * multiplier,
                confidence_low=base_revenue * multiplier * 0.5,
                confidence_high=base_revenue * multiplier * 1.5,
                factors=["Limited historical data - using defaults"]
            ))

        return DemandForecastResult(
            daily_forecasts=forecasts,
            item_forecasts=[],
            confidence_level=0.40,
            model_version="v1.0-default"
        )

    async def auto_generate_schedule(
        self,
        venue_id: int,
        week_start: date
    ) -> ScheduleProposalResult:
        """
        Auto-generate staff schedule based on demand forecast

        Uses:
        - Demand forecast for the week
        - Staff availability (if available)
        - Labor rules and constraints
        """
        # Get demand forecast for the week
        week_end = week_start + timedelta(days=6)
        forecast = await self.forecast_demand(venue_id, 7)

        # Get available staff
        staff = self.db.query(StaffUser).filter(
            StaffUser.venue_id == venue_id,
            StaffUser.active == True
        ).all()

        if not staff:
            return ScheduleProposalResult(
                shifts=[],
                total_hours=0,
                estimated_cost=0,
                coverage_score=0
            )

        # Calculate required labor hours per day
        shifts = []
        total_hours = 0

        for i, daily in enumerate(forecast.daily_forecasts):
            shift_date = week_start + timedelta(days=i)

            # Estimate required staff based on covers
            # Rule of thumb: 1 server per 20 covers per shift
            expected_covers = daily.expected_covers
            required_servers = max(2, math.ceil(expected_covers / 20))

            # Kitchen staff: 1 per 30 covers
            required_kitchen = max(1, math.ceil(expected_covers / 30))

            # Assign staff (round-robin for simplicity)
            servers = [s for s in staff if s.role.value in ['waiter', 'manager', 'admin']]
            kitchen = [s for s in staff if s.role.value in ['kitchen', 'bar']]

            # Morning shift (11:00 - 17:00)
            for j in range(min(required_servers, len(servers))):
                server = servers[j % len(servers)]
                shifts.append(ShiftAssignment(
                    staff_id=server.id,
                    staff_name=server.full_name,
                    shift_date=shift_date,
                    start_time="11:00",
                    end_time="17:00",
                    role=server.role.value,
                    hours=6.0
                ))
                total_hours += 6.0

            # Evening shift (17:00 - 23:00)
            for j in range(min(required_servers, len(servers))):
                server = servers[(j + required_servers) % len(servers)]
                shifts.append(ShiftAssignment(
                    staff_id=server.id,
                    staff_name=server.full_name,
                    shift_date=shift_date,
                    start_time="17:00",
                    end_time="23:00",
                    role=server.role.value,
                    hours=6.0
                ))
                total_hours += 6.0

            # Kitchen shifts
            for j in range(min(required_kitchen, len(kitchen))):
                cook = kitchen[j % len(kitchen)]
                shifts.append(ShiftAssignment(
                    staff_id=cook.id,
                    staff_name=cook.full_name,
                    shift_date=shift_date,
                    start_time="10:00",
                    end_time="22:00",
                    role=cook.role.value,
                    hours=12.0
                ))
                total_hours += 12.0

        # Estimate cost (assumes average hourly rate)
        avg_hourly = 15.0  # BGN
        estimated_cost = total_hours * avg_hourly

        # Calculate coverage score (simplified)
        coverage_score = min(100, (len(shifts) / (len(forecast.daily_forecasts) * 4)) * 100)

        return ScheduleProposalResult(
            shifts=shifts,
            total_hours=total_hours,
            estimated_cost=estimated_cost,
            coverage_score=coverage_score
        )

    async def auto_generate_purchase_plan(
        self,
        venue_id: int,
        forecast_days: int = 7
    ) -> List[PurchaseOrderSuggestion]:
        """
        Auto-generate purchase orders based on demand forecast

        Uses:
        - Item demand forecast
        - Current inventory levels (if available)
        - Par levels and reorder points
        - Supplier lead times
        """
        # Get demand forecast
        forecast = await self.forecast_demand(venue_id, forecast_days)

        if not forecast.item_forecasts:
            return []

        # Group items by supplier (simplified - assumes single supplier)
        purchase_items = []

        for item_forecast in forecast.item_forecasts:
            # Get item details
            item = self.db.query(MenuItem).filter(
                MenuItem.id == item_forecast.item_id
            ).first()

            if not item:
                continue

            # Calculate required quantity (forecast + safety stock)
            required = item_forecast.expected_quantity
            safety_stock = int(required * 0.2)  # 20% safety margin
            total_needed = required + safety_stock

            # Get estimated cost
            unit_cost = item.cost if item.cost else item.price * 0.3

            purchase_items.append({
                "item_id": item.id,
                "name": item_forecast.item_name,
                "quantity": total_needed,
                "unit_cost": float(unit_cost),
                "total_cost": float(unit_cost * total_needed)
            })

        if not purchase_items:
            return []

        # Create single PO suggestion (in production, would group by supplier)
        total_cost = sum(p["total_cost"] for p in purchase_items)
        delivery_date = date.today() + timedelta(days=2)  # Assume 2-day lead time

        return [
            PurchaseOrderSuggestion(
                supplier_id=None,
                supplier_name="Default Supplier",
                items=purchase_items,
                total_cost=total_cost,
                delivery_date=delivery_date
            )
        ]

    async def save_forecast(
        self,
        venue_id: int,
        forecast_result: DemandForecastResult
    ) -> List[DemandForecast]:
        """Save forecast to database"""
        saved = []

        for daily in forecast_result.daily_forecasts:
            db_forecast = DemandForecast(
                venue_id=venue_id,
                forecast_date=daily.date,
                forecast_type="daily",
                expected_covers=daily.expected_covers,
                expected_revenue=Decimal(str(daily.expected_revenue)),
                confidence_low=Decimal(str(daily.confidence_low)),
                confidence_high=Decimal(str(daily.confidence_high)),
                confidence_level=Decimal(str(forecast_result.confidence_level)),
                factors=daily.factors,
                model_version=forecast_result.model_version
            )
            self.db.add(db_forecast)
            self.db.flush()

            # Save item forecasts
            for item in forecast_result.item_forecasts:
                item_forecast = ItemDemandForecast(
                    forecast_id=db_forecast.id,
                    menu_item_id=item.item_id,
                    expected_quantity=item.expected_quantity,
                    confidence_low=item.confidence_low,
                    confidence_high=item.confidence_high
                )
                self.db.add(item_forecast)

            saved.append(db_forecast)

        self.db.commit()
        return saved

    async def save_schedule_proposal(
        self,
        venue_id: int,
        week_start: date,
        schedule: ScheduleProposalResult
    ) -> ScheduleProposal:
        """Save schedule proposal to database"""
        proposal = ScheduleProposal(
            venue_id=venue_id,
            week_start=week_start,
            week_end=week_start + timedelta(days=6),
            total_labor_hours=Decimal(str(schedule.total_hours)),
            estimated_labor_cost=Decimal(str(schedule.estimated_cost)),
            coverage_score=Decimal(str(schedule.coverage_score)),
            shifts_data=[s.to_dict() for s in schedule.shifts]
        )

        self.db.add(proposal)
        self.db.commit()
        self.db.refresh(proposal)

        return proposal

    async def save_purchase_plan(
        self,
        venue_id: int,
        purchase_orders: List[PurchaseOrderSuggestion]
    ) -> PurchasePlanProposal:
        """Save purchase plan proposal to database"""
        total_cost = sum(po.total_cost for po in purchase_orders)

        proposal = PurchasePlanProposal(
            venue_id=venue_id,
            plan_date=date.today(),
            total_cost=Decimal(str(total_cost)),
            purchase_orders=[po.to_dict() for po in purchase_orders]
        )

        self.db.add(proposal)
        self.db.commit()
        self.db.refresh(proposal)

        return proposal

    async def update_forecast_actuals(
        self,
        venue_id: int,
        forecast_date: date
    ):
        """Update forecast with actual values after the day completes"""
        # Get actual data
        actuals = self.db.query(
            func.count(Order.id).label('orders'),
            func.sum(Order.total).label('revenue'),
            func.sum(Order.guest_count).label('guests')
        ).filter(
            Order.venue_id == venue_id,
            func.date(Order.created_at) == forecast_date,
            Order.status != 'cancelled'
        ).first()

        # Update forecast record
        forecast = self.db.query(DemandForecast).filter(
            DemandForecast.venue_id == venue_id,
            DemandForecast.forecast_date == forecast_date
        ).first()

        if forecast:
            forecast.actual_covers = actuals.guests or 0
            forecast.actual_revenue = Decimal(str(actuals.revenue or 0))

            # Calculate accuracy
            if forecast.expected_revenue > 0:
                actual = float(actuals.revenue or 0)
                expected = float(forecast.expected_revenue)
                accuracy = 1 - abs(actual - expected) / expected
                forecast.accuracy_score = Decimal(str(max(0, min(1, accuracy))))

            self.db.commit()

    async def get_forecast_accuracy(
        self,
        venue_id: int,
        days: int = 30
    ) -> Dict:
        """Calculate forecast accuracy metrics"""
        start_date = date.today() - timedelta(days=days)

        forecasts = self.db.query(DemandForecast).filter(
            DemandForecast.venue_id == venue_id,
            DemandForecast.forecast_date >= start_date,
            DemandForecast.actual_revenue.isnot(None)
        ).all()

        if not forecasts:
            return {
                "sample_size": 0,
                "avg_accuracy": None,
                "mape": None,
                "within_confidence": None
            }

        accuracies = []
        within_ci = 0

        for f in forecasts:
            if f.expected_revenue > 0:
                actual = float(f.actual_revenue or 0)
                expected = float(f.expected_revenue)
                low = float(f.confidence_low or 0)
                high = float(f.confidence_high or expected * 2)

                accuracy = 1 - abs(actual - expected) / expected
                accuracies.append(max(0, accuracy))

                if low <= actual <= high:
                    within_ci += 1

        avg_accuracy = statistics.mean(accuracies) if accuracies else 0
        mape = 1 - avg_accuracy  # Mean Absolute Percentage Error

        return {
            "sample_size": len(forecasts),
            "avg_accuracy": round(avg_accuracy * 100, 1),
            "mape": round(mape * 100, 1),
            "within_confidence": round((within_ci / len(forecasts)) * 100, 1) if forecasts else 0
        }

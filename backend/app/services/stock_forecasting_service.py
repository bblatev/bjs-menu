"""Predictive Stock Forecasting Service.

Uses historical sales data (StockMovement with reason=SALE) to predict
future demand and generate automated reorder suggestions.

Algorithms:
1. Moving average (7-day, 14-day, 30-day)
2. Day-of-week pattern detection (weekends vs weekdays)
3. Trend detection (growing vs declining items)
4. Safety stock calculation (service level based)
5. EOQ (Economic Order Quantity) calculation
"""

from __future__ import annotations

import logging
import math
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.stock import StockMovement, StockOnHand

logger = logging.getLogger(__name__)

# Z-scores for common service levels (one-tailed normal distribution)
_Z_SCORES: Dict[float, float] = {
    0.80: 0.842,
    0.85: 1.036,
    0.90: 1.282,
    0.95: 1.645,
    0.97: 1.881,
    0.99: 2.326,
}


class StockForecastingService:
    """Demand forecasting and reorder optimization."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def forecast_demand(
        self,
        product_id: int,
        location_id: int,
        days_ahead: int = 7,
    ) -> Dict[str, Any]:
        """Return a daily demand forecast for *days_ahead* days.

        Uses weighted moving averages and day-of-week patterns to project
        future daily usage.
        """
        daily_usage = self._get_daily_usage(product_id, location_id, lookback_days=90)

        if not daily_usage:
            return {
                "product_id": product_id,
                "location_id": location_id,
                "days_ahead": days_ahead,
                "forecast": [],
                "avg_daily_demand": 0,
                "confidence": "no_data",
            }

        dow_patterns = self._compute_dow_patterns(daily_usage)
        ma_7 = self._moving_average(daily_usage, window=7)
        ma_14 = self._moving_average(daily_usage, window=14)
        ma_30 = self._moving_average(daily_usage, window=30)

        # Weighted average of MAs (more weight on recent)
        overall_avg = (ma_7 * 0.5 + ma_14 * 0.3 + ma_30 * 0.2) if ma_30 > 0 else ma_7

        today = date.today()
        forecast: List[Dict[str, Any]] = []
        total_forecast_qty = 0.0

        for i in range(1, days_ahead + 1):
            forecast_date = today + timedelta(days=i)
            dow = forecast_date.weekday()  # 0=Monday
            dow_factor = dow_patterns.get(dow, 1.0)
            daily_qty = round(overall_avg * dow_factor, 2)
            total_forecast_qty += daily_qty
            forecast.append({
                "date": forecast_date.isoformat(),
                "day_of_week": forecast_date.strftime("%A"),
                "predicted_qty": daily_qty,
                "dow_factor": round(dow_factor, 3),
            })

        data_days = len(daily_usage)
        confidence = "high" if data_days >= 60 else ("medium" if data_days >= 14 else "low")

        return {
            "product_id": product_id,
            "location_id": location_id,
            "days_ahead": days_ahead,
            "forecast": forecast,
            "total_forecast_qty": round(total_forecast_qty, 2),
            "avg_daily_demand": round(overall_avg, 2),
            "moving_averages": {
                "ma_7": round(ma_7, 2),
                "ma_14": round(ma_14, 2),
                "ma_30": round(ma_30, 2),
            },
            "data_days": data_days,
            "confidence": confidence,
        }

    def get_day_of_week_patterns(
        self, product_id: int, location_id: int,
    ) -> Dict[str, Any]:
        """Return usage patterns grouped by day of week."""
        daily_usage = self._get_daily_usage(product_id, location_id, lookback_days=90)
        dow_patterns = self._compute_dow_patterns(daily_usage)

        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        # Build per-day stats
        dow_buckets: Dict[int, List[float]] = defaultdict(list)
        for d, qty in daily_usage.items():
            dow_buckets[d.weekday()].append(qty)

        patterns: List[Dict[str, Any]] = []
        for dow_idx in range(7):
            vals = dow_buckets.get(dow_idx, [])
            avg_val = sum(vals) / len(vals) if vals else 0
            patterns.append({
                "day_of_week": dow_idx,
                "day_name": day_names[dow_idx],
                "avg_usage": round(avg_val, 2),
                "factor": round(dow_patterns.get(dow_idx, 1.0), 3),
                "sample_count": len(vals),
                "max_usage": round(max(vals), 2) if vals else 0,
                "min_usage": round(min(vals), 2) if vals else 0,
            })

        weekend_avg = sum(p["avg_usage"] for p in patterns if p["day_of_week"] >= 5) / 2 if patterns else 0
        weekday_avg = sum(p["avg_usage"] for p in patterns if p["day_of_week"] < 5) / 5 if patterns else 0

        return {
            "product_id": product_id,
            "location_id": location_id,
            "patterns": patterns,
            "weekend_avg": round(weekend_avg, 2),
            "weekday_avg": round(weekday_avg, 2),
            "weekend_weekday_ratio": round(weekend_avg / weekday_avg, 2) if weekday_avg > 0 else 0,
        }

    def calculate_eoq(
        self,
        product_id: int,
        location_id: int,
        ordering_cost: float = 25.0,
        holding_cost_pct: float = 0.25,
    ) -> Dict[str, Any]:
        """Economic Order Quantity calculation.

        EOQ = sqrt(2 * D * S / H)
        where D = annual demand, S = ordering cost per order,
        H = holding cost per unit per year.
        """
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return {"error": f"Product {product_id} not found"}

        daily_usage = self._get_daily_usage(product_id, location_id, lookback_days=90)
        avg_daily = self._moving_average(daily_usage, window=30)
        annual_demand = avg_daily * 365

        unit_cost = float(product.cost_price) if product.cost_price else 1.0
        holding_cost_per_unit = unit_cost * holding_cost_pct

        if annual_demand <= 0 or holding_cost_per_unit <= 0:
            return {
                "product_id": product_id,
                "location_id": location_id,
                "eoq": 0,
                "reason": "insufficient_data",
                "annual_demand": round(annual_demand, 2),
            }

        eoq = math.sqrt((2 * annual_demand * ordering_cost) / holding_cost_per_unit)
        orders_per_year = annual_demand / eoq if eoq > 0 else 0
        order_interval_days = 365 / orders_per_year if orders_per_year > 0 else 0

        return {
            "product_id": product_id,
            "product_name": product.name,
            "location_id": location_id,
            "eoq": round(eoq, 1),
            "annual_demand": round(annual_demand, 1),
            "avg_daily_demand": round(avg_daily, 2),
            "unit_cost": unit_cost,
            "ordering_cost": ordering_cost,
            "holding_cost_pct": holding_cost_pct,
            "holding_cost_per_unit": round(holding_cost_per_unit, 2),
            "orders_per_year": round(orders_per_year, 1),
            "order_interval_days": round(order_interval_days, 1),
            "total_annual_cost": round(
                (annual_demand * unit_cost)
                + (orders_per_year * ordering_cost)
                + (eoq / 2 * holding_cost_per_unit),
                2,
            ),
        }

    def calculate_safety_stock(
        self,
        product_id: int,
        location_id: int,
        service_level: float = 0.95,
    ) -> Dict[str, Any]:
        """Safety stock calculation for a desired service level.

        SS = Z * sigma_d * sqrt(L) + Z * d_avg * sigma_L
        Simplified (assuming deterministic lead time):
        SS = Z * sigma_d * sqrt(L)
        """
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return {"error": f"Product {product_id} not found"}

        daily_usage = self._get_daily_usage(product_id, location_id, lookback_days=90)
        avg_daily = self._moving_average(daily_usage, window=30)
        std_daily = self._std_deviation(daily_usage)
        lead_time = product.lead_time_days or 1

        z_score = _Z_SCORES.get(service_level)
        if z_score is None:
            # Find the closest service level
            closest = min(_Z_SCORES.keys(), key=lambda x: abs(x - service_level))
            z_score = _Z_SCORES[closest]

        safety_stock = z_score * std_daily * math.sqrt(lead_time)
        reorder_point = (avg_daily * lead_time) + safety_stock

        return {
            "product_id": product_id,
            "product_name": product.name,
            "location_id": location_id,
            "service_level": service_level,
            "z_score": round(z_score, 3),
            "avg_daily_demand": round(avg_daily, 2),
            "std_daily_demand": round(std_daily, 2),
            "lead_time_days": lead_time,
            "safety_stock": round(safety_stock, 1),
            "reorder_point": round(reorder_point, 1),
            "current_stock": float(
                self._get_current_stock(product_id, location_id)
            ),
        }

    def generate_reorder_suggestions(
        self, location_id: int
    ) -> List[Dict[str, Any]]:
        """For every active product at *location_id*, compute a reorder
        suggestion if current stock is at or below the reorder point."""
        products = (
            self.db.query(Product)
            .filter(Product.active == True)  # noqa: E712
            .all()
        )

        suggestions: List[Dict[str, Any]] = []
        for product in products:
            current = float(self._get_current_stock(product.id, location_id))

            daily_usage = self._get_daily_usage(product.id, location_id, lookback_days=60)
            avg_daily = self._moving_average(daily_usage, window=14)
            if avg_daily <= 0:
                continue

            std_daily = self._std_deviation(daily_usage)
            lead_time = product.lead_time_days or 1
            z_score = _Z_SCORES.get(0.95, 1.645)

            safety_stock = z_score * std_daily * math.sqrt(lead_time)
            reorder_point = (avg_daily * lead_time) + safety_stock

            if current <= reorder_point:
                # How much to order: bring up to par or target stock
                target = float(product.target_stock) if product.target_stock else reorder_point * 2
                order_qty = max(0, target - current)

                days_until_stockout = current / avg_daily if avg_daily > 0 else 999
                urgency = "critical" if days_until_stockout <= 1 else (
                    "high" if days_until_stockout <= lead_time else "normal"
                )

                suggestions.append({
                    "product_id": product.id,
                    "product_name": product.name,
                    "supplier_id": product.supplier_id,
                    "current_stock": current,
                    "reorder_point": round(reorder_point, 1),
                    "safety_stock": round(safety_stock, 1),
                    "suggested_order_qty": round(order_qty, 1),
                    "avg_daily_demand": round(avg_daily, 2),
                    "lead_time_days": lead_time,
                    "days_until_stockout": round(days_until_stockout, 1),
                    "urgency": urgency,
                    "unit": product.unit,
                })

        # Sort by urgency: critical first, then high, then normal
        urgency_order = {"critical": 0, "high": 1, "normal": 2}
        suggestions.sort(key=lambda s: (urgency_order.get(s["urgency"], 3), s["days_until_stockout"]))

        return suggestions

    def get_demand_trends(
        self,
        location_id: int,
        top_n: int = 20,
    ) -> Dict[str, Any]:
        """Identify products trending up vs down by comparing recent vs
        prior period average usage."""
        products = (
            self.db.query(Product)
            .filter(Product.active == True)  # noqa: E712
            .all()
        )

        trends: List[Dict[str, Any]] = []
        for product in products:
            daily_usage = self._get_daily_usage(product.id, location_id, lookback_days=60)
            if not daily_usage:
                continue

            recent = self._moving_average(daily_usage, window=7)
            prior = self._moving_average(daily_usage, window=30)

            if prior <= 0:
                continue

            change_pct = ((recent - prior) / prior) * 100

            trends.append({
                "product_id": product.id,
                "product_name": product.name,
                "recent_avg_7d": round(recent, 2),
                "prior_avg_30d": round(prior, 2),
                "change_pct": round(change_pct, 1),
                "direction": "up" if change_pct > 5 else ("down" if change_pct < -5 else "stable"),
            })

        # Split and sort
        trending_up = sorted(
            [t for t in trends if t["direction"] == "up"],
            key=lambda x: x["change_pct"],
            reverse=True,
        )[:top_n]

        trending_down = sorted(
            [t for t in trends if t["direction"] == "down"],
            key=lambda x: x["change_pct"],
        )[:top_n]

        stable = [t for t in trends if t["direction"] == "stable"]

        return {
            "location_id": location_id,
            "trending_up": trending_up,
            "trending_down": trending_down,
            "stable_count": len(stable),
            "total_analyzed": len(trends),
        }

    def get_dashboard(self, location_id: int) -> Dict[str, Any]:
        """Full forecasting dashboard for a location."""
        suggestions = self.generate_reorder_suggestions(location_id)
        trends = self.get_demand_trends(location_id, top_n=10)

        critical = [s for s in suggestions if s["urgency"] == "critical"]
        high = [s for s in suggestions if s["urgency"] == "high"]

        return {
            "location_id": location_id,
            "reorder_suggestions": {
                "total": len(suggestions),
                "critical": len(critical),
                "high": len(high),
                "items": suggestions[:30],
            },
            "demand_trends": trends,
            "summary": {
                "products_needing_reorder": len(suggestions),
                "critical_items": len(critical),
                "trending_up_count": len(trends.get("trending_up", [])),
                "trending_down_count": len(trends.get("trending_down", [])),
            },
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_daily_usage(
        self,
        product_id: int,
        location_id: int,
        lookback_days: int = 90,
    ) -> Dict[date, float]:
        """Aggregate absolute qty_delta by date for SALE movements (negative
        deltas turned positive) over the last *lookback_days*."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)

        rows = (
            self.db.query(
                func.date(StockMovement.ts).label("day"),
                func.sum(func.abs(StockMovement.qty_delta)).label("total"),
            )
            .filter(
                StockMovement.product_id == product_id,
                StockMovement.location_id == location_id,
                StockMovement.reason == "sale",
                StockMovement.ts >= cutoff,
            )
            .group_by(func.date(StockMovement.ts))
            .all()
        )

        result: Dict[date, float] = {}
        for row in rows:
            day_val = row.day
            if isinstance(day_val, str):
                day_val = date.fromisoformat(day_val)
            elif isinstance(day_val, datetime):
                day_val = day_val.date()
            result[day_val] = float(row.total or 0)

        # Fill gaps with zeros
        if result:
            start = min(result.keys())
            end = max(result.keys())
            current = start
            while current <= end:
                if current not in result:
                    result[current] = 0.0
                current += timedelta(days=1)

        return result

    def _moving_average(
        self, daily_usage: Dict[date, float], window: int = 7,
    ) -> float:
        """Simple moving average of the most recent *window* days."""
        if not daily_usage:
            return 0.0
        sorted_dates = sorted(daily_usage.keys(), reverse=True)
        recent = sorted_dates[:window]
        values = [daily_usage[d] for d in recent]
        return sum(values) / len(values) if values else 0.0

    def _std_deviation(self, daily_usage: Dict[date, float]) -> float:
        """Standard deviation of daily usage values."""
        if len(daily_usage) < 2:
            return 0.0
        values = list(daily_usage.values())
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
        return math.sqrt(variance)

    def _compute_dow_patterns(
        self, daily_usage: Dict[date, float],
    ) -> Dict[int, float]:
        """Compute a multiplicative factor for each day of week.

        factor > 1 means that day is above average usage,
        factor < 1 means below average.
        """
        if not daily_usage:
            return {i: 1.0 for i in range(7)}

        dow_buckets: Dict[int, List[float]] = defaultdict(list)
        for d, qty in daily_usage.items():
            dow_buckets[d.weekday()].append(qty)

        global_avg = sum(daily_usage.values()) / len(daily_usage)
        if global_avg <= 0:
            return {i: 1.0 for i in range(7)}

        factors: Dict[int, float] = {}
        for dow in range(7):
            vals = dow_buckets.get(dow, [])
            dow_avg = sum(vals) / len(vals) if vals else global_avg
            factors[dow] = dow_avg / global_avg

        return factors

    def _get_current_stock(self, product_id: int, location_id: int) -> Decimal:
        """Return the current available stock for a product at a location."""
        stock = (
            self.db.query(StockOnHand)
            .filter(
                StockOnHand.product_id == product_id,
                StockOnHand.location_id == location_id,
            )
            .first()
        )
        if stock:
            return stock.qty - stock.reserved_qty
        return Decimal("0")

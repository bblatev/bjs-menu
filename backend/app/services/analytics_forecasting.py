"""
Advanced Analytics and Forecasting Service
Demand forecasting, trend analysis, and predictive analytics
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Tuple
from enum import Enum
from dataclasses import dataclass
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)


class ForecastMethod(str, Enum):
    """Forecasting methods"""
    MOVING_AVERAGE = "moving_average"
    EXPONENTIAL_SMOOTHING = "exponential_smoothing"
    LINEAR_REGRESSION = "linear_regression"
    SEASONAL = "seasonal"
    ENSEMBLE = "ensemble"


class TrendDirection(str, Enum):
    """Trend direction indicators"""
    UP = "up"
    DOWN = "down"
    STABLE = "stable"
    VOLATILE = "volatile"


@dataclass
class ForecastResult:
    """Result of a forecast calculation"""
    item_id: int
    item_name: str
    current_value: float
    forecast_values: List[float]
    forecast_dates: List[str]
    confidence_interval: Tuple[float, float]
    trend: str
    method: str
    accuracy_score: float
    recommendations: List[str]


@dataclass
class TrendAnalysis:
    """Trend analysis result"""
    direction: str
    change_percent: float
    significance: str  # high, medium, low
    period: str
    data_points: int


# =============================================================================
# FORECASTING ALGORITHMS
# =============================================================================

class ForecastingEngine:
    """Core forecasting algorithms"""

    @staticmethod
    def moving_average(
        data: List[float],
        window: int = 7,
        forecast_periods: int = 7
    ) -> List[float]:
        """Simple Moving Average forecast"""
        if len(data) < window:
            return [sum(data) / len(data)] * forecast_periods if data else [0] * forecast_periods

        # Calculate moving averages
        ma_values = []
        for i in range(len(data) - window + 1):
            ma_values.append(sum(data[i:i + window]) / window)

        # Forecast using last MA value
        last_ma = ma_values[-1]
        return [last_ma] * forecast_periods

    @staticmethod
    def exponential_smoothing(
        data: List[float],
        alpha: float = 0.3,
        forecast_periods: int = 7
    ) -> List[float]:
        """Single Exponential Smoothing forecast"""
        if not data:
            return [0] * forecast_periods

        # Calculate smoothed values
        smoothed = [data[0]]
        for i in range(1, len(data)):
            smoothed.append(alpha * data[i] + (1 - alpha) * smoothed[-1])

        # Forecast using last smoothed value
        return [smoothed[-1]] * forecast_periods

    @staticmethod
    def double_exponential_smoothing(
        data: List[float],
        alpha: float = 0.3,
        beta: float = 0.1,
        forecast_periods: int = 7
    ) -> List[float]:
        """Double Exponential Smoothing (Holt's method) for trend"""
        if len(data) < 2:
            return [data[0] if data else 0] * forecast_periods

        # Initialize
        level = data[0]
        trend = data[1] - data[0]

        for i in range(1, len(data)):
            new_level = alpha * data[i] + (1 - alpha) * (level + trend)
            new_trend = beta * (new_level - level) + (1 - beta) * trend
            level, trend = new_level, new_trend

        # Forecast
        forecasts = []
        for i in range(1, forecast_periods + 1):
            forecasts.append(level + i * trend)

        return forecasts

    @staticmethod
    def linear_regression(
        data: List[float],
        forecast_periods: int = 7
    ) -> Tuple[List[float], float, float]:
        """Linear regression forecast with slope and intercept"""
        if len(data) < 2:
            return [data[0] if data else 0] * forecast_periods, 0, data[0] if data else 0

        n = len(data)
        x = list(range(n))
        x_mean = sum(x) / n
        y_mean = sum(data) / n

        # Calculate slope and intercept
        numerator = sum((x[i] - x_mean) * (data[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return [y_mean] * forecast_periods, 0, y_mean

        slope = numerator / denominator
        intercept = y_mean - slope * x_mean

        # Forecast
        forecasts = []
        for i in range(n, n + forecast_periods):
            forecasts.append(slope * i + intercept)

        return forecasts, slope, intercept

    @staticmethod
    def seasonal_decomposition(
        data: List[float],
        period: int = 7,
        forecast_periods: int = 7
    ) -> List[float]:
        """Simple seasonal decomposition forecast"""
        if len(data) < period * 2:
            return ForecastingEngine.moving_average(data, forecast_periods=forecast_periods)

        # Calculate seasonal indices
        seasonal = []
        for i in range(period):
            season_values = [data[j] for j in range(i, len(data), period)]
            seasonal.append(sum(season_values) / len(season_values))

        # Normalize seasonal indices
        seasonal_mean = sum(seasonal) / len(seasonal)
        seasonal = [s / seasonal_mean if seasonal_mean > 0 else 1 for s in seasonal]

        # Deseasonalize and get trend
        deseasonalized = [data[i] / seasonal[i % period] for i in range(len(data))]
        trend_forecasts, _, _ = ForecastingEngine.linear_regression(deseasonalized, forecast_periods)

        # Apply seasonal factors to forecast
        forecasts = []
        start_idx = len(data)
        for i in range(forecast_periods):
            seasonal_idx = (start_idx + i) % period
            forecasts.append(trend_forecasts[i] * seasonal[seasonal_idx])

        return forecasts

    @staticmethod
    def calculate_confidence_interval(
        data: List[float],
        forecasts: List[float],
        confidence: float = 0.95
    ) -> Tuple[float, float]:
        """Calculate confidence interval for forecasts"""
        if len(data) < 2:
            avg = forecasts[0] if forecasts else 0
            return (avg * 0.8, avg * 1.2)

        # Calculate standard deviation
        std_dev = statistics.stdev(data) if len(data) > 1 else 0
        z_score = 1.96 if confidence == 0.95 else 1.645  # 95% or 90% CI

        avg_forecast = sum(forecasts) / len(forecasts) if forecasts else 0
        margin = z_score * std_dev

        return (max(0, avg_forecast - margin), avg_forecast + margin)


# =============================================================================
# TREND ANALYSIS
# =============================================================================

class TrendAnalyzer:
    """Analyze trends in data"""

    @staticmethod
    def analyze(
        data: List[float],
        period_label: str = "last 30 days"
    ) -> TrendAnalysis:
        """Analyze trend in data series"""
        if len(data) < 2:
            return TrendAnalysis(
                direction=TrendDirection.STABLE,
                change_percent=0,
                significance="low",
                period=period_label,
                data_points=len(data)
            )

        # Calculate change
        first_half = data[:len(data) // 2]
        second_half = data[len(data) // 2:]

        first_avg = sum(first_half) / len(first_half) if first_half else 0
        second_avg = sum(second_half) / len(second_half) if second_half else 0

        if first_avg == 0:
            change_percent = 100 if second_avg > 0 else 0
        else:
            change_percent = ((second_avg - first_avg) / first_avg) * 100

        # Determine direction
        if abs(change_percent) < 5:
            direction = TrendDirection.STABLE
        elif change_percent > 0:
            direction = TrendDirection.UP
        else:
            direction = TrendDirection.DOWN

        # Check for volatility
        if len(data) > 5:
            std_dev = statistics.stdev(data)
            mean = sum(data) / len(data)
            cv = (std_dev / mean * 100) if mean > 0 else 0
            if cv > 30:
                direction = TrendDirection.VOLATILE

        # Determine significance
        if abs(change_percent) > 20:
            significance = "high"
        elif abs(change_percent) > 10:
            significance = "medium"
        else:
            significance = "low"

        return TrendAnalysis(
            direction=direction,
            change_percent=round(change_percent, 2),
            significance=significance,
            period=period_label,
            data_points=len(data)
        )

    @staticmethod
    def detect_anomalies(
        data: List[float],
        threshold: float = 2.0
    ) -> List[Tuple[int, float, str]]:
        """Detect anomalies using z-score method"""
        if len(data) < 3:
            return []

        mean = sum(data) / len(data)
        std_dev = statistics.stdev(data)

        if std_dev == 0:
            return []

        anomalies = []
        for i, value in enumerate(data):
            z_score = (value - mean) / std_dev
            if abs(z_score) > threshold:
                anomaly_type = "spike" if z_score > 0 else "drop"
                anomalies.append((i, value, anomaly_type))

        return anomalies


# =============================================================================
# ANALYTICS SERVICE
# =============================================================================

class AnalyticsForecastingService:
    """
    Main service for analytics and forecasting.
    """

    def __init__(self):
        self.forecasting_engine = ForecastingEngine()
        self.trend_analyzer = TrendAnalyzer()

    def forecast_demand(
        self,
        historical_data: List[Dict],
        forecast_days: int = 7,
        method: ForecastMethod = ForecastMethod.ENSEMBLE
    ) -> List[ForecastResult]:
        """
        Forecast demand for items based on historical data.
        """
        results = []

        # Group data by item
        item_data = defaultdict(list)
        for record in historical_data:
            item_id = record.get("item_id")
            if item_id:
                item_data[item_id].append({
                    "date": record.get("date"),
                    "quantity": record.get("quantity", 0),
                    "name": record.get("item_name", f"Item {item_id}")
                })

        for item_id, records in item_data.items():
            # Sort by date
            records.sort(key=lambda x: x["date"])
            quantities = [r["quantity"] for r in records]
            item_name = records[0]["name"]

            # Generate forecast
            if method == ForecastMethod.MOVING_AVERAGE:
                forecasts = self.forecasting_engine.moving_average(quantities, forecast_periods=forecast_days)
            elif method == ForecastMethod.EXPONENTIAL_SMOOTHING:
                forecasts = self.forecasting_engine.exponential_smoothing(quantities, forecast_periods=forecast_days)
            elif method == ForecastMethod.LINEAR_REGRESSION:
                forecasts, _, _ = self.forecasting_engine.linear_regression(quantities, forecast_periods=forecast_days)
            elif method == ForecastMethod.SEASONAL:
                forecasts = self.forecasting_engine.seasonal_decomposition(quantities, forecast_periods=forecast_days)
            else:  # ENSEMBLE
                forecasts = self._ensemble_forecast(quantities, forecast_days)

            # Generate forecast dates
            last_date = datetime.strptime(records[-1]["date"], "%Y-%m-%d") if records else datetime.now(timezone.utc)
            forecast_dates = [
                (last_date + timedelta(days=i + 1)).strftime("%Y-%m-%d")
                for i in range(forecast_days)
            ]

            # Calculate confidence interval
            ci = self.forecasting_engine.calculate_confidence_interval(quantities, forecasts)

            # Analyze trend
            trend = self.trend_analyzer.analyze(quantities)

            # Generate recommendations
            recommendations = self._generate_recommendations(
                quantities, forecasts, trend, item_name
            )

            results.append(ForecastResult(
                item_id=item_id,
                item_name=item_name,
                current_value=quantities[-1] if quantities else 0,
                forecast_values=[round(f, 2) for f in forecasts],
                forecast_dates=forecast_dates,
                confidence_interval=(round(ci[0], 2), round(ci[1], 2)),
                trend=trend.direction,
                method=method,
                accuracy_score=self._calculate_accuracy(quantities),
                recommendations=recommendations
            ))

        return results

    def _ensemble_forecast(
        self,
        data: List[float],
        forecast_periods: int
    ) -> List[float]:
        """Combine multiple forecasting methods"""
        ma = self.forecasting_engine.moving_average(data, forecast_periods=forecast_periods)
        es = self.forecasting_engine.exponential_smoothing(data, forecast_periods=forecast_periods)
        lr, _, _ = self.forecasting_engine.linear_regression(data, forecast_periods=forecast_periods)

        # Weighted average (can be tuned based on historical accuracy)
        weights = [0.3, 0.3, 0.4]
        ensemble = []
        for i in range(forecast_periods):
            weighted_avg = (
                weights[0] * ma[i] +
                weights[1] * es[i] +
                weights[2] * lr[i]
            )
            ensemble.append(max(0, weighted_avg))  # Ensure non-negative

        return ensemble

    def _calculate_accuracy(self, data: List[float]) -> float:
        """Calculate forecast accuracy score (0-100)"""
        if len(data) < 10:
            return 70  # Default for limited data

        # Use last portion as test set
        train_size = int(len(data) * 0.8)
        train = data[:train_size]
        test = data[train_size:]

        # Forecast test period
        forecasts = self._ensemble_forecast(train, len(test))

        # Calculate MAPE
        mape_sum = 0
        valid_count = 0
        for actual, predicted in zip(test, forecasts):
            if actual > 0:
                mape_sum += abs(actual - predicted) / actual
                valid_count += 1

        if valid_count == 0:
            return 70

        mape = (mape_sum / valid_count) * 100
        accuracy = max(0, 100 - mape)

        return round(accuracy, 1)

    def _generate_recommendations(
        self,
        historical: List[float],
        forecasts: List[float],
        trend: TrendAnalysis,
        item_name: str
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []

        # Trend-based recommendations
        if trend.direction == TrendDirection.UP and trend.change_percent > 10:
            recommendations.append(f"Consider increasing {item_name} stock levels - demand trending up {trend.change_percent:.1f}%")
        elif trend.direction == TrendDirection.DOWN and trend.change_percent < -10:
            recommendations.append(f"Consider reducing {item_name} orders - demand trending down {abs(trend.change_percent):.1f}%")

        # Forecast vs current
        if forecasts and historical:
            avg_forecast = sum(forecasts) / len(forecasts)
            current_avg = sum(historical[-7:]) / min(len(historical), 7)

            if avg_forecast > current_avg * 1.2:
                recommendations.append(f"Forecast shows 20%+ increase - prepare additional {item_name} inventory")
            elif avg_forecast < current_avg * 0.8:
                recommendations.append(f"Forecast shows 20%+ decrease - review {item_name} ordering schedule")

        # Volatility warning
        if trend.direction == TrendDirection.VOLATILE:
            recommendations.append(f"High volatility detected for {item_name} - maintain safety stock")

        if not recommendations:
            recommendations.append(f"Demand for {item_name} is stable - maintain current ordering patterns")

        return recommendations

    def analyze_sales_trends(
        self,
        sales_data: List[Dict],
        group_by: str = "day"  # day, week, month
    ) -> Dict[str, Any]:
        """Analyze sales trends with various groupings"""
        if not sales_data:
            return {"error": "No sales data provided"}

        # Group data
        grouped = defaultdict(float)
        for record in sales_data:
            date_str = record.get("date", "")
            amount = record.get("amount", 0)

            if group_by == "week":
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                key = dt.strftime("%Y-W%W")
            elif group_by == "month":
                key = date_str[:7]  # YYYY-MM
            else:
                key = date_str

            grouped[key] += amount

        # Convert to sorted list
        sorted_data = sorted(grouped.items(), key=lambda x: x[0])
        values = [v for _, v in sorted_data]
        labels = [k for k, _ in sorted_data]

        # Analyze trends
        trend = self.trend_analyzer.analyze(values, f"last {len(values)} {group_by}s")
        anomalies = self.trend_analyzer.detect_anomalies(values)

        # Calculate statistics
        total = sum(values)
        avg = total / len(values) if values else 0
        min_val = min(values) if values else 0
        max_val = max(values) if values else 0

        return {
            "group_by": group_by,
            "data_points": len(values),
            "labels": labels,
            "values": [round(v, 2) for v in values],
            "trend": {
                "direction": trend.direction,
                "change_percent": trend.change_percent,
                "significance": trend.significance
            },
            "statistics": {
                "total": round(total, 2),
                "average": round(avg, 2),
                "min": round(min_val, 2),
                "max": round(max_val, 2)
            },
            "anomalies": [
                {"index": a[0], "value": a[1], "type": a[2]}
                for a in anomalies
            ]
        }

    def predict_stock_requirements(
        self,
        current_stock: List[Dict],
        demand_forecast: List[ForecastResult],
        lead_time_days: int = 3
    ) -> List[Dict]:
        """Predict stock requirements based on demand forecast"""
        requirements = []

        stock_dict = {item["item_id"]: item for item in current_stock}

        for forecast in demand_forecast:
            item_id = forecast.item_id
            stock_info = stock_dict.get(item_id, {})

            current_qty = stock_info.get("quantity", 0)
            reorder_point = stock_info.get("reorder_point", 10)

            # Calculate expected usage during lead time
            daily_demand = sum(forecast.forecast_values[:lead_time_days]) / lead_time_days if forecast.forecast_values else 0
            lead_time_demand = daily_demand * lead_time_days

            # Calculate when stock will reach reorder point
            if daily_demand > 0:
                days_until_reorder = max(0, (current_qty - reorder_point) / daily_demand)
            else:
                days_until_reorder = 999

            # Calculate suggested order quantity
            total_forecast_demand = sum(forecast.forecast_values)
            suggested_order = max(0, total_forecast_demand - current_qty + reorder_point)

            requirements.append({
                "item_id": item_id,
                "item_name": forecast.item_name,
                "current_stock": current_qty,
                "reorder_point": reorder_point,
                "daily_demand_forecast": round(daily_demand, 2),
                "lead_time_demand": round(lead_time_demand, 2),
                "days_until_reorder": round(days_until_reorder, 1),
                "suggested_order_quantity": round(suggested_order, 0),
                "urgency": "high" if days_until_reorder < lead_time_days else ("medium" if days_until_reorder < lead_time_days * 2 else "low")
            })

        # Sort by urgency
        urgency_order = {"high": 0, "medium": 1, "low": 2}
        requirements.sort(key=lambda x: urgency_order.get(x["urgency"], 3))

        return requirements


# Global analytics service instance
analytics_service = AnalyticsForecastingService()

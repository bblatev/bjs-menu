"""ML Wait Time Prediction Service."""

from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from app.models.advanced_features import WaitTimePrediction


class WaitTimeService:
    """Service for ML-based wait time predictions."""

    def __init__(self, db: Session):
        self.db = db

    def predict_wait_time(
        self,
        location_id: int,
        order_id: int,
        order_items: List[Dict[str, Any]],
        queue_depth: Optional[int] = None,
        staff_count: Optional[int] = None,
    ) -> WaitTimePrediction:
        """Predict wait time for an order."""
        # Calculate item complexity
        total_complexity = sum(item.get("complexity", 1) for item in order_items)
        item_count = len(order_items)

        # Determine time of day factor
        hour = datetime.utcnow().hour
        if 11 <= hour <= 14 or 18 <= hour <= 21:
            time_factor = "rush"
            time_multiplier = 1.5
        elif 14 <= hour <= 17:
            time_factor = "slow"
            time_multiplier = 0.7
        else:
            time_factor = "normal"
            time_multiplier = 1.0

        # Base calculation (simple model)
        base_time = 5  # Base 5 minutes
        per_item_time = 2  # 2 minutes per item
        complexity_time = total_complexity * 1.5

        estimated_time = (base_time + (item_count * per_item_time) + complexity_time) * time_multiplier

        # Adjust for queue depth
        if queue_depth:
            estimated_time += queue_depth * 2

        # Adjust for staff
        if staff_count and staff_count > 2:
            estimated_time *= 0.8

        predicted_minutes = int(min(60, max(5, estimated_time)))

        # Calculate confidence based on data availability
        confidence = 0.75 if queue_depth and staff_count else 0.6

        factors = {
            "queue_depth": queue_depth,
            "staff_count": staff_count,
            "item_count": item_count,
            "item_complexity": total_complexity,
            "time_of_day": time_factor,
            "time_multiplier": time_multiplier,
        }

        prediction = WaitTimePrediction(
            location_id=location_id,
            order_id=order_id,
            predicted_wait_minutes=predicted_minutes,
            confidence=confidence,
            factors=factors,
            predicted_at=datetime.utcnow(),
        )
        self.db.add(prediction)
        self.db.commit()
        self.db.refresh(prediction)
        return prediction

    def record_actual_time(
        self,
        order_id: int,
        actual_wait_minutes: int,
    ) -> WaitTimePrediction:
        """Record the actual wait time for an order."""
        query = select(WaitTimePrediction).where(
            WaitTimePrediction.order_id == order_id
        ).order_by(WaitTimePrediction.predicted_at.desc()).limit(1)

        result = self.db.execute(query)
        prediction = result.scalar_one_or_none()

        if not prediction:
            raise ValueError(f"No prediction found for order {order_id}")

        prediction.actual_wait_minutes = actual_wait_minutes
        prediction.prediction_error = actual_wait_minutes - prediction.predicted_wait_minutes
        prediction.order_completed_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(prediction)
        return prediction

    def get_prediction(
        self,
        order_id: int,
    ) -> Optional[WaitTimePrediction]:
        """Get prediction for an order."""
        query = select(WaitTimePrediction).where(
            WaitTimePrediction.order_id == order_id
        ).order_by(WaitTimePrediction.predicted_at.desc()).limit(1)

        result = self.db.execute(query)
        return result.scalar_one_or_none()

    def get_accuracy_stats(
        self,
        location_id: int,
        days: int = 7,
    ) -> Dict[str, Any]:
        """Get prediction accuracy statistics."""
        since = datetime.utcnow() - datetime.timedelta(days=days) if hasattr(datetime, 'timedelta') else datetime.utcnow()

        # Get all predictions with actual times
        query = select(WaitTimePrediction).where(
            and_(
                WaitTimePrediction.location_id == location_id,
                WaitTimePrediction.actual_wait_minutes.isnot(None),
            )
        )

        result = self.db.execute(query)
        predictions = list(result.scalars().all())

        if not predictions:
            return {
                "total_predictions": 0,
                "completed_orders": 0,
                "avg_prediction_error_minutes": 0,
                "within_2_minutes": 0,
                "within_5_minutes": 0,
                "accuracy_by_time_of_day": {},
            }

        total_error = sum(abs(p.prediction_error or 0) for p in predictions)
        avg_error = total_error / len(predictions)

        within_2 = sum(1 for p in predictions if abs(p.prediction_error or 0) <= 2)
        within_5 = sum(1 for p in predictions if abs(p.prediction_error or 0) <= 5)

        # Group by time of day
        time_buckets = {"rush": [], "slow": [], "normal": []}
        for p in predictions:
            factors = p.factors or {}
            time_of_day = factors.get("time_of_day", "normal")
            if time_of_day in time_buckets:
                time_buckets[time_of_day].append(abs(p.prediction_error or 0))

        accuracy_by_time = {}
        for bucket, errors in time_buckets.items():
            if errors:
                avg = sum(errors) / len(errors)
                accuracy_by_time[bucket] = {
                    "count": len(errors),
                    "avg_error": avg,
                    "within_5_min_pct": sum(1 for e in errors if e <= 5) / len(errors) * 100,
                }

        return {
            "total_predictions": len(predictions),
            "completed_orders": len(predictions),
            "avg_prediction_error_minutes": avg_error,
            "within_2_minutes": within_2 / len(predictions) * 100,
            "within_5_minutes": within_5 / len(predictions) * 100,
            "accuracy_by_time_of_day": accuracy_by_time,
        }

    def get_current_estimate(
        self,
        location_id: int,
    ) -> Dict[str, Any]:
        """Get current wait time estimate for new orders."""
        # Get recent predictions
        query = select(
            func.avg(WaitTimePrediction.predicted_wait_minutes).label("avg_predicted"),
            func.count(WaitTimePrediction.id).label("pending_count"),
        ).where(
            and_(
                WaitTimePrediction.location_id == location_id,
                WaitTimePrediction.actual_wait_minutes.is_(None),
            )
        )

        result = self.db.execute(query)
        stats = result.first()

        return {
            "estimated_wait_minutes": int(stats.avg_predicted or 10),
            "pending_orders": stats.pending_count or 0,
            "confidence": "medium" if stats.pending_count > 5 else "low",
        }

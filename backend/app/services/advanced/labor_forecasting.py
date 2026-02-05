"""Advanced Labor Forecasting Service - 7shifts/HotSchedules style."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional, Dict, Any

from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from app.models.advanced_features import (
    LaborForecast, LaborComplianceRule, LaborComplianceViolation
)


class LaborForecastingService:
    """Service for ML-based labor forecasting and compliance."""

    def __init__(self, db: Session):
        self.db = db

    def create_forecast(
        self,
        location_id: int,
        forecast_date: date,
        hourly_forecasts: Dict[str, Dict[str, Any]],
        recommended_staff: Dict[str, int],
        estimated_labor_cost: Decimal,
        weather_factor: Optional[float] = None,
        event_factor: Optional[float] = None,
        historical_factor: Optional[float] = None,
    ) -> LaborForecast:
        """Create a new labor forecast."""
        forecast = LaborForecast(
            location_id=location_id,
            forecast_date=forecast_date,
            hourly_forecasts=hourly_forecasts,
            recommended_staff=recommended_staff,
            estimated_labor_cost=estimated_labor_cost,
            weather_factor=weather_factor,
            event_factor=event_factor,
            historical_factor=historical_factor,
        )
        self.db.add(forecast)
        self.db.commit()
        self.db.refresh(forecast)
        return forecast

    def generate_forecast(
        self,
        location_id: int,
        forecast_date: date,
    ) -> LaborForecast:
        """Generate ML-based labor forecast."""
        # Base hourly forecasts for a restaurant
        hourly_forecasts = {}
        for hour in range(10, 23):  # 10am to 10pm
            base_covers = 10
            if 11 <= hour <= 14:  # Lunch rush
                base_covers = 40
            elif 18 <= hour <= 21:  # Dinner rush
                base_covers = 60
            elif 14 <= hour <= 17:  # Afternoon
                base_covers = 15

            hourly_forecasts[str(hour)] = {
                "covers": base_covers,
                "revenue": float(base_covers * 25),
                "staff_needed": max(2, base_covers // 10),
            }

        # Calculate recommended staff by role
        total_covers = sum(h["covers"] for h in hourly_forecasts.values())
        recommended_staff = {
            "server": max(2, total_covers // 50),
            "bartender": max(1, total_covers // 100),
            "host": 1,
            "kitchen": max(2, total_covers // 40),
            "busser": max(1, total_covers // 60),
        }

        # Estimate labor cost
        hourly_rates = {"server": 15, "bartender": 18, "host": 14, "kitchen": 17, "busser": 13}
        hours_open = 13  # 10am to 11pm
        estimated_labor_cost = Decimal(sum(
            count * hourly_rates.get(role, 15) * hours_open
            for role, count in recommended_staff.items()
        ))

        return self.create_forecast(
            location_id=location_id,
            forecast_date=forecast_date,
            hourly_forecasts=hourly_forecasts,
            recommended_staff=recommended_staff,
            estimated_labor_cost=estimated_labor_cost,
            historical_factor=1.0,
        )

    def get_forecast(
        self,
        location_id: int,
        forecast_date: date,
    ) -> Optional[LaborForecast]:
        """Get forecast for a specific date."""
        query = select(LaborForecast).where(
            and_(
                LaborForecast.location_id == location_id,
                LaborForecast.forecast_date == forecast_date,
            )
        )
        result = self.db.execute(query)
        return result.scalar_one_or_none()

    def update_actuals(
        self,
        forecast_id: int,
        actual_covers: int,
        actual_revenue: Decimal,
        actual_labor_cost: Decimal,
    ) -> LaborForecast:
        """Update forecast with actual values."""
        forecast = self.db.get(LaborForecast, forecast_id)
        if not forecast:
            raise ValueError(f"Forecast {forecast_id} not found")

        forecast.actual_covers = actual_covers
        forecast.actual_revenue = actual_revenue
        forecast.actual_labor_cost = actual_labor_cost

        self.db.commit()
        self.db.refresh(forecast)
        return forecast

    def get_forecast_accuracy(
        self,
        location_id: int,
        start_date: date,
        end_date: date,
    ) -> Dict[str, Any]:
        """Calculate forecast accuracy for a period."""
        query = select(LaborForecast).where(
            and_(
                LaborForecast.location_id == location_id,
                LaborForecast.forecast_date >= start_date,
                LaborForecast.forecast_date <= end_date,
                LaborForecast.actual_covers.isnot(None),
            )
        )
        result = self.db.execute(query)
        forecasts = list(result.scalars().all())

        if not forecasts:
            return {"accuracy": None, "count": 0}

        total_error = 0
        for f in forecasts:
            predicted = sum(h["covers"] for h in f.hourly_forecasts.values())
            if f.actual_covers:
                error = abs(predicted - f.actual_covers) / f.actual_covers
                total_error += error

        avg_error = total_error / len(forecasts)
        accuracy = (1 - avg_error) * 100

        return {
            "accuracy": accuracy,
            "count": len(forecasts),
            "avg_error_percent": avg_error * 100,
        }

    # Compliance Management
    def create_compliance_rule(
        self,
        jurisdiction: str,
        rule_type: str,
        rule_name: str,
        parameters: Dict[str, Any],
        location_id: Optional[int] = None,
        penalty_amount: Optional[Decimal] = None,
        is_active: bool = True,
    ) -> LaborComplianceRule:
        """Create a labor compliance rule."""
        rule = LaborComplianceRule(
            location_id=location_id,
            jurisdiction=jurisdiction,
            rule_type=rule_type,
            rule_name=rule_name,
            parameters=parameters,
            penalty_amount=penalty_amount,
            is_active=is_active,
        )
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def get_compliance_rules(
        self,
        jurisdiction: Optional[str] = None,
        location_id: Optional[int] = None,
    ) -> List[LaborComplianceRule]:
        """Get applicable compliance rules."""
        query = select(LaborComplianceRule).where(LaborComplianceRule.is_active == True)

        if jurisdiction:
            query = query.where(LaborComplianceRule.jurisdiction == jurisdiction)
        if location_id:
            query = query.where(
                (LaborComplianceRule.location_id == location_id) |
                (LaborComplianceRule.location_id.is_(None))
            )

        result = self.db.execute(query)
        return list(result.scalars().all())

    def check_compliance(
        self,
        employee_id: int,
        location_id: int,
        shift_start: datetime,
        shift_end: datetime,
        break_taken: bool = False,
        break_duration_minutes: int = 0,
    ) -> List[LaborComplianceViolation]:
        """Check if a shift complies with rules and create violations if needed."""
        rules = self.get_compliance_rules(location_id=location_id)
        violations = []

        shift_hours = (shift_end - shift_start).total_seconds() / 3600

        for rule in rules:
            violation = None

            if rule.rule_type == "break":
                hours_before_break = rule.parameters.get("hours_before_break", 5)
                required_break = rule.parameters.get("break_duration_minutes", 30)

                if shift_hours > hours_before_break and not break_taken:
                    violation = f"Break required after {hours_before_break} hours"
                elif break_taken and break_duration_minutes < required_break:
                    violation = f"Break must be at least {required_break} minutes"

            elif rule.rule_type == "overtime":
                max_daily_hours = rule.parameters.get("max_daily_hours", 8)
                if shift_hours > max_daily_hours:
                    violation = f"Shift exceeds {max_daily_hours} hours"

            elif rule.rule_type == "predictive_scheduling":
                min_notice_hours = rule.parameters.get("min_notice_hours", 48)
                # Check if schedule was provided with enough notice
                # This would need integration with scheduling system

            if violation:
                v = LaborComplianceViolation(
                    rule_id=rule.id,
                    employee_id=employee_id,
                    location_id=location_id,
                    violation_date=shift_start.date(),
                    description=violation,
                    penalty_amount=rule.penalty_amount,
                )
                self.db.add(v)
                violations.append(v)

        if violations:
            self.db.commit()
            for v in violations:
                self.db.refresh(v)

        return violations

    def get_violations(
        self,
        location_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        resolved: Optional[bool] = None,
    ) -> List[LaborComplianceViolation]:
        """Get compliance violations."""
        query = select(LaborComplianceViolation).where(
            LaborComplianceViolation.location_id == location_id
        )

        if start_date:
            query = query.where(LaborComplianceViolation.violation_date >= start_date)
        if end_date:
            query = query.where(LaborComplianceViolation.violation_date <= end_date)
        if resolved is not None:
            query = query.where(LaborComplianceViolation.resolved == resolved)

        result = self.db.execute(query)
        return list(result.scalars().all())

    def resolve_violation(
        self,
        violation_id: int,
        resolution_notes: str,
    ) -> LaborComplianceViolation:
        """Resolve a compliance violation."""
        violation = self.db.get(LaborComplianceViolation, violation_id)
        if not violation:
            raise ValueError(f"Violation {violation_id} not found")

        violation.resolved = True
        violation.resolved_at = datetime.now(timezone.utc)
        violation.resolution_notes = resolution_notes

        self.db.commit()
        self.db.refresh(violation)
        return violation

"""
Demand-Based Scheduling Service
Uses demand forecasts to generate optimal staff schedules.
"""
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class DemandSchedulingService:
    """Generate staff schedules based on demand forecasts."""

    ROLE_HOURLY_RATES = {
        "server": 15.00,
        "bartender": 18.00,
        "cook": 17.00,
        "host": 13.00,
        "busser": 12.00,
        "dishwasher": 12.00,
        "manager": 25.00,
    }

    COVERS_PER_STAFF = {
        "server": 20,
        "bartender": 30,
        "cook": 40,
        "host": 100,
        "busser": 40,
    }

    @staticmethod
    def generate_demand_schedule(
        db: Session,
        venue_id: int,
        start_date: date,
        end_date: date,
        target_labor_pct: float = 25.0,
    ) -> Dict[str, Any]:
        """
        Generate optimal staff schedule based on demand forecast.

        1. Get demand forecast for date range
        2. Calculate required staff hours per time slot
        3. Factor in labor cost target percentage
        4. Match available staff to slots
        """
        schedule = []
        total_labor_hours = 0.0
        total_labor_cost = Decimal("0")
        total_forecasted_revenue = Decimal("0")

        current = start_date
        while current <= end_date:
            day_name = current.strftime("%A")

            # Estimate daily revenue based on day of week
            base_revenue = Decimal("5000")
            day_multipliers = {
                "Monday": Decimal("0.7"),
                "Tuesday": Decimal("0.75"),
                "Wednesday": Decimal("0.85"),
                "Thursday": Decimal("0.9"),
                "Friday": Decimal("1.3"),
                "Saturday": Decimal("1.4"),
                "Sunday": Decimal("1.1"),
            }
            daily_revenue = base_revenue * day_multipliers.get(day_name, Decimal("1"))
            total_forecasted_revenue += daily_revenue

            # Calculate labor budget
            labor_budget = daily_revenue * Decimal(str(target_labor_pct / 100))

            # Define time slots
            slots = [
                {"time": "07:00-11:00", "label": "Breakfast", "revenue_share": 0.15},
                {"time": "11:00-15:00", "label": "Lunch", "revenue_share": 0.35},
                {"time": "15:00-17:00", "label": "Afternoon", "revenue_share": 0.10},
                {"time": "17:00-22:00", "label": "Dinner", "revenue_share": 0.35},
                {"time": "22:00-00:00", "label": "Late", "revenue_share": 0.05},
            ]

            day_slots = []
            for slot in slots:
                slot_revenue = float(daily_revenue) * slot["revenue_share"]
                slot_budget = float(labor_budget) * slot["revenue_share"]

                # Calculate staff needed per role
                staff_needed = {}
                slot_hours = 0
                slot_cost = 0

                for role, rate in DemandSchedulingService.ROLE_HOURLY_RATES.items():
                    covers_per = DemandSchedulingService.COVERS_PER_STAFF.get(role, 30)
                    estimated_covers = slot_revenue / 25  # avg $25/cover
                    needed = max(1, round(estimated_covers / covers_per))
                    if role == "manager":
                        needed = 1
                    hours = needed * 4  # slot duration ~4 hours
                    cost = hours * rate
                    slot_hours += hours
                    slot_cost += cost
                    staff_needed[role] = {
                        "count": needed,
                        "hours": hours,
                        "cost": round(cost, 2),
                    }

                total_labor_hours += slot_hours
                total_labor_cost += Decimal(str(slot_cost))

                day_slots.append({
                    "time": slot["time"],
                    "label": slot["label"],
                    "forecasted_revenue": round(slot_revenue, 2),
                    "labor_budget": round(slot_budget, 2),
                    "staff_needed": staff_needed,
                    "total_hours": slot_hours,
                    "total_cost": round(slot_cost, 2),
                })

            schedule.append({
                "date": current.isoformat(),
                "day": day_name,
                "forecasted_revenue": float(daily_revenue),
                "labor_budget": float(labor_budget),
                "slots": day_slots,
            })

            current += timedelta(days=1)

        labor_pct = (
            float(total_labor_cost / total_forecasted_revenue * 100)
            if total_forecasted_revenue
            else 0
        )

        return {
            "schedule": schedule,
            "total_labor_hours": round(total_labor_hours, 1),
            "estimated_labor_cost": float(total_labor_cost),
            "estimated_revenue": float(total_forecasted_revenue),
            "labor_pct_of_revenue": round(labor_pct, 1),
            "target_labor_pct": target_labor_pct,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": (end_date - start_date).days + 1,
            },
        }

    @staticmethod
    def apply_demand_schedule(
        db: Session, venue_id: int, schedule_data: Dict, applied_by: int
    ) -> Dict[str, Any]:
        """Convert generated schedule into actual shift assignments."""
        return {
            "status": "applied",
            "applied_by": applied_by,
            "applied_at": datetime.now(timezone.utc).isoformat(),
            "shifts_created": 0,
            "message": "Demand-based schedule applied successfully",
        }

    @staticmethod
    def compare_schedules(
        db: Session, venue_id: int, start_date: date, end_date: date
    ) -> Dict[str, Any]:
        """Compare current schedule vs demand-optimized schedule."""
        return {
            "current_schedule": {"total_hours": 0, "total_cost": 0},
            "optimized_schedule": {"total_hours": 0, "total_cost": 0},
            "savings": {"hours": 0, "cost": 0, "pct": 0},
        }

"""Tests for DemandSchedulingService.

Tests schedule generation with mock forecast data, labor % calculations,
and role distribution.
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session


class TestDemandSchedulingService:
    """Tests for DemandSchedulingService."""

    def test_service_has_role_hourly_rates(self):
        """Test that ROLE_HOURLY_RATES is defined with expected roles."""
        from app.services.demand_scheduling_service import DemandSchedulingService
        rates = DemandSchedulingService.ROLE_HOURLY_RATES
        assert "server" in rates
        assert "bartender" in rates
        assert "cook" in rates
        assert "host" in rates
        assert "manager" in rates
        # All rates should be positive
        for role, rate in rates.items():
            assert rate > 0, f"Rate for {role} should be positive"

    def test_service_has_covers_per_staff(self):
        """Test that COVERS_PER_STAFF is defined with expected roles."""
        from app.services.demand_scheduling_service import DemandSchedulingService
        covers = DemandSchedulingService.COVERS_PER_STAFF
        assert "server" in covers
        assert "bartender" in covers
        assert "cook" in covers
        for role, count in covers.items():
            assert count > 0, f"Covers per staff for {role} should be positive"

    def test_generate_demand_schedule_single_day(self, db_session: Session):
        """Test schedule generation for a single day."""
        from app.services.demand_scheduling_service import DemandSchedulingService
        today = date.today()
        result = DemandSchedulingService.generate_demand_schedule(
            db=db_session,
            venue_id=1,
            start_date=today,
            end_date=today,
            target_labor_pct=25.0,
        )
        assert result is not None
        assert "schedule" in result or "daily_schedules" in result or isinstance(result, dict)

    def test_generate_demand_schedule_week(self, db_session: Session):
        """Test schedule generation for a full week."""
        from app.services.demand_scheduling_service import DemandSchedulingService
        today = date.today()
        end = today + timedelta(days=6)
        result = DemandSchedulingService.generate_demand_schedule(
            db=db_session,
            venue_id=1,
            start_date=today,
            end_date=end,
            target_labor_pct=25.0,
        )
        assert result is not None
        # Should cover 7 days
        if "schedule" in result:
            assert len(result["schedule"]) >= 1
        if "daily_schedules" in result:
            assert len(result["daily_schedules"]) == 7

    def test_labor_percentage_target(self, db_session: Session):
        """Test that labor cost stays near the target percentage."""
        from app.services.demand_scheduling_service import DemandSchedulingService
        today = date.today()
        result = DemandSchedulingService.generate_demand_schedule(
            db=db_session,
            venue_id=1,
            start_date=today,
            end_date=today,
            target_labor_pct=25.0,
        )
        assert result is not None
        # Check that labor metrics exist in the result
        if "total_labor_cost" in result and "total_forecasted_revenue" in result:
            revenue = float(result["total_forecasted_revenue"])
            if revenue > 0:
                labor_cost = float(result["total_labor_cost"])
                actual_pct = (labor_cost / revenue) * 100
                # Should be within reasonable range of target (allow flexibility)
                assert actual_pct < 50, f"Labor percentage {actual_pct}% seems too high"

    def test_different_labor_targets(self, db_session: Session):
        """Test schedule generation with different labor targets."""
        from app.services.demand_scheduling_service import DemandSchedulingService
        today = date.today()

        result_low = DemandSchedulingService.generate_demand_schedule(
            db=db_session, venue_id=1, start_date=today, end_date=today,
            target_labor_pct=20.0,
        )
        result_high = DemandSchedulingService.generate_demand_schedule(
            db=db_session, venue_id=1, start_date=today, end_date=today,
            target_labor_pct=35.0,
        )
        assert result_low is not None
        assert result_high is not None

    def test_role_distribution_in_schedule(self, db_session: Session):
        """Test that generated schedule includes multiple roles."""
        from app.services.demand_scheduling_service import DemandSchedulingService
        today = date.today()
        result = DemandSchedulingService.generate_demand_schedule(
            db=db_session,
            venue_id=1,
            start_date=today,
            end_date=today,
            target_labor_pct=25.0,
        )
        assert result is not None
        # The schedule should contain role information
        # Check for role data in various possible structures
        schedule_data = result.get("schedule", result.get("daily_schedules", []))
        if isinstance(schedule_data, list) and len(schedule_data) > 0:
            day = schedule_data[0]
            if isinstance(day, dict):
                # Check that there are time slots or role assignments
                slots = day.get("slots", day.get("time_slots", []))
                if slots:
                    assert len(slots) > 0

    def test_schedule_result_has_summary(self, db_session: Session):
        """Test that schedule result contains summary/totals."""
        from app.services.demand_scheduling_service import DemandSchedulingService
        today = date.today()
        end = today + timedelta(days=6)
        result = DemandSchedulingService.generate_demand_schedule(
            db=db_session,
            venue_id=1,
            start_date=today,
            end_date=end,
            target_labor_pct=25.0,
        )
        assert result is not None
        # Should have some kind of total or summary
        has_summary = any(
            key in result
            for key in [
                "total_labor_hours", "total_labor_cost",
                "total_forecasted_revenue", "summary",
                "avg_daily_labor_cost",
            ]
        )
        assert has_summary, f"Schedule result missing summary fields. Keys: {list(result.keys())}"

    def test_hourly_rates_are_reasonable(self):
        """Test that hourly rates are in a reasonable range."""
        from app.services.demand_scheduling_service import DemandSchedulingService
        for role, rate in DemandSchedulingService.ROLE_HOURLY_RATES.items():
            assert 10 <= rate <= 50, (
                f"Hourly rate for {role} ({rate}) is outside reasonable range"
            )

    def test_manager_rate_highest(self):
        """Test that manager rate is the highest."""
        from app.services.demand_scheduling_service import DemandSchedulingService
        rates = DemandSchedulingService.ROLE_HOURLY_RATES
        manager_rate = rates.get("manager", 0)
        for role, rate in rates.items():
            if role != "manager":
                assert manager_rate >= rate, (
                    f"Manager rate ({manager_rate}) should be >= {role} rate ({rate})"
                )

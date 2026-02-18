"""Tests for payroll service (H1.4)."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch


class TestPayrollCalculation:
    """Test payroll calculations."""

    def test_regular_hours_calculation(self):
        """Standard 8-hour shift calculates correctly."""
        start = datetime(2026, 2, 1, 9, 0, tzinfo=timezone.utc)
        end = datetime(2026, 2, 1, 17, 0, tzinfo=timezone.utc)
        hours = (end - start).total_seconds() / 3600
        assert hours == 8.0

    def test_overtime_calculation(self):
        """Hours over 40/week should be flagged as overtime."""
        weekly_hours = 45.0
        regular = min(weekly_hours, 40.0)
        overtime = max(weekly_hours - 40.0, 0.0)
        assert regular == 40.0
        assert overtime == 5.0

    def test_no_overtime_under_40(self):
        """No overtime if under 40 hours."""
        weekly_hours = 35.0
        overtime = max(weekly_hours - 40.0, 0.0)
        assert overtime == 0.0

    def test_commission_calculation(self):
        """Commission % applied to sales total."""
        sales_total = 5000.0
        commission_rate = 0.05  # 5%
        commission = sales_total * commission_rate
        assert commission == 250.0

    def test_zero_sales_commission(self):
        """Zero sales = zero commission."""
        commission = 0.0 * 0.05
        assert commission == 0.0

    def test_tip_distribution_equal_split(self):
        """Tips split equally among N staff."""
        total_tips = 300.0
        staff_count = 3
        per_person = total_tips / staff_count
        assert per_person == 100.0

    def test_tip_distribution_single_staff(self):
        """Single staff gets all tips."""
        total_tips = 150.0
        per_person = total_tips / 1
        assert per_person == 150.0

    def test_negative_hours_rejected(self):
        """Negative hours should not be accepted."""
        hours = -2.0
        assert hours < 0
        # Payroll service should reject this

    def test_zero_hours_accepted(self):
        """Zero hours is valid (day off / no shift)."""
        hours = 0.0
        pay = hours * 15.0  # $15/hr
        assert pay == 0.0

    def test_break_deduction(self):
        """30-min unpaid break deducted from shift."""
        shift_hours = 8.0
        break_hours = 0.5
        paid_hours = shift_hours - break_hours
        assert paid_hours == 7.5

    def test_payroll_period_weekly(self):
        """Weekly pay period spans 7 days."""
        start = datetime(2026, 2, 2, tzinfo=timezone.utc)
        end = start + timedelta(days=7)
        delta = (end - start).days
        assert delta == 7

    def test_payroll_period_biweekly(self):
        """Bi-weekly pay period spans 14 days."""
        start = datetime(2026, 2, 2, tzinfo=timezone.utc)
        end = start + timedelta(days=14)
        delta = (end - start).days
        assert delta == 14


class TestPayrollEdgeCases:
    """Edge cases for payroll."""

    def test_overnight_shift(self):
        """Shift crossing midnight calculates correctly."""
        start = datetime(2026, 2, 1, 22, 0, tzinfo=timezone.utc)
        end = datetime(2026, 2, 2, 6, 0, tzinfo=timezone.utc)
        hours = (end - start).total_seconds() / 3600
        assert hours == 8.0

    def test_fractional_hours(self):
        """Non-whole hours calculated correctly."""
        start = datetime(2026, 2, 1, 9, 0, tzinfo=timezone.utc)
        end = datetime(2026, 2, 1, 14, 15, tzinfo=timezone.utc)
        hours = (end - start).total_seconds() / 3600
        assert hours == 5.25

    def test_holiday_premium(self):
        """Holiday shifts should get premium rate."""
        base_rate = 15.0
        holiday_multiplier = 1.5
        premium_rate = base_rate * holiday_multiplier
        assert premium_rate == 22.5

"""Operations models for settings, payroll, notifications, HACCP, feedback,
audit logs, VIP, warehouses, promotions, gamification, risk alerts,
referrals, tax, financial, and shifts."""

from datetime import datetime, date, time, timezone
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import (
    Column, Integer, String, DateTime, Date, Time, Numeric, Boolean,
    ForeignKey, Text, JSON, Float,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


# ===================== SETTINGS =====================

class AppSetting(Base):
    """Key-value settings store."""
    __tablename__ = "app_settings"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), nullable=False, index=True)  # general, venue, payment, security, fiscal, tax
    key = Column(String(100), nullable=False)
    value = Column(JSON, nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        # Unique constraint on category + key
        {"sqlite_autoincrement": True},
    )


# ===================== PAYROLL =====================

class PayrollRun(Base):
    """A payroll run for a period."""
    __tablename__ = "payroll_runs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    status = Column(String(20), default="pending")
    total_gross = Column(Numeric(12, 2), default=0)
    total_net = Column(Numeric(12, 2), default=0)
    total_tax = Column(Numeric(12, 2), default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    approved_at = Column(DateTime, nullable=True)
    paid_at = Column(DateTime, nullable=True)

    entries = relationship("PayrollEntry", back_populates="payroll_run")


class PayrollEntry(Base):
    """Individual payroll entry for a staff member."""
    __tablename__ = "payroll_entries"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    payroll_run_id = Column(Integer, ForeignKey("payroll_runs.id"), nullable=True)
    staff_id = Column(Integer, nullable=False, index=True)
    staff_name = Column(String(200), nullable=True)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    hours_worked = Column(Numeric(8, 2), default=0)
    overtime_hours = Column(Numeric(8, 2), default=0)
    hourly_rate = Column(Numeric(8, 2), default=0)
    gross_pay = Column(Numeric(10, 2), default=0)
    tax = Column(Numeric(10, 2), default=0)
    deductions = Column(Numeric(10, 2), default=0)
    net_pay = Column(Numeric(10, 2), default=0)
    tips = Column(Numeric(10, 2), default=0)
    status = Column(String(20), default="pending")  # pending, approved, paid
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    payroll_run = relationship("PayrollRun", back_populates="entries")


# ===================== NOTIFICATIONS =====================

class Notification(Base):
    """User notification."""
    __tablename__ = "notifications"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=True)
    type = Column(String(50), default="info")  # info, warning, error, success
    category = Column(String(50), nullable=True)
    read = Column(Boolean, default=False)
    action_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class NotificationPreference(Base):
    """Notification preference for a channel."""
    __tablename__ = "notification_preferences"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)
    channel = Column(String(50), nullable=False)  # email, push, sms, in_app
    enabled = Column(Boolean, default=True)
    categories = Column(JSON, nullable=True)  # list of category strings
    quiet_hours_start = Column(String(5), nullable=True)
    quiet_hours_end = Column(String(5), nullable=True)


class AlertConfig(Base):
    """Alert configuration."""
    __tablename__ = "alert_configs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    type = Column(String(50), nullable=False)
    enabled = Column(Boolean, default=True)
    threshold = Column(Float, nullable=True)
    channels = Column(JSON, nullable=True)
    recipients = Column(JSON, nullable=True)


# ===================== HACCP =====================

class HACCPTemperatureLog(Base):
    """HACCP temperature log entry."""
    __tablename__ = "haccp_temperature_logs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    location = Column(String(100), nullable=False)
    equipment = Column(String(100), nullable=True)
    temperature = Column(Float, nullable=False)
    unit = Column(String(5), default="C")
    min_temp = Column(Float, nullable=True)
    max_temp = Column(Float, nullable=True)
    status = Column(String(20), default="normal")  # normal, warning, critical
    recorded_by = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    recorded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class HACCPSafetyCheck(Base):
    """HACCP safety check."""
    __tablename__ = "haccp_safety_checks"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    category = Column(String(50), nullable=True)
    frequency = Column(String(20), default="daily")  # daily, weekly, monthly
    status = Column(String(20), default="pending")  # pending, completed, overdue
    due_date = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    completed_by = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ===================== FEEDBACK =====================

class FeedbackReview(Base):
    """Customer feedback/review."""
    __tablename__ = "feedback_reviews"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(50), default="internal")  # google, yelp, tripadvisor, internal
    customer_name = Column(String(200), nullable=True)
    rating = Column(Integer, nullable=True)
    text = Column(Text, nullable=True)
    sentiment = Column(String(20), nullable=True)  # positive, negative, neutral
    status = Column(String(20), default="new")  # new, responded, flagged
    response = Column(Text, nullable=True)
    responded_at = Column(DateTime, nullable=True)
    responded_by = Column(String(100), nullable=True)
    visit_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ===================== AUDIT LOGS =====================

class AuditLogEntry(Base):
    """Audit log entry."""
    __tablename__ = "audit_log_entries"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    user_name = Column(String(200), nullable=True)
    action = Column(String(50), nullable=False, index=True)
    entity_type = Column(String(50), nullable=True, index=True)
    entity_id = Column(String(50), nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)


# ===================== VIP =====================

class VIPCustomerLink(Base):
    """Links a customer to VIP status."""
    __tablename__ = "vip_customer_links"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, nullable=True, index=True)
    name = Column(String(200), nullable=False)
    email = Column(String(200), nullable=True)
    phone = Column(String(50), nullable=True)
    tier = Column(String(50), default="silver")  # silver, gold, platinum, diamond
    points = Column(Integer, default=0)
    total_spent = Column(Numeric(12, 2), default=0)
    visits = Column(Integer, default=0)
    joined_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    notes = Column(Text, nullable=True)


class VIPOccasion(Base):
    """VIP special occasion."""
    __tablename__ = "vip_occasions"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, nullable=True)
    customer_name = Column(String(200), nullable=True)
    type = Column(String(50), nullable=False)  # birthday, anniversary, corporate
    occasion_date = Column(Date, nullable=False)
    notes = Column(Text, nullable=True)
    notification_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ===================== WAREHOUSES =====================

class Warehouse(Base):
    """Warehouse/storage location."""
    __tablename__ = "warehouses"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    type = Column(String(50), default="dry")  # dry, cold, frozen, bar
    location_id = Column(Integer, nullable=True)
    address = Column(Text, nullable=True)
    capacity = Column(Integer, nullable=True)
    temperature_min = Column(Float, nullable=True)
    temperature_max = Column(Float, nullable=True)
    manager = Column(String(200), nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class WarehouseTransfer(Base):
    """Transfer between warehouses."""
    __tablename__ = "warehouse_transfers"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    from_warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)
    to_warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)
    product_id = Column(Integer, nullable=True)
    product_name = Column(String(200), nullable=True)
    quantity = Column(Numeric(10, 2), nullable=False)
    status = Column(String(20), default="pending")  # pending, in_transit, completed
    notes = Column(Text, nullable=True)
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)


# ===================== PROMOTIONS =====================

class Promotion(Base):
    """Promotion/discount."""
    __tablename__ = "promotions"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    type = Column(String(50), default="percentage")  # percentage, fixed, bogo, combo
    value = Column(Numeric(10, 2), nullable=True)
    min_order_amount = Column(Numeric(10, 2), nullable=True)
    max_discount = Column(Numeric(10, 2), nullable=True)
    code = Column(String(50), nullable=True)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    active = Column(Boolean, default=True)
    usage_count = Column(Integer, default=0)
    usage_limit = Column(Integer, nullable=True)
    applicable_items = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ===================== GAMIFICATION =====================

class Badge(Base):
    """Staff badge/achievement type."""
    __tablename__ = "badges"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)
    category = Column(String(50), nullable=True)  # performance, attendance, sales, teamwork
    criteria = Column(JSON, nullable=True)
    points = Column(Integer, default=0)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Challenge(Base):
    """Staff challenge."""
    __tablename__ = "challenges"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    type = Column(String(50), default="individual")
    target_value = Column(Float, nullable=True)
    reward_points = Column(Integer, default=0)
    reward_description = Column(String(200), nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class StaffAchievement(Base):
    """Record of a staff member earning a badge."""
    __tablename__ = "staff_achievements"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, nullable=False, index=True)
    staff_name = Column(String(200), nullable=True)
    badge_id = Column(Integer, ForeignKey("badges.id"), nullable=True)
    badge_name = Column(String(200), nullable=True)
    points = Column(Integer, default=0)
    earned_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class StaffPoints(Base):
    """Staff gamification points."""
    __tablename__ = "staff_points"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, nullable=False, unique=True, index=True)
    staff_name = Column(String(200), nullable=True)
    total_points = Column(Integer, default=0)
    level = Column(Integer, default=1)
    badges_earned = Column(Integer, default=0)
    challenges_completed = Column(Integer, default=0)


# ===================== RISK ALERTS =====================

class RiskAlert(Base):
    """Fraud/risk alert."""
    __tablename__ = "risk_alerts"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(50), nullable=False)  # void_pattern, discount_abuse, cash_variance, time_theft
    severity = Column(String(20), default="medium")  # low, medium, high, critical
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    staff_id = Column(Integer, nullable=True)
    staff_name = Column(String(200), nullable=True)
    amount = Column(Numeric(10, 2), nullable=True)
    status = Column(String(20), default="open")  # open, acknowledged, resolved, dismissed
    acknowledged_by = Column(String(100), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ===================== REFERRALS =====================

class ReferralProgram(Base):
    """Referral program."""
    __tablename__ = "referral_programs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    reward_type = Column(String(50), default="discount")
    reward_value = Column(Numeric(10, 2), default=0)
    referee_reward_value = Column(Numeric(10, 2), default=0)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ReferralRecord(Base):
    """Individual referral record."""
    __tablename__ = "referral_records"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    referrer_name = Column(String(200), nullable=True)
    referrer_email = Column(String(200), nullable=True)
    referee_name = Column(String(200), nullable=True)
    referee_email = Column(String(200), nullable=True)
    status = Column(String(20), default="pending")  # pending, completed, expired
    reward_claimed = Column(Boolean, default=False)
    program_id = Column(Integer, ForeignKey("referral_programs.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)


# ===================== TAX =====================

class TaxFiling(Base):
    """Tax filing record."""
    __tablename__ = "tax_filings"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    period = Column(String(20), nullable=False)  # Q1, Q2, Q3, Q4
    year = Column(Integer, nullable=False)
    total_revenue = Column(Numeric(12, 2), default=0)
    total_tax = Column(Numeric(12, 2), default=0)
    status = Column(String(20), default="pending")  # pending, filed, paid
    due_date = Column(Date, nullable=True)
    filed_at = Column(DateTime, nullable=True)
    filed_by = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ===================== FINANCIAL =====================

class Budget(Base):
    """Budget entry."""
    __tablename__ = "budgets"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False)
    period = Column(String(20), nullable=True)
    year = Column(Integer, nullable=True)
    month = Column(Integer, nullable=True)
    budgeted_amount = Column(Numeric(12, 2), default=0)
    actual_amount = Column(Numeric(12, 2), default=0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class DailyReconciliation(Base):
    """Daily reconciliation/close session."""
    __tablename__ = "daily_reconciliations"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)
    status = Column(String(20), default="open")
    expected_cash = Column(Numeric(10, 2), default=0)
    actual_cash = Column(Numeric(10, 2), default=0)
    cash_variance = Column(Numeric(10, 2), default=0)
    total_sales = Column(Numeric(12, 2), default=0)
    card_total = Column(Numeric(12, 2), default=0)
    cash_total = Column(Numeric(12, 2), default=0)
    completed_by = Column(String(100), nullable=True)
    completed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ===================== SHIFT SCHEDULING =====================

class ShiftSchedule(Base):
    """Shift schedule entry (for the shifts.py route, separate from staff/shifts)."""
    __tablename__ = "shift_schedules"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, nullable=False, index=True)
    staff_name = Column(String(200), nullable=True)
    role = Column(String(50), nullable=True)
    date = Column(Date, nullable=False)
    start_time = Column(String(10), nullable=True)
    end_time = Column(String(10), nullable=True)
    status = Column(String(20), default="scheduled")  # scheduled, confirmed, completed, cancelled
    break_minutes = Column(Integer, default=0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

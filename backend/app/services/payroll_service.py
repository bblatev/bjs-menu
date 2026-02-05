"""Payroll Service.

Handles staff payroll calculations, pay periods, wages, and deductions.
"""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta, timezone
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class PayFrequency(str, Enum):
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    SEMIMONTHLY = "semimonthly"
    MONTHLY = "monthly"


class PayrollStatus(str, Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DeductionType(str, Enum):
    TAX_FEDERAL = "tax_federal"
    TAX_STATE = "tax_state"
    TAX_LOCAL = "tax_local"
    SOCIAL_SECURITY = "social_security"
    MEDICARE = "medicare"
    HEALTH_INSURANCE = "health_insurance"
    RETIREMENT_401K = "retirement_401k"
    GARNISHMENT = "garnishment"
    OTHER = "other"


@dataclass
class StaffMember:
    """Staff member payroll information."""
    id: str
    name: str
    email: str
    role: str
    hourly_rate: float
    salary: Optional[float] = None  # For salaried employees
    is_hourly: bool = True
    tax_filing_status: str = "single"
    federal_allowances: int = 1
    state_allowances: int = 1
    hire_date: date = field(default_factory=date.today)
    department: str = "general"


@dataclass
class TimeEntry:
    """Time tracking entry for payroll."""
    id: str
    staff_id: str
    date: date
    clock_in: datetime
    clock_out: Optional[datetime] = None
    break_minutes: int = 0
    regular_hours: float = 0
    overtime_hours: float = 0
    tips: float = 0
    notes: str = ""


@dataclass
class Deduction:
    """Payroll deduction."""
    type: DeductionType
    amount: float
    is_percentage: bool = False
    description: str = ""


@dataclass
class PayStub:
    """Individual pay stub for a staff member."""
    id: str
    staff_id: str
    staff_name: str
    pay_period_id: str
    pay_period_start: date
    pay_period_end: date
    regular_hours: float
    overtime_hours: float
    regular_pay: float
    overtime_pay: float
    tips: float
    gross_pay: float
    deductions: List[Deduction]
    total_deductions: float
    net_pay: float
    payment_method: str = "direct_deposit"
    payment_date: Optional[date] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PayPeriod:
    """Pay period containing all pay stubs."""
    id: str
    start_date: date
    end_date: date
    pay_date: date
    status: PayrollStatus
    total_gross: float = 0
    total_deductions: float = 0
    total_net: float = 0
    staff_count: int = 0
    pay_stubs: List[PayStub] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None


class PayrollService:
    """Service for managing payroll operations.

    Provides:
    - Pay period management
    - Time tracking integration
    - Wage calculations (regular + overtime)
    - Tax and deduction calculations
    - Pay stub generation
    - Payroll reports
    """

    OVERTIME_MULTIPLIER = 1.5
    STANDARD_HOURS_PER_WEEK = 40

    def __init__(self):
        # In-memory storage (use database in production)
        self._staff: Dict[str, StaffMember] = {}
        self._time_entries: Dict[str, TimeEntry] = {}
        self._pay_periods: Dict[str, PayPeriod] = {}
        self._pay_stubs: Dict[str, PayStub] = {}

        # Default tax rates (simplified)
        self._tax_rates = {
            "federal": 0.12,  # 12% federal
            "state": 0.05,    # 5% state
            "social_security": 0.062,  # 6.2%
            "medicare": 0.0145,  # 1.45%
        }

        self._settings = {
            "pay_frequency": PayFrequency.BIWEEKLY,
            "overtime_after_hours": 40,
            "overtime_multiplier": 1.5,
        }

        # Initialize with sample data
        self._init_sample_data()

    def _init_sample_data(self):
        """Initialize sample data for demonstration."""
        # Sample staff
        staff_data = [
            ("S001", "John Smith", "john@example.com", "Server", 15.00),
            ("S002", "Maria Garcia", "maria@example.com", "Bartender", 18.00),
            ("S003", "David Chen", "david@example.com", "Line Cook", 17.50),
            ("S004", "Sarah Johnson", "sarah@example.com", "Host", 14.00),
            ("S005", "Michael Brown", "michael@example.com", "Manager", 25.00),
        ]

        for sid, name, email, role, rate in staff_data:
            self._staff[sid] = StaffMember(
                id=sid,
                name=name,
                email=email,
                role=role,
                hourly_rate=rate,
            )

    # =========================================================================
    # Staff Management
    # =========================================================================

    def get_staff(self, staff_id: str) -> Optional[StaffMember]:
        """Get a staff member by ID."""
        return self._staff.get(staff_id)

    def list_staff(self) -> List[StaffMember]:
        """List all staff members."""
        return list(self._staff.values())

    def add_staff(self, staff: StaffMember) -> StaffMember:
        """Add a new staff member."""
        self._staff[staff.id] = staff
        return staff

    def update_staff(self, staff_id: str, **updates) -> Optional[StaffMember]:
        """Update staff member details."""
        staff = self._staff.get(staff_id)
        if not staff:
            return None

        for key, value in updates.items():
            if hasattr(staff, key) and value is not None:
                setattr(staff, key, value)

        return staff

    # =========================================================================
    # Time Tracking
    # =========================================================================

    def add_time_entry(
        self,
        staff_id: str,
        date: date,
        clock_in: datetime,
        clock_out: Optional[datetime] = None,
        break_minutes: int = 0,
        tips: float = 0,
    ) -> Optional[TimeEntry]:
        """Add a time entry for a staff member."""
        if staff_id not in self._staff:
            return None

        entry_id = f"TE-{uuid.uuid4().hex[:8]}"

        regular_hours = 0.0
        overtime_hours = 0.0

        if clock_out:
            total_minutes = (clock_out - clock_in).total_seconds() / 60
            worked_minutes = max(0, total_minutes - break_minutes)
            worked_hours = worked_minutes / 60

            # Calculate overtime (simplified - per day basis)
            if worked_hours > 8:
                regular_hours = 8.0
                overtime_hours = worked_hours - 8.0
            else:
                regular_hours = worked_hours

        entry = TimeEntry(
            id=entry_id,
            staff_id=staff_id,
            date=date,
            clock_in=clock_in,
            clock_out=clock_out,
            break_minutes=break_minutes,
            regular_hours=round(regular_hours, 2),
            overtime_hours=round(overtime_hours, 2),
            tips=tips,
        )

        self._time_entries[entry_id] = entry
        return entry

    def get_time_entries(
        self,
        staff_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[TimeEntry]:
        """Get time entries with optional filters."""
        entries = list(self._time_entries.values())

        if staff_id:
            entries = [e for e in entries if e.staff_id == staff_id]

        if start_date:
            entries = [e for e in entries if e.date >= start_date]

        if end_date:
            entries = [e for e in entries if e.date <= end_date]

        return sorted(entries, key=lambda e: (e.date, e.clock_in))

    # =========================================================================
    # Pay Period Management
    # =========================================================================

    def create_pay_period(
        self,
        start_date: date,
        end_date: date,
        pay_date: date,
    ) -> PayPeriod:
        """Create a new pay period."""
        period_id = f"PP-{uuid.uuid4().hex[:8]}"

        period = PayPeriod(
            id=period_id,
            start_date=start_date,
            end_date=end_date,
            pay_date=pay_date,
            status=PayrollStatus.DRAFT,
        )

        self._pay_periods[period_id] = period
        return period

    def get_pay_period(self, period_id: str) -> Optional[PayPeriod]:
        """Get a pay period by ID."""
        return self._pay_periods.get(period_id)

    def list_pay_periods(
        self,
        status: Optional[PayrollStatus] = None,
        limit: int = 20,
    ) -> List[PayPeriod]:
        """List pay periods with optional filter."""
        periods = list(self._pay_periods.values())

        if status:
            periods = [p for p in periods if p.status == status]

        return sorted(periods, key=lambda p: p.start_date, reverse=True)[:limit]

    def calculate_payroll(self, period_id: str) -> Optional[PayPeriod]:
        """Calculate payroll for all staff in a pay period."""
        period = self._pay_periods.get(period_id)
        if not period:
            return None

        if period.status not in (PayrollStatus.DRAFT, PayrollStatus.PENDING):
            return period

        pay_stubs = []
        total_gross = 0
        total_deductions = 0
        total_net = 0

        for staff in self._staff.values():
            # Get time entries for this staff in this period
            entries = self.get_time_entries(
                staff_id=staff.id,
                start_date=period.start_date,
                end_date=period.end_date,
            )

            # Calculate hours and pay
            regular_hours = sum(e.regular_hours for e in entries)
            overtime_hours = sum(e.overtime_hours for e in entries)
            tips = sum(e.tips for e in entries)

            regular_pay = regular_hours * staff.hourly_rate
            overtime_pay = overtime_hours * staff.hourly_rate * self.OVERTIME_MULTIPLIER
            gross_pay = regular_pay + overtime_pay + tips

            # Calculate deductions
            deductions = self._calculate_deductions(gross_pay, staff)
            total_ded = sum(d.amount for d in deductions)
            net_pay = gross_pay - total_ded

            # Create pay stub
            stub = PayStub(
                id=f"PS-{uuid.uuid4().hex[:8]}",
                staff_id=staff.id,
                staff_name=staff.name,
                pay_period_id=period_id,
                pay_period_start=period.start_date,
                pay_period_end=period.end_date,
                regular_hours=round(regular_hours, 2),
                overtime_hours=round(overtime_hours, 2),
                regular_pay=round(regular_pay, 2),
                overtime_pay=round(overtime_pay, 2),
                tips=round(tips, 2),
                gross_pay=round(gross_pay, 2),
                deductions=deductions,
                total_deductions=round(total_ded, 2),
                net_pay=round(net_pay, 2),
                payment_date=period.pay_date,
            )

            pay_stubs.append(stub)
            self._pay_stubs[stub.id] = stub

            total_gross += gross_pay
            total_deductions += total_ded
            total_net += net_pay

        # Update period
        period.pay_stubs = pay_stubs
        period.total_gross = round(total_gross, 2)
        period.total_deductions = round(total_deductions, 2)
        period.total_net = round(total_net, 2)
        period.staff_count = len(pay_stubs)
        period.status = PayrollStatus.PENDING

        return period

    def _calculate_deductions(
        self,
        gross_pay: float,
        staff: StaffMember,
    ) -> List[Deduction]:
        """Calculate tax and other deductions."""
        deductions = []

        # Federal tax (simplified flat rate)
        fed_tax = gross_pay * self._tax_rates["federal"]
        deductions.append(Deduction(
            type=DeductionType.TAX_FEDERAL,
            amount=round(fed_tax, 2),
            description="Federal Income Tax",
        ))

        # State tax
        state_tax = gross_pay * self._tax_rates["state"]
        deductions.append(Deduction(
            type=DeductionType.TAX_STATE,
            amount=round(state_tax, 2),
            description="State Income Tax",
        ))

        # Social Security
        ss_tax = gross_pay * self._tax_rates["social_security"]
        deductions.append(Deduction(
            type=DeductionType.SOCIAL_SECURITY,
            amount=round(ss_tax, 2),
            description="Social Security",
        ))

        # Medicare
        medicare_tax = gross_pay * self._tax_rates["medicare"]
        deductions.append(Deduction(
            type=DeductionType.MEDICARE,
            amount=round(medicare_tax, 2),
            description="Medicare",
        ))

        return deductions

    def approve_payroll(
        self,
        period_id: str,
        approved_by: str,
    ) -> Optional[PayPeriod]:
        """Approve a payroll period for processing."""
        period = self._pay_periods.get(period_id)
        if not period:
            return None

        if period.status != PayrollStatus.PENDING:
            return period

        period.status = PayrollStatus.APPROVED
        period.approved_by = approved_by
        period.approved_at = datetime.now(timezone.utc)

        return period

    def process_payroll(self, period_id: str) -> Optional[PayPeriod]:
        """Process approved payroll (initiate payments)."""
        period = self._pay_periods.get(period_id)
        if not period:
            return None

        if period.status != PayrollStatus.APPROVED:
            return period

        period.status = PayrollStatus.PROCESSING

        # In production, this would integrate with payment provider
        # For now, simulate processing
        period.status = PayrollStatus.COMPLETED

        logger.info(f"Processed payroll {period_id}: {period.staff_count} staff, ${period.total_net:.2f} total")

        return period

    # =========================================================================
    # Pay Stubs
    # =========================================================================

    def get_pay_stub(self, stub_id: str) -> Optional[PayStub]:
        """Get a pay stub by ID."""
        return self._pay_stubs.get(stub_id)

    def get_staff_pay_stubs(
        self,
        staff_id: str,
        limit: int = 10,
    ) -> List[PayStub]:
        """Get pay stubs for a specific staff member."""
        stubs = [s for s in self._pay_stubs.values() if s.staff_id == staff_id]
        return sorted(stubs, key=lambda s: s.pay_period_end, reverse=True)[:limit]

    # =========================================================================
    # Reports
    # =========================================================================

    def get_payroll_summary(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """Get payroll summary statistics."""
        periods = list(self._pay_periods.values())

        if start_date:
            periods = [p for p in periods if p.start_date >= start_date]

        if end_date:
            periods = [p for p in periods if p.end_date <= end_date]

        completed = [p for p in periods if p.status == PayrollStatus.COMPLETED]

        return {
            "total_periods": len(periods),
            "completed_periods": len(completed),
            "total_gross": sum(p.total_gross for p in completed),
            "total_deductions": sum(p.total_deductions for p in completed),
            "total_net": sum(p.total_net for p in completed),
            "total_staff_payments": sum(p.staff_count for p in completed),
            "average_per_period": round(
                sum(p.total_net for p in completed) / len(completed), 2
            ) if completed else 0,
        }

    def get_labor_cost_report(
        self,
        start_date: date,
        end_date: date,
    ) -> Dict[str, Any]:
        """Get labor cost breakdown by department/role."""
        entries = self.get_time_entries(start_date=start_date, end_date=end_date)

        by_role: Dict[str, Dict[str, float]] = {}

        for entry in entries:
            staff = self._staff.get(entry.staff_id)
            if not staff:
                continue

            role = staff.role
            if role not in by_role:
                by_role[role] = {
                    "regular_hours": 0,
                    "overtime_hours": 0,
                    "regular_cost": 0,
                    "overtime_cost": 0,
                    "tips": 0,
                }

            by_role[role]["regular_hours"] += entry.regular_hours
            by_role[role]["overtime_hours"] += entry.overtime_hours
            by_role[role]["regular_cost"] += entry.regular_hours * staff.hourly_rate
            by_role[role]["overtime_cost"] += entry.overtime_hours * staff.hourly_rate * self.OVERTIME_MULTIPLIER
            by_role[role]["tips"] += entry.tips

        total_labor = sum(
            r["regular_cost"] + r["overtime_cost"]
            for r in by_role.values()
        )

        return {
            "period": {"start": str(start_date), "end": str(end_date)},
            "by_role": by_role,
            "total_labor_cost": round(total_labor, 2),
            "total_tips": round(sum(r["tips"] for r in by_role.values()), 2),
        }


# Singleton instance
_payroll_service: Optional[PayrollService] = None


def get_payroll_service() -> PayrollService:
    """Get the payroll service singleton."""
    global _payroll_service
    if _payroll_service is None:
        _payroll_service = PayrollService()
    return _payroll_service

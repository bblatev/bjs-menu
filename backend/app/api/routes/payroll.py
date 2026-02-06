"""Payroll API routes."""

from typing import List, Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter()


class PayrollEntry(BaseModel):
    id: str
    staff_id: str
    staff_name: str
    role: str
    period_start: str
    period_end: str
    regular_hours: float
    overtime_hours: float
    hourly_rate: float
    overtime_rate: float
    gross_pay: float
    deductions: float
    net_pay: float
    tips: float
    status: str  # pending, approved, paid


@router.get("/entries")
async def get_payroll_entries(period: str = Query(None)):
    """Get payroll entries."""
    return [
        PayrollEntry(id="1", staff_id="1", staff_name="John Doe", role="Server", period_start="2026-01-16", period_end="2026-01-31", regular_hours=80, overtime_hours=5, hourly_rate=12.50, overtime_rate=18.75, gross_pay=1093.75, deductions=164.06, net_pay=929.69, tips=450.00, status="approved"),
        PayrollEntry(id="2", staff_id="2", staff_name="Jane Smith", role="Bartender", period_start="2026-01-16", period_end="2026-01-31", regular_hours=80, overtime_hours=10, hourly_rate=14.00, overtime_rate=21.00, gross_pay=1330.00, deductions=199.50, net_pay=1130.50, tips=620.00, status="approved"),
        PayrollEntry(id="3", staff_id="3", staff_name="Mike Johnson", role="Chef", period_start="2026-01-16", period_end="2026-01-31", regular_hours=80, overtime_hours=8, hourly_rate=18.00, overtime_rate=27.00, gross_pay=1656.00, deductions=248.40, net_pay=1407.60, tips=0.00, status="pending"),
    ]


@router.get("/entries/{entry_id}")
async def get_payroll_entry(entry_id: str):
    """Get a specific payroll entry."""
    return PayrollEntry(id=entry_id, staff_id="1", staff_name="John Doe", role="Server", period_start="2026-01-16", period_end="2026-01-31", regular_hours=80, overtime_hours=5, hourly_rate=12.50, overtime_rate=18.75, gross_pay=1093.75, deductions=164.06, net_pay=929.69, tips=450.00, status="approved")


@router.post("/generate")
async def generate_payroll(period_start: str = Query(...), period_end: str = Query(...)):
    """Generate payroll for a period."""
    return {"success": True, "entries_created": 4, "total_gross": 5079.75}


@router.post("/entries/{entry_id}/approve")
async def approve_payroll_entry(entry_id: str):
    """Approve a payroll entry."""
    return {"success": True}


@router.post("/approve-all")
async def approve_all_payroll():
    """Approve all pending payroll entries."""
    return {"success": True, "approved_count": 3}


@router.post("/entries/{entry_id}/pay")
async def mark_as_paid(entry_id: str):
    """Mark a payroll entry as paid."""
    return {"success": True}


@router.get("/runs")
async def get_payroll_runs():
    """Get payroll runs."""
    return []


@router.get("/employees")
async def get_payroll_employees():
    """Get payroll employees."""
    return []

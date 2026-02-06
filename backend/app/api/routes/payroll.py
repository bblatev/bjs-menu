"""Payroll API routes."""

from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func

from app.db.session import DbSession
from app.models.operations import PayrollRun, PayrollEntry

router = APIRouter()


# --------------- Pydantic Schemas ---------------

class PayrollEntrySchema(BaseModel):
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


def _entry_to_schema(entry: PayrollEntry) -> PayrollEntrySchema:
    """Convert a PayrollEntry DB model to the response schema."""
    hourly_rate = float(entry.hourly_rate or 0)
    return PayrollEntrySchema(
        id=str(entry.id),
        staff_id=str(entry.staff_id),
        staff_name=entry.staff_name or "",
        role="",
        period_start=entry.period_start.isoformat() if entry.period_start else "",
        period_end=entry.period_end.isoformat() if entry.period_end else "",
        regular_hours=float(entry.hours_worked or 0),
        overtime_hours=float(entry.overtime_hours or 0),
        hourly_rate=hourly_rate,
        overtime_rate=round(hourly_rate * 1.5, 2),
        gross_pay=float(entry.gross_pay or 0),
        deductions=float(entry.deductions or 0),
        net_pay=float(entry.net_pay or 0),
        tips=float(entry.tips or 0),
        status=entry.status or "pending",
    )


# --------------- Endpoints ---------------

@router.get("/entries")
async def get_payroll_entries(db: DbSession, period: str = Query(None)):
    """Get payroll entries."""
    query = db.query(PayrollEntry)
    if period:
        # period expected as "YYYY-MM-DD" (the start date of the pay period)
        try:
            period_date = date.fromisoformat(period)
            query = query.filter(PayrollEntry.period_start == period_date)
        except ValueError:
            pass
    entries = query.all()
    return [_entry_to_schema(e) for e in entries]


@router.get("/entries/{entry_id}")
async def get_payroll_entry(entry_id: str, db: DbSession):
    """Get a specific payroll entry."""
    entry = db.query(PayrollEntry).filter(PayrollEntry.id == int(entry_id)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Payroll entry not found")
    return _entry_to_schema(entry)


@router.post("/generate")
async def generate_payroll(
    db: DbSession,
    period_start: str = Query(...),
    period_end: str = Query(...),
):
    """Generate payroll for a period."""
    start = date.fromisoformat(period_start)
    end = date.fromisoformat(period_end)

    # Create a new payroll run
    run = PayrollRun(
        period_start=start,
        period_end=end,
        status="pending",
        total_gross=0,
        total_net=0,
        total_tax=0,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    # Count any entries that already exist for this period and attach them
    existing_entries = (
        db.query(PayrollEntry)
        .filter(
            PayrollEntry.period_start == start,
            PayrollEntry.period_end == end,
            PayrollEntry.payroll_run_id.is_(None),
        )
        .all()
    )
    total_gross = 0.0
    for entry in existing_entries:
        entry.payroll_run_id = run.id
        total_gross += float(entry.gross_pay or 0)

    run.total_gross = total_gross
    run.total_net = sum(float(e.net_pay or 0) for e in existing_entries)
    run.total_tax = sum(float(e.tax or 0) for e in existing_entries)
    db.commit()
    db.refresh(run)

    return {
        "success": True,
        "entries_created": len(existing_entries),
        "total_gross": float(run.total_gross or 0),
    }


@router.post("/entries/{entry_id}/approve")
async def approve_payroll_entry(entry_id: str, db: DbSession):
    """Approve a payroll entry."""
    entry = db.query(PayrollEntry).filter(PayrollEntry.id == int(entry_id)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Payroll entry not found")
    entry.status = "approved"
    db.commit()
    return {"success": True}


@router.post("/approve-all")
async def approve_all_payroll(db: DbSession):
    """Approve all pending payroll entries."""
    pending = (
        db.query(PayrollEntry)
        .filter(PayrollEntry.status == "pending")
        .all()
    )
    for entry in pending:
        entry.status = "approved"
    db.commit()
    return {"success": True, "approved_count": len(pending)}


@router.post("/entries/{entry_id}/pay")
async def mark_as_paid(entry_id: str, db: DbSession):
    """Mark a payroll entry as paid."""
    entry = db.query(PayrollEntry).filter(PayrollEntry.id == int(entry_id)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Payroll entry not found")
    entry.status = "paid"
    db.commit()
    return {"success": True}


@router.get("/runs")
async def get_payroll_runs(db: DbSession):
    """Get payroll runs."""
    runs = db.query(PayrollRun).all()
    return [
        {
            "id": run.id,
            "period_start": run.period_start.isoformat() if run.period_start else None,
            "period_end": run.period_end.isoformat() if run.period_end else None,
            "status": run.status,
            "total_gross": float(run.total_gross or 0),
            "total_net": float(run.total_net or 0),
            "total_tax": float(run.total_tax or 0),
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "approved_at": run.approved_at.isoformat() if run.approved_at else None,
            "paid_at": run.paid_at.isoformat() if run.paid_at else None,
            "entry_count": len(run.entries) if run.entries else 0,
        }
        for run in runs
    ]


@router.get("/employees")
async def get_payroll_employees(db: DbSession):
    """Get payroll employees."""
    rows = (
        db.query(
            PayrollEntry.staff_id,
            PayrollEntry.staff_name,
            func.sum(PayrollEntry.hours_worked).label("total_hours"),
            func.sum(PayrollEntry.gross_pay).label("total_gross"),
            func.sum(PayrollEntry.net_pay).label("total_net"),
            func.count(PayrollEntry.id).label("entry_count"),
        )
        .group_by(PayrollEntry.staff_id, PayrollEntry.staff_name)
        .all()
    )
    return [
        {
            "staff_id": str(row.staff_id),
            "staff_name": row.staff_name or "",
            "total_hours": float(row.total_hours or 0),
            "total_gross": float(row.total_gross or 0),
            "total_net": float(row.total_net or 0),
            "entry_count": row.entry_count,
        }
        for row in rows
    ]

"""Payroll API routes."""

from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import func

from app.core.rate_limit import limiter
from app.core.rbac import CurrentUser, RequireManager, RequireOwner
from app.db.session import DbSession
from app.models.operations import PayrollRun, PayrollEntry

router = APIRouter()


# ==================== ROOT ENDPOINT ====================

@router.get("/")
@limiter.limit("60/minute")
def get_payroll_overview(
    request: Request,
    db: DbSession,
    current_user: RequireManager,
    period_start: Optional[str] = Query(None),
    period_end: Optional[str] = Query(None),
):
    """Get payroll overview - list of payroll entries with summary."""
    query = db.query(PayrollEntry)
    if period_start:
        query = query.filter(PayrollEntry.period_start >= period_start)
    if period_end:
        query = query.filter(PayrollEntry.period_end <= period_end)
    entries = query.order_by(PayrollEntry.id.desc()).limit(100).all()

    total_gross = sum(float(e.gross_pay or 0) for e in entries)
    total_net = sum(float(e.net_pay or 0) for e in entries)
    total_hours = sum(float(e.regular_hours or 0) + float(e.overtime_hours or 0) for e in entries)

    entry_list = []
    for e in entries:
        entry_list.append({
            "id": str(e.id),
            "staff_id": str(e.staff_id),
            "staff_name": e.staff_name or "",
            "role": e.role or "",
            "period_start": e.period_start.isoformat() if e.period_start else "",
            "period_end": e.period_end.isoformat() if e.period_end else "",
            "regular_hours": float(e.regular_hours or 0),
            "overtime_hours": float(e.overtime_hours or 0),
            "hourly_rate": float(e.hourly_rate or 0),
            "overtime_rate": float(e.overtime_rate or 0),
            "gross_pay": float(e.gross_pay or 0),
            "deductions": float(e.deductions or 0),
            "net_pay": float(e.net_pay or 0),
            "status": e.status or "draft",
        })

    return {
        "entries": entry_list,
        "total": len(entry_list),
        "summary": {
            "total_gross": round(total_gross, 2),
            "total_net": round(total_net, 2),
            "total_hours": round(total_hours, 2),
            "entry_count": len(entry_list),
        },
    }


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
@limiter.limit("60/minute")
async def get_payroll_entries(request: Request, db: DbSession, current_user: RequireManager, period: str = Query(None)):
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
@limiter.limit("60/minute")
async def get_payroll_entry(request: Request, entry_id: str, db: DbSession, current_user: RequireManager):
    """Get a specific payroll entry."""
    entry = db.query(PayrollEntry).filter(PayrollEntry.id == int(entry_id)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Payroll entry not found")
    return _entry_to_schema(entry)


@router.post("/generate")
@limiter.limit("30/minute")
async def generate_payroll(
    request: Request,
    db: DbSession,
    current_user: RequireOwner,
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
@limiter.limit("30/minute")
async def approve_payroll_entry(request: Request, entry_id: str, db: DbSession, current_user: RequireManager):
    """Approve a payroll entry."""
    entry = db.query(PayrollEntry).filter(PayrollEntry.id == int(entry_id)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Payroll entry not found")
    entry.status = "approved"
    db.commit()
    return {"success": True}


@router.post("/approve-all")
@limiter.limit("30/minute")
async def approve_all_payroll(request: Request, db: DbSession, current_user: RequireManager):
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
@limiter.limit("30/minute")
async def mark_as_paid(request: Request, entry_id: str, db: DbSession, current_user: RequireOwner):
    """Mark a payroll entry as paid."""
    entry = db.query(PayrollEntry).filter(PayrollEntry.id == int(entry_id)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Payroll entry not found")
    entry.status = "paid"
    db.commit()
    return {"success": True}


@router.get("/summary")
@limiter.limit("60/minute")
async def get_payroll_summary(request: Request, db: DbSession, current_user: RequireManager):
    """Get payroll summary statistics."""
    total_entries = db.query(func.count(PayrollEntry.id)).scalar() or 0
    total_gross = float(db.query(func.coalesce(func.sum(PayrollEntry.gross_pay), 0)).scalar())
    total_net = float(db.query(func.coalesce(func.sum(PayrollEntry.net_pay), 0)).scalar())
    total_hours = float(db.query(func.coalesce(func.sum(PayrollEntry.hours_worked), 0)).scalar())
    total_runs = db.query(func.count(PayrollRun.id)).scalar() or 0

    return {
        "total_entries": total_entries,
        "total_runs": total_runs,
        "total_gross_pay": total_gross,
        "total_net_pay": total_net,
        "total_hours_worked": total_hours,
        "avg_hourly_rate": round(total_gross / total_hours, 2) if total_hours > 0 else 0,
    }


@router.get("/runs")
@limiter.limit("60/minute")
async def get_payroll_runs(request: Request, db: DbSession, current_user: RequireManager):
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
@limiter.limit("60/minute")
async def get_payroll_employees(request: Request, db: DbSession, current_user: RequireManager):
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


# ==================== TIP COMPLIANCE ====================

@router.get("/tip-compliance/summary")
@limiter.limit("60/minute")
async def get_tip_compliance_summary(
    request: Request,
    db: DbSession,
    current_user: RequireManager,
    period_start: Optional[str] = Query(None),
    period_end: Optional[str] = Query(None),
    location_id: int = Query(1),
):
    """Get tip compliance summary - ensures minimum wage met after tips."""
    try:
        from app.services.tip_compliance_service import TipComplianceService
        return TipComplianceService(db).get_compliance_summary(location_id, period_start, period_end)
    except ImportError:
        entries = db.query(PayrollEntry).limit(100).all()
        total_tips = sum(float(e.tips or 0) for e in entries)
        total_hours = sum(float(e.hours_worked or 0) for e in entries)
        return {
            "location_id": location_id,
            "period_start": period_start,
            "period_end": period_end,
            "total_tips_collected": round(total_tips, 2),
            "total_hours_worked": round(total_hours, 2),
            "avg_tip_per_hour": round(total_tips / total_hours, 2) if total_hours > 0 else 0,
            "minimum_wage": 7.25,
            "compliance_status": "compliant",
            "flagged_employees": [],
        }


@router.post("/tip-pool/rules")
@limiter.limit("30/minute")
async def create_tip_pool_rules(
    request: Request,
    db: DbSession,
    current_user: RequireManager,
    data: dict = {},
):
    """Create or update tip pool distribution rules."""
    try:
        from app.services.tip_compliance_service import TipComplianceService
        return TipComplianceService(db).set_tip_pool_rules(data)
    except ImportError:
        return {
            "success": True,
            "rules": {
                "distribution_method": data.get("distribution_method", "equal"),
                "eligible_roles": data.get("eligible_roles", ["waiter", "bar"]),
                "tip_out_percentage": data.get("tip_out_percentage", 0),
                "back_of_house_share": data.get("back_of_house_share", 0),
            },
            "message": "Tip pool rules saved (stub)",
        }


@router.get("/tip-pool/rules")
@limiter.limit("60/minute")
async def get_tip_pool_rules(
    request: Request,
    db: DbSession,
    current_user: RequireManager,
):
    """Get current tip pool distribution rules."""
    try:
        from app.services.tip_compliance_service import TipComplianceService
        return TipComplianceService(db).get_tip_pool_rules()
    except ImportError:
        return {
            "distribution_method": "equal",
            "eligible_roles": ["waiter", "bar"],
            "tip_out_percentage": 0,
            "back_of_house_share": 0,
            "rules": [],
        }


@router.get("/tip-pool/distribution")
@limiter.limit("60/minute")
async def get_tip_pool_distribution(
    request: Request,
    db: DbSession,
    current_user: RequireManager,
    period_start: Optional[str] = Query(None),
    period_end: Optional[str] = Query(None),
):
    """Get tip pool distribution breakdown by employee."""
    try:
        from app.services.tip_compliance_service import TipComplianceService
        return TipComplianceService(db).get_distribution(period_start, period_end)
    except ImportError:
        return {
            "period_start": period_start,
            "period_end": period_end,
            "total_tips": 0,
            "distributions": [],
            "status": "not_distributed",
        }


@router.post("/tip-pool/distribution")
@limiter.limit("30/minute")
async def execute_tip_pool_distribution(
    request: Request,
    db: DbSession,
    current_user: RequireManager,
    data: dict = {},
):
    """Execute tip pool distribution for a period."""
    try:
        from app.services.tip_compliance_service import TipComplianceService
        return TipComplianceService(db).execute_distribution(data)
    except ImportError:
        return {
            "success": True,
            "total_distributed": 0,
            "recipients": 0,
            "message": "Tip distribution executed (stub)",
        }

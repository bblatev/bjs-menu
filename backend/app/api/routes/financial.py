"""Financial and budgets API routes."""

from typing import List, Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.db.session import DbSession
from app.models.operations import Budget as BudgetModel, DailyReconciliation as ReconciliationModel

router = APIRouter()


@router.get("/accounts/")
def get_financial_accounts(db: DbSession):
    """Get financial accounts."""
    return {"accounts": [], "total": 0}


@router.get("/transactions/")
def get_financial_transactions(db: DbSession):
    """Get financial transactions."""
    return {"transactions": [], "total": 0}


@router.get("/financial-alerts/")
def get_financial_alerts(db: DbSession):
    """Get financial alerts."""
    return {"alerts": [], "total": 0}


@router.get("/bank-accounts")
def get_bank_accounts(db: DbSession):
    """Get bank accounts."""
    return {"accounts": [], "total": 0}


@router.get("/bank-reconciliation")
def get_bank_reconciliation(db: DbSession):
    """Get bank reconciliation data."""
    return {"reconciliations": [], "total": 0}


@router.get("/reports/financial")
def get_financial_reports(db: DbSession):
    """Get financial reports."""
    return {"revenue": 0, "expenses": 0, "profit": 0, "by_category": []}


@router.get("/chart-of-accounts")
def get_chart_of_accounts(db: DbSession):
    """Get chart of accounts."""
    return {"accounts": [], "total": 0}


@router.get("/daily-close")
def get_daily_close(db: DbSession):
    """Get daily close sessions."""
    return {"sessions": [], "current": None}


def _budget_to_dict(b: BudgetModel) -> dict:
    budgeted = float(b.budgeted_amount or 0)
    actual = float(b.actual_amount or 0)
    remaining = budgeted - actual
    if budgeted > 0:
        status = "over" if actual > budgeted else ("under" if actual < budgeted * 0.8 else "on_track")
    else:
        status = "on_track"
    return {
        "id": str(b.id),
        "name": b.name,
        "category": b.category,
        "allocated": budgeted,
        "spent": actual,
        "remaining": remaining,
        "period": f"{b.period or ''} {b.year or ''}".strip(),
        "status": status,
    }


@router.get("/budgets")
async def get_budgets(db: DbSession):
    """Get all budgets."""
    budgets = db.query(BudgetModel).order_by(BudgetModel.id).all()
    return [_budget_to_dict(b) for b in budgets]


@router.get("/budget-variance/{period}")
async def get_budget_variance(period: str, db: DbSession):
    """Get budget variance for a period."""
    budgets = db.query(BudgetModel).all()
    result = []
    for b in budgets:
        budgeted = float(b.budgeted_amount or 0)
        actual = float(b.actual_amount or 0)
        variance = budgeted - actual
        variance_pct = round((variance / budgeted) * 100, 1) if budgeted > 0 else 0
        result.append({
            "category": b.category,
            "budgeted": budgeted,
            "actual": actual,
            "variance": variance,
            "variance_pct": variance_pct,
        })
    return result


@router.get("/budget-variance")
async def get_budget_variance_default(db: DbSession):
    """Get budget variance for the current period."""
    budgets = db.query(BudgetModel).all()
    result = []
    for b in budgets:
        budgeted = float(b.budgeted_amount or 0)
        actual = float(b.actual_amount or 0)
        variance = budgeted - actual
        variance_pct = round((variance / budgeted) * 100, 1) if budgeted > 0 else 0
        result.append({
            "category": b.category,
            "budgeted": budgeted,
            "actual": actual,
            "variance": variance,
            "variance_pct": variance_pct,
        })
    return result


def _reconciliation_to_dict(r: ReconciliationModel) -> dict:
    return {
        "id": str(r.id),
        "date": r.date.isoformat() if r.date else None,
        "status": r.status,
        "total_sales": float(r.total_sales or 0),
        "cash_sales": float(r.cash_total or 0),
        "card_sales": float(r.card_total or 0),
        "expected_cash": float(r.expected_cash or 0),
        "actual_cash": float(r.actual_cash or 0),
        "variance": float(r.cash_variance or 0),
        "completed_by": r.completed_by,
        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
    }


@router.get("/daily-reconciliation/{date}")
async def get_daily_reconciliation(date: str, db: DbSession):
    """Get daily reconciliation for a specific date."""
    from datetime import datetime as dt
    try:
        target_date = dt.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        return {}
    rec = db.query(ReconciliationModel).filter(ReconciliationModel.date == target_date).first()
    if not rec:
        return {}
    return _reconciliation_to_dict(rec)


@router.get("/daily-reconciliation")
async def get_daily_reconciliation_list(db: DbSession):
    """Get daily reconciliation sessions list."""
    recs = db.query(ReconciliationModel).order_by(ReconciliationModel.date.desc()).limit(30).all()
    sessions = [
        {
            "id": str(r.id),
            "date": r.date.isoformat() if r.date else None,
            "status": r.status,
            "total_sales": float(r.total_sales or 0),
            "variance": float(r.cash_variance or 0),
        }
        for r in recs
    ]
    current = None
    open_recs = [r for r in recs if r.status == "open"]
    if open_recs:
        current = {"id": str(open_recs[0].id), "date": open_recs[0].date.isoformat() if open_recs[0].date else None, "status": "open"}
    return {"sessions": sessions, "current": current}


@router.post("/daily-reconciliation/{rec_id}/cash-count")
async def submit_cash_count(rec_id: str, db: DbSession):
    """Submit cash count for daily reconciliation."""
    rec = db.query(ReconciliationModel).filter(ReconciliationModel.id == int(rec_id)).first()
    if not rec:
        return {"success": False, "error": "Not found"}
    return {"success": True, "reconciliation_id": rec_id}


@router.post("/daily-reconciliation/{rec_id}/complete")
async def complete_reconciliation(rec_id: str, db: DbSession):
    """Complete daily reconciliation."""
    from datetime import datetime, timezone
    rec = db.query(ReconciliationModel).filter(ReconciliationModel.id == int(rec_id)).first()
    if not rec:
        return {"success": False, "error": "Not found"}
    rec.status = "completed"
    rec.completed_at = datetime.now(timezone.utc)
    db.commit()
    return {"success": True, "reconciliation_id": rec_id, "status": "completed"}


@router.post("/budgets")
async def create_budget(budget: dict, db: DbSession):
    """Create a new budget."""
    new_budget = BudgetModel(
        name=budget.get("name", ""),
        category=budget.get("category", ""),
        period=budget.get("period"),
        budgeted_amount=budget.get("allocated", 0),
        actual_amount=budget.get("spent", 0),
    )
    db.add(new_budget)
    db.commit()
    db.refresh(new_budget)
    return {"success": True, "id": str(new_budget.id)}

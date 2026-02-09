"""Financial and budgets API routes."""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import func

from app.db.session import DbSession
from app.models.operations import (
    Budget as BudgetModel,
    DailyReconciliation as ReconciliationModel,
    RiskAlert,
)
from app.models.invoice import GLCode, Invoice
from app.models.price_lists import ManagerAlert
from app.models.analytics import DailyMetrics

router = APIRouter()


@router.get("/accounts/")
def get_financial_accounts(db: DbSession):
    """Get financial accounts from GL codes."""
    codes = db.query(GLCode).order_by(GLCode.id).all()
    accounts = [
        {"id": c.id, "code": c.code, "name": c.name, "type": c.category, "active": c.is_active}
        for c in codes
    ]
    return {"accounts": accounts, "total": len(accounts)}


@router.get("/transactions/")
def get_financial_transactions(db: DbSession):
    """Get financial transactions from invoices."""
    invoices = db.query(Invoice).order_by(Invoice.created_at.desc()).limit(50).all()
    transactions = [
        {
            "id": inv.id,
            "type": "invoice",
            "supplier_id": inv.supplier_id,
            "amount": float(inv.total_amount or 0),
            "status": inv.status.value if hasattr(inv.status, 'value') else str(inv.status),
            "date": inv.invoice_date.isoformat() if inv.invoice_date else None,
        }
        for inv in invoices
    ]
    return {"transactions": transactions, "total": len(transactions)}


@router.get("/financial-alerts/")
def get_financial_alerts(db: DbSession):
    """Get financial alerts from risk alerts and manager alerts."""
    risk_alerts = db.query(RiskAlert).filter(
        RiskAlert.status == "open"
    ).order_by(RiskAlert.created_at.desc()).limit(20).all()
    mgr_alerts = db.query(ManagerAlert).order_by(ManagerAlert.created_at.desc()).limit(20).all()
    alerts = []
    for ra in risk_alerts:
        alerts.append({
            "id": f"risk-{ra.id}",
            "type": ra.type,
            "severity": ra.severity,
            "title": ra.title,
            "amount": float(ra.amount or 0),
            "created_at": ra.created_at.isoformat() if ra.created_at else None,
        })
    for ma in mgr_alerts:
        alerts.append({
            "id": f"mgr-{ma.id}",
            "type": ma.alert_type,
            "severity": "info",
            "title": ma.name or "",
            "created_at": ma.created_at.isoformat() if ma.created_at else None,
        })
    return {"alerts": alerts, "total": len(alerts)}


@router.get("/bank-accounts")
def get_bank_accounts(db: DbSession):
    """Get bank accounts from app settings."""
    from app.models.operations import AppSetting
    setting = db.query(AppSetting).filter(
        AppSetting.category == "bank",
        AppSetting.key == "accounts",
    ).first()
    if setting and isinstance(setting.value, list):
        return {"accounts": setting.value, "total": len(setting.value)}
    return {"accounts": [], "total": 0}


@router.get("/bank-reconciliation")
def get_bank_reconciliation(db: DbSession):
    """Get bank reconciliation data."""
    recs = db.query(ReconciliationModel).order_by(
        ReconciliationModel.date.desc()
    ).limit(30).all()
    reconciliations = [
        {
            "id": r.id,
            "date": r.date.isoformat() if r.date else None,
            "status": r.status,
            "total_sales": float(r.total_sales or 0),
            "variance": float(r.cash_variance or 0),
        }
        for r in recs
    ]
    return {"reconciliations": reconciliations, "total": len(reconciliations)}


@router.get("/reports/financial")
def get_financial_reports(db: DbSession):
    """Get financial reports from daily metrics."""
    metrics = db.query(DailyMetrics).order_by(DailyMetrics.date.desc()).limit(30).all()
    revenue = sum(float(m.total_revenue or 0) for m in metrics)
    expenses = sum(float(m.food_cost or 0) + float(m.labor_cost or 0) for m in metrics) if metrics else 0
    profit = revenue - expenses
    by_category = []
    categories = {}
    for m in metrics:
        cat = str(m.date) if m.date else "unknown"
        categories[cat] = {
            "revenue": float(m.total_revenue or 0),
            "expenses": float(m.food_cost or 0) + float(m.labor_cost or 0),
        }
    by_category = [
        {"date": k, "revenue": v["revenue"], "expenses": v["expenses"]}
        for k, v in list(categories.items())[:10]
    ]
    return {"revenue": round(revenue, 2), "expenses": round(expenses, 2), "profit": round(profit, 2), "by_category": by_category}


@router.get("/chart-of-accounts")
def get_chart_of_accounts(db: DbSession):
    """Get chart of accounts from GL codes."""
    codes = db.query(GLCode).order_by(GLCode.code).all()
    accounts = [
        {"id": c.id, "code": c.code, "name": c.name, "type": c.category, "active": c.is_active}
        for c in codes
    ]
    return {"accounts": accounts, "total": len(accounts)}


@router.get("/daily-close")
def get_daily_close(db: DbSession):
    """Get daily close sessions."""
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


@router.post("/accounts/")
async def create_financial_account(data: dict, db: DbSession):
    """Create a financial account (GL code)."""
    code = data.get("code", "")
    name = data.get("name", "")
    if not code or not name:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="code and name are required")
    existing = db.query(GLCode).filter(GLCode.code == code).first()
    if existing:
        return {"id": existing.id, "code": existing.code, "name": existing.name, "type": existing.category}
    gl = GLCode(code=code, name=name, category=data.get("type", "expense"), is_active=True)
    db.add(gl)
    db.commit()
    db.refresh(gl)
    return {"id": gl.id, "code": gl.code, "name": gl.name, "type": gl.category}


@router.post("/transactions/")
async def create_financial_transaction(data: dict, db: DbSession):
    """Create a financial transaction (invoice record)."""
    inv = Invoice(
        supplier_id=data.get("account_id", data.get("supplier_id", 1)),
        invoice_number=f"TXN-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        total_amount=data.get("amount", 0),
        status="pending",
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return {"id": inv.id, "type": data.get("type", "credit"), "amount": float(inv.total_amount or 0)}


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

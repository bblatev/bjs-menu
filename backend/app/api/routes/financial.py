"""Financial and budgets API routes."""

from datetime import date, datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.rbac import CurrentUser, RequireManager, get_current_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models import StaffUser
from app.db.session import DbSession
from app.models.operations import (
    Budget as BudgetModel,
    DailyReconciliation as ReconciliationModel,
    RiskAlert,
)
from app.models.invoice import GLCode, Invoice
from app.models.price_lists import ManagerAlert
from app.models.analytics import DailyMetrics
from app.schemas.pagination import paginate_query

router = APIRouter()


@router.get("/accounts/")
@limiter.limit("60/minute")
def get_financial_accounts(
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
):
    """Get financial accounts from GL codes."""
    query = db.query(GLCode).order_by(GLCode.id)
    items, total = paginate_query(query, skip, limit)
    accounts = [
        {"id": c.id, "code": c.code, "name": c.name, "type": c.category, "active": c.is_active}
        for c in items
    ]
    return {"accounts": accounts, "total": total, "skip": skip, "limit": limit}


@router.get("/transactions/")
@limiter.limit("60/minute")
def get_financial_transactions(request: Request, db: DbSession, current_user: CurrentUser):
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
@limiter.limit("60/minute")
def get_financial_alerts(request: Request, db: DbSession, current_user: RequireManager):
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
@limiter.limit("60/minute")
def get_bank_accounts(request: Request, db: DbSession, current_user: RequireManager):
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
@limiter.limit("60/minute")
def get_bank_reconciliation(request: Request, db: DbSession, current_user: RequireManager):
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
@limiter.limit("60/minute")
def get_financial_reports(request: Request, db: DbSession, current_user: RequireManager):
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
@limiter.limit("60/minute")
def get_chart_of_accounts(
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
):
    """Get chart of accounts from GL codes."""
    query = db.query(GLCode).order_by(GLCode.code)
    items, total = paginate_query(query, skip, limit)
    accounts = [
        {"id": c.id, "code": c.code, "name": c.name, "type": c.category, "active": c.is_active}
        for c in items
    ]
    return {"accounts": accounts, "total": total, "skip": skip, "limit": limit}


@router.get("/daily-close")
@limiter.limit("60/minute")
def get_daily_close(request: Request, db: DbSession, current_user: CurrentUser):
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
@limiter.limit("60/minute")
async def get_budgets(
    request: Request,
    db: DbSession,
    current_user: RequireManager,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
):
    """Get all budgets."""
    query = db.query(BudgetModel).order_by(BudgetModel.id)
    items, total = paginate_query(query, skip, limit)
    return {"items": [_budget_to_dict(b) for b in items], "total": total, "skip": skip, "limit": limit}


@router.get("/budget-variance/{period}")
@limiter.limit("60/minute")
async def get_budget_variance(
    request: Request,
    period: str,
    db: DbSession,
    current_user: RequireManager,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
):
    """Get budget variance for a period."""
    query = db.query(BudgetModel).order_by(BudgetModel.id)
    items, total = paginate_query(query, skip, limit)
    result = []
    for b in items:
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
    return {"items": result, "total": total, "skip": skip, "limit": limit}


@router.get("/budget-variance")
@limiter.limit("60/minute")
async def get_budget_variance_default(
    request: Request,
    db: DbSession,
    current_user: RequireManager,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
):
    """Get budget variance for the current period."""
    query = db.query(BudgetModel).order_by(BudgetModel.id)
    items, total = paginate_query(query, skip, limit)
    result = []
    for b in items:
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
    return {"items": result, "total": total, "skip": skip, "limit": limit}


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
@limiter.limit("60/minute")
async def get_daily_reconciliation(request: Request, date: str, db: DbSession, current_user: CurrentUser):
    """Get daily reconciliation for a specific date."""
    from datetime import datetime as dt, timezone
    try:
        target_date = dt.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {date}. Expected YYYY-MM-DD.")
    rec = db.query(ReconciliationModel).filter(ReconciliationModel.date == target_date).first()
    if not rec:
        return {}
    return _reconciliation_to_dict(rec)


@router.get("/daily-reconciliation")
@limiter.limit("60/minute")
async def get_daily_reconciliation_list(request: Request, db: DbSession, current_user: CurrentUser):
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
@limiter.limit("30/minute")
async def submit_cash_count(request: Request, rec_id: str, db: DbSession, current_user: CurrentUser):
    """Submit cash count for daily reconciliation."""
    rec = db.query(ReconciliationModel).filter(ReconciliationModel.id == int(rec_id)).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Reconciliation not found")
    return {"success": True, "reconciliation_id": rec_id}


@router.post("/daily-reconciliation/{rec_id}/complete")
@limiter.limit("30/minute")
async def complete_reconciliation(request: Request, rec_id: str, db: DbSession, current_user: RequireManager):
    """Complete daily reconciliation."""
    from datetime import datetime, timezone
    rec = db.query(ReconciliationModel).filter(ReconciliationModel.id == int(rec_id)).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Reconciliation not found")
    rec.status = "completed"
    rec.completed_at = datetime.now(timezone.utc)
    db.commit()
    return {"success": True, "reconciliation_id": rec_id, "status": "completed"}


class CreateFinancialAccountRequest(BaseModel):
    code: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    type: str = Field(default="expense")


@router.post("/accounts/")
@limiter.limit("30/minute")
async def create_financial_account(request: Request, data: CreateFinancialAccountRequest, db: DbSession, current_user: RequireManager):
    """Create a financial account (GL code)."""
    existing = db.query(GLCode).filter(GLCode.code == data.code).first()
    if existing:
        return {"id": existing.id, "code": existing.code, "name": existing.name, "type": existing.category}
    gl = GLCode(code=data.code, name=data.name, category=data.type, is_active=True)
    db.add(gl)
    db.commit()
    db.refresh(gl)
    return {"id": gl.id, "code": gl.code, "name": gl.name, "type": gl.category}


@router.post("/transactions/")
@limiter.limit("30/minute")
async def create_financial_transaction(request: Request, data: dict, db: DbSession, current_user: RequireManager):
    """Create a financial transaction (invoice record)."""
    inv = Invoice(
        supplier_id=data.get("account_id", data.get("supplier_id", 1)),
        invoice_number=f"TXN-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        total_amount=data.get("amount", 0),
        status="pending",
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return {"id": inv.id, "type": data.get("type", "credit"), "amount": float(inv.total_amount or 0)}


@router.post("/budgets")
@limiter.limit("30/minute")
async def create_budget(request: Request, budget: dict, db: DbSession, current_user: RequireManager):
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


# ============================================================================
# MERGED FROM financial_endpoints.py
# Unique endpoints: journal entries, bank reconciliation (service-based),
# bank transaction import, account balance, daily close start, etc.
# ============================================================================

from app.services.financial_service import (
    get_chart_of_accounts_service,
    get_journal_entry_service,
    get_bank_reconciliation_service,
    get_budget_service,
    get_daily_reconciliation_service,
)


def _require_admin(current_user=Depends(get_current_user)):
    """Require admin/owner role."""
    if not hasattr(current_user, "role"):
        return current_user
    if current_user.role not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def _require_manager_dep(current_user=Depends(get_current_user)):
    """Require manager or above role."""
    if not hasattr(current_user, "role"):
        return current_user
    if current_user.role not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Manager access required")
    return current_user


# ----- Schemas (from financial_endpoints.py) -----

class AccountCreate(BaseModel):
    account_code: str = Field(..., min_length=1, max_length=20)
    account_name: str = Field(..., min_length=1, max_length=200)
    account_type: str = Field(..., description="asset, liability, equity, revenue, expense")
    parent_id: Optional[int] = None
    description: Optional[str] = None


class JournalEntryLineSchema(BaseModel):
    account_id: int
    debit_amount: float = 0
    credit_amount: float = 0
    description: Optional[str] = None


class JournalEntryCreate(BaseModel):
    entry_date: date
    description: str
    lines: List[JournalEntryLineSchema] = Field(..., min_length=2)
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None


class BankAccountCreate(BaseModel):
    account_name: str
    bank_name: str
    account_number: str
    routing_number: Optional[str] = None
    currency: str = "BGN"


class BankTransactionImport(BaseModel):
    date: date
    amount: float
    description: Optional[str] = None
    reference: Optional[str] = None
    type: str = "other"


class ReconciliationStart(BaseModel):
    bank_account_id: int
    statement_date: date
    statement_balance: float


class TransactionMatch(BaseModel):
    bank_transaction_id: int
    system_record_type: str
    system_record_id: int


class BudgetLineCreate(BaseModel):
    account_id: Optional[int] = None
    category: Optional[str] = None
    amount: float


class BudgetCreateFull(BaseModel):
    name: str
    budget_type: str
    period_start: date
    period_end: date
    line_items: List[BudgetLineCreate]


class CashCountRecord(BaseModel):
    denomination_counts: dict  # {"100": 5, "50": 10, etc.}


# ----- Chart of Accounts (service-based) -----

@router.post("/chart-of-accounts")
@limiter.limit("30/minute")
async def create_account_via_service(
    request: Request,
    data: AccountCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(_require_admin),
):
    """Create a new GL account (service-based)."""
    service = get_chart_of_accounts_service(db)
    try:
        return service.create_account(
            venue_id=current_user.venue_id,
            **data.model_dump(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/chart-of-accounts/{account_id}/balance")
@limiter.limit("60/minute")
async def get_account_balance(
    request: Request,
    account_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(_require_manager_dep),
):
    """Get current balance for an account."""
    service = get_chart_of_accounts_service(db)
    try:
        return service.get_account_balance(account_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ----- Journal Entries -----

@router.get("/journal-entries")
@limiter.limit("60/minute")
async def get_journal_entries(
    request: Request,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(_require_manager_dep),
):
    """Get journal entries."""
    service = get_journal_entry_service(db)
    return service.get_journal_entries(
        venue_id=current_user.venue_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )


@router.post("/journal-entries")
@limiter.limit("30/minute")
async def create_journal_entry(
    request: Request,
    data: JournalEntryCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(_require_manager_dep),
):
    """Create a new journal entry."""
    service = get_journal_entry_service(db)
    try:
        return service.create_journal_entry(
            venue_id=current_user.venue_id,
            entry_date=data.entry_date,
            description=data.description,
            lines=[line.model_dump() for line in data.lines],
            reference_type=data.reference_type,
            reference_id=data.reference_id,
            created_by=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ----- Bank Accounts (service-based) -----

@router.post("/bank-accounts")
@limiter.limit("30/minute")
async def create_bank_account(
    request: Request,
    data: BankAccountCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(_require_admin),
):
    """Create a new bank account."""
    service = get_bank_reconciliation_service(db)
    return service.create_bank_account(
        venue_id=current_user.venue_id,
        **data.model_dump(),
    )


@router.post("/bank-accounts/{bank_account_id}/import-transactions")
@limiter.limit("30/minute")
async def import_bank_transactions(
    request: Request,
    bank_account_id: int,
    transactions: List[BankTransactionImport],
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(_require_manager_dep),
):
    """Import bank transactions from statement."""
    service = get_bank_reconciliation_service(db)
    return service.import_bank_transactions(
        bank_account_id=bank_account_id,
        transactions=[t.model_dump() for t in transactions],
    )


# ----- Bank Reconciliation (service-based) -----

@router.post("/bank-reconciliation")
@limiter.limit("30/minute")
async def start_bank_reconciliation(
    request: Request,
    data: ReconciliationStart,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(_require_manager_dep),
):
    """Start a new bank reconciliation session."""
    service = get_bank_reconciliation_service(db)
    return service.start_reconciliation(
        venue_id=current_user.venue_id,
        **data.model_dump(),
    )


@router.get("/bank-reconciliation/{reconciliation_id}")
@limiter.limit("60/minute")
async def get_bank_reconciliation_by_id(
    request: Request,
    reconciliation_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(_require_manager_dep),
):
    """Get bank reconciliation details."""
    from app.models.financial_models import BankReconciliation

    reconciliation = (
        db.query(BankReconciliation)
        .filter(BankReconciliation.id == reconciliation_id)
        .first()
    )
    if not reconciliation:
        raise HTTPException(status_code=404, detail="Reconciliation not found")
    return {
        "id": reconciliation.id,
        "bank_account_id": reconciliation.bank_account_id,
        "statement_date": reconciliation.statement_date.isoformat(),
        "statement_balance": float(reconciliation.statement_balance or 0),
        "reconciled_balance": float(reconciliation.reconciled_balance or 0)
        if reconciliation.reconciled_balance
        else None,
        "difference": float(reconciliation.difference or 0)
        if reconciliation.difference
        else None,
        "status": reconciliation.status,
    }


@router.post("/bank-reconciliation/{reconciliation_id}/match")
@limiter.limit("30/minute")
async def match_bank_transaction(
    request: Request,
    reconciliation_id: int,
    data: TransactionMatch,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(_require_manager_dep),
):
    """Match a bank transaction with a system record."""
    service = get_bank_reconciliation_service(db)
    return service.match_transaction(
        reconciliation_id=reconciliation_id,
        **data.model_dump(),
    )


@router.post("/bank-reconciliation/{reconciliation_id}/complete")
@limiter.limit("30/minute")
async def complete_bank_reconciliation(
    request: Request,
    reconciliation_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(_require_manager_dep),
):
    """Complete a bank reconciliation session."""
    service = get_bank_reconciliation_service(db)
    try:
        return service.complete_reconciliation(reconciliation_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ----- Daily Close (service-based) -----

@router.post("/daily-close")
@limiter.limit("30/minute")
async def start_daily_close(
    request: Request,
    business_date: date,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(_require_manager_dep),
):
    """Start daily close/reconciliation process."""
    service = get_daily_reconciliation_service(db)
    return service.start_daily_close(
        venue_id=current_user.venue_id,
        business_date=business_date,
        closed_by=current_user.id,
    )

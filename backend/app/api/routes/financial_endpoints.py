"""
Financial API Endpoints
Chart of Accounts, Journal Entries, Bank Reconciliation, Budgets, Daily Close
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date
from pydantic import BaseModel, Field

from app.db.session import get_db
from app.models import StaffUser
from app.core.rate_limit import limiter
from app.services.financial_service import (
    get_chart_of_accounts_service,
    get_journal_entry_service,
    get_bank_reconciliation_service,
    get_budget_service,
    get_daily_reconciliation_service
)


router = APIRouter(tags=["Financial"])

from app.core.rbac import get_current_user

def require_admin(current_user = Depends(get_current_user)):
    """Require admin/owner role."""
    if not hasattr(current_user, 'role'):
        return current_user
    if current_user.role not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def require_manager(current_user = Depends(get_current_user)):
    """Require manager or above role."""
    if not hasattr(current_user, 'role'):
        return current_user
    if current_user.role not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Manager access required")
    return current_user



# ========================= SCHEMAS =========================

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


class BudgetCreate(BaseModel):
    name: str
    budget_type: str
    period_start: date
    period_end: date
    line_items: List[BudgetLineCreate]


class CashCountRecord(BaseModel):
    denomination_counts: dict  # {"100": 5, "50": 10, etc.}


# ========================= CHART OF ACCOUNTS =========================

@router.get("/")
@limiter.limit("60/minute")
async def get_financial_root(request: Request, db: Session = Depends(get_db), current_user: StaffUser = Depends(require_manager)):
    """Financial overview."""
    return await get_chart_of_accounts(request=request, db=db, current_user=current_user)


@router.get("/chart-of-accounts")
@limiter.limit("60/minute")
async def get_chart_of_accounts(
    request: Request,
    account_type: Optional[str] = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Get all chart of accounts entries"""
    service = get_chart_of_accounts_service(db)
    return service.get_accounts(
        venue_id=current_user.venue_id,
        account_type=account_type,
        active_only=active_only
    )


@router.post("/chart-of-accounts")
@limiter.limit("30/minute")
async def create_account(
    request: Request,
    data: AccountCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin)
):
    """Create a new GL account"""
    service = get_chart_of_accounts_service(db)
    try:
        return service.create_account(
            venue_id=current_user.venue_id,
            **data.model_dump()
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/chart-of-accounts/{account_id}/balance")
@limiter.limit("60/minute")
async def get_account_balance(
    request: Request,
    account_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Get current balance for an account"""
    service = get_chart_of_accounts_service(db)
    try:
        return service.get_account_balance(account_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ========================= JOURNAL ENTRIES =========================

@router.get("/journal-entries")
@limiter.limit("60/minute")
async def get_journal_entries(
    request: Request,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Get journal entries"""
    service = get_journal_entry_service(db)
    return service.get_journal_entries(
        venue_id=current_user.venue_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset
    )


@router.post("/journal-entries")
@limiter.limit("30/minute")
async def create_journal_entry(
    request: Request,
    data: JournalEntryCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Create a new journal entry"""
    service = get_journal_entry_service(db)
    try:
        return service.create_journal_entry(
            venue_id=current_user.venue_id,
            entry_date=data.entry_date,
            description=data.description,
            lines=[line.model_dump() for line in data.lines],
            reference_type=data.reference_type,
            reference_id=data.reference_id,
            created_by=current_user.id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ========================= BANK ACCOUNTS & RECONCILIATION =========================

@router.get("/bank-accounts")
@limiter.limit("60/minute")
async def get_bank_accounts(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Get all bank accounts"""
    from app.models.financial_models import BankAccount
    accounts = db.query(BankAccount).filter(
        BankAccount.venue_id == current_user.venue_id,
        BankAccount.is_active == True
    ).all()
    return [
        {
            "id": a.id,
            "account_name": a.account_name,
            "bank_name": a.bank_name,
            "account_number": "****" + a.account_number[-4:] if a.account_number else None,
            "current_balance": float(a.current_balance or 0),
            "currency": a.currency
        }
        for a in accounts
    ]


@router.post("/bank-accounts")
@limiter.limit("30/minute")
async def create_bank_account(
    request: Request,
    data: BankAccountCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin)
):
    """Create a new bank account"""
    service = get_bank_reconciliation_service(db)
    return service.create_bank_account(
        venue_id=current_user.venue_id,
        **data.model_dump()
    )


@router.post("/bank-accounts/{bank_account_id}/import-transactions")
@limiter.limit("30/minute")
async def import_bank_transactions(
    request: Request,
    bank_account_id: int,
    transactions: List[BankTransactionImport],
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Import bank transactions from statement"""
    service = get_bank_reconciliation_service(db)
    return service.import_bank_transactions(
        bank_account_id=bank_account_id,
        transactions=[t.model_dump() for t in transactions]
    )


@router.post("/bank-reconciliation")
@limiter.limit("30/minute")
async def start_reconciliation(
    request: Request,
    data: ReconciliationStart,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Start a new bank reconciliation session"""
    service = get_bank_reconciliation_service(db)
    return service.start_reconciliation(
        venue_id=current_user.venue_id,
        **data.model_dump()
    )


@router.get("/bank-reconciliation/{reconciliation_id}")
@limiter.limit("60/minute")
async def get_reconciliation(
    request: Request,
    reconciliation_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Get reconciliation details"""
    from app.models.financial_models import BankReconciliation
    reconciliation = db.query(BankReconciliation).filter(
        BankReconciliation.id == reconciliation_id
    ).first()
    if not reconciliation:
        raise HTTPException(status_code=404, detail="Reconciliation not found")
    return {
        "id": reconciliation.id,
        "bank_account_id": reconciliation.bank_account_id,
        "statement_date": reconciliation.statement_date.isoformat(),
        "statement_balance": float(reconciliation.statement_balance or 0),
        "reconciled_balance": float(reconciliation.reconciled_balance or 0) if reconciliation.reconciled_balance else None,
        "difference": float(reconciliation.difference or 0) if reconciliation.difference else None,
        "status": reconciliation.status
    }


@router.post("/bank-reconciliation/{reconciliation_id}/match")
@limiter.limit("30/minute")
async def match_transaction(
    request: Request,
    reconciliation_id: int,
    data: TransactionMatch,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Match a bank transaction with a system record"""
    service = get_bank_reconciliation_service(db)
    return service.match_transaction(
        reconciliation_id=reconciliation_id,
        **data.model_dump()
    )


@router.post("/bank-reconciliation/{reconciliation_id}/complete")
@limiter.limit("30/minute")
async def complete_reconciliation(
    request: Request,
    reconciliation_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Complete a reconciliation session"""
    service = get_bank_reconciliation_service(db)
    try:
        return service.complete_reconciliation(reconciliation_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ========================= BUDGETS =========================

@router.get("/budgets")
@limiter.limit("60/minute")
async def get_budgets(
    request: Request,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Get all budgets"""
    from app.models.operations import Budget
    query = db.query(Budget)
    budgets = query.all()
    return [
        {
            "id": b.id,
            "name": b.name,
            "category": b.category,
            "period": b.period,
            "year": b.year,
            "month": b.month,
            "budgeted_amount": float(b.budgeted_amount or 0),
            "actual_amount": float(b.actual_amount or 0),
            "notes": b.notes
        }
        for b in budgets
    ]


@router.post("/budgets")
@limiter.limit("30/minute")
async def create_budget(
    request: Request,
    data: BudgetCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Create a new budget"""
    service = get_budget_service(db)
    return service.create_budget(
        venue_id=current_user.venue_id,
        name=data.name,
        budget_type=data.budget_type,
        period_start=data.period_start,
        period_end=data.period_end,
        line_items=[item.model_dump() for item in data.line_items],
        created_by=current_user.id
    )


@router.get("/budget-variance/{budget_id}")
@limiter.limit("60/minute")
async def get_budget_variance(
    request: Request,
    budget_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Get budget vs actual variance report"""
    service = get_budget_service(db)
    try:
        return service.get_budget_variance(budget_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ========================= DAILY CLOSE =========================

@router.post("/daily-close")
@limiter.limit("30/minute")
async def start_daily_close(
    request: Request,
    business_date: date,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Start daily close/reconciliation process"""
    service = get_daily_reconciliation_service(db)
    return service.start_daily_close(
        venue_id=current_user.venue_id,
        business_date=business_date,
        closed_by=current_user.id
    )


@router.get("/daily-reconciliation/{business_date}")
@limiter.limit("60/minute")
async def get_daily_reconciliation(
    request: Request,
    business_date: date,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Get daily reconciliation for a specific date"""
    from app.models.operations import DailyReconciliation
    reconciliation = db.query(DailyReconciliation).filter(
        DailyReconciliation.venue_id == current_user.venue_id,
        DailyReconciliation.business_date == business_date
    ).first()
    if not reconciliation:
        raise HTTPException(status_code=404, detail="Daily reconciliation not found")
    return {
        "id": reconciliation.id,
        "business_date": reconciliation.business_date.isoformat(),
        "status": reconciliation.status,
        "expected_cash": float(reconciliation.expected_cash or 0),
        "actual_cash": float(reconciliation.actual_cash or 0),
        "cash_variance": float(reconciliation.cash_variance or 0),
        "closed_at": reconciliation.closed_at.isoformat() if reconciliation.closed_at else None
    }


@router.post("/daily-reconciliation/{reconciliation_id}/cash-count")
@limiter.limit("30/minute")
async def record_cash_count(
    request: Request,
    reconciliation_id: int,
    data: CashCountRecord,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Record cash drawer count"""
    service = get_daily_reconciliation_service(db)
    return service.record_cash_count(
        reconciliation_id=reconciliation_id,
        denomination_counts=data.denomination_counts,
        counted_by=current_user.id
    )


@router.post("/daily-reconciliation/{reconciliation_id}/complete")
@limiter.limit("30/minute")
async def complete_daily_close(
    request: Request,
    reconciliation_id: int,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Complete daily close process"""
    service = get_daily_reconciliation_service(db)
    try:
        return service.complete_daily_close(
            reconciliation_id=reconciliation_id,
            closed_by=current_user.id,
            notes=notes
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

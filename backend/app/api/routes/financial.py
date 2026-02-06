"""Financial and budgets API routes."""

from typing import List, Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.db.session import DbSession

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


class Budget(BaseModel):
    id: str
    name: str
    category: str
    allocated: float
    spent: float
    remaining: float
    period: str
    status: str  # on_track, over, under


class BudgetVariance(BaseModel):
    category: str
    budgeted: float
    actual: float
    variance: float
    variance_pct: float


@router.get("/budgets")
async def get_budgets():
    """Get all budgets."""
    return [
        Budget(id="1", name="Food Costs", category="COGS", allocated=15000, spent=12500, remaining=2500, period="January 2026", status="on_track"),
        Budget(id="2", name="Beverage Costs", category="COGS", allocated=8000, spent=7200, remaining=800, period="January 2026", status="on_track"),
        Budget(id="3", name="Labor", category="OpEx", allocated=25000, spent=26500, remaining=-1500, period="January 2026", status="over"),
        Budget(id="4", name="Marketing", category="OpEx", allocated=3000, spent=1800, remaining=1200, period="January 2026", status="under"),
        Budget(id="5", name="Utilities", category="OpEx", allocated=2500, spent=2400, remaining=100, period="January 2026", status="on_track"),
    ]


@router.get("/budget-variance/{period}")
async def get_budget_variance(period: str):
    """Get budget variance for a period."""
    return [
        BudgetVariance(category="Food", budgeted=15000, actual=12500, variance=2500, variance_pct=16.7),
        BudgetVariance(category="Beverage", budgeted=8000, actual=7200, variance=800, variance_pct=10.0),
        BudgetVariance(category="Labor", budgeted=25000, actual=26500, variance=-1500, variance_pct=-6.0),
        BudgetVariance(category="Marketing", budgeted=3000, actual=1800, variance=1200, variance_pct=40.0),
    ]


@router.post("/budgets")
async def create_budget(budget: Budget):
    """Create a new budget."""
    return {"success": True, "id": "new-id"}

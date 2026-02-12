"""
Financial Management Service - BJS V6
======================================
Cash flow forecasting, expense tracking, bank reconciliation, break-even analysis
with database integration.
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class ExpenseCategory(str, Enum):
    FOOD_COST = "food_cost"
    LABOR = "labor"
    RENT = "rent"
    UTILITIES = "utilities"
    MARKETING = "marketing"
    EQUIPMENT = "equipment"
    SUPPLIES = "supplies"
    INSURANCE = "insurance"
    LICENSES = "licenses"
    MAINTENANCE = "maintenance"
    OTHER = "other"


class TransactionType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"


# Pydantic models for API responses
class ExpenseResponse(BaseModel):
    id: int
    venue_id: int
    category: str
    description: str
    amount: float
    currency: str
    expense_date: date

    model_config = ConfigDict(from_attributes=True)


class BankTransactionResponse(BaseModel):
    id: int
    venue_id: int
    bank_account: str
    transaction_type: str
    amount: float
    description: str
    transaction_date: date
    reconciled: bool

    model_config = ConfigDict(from_attributes=True)


class CashFlowForecast(BaseModel):
    venue_id: int
    forecast_date: date
    projected_income: float
    projected_expenses: float
    net_cash_flow: float
    opening_balance: float
    closing_balance: float
    confidence_level: float = 0.8


class BreakEvenAnalysis(BaseModel):
    venue_id: int
    period: str
    fixed_costs: float
    variable_cost_percent: float
    avg_check: float
    break_even_revenue: float
    break_even_covers: int
    current_revenue: float
    margin_of_safety: float


class FinancialManagementService:
    """Financial operations and analysis with database persistence."""

    def __init__(self, db_session: Session = None):
        self.db = db_session

    # ==================== EXPENSE TRACKING ====================

    def create_expense(self, venue_id: int, category: str,
                       description: str, amount: float, expense_date: date,
                       created_by: int = None, **kwargs) -> Dict[str, Any]:
        """Create a new expense record."""
        from app.models.v6_features_models import FinancialExpense

        if not self.db:
            logger.warning("No database session - returning mock response")
            return {"id": 1, "venue_id": venue_id, "amount": amount}

        # Handle ExpenseCategory enum
        if isinstance(category, ExpenseCategory):
            category = category.value

        expense = FinancialExpense(
            venue_id=venue_id,
            category=category,
            description=description,
            amount=amount,
            expense_date=expense_date,
            created_by=created_by,
            vendor=kwargs.get('vendor'),
            invoice_number=kwargs.get('invoice_number'),
            payment_method=kwargs.get('payment_method', 'bank_transfer'),
            recurring=kwargs.get('recurring', False),
            recurring_frequency=kwargs.get('recurring_frequency'),
            tax_deductible=kwargs.get('tax_deductible', True),
            receipt_url=kwargs.get('receipt_url'),
            currency=kwargs.get('currency', 'BGN')
        )

        self.db.add(expense)
        self.db.commit()
        self.db.refresh(expense)

        logger.info(f"Created expense {expense.id}: {description} - {amount}")

        return {
            "success": True,
            "id": expense.id,
            "venue_id": expense.venue_id,
            "category": expense.category,
            "description": expense.description,
            "amount": float(expense.amount),
            "expense_date": expense.expense_date.isoformat()
        }

    def update_expense(self, expense_id: int, **kwargs) -> Dict[str, Any]:
        """Update an expense record."""
        from app.models.v6_features_models import FinancialExpense

        if not self.db:
            return {"success": False, "error": "No database session"}

        expense = self.db.query(FinancialExpense).filter(
            FinancialExpense.id == expense_id
        ).first()

        if not expense:
            return {"success": False, "error": "Expense not found"}

        allowed_fields = ['category', 'description', 'amount', 'expense_date',
                          'vendor', 'invoice_number', 'payment_method',
                          'recurring', 'recurring_frequency', 'tax_deductible', 'receipt_url']

        for field, value in kwargs.items():
            if field in allowed_fields and value is not None:
                if field == 'category' and isinstance(value, ExpenseCategory):
                    value = value.value
                setattr(expense, field, value)

        self.db.commit()
        self.db.refresh(expense)

        return {
            "success": True,
            "id": expense.id,
            "category": expense.category,
            "amount": float(expense.amount)
        }

    def delete_expense(self, expense_id: int) -> Dict[str, Any]:
        """Delete an expense record."""
        from app.models.v6_features_models import FinancialExpense

        if not self.db:
            return {"success": False, "error": "No database session"}

        expense = self.db.query(FinancialExpense).filter(
            FinancialExpense.id == expense_id
        ).first()

        if not expense:
            return {"success": False, "error": "Expense not found"}

        self.db.delete(expense)
        self.db.commit()

        return {"success": True, "deleted_id": expense_id}

    def get_expenses(self, venue_id: int, start: date, end: date,
                     category: str = None) -> List[Dict[str, Any]]:
        """Get expenses for a venue within a date range."""
        from app.models.v6_features_models import FinancialExpense

        if not self.db:
            return []

        query = self.db.query(FinancialExpense).filter(
            FinancialExpense.venue_id == venue_id,
            FinancialExpense.expense_date >= start,
            FinancialExpense.expense_date <= end
        )

        if category:
            if isinstance(category, ExpenseCategory):
                category = category.value
            query = query.filter(FinancialExpense.category == category)

        expenses = query.order_by(FinancialExpense.expense_date.desc()).all()

        return [
            {
                "id": e.id,
                "venue_id": e.venue_id,
                "category": e.category,
                "description": e.description,
                "amount": float(e.amount),
                "currency": e.currency,
                "vendor": e.vendor,
                "invoice_number": e.invoice_number,
                "payment_method": e.payment_method,
                "expense_date": e.expense_date.isoformat(),
                "recurring": e.recurring,
                "recurring_frequency": e.recurring_frequency,
                "tax_deductible": e.tax_deductible,
                "receipt_url": e.receipt_url
            }
            for e in expenses
        ]

    def get_expense_summary(self, venue_id: int, start: date, end: date) -> Dict[str, Any]:
        """Get expense summary by category."""
        from app.models.v6_features_models import FinancialExpense

        if not self.db:
            return {"period": f"{start} to {end}", "total_expenses": 0, "by_category": {}}

        expenses = self.db.query(FinancialExpense).filter(
            FinancialExpense.venue_id == venue_id,
            FinancialExpense.expense_date >= start,
            FinancialExpense.expense_date <= end
        ).all()

        by_category = {}
        for cat in ExpenseCategory:
            cat_expenses = [e for e in expenses if e.category == cat.value]
            by_category[cat.value] = sum(float(e.amount) for e in cat_expenses)

        return {
            "period": f"{start} to {end}",
            "total_expenses": sum(float(e.amount) for e in expenses),
            "by_category": by_category,
            "expense_count": len(expenses)
        }

    # ==================== BANK RECONCILIATION ====================

    def import_transaction(self, venue_id: int, bank_account: str,
                           transaction_type: str, amount: float,
                           description: str, transaction_date: date,
                           reference: str = None) -> Dict[str, Any]:
        """Import a bank transaction."""
        from app.models.v6_features_models import BankTransaction

        if not self.db:
            return {"success": False, "error": "No database session"}

        if isinstance(transaction_type, TransactionType):
            transaction_type = transaction_type.value

        transaction = BankTransaction(
            venue_id=venue_id,
            bank_account=bank_account,
            transaction_type=transaction_type,
            amount=amount,
            description=description,
            transaction_date=transaction_date,
            reference=reference
        )

        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)

        logger.info(f"Imported transaction {transaction.id}: {description}")

        return {
            "success": True,
            "id": transaction.id,
            "venue_id": transaction.venue_id,
            "amount": float(transaction.amount),
            "transaction_date": transaction.transaction_date.isoformat()
        }

    def match_transaction(self, transaction_id: int, expense_id: int = None,
                          order_id: int = None) -> Dict[str, Any]:
        """Match a bank transaction to an expense or order."""
        from app.models.v6_features_models import BankTransaction

        if not self.db:
            return {"success": False, "error": "No database session"}

        transaction = self.db.query(BankTransaction).filter(
            BankTransaction.id == transaction_id
        ).first()

        if not transaction:
            return {"success": False, "error": "Transaction not found"}

        transaction.matched_expense_id = expense_id
        transaction.matched_order_id = order_id
        transaction.reconciled = True
        self.db.commit()

        return {
            "success": True,
            "transaction_id": transaction_id,
            "reconciled": True,
            "matched_expense_id": expense_id,
            "matched_order_id": order_id
        }

    def get_unreconciled_transactions(self, venue_id: int) -> List[Dict[str, Any]]:
        """Get unreconciled bank transactions."""
        from app.models.v6_features_models import BankTransaction

        if not self.db:
            return []

        transactions = self.db.query(BankTransaction).filter(
            BankTransaction.venue_id == venue_id,
            BankTransaction.reconciled == False
        ).order_by(BankTransaction.transaction_date.desc()).all()

        return [
            {
                "id": t.id,
                "venue_id": t.venue_id,
                "bank_account": t.bank_account,
                "transaction_type": t.transaction_type,
                "amount": float(t.amount),
                "description": t.description,
                "reference": t.reference,
                "transaction_date": t.transaction_date.isoformat(),
                "reconciled": t.reconciled
            }
            for t in transactions
        ]

    def get_reconciled_transactions(self, venue_id: int, start: date = None,
                                     end: date = None) -> List[Dict[str, Any]]:
        """Get reconciled bank transactions."""
        from app.models.v6_features_models import BankTransaction

        if not self.db:
            return []

        query = self.db.query(BankTransaction).filter(
            BankTransaction.venue_id == venue_id,
            BankTransaction.reconciled == True
        )

        if start:
            query = query.filter(BankTransaction.transaction_date >= start)
        if end:
            query = query.filter(BankTransaction.transaction_date <= end)

        transactions = query.order_by(BankTransaction.transaction_date.desc()).all()

        return [
            {
                "id": t.id,
                "bank_account": t.bank_account,
                "transaction_type": t.transaction_type,
                "amount": float(t.amount),
                "description": t.description,
                "transaction_date": t.transaction_date.isoformat(),
                "matched_expense_id": t.matched_expense_id,
                "matched_order_id": t.matched_order_id
            }
            for t in transactions
        ]

    def auto_match_transactions(self, venue_id: int) -> Dict[str, Any]:
        """Attempt to auto-match transactions with expenses."""
        from app.models.v6_features_models import BankTransaction, FinancialExpense

        if not self.db:
            return {"success": False, "error": "No database session"}

        unreconciled = self.db.query(BankTransaction).filter(
            BankTransaction.venue_id == venue_id,
            BankTransaction.reconciled == False,
            BankTransaction.transaction_type == "expense"
        ).all()

        matched = 0

        for txn in unreconciled:
            # Try to match by amount and date
            expense = self.db.query(FinancialExpense).filter(
                FinancialExpense.venue_id == venue_id,
                FinancialExpense.amount == txn.amount,
                FinancialExpense.expense_date == txn.transaction_date
            ).first()

            if expense:
                # Check if not already matched
                already_matched = self.db.query(BankTransaction).filter(
                    BankTransaction.matched_expense_id == expense.id
                ).first()

                if not already_matched:
                    txn.matched_expense_id = expense.id
                    txn.reconciled = True
                    matched += 1

        self.db.commit()

        logger.info(f"Auto-matched {matched} transactions for venue {venue_id}")
        return {"success": True, "matched_count": matched}

    # ==================== CASH FLOW FORECASTING ====================

    def forecast_cash_flow(self, venue_id: int, days: int = 30,
                           opening_balance: float = 50000) -> List[Dict[str, Any]]:
        """Generate cash flow forecast using historical data."""
        if not self.db:
            return []

        forecasts = []
        today = date.today()

        # Get historical averages from past 30 days
        past_30_days = today - timedelta(days=30)
        expenses = self.get_expenses(venue_id, past_30_days, today)
        total_expense = sum(e['amount'] for e in expenses)
        avg_daily_expense = total_expense / 30 if expenses else 0

        # Assume income from orders (would integrate with order service in production)
        avg_daily_income = avg_daily_expense * 1.3  # Assume 30% margin

        current_balance = opening_balance

        for i in range(days):
            forecast_date = today + timedelta(days=i)

            # Adjust for day of week
            day_factor = 1.2 if forecast_date.weekday() >= 5 else 1.0  # Weekend boost

            projected_income = avg_daily_income * day_factor
            projected_expenses = avg_daily_expense
            net_flow = projected_income - projected_expenses
            closing = current_balance + net_flow

            forecasts.append({
                "venue_id": venue_id,
                "forecast_date": forecast_date.isoformat(),
                "projected_income": round(projected_income, 2),
                "projected_expenses": round(projected_expenses, 2),
                "net_cash_flow": round(net_flow, 2),
                "opening_balance": round(current_balance, 2),
                "closing_balance": round(closing, 2),
                "confidence_level": 0.8
            })

            current_balance = closing

        return forecasts

    # ==================== BREAK-EVEN ANALYSIS ====================

    def calculate_break_even(self, venue_id: int, period_start: date,
                              period_end: date, current_revenue: float,
                              avg_check: float) -> Dict[str, Any]:
        """Calculate break-even analysis."""
        expenses = self.get_expenses(venue_id, period_start, period_end)

        # Fixed costs
        fixed_categories = ['rent', 'insurance', 'licenses', 'utilities']
        fixed_costs = sum(e['amount'] for e in expenses if e['category'] in fixed_categories)

        # Variable costs (food, supplies)
        variable_categories = ['food_cost', 'supplies']
        variable_expenses = sum(e['amount'] for e in expenses if e['category'] in variable_categories)
        variable_cost_percent = (variable_expenses / current_revenue * 100) if current_revenue else 35

        # Break-even calculation
        contribution_margin = 1 - (variable_cost_percent / 100)
        break_even_revenue = fixed_costs / contribution_margin if contribution_margin else 0
        break_even_covers = int(break_even_revenue / avg_check) if avg_check else 0

        margin_of_safety = ((current_revenue - break_even_revenue) / current_revenue * 100) if current_revenue else 0

        return {
            "venue_id": venue_id,
            "period": f"{period_start} to {period_end}",
            "fixed_costs": round(fixed_costs, 2),
            "variable_cost_percent": round(variable_cost_percent, 2),
            "avg_check": round(avg_check, 2),
            "break_even_revenue": round(break_even_revenue, 2),
            "break_even_covers": break_even_covers,
            "current_revenue": round(current_revenue, 2),
            "margin_of_safety": round(margin_of_safety, 2)
        }

    # ==================== PROFIT MARGIN ANALYSIS ====================

    def get_profit_margins(self, venue_id: int, start: date, end: date,
                           revenue: float) -> Dict[str, Any]:
        """Calculate profit margins for a period."""
        expenses = self.get_expenses(venue_id, start, end)
        total_expenses = sum(e['amount'] for e in expenses)

        food_cost = sum(e['amount'] for e in expenses if e['category'] == 'food_cost')
        labor_cost = sum(e['amount'] for e in expenses if e['category'] == 'labor')

        gross_profit = revenue - food_cost
        operating_profit = revenue - total_expenses

        return {
            "period": f"{start} to {end}",
            "revenue": round(revenue, 2),
            "food_cost": round(food_cost, 2),
            "food_cost_percent": round((food_cost / revenue * 100) if revenue else 0, 2),
            "labor_cost": round(labor_cost, 2),
            "labor_cost_percent": round((labor_cost / revenue * 100) if revenue else 0, 2),
            "total_expenses": round(total_expenses, 2),
            "gross_profit": round(gross_profit, 2),
            "gross_margin_percent": round((gross_profit / revenue * 100) if revenue else 0, 2),
            "operating_profit": round(operating_profit, 2),
            "operating_margin_percent": round((operating_profit / revenue * 100) if revenue else 0, 2)
        }

    # ==================== BUDGET MANAGEMENT ====================

    def set_budget(self, venue_id: int, category: str,
                   monthly_budget: float, year: int = None,
                   month: int = None) -> Dict[str, Any]:
        """Set budget for a category."""
        from app.models.v6_features_models import FinancialBudget

        if not self.db:
            return {"success": False, "error": "No database session"}

        if isinstance(category, ExpenseCategory):
            category = category.value

        today = date.today()
        year = year or today.year
        month = month or today.month

        # Check if budget already exists
        existing = self.db.query(FinancialBudget).filter(
            FinancialBudget.venue_id == venue_id,
            FinancialBudget.category == category,
            FinancialBudget.year == year,
            FinancialBudget.month == month
        ).first()

        if existing:
            existing.monthly_budget = monthly_budget
            budget = existing
        else:
            budget = FinancialBudget(
                venue_id=venue_id,
                category=category,
                monthly_budget=monthly_budget,
                year=year,
                month=month
            )
            self.db.add(budget)

        self.db.commit()
        self.db.refresh(budget)

        return {
            "success": True,
            "venue_id": venue_id,
            "category": category,
            "monthly_budget": float(budget.monthly_budget),
            "year": year,
            "month": month
        }

    def get_budget_status(self, venue_id: int, target_month: date = None) -> Dict[str, Any]:
        """Get budget status for a month."""
        from app.models.v6_features_models import FinancialBudget

        if not self.db:
            return {"error": "No database session"}

        if target_month is None:
            target_month = date.today()

        year = target_month.year
        month = target_month.month

        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(year, month + 1, 1) - timedelta(days=1)

        # Get expenses for the month
        expenses = self.get_expenses(venue_id, month_start, month_end)

        # Get budgets
        budgets = self.db.query(FinancialBudget).filter(
            FinancialBudget.venue_id == venue_id,
            FinancialBudget.year == year,
            FinancialBudget.month == month
        ).all()

        budget_map = {b.category: float(b.monthly_budget) for b in budgets}

        status = {}
        for cat in ExpenseCategory:
            spent = sum(e['amount'] for e in expenses if e['category'] == cat.value)
            budget = budget_map.get(cat.value, 0)
            status[cat.value] = {
                "budget": budget,
                "spent": round(spent, 2),
                "remaining": round(budget - spent, 2),
                "percent_used": round((spent / budget * 100) if budget else 0, 2)
            }

        return {
            "month": str(target_month),
            "year": year,
            "month_number": month,
            "categories": status,
            "total_budget": sum(b.get('budget', 0) for b in status.values()),
            "total_spent": sum(b.get('spent', 0) for b in status.values())
        }

    def list_budgets(self, venue_id: int, year: int = None, month: int = None) -> List[Dict[str, Any]]:
        """List all budgets for a venue with optional filtering by year/month."""
        from app.models.v6_features_models import FinancialBudget

        if not self.db:
            return []

        query = self.db.query(FinancialBudget).filter(
            FinancialBudget.venue_id == venue_id
        )

        if year is not None:
            query = query.filter(FinancialBudget.year == year)
        if month is not None:
            query = query.filter(FinancialBudget.month == month)

        budgets = query.order_by(
            FinancialBudget.year.desc(),
            FinancialBudget.month.desc(),
            FinancialBudget.category
        ).all()

        return [
            {
                "id": b.id,
                "venue_id": b.venue_id,
                "category": b.category,
                "monthly_budget": float(b.monthly_budget),
                "year": b.year,
                "month": b.month,
                "created_at": b.created_at.isoformat(),
                "updated_at": b.updated_at.isoformat()
            }
            for b in budgets
        ]

    def get_variance_analysis(self, venue_id: int, year: int = None,
                               month: int = None) -> Dict[str, Any]:
        """Calculate budget variance analysis comparing actual vs budgeted amounts."""
        from app.models.v6_features_models import FinancialBudget, FinancialExpense

        if not self.db:
            return {"error": "No database session"}

        # Default to current month if not specified
        if year is None or month is None:
            today = date.today()
            year = year or today.year
            month = month or today.month

        # Calculate month boundaries
        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(year, month + 1, 1) - timedelta(days=1)

        # Get budgets for the period
        budgets = self.db.query(FinancialBudget).filter(
            FinancialBudget.venue_id == venue_id,
            FinancialBudget.year == year,
            FinancialBudget.month == month
        ).all()

        # Get actual expenses for the period
        expenses = self.db.query(FinancialExpense).filter(
            FinancialExpense.venue_id == venue_id,
            FinancialExpense.expense_date >= month_start,
            FinancialExpense.expense_date <= month_end
        ).all()

        # Calculate actual spending by category
        actual_by_category = {}
        for expense in expenses:
            category = expense.category
            if category not in actual_by_category:
                actual_by_category[category] = 0
            actual_by_category[category] += float(expense.amount)

        # Create budget map
        budget_by_category = {b.category: float(b.monthly_budget) for b in budgets}

        # Calculate variances
        variances = {}
        total_budget = 0
        total_actual = 0
        total_variance = 0

        all_categories = set(list(budget_by_category.keys()) + list(actual_by_category.keys()))

        for category in all_categories:
            budgeted = budget_by_category.get(category, 0)
            actual = actual_by_category.get(category, 0)
            variance = budgeted - actual
            variance_percent = ((variance / budgeted) * 100) if budgeted > 0 else 0

            variances[category] = {
                "budgeted": round(budgeted, 2),
                "actual": round(actual, 2),
                "variance": round(variance, 2),
                "variance_percent": round(variance_percent, 2),
                "status": "over_budget" if variance < 0 else ("under_budget" if variance > 0 else "on_budget")
            }

            total_budget += budgeted
            total_actual += actual
            total_variance += variance

        total_variance_percent = ((total_variance / total_budget) * 100) if total_budget > 0 else 0

        return {
            "venue_id": venue_id,
            "year": year,
            "month": month,
            "period": f"{year}-{month:02d}",
            "month_start": month_start.isoformat(),
            "month_end": month_end.isoformat(),
            "categories": variances,
            "summary": {
                "total_budgeted": round(total_budget, 2),
                "total_actual": round(total_actual, 2),
                "total_variance": round(total_variance, 2),
                "total_variance_percent": round(total_variance_percent, 2),
                "budget_utilization": round((total_actual / total_budget * 100) if total_budget > 0 else 0, 2)
            },
            "over_budget_categories": [cat for cat, data in variances.items() if data["status"] == "over_budget"],
            "categories_count": len(variances)
        }

    def get_budget_alerts(self, venue_id: int, threshold_percent: float = 90.0) -> List[Dict[str, Any]]:
        """Get budget alerts for categories approaching or exceeding their budget."""
        from app.models.v6_features_models import FinancialBudget, FinancialExpense

        if not self.db:
            return []

        today = date.today()
        month_start = date(today.year, today.month, 1)

        # Get current month budgets
        budgets = self.db.query(FinancialBudget).filter(
            FinancialBudget.venue_id == venue_id,
            FinancialBudget.year == today.year,
            FinancialBudget.month == today.month
        ).all()

        if not budgets:
            return []

        # Get current month expenses
        expenses = self.db.query(FinancialExpense).filter(
            FinancialExpense.venue_id == venue_id,
            FinancialExpense.expense_date >= month_start,
            FinancialExpense.expense_date <= today
        ).all()

        # Calculate spending by category
        spending_by_category = {}
        for expense in expenses:
            category = expense.category
            if category not in spending_by_category:
                spending_by_category[category] = 0
            spending_by_category[category] += float(expense.amount)

        # Generate alerts
        alerts = []
        for budget in budgets:
            category = budget.category
            budgeted = float(budget.monthly_budget)
            spent = spending_by_category.get(category, 0)
            remaining = budgeted - spent
            percent_used = (spent / budgeted * 100) if budgeted > 0 else 0

            # Create alert if threshold exceeded or budget exceeded
            if percent_used >= threshold_percent or remaining < 0:
                severity = "critical" if percent_used >= 100 else ("warning" if percent_used >= threshold_percent else "info")

                alert = {
                    "category": category,
                    "budgeted": round(budgeted, 2),
                    "spent": round(spent, 2),
                    "remaining": round(remaining, 2),
                    "percent_used": round(percent_used, 2),
                    "severity": severity,
                    "message": self._generate_budget_alert_message(category, percent_used, remaining, budgeted),
                    "year": budget.year,
                    "month": budget.month,
                    "days_remaining_in_month": (date(today.year, today.month + 1, 1) - today - timedelta(days=1)).days if today.month < 12 else (date(today.year + 1, 1, 1) - today - timedelta(days=1)).days
                }
                alerts.append(alert)

        # Sort by severity and percent used
        severity_order = {"critical": 0, "warning": 1, "info": 2}
        alerts.sort(key=lambda x: (severity_order.get(x["severity"], 3), -x["percent_used"]))

        return alerts

    def _generate_budget_alert_message(self, category: str, percent_used: float,
                                        remaining: float, budgeted: float) -> str:
        """Generate a human-readable alert message."""
        if percent_used >= 100:
            overage = abs(remaining)
            return f"{category.replace('_', ' ').title()} budget exceeded by {overage:.2f} BGN ({percent_used:.1f}% used)"
        elif percent_used >= 90:
            return f"{category.replace('_', ' ').title()} budget at {percent_used:.1f}% - only {remaining:.2f} BGN remaining"
        else:
            return f"{category.replace('_', ' ').title()} budget warning - {percent_used:.1f}% used"

    # ==================== DASHBOARD ====================

    def get_financial_dashboard(self, venue_id: int) -> Dict[str, Any]:
        """Get financial dashboard summary."""
        today = date.today()
        month_start = date(today.year, today.month, 1)

        # Get current month expenses
        expenses = self.get_expenses(venue_id, month_start, today)
        total_expenses = sum(e['amount'] for e in expenses)

        # Get unreconciled transactions
        unreconciled = self.get_unreconciled_transactions(venue_id)

        # Get budget status
        budget_status = self.get_budget_status(venue_id, today)

        # Get cash flow forecast
        forecast = self.forecast_cash_flow(venue_id, days=7)

        return {
            "venue_id": venue_id,
            "date": today.isoformat(),
            "mtd_expenses": round(total_expenses, 2),
            "expense_count": len(expenses),
            "unreconciled_transactions": len(unreconciled),
            "unreconciled_amount": sum(t['amount'] for t in unreconciled),
            "budget_status": budget_status,
            "week_forecast": forecast[:7] if forecast else [],
            "top_expenses": sorted(expenses, key=lambda x: x['amount'], reverse=True)[:5]
        }

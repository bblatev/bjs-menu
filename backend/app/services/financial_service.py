"""
Financial Services - Chart of Accounts, Journal Entries, Bank Reconciliation, Budgets
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timezone
import logging

from app.models.financial_models import (
    ChartOfAccounts, AccountType, JournalEntry, JournalEntryLine,
    BankAccount, BankTransaction, BankReconciliation,
    BudgetLineItem, CashCount,
)
from app.models.operations import Budget, DailyReconciliation

logger = logging.getLogger(__name__)


class ChartOfAccountsService:
    """
    Manage Chart of Accounts for general ledger accounting.
    """

    def __init__(self, db: Session):
        self.db = db

    def create_account(
        self,
        venue_id: int,
        account_code: str,
        account_name: str,
        account_type: str,
        parent_id: Optional[int] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new GL account."""
        # Validate account type
        try:
            acct_type = AccountType(account_type)
        except ValueError:
            raise ValueError(f"Invalid account type: {account_type}")

        # Check for duplicate code
        existing = self.db.query(ChartOfAccounts).filter(
            ChartOfAccounts.venue_id == venue_id,
            ChartOfAccounts.account_code == account_code
        ).first()

        if existing:
            raise ValueError(f"Account code {account_code} already exists")

        account = ChartOfAccounts(
            venue_id=venue_id,
            account_code=account_code,
            account_name=account_name,
            account_type=acct_type,
            parent_id=parent_id,
            description=description,
            is_active=True,
            current_balance=0
        )

        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)

        return self._account_to_dict(account)

    def get_accounts(
        self,
        venue_id: int,
        account_type: Optional[str] = None,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Get all accounts for a venue."""
        query = self.db.query(ChartOfAccounts).filter(
            ChartOfAccounts.venue_id == venue_id
        )

        if active_only:
            query = query.filter(ChartOfAccounts.is_active == True)

        if account_type:
            try:
                acct_type = AccountType(account_type)
                query = query.filter(ChartOfAccounts.account_type == acct_type)
            except ValueError:
                pass

        accounts = query.order_by(ChartOfAccounts.account_code).all()
        return [self._account_to_dict(a) for a in accounts]

    def get_account_balance(self, account_id: int) -> Dict[str, Any]:
        """Get current balance for an account."""
        account = self.db.query(ChartOfAccounts).filter(
            ChartOfAccounts.id == account_id
        ).first()

        if not account:
            raise ValueError("Account not found")

        # Calculate balance from journal entries
        debits = self.db.query(func.sum(JournalEntryLine.debit_amount)).filter(
            JournalEntryLine.account_id == account_id
        ).scalar() or 0

        credits = self.db.query(func.sum(JournalEntryLine.credit_amount)).filter(
            JournalEntryLine.account_id == account_id
        ).scalar() or 0

        # Calculate balance based on account type (debit or credit normal)
        if account.account_type in [AccountType.ASSET, AccountType.EXPENSE]:
            balance = float(debits) - float(credits)
        else:
            balance = float(credits) - float(debits)

        return {
            "account_id": account_id,
            "account_code": account.account_code,
            "account_name": account.account_name,
            "total_debits": float(debits),
            "total_credits": float(credits),
            "current_balance": balance
        }

    def _account_to_dict(self, account: ChartOfAccounts) -> Dict[str, Any]:
        return {
            "id": account.id,
            "account_code": account.account_code,
            "account_name": account.account_name,
            "account_type": account.account_type.value if account.account_type else None,
            "parent_id": account.parent_id,
            "description": account.description,
            "is_active": account.is_active,
            "current_balance": float(account.current_balance or 0)
        }


class JournalEntryService:
    """
    Manage journal entries for double-entry accounting.
    """

    def __init__(self, db: Session):
        self.db = db

    def create_journal_entry(
        self,
        venue_id: int,
        entry_date: date,
        description: str,
        lines: List[Dict[str, Any]],
        reference_type: Optional[str] = None,
        reference_id: Optional[int] = None,
        created_by: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create a journal entry with multiple lines.

        Args:
            lines: List of dicts with account_id, debit_amount, credit_amount, description
        """
        # Validate that debits equal credits
        total_debits = sum(float(line.get("debit_amount", 0)) for line in lines)
        total_credits = sum(float(line.get("credit_amount", 0)) for line in lines)

        if abs(total_debits - total_credits) > 0.01:
            raise ValueError(f"Debits ({total_debits}) must equal credits ({total_credits})")

        # Generate entry number
        last_entry = self.db.query(JournalEntry).filter(
            JournalEntry.venue_id == venue_id
        ).order_by(JournalEntry.id.desc()).first()

        entry_number = f"JE-{datetime.now(timezone.utc).strftime('%Y%m')}-{(last_entry.id + 1) if last_entry else 1:04d}"

        # Create journal entry
        entry = JournalEntry(
            venue_id=venue_id,
            entry_number=entry_number,
            entry_date=entry_date,
            description=description,
            total_debit=total_debits,
            total_credit=total_credits,
            status="posted",
            reference_type=reference_type,
            reference_id=reference_id,
            posted_at=datetime.now(timezone.utc),
            created_by=created_by
        )

        self.db.add(entry)
        self.db.flush()

        # Create journal entry lines
        for i, line in enumerate(lines):
            entry_line = JournalEntryLine(
                journal_entry_id=entry.id,
                account_id=line["account_id"],
                debit_amount=line.get("debit_amount", 0),
                credit_amount=line.get("credit_amount", 0),
                description=line.get("description", ""),
                line_number=i + 1
            )
            self.db.add(entry_line)

            # Update account balance
            account = self.db.query(ChartOfAccounts).filter(
                ChartOfAccounts.id == line["account_id"]
            ).first()

            if account:
                debit = float(line.get("debit_amount", 0))
                credit = float(line.get("credit_amount", 0))

                if account.account_type in [AccountType.ASSET, AccountType.EXPENSE]:
                    account.current_balance = float(account.current_balance or 0) + debit - credit
                else:
                    account.current_balance = float(account.current_balance or 0) + credit - debit

        self.db.commit()
        self.db.refresh(entry)

        return {
            "id": entry.id,
            "entry_number": entry.entry_number,
            "entry_date": entry.entry_date.isoformat(),
            "description": entry.description,
            "total_debit": float(entry.total_debit),
            "total_credit": float(entry.total_credit),
            "status": entry.status,
            "line_count": len(lines)
        }

    def get_journal_entries(
        self,
        venue_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get journal entries for a venue."""
        query = self.db.query(JournalEntry).filter(
            JournalEntry.venue_id == venue_id
        )

        if start_date:
            query = query.filter(JournalEntry.entry_date >= start_date)
        if end_date:
            query = query.filter(JournalEntry.entry_date <= end_date)

        total = query.count()
        entries = query.order_by(JournalEntry.entry_date.desc()).offset(offset).limit(limit).all()

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "items": [
                {
                    "id": e.id,
                    "entry_number": e.entry_number,
                    "entry_date": e.entry_date.isoformat(),
                    "description": e.description,
                    "total_debit": float(e.total_debit or 0),
                    "total_credit": float(e.total_credit or 0),
                    "status": e.status
                }
                for e in entries
            ]
        }


class BankReconciliationService:
    """
    Handle bank reconciliation - matching bank transactions with system records.
    """

    def __init__(self, db: Session):
        self.db = db

    def create_bank_account(
        self,
        venue_id: int,
        account_name: str,
        bank_name: str,
        account_number: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Create a new bank account record."""
        account = BankAccount(
            venue_id=venue_id,
            account_name=account_name,
            bank_name=bank_name,
            account_number=account_number,
            current_balance=0,
            is_active=True,
            **kwargs
        )

        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)

        return {
            "id": account.id,
            "account_name": account.account_name,
            "bank_name": account.bank_name,
            "account_number": account.account_number[-4:] + "****",  # Mask
            "current_balance": float(account.current_balance or 0)
        }

    def import_bank_transactions(
        self,
        bank_account_id: int,
        transactions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Import bank transactions from statement."""
        imported = 0
        duplicates = 0

        for txn in transactions:
            # Check for duplicates
            existing = self.db.query(BankTransaction).filter(
                BankTransaction.bank_account_id == bank_account_id,
                BankTransaction.transaction_date == txn["date"],
                BankTransaction.amount == txn["amount"],
                BankTransaction.reference == txn.get("reference")
            ).first()

            if existing:
                duplicates += 1
                continue

            bank_txn = BankTransaction(
                bank_account_id=bank_account_id,
                transaction_date=txn["date"],
                amount=txn["amount"],
                description=txn.get("description"),
                reference=txn.get("reference"),
                transaction_type=txn.get("type", "other"),
                is_reconciled=False
            )
            self.db.add(bank_txn)
            imported += 1

        self.db.commit()

        return {
            "imported": imported,
            "duplicates": duplicates,
            "total_processed": len(transactions)
        }

    def start_reconciliation(
        self,
        venue_id: int,
        bank_account_id: int,
        statement_date: date,
        statement_balance: float
    ) -> Dict[str, Any]:
        """Start a new bank reconciliation session."""
        reconciliation = BankReconciliation(
            venue_id=venue_id,
            bank_account_id=bank_account_id,
            statement_date=statement_date,
            statement_balance=statement_balance,
            status="in_progress",
            started_at=datetime.now(timezone.utc)
        )

        self.db.add(reconciliation)
        self.db.commit()
        self.db.refresh(reconciliation)

        return {
            "id": reconciliation.id,
            "bank_account_id": bank_account_id,
            "statement_date": statement_date.isoformat(),
            "statement_balance": statement_balance,
            "status": "in_progress"
        }

    def match_transaction(
        self,
        reconciliation_id: int,
        bank_transaction_id: int,
        system_record_type: str,
        system_record_id: int
    ) -> Dict[str, Any]:
        """Match a bank transaction with a system record."""
        bank_txn = self.db.query(BankTransaction).filter(
            BankTransaction.id == bank_transaction_id
        ).first()

        if not bank_txn:
            raise ValueError("Bank transaction not found")

        bank_txn.is_reconciled = True
        bank_txn.reconciled_at = datetime.now(timezone.utc)
        bank_txn.matched_record_type = system_record_type
        bank_txn.matched_record_id = system_record_id

        self.db.commit()

        return {
            "bank_transaction_id": bank_transaction_id,
            "matched": True,
            "matched_to": f"{system_record_type}#{system_record_id}"
        }

    def complete_reconciliation(self, reconciliation_id: int) -> Dict[str, Any]:
        """Complete a reconciliation session."""
        reconciliation = self.db.query(BankReconciliation).filter(
            BankReconciliation.id == reconciliation_id
        ).first()

        if not reconciliation:
            raise ValueError("Reconciliation not found")

        # Calculate reconciled balance
        matched_txns = self.db.query(BankTransaction).filter(
            BankTransaction.bank_account_id == reconciliation.bank_account_id,
            BankTransaction.is_reconciled == True
        ).all()

        reconciled_balance = sum(float(t.amount) for t in matched_txns)

        reconciliation.reconciled_balance = reconciled_balance
        reconciliation.difference = float(reconciliation.statement_balance) - reconciled_balance
        reconciliation.status = "completed"
        reconciliation.completed_at = datetime.now(timezone.utc)

        self.db.commit()

        return {
            "id": reconciliation_id,
            "status": "completed",
            "statement_balance": float(reconciliation.statement_balance),
            "reconciled_balance": reconciled_balance,
            "difference": float(reconciliation.difference)
        }


class BudgetService:
    """
    Manage budgets and budget variance tracking.
    """

    def __init__(self, db: Session):
        self.db = db

    def create_budget(
        self,
        venue_id: int,
        name: str,
        budget_type: str,
        period_start: date,
        period_end: date,
        line_items: List[Dict[str, Any]],
        created_by: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a new budget with line items."""
        budget = Budget(
            venue_id=venue_id,
            name=name,
            budget_type=budget_type,
            period_start=period_start,
            period_end=period_end,
            status="active",
            created_by=created_by
        )

        self.db.add(budget)
        self.db.flush()

        total_amount = 0
        for item in line_items:
            line = BudgetLineItem(
                budget_id=budget.id,
                account_id=item.get("account_id"),
                category=item.get("category"),
                budgeted_amount=item["amount"],
                actual_amount=0
            )
            self.db.add(line)
            total_amount += float(item["amount"])

        budget.total_amount = total_amount

        self.db.commit()
        self.db.refresh(budget)

        return {
            "id": budget.id,
            "name": budget.name,
            "budget_type": budget.budget_type,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "total_amount": total_amount,
            "line_count": len(line_items)
        }

    def get_budget_variance(self, budget_id: int) -> Dict[str, Any]:
        """Get budget vs actual variance report."""
        budget = self.db.query(Budget).filter(Budget.id == budget_id).first()

        if not budget:
            raise ValueError("Budget not found")

        line_items = self.db.query(BudgetLineItem).filter(
            BudgetLineItem.budget_id == budget_id
        ).all()

        total_budgeted = sum(float(item.budgeted_amount or 0) for item in line_items)
        total_actual = sum(float(item.actual_amount or 0) for item in line_items)
        total_variance = total_budgeted - total_actual

        return {
            "budget_id": budget_id,
            "budget_name": budget.name,
            "period": {
                "start": budget.period_start.isoformat(),
                "end": budget.period_end.isoformat()
            },
            "summary": {
                "total_budgeted": total_budgeted,
                "total_actual": total_actual,
                "variance": total_variance,
                "variance_pct": (total_variance / total_budgeted * 100) if total_budgeted > 0 else 0
            },
            "line_items": [
                {
                    "id": item.id,
                    "account_id": item.account_id,
                    "category": item.category,
                    "budgeted": float(item.budgeted_amount or 0),
                    "actual": float(item.actual_amount or 0),
                    "variance": float(item.budgeted_amount or 0) - float(item.actual_amount or 0)
                }
                for item in line_items
            ]
        }


class DailyReconciliationService:
    """
    Handle end-of-day reconciliation and cash counting.
    """

    def __init__(self, db: Session):
        self.db = db

    def start_daily_close(
        self,
        venue_id: int,
        business_date: date,
        closed_by: int
    ) -> Dict[str, Any]:
        """Start daily close/reconciliation process."""
        # Check if already exists
        existing = self.db.query(DailyReconciliation).filter(
            DailyReconciliation.venue_id == venue_id,
            DailyReconciliation.business_date == business_date
        ).first()

        if existing:
            return {
                "id": existing.id,
                "status": existing.status,
                "message": "Daily reconciliation already exists"
            }

        reconciliation = DailyReconciliation(
            venue_id=venue_id,
            business_date=business_date,
            status="in_progress",
            opened_by=closed_by,
            opened_at=datetime.now(timezone.utc)
        )

        self.db.add(reconciliation)
        self.db.commit()
        self.db.refresh(reconciliation)

        return {
            "id": reconciliation.id,
            "business_date": business_date.isoformat(),
            "status": "in_progress"
        }

    def record_cash_count(
        self,
        reconciliation_id: int,
        denomination_counts: Dict[str, int],
        counted_by: int
    ) -> Dict[str, Any]:
        """Record cash drawer count."""
        reconciliation = self.db.query(DailyReconciliation).filter(
            DailyReconciliation.id == reconciliation_id
        ).first()

        if not reconciliation:
            raise ValueError("Reconciliation not found")

        # Calculate total from denominations
        denominations = {
            "100": 100, "50": 50, "20": 20, "10": 10, "5": 5, "2": 2, "1": 1,
            "0.50": 0.50, "0.20": 0.20, "0.10": 0.10, "0.05": 0.05, "0.02": 0.02, "0.01": 0.01
        }

        total = sum(
            denominations.get(denom, float(denom)) * count
            for denom, count in denomination_counts.items()
        )

        cash_count = CashCount(
            daily_reconciliation_id=reconciliation_id,
            count_type="closing",
            denomination_counts=denomination_counts,
            total_amount=total,
            counted_by=counted_by,
            counted_at=datetime.now(timezone.utc)
        )

        self.db.add(cash_count)

        reconciliation.actual_cash = total

        self.db.commit()

        return {
            "reconciliation_id": reconciliation_id,
            "total_counted": total,
            "count_type": "closing"
        }

    def complete_daily_close(
        self,
        reconciliation_id: int,
        closed_by: int,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Complete the daily close process."""

        reconciliation = self.db.query(DailyReconciliation).filter(
            DailyReconciliation.id == reconciliation_id
        ).first()

        if not reconciliation:
            raise ValueError("Reconciliation not found")

        # Calculate expected totals from orders
        # This would typically involve summing all payments by type
        # Simplified for this implementation

        reconciliation.status = "completed"
        reconciliation.closed_by = closed_by
        reconciliation.closed_at = datetime.now(timezone.utc)
        reconciliation.notes = notes

        # Calculate variance
        if reconciliation.expected_cash and reconciliation.actual_cash:
            reconciliation.cash_variance = float(reconciliation.actual_cash) - float(reconciliation.expected_cash)

        self.db.commit()

        return {
            "id": reconciliation_id,
            "status": "completed",
            "business_date": reconciliation.business_date.isoformat(),
            "expected_cash": float(reconciliation.expected_cash or 0),
            "actual_cash": float(reconciliation.actual_cash or 0),
            "cash_variance": float(reconciliation.cash_variance or 0),
            "closed_at": reconciliation.closed_at.isoformat()
        }


# Factory functions
def get_chart_of_accounts_service(db: Session) -> ChartOfAccountsService:
    return ChartOfAccountsService(db)

def get_journal_entry_service(db: Session) -> JournalEntryService:
    return JournalEntryService(db)

def get_bank_reconciliation_service(db: Session) -> BankReconciliationService:
    return BankReconciliationService(db)

def get_budget_service(db: Session) -> BudgetService:
    return BudgetService(db)

def get_daily_reconciliation_service(db: Session) -> DailyReconciliationService:
    return DailyReconciliationService(db)

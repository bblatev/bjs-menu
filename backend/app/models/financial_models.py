"""
Financial and Accounting Models
Implements Chart of Accounts, Journal Entries, Bank Reconciliation, Budgets, etc.
"""
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Text, JSON, Enum, UniqueConstraint, Index, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum
from app.db.base import Base


# ============================================================================
# CHART OF ACCOUNTS MODELS
# ============================================================================

class AccountType(str, enum.Enum):
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    REVENUE = "revenue"
    EXPENSE = "expense"
    COST_OF_GOODS_SOLD = "cogs"


class ChartOfAccounts(Base):
    """Chart of Accounts - General Ledger accounts"""
    __tablename__ = "chart_of_accounts"

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    account_code = Column(String(20), nullable=False, index=True)
    account_name = Column(String(200), nullable=False)
    account_type = Column(Enum(AccountType), nullable=False)

    parent_account_id = Column(Integer, ForeignKey("chart_of_accounts.id"), nullable=True)
    description = Column(Text, nullable=True)

    # Balance tracking
    opening_balance = Column(Numeric(14, 2), default=0)
    current_balance = Column(Numeric(14, 2), default=0)

    # Flags
    is_active = Column(Boolean, default=True)
    is_system_account = Column(Boolean, default=False)  # Cannot be deleted
    is_bank_account = Column(Boolean, default=False)
    is_control_account = Column(Boolean, default=False)  # Subsidiary ledger control

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    venue = relationship("Venue", backref="chart_of_accounts")
    parent_account = relationship("ChartOfAccounts", remote_side=[id], backref="sub_accounts")
    journal_lines = relationship("JournalEntryLine", back_populates="account")

    __table_args__ = (
        UniqueConstraint('venue_id', 'account_code', name='uq_venue_account_code'),
        Index('idx_account_type', 'venue_id', 'account_type'),
        {'extend_existing': True},
    )


class JournalEntryStatus(str, enum.Enum):
    DRAFT = "draft"
    POSTED = "posted"
    REVERSED = "reversed"


class JournalEntry(Base):
    """Journal entries for double-entry accounting"""
    __tablename__ = "journal_entries"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    entry_number = Column(String(50), nullable=False, unique=True, index=True)
    entry_date = Column(DateTime(timezone=True), nullable=False, index=True)

    description = Column(Text, nullable=True)
    reference = Column(String(100), nullable=True)  # Invoice/PO number
    source = Column(String(50), nullable=True)  # sales, purchase, adjustment, etc.

    status = Column(Enum(JournalEntryStatus), default=JournalEntryStatus.DRAFT)

    # Totals (must balance)
    total_debit = Column(Numeric(14, 2), default=0)
    total_credit = Column(Numeric(14, 2), default=0)

    # Tracking
    created_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    posted_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    posted_at = Column(DateTime(timezone=True), nullable=True)

    # Reversal tracking
    reversed_by_entry_id = Column(Integer, ForeignKey("journal_entries.id"), nullable=True)
    reverses_entry_id = Column(Integer, ForeignKey("journal_entries.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    venue = relationship("Venue", backref="journal_entries")
    lines = relationship("JournalEntryLine", back_populates="journal_entry", cascade="all, delete-orphan")
    created_by_user = relationship("StaffUser", foreign_keys=[created_by])
    posted_by_user = relationship("StaffUser", foreign_keys=[posted_by])


class JournalEntryLine(Base):
    """Individual lines in a journal entry"""
    __tablename__ = "journal_entry_lines"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    journal_entry_id = Column(Integer, ForeignKey("journal_entries.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("chart_of_accounts.id"), nullable=False)

    description = Column(String(500), nullable=True)

    debit_amount = Column(Numeric(14, 2), default=0)
    credit_amount = Column(Numeric(14, 2), default=0)

    # Reference to source document
    source_type = Column(String(50), nullable=True)  # order, purchase_order, expense
    source_id = Column(Integer, nullable=True)

    journal_entry = relationship("JournalEntry", back_populates="lines")
    account = relationship("ChartOfAccounts", back_populates="journal_lines")


# ============================================================================
# BANK ACCOUNT & RECONCILIATION MODELS
# ============================================================================

class BankAccount(Base):
    """Bank accounts for reconciliation"""
    __tablename__ = "bank_accounts"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    gl_account_id = Column(Integer, ForeignKey("chart_of_accounts.id"), nullable=True)

    bank_name = Column(String(200), nullable=False)
    account_name = Column(String(200), nullable=False)
    account_number = Column(String(50), nullable=False)
    iban = Column(String(50), nullable=True)
    swift_bic = Column(String(20), nullable=True)
    currency = Column(String(10), default="BGN")

    opening_balance = Column(Numeric(14, 2), default=0)
    current_balance = Column(Numeric(14, 2), default=0)
    last_reconciled_date = Column(DateTime(timezone=True), nullable=True)
    last_reconciled_balance = Column(Numeric(14, 2), nullable=True)

    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    venue = relationship("Venue", backref="bank_accounts")
    gl_account = relationship("ChartOfAccounts", backref="bank_account")
    transactions = relationship("BankTransaction", back_populates="bank_account")
    reconciliations = relationship("BankReconciliation", back_populates="bank_account")


class BankTransactionType(str, enum.Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRANSFER = "transfer"
    FEE = "fee"
    INTEREST = "interest"
    PAYMENT = "payment"
    RECEIPT = "receipt"


class BankTransaction(Base):
    """Bank transactions for reconciliation"""
    __tablename__ = "bank_transactions"

    id = Column(Integer, primary_key=True, index=True)
    bank_account_id = Column(Integer, ForeignKey("bank_accounts.id"), nullable=False)

    transaction_date = Column(DateTime(timezone=True), nullable=False, index=True)
    value_date = Column(DateTime(timezone=True), nullable=True)

    transaction_type = Column(Enum(BankTransactionType), nullable=False)
    description = Column(Text, nullable=True)
    reference = Column(String(100), nullable=True)

    amount = Column(Numeric(14, 2), nullable=False)  # Positive for deposits, negative for withdrawals
    balance_after = Column(Numeric(14, 2), nullable=True)

    # Reconciliation status
    is_reconciled = Column(Boolean, default=False)
    reconciliation_id = Column(Integer, ForeignKey("bank_reconciliations.id"), nullable=True)
    matched_transaction_id = Column(Integer, nullable=True)  # Internal transaction ID matched
    matched_type = Column(String(50), nullable=True)  # order, expense, transfer, etc.

    # Import tracking
    import_batch_id = Column(String(100), nullable=True)
    external_id = Column(String(100), nullable=True)  # Bank's transaction ID

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    bank_account = relationship("BankAccount", back_populates="transactions")
    reconciliation = relationship("BankReconciliation", back_populates="transactions")

    __table_args__ = (
        Index('idx_bank_tx_date', 'bank_account_id', 'transaction_date'),
        {'extend_existing': True},
    )


class ReconciliationStatus(str, enum.Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class BankReconciliation(Base):
    """Bank reconciliation sessions"""
    __tablename__ = "bank_reconciliations"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    bank_account_id = Column(Integer, ForeignKey("bank_accounts.id"), nullable=False)

    reconciliation_date = Column(DateTime(timezone=True), nullable=False)
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)

    statement_balance = Column(Numeric(14, 2), nullable=False)  # From bank statement
    book_balance = Column(Numeric(14, 2), nullable=False)  # From our records

    # Reconciliation items
    outstanding_deposits = Column(Numeric(14, 2), default=0)
    outstanding_withdrawals = Column(Numeric(14, 2), default=0)
    bank_charges = Column(Numeric(14, 2), default=0)
    adjustments = Column(Numeric(14, 2), default=0)

    reconciled_balance = Column(Numeric(14, 2), nullable=True)
    difference = Column(Numeric(14, 2), nullable=True)

    status = Column(Enum(ReconciliationStatus), default=ReconciliationStatus.IN_PROGRESS)
    notes = Column(Text, nullable=True)

    created_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    completed_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    venue = relationship("Venue", backref="bank_reconciliations")
    bank_account = relationship("BankAccount", back_populates="reconciliations")
    transactions = relationship("BankTransaction", back_populates="reconciliation")
    created_by_user = relationship("StaffUser", foreign_keys=[created_by])
    completed_by_user = relationship("StaffUser", foreign_keys=[completed_by])


# ============================================================================
# PAYMENT METHOD MODELS
# ============================================================================

class PaymentMethod(Base):
    """Payment method configuration"""
    __tablename__ = "payment_methods"

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    gl_account_id = Column(Integer, ForeignKey("chart_of_accounts.id"), nullable=True)

    code = Column(String(20), nullable=False)  # cash, card, voucher, gift_card
    name = Column(JSON, nullable=False)  # Multilingual

    payment_type = Column(String(50), nullable=False)  # cash, card, digital, voucher

    # For card payments
    gateway = Column(String(50), nullable=True)  # stripe, borica, epay
    gateway_config = Column(JSON, nullable=True)  # Gateway-specific config

    # Fees
    fee_type = Column(String(20), nullable=True)  # percentage, fixed
    fee_amount = Column(Numeric(8, 4), nullable=True)

    # Display
    icon = Column(String(50), nullable=True)
    sort_order = Column(Integer, default=0)

    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    requires_approval = Column(Boolean, default=False)  # Manager approval needed

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    venue = relationship("Venue", backref="payment_methods")
    gl_account = relationship("ChartOfAccounts", backref="payment_method")

    __table_args__ = (
        UniqueConstraint('venue_id', 'code', name='uq_venue_payment_code'),
        {'extend_existing': True},
    )


# ============================================================================
# TAX MODELS
# ============================================================================

class TaxRate(Base):
    """Tax rate definitions"""
    __tablename__ = "tax_rates"

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    code = Column(String(20), nullable=False)
    name = Column(String(100), nullable=False)
    rate = Column(Numeric(5, 2), nullable=False)  # Percentage

    tax_type = Column(String(50), nullable=False)  # vat, sales, service

    # GL accounts for tax
    tax_collected_account_id = Column(Integer, ForeignKey("chart_of_accounts.id"), nullable=True)
    tax_paid_account_id = Column(Integer, ForeignKey("chart_of_accounts.id"), nullable=True)

    is_default = Column(Boolean, default=False)
    is_inclusive = Column(Boolean, default=True)  # Tax included in price
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    venue = relationship("Venue", backref="tax_rates")

    __table_args__ = (
        UniqueConstraint('venue_id', 'code', name='uq_venue_tax_code'),
        {'extend_existing': True},
    )


# ============================================================================
# EXPENSE MODELS
# ============================================================================

class ExpenseCategory(Base):
    """Expense categories"""
    __tablename__ = "expense_categories"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    gl_account_id = Column(Integer, ForeignKey("chart_of_accounts.id"), nullable=True)

    name = Column(String(100), nullable=False)
    code = Column(String(20), nullable=True)
    description = Column(Text, nullable=True)

    parent_category_id = Column(Integer, ForeignKey("expense_categories.id"), nullable=True)

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    venue = relationship("Venue", backref="expense_categories")
    gl_account = relationship("ChartOfAccounts", backref="expense_category")
    parent_category = relationship("ExpenseCategory", remote_side=[id], backref="sub_categories")
    expenses = relationship("Expense", back_populates="category")


class ExpenseStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"


class Expense(Base):
    """Expense tracking"""
    __tablename__ = "expenses"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("expense_categories.id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)

    expense_date = Column(DateTime(timezone=True), nullable=False, index=True)
    description = Column(Text, nullable=False)
    reference = Column(String(100), nullable=True)  # Invoice number

    amount = Column(Numeric(14, 2), nullable=False)
    tax_amount = Column(Numeric(14, 2), default=0)
    total_amount = Column(Numeric(14, 2), nullable=False)

    payment_method_id = Column(Integer, ForeignKey("payment_methods.id"), nullable=True)
    payment_date = Column(DateTime(timezone=True), nullable=True)
    payment_reference = Column(String(100), nullable=True)

    status = Column(Enum(ExpenseStatus), default=ExpenseStatus.DRAFT)

    # Approval workflow
    requires_approval = Column(Boolean, default=False)
    approved_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Attachments
    receipt_url = Column(String(500), nullable=True)
    attachments = Column(JSON, nullable=True)  # List of attachment URLs

    # Journal entry link
    journal_entry_id = Column(Integer, ForeignKey("journal_entries.id"), nullable=True)

    created_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    venue = relationship("Venue", backref="expenses")
    category = relationship("ExpenseCategory", back_populates="expenses")
    supplier = relationship("Supplier", backref="expenses")
    payment_method = relationship("PaymentMethod", backref="expenses")
    approved_by_user = relationship("StaffUser", foreign_keys=[approved_by])
    created_by_user = relationship("StaffUser", foreign_keys=[created_by])
    journal_entry = relationship("JournalEntry", backref="expense")


class BudgetLineItem(Base):
    """Individual line item within a budget"""
    __tablename__ = "budget_line_items"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    budget_id = Column(Integer, ForeignKey('budgets.id'), nullable=False, index=True)
    category = Column(String(100), nullable=False)
    subcategory = Column(String(100), nullable=True)
    planned_amount = Column(Numeric(12, 2), nullable=False)
    actual_amount = Column(Numeric(12, 2), default=0)
    variance = Column(Numeric(12, 2), default=0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    budget = relationship("Budget", backref="line_items")


class CashCount(Base):
    """Cash count record for daily reconciliation"""
    __tablename__ = "cash_counts"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    reconciliation_id = Column(Integer, ForeignKey('daily_reconciliations.id'), nullable=False, index=True)
    denomination = Column(String(20), nullable=False)
    count = Column(Integer, nullable=False, default=0)
    value = Column(Numeric(12, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    reconciliation = relationship("DailyReconciliation", backref="cash_counts")



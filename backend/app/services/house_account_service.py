"""
House Accounts Service - Complete Implementation with Database Integration
Missing Feature: House Accounts (iiko & Toast have this)

Features:
- Corporate account management
- Credit limits and terms
- Monthly billing
- Statement generation
- Payment tracking
- Account aging reports
- Multi-location support
"""

from datetime import datetime, timedelta, timezone, date
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from decimal import Decimal
import uuid
import enum
import logging

from app.models import Order, HouseAccount, HouseAccountTransaction

logger = logging.getLogger(__name__)


class HouseAccountStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"
    PENDING_APPROVAL = "pending_approval"


class HouseAccountType(str, enum.Enum):
    CORPORATE = "corporate"
    VIP = "vip"
    STAFF = "staff"
    PARTNER = "partner"


class PaymentTerms(str, enum.Enum):
    NET_7 = "net_7"      # Payment due in 7 days
    NET_15 = "net_15"    # Payment due in 15 days
    NET_30 = "net_30"    # Payment due in 30 days
    NET_45 = "net_45"    # Payment due in 45 days
    ON_DEMAND = "on_demand"  # Pay when requested


class HouseAccountService:
    """Complete House Account Management Service with Database Integration"""

    def __init__(self, db: Session):
        self.db = db

    # ========== ACCOUNT MANAGEMENT ==========

    def create_account(
        self,
        venue_id: int,
        account_name: str,
        account_type: str,
        contact_name: str,
        contact_email: str,
        contact_phone: str,
        billing_address: str,
        credit_limit: float = 5000.0,
        payment_terms: str = "net_30",
        discount_percentage: float = 0.0,
        tax_id: Optional[str] = None,
        notes: Optional[str] = None,
        authorized_users: Optional[List[Dict]] = None,
        created_by: int = None
    ) -> Dict[str, Any]:
        """
        Create a new house account

        Args:
            venue_id: Venue ID
            account_name: Company/Account name
            account_type: Type of account (corporate, vip, staff, partner)
            contact_name: Primary contact name
            contact_email: Contact email
            contact_phone: Contact phone
            billing_address: Billing address
            credit_limit: Maximum credit allowed
            payment_terms: Payment terms (net_7, net_15, net_30, etc.)
            discount_percentage: Automatic discount for this account
            tax_id: Tax/VAT ID
            notes: Additional notes
            authorized_users: List of users who can charge to this account
            created_by: Staff ID who created the account

        Returns:
            Account details dictionary
        """
        # Generate unique account number
        account_number = f"HA-{uuid.uuid4().hex[:8].upper()}"

        # Convert payment_terms string to days integer for database
        payment_terms_days = self._payment_terms_to_days(payment_terms)

        # Create the database record
        account = HouseAccount(
            venue_id=venue_id,
            account_number=account_number,
            account_name=account_name,
            account_type=account_type,
            status=HouseAccountStatus.ACTIVE.value,
            contact_name=contact_name,
            contact_email=contact_email,
            contact_phone=contact_phone,
            billing_address=billing_address,
            credit_limit=Decimal(str(credit_limit)),
            current_balance=Decimal("0.0"),
            payment_terms=payment_terms_days,
            discount_percentage=Decimal(str(discount_percentage)),
            tax_id=tax_id,
            authorized_users=authorized_users or []
        )

        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)

        return {
            "success": True,
            "account_id": account.account_number,
            "id": account.id,
            "account_name": account_name,
            "credit_limit": credit_limit,
            "payment_terms": payment_terms,
            "message": f"House account {account_name} created successfully"
        }

    def charge_to_account(
        self,
        account_id: str,
        order_id: int,
        amount: float,
        description: str,
        authorized_by: str,
        staff_id: int,
        signature: Optional[str] = None,
        table_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Charge an order to a house account

        Args:
            account_id: House account number (HA-XXXXXXXX) or database ID
            order_id: Order being charged
            amount: Total amount to charge
            description: Description of the charge
            authorized_by: Name of person authorizing the charge
            staff_id: Staff processing the charge
            signature: Optional digital signature
            table_id: Table ID if applicable

        Returns:
            Transaction confirmation
        """
        account = self._get_account(account_id)
        if not account:
            return {"success": False, "error": "Account not found"}

        # Check account status
        if account.status != HouseAccountStatus.ACTIVE.value:
            return {"success": False, "error": f"Account is {account.status}"}

        # Apply account discount
        discount_pct = float(account.discount_percentage or 0)
        discount = amount * (discount_pct / 100)
        net_amount = amount - discount

        # Check credit limit
        current_balance = float(account.current_balance or 0)
        credit_limit = float(account.credit_limit or 0)
        available_credit = credit_limit - current_balance

        if current_balance + net_amount > credit_limit:
            return {
                "success": False,
                "error": "Credit limit exceeded",
                "available_credit": available_credit,
                "requested_amount": net_amount
            }

        # Check if user is authorized
        authorized_user_found = False
        for user in (account.authorized_users or []):
            if isinstance(user, dict) and user.get("name", "").lower() == authorized_by.lower():
                authorized_user_found = True
                break

        # Calculate new balance
        new_balance = current_balance + net_amount

        # Create transaction record
        transaction = HouseAccountTransaction(
            account_id=account.id,
            order_id=order_id,
            transaction_type="charge",
            amount=Decimal(str(net_amount)),
            balance_after=Decimal(str(new_balance)),
            description=description,
            reference_number=f"TXN-{uuid.uuid4().hex[:8].upper()}",
            created_by=staff_id
        )

        self.db.add(transaction)

        # Update account balance
        account.current_balance = Decimal(str(new_balance))

        # Update the order payment method
        order = self.db.query(Order).filter(Order.id == order_id).first()
        if order:
            order.payment_method = f"house_account:{account.account_number}"
            order.payment_status = "pending"  # Will be paid when account settles

        self.db.commit()
        self.db.refresh(transaction)

        # Calculate due date
        due_date = self._calculate_due_date_from_days(account.payment_terms or 30)

        return {
            "success": True,
            "transaction_id": transaction.reference_number,
            "account_id": account.account_number,
            "account_name": account.account_name,
            "gross_amount": amount,
            "discount": discount,
            "discount_percentage": discount_pct,
            "net_amount": net_amount,
            "new_balance": new_balance,
            "available_credit": credit_limit - new_balance,
            "due_date": due_date.isoformat(),
            "authorized_by": authorized_by,
            "message": f"{net_amount:.2f} charged to {account.account_name}"
        }

    def record_payment(
        self,
        account_id: str,
        amount: float,
        payment_method: str,
        reference: Optional[str] = None,
        notes: Optional[str] = None,
        staff_id: int = None
    ) -> Dict[str, Any]:
        """
        Record a payment received on a house account

        Args:
            account_id: House account number or database ID
            amount: Payment amount
            payment_method: How payment was made (check, bank_transfer, card, cash)
            reference: Check number, transfer reference, etc.
            notes: Additional notes
            staff_id: Staff recording payment

        Returns:
            Payment confirmation
        """
        account = self._get_account(account_id)
        if not account:
            return {"success": False, "error": "Account not found"}

        old_balance = float(account.current_balance or 0)
        new_balance = max(0, old_balance - amount)

        # Create payment transaction record
        transaction = HouseAccountTransaction(
            account_id=account.id,
            order_id=None,
            transaction_type="payment",
            amount=Decimal(str(-amount)),  # Negative for payments
            balance_after=Decimal(str(new_balance)),
            description=f"Payment via {payment_method}" + (f" - {notes}" if notes else ""),
            reference_number=reference or f"PMT-{uuid.uuid4().hex[:8].upper()}",
            created_by=staff_id
        )

        self.db.add(transaction)

        # Update account balance
        account.current_balance = Decimal(str(new_balance))

        self.db.commit()
        self.db.refresh(transaction)

        credit_limit = float(account.credit_limit or 0)

        return {
            "success": True,
            "payment_id": transaction.reference_number,
            "account_id": account.account_number,
            "account_name": account.account_name,
            "payment_amount": amount,
            "previous_balance": old_balance,
            "new_balance": new_balance,
            "available_credit": credit_limit - new_balance,
            "overpayment": max(0, amount - old_balance),
            "message": f"Payment of {amount:.2f} recorded for {account.account_name}"
        }

    def generate_statement(
        self,
        account_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Generate an account statement

        Args:
            account_id: House account number or database ID
            start_date: Statement start date (default: first of current month)
            end_date: Statement end date (default: today)

        Returns:
            Statement data dictionary
        """
        account = self._get_account(account_id)
        if not account:
            return {"success": False, "error": "Account not found"}

        # Default to current month
        if not start_date:
            start_date = date.today().replace(day=1)
        if not end_date:
            end_date = date.today()

        # Convert dates to datetime for comparison
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())

        # Get transactions in date range
        transactions_query = self.db.query(HouseAccountTransaction).filter(
            HouseAccountTransaction.account_id == account.id,
            HouseAccountTransaction.created_at >= start_datetime,
            HouseAccountTransaction.created_at <= end_datetime
        ).order_by(HouseAccountTransaction.created_at).all()

        transactions = []
        payments = []
        total_charges = 0.0
        total_payments = 0.0

        for txn in transactions_query:
            txn_data = {
                "transaction_id": txn.reference_number,
                "type": txn.transaction_type,
                "amount": float(txn.amount),
                "balance_after": float(txn.balance_after),
                "description": txn.description,
                "created_at": txn.created_at.isoformat() if txn.created_at else None,
                "order_id": txn.order_id
            }

            if txn.transaction_type == "payment":
                payments.append(txn_data)
                total_payments += abs(float(txn.amount))
            else:
                transactions.append(txn_data)
                total_charges += float(txn.amount)

        # Calculate opening balance (balance at start of period)
        opening_txn = self.db.query(HouseAccountTransaction).filter(
            HouseAccountTransaction.account_id == account.id,
            HouseAccountTransaction.created_at < start_datetime
        ).order_by(HouseAccountTransaction.created_at.desc()).first()

        opening_balance = float(opening_txn.balance_after) if opening_txn else 0.0

        # Aging analysis
        aging = self._calculate_aging(account.id)

        statement_id = f"STMT-{uuid.uuid4().hex[:8].upper()}"

        statement = {
            "success": True,
            "statement_id": statement_id,
            "account_id": account.account_number,
            "account_name": account.account_name,
            "billing_address": account.billing_address,
            "contact_name": account.contact_name,
            "contact_email": account.contact_email,
            "statement_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "summary": {
                "opening_balance": opening_balance,
                "total_charges": total_charges,
                "total_payments": total_payments,
                "closing_balance": float(account.current_balance or 0),
                "credit_limit": float(account.credit_limit or 0),
                "available_credit": float(account.credit_limit or 0) - float(account.current_balance or 0)
            },
            "transactions": transactions,
            "payments": payments,
            "aging": aging,
            "payment_terms": self._days_to_payment_terms(account.payment_terms or 30),
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

        return statement

    def get_aging_report(self, venue_id: int) -> Dict[str, Any]:
        """
        Generate accounts receivable aging report

        Returns aging analysis for all house accounts
        """
        aging_buckets = {
            "current": 0.0,      # 0-30 days
            "30_days": 0.0,      # 31-60 days
            "60_days": 0.0,      # 61-90 days
            "90_days": 0.0,      # 91-120 days
            "120_plus": 0.0      # 121+ days
        }

        account_details = []

        # Get all accounts for the venue with positive balance
        accounts = self.db.query(HouseAccount).filter(
            HouseAccount.venue_id == venue_id,
            HouseAccount.current_balance > 0
        ).all()

        for account in accounts:
            aging = self._calculate_aging(account.id)

            aging_buckets["current"] += aging.get("current", 0)
            aging_buckets["30_days"] += aging.get("30_days", 0)
            aging_buckets["60_days"] += aging.get("60_days", 0)
            aging_buckets["90_days"] += aging.get("90_days", 0)
            aging_buckets["120_plus"] += aging.get("120_plus", 0)

            account_details.append({
                "account_id": account.account_number,
                "account_name": account.account_name,
                "current_balance": float(account.current_balance or 0),
                "credit_limit": float(account.credit_limit or 0),
                "aging": aging,
                "oldest_unpaid": self._get_oldest_unpaid_date(account.id),
                "status": account.status
            })

        total_ar = sum(aging_buckets.values())

        return {
            "success": True,
            "venue_id": venue_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_accounts_receivable": total_ar,
                "aging_buckets": aging_buckets,
                "accounts_count": len(account_details)
            },
            "accounts": sorted(
                account_details,
                key=lambda x: x["current_balance"],
                reverse=True
            )
        }

    def add_authorized_user(
        self,
        account_id: str,
        name: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        spending_limit: Optional[float] = None
    ) -> Dict[str, Any]:
        """Add an authorized user to a house account"""
        account = self._get_account(account_id)
        if not account:
            return {"success": False, "error": "Account not found"}

        user = {
            "user_id": f"USR-{uuid.uuid4().hex[:6].upper()}",
            "name": name,
            "email": email,
            "phone": phone,
            "spending_limit": spending_limit,
            "added_at": datetime.now(timezone.utc).isoformat(),
            "is_active": True
        }

        # Get current authorized users or initialize empty list
        authorized_users = account.authorized_users or []
        if not isinstance(authorized_users, list):
            authorized_users = []

        authorized_users.append(user)
        account.authorized_users = authorized_users

        self.db.commit()

        return {
            "success": True,
            "account_id": account.account_number,
            "user_id": user["user_id"],
            "user_name": name,
            "message": f"User {name} added to {account.account_name}"
        }

    def remove_authorized_user(
        self,
        account_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Remove an authorized user from a house account"""
        account = self._get_account(account_id)
        if not account:
            return {"success": False, "error": "Account not found"}

        authorized_users = account.authorized_users or []
        if not isinstance(authorized_users, list):
            return {"success": False, "error": "No authorized users found"}

        # Find and remove user
        user_found = False
        updated_users = []
        removed_user_name = None

        for user in authorized_users:
            if isinstance(user, dict) and user.get("user_id") == user_id:
                user_found = True
                removed_user_name = user.get("name", "Unknown")
            else:
                updated_users.append(user)

        if not user_found:
            return {"success": False, "error": "User not found"}

        account.authorized_users = updated_users
        self.db.commit()

        return {
            "success": True,
            "account_id": account.account_number,
            "user_id": user_id,
            "message": f"User {removed_user_name} removed from {account.account_name}"
        }

    def suspend_account(self, account_id: str, reason: str, staff_id: int) -> Dict[str, Any]:
        """Suspend a house account"""
        account = self._get_account(account_id)
        if not account:
            return {"success": False, "error": "Account not found"}

        account.status = HouseAccountStatus.SUSPENDED.value

        # Create a transaction record for the suspension
        transaction = HouseAccountTransaction(
            account_id=account.id,
            order_id=None,
            transaction_type="adjustment",
            amount=Decimal("0"),
            balance_after=account.current_balance,
            description=f"Account suspended: {reason}",
            reference_number=f"SUS-{uuid.uuid4().hex[:8].upper()}",
            created_by=staff_id
        )

        self.db.add(transaction)
        self.db.commit()

        return {
            "success": True,
            "account_id": account.account_number,
            "account_name": account.account_name,
            "new_status": "suspended",
            "reason": reason,
            "message": f"Account {account.account_name} has been suspended"
        }

    def reactivate_account(self, account_id: str, staff_id: int) -> Dict[str, Any]:
        """Reactivate a suspended house account"""
        account = self._get_account(account_id)
        if not account:
            return {"success": False, "error": "Account not found"}

        account.status = HouseAccountStatus.ACTIVE.value

        # Create a transaction record for the reactivation
        transaction = HouseAccountTransaction(
            account_id=account.id,
            order_id=None,
            transaction_type="adjustment",
            amount=Decimal("0"),
            balance_after=account.current_balance,
            description="Account reactivated",
            reference_number=f"REA-{uuid.uuid4().hex[:8].upper()}",
            created_by=staff_id
        )

        self.db.add(transaction)
        self.db.commit()

        return {
            "success": True,
            "account_id": account.account_number,
            "account_name": account.account_name,
            "new_status": "active",
            "message": f"Account {account.account_name} has been reactivated"
        }

    def close_account(self, account_id: str, staff_id: int, reason: Optional[str] = None) -> Dict[str, Any]:
        """Close a house account permanently"""
        account = self._get_account(account_id)
        if not account:
            return {"success": False, "error": "Account not found"}

        current_balance = float(account.current_balance or 0)
        if current_balance > 0:
            return {
                "success": False,
                "error": f"Cannot close account with outstanding balance of {current_balance:.2f}",
                "current_balance": current_balance
            }

        account.status = HouseAccountStatus.CLOSED.value

        # Create a transaction record for the closure
        transaction = HouseAccountTransaction(
            account_id=account.id,
            order_id=None,
            transaction_type="adjustment",
            amount=Decimal("0"),
            balance_after=account.current_balance,
            description=f"Account closed" + (f": {reason}" if reason else ""),
            reference_number=f"CLO-{uuid.uuid4().hex[:8].upper()}",
            created_by=staff_id
        )

        self.db.add(transaction)
        self.db.commit()

        return {
            "success": True,
            "account_id": account.account_number,
            "account_name": account.account_name,
            "new_status": "closed",
            "message": f"Account {account.account_name} has been closed"
        }

    def delete_account(self, account_id: str, staff_id: int, force: bool = False) -> Dict[str, Any]:
        """
        Delete a house account permanently from the database.

        Args:
            account_id: House account number or database ID
            staff_id: Staff ID performing the deletion
            force: If True, delete even if there are transactions (use with caution)

        Returns:
            Success/failure dictionary

        Note: This permanently removes the account and all associated data.
        Consider using close_account() instead for audit trail purposes.
        """
        account = self._get_account(account_id)
        if not account:
            return {"success": False, "error": "Account not found"}

        # Check if account has outstanding balance
        current_balance = float(account.current_balance or 0)
        if current_balance > 0 and not force:
            return {
                "success": False,
                "error": f"Cannot delete account with outstanding balance of {current_balance:.2f}. Use force=True to override.",
                "current_balance": current_balance
            }

        # Count transactions
        transaction_count = self.db.query(HouseAccountTransaction).filter(
            HouseAccountTransaction.account_id == account.id
        ).count()

        if transaction_count > 0 and not force:
            return {
                "success": False,
                "error": f"Account has {transaction_count} transaction(s). Use close_account() instead or force=True to delete permanently.",
                "transaction_count": transaction_count
            }

        # Store account info for return message
        account_number = account.account_number
        account_name = account.account_name

        # Delete all transactions first (cascade)
        self.db.query(HouseAccountTransaction).filter(
            HouseAccountTransaction.account_id == account.id
        ).delete()

        # Delete the account
        self.db.delete(account)
        self.db.commit()

        logger.warning(
            f"House account {account_number} ({account_name}) permanently deleted by staff {staff_id}. "
            f"Transactions deleted: {transaction_count}"
        )

        return {
            "success": True,
            "account_id": account_number,
            "account_name": account_name,
            "transactions_deleted": transaction_count,
            "message": f"Account {account_name} has been permanently deleted"
        }

    def update_account(
        self,
        account_id: str,
        account_name: Optional[str] = None,
        contact_name: Optional[str] = None,
        contact_email: Optional[str] = None,
        contact_phone: Optional[str] = None,
        billing_address: Optional[str] = None,
        credit_limit: Optional[float] = None,
        payment_terms: Optional[str] = None,
        discount_percentage: Optional[float] = None,
        tax_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update house account details"""
        account = self._get_account(account_id)
        if not account:
            return {"success": False, "error": "Account not found"}

        # Update fields if provided
        if account_name is not None:
            account.account_name = account_name
        if contact_name is not None:
            account.contact_name = contact_name
        if contact_email is not None:
            account.contact_email = contact_email
        if contact_phone is not None:
            account.contact_phone = contact_phone
        if billing_address is not None:
            account.billing_address = billing_address
        if credit_limit is not None:
            account.credit_limit = Decimal(str(credit_limit))
        if payment_terms is not None:
            account.payment_terms = self._payment_terms_to_days(payment_terms)
        if discount_percentage is not None:
            account.discount_percentage = Decimal(str(discount_percentage))
        if tax_id is not None:
            account.tax_id = tax_id

        self.db.commit()
        self.db.refresh(account)

        return {
            "success": True,
            "account_id": account.account_number,
            "account_name": account.account_name,
            "message": f"Account {account.account_name} updated successfully"
        }

    def apply_credit(
        self,
        account_id: str,
        amount: float,
        reason: str,
        staff_id: int
    ) -> Dict[str, Any]:
        """Apply a credit/adjustment to a house account"""
        account = self._get_account(account_id)
        if not account:
            return {"success": False, "error": "Account not found"}

        old_balance = float(account.current_balance or 0)
        new_balance = max(0, old_balance - amount)

        # Create credit transaction record
        transaction = HouseAccountTransaction(
            account_id=account.id,
            order_id=None,
            transaction_type="credit",
            amount=Decimal(str(-amount)),  # Negative for credits
            balance_after=Decimal(str(new_balance)),
            description=f"Credit applied: {reason}",
            reference_number=f"CRD-{uuid.uuid4().hex[:8].upper()}",
            created_by=staff_id
        )

        self.db.add(transaction)
        account.current_balance = Decimal(str(new_balance))

        self.db.commit()
        self.db.refresh(transaction)

        return {
            "success": True,
            "transaction_id": transaction.reference_number,
            "account_id": account.account_number,
            "account_name": account.account_name,
            "credit_amount": amount,
            "previous_balance": old_balance,
            "new_balance": new_balance,
            "reason": reason,
            "message": f"Credit of {amount:.2f} applied to {account.account_name}"
        }

    def get_account(self, account_id: str) -> Dict[str, Any]:
        """Get account details"""
        account = self._get_account(account_id)
        if not account:
            return {"success": False, "error": "Account not found"}

        # Get recent transactions
        recent_transactions = self.db.query(HouseAccountTransaction).filter(
            HouseAccountTransaction.account_id == account.id,
            HouseAccountTransaction.transaction_type.in_(["charge", "credit", "adjustment"])
        ).order_by(HouseAccountTransaction.created_at.desc()).limit(10).all()

        # Get recent payments
        recent_payments = self.db.query(HouseAccountTransaction).filter(
            HouseAccountTransaction.account_id == account.id,
            HouseAccountTransaction.transaction_type == "payment"
        ).order_by(HouseAccountTransaction.created_at.desc()).limit(10).all()

        # Calculate totals
        total_charges = self.db.query(func.sum(HouseAccountTransaction.amount)).filter(
            HouseAccountTransaction.account_id == account.id,
            HouseAccountTransaction.transaction_type == "charge"
        ).scalar() or Decimal("0")

        total_payments = self.db.query(func.sum(HouseAccountTransaction.amount)).filter(
            HouseAccountTransaction.account_id == account.id,
            HouseAccountTransaction.transaction_type == "payment"
        ).scalar() or Decimal("0")

        credit_limit = float(account.credit_limit or 0)
        current_balance = float(account.current_balance or 0)

        return {
            "success": True,
            "account_id": account.account_number,
            "id": account.id,
            "venue_id": account.venue_id,
            "account_name": account.account_name,
            "account_type": account.account_type,
            "status": account.status,
            "contact_name": account.contact_name,
            "contact_email": account.contact_email,
            "contact_phone": account.contact_phone,
            "billing_address": account.billing_address,
            "credit_limit": credit_limit,
            "current_balance": current_balance,
            "available_credit": credit_limit - current_balance,
            "payment_terms": self._days_to_payment_terms(account.payment_terms or 30),
            "discount_percentage": float(account.discount_percentage or 0),
            "tax_id": account.tax_id,
            "authorized_users": account.authorized_users or [],
            "created_at": account.created_at.isoformat() if account.created_at else None,
            "updated_at": account.updated_at.isoformat() if account.updated_at else None,
            "total_charges": float(total_charges),
            "total_payments": abs(float(total_payments)),
            "recent_transactions": [
                {
                    "transaction_id": t.reference_number,
                    "type": t.transaction_type,
                    "amount": float(t.amount),
                    "balance_after": float(t.balance_after),
                    "description": t.description,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                    "order_id": t.order_id
                }
                for t in recent_transactions
            ],
            "recent_payments": [
                {
                    "payment_id": p.reference_number,
                    "amount": abs(float(p.amount)),
                    "description": p.description,
                    "created_at": p.created_at.isoformat() if p.created_at else None
                }
                for p in recent_payments
            ],
            "aging": self._calculate_aging(account.id)
        }

    def list_accounts(self, venue_id: int, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all house accounts for a venue"""
        query = self.db.query(HouseAccount).filter(HouseAccount.venue_id == venue_id)

        if status:
            query = query.filter(HouseAccount.status == status)

        accounts = query.order_by(HouseAccount.account_name).all()

        result = []
        for account in accounts:
            credit_limit = float(account.credit_limit or 0)
            current_balance = float(account.current_balance or 0)

            result.append({
                "account_id": account.account_number,
                "id": account.id,
                "account_name": account.account_name,
                "account_type": account.account_type,
                "status": account.status,
                "current_balance": current_balance,
                "credit_limit": credit_limit,
                "available_credit": credit_limit - current_balance,
                "last_activity": self._get_last_activity_date(account.id),
                "authorized_users_count": len(account.authorized_users or [])
            })

        return result

    def get_transaction_history(
        self,
        account_id: str,
        limit: int = 50,
        offset: int = 0,
        transaction_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get transaction history for an account"""
        account = self._get_account(account_id)
        if not account:
            return {"success": False, "error": "Account not found"}

        query = self.db.query(HouseAccountTransaction).filter(
            HouseAccountTransaction.account_id == account.id
        )

        if transaction_type:
            query = query.filter(HouseAccountTransaction.transaction_type == transaction_type)

        total_count = query.count()

        transactions = query.order_by(
            HouseAccountTransaction.created_at.desc()
        ).offset(offset).limit(limit).all()

        return {
            "success": True,
            "account_id": account.account_number,
            "account_name": account.account_name,
            "total_count": total_count,
            "offset": offset,
            "limit": limit,
            "transactions": [
                {
                    "transaction_id": t.reference_number,
                    "type": t.transaction_type,
                    "amount": float(t.amount),
                    "balance_after": float(t.balance_after),
                    "description": t.description,
                    "reference_number": t.reference_number,
                    "order_id": t.order_id,
                    "created_by": t.created_by,
                    "created_at": t.created_at.isoformat() if t.created_at else None
                }
                for t in transactions
            ]
        }

    def search_accounts(
        self,
        venue_id: int,
        query: str
    ) -> List[Dict[str, Any]]:
        """Search house accounts by name, contact, or account number"""
        search_pattern = f"%{query}%"

        accounts = self.db.query(HouseAccount).filter(
            HouseAccount.venue_id == venue_id,
            or_(
                HouseAccount.account_name.ilike(search_pattern),
                HouseAccount.account_number.ilike(search_pattern),
                HouseAccount.contact_name.ilike(search_pattern),
                HouseAccount.contact_email.ilike(search_pattern)
            )
        ).order_by(HouseAccount.account_name).limit(20).all()

        result = []
        for account in accounts:
            credit_limit = float(account.credit_limit or 0)
            current_balance = float(account.current_balance or 0)

            result.append({
                "account_id": account.account_number,
                "id": account.id,
                "account_name": account.account_name,
                "account_type": account.account_type,
                "status": account.status,
                "contact_name": account.contact_name,
                "current_balance": current_balance,
                "credit_limit": credit_limit,
                "available_credit": credit_limit - current_balance
            })

        return result

    # ========== HELPER METHODS ==========

    def _get_account(self, account_id: str) -> Optional[HouseAccount]:
        """Get account by account number or database ID"""
        # Try by account number first
        account = self.db.query(HouseAccount).filter(
            HouseAccount.account_number == account_id
        ).first()

        if account:
            return account

        # Try by database ID if account_id is numeric
        try:
            db_id = int(account_id)
            return self.db.query(HouseAccount).filter(HouseAccount.id == db_id).first()
        except (ValueError, TypeError):
            return None

    def _payment_terms_to_days(self, payment_terms: str) -> int:
        """Convert payment terms string to days integer"""
        days_map = {
            "net_7": 7,
            "net_15": 15,
            "net_30": 30,
            "net_45": 45,
            "on_demand": 0
        }
        return days_map.get(payment_terms, 30)

    def _days_to_payment_terms(self, days: int) -> str:
        """Convert days integer to payment terms string"""
        terms_map = {
            7: "net_7",
            15: "net_15",
            30: "net_30",
            45: "net_45",
            0: "on_demand"
        }
        return terms_map.get(days, "net_30")

    def _calculate_due_date_from_days(self, days: int) -> date:
        """Calculate due date based on payment terms days"""
        return date.today() + timedelta(days=days)

    def _calculate_aging(self, account_db_id: int) -> Dict[str, float]:
        """Calculate aging buckets for an account"""
        aging = {
            "current": 0.0,
            "30_days": 0.0,
            "60_days": 0.0,
            "90_days": 0.0,
            "120_plus": 0.0
        }

        today = date.today()

        # Get all charge transactions (unpaid amounts)
        transactions = self.db.query(HouseAccountTransaction).filter(
            HouseAccountTransaction.account_id == account_db_id,
            HouseAccountTransaction.transaction_type == "charge"
        ).all()

        for txn in transactions:
            if txn.created_at:
                txn_date = txn.created_at.date()
                days_old = (today - txn_date).days
                amount = float(txn.amount)

                if days_old <= 30:
                    aging["current"] += amount
                elif days_old <= 60:
                    aging["30_days"] += amount
                elif days_old <= 90:
                    aging["60_days"] += amount
                elif days_old <= 120:
                    aging["90_days"] += amount
                else:
                    aging["120_plus"] += amount

        return aging

    def _get_oldest_unpaid_date(self, account_db_id: int) -> Optional[str]:
        """Get the date of the oldest unpaid transaction"""
        oldest_txn = self.db.query(HouseAccountTransaction).filter(
            HouseAccountTransaction.account_id == account_db_id,
            HouseAccountTransaction.transaction_type == "charge"
        ).order_by(HouseAccountTransaction.created_at.asc()).first()

        if oldest_txn and oldest_txn.created_at:
            return oldest_txn.created_at.isoformat()

        return None

    def _get_last_activity_date(self, account_db_id: int) -> Optional[str]:
        """Get the date of the most recent transaction"""
        latest_txn = self.db.query(HouseAccountTransaction).filter(
            HouseAccountTransaction.account_id == account_db_id
        ).order_by(HouseAccountTransaction.created_at.desc()).first()

        if latest_txn and latest_txn.created_at:
            return latest_txn.created_at.isoformat()

        return None

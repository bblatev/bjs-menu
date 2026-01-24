"""Gift Card Platform Service."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any
import secrets
import string

from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from app.models.advanced_features import GiftCardProgram, GiftCard, GiftCardTransaction


class GiftCardService:
    """Service for gift card program management."""

    def __init__(self, db: Session):
        self.db = db

    def _generate_card_number(self) -> str:
        """Generate a unique 16-digit card number."""
        return ''.join(secrets.choice(string.digits) for _ in range(16))

    def _generate_pin(self) -> str:
        """Generate a 4-digit PIN."""
        return ''.join(secrets.choice(string.digits) for _ in range(4))

    def create_program(
        self,
        name: str,
        denominations: List[Decimal],
        custom_amount_allowed: bool = True,
        min_amount: Decimal = Decimal("5"),
        max_amount: Decimal = Decimal("500"),
        bonus_enabled: bool = False,
        bonus_rules: Optional[Dict[str, Any]] = None,
        expiration_months: Optional[int] = None,
        dormancy_fee_enabled: bool = False,
    ) -> GiftCardProgram:
        """Create a gift card program."""
        program = GiftCardProgram(
            name=name,
            denominations=denominations,
            custom_amount_allowed=custom_amount_allowed,
            min_amount=min_amount,
            max_amount=max_amount,
            bonus_enabled=bonus_enabled,
            bonus_rules=bonus_rules,
            expiration_months=expiration_months,
            dormancy_fee_enabled=dormancy_fee_enabled,
            is_active=True,
        )
        self.db.add(program)
        self.db.commit()
        self.db.refresh(program)
        return program

    def get_programs(
        self,
        active_only: bool = True,
    ) -> List[GiftCardProgram]:
        """Get gift card programs."""
        query = select(GiftCardProgram)
        if active_only:
            query = query.where(GiftCardProgram.is_active == True)

        result = self.db.execute(query)
        return list(result.scalars().all())

    def purchase_card(
        self,
        program_id: int,
        initial_balance: Decimal,
        purchaser_email: Optional[str] = None,
        purchaser_name: Optional[str] = None,
        recipient_email: Optional[str] = None,
        recipient_name: Optional[str] = None,
        recipient_message: Optional[str] = None,
        delivery_method: str = "email",
        purchase_order_id: Optional[int] = None,
        purchase_location_id: Optional[int] = None,
    ) -> GiftCard:
        """Purchase a new gift card."""
        program = self.db.get(GiftCardProgram, program_id)
        if not program:
            raise ValueError(f"Program {program_id} not found")

        if not program.is_active:
            raise ValueError("Gift card program is not active")

        if initial_balance < program.min_amount or initial_balance > program.max_amount:
            raise ValueError(f"Amount must be between {program.min_amount} and {program.max_amount}")

        # Calculate bonus if applicable
        bonus_balance = Decimal("0")
        if program.bonus_enabled and program.bonus_rules:
            buy_amount = program.bonus_rules.get("buy_amount", 0)
            bonus_amount = program.bonus_rules.get("bonus_amount", 0)
            if initial_balance >= Decimal(str(buy_amount)):
                bonus_balance = Decimal(str(bonus_amount))

        # Generate card number and PIN
        card_number = self._generate_card_number()
        pin = self._generate_pin()

        # Calculate expiration
        expires_at = None
        if program.expiration_months:
            expires_at = datetime.utcnow() + timedelta(days=program.expiration_months * 30)

        card = GiftCard(
            program_id=program_id,
            card_number=card_number,
            pin=pin,
            initial_balance=initial_balance,
            current_balance=initial_balance,
            bonus_balance=bonus_balance,
            purchaser_email=purchaser_email,
            purchaser_name=purchaser_name,
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            recipient_message=recipient_message,
            delivery_method=delivery_method,
            expires_at=expires_at,
            purchase_order_id=purchase_order_id,
            purchase_location_id=purchase_location_id,
            is_active=True,
        )
        self.db.add(card)
        self.db.commit()
        self.db.refresh(card)

        # Record activation transaction
        self._record_transaction(
            card.id,
            "activation",
            initial_balance + bonus_balance,
            initial_balance + bonus_balance,
            location_id=purchase_location_id,
        )

        return card

    def get_card_by_number(
        self,
        card_number: str,
    ) -> Optional[GiftCard]:
        """Get a gift card by number."""
        query = select(GiftCard).where(GiftCard.card_number == card_number)
        result = self.db.execute(query)
        return result.scalar_one_or_none()

    def check_balance(
        self,
        card_number: str,
        pin: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Check gift card balance."""
        card = self.get_card_by_number(card_number)
        if not card:
            raise ValueError("Card not found")

        if pin and card.pin != pin:
            raise ValueError("Invalid PIN")

        return {
            "card_number": card.card_number,
            "current_balance": card.current_balance,
            "bonus_balance": card.bonus_balance,
            "total_available": card.current_balance + card.bonus_balance,
            "expires_at": card.expires_at,
            "is_active": card.is_active,
        }

    def redeem(
        self,
        card_number: str,
        amount: Decimal,
        pin: Optional[str] = None,
        order_id: Optional[int] = None,
        location_id: Optional[int] = None,
        performed_by_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Redeem an amount from a gift card."""
        card = self.get_card_by_number(card_number)
        if not card:
            raise ValueError("Card not found")

        if pin and card.pin != pin:
            raise ValueError("Invalid PIN")

        if not card.is_active:
            raise ValueError("Card is not active")

        if card.expires_at and card.expires_at < datetime.utcnow():
            raise ValueError("Card has expired")

        total_available = card.current_balance + card.bonus_balance
        if amount > total_available:
            raise ValueError(f"Insufficient balance. Available: {total_available}")

        # Deduct from bonus first, then main balance
        bonus_used = min(amount, card.bonus_balance)
        main_used = amount - bonus_used

        card.bonus_balance -= bonus_used
        card.current_balance -= main_used

        self.db.commit()
        self.db.refresh(card)

        # Record transaction
        self._record_transaction(
            card.id,
            "redemption",
            -amount,
            card.current_balance + card.bonus_balance,
            order_id=order_id,
            location_id=location_id,
            performed_by_id=performed_by_id,
        )

        return {
            "card_number": card.card_number,
            "amount_redeemed": amount,
            "new_balance": card.current_balance + card.bonus_balance,
        }

    def reload(
        self,
        card_number: str,
        amount: Decimal,
        location_id: Optional[int] = None,
        performed_by_id: Optional[int] = None,
    ) -> GiftCard:
        """Reload a gift card."""
        card = self.get_card_by_number(card_number)
        if not card:
            raise ValueError("Card not found")

        if not card.is_active:
            raise ValueError("Card is not active")

        program = self.db.get(GiftCardProgram, card.program_id)
        if program and amount + card.current_balance > program.max_amount:
            raise ValueError(f"Cannot exceed maximum balance of {program.max_amount}")

        card.current_balance += amount
        self.db.commit()
        self.db.refresh(card)

        self._record_transaction(
            card.id,
            "reload",
            amount,
            card.current_balance + card.bonus_balance,
            location_id=location_id,
            performed_by_id=performed_by_id,
        )

        return card

    def void_card(
        self,
        card_number: str,
        reason: str,
        performed_by_id: Optional[int] = None,
    ) -> GiftCard:
        """Void a gift card."""
        card = self.get_card_by_number(card_number)
        if not card:
            raise ValueError("Card not found")

        remaining = card.current_balance + card.bonus_balance
        card.current_balance = Decimal("0")
        card.bonus_balance = Decimal("0")
        card.is_active = False

        self.db.commit()
        self.db.refresh(card)

        self._record_transaction(
            card.id,
            "void",
            -remaining,
            Decimal("0"),
            notes=reason,
            performed_by_id=performed_by_id,
        )

        return card

    def _record_transaction(
        self,
        gift_card_id: int,
        transaction_type: str,
        amount: Decimal,
        balance_after: Decimal,
        order_id: Optional[int] = None,
        location_id: Optional[int] = None,
        performed_by_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> GiftCardTransaction:
        """Record a gift card transaction."""
        transaction = GiftCardTransaction(
            gift_card_id=gift_card_id,
            transaction_type=transaction_type,
            amount=amount,
            balance_after=balance_after,
            order_id=order_id,
            location_id=location_id,
            performed_by_id=performed_by_id,
            notes=notes,
        )
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        return transaction

    def get_transactions(
        self,
        card_number: str,
        limit: int = 50,
    ) -> List[GiftCardTransaction]:
        """Get transaction history for a card."""
        card = self.get_card_by_number(card_number)
        if not card:
            raise ValueError("Card not found")

        query = select(GiftCardTransaction).where(
            GiftCardTransaction.gift_card_id == card.id
        ).order_by(GiftCardTransaction.created_at.desc()).limit(limit)

        result = self.db.execute(query)
        return list(result.scalars().all())

    def get_stats(
        self,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Get gift card program statistics."""
        start_date = datetime.utcnow() - timedelta(days=days)

        # Cards sold
        sold_query = select(
            func.count(GiftCard.id).label("count"),
            func.sum(GiftCard.initial_balance).label("total"),
        ).where(GiftCard.created_at >= start_date)

        sold_result = self.db.execute(sold_query)
        sold = sold_result.first()

        # Redemptions
        redeemed_query = select(
            func.count(GiftCardTransaction.id).label("count"),
            func.sum(func.abs(GiftCardTransaction.amount)).label("total"),
        ).where(
            and_(
                GiftCardTransaction.transaction_type == "redemption",
                GiftCardTransaction.created_at >= start_date,
            )
        )

        redeemed_result = self.db.execute(redeemed_query)
        redeemed = redeemed_result.first()

        # Outstanding balance
        outstanding_query = select(
            func.sum(GiftCard.current_balance + GiftCard.bonus_balance).label("total"),
        ).where(GiftCard.is_active == True)

        outstanding_result = self.db.execute(outstanding_query)
        outstanding = outstanding_result.scalar() or Decimal("0")

        return {
            "period_days": days,
            "cards_sold": sold.count or 0,
            "sold_value": float(sold.total or 0),
            "redemptions": redeemed.count or 0,
            "redeemed_value": float(redeemed.total or 0),
            "outstanding_balance": float(outstanding),
        }

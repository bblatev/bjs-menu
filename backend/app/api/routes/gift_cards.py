"""Gift cards API routes with real database queries."""

from typing import List, Optional
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import secrets
import string

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from app.db.session import DbSession
from app.models.advanced_features import (
    GiftCard as GiftCardModel,
    GiftCardTransaction as GiftCardTransactionModel,
    GiftCardProgram
)

router = APIRouter()


# ============================================================================
# Pydantic Schemas
# ============================================================================

class GiftCardCreate(BaseModel):
    program_id: int = 1
    card_number: Optional[str] = None
    pin: Optional[str] = None
    initial_balance: float
    purchaser_email: Optional[str] = None
    purchaser_name: Optional[str] = None
    recipient_email: Optional[str] = None
    recipient_name: Optional[str] = None
    recipient_message: Optional[str] = None
    delivery_method: str = "email"
    expiration_months: Optional[int] = None
    purchase_order_id: Optional[int] = None
    purchase_location_id: Optional[int] = None


class GiftCard(BaseModel):
    id: str
    code: str
    initial_balance: float
    current_balance: float
    status: str  # active, used, expired
    issued_date: str
    expiry_date: str
    last_used: Optional[str] = None


class GiftCardDetailed(BaseModel):
    id: int
    program_id: int
    card_number: str
    pin: Optional[str] = None
    initial_balance: float
    current_balance: float
    bonus_balance: float
    purchaser_email: Optional[str] = None
    purchaser_name: Optional[str] = None
    recipient_email: Optional[str] = None
    recipient_name: Optional[str] = None
    recipient_message: Optional[str] = None
    delivery_method: str
    delivered_at: Optional[str] = None
    is_active: bool
    expires_at: Optional[str] = None
    created_at: str
    updated_at: str


class GiftCardTransaction(BaseModel):
    id: str
    card_id: str
    type: str  # purchase, redemption, refund
    amount: float
    balance_after: float
    order_id: Optional[str] = None
    timestamp: str
    staff: str


class GiftCardStats(BaseModel):
    total_issued: int
    total_value_issued: float
    total_redeemed: float
    outstanding_liability: float
    expired_unredeemed: float


class RedeemRequest(BaseModel):
    amount: float
    reference: str = ""


class ReloadRequest(BaseModel):
    amount: float


# ============================================================================
# Helper Functions
# ============================================================================

def generate_card_number() -> str:
    """Generate a unique gift card number."""
    year = datetime.now().year
    random_part = ''.join(secrets.choice(string.digits) for _ in range(6))
    return f"GC-{year}-{random_part}"


def determine_status(card: GiftCardModel) -> str:
    """Determine the display status of a gift card."""
    if not card.is_active:
        return "cancelled"

    if card.expires_at and card.expires_at < datetime.now(timezone.utc):
        return "expired"

    if card.current_balance <= 0:
        return "used"

    return "active"


def get_last_used_date(db: Session, card_id: int) -> Optional[str]:
    """Get the last redemption date for a gift card."""
    last_transaction = db.query(GiftCardTransactionModel).filter(
        GiftCardTransactionModel.gift_card_id == card_id,
        GiftCardTransactionModel.transaction_type == "redemption"
    ).order_by(GiftCardTransactionModel.created_at.desc()).first()

    if last_transaction:
        return last_transaction.created_at.isoformat()
    return None


def convert_to_simple_schema(card: GiftCardModel, db: Session) -> GiftCard:
    """Convert DB model to simple API schema."""
    return GiftCard(
        id=str(card.id),
        code=card.card_number,
        initial_balance=float(card.initial_balance),
        current_balance=float(card.current_balance),
        status=determine_status(card),
        issued_date=card.created_at.isoformat(),
        expiry_date=card.expires_at.isoformat() if card.expires_at else "",
        last_used=get_last_used_date(db, card.id)
    )


# ============================================================================
# Pydantic Schemas for Programs
# ============================================================================

class GiftCardProgramCreate(BaseModel):
    name: str
    type: str = "standard"
    denominations: Optional[list] = None
    custom_amount_allowed: bool = True
    min_amount: float = 5.00
    max_amount: float = 500.00
    bonus_enabled: bool = False
    bonus_rules: Optional[dict] = None
    expiration_months: Optional[int] = None


# ============================================================================
# Routes (Static routes BEFORE dynamic routes!)
# ============================================================================

@router.post("/programs")
async def create_gift_card_program(data: GiftCardProgramCreate, db: DbSession):
    """Create a gift card program."""
    program = GiftCardProgram(
        name=data.name,
        denominations=data.denominations or [25, 50, 75, 100],
        custom_amount_allowed=data.custom_amount_allowed,
        min_amount=Decimal(str(data.min_amount)),
        max_amount=Decimal(str(data.max_amount)),
        bonus_enabled=data.bonus_enabled,
        bonus_rules=data.bonus_rules,
        expiration_months=data.expiration_months,
        is_active=True,
    )
    db.add(program)
    db.commit()
    db.refresh(program)
    return {
        "id": program.id,
        "name": program.name,
        "denominations": program.denominations,
        "custom_amount_allowed": program.custom_amount_allowed,
        "min_amount": float(program.min_amount),
        "max_amount": float(program.max_amount),
        "bonus_enabled": program.bonus_enabled,
        "is_active": program.is_active,
    }


@router.get("/programs")
async def get_gift_card_programs(db: DbSession):
    """Get all gift card programs."""
    programs = db.query(GiftCardProgram).order_by(GiftCardProgram.id).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "denominations": p.denominations,
            "custom_amount_allowed": p.custom_amount_allowed,
            "min_amount": float(p.min_amount) if p.min_amount else 0,
            "max_amount": float(p.max_amount) if p.max_amount else 0,
            "bonus_enabled": p.bonus_enabled,
            "is_active": p.is_active,
        }
        for p in programs
    ]


@router.get("/stats/summary")
async def get_gift_card_stats(db: DbSession):
    """Get gift card statistics from database."""

    # Total issued cards
    total_issued = db.query(func.count(GiftCardModel.id)).scalar() or 0

    # Total value issued
    total_value_issued = db.query(
        func.coalesce(func.sum(GiftCardModel.initial_balance), 0)
    ).scalar() or 0

    # Total redeemed (sum of all redemption transactions)
    total_redeemed = db.query(
        func.coalesce(func.sum(GiftCardTransactionModel.amount), 0)
    ).filter(
        GiftCardTransactionModel.transaction_type == "redemption"
    ).scalar() or 0

    # Make positive (redemptions are stored as negative amounts)
    total_redeemed = abs(float(total_redeemed))

    # Outstanding liability (sum of current balances for active, non-expired cards)
    outstanding_liability = db.query(
        func.coalesce(func.sum(GiftCardModel.current_balance), 0)
    ).filter(
        GiftCardModel.is_active == True,
        func.coalesce(GiftCardModel.expires_at > datetime.now(timezone.utc), True)
    ).scalar() or 0

    # Expired unredeemed (current balance of expired cards)
    expired_unredeemed = db.query(
        func.coalesce(func.sum(GiftCardModel.current_balance), 0)
    ).filter(
        GiftCardModel.expires_at <= datetime.now(timezone.utc),
        GiftCardModel.current_balance > 0
    ).scalar() or 0

    return GiftCardStats(
        total_issued=total_issued,
        total_value_issued=float(total_value_issued),
        total_redeemed=total_redeemed,
        outstanding_liability=float(outstanding_liability),
        expired_unredeemed=float(expired_unredeemed)
    )


@router.get("/lookup/{code}")
async def lookup_gift_card(code: str, db: DbSession):
    """Lookup a gift card by card number."""
    card = db.query(GiftCardModel).filter(
        GiftCardModel.card_number == code
    ).first()

    if not card:
        raise HTTPException(status_code=404, detail=f"Gift card {code} not found")

    return convert_to_simple_schema(card, db)


@router.get("/")
async def get_gift_cards(
    db: DbSession,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
):
    """Get all gift cards with optional filtering."""
    query = db.query(GiftCardModel)

    # Apply status filter if provided
    if status:
        if status == "active":
            query = query.filter(
                GiftCardModel.is_active == True,
                GiftCardModel.current_balance > 0,
                func.coalesce(GiftCardModel.expires_at > datetime.now(timezone.utc), True)
            )
        elif status == "used":
            query = query.filter(GiftCardModel.current_balance <= 0)
        elif status == "expired":
            query = query.filter(GiftCardModel.expires_at <= datetime.now(timezone.utc))
        elif status == "cancelled":
            query = query.filter(GiftCardModel.is_active == False)

    cards = query.order_by(GiftCardModel.created_at.desc()).offset(skip).limit(limit).all()

    return [convert_to_simple_schema(card, db) for card in cards]


@router.post("/")
async def create_gift_card(card_data: GiftCardCreate, db: DbSession):
    """Create a new gift card."""

    # Generate card number if not provided
    card_number = card_data.card_number
    if not card_number:
        # Generate unique card number
        while True:
            card_number = generate_card_number()
            existing = db.query(GiftCardModel).filter(
                GiftCardModel.card_number == card_number
            ).first()
            if not existing:
                break
    else:
        # Check if card number already exists
        existing = db.query(GiftCardModel).filter(
            GiftCardModel.card_number == card_number
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Card number {card_number} already exists")

    # Validate program exists
    program = db.query(GiftCardProgram).filter(GiftCardProgram.id == card_data.program_id).first()
    if not program:
        raise HTTPException(status_code=404, detail=f"Gift card program {card_data.program_id} not found")

    # Calculate expiration date if expiration_months provided
    expires_at = None
    if card_data.expiration_months:
        expires_at = datetime.now(timezone.utc) + timedelta(days=card_data.expiration_months * 30)

    # Create gift card
    new_card = GiftCardModel(
        program_id=card_data.program_id,
        card_number=card_number,
        pin=card_data.pin,
        initial_balance=Decimal(str(card_data.initial_balance)),
        current_balance=Decimal(str(card_data.initial_balance)),
        bonus_balance=Decimal('0'),
        purchaser_email=card_data.purchaser_email,
        purchaser_name=card_data.purchaser_name,
        recipient_email=card_data.recipient_email,
        recipient_name=card_data.recipient_name,
        recipient_message=card_data.recipient_message,
        delivery_method=card_data.delivery_method,
        is_active=True,
        expires_at=expires_at,
        purchase_order_id=card_data.purchase_order_id,
        purchase_location_id=card_data.purchase_location_id
    )

    db.add(new_card)
    db.commit()
    db.refresh(new_card)

    # Create activation transaction
    activation_txn = GiftCardTransactionModel(
        gift_card_id=new_card.id,
        transaction_type="activation",
        amount=new_card.initial_balance,
        balance_after=new_card.initial_balance,
        location_id=card_data.purchase_location_id,
        notes="Initial card activation"
    )
    db.add(activation_txn)
    db.commit()

    return {
        "success": True,
        "id": str(new_card.id),
        "code": new_card.card_number,
        "initial_balance": float(new_card.initial_balance),
        "current_balance": float(new_card.current_balance),
        "expires_at": new_card.expires_at.isoformat() if new_card.expires_at else None
    }


@router.get("/{card_id}")
async def get_gift_card(card_id: int, db: DbSession):
    """Get a specific gift card by ID."""
    card = db.query(GiftCardModel).filter(GiftCardModel.id == card_id).first()

    if not card:
        raise HTTPException(status_code=404, detail=f"Gift card {card_id} not found")

    # Return detailed schema
    return GiftCardDetailed(
        id=card.id,
        program_id=card.program_id,
        card_number=card.card_number,
        pin=card.pin,
        initial_balance=float(card.initial_balance),
        current_balance=float(card.current_balance),
        bonus_balance=float(card.bonus_balance),
        purchaser_email=card.purchaser_email,
        purchaser_name=card.purchaser_name,
        recipient_email=card.recipient_email,
        recipient_name=card.recipient_name,
        recipient_message=card.recipient_message,
        delivery_method=card.delivery_method,
        delivered_at=card.delivered_at.isoformat() if card.delivered_at else None,
        is_active=card.is_active,
        expires_at=card.expires_at.isoformat() if card.expires_at else None,
        created_at=card.created_at.isoformat(),
        updated_at=card.updated_at.isoformat()
    )


@router.get("/{card_id}/transactions")
async def get_card_transactions(card_id: int, db: DbSession):
    """Get transaction history for a gift card."""

    # Verify card exists
    card = db.query(GiftCardModel).filter(GiftCardModel.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail=f"Gift card {card_id} not found")

    # Get all transactions
    transactions = db.query(GiftCardTransactionModel).filter(
        GiftCardTransactionModel.gift_card_id == card_id
    ).order_by(GiftCardTransactionModel.created_at.desc()).all()

    # Convert to response schema
    result = []
    for txn in transactions:
        # Map transaction_type to simple type names
        txn_type = txn.transaction_type
        if txn_type == "activation":
            txn_type = "purchase"
        elif txn_type == "reload":
            txn_type = "reload"
        elif txn_type == "redemption":
            txn_type = "redemption"
        elif txn_type == "void":
            txn_type = "refund"

        result.append(GiftCardTransaction(
            id=str(txn.id),
            card_id=str(txn.gift_card_id),
            type=txn_type,
            amount=float(txn.amount),
            balance_after=float(txn.balance_after),
            order_id=str(txn.order_id) if txn.order_id else None,
            timestamp=txn.created_at.isoformat(),
            staff=f"Staff #{txn.performed_by_id}" if txn.performed_by_id else "System"
        ))

    return result


@router.post("/{card_id}/redeem")
async def redeem_gift_card(card_id: int, redeem_data: RedeemRequest, db: DbSession):
    """Redeem (spend) from a gift card."""
    card = db.query(GiftCardModel).filter(GiftCardModel.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail=f"Gift card {card_id} not found")
    if not card.is_active:
        raise HTTPException(status_code=400, detail="Gift card is not active")
    if card.current_balance < Decimal(str(redeem_data.amount)):
        raise HTTPException(status_code=400, detail="Insufficient balance")

    previous_balance = float(card.current_balance)
    card.current_balance -= Decimal(str(redeem_data.amount))

    txn = GiftCardTransactionModel(
        gift_card_id=card.id,
        transaction_type="redemption",
        amount=-Decimal(str(redeem_data.amount)),
        balance_after=card.current_balance,
        notes=redeem_data.reference or "Redemption",
    )
    db.add(txn)
    db.commit()

    return {
        "success": True,
        "card_number": card.card_number,
        "previous_balance": previous_balance,
        "redeemed_amount": redeem_data.amount,
        "new_balance": float(card.current_balance),
    }


@router.post("/{card_id}/cancel")
async def cancel_gift_card(card_id: int, db: DbSession):
    """Cancel a gift card (deactivate)."""

    card = db.query(GiftCardModel).filter(GiftCardModel.id == card_id).first()

    if not card:
        raise HTTPException(status_code=404, detail=f"Gift card {card_id} not found")

    if not card.is_active:
        raise HTTPException(status_code=400, detail="Gift card is already cancelled")

    # Deactivate the card
    card.is_active = False

    # Create void transaction for remaining balance
    voided_balance = 0
    if card.current_balance > 0:
        voided_balance = float(card.current_balance)
        void_txn = GiftCardTransactionModel(
            gift_card_id=card.id,
            transaction_type="void",
            amount=-card.current_balance,
            balance_after=Decimal('0'),
            notes="Card cancelled - balance voided"
        )
        db.add(void_txn)
        card.current_balance = Decimal('0')

    db.commit()

    return {
        "success": True,
        "message": f"Gift card {card.card_number} cancelled",
        "voided_balance": voided_balance
    }


@router.post("/{card_id}/reload")
async def reload_gift_card(card_id: int, reload_data: ReloadRequest, db: DbSession):
    """Reload a gift card with additional funds."""

    card = db.query(GiftCardModel).filter(GiftCardModel.id == card_id).first()

    if not card:
        raise HTTPException(status_code=404, detail=f"Gift card {card_id} not found")

    if not card.is_active:
        raise HTTPException(status_code=400, detail="Cannot reload a cancelled gift card")

    if reload_data.amount <= 0:
        raise HTTPException(status_code=400, detail="Reload amount must be positive")

    # Add to current balance
    old_balance = card.current_balance
    card.current_balance += Decimal(str(reload_data.amount))

    # Create reload transaction
    reload_txn = GiftCardTransactionModel(
        gift_card_id=card.id,
        transaction_type="reload",
        amount=Decimal(str(reload_data.amount)),
        balance_after=card.current_balance,
        notes=f"Card reloaded with ${reload_data.amount}"
    )
    db.add(reload_txn)
    db.commit()

    return {
        "success": True,
        "card_number": card.card_number,
        "previous_balance": float(old_balance),
        "reload_amount": reload_data.amount,
        "new_balance": float(card.current_balance)
    }

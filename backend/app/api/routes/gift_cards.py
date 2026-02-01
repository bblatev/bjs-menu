"""Gift cards API routes (direct access)."""

from typing import List, Optional
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class GiftCard(BaseModel):
    id: str
    code: str
    initial_balance: float
    current_balance: float
    status: str  # active, used, expired
    issued_date: str
    expiry_date: str
    last_used: Optional[str] = None


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


MOCK_CARDS = [
    GiftCard(id="1", code="GC-2026-001", initial_balance=100.00, current_balance=45.00, status="active", issued_date="2026-01-15", expiry_date="2027-01-15", last_used="2026-01-28"),
    GiftCard(id="2", code="GC-2026-002", initial_balance=50.00, current_balance=50.00, status="active", issued_date="2026-01-20", expiry_date="2027-01-20"),
    GiftCard(id="3", code="GC-2026-003", initial_balance=200.00, current_balance=0.00, status="used", issued_date="2025-12-25", expiry_date="2026-12-25", last_used="2026-01-30"),
]


@router.get("/")
async def get_gift_cards():
    """Get all gift cards."""
    return MOCK_CARDS


@router.post("/")
async def create_gift_card(card: GiftCard):
    """Create a new gift card."""
    return {"success": True, "id": "new-id", "code": "GC-2026-NEW"}


@router.get("/stats/summary")
async def get_gift_card_stats():
    """Get gift card statistics."""
    return GiftCardStats(
        total_issued=156,
        total_value_issued=12500.00,
        total_redeemed=8750.00,
        outstanding_liability=3250.00,
        expired_unredeemed=500.00
    )


@router.get("/lookup/{code}")
async def lookup_gift_card(code: str):
    """Lookup a gift card by code."""
    for card in MOCK_CARDS:
        if card.code == code:
            return card
    return GiftCard(id="0", code=code, initial_balance=0, current_balance=0, status="not_found", issued_date="", expiry_date="")


@router.get("/{card_id}")
async def get_gift_card(card_id: str):
    """Get a specific gift card."""
    for card in MOCK_CARDS:
        if card.id == card_id:
            return card
    return MOCK_CARDS[0]


@router.get("/{card_id}/transactions")
async def get_card_transactions(card_id: str):
    """Get transactions for a gift card."""
    return [
        GiftCardTransaction(id="1", card_id=card_id, type="purchase", amount=100.00, balance_after=100.00, timestamp="2026-01-15T12:00:00Z", staff="Manager"),
        GiftCardTransaction(id="2", card_id=card_id, type="redemption", amount=-35.00, balance_after=65.00, order_id="ORD-1234", timestamp="2026-01-20T18:30:00Z", staff="Server"),
        GiftCardTransaction(id="3", card_id=card_id, type="redemption", amount=-20.00, balance_after=45.00, order_id="ORD-1456", timestamp="2026-01-28T20:15:00Z", staff="Server"),
    ]


@router.post("/{card_id}/cancel")
async def cancel_gift_card(card_id: str):
    """Cancel a gift card."""
    return {"success": True, "message": f"Gift card {card_id} cancelled"}


@router.post("/{card_id}/reload")
async def reload_gift_card(card_id: str, amount: float):
    """Reload a gift card."""
    return {"success": True, "new_balance": 145.00}

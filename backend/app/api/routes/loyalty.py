"""Loyalty and gift cards API routes."""

from typing import List, Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter()


class LoyaltyMember(BaseModel):
    id: str
    name: str
    email: str
    phone: Optional[str] = None
    points: int
    tier: str  # bronze, silver, gold, platinum
    total_spent: float
    visits: int
    joined_date: str
    last_visit: str


class GiftCard(BaseModel):
    id: str
    code: str
    initial_balance: float
    current_balance: float
    status: str  # active, used, expired
    issued_date: str
    expiry_date: str
    last_used: Optional[str] = None


class GiftCardStats(BaseModel):
    total_issued: int
    total_value_issued: float
    total_redeemed: float
    outstanding_liability: float
    expired_unredeemed: float


@router.get("/members")
async def get_loyalty_members():
    """Get loyalty program members."""
    return [
        LoyaltyMember(id="1", name="John Smith", email="john@example.com", phone="+359888123456", points=2450, tier="gold", total_spent=4850.00, visits=45, joined_date="2025-03-15", last_visit="2026-01-30"),
        LoyaltyMember(id="2", name="Sarah Johnson", email="sarah@example.com", points=890, tier="silver", total_spent=1780.00, visits=18, joined_date="2025-08-20", last_visit="2026-01-28"),
        LoyaltyMember(id="3", name="Mike Brown", email="mike@example.com", points=5200, tier="platinum", total_spent=10400.00, visits=85, joined_date="2024-12-01", last_visit="2026-02-01"),
    ]


@router.get("/gift-cards/")
async def get_gift_cards():
    """Get all gift cards."""
    return [
        GiftCard(id="1", code="GC-2026-001", initial_balance=100.00, current_balance=45.00, status="active", issued_date="2026-01-15", expiry_date="2027-01-15", last_used="2026-01-28"),
        GiftCard(id="2", code="GC-2026-002", initial_balance=50.00, current_balance=50.00, status="active", issued_date="2026-01-20", expiry_date="2027-01-20"),
        GiftCard(id="3", code="GC-2026-003", initial_balance=200.00, current_balance=0.00, status="used", issued_date="2025-12-25", expiry_date="2026-12-25", last_used="2026-01-30"),
    ]


@router.get("/gift-cards/stats/summary")
async def get_gift_card_stats():
    """Get gift card statistics."""
    return GiftCardStats(
        total_issued=156,
        total_value_issued=12500.00,
        total_redeemed=8750.00,
        outstanding_liability=3250.00,
        expired_unredeemed=500.00
    )


@router.get("/gift-cards/lookup/{code}")
async def lookup_gift_card(code: str):
    """Lookup a gift card by code."""
    return GiftCard(id="1", code=code, initial_balance=100.00, current_balance=45.00, status="active", issued_date="2026-01-15", expiry_date="2027-01-15")


@router.get("/gift-cards/{card_id}")
async def get_gift_card(card_id: str):
    """Get a specific gift card."""
    return GiftCard(id=card_id, code="GC-2026-001", initial_balance=100.00, current_balance=45.00, status="active", issued_date="2026-01-15", expiry_date="2027-01-15")


@router.post("/gift-cards/")
async def create_gift_card(card: GiftCard):
    """Create a new gift card."""
    return {"success": True, "id": "new-id", "code": "GC-2026-NEW"}

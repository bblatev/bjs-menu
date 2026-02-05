"""Loyalty program API routes (gift cards at /gift-cards)."""

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


@router.get("/members")
async def get_loyalty_members():
    """Get loyalty program members."""
    return [
        LoyaltyMember(id="1", name="John Smith", email="john@example.com", phone="+359888123456", points=2450, tier="gold", total_spent=4850.00, visits=45, joined_date="2025-03-15", last_visit="2026-01-30"),
        LoyaltyMember(id="2", name="Sarah Johnson", email="sarah@example.com", points=890, tier="silver", total_spent=1780.00, visits=18, joined_date="2025-08-20", last_visit="2026-01-28"),
        LoyaltyMember(id="3", name="Mike Brown", email="mike@example.com", points=5200, tier="platinum", total_spent=10400.00, visits=85, joined_date="2024-12-01", last_visit="2026-02-01"),
    ]

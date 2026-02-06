"""Referral program API routes."""

from typing import List, Optional
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class Referral(BaseModel):
    id: str
    referrer_id: str
    referrer_name: str
    referee_name: str
    referee_email: str
    status: str  # pending, completed, expired
    reward_amount: float
    created_at: str
    completed_at: Optional[str] = None


class Referrer(BaseModel):
    id: str
    name: str
    email: str
    total_referrals: int
    successful_referrals: int
    total_earned: float
    pending_rewards: float


class ReferralCampaign(BaseModel):
    id: str
    name: str
    referrer_reward: float
    referee_reward: float
    min_spend: float
    expires_at: Optional[str] = None
    active: bool = True


class ReferralSettings(BaseModel):
    default_referrer_reward: float
    default_referee_reward: float
    min_spend_required: float
    reward_expiry_days: int
    max_referrals_per_customer: int


@router.get("/programs")
async def get_referral_programs():
    """Get referral programs."""
    return {"programs": [], "total": 0}


@router.get("/")
async def get_referrals():
    """Get all referrals."""
    return [
        Referral(id="1", referrer_id="1", referrer_name="John Smith", referee_name="Mike Brown", referee_email="mike@email.com", status="completed", reward_amount=20.00, created_at="2026-01-15", completed_at="2026-01-20"),
        Referral(id="2", referrer_id="1", referrer_name="John Smith", referee_name="Sarah Lee", referee_email="sarah@email.com", status="pending", reward_amount=20.00, created_at="2026-01-28"),
        Referral(id="3", referrer_id="2", referrer_name="Jane Doe", referee_name="Tom Wilson", referee_email="tom@email.com", status="completed", reward_amount=25.00, created_at="2026-01-10", completed_at="2026-01-18"),
    ]


@router.get("/referrers")
async def get_referrers():
    """Get all referrers."""
    return [
        Referrer(id="1", name="John Smith", email="john@email.com", total_referrals=5, successful_referrals=3, total_earned=60.00, pending_rewards=20.00),
        Referrer(id="2", name="Jane Doe", email="jane@email.com", total_referrals=8, successful_referrals=6, total_earned=150.00, pending_rewards=0.00),
        Referrer(id="3", name="Mike Johnson", email="mike.j@email.com", total_referrals=2, successful_referrals=1, total_earned=20.00, pending_rewards=20.00),
    ]


@router.get("/campaigns")
async def get_referral_campaigns():
    """Get referral campaigns."""
    return [
        ReferralCampaign(id="1", name="Standard Referral", referrer_reward=20.00, referee_reward=15.00, min_spend=50.00, active=True),
        ReferralCampaign(id="2", name="Summer Special", referrer_reward=30.00, referee_reward=25.00, min_spend=75.00, expires_at="2026-08-31", active=True),
    ]


@router.get("/settings")
async def get_referral_settings():
    """Get referral program settings."""
    return ReferralSettings(
        default_referrer_reward=20.00,
        default_referee_reward=15.00,
        min_spend_required=50.00,
        reward_expiry_days=90,
        max_referrals_per_customer=10
    )


@router.post("/bulk-send")
async def send_bulk_invites(emails: List[str]):
    """Send bulk referral invites."""
    return {"success": True, "sent_count": len(emails)}

"""Loyalty program API routes (gift cards at /gift-cards)."""

from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy import func

from app.db.session import DbSession
from app.models.marketing import LoyaltyProgram, CustomerLoyalty
from app.models.customer import Customer

router = APIRouter()


@router.get("/program")
def get_loyalty_program(db: DbSession):
    """Get loyalty program details."""
    program = db.query(LoyaltyProgram).filter(
        LoyaltyProgram.is_active == True  # noqa: E712
    ).first()

    if not program:
        return {
            "name": "Loyalty Program",
            "points_per_dollar": 1,
            "tiers": [],
            "active_members": 0,
        }

    active_members = db.query(func.count(CustomerLoyalty.id)).filter(
        CustomerLoyalty.program_id == program.id
    ).scalar() or 0

    return {
        "name": program.name,
        "points_per_dollar": program.points_per_dollar,
        "tiers": program.tiers or [],
        "active_members": active_members,
    }


class CreateLoyaltyProgramRequest(BaseModel):
    name: str
    points_per_dollar: float = 1.0
    redemption_rate: float = 0.01
    signup_bonus: int = 0


@router.post("/program")
def create_loyalty_program(request: CreateLoyaltyProgramRequest, db: DbSession):
    """Create or update a loyalty program."""
    # Check if one already exists
    existing = db.query(LoyaltyProgram).first()
    if existing:
        existing.name = request.name
        existing.points_per_dollar = request.points_per_dollar
        existing.points_to_dollar = request.redemption_rate
        db.commit()
        db.refresh(existing)
        return {
            "id": existing.id,
            "name": existing.name,
            "points_per_dollar": existing.points_per_dollar,
            "redemption_rate": existing.points_to_dollar,
        }

    program = LoyaltyProgram(
        name=request.name,
        points_per_dollar=request.points_per_dollar,
        points_to_dollar=request.redemption_rate,
        is_active=True,
    )
    db.add(program)
    db.commit()
    db.refresh(program)
    return {
        "id": program.id,
        "name": program.name,
        "points_per_dollar": program.points_per_dollar,
        "redemption_rate": program.points_to_dollar,
    }


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
def get_loyalty_members(db: DbSession):
    """Get loyalty program members."""
    rows = (
        db.query(CustomerLoyalty, Customer)
        .join(Customer, Customer.id == CustomerLoyalty.customer_id)
        .all()
    )

    members: List[LoyaltyMember] = []
    for loyalty, customer in rows:
        members.append(
            LoyaltyMember(
                id=str(loyalty.id),
                name=customer.name,
                email=customer.email or "",
                phone=customer.phone if customer.phone else None,
                points=loyalty.current_points or 0,
                tier=loyalty.current_tier or "bronze",
                total_spent=loyalty.total_spend or 0.0,
                visits=loyalty.total_visits or 0,
                joined_date=(
                    loyalty.first_visit_at.strftime("%Y-%m-%d")
                    if loyalty.first_visit_at
                    else loyalty.created_at.strftime("%Y-%m-%d")
                ),
                last_visit=(
                    loyalty.last_visit_at.strftime("%Y-%m-%d")
                    if loyalty.last_visit_at
                    else loyalty.created_at.strftime("%Y-%m-%d")
                ),
            )
        )

    return members

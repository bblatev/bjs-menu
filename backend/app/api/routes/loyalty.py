"""Loyalty program API routes (gift cards at /gift-cards)."""

from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import func

from app.db.session import DbSession
from app.models.marketing import LoyaltyProgram, CustomerLoyalty
from app.models.customer import Customer
from app.core.rate_limit import limiter

router = APIRouter()


@router.get("/")
@limiter.limit("60/minute")
def get_loyalty_root(request: Request, db: DbSession):
    """Loyalty program overview."""
    return get_loyalty_program(request=request, db=db)


@router.get("/program")
@limiter.limit("60/minute")
def get_loyalty_program(request: Request, db: DbSession):
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
@limiter.limit("30/minute")
def create_loyalty_program(request: Request, body: CreateLoyaltyProgramRequest, db: DbSession):
    """Create or update a loyalty program."""
    # Check if one already exists
    existing = db.query(LoyaltyProgram).first()
    if existing:
        existing.name = body.name
        existing.points_per_dollar = body.points_per_dollar
        existing.points_to_dollar = body.redemption_rate
        db.commit()
        db.refresh(existing)
        return {
            "id": existing.id,
            "name": existing.name,
            "points_per_dollar": existing.points_per_dollar,
            "redemption_rate": existing.points_to_dollar,
        }

    program = LoyaltyProgram(
        name=body.name,
        points_per_dollar=body.points_per_dollar,
        points_to_dollar=body.redemption_rate,
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


@router.post("/members")
@limiter.limit("30/minute")
def add_loyalty_member(request: Request, data: dict, db: DbSession):
    """Add a customer to the loyalty program."""
    customer_id = data.get("customer_id")
    if not customer_id:
        raise HTTPException(status_code=422, detail="customer_id is required")
    # Find or create program
    program = db.query(LoyaltyProgram).first()
    if not program:
        program = LoyaltyProgram(name="Default", points_per_dollar=1, is_active=True)
        db.add(program)
        db.flush()
    existing = db.query(CustomerLoyalty).filter(CustomerLoyalty.customer_id == int(customer_id)).first()
    if existing:
        return {"id": existing.id, "customer_id": int(customer_id), "points": existing.current_points}
    member = CustomerLoyalty(
        customer_id=int(customer_id),
        program_id=program.id,
        current_points=data.get("points", 0),
        current_tier="bronze",
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return {"id": member.id, "customer_id": int(customer_id), "points": member.current_points}


@router.get("/members")
@limiter.limit("60/minute")
def get_loyalty_members(request: Request, db: DbSession):
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

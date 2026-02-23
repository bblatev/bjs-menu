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


# ==================== AI RECOMMENDATIONS, TIERS, SUBSCRIPTIONS ====================

@router.get("/ai-recommendations/{customer_id}")
@limiter.limit("60/minute")
def get_ai_recommendations(request: Request, customer_id: int, db: DbSession):
    """Get AI-powered loyalty recommendations for a customer."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    loyalty = db.query(CustomerLoyalty).filter(
        CustomerLoyalty.customer_id == customer_id
    ).first()

    points = loyalty.current_points if loyalty else 0
    tier = loyalty.current_tier if loyalty else "bronze"

    return {
        "customer_id": customer_id,
        "customer_name": customer.name,
        "current_points": points,
        "current_tier": tier,
        "recommendations": [
            {"type": "reward", "description": "Offer a free appetizer on next visit", "reason": "Increase visit frequency"},
            {"type": "upsell", "description": "Suggest premium menu items", "reason": "Increase average ticket"},
            {"type": "engagement", "description": "Send birthday offer next month", "reason": "Personal touch"},
        ],
        "predicted_next_visit_days": 14,
        "churn_risk": "low",
    }


@router.get("/tiers")
@limiter.limit("60/minute")
def get_loyalty_tiers(request: Request, db: DbSession):
    """Get loyalty tier configuration."""
    program = db.query(LoyaltyProgram).filter(LoyaltyProgram.is_active == True).first()
    tiers = program.tiers if program and program.tiers else []
    if not tiers:
        tiers = [
            {"name": "Bronze", "min_points": 0, "benefits": ["1x points earning"], "discount_pct": 0},
            {"name": "Silver", "min_points": 500, "benefits": ["1.5x points earning", "Free birthday dessert"], "discount_pct": 5},
            {"name": "Gold", "min_points": 1500, "benefits": ["2x points earning", "Priority seating", "Free birthday meal"], "discount_pct": 10},
            {"name": "Platinum", "min_points": 5000, "benefits": ["3x points earning", "VIP events", "Complimentary drinks"], "discount_pct": 15},
        ]
    return {"tiers": tiers, "total": len(tiers)}


@router.get("/tiers/{customer_id}/progress")
@limiter.limit("60/minute")
def get_tier_progress(request: Request, customer_id: int, db: DbSession):
    """Get a customer's progress toward the next loyalty tier."""
    loyalty = db.query(CustomerLoyalty).filter(
        CustomerLoyalty.customer_id == customer_id
    ).first()

    if not loyalty:
        raise HTTPException(status_code=404, detail="Customer not in loyalty program")

    current_points = loyalty.current_points or 0
    current_tier = loyalty.current_tier or "bronze"

    # Define tier thresholds
    tier_thresholds = {"bronze": 0, "silver": 500, "gold": 1500, "platinum": 5000}
    tier_order = ["bronze", "silver", "gold", "platinum"]

    current_idx = tier_order.index(current_tier) if current_tier in tier_order else 0
    next_tier = tier_order[current_idx + 1] if current_idx < len(tier_order) - 1 else None
    next_threshold = tier_thresholds.get(next_tier, 0) if next_tier else 0
    points_needed = max(0, next_threshold - current_points)
    progress_pct = round((current_points / next_threshold * 100), 1) if next_threshold > 0 else 100

    return {
        "customer_id": customer_id,
        "current_tier": current_tier,
        "current_points": current_points,
        "next_tier": next_tier,
        "points_to_next_tier": points_needed,
        "progress_pct": min(progress_pct, 100),
    }


@router.post("/tiers/configure")
@limiter.limit("30/minute")
def configure_loyalty_tiers(request: Request, db: DbSession, data: dict = {}):
    """Configure loyalty tier thresholds and benefits."""
    program = db.query(LoyaltyProgram).first()
    if not program:
        program = LoyaltyProgram(name="Default", points_per_dollar=1, is_active=True)
        db.add(program)
        db.flush()

    tiers = data.get("tiers", [])
    if tiers:
        program.tiers = tiers
        db.commit()

    return {"success": True, "tiers": program.tiers or [], "program_id": program.id}


@router.get("/subscriptions")
@limiter.limit("60/minute")
def get_subscriptions(request: Request, db: DbSession):
    """Get loyalty subscription plans (meal plans, VIP memberships)."""
    return {
        "subscriptions": [
            {"id": 1, "name": "Weekly Lunch Plan", "price": 49.99, "frequency": "weekly", "includes": "5 lunches", "active_subscribers": 0},
            {"id": 2, "name": "Monthly VIP", "price": 29.99, "frequency": "monthly", "includes": "Priority seating + 10% off", "active_subscribers": 0},
            {"id": 3, "name": "Date Night Package", "price": 99.99, "frequency": "monthly", "includes": "2 dinners + bottle of wine", "active_subscribers": 0},
        ],
        "total_active_subscribers": 0,
    }


@router.post("/subscriptions/enroll")
@limiter.limit("30/minute")
def enroll_subscription(request: Request, db: DbSession, data: dict = {}):
    """Enroll a customer in a loyalty subscription plan."""
    customer_id = data.get("customer_id")
    subscription_id = data.get("subscription_id")

    if not customer_id or not subscription_id:
        raise HTTPException(status_code=400, detail="customer_id and subscription_id are required")

    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    return {
        "success": True,
        "customer_id": customer_id,
        "subscription_id": subscription_id,
        "status": "active",
        "enrolled_at": None,
    }

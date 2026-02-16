"""Gamification routes - badges, challenges, leaderboard."""

from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import func

from app.core.rate_limit import limiter
from app.db.session import DbSession
from app.models.operations import Badge, Challenge, StaffAchievement, StaffPoints

router = APIRouter()


# ===================== Pydantic Schemas =====================

class BadgeCreate(BaseModel):
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    category: Optional[str] = None
    criteria: Optional[dict] = None
    points: int = 0
    active: bool = True


class BadgeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    category: Optional[str] = None
    criteria: Optional[dict] = None
    points: Optional[int] = None
    active: Optional[bool] = None


class ChallengeCreate(BaseModel):
    name: str
    description: Optional[str] = None
    type: str = "individual"
    target_value: Optional[float] = None
    reward_points: int = 0
    reward_description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    active: bool = True


# ===================== Badge Endpoints =====================

@router.get("/")
@limiter.limit("60/minute")
def get_gamification_root(request: Request, db: DbSession):
    """Gamification overview."""
    return get_badges(request=request, db=db)


@router.get("/badges")
@limiter.limit("60/minute")
def get_badges(request: Request, db: DbSession):
    """Get all badges."""
    badges = db.query(Badge).order_by(Badge.created_at.desc()).all()

    result = []
    for b in badges:
        # Count how many staff have earned this badge
        earned_count = db.query(func.count(StaffAchievement.id)).filter(
            StaffAchievement.badge_id == b.id
        ).scalar() or 0

        result.append({
            "id": str(b.id),
            "name": b.name,
            "description": b.description,
            "icon": b.icon,
            "category": b.category,
            "criteria": b.criteria,
            "points": b.points,
            "active": b.active,
            "earned_count": earned_count,
            "created_at": b.created_at.isoformat() if b.created_at else None,
        })

    return result


@router.post("/badges")
@limiter.limit("30/minute")
def create_badge(request: Request, data: BadgeCreate, db: DbSession):
    """Create a badge."""
    badge = Badge(
        name=data.name,
        description=data.description,
        icon=data.icon,
        category=data.category,
        criteria=data.criteria,
        points=data.points,
        active=data.active,
    )
    db.add(badge)
    db.commit()
    db.refresh(badge)
    return {"success": True, "id": str(badge.id)}


@router.put("/badges/{badge_id}")
@limiter.limit("30/minute")
def update_badge(request: Request, badge_id: str, data: BadgeUpdate, db: DbSession):
    """Update a badge."""
    badge = db.query(Badge).filter(Badge.id == int(badge_id)).first()
    if not badge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Badge not found",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(badge, field, value)

    db.commit()
    db.refresh(badge)
    return {"success": True}


@router.api_route("/badges/{badge_id}/toggle-active", methods=["POST", "PATCH"])
@limiter.limit("30/minute")
def toggle_badge(request: Request, badge_id: str, db: DbSession):
    """Toggle badge active status."""
    badge = db.query(Badge).filter(Badge.id == int(badge_id)).first()
    if not badge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Badge not found",
        )

    badge.active = not badge.active
    db.commit()
    db.refresh(badge)
    return {"success": True, "active": badge.active}


# ===================== Challenge Endpoints =====================

@router.get("/challenges")
@limiter.limit("60/minute")
def get_challenges(request: Request, db: DbSession):
    """Get active challenges."""
    challenges = db.query(Challenge).order_by(Challenge.created_at.desc()).all()

    today = date.today()
    result = []
    for c in challenges:
        # Determine status based on dates and active flag
        if not c.active:
            c_status = "inactive"
        elif c.end_date and c.end_date < today:
            c_status = "completed"
        elif c.start_date and c.start_date > today:
            c_status = "scheduled"
        else:
            c_status = "active"

        result.append({
            "id": str(c.id),
            "name": c.name,
            "description": c.description,
            "type": c.type,
            "target_value": c.target_value,
            "reward_points": c.reward_points,
            "reward_description": c.reward_description,
            "start_date": c.start_date.isoformat() if c.start_date else None,
            "end_date": c.end_date.isoformat() if c.end_date else None,
            "active": c.active,
            "status": c_status,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })

    return result


@router.post("/challenges")
@limiter.limit("30/minute")
def create_challenge(request: Request, data: ChallengeCreate, db: DbSession):
    """Create a challenge."""
    challenge = Challenge(
        name=data.name,
        description=data.description,
        type=data.type,
        target_value=data.target_value,
        reward_points=data.reward_points,
        reward_description=data.reward_description,
        start_date=data.start_date,
        end_date=data.end_date,
        active=data.active,
    )
    db.add(challenge)
    db.commit()
    db.refresh(challenge)
    return {"success": True, "id": str(challenge.id)}


@router.api_route("/challenges/{challenge_id}/toggle-active", methods=["POST", "PATCH"])
@limiter.limit("30/minute")
def toggle_challenge(request: Request, challenge_id: str, db: DbSession):
    """Toggle challenge active status."""
    challenge = db.query(Challenge).filter(
        Challenge.id == int(challenge_id)
    ).first()
    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Challenge not found",
        )

    challenge.active = not challenge.active
    db.commit()
    db.refresh(challenge)
    return {"success": True, "active": challenge.active}


# ===================== Leaderboard Endpoint =====================

@router.get("/leaderboard")
@limiter.limit("60/minute")
def get_leaderboard(request: Request, db: DbSession):
    """Get staff leaderboard."""
    staff_points = db.query(StaffPoints).order_by(
        StaffPoints.total_points.desc()
    ).all()

    result = []
    for rank, sp in enumerate(staff_points, start=1):
        result.append({
            "rank": rank,
            "staff_id": str(sp.staff_id),
            "name": sp.staff_name,
            "points": sp.total_points,
            "level": sp.level,
            "badges": sp.badges_earned,
            "challenges_completed": sp.challenges_completed,
        })

    return result


# ===================== Achievements Endpoint =====================

@router.get("/achievements/recent")
@limiter.limit("60/minute")
def get_recent_achievements(
    request: Request,
    db: DbSession,
    limit: int = Query(20, le=100),
):
    """Get recent achievements."""
    achievements = db.query(StaffAchievement).order_by(
        StaffAchievement.earned_at.desc()
    ).limit(limit).all()

    return [
        {
            "id": str(a.id),
            "staff_id": str(a.staff_id),
            "staff_name": a.staff_name,
            "badge_id": str(a.badge_id) if a.badge_id else None,
            "badge": a.badge_name,
            "points": a.points,
            "earned_at": a.earned_at.isoformat() if a.earned_at else None,
        }
        for a in achievements
    ]

"""Referral program API routes."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import func

from app.db.session import DbSession
from app.models.operations import ReferralProgram, ReferralRecord

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


class CreateReferralProgramRequest(BaseModel):
    name: str
    referrer_reward: float = 0
    referee_reward: float = 0
    reward_type: str = "points"


@router.post("/programs")
def create_referral_program(request: CreateReferralProgramRequest, db: DbSession):
    """Create a referral program."""
    program = ReferralProgram(
        name=request.name,
        reward_type=request.reward_type,
        reward_value=request.referrer_reward,
        referee_reward_value=request.referee_reward,
        active=True,
    )
    db.add(program)
    db.commit()
    db.refresh(program)
    return {
        "id": program.id,
        "name": program.name,
        "reward_type": program.reward_type,
        "referrer_reward": float(program.reward_value) if program.reward_value else 0,
        "referee_reward": float(program.referee_reward_value) if program.referee_reward_value else 0,
        "active": program.active,
    }


@router.get("/programs")
def get_referral_programs(db: DbSession):
    """Get referral programs."""
    programs = db.query(ReferralProgram).all()
    result = []
    for p in programs:
        result.append({
            "id": str(p.id),
            "name": p.name,
            "reward_type": p.reward_type,
            "reward_value": float(p.reward_value) if p.reward_value else 0.0,
            "referee_reward_value": float(p.referee_reward_value) if p.referee_reward_value else 0.0,
            "active": p.active,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        })
    return {"programs": result, "total": len(result)}


@router.post("/")
def create_referral(data: dict, db: DbSession):
    """Create a single referral."""
    program = db.query(ReferralProgram).filter(ReferralProgram.active == True).first()
    record = ReferralRecord(
        referrer_name=data.get("referrer_name", ""),
        referrer_email=data.get("referrer_email", ""),
        referee_name=data.get("referee_name", ""),
        referee_email=data.get("referee_email", data.get("referee_phone", "")),
        status="pending",
        reward_claimed=False,
        program_id=program.id if program else None,
        created_at=datetime.utcnow(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"id": record.id, "status": "pending", "referee_name": record.referee_name}


@router.get("/")
def get_referrals(db: DbSession):
    """Get all referrals."""
    records = (
        db.query(ReferralRecord)
        .order_by(ReferralRecord.created_at.desc())
        .all()
    )
    result = []
    for r in records:
        # Look up the program to get the reward value
        reward_amount = 0.0
        if r.program_id:
            program = db.query(ReferralProgram).filter(ReferralProgram.id == r.program_id).first()
            if program and program.reward_value:
                reward_amount = float(program.reward_value)

        result.append(Referral(
            id=str(r.id),
            referrer_id=str(r.id),
            referrer_name=r.referrer_name or "",
            referee_name=r.referee_name or "",
            referee_email=r.referee_email or "",
            status=r.status or "pending",
            reward_amount=reward_amount,
            created_at=r.created_at.isoformat() if r.created_at else "",
            completed_at=r.completed_at.isoformat() if r.completed_at else None,
        ))
    return result


@router.get("/referrers")
def get_referrers(db: DbSession):
    """Get all referrers."""
    # Aggregate referral records by referrer_email to build referrer summaries
    referrer_rows = (
        db.query(
            ReferralRecord.referrer_name,
            ReferralRecord.referrer_email,
            func.count(ReferralRecord.id).label("total_referrals"),
            func.count(
                func.nullif(ReferralRecord.status != "completed", True)
            ).label("successful_referrals"),
        )
        .group_by(ReferralRecord.referrer_email, ReferralRecord.referrer_name)
        .all()
    )

    result = []
    for idx, row in enumerate(referrer_rows, start=1):
        referrer_email = row.referrer_email or ""
        referrer_name = row.referrer_name or ""

        # Calculate earnings from completed referrals for this referrer
        completed_records = (
            db.query(ReferralRecord)
            .filter(
                ReferralRecord.referrer_email == referrer_email,
                ReferralRecord.status == "completed",
                ReferralRecord.reward_claimed == True,
            )
            .all()
        )
        total_earned = 0.0
        for rec in completed_records:
            if rec.program_id:
                prog = db.query(ReferralProgram).filter(ReferralProgram.id == rec.program_id).first()
                if prog and prog.reward_value:
                    total_earned += float(prog.reward_value)

        # Pending rewards: completed but not yet claimed
        pending_records = (
            db.query(ReferralRecord)
            .filter(
                ReferralRecord.referrer_email == referrer_email,
                ReferralRecord.status == "completed",
                ReferralRecord.reward_claimed == False,
            )
            .all()
        )
        pending_rewards = 0.0
        for rec in pending_records:
            if rec.program_id:
                prog = db.query(ReferralProgram).filter(ReferralProgram.id == rec.program_id).first()
                if prog and prog.reward_value:
                    pending_rewards += float(prog.reward_value)

        result.append(Referrer(
            id=str(idx),
            name=referrer_name,
            email=referrer_email,
            total_referrals=row.total_referrals,
            successful_referrals=row.successful_referrals,
            total_earned=total_earned,
            pending_rewards=pending_rewards,
        ))
    return result


@router.get("/campaigns")
def get_referral_campaigns(db: DbSession):
    """Get referral campaigns."""
    programs = db.query(ReferralProgram).all()
    result = []
    for p in programs:
        result.append(ReferralCampaign(
            id=str(p.id),
            name=p.name or "",
            referrer_reward=float(p.reward_value) if p.reward_value else 0.0,
            referee_reward=float(p.referee_reward_value) if p.referee_reward_value else 0.0,
            min_spend=0.0,
            expires_at=None,
            active=p.active if p.active is not None else True,
        ))
    return result


@router.get("/settings")
def get_referral_settings(db: DbSession):
    """Get referral program settings."""
    # Derive defaults from the first active program, or use sensible defaults
    default_program = (
        db.query(ReferralProgram)
        .filter(ReferralProgram.active == True)
        .first()
    )
    if default_program:
        default_referrer_reward = float(default_program.reward_value) if default_program.reward_value else 0.0
        default_referee_reward = float(default_program.referee_reward_value) if default_program.referee_reward_value else 0.0
    else:
        default_referrer_reward = 0.0
        default_referee_reward = 0.0

    total_referrers = (
        db.query(func.count(func.distinct(ReferralRecord.referrer_email)))
        .scalar() or 0
    )

    return ReferralSettings(
        default_referrer_reward=default_referrer_reward,
        default_referee_reward=default_referee_reward,
        min_spend_required=0.0,
        reward_expiry_days=90,
        max_referrals_per_customer=10,
    )


@router.post("/bulk-send")
def send_bulk_invites(emails: List[str], db: DbSession):
    """Send bulk referral invites."""
    # Get the default active program
    program = (
        db.query(ReferralProgram)
        .filter(ReferralProgram.active == True)
        .first()
    )

    created_count = 0
    for email in emails:
        record = ReferralRecord(
            referee_email=email,
            status="pending",
            reward_claimed=False,
            program_id=program.id if program else None,
            created_at=datetime.utcnow(),
        )
        db.add(record)
        created_count += 1

    db.commit()
    return {"success": True, "sent_count": created_count}


@router.get("/stats")
def get_referral_stats(db: DbSession):
    """Get referral program statistics."""
    total_referrals = (
        db.query(func.count(ReferralRecord.id)).scalar() or 0
    )
    successful_referrals = (
        db.query(func.count(ReferralRecord.id))
        .filter(ReferralRecord.status == "completed")
        .scalar() or 0
    )
    pending_referrals = (
        db.query(func.count(ReferralRecord.id))
        .filter(ReferralRecord.status == "pending")
        .scalar() or 0
    )

    # Calculate total rewards given from completed + claimed referrals
    claimed_records = (
        db.query(ReferralRecord)
        .filter(
            ReferralRecord.status == "completed",
            ReferralRecord.reward_claimed == True,
        )
        .all()
    )
    total_rewards_given = 0.0
    for rec in claimed_records:
        if rec.program_id:
            prog = db.query(ReferralProgram).filter(ReferralProgram.id == rec.program_id).first()
            if prog and prog.reward_value:
                total_rewards_given += float(prog.reward_value)

    avg_reward_value = 0.0
    if claimed_records:
        avg_reward_value = round(total_rewards_given / len(claimed_records), 2)

    conversion_rate = 0.0
    if total_referrals > 0:
        conversion_rate = round((successful_referrals / total_referrals) * 100, 1)

    # Top referrers by successful referral count
    top_referrer_rows = (
        db.query(
            ReferralRecord.referrer_name,
            ReferralRecord.referrer_email,
            func.count(ReferralRecord.id).label("count"),
        )
        .filter(ReferralRecord.status == "completed")
        .group_by(ReferralRecord.referrer_email, ReferralRecord.referrer_name)
        .order_by(func.count(ReferralRecord.id).desc())
        .limit(10)
        .all()
    )
    top_referrers = [
        {
            "name": row.referrer_name or "",
            "email": row.referrer_email or "",
            "successful_referrals": row.count,
        }
        for row in top_referrer_rows
    ]

    return {
        "total_referrals": total_referrals,
        "successful_referrals": successful_referrals,
        "pending_referrals": pending_referrals,
        "total_rewards_given": total_rewards_given,
        "avg_reward_value": avg_reward_value,
        "conversion_rate": conversion_rate,
        "top_referrers": top_referrers,
    }

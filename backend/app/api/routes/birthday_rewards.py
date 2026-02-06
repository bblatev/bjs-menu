"""Birthday & Anniversary Auto-Rewards API routes.

Automated reward triggers for customer birthdays and special occasions.
"""

from typing import Optional, List
from datetime import date
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.birthday_rewards_service import (
    get_birthday_rewards_service,
    OccasionType,
    RewardType,
    RewardStatus,
)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class CreateRuleRequest(BaseModel):
    name: str
    occasion_type: str  # birthday, anniversary, membership, custom
    reward_type: str  # points, discount_percent, discount_amount, free_item, gift_card
    reward_value: float
    reward_item_id: Optional[str] = None
    valid_days_before: int = 7
    valid_days_after: int = 14
    min_visits: int = 0
    min_spend: float = 0
    message_template: str = ""
    venue_id: Optional[int] = None


class UpdateRuleRequest(BaseModel):
    name: Optional[str] = None
    reward_value: Optional[float] = None
    valid_days_before: Optional[int] = None
    valid_days_after: Optional[int] = None
    min_visits: Optional[int] = None
    min_spend: Optional[float] = None
    message_template: Optional[str] = None
    is_active: Optional[bool] = None


class SetBirthdayRequest(BaseModel):
    customer_id: int
    birthday: str  # YYYY-MM-DD


class SetAnniversaryRequest(BaseModel):
    customer_id: int
    anniversary_date: str  # YYYY-MM-DD
    occasion_type: str = "membership"


class ValidateRewardRequest(BaseModel):
    code: str


class ClaimRewardRequest(BaseModel):
    code: str
    order_id: Optional[str] = None


class RuleResponse(BaseModel):
    rule_id: str
    name: str
    occasion_type: str
    reward_type: str
    reward_value: float
    reward_item_id: Optional[str] = None
    valid_days_before: int
    valid_days_after: int
    min_visits: int
    min_spend: float
    message_template: str
    is_active: bool
    venue_id: Optional[int] = None
    created_at: str


class RewardResponse(BaseModel):
    reward_id: str
    customer_id: int
    occasion_type: str
    reward_type: str
    reward_value: float
    reward_item_id: Optional[str] = None
    code: str
    message: str
    status: str
    valid_from: str
    valid_until: str
    issued_at: str
    claimed_at: Optional[str] = None
    order_id: Optional[str] = None


# ============================================================================
# Rule Management
# ============================================================================

@router.post("/rules", response_model=RuleResponse)
async def create_rule(request: CreateRuleRequest):
    """
    Create a reward rule for automatic occasion-based rewards.

    Occasion types: birthday, anniversary, membership, custom
    Reward types: points, discount_percent, discount_amount, free_item, gift_card
    """
    service = get_birthday_rewards_service()

    try:
        occasion_type = OccasionType(request.occasion_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid occasion type: {request.occasion_type}")

    try:
        reward_type = RewardType(request.reward_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid reward type: {request.reward_type}")

    rule = service.create_rule(
        name=request.name,
        occasion_type=occasion_type,
        reward_type=reward_type,
        reward_value=request.reward_value,
        reward_item_id=request.reward_item_id,
        valid_days_before=request.valid_days_before,
        valid_days_after=request.valid_days_after,
        min_visits=request.min_visits,
        min_spend=request.min_spend,
        message_template=request.message_template,
        venue_id=request.venue_id,
    )

    return _rule_to_response(rule)


@router.get("/rules", response_model=List[RuleResponse])
async def list_rules(
    occasion_type: Optional[str] = None,
    is_active: Optional[bool] = None,
):
    """List reward rules."""
    service = get_birthday_rewards_service()

    occ_type = None
    if occasion_type:
        try:
            occ_type = OccasionType(occasion_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid occasion type: {occasion_type}")

    rules = service.list_rules(occasion_type=occ_type, is_active=is_active)

    return [_rule_to_response(r) for r in rules]


@router.get("/rules/{rule_id}", response_model=RuleResponse)
async def get_rule(rule_id: str):
    """Get a specific rule."""
    service = get_birthday_rewards_service()

    rule = service.get_rule(rule_id)

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    return _rule_to_response(rule)


@router.put("/rules/{rule_id}", response_model=RuleResponse)
async def update_rule(rule_id: str, request: UpdateRuleRequest):
    """Update a reward rule."""
    service = get_birthday_rewards_service()

    updates = {}
    if request.name is not None:
        updates["name"] = request.name
    if request.reward_value is not None:
        updates["reward_value"] = request.reward_value
    if request.valid_days_before is not None:
        updates["valid_days_before"] = request.valid_days_before
    if request.valid_days_after is not None:
        updates["valid_days_after"] = request.valid_days_after
    if request.min_visits is not None:
        updates["min_visits"] = request.min_visits
    if request.min_spend is not None:
        updates["min_spend"] = request.min_spend
    if request.message_template is not None:
        updates["message_template"] = request.message_template
    if request.is_active is not None:
        updates["is_active"] = request.is_active

    rule = service.update_rule(rule_id, **updates)

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    return _rule_to_response(rule)


@router.post("/rules/{rule_id}/toggle")
async def toggle_rule(rule_id: str, is_active: bool):
    """Enable or disable a rule."""
    service = get_birthday_rewards_service()

    rule = service.toggle_rule(rule_id, is_active)

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    return {
        "success": True,
        "rule_id": rule_id,
        "is_active": rule.is_active,
    }


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str):
    """Delete a reward rule."""
    service = get_birthday_rewards_service()

    if not service.delete_rule(rule_id):
        raise HTTPException(status_code=404, detail="Rule not found")

    return {"success": True, "message": "Rule deleted"}


# ============================================================================
# Customer Occasions
# ============================================================================

@router.post("/customers/birthday")
async def set_customer_birthday(request: SetBirthdayRequest):
    """Set a customer's birthday."""
    service = get_birthday_rewards_service()

    try:
        birthday = date.fromisoformat(request.birthday)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    occasion = service.set_customer_birthday(request.customer_id, birthday)

    return {
        "success": True,
        "customer_id": request.customer_id,
        "occasion_type": occasion.occasion_type.value,
        "occasion_date": occasion.occasion_date.isoformat(),
    }


@router.post("/customers/anniversary")
async def set_customer_anniversary(request: SetAnniversaryRequest):
    """Set a customer's anniversary date."""
    service = get_birthday_rewards_service()

    try:
        anniversary = date.fromisoformat(request.anniversary_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    try:
        occasion_type = OccasionType(request.occasion_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid occasion type: {request.occasion_type}")

    occasion = service.set_customer_anniversary(
        request.customer_id,
        anniversary,
        occasion_type,
    )

    return {
        "success": True,
        "customer_id": request.customer_id,
        "occasion_type": occasion.occasion_type.value,
        "occasion_date": occasion.occasion_date.isoformat(),
    }


@router.get("/customers/{customer_id}/occasions")
async def get_customer_occasions(customer_id: int):
    """Get all occasions for a customer."""
    service = get_birthday_rewards_service()

    occasions = service.get_customer_occasions(customer_id)

    return {
        "customer_id": customer_id,
        "occasions": [
            {
                "occasion_type": o.occasion_type.value,
                "occasion_date": o.occasion_date.isoformat(),
                "year": o.year,
            }
            for o in occasions
        ],
    }


# ============================================================================
# Upcoming Occasions & Auto-Issue
# ============================================================================

@router.get("/upcoming")
async def get_upcoming_occasions(days_ahead: int = 7):
    """Get customers with upcoming occasions."""
    service = get_birthday_rewards_service()

    upcoming = service.get_upcoming_occasions(days_ahead)

    return {
        "days_ahead": days_ahead,
        "count": len(upcoming),
        "occasions": upcoming,
    }


@router.post("/check-and-issue")
async def check_and_issue_rewards():
    """
    Check for upcoming occasions and automatically issue rewards.

    Call this from a daily cron job to ensure rewards are issued on time.
    """
    service = get_birthday_rewards_service()

    result = await service.check_and_issue_rewards()

    return result


# ============================================================================
# Rewards
# ============================================================================

@router.get("/rewards", response_model=None)
async def list_customer_rewards(
    customer_id: Optional[int] = None,
    status: Optional[str] = None,
    include_expired: bool = False,
):
    """Get rewards for a customer."""
    if customer_id is None:
        return []
    service = get_birthday_rewards_service()

    reward_status = None
    if status:
        try:
            reward_status = RewardStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    rewards = service.get_customer_rewards(
        customer_id,
        status=reward_status,
        include_expired=include_expired,
    )

    return [_reward_to_response(r) for r in rewards]


@router.get("/rewards/{reward_id}", response_model=RewardResponse)
async def get_reward(reward_id: str):
    """Get a specific reward."""
    service = get_birthday_rewards_service()

    reward = service.get_reward(reward_id)

    if not reward:
        raise HTTPException(status_code=404, detail="Reward not found")

    return _reward_to_response(reward)


@router.post("/rewards/validate")
async def validate_reward(request: ValidateRewardRequest):
    """
    Validate a reward code.

    Use this at checkout to verify the reward is valid before applying.
    """
    service = get_birthday_rewards_service()

    result = service.validate_reward(request.code)

    return result


@router.post("/rewards/claim")
async def claim_reward(request: ClaimRewardRequest):
    """
    Claim a reward.

    Call this when applying the reward to an order.
    """
    service = get_birthday_rewards_service()

    reward = service.claim_reward(request.code, request.order_id)

    if not reward:
        validation = service.validate_reward(request.code)
        raise HTTPException(
            status_code=400,
            detail=validation.get("error", "Invalid reward"),
        )

    return {
        "success": True,
        "reward_id": reward.reward_id,
        "status": reward.status.value,
        "claimed_at": reward.claimed_at.isoformat() if reward.claimed_at else None,
    }


# ============================================================================
# Statistics
# ============================================================================

@router.get("/stats")
async def get_stats():
    """Get birthday rewards statistics."""
    service = get_birthday_rewards_service()

    return service.get_stats()


# ============================================================================
# Info
# ============================================================================

@router.get("/occasion-types")
async def get_occasion_types():
    """Get available occasion types."""
    return {
        "types": [
            {"id": "birthday", "name": "Birthday"},
            {"id": "anniversary", "name": "First Visit Anniversary"},
            {"id": "membership", "name": "Loyalty Membership Anniversary"},
            {"id": "custom", "name": "Custom Occasion"},
        ],
    }


@router.get("/reward-types")
async def get_reward_types():
    """Get available reward types."""
    return {
        "types": [
            {"id": "points", "name": "Bonus Points", "description": "Award loyalty points"},
            {"id": "discount_percent", "name": "Percentage Discount", "description": "Discount by percentage"},
            {"id": "discount_amount", "name": "Fixed Discount", "description": "Discount by fixed amount"},
            {"id": "free_item", "name": "Free Item", "description": "Free menu item"},
            {"id": "gift_card", "name": "Gift Card", "description": "Issue gift card credit"},
        ],
    }


# ============================================================================
# Helper Functions
# ============================================================================

def _rule_to_response(rule) -> RuleResponse:
    """Convert rule to response model."""
    return RuleResponse(
        rule_id=rule.rule_id,
        name=rule.name,
        occasion_type=rule.occasion_type.value,
        reward_type=rule.reward_type.value,
        reward_value=rule.reward_value,
        reward_item_id=rule.reward_item_id,
        valid_days_before=rule.valid_days_before,
        valid_days_after=rule.valid_days_after,
        min_visits=rule.min_visits,
        min_spend=rule.min_spend,
        message_template=rule.message_template,
        is_active=rule.is_active,
        venue_id=rule.venue_id,
        created_at=rule.created_at.isoformat(),
    )


def _reward_to_response(reward) -> RewardResponse:
    """Convert reward to response model."""
    return RewardResponse(
        reward_id=reward.reward_id,
        customer_id=reward.customer_id,
        occasion_type=reward.occasion_type.value,
        reward_type=reward.reward_type.value,
        reward_value=reward.reward_value,
        reward_item_id=reward.reward_item_id,
        code=reward.code,
        message=reward.message,
        status=reward.status.value,
        valid_from=reward.valid_from.isoformat(),
        valid_until=reward.valid_until.isoformat(),
        issued_at=reward.issued_at.isoformat(),
        claimed_at=reward.claimed_at.isoformat() if reward.claimed_at else None,
        order_id=reward.order_id,
    )

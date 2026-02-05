"""Birthday & Anniversary Auto-Rewards Service.

Automatically triggers rewards for customer birthdays and special occasions.
"""

import logging
from datetime import datetime, date, timedelta, timezone
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class OccasionType(str, Enum):
    BIRTHDAY = "birthday"
    ANNIVERSARY = "anniversary"  # Customer since anniversary
    MEMBERSHIP = "membership"  # Loyalty membership anniversary
    CUSTOM = "custom"


class RewardType(str, Enum):
    POINTS = "points"
    DISCOUNT_PERCENT = "discount_percent"
    DISCOUNT_AMOUNT = "discount_amount"
    FREE_ITEM = "free_item"
    GIFT_CARD = "gift_card"


class RewardStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    CLAIMED = "claimed"
    EXPIRED = "expired"


@dataclass
class OccasionRewardRule:
    """A rule for automatic occasion-based rewards."""
    rule_id: str
    name: str
    occasion_type: OccasionType
    reward_type: RewardType
    reward_value: float  # Points amount, discount %, or discount amount
    reward_item_id: Optional[str] = None  # For free_item type
    valid_days_before: int = 7  # Send reward N days before occasion
    valid_days_after: int = 14  # Reward valid until N days after
    min_visits: int = 0  # Minimum visits to qualify
    min_spend: float = 0  # Minimum total spend to qualify
    message_template: str = ""
    is_active: bool = True
    venue_id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CustomerOccasion:
    """A customer's special occasion."""
    customer_id: int
    occasion_type: OccasionType
    occasion_date: date  # Month and day (year ignored for recurring)
    year: Optional[int] = None  # Original year for anniversaries


@dataclass
class IssuedReward:
    """A reward issued to a customer."""
    reward_id: str
    customer_id: int
    rule_id: str
    occasion_type: OccasionType
    reward_type: RewardType
    reward_value: float
    code: str  # Redemption code
    message: str
    reward_item_id: Optional[str] = None
    status: RewardStatus = RewardStatus.PENDING
    valid_from: date = field(default_factory=date.today)
    valid_until: date = field(default_factory=date.today)
    issued_at: datetime = field(default_factory=datetime.utcnow)
    claimed_at: Optional[datetime] = None
    order_id: Optional[str] = None


class BirthdayRewardsService:
    """Service for managing birthday and occasion-based rewards.

    Features:
    - Configure reward rules for birthdays, anniversaries, etc.
    - Automatically detect upcoming occasions
    - Issue and track rewards
    - Integration with notification service for delivery
    """

    def __init__(self, notification_service=None, loyalty_service=None):
        self.notification_service = notification_service
        self.loyalty_service = loyalty_service

        # In-memory storage (use database in production)
        self._rules: Dict[str, OccasionRewardRule] = {}
        self._occasions: Dict[int, List[CustomerOccasion]] = {}  # customer_id -> occasions
        self._rewards: Dict[str, IssuedReward] = {}
        self._rewards_by_customer: Dict[int, List[str]] = {}  # customer_id -> reward_ids

        # Create default rules
        self._create_default_rules()

    def _create_default_rules(self):
        """Create default birthday and anniversary rules."""
        # Birthday reward
        birthday_rule = OccasionRewardRule(
            rule_id="rule-birthday-default",
            name="Birthday Reward",
            occasion_type=OccasionType.BIRTHDAY,
            reward_type=RewardType.DISCOUNT_PERCENT,
            reward_value=20,  # 20% off
            valid_days_before=7,
            valid_days_after=7,
            message_template="Happy Birthday, {{customer_name}}! Enjoy {{reward_value}}% off your next visit!",
        )
        self._rules[birthday_rule.rule_id] = birthday_rule

        # Membership anniversary reward
        anniversary_rule = OccasionRewardRule(
            rule_id="rule-anniversary-default",
            name="Loyalty Anniversary Reward",
            occasion_type=OccasionType.MEMBERSHIP,
            reward_type=RewardType.POINTS,
            reward_value=500,  # 500 bonus points
            valid_days_before=0,
            valid_days_after=30,
            min_visits=3,
            message_template="Thank you for {{years}} years with us, {{customer_name}}! Here's {{reward_value}} bonus points!",
        )
        self._rules[anniversary_rule.rule_id] = anniversary_rule

    # =========================================================================
    # Rule Management
    # =========================================================================

    def create_rule(
        self,
        name: str,
        occasion_type: OccasionType,
        reward_type: RewardType,
        reward_value: float,
        reward_item_id: Optional[str] = None,
        valid_days_before: int = 7,
        valid_days_after: int = 14,
        min_visits: int = 0,
        min_spend: float = 0,
        message_template: str = "",
        venue_id: Optional[int] = None,
    ) -> OccasionRewardRule:
        """Create a new reward rule."""
        rule_id = f"rule-{uuid.uuid4().hex[:8]}"

        rule = OccasionRewardRule(
            rule_id=rule_id,
            name=name,
            occasion_type=occasion_type,
            reward_type=reward_type,
            reward_value=reward_value,
            reward_item_id=reward_item_id,
            valid_days_before=valid_days_before,
            valid_days_after=valid_days_after,
            min_visits=min_visits,
            min_spend=min_spend,
            message_template=message_template,
            venue_id=venue_id,
        )

        self._rules[rule_id] = rule
        logger.info(f"Created reward rule {rule_id}: {name}")

        return rule

    def update_rule(self, rule_id: str, **updates) -> Optional[OccasionRewardRule]:
        """Update a reward rule."""
        rule = self._rules.get(rule_id)
        if not rule:
            return None

        for key, value in updates.items():
            if hasattr(rule, key) and value is not None:
                setattr(rule, key, value)

        return rule

    def get_rule(self, rule_id: str) -> Optional[OccasionRewardRule]:
        """Get a rule by ID."""
        return self._rules.get(rule_id)

    def list_rules(
        self,
        occasion_type: Optional[OccasionType] = None,
        is_active: Optional[bool] = None,
    ) -> List[OccasionRewardRule]:
        """List reward rules."""
        rules = list(self._rules.values())

        if occasion_type:
            rules = [r for r in rules if r.occasion_type == occasion_type]

        if is_active is not None:
            rules = [r for r in rules if r.is_active == is_active]

        return rules

    def toggle_rule(self, rule_id: str, is_active: bool) -> Optional[OccasionRewardRule]:
        """Enable or disable a rule."""
        rule = self._rules.get(rule_id)
        if rule:
            rule.is_active = is_active
        return rule

    def delete_rule(self, rule_id: str) -> bool:
        """Delete a rule."""
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False

    # =========================================================================
    # Customer Occasions
    # =========================================================================

    def set_customer_birthday(
        self,
        customer_id: int,
        birthday: date,
    ) -> CustomerOccasion:
        """Set a customer's birthday."""
        occasion = CustomerOccasion(
            customer_id=customer_id,
            occasion_type=OccasionType.BIRTHDAY,
            occasion_date=birthday,
            year=birthday.year,
        )

        if customer_id not in self._occasions:
            self._occasions[customer_id] = []

        # Remove existing birthday if any
        self._occasions[customer_id] = [
            o for o in self._occasions[customer_id]
            if o.occasion_type != OccasionType.BIRTHDAY
        ]

        self._occasions[customer_id].append(occasion)
        logger.info(f"Set birthday for customer {customer_id}: {birthday}")

        return occasion

    def set_customer_anniversary(
        self,
        customer_id: int,
        anniversary_date: date,
        occasion_type: OccasionType = OccasionType.MEMBERSHIP,
    ) -> CustomerOccasion:
        """Set a customer's anniversary date."""
        occasion = CustomerOccasion(
            customer_id=customer_id,
            occasion_type=occasion_type,
            occasion_date=anniversary_date,
            year=anniversary_date.year,
        )

        if customer_id not in self._occasions:
            self._occasions[customer_id] = []

        # Remove existing of same type
        self._occasions[customer_id] = [
            o for o in self._occasions[customer_id]
            if o.occasion_type != occasion_type
        ]

        self._occasions[customer_id].append(occasion)

        return occasion

    def get_customer_occasions(self, customer_id: int) -> List[CustomerOccasion]:
        """Get all occasions for a customer."""
        return self._occasions.get(customer_id, [])

    # =========================================================================
    # Occasion Detection & Reward Issuance
    # =========================================================================

    def get_upcoming_occasions(
        self,
        days_ahead: int = 7,
    ) -> List[Dict[str, Any]]:
        """Get customers with upcoming occasions."""
        today = date.today()
        upcoming = []

        for customer_id, occasions in self._occasions.items():
            for occasion in occasions:
                # Check if occasion falls within the window
                occasion_this_year = occasion.occasion_date.replace(year=today.year)

                # Handle year boundary
                if occasion_this_year < today:
                    occasion_this_year = occasion_this_year.replace(year=today.year + 1)

                days_until = (occasion_this_year - today).days

                if 0 <= days_until <= days_ahead:
                    # Calculate years (for anniversaries)
                    years = None
                    if occasion.year:
                        years = today.year - occasion.year
                        if occasion_this_year.year > today.year:
                            years = today.year + 1 - occasion.year

                    upcoming.append({
                        "customer_id": customer_id,
                        "occasion_type": occasion.occasion_type.value,
                        "occasion_date": occasion_this_year.isoformat(),
                        "days_until": days_until,
                        "years": years,
                    })

        return sorted(upcoming, key=lambda x: x["days_until"])

    async def check_and_issue_rewards(self) -> Dict[str, Any]:
        """Check for upcoming occasions and issue rewards."""
        today = date.today()
        issued_count = 0
        skipped_count = 0

        for customer_id, occasions in self._occasions.items():
            for occasion in occasions:
                # Find applicable rules
                rules = [
                    r for r in self._rules.values()
                    if r.is_active and r.occasion_type == occasion.occasion_type
                ]

                for rule in rules:
                    # Check if occasion is within the trigger window
                    occasion_this_year = occasion.occasion_date.replace(year=today.year)
                    if occasion_this_year < today - timedelta(days=rule.valid_days_after):
                        occasion_this_year = occasion_this_year.replace(year=today.year + 1)

                    days_until = (occasion_this_year - today).days

                    # Check if within trigger window
                    if days_until > rule.valid_days_before:
                        continue

                    if days_until < -rule.valid_days_after:
                        continue

                    # Check if reward already issued this year
                    existing = self._get_existing_reward(customer_id, rule.rule_id, today.year)
                    if existing:
                        skipped_count += 1
                        continue

                    # Issue reward
                    reward = await self._issue_reward(
                        customer_id=customer_id,
                        rule=rule,
                        occasion=occasion,
                        occasion_date=occasion_this_year,
                    )

                    if reward:
                        issued_count += 1

        logger.info(f"Issued {issued_count} rewards, skipped {skipped_count}")

        return {
            "issued": issued_count,
            "skipped": skipped_count,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    def _get_existing_reward(
        self,
        customer_id: int,
        rule_id: str,
        year: int,
    ) -> Optional[IssuedReward]:
        """Check if reward already issued for this customer/rule/year."""
        reward_ids = self._rewards_by_customer.get(customer_id, [])
        for rid in reward_ids:
            reward = self._rewards.get(rid)
            if (reward and
                reward.rule_id == rule_id and
                reward.issued_at.year == year):
                return reward
        return None

    async def _issue_reward(
        self,
        customer_id: int,
        rule: OccasionRewardRule,
        occasion: CustomerOccasion,
        occasion_date: date,
    ) -> Optional[IssuedReward]:
        """Issue a reward to a customer."""
        today = date.today()

        # Generate redemption code
        code = f"BDAY-{uuid.uuid4().hex[:8].upper()}"
        if rule.occasion_type == OccasionType.MEMBERSHIP:
            code = f"ANNI-{uuid.uuid4().hex[:8].upper()}"

        # Calculate validity period
        valid_from = today
        valid_until = occasion_date + timedelta(days=rule.valid_days_after)

        # Calculate years for message
        years = None
        if occasion.year:
            years = today.year - occasion.year

        # Build message
        message = rule.message_template
        message = message.replace("{{customer_name}}", f"Customer {customer_id}")  # Replace with actual name
        message = message.replace("{{reward_value}}", str(int(rule.reward_value)))
        if years:
            message = message.replace("{{years}}", str(years))

        reward = IssuedReward(
            reward_id=f"rwd-{uuid.uuid4().hex[:8]}",
            customer_id=customer_id,
            rule_id=rule.rule_id,
            occasion_type=rule.occasion_type,
            reward_type=rule.reward_type,
            reward_value=rule.reward_value,
            reward_item_id=rule.reward_item_id,
            code=code,
            message=message,
            valid_from=valid_from,
            valid_until=valid_until,
        )

        self._rewards[reward.reward_id] = reward

        if customer_id not in self._rewards_by_customer:
            self._rewards_by_customer[customer_id] = []
        self._rewards_by_customer[customer_id].append(reward.reward_id)

        logger.info(f"Issued {rule.occasion_type.value} reward {reward.reward_id} to customer {customer_id}")

        # Send notification if service available
        if self.notification_service:
            await self._send_reward_notification(reward)

        return reward

    async def _send_reward_notification(self, reward: IssuedReward):
        """Send reward notification to customer."""
        # In production, use notification service to send email/SMS/push
        reward.status = RewardStatus.SENT
        logger.info(f"Sent notification for reward {reward.reward_id}")

    # =========================================================================
    # Reward Redemption
    # =========================================================================

    def get_reward(self, reward_id: str) -> Optional[IssuedReward]:
        """Get a reward by ID."""
        return self._rewards.get(reward_id)

    def get_reward_by_code(self, code: str) -> Optional[IssuedReward]:
        """Get a reward by redemption code."""
        for reward in self._rewards.values():
            if reward.code == code:
                return reward
        return None

    def get_customer_rewards(
        self,
        customer_id: int,
        status: Optional[RewardStatus] = None,
        include_expired: bool = False,
    ) -> List[IssuedReward]:
        """Get rewards for a customer."""
        reward_ids = self._rewards_by_customer.get(customer_id, [])
        rewards = [self._rewards[rid] for rid in reward_ids if rid in self._rewards]

        today = date.today()

        if not include_expired:
            rewards = [r for r in rewards if r.valid_until >= today]

        if status:
            rewards = [r for r in rewards if r.status == status]

        return sorted(rewards, key=lambda r: r.valid_until)

    def validate_reward(self, code: str) -> Dict[str, Any]:
        """Validate a reward code."""
        reward = self.get_reward_by_code(code)

        if not reward:
            return {"valid": False, "error": "Invalid reward code"}

        today = date.today()

        if reward.status == RewardStatus.CLAIMED:
            return {"valid": False, "error": "Reward already claimed"}

        if reward.status == RewardStatus.EXPIRED:
            return {"valid": False, "error": "Reward expired"}

        if today < reward.valid_from:
            return {"valid": False, "error": f"Reward not yet valid. Valid from {reward.valid_from}"}

        if today > reward.valid_until:
            reward.status = RewardStatus.EXPIRED
            return {"valid": False, "error": "Reward expired"}

        return {
            "valid": True,
            "reward_id": reward.reward_id,
            "reward_type": reward.reward_type.value,
            "reward_value": reward.reward_value,
            "reward_item_id": reward.reward_item_id,
            "valid_until": reward.valid_until.isoformat(),
        }

    def claim_reward(
        self,
        code: str,
        order_id: Optional[str] = None,
    ) -> Optional[IssuedReward]:
        """Claim a reward."""
        validation = self.validate_reward(code)
        if not validation.get("valid"):
            return None

        reward = self.get_reward_by_code(code)
        if reward:
            reward.status = RewardStatus.CLAIMED
            reward.claimed_at = datetime.now(timezone.utc)
            reward.order_id = order_id

            logger.info(f"Reward {reward.reward_id} claimed on order {order_id}")

        return reward

    # =========================================================================
    # Reporting
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get reward statistics."""
        total_issued = len(self._rewards)
        claimed = sum(1 for r in self._rewards.values() if r.status == RewardStatus.CLAIMED)
        pending = sum(1 for r in self._rewards.values() if r.status == RewardStatus.PENDING)
        sent = sum(1 for r in self._rewards.values() if r.status == RewardStatus.SENT)
        expired = sum(1 for r in self._rewards.values() if r.status == RewardStatus.EXPIRED)

        claim_rate = (claimed / total_issued * 100) if total_issued > 0 else 0

        return {
            "total_issued": total_issued,
            "claimed": claimed,
            "pending": pending,
            "sent": sent,
            "expired": expired,
            "claim_rate": round(claim_rate, 2),
            "active_rules": sum(1 for r in self._rules.values() if r.is_active),
            "total_customers_with_occasions": len(self._occasions),
        }


# Singleton instance
_birthday_service: Optional[BirthdayRewardsService] = None


def get_birthday_rewards_service() -> BirthdayRewardsService:
    """Get the birthday rewards service singleton."""
    global _birthday_service
    if _birthday_service is None:
        _birthday_service = BirthdayRewardsService()
    return _birthday_service

"""Dynamic Surge Pricing Service."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional, Dict, Any

from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from app.models.advanced_features import DynamicPricingRule, DynamicPriceAdjustment


class DynamicPricingService:
    """Service for demand-based dynamic pricing."""

    def __init__(self, db: Session):
        self.db = db
        self._active_adjustments: Dict[int, DynamicPriceAdjustment] = {}

    def create_rule(
        self,
        name: str,
        trigger_type: str,
        trigger_conditions: Dict[str, Any],
        adjustment_type: str,
        adjustment_value: Decimal,
        applies_to: str,
        location_id: Optional[int] = None,
        max_adjustment_percent: Optional[float] = None,
        item_ids: Optional[List[int]] = None,
        category_ids: Optional[List[int]] = None,
        is_active: bool = True,
    ) -> DynamicPricingRule:
        """Create a dynamic pricing rule."""
        rule = DynamicPricingRule(
            location_id=location_id,
            name=name,
            trigger_type=trigger_type,
            trigger_conditions=trigger_conditions,
            adjustment_type=adjustment_type,
            adjustment_value=adjustment_value,
            max_adjustment_percent=max_adjustment_percent,
            applies_to=applies_to,
            item_ids=item_ids,
            category_ids=category_ids,
            is_active=is_active,
        )
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def get_rules(
        self,
        location_id: Optional[int] = None,
        active_only: bool = True,
    ) -> List[DynamicPricingRule]:
        """Get pricing rules."""
        query = select(DynamicPricingRule)

        if location_id:
            query = query.where(
                (DynamicPricingRule.location_id == location_id) |
                (DynamicPricingRule.location_id.is_(None))
            )

        if active_only:
            query = query.where(DynamicPricingRule.is_active == True)

        result = self.db.execute(query)
        return list(result.scalars().all())

    def check_triggers(
        self,
        location_id: int,
        current_demand: float,
        current_wait_time: Optional[int] = None,
        current_weather: Optional[str] = None,
        current_inventory: Optional[Dict[int, int]] = None,
    ) -> List[DynamicPricingRule]:
        """Check which pricing rules should be triggered."""
        rules = self.get_rules(location_id=location_id)
        triggered = []

        for rule in rules:
            should_trigger = False
            conditions = rule.trigger_conditions

            if rule.trigger_type == "demand":
                threshold = conditions.get("demand_percentile", 90)
                if current_demand >= threshold:
                    should_trigger = True

            elif rule.trigger_type == "time":
                hours = conditions.get("hours", [])
                days = conditions.get("days", [])
                now = datetime.now(timezone.utc)
                if now.hour in hours and (not days or now.weekday() in days):
                    should_trigger = True

            elif rule.trigger_type == "weather":
                weather_conditions = conditions.get("weather_types", [])
                if current_weather and current_weather in weather_conditions:
                    should_trigger = True

            elif rule.trigger_type == "event":
                # Would integrate with external event API
                pass

            elif rule.trigger_type == "inventory":
                low_threshold = conditions.get("low_stock_threshold", 10)
                if current_inventory:
                    item_ids = rule.item_ids or []
                    for item_id in item_ids:
                        if current_inventory.get(item_id, 100) <= low_threshold:
                            should_trigger = True
                            break

            if should_trigger:
                triggered.append(rule)

        return triggered

    def activate_surge(
        self,
        rule_id: int,
        location_id: int,
        original_price: Decimal,
        trigger_value: Optional[str] = None,
    ) -> DynamicPriceAdjustment:
        """Activate surge pricing for a rule."""
        rule = self.db.get(DynamicPricingRule, rule_id)
        if not rule:
            raise ValueError(f"Rule {rule_id} not found")

        # Calculate adjusted price
        if rule.adjustment_type == "percentage":
            adjustment = original_price * (rule.adjustment_value / 100)
        else:
            adjustment = rule.adjustment_value

        adjusted_price = original_price + adjustment

        # Apply max adjustment cap if set
        if rule.max_adjustment_percent:
            max_price = original_price * (1 + rule.max_adjustment_percent / 100)
            adjusted_price = min(adjusted_price, max_price)

        # Create adjustment record
        adjustment = DynamicPriceAdjustment(
            rule_id=rule_id,
            location_id=location_id,
            activated_at=datetime.now(timezone.utc),
            original_price=original_price,
            adjusted_price=adjusted_price,
            trigger_value=trigger_value,
        )
        self.db.add(adjustment)
        self.db.commit()
        self.db.refresh(adjustment)

        # Track active adjustment
        self._active_adjustments[rule_id] = adjustment

        return adjustment

    def deactivate_surge(
        self,
        adjustment_id: int,
    ) -> DynamicPriceAdjustment:
        """Deactivate surge pricing."""
        adjustment = self.db.get(DynamicPriceAdjustment, adjustment_id)
        if not adjustment:
            raise ValueError(f"Adjustment {adjustment_id} not found")

        adjustment.deactivated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(adjustment)

        # Remove from active tracking
        if adjustment.rule_id in self._active_adjustments:
            del self._active_adjustments[adjustment.rule_id]

        return adjustment

    def record_surge_order(
        self,
        adjustment_id: int,
        revenue_added: Decimal,
    ) -> None:
        """Record an order during surge pricing."""
        adjustment = self.db.get(DynamicPriceAdjustment, adjustment_id)
        if adjustment:
            adjustment.orders_during_surge += 1
            adjustment.additional_revenue += revenue_added
            self.db.commit()

    def get_current_price(
        self,
        item_id: int,
        base_price: Decimal,
        location_id: int,
    ) -> Dict[str, Any]:
        """Get current price for an item considering surge pricing."""
        rules = self.get_rules(location_id=location_id)

        active_rule = None
        for rule in rules:
            if rule.id in self._active_adjustments:
                if rule.applies_to == "all":
                    active_rule = rule
                    break
                elif rule.applies_to == "item" and item_id in (rule.item_ids or []):
                    active_rule = rule
                    break
                # Would also check category_ids

        if not active_rule:
            return {
                "is_surge": False,
                "base_price": base_price,
                "current_price": base_price,
                "adjustment_percent": 0,
            }

        adjustment = self._active_adjustments[active_rule.id]

        # Calculate adjustment for this specific item
        if active_rule.adjustment_type == "percentage":
            current_price = base_price * (1 + active_rule.adjustment_value / 100)
            adjustment_percent = float(active_rule.adjustment_value)
        else:
            current_price = base_price + active_rule.adjustment_value
            adjustment_percent = float((active_rule.adjustment_value / base_price) * 100)

        return {
            "is_surge": True,
            "base_price": base_price,
            "current_price": current_price,
            "adjustment_percent": adjustment_percent,
            "rule_id": active_rule.id,
            "rule_name": active_rule.name,
        }

    def get_surge_status(
        self,
        location_id: int,
    ) -> Dict[str, Any]:
        """Get current surge pricing status for a location."""
        active_rules = []
        total_multiplier = 1.0
        affected_items = set()

        rules = self.get_rules(location_id=location_id)

        for rule in rules:
            if rule.id in self._active_adjustments:
                adjustment = self._active_adjustments[rule.id]
                active_rules.append(rule.id)

                if rule.adjustment_type == "percentage":
                    total_multiplier *= (1 + float(rule.adjustment_value) / 100)

                if rule.item_ids:
                    affected_items.update(rule.item_ids)

        return {
            "is_surge_active": len(active_rules) > 0,
            "active_rules": active_rules,
            "current_multiplier": total_multiplier,
            "affected_items": list(affected_items),
            "estimated_end_time": None,  # Would calculate based on historical patterns
        }

    def get_surge_history(
        self,
        location_id: int,
        days: int = 7,
    ) -> Dict[str, Any]:
        """Get surge pricing history and analytics."""
        start_date = datetime.now(timezone.utc) - timedelta(days=days)

        query = select(
            func.count(DynamicPriceAdjustment.id).label("total_surges"),
            func.sum(DynamicPriceAdjustment.orders_during_surge).label("total_orders"),
            func.sum(DynamicPriceAdjustment.additional_revenue).label("total_revenue"),
        ).where(
            and_(
                DynamicPriceAdjustment.location_id == location_id,
                DynamicPriceAdjustment.activated_at >= start_date,
            )
        )

        result = self.db.execute(query)
        stats = result.first()

        return {
            "period_days": days,
            "total_surge_events": stats.total_surges or 0,
            "orders_during_surge": stats.total_orders or 0,
            "additional_revenue": float(stats.total_revenue or 0),
        }

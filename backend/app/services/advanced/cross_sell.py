"""AI Cross-Sell Engine Service."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any

from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from app.models.advanced_features import CrossSellRule, CrossSellImpression


class CrossSellService:
    """Service for AI-powered cross-sell and upsell recommendations."""

    def __init__(self, db: Session):
        self.db = db

    def create_rule(
        self,
        name: str,
        rule_type: str,
        recommend_product_ids: List[int],
        display_position: str,
        location_id: Optional[int] = None,
        trigger_product_ids: Optional[List[int]] = None,
        trigger_category_ids: Optional[List[int]] = None,
        trigger_cart_minimum: Optional[Decimal] = None,
        recommendation_message: Optional[str] = None,
        priority: int = 1,
    ) -> CrossSellRule:
        """Create a cross-sell rule."""
        rule = CrossSellRule(
            location_id=location_id,
            name=name,
            rule_type=rule_type,
            trigger_product_ids=trigger_product_ids,
            trigger_category_ids=trigger_category_ids,
            trigger_cart_minimum=trigger_cart_minimum,
            recommend_product_ids=recommend_product_ids,
            recommendation_message=recommendation_message,
            display_position=display_position,
            priority=priority,
            is_active=True,
        )
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def get_rules(
        self,
        location_id: Optional[int] = None,
        active_only: bool = True,
    ) -> List[CrossSellRule]:
        """Get cross-sell rules."""
        query = select(CrossSellRule)

        if location_id:
            query = query.where(
                (CrossSellRule.location_id == location_id) |
                (CrossSellRule.location_id.is_(None))
            )

        if active_only:
            query = query.where(CrossSellRule.is_active == True)

        query = query.order_by(CrossSellRule.priority)

        result = self.db.execute(query)
        return list(result.scalars().all())

    def get_recommendations(
        self,
        cart_items: List[int],
        cart_total: Decimal,
        customer_id: Optional[int] = None,
        location_id: Optional[int] = None,
        position: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get cross-sell recommendations based on cart."""
        rules = self.get_rules(location_id=location_id)
        triggered_rules = []
        recommendations = []
        seen_products = set(cart_items)

        for rule in rules:
            if position and rule.display_position != position:
                continue

            should_trigger = False

            # Check triggers
            if rule.trigger_product_ids:
                if any(item in rule.trigger_product_ids for item in cart_items):
                    should_trigger = True

            if rule.trigger_cart_minimum and cart_total >= rule.trigger_cart_minimum:
                should_trigger = True

            if rule.rule_type == "ai_recommendation":
                # AI-based recommendations would go here
                should_trigger = True

            if should_trigger:
                triggered_rules.append(rule.id)

                for product_id in rule.recommend_product_ids:
                    if product_id not in seen_products:
                        recommendations.append({
                            "product_id": product_id,
                            "rule_id": rule.id,
                            "message": rule.recommendation_message,
                            "priority": rule.priority,
                        })
                        seen_products.add(product_id)

        # Sort by priority and limit
        recommendations.sort(key=lambda x: x["priority"])
        recommendations = recommendations[:5]  # Top 5 recommendations

        return {
            "recommendations": recommendations,
            "rule_ids_triggered": triggered_rules,
        }

    def record_impression(
        self,
        rule_id: int,
        order_id: int,
        recommended_product_id: int,
    ) -> CrossSellImpression:
        """Record a cross-sell impression."""
        impression = CrossSellImpression(
            rule_id=rule_id,
            order_id=order_id,
            recommended_product_id=recommended_product_id,
            shown_at=datetime.utcnow(),
        )
        self.db.add(impression)

        # Update rule impressions count
        rule = self.db.get(CrossSellRule, rule_id)
        if rule:
            rule.impressions += 1

        self.db.commit()
        self.db.refresh(impression)
        return impression

    def record_conversion(
        self,
        impression_id: int,
        added_product_id: int,
        revenue: Decimal,
    ) -> CrossSellImpression:
        """Record a conversion from a cross-sell impression."""
        impression = self.db.get(CrossSellImpression, impression_id)
        if not impression:
            raise ValueError(f"Impression {impression_id} not found")

        impression.converted = True
        impression.converted_at = datetime.utcnow()
        impression.added_product_id = added_product_id
        impression.revenue = revenue

        # Update rule conversion count
        rule = self.db.get(CrossSellRule, impression.rule_id)
        if rule:
            rule.conversions += 1
            rule.revenue_generated += revenue

        self.db.commit()
        self.db.refresh(impression)
        return impression

    def get_performance(
        self,
        location_id: Optional[int] = None,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Get cross-sell performance statistics."""
        start_date = datetime.utcnow() - timedelta(days=days)

        # Build base query
        rules_query = select(CrossSellRule)
        if location_id:
            rules_query = rules_query.where(
                (CrossSellRule.location_id == location_id) |
                (CrossSellRule.location_id.is_(None))
            )

        rules_result = self.db.execute(rules_query)
        rules = list(rules_result.scalars().all())

        total_impressions = sum(r.impressions for r in rules)
        total_conversions = sum(r.conversions for r in rules)
        total_revenue = sum(r.revenue_generated for r in rules)

        conversion_rate = (total_conversions / total_impressions * 100) if total_impressions > 0 else 0
        avg_revenue = (total_revenue / total_conversions) if total_conversions > 0 else Decimal("0")

        # Top performing rules
        top_rules = sorted(rules, key=lambda r: r.revenue_generated, reverse=True)[:5]

        return {
            "period_days": days,
            "total_impressions": total_impressions,
            "total_conversions": total_conversions,
            "conversion_rate": conversion_rate,
            "total_revenue": float(total_revenue),
            "avg_revenue_per_conversion": float(avg_revenue),
            "top_performing_rules": [
                {
                    "id": r.id,
                    "name": r.name,
                    "impressions": r.impressions,
                    "conversions": r.conversions,
                    "revenue": float(r.revenue_generated),
                    "conversion_rate": (r.conversions / r.impressions * 100) if r.impressions > 0 else 0,
                }
                for r in top_rules
            ],
        }

    def update_rule(
        self,
        rule_id: int,
        **updates,
    ) -> CrossSellRule:
        """Update a cross-sell rule."""
        rule = self.db.get(CrossSellRule, rule_id)
        if not rule:
            raise ValueError(f"Rule {rule_id} not found")

        for key, value in updates.items():
            if hasattr(rule, key) and key not in ["id", "impressions", "conversions", "revenue_generated"]:
                setattr(rule, key, value)

        self.db.commit()
        self.db.refresh(rule)
        return rule

    def deactivate_rule(
        self,
        rule_id: int,
    ) -> CrossSellRule:
        """Deactivate a cross-sell rule."""
        rule = self.db.get(CrossSellRule, rule_id)
        if not rule:
            raise ValueError(f"Rule {rule_id} not found")

        rule.is_active = False
        self.db.commit()
        self.db.refresh(rule)
        return rule

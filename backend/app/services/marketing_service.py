"""AI Marketing Automation Service - SpotOn style."""

import os
import random
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models.marketing import (
    MarketingCampaign, CampaignRecipient, CustomerSegment,
    AutomatedTrigger, MenuRecommendation, LoyaltyProgram, CustomerLoyalty,
    CampaignStatus, CampaignType, TriggerType
)
from app.models.pos import PosSalesLine
from app.services.communication_service import EmailService, SMSService


class MarketingAutomationService:
    """AI-powered marketing automation - SpotOn Marketing Assist style."""

    def __init__(self, db: Session):
        self.db = db
        self.email_service = EmailService()
        self.sms_service = SMSService()

    async def create_ai_campaign(
        self,
        campaign_type: CampaignType,
        goal: str,
        target_segment: str = "all",
        schedule_at: Optional[datetime] = None
    ) -> MarketingCampaign:
        """Create an AI-generated marketing campaign."""
        # Generate campaign content based on goal
        content = self._generate_campaign_content(campaign_type, goal)

        campaign = MarketingCampaign(
            name=content["name"],
            description=f"AI-generated campaign: {goal}",
            campaign_type=campaign_type,
            trigger_type=TriggerType.SCHEDULED if schedule_at else TriggerType.MANUAL,
            status=CampaignStatus.DRAFT,
            scheduled_at=schedule_at,
            subject_line=content["subject"],
            content_html=content["html"],
            content_text=content["text"],
            ai_generated=True,
            target_segment=target_segment,
            offer_type=content.get("offer_type"),
            offer_value=content.get("offer_value"),
            offer_code=content.get("offer_code")
        )

        self.db.add(campaign)
        self.db.commit()

        return campaign

    def _generate_campaign_content(
        self,
        campaign_type: CampaignType,
        goal: str
    ) -> Dict[str, Any]:
        """Generate campaign content using AI/templates."""
        # Template-based content generation
        # In production, this would use an LLM API

        templates = {
            "win_back": {
                "name": "We Miss You! Come Back Special",
                "subject": "It's been a while - here's 15% off your next visit",
                "html": """
                    <div style="font-family: Arial; max-width: 600px; margin: 0 auto;">
                        <h1 style="color: #2563eb;">We've Missed You!</h1>
                        <p>It's been a while since your last visit, and we'd love to see you again.</p>
                        <p>As a thank you for being a valued customer, enjoy <strong>15% off</strong> your next order!</p>
                        <div style="background: #f0f9ff; padding: 20px; border-radius: 8px; text-align: center;">
                            <p style="font-size: 24px; font-weight: bold; color: #2563eb;">COMEBACK15</p>
                            <p>Use this code at checkout</p>
                        </div>
                        <p style="margin-top: 20px;">Valid for the next 14 days. We can't wait to serve you again!</p>
                    </div>
                """,
                "text": "We've missed you! Use code COMEBACK15 for 15% off your next order. Valid for 14 days.",
                "offer_type": "discount_percent",
                "offer_value": 15,
                "offer_code": "COMEBACK15"
            },
            "birthday": {
                "name": "Birthday Celebration Special",
                "subject": "Happy Birthday! A special gift from us 🎂",
                "html": """
                    <div style="font-family: Arial; max-width: 600px; margin: 0 auto;">
                        <h1 style="color: #2563eb;">Happy Birthday! 🎉</h1>
                        <p>Wishing you a wonderful birthday filled with joy!</p>
                        <p>As our gift to you, enjoy a <strong>FREE dessert</strong> on your birthday!</p>
                        <div style="background: #fef3c7; padding: 20px; border-radius: 8px; text-align: center;">
                            <p style="font-size: 24px; font-weight: bold; color: #d97706;">BDAY2024</p>
                            <p>Show this code to your server</p>
                        </div>
                        <p style="margin-top: 20px;">Valid within 7 days of your birthday.</p>
                    </div>
                """,
                "text": "Happy Birthday! Enjoy a FREE dessert with code BDAY2024. Valid within 7 days of your birthday.",
                "offer_type": "free_item",
                "offer_code": "BDAY2024"
            },
            "promotion": {
                "name": "Limited Time Offer",
                "subject": "Don't Miss Out - Special Offer Inside!",
                "html": """
                    <div style="font-family: Arial; max-width: 600px; margin: 0 auto;">
                        <h1 style="color: #2563eb;">Special Offer Just For You!</h1>
                        <p>For a limited time, enjoy special savings at our restaurant.</p>
                        <div style="background: #dcfce7; padding: 20px; border-radius: 8px; text-align: center;">
                            <p style="font-size: 24px; font-weight: bold; color: #16a34a;">20% OFF</p>
                            <p>Your entire order</p>
                        </div>
                        <p style="margin-top: 20px;">Use code <strong>SPECIAL20</strong> at checkout. Expires in 7 days!</p>
                    </div>
                """,
                "text": "Special offer! 20% off your entire order with code SPECIAL20. Expires in 7 days!",
                "offer_type": "discount_percent",
                "offer_value": 20,
                "offer_code": "SPECIAL20"
            }
        }

        # Match goal to template
        if "win" in goal.lower() or "lapsed" in goal.lower() or "back" in goal.lower():
            return templates["win_back"]
        elif "birthday" in goal.lower():
            return templates["birthday"]
        else:
            return templates["promotion"]

    async def send_campaign(
        self,
        campaign_id: int,
        test_mode: bool = False,
        test_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send a marketing campaign to recipients."""
        campaign = self.db.query(MarketingCampaign).filter(
            MarketingCampaign.id == campaign_id
        ).first()

        if not campaign:
            return {"error": "Campaign not found"}

        if test_mode:
            # Send to test email only
            if test_email:
                result = self.email_service.send_marketing_email(
                    to_email=test_email,
                    campaign_name=campaign.name,
                    subject=campaign.subject_line,
                    body_html=campaign.content_html,
                    unsubscribe_link="https://example.com/unsubscribe"
                )
                return {"test_sent": True, "result": result}
            return {"error": "Test email required"}

        # Get recipients based on segment
        recipients = self._get_segment_recipients(campaign.target_segment)

        sent_count = 0
        failed_count = 0

        for recipient in recipients:
            try:
                # Create recipient record
                campaign_recipient = CampaignRecipient(
                    campaign_id=campaign.id,
                    customer_id=recipient.get("customer_id"),
                    email=recipient.get("email"),
                    phone=recipient.get("phone")
                )
                self.db.add(campaign_recipient)
                self.db.flush()

                # Send based on campaign type
                if campaign.campaign_type in [CampaignType.EMAIL, CampaignType.MULTI_CHANNEL]:
                    if recipient.get("email"):
                        self.email_service.send_marketing_email(
                            to_email=recipient["email"],
                            campaign_name=campaign.name,
                            subject=campaign.subject_line,
                            body_html=campaign.content_html,
                            unsubscribe_link=f"https://example.com/unsubscribe/{campaign_recipient.id}"
                        )
                        campaign_recipient.sent_at = datetime.utcnow()

                if campaign.campaign_type in [CampaignType.SMS, CampaignType.MULTI_CHANNEL]:
                    if recipient.get("phone"):
                        await self.sms_service.send_marketing_sms(
                            to_number=recipient["phone"],
                            message=campaign.content_text
                        )
                        campaign_recipient.sent_at = datetime.utcnow()

                sent_count += 1

            except Exception as e:
                campaign_recipient.error_message = str(e)
                failed_count += 1

        # Update campaign stats
        campaign.status = CampaignStatus.ACTIVE
        campaign.started_at = datetime.utcnow()
        campaign.total_sent = sent_count

        self.db.commit()

        return {
            "campaign_id": campaign.id,
            "sent": sent_count,
            "failed": failed_count,
            "status": "active"
        }

    def _get_segment_recipients(self, segment: str) -> List[Dict[str, Any]]:
        """Get recipients for a segment."""
        # This would integrate with customer database
        # For now, return placeholder
        return []


class AutomatedTriggerService:
    """Manage automated marketing triggers."""

    def __init__(self, db: Session):
        self.db = db
        self.marketing_service = MarketingAutomationService(db)

    async def process_triggers(self) -> Dict[str, Any]:
        """Process all active automated triggers."""
        triggers = self.db.query(AutomatedTrigger).filter(
            AutomatedTrigger.is_active == True
        ).all()

        results = {}

        for trigger in triggers:
            try:
                triggered_count = await self._process_trigger(trigger)
                results[trigger.name] = {"triggered": triggered_count}
            except Exception as e:
                results[trigger.name] = {"error": str(e)}

        return results

    async def _process_trigger(self, trigger: AutomatedTrigger) -> int:
        """Process a single trigger."""
        triggered = 0

        if trigger.trigger_type == TriggerType.BIRTHDAY:
            triggered = await self._process_birthday_trigger(trigger)
        elif trigger.trigger_type == TriggerType.WIN_BACK:
            triggered = await self._process_winback_trigger(trigger)
        elif trigger.trigger_type == TriggerType.LOYALTY_MILESTONE:
            triggered = await self._process_loyalty_trigger(trigger)

        trigger.total_triggered += triggered
        self.db.commit()

        return triggered

    async def _process_birthday_trigger(self, trigger: AutomatedTrigger) -> int:
        """Send birthday emails/SMS."""
        today = datetime.utcnow().date()
        send_days = trigger.send_days_before or 0

        target_date = today + timedelta(days=send_days)

        # Find customers with birthdays
        customers = self.db.query(CustomerLoyalty).filter(
            func.extract('month', CustomerLoyalty.birthday) == target_date.month,
            func.extract('day', CustomerLoyalty.birthday) == target_date.day
        ).all()

        # Send birthday campaign
        for customer in customers:
            # Would send personalized birthday message
            pass

        return len(customers)

    async def _process_winback_trigger(self, trigger: AutomatedTrigger) -> int:
        """Send win-back campaigns to lapsed customers."""
        threshold_date = datetime.utcnow() - timedelta(days=trigger.days_threshold or 30)

        # Find customers who haven't visited since threshold
        lapsed = self.db.query(CustomerLoyalty).filter(
            CustomerLoyalty.last_visit_at < threshold_date,
            CustomerLoyalty.last_visit_at.isnot(None)
        ).all()

        # Send win-back campaign
        for customer in lapsed:
            # Would send personalized win-back message
            pass

        return len(lapsed)

    async def _process_loyalty_trigger(self, trigger: AutomatedTrigger) -> int:
        """Send loyalty milestone rewards."""
        if not trigger.amount_threshold:
            return 0

        # Find customers who reached milestone
        milestone = self.db.query(CustomerLoyalty).filter(
            CustomerLoyalty.lifetime_points >= trigger.amount_threshold
        ).all()

        # Send milestone notification
        for customer in milestone:
            # Would send milestone celebration
            pass

        return len(milestone)


class MenuRecommendationService:
    """AI-powered menu recommendations - 'Picked for You' style."""

    def __init__(self, db: Session):
        self.db = db

    def get_recommendations(
        self,
        customer_id: Optional[int] = None,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Get personalized menu recommendations."""
        now = datetime.utcnow()
        day_of_week = now.weekday()
        hour = now.hour

        recommendations = []

        # Get top selling items for this time
        time_based = self._get_time_based_recommendations(day_of_week, hour)
        recommendations.extend(time_based)

        # Get customer-specific recommendations
        if customer_id:
            customer_recs = self._get_customer_recommendations(customer_id)
            recommendations.extend(customer_recs)

        # Deduplicate and score
        seen_ids = set()
        unique_recs = []
        for rec in recommendations:
            if rec["product_id"] not in seen_ids:
                seen_ids.add(rec["product_id"])
                unique_recs.append(rec)

        # Sort by score and return top 5
        unique_recs.sort(key=lambda x: x.get("score", 0), reverse=True)

        # Save recommendation for tracking
        if unique_recs:
            menu_rec = MenuRecommendation(
                customer_id=customer_id,
                session_id=session_id,
                day_of_week=day_of_week,
                hour_of_day=hour,
                is_weekend=day_of_week >= 5,
                recommended_items=unique_recs[:5],
                items_shown=[r["product_id"] for r in unique_recs[:5]]
            )
            self.db.add(menu_rec)
            self.db.commit()

        return unique_recs[:5]

    def _get_time_based_recommendations(
        self,
        day_of_week: int,
        hour: int
    ) -> List[Dict[str, Any]]:
        """Get recommendations based on time patterns."""
        # Query most ordered items at this time
        from app.models.product import Product

        # Get top items from sales
        # This would analyze historical sales data
        # For now, return top products

        products = self.db.query(Product).filter(
            Product.is_active == True
        ).limit(10).all()

        return [
            {
                "product_id": p.id,
                "name": p.name,
                "score": 0.8,
                "reason": "popular_at_time"
            }
            for p in products
        ]

    def _get_customer_recommendations(
        self,
        customer_id: int
    ) -> List[Dict[str, Any]]:
        """Get recommendations based on customer history."""
        loyalty = self.db.query(CustomerLoyalty).filter(
            CustomerLoyalty.customer_id == customer_id
        ).first()

        if loyalty and loyalty.favorite_items:
            return [
                {
                    "product_id": item_id,
                    "score": 0.95,
                    "reason": "frequently_ordered"
                }
                for item_id in loyalty.favorite_items[:5]
            ]

        return []

    def record_conversion(
        self,
        recommendation_id: int,
        ordered_items: List[int]
    ) -> None:
        """Record which recommended items were ordered."""
        rec = self.db.query(MenuRecommendation).filter(
            MenuRecommendation.id == recommendation_id
        ).first()

        if rec:
            rec.items_ordered = ordered_items

            # Calculate conversion rate
            if rec.items_shown:
                ordered_set = set(ordered_items)
                shown_set = set(rec.items_shown)
                conversions = len(ordered_set.intersection(shown_set))
                rec.conversion_rate = conversions / len(rec.items_shown)

            self.db.commit()


class LoyaltyService:
    """Manage customer loyalty program."""

    def __init__(self, db: Session):
        self.db = db

    def add_points(
        self,
        customer_id: int,
        points: int,
        reason: str = "purchase"
    ) -> CustomerLoyalty:
        """Add points to customer account."""
        loyalty = self.db.query(CustomerLoyalty).filter(
            CustomerLoyalty.customer_id == customer_id
        ).first()

        if not loyalty:
            loyalty = CustomerLoyalty(customer_id=customer_id)
            self.db.add(loyalty)

        loyalty.current_points += points
        loyalty.lifetime_points += points

        self.db.commit()
        return loyalty

    def redeem_points(
        self,
        customer_id: int,
        points: int
    ) -> Dict[str, Any]:
        """Redeem points from customer account."""
        loyalty = self.db.query(CustomerLoyalty).filter(
            CustomerLoyalty.customer_id == customer_id
        ).first()

        if not loyalty:
            return {"error": "Customer not found"}

        if loyalty.current_points < points:
            return {"error": "Insufficient points"}

        loyalty.current_points -= points
        loyalty.redeemed_points += points

        # Get program for conversion
        program = self.db.query(LoyaltyProgram).filter(
            LoyaltyProgram.is_active == True
        ).first()

        reward_value = 0
        if program:
            reward_value = points * program.points_to_dollar

        self.db.commit()

        return {
            "redeemed": points,
            "reward_value": reward_value,
            "remaining_points": loyalty.current_points
        }

    def record_visit(
        self,
        customer_id: int,
        spend_amount: float,
        items_ordered: Optional[List[int]] = None
    ) -> CustomerLoyalty:
        """Record a customer visit."""
        loyalty = self.db.query(CustomerLoyalty).filter(
            CustomerLoyalty.customer_id == customer_id
        ).first()

        if not loyalty:
            loyalty = CustomerLoyalty(
                customer_id=customer_id,
                first_visit_at=datetime.utcnow()
            )
            self.db.add(loyalty)

        loyalty.total_visits += 1
        loyalty.total_spend += spend_amount
        loyalty.last_visit_at = datetime.utcnow()

        # Update favorite items
        if items_ordered:
            if not loyalty.favorite_items:
                loyalty.favorite_items = []

            # Track frequency
            item_freq = {}
            for item in loyalty.favorite_items:
                item_freq[item] = item_freq.get(item, 0) + 1
            for item in items_ordered:
                item_freq[item] = item_freq.get(item, 0) + 1

            # Sort by frequency and keep top 10
            sorted_items = sorted(item_freq.keys(), key=lambda x: item_freq[x], reverse=True)
            loyalty.favorite_items = sorted_items[:10]

        # Add points based on spend
        program = self.db.query(LoyaltyProgram).filter(
            LoyaltyProgram.is_active == True
        ).first()

        if program:
            points = int(spend_amount * program.points_per_dollar)
            loyalty.current_points += points
            loyalty.lifetime_points += points

            # Update tier
            loyalty.current_tier = self._calculate_tier(loyalty.lifetime_points, program)

        self.db.commit()
        return loyalty

    def _calculate_tier(self, points: int, program: LoyaltyProgram) -> str:
        """Calculate loyalty tier based on points."""
        if not program.tiers:
            return "Member"

        current_tier = "Member"
        for tier in sorted(program.tiers, key=lambda x: x.get("min_points", 0)):
            if points >= tier.get("min_points", 0):
                current_tier = tier.get("name", "Member")

        return current_tier

    def get_customer_status(self, customer_id: int) -> Dict[str, Any]:
        """Get customer loyalty status."""
        loyalty = self.db.query(CustomerLoyalty).filter(
            CustomerLoyalty.customer_id == customer_id
        ).first()

        if not loyalty:
            return {"error": "Customer not found"}

        program = self.db.query(LoyaltyProgram).filter(
            LoyaltyProgram.is_active == True
        ).first()

        reward_value = 0
        if program and loyalty.current_points >= program.min_redemption:
            reward_value = loyalty.current_points * program.points_to_dollar

        return {
            "customer_id": customer_id,
            "current_points": loyalty.current_points,
            "lifetime_points": loyalty.lifetime_points,
            "tier": loyalty.current_tier,
            "total_visits": loyalty.total_visits,
            "total_spend": loyalty.total_spend,
            "available_reward_value": reward_value,
            "member_since": loyalty.first_visit_at
        }

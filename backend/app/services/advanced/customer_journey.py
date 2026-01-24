"""Customer Journey Analytics Service."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any

from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from app.models.advanced_features import CustomerJourneyEvent, CustomerJourneyFunnel


class CustomerJourneyService:
    """Service for customer journey analytics."""

    def __init__(self, db: Session):
        self.db = db

    def track_event(
        self,
        session_id: str,
        event_type: str,
        channel: str,
        customer_id: Optional[int] = None,
        location_id: Optional[int] = None,
        event_data: Optional[Dict[str, Any]] = None,
        utm_source: Optional[str] = None,
        utm_medium: Optional[str] = None,
        utm_campaign: Optional[str] = None,
        device_type: Optional[str] = None,
        browser: Optional[str] = None,
    ) -> CustomerJourneyEvent:
        """Track a customer journey event."""
        event = CustomerJourneyEvent(
            customer_id=customer_id,
            session_id=session_id,
            location_id=location_id,
            event_type=event_type,
            event_data=event_data,
            channel=channel,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            device_type=device_type,
            browser=browser,
            timestamp=datetime.utcnow(),
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def get_session_events(
        self,
        session_id: str,
    ) -> List[CustomerJourneyEvent]:
        """Get all events for a session."""
        query = select(CustomerJourneyEvent).where(
            CustomerJourneyEvent.session_id == session_id
        ).order_by(CustomerJourneyEvent.timestamp)

        result = self.db.execute(query)
        return list(result.scalars().all())

    def get_customer_journey(
        self,
        customer_id: int,
        days: int = 30,
    ) -> List[CustomerJourneyEvent]:
        """Get journey events for a customer."""
        start_date = datetime.utcnow() - timedelta(days=days)

        query = select(CustomerJourneyEvent).where(
            and_(
                CustomerJourneyEvent.customer_id == customer_id,
                CustomerJourneyEvent.timestamp >= start_date,
            )
        ).order_by(CustomerJourneyEvent.timestamp)

        result = self.db.execute(query)
        return list(result.scalars().all())

    def calculate_funnel(
        self,
        location_id: Optional[int],
        date_val: date,
        channel: str,
    ) -> CustomerJourneyFunnel:
        """Calculate funnel metrics for a day."""
        start = datetime.combine(date_val, datetime.min.time())
        end = datetime.combine(date_val, datetime.max.time())

        # Build base filter
        base_filter = and_(
            CustomerJourneyEvent.timestamp >= start,
            CustomerJourneyEvent.timestamp <= end,
            CustomerJourneyEvent.channel == channel,
        )
        if location_id:
            base_filter = and_(base_filter, CustomerJourneyEvent.location_id == location_id)

        # Count unique sessions for each stage
        stages = {
            "sessions": None,  # Any event
            "menu_views": "menu_view",
            "item_views": "item_view",
            "add_to_carts": "add_to_cart",
            "checkout_starts": "checkout_start",
            "orders_placed": "order_placed",
        }

        counts = {}
        for stage, event_type in stages.items():
            query = select(
                func.count(func.distinct(CustomerJourneyEvent.session_id))
            ).where(base_filter)

            if event_type:
                query = query.where(CustomerJourneyEvent.event_type == event_type)

            result = self.db.execute(query)
            counts[stage] = result.scalar() or 0

        # Calculate revenue
        revenue_query = select(
            func.sum(CustomerJourneyEvent.event_data["order_total"].cast(Decimal))
        ).where(
            and_(
                base_filter,
                CustomerJourneyEvent.event_type == "order_placed",
            )
        )
        revenue_result = self.db.execute(revenue_query)
        total_revenue = revenue_result.scalar() or Decimal("0")

        # Calculate rates
        sessions = counts["sessions"]
        menu_to_item = (counts["item_views"] / counts["menu_views"] * 100) if counts["menu_views"] > 0 else None
        cart_rate = (counts["add_to_carts"] / counts["item_views"] * 100) if counts["item_views"] > 0 else None
        checkout_rate = (counts["checkout_starts"] / counts["add_to_carts"] * 100) if counts["add_to_carts"] > 0 else None
        conversion_rate = (counts["orders_placed"] / sessions * 100) if sessions > 0 else None
        avg_order_value = (total_revenue / counts["orders_placed"]) if counts["orders_placed"] > 0 else None

        # Check for existing funnel record
        existing_query = select(CustomerJourneyFunnel).where(
            and_(
                CustomerJourneyFunnel.location_id == location_id,
                CustomerJourneyFunnel.date == date_val,
                CustomerJourneyFunnel.channel == channel,
            )
        )
        existing_result = self.db.execute(existing_query)
        funnel = existing_result.scalar_one_or_none()

        if funnel:
            # Update existing
            funnel.sessions = counts["sessions"]
            funnel.menu_views = counts["menu_views"]
            funnel.item_views = counts["item_views"]
            funnel.add_to_carts = counts["add_to_carts"]
            funnel.checkout_starts = counts["checkout_starts"]
            funnel.orders_placed = counts["orders_placed"]
            funnel.menu_to_item_rate = menu_to_item
            funnel.cart_rate = cart_rate
            funnel.checkout_rate = checkout_rate
            funnel.conversion_rate = conversion_rate
            funnel.total_revenue = total_revenue
            funnel.avg_order_value = avg_order_value
        else:
            # Create new
            funnel = CustomerJourneyFunnel(
                location_id=location_id,
                date=date_val,
                channel=channel,
                sessions=counts["sessions"],
                menu_views=counts["menu_views"],
                item_views=counts["item_views"],
                add_to_carts=counts["add_to_carts"],
                checkout_starts=counts["checkout_starts"],
                orders_placed=counts["orders_placed"],
                menu_to_item_rate=menu_to_item,
                cart_rate=cart_rate,
                checkout_rate=checkout_rate,
                conversion_rate=conversion_rate,
                total_revenue=total_revenue,
                avg_order_value=avg_order_value,
            )
            self.db.add(funnel)

        self.db.commit()
        self.db.refresh(funnel)
        return funnel

    def get_funnel_analysis(
        self,
        location_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        channel: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get funnel analysis for a period."""
        if start_date is None:
            start_date = date.today() - timedelta(days=30)
        if end_date is None:
            end_date = date.today()

        query = select(CustomerJourneyFunnel).where(
            and_(
                CustomerJourneyFunnel.date >= start_date,
                CustomerJourneyFunnel.date <= end_date,
            )
        )

        if location_id:
            query = query.where(CustomerJourneyFunnel.location_id == location_id)
        if channel:
            query = query.where(CustomerJourneyFunnel.channel == channel)

        result = self.db.execute(query)
        funnels = list(result.scalars().all())

        if not funnels:
            return {
                "date_range": {"start": start_date.isoformat(), "end": end_date.isoformat()},
                "total_sessions": 0,
                "total_conversions": 0,
                "overall_conversion_rate": 0,
                "by_channel": {},
                "drop_off_points": [],
                "recommendations": ["Not enough data to analyze"],
            }

        # Aggregate by channel
        by_channel = {}
        total_sessions = 0
        total_conversions = 0

        for funnel in funnels:
            ch = funnel.channel
            if ch not in by_channel:
                by_channel[ch] = {
                    "sessions": 0,
                    "menu_views": 0,
                    "item_views": 0,
                    "add_to_carts": 0,
                    "checkout_starts": 0,
                    "orders_placed": 0,
                    "revenue": Decimal("0"),
                }

            by_channel[ch]["sessions"] += funnel.sessions
            by_channel[ch]["menu_views"] += funnel.menu_views
            by_channel[ch]["item_views"] += funnel.item_views
            by_channel[ch]["add_to_carts"] += funnel.add_to_carts
            by_channel[ch]["checkout_starts"] += funnel.checkout_starts
            by_channel[ch]["orders_placed"] += funnel.orders_placed
            by_channel[ch]["revenue"] += funnel.total_revenue

            total_sessions += funnel.sessions
            total_conversions += funnel.orders_placed

        # Calculate conversion rates by channel
        for ch, data in by_channel.items():
            data["conversion_rate"] = (data["orders_placed"] / data["sessions"] * 100) if data["sessions"] > 0 else 0
            data["revenue"] = float(data["revenue"])

        # Identify drop-off points
        total_stages = {
            "menu_views": sum(d["menu_views"] for d in by_channel.values()),
            "item_views": sum(d["item_views"] for d in by_channel.values()),
            "add_to_carts": sum(d["add_to_carts"] for d in by_channel.values()),
            "checkout_starts": sum(d["checkout_starts"] for d in by_channel.values()),
            "orders_placed": sum(d["orders_placed"] for d in by_channel.values()),
        }

        drop_offs = []
        stages = list(total_stages.keys())
        for i in range(len(stages) - 1):
            current = total_stages[stages[i]]
            next_stage = total_stages[stages[i + 1]]
            if current > 0:
                drop_rate = (1 - next_stage / current) * 100
                drop_offs.append({
                    "from": stages[i],
                    "to": stages[i + 1],
                    "drop_rate": drop_rate,
                })

        # Sort by drop rate
        drop_offs.sort(key=lambda x: x["drop_rate"], reverse=True)

        # Generate recommendations
        recommendations = []
        if drop_offs:
            worst = drop_offs[0]
            if worst["from"] == "menu_views" and worst["drop_rate"] > 50:
                recommendations.append("Consider improving menu layout and item visibility")
            if worst["from"] == "add_to_carts" and worst["drop_rate"] > 70:
                recommendations.append("Simplify the checkout process to reduce abandonment")
            if worst["from"] == "checkout_starts" and worst["drop_rate"] > 30:
                recommendations.append("Review payment options and checkout flow")

        return {
            "date_range": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "total_sessions": total_sessions,
            "total_conversions": total_conversions,
            "overall_conversion_rate": (total_conversions / total_sessions * 100) if total_sessions > 0 else 0,
            "by_channel": by_channel,
            "drop_off_points": drop_offs[:3],
            "recommendations": recommendations or ["Performance looks good!"],
        }

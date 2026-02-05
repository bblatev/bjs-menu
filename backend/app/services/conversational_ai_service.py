"""Conversational AI Analytics Service - Lightspeed AI style."""

import re
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, text

from app.models.analytics import ConversationalQuery, DailyMetrics, MenuAnalysis
from app.models.pos import PosSalesLine
from app.models.product import Product


class ConversationalAIService:
    """
    Handle natural language queries about business data.
    Lightspeed AI-style conversational analytics.
    """

    def __init__(self, db: Session):
        self.db = db
        self.conversation_context: Dict[str, Any] = {}

    async def process_query(
        self,
        query_text: str,
        user_id: Optional[int] = None,
        location_id: Optional[int] = None,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process a natural language query and return results."""
        start_time = datetime.now(timezone.utc)

        # Parse the query to understand intent
        intent, entities = self._parse_query(query_text)

        # Generate response based on intent
        response_text, response_data = await self._generate_response(
            intent, entities, location_id, conversation_id
        )

        # Calculate processing time
        processing_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

        # Serialize entities for JSON storage (convert datetime objects to strings)
        serializable_entities = self._serialize_entities(entities)

        # Log the query
        query_log = ConversationalQuery(
            user_id=user_id,
            location_id=location_id,
            query_text=query_text,
            query_intent=intent,
            extracted_entities=serializable_entities,
            response_text=response_text,
            response_data=response_data,
            conversation_id=conversation_id,
            processing_time_ms=processing_time
        )
        self.db.add(query_log)
        self.db.commit()

        return {
            "query": query_text,
            "intent": intent,
            "response": response_text,
            "data": response_data,
            "query_id": query_log.id,
            "conversation_id": conversation_id,
            "processing_time_ms": processing_time
        }

    def _serialize_entities(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Convert datetime objects in entities to ISO format strings for JSON serialization."""
        result = {}
        for key, value in entities.items():
            if isinstance(value, dict):
                result[key] = {
                    k: v.isoformat() if isinstance(v, datetime) else v
                    for k, v in value.items()
                }
            elif isinstance(value, datetime):
                result[key] = value.isoformat()
            else:
                result[key] = value
        return result

    def _parse_query(self, query_text: str) -> Tuple[str, Dict[str, Any]]:
        """Parse query to extract intent and entities."""
        query_lower = query_text.lower()
        entities = {}

        # Date/time extraction
        date_range = self._extract_date_range(query_lower)
        if date_range:
            entities["date_range"] = date_range

        # Product extraction
        product = self._extract_product(query_lower)
        if product:
            entities["product"] = product

        # Metric extraction
        metric = self._extract_metric(query_lower)
        if metric:
            entities["metric"] = metric

        # Intent classification
        intent = self._classify_intent(query_lower)

        return intent, entities

    def _extract_date_range(self, query: str) -> Optional[Dict[str, datetime]]:
        """Extract date range from query."""
        now = datetime.now(timezone.utc)

        patterns = {
            "today": (now.replace(hour=0, minute=0, second=0), now),
            "yesterday": (
                (now - timedelta(days=1)).replace(hour=0, minute=0, second=0),
                now.replace(hour=0, minute=0, second=0)
            ),
            "this week": (
                now - timedelta(days=now.weekday()),
                now
            ),
            "last week": (
                now - timedelta(days=now.weekday() + 7),
                now - timedelta(days=now.weekday())
            ),
            "this month": (
                now.replace(day=1, hour=0, minute=0, second=0),
                now
            ),
            "last month": (
                (now.replace(day=1) - timedelta(days=1)).replace(day=1),
                now.replace(day=1)
            ),
            "last 7 days": (now - timedelta(days=7), now),
            "last 30 days": (now - timedelta(days=30), now),
            "last 90 days": (now - timedelta(days=90), now),
        }

        for pattern, dates in patterns.items():
            if pattern in query:
                return {"start": dates[0], "end": dates[1], "label": pattern}

        # Try to extract specific day (e.g., "last Tuesday")
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        for i, day in enumerate(days):
            if f"last {day}" in query:
                days_ago = (now.weekday() - i) % 7
                if days_ago == 0:
                    days_ago = 7
                target = now - timedelta(days=days_ago)
                return {
                    "start": target.replace(hour=0, minute=0, second=0),
                    "end": target.replace(hour=23, minute=59, second=59),
                    "label": f"last {day}"
                }

        return None

    def _extract_product(self, query: str) -> Optional[Dict[str, Any]]:
        """Extract product references from query."""
        # Get all products for matching
        products = self.db.query(Product).all()

        for product in products:
            if product.name and product.name.lower() in query:
                return {"id": product.id, "name": product.name}

        return None

    def _extract_metric(self, query: str) -> Optional[str]:
        """Extract metric type from query."""
        metrics_map = {
            "revenue": ["revenue", "sales", "money", "income", "earnings"],
            "orders": ["orders", "transactions", "tickets"],
            "covers": ["covers", "guests", "customers", "diners"],
            "average_ticket": ["average ticket", "avg ticket", "ticket size", "check average"],
            "tips": ["tips", "gratuity"],
            "profit": ["profit", "margin", "profitability"],
            "cost": ["cost", "expenses", "food cost"],
            "items_sold": ["items sold", "quantity", "units"]
        }

        for metric, keywords in metrics_map.items():
            for keyword in keywords:
                if keyword in query:
                    return metric

        return "revenue"  # Default to revenue

    def _classify_intent(self, query: str) -> str:
        """Classify the intent of the query."""
        intents = {
            "sales_inquiry": ["how much", "what was", "total", "revenue", "sales"],
            "comparison": ["compare", "versus", "vs", "difference", "compared to"],
            "ranking": ["top", "best", "worst", "most", "least", "popular"],
            "trend": ["trend", "growing", "declining", "over time", "history"],
            "forecast": ["forecast", "predict", "projection", "expected", "will be"],
            "performance": ["performance", "how did", "doing"],
            "item_inquiry": ["what item", "which product", "which menu"],
            "staff_inquiry": ["who", "which server", "staff", "employee"]
        }

        for intent, keywords in intents.items():
            for keyword in keywords:
                if keyword in query:
                    return intent

        return "general_inquiry"

    async def _generate_response(
        self,
        intent: str,
        entities: Dict[str, Any],
        location_id: Optional[int],
        conversation_id: Optional[str]
    ) -> Tuple[str, Dict[str, Any]]:
        """Generate response based on intent and entities."""
        handlers = {
            "sales_inquiry": self._handle_sales_inquiry,
            "comparison": self._handle_comparison,
            "ranking": self._handle_ranking,
            "trend": self._handle_trend,
            "performance": self._handle_performance,
            "item_inquiry": self._handle_item_inquiry,
        }

        handler = handlers.get(intent, self._handle_general_inquiry)
        return await handler(entities, location_id)

    async def _handle_sales_inquiry(
        self,
        entities: Dict[str, Any],
        location_id: Optional[int]
    ) -> Tuple[str, Dict[str, Any]]:
        """Handle sales-related queries."""
        date_range = entities.get("date_range", {})
        start = date_range.get("start", datetime.now(timezone.utc) - timedelta(days=1))
        end = date_range.get("end", datetime.now(timezone.utc))
        label = date_range.get("label", "the selected period")

        metric = entities.get("metric", "revenue")
        product = entities.get("product")

        # Build query
        query = self.db.query(
            func.count(PosSalesLine.id).label("order_count"),
            func.sum(PosSalesLine.qty).label("total_items")
        ).filter(
            PosSalesLine.ts >= start,
            PosSalesLine.ts <= end,
            PosSalesLine.is_refund == False
        )

        if location_id:
            query = query.filter(PosSalesLine.location_id == location_id)

        if product:
            query = query.filter(PosSalesLine.item_id == product["id"])

        result = query.first()

        # Format response
        order_count = result.order_count or 0
        total_items = result.total_items or 0

        if product:
            response = f"For {label}, {product['name']} had {order_count} orders with {total_items} items sold."
        else:
            response = f"For {label}, there were {order_count} orders with {total_items} total items sold."

        data = {
            "period": {"start": start.isoformat(), "end": end.isoformat()},
            "orders": order_count,
            "items_sold": total_items,
            "product": product
        }

        return response, data

    async def _handle_comparison(
        self,
        entities: Dict[str, Any],
        location_id: Optional[int]
    ) -> Tuple[str, Dict[str, Any]]:
        """Handle comparison queries."""
        # Compare current period to previous
        date_range = entities.get("date_range", {})
        end = date_range.get("end", datetime.now(timezone.utc))
        start = date_range.get("start", end - timedelta(days=7))

        duration = end - start
        prev_end = start
        prev_start = prev_end - duration

        # Current period
        current = self.db.query(
            func.count(PosSalesLine.id)
        ).filter(
            PosSalesLine.ts >= start,
            PosSalesLine.ts <= end,
            PosSalesLine.is_refund == False
        ).scalar() or 0

        # Previous period
        previous = self.db.query(
            func.count(PosSalesLine.id)
        ).filter(
            PosSalesLine.ts >= prev_start,
            PosSalesLine.ts <= prev_end,
            PosSalesLine.is_refund == False
        ).scalar() or 0

        change = ((current - previous) / previous * 100) if previous > 0 else 0
        direction = "up" if change > 0 else "down" if change < 0 else "flat"

        response = f"Orders are {direction} {abs(change):.1f}% compared to the previous period ({current} vs {previous})."

        data = {
            "current_period": {"orders": current},
            "previous_period": {"orders": previous},
            "change_percent": change
        }

        return response, data

    async def _handle_ranking(
        self,
        entities: Dict[str, Any],
        location_id: Optional[int]
    ) -> Tuple[str, Dict[str, Any]]:
        """Handle ranking queries (top/best items)."""
        date_range = entities.get("date_range", {})
        start = date_range.get("start", datetime.now(timezone.utc) - timedelta(days=30))
        end = date_range.get("end", datetime.now(timezone.utc))

        # Get top items
        top_items = self.db.query(
            PosSalesLine.item_name,
            func.sum(PosSalesLine.qty).label("total_qty"),
            func.count(PosSalesLine.id).label("order_count")
        ).filter(
            PosSalesLine.ts >= start,
            PosSalesLine.ts <= end,
            PosSalesLine.is_refund == False
        ).group_by(
            PosSalesLine.item_name
        ).order_by(
            func.sum(PosSalesLine.qty).desc()
        ).limit(5).all()

        if not top_items:
            return "No sales data found for this period.", {}

        items_text = ", ".join([f"{item.item_name} ({item.total_qty} sold)" for item in top_items])
        response = f"Top selling items: {items_text}."

        data = {
            "top_items": [
                {
                    "name": item.item_name,
                    "quantity_sold": item.total_qty,
                    "order_count": item.order_count
                }
                for item in top_items
            ]
        }

        return response, data

    async def _handle_trend(
        self,
        entities: Dict[str, Any],
        location_id: Optional[int]
    ) -> Tuple[str, Dict[str, Any]]:
        """Handle trend analysis queries."""
        # Get daily metrics for trend
        days = 14
        metrics = self.db.query(DailyMetrics).filter(
            DailyMetrics.date >= datetime.now(timezone.utc) - timedelta(days=days)
        ).order_by(DailyMetrics.date).all()

        if not metrics:
            return "Not enough data for trend analysis.", {}

        # Calculate trend
        revenues = [m.total_revenue or 0 for m in metrics]
        orders = [m.total_orders or 0 for m in metrics]

        avg_revenue = sum(revenues) / len(revenues) if revenues else 0
        avg_orders = sum(orders) / len(orders) if orders else 0

        # Simple trend: compare first half to second half
        mid = len(revenues) // 2
        first_half_avg = sum(revenues[:mid]) / mid if mid > 0 else 0
        second_half_avg = sum(revenues[mid:]) / (len(revenues) - mid) if len(revenues) > mid else 0

        trend = "upward" if second_half_avg > first_half_avg else "downward" if second_half_avg < first_half_avg else "stable"

        response = f"Over the last {days} days, the trend is {trend}. Average daily revenue is ${avg_revenue:.2f} with {avg_orders:.0f} orders."

        data = {
            "period_days": days,
            "trend": trend,
            "average_daily_revenue": avg_revenue,
            "average_daily_orders": avg_orders,
            "daily_data": [
                {"date": m.date.isoformat(), "revenue": m.total_revenue, "orders": m.total_orders}
                for m in metrics
            ]
        }

        return response, data

    async def _handle_performance(
        self,
        entities: Dict[str, Any],
        location_id: Optional[int]
    ) -> Tuple[str, Dict[str, Any]]:
        """Handle performance queries."""
        # Similar to sales inquiry but with performance framing
        return await self._handle_sales_inquiry(entities, location_id)

    async def _handle_item_inquiry(
        self,
        entities: Dict[str, Any],
        location_id: Optional[int]
    ) -> Tuple[str, Dict[str, Any]]:
        """Handle item-specific queries."""
        product = entities.get("product")
        if not product:
            return "Please specify which item you'd like to know about.", {}

        # Get menu analysis
        analysis = self.db.query(MenuAnalysis).filter(
            MenuAnalysis.product_id == product["id"]
        ).order_by(MenuAnalysis.calculated_at.desc()).first()

        if analysis:
            response = (
                f"{product['name']} is classified as a '{analysis.quadrant.value}' item. "
                f"It has sold {analysis.quantity_sold} units with ${analysis.total_revenue:.2f} in revenue. "
                f"Recommendation: {analysis.recommendation_reason}"
            )
            data = {
                "product": product,
                "quadrant": analysis.quadrant.value,
                "quantity_sold": analysis.quantity_sold,
                "revenue": analysis.total_revenue,
                "recommendation": analysis.recommended_action
            }
        else:
            response = f"No analysis data available for {product['name']}."
            data = {"product": product}

        return response, data

    async def _handle_general_inquiry(
        self,
        entities: Dict[str, Any],
        location_id: Optional[int]
    ) -> Tuple[str, Dict[str, Any]]:
        """Handle general queries."""
        return (
            "I can help you with sales data, comparisons, top items, trends, and item performance. "
            "Try asking something like 'What were our total sales yesterday?' or 'What are our top selling items?'",
            {"suggestions": [
                "What were sales yesterday?",
                "What are our top 5 items this week?",
                "How do this week's sales compare to last week?",
                "What's the trend in orders over the last 14 days?"
            ]}
        )

    def get_conversation_history(
        self,
        conversation_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get conversation history for context."""
        queries = self.db.query(ConversationalQuery).filter(
            ConversationalQuery.conversation_id == conversation_id
        ).order_by(ConversationalQuery.created_at.desc()).limit(limit).all()

        return [
            {
                "query": q.query_text,
                "response": q.response_text,
                "timestamp": q.created_at.isoformat()
            }
            for q in reversed(queries)
        ]

    def provide_feedback(
        self,
        query_id: int,
        was_helpful: bool
    ) -> None:
        """Record user feedback on query response."""
        query = self.db.query(ConversationalQuery).filter(
            ConversationalQuery.id == query_id
        ).first()

        if query:
            query.was_helpful = was_helpful
            self.db.commit()

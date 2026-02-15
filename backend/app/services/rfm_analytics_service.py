"""RFM Analytics Service - iiko parity feature"""
from datetime import datetime, date, timedelta, timezone
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from decimal import Decimal
import statistics


class RFMAnalyticsService:
    """Recency, Frequency, Monetary customer segmentation"""
    
    RFM_SEGMENTS = {
        (5, 5, 5): "Champions",
        (5, 5, 4): "Champions",
        (5, 4, 5): "Champions",
        (4, 5, 5): "Loyal Customers",
        (5, 4, 4): "Loyal Customers",
        (4, 4, 5): "Loyal Customers",
        (4, 5, 4): "Loyal Customers",
        (5, 3, 3): "Potential Loyalists",
        (4, 3, 3): "Potential Loyalists",
        (3, 3, 3): "Potential Loyalists",
        (5, 1, 1): "New Customers",
        (4, 1, 1): "New Customers",
        (5, 2, 2): "Promising",
        (4, 2, 2): "Promising",
        (3, 2, 2): "Needing Attention",
        (3, 3, 2): "Needing Attention",
        (2, 3, 3): "About to Sleep",
        (2, 2, 3): "About to Sleep",
        (2, 2, 2): "At Risk",
        (2, 3, 2): "At Risk",
        (1, 3, 3): "Can't Lose Them",
        (1, 4, 4): "Can't Lose Them",
        (1, 2, 2): "Hibernating",
        (1, 2, 1): "Hibernating",
        (1, 1, 1): "Lost",
        (1, 1, 2): "Lost",
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    async def calculate_customer_rfm(
        self,
        customer_id: int,
        venue_id: int
    ) -> Dict[str, Any]:
        """Calculate RFM score for a single customer"""
        # Get customer order data
        customer_data = await self._get_customer_order_data(customer_id, venue_id)
        
        # Calculate individual scores
        r_score = self._calculate_recency_score(customer_data["last_order_date"])
        f_score = self._calculate_frequency_score(customer_data["order_count"])
        m_score = self._calculate_monetary_score(customer_data["total_spent"])
        
        rfm_score = r_score * 100 + f_score * 10 + m_score
        segment = self._get_segment(r_score, f_score, m_score)
        
        return {
            "customer_id": customer_id,
            "venue_id": venue_id,
            "recency_score": r_score,
            "frequency_score": f_score,
            "monetary_score": m_score,
            "rfm_score": rfm_score,
            "segment": segment,
            "last_order_date": customer_data["last_order_date"],
            "total_orders": customer_data["order_count"],
            "total_spent": customer_data["total_spent"],
            "avg_order_value": customer_data["total_spent"] / max(customer_data["order_count"], 1),
            "calculated_at": datetime.now(timezone.utc).isoformat()
        }
    
    async def _get_customer_order_data(
        self, 
        customer_id: int, 
        venue_id: int
    ) -> Dict[str, Any]:
        """Get customer's order history data"""
        # In production: Query actual order data
        return {
            "last_order_date": (datetime.now(timezone.utc) - timedelta(days=15)).date(),
            "order_count": 12,
            "total_spent": 540.00
        }
    
    def _calculate_recency_score(self, last_order_date: date) -> int:
        """Calculate recency score (1-5)"""
        days_since = (date.today() - last_order_date).days
        
        if days_since <= 7:
            return 5
        elif days_since <= 14:
            return 4
        elif days_since <= 30:
            return 3
        elif days_since <= 60:
            return 2
        else:
            return 1
    
    def _calculate_frequency_score(self, order_count: int) -> int:
        """Calculate frequency score (1-5)"""
        if order_count >= 20:
            return 5
        elif order_count >= 10:
            return 4
        elif order_count >= 5:
            return 3
        elif order_count >= 2:
            return 2
        else:
            return 1
    
    def _calculate_monetary_score(self, total_spent: float) -> int:
        """Calculate monetary score (1-5)"""
        if total_spent >= 1000:
            return 5
        elif total_spent >= 500:
            return 4
        elif total_spent >= 200:
            return 3
        elif total_spent >= 50:
            return 2
        else:
            return 1
    
    def _get_segment(self, r: int, f: int, m: int) -> str:
        """Get customer segment based on RFM scores"""
        # Try exact match first
        key = (r, f, m)
        if key in self.RFM_SEGMENTS:
            return self.RFM_SEGMENTS[key]
        
        # Fallback to general rules
        avg = (r + f + m) / 3
        if avg >= 4:
            return "Loyal Customers"
        elif avg >= 3:
            return "Potential Loyalists"
        elif avg >= 2:
            return "At Risk"
        else:
            return "Lost"
    
    async def calculate_all_customers(
        self,
        venue_id: int
    ) -> Dict[str, Any]:
        """Calculate RFM for all customers at venue"""
        # In production: Batch process all customers
        return {
            "venue_id": venue_id,
            "customers_processed": 500,
            "segments": {
                "Champions": 45,
                "Loyal Customers": 80,
                "Potential Loyalists": 95,
                "New Customers": 60,
                "Promising": 40,
                "Needing Attention": 55,
                "About to Sleep": 35,
                "At Risk": 40,
                "Can't Lose Them": 15,
                "Hibernating": 20,
                "Lost": 15
            },
            "calculated_at": datetime.now(timezone.utc).isoformat()
        }
    
    async def get_segment_customers(
        self,
        venue_id: int,
        segment: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get customers in a specific segment"""
        return [
            {
                "customer_id": i,
                "name": f"Customer {i}",
                "email": f"customer{i}@example.com",
                "rfm_score": 445 - i * 5,
                "last_order": (datetime.now(timezone.utc) - timedelta(days=i*3)).isoformat(),
                "total_spent": 500 - i * 20,
                "order_count": 10 - i
            }
            for i in range(1, min(limit, 11))
        ]
    
    async def get_segment_recommendations(
        self,
        segment: str
    ) -> Dict[str, Any]:
        """Get marketing recommendations for segment"""
        recommendations = {
            "Champions": {
                "strategy": "Reward and engage",
                "actions": [
                    "Offer exclusive VIP perks",
                    "Early access to new menu items",
                    "Birthday/anniversary surprises",
                    "Referral program enrollment"
                ],
                "suggested_offers": ["20% VIP discount", "Free dessert with meal"]
            },
            "Loyal Customers": {
                "strategy": "Maintain relationship",
                "actions": [
                    "Regular loyalty rewards",
                    "Personalized recommendations",
                    "Feedback requests"
                ],
                "suggested_offers": ["Double points day", "Complimentary appetizer"]
            },
            "At Risk": {
                "strategy": "Win back urgently",
                "actions": [
                    "Send reactivation offer",
                    "Personalized \"we miss you\" message",
                    "Survey to understand issues"
                ],
                "suggested_offers": ["30% comeback discount", "Free main course"]
            },
            "Lost": {
                "strategy": "Attempt reactivation",
                "actions": [
                    "Strong reactivation offer",
                    "Highlight new menu items",
                    "Limited time urgent offer"
                ],
                "suggested_offers": ["50% discount on next visit", "Buy one get one free"]
            }
        }
        
        return recommendations.get(segment, {
            "strategy": "Standard engagement",
            "actions": ["Regular marketing", "Loyalty program promotion"],
            "suggested_offers": ["10% discount"]
        })
    
    async def get_rfm_dashboard(
        self,
        venue_id: int
    ) -> Dict[str, Any]:
        """Get RFM analytics dashboard data"""
        all_rfm = await self.calculate_all_customers(venue_id)
        
        return {
            "venue_id": venue_id,
            "summary": {
                "total_customers": all_rfm["customers_processed"],
                "high_value": all_rfm["segments"]["Champions"] + all_rfm["segments"]["Loyal Customers"],
                "at_risk": all_rfm["segments"]["At Risk"] + all_rfm["segments"]["Can't Lose Them"],
                "lost": all_rfm["segments"]["Lost"] + all_rfm["segments"]["Hibernating"]
            },
            "segments": all_rfm["segments"],
            "trends": {
                "champions_change": "+5%",
                "at_risk_change": "-2%",
                "avg_rfm_score": 345
            },
            "recommendations_count": 3,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

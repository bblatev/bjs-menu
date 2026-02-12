"""Customer Engagement V5 Service - VIP Management, Guestbook, Menu Reviews, Fundraising"""
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from decimal import Decimal
import secrets


class CustomerEngagementV5Service:
    """Enhanced customer engagement features"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ==================== VIP MANAGEMENT ====================
    
    async def create_vip_profile(
        self,
        customer_id: int,
        venue_id: int,
        vip_tier: str = "silver",
        preferences: Optional[Dict] = None,
        special_occasions: Optional[List[Dict]] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create VIP profile for customer"""
        vip = {
            "id": secrets.randbelow(10000) + 1,
            "customer_id": customer_id,
            "venue_id": venue_id,
            "vip_tier": vip_tier,
            "vip_since": date.today().isoformat(),
            "preferences": preferences or {},
            "special_occasions": special_occasions or [],
            "notes": notes,
            "lifetime_spend": 0,
            "visit_count": 0,
            "is_active": True,
            "created_at": datetime.utcnow().isoformat()
        }
        return vip
    
    async def update_vip_tier(
        self,
        customer_id: int,
        new_tier: str
    ) -> Dict[str, Any]:
        """Update VIP tier"""
        tiers = ["silver", "gold", "platinum", "diamond"]
        if new_tier not in tiers:
            raise ValueError(f"Invalid tier. Must be one of: {tiers}")
        
        return {
            "customer_id": customer_id,
            "previous_tier": "silver",
            "new_tier": new_tier,
            "updated_at": datetime.utcnow().isoformat()
        }
    
    async def get_vip_profile(self, customer_id: int) -> Optional[Dict[str, Any]]:
        """Get VIP profile"""
        return {
            "id": 1,
            "customer_id": customer_id,
            "customer_name": "John VIP",
            "vip_tier": "gold",
            "vip_since": "2024-01-15",
            "preferences": {
                "seating": "booth by window",
                "dietary": ["no nuts"],
                "favorite_drinks": ["Old Fashioned", "Cabernet"],
                "temperature": "warm side"
            },
            "special_occasions": [
                {"type": "birthday", "date": "1985-06-15"},
                {"type": "anniversary", "date": "2020-09-22"}
            ],
            "favorite_items": ["Ribeye Steak", "Caesar Salad", "Tiramisu"],
            "notes": "Prefers quiet tables. Always ask about his golf game.",
            "lifetime_spend": 12500.00,
            "visit_count": 85,
            "last_visit": "2025-12-20",
            "assigned_server": "Maria",
            "is_active": True
        }
    
    async def get_upcoming_vip_occasions(
        self,
        venue_id: int,
        days_ahead: int = 30
    ) -> List[Dict[str, Any]]:
        """Get upcoming VIP special occasions"""
        return [
            {
                "customer_id": 1,
                "customer_name": "John VIP",
                "occasion": "birthday",
                "date": (date.today() + timedelta(days=5)).isoformat(),
                "vip_tier": "gold",
                "suggested_action": "Complimentary dessert and birthday message"
            },
            {
                "customer_id": 2,
                "customer_name": "Sarah Elite",
                "occasion": "anniversary",
                "date": (date.today() + timedelta(days=12)).isoformat(),
                "vip_tier": "platinum",
                "suggested_action": "Champagne and flowers at table"
            }
        ]
    
    async def get_vip_list(
        self,
        venue_id: int,
        tier: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get list of VIP customers"""
        vips = [
            {"id": 1, "name": "Diamond VIP", "tier": "diamond", "spend": 50000, "visits": 200},
            {"id": 2, "name": "Platinum VIP", "tier": "platinum", "spend": 25000, "visits": 120},
            {"id": 3, "name": "Gold VIP 1", "tier": "gold", "spend": 12000, "visits": 80},
            {"id": 4, "name": "Gold VIP 2", "tier": "gold", "spend": 10000, "visits": 65},
            {"id": 5, "name": "Silver VIP", "tier": "silver", "spend": 5000, "visits": 40},
        ]
        
        if tier:
            vips = [v for v in vips if v["tier"] == tier]
        
        return vips
    
    # ==================== GUESTBOOK ====================
    
    async def create_guestbook_entry(
        self,
        venue_id: int,
        visit_date: datetime,
        customer_id: Optional[int] = None,
        party_size: Optional[int] = None,
        occasion: Optional[str] = None,
        table_number: Optional[int] = None,
        server_id: Optional[int] = None,
        host_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create guestbook entry for visit"""
        entry = {
            "id": secrets.randbelow(10000) + 1,
            "venue_id": venue_id,
            "customer_id": customer_id,
            "visit_date": visit_date.isoformat(),
            "party_size": party_size,
            "occasion": occasion,
            "table_number": table_number,
            "server_id": server_id,
            "host_notes": host_notes,
            "created_at": datetime.utcnow().isoformat()
        }
        return entry
    
    async def add_visit_feedback(
        self,
        entry_id: int,
        rating: int,
        comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add feedback to guestbook entry"""
        return {
            "entry_id": entry_id,
            "feedback_rating": rating,
            "feedback_comment": comment,
            "feedback_at": datetime.utcnow().isoformat()
        }
    
    async def get_customer_visit_history(
        self,
        customer_id: int,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get customer's visit history"""
        return [
            {
                "visit_date": (datetime.utcnow() - timedelta(days=i*7)).isoformat(),
                "party_size": 2 + (i % 3),
                "table_number": 5 + i,
                "server": "Maria",
                "order_total": 85.50 + i * 10,
                "occasion": "dinner" if i % 2 == 0 else None,
                "feedback_rating": 5 if i < 3 else 4
            }
            for i in range(min(limit, 10))
        ]
    
    async def get_guestbook_notes_for_reservation(
        self,
        customer_id: int
    ) -> Dict[str, Any]:
        """Get relevant notes for upcoming reservation"""
        vip = await self.get_vip_profile(customer_id)
        history = await self.get_customer_visit_history(customer_id, limit=5)
        
        return {
            "customer_id": customer_id,
            "is_vip": vip is not None,
            "vip_tier": vip["vip_tier"] if vip else None,
            "preferences": vip["preferences"] if vip else {},
            "last_visit": history[0]["visit_date"] if history else None,
            "visit_count": len(history),
            "avg_spend": sum(h["order_total"] for h in history) / len(history) if history else 0,
            "special_notes": vip["notes"] if vip else None,
            "favorite_items": vip["favorite_items"] if vip else [],
            "upcoming_occasions": []
        }
    
    # ==================== MENU ITEM REVIEWS ====================
    
    async def submit_menu_review(
        self,
        menu_item_id: int,
        rating: int,  # 1 (thumbs down) or 5 (thumbs up) for thumbs, 1-5 for stars
        order_id: Optional[int] = None,
        customer_id: Optional[int] = None,
        comment: Optional[str] = None,
        review_type: str = "thumbs"
    ) -> Dict[str, Any]:
        """Submit a menu item review"""
        review = {
            "id": secrets.randbelow(10000) + 1,
            "menu_item_id": menu_item_id,
            "order_id": order_id,
            "customer_id": customer_id,
            "rating": rating,
            "review_type": review_type,
            "comment": comment,
            "is_verified_purchase": order_id is not None,
            "is_published": True,
            "created_at": datetime.utcnow().isoformat()
        }
        return review
    
    async def get_item_reviews(
        self,
        menu_item_id: int,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Get reviews for a menu item"""
        return {
            "menu_item_id": menu_item_id,
            "total_reviews": 45,
            "avg_rating": 4.2,
            "thumbs_up_pct": 85,
            "rating_distribution": {
                "5": 25,
                "4": 12,
                "3": 5,
                "2": 2,
                "1": 1
            },
            "recent_reviews": [
                {
                    "rating": 5,
                    "comment": "Best burger I've had!",
                    "created_at": (datetime.utcnow() - timedelta(days=1)).isoformat()
                },
                {
                    "rating": 4,
                    "comment": "Great flavor, portion could be bigger",
                    "created_at": (datetime.utcnow() - timedelta(days=3)).isoformat()
                }
            ]
        }
    
    async def get_menu_review_summary(
        self,
        venue_id: int
    ) -> Dict[str, Any]:
        """Get overall menu review summary"""
        return {
            "venue_id": venue_id,
            "total_reviews": 1250,
            "avg_rating": 4.3,
            "reviews_this_month": 85,
            "top_rated_items": [
                {"item": "Ribeye Steak", "rating": 4.8, "reviews": 120},
                {"item": "Truffle Pasta", "rating": 4.7, "reviews": 95},
                {"item": "Tiramisu", "rating": 4.6, "reviews": 80}
            ],
            "lowest_rated_items": [
                {"item": "House Salad", "rating": 3.2, "reviews": 45},
                {"item": "Fish Tacos", "rating": 3.5, "reviews": 30}
            ],
            "improvement_suggestions": [
                "House Salad: Consider fresher ingredients",
                "Fish Tacos: Review portion size"
            ]
        }
    
    # ==================== FUNDRAISING / ROUND-UP ====================
    
    async def create_charity_campaign(
        self,
        venue_id: int,
        charity_name: str,
        charity_description: Optional[str] = None,
        campaign_start: date = None,
        campaign_end: Optional[date] = None,
        goal_amount: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """Create a charity fundraising campaign"""
        campaign = {
            "id": secrets.randbelow(10000) + 1,
            "venue_id": venue_id,
            "charity_name": charity_name,
            "charity_description": charity_description,
            "campaign_start": (campaign_start or date.today()).isoformat(),
            "campaign_end": campaign_end.isoformat() if campaign_end else None,
            "goal_amount": float(goal_amount) if goal_amount else None,
            "total_raised": 0,
            "donation_count": 0,
            "is_active": True,
            "round_up_enabled": True,
            "flat_donation_amounts": [1, 2, 5, 10],
            "created_at": datetime.utcnow().isoformat()
        }
        return campaign
    
    async def process_round_up_donation(
        self,
        campaign_id: int,
        order_id: int,
        original_total: Decimal,
        customer_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Process round-up donation"""
        import math
        rounded_total = Decimal(math.ceil(float(original_total)))
        donation_amount = rounded_total - original_total
        
        if donation_amount <= 0:
            donation_amount = Decimal("1.00")
            rounded_total = original_total + donation_amount
        
        donation = {
            "id": secrets.randbelow(10000) + 1,
            "campaign_id": campaign_id,
            "order_id": order_id,
            "customer_id": customer_id,
            "amount": float(donation_amount),
            "donation_type": "round_up",
            "original_total": float(original_total),
            "rounded_total": float(rounded_total),
            "created_at": datetime.utcnow().isoformat()
        }
        return donation
    
    async def process_flat_donation(
        self,
        campaign_id: int,
        amount: Decimal,
        order_id: Optional[int] = None,
        customer_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Process flat amount donation"""
        donation = {
            "id": secrets.randbelow(10000) + 1,
            "campaign_id": campaign_id,
            "order_id": order_id,
            "customer_id": customer_id,
            "amount": float(amount),
            "donation_type": "flat",
            "created_at": datetime.utcnow().isoformat()
        }
        return donation
    
    async def get_campaign_stats(
        self,
        campaign_id: int
    ) -> Dict[str, Any]:
        """Get charity campaign statistics"""
        return {
            "campaign_id": campaign_id,
            "charity_name": "Local Food Bank",
            "total_raised": 2350.75,
            "goal_amount": 5000.00,
            "progress_pct": 47.0,
            "donation_count": 425,
            "avg_donation": 5.53,
            "round_up_donations": 380,
            "flat_donations": 45,
            "top_donation": 50.00,
            "days_active": 45,
            "donations_today": 12,
            "raised_today": 65.25
        }
    
    async def get_active_campaigns(
        self,
        venue_id: int
    ) -> List[Dict[str, Any]]:
        """Get active charity campaigns"""
        return [
            {
                "id": 1,
                "charity_name": "Local Food Bank",
                "total_raised": 2350.75,
                "goal_amount": 5000.00,
                "progress_pct": 47.0,
                "campaign_end": (date.today() + timedelta(days=30)).isoformat()
            }
        ]

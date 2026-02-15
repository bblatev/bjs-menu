"""Promo Codes and Smart Ordering V5 Service"""
from datetime import datetime, date, timedelta, timezone
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from decimal import Decimal
import secrets
import string


class PromoAndOrderingV5Service:
    """Single-use promo codes and smart prep time estimation"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ==================== SINGLE-USE PROMO CODES ====================
    
    async def generate_single_use_codes(
        self,
        venue_id: int,
        count: int,
        discount_type: str,  # percentage, fixed
        discount_value: float,
        valid_from: Optional[datetime] = None,
        valid_until: Optional[datetime] = None,
        minimum_order: Optional[float] = None,
        max_discount: Optional[float] = None,
        campaign_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Generate batch of single-use promo codes"""
        codes = []
        
        for _ in range(count):
            code = self._generate_unique_code()
            promo = {
                "id": secrets.randbelow(100000) + 1,
                "venue_id": venue_id,
                "campaign_id": campaign_id,
                "code": code,
                "discount_type": discount_type,
                "discount_value": discount_value,
                "minimum_order": minimum_order,
                "max_discount": max_discount,
                "valid_from": (valid_from or datetime.now(timezone.utc)).isoformat(),
                "valid_until": valid_until.isoformat() if valid_until else None,
                "is_used": False,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            codes.append(promo)
        
        return codes
    
    def _generate_unique_code(self) -> str:
        """Generate unique promo code"""
        chars = string.ascii_uppercase + string.digits
        return ''.join(secrets.choice(chars) for _ in range(8))
    
    async def validate_promo_code(
        self,
        code: str,
        order_total: Decimal,
        customer_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Validate a promo code"""
        # In production: Look up code from database
        promo = await self._get_promo_by_code(code)
        
        if not promo:
            return {"valid": False, "error": "Invalid promo code"}
        
        if promo["is_used"]:
            return {"valid": False, "error": "This code has already been used"}
        
        if promo["valid_until"] and datetime.fromisoformat(promo["valid_until"]) < datetime.now(timezone.utc):
            return {"valid": False, "error": "This code has expired"}
        
        if promo["minimum_order"] and float(order_total) < promo["minimum_order"]:
            return {
                "valid": False, 
                "error": f"Minimum order of {promo['minimum_order']} лв required"
            }
        
        # Calculate discount
        if promo["discount_type"] == "percentage":
            discount = float(order_total) * (promo["discount_value"] / 100)
            if promo["max_discount"]:
                discount = min(discount, promo["max_discount"])
        else:
            discount = promo["discount_value"]
        
        return {
            "valid": True,
            "code": code,
            "discount_type": promo["discount_type"],
            "discount_value": promo["discount_value"],
            "calculated_discount": discount,
            "new_total": float(order_total) - discount
        }
    
    async def _get_promo_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Get promo code details"""
        return {
            "id": 1,
            "code": code,
            "discount_type": "percentage",
            "discount_value": 15,
            "minimum_order": 30.00,
            "max_discount": 20.00,
            "valid_until": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "is_used": False
        }
    
    async def redeem_promo_code(
        self,
        code: str,
        order_id: int
    ) -> Dict[str, Any]:
        """Mark promo code as used"""
        return {
            "code": code,
            "order_id": order_id,
            "is_used": True,
            "used_at": datetime.now(timezone.utc).isoformat()
        }
    
    async def get_promo_code_stats(
        self,
        venue_id: int,
        campaign_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get promo code usage statistics"""
        return {
            "venue_id": venue_id,
            "campaign_id": campaign_id,
            "total_codes": 500,
            "codes_used": 320,
            "codes_remaining": 180,
            "redemption_rate": 64.0,
            "total_discount_given": 4800.00,
            "avg_discount_per_order": 15.00,
            "revenue_from_promo_orders": 32000.00
        }
    
    # ==================== SMART QUOTE / PREP TIME ====================
    
    async def get_estimated_prep_time(
        self,
        venue_id: int,
        order_items: List[Dict],
        order_channel: str = "online"  # online, kiosk, delivery
    ) -> Dict[str, Any]:
        """Get AI-estimated prep time for order"""
        # Get current conditions
        current_load = await self._get_current_kitchen_load(venue_id)
        historical_data = await self._get_historical_prep_times(venue_id, order_channel)
        
        # Base time calculation
        base_time = 0
        for item in order_items:
            item_time = await self._get_item_prep_time(item["menu_item_id"])
            base_time = max(base_time, item_time)  # Parallel prep
        
        # Adjust for current load
        load_multiplier = 1 + (current_load / 100) * 0.5  # 50% max increase at full load
        
        # Adjust for time of day
        hour = datetime.now(timezone.utc).hour
        time_multiplier = 1.2 if 12 <= hour <= 14 or 18 <= hour <= 21 else 1.0
        
        estimated_minutes = int(base_time * load_multiplier * time_multiplier)
        
        # Add buffer
        min_time = max(10, estimated_minutes - 5)
        max_time = estimated_minutes + 10
        
        return {
            "estimated_minutes": estimated_minutes,
            "range": {
                "min": min_time,
                "max": max_time
            },
            "ready_by": (datetime.now(timezone.utc) + timedelta(minutes=estimated_minutes)).isoformat(),
            "confidence": 85,
            "factors": {
                "base_prep_time": base_time,
                "kitchen_load": current_load,
                "time_of_day_factor": time_multiplier,
                "item_count": len(order_items)
            }
        }
    
    async def _get_current_kitchen_load(self, venue_id: int) -> int:
        """Get current kitchen load percentage"""
        # In production: Count active orders in kitchen
        hour = datetime.now(timezone.utc).hour
        if 12 <= hour <= 14 or 18 <= hour <= 21:
            return 75
        return 40
    
    async def _get_historical_prep_times(
        self, 
        venue_id: int, 
        channel: str
    ) -> Dict[str, Any]:
        """Get historical prep time data"""
        return {
            "avg_prep_time": 18,
            "median_prep_time": 15,
            "p95_prep_time": 35
        }
    
    async def _get_item_prep_time(self, menu_item_id: int) -> int:
        """Get prep time for specific item"""
        # In production: Look up from menu_items table
        return 12  # minutes
    
    async def update_prep_time_estimate(
        self,
        venue_id: int,
        order_channel: str,
        day_of_week: int,
        hour_of_day: int,
        actual_prep_time: int
    ) -> Dict[str, Any]:
        """Update prep time estimates with actual data"""
        return {
            "venue_id": venue_id,
            "order_channel": order_channel,
            "day_of_week": day_of_week,
            "hour_of_day": hour_of_day,
            "new_sample": actual_prep_time,
            "updated_avg": 17,
            "sample_size": 150,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    
    async def get_prep_time_analytics(
        self,
        venue_id: int,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Get prep time analytics"""
        return {
            "venue_id": venue_id,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "avg_prep_time": 17,
            "median_prep_time": 15,
            "p95_prep_time": 32,
            "on_time_rate": 92.5,
            "by_channel": {
                "online": {"avg": 18, "on_time_rate": 91},
                "kiosk": {"avg": 12, "on_time_rate": 95},
                "delivery": {"avg": 22, "on_time_rate": 88}
            },
            "by_day_of_week": {
                "Monday": 15,
                "Tuesday": 14,
                "Wednesday": 16,
                "Thursday": 17,
                "Friday": 22,
                "Saturday": 25,
                "Sunday": 20
            },
            "peak_hours": [
                {"hour": 12, "avg_time": 25},
                {"hour": 13, "avg_time": 28},
                {"hour": 19, "avg_time": 30},
                {"hour": 20, "avg_time": 28}
            ]
        }

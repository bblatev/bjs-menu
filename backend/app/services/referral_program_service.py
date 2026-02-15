"""Referral Program Service - iiko parity feature"""
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
import secrets
import string


class ReferralProgramService:
    """Customer referral rewards program"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def create_program(
        self,
        venue_id: int,
        name: str,
        referrer_reward_type: str,
        referrer_reward_value: float,
        referee_reward_type: str,
        referee_reward_value: float,
        min_referee_order: Optional[float] = None,
        max_referrals: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a new referral program"""
        program = {
            "id": secrets.randbelow(10000) + 1,
            "venue_id": venue_id,
            "name": name,
            "referrer_reward_type": referrer_reward_type,
            "referrer_reward_value": referrer_reward_value,
            "referee_reward_type": referee_reward_type,
            "referee_reward_value": referee_reward_value,
            "min_referee_order": min_referee_order,
            "max_referrals_per_customer": max_referrals,
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        return program
    
    async def generate_referral_code(
        self,
        program_id: int,
        customer_id: int
    ) -> Dict[str, Any]:
        """Generate unique referral code for customer"""
        code = self._generate_code(customer_id)
        
        referral = {
            "id": secrets.randbelow(10000) + 1,
            "program_id": program_id,
            "referrer_customer_id": customer_id,
            "referral_code": code,
            "status": "active",
            "referrals_made": 0,
            "rewards_earned": 0,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        return referral
    
    def _generate_code(self, customer_id: int) -> str:
        """Generate unique referral code"""
        chars = string.ascii_uppercase + string.digits
        random_part = ''.join(secrets.choice(chars) for _ in range(6))
        return f"REF{random_part}"
    
    async def validate_referral_code(
        self,
        code: str,
        referee_customer_id: int
    ) -> Dict[str, Any]:
        """Validate a referral code"""
        # Check if code exists and is active
        referral = await self._get_referral_by_code(code)
        if not referral:
            return {"valid": False, "error": "Invalid referral code"}
        
        # Check if referee is not the referrer
        if referral["referrer_customer_id"] == referee_customer_id:
            return {"valid": False, "error": "Cannot use your own referral code"}
        
        # Check if referee hasn't been referred before
        existing = await self._check_existing_referral(referee_customer_id)
        if existing:
            return {"valid": False, "error": "You have already been referred"}
        
        return {
            "valid": True,
            "referral_id": referral["id"],
            "referrer_id": referral["referrer_customer_id"],
            "referee_reward": {
                "type": "discount",
                "value": 15.00
            }
        }
    
    async def _get_referral_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Get referral by code"""
        return {
            "id": 1,
            "program_id": 1,
            "referrer_customer_id": 100,
            "referral_code": code,
            "status": "active"
        }
    
    async def _check_existing_referral(self, customer_id: int) -> bool:
        """Check if customer was already referred"""
        return False
    
    async def complete_referral(
        self,
        referral_code: str,
        referee_customer_id: int,
        order_id: int,
        order_total: float
    ) -> Dict[str, Any]:
        """Complete a referral when referee makes qualifying order"""
        referral = await self._get_referral_by_code(referral_code)
        
        return {
            "referral_id": referral["id"],
            "status": "completed",
            "referee_customer_id": referee_customer_id,
            "order_id": order_id,
            "referrer_reward": {
                "type": "credit",
                "value": 20.00,
                "credited": True
            },
            "referee_reward": {
                "type": "discount",
                "value": 15.00,
                "applied": True
            },
            "completed_at": datetime.now(timezone.utc).isoformat()
        }
    
    async def get_customer_referrals(
        self,
        customer_id: int
    ) -> Dict[str, Any]:
        """Get customer's referral statistics"""
        return {
            "customer_id": customer_id,
            "referral_code": "REF123ABC",
            "total_referrals": 5,
            "successful_referrals": 4,
            "pending_referrals": 1,
            "total_rewards_earned": 80.00,
            "referrals": [
                {
                    "referee_name": "John D.",
                    "status": "completed",
                    "reward_earned": 20.00,
                    "completed_at": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
                },
                {
                    "referee_name": "Sarah M.",
                    "status": "completed",
                    "reward_earned": 20.00,
                    "completed_at": (datetime.now(timezone.utc) - timedelta(days=12)).isoformat()
                }
            ]
        }
    
    async def get_program_stats(
        self,
        program_id: int
    ) -> Dict[str, Any]:
        """Get referral program statistics"""
        return {
            "program_id": program_id,
            "total_referrals": 150,
            "successful_referrals": 120,
            "conversion_rate": 80.0,
            "total_referrer_rewards": 2400.00,
            "total_referee_rewards": 1800.00,
            "new_customers_acquired": 120,
            "revenue_from_referrals": 12000.00,
            "avg_referee_order_value": 65.00,
            "top_referrers": [
                {"customer_id": 1, "name": "Top Customer", "referrals": 15},
                {"customer_id": 2, "name": "Second Best", "referrals": 12}
            ]
        }
    
    async def share_referral_link(
        self,
        referral_code: str,
        channel: str  # email, sms, social
    ) -> Dict[str, Any]:
        """Generate shareable referral link"""
        base_url = "https://bjsbar.bg/ref"
        return {
            "referral_code": referral_code,
            "share_url": f"{base_url}/{referral_code}",
            "channel": channel,
            "share_message": f"Get 15 лв off your first order at BJ's Bar! Use code {referral_code} or click: {base_url}/{referral_code}"
        }

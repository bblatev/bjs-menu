"""SMS Marketing Service - TouchBistro/Toast parity feature"""
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import secrets
import re


class SMSMarketingService:
    """Complete SMS marketing functionality"""
    
    def __init__(self, db: Session):
        self.db = db
        self.sms_provider = None  # Twilio, MessageBird, etc.
    
    # Campaign Management
    async def create_campaign(
        self,
        venue_id: int,
        name: str,
        message: str,
        target_segment: str = "all",
        scheduled_at: Optional[datetime] = None,
        created_by: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a new SMS campaign"""
        # Validate message length (SMS limit is 160 chars, or 70 for unicode)
        if len(message) > 320:
            raise ValueError("Message too long. Max 320 characters for multi-part SMS.")
        
        campaign = {
            "venue_id": venue_id,
            "name": name,
            "message": message,
            "target_segment": target_segment,
            "status": "draft" if not scheduled_at else "scheduled",
            "scheduled_at": scheduled_at,
            "created_by": created_by,
            "created_at": datetime.now(timezone.utc)
        }
        
        # In production: INSERT INTO sms_campaigns
        campaign["id"] = secrets.randbelow(10000) + 1
        
        # Get recipient count estimate
        recipient_count = await self._get_segment_count(venue_id, target_segment)
        campaign["estimated_recipients"] = recipient_count
        
        return campaign
    
    async def _get_segment_count(self, venue_id: int, segment: str) -> int:
        """Get count of customers in segment"""
        # In production: query customers based on segment
        segment_counts = {
            "all": 500,
            "vip": 50,
            "inactive": 150,
            "birthday_this_month": 25,
            "new_customers": 75,
            "loyalty_members": 200
        }
        return segment_counts.get(segment, 0)
    
    async def send_campaign(self, campaign_id: int) -> Dict[str, Any]:
        """Send an SMS campaign immediately"""
        # Get campaign details
        campaign = await self.get_campaign(campaign_id)
        if not campaign:
            raise ValueError("Campaign not found")
        
        if campaign["status"] not in ["draft", "scheduled"]:
            raise ValueError(f"Cannot send campaign in {campaign['status']} status")
        
        # Get recipients
        recipients = await self._get_campaign_recipients(
            campaign["venue_id"], 
            campaign["target_segment"]
        )
        
        # Send messages
        results = {
            "campaign_id": campaign_id,
            "total_recipients": len(recipients),
            "sent": 0,
            "failed": 0,
            "status": "sending"
        }
        
        for recipient in recipients:
            try:
                await self._send_sms(
                    recipient["phone"],
                    campaign["message"],
                    campaign_id
                )
                results["sent"] += 1
            except Exception as e:
                results["failed"] += 1
        
        results["status"] = "sent"
        return results
    
    async def _get_campaign_recipients(
        self, 
        venue_id: int, 
        segment: str
    ) -> List[Dict[str, Any]]:
        """Get list of recipients for a segment"""
        # In production: query customers with valid phone numbers
        # Filter by segment criteria
        return [
            {"customer_id": i, "phone": f"+359888{100000+i}", "name": f"Customer {i}"}
            for i in range(10)  # Mock data
        ]
    
    async def _send_sms(
        self, 
        phone_number: str, 
        message: str, 
        campaign_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Send individual SMS via provider"""
        # Validate phone number
        if not self._validate_phone(phone_number):
            raise ValueError(f"Invalid phone number: {phone_number}")
        
        # In production: call SMS provider API (Twilio, etc.)
        return {
            "message_id": secrets.token_hex(16),
            "phone": phone_number,
            "status": "sent",
            "sent_at": datetime.now(timezone.utc).isoformat()
        }
    
    def _validate_phone(self, phone: str) -> bool:
        """Validate phone number format"""
        # Bulgarian phone: +359 or starting with 0
        pattern = r'^(\+359|0)[0-9]{9}$'
        cleaned = re.sub(r'[\s\-\(\)]', '', phone)
        return bool(re.match(pattern, cleaned))
    
    async def get_campaign(self, campaign_id: int) -> Optional[Dict[str, Any]]:
        """Get campaign details"""
        # In production: SELECT FROM sms_campaigns
        return {
            "id": campaign_id,
            "venue_id": 1,
            "name": "Holiday Special",
            "message": "🎄 Happy Holidays! Get 20% off your next visit at BJ's Bar!",
            "status": "draft",
            "target_segment": "all",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    
    async def list_campaigns(
        self, 
        venue_id: int, 
        status: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """List all campaigns for venue"""
        campaigns = [
            {
                "id": i,
                "name": f"Campaign {i}",
                "status": ["draft", "sent", "scheduled"][i % 3],
                "target_segment": "all",
                "total_recipients": 100 + i * 10,
                "delivered_count": 95 + i * 9,
                "created_at": (datetime.now(timezone.utc) - timedelta(days=i)).isoformat()
            }
            for i in range(1, 6)
        ]
        
        if status:
            campaigns = [c for c in campaigns if c["status"] == status]
        
        return campaigns[:limit]
    
    # Transactional SMS
    async def send_order_confirmation(
        self, 
        phone: str, 
        order_number: str, 
        total: float
    ) -> Dict[str, Any]:
        """Send order confirmation SMS"""
        message = f"BJ's Bar: Your order #{order_number} for {total:.2f} лв has been confirmed! Thank you!"
        return await self._send_sms(phone, message)
    
    async def send_order_ready(
        self, 
        phone: str, 
        order_number: str
    ) -> Dict[str, Any]:
        """Send order ready notification"""
        message = f"BJ's Bar: Your order #{order_number} is ready for pickup! 🍕"
        return await self._send_sms(phone, message)
    
    async def send_reservation_reminder(
        self, 
        phone: str, 
        reservation_time: datetime,
        party_size: int
    ) -> Dict[str, Any]:
        """Send reservation reminder"""
        time_str = reservation_time.strftime("%H:%M")
        date_str = reservation_time.strftime("%d/%m")
        message = f"BJ's Bar: Reminder - Your table for {party_size} is booked for {date_str} at {time_str}. See you soon!"
        return await self._send_sms(phone, message)
    
    async def send_waitlist_notification(
        self, 
        phone: str, 
        estimated_wait: int
    ) -> Dict[str, Any]:
        """Send waitlist ready notification"""
        message = f"BJ's Bar: Your table is ready! Please check in with the host within 10 minutes."
        return await self._send_sms(phone, message)
    
    # Analytics
    async def get_campaign_analytics(
        self, 
        campaign_id: int
    ) -> Dict[str, Any]:
        """Get detailed analytics for a campaign"""
        return {
            "campaign_id": campaign_id,
            "total_sent": 500,
            "delivered": 485,
            "failed": 15,
            "delivery_rate": 97.0,
            "opt_outs": 3,
            "cost": 25.00,  # Cost in BGN
            "cost_per_message": 0.05,
            "orders_attributed": 45,
            "revenue_attributed": 2250.00,
            "roi": 8900.0  # percentage
        }
    
    async def get_sms_stats(
        self, 
        venue_id: int, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get SMS statistics for period"""
        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "campaigns_sent": 12,
            "total_messages": 6000,
            "delivery_rate": 96.5,
            "total_cost": 300.00,
            "opt_out_rate": 0.5,
            "engagement_rate": 15.2
        }
    
    # Opt-out Management
    async def opt_out_customer(
        self, 
        phone: str, 
        venue_id: int
    ) -> Dict[str, Any]:
        """Opt customer out of SMS marketing"""
        # In production: UPDATE customers SET sms_opt_out = true
        return {
            "phone": phone,
            "opted_out": True,
            "opted_out_at": datetime.now(timezone.utc).isoformat()
        }
    
    async def check_opt_out_status(
        self, 
        phone: str, 
        venue_id: int
    ) -> bool:
        """Check if customer has opted out"""
        # In production: SELECT sms_opt_out FROM customers
        return False

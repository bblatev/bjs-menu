"""
Order Throttling (Snooze) Service - Enterprise Grade
Implements Toast-style dynamic order throttling for peak management

Features:
- Real-time order flow control
- Channel-specific throttling (online, kiosk, delivery)
- Automatic kitchen load detection
- Estimated wait time calculation
- Customer communication
- Delivery platform integration
- Smart capacity management
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from enum import Enum
import statistics
from app.core.config import settings


class OrderChannel(str, Enum):
    DINE_IN = "dine_in"
    TAKEOUT = "takeout"
    DELIVERY = "delivery"
    KIOSK = "kiosk"
    ONLINE = "online"
    PHONE = "phone"
    THIRD_PARTY = "third_party"


class ThrottleLevel(str, Enum):
    NORMAL = "normal"           # No throttling
    LIGHT = "light"             # Slight delays
    MODERATE = "moderate"       # Significant delays
    HEAVY = "heavy"             # Major delays
    PAUSED = "paused"           # Channel paused


class ThrottleReason(str, Enum):
    KITCHEN_OVERLOAD = "kitchen_overload"
    STAFF_SHORTAGE = "staff_shortage"
    INGREDIENT_SHORTAGE = "ingredient_shortage"
    EQUIPMENT_ISSUE = "equipment_issue"
    MANUAL_PAUSE = "manual_pause"
    HIGH_DEMAND = "high_demand"
    WEATHER_SURGE = "weather_surge"


class OrderThrottlingService:
    """
    Dynamic order throttling service matching Toast's snooze feature.
    Manages order flow across all channels based on kitchen capacity.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.channel_status = {}  # Current throttle status by channel
        self.throttle_history = []  # Historical throttle events
        self.kitchen_metrics = {}  # Real-time kitchen metrics
        
        # Default configuration
        self.config = {
            "max_orders_per_15min": 30,
            "max_items_per_15min": 100,
            "target_ticket_time_seconds": 600,  # 10 minutes
            "auto_throttle_enabled": True,
            "auto_pause_threshold": 0.9,  # 90% capacity
            "staff_per_order_ratio": 5,  # 5 orders per staff
        }
        
        # Initialize channel status
        for channel in OrderChannel:
            self.channel_status[channel.value] = {
                "channel": channel.value,
                "level": ThrottleLevel.NORMAL.value,
                "reason": None,
                "modified_at": None,
                "auto_resume_at": None,
                "estimated_delay_minutes": 0
            }
    
    # ==================== THROTTLE MANAGEMENT ====================
    
    def set_channel_throttle(
        self,
        channel: OrderChannel,
        level: ThrottleLevel,
        reason: ThrottleReason,
        duration_minutes: Optional[int] = None,
        message: Optional[str] = None,
        modified_by: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Set throttle level for a specific channel
        """
        now = datetime.utcnow()
        auto_resume = None
        
        if duration_minutes:
            auto_resume = now + timedelta(minutes=duration_minutes)
        
        previous = self.channel_status[channel.value].copy()
        
        self.channel_status[channel.value] = {
            "channel": channel.value,
            "level": level.value,
            "reason": reason.value,
            "message": message,
            "modified_at": now.isoformat(),
            "modified_by": modified_by,
            "auto_resume_at": auto_resume.isoformat() if auto_resume else None,
            "estimated_delay_minutes": self._calculate_delay_for_level(level)
        }
        
        # Log the change
        self.throttle_history.append({
            "timestamp": now.isoformat(),
            "channel": channel.value,
            "previous_level": previous["level"],
            "new_level": level.value,
            "reason": reason.value,
            "duration_minutes": duration_minutes,
            "modified_by": modified_by
        })
        
        # Notify affected platforms
        notifications = self._notify_channel_change(channel, level)
        
        return {
            "success": True,
            "channel": channel.value,
            "level": level.value,
            "reason": reason.value,
            "estimated_delay_minutes": self.channel_status[channel.value]["estimated_delay_minutes"],
            "auto_resume_at": auto_resume.isoformat() if auto_resume else None,
            "notifications_sent": notifications
        }
    
    def pause_channel(
        self,
        channel: OrderChannel,
        reason: ThrottleReason,
        duration_minutes: int = 30,
        message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Pause a channel completely (stop accepting orders)
        """
        return self.set_channel_throttle(
            channel=channel,
            level=ThrottleLevel.PAUSED,
            reason=reason,
            duration_minutes=duration_minutes,
            message=message or f"Orders temporarily paused for {duration_minutes} minutes"
        )
    
    def resume_channel(
        self,
        channel: OrderChannel,
        modified_by: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Resume a paused/throttled channel to normal
        """
        return self.set_channel_throttle(
            channel=channel,
            level=ThrottleLevel.NORMAL,
            reason=ThrottleReason.MANUAL_PAUSE,  # Manual resume
            modified_by=modified_by
        )
    
    def snooze_all_online(
        self,
        duration_minutes: int = 15,
        reason: ThrottleReason = ThrottleReason.KITCHEN_OVERLOAD
    ) -> Dict[str, Any]:
        """
        Snooze all online ordering channels (Toast-style snooze button)
        """
        online_channels = [
            OrderChannel.ONLINE,
            OrderChannel.KIOSK,
            OrderChannel.THIRD_PARTY
        ]
        
        results = []
        for channel in online_channels:
            result = self.pause_channel(channel, reason, duration_minutes)
            results.append(result)
        
        return {
            "success": True,
            "channels_paused": [c.value for c in online_channels],
            "duration_minutes": duration_minutes,
            "auto_resume_at": (datetime.utcnow() + timedelta(minutes=duration_minutes)).isoformat(),
            "results": results
        }
    
    # ==================== AUTOMATIC THROTTLING ====================
    
    def update_kitchen_metrics(
        self,
        venue_id: int,
        active_orders: int,
        pending_items: int,
        avg_ticket_time: float,
        staff_count: int,
        stations_active: int
    ) -> Dict[str, Any]:
        """
        Update real-time kitchen metrics for auto-throttling decisions
        """
        now = datetime.utcnow()
        
        metrics = {
            "venue_id": venue_id,
            "timestamp": now.isoformat(),
            "active_orders": active_orders,
            "pending_items": pending_items,
            "avg_ticket_time_seconds": avg_ticket_time,
            "staff_count": staff_count,
            "stations_active": stations_active
        }
        
        # Calculate capacity utilization
        max_orders = self.config["max_orders_per_15min"]
        order_capacity = active_orders / max_orders
        
        max_items = self.config["max_items_per_15min"]
        item_capacity = pending_items / max_items
        
        target_time = self.config["target_ticket_time_seconds"]
        time_pressure = avg_ticket_time / target_time
        
        staff_capacity = active_orders / (staff_count * self.config["staff_per_order_ratio"]) if staff_count else 1
        
        # Overall capacity score (0-1, higher = more stressed)
        capacity_score = max(order_capacity, item_capacity, time_pressure, staff_capacity)
        
        metrics["capacity_score"] = round(capacity_score, 2)
        metrics["order_capacity_pct"] = round(order_capacity * 100, 1)
        metrics["item_capacity_pct"] = round(item_capacity * 100, 1)
        metrics["time_pressure"] = round(time_pressure, 2)
        metrics["staff_utilization_pct"] = round(staff_capacity * 100, 1)
        
        self.kitchen_metrics[venue_id] = metrics
        
        # Auto-throttle if enabled
        throttle_actions = []
        if self.config["auto_throttle_enabled"]:
            throttle_actions = self._evaluate_auto_throttle(venue_id, capacity_score)
        
        return {
            "metrics": metrics,
            "capacity_score": capacity_score,
            "status": self._get_capacity_status(capacity_score),
            "auto_throttle_actions": throttle_actions,
            "recommendations": self._get_capacity_recommendations(capacity_score, metrics)
        }
    
    def _evaluate_auto_throttle(
        self,
        venue_id: int,
        capacity_score: float
    ) -> List[Dict[str, Any]]:
        """
        Evaluate and apply automatic throttling based on capacity
        """
        actions = []
        
        if capacity_score >= 0.9:
            # Critical - pause online ordering
            for channel in [OrderChannel.ONLINE, OrderChannel.THIRD_PARTY]:
                if self.channel_status[channel.value]["level"] != ThrottleLevel.PAUSED.value:
                    result = self.pause_channel(
                        channel,
                        ThrottleReason.KITCHEN_OVERLOAD,
                        duration_minutes=15
                    )
                    actions.append({
                        "action": "paused",
                        "channel": channel.value,
                        "reason": "capacity_critical"
                    })
        
        elif capacity_score >= 0.75:
            # Heavy load - heavy throttle
            for channel in [OrderChannel.ONLINE, OrderChannel.KIOSK]:
                if self.channel_status[channel.value]["level"] not in [ThrottleLevel.HEAVY.value, ThrottleLevel.PAUSED.value]:
                    self.set_channel_throttle(
                        channel,
                        ThrottleLevel.HEAVY,
                        ThrottleReason.HIGH_DEMAND
                    )
                    actions.append({
                        "action": "throttled_heavy",
                        "channel": channel.value
                    })
        
        elif capacity_score >= 0.6:
            # Moderate load - moderate throttle
            for channel in [OrderChannel.ONLINE]:
                if self.channel_status[channel.value]["level"] == ThrottleLevel.NORMAL.value:
                    self.set_channel_throttle(
                        channel,
                        ThrottleLevel.MODERATE,
                        ThrottleReason.HIGH_DEMAND
                    )
                    actions.append({
                        "action": "throttled_moderate",
                        "channel": channel.value
                    })
        
        elif capacity_score < 0.4:
            # Light load - resume all
            for channel in OrderChannel:
                if self.channel_status[channel.value]["level"] != ThrottleLevel.NORMAL.value:
                    # Check if was auto-paused (not manual)
                    if self.channel_status[channel.value].get("reason") != ThrottleReason.MANUAL_PAUSE.value:
                        self.resume_channel(channel)
                        actions.append({
                            "action": "resumed",
                            "channel": channel.value
                        })
        
        return actions
    
    # ==================== ORDER ACCEPTANCE ====================
    
    def check_order_acceptance(
        self,
        channel: OrderChannel,
        order_items_count: int = 1,
        customer_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Check if a new order can be accepted on this channel
        """
        status = self.channel_status[channel.value]
        
        # Check if channel is paused
        if status["level"] == ThrottleLevel.PAUSED.value:
            # Check auto-resume
            if status.get("auto_resume_at"):
                resume_time = datetime.fromisoformat(status["auto_resume_at"])
                if datetime.utcnow() >= resume_time:
                    # Auto-resume
                    self.resume_channel(channel)
                    status = self.channel_status[channel.value]
                else:
                    return {
                        "accepted": False,
                        "reason": "channel_paused",
                        "message": status.get("message", "Orders temporarily unavailable"),
                        "resume_at": status["auto_resume_at"],
                        "minutes_until_resume": int((resume_time - datetime.utcnow()).total_seconds() / 60)
                    }
            else:
                return {
                    "accepted": False,
                    "reason": "channel_paused",
                    "message": status.get("message", "Orders temporarily unavailable")
                }
        
        # Calculate estimated wait time
        estimated_wait = self._calculate_estimated_wait(channel, order_items_count)
        
        # Check throttle level
        level = ThrottleLevel(status["level"])
        
        if level == ThrottleLevel.HEAVY:
            # Accept but with significant delay warning
            return {
                "accepted": True,
                "throttled": True,
                "level": level.value,
                "estimated_wait_minutes": estimated_wait,
                "warning_message": f"Current wait time is approximately {estimated_wait} minutes",
                "show_warning": True
            }
        
        elif level == ThrottleLevel.MODERATE:
            # Accept with delay warning
            return {
                "accepted": True,
                "throttled": True,
                "level": level.value,
                "estimated_wait_minutes": estimated_wait,
                "warning_message": f"Current wait time is approximately {estimated_wait} minutes",
                "show_warning": estimated_wait > 15
            }
        
        elif level == ThrottleLevel.LIGHT:
            # Accept with minor delay possible
            return {
                "accepted": True,
                "throttled": True,
                "level": level.value,
                "estimated_wait_minutes": estimated_wait,
                "show_warning": False
            }
        
        # Normal - accept without warning
        return {
            "accepted": True,
            "throttled": False,
            "level": ThrottleLevel.NORMAL.value,
            "estimated_wait_minutes": estimated_wait,
            "show_warning": False
        }
    
    def _calculate_estimated_wait(
        self,
        channel: OrderChannel,
        items_count: int
    ) -> int:
        """
        Calculate estimated wait time in minutes
        """
        status = self.channel_status[channel.value]
        base_delay = status.get("estimated_delay_minutes", 0)
        
        # Get kitchen metrics if available
        metrics = list(self.kitchen_metrics.values())
        if metrics:
            latest = metrics[-1]
            active_orders = latest.get("active_orders", 0)
            avg_time = latest.get("avg_ticket_time_seconds", 600)
            
            # Estimate based on queue position
            queue_time = (active_orders * avg_time) / 60 / 2  # Assume parallel processing
            
            return int(base_delay + queue_time + (items_count * 2))
        
        # Default estimates by throttle level
        level_estimates = {
            ThrottleLevel.NORMAL.value: 10,
            ThrottleLevel.LIGHT.value: 15,
            ThrottleLevel.MODERATE.value: 25,
            ThrottleLevel.HEAVY.value: 40
        }
        
        return level_estimates.get(status["level"], 15) + (items_count * 2)
    
    # ==================== THIRD-PARTY INTEGRATION ====================
    
    def update_delivery_platform_status(
        self,
        platform: str,  # "uber_eats", "doordash", "glovo", etc.
        paused: bool,
        prep_time_minutes: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Update status on third-party delivery platforms
        """
        # In production, call platform APIs
        updates = {
            "platform": platform,
            "paused": paused,
            "prep_time_minutes": prep_time_minutes,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        if platform == "uber_eats":
            updates["api_response"] = self._update_uber_eats(paused, prep_time_minutes)
        elif platform == "doordash":
            updates["api_response"] = self._update_doordash(paused, prep_time_minutes)
        elif platform == "glovo":
            updates["api_response"] = self._update_glovo(paused, prep_time_minutes)
        elif platform == "wolt":
            updates["api_response"] = self._update_wolt(paused, prep_time_minutes)
        
        return updates
    
    def sync_all_platforms(self) -> Dict[str, Any]:
        """
        Sync throttle status with all delivery platforms
        """
        third_party_status = self.channel_status[OrderChannel.THIRD_PARTY.value]
        paused = third_party_status["level"] == ThrottleLevel.PAUSED.value
        prep_time = third_party_status["estimated_delay_minutes"]
        
        platforms = ["uber_eats", "doordash", "glovo", "wolt", "foodpanda"]
        results = {}
        
        for platform in platforms:
            try:
                result = self.update_delivery_platform_status(platform, paused, prep_time)
                results[platform] = {"success": True, "response": result}
            except Exception as e:
                results[platform] = {"success": False, "error": str(e)}
        
        return {
            "synced_at": datetime.utcnow().isoformat(),
            "paused": paused,
            "prep_time_minutes": prep_time,
            "platforms": results
        }
    
    def _update_uber_eats(self, paused: bool, prep_time: int) -> Dict:
        """Update Uber Eats status via API"""
        import requests
        import os

        try:
            # Get Uber Eats API credentials from environment
            api_key = settings.uber_eats_api_key
            store_id = settings.uber_eats_store_id

            if not api_key or not store_id:
                return {
                    "status": "skipped",
                    "platform": "uber_eats",
                    "reason": "API credentials not configured"
                }

            # Uber Eats Store API endpoint
            base_url = "https://api.uber.com/v1/eats/store"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            # Update store status
            if paused:
                # Pause store - set to offline
                response = requests.post(
                    f"{base_url}/{store_id}/status",
                    headers=headers,
                    json={
                        "status": "OFFLINE",
                        "reason": "BUSY",
                        "offline_reason_description": "High order volume - temporarily paused"
                    },
                    timeout=10
                )
            else:
                # Resume store - set to online with updated prep time
                response = requests.post(
                    f"{base_url}/{store_id}/status",
                    headers=headers,
                    json={
                        "status": "ONLINE",
                        "prep_time_minutes": prep_time or 15
                    },
                    timeout=10
                )

            if response.status_code in [200, 201, 204]:
                return {
                    "status": "updated",
                    "platform": "uber_eats",
                    "paused": paused,
                    "prep_time": prep_time,
                    "response_code": response.status_code
                }
            else:
                return {
                    "status": "error",
                    "platform": "uber_eats",
                    "error": f"API returned {response.status_code}",
                    "response": response.text[:200] if response.text else None
                }

        except requests.exceptions.Timeout:
            return {"status": "error", "platform": "uber_eats", "error": "Request timed out"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "platform": "uber_eats", "error": str(e)}
        except Exception as e:
            return {"status": "error", "platform": "uber_eats", "error": str(e)}

    def _update_doordash(self, paused: bool, prep_time: int) -> Dict:
        """Update DoorDash status via API"""
        import requests
        import os

        try:
            # Get DoorDash API credentials from environment
            api_key = settings.doordash_api_key
            store_id = settings.doordash_store_id

            if not api_key or not store_id:
                return {
                    "status": "skipped",
                    "platform": "doordash",
                    "reason": "API credentials not configured"
                }

            # DoorDash Drive API endpoint
            base_url = "https://openapi.doordash.com/drive/v2"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            if paused:
                # Pause accepting orders
                response = requests.patch(
                    f"{base_url}/stores/{store_id}",
                    headers=headers,
                    json={
                        "is_accepting_orders": False,
                        "status_reason": "temporarily_busy"
                    },
                    timeout=10
                )
            else:
                # Resume accepting orders with updated prep time
                response = requests.patch(
                    f"{base_url}/stores/{store_id}",
                    headers=headers,
                    json={
                        "is_accepting_orders": True,
                        "default_prep_time_minutes": prep_time or 15
                    },
                    timeout=10
                )

            if response.status_code in [200, 201, 204]:
                return {
                    "status": "updated",
                    "platform": "doordash",
                    "paused": paused,
                    "prep_time": prep_time,
                    "response_code": response.status_code
                }
            else:
                return {
                    "status": "error",
                    "platform": "doordash",
                    "error": f"API returned {response.status_code}",
                    "response": response.text[:200] if response.text else None
                }

        except requests.exceptions.Timeout:
            return {"status": "error", "platform": "doordash", "error": "Request timed out"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "platform": "doordash", "error": str(e)}
        except Exception as e:
            return {"status": "error", "platform": "doordash", "error": str(e)}

    def _update_glovo(self, paused: bool, prep_time: int) -> Dict:
        """Update Glovo status via API"""
        import requests
        import os

        try:
            # Get Glovo API credentials from environment
            api_key = settings.glovo_api_key
            store_id = settings.glovo_store_id

            if not api_key or not store_id:
                return {
                    "status": "skipped",
                    "platform": "glovo",
                    "reason": "API credentials not configured"
                }

            # Glovo Partner API endpoint
            base_url = "https://api.glovoapp.com/partner"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            if paused:
                # Close store temporarily
                response = requests.put(
                    f"{base_url}/stores/{store_id}/status",
                    headers=headers,
                    json={
                        "status": "CLOSED",
                        "reason": "HIGH_DEMAND",
                        "message": "Temporarily closed due to high order volume"
                    },
                    timeout=10
                )
            else:
                # Open store with updated prep time
                response = requests.put(
                    f"{base_url}/stores/{store_id}/status",
                    headers=headers,
                    json={
                        "status": "OPEN",
                        "preparation_time_minutes": prep_time or 15
                    },
                    timeout=10
                )

            if response.status_code in [200, 201, 204]:
                return {
                    "status": "updated",
                    "platform": "glovo",
                    "paused": paused,
                    "prep_time": prep_time,
                    "response_code": response.status_code
                }
            else:
                return {
                    "status": "error",
                    "platform": "glovo",
                    "error": f"API returned {response.status_code}",
                    "response": response.text[:200] if response.text else None
                }

        except requests.exceptions.Timeout:
            return {"status": "error", "platform": "glovo", "error": "Request timed out"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "platform": "glovo", "error": str(e)}
        except Exception as e:
            return {"status": "error", "platform": "glovo", "error": str(e)}

    def _update_wolt(self, paused: bool, prep_time: int) -> Dict:
        """Update Wolt status via API"""
        import requests
        import os

        try:
            # Get Wolt API credentials from environment
            api_key = settings.wolt_api_key
            venue_id = settings.wolt_venue_id

            if not api_key or not venue_id:
                return {
                    "status": "skipped",
                    "platform": "wolt",
                    "reason": "API credentials not configured"
                }

            # Wolt Merchant API endpoint
            base_url = "https://restaurant-api.wolt.com/v1"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            if paused:
                # Set venue to busy/closed
                response = requests.put(
                    f"{base_url}/venues/{venue_id}/availability",
                    headers=headers,
                    json={
                        "is_available": False,
                        "unavailability_reason": "busy",
                        "message": "High order volume - temporarily paused"
                    },
                    timeout=10
                )
            else:
                # Set venue to available with prep time
                response = requests.put(
                    f"{base_url}/venues/{venue_id}/availability",
                    headers=headers,
                    json={
                        "is_available": True,
                        "estimated_delivery_time_minutes": prep_time or 15
                    },
                    timeout=10
                )

            if response.status_code in [200, 201, 204]:
                return {
                    "status": "updated",
                    "platform": "wolt",
                    "paused": paused,
                    "prep_time": prep_time,
                    "response_code": response.status_code
                }
            else:
                return {
                    "status": "error",
                    "platform": "wolt",
                    "error": f"API returned {response.status_code}",
                    "response": response.text[:200] if response.text else None
                }

        except requests.exceptions.Timeout:
            return {"status": "error", "platform": "wolt", "error": "Request timed out"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "platform": "wolt", "error": str(e)}
        except Exception as e:
            return {"status": "error", "platform": "wolt", "error": str(e)}
    
    # ==================== STATUS & REPORTING ====================
    
    def get_all_channel_status(self) -> Dict[str, Any]:
        """
        Get current status of all order channels
        """
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "channels": self.channel_status,
            "overall_status": self._get_overall_status(),
            "kitchen_metrics": list(self.kitchen_metrics.values())[-1] if self.kitchen_metrics else None
        }
    
    def get_throttle_dashboard(
        self,
        venue_id: int
    ) -> Dict[str, Any]:
        """
        Get comprehensive throttle dashboard
        """
        metrics = self.kitchen_metrics.get(venue_id, {})
        
        # Count throttled channels
        throttled = sum(
            1 for s in self.channel_status.values()
            if s["level"] != ThrottleLevel.NORMAL.value
        )
        
        paused = sum(
            1 for s in self.channel_status.values()
            if s["level"] == ThrottleLevel.PAUSED.value
        )
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total_channels": len(self.channel_status),
                "throttled_channels": throttled,
                "paused_channels": paused,
                "capacity_score": metrics.get("capacity_score", 0),
                "capacity_status": self._get_capacity_status(metrics.get("capacity_score", 0))
            },
            "channels": self.channel_status,
            "kitchen_metrics": metrics,
            "recent_actions": self.throttle_history[-10:],
            "recommendations": self._get_capacity_recommendations(
                metrics.get("capacity_score", 0),
                metrics
            )
        }
    
    def get_throttle_history(
        self,
        venue_id: int,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get throttle history for analysis
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        history = [
            h for h in self.throttle_history
            if h.get("timestamp", "") >= cutoff.isoformat()
        ]
        
        # Analyze patterns
        by_channel = {}
        by_reason = {}
        by_hour = {}
        
        for event in history:
            channel = event.get("channel", "unknown")
            reason = event.get("reason", "unknown")
            hour = event.get("timestamp", "")[:13]  # YYYY-MM-DDTHH
            
            by_channel[channel] = by_channel.get(channel, 0) + 1
            by_reason[reason] = by_reason.get(reason, 0) + 1
            by_hour[hour] = by_hour.get(hour, 0) + 1
        
        # Calculate total downtime per channel
        downtime = self._calculate_channel_downtime(history)
        
        return {
            "period_hours": hours,
            "total_events": len(history),
            "events": history,
            "analysis": {
                "by_channel": by_channel,
                "by_reason": by_reason,
                "by_hour": dict(sorted(by_hour.items())),
                "channel_downtime_minutes": downtime
            }
        }
    
    # ==================== HELPER METHODS ====================
    
    def _calculate_delay_for_level(self, level: ThrottleLevel) -> int:
        """Get estimated delay minutes for throttle level"""
        delays = {
            ThrottleLevel.NORMAL: 0,
            ThrottleLevel.LIGHT: 5,
            ThrottleLevel.MODERATE: 15,
            ThrottleLevel.HEAVY: 30,
            ThrottleLevel.PAUSED: 0  # N/A when paused
        }
        return delays.get(level, 0)
    
    def _get_overall_status(self) -> str:
        """Get overall order acceptance status"""
        levels = [ThrottleLevel(s["level"]) for s in self.channel_status.values()]
        
        if all(l == ThrottleLevel.PAUSED for l in levels):
            return "all_paused"
        elif all(l == ThrottleLevel.NORMAL for l in levels):
            return "normal"
        elif any(l == ThrottleLevel.PAUSED for l in levels):
            return "partial_pause"
        elif any(l in [ThrottleLevel.HEAVY, ThrottleLevel.MODERATE] for l in levels):
            return "throttled"
        else:
            return "light_throttle"
    
    def _get_capacity_status(self, score: float) -> str:
        """Get human-readable capacity status"""
        if score >= 0.9:
            return "critical"
        elif score >= 0.75:
            return "high"
        elif score >= 0.5:
            return "moderate"
        elif score >= 0.25:
            return "light"
        else:
            return "normal"
    
    def _get_capacity_recommendations(
        self,
        score: float,
        metrics: Dict
    ) -> List[str]:
        """Get recommendations based on capacity"""
        recommendations = []
        
        if score >= 0.9:
            recommendations.append("Critical capacity - consider pausing online orders")
            recommendations.append("Call in additional staff if available")
        
        if metrics.get("time_pressure", 0) > 1.5:
            recommendations.append("Ticket times are high - review kitchen workflow")
        
        if metrics.get("staff_utilization_pct", 0) > 100:
            recommendations.append("Staff overutilized - redistribute workload")
        
        if score < 0.3 and any(
            s["level"] != ThrottleLevel.NORMAL.value
            for s in self.channel_status.values()
        ):
            recommendations.append("Capacity available - consider resuming throttled channels")
        
        return recommendations
    
    def _notify_channel_change(
        self,
        channel: OrderChannel,
        level: ThrottleLevel
    ) -> List[str]:
        """Send notifications about channel status change"""
        notifications = []
        
        # Notify management
        notifications.append(f"manager_notification_sent")
        
        # Update delivery platforms if third-party
        if channel == OrderChannel.THIRD_PARTY:
            self.sync_all_platforms()
            notifications.append("delivery_platforms_synced")
        
        # Update website/app
        if channel in [OrderChannel.ONLINE, OrderChannel.KIOSK]:
            notifications.append("frontend_updated")
        
        return notifications
    
    def _calculate_channel_downtime(
        self,
        history: List[Dict]
    ) -> Dict[str, int]:
        """Calculate total downtime per channel"""
        downtime = {c.value: 0 for c in OrderChannel}
        
        # Track pause/resume pairs
        paused_at = {}
        
        for event in sorted(history, key=lambda x: x.get("timestamp", "")):
            channel = event.get("channel")
            if not channel:
                continue
            
            if event.get("new_level") == ThrottleLevel.PAUSED.value:
                paused_at[channel] = datetime.fromisoformat(event["timestamp"])
            
            elif event.get("previous_level") == ThrottleLevel.PAUSED.value:
                if channel in paused_at:
                    start = paused_at[channel]
                    end = datetime.fromisoformat(event["timestamp"])
                    downtime[channel] += int((end - start).total_seconds() / 60)
                    del paused_at[channel]
        
        # Add ongoing pauses
        now = datetime.utcnow()
        for channel, start in paused_at.items():
            downtime[channel] += int((now - start).total_seconds() / 60)
        
        return downtime
    
    # ==================== API ENDPOINT METHODS ====================
    
    def get_throttling_status(self, venue_id: int) -> Dict[str, Any]:
        """Get current throttling status and active rules for a venue"""
        return {
            "venue_id": venue_id,
            "timestamp": datetime.utcnow().isoformat(),
            "channels": self.channel_status,
            "overall_status": self._get_overall_status(),
            "kitchen_metrics": self.kitchen_metrics.get(venue_id, {}),
            "active_rules": self._get_active_rules(venue_id),
            "snooze_active": self._is_snooze_active(venue_id)
        }
    
    def _get_active_rules(self, venue_id: int) -> List[Dict]:
        """Get active throttle rules for venue from database"""
        from app.models import ThrottleRule
        
        try:
            rules = self.db.query(ThrottleRule).filter(
                ThrottleRule.venue_id == venue_id,
                ThrottleRule.is_active == True
            ).all()
            
            return [{
                "id": r.id,
                "name": r.name,
                "trigger_type": r.trigger_type,
                "threshold_value": r.threshold_value,
                "action_type": r.action_type
            } for r in rules]
        except Exception:
            return []
    
    def _is_snooze_active(self, venue_id: int) -> Dict[str, Any]:
        """Check if ordering is snoozed for venue"""
        venue_key = f"venue_{venue_id}"
        if venue_key in self.channel_status:
            status = self.channel_status[venue_key]
            if status.get("level") == ThrottleLevel.PAUSED.value:
                return {
                    "active": True,
                    "reason": status.get("reason"),
                    "resume_at": status.get("auto_resume_at")
                }
        return {"active": False}
    
    def get_rules(self, venue_id: int, active_only: bool = True) -> Dict[str, Any]:
        """Get all throttle rules for a venue"""
        from app.models import ThrottleRule
        
        try:
            query = self.db.query(ThrottleRule).filter(
                ThrottleRule.venue_id == venue_id
            )
            
            if active_only:
                query = query.filter(ThrottleRule.is_active == True)
            
            rules = query.order_by(ThrottleRule.priority).all()
            
            return {
                "venue_id": venue_id,
                "rules": [{
                    "id": r.id,
                    "name": r.name,
                    "description": r.description,
                    "trigger_type": r.trigger_type,
                    "threshold_value": r.threshold_value,
                    "time_window_minutes": r.time_window_minutes,
                    "action_type": r.action_type,
                    "action_params": r.action_params,
                    "affected_categories": r.affected_categories,
                    "affected_items": r.affected_items,
                    "is_active": r.is_active,
                    "priority": r.priority,
                    "created_at": r.created_at.isoformat() if r.created_at else None
                } for r in rules],
                "total": len(rules)
            }
        except Exception:
            return {"venue_id": venue_id, "rules": [], "total": 0}
    
    def create_rule(
        self,
        venue_id: int,
        name: str,
        trigger_type: str,
        threshold_value: int,
        time_window_minutes: int,
        action_type: str,
        action_params: Optional[Dict] = None,
        affected_categories: Optional[List[int]] = None,
        affected_items: Optional[List[int]] = None,
        station_id: Optional[int] = None,
        active_days: Optional[List[str]] = None,
        active_start_time: Optional[str] = None,
        active_end_time: Optional[str] = None,
        priority: int = 50
    ) -> Dict[str, Any]:
        """Create a new throttle rule"""
        from app.models import ThrottleRule
        
        try:
            rule = ThrottleRule(
                venue_id=venue_id,
                station_id=station_id,
                name=name,
                trigger_type=trigger_type,
                threshold_value=threshold_value,
                time_window_minutes=time_window_minutes,
                action_type=action_type,
                action_params=action_params,
                affected_categories=affected_categories,
                affected_items=affected_items,
                is_active=True,
                active_days=active_days,
                active_start_time=active_start_time,
                active_end_time=active_end_time,
                priority=priority
            )
            
            self.db.add(rule)
            self.db.commit()
            
            return {
                "success": True,
                "rule_id": rule.id,
                "message": f"Rule '{name}' created successfully"
            }
        except Exception as e:
            self.db.rollback()
            return {"success": False, "error": str(e)}
    
    def update_rule(self, rule_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing throttle rule"""
        from app.models import ThrottleRule
        
        try:
            rule = self.db.query(ThrottleRule).filter(
                ThrottleRule.id == rule_id
            ).first()
            
            if not rule:
                return {"success": False, "error": "Rule not found"}
            
            # Update allowed fields
            allowed_fields = [
                'name', 'description', 'trigger_type', 'threshold_value',
                'time_window_minutes', 'action_type', 'action_params',
                'affected_categories', 'affected_items', 'is_active',
                'active_days', 'active_start_time', 'active_end_time', 'priority'
            ]
            
            for field in allowed_fields:
                if field in updates:
                    setattr(rule, field, updates[field])
            
            self.db.commit()
            
            return {
                "success": True,
                "rule_id": rule_id,
                "message": "Rule updated successfully"
            }
        except Exception as e:
            self.db.rollback()
            return {"success": False, "error": str(e)}
    
    def delete_rule(self, rule_id: int) -> Dict[str, Any]:
        """Delete a throttle rule"""
        from app.models import ThrottleRule
        
        try:
            rule = self.db.query(ThrottleRule).filter(
                ThrottleRule.id == rule_id
            ).first()
            
            if not rule:
                return {"success": False, "error": "Rule not found"}
            
            self.db.delete(rule)
            self.db.commit()
            
            return {
                "success": True,
                "message": f"Rule {rule_id} deleted successfully"
            }
        except Exception as e:
            self.db.rollback()
            return {"success": False, "error": str(e)}
    
    def toggle_rule(self, rule_id: int, is_active: bool) -> Dict[str, Any]:
        """Enable or disable a throttle rule"""
        from app.models import ThrottleRule
        
        try:
            rule = self.db.query(ThrottleRule).filter(
                ThrottleRule.id == rule_id
            ).first()
            
            if not rule:
                return {"success": False, "error": "Rule not found"}
            
            rule.is_active = is_active
            self.db.commit()
            
            status = "enabled" if is_active else "disabled"
            return {
                "success": True,
                "rule_id": rule_id,
                "is_active": is_active,
                "message": f"Rule {status} successfully"
            }
        except Exception as e:
            self.db.rollback()
            return {"success": False, "error": str(e)}
    
    def check_throttling(self, venue_id: int, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check if an order would trigger throttling"""
        channel_str = order_data.get("channel", "online")
        items_count = len(order_data.get("items", []))
        
        # Map string channel to enum
        channel_map = {
            "online": OrderChannel.ONLINE,
            "kiosk": OrderChannel.KIOSK,
            "delivery": OrderChannel.DELIVERY,
            "dine_in": OrderChannel.DINE_IN,
            "takeout": OrderChannel.TAKEOUT,
            "phone": OrderChannel.PHONE,
            "third_party": OrderChannel.THIRD_PARTY
        }
        channel = channel_map.get(channel_str, OrderChannel.ONLINE)
        
        # Check channel status
        channel_status = self.channel_status.get(channel.value, {})
        
        if channel_status.get("level") == ThrottleLevel.PAUSED.value:
            return {
                "allowed": False,
                "reason": "channel_paused",
                "message": channel_status.get("message", "Orders temporarily unavailable"),
                "estimated_wait_minutes": channel_status.get("estimated_delay_minutes", 30)
            }
        
        if channel_status.get("level") in [ThrottleLevel.HEAVY.value, ThrottleLevel.MODERATE.value]:
            return {
                "allowed": True,
                "delayed": True,
                "delay_minutes": channel_status.get("estimated_delay_minutes", 15),
                "message": "Your order may take longer than usual"
            }
        
        return {
            "allowed": True,
            "delayed": False,
            "estimated_time_minutes": self._calculate_estimated_wait(channel, items_count)
        }
    
    def snooze_ordering(
        self,
        venue_id: int,
        duration_minutes: int,
        reason: Optional[str] = None,
        station_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Temporarily pause ordering (Toast-style snooze)"""
        now = datetime.utcnow()
        resume_at = now + timedelta(minutes=duration_minutes)
        
        # Pause all online channels
        channels_paused = []
        for channel in [OrderChannel.ONLINE, OrderChannel.KIOSK, OrderChannel.DELIVERY, OrderChannel.THIRD_PARTY]:
            self.channel_status[channel.value] = {
                "channel": channel.value,
                "level": ThrottleLevel.PAUSED.value,
                "reason": reason or "Manual snooze",
                "modified_at": now.isoformat(),
                "auto_resume_at": resume_at.isoformat(),
                "estimated_delay_minutes": duration_minutes,
                "message": f"Orders temporarily paused for {duration_minutes} minutes"
            }
            channels_paused.append(channel.value)
        
        # Log event
        self.throttle_history.append({
            "event": "snooze_activated",
            "venue_id": venue_id,
            "station_id": station_id,
            "duration_minutes": duration_minutes,
            "reason": reason,
            "channels": channels_paused,
            "timestamp": now.isoformat(),
            "resume_at": resume_at.isoformat()
        })
        
        # Sync with delivery platforms
        self.sync_all_platforms()
        
        return {
            "success": True,
            "snooze_active": True,
            "duration_minutes": duration_minutes,
            "resume_at": resume_at.isoformat(),
            "channels_affected": channels_paused
        }
    
    def resume_ordering(
        self,
        venue_id: int,
        station_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Resume ordering after snooze"""
        now = datetime.utcnow()
        
        # Resume all paused channels
        channels_resumed = []
        for channel in OrderChannel:
            if self.channel_status.get(channel.value, {}).get("level") == ThrottleLevel.PAUSED.value:
                self.channel_status[channel.value] = {
                    "channel": channel.value,
                    "level": ThrottleLevel.NORMAL.value,
                    "reason": None,
                    "modified_at": now.isoformat(),
                    "auto_resume_at": None,
                    "estimated_delay_minutes": 0
                }
                channels_resumed.append(channel.value)
        
        # Log event
        self.throttle_history.append({
            "event": "snooze_ended",
            "venue_id": venue_id,
            "station_id": station_id,
            "channels": channels_resumed,
            "timestamp": now.isoformat()
        })
        
        # Sync with delivery platforms
        self.sync_all_platforms()
        
        return {
            "success": True,
            "snooze_active": False,
            "channels_resumed": channels_resumed
        }
    
    def get_events(
        self,
        venue_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get throttling event history"""
        from app.models import ThrottleEvent
        
        try:
            query = self.db.query(ThrottleEvent).filter(
                ThrottleEvent.venue_id == venue_id
            )
            
            if start_date:
                query = query.filter(ThrottleEvent.started_at >= start_date)
            if end_date:
                query = query.filter(ThrottleEvent.started_at <= end_date)
            
            events = query.order_by(ThrottleEvent.started_at.desc()).limit(100).all()
            
            return {
                "venue_id": venue_id,
                "events": [{
                    "id": e.id,
                    "rule_id": e.rule_id,
                    "event_type": e.event_type,
                    "trigger_value": e.trigger_value,
                    "threshold_value": e.threshold_value,
                    "orders_affected": e.orders_affected,
                    "started_at": e.started_at.isoformat() if e.started_at else None,
                    "ended_at": e.ended_at.isoformat() if e.ended_at else None,
                    "duration_minutes": e.duration_minutes
                } for e in events],
                "total": len(events),
                "in_memory_events": self.throttle_history[-20:]
            }
        except Exception:
            return {
                "venue_id": venue_id,
                "events": [],
                "total": 0,
                "in_memory_events": self.throttle_history[-20:]
            }
    
    def get_analytics(self, venue_id: int, period_days: int = 30) -> Dict[str, Any]:
        """Get throttling analytics and impact analysis"""
        from datetime import timedelta
        
        start_date = datetime.utcnow() - timedelta(days=period_days)
        
        # Get events from database
        events_data = self.get_events(venue_id, start_date)
        events = events_data.get("events", [])
        
        # Calculate metrics
        total_events = len(events)
        total_duration = sum(e.get("duration_minutes", 0) or 0 for e in events)
        orders_affected = sum(e.get("orders_affected", 0) or 0 for e in events)
        
        # Calculate by type
        by_type = {}
        for event in events:
            event_type = event.get("event_type", "unknown")
            if event_type not in by_type:
                by_type[event_type] = {"count": 0, "duration": 0, "orders": 0}
            by_type[event_type]["count"] += 1
            by_type[event_type]["duration"] += event.get("duration_minutes", 0) or 0
            by_type[event_type]["orders"] += event.get("orders_affected", 0) or 0
        
        return {
            "venue_id": venue_id,
            "period_days": period_days,
            "summary": {
                "total_throttle_events": total_events,
                "total_throttle_duration_minutes": total_duration,
                "total_orders_affected": orders_affected,
                "avg_event_duration_minutes": total_duration / total_events if total_events > 0 else 0,
                "throttle_rate_per_day": total_events / period_days if period_days > 0 else 0
            },
            "by_event_type": by_type,
            "channel_downtime": self._calculate_channel_downtime(self.throttle_history),
            "recommendations": self._generate_throttle_recommendations(events)
        }
    
    def _generate_throttle_recommendations(self, events: List[Dict]) -> List[str]:
        """Generate recommendations based on throttle history"""
        recommendations = []
        
        if len(events) > 20:
            recommendations.append("High throttle frequency detected. Consider increasing kitchen capacity.")
        
        peak_hours = {}
        for event in events:
            if event.get("started_at"):
                try:
                    hour = datetime.fromisoformat(event["started_at"]).hour
                    peak_hours[hour] = peak_hours.get(hour, 0) + 1
                except (ValueError, TypeError):
                    continue  # Skip events with invalid timestamps
        
        if peak_hours:
            peak_hour = max(peak_hours, key=peak_hours.get)
            if peak_hours[peak_hour] > 5:
                recommendations.append(f"Peak throttling at {peak_hour}:00. Consider adding staff during this hour.")
        
        return recommendations

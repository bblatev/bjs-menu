"""
Self-Service Kiosk Service - Enterprise Grade
Implements Revel and CAKE-style self-ordering kiosk functionality

Features:
- Customer-facing ordering interface
- Upsell and cross-sell automation
- Accessibility compliance (ADA)
- Multi-language support
- Payment integration
- Order customization flows
- Queue management
- Analytics and conversion tracking
"""

from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from enum import Enum
import logging
import uuid

logger = logging.getLogger(__name__)


class KioskMode(str, Enum):
    ORDERING = "ordering"
    MENU_BROWSE = "menu_browse"
    CHECKOUT = "checkout"
    PAYMENT = "payment"
    ORDER_STATUS = "order_status"
    IDLE = "idle"
    MAINTENANCE = "maintenance"


class UpsellType(str, Enum):
    SIZE_UPGRADE = "size_upgrade"
    ADD_ON = "add_on"
    COMBO = "combo"
    PREMIUM = "premium"
    DESSERT = "dessert"
    DRINK = "drink"


class SelfServiceKioskService:
    """
    Self-service kiosk management matching Revel Kiosk XT and CAKE capabilities.
    Provides customer-facing ordering with intelligent upselling.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.active_sessions = {}
        self.kiosk_registry = {}
        self.conversion_data = []
        
    # ==================== KIOSK MANAGEMENT ====================
    
    def register_kiosk(
        self,
        kiosk_id: str,
        venue_id: int,
        location: str,
        hardware_type: str = "standard",
        features: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Register a new kiosk in the system
        """
        kiosk = {
            "kiosk_id": kiosk_id,
            "venue_id": venue_id,
            "location": location,
            "hardware_type": hardware_type,
            "features": features or {
                "touchscreen": True,
                "card_reader": True,
                "receipt_printer": True,
                "barcode_scanner": True,
                "nfc_reader": True,
                "camera": False,
                "voice_enabled": False
            },
            "status": "active",
            "mode": KioskMode.IDLE.value,
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "last_heartbeat": datetime.now(timezone.utc).isoformat(),
            "session_count_today": 0,
            "revenue_today": 0
        }
        
        self.kiosk_registry[kiosk_id] = kiosk
        
        return {
            "success": True,
            "kiosk": kiosk,
            "configuration": self._get_kiosk_configuration(venue_id)
        }
    
    def get_kiosk_status(self, kiosk_id: str) -> Dict[str, Any]:
        """Get current kiosk status"""
        kiosk = self.kiosk_registry.get(kiosk_id)
        if not kiosk:
            return {"error": "Kiosk not found", "success": False}
        
        # Check for active session
        active_session = self._get_active_kiosk_session(kiosk_id)
        
        return {
            "kiosk_id": kiosk_id,
            "status": kiosk["status"],
            "mode": kiosk["mode"],
            "has_active_session": active_session is not None,
            "session_duration": self._calculate_session_duration(active_session) if active_session else 0,
            "last_heartbeat": kiosk["last_heartbeat"],
            "uptime_today": self._calculate_uptime(kiosk_id),
            "sessions_today": kiosk["session_count_today"],
            "revenue_today": kiosk["revenue_today"]
        }
    
    def set_kiosk_mode(
        self,
        kiosk_id: str,
        mode: KioskMode,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Set kiosk operating mode"""
        kiosk = self.kiosk_registry.get(kiosk_id)
        if not kiosk:
            return {"error": "Kiosk not found", "success": False}
        
        old_mode = kiosk["mode"]
        kiosk["mode"] = mode.value
        
        if mode == KioskMode.MAINTENANCE:
            # End any active sessions
            self._end_kiosk_session(kiosk_id, "maintenance")
        
        return {
            "success": True,
            "kiosk_id": kiosk_id,
            "previous_mode": old_mode,
            "current_mode": mode.value,
            "reason": reason
        }
    
    # ==================== ORDERING SESSION ====================
    
    def start_session(
        self,
        kiosk_id: str,
        language: str = "en",
        accessibility_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Start a new ordering session at a kiosk
        """
        kiosk = self.kiosk_registry.get(kiosk_id)
        if not kiosk:
            return {"error": "Kiosk not found", "success": False}
        
        if kiosk["mode"] == KioskMode.MAINTENANCE.value:
            return {"error": "Kiosk is under maintenance", "success": False}
        
        session_id = f"KS-{uuid.uuid4().hex[:8].upper()}"
        
        session = {
            "session_id": session_id,
            "kiosk_id": kiosk_id,
            "venue_id": kiosk["venue_id"],
            "language": language,
            "accessibility_mode": accessibility_mode,
            "cart": [],
            "subtotal": 0,
            "tax": 0,
            "total": 0,
            "discounts": [],
            "upsells_shown": [],
            "upsells_accepted": [],
            "started_at": datetime.now(timezone.utc).isoformat(),
            "last_activity": datetime.now(timezone.utc).isoformat(),
            "timeout_seconds": 120,  # 2 minute inactivity timeout
            "step": "menu",
            "customer_id": None
        }
        
        self.active_sessions[session_id] = session
        kiosk["mode"] = KioskMode.ORDERING.value
        kiosk["session_count_today"] += 1
        
        # Get menu for display
        menu = self._get_kiosk_menu(kiosk["venue_id"], language)
        
        return {
            "success": True,
            "session_id": session_id,
            "menu": menu,
            "welcome_message": self._get_welcome_message(language),
            "featured_items": self._get_featured_items(kiosk["venue_id"]),
            "promotions": self._get_active_promotions(kiosk["venue_id"]),
            "accessibility": {
                "enabled": accessibility_mode,
                "font_size": "large" if accessibility_mode else "normal",
                "high_contrast": accessibility_mode,
                "voice_guidance": accessibility_mode
            }
        }
    
    def add_to_cart(
        self,
        session_id: str,
        item_id: int,
        quantity: int = 1,
        modifiers: Optional[List[Dict]] = None,
        special_instructions: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add an item to the kiosk cart
        """
        session = self.active_sessions.get(session_id)
        if not session:
            return {"error": "Session not found or expired", "success": False}
        
        # Update activity
        session["last_activity"] = datetime.now(timezone.utc).isoformat()
        
        # Get item details
        item = self._get_menu_item(item_id, session["language"])
        if not item:
            return {"error": "Item not found", "success": False}
        
        # Calculate item price with modifiers
        base_price = item.get("price", 0)
        modifier_price = sum(m.get("price", 0) for m in (modifiers or []))
        item_total = (base_price + modifier_price) * quantity
        
        cart_item = {
            "cart_item_id": str(uuid.uuid4()),
            "item_id": item_id,
            "name": item.get("name"),
            "quantity": quantity,
            "base_price": base_price,
            "modifiers": modifiers or [],
            "modifier_price": modifier_price,
            "special_instructions": special_instructions,
            "item_total": item_total,
            "image_url": item.get("image_url")
        }
        
        session["cart"].append(cart_item)
        self._recalculate_totals(session)
        
        # Generate upsell suggestions
        upsells = self._generate_upsell_suggestions(session, item)
        
        return {
            "success": True,
            "cart_item": cart_item,
            "cart": session["cart"],
            "subtotal": session["subtotal"],
            "tax": session["tax"],
            "total": session["total"],
            "item_count": sum(i["quantity"] for i in session["cart"]),
            "upsells": upsells
        }
    
    def update_cart_item(
        self,
        session_id: str,
        cart_item_id: str,
        quantity: Optional[int] = None,
        modifiers: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """Update a cart item"""
        session = self.active_sessions.get(session_id)
        if not session:
            return {"error": "Session not found", "success": False}
        
        session["last_activity"] = datetime.now(timezone.utc).isoformat()
        
        # Find cart item
        cart_item = next(
            (i for i in session["cart"] if i["cart_item_id"] == cart_item_id),
            None
        )
        
        if not cart_item:
            return {"error": "Cart item not found", "success": False}
        
        if quantity is not None:
            if quantity <= 0:
                # Remove item
                session["cart"] = [i for i in session["cart"] if i["cart_item_id"] != cart_item_id]
            else:
                cart_item["quantity"] = quantity
        
        if modifiers is not None:
            cart_item["modifiers"] = modifiers
            cart_item["modifier_price"] = sum(m.get("price", 0) for m in modifiers)
        
        # Recalculate item total
        if cart_item in session["cart"]:
            cart_item["item_total"] = (
                cart_item["base_price"] + cart_item["modifier_price"]
            ) * cart_item["quantity"]
        
        self._recalculate_totals(session)
        
        return {
            "success": True,
            "cart": session["cart"],
            "subtotal": session["subtotal"],
            "total": session["total"]
        }
    
    def remove_from_cart(
        self,
        session_id: str,
        cart_item_id: str
    ) -> Dict[str, Any]:
        """Remove an item from cart"""
        return self.update_cart_item(session_id, cart_item_id, quantity=0)
    
    # ==================== UPSELLING ENGINE ====================
    
    def _generate_upsell_suggestions(
        self,
        session: Dict,
        added_item: Dict
    ) -> List[Dict[str, Any]]:
        """
        Generate intelligent upsell suggestions based on cart contents
        """
        upsells = []
        cart_items = session["cart"]
        venue_id = session["venue_id"]
        
        # 1. Size upgrade upsell
        if added_item.get("has_sizes"):
            current_size = next(
                (m for m in (added_item.get("modifiers") or []) if m.get("type") == "size"),
                None
            )
            if current_size and current_size.get("value") != "large":
                upsells.append({
                    "type": UpsellType.SIZE_UPGRADE.value,
                    "message": self._get_upsell_message("size_upgrade", session["language"]),
                    "item_id": added_item["id"],
                    "upgrade_price": 1.00,
                    "display_priority": 1
                })
        
        # 2. Combo upsell
        combo = self._check_combo_opportunity(cart_items, venue_id)
        if combo:
            upsells.append({
                "type": UpsellType.COMBO.value,
                "message": self._get_upsell_message("combo", session["language"]),
                "combo_id": combo["id"],
                "combo_name": combo["name"],
                "savings": combo["savings"],
                "display_priority": 2
            })
        
        # 3. Add-on suggestions
        add_ons = self._get_complementary_items(added_item["id"], venue_id)
        for add_on in add_ons[:2]:
            upsells.append({
                "type": UpsellType.ADD_ON.value,
                "message": f"Add {add_on['name']}?",
                "item_id": add_on["id"],
                "item_name": add_on["name"],
                "price": add_on["price"],
                "image_url": add_on.get("image_url"),
                "display_priority": 3
            })
        
        # 4. Drink suggestion if no drinks in cart
        has_drink = any(
            self._is_drink_item(i["item_id"]) for i in cart_items
        )
        if not has_drink:
            drinks = self._get_popular_drinks(venue_id)
            if drinks:
                upsells.append({
                    "type": UpsellType.DRINK.value,
                    "message": self._get_upsell_message("drink", session["language"]),
                    "items": drinks[:3],
                    "display_priority": 4
                })
        
        # Track shown upsells
        session["upsells_shown"].extend([u["type"] for u in upsells])
        
        return sorted(upsells, key=lambda x: x.get("display_priority", 99))
    
    def accept_upsell(
        self,
        session_id: str,
        upsell_type: str,
        upsell_data: Dict
    ) -> Dict[str, Any]:
        """Accept an upsell offer"""
        session = self.active_sessions.get(session_id)
        if not session:
            return {"error": "Session not found", "success": False}
        
        session["upsells_accepted"].append({
            "type": upsell_type,
            "data": upsell_data,
            "accepted_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Handle different upsell types
        if upsell_type == UpsellType.SIZE_UPGRADE.value:
            # Apply size upgrade to item
            return self._apply_size_upgrade(session, upsell_data)
        
        elif upsell_type == UpsellType.COMBO.value:
            # Convert items to combo
            return self._apply_combo(session, upsell_data)
        
        elif upsell_type in [UpsellType.ADD_ON.value, UpsellType.DRINK.value]:
            # Add item to cart
            return self.add_to_cart(
                session_id,
                upsell_data.get("item_id"),
                quantity=1
            )
        
        return {"success": True}
    
    def decline_upsell(
        self,
        session_id: str,
        upsell_type: str
    ) -> Dict[str, Any]:
        """Track declined upsell for analytics"""
        session = self.active_sessions.get(session_id)
        if not session:
            return {"error": "Session not found", "success": False}
        
        # Just continue - used for conversion tracking
        return {"success": True, "message": "Continuing to checkout"}
    
    # ==================== CHECKOUT FLOW ====================
    
    def proceed_to_checkout(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Proceed to checkout screen
        """
        session = self.active_sessions.get(session_id)
        if not session:
            return {"error": "Session not found", "success": False}
        
        if not session["cart"]:
            return {"error": "Cart is empty", "success": False}
        
        session["step"] = "checkout"
        session["last_activity"] = datetime.now(timezone.utc).isoformat()
        
        # Final upsell opportunity (dessert)
        dessert_upsell = self._get_dessert_upsell(session)
        
        return {
            "success": True,
            "cart": session["cart"],
            "subtotal": session["subtotal"],
            "tax": session["tax"],
            "discounts": session["discounts"],
            "total": session["total"],
            "item_count": sum(i["quantity"] for i in session["cart"]),
            "final_upsell": dessert_upsell,
            "payment_methods": self._get_available_payment_methods(session["kiosk_id"]),
            "loyalty_prompt": self._should_prompt_loyalty(session)
        }
    
    def apply_loyalty_card(
        self,
        session_id: str,
        loyalty_identifier: str  # Phone, email, or card number
    ) -> Dict[str, Any]:
        """Apply loyalty card to order"""
        session = self.active_sessions.get(session_id)
        if not session:
            return {"error": "Session not found", "success": False}
        
        # Look up customer
        customer = self._lookup_loyalty_customer(loyalty_identifier)
        
        if not customer:
            return {
                "success": False,
                "error": "Loyalty account not found",
                "prompt_signup": True
            }
        
        session["customer_id"] = customer["id"]
        
        # Apply any available rewards/discounts
        rewards = self._get_available_rewards(customer["id"], session["total"])
        
        return {
            "success": True,
            "customer_name": customer.get("first_name", "Guest"),
            "points_balance": customer.get("points", 0),
            "tier": customer.get("tier", "Bronze"),
            "available_rewards": rewards,
            "points_to_earn": int(session["total"] * 10)  # 10 points per EUR
        }
    
    def apply_reward(
        self,
        session_id: str,
        reward_id: str
    ) -> Dict[str, Any]:
        """Apply a loyalty reward to the order"""
        session = self.active_sessions.get(session_id)
        if not session:
            return {"error": "Session not found", "success": False}
        
        # Get reward details
        reward = self._get_reward_details(reward_id)
        if not reward:
            return {"error": "Reward not found", "success": False}
        
        # Apply discount
        discount = {
            "type": "reward",
            "reward_id": reward_id,
            "description": reward.get("name"),
            "amount": reward.get("value", 0)
        }
        
        session["discounts"].append(discount)
        self._recalculate_totals(session)
        
        return {
            "success": True,
            "discount_applied": discount,
            "new_total": session["total"]
        }
    
    def process_payment(
        self,
        session_id: str,
        payment_method: str,
        payment_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Process kiosk payment
        """
        session = self.active_sessions.get(session_id)
        if not session:
            return {"error": "Session not found", "success": False}
        
        session["step"] = "payment"
        
        # Validate payment data based on method
        if payment_method == "card":
            # Initiate card payment on integrated reader
            return self._initiate_card_payment(session, payment_data)
        
        elif payment_method == "apple_pay":
            return self._initiate_mobile_payment(session, "apple_pay")
        
        elif payment_method == "google_pay":
            return self._initiate_mobile_payment(session, "google_pay")
        
        elif payment_method == "cash":
            # Generate cash payment code for POS
            return self._generate_cash_payment(session)
        
        elif payment_method == "qr_code":
            # Generate QR for mobile payment
            return self._generate_qr_payment(session)
        
        return {"error": "Invalid payment method", "success": False}
    
    def complete_order(
        self,
        session_id: str,
        payment_result: Dict
    ) -> Dict[str, Any]:
        """
        Complete the order after successful payment
        """
        session = self.active_sessions.get(session_id)
        if not session:
            return {"error": "Session not found", "success": False}
        
        if not payment_result.get("success"):
            return {
                "success": False,
                "error": "Payment failed",
                "retry_allowed": True
            }
        
        # Create order in system
        order = self._create_order_from_session(session, payment_result)
        
        # Update kiosk stats
        kiosk = self.kiosk_registry.get(session["kiosk_id"])
        if kiosk:
            kiosk["revenue_today"] += session["total"]
        
        # Track conversion
        self._track_conversion(session, order)
        
        # Clean up session
        del self.active_sessions[session_id]
        
        # Set kiosk back to idle
        if kiosk:
            kiosk["mode"] = KioskMode.IDLE.value
        
        return {
            "success": True,
            "order_number": order["order_number"],
            "order_id": order["id"],
            "estimated_time": order.get("estimated_time", 10),
            "receipt": self._generate_receipt(order),
            "thank_you_message": self._get_thank_you_message(session["language"]),
            "survey_link": self._generate_survey_link(order["id"])
        }
    
    # ==================== SESSION MANAGEMENT ====================
    
    def check_session_timeout(self, session_id: str) -> Dict[str, Any]:
        """Check if session has timed out"""
        session = self.active_sessions.get(session_id)
        if not session:
            return {"valid": False, "reason": "not_found"}
        
        last_activity = datetime.fromisoformat(session["last_activity"])
        elapsed = (datetime.now(timezone.utc) - last_activity).total_seconds()
        
        if elapsed > session["timeout_seconds"]:
            return {
                "valid": False,
                "reason": "timeout",
                "elapsed_seconds": elapsed
            }
        
        return {
            "valid": True,
            "seconds_remaining": session["timeout_seconds"] - elapsed
        }
    
    def extend_session(self, session_id: str) -> Dict[str, Any]:
        """Extend session timeout (user touched screen)"""
        session = self.active_sessions.get(session_id)
        if not session:
            return {"error": "Session not found", "success": False}
        
        session["last_activity"] = datetime.now(timezone.utc).isoformat()
        
        return {
            "success": True,
            "timeout_seconds": session["timeout_seconds"]
        }
    
    def cancel_session(
        self,
        session_id: str,
        reason: str = "user_cancelled"
    ) -> Dict[str, Any]:
        """Cancel and clean up a session"""
        session = self.active_sessions.get(session_id)
        if not session:
            return {"error": "Session not found", "success": False}
        
        # Track abandonment
        self._track_abandonment(session, reason)
        
        # Clean up
        del self.active_sessions[session_id]
        
        # Reset kiosk
        kiosk = self.kiosk_registry.get(session["kiosk_id"])
        if kiosk:
            kiosk["mode"] = KioskMode.IDLE.value
        
        return {
            "success": True,
            "message": "Session cancelled"
        }
    
    # ==================== ANALYTICS ====================
    
    def get_kiosk_analytics(
        self,
        venue_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get kiosk performance analytics"""
        # Get all kiosks for venue
        venue_kiosks = [
            k for k in self.kiosk_registry.values()
            if k.get("venue_id") == venue_id
        ]
        
        # Filter conversion data
        period_conversions = [
            c for c in self.conversion_data
            if start_date.isoformat() <= c.get("timestamp", "") <= end_date.isoformat()
            and c.get("venue_id") == venue_id
        ]
        
        completed = [c for c in period_conversions if c.get("completed")]
        abandoned = [c for c in period_conversions if not c.get("completed")]
        
        total_sessions = len(period_conversions)
        total_revenue = sum(c.get("total", 0) for c in completed)
        
        # Upsell analytics
        upsells_shown = sum(len(c.get("upsells_shown", [])) for c in period_conversions)
        upsells_accepted = sum(len(c.get("upsells_accepted", [])) for c in completed)
        
        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "kiosks": {
                "total": len(venue_kiosks),
                "active": len([k for k in venue_kiosks if k["status"] == "active"])
            },
            "sessions": {
                "total": total_sessions,
                "completed": len(completed),
                "abandoned": len(abandoned),
                "conversion_rate": (len(completed) / total_sessions * 100) if total_sessions else 0
            },
            "revenue": {
                "total": total_revenue,
                "average_order_value": (total_revenue / len(completed)) if completed else 0,
                "per_kiosk_per_day": self._calculate_revenue_per_kiosk(venue_kiosks, total_revenue, start_date, end_date)
            },
            "upselling": {
                "upsells_shown": upsells_shown,
                "upsells_accepted": upsells_accepted,
                "acceptance_rate": (upsells_accepted / upsells_shown * 100) if upsells_shown else 0,
                "upsell_revenue": sum(c.get("upsell_value", 0) for c in completed)
            },
            "abandonment": {
                "total": len(abandoned),
                "rate": (len(abandoned) / total_sessions * 100) if total_sessions else 0,
                "by_stage": self._analyze_abandonment_stages(abandoned),
                "avg_cart_value_abandoned": (
                    sum(a.get("cart_value", 0) for a in abandoned) / len(abandoned)
                ) if abandoned else 0
            },
            "popular_items": self._get_popular_kiosk_items(completed),
            "peak_hours": self._analyze_peak_hours(period_conversions),
            "avg_session_duration": self._calculate_avg_session_duration(period_conversions)
        }
    
    def get_realtime_kiosk_dashboard(
        self,
        venue_id: int
    ) -> Dict[str, Any]:
        """Get real-time kiosk dashboard"""
        venue_kiosks = [
            k for k in self.kiosk_registry.values()
            if k.get("venue_id") == venue_id
        ]
        
        active_sessions = [
            s for s in self.active_sessions.values()
            if s.get("venue_id") == venue_id
        ]
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "kiosks": [
                {
                    "kiosk_id": k["kiosk_id"],
                    "location": k["location"],
                    "status": k["status"],
                    "mode": k["mode"],
                    "sessions_today": k["session_count_today"],
                    "revenue_today": k["revenue_today"],
                    "last_heartbeat": k["last_heartbeat"]
                }
                for k in venue_kiosks
            ],
            "active_sessions": len(active_sessions),
            "total_in_carts": sum(s["total"] for s in active_sessions),
            "today_summary": {
                "sessions": sum(k["session_count_today"] for k in venue_kiosks),
                "revenue": sum(k["revenue_today"] for k in venue_kiosks)
            }
        }
    
    # ==================== HELPER METHODS ====================
    
    def _get_kiosk_configuration(self, venue_id: int) -> Dict:
        """Get kiosk configuration for venue"""
        return {
            "idle_timeout": 120,
            "checkout_timeout": 180,
            "default_language": "en",
            "available_languages": ["en", "bg", "de", "ru"],
            "show_calories": True,
            "show_allergens": True,
            "upsell_enabled": True,
            "loyalty_enabled": True,
            "tip_enabled": False,
            "theme": "ski_resort"
        }
    
    def _get_active_kiosk_session(self, kiosk_id: str) -> Optional[Dict]:
        """Get active session for a kiosk"""
        for session in self.active_sessions.values():
            if session.get("kiosk_id") == kiosk_id:
                return session
        return None
    
    def _end_kiosk_session(self, kiosk_id: str, reason: str):
        """End all sessions for a kiosk"""
        to_remove = [
            sid for sid, s in self.active_sessions.items()
            if s.get("kiosk_id") == kiosk_id
        ]
        for sid in to_remove:
            self.cancel_session(sid, reason)
    
    def _calculate_session_duration(self, session: Dict) -> int:
        """Calculate session duration in seconds"""
        if not session:
            return 0
        start = datetime.fromisoformat(session["started_at"])
        return int((datetime.now(timezone.utc) - start).total_seconds())
    
    def _calculate_uptime(self, kiosk_id: str) -> float:
        """Calculate kiosk uptime percentage for today"""
        from app.models import KioskStatusLog
        from sqlalchemy import func

        try:
            # Get today's start
            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

            # Query status logs for this kiosk today
            status_logs = self.db.query(KioskStatusLog).filter(
                KioskStatusLog.kiosk_id == kiosk_id,
                KioskStatusLog.created_at >= today_start
            ).order_by(KioskStatusLog.created_at).all()

            if not status_logs:
                # No logs today - assume 100% uptime if kiosk is registered
                kiosk = self.registered_kiosks.get(kiosk_id)
                if kiosk and kiosk.get("status") == "active":
                    return 100.0
                return 0.0

            # Calculate uptime based on status changes
            total_minutes = (datetime.now(timezone.utc) - today_start).total_seconds() / 60
            if total_minutes <= 0:
                return 100.0

            # Track downtime periods
            downtime_minutes = 0
            last_status = "active"
            last_time = today_start

            for log in status_logs:
                if last_status in ["offline", "error", "maintenance"]:
                    # Add downtime from last_time to this log
                    downtime_minutes += (log.created_at - last_time).total_seconds() / 60
                last_status = log.status
                last_time = log.created_at

            # Check if currently down
            if last_status in ["offline", "error", "maintenance"]:
                downtime_minutes += (datetime.now(timezone.utc) - last_time).total_seconds() / 60

            # Calculate uptime percentage
            uptime_minutes = total_minutes - downtime_minutes
            uptime_percent = (uptime_minutes / total_minutes) * 100

            return round(max(0, min(100, uptime_percent)), 2)

        except Exception as e:
            logger.warning(f"Failed to calculate uptime for kiosk {kiosk_id}: {e}")
            # Fallback to checking current status
            kiosk = self.registered_kiosks.get(kiosk_id)
            if kiosk and kiosk.get("status") == "active":
                return 99.0  # Assume high uptime if active
            return 0.0
    
    def _get_kiosk_menu(self, venue_id: int, language: str) -> Dict:
        """Get menu formatted for kiosk display"""
        from app.models import Menu, MenuVersion, MenuCategory, MenuItem

        try:
            # Get active published menu for venue
            menu = self.db.query(Menu).filter(
                Menu.venue_id == venue_id,
                Menu.active == True
            ).first()

            if not menu:
                return {"categories": []}

            # Get latest published version
            version = self.db.query(MenuVersion).filter(
                MenuVersion.menu_id == menu.id,
                MenuVersion.published == True
            ).order_by(MenuVersion.version_number.desc()).first()

            if not version:
                return {"categories": []}

            # Get categories with items
            categories = self.db.query(MenuCategory).filter(
                MenuCategory.version_id == version.id,
                MenuCategory.active == True
            ).order_by(MenuCategory.sort_order).all()

            result_categories = []
            for category in categories:
                items = self.db.query(MenuItem).filter(
                    MenuItem.category_id == category.id,
                    MenuItem.available == True
                ).order_by(MenuItem.sort_order).all()

                category_items = []
                for item in items:
                    category_items.append({
                        "id": item.id,
                        "name": item.name.get(language, str(item.name)) if isinstance(item.name, dict) else str(item.name),
                        "description": item.description.get(language, "") if isinstance(item.description, dict) else str(item.description or ""),
                        "price": float(item.price or 0),
                        "image_url": item.images[0].url if item.images else None,
                        "allergens": item.allergens or []
                    })

                result_categories.append({
                    "id": category.id,
                    "name": category.name.get(language, str(category.name)) if isinstance(category.name, dict) else str(category.name),
                    "description": category.description.get(language, "") if isinstance(category.description, dict) else str(category.description or ""),
                    "items": category_items
                })

            return {"categories": result_categories}
        except Exception as e:
            logger.warning(f"Failed to get kiosk menu for venue {venue_id} (language={language}): {e}")
            return {"categories": []}
    
    def _get_welcome_message(self, language: str) -> str:
        """Get welcome message in language"""
        messages = {
            "en": "Welcome! Touch to start ordering",
            "bg": "Добре дошли! Докоснете за поръчка",
            "de": "Willkommen! Tippen Sie, um zu bestellen",
            "ru": "Добро пожаловать! Нажмите для заказа"
        }
        return messages.get(language, messages["en"])
    
    def _get_featured_items(self, venue_id: int) -> List[Dict]:
        """Get featured items for kiosk"""
        from app.models import MenuItem, MenuCategory, ItemTag, ItemTagLink, OrderItem
        from sqlalchemy import func, desc

        try:
            # Get items tagged as "featured" or "popular"
            featured_tag_items = self.db.query(MenuItem).join(
                ItemTagLink
            ).join(
                ItemTag
            ).filter(
                MenuItem.available == True,
                ItemTag.name.in_(["featured", "popular", "new"])
            ).limit(6).all()

            if featured_tag_items:
                return [
                    {
                        "id": item.id,
                        "name": str(item.name),
                        "price": float(item.price or 0),
                        "image_url": item.images[0].url if item.images else None
                    }
                    for item in featured_tag_items
                ]

            # Fallback: get most ordered items
            popular_items = self.db.query(
                MenuItem,
                func.sum(OrderItem.quantity).label("total_qty")
            ).join(
                OrderItem
            ).filter(
                MenuItem.available == True
            ).group_by(
                MenuItem.id
            ).order_by(
                desc("total_qty")
            ).limit(6).all()

            return [
                {
                    "id": item.id,
                    "name": str(item.name),
                    "price": float(item.price or 0),
                    "image_url": item.images[0].url if item.images else None
                }
                for item, _ in popular_items
            ]
        except Exception as e:
            logger.warning(f"Failed to get featured items for venue {venue_id}: {e}")
            return []

    def _get_active_promotions(self, venue_id: int) -> List[Dict]:
        """Get active promotions"""
        from app.models import Promotion
        from datetime import datetime

        try:
            now = datetime.now(timezone.utc)
            promotions = self.db.query(Promotion).filter(
                Promotion.venue_id == venue_id,
                Promotion.is_active == True,
                Promotion.start_date <= now,
                Promotion.end_date >= now
            ).all()

            return [
                {
                    "id": promo.id,
                    "name": promo.name,
                    "description": promo.description,
                    "type": promo.promotion_type,
                    "discount_value": float(promo.discount_value or 0)
                }
                for promo in promotions
            ]
        except Exception as e:
            logger.warning(f"Failed to get active promotions for venue {venue_id}: {e}")
            return []

    def _get_menu_item(self, item_id: int, language: str) -> Optional[Dict]:
        """Get menu item details"""
        from app.models import MenuItem, ModifierGroup

        try:
            item = self.db.query(MenuItem).filter(MenuItem.id == item_id).first()

            if not item:
                return None

            # Check if item has size modifiers
            modifier_groups = self.db.query(ModifierGroup).filter(
                ModifierGroup.item_id == item_id
            ).all()

            has_sizes = any(
                "size" in group.name.get("en", "").lower()
                for group in modifier_groups
            )

            return {
                "id": item.id,
                "name": item.name.get(language, str(item.name)) if isinstance(item.name, dict) else str(item.name),
                "description": item.description.get(language, "") if isinstance(item.description, dict) else str(item.description or ""),
                "price": float(item.price or 0),
                "image_url": item.images[0].url if item.images else None,
                "has_sizes": has_sizes,
                "allergens": item.allergens or [],
                "category_id": item.category_id
            }
        except Exception as e:
            logger.warning(f"Failed to get menu item {item_id} (language={language}): {e}")
            return None

    def _recalculate_totals(self, session: Dict):
        """Recalculate session totals"""
        subtotal = sum(i["item_total"] for i in session["cart"])
        discount_total = sum(d.get("amount", 0) for d in session["discounts"])
        tax = (subtotal - discount_total) * 0.20  # 20% VAT
        
        session["subtotal"] = round(subtotal, 2)
        session["tax"] = round(tax, 2)
        session["total"] = round(subtotal - discount_total + tax, 2)
    
    def _get_upsell_message(self, upsell_type: str, language: str) -> str:
        """Get upsell message"""
        messages = {
            "size_upgrade": {
                "en": "Make it a large for just €1 more?",
                "bg": "Голям размер само за €1 повече?"
            },
            "combo": {
                "en": "Save with a combo deal!",
                "bg": "Спестете с комбо!"
            },
            "drink": {
                "en": "Add a drink to your order?",
                "bg": "Добавете напитка?"
            },
            "dessert": {
                "en": "Complete your meal with dessert?",
                "bg": "Завършете с десерт?"
            }
        }
        return messages.get(upsell_type, {}).get(language, "")
    
    def _check_combo_opportunity(self, cart: List[Dict], venue_id: int) -> Optional[Dict]:
        """Check if cart items could form a combo"""
        from app.models import ComboMenu, ComboMenuItem

        try:
            if not cart:
                return None

            cart_item_ids = [item["item_id"] for item in cart]

            # Get active combos for venue
            combos = self.db.query(ComboMenu).filter(
                ComboMenu.venue_id == venue_id,
                ComboMenu.is_available == True
            ).all()

            for combo in combos:
                # Get combo items
                combo_items = self.db.query(ComboMenuItem).filter(
                    ComboMenuItem.combo_id == combo.id
                ).all()

                # Check if cart has items that match the combo
                combo_item_ids = [ci.menu_item_id for ci in combo_items if ci.menu_item_id]

                # If cart contains all combo items
                if all(item_id in cart_item_ids for item_id in combo_item_ids):
                    # Calculate savings
                    individual_total = sum(
                        item["item_total"] for item in cart
                        if item["item_id"] in combo_item_ids
                    )
                    savings = individual_total - float(combo.combo_price or 0)

                    if savings > 0:
                        return {
                            "id": combo.id,
                            "name": str(combo.name),
                            "combo_price": float(combo.combo_price or 0),
                            "savings": round(savings, 2)
                        }

            return None
        except Exception as e:
            logger.warning(f"Failed to check combo opportunity for venue {venue_id} with {len(cart)} cart items: {e}")
            return None

    def _get_complementary_items(self, item_id: int, venue_id: int) -> List[Dict]:
        """Get items commonly ordered with this item"""
        from app.models import MenuItem, OrderItem, Order
        from sqlalchemy import func, and_, desc

        try:
            # Find orders that contain the given item
            orders_with_item = self.db.query(Order.id).join(
                OrderItem
            ).filter(
                OrderItem.menu_item_id == item_id
            ).subquery()

            # Find items frequently ordered together with this item
            complementary = self.db.query(
                MenuItem,
                func.count(OrderItem.id).label("frequency")
            ).join(
                OrderItem
            ).join(
                Order
            ).filter(
                and_(
                    Order.id.in_(orders_with_item),
                    MenuItem.id != item_id,
                    MenuItem.available == True
                )
            ).group_by(
                MenuItem.id
            ).order_by(
                desc("frequency")
            ).limit(5).all()

            return [
                {
                    "id": item.id,
                    "name": str(item.name),
                    "price": float(item.price or 0),
                    "image_url": item.images[0].url if item.images else None
                }
                for item, _ in complementary
            ]
        except Exception as e:
            logger.warning(f"Failed to get complementary items for item {item_id} in venue {venue_id}: {e}")
            return []

    def _is_drink_item(self, item_id: int) -> bool:
        """Check if item is a drink"""
        from app.models import MenuItem, MenuCategory

        try:
            item = self.db.query(MenuItem).filter(MenuItem.id == item_id).first()

            if not item:
                return False

            category = self.db.query(MenuCategory).filter(
                MenuCategory.id == item.category_id
            ).first()

            if not category:
                return False

            # Check if category name contains "drink", "beverage", "napitka", etc
            category_name = str(category.name).lower()
            drink_keywords = ["drink", "beverage", "napitka", "напитка", "getränk"]

            return any(keyword in category_name for keyword in drink_keywords)
        except Exception as e:
            logger.warning(f"Failed to check if item {item_id} is a drink: {e}")
            return False
    
    def _get_popular_drinks(self, venue_id: int) -> List[Dict]:
        """Get popular drinks"""
        from app.models import MenuItem, MenuCategory, OrderItem, Menu, MenuVersion
        from sqlalchemy import func, desc

        try:
            # Get menu and version for venue
            menu = self.db.query(Menu).filter(
                Menu.venue_id == venue_id,
                Menu.active == True
            ).first()

            if not menu:
                return []

            version = self.db.query(MenuVersion).filter(
                MenuVersion.menu_id == menu.id,
                MenuVersion.published == True
            ).order_by(MenuVersion.version_number.desc()).first()

            if not version:
                return []

            # Get drink categories
            drink_categories = self.db.query(MenuCategory).filter(
                MenuCategory.version_id == version.id,
                MenuCategory.active == True
            ).all()

            drink_category_ids = [
                cat.id for cat in drink_categories
                if any(
                    keyword in str(cat.name).lower()
                    for keyword in ["drink", "beverage", "napitka", "напитка", "getränk"]
                )
            ]

            if not drink_category_ids:
                return []

            # Get popular drinks from those categories
            popular_drinks = self.db.query(
                MenuItem,
                func.sum(OrderItem.quantity).label("total_qty")
            ).outerjoin(
                OrderItem
            ).filter(
                MenuItem.category_id.in_(drink_category_ids),
                MenuItem.available == True
            ).group_by(
                MenuItem.id
            ).order_by(
                desc("total_qty")
            ).limit(5).all()

            return [
                {
                    "id": item.id,
                    "name": str(item.name),
                    "price": float(item.price or 0),
                    "image_url": item.images[0].url if item.images else None
                }
                for item, _ in popular_drinks
            ]
        except Exception as e:
            logger.warning(f"Failed to get popular drinks for venue {venue_id}: {e}")
            return []

    def _apply_size_upgrade(self, session: Dict, data: Dict) -> Dict:
        """Apply size upgrade to cart item"""
        from app.models import MenuItem, MenuItemVariant

        try:
            cart_item_index = data.get("cart_item_index")
            new_size = data.get("new_size")  # e.g., "large", "xl"

            if cart_item_index is None or cart_item_index >= len(session["cart"]):
                return {"success": False, "error": "Invalid cart item index"}

            cart_item = session["cart"][cart_item_index]
            menu_item_id = cart_item.get("item_id")

            # Look up the size variant
            variant = self.db.query(MenuItemVariant).filter(
                MenuItemVariant.menu_item_id == menu_item_id,
                MenuItemVariant.size == new_size,
                MenuItemVariant.is_available == True
            ).first()

            if not variant:
                # Fallback: Try to find the base item and apply a price multiplier
                base_item = self.db.query(MenuItem).filter(
                    MenuItem.id == menu_item_id
                ).first()

                if not base_item:
                    return {"success": False, "error": "Item not found"}

                # Apply standard size upgrade prices
                size_multipliers = {
                    "medium": 1.0,
                    "large": 1.25,
                    "xl": 1.50,
                    "extra_large": 1.50
                }

                multiplier = size_multipliers.get(new_size.lower(), 1.0)
                original_price = cart_item.get("price", 0)
                new_price = round(original_price * multiplier, 2)
                price_diff = new_price - original_price

                # Update cart item
                cart_item["size"] = new_size
                cart_item["price"] = new_price
                cart_item["size_upgrade_applied"] = True

                # Recalculate cart total
                session["cart_total"] = sum(
                    item.get("price", 0) * item.get("quantity", 1)
                    for item in session["cart"]
                )

                return {
                    "success": True,
                    "new_size": new_size,
                    "price_difference": price_diff,
                    "new_item_price": new_price,
                    "new_cart_total": session["cart_total"]
                }

            # Use the variant
            old_price = cart_item.get("price", 0)
            cart_item["size"] = new_size
            cart_item["price"] = float(variant.price)
            cart_item["variant_id"] = variant.id
            cart_item["size_upgrade_applied"] = True

            # Recalculate cart total
            session["cart_total"] = sum(
                item.get("price", 0) * item.get("quantity", 1)
                for item in session["cart"]
            )

            return {
                "success": True,
                "new_size": new_size,
                "price_difference": float(variant.price) - old_price,
                "new_item_price": float(variant.price),
                "new_cart_total": session["cart_total"]
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _apply_combo(self, session: Dict, data: Dict) -> Dict:
        """Convert cart items to combo"""
        from app.models import ComboMenu, ComboMenuItem

        try:
            combo_id = data.get("combo_id")
            cart_item_indices = data.get("cart_item_indices", [])

            if not combo_id:
                return {"success": False, "error": "Combo ID required"}

            # Get combo details
            combo = self.db.query(ComboMenu).filter(
                ComboMenu.id == combo_id,
                ComboMenu.is_active == True
            ).first()

            if not combo:
                return {"success": False, "error": "Combo not found or not active"}

            # Get combo items
            combo_items = self.db.query(ComboMenuItem).filter(
                ComboMenuItem.combo_id == combo_id
            ).all()

            # Calculate original total of items being replaced
            original_total = 0
            items_to_remove = []

            for idx in sorted(cart_item_indices, reverse=True):
                if idx < len(session["cart"]):
                    item = session["cart"][idx]
                    original_total += item.get("price", 0) * item.get("quantity", 1)
                    items_to_remove.append(idx)

            # Remove items being converted to combo (in reverse order to maintain indices)
            for idx in items_to_remove:
                session["cart"].pop(idx)

            # Get combo price
            combo_price = float(combo.price) if combo.price else original_total * 0.85  # 15% discount if no price set

            # Add combo as a single cart item
            combo_cart_item = {
                "item_id": f"combo_{combo_id}",
                "is_combo": True,
                "combo_id": combo_id,
                "name": combo.name.get(session.get("language", "en"), str(combo.name)) if isinstance(combo.name, dict) else str(combo.name),
                "price": combo_price,
                "quantity": 1,
                "components": [
                    {
                        "menu_item_id": ci.menu_item_id,
                        "category_id": ci.category_id,
                        "quantity": ci.quantity or 1
                    } for ci in combo_items
                ],
                "original_items_total": original_total,
                "savings": max(0, original_total - combo_price)
            }

            session["cart"].append(combo_cart_item)

            # Recalculate cart total
            session["cart_total"] = sum(
                item.get("price", 0) * item.get("quantity", 1)
                for item in session["cart"]
            )

            return {
                "success": True,
                "combo_name": combo_cart_item["name"],
                "combo_price": combo_price,
                "original_total": original_total,
                "savings": combo_cart_item["savings"],
                "new_cart_total": session["cart_total"]
            }

        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _get_dessert_upsell(self, session: Dict) -> Optional[Dict]:
        """Get dessert upsell at checkout"""
        from app.models import MenuItem, MenuCategory, Menu, MenuVersion, OrderItem
        from sqlalchemy import func, desc

        try:
            # Check if cart already has dessert
            cart_item_ids = [item["item_id"] for item in session["cart"]]

            # Get dessert categories
            menu = self.db.query(Menu).filter(
                Menu.venue_id == session["venue_id"],
                Menu.active == True
            ).first()

            if not menu:
                return None

            version = self.db.query(MenuVersion).filter(
                MenuVersion.menu_id == menu.id,
                MenuVersion.published == True
            ).order_by(MenuVersion.version_number.desc()).first()

            if not version:
                return None

            dessert_categories = self.db.query(MenuCategory).filter(
                MenuCategory.version_id == version.id,
                MenuCategory.active == True
            ).all()

            dessert_category_ids = [
                cat.id for cat in dessert_categories
                if any(
                    keyword in str(cat.name).lower()
                    for keyword in ["dessert", "sweet", "десерт", "nachspeise"]
                )
            ]

            if not dessert_category_ids:
                return None

            # Check if already has dessert
            has_dessert = any(
                self._get_menu_item(item_id, session.get("language", "en")) and
                self._get_menu_item(item_id, session.get("language", "en")).get("category_id") in dessert_category_ids
                for item_id in cart_item_ids
            )

            if has_dessert:
                return None

            # Get most popular dessert
            popular_dessert = self.db.query(
                MenuItem,
                func.sum(OrderItem.quantity).label("total_qty")
            ).outerjoin(
                OrderItem
            ).filter(
                MenuItem.category_id.in_(dessert_category_ids),
                MenuItem.available == True
            ).group_by(
                MenuItem.id
            ).order_by(
                desc("total_qty")
            ).first()

            if popular_dessert:
                item, _ = popular_dessert
                return {
                    "type": UpsellType.DESSERT.value,
                    "message": self._get_upsell_message("dessert", session.get("language", "en")),
                    "item": {
                        "id": item.id,
                        "name": str(item.name),
                        "price": float(item.price or 0),
                        "image_url": item.images[0].url if item.images else None
                    }
                }

            return None
        except Exception as e:
            logger.warning(f"Failed to get dessert upsell for session (venue={session.get('venue_id')}): {e}")
            return None

    def _get_available_payment_methods(self, kiosk_id: str) -> List[str]:
        """Get available payment methods for kiosk"""
        return ["card", "apple_pay", "google_pay", "qr_code"]
    
    def _should_prompt_loyalty(self, session: Dict) -> bool:
        """Check if should prompt for loyalty card"""
        return session.get("customer_id") is None
    
    def _lookup_loyalty_customer(self, identifier: str) -> Optional[Dict]:
        """Look up loyalty customer"""
        from app.models import Customer

        try:
            # Try to find by phone or email
            customer = self.db.query(Customer).filter(
                (Customer.phone == identifier) | (Customer.email == identifier)
            ).first()

            if not customer:
                return None

            return {
                "id": customer.id,
                "name": customer.name,
                "first_name": customer.name.split()[0] if customer.name else "Guest",
                "email": customer.email,
                "phone": customer.phone,
                "points": customer.loyalty_points or 0,
                "tier": customer.loyalty_tier or "Bronze",
                "total_spent": float(customer.total_spent or 0),
                "total_orders": customer.total_orders or 0
            }
        except Exception as e:
            logger.warning(f"Failed to look up loyalty customer with identifier '{identifier}': {e}")
            return None

    def _get_available_rewards(self, customer_id: int, total: float = 0) -> List[Dict]:
        """Get available rewards for customer"""
        from app.models import Customer, Promotion
        from datetime import datetime

        try:
            customer = self.db.query(Customer).filter(Customer.id == customer_id).first()

            if not customer:
                return []

            rewards = []

            # Check if customer has enough loyalty points to redeem
            loyalty_points = customer.loyalty_points or 0

            # Point-based rewards (e.g., 100 points = $5 off)
            if loyalty_points >= 100:
                discount_amount = (loyalty_points // 100) * 5
                rewards.append({
                    "id": f"loyalty_points_{customer_id}",
                    "type": "loyalty_points",
                    "name": f"Loyalty Points Discount",
                    "description": f"Redeem {loyalty_points} points for ${discount_amount} off",
                    "points_required": 100,
                    "discount_value": discount_amount,
                    "value": discount_amount
                })

            # Check for any customer-specific promotions
            now = datetime.now(timezone.utc)
            promotions = self.db.query(Promotion).filter(
                Promotion.venue_id == customer.venue_id,
                Promotion.is_active == True,
                Promotion.start_date <= now,
                Promotion.end_date >= now,
                Promotion.min_purchase_amount <= total
            ).all()

            for promo in promotions:
                rewards.append({
                    "id": f"promo_{promo.id}",
                    "type": "promotion",
                    "name": promo.name,
                    "description": promo.description,
                    "discount_value": float(promo.discount_value or 0),
                    "value": float(promo.discount_value or 0)
                })

            return rewards
        except Exception as e:
            logger.warning(f"Failed to get available rewards for customer {customer_id} (total={total}): {e}")
            return []

    def _get_reward_details(self, reward_id: str) -> Optional[Dict]:
        """Get reward details"""
        from app.models import Promotion

        try:
            # Check if it's a promotion-based reward
            if reward_id.startswith("promo_"):
                promo_id = int(reward_id.replace("promo_", ""))
                promo = self.db.query(Promotion).filter(Promotion.id == promo_id).first()

                if promo:
                    return {
                        "id": reward_id,
                        "name": promo.name,
                        "type": "promotion",
                        "value": float(promo.discount_value or 0)
                    }

            # Check if it's a loyalty points reward
            if reward_id.startswith("loyalty_points_"):
                customer_id = int(reward_id.replace("loyalty_points_", ""))
                from app.models import Customer

                customer = self.db.query(Customer).filter(Customer.id == customer_id).first()

                if customer and customer.loyalty_points >= 100:
                    discount_amount = (customer.loyalty_points // 100) * 5
                    return {
                        "id": reward_id,
                        "name": "Loyalty Points Reward",
                        "type": "loyalty_points",
                        "value": discount_amount
                    }

            return None
        except Exception as e:
            logger.warning(f"Failed to get reward details for reward '{reward_id}': {e}")
            return None

    def _initiate_card_payment(self, session: Dict, data: Dict) -> Dict:
        """Initiate card payment"""
        return {
            "success": True,
            "action": "wait_for_card",
            "message": "Please insert or tap your card"
        }
    
    def _initiate_mobile_payment(self, session: Dict, provider: str) -> Dict:
        """Initiate mobile payment"""
        return {
            "success": True,
            "action": "present_device",
            "message": f"Hold your device near the reader for {provider}"
        }
    
    def _generate_cash_payment(self, session: Dict) -> Dict:
        """Generate cash payment code"""
        return {
            "success": True,
            "action": "pay_at_counter",
            "code": f"CASH-{uuid.uuid4().hex[:6].upper()}",
            "message": "Please pay at the counter with this code"
        }
    
    def _generate_qr_payment(self, session: Dict) -> Dict:
        """Generate QR code payment"""
        return {
            "success": True,
            "action": "scan_qr",
            "qr_data": f"bjs://pay/{session['session_id']}",
            "message": "Scan with your phone to pay"
        }
    
    def _create_order_from_session(self, session: Dict, payment: Dict) -> Dict:
        """Create order from kiosk session"""
        from app.models import Order, OrderItem, OrderItemModifier, OrderEvent, VenueStation
        from datetime import datetime, timedelta, timezone

        try:
            # Get venue's default station (or kiosk station)
            station = self.db.query(VenueStation).filter(
                VenueStation.venue_id == session["venue_id"],
                VenueStation.active == True
            ).first()

            if not station:
                # Fallback to creating a minimal response without DB insertion
                return {
                    "id": str(uuid.uuid4()),
                    "order_number": f"K{datetime.now(timezone.utc).strftime('%H%M%S')}",
                    "items": session["cart"],
                    "total": session["total"],
                    "estimated_time": 10
                }

            # Generate order number
            order_number = f"KIOSK-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"

            # Create order
            new_order = Order(
                table_id=None,  # Kiosk orders don't have table
                station_id=station.id,
                order_number=order_number,
                order_type="kiosk",
                status="new",
                total=session["total"],
                tip_amount=0,
                payment_method=payment.get("method", "card"),
                payment_status="paid",
                payment_date=datetime.now(timezone.utc),
                customer_name=session.get("customer_name"),
                customer_phone=session.get("customer_phone"),
                estimated_ready_time=datetime.now(timezone.utc) + timedelta(minutes=10),
                notes=f"Kiosk order - Session: {session['session_id']}"
            )

            self.db.add(new_order)
            self.db.flush()  # Get order ID

            # Create order items
            for cart_item in session["cart"]:
                order_item = OrderItem(
                    order_id=new_order.id,
                    menu_item_id=cart_item["item_id"],
                    quantity=cart_item["quantity"],
                    unit_price=cart_item["base_price"],
                    subtotal=cart_item["item_total"],
                    notes=cart_item.get("special_instructions")
                )
                self.db.add(order_item)
                self.db.flush()

                # Add modifiers if any
                for modifier in cart_item.get("modifiers", []):
                    if modifier.get("option_id"):
                        order_modifier = OrderItemModifier(
                            order_item_id=order_item.id,
                            modifier_option_id=modifier["option_id"],
                            price_delta=modifier.get("price", 0)
                        )
                        self.db.add(order_modifier)

            # Create order event
            order_event = OrderEvent(
                order_id=new_order.id,
                status="new",
                notes="Order created via self-service kiosk"
            )
            self.db.add(order_event)

            # Update customer loyalty points if applicable
            if session.get("customer_id"):
                from app.models import Customer, LoyaltyTransaction

                customer = self.db.query(Customer).filter(
                    Customer.id == session["customer_id"]
                ).first()

                if customer:
                    # Award points (10 points per currency unit)
                    points_earned = int(session["total"] * 10)
                    customer.loyalty_points = (customer.loyalty_points or 0) + points_earned
                    customer.total_orders = (customer.total_orders or 0) + 1
                    customer.total_spent = (customer.total_spent or 0) + session["total"]
                    customer.last_visit = datetime.now(timezone.utc)

                    # Create loyalty transaction
                    loyalty_txn = LoyaltyTransaction(
                        customer_id=customer.id,
                        order_id=new_order.id,
                        transaction_type="earn",
                        points=points_earned,
                        balance_after=customer.loyalty_points,
                        description=f"Earned from kiosk order {order_number}"
                    )
                    self.db.add(loyalty_txn)

            self.db.commit()

            return {
                "id": new_order.id,
                "order_number": new_order.order_number,
                "items": session["cart"],
                "total": session["total"],
                "estimated_time": 10,
                "status": "new"
            }
        except Exception as e:
            self.db.rollback()
            # Return fallback response
            return {
                "id": str(uuid.uuid4()),
                "order_number": f"K{datetime.now(timezone.utc).strftime('%H%M%S')}",
                "items": session["cart"],
                "total": session["total"],
                "estimated_time": 10,
                "error": str(e)
            }
    
    def _track_conversion(self, session: Dict, order: Dict):
        """Track successful conversion"""
        self.conversion_data.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "venue_id": session["venue_id"],
            "kiosk_id": session["kiosk_id"],
            "session_id": session["session_id"],
            "completed": True,
            "total": session["total"],
            "items": len(session["cart"]),
            "upsells_shown": session["upsells_shown"],
            "upsells_accepted": session["upsells_accepted"],
            "duration": self._calculate_session_duration(session)
        })
    
    def _track_abandonment(self, session: Dict, reason: str):
        """Track session abandonment"""
        self.conversion_data.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "venue_id": session["venue_id"],
            "kiosk_id": session["kiosk_id"],
            "session_id": session["session_id"],
            "completed": False,
            "cart_value": session["total"],
            "stage": session["step"],
            "reason": reason,
            "upsells_shown": session["upsells_shown"],
            "duration": self._calculate_session_duration(session)
        })
    
    def _generate_receipt(self, order: Dict) -> Dict:
        """Generate receipt data"""
        return {
            "order_number": order["order_number"],
            "items": order["items"],
            "total": order["total"],
            "payment_method": "Card",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def _get_thank_you_message(self, language: str) -> str:
        """Get thank you message"""
        messages = {
            "en": "Thank you for your order!",
            "bg": "Благодарим за поръчката!",
            "de": "Vielen Dank für Ihre Bestellung!",
            "ru": "Спасибо за заказ!"
        }
        return messages.get(language, messages["en"])
    
    def _generate_survey_link(self, order_id: str) -> str:
        """Generate feedback survey link"""
        return f"https://bjsbar.bg/feedback/{order_id}"
    
    def _calculate_revenue_per_kiosk(self, kiosks, total, start, end) -> float:
        """Calculate daily revenue per kiosk"""
        days = max(1, (end - start).days)
        return (total / len(kiosks) / days) if kiosks else 0
    
    def _analyze_abandonment_stages(self, abandoned: List) -> Dict:
        """Analyze at which stage orders were abandoned"""
        stages = {}
        for a in abandoned:
            stage = a.get("stage", "unknown")
            stages[stage] = stages.get(stage, 0) + 1
        return stages
    
    def _get_popular_kiosk_items(self, completed: List) -> List:
        """Get most popular items ordered via kiosk"""
        from app.models import MenuItem, Order, OrderItem
        from sqlalchemy import func, desc

        try:
            # Get most ordered items from kiosk orders
            popular_items = self.db.query(
                MenuItem.id,
                MenuItem.name,
                func.count(OrderItem.id).label("order_count"),
                func.sum(OrderItem.quantity).label("total_quantity"),
                func.sum(OrderItem.subtotal).label("total_revenue")
            ).join(
                OrderItem
            ).join(
                Order
            ).filter(
                Order.order_type == "kiosk"
            ).group_by(
                MenuItem.id,
                MenuItem.name
            ).order_by(
                desc("total_quantity")
            ).limit(10).all()

            return [
                {
                    "item_id": item.id,
                    "name": str(item.name),
                    "order_count": item.order_count,
                    "total_quantity": item.total_quantity,
                    "revenue": float(item.total_revenue or 0)
                }
                for item in popular_items
            ]
        except Exception as e:
            logger.warning(f"Failed to get popular kiosk items: {e}")
            return []

    def _analyze_peak_hours(self, conversions: List) -> List:
        """Analyze peak ordering hours"""
        from collections import defaultdict
        from datetime import datetime

        try:
            # Group conversions by hour
            hourly_counts = defaultdict(int)

            for conversion in conversions:
                timestamp_str = conversion.get("timestamp")
                if timestamp_str:
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str)
                        hour = timestamp.hour
                        hourly_counts[hour] += 1
                    except Exception as e:
                        logger.warning(f"Failed to parse conversion timestamp '{timestamp_str}': {e}")
                        continue

            # Convert to sorted list
            peak_hours = [
                {
                    "hour": hour,
                    "count": count,
                    "percentage": (count / len(conversions) * 100) if conversions else 0
                }
                for hour, count in sorted(hourly_counts.items(), key=lambda x: x[1], reverse=True)
            ]

            return peak_hours[:10]  # Top 10 peak hours
        except Exception as e:
            logger.warning(f"Failed to analyze peak hours from {len(conversions)} conversions: {e}")
            return []
    
    def _calculate_avg_session_duration(self, conversions: List) -> float:
        """Calculate average session duration"""
        durations = [c.get("duration", 0) for c in conversions]
        return sum(durations) / len(durations) if durations else 0
    
    # ==================== API ENDPOINT METHODS ====================
    
    def select_language(self, session_id: str, language: str) -> Dict[str, Any]:
        """Select language for the kiosk session"""
        if session_id not in self.active_sessions:
            return {"success": False, "error": "Session not found"}
        
        session = self.active_sessions[session_id]
        session["language"] = language
        session["state"] = "order_type_select"
        
        return {
            "success": True,
            "session_id": session_id,
            "language": language,
            "next_step": "order_type_select",
            "prompts": {
                "dine_in": self._get_text("Dine In", language),
                "takeaway": self._get_text("Takeaway", language)
            }
        }
    
    def _get_text(self, key: str, language: str) -> str:
        """Get translated text"""
        translations = {
            "Dine In": {"en": "Dine In", "bg": "На място", "de": "Hier essen", "ru": "На месте"},
            "Takeaway": {"en": "Takeaway", "bg": "За вкъщи", "de": "Mitnehmen", "ru": "С собой"}
        }
        return translations.get(key, {}).get(language, key)
    
    def select_order_type(self, session_id: str, order_type: str) -> Dict[str, Any]:
        """Select dine-in or takeaway"""
        if session_id not in self.active_sessions:
            return {"success": False, "error": "Session not found"}
        
        session = self.active_sessions[session_id]
        session["order_type"] = order_type
        session["state"] = "browsing"
        
        return {
            "success": True,
            "session_id": session_id,
            "order_type": order_type,
            "next_step": "browsing",
            "menu": self._get_kiosk_menu(session["venue_id"], session.get("language", "en"))
        }
    
    def get_cart(self, session_id: str) -> Dict[str, Any]:
        """Get current cart contents"""
        if session_id not in self.active_sessions:
            return {"success": False, "error": "Session not found"}
        
        session = self.active_sessions[session_id]
        
        return {
            "success": True,
            "session_id": session_id,
            "cart": session.get("cart", []),
            "subtotal": session.get("subtotal", 0),
            "tax": session.get("tax", 0),
            "total": session.get("total", 0),
            "item_count": len(session.get("cart", [])),
            "discounts": session.get("discounts", [])
        }
    
    def respond_to_upsell(
        self,
        session_id: str,
        accepted: bool,
        upsell_item_id: Optional[int] = None,
        quantity: int = 1
    ) -> Dict[str, Any]:
        """Handle upsell acceptance or rejection"""
        if session_id not in self.active_sessions:
            return {"success": False, "error": "Session not found"}
        
        session = self.active_sessions[session_id]
        
        if accepted and upsell_item_id:
            # Add upsell item to cart
            item = self._get_menu_item(upsell_item_id, session.get("language", "en"))
            if item:
                cart_item = {
                    "cart_item_id": f"upsell_{len(session['cart'])}",
                    "item_id": upsell_item_id,
                    "name": item["name"],
                    "quantity": quantity,
                    "unit_price": item["price"],
                    "item_total": item["price"] * quantity,
                    "is_upsell": True
                }
                session["cart"].append(cart_item)
                self._recalculate_totals(session)
                session["upsells_accepted"] = session.get("upsells_accepted", 0) + 1
        
        return {
            "success": True,
            "accepted": accepted,
            "cart": self.get_cart(session_id)
        }
    
    def get_category(self, session_id: str, category_id: int) -> Dict[str, Any]:
        """Get items in a category"""
        if session_id not in self.active_sessions:
            return {"success": False, "error": "Session not found"}
        
        session = self.active_sessions[session_id]
        language = session.get("language", "en")
        
        # Get category items from database
        from app.models import MenuItem, MenuCategory
        
        try:
            category = self.db.query(MenuCategory).filter(
                MenuCategory.id == category_id
            ).first()
            
            items = self.db.query(MenuItem).filter(
                MenuItem.category_id == category_id,
                MenuItem.is_available == True
            ).all()
            
            return {
                "success": True,
                "category_id": category_id,
                "category_name": category.name.get(language, str(category.name)) if category else "Unknown",
                "items": [{
                    "id": item.id,
                    "name": item.name.get(language, str(item.name)) if isinstance(item.name, dict) else str(item.name),
                    "price": float(item.price or 0),
                    "image_url": item.image_url,
                    "description": item.description.get(language, "") if isinstance(item.description, dict) else str(item.description or "")
                } for item in items]
            }
        except Exception as e:
            logger.warning(f"Failed to get category {category_id} (language={language}): {e}")
            return {
                "success": True,
                "category_id": category_id,
                "category_name": "Category",
                "items": []
            }
    
    def get_item_detail(self, session_id: str, item_id: int) -> Dict[str, Any]:
        """Get detailed item view with customization options"""
        if session_id not in self.active_sessions:
            return {"success": False, "error": "Session not found"}
        
        session = self.active_sessions[session_id]
        language = session.get("language", "en")
        
        from app.models import MenuItem, MenuItemModifier
        
        try:
            item = self.db.query(MenuItem).filter(MenuItem.id == item_id).first()
            
            if not item:
                return {"success": False, "error": "Item not found"}
            
            modifiers = self.db.query(MenuItemModifier).filter(
                MenuItemModifier.menu_item_id == item_id
            ).all()
            
            return {
                "success": True,
                "item": {
                    "id": item.id,
                    "name": item.name.get(language, str(item.name)) if isinstance(item.name, dict) else str(item.name),
                    "description": item.description.get(language, "") if isinstance(item.description, dict) else str(item.description or ""),
                    "price": float(item.price or 0),
                    "image_url": item.image_url,
                    "allergens": item.allergens if hasattr(item, 'allergens') else [],
                    "calories": item.calories if hasattr(item, 'calories') else None
                },
                "customizations": [{
                    "id": mod.id,
                    "name": mod.name,
                    "options": mod.options,
                    "is_required": mod.is_required,
                    "max_selections": mod.max_selections if hasattr(mod, 'max_selections') else 1
                } for mod in modifiers]
            }
        except Exception as e:
            logger.warning(f"Failed to get item detail for item {item_id} (language={language}): {e}")
            return {
                "success": True,
                "item": self._get_menu_item(item_id, language),
                "customizations": []
            }
    
    def verify_age(self, session_id: str, birth_year: int) -> Dict[str, Any]:
        """Verify customer age for alcohol"""
        if session_id not in self.active_sessions:
            return {"success": False, "error": "Session not found"}
        
        from datetime import datetime
        current_year = datetime.now(timezone.utc).year
        age = current_year - birth_year
        
        session = self.active_sessions[session_id]
        
        if age >= 18:
            session["age_verified"] = True
            return {
                "success": True,
                "verified": True,
                "age": age,
                "message": "Age verified. You can order alcohol."
            }
        else:
            session["age_verified"] = False
            return {
                "success": True,
                "verified": False,
                "age": age,
                "message": "Sorry, you must be 18 or older to order alcohol."
            }
    
    def apply_loyalty(
        self,
        session_id: str,
        phone_number: Optional[str] = None,
        loyalty_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """Apply loyalty program to order"""
        if session_id not in self.active_sessions:
            return {"success": False, "error": "Session not found"}
        
        session = self.active_sessions[session_id]
        
        # Look up customer by phone or code
        from app.models import Customer, LoyaltyCard
        
        try:
            customer = None
            loyalty = None
            
            if phone_number:
                customer = self.db.query(Customer).filter(
                    Customer.phone == phone_number
                ).first()
            elif loyalty_code:
                loyalty = self.db.query(LoyaltyCard).filter(
                    LoyaltyCard.card_number == loyalty_code
                ).first()
                if loyalty:
                    customer = self.db.query(Customer).filter(
                        Customer.id == loyalty.customer_id
                    ).first()
            
            if customer:
                session["customer_id"] = customer.id
                session["loyalty_points"] = getattr(customer, 'loyalty_points', 0)
                
                return {
                    "success": True,
                    "customer_found": True,
                    "customer_name": customer.name,
                    "loyalty_points": session["loyalty_points"],
                    "available_rewards": self._get_available_rewards(customer.id)
                }
            else:
                return {
                    "success": True,
                    "customer_found": False,
                    "message": "Customer not found. Would you like to create an account?"
                }
        except Exception as e:
            logger.warning(f"Failed to apply loyalty lookup (phone={phone_number}, code={loyalty_code}): {e}")
            return {"success": False, "error": "Unable to look up loyalty information"}

    def get_accessibility_config(self, session_id: str) -> Dict[str, Any]:
        """Get accessibility settings for kiosk session"""
        if session_id not in self.active_sessions:
            return {"success": False, "error": "Session not found"}
        
        session = self.active_sessions[session_id]
        
        # Default accessibility settings
        default_settings = {
            "high_contrast": False,
            "large_text": False,
            "screen_reader": False,
            "audio_feedback": False,
            "extended_timeout": False,
            "simplified_ui": False
        }
        
        current_settings = session.get("accessibility", default_settings)
        
        return {
            "success": True,
            "session_id": session_id,
            "settings": current_settings,
            "available_options": list(default_settings.keys())
        }
    
    def update_accessibility(
        self,
        session_id: str,
        settings: Dict[str, bool]
    ) -> Dict[str, Any]:
        """Update accessibility settings for session"""
        if session_id not in self.active_sessions:
            return {"success": False, "error": "Session not found"}
        
        session = self.active_sessions[session_id]
        
        if "accessibility" not in session:
            session["accessibility"] = {}
        
        # Update only valid settings
        valid_settings = [
            "high_contrast", "large_text", "screen_reader",
            "audio_feedback", "extended_timeout", "simplified_ui"
        ]
        
        for key, value in settings.items():
            if key in valid_settings:
                session["accessibility"][key] = value
        
        # Extend timeout if requested
        if settings.get("extended_timeout"):
            session["timeout_minutes"] = 10  # Extended from default 3
        
        return {
            "success": True,
            "session_id": session_id,
            "settings": session["accessibility"],
            "message": "Accessibility settings updated"
        }

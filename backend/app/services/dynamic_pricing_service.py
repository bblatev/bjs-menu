"""
Dynamic Pricing Service
Implements intelligent pricing strategies:
- Weather-based price adjustments (ski resort specific)
- Time-of-day pricing (après-ski hours, happy hour)
- Demand-based pricing
- Seasonal pricing calendars
- Happy hour automation
"""

from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
import logging
from enum import Enum

from app.models import MenuItem, Order, OrderItem

logger = logging.getLogger(__name__)


class PricingStrategy(str, Enum):
    FIXED = "fixed"
    TIME_BASED = "time_based"
    WEATHER_BASED = "weather_based"
    DEMAND_BASED = "demand_based"
    SEASONAL = "seasonal"
    HAPPY_HOUR = "happy_hour"


class DynamicPricingService:
    """Advanced dynamic pricing engine"""
    
    def __init__(self, db: Session):
        self.db = db
        
    # ==================== CORE PRICING ENGINE ====================
    
    def calculate_dynamic_price(
        self,
        item_id: int,
        venue_id: int,
        quantity: int = 1,
        current_time: Optional[datetime] = None,
        weather_data: Optional[Dict] = None
    ) -> Dict:
        """
        Calculate final price with all applicable adjustments
        Returns price breakdown showing all applied rules
        """
        if not current_time:
            current_time = datetime.now()
        
        # Get base item
        item = self.db.query(MenuItem).filter(
            MenuItem.id == item_id,
            MenuItem.venue_id == venue_id
        ).first()
        
        if not item:
            raise ValueError(f"Item {item_id} not found")
        
        base_price = float(item.price)
        final_price = base_price
        adjustments = []
        
        # Apply time-based pricing
        time_adjustment = self._calculate_time_based_adjustment(
            item_id, venue_id, current_time
        )
        if time_adjustment:
            adjustment_amount = base_price * (time_adjustment['multiplier'] - 1)
            final_price += adjustment_amount
            adjustments.append({
                'type': 'time_based',
                'rule': time_adjustment['rule_name'],
                'multiplier': time_adjustment['multiplier'],
                'amount': adjustment_amount,
                'reason': time_adjustment['reason']
            })
        
        # Apply weather-based pricing
        if weather_data:
            weather_adjustment = self._calculate_weather_based_adjustment(
                item_id, venue_id, weather_data
            )
            if weather_adjustment:
                adjustment_amount = base_price * (weather_adjustment['multiplier'] - 1)
                final_price += adjustment_amount
                adjustments.append({
                    'type': 'weather_based',
                    'rule': weather_adjustment['rule_name'],
                    'multiplier': weather_adjustment['multiplier'],
                    'amount': adjustment_amount,
                    'reason': weather_adjustment['reason']
                })
        
        # Apply demand-based pricing
        demand_adjustment = self._calculate_demand_based_adjustment(
            item_id, venue_id, current_time
        )
        if demand_adjustment:
            adjustment_amount = base_price * (demand_adjustment['multiplier'] - 1)
            final_price += adjustment_amount
            adjustments.append({
                'type': 'demand_based',
                'multiplier': demand_adjustment['multiplier'],
                'amount': adjustment_amount,
                'reason': demand_adjustment['reason']
            })
        
        # Apply seasonal pricing
        seasonal_adjustment = self._calculate_seasonal_adjustment(
            item_id, venue_id, current_time
        )
        if seasonal_adjustment:
            adjustment_amount = base_price * (seasonal_adjustment['multiplier'] - 1)
            final_price += adjustment_amount
            adjustments.append({
                'type': 'seasonal',
                'season': seasonal_adjustment['season'],
                'multiplier': seasonal_adjustment['multiplier'],
                'amount': adjustment_amount,
                'reason': seasonal_adjustment['reason']
            })
        
        # Ensure price doesn't go below minimum
        min_price = base_price * 0.5  # Never discount more than 50%
        max_price = base_price * 2.0  # Never increase more than 2x
        final_price = max(min_price, min(final_price, max_price))
        
        # Round to 2 decimal places
        final_price = round(final_price, 2)
        total_price = final_price * quantity
        
        return {
            'item_id': item_id,
            'item_name': item.name,
            'base_price': base_price,
            'final_price': final_price,
            'quantity': quantity,
            'total_price': total_price,
            'adjustments': adjustments,
            'total_discount': base_price - final_price if final_price < base_price else 0,
            'total_surcharge': final_price - base_price if final_price > base_price else 0,
            'timestamp': current_time.isoformat()
        }
    
    # ==================== TIME-BASED PRICING ====================
    
    def _calculate_time_based_adjustment(
        self,
        item_id: int,
        venue_id: int,
        current_time: datetime
    ) -> Optional[Dict]:
        """
        Calculate time-based pricing adjustment
        - Happy Hour (16:00-19:00): 20% off drinks (APRÈS-SKI)
        - Peak Hours (12:00-14:00, 19:00-21:00): 10% surcharge
        - Off-Peak (15:00-17:00): 15% off food
        """
        hour = current_time.hour
        minute = current_time.minute
        current_minutes = hour * 60 + minute
        
        # Get item category to determine applicability
        item = self.db.query(MenuItem).filter(MenuItem.id == item_id).first()
        if not item:
            return None
        
        category_name = item.category.name.get('en', '').lower() if item.category else ''
        
        # APRÈS-SKI HAPPY HOUR (4-7 PM) - 20% off drinks
        if 16 * 60 <= current_minutes < 19 * 60:
            if any(drink in category_name for drink in ['drink', 'beer', 'wine', 'cocktail', 'beverage']):
                return {
                    'rule_name': 'apres_ski_happy_hour',
                    'multiplier': 0.8,  # 20% off
                    'reason': '🎿 Après-ski Happy Hour Special!',
                    'time_range': '16:00-19:00'
                }
        
        # PEAK LUNCH HOUR (12-2 PM) - 10% surcharge on popular items
        if 12 * 60 <= current_minutes < 14 * 60:
            # Check if item is popular
            is_popular = self._is_item_popular(item_id, venue_id)
            if is_popular:
                return {
                    'rule_name': 'peak_lunch_surcharge',
                    'multiplier': 1.1,  # 10% surcharge
                    'reason': 'Peak hour pricing',
                    'time_range': '12:00-14:00'
                }
        
        # OFF-PEAK AFTERNOON (3-4 PM) - 15% off food
        if 15 * 60 <= current_minutes < 16 * 60:
            if 'food' in category_name or 'meal' in category_name:
                return {
                    'rule_name': 'off_peak_discount',
                    'multiplier': 0.85,  # 15% off
                    'reason': 'Afternoon special',
                    'time_range': '15:00-16:00'
                }
        
        # PEAK DINNER (7-9 PM) - 10% surcharge on mains
        if 19 * 60 <= current_minutes < 21 * 60:
            if any(main in category_name for main in ['main', 'dinner', 'entree']):
                is_popular = self._is_item_popular(item_id, venue_id)
                if is_popular:
                    return {
                        'rule_name': 'peak_dinner_surcharge',
                        'multiplier': 1.1,  # 10% surcharge
                        'reason': 'Peak dinner hour',
                        'time_range': '19:00-21:00'
                    }
        
        return None
    
    def _is_item_popular(self, item_id: int, venue_id: int, days: int = 7) -> bool:
        """Check if item is in top 20% most ordered items"""
        since_date = datetime.now() - timedelta(days=days)
        
        # Get order count for this item
        item_orders = self.db.query(func.count(OrderItem.id)).join(Order).filter(
            OrderItem.menu_item_id == item_id,
            Order.venue_id == venue_id,
            Order.created_at >= since_date
        ).scalar() or 0
        
        # Get total orders
        total_orders = self.db.query(func.count(OrderItem.id)).join(Order).filter(
            Order.venue_id == venue_id,
            Order.created_at >= since_date
        ).scalar() or 1
        
        # Popular if more than average orders
        avg_orders = total_orders / max(1, self.db.query(func.count(MenuItem.id)).filter(
            MenuItem.venue_id == venue_id
        ).scalar())
        
        return item_orders > avg_orders * 1.5
    
    # ==================== WEATHER-BASED PRICING ====================
    
    def _calculate_weather_based_adjustment(
        self,
        item_id: int,
        venue_id: int,
        weather_data: Dict
    ) -> Optional[Dict]:
        """
        Weather-based pricing for ski resort
        - Cold/snowy weather: increase hot drinks, soups (+15%)
        - Sunny weather: increase cold drinks, ice cream (+10%)
        - Heavy snow: discount desserts to move inventory (-10%)
        """
        temp = weather_data.get('temp', 10)
        condition = weather_data.get('condition', '').lower()
        
        item = self.db.query(MenuItem).filter(MenuItem.id == item_id).first()
        if not item:
            return None
        
        item_name = item.name.get('en', '').lower() if isinstance(item.name, dict) else str(item.name).lower()
        category_name = item.category.name.get('en', '').lower() if item.category else ''
        
        # COLD WEATHER (below 0°C) - Increase hot items
        if temp < 0:
            hot_keywords = ['hot', 'warm', 'soup', 'tea', 'coffee', 'chocolate', 'mulled']
            if any(keyword in item_name or keyword in category_name for keyword in hot_keywords):
                return {
                    'rule_name': 'cold_weather_boost',
                    'multiplier': 1.15,  # 15% increase
                    'reason': f'Perfect for {temp}°C weather',
                    'weather': weather_data
                }
        
        # SNOWY WEATHER - Increase comfort food
        if 'snow' in condition:
            comfort_keywords = ['comfort', 'hearty', 'stew', 'pasta', 'burger']
            if any(keyword in item_name or keyword in category_name for keyword in comfort_keywords):
                return {
                    'rule_name': 'snowy_day_special',
                    'multiplier': 1.12,  # 12% increase
                    'reason': 'Snowy day comfort food',
                    'weather': weather_data
                }
        
        # WARM WEATHER (above 10°C) - Increase cold items
        if temp > 10:
            cold_keywords = ['cold', 'ice', 'frozen', 'refreshing', 'salad', 'beer']
            if any(keyword in item_name or keyword in category_name for keyword in cold_keywords):
                return {
                    'rule_name': 'warm_weather_boost',
                    'multiplier': 1.10,  # 10% increase
                    'reason': f'Refreshing on {temp}°C day',
                    'weather': weather_data
                }
        
        return None
    
    # ==================== DEMAND-BASED PRICING ====================
    
    def _calculate_demand_based_adjustment(
        self,
        item_id: int,
        venue_id: int,
        current_time: datetime
    ) -> Optional[Dict]:
        """
        Demand-based pricing based on recent order velocity
        High demand (orders > 2x average): +15%
        Low demand (orders < 0.5x average): -10%
        """
        # Check orders in last hour
        hour_ago = current_time - timedelta(hours=1)
        
        item_orders_last_hour = self.db.query(func.count(OrderItem.id)).join(Order).filter(
            OrderItem.menu_item_id == item_id,
            Order.venue_id == venue_id,
            Order.created_at >= hour_ago,
            Order.created_at <= current_time
        ).scalar() or 0
        
        # Get average orders per hour for this item
        week_ago = current_time - timedelta(days=7)
        total_orders = self.db.query(func.count(OrderItem.id)).join(Order).filter(
            OrderItem.menu_item_id == item_id,
            Order.venue_id == venue_id,
            Order.created_at >= week_ago
        ).scalar() or 0
        
        avg_orders_per_hour = total_orders / (7 * 24) if total_orders > 0 else 0
        
        # High demand - surge pricing
        if avg_orders_per_hour > 0 and item_orders_last_hour > avg_orders_per_hour * 2:
            return {
                'multiplier': 1.15,  # 15% increase
                'reason': 'High demand right now',
                'demand_level': 'high',
                'orders_last_hour': item_orders_last_hour
            }
        
        # Low demand - discount to stimulate
        if avg_orders_per_hour > 0 and item_orders_last_hour < avg_orders_per_hour * 0.5:
            return {
                'multiplier': 0.90,  # 10% discount
                'reason': 'Special offer',
                'demand_level': 'low',
                'orders_last_hour': item_orders_last_hour
            }
        
        return None
    
    # ==================== SEASONAL PRICING ====================
    
    def _calculate_seasonal_adjustment(
        self,
        item_id: int,
        venue_id: int,
        current_time: datetime
    ) -> Optional[Dict]:
        """
        Seasonal pricing for ski resort
        - Winter season (Dec-Mar): +20% on winter specials
        - Summer season (Jun-Aug): +10% on summer items
        - Shoulder season (Apr-May, Sep-Nov): -15% to attract customers
        """
        month = current_time.month
        
        item = self.db.query(MenuItem).filter(MenuItem.id == item_id).first()
        if not item:
            return None
        
        item_name = item.name.get('en', '').lower() if isinstance(item.name, dict) else str(item.name).lower()
        
        # WINTER SKI SEASON (December-March)
        if month in [12, 1, 2, 3]:
            winter_keywords = ['winter', 'ski', 'après', 'hot', 'mulled', 'fondue']
            if any(keyword in item_name for keyword in winter_keywords):
                return {
                    'season': 'winter',
                    'multiplier': 1.20,  # 20% increase
                    'reason': '❄️ Winter season special'
                }
        
        # SUMMER SEASON (June-August)
        elif month in [6, 7, 8]:
            summer_keywords = ['summer', 'cold', 'ice', 'salad', 'grill', 'bbq']
            if any(keyword in item_name for keyword in summer_keywords):
                return {
                    'season': 'summer',
                    'multiplier': 1.10,  # 10% increase
                    'reason': '☀️ Summer special'
                }
        
        # SHOULDER SEASON (April-May, September-November)
        elif month in [4, 5, 9, 10, 11]:
            return {
                'season': 'shoulder',
                'multiplier': 0.85,  # 15% discount
                'reason': 'Shoulder season offer'
            }
        
        return None
    
    # ==================== PRICING RULES MANAGEMENT ====================
    
    def get_active_pricing_rules(
        self,
        venue_id: int,
        current_time: Optional[datetime] = None
    ) -> List[Dict]:
        """Get all currently active pricing rules"""
        if not current_time:
            current_time = datetime.now()
        
        active_rules = []
        
        # Time-based rules
        hour = current_time.hour
        if 16 <= hour < 19:
            active_rules.append({
                'type': 'time_based',
                'name': 'après_ski_happy_hour',
                'discount': 20,
                'applies_to': 'Drinks',
                'time_range': '16:00-19:00'
            })
        
        if 15 <= hour < 16:
            active_rules.append({
                'type': 'time_based',
                'name': 'off_peak_discount',
                'discount': 15,
                'applies_to': 'Food',
                'time_range': '15:00-16:00'
            })
        
        # Seasonal rules
        month = current_time.month
        if month in [12, 1, 2, 3]:
            active_rules.append({
                'type': 'seasonal',
                'name': 'winter_season',
                'surcharge': 20,
                'applies_to': 'Winter specials'
            })
        elif month in [4, 5, 9, 10, 11]:
            active_rules.append({
                'type': 'seasonal',
                'name': 'shoulder_season',
                'discount': 15,
                'applies_to': 'All items'
            })
        
        return active_rules
    
    def get_pricing_analytics(
        self,
        venue_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """Get analytics on pricing effectiveness"""
        
        # Revenue by pricing strategy
        orders = self.db.query(
            Order.id,
            Order.total,
            Order.created_at
        ).filter(
            Order.venue_id == venue_id,
            Order.created_at >= start_date,
            Order.created_at <= end_date
        ).all()
        
        total_revenue = sum(float(o.total) for o in orders)
        total_orders = len(orders)
        avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
        
        # Revenue by time period
        revenue_by_hour = {}
        for order in orders:
            hour = order.created_at.hour
            revenue_by_hour[hour] = revenue_by_hour.get(hour, 0) + float(order.total)
        
        # Peak hours
        peak_hours = sorted(revenue_by_hour.items(), key=lambda x: x[1], reverse=True)[:3]
        
        return {
            'total_revenue': total_revenue,
            'total_orders': total_orders,
            'avg_order_value': avg_order_value,
            'revenue_by_hour': revenue_by_hour,
            'peak_hours': [{'hour': h, 'revenue': r} for h, r in peak_hours],
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            }
        }

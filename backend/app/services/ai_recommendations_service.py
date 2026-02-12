"""
AI Recommendations Service
Provides intelligent menu item recommendations using:
- Collaborative filtering (user-based and item-based)
- Content-based filtering
- Weather-aware suggestions (ski resort specific)
- Time-based recommendations (après-ski hours 4-7 PM)
- Cross-sell optimization
"""

from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc, case
from datetime import datetime, timedelta
import logging
from redis import Redis
import json
from enum import Enum
import os
import requests

from app.models import (
    MenuItem, Order, OrderItem, MenuCategory, ItemImage,
    AnalyticsEvent, ItemRating, VenueStation, ItemTag,
    ItemTagLink
)

logger = logging.getLogger(__name__)

# OpenWeatherMap API key from environment
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")


class WeatherCondition(str, Enum):
    """Weather conditions for ski resort recommendations"""
    HEAVY_SNOW = "heavy_snow"
    LIGHT_SNOW = "light_snow"
    CLOUDY = "cloudy"
    SUNNY = "sunny"
    FREEZING = "freezing"  # Below -10°C
    COLD = "cold"  # -10°C to 0°C
    MILD = "mild"  # 0°C to 10°C
    WARM = "warm"  # Above 10°C


class AIRecommendationsService:
    """Advanced AI-powered recommendation engine"""

    def __init__(self, db: Session, redis_client: Optional[Redis] = None):
        self.db = db
        self.redis = redis_client
        self.cache_ttl = 3600  # 1 hour

    def _fetch_current_weather(self, latitude: float = 42.2667, longitude: float = 23.7833) -> dict:
        """Fetch current weather from OpenWeatherMap API.
        Default coordinates are for Borovets, Bulgaria.

        Args:
            latitude: Latitude coordinate (default: Borovets)
            longitude: Longitude coordinate (default: Borovets)

        Returns:
            Dictionary with condition (WeatherCondition), temperature (float), and description (str)
        """
        if not OPENWEATHER_API_KEY:
            # Return default winter weather for ski resort
            return {
                "condition": WeatherCondition.COLD,
                "temperature": -5.0,
                "description": "Mock weather - set OPENWEATHER_API_KEY for real data"
            }

        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?lat={latitude}&lon={longitude}&appid={OPENWEATHER_API_KEY}&units=metric"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()

            temp = data["main"]["temp"]
            weather_id = data["weather"][0]["id"]

            # Map OpenWeather condition codes to our enum
            if weather_id >= 600 and weather_id < 700:
                condition = WeatherCondition.HEAVY_SNOW if weather_id < 610 else WeatherCondition.LIGHT_SNOW
            elif weather_id >= 800 and weather_id < 802:
                condition = WeatherCondition.SUNNY
            else:
                condition = WeatherCondition.CLOUDY

            # Temperature-based override
            if temp < -10:
                condition = WeatherCondition.FREEZING
            elif temp < 0:
                condition = WeatherCondition.COLD
            elif temp > 10:
                condition = WeatherCondition.WARM

            return {
                "condition": condition,
                "temperature": temp,
                "description": data["weather"][0]["description"]
            }
        except Exception as e:
            logger.warning(f"Weather API error: {e}, using default")
            return {
                "condition": WeatherCondition.COLD,
                "temperature": -5.0,
                "description": "API error - using default"
            }

    def _get_primary_image_url(self, menu_item_id: int) -> Optional[str]:
        """Get the primary image URL for a menu item"""
        primary_image = self.db.query(ItemImage.url).filter(
            ItemImage.item_id == menu_item_id,
            ItemImage.is_primary == True
        ).first()

        if primary_image:
            return primary_image[0]

        # Fallback to first image if no primary set
        first_image = self.db.query(ItemImage.url).filter(
            ItemImage.item_id == menu_item_id
        ).first()

        return first_image[0] if first_image else None

    # ==================== COLLABORATIVE FILTERING ====================

    def get_user_based_recommendations(
        self,
        customer_id: int,
        venue_id: int,
        limit: int = 10
    ) -> List[Dict]:
        """
        User-based collaborative filtering
        "Customers similar to you also liked..."
        Finds customers with similar order patterns and recommends items they ordered
        """
        # Get items ordered by this customer
        customer_items = self.db.query(MenuItem.id).join(
            OrderItem, MenuItem.id == OrderItem.menu_item_id
        ).join(
            Order, OrderItem.order_id == Order.id
        ).join(
            VenueStation, Order.station_id == VenueStation.id
        ).filter(
            Order.customer_id == customer_id,
            VenueStation.venue_id == venue_id
        ).distinct().all()

        if not customer_items:
            # No order history, return popular items
            logger.info(f"No order history for customer {customer_id}, returning popular items")
            return self.get_popular_items(venue_id, limit)

        customer_item_ids = [item.id for item in customer_items]

        # Find other customers who ordered the same items (similar customers)
        similar_customers = self.db.query(
            Order.customer_id,
            func.count(func.distinct(OrderItem.menu_item_id)).label('common_items')
        ).join(
            OrderItem, Order.id == OrderItem.order_id
        ).join(
            VenueStation, Order.station_id == VenueStation.id
        ).filter(
            Order.customer_id != customer_id,
            Order.customer_id.isnot(None),
            OrderItem.menu_item_id.in_(customer_item_ids),
            VenueStation.venue_id == venue_id
        ).group_by(Order.customer_id).order_by(
            desc('common_items')
        ).limit(10).all()

        if not similar_customers:
            # No similar customers found, return popular items
            logger.info(f"No similar customers found for customer {customer_id}, returning popular items")
            return self.get_popular_items(venue_id, limit)

        similar_customer_ids = [customer.customer_id for customer in similar_customers]

        # Get items ordered by similar customers that this customer hasn't tried
        recommendations = self.db.query(
            MenuItem.id,
            MenuItem.name,
            MenuItem.price,
            func.count(func.distinct(Order.customer_id)).label('customer_count'),
            func.count(OrderItem.id).label('order_count'),
            func.avg(ItemRating.rating).label('avg_rating')
        ).join(
            OrderItem, MenuItem.id == OrderItem.menu_item_id
        ).join(
            Order, OrderItem.order_id == Order.id
        ).join(
            VenueStation, Order.station_id == VenueStation.id
        ).outerjoin(
            ItemRating, MenuItem.id == ItemRating.item_id
        ).filter(
            Order.customer_id.in_(similar_customer_ids),
            MenuItem.id.notin_(customer_item_ids),
            MenuItem.available == True,
            VenueStation.venue_id == venue_id
        ).group_by(MenuItem.id).order_by(
            desc('customer_count'),
            desc('avg_rating'),
            desc('order_count')
        ).limit(limit).all()

        results = []
        for r in recommendations:
            image_url = self._get_primary_image_url(r.id)
            results.append({
                'item_id': r.id,
                'name': r.name,
                'price': float(r.price),
                'image_url': image_url,
                'customer_count': r.customer_count,
                'order_count': r.order_count,
                'avg_rating': float(r.avg_rating) if r.avg_rating else None,
                'recommendation_type': 'user_based',
                'reason': 'Customers like you also enjoyed this'
            })

        return results
    
    def get_item_based_recommendations(
        self,
        item_id: int,
        venue_id: int,
        limit: int = 5
    ) -> List[Dict]:
        """
        Item-based collaborative filtering
        "Customers who ordered X also ordered Y"
        Finds items frequently ordered together in the same order
        """
        cache_key = f"item_reco:{item_id}:{venue_id}"
        if self.redis:
            cached = self.redis.get(cache_key)
            if cached:
                return json.loads(cached)

        # Find orders containing this item, filtering by venue through station
        orders_with_item = self.db.query(Order.id).join(
            OrderItem
        ).join(
            VenueStation, Order.station_id == VenueStation.id
        ).filter(
            OrderItem.menu_item_id == item_id,
            VenueStation.venue_id == venue_id
        ).subquery()

        # Find other items frequently ordered together
        recommendations = self.db.query(
            MenuItem.id,
            MenuItem.name,
            MenuItem.price,
            func.count(OrderItem.id).label('co_occurrence'),
            func.avg(ItemRating.rating).label('avg_rating')
        ).join(
            OrderItem, MenuItem.id == OrderItem.menu_item_id
        ).join(
            Order, OrderItem.order_id == Order.id
        ).outerjoin(
            ItemRating, MenuItem.id == ItemRating.item_id
        ).filter(
            Order.id.in_(orders_with_item),
            MenuItem.id != item_id,
            MenuItem.available == True
        ).group_by(MenuItem.id).order_by(
            desc('co_occurrence')
        ).limit(limit).all()

        results = []
        for r in recommendations:
            image_url = self._get_primary_image_url(r.id)
            results.append({
                'item_id': r.id,
                'name': r.name,
                'price': float(r.price),
                'image_url': image_url,
                'co_occurrence': r.co_occurrence,
                'avg_rating': float(r.avg_rating) if r.avg_rating else None,
                'recommendation_type': 'item_based',
                'reason': 'Often ordered together'
            })

        if self.redis:
            self.redis.setex(cache_key, self.cache_ttl, json.dumps(results))

        return results
    
    # ==================== CONTENT-BASED FILTERING ====================

    def get_content_based_recommendations(
        self,
        customer_id: int,
        venue_id: int,
        limit: int = 10
    ) -> List[Dict]:
        """
        Content-based filtering based on customer's order history
        Analyzes what categories/tags the customer prefers and recommends similar items
        """
        # Get customer's order history to understand preferences
        customer_items = self.db.query(
            MenuItem.category_id,
            func.count(OrderItem.id).label('order_count')
        ).join(
            OrderItem, MenuItem.id == OrderItem.menu_item_id
        ).join(
            Order, OrderItem.order_id == Order.id
        ).join(
            VenueStation, Order.station_id == VenueStation.id
        ).filter(
            Order.customer_id == customer_id,
            VenueStation.venue_id == venue_id
        ).group_by(MenuItem.category_id).order_by(
            desc('order_count')
        ).limit(3).all()

        if not customer_items:
            # No order history, return popular items instead
            logger.info(f"No order history for customer {customer_id}, returning popular items")
            return self.get_popular_items(venue_id, limit)

        # Get the customer's preferred categories
        preferred_categories = [item.category_id for item in customer_items]

        # Get items already ordered by the customer to exclude them
        ordered_item_ids = self.db.query(MenuItem.id).join(
            OrderItem, MenuItem.id == OrderItem.menu_item_id
        ).join(
            Order, OrderItem.order_id == Order.id
        ).join(
            VenueStation, Order.station_id == VenueStation.id
        ).filter(
            Order.customer_id == customer_id,
            VenueStation.venue_id == venue_id
        ).distinct().all()

        ordered_item_ids = [item.id for item in ordered_item_ids]

        # Recommend items from preferred categories that the customer hasn't tried yet
        recommendations = self.db.query(
            MenuItem.id,
            MenuItem.name,
            MenuItem.price,
            MenuItem.category_id,
            func.count(OrderItem.id).label('order_count'),
            func.avg(ItemRating.rating).label('avg_rating')
        ).outerjoin(
            OrderItem, MenuItem.id == OrderItem.menu_item_id
        ).outerjoin(
            ItemRating, MenuItem.id == ItemRating.item_id
        ).join(
            VenueStation, MenuItem.station_id == VenueStation.id
        ).filter(
            MenuItem.category_id.in_(preferred_categories),
            MenuItem.available == True,
            VenueStation.venue_id == venue_id,
            MenuItem.id.notin_(ordered_item_ids) if ordered_item_ids else True
        ).group_by(MenuItem.id).order_by(
            desc('avg_rating'),
            desc('order_count')
        ).limit(limit).all()

        results = []
        for r in recommendations:
            image_url = self._get_primary_image_url(r.id)
            results.append({
                'item_id': r.id,
                'name': r.name,
                'price': float(r.price),
                'image_url': image_url,
                'category_id': r.category_id,
                'order_count': r.order_count or 0,
                'avg_rating': float(r.avg_rating) if r.avg_rating else None,
                'recommendation_type': 'content_based',
                'reason': 'Based on your preferences'
            })

        return results

    def get_category_recommendations(
        self,
        category_id: int,
        venue_id: int,
        limit: int = 10
    ) -> List[Dict]:
        """
        Get top-rated items from a specific category
        Useful for category-based browsing
        """
        recommendations = self.db.query(
            MenuItem.id,
            MenuItem.name,
            MenuItem.price,
            MenuItem.category_id,
            func.count(OrderItem.id).label('order_count'),
            func.avg(ItemRating.rating).label('avg_rating')
        ).outerjoin(
            OrderItem, MenuItem.id == OrderItem.menu_item_id
        ).outerjoin(
            ItemRating, MenuItem.id == ItemRating.item_id
        ).join(
            VenueStation, MenuItem.station_id == VenueStation.id
        ).filter(
            MenuItem.category_id == category_id,
            MenuItem.available == True,
            VenueStation.venue_id == venue_id
        ).group_by(MenuItem.id).order_by(
            desc('avg_rating'),
            desc('order_count')
        ).limit(limit).all()

        results = []
        for r in recommendations:
            image_url = self._get_primary_image_url(r.id)
            results.append({
                'item_id': r.id,
                'name': r.name,
                'price': float(r.price),
                'image_url': image_url,
                'category_id': r.category_id,
                'order_count': r.order_count or 0,
                'avg_rating': float(r.avg_rating) if r.avg_rating else None,
                'recommendation_type': 'category_based',
                'reason': 'Top rated in category'
            })

        return results
    
    # ==================== WEATHER-AWARE RECOMMENDATIONS ====================

    def get_weather_aware_recommendations(
        self,
        venue_id: int,
        weather_condition: Optional[WeatherCondition] = None,
        temperature: Optional[float] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        Weather-aware recommendations for ski resort
        Fetches real weather from OpenWeatherMap API if weather parameters not provided

        Args:
            venue_id: The venue ID
            weather_condition: WeatherCondition enum (fetches real weather if None)
            temperature: Temperature in Celsius (fetches real weather if None)
            limit: Number of recommendations

        Returns:
            List of recommended menu items based on weather
        """
        # Fetch real weather if not provided
        if weather_condition is None or temperature is None:
            weather_data = self._fetch_current_weather()
            weather_condition = weather_data["condition"]
            temperature = weather_data["temperature"]

        # Determine recommendation tags based on weather
        tags = []

        # Temperature-based tags
        if temperature < -10:
            tags.extend(['hot', 'warm', 'soup', 'tea', 'coffee', 'hearty'])
        elif temperature < 0:
            tags.extend(['warm', 'comfort', 'hot chocolate', 'mulled wine', 'soup'])
        elif temperature < 10:
            tags.extend(['warm', 'comfort'])
        else:
            tags.extend(['refreshing', 'cold', 'salad', 'beer', 'ice cream'])

        # Condition-based tags
        if weather_condition in [WeatherCondition.HEAVY_SNOW, WeatherCondition.LIGHT_SNOW]:
            tags.extend(['apres-ski', 'winter special', 'hot drink'])
        elif weather_condition == WeatherCondition.SUNNY:
            tags.extend(['refreshing', 'light'])

        if not tags:
            # No specific weather tags, return popular items instead
            logger.info(f"No weather tags determined for {weather_condition}, returning popular items")
            return self.get_popular_items(venue_id, limit)

        # Find items matching weather tags
        # Note: Using LIKE for tag matching since tags are stored in ItemTag table
        recommendations = self.db.query(
            MenuItem.id,
            MenuItem.name,
            MenuItem.price,
            MenuItem.description,
            func.count(OrderItem.id).label('order_count'),
            func.avg(ItemRating.rating).label('avg_rating')
        ).outerjoin(
            ItemTagLink, MenuItem.id == ItemTagLink.item_id
        ).outerjoin(
            ItemTag, ItemTagLink.tag_id == ItemTag.id
        ).outerjoin(
            OrderItem, MenuItem.id == OrderItem.menu_item_id
        ).outerjoin(
            ItemRating, MenuItem.id == ItemRating.item_id
        ).join(
            VenueStation, MenuItem.station_id == VenueStation.id
        ).filter(
            VenueStation.venue_id == venue_id,
            MenuItem.available == True,
            or_(
                ItemTag.name.in_(tags),
                # Also check description for weather-related keywords
                *[MenuItem.description.ilike(f'%{tag}%') for tag in tags[:3]]
            )
        ).group_by(MenuItem.id).order_by(
            desc('avg_rating'),
            desc('order_count')
        ).limit(limit).all()

        results = []
        for r in recommendations:
            image_url = self._get_primary_image_url(r.id)
            results.append({
                'item_id': r.id,
                'name': r.name,
                'price': float(r.price),
                'image_url': image_url,
                'order_count': r.order_count or 0,
                'avg_rating': float(r.avg_rating) if r.avg_rating else None,
                'recommendation_type': 'weather_based',
                'reason': f'Perfect for {weather_condition.value} weather ({temperature:.1f}°C)',
                'weather': {
                    'condition': weather_condition.value,
                    'temp': temperature
                }
            })

        return results
    
    # ==================== TIME-BASED RECOMMENDATIONS ====================

    def get_time_based_recommendations(
        self,
        venue_id: int,
        current_time: Optional[datetime] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        Time-based recommendations with popularity analysis
        Analyzes order patterns by hour and day of week

        Time periods:
        - Breakfast (6-11 AM)
        - Lunch (11 AM - 3 PM)
        - Après-ski (4-7 PM) - SKI RESORT SPECIFIC
        - Dinner (6-10 PM)
        - Late night (10 PM+)

        Returns popular items for the current time period based on historical orders
        """
        if not current_time:
            current_time = datetime.now()

        hour = current_time.hour
        day_of_week = current_time.weekday()  # 0=Monday, 6=Sunday

        # Determine time period and tags
        if 6 <= hour < 11:
            period = 'breakfast'
            tags = ['breakfast', 'morning', 'coffee', 'pastry']
            hour_range = (6, 11)
        elif 11 <= hour < 15:
            period = 'lunch'
            tags = ['lunch', 'sandwich', 'salad', 'soup']
            hour_range = (11, 15)
        elif 16 <= hour < 19:  # APRÈS-SKI HOURS
            period = 'apres_ski'
            tags = ['apres-ski', 'hot drink', 'comfort food', 'beer', 'wine']
            hour_range = (16, 19)
        elif 18 <= hour < 22:
            period = 'dinner'
            tags = ['dinner', 'main course', 'pasta', 'meat', 'dessert']
            hour_range = (18, 22)
        else:
            period = 'late_night'
            tags = ['snack', 'light', 'drinks']
            hour_range = (22, 6)

        # Get items popular during this time period from order history
        # Look at orders from the last 30 days during this hour range
        since_date = datetime.now() - timedelta(days=30)

        recommendations = self.db.query(
            MenuItem.id,
            MenuItem.name,
            MenuItem.price,
            MenuItem.description,
            func.count(OrderItem.id).label('order_count'),
            func.avg(ItemRating.rating).label('avg_rating')
        ).join(
            OrderItem, MenuItem.id == OrderItem.menu_item_id
        ).join(
            Order, OrderItem.order_id == Order.id
        ).join(
            VenueStation, Order.station_id == VenueStation.id
        ).outerjoin(
            ItemRating, MenuItem.id == ItemRating.item_id
        ).outerjoin(
            ItemTagLink, MenuItem.id == ItemTagLink.item_id
        ).outerjoin(
            ItemTag, ItemTagLink.tag_id == ItemTag.id
        ).filter(
            VenueStation.venue_id == venue_id,
            MenuItem.available == True,
            Order.created_at >= since_date,
            # Filter by hour range
            or_(
                and_(
                    func.extract('hour', Order.created_at) >= hour_range[0],
                    func.extract('hour', Order.created_at) < hour_range[1]
                ) if hour_range[0] < hour_range[1] else or_(
                    func.extract('hour', Order.created_at) >= hour_range[0],
                    func.extract('hour', Order.created_at) < hour_range[1]
                ),
                # Also include items with matching tags
                ItemTag.name.in_(tags)
            )
        ).group_by(MenuItem.id).order_by(
            desc('order_count'),
            desc('avg_rating')
        ).limit(limit).all()

        reason_map = {
            'breakfast': 'Great for breakfast',
            'lunch': 'Perfect lunch option',
            'apres_ski': 'Apres-ski special!',
            'dinner': 'Dinner favorite',
            'late_night': 'Late night snack'
        }

        results = []
        for r in recommendations:
            image_url = self._get_primary_image_url(r.id)
            results.append({
                'item_id': r.id,
                'name': r.name,
                'price': float(r.price),
                'image_url': image_url,
                'order_count': r.order_count or 0,
                'avg_rating': float(r.avg_rating) if r.avg_rating else None,
                'recommendation_type': 'time_based',
                'reason': reason_map.get(period, 'Recommended for now'),
                'time_period': period,
                'hour': hour
            })

        return results
    
    # ==================== CROSS-SELL OPTIMIZATION ====================

    def get_cart_based_recommendations(
        self,
        cart_items: List[int],
        venue_id: int,
        limit: int = 5
    ) -> List[Dict]:
        """
        Cross-sell recommendations based on current cart
        Suggests complementary items (e.g., fries with burger, wine with pasta)
        Finds items frequently ordered together with items in the cart
        """
        if not cart_items:
            # Empty cart, return popular items instead
            logger.info("Empty cart, returning popular items for cross-sell")
            return self.get_popular_items(venue_id, limit)

        # Find orders containing any of the cart items
        orders_with_cart_items = self.db.query(Order.id).join(
            OrderItem
        ).join(
            VenueStation, Order.station_id == VenueStation.id
        ).filter(
            OrderItem.menu_item_id.in_(cart_items),
            VenueStation.venue_id == venue_id
        ).subquery()

        # Find other items frequently ordered together with cart items
        recommendations = self.db.query(
            MenuItem.id,
            MenuItem.name,
            MenuItem.price,
            func.count(OrderItem.id).label('frequency'),
            func.avg(ItemRating.rating).label('avg_rating')
        ).join(
            OrderItem, MenuItem.id == OrderItem.menu_item_id
        ).join(
            Order, OrderItem.order_id == Order.id
        ).outerjoin(
            ItemRating, MenuItem.id == ItemRating.item_id
        ).filter(
            Order.id.in_(orders_with_cart_items),
            MenuItem.id.notin_(cart_items),
            MenuItem.available == True
        ).group_by(MenuItem.id).order_by(
            desc('frequency'),
            desc('avg_rating')
        ).limit(limit).all()

        results = []
        for r in recommendations:
            image_url = self._get_primary_image_url(r.id)
            results.append({
                'item_id': r.id,
                'name': r.name,
                'price': float(r.price),
                'image_url': image_url,
                'frequency': r.frequency,
                'avg_rating': float(r.avg_rating) if r.avg_rating else None,
                'recommendation_type': 'cross_sell',
                'reason': 'Great with your current selection'
            })

        return results
    
    # ==================== POPULAR ITEMS ====================

    def get_popular_items(
        self,
        venue_id: int,
        limit: int = 10,
        days: int = 30
    ) -> List[Dict]:
        """
        Get most popular items in the last N days
        Calculates popularity score based on order count, quantity, and ratings
        """
        since_date = datetime.now() - timedelta(days=days)

        popular = self.db.query(
            MenuItem.id,
            MenuItem.name,
            MenuItem.price,
            func.count(OrderItem.id).label('order_count'),
            func.sum(OrderItem.quantity).label('total_quantity'),
            func.avg(ItemRating.rating).label('avg_rating'),
            # Popularity score: order_count * 2 + total_quantity + (avg_rating * 10)
            (
                func.count(OrderItem.id) * 2 +
                func.coalesce(func.sum(OrderItem.quantity), 0) +
                func.coalesce(func.avg(ItemRating.rating) * 10, 0)
            ).label('popularity_score')
        ).join(
            OrderItem, MenuItem.id == OrderItem.menu_item_id
        ).join(
            Order, OrderItem.order_id == Order.id
        ).join(
            VenueStation, Order.station_id == VenueStation.id
        ).outerjoin(
            ItemRating, MenuItem.id == ItemRating.item_id
        ).filter(
            VenueStation.venue_id == venue_id,
            Order.created_at >= since_date,
            MenuItem.available == True
        ).group_by(MenuItem.id).order_by(
            desc('popularity_score'),
            desc('order_count')
        ).limit(limit).all()

        results = []
        for r in popular:
            image_url = self._get_primary_image_url(r.id)
            results.append({
                'item_id': r.id,
                'name': r.name,
                'price': float(r.price),
                'image_url': image_url,
                'order_count': r.order_count,
                'total_quantity': r.total_quantity or 0,
                'avg_rating': float(r.avg_rating) if r.avg_rating else None,
                'popularity_score': float(r.popularity_score),
                'recommendation_type': 'popular',
                'reason': 'Customer favorite'
            })

        return results

    def get_popular_items_by_hour(
        self,
        venue_id: int,
        hour: int,
        limit: int = 10,
        days: int = 30
    ) -> List[Dict]:
        """
        Get popular items for a specific hour of day
        Useful for understanding hourly patterns

        Args:
            venue_id: The venue ID
            hour: Hour of day (0-23)
            limit: Number of items to return
            days: Look back period in days

        Returns:
            List of popular items for that hour
        """
        since_date = datetime.now() - timedelta(days=days)

        popular = self.db.query(
            MenuItem.id,
            MenuItem.name,
            MenuItem.price,
            func.count(OrderItem.id).label('order_count'),
            func.sum(OrderItem.quantity).label('total_quantity'),
            func.avg(ItemRating.rating).label('avg_rating')
        ).join(
            OrderItem, MenuItem.id == OrderItem.menu_item_id
        ).join(
            Order, OrderItem.order_id == Order.id
        ).join(
            VenueStation, Order.station_id == VenueStation.id
        ).outerjoin(
            ItemRating, MenuItem.id == ItemRating.item_id
        ).filter(
            VenueStation.venue_id == venue_id,
            Order.created_at >= since_date,
            MenuItem.available == True,
            func.extract('hour', Order.created_at) == hour
        ).group_by(MenuItem.id).order_by(
            desc('order_count')
        ).limit(limit).all()

        results = []
        for r in popular:
            image_url = self._get_primary_image_url(r.id)
            results.append({
                'item_id': r.id,
                'name': r.name,
                'price': float(r.price),
                'image_url': image_url,
                'order_count': r.order_count,
                'total_quantity': r.total_quantity or 0,
                'avg_rating': float(r.avg_rating) if r.avg_rating else None,
                'recommendation_type': 'hourly_popular',
                'reason': f'Popular at {hour}:00',
                'hour': hour
            })

        return results

    def get_popular_items_by_day(
        self,
        venue_id: int,
        day_of_week: int,
        limit: int = 10,
        days: int = 90
    ) -> List[Dict]:
        """
        Get popular items for a specific day of week
        Useful for understanding weekly patterns

        Args:
            venue_id: The venue ID
            day_of_week: Day of week (0=Monday, 6=Sunday)
            limit: Number of items to return
            days: Look back period in days

        Returns:
            List of popular items for that day
        """
        since_date = datetime.now() - timedelta(days=days)

        popular = self.db.query(
            MenuItem.id,
            MenuItem.name,
            MenuItem.price,
            func.count(OrderItem.id).label('order_count'),
            func.sum(OrderItem.quantity).label('total_quantity'),
            func.avg(ItemRating.rating).label('avg_rating')
        ).join(
            OrderItem, MenuItem.id == OrderItem.menu_item_id
        ).join(
            Order, OrderItem.order_id == Order.id
        ).join(
            VenueStation, Order.station_id == VenueStation.id
        ).outerjoin(
            ItemRating, MenuItem.id == ItemRating.item_id
        ).filter(
            VenueStation.venue_id == venue_id,
            Order.created_at >= since_date,
            MenuItem.available == True,
            func.extract('dow', Order.created_at) == (day_of_week + 1) % 7  # PostgreSQL: 0=Sunday
        ).group_by(MenuItem.id).order_by(
            desc('order_count')
        ).limit(limit).all()

        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

        results = []
        for r in popular:
            image_url = self._get_primary_image_url(r.id)
            results.append({
                'item_id': r.id,
                'name': r.name,
                'price': float(r.price),
                'image_url': image_url,
                'order_count': r.order_count,
                'total_quantity': r.total_quantity or 0,
                'avg_rating': float(r.avg_rating) if r.avg_rating else None,
                'recommendation_type': 'daily_popular',
                'reason': f'Popular on {day_names[day_of_week]}s',
                'day_of_week': day_of_week
            })

        return results

    # ==================== HYBRID RECOMMENDATIONS ====================

    def get_personalized_recommendations(
        self,
        customer_id: Optional[int],
        venue_id: int,
        cart_items: Optional[List[int]] = None,
        weather_condition: Optional[WeatherCondition] = None,
        temperature: Optional[float] = None,
        current_time: Optional[datetime] = None,
        limit: int = 20
    ) -> Dict[str, List[Dict]]:
        """
        Hybrid recommendation engine combining multiple strategies
        Returns categorized recommendations

        Args:
            customer_id: Customer ID (currently not used as Order doesn't track customers)
            venue_id: Venue ID
            cart_items: List of item IDs in cart for cross-sell recommendations
            weather_condition: Current weather condition (WeatherCondition enum)
            temperature: Current temperature in Celsius
            current_time: Current time for time-based recommendations
            limit: Total items to recommend

        Returns:
            Dictionary with categorized recommendation lists
        """
        recommendations = {}

        # Time-based (always show)
        time_recos = self.get_time_based_recommendations(
            venue_id, current_time=current_time, limit=5
        )
        if time_recos:
            recommendations['perfect_for_now'] = time_recos

        # Weather-aware (always show)
        weather_recos = self.get_weather_aware_recommendations(
            venue_id,
            weather_condition=weather_condition,
            temperature=temperature,
            limit=5
        )
        if weather_recos:
            recommendations['weather_picks'] = weather_recos

        # Cart-based cross-sell
        if cart_items:
            cart_recos = self.get_cart_based_recommendations(
                cart_items, venue_id, limit=5
            )
            if cart_recos:
                recommendations['add_to_order'] = cart_recos

        # Popular items (always show)
        popular_recos = self.get_popular_items(venue_id, limit=5)
        if popular_recos:
            recommendations['popular'] = popular_recos

        return recommendations
    
    # ==================== RECOMMENDATION FEEDBACK ====================

    def record_recommendation_feedback(
        self,
        venue_id: int,
        item_id: int,
        recommendation_type: str,
        action: str,  # 'clicked', 'ordered', 'dismissed'
        session_id: Optional[str] = None
    ):
        """
        Record feedback to improve recommendation quality

        Args:
            venue_id: The venue ID
            item_id: The menu item ID
            recommendation_type: Type of recommendation (e.g., 'popular', 'weather_based')
            action: User action ('clicked', 'ordered', 'dismissed')
            session_id: Optional session identifier
        """
        try:
            # Store in analytics for later analysis
            event = AnalyticsEvent(
                venue_id=venue_id,
                event_type='recommendation_feedback',
                event_data={
                    'item_id': item_id,
                    'recommendation_type': recommendation_type,
                    'action': action,
                    'session_id': session_id,
                    'timestamp': datetime.now().isoformat()
                }
            )
            self.db.add(event)
            self.db.commit()

            logger.info(
                f"Recommendation feedback: venue={venue_id}, "
                f"item={item_id}, type={recommendation_type}, action={action}"
            )
        except Exception as e:
            logger.error(f"Error recording recommendation feedback: {e}")
            self.db.rollback()

    # ==================== ADVANCED AI FEATURES ====================

    def get_trending_items(
        self,
        venue_id: int,
        limit: int = 10,
        trend_window_days: int = 7,
        comparison_window_days: int = 30
    ) -> List[Dict]:
        """
        Detect trending items - items with accelerating popularity
        Compares recent orders to historical baseline to find rising stars

        Args:
            venue_id: Venue ID
            limit: Number of items to return
            trend_window_days: Recent period to analyze (default 7 days)
            comparison_window_days: Historical period for baseline (default 30 days)

        Returns:
            Items with highest growth rate
        """
        now = datetime.now()
        recent_start = now - timedelta(days=trend_window_days)
        historical_start = now - timedelta(days=comparison_window_days)

        # Recent order counts
        recent_orders = self.db.query(
            MenuItem.id,
            func.count(OrderItem.id).label('recent_count')
        ).join(
            OrderItem, MenuItem.id == OrderItem.menu_item_id
        ).join(
            Order, OrderItem.order_id == Order.id
        ).join(
            VenueStation, Order.station_id == VenueStation.id
        ).filter(
            VenueStation.venue_id == venue_id,
            Order.created_at >= recent_start,
            MenuItem.available == True
        ).group_by(MenuItem.id).subquery()

        # Historical order counts (excluding recent)
        historical_orders = self.db.query(
            MenuItem.id,
            func.count(OrderItem.id).label('historical_count')
        ).join(
            OrderItem, MenuItem.id == OrderItem.menu_item_id
        ).join(
            Order, OrderItem.order_id == Order.id
        ).join(
            VenueStation, Order.station_id == VenueStation.id
        ).filter(
            VenueStation.venue_id == venue_id,
            Order.created_at >= historical_start,
            Order.created_at < recent_start,
            MenuItem.available == True
        ).group_by(MenuItem.id).subquery()

        # Calculate trend score: recent_count / (historical_count / days_ratio + 1)
        days_ratio = comparison_window_days / trend_window_days

        trending = self.db.query(
            MenuItem.id,
            MenuItem.name,
            MenuItem.price,
            recent_orders.c.recent_count,
            historical_orders.c.historical_count,
            func.avg(ItemRating.rating).label('avg_rating'),
            # Trend score with smoothing to avoid division by zero
            (
                func.coalesce(recent_orders.c.recent_count, 0) * days_ratio /
                (func.coalesce(historical_orders.c.historical_count, 0) + 1)
            ).label('trend_score')
        ).outerjoin(
            recent_orders, MenuItem.id == recent_orders.c.id
        ).outerjoin(
            historical_orders, MenuItem.id == historical_orders.c.id
        ).outerjoin(
            ItemRating, MenuItem.id == ItemRating.item_id
        ).join(
            VenueStation, MenuItem.station_id == VenueStation.id
        ).filter(
            VenueStation.venue_id == venue_id,
            MenuItem.available == True,
            recent_orders.c.recent_count > 0  # Must have recent orders
        ).group_by(
            MenuItem.id,
            recent_orders.c.recent_count,
            historical_orders.c.historical_count
        ).order_by(
            desc('trend_score')
        ).limit(limit).all()

        results = []
        for r in trending:
            image_url = self._get_primary_image_url(r.id)
            trend_pct = ((r.trend_score or 1) - 1) * 100
            results.append({
                'item_id': r.id,
                'name': r.name,
                'price': float(r.price),
                'image_url': image_url,
                'recent_orders': r.recent_count or 0,
                'trend_score': float(r.trend_score) if r.trend_score else 1.0,
                'trend_percentage': round(trend_pct, 1),
                'avg_rating': float(r.avg_rating) if r.avg_rating else None,
                'recommendation_type': 'trending',
                'reason': f'📈 Trending up {round(trend_pct)}%' if trend_pct > 0 else 'Rising star'
            })

        return results

    def get_segment_based_recommendations(
        self,
        customer_id: int,
        venue_id: int,
        limit: int = 10
    ) -> List[Dict]:
        """
        RFM Segment-based recommendations
        Recommends items popular among customers in the same RFM segment

        Segments:
        - Champions: Best customers, show premium items
        - Loyal: Regular customers, show variety
        - At Risk: Haven't ordered recently, show favorites
        - New: First-time customers, show bestsellers
        """
        from app.models.marketing_models import RFMScore

        # Get customer's RFM segment
        customer_rfm = self.db.query(RFMScore).filter(
            RFMScore.customer_id == customer_id
        ).first()

        if not customer_rfm:
            # No RFM data, return popular items
            return self.get_popular_items(venue_id, limit)

        segment = customer_rfm.segment

        # Find other customers in same segment
        segment_customers = self.db.query(RFMScore.customer_id).filter(
            RFMScore.segment == segment,
            RFMScore.customer_id != customer_id
        ).limit(100).all()

        if not segment_customers:
            return self.get_popular_items(venue_id, limit)

        segment_customer_ids = [c.customer_id for c in segment_customers]

        # Segment-specific filtering
        price_filter = True
        if segment == 'champions':
            # Show premium items for champions
            avg_price = self.db.query(func.avg(MenuItem.price)).join(
                VenueStation, MenuItem.station_id == VenueStation.id
            ).filter(VenueStation.venue_id == venue_id).scalar() or 0
            price_filter = MenuItem.price >= avg_price
        elif segment == 'at_risk':
            # Show their past favorites
            pass

        # Get items popular in this segment
        recommendations = self.db.query(
            MenuItem.id,
            MenuItem.name,
            MenuItem.price,
            func.count(OrderItem.id).label('segment_orders'),
            func.avg(ItemRating.rating).label('avg_rating')
        ).join(
            OrderItem, MenuItem.id == OrderItem.menu_item_id
        ).join(
            Order, OrderItem.order_id == Order.id
        ).join(
            VenueStation, Order.station_id == VenueStation.id
        ).outerjoin(
            ItemRating, MenuItem.id == ItemRating.item_id
        ).filter(
            Order.customer_id.in_(segment_customer_ids),
            VenueStation.venue_id == venue_id,
            MenuItem.available == True,
            price_filter
        ).group_by(MenuItem.id).order_by(
            desc('segment_orders'),
            desc('avg_rating')
        ).limit(limit).all()

        segment_messages = {
            'champions': 'Top choice for VIP customers',
            'loyal': 'Popular with regular guests',
            'at_risk': 'Remember this favorite?',
            'new': 'Bestseller for new guests',
            'potential_loyalist': 'Becoming a favorite',
            'promising': 'Worth trying',
            'need_attention': 'Recommended for you',
            'about_to_sleep': 'Your past favorite',
            'hibernating': 'Time to revisit',
            'lost': 'Welcome back special'
        }

        results = []
        for r in recommendations:
            image_url = self._get_primary_image_url(r.id)
            results.append({
                'item_id': r.id,
                'name': r.name,
                'price': float(r.price),
                'image_url': image_url,
                'segment_orders': r.segment_orders,
                'avg_rating': float(r.avg_rating) if r.avg_rating else None,
                'recommendation_type': 'segment_based',
                'customer_segment': segment,
                'reason': segment_messages.get(segment, 'Recommended for you')
            })

        return results

    def get_seasonal_recommendations(
        self,
        venue_id: int,
        limit: int = 10
    ) -> List[Dict]:
        """
        Seasonal recommendations based on historical patterns
        Analyzes which items were popular in the same month/season historically
        """
        now = datetime.now()
        current_month = now.month

        # Determine season
        if current_month in [12, 1, 2]:
            season = 'winter'
            months = [12, 1, 2]
            season_tags = ['winter', 'ski', 'warm', 'hot chocolate', 'mulled wine', 'soup']
        elif current_month in [3, 4, 5]:
            season = 'spring'
            months = [3, 4, 5]
            season_tags = ['spring', 'fresh', 'light', 'salad']
        elif current_month in [6, 7, 8]:
            season = 'summer'
            months = [6, 7, 8]
            season_tags = ['summer', 'cold', 'refreshing', 'ice cream', 'cocktail']
        else:
            season = 'autumn'
            months = [9, 10, 11]
            season_tags = ['autumn', 'fall', 'comfort', 'warm']

        # Get items popular during this season from historical data
        recommendations = self.db.query(
            MenuItem.id,
            MenuItem.name,
            MenuItem.price,
            func.count(OrderItem.id).label('seasonal_orders'),
            func.avg(ItemRating.rating).label('avg_rating')
        ).join(
            OrderItem, MenuItem.id == OrderItem.menu_item_id
        ).join(
            Order, OrderItem.order_id == Order.id
        ).join(
            VenueStation, Order.station_id == VenueStation.id
        ).outerjoin(
            ItemRating, MenuItem.id == ItemRating.item_id
        ).outerjoin(
            ItemTagLink, MenuItem.id == ItemTagLink.item_id
        ).outerjoin(
            ItemTag, ItemTagLink.tag_id == ItemTag.id
        ).filter(
            VenueStation.venue_id == venue_id,
            MenuItem.available == True,
            or_(
                func.extract('month', Order.created_at).in_(months),
                ItemTag.name.in_(season_tags)
            )
        ).group_by(MenuItem.id).order_by(
            desc('seasonal_orders'),
            desc('avg_rating')
        ).limit(limit).all()

        season_emojis = {
            'winter': '❄️',
            'spring': '🌸',
            'summer': '☀️',
            'autumn': '🍂'
        }

        results = []
        for r in recommendations:
            image_url = self._get_primary_image_url(r.id)
            results.append({
                'item_id': r.id,
                'name': r.name,
                'price': float(r.price),
                'image_url': image_url,
                'seasonal_orders': r.seasonal_orders,
                'avg_rating': float(r.avg_rating) if r.avg_rating else None,
                'recommendation_type': 'seasonal',
                'season': season,
                'reason': f'{season_emojis.get(season, "")} {season.title()} favorite'
            })

        return results

    def calculate_item_similarity(
        self,
        item_id: int,
        venue_id: int,
        limit: int = 10
    ) -> List[Dict]:
        """
        Calculate item similarity based on multiple features:
        - Category similarity
        - Price range similarity
        - Tag overlap
        - Co-occurrence in orders
        - Rating similarity

        Returns items most similar to the given item
        """
        # Get the source item
        source_item = self.db.query(MenuItem).filter(MenuItem.id == item_id).first()
        if not source_item:
            return []

        # Get source item's tags
        source_tags = self.db.query(ItemTag.id).join(
            ItemTagLink
        ).filter(ItemTagLink.item_id == item_id).all()
        source_tag_ids = [t.id for t in source_tags]

        # Price range (within 30% of source price)
        price_margin = float(source_item.price) * 0.3
        min_price = float(source_item.price) - price_margin
        max_price = float(source_item.price) + price_margin

        # Calculate similarity score
        # Components:
        # - Same category: +40 points
        # - Similar price: +20 points
        # - Tag overlap: +10 points per shared tag
        # - Co-occurrence: +5 points per co-occurrence

        similar_items = self.db.query(
            MenuItem.id,
            MenuItem.name,
            MenuItem.price,
            MenuItem.category_id,
            func.count(func.distinct(ItemTagLink.tag_id)).filter(
                ItemTagLink.tag_id.in_(source_tag_ids)
            ).label('shared_tags'),
            func.avg(ItemRating.rating).label('avg_rating'),
            # Category similarity
            case(
                (MenuItem.category_id == source_item.category_id, 40),
                else_=0
            ).label('category_score'),
            # Price similarity
            case(
                (and_(MenuItem.price >= min_price, MenuItem.price <= max_price), 20),
                else_=0
            ).label('price_score')
        ).outerjoin(
            ItemTagLink, MenuItem.id == ItemTagLink.item_id
        ).outerjoin(
            ItemRating, MenuItem.id == ItemRating.item_id
        ).join(
            VenueStation, MenuItem.station_id == VenueStation.id
        ).filter(
            MenuItem.id != item_id,
            MenuItem.available == True,
            VenueStation.venue_id == venue_id
        ).group_by(MenuItem.id).all()

        # Calculate total similarity and sort
        scored_items = []
        for item in similar_items:
            total_score = (
                (item.category_score or 0) +
                (item.price_score or 0) +
                (item.shared_tags or 0) * 10
            )
            if total_score > 0:
                scored_items.append({
                    'item': item,
                    'score': total_score
                })

        # Sort by score and take top items
        scored_items.sort(key=lambda x: x['score'], reverse=True)
        top_items = scored_items[:limit]

        results = []
        for scored in top_items:
            item = scored['item']
            image_url = self._get_primary_image_url(item.id)
            results.append({
                'item_id': item.id,
                'name': item.name,
                'price': float(item.price),
                'image_url': image_url,
                'similarity_score': scored['score'],
                'shared_tags': item.shared_tags or 0,
                'avg_rating': float(item.avg_rating) if item.avg_rating else None,
                'recommendation_type': 'similar_items',
                'reason': 'Similar to what you viewed'
            })

        return results

    def get_diversity_aware_recommendations(
        self,
        venue_id: int,
        already_recommended: List[int] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        Diversity-aware recommendations to avoid filter bubbles
        Ensures recommendations span multiple categories and price points
        """
        if already_recommended is None:
            already_recommended = []

        # Get all categories with their item counts
        categories = self.db.query(
            MenuCategory.id,
            MenuCategory.name,
            func.count(MenuItem.id).label('item_count')
        ).join(
            MenuItem, MenuCategory.id == MenuItem.category_id
        ).join(
            VenueStation, MenuItem.station_id == VenueStation.id
        ).filter(
            VenueStation.venue_id == venue_id,
            MenuItem.available == True,
            MenuItem.id.notin_(already_recommended) if already_recommended else True
        ).group_by(MenuCategory.id).all()

        if not categories:
            return []

        # Calculate items per category (distribute evenly)
        items_per_category = max(1, limit // len(categories))

        results = []
        for category in categories:
            if len(results) >= limit:
                break

            # Get top items from each category
            category_items = self.db.query(
                MenuItem.id,
                MenuItem.name,
                MenuItem.price,
                func.count(OrderItem.id).label('order_count'),
                func.avg(ItemRating.rating).label('avg_rating')
            ).outerjoin(
                OrderItem, MenuItem.id == OrderItem.menu_item_id
            ).outerjoin(
                ItemRating, MenuItem.id == ItemRating.item_id
            ).filter(
                MenuItem.category_id == category.id,
                MenuItem.available == True,
                MenuItem.id.notin_(already_recommended) if already_recommended else True,
                MenuItem.id.notin_([r['item_id'] for r in results]) if results else True
            ).group_by(MenuItem.id).order_by(
                desc('avg_rating'),
                desc('order_count')
            ).limit(items_per_category).all()

            for item in category_items:
                if len(results) >= limit:
                    break
                image_url = self._get_primary_image_url(item.id)
                results.append({
                    'item_id': item.id,
                    'name': item.name,
                    'price': float(item.price),
                    'image_url': image_url,
                    'category': category.name,
                    'order_count': item.order_count or 0,
                    'avg_rating': float(item.avg_rating) if item.avg_rating else None,
                    'recommendation_type': 'diverse',
                    'reason': f'Try something from {category.name}'
                })

        return results

    def get_new_items_recommendations(
        self,
        venue_id: int,
        days_since_added: int = 14,
        limit: int = 10
    ) -> List[Dict]:
        """
        Recommend newly added menu items
        Helps promote new additions to the menu
        """
        cutoff_date = datetime.now() - timedelta(days=days_since_added)

        new_items = self.db.query(
            MenuItem.id,
            MenuItem.name,
            MenuItem.price,
            MenuItem.created_at,
            func.count(OrderItem.id).label('order_count'),
            func.avg(ItemRating.rating).label('avg_rating')
        ).outerjoin(
            OrderItem, MenuItem.id == OrderItem.menu_item_id
        ).outerjoin(
            ItemRating, MenuItem.id == ItemRating.item_id
        ).join(
            VenueStation, MenuItem.station_id == VenueStation.id
        ).filter(
            VenueStation.venue_id == venue_id,
            MenuItem.available == True,
            MenuItem.created_at >= cutoff_date
        ).group_by(MenuItem.id).order_by(
            desc(MenuItem.created_at),
            desc('avg_rating')
        ).limit(limit).all()

        results = []
        for item in new_items:
            image_url = self._get_primary_image_url(item.id)
            days_ago = (datetime.now() - item.created_at).days if item.created_at else 0
            results.append({
                'item_id': item.id,
                'name': item.name,
                'price': float(item.price),
                'image_url': image_url,
                'days_since_added': days_ago,
                'order_count': item.order_count or 0,
                'avg_rating': float(item.avg_rating) if item.avg_rating else None,
                'recommendation_type': 'new_item',
                'reason': '✨ New on the menu!' if days_ago <= 3 else f'Added {days_ago} days ago'
            })

        return results

    def generate_recommendation_explanation(
        self,
        item_id: int,
        recommendation_type: str,
        context: Dict = None
    ) -> str:
        """
        Generate human-readable explanation for why an item was recommended
        Improves transparency and user trust
        """
        if context is None:
            context = {}

        explanations = {
            'user_based': lambda: f"Customers with similar tastes ordered this {context.get('order_count', 'often')} times",
            'item_based': lambda: f"Frequently ordered together with items you've purchased",
            'content_based': lambda: f"Matches your preference for {context.get('category', 'this type of food')}",
            'weather_based': lambda: f"Perfect for today's {context.get('weather', 'weather')} ({context.get('temp', '')}°C)",
            'time_based': lambda: f"Popular during {context.get('period', 'this time')}",
            'trending': lambda: f"Trending up {context.get('trend_pct', 0)}% this week",
            'segment_based': lambda: f"Top choice among customers like you",
            'seasonal': lambda: f"A {context.get('season', 'seasonal')} favorite",
            'similar_items': lambda: f"Similar to items you've enjoyed",
            'diverse': lambda: f"Something different to try",
            'new_item': lambda: f"New addition to our menu",
            'popular': lambda: f"Customer favorite with {context.get('orders', 'many')} orders",
            'cross_sell': lambda: f"Great pairing with your current selection"
        }

        generator = explanations.get(recommendation_type, lambda: "Recommended for you")
        return generator()

    def get_complete_recommendations(
        self,
        customer_id: Optional[int],
        venue_id: int,
        cart_items: Optional[List[int]] = None,
        viewed_items: Optional[List[int]] = None,
        limit_per_category: int = 5
    ) -> Dict[str, List[Dict]]:
        """
        Complete recommendation engine combining ALL strategies
        Returns a comprehensive set of categorized recommendations
        """
        recommendations = {}
        all_recommended_ids = []

        # 1. Trending items (always interesting)
        trending = self.get_trending_items(venue_id, limit=limit_per_category)
        if trending:
            recommendations['trending_now'] = trending
            all_recommended_ids.extend([r['item_id'] for r in trending])

        # 2. Time-based recommendations
        time_recos = self.get_time_based_recommendations(venue_id, limit=limit_per_category)
        if time_recos:
            recommendations['perfect_for_now'] = time_recos
            all_recommended_ids.extend([r['item_id'] for r in time_recos])

        # 3. Weather-aware
        weather_recos = self.get_weather_aware_recommendations(venue_id, limit=limit_per_category)
        if weather_recos:
            recommendations['weather_picks'] = weather_recos
            all_recommended_ids.extend([r['item_id'] for r in weather_recos])

        # 4. Seasonal recommendations
        seasonal = self.get_seasonal_recommendations(venue_id, limit=limit_per_category)
        if seasonal:
            recommendations['seasonal_favorites'] = seasonal
            all_recommended_ids.extend([r['item_id'] for r in seasonal])

        # 5. Personalized (if customer ID provided)
        if customer_id:
            # User-based collaborative
            user_based = self.get_user_based_recommendations(customer_id, venue_id, limit=limit_per_category)
            if user_based:
                recommendations['you_might_like'] = user_based
                all_recommended_ids.extend([r['item_id'] for r in user_based])

            # Content-based
            content_based = self.get_content_based_recommendations(customer_id, venue_id, limit=limit_per_category)
            if content_based:
                recommendations['based_on_preferences'] = content_based
                all_recommended_ids.extend([r['item_id'] for r in content_based])

            # Segment-based
            segment_based = self.get_segment_based_recommendations(customer_id, venue_id, limit=limit_per_category)
            if segment_based:
                recommendations['for_you'] = segment_based
                all_recommended_ids.extend([r['item_id'] for r in segment_based])

        # 6. Cart-based cross-sell
        if cart_items:
            cross_sell = self.get_cart_based_recommendations(cart_items, venue_id, limit=limit_per_category)
            if cross_sell:
                recommendations['add_to_order'] = cross_sell
                all_recommended_ids.extend([r['item_id'] for r in cross_sell])

        # 7. Similar items (if viewing something)
        if viewed_items and len(viewed_items) > 0:
            similar = self.calculate_item_similarity(viewed_items[-1], venue_id, limit=limit_per_category)
            if similar:
                recommendations['similar_items'] = similar
                all_recommended_ids.extend([r['item_id'] for r in similar])

        # 8. New items
        new_items = self.get_new_items_recommendations(venue_id, limit=limit_per_category)
        if new_items:
            recommendations['new_on_menu'] = new_items
            all_recommended_ids.extend([r['item_id'] for r in new_items])

        # 9. Popular items (fallback and always good)
        popular = self.get_popular_items(venue_id, limit=limit_per_category)
        if popular:
            recommendations['customer_favorites'] = popular
            all_recommended_ids.extend([r['item_id'] for r in popular])

        # 10. Diversity picks (to avoid filter bubble)
        diverse = self.get_diversity_aware_recommendations(
            venue_id,
            already_recommended=all_recommended_ids,
            limit=limit_per_category
        )
        if diverse:
            recommendations['discover'] = diverse

        return recommendations

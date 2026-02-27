"""
Delivery Aggregator Integration Service - BJS V6
=================================================
Integrates with: Glovo, Foodpanda, Wolt, Bolt Food, Uber Eats, Takeaway.com
Features: Auto-accept, unified dashboard, menu sync, driver tracking, commission tracking
with full database integration.
"""

from datetime import datetime, timedelta, timezone, date
from typing import List, Dict, Any, Optional, Callable
from enum import Enum
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
import logging

logger = logging.getLogger(__name__)


class DeliveryPlatform(str, Enum):
    GLOVO = "glovo"
    FOODPANDA = "foodpanda"
    WOLT = "wolt"
    BOLT_FOOD = "bolt_food"
    UBER_EATS = "uber_eats"
    TAKEAWAY = "takeaway"
    OWN_FLEET = "own_fleet"


class AggregatorOrderStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    PREPARING = "preparing"
    READY_FOR_PICKUP = "ready_for_pickup"
    PICKED_UP = "picked_up"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class DriverStatus(str, Enum):
    OFFLINE = "offline"
    AVAILABLE = "available"
    ASSIGNED = "assigned"
    PICKING_UP = "picking_up"
    DELIVERING = "delivering"
    RETURNING = "returning"


# Pydantic models for API responses
class PlatformCredentialsResponse(BaseModel):
    id: int
    platform: str
    venue_id: int
    store_id: str
    auto_accept: bool
    enabled: bool
    connected: bool

    model_config = ConfigDict(from_attributes=True)


class AggregatorOrderResponse(BaseModel):
    id: int
    platform: str
    platform_order_id: str
    status: str
    customer_name: str
    total: float

    model_config = ConfigDict(from_attributes=True)


class DeliveryAggregatorService:
    """Unified delivery platform integration with database persistence."""

    PLATFORM_ENDPOINTS = {
        DeliveryPlatform.GLOVO: {"base_url": "https://api.glovoapp.com/v1", "orders": "/orders"},
        DeliveryPlatform.FOODPANDA: {"base_url": "https://api.foodpanda.com/v1", "orders": "/orders"},
        DeliveryPlatform.WOLT: {"base_url": "https://api.wolt.com/v1", "orders": "/orders"},
        DeliveryPlatform.BOLT_FOOD: {"base_url": "https://api.bolt.eu/food/v1", "orders": "/orders"},
        DeliveryPlatform.UBER_EATS: {"base_url": "https://api.uber.com/v1/eats", "orders": "/orders"},
    }

    def __init__(self, db_session: Session = None):
        self.db = db_session
        self._order_handlers: List[Callable] = []

    # ==================== PLATFORM CREDENTIALS ====================

    def connect_platform(self, venue_id: int, platform: str, api_key: str,
                         api_secret: str, store_id: str, **settings) -> Dict[str, Any]:
        """Connect a delivery platform."""
        from app.models.v6_features_models import DeliveryPlatformCredentials

        if not self.db:
            logger.warning("No database session - returning mock response")
            return {"id": 1, "platform": platform, "venue_id": venue_id}

        if isinstance(platform, DeliveryPlatform):
            platform = platform.value

        # Check if already exists
        existing = self.db.query(DeliveryPlatformCredentials).filter(
            DeliveryPlatformCredentials.venue_id == venue_id,
            DeliveryPlatformCredentials.platform == platform
        ).first()

        try:
            if existing:
                # Update existing
                existing.api_key = api_key
                existing.api_secret = api_secret
                existing.store_id = store_id
                existing.connected = True
                existing.last_sync = datetime.now(timezone.utc)
                for key, value in settings.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                self.db.commit()
                self.db.refresh(existing)
                creds = existing
            else:
                creds = DeliveryPlatformCredentials(
                    venue_id=venue_id,
                    platform=platform,
                    api_key=api_key,
                    api_secret=api_secret,
                    store_id=store_id,
                    connected=True,
                    last_sync=datetime.now(timezone.utc),
                    auto_accept=settings.get('auto_accept', False),
                    auto_accept_delay_seconds=settings.get('auto_accept_delay_seconds', 30),
                    prep_time_minutes=settings.get('prep_time_minutes', 20),
                    commission_percent=settings.get('commission_percent', 30.0)
                )
                self.db.add(creds)
                self.db.commit()
                self.db.refresh(creds)
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to connect platform {platform} for venue {venue_id}: {e}")
            return {"success": False, "error": f"Failed to connect platform: {str(e)}"}

        logger.info(f"Connected platform {platform} for venue {venue_id}")

        return {
            "success": True,
            "id": creds.id,
            "venue_id": creds.venue_id,
            "platform": creds.platform,
            "store_id": creds.store_id,
            "connected": creds.connected
        }

    def disconnect_platform(self, venue_id: int, platform: str) -> Dict[str, Any]:
        """Disconnect a delivery platform."""
        from app.models.v6_features_models import DeliveryPlatformCredentials

        if not self.db:
            return {"success": False, "error": "No database session"}

        if isinstance(platform, DeliveryPlatform):
            platform = platform.value

        creds = self.db.query(DeliveryPlatformCredentials).filter(
            DeliveryPlatformCredentials.venue_id == venue_id,
            DeliveryPlatformCredentials.platform == platform
        ).first()

        if creds:
            creds.connected = False
            creds.enabled = False
            try:
                self.db.commit()
            except Exception as e:
                self.db.rollback()
                return {"success": False, "error": f"Failed to disconnect platform: {str(e)}"}
            return {"success": True, "platform": platform}

        return {"success": False, "error": "Platform not found"}

    def get_connected_platforms(self, venue_id: int) -> List[Dict[str, Any]]:
        """Get all connected platforms for a venue."""
        from app.models.v6_features_models import DeliveryPlatformCredentials

        if not self.db:
            return []

        platforms = self.db.query(DeliveryPlatformCredentials).filter(
            DeliveryPlatformCredentials.venue_id == venue_id,
            DeliveryPlatformCredentials.enabled == True
        ).all()

        return [
            {
                "id": p.id,
                "platform": p.platform,
                "store_id": p.store_id,
                "auto_accept": p.auto_accept,
                "prep_time_minutes": p.prep_time_minutes,
                "commission_percent": float(p.commission_percent),
                "connected": p.connected,
                "last_sync": p.last_sync.isoformat() if p.last_sync else None
            }
            for p in platforms
        ]

    def update_platform_settings(self, venue_id: int, platform: str,
                                  **settings) -> Dict[str, Any]:
        """Update platform settings."""
        from app.models.v6_features_models import DeliveryPlatformCredentials

        if not self.db:
            return {"success": False, "error": "No database session"}

        if isinstance(platform, DeliveryPlatform):
            platform = platform.value

        creds = self.db.query(DeliveryPlatformCredentials).filter(
            DeliveryPlatformCredentials.venue_id == venue_id,
            DeliveryPlatformCredentials.platform == platform
        ).first()

        if not creds:
            return {"success": False, "error": "Platform not found"}

        allowed = ['auto_accept', 'auto_accept_delay_seconds', 'prep_time_minutes',
                   'commission_percent', 'enabled', 'webhook_secret']

        for key, value in settings.items():
            if key in allowed:
                setattr(creds, key, value)

        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            return {"success": False, "error": f"Failed to update platform settings: {str(e)}"}

        return {"success": True, "platform": platform}

    # ==================== ORDER MANAGEMENT ====================

    def receive_order(self, venue_id: int, platform: str,
                      order_data: Dict) -> Dict[str, Any]:
        """Receive order from delivery platform."""
        from app.models.v6_features_models import AggregatorOrder, DeliveryPlatformCredentials

        if not self.db:
            return {"success": False, "error": "No database session"}

        if isinstance(platform, DeliveryPlatform):
            platform = platform.value

        # Get platform credentials for commission
        creds = self.db.query(DeliveryPlatformCredentials).filter(
            DeliveryPlatformCredentials.venue_id == venue_id,
            DeliveryPlatformCredentials.platform == platform
        ).first()

        subtotal = order_data.get("subtotal", 0)
        commission = (subtotal * (float(creds.commission_percent) / 100)) if creds else 0
        total = order_data.get("total", subtotal)

        order = AggregatorOrder(
            venue_id=venue_id,
            platform=platform,
            platform_order_id=order_data.get("platform_order_id", ""),
            status=AggregatorOrderStatus.PENDING.value,
            customer_name=order_data.get("customer_name", ""),
            customer_phone=order_data.get("customer_phone"),
            customer_address=order_data.get("delivery_address", ""),
            customer_notes=order_data.get("notes"),
            delivery_lat=order_data.get("lat"),
            delivery_lng=order_data.get("lng"),
            items=order_data.get("items", []),
            subtotal=subtotal,
            delivery_fee=order_data.get("delivery_fee", 0),
            platform_fee=order_data.get("platform_fee", 0),
            tip=order_data.get("tip", 0),
            total=total,
            commission_amount=commission,
            net_revenue=total - commission,
            ordered_at=datetime.now(timezone.utc)
        )

        try:
            self.db.add(order)
            self.db.commit()
            self.db.refresh(order)
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to save delivery order from {platform} for venue {venue_id}: {e}")
            return {"success": False, "error": f"Failed to save order: {str(e)}"}

        logger.info(f"Received order {order.id} from {platform} for venue {venue_id}")

        # Auto-accept if enabled
        if creds and creds.auto_accept:
            self.accept_order(order.id, creds.prep_time_minutes)

        return {
            "success": True,
            "id": order.id,
            "platform": platform,
            "platform_order_id": order.platform_order_id,
            "status": order.status,
            "total": float(order.total)
        }

    def accept_order(self, order_id: int, prep_time_minutes: int = 20) -> Dict[str, Any]:
        """Accept an order."""
        from app.models.v6_features_models import AggregatorOrder

        if not self.db:
            return {"success": False, "error": "No database session"}

        order = self.db.query(AggregatorOrder).filter(
            AggregatorOrder.id == order_id
        ).first()

        if not order:
            return {"success": False, "error": "Order not found"}

        order.status = AggregatorOrderStatus.ACCEPTED.value
        order.accepted_at = datetime.now(timezone.utc)
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to accept order {order_id}: {e}")
            return {"success": False, "error": f"Failed to accept order: {str(e)}"}

        logger.info(f"Accepted order {order_id}")
        return {"success": True, "order_id": order_id, "status": order.status}

    def reject_order(self, order_id: int, reason: str = "") -> Dict[str, Any]:
        """Reject an order."""
        from app.models.v6_features_models import AggregatorOrder

        if not self.db:
            return {"success": False, "error": "No database session"}

        order = self.db.query(AggregatorOrder).filter(
            AggregatorOrder.id == order_id
        ).first()

        if not order:
            return {"success": False, "error": "Order not found"}

        order.status = AggregatorOrderStatus.REJECTED.value
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to reject order {order_id}: {e}")
            return {"success": False, "error": f"Failed to reject order: {str(e)}"}

        logger.info(f"Rejected order {order_id}: {reason}")
        return {"success": True, "order_id": order_id, "status": order.status}

    def update_order_status(self, order_id: int, status: str) -> Dict[str, Any]:
        """Update order status."""
        from app.models.v6_features_models import AggregatorOrder

        if not self.db:
            return {"success": False, "error": "No database session"}

        order = self.db.query(AggregatorOrder).filter(
            AggregatorOrder.id == order_id
        ).first()

        if not order:
            return {"success": False, "error": "Order not found"}

        if isinstance(status, AggregatorOrderStatus):
            status = status.value

        order.status = status

        if status == AggregatorOrderStatus.READY_FOR_PICKUP.value:
            order.ready_at = datetime.now(timezone.utc)
        elif status == AggregatorOrderStatus.DELIVERED.value:
            order.delivered_at = datetime.now(timezone.utc)

        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            return {"success": False, "error": f"Failed to update order status: {str(e)}"}

        return {"success": True, "order_id": order_id, "status": order.status}

    def mark_ready(self, order_id: int) -> Dict[str, Any]:
        """Mark order as ready for pickup."""
        return self.update_order_status(order_id, AggregatorOrderStatus.READY_FOR_PICKUP.value)

    def get_orders(self, venue_id: int, status: str = None,
                   platform: str = None) -> List[Dict[str, Any]]:
        """Get orders for a venue."""
        from app.models.v6_features_models import AggregatorOrder

        if not self.db:
            return []

        query = self.db.query(AggregatorOrder).filter(
            AggregatorOrder.venue_id == venue_id
        )

        if status:
            if isinstance(status, AggregatorOrderStatus):
                status = status.value
            query = query.filter(AggregatorOrder.status == status)

        if platform:
            if isinstance(platform, DeliveryPlatform):
                platform = platform.value
            query = query.filter(AggregatorOrder.platform == platform)

        orders = query.order_by(AggregatorOrder.ordered_at.desc()).all()

        return [
            {
                "id": o.id,
                "platform": o.platform,
                "platform_order_id": o.platform_order_id,
                "status": o.status,
                "customer_name": o.customer_name,
                "customer_address": o.customer_address,
                "items": o.items,
                "subtotal": float(o.subtotal),
                "delivery_fee": float(o.delivery_fee),
                "total": float(o.total),
                "commission_amount": float(o.commission_amount),
                "net_revenue": float(o.net_revenue),
                "ordered_at": o.ordered_at.isoformat(),
                "accepted_at": o.accepted_at.isoformat() if o.accepted_at else None,
                "ready_at": o.ready_at.isoformat() if o.ready_at else None,
                "delivered_at": o.delivered_at.isoformat() if o.delivered_at else None
            }
            for o in orders
        ]

    def get_active_orders(self, venue_id: int) -> List[Dict[str, Any]]:
        """Get active orders."""
        from app.models.v6_features_models import AggregatorOrder

        if not self.db:
            return []

        completed_statuses = [
            AggregatorOrderStatus.DELIVERED.value,
            AggregatorOrderStatus.CANCELLED.value,
            AggregatorOrderStatus.REJECTED.value
        ]

        orders = self.db.query(AggregatorOrder).filter(
            AggregatorOrder.venue_id == venue_id,
            AggregatorOrder.status.notin_(completed_statuses)
        ).order_by(AggregatorOrder.ordered_at.asc()).all()

        return [
            {
                "id": o.id,
                "platform": o.platform,
                "platform_order_id": o.platform_order_id,
                "status": o.status,
                "customer_name": o.customer_name,
                "total": float(o.total),
                "ordered_at": o.ordered_at.isoformat()
            }
            for o in orders
        ]

    def get_order_history(self, venue_id: int, start_date: datetime = None,
                          end_date: datetime = None, platform: str = None,
                          limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get historical orders with filtering options.

        Args:
            venue_id: Venue ID
            start_date: Filter orders from this date
            end_date: Filter orders until this date
            platform: Filter by specific platform
            limit: Maximum number of orders to return

        Returns:
            List of historical order dictionaries
        """
        from app.models.v6_features_models import AggregatorOrder

        if not self.db:
            return []

        # Build query
        query = self.db.query(AggregatorOrder).filter(
            AggregatorOrder.venue_id == venue_id
        )

        # Apply date filters
        if start_date:
            query = query.filter(AggregatorOrder.ordered_at >= start_date)
        if end_date:
            query = query.filter(AggregatorOrder.ordered_at <= end_date)

        # Apply platform filter
        if platform:
            if isinstance(platform, DeliveryPlatform):
                platform = platform.value
            query = query.filter(AggregatorOrder.platform == platform)

        # Get completed orders only
        completed_statuses = [
            AggregatorOrderStatus.DELIVERED.value,
            AggregatorOrderStatus.CANCELLED.value,
            AggregatorOrderStatus.REJECTED.value
        ]
        query = query.filter(AggregatorOrder.status.in_(completed_statuses))

        # Order by date descending and limit
        orders = query.order_by(AggregatorOrder.ordered_at.desc()).limit(limit).all()

        return [
            {
                "id": o.id,
                "platform": o.platform,
                "platform_order_id": o.platform_order_id,
                "status": o.status,
                "customer_name": o.customer_name,
                "customer_address": o.customer_address,
                "customer_phone": o.customer_phone,
                "items": o.items,
                "subtotal": float(o.subtotal),
                "delivery_fee": float(o.delivery_fee),
                "platform_fee": float(o.platform_fee),
                "tip": float(o.tip),
                "total": float(o.total),
                "commission_amount": float(o.commission_amount),
                "net_revenue": float(o.net_revenue),
                "ordered_at": o.ordered_at.isoformat(),
                "accepted_at": o.accepted_at.isoformat() if o.accepted_at else None,
                "ready_at": o.ready_at.isoformat() if o.ready_at else None,
                "delivered_at": o.delivered_at.isoformat() if o.delivered_at else None,
                "driver_name": o.driver_name,
                "driver_phone": o.driver_phone
            }
            for o in orders
        ]

    # ==================== OWN FLEET MANAGEMENT ====================

    def add_driver(self, venue_id: int, name: str, phone: str,
                   **kwargs) -> Dict[str, Any]:
        """Add an own fleet driver."""
        from app.models.v6_features_models import OwnDeliveryDriver

        if not self.db:
            return {"success": False, "error": "No database session"}

        driver = OwnDeliveryDriver(
            venue_id=venue_id,
            name=name,
            phone=phone,
            vehicle_type=kwargs.get('vehicle_type', 'car'),
            vehicle_plate=kwargs.get('vehicle_plate'),
            status=DriverStatus.OFFLINE.value
        )

        try:
            self.db.add(driver)
            self.db.commit()
            self.db.refresh(driver)
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to add driver {name}: {e}")
            return {"success": False, "error": f"Failed to add driver: {str(e)}"}

        logger.info(f"Added driver {driver.id}: {name}")

        return {
            "success": True,
            "id": driver.id,
            "name": driver.name,
            "phone": driver.phone,
            "status": driver.status
        }

    def update_driver_status(self, driver_id: int, status: str) -> Dict[str, Any]:
        """Update driver status."""
        from app.models.v6_features_models import OwnDeliveryDriver

        if not self.db:
            return {"success": False, "error": "No database session"}

        driver = self.db.query(OwnDeliveryDriver).filter(
            OwnDeliveryDriver.id == driver_id
        ).first()

        if not driver:
            return {"success": False, "error": "Driver not found"}

        if isinstance(status, DriverStatus):
            status = status.value

        driver.status = status
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            return {"success": False, "error": f"Failed to update driver status: {str(e)}"}

        return {"success": True, "driver_id": driver_id, "status": driver.status}

    def update_driver_location(self, driver_id: int, lat: float,
                                lng: float) -> Dict[str, Any]:
        """Update driver location."""
        from app.models.v6_features_models import OwnDeliveryDriver

        if not self.db:
            return {"success": False, "error": "No database session"}

        driver = self.db.query(OwnDeliveryDriver).filter(
            OwnDeliveryDriver.id == driver_id
        ).first()

        if not driver:
            return {"success": False, "error": "Driver not found"}

        driver.current_lat = lat
        driver.current_lng = lng
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            return {"success": False, "error": f"Failed to update driver location: {str(e)}"}

        return {"success": True, "driver_id": driver_id, "lat": lat, "lng": lng}

    def assign_driver(self, order_id: int, driver_id: int) -> Dict[str, Any]:
        """Assign driver to an order."""
        from app.models.v6_features_models import OwnDeliveryDriver, AggregatorOrder

        if not self.db:
            return {"success": False, "error": "No database session"}

        driver = self.db.query(OwnDeliveryDriver).filter(
            OwnDeliveryDriver.id == driver_id
        ).first()

        order = self.db.query(AggregatorOrder).filter(
            AggregatorOrder.id == order_id
        ).first()

        if not driver or not order:
            return {"success": False, "error": "Driver or order not found"}

        if driver.status != DriverStatus.AVAILABLE.value:
            return {"success": False, "error": "Driver not available"}

        try:
            with self.db.begin_nested():
                driver.status = DriverStatus.ASSIGNED.value
                driver.current_order_id = order_id
                order.driver_name = driver.name
                order.driver_phone = driver.phone
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to assign driver {driver_id} to order {order_id}: {e}")
            return {"success": False, "error": f"Failed to assign driver: {str(e)}"}

        return {"success": True, "order_id": order_id, "driver_id": driver_id}

    def get_drivers(self, venue_id: int, status: str = None) -> List[Dict[str, Any]]:
        """Get drivers for a venue."""
        from app.models.v6_features_models import OwnDeliveryDriver

        if not self.db:
            return []

        query = self.db.query(OwnDeliveryDriver).filter(
            OwnDeliveryDriver.venue_id == venue_id,
            OwnDeliveryDriver.active == True
        )

        if status:
            if isinstance(status, DriverStatus):
                status = status.value
            query = query.filter(OwnDeliveryDriver.status == status)

        drivers = query.all()

        return [
            {
                "id": d.id,
                "name": d.name,
                "phone": d.phone,
                "vehicle_type": d.vehicle_type,
                "vehicle_plate": d.vehicle_plate,
                "status": d.status,
                "current_lat": d.current_lat,
                "current_lng": d.current_lng,
                "current_order_id": d.current_order_id,
                "deliveries_today": d.deliveries_today,
                "rating": float(d.rating)
            }
            for d in drivers
        ]

    def get_available_drivers(self, venue_id: int) -> List[Dict[str, Any]]:
        """Get available drivers."""
        return self.get_drivers(venue_id, DriverStatus.AVAILABLE.value)

    # ==================== DELIVERY ZONES ====================

    def create_zone(self, venue_id: int, name: str, center_lat: float,
                    center_lng: float, **kwargs) -> Dict[str, Any]:
        """Create a delivery zone."""
        from app.models.v6_features_models import DeliveryZoneConfig

        if not self.db:
            return {"success": False, "error": "No database session"}

        zone = DeliveryZoneConfig(
            venue_id=venue_id,
            name=name,
            center_lat=center_lat,
            center_lng=center_lng,
            radius_km=kwargs.get('radius_km', 5.0),
            delivery_fee=kwargs.get('delivery_fee', 3.0),
            min_order_amount=kwargs.get('min_order_amount', 15.0),
            free_delivery_threshold=kwargs.get('free_delivery_threshold'),
            estimated_minutes=kwargs.get('estimated_minutes', 30)
        )

        try:
            self.db.add(zone)
            self.db.commit()
            self.db.refresh(zone)
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create delivery zone {name}: {e}")
            return {"success": False, "error": f"Failed to create zone: {str(e)}"}

        return {
            "success": True,
            "id": zone.id,
            "name": zone.name,
            "radius_km": float(zone.radius_km),
            "delivery_fee": float(zone.delivery_fee)
        }

    def get_zones(self, venue_id: int) -> List[Dict[str, Any]]:
        """Get delivery zones for a venue."""
        from app.models.v6_features_models import DeliveryZoneConfig

        if not self.db:
            return []

        zones = self.db.query(DeliveryZoneConfig).filter(
            DeliveryZoneConfig.venue_id == venue_id,
            DeliveryZoneConfig.active == True
        ).all()

        return [
            {
                "id": z.id,
                "name": z.name,
                "radius_km": float(z.radius_km),
                "center_lat": z.center_lat,
                "center_lng": z.center_lng,
                "delivery_fee": float(z.delivery_fee),
                "min_order_amount": float(z.min_order_amount),
                "free_delivery_threshold": float(z.free_delivery_threshold) if z.free_delivery_threshold else None,
                "estimated_minutes": z.estimated_minutes
            }
            for z in zones
        ]

    # ==================== ANALYTICS ====================

    def get_delivery_stats(self, venue_id: int, start: datetime,
                            end: datetime) -> Dict[str, Any]:
        """Get delivery statistics."""
        from app.models.v6_features_models import AggregatorOrder

        if not self.db:
            return {}

        orders = self.db.query(AggregatorOrder).filter(
            AggregatorOrder.venue_id == venue_id,
            AggregatorOrder.ordered_at >= start,
            AggregatorOrder.ordered_at <= end
        ).all()

        by_platform = {}
        for platform in DeliveryPlatform:
            p_orders = [o for o in orders if o.platform == platform.value]
            if p_orders:
                by_platform[platform.value] = {
                    "orders": len(p_orders),
                    "revenue": sum(float(o.total) for o in p_orders),
                    "commission": sum(float(o.commission_amount) for o in p_orders),
                    "net": sum(float(o.net_revenue) for o in p_orders)
                }

        delivered = [o for o in orders if o.status == AggregatorOrderStatus.DELIVERED.value]
        rejected = [o for o in orders if o.status == AggregatorOrderStatus.REJECTED.value]
        cancelled = [o for o in orders if o.status == AggregatorOrderStatus.CANCELLED.value]

        return {
            "period": f"{start} to {end}",
            "total_orders": len(orders),
            "delivered": len(delivered),
            "rejected": len(rejected),
            "cancelled": len(cancelled),
            "total_revenue": sum(float(o.total) for o in delivered),
            "total_commission": sum(float(o.commission_amount) for o in delivered),
            "net_revenue": sum(float(o.net_revenue) for o in delivered),
            "avg_order_value": sum(float(o.total) for o in delivered) / len(delivered) if delivered else 0,
            "by_platform": by_platform
        }

    def get_dashboard(self, venue_id: int) -> Dict[str, Any]:
        """Get delivery dashboard data."""
        from app.models.v6_features_models import AggregatorOrder, OwnDeliveryDriver

        if not self.db:
            return {}

        today = date.today()
        today_start = datetime.combine(today, datetime.min.time())

        # Today's orders
        orders_today = self.db.query(AggregatorOrder).filter(
            AggregatorOrder.venue_id == venue_id,
            AggregatorOrder.ordered_at >= today_start
        ).all()

        # Active orders
        active = [o for o in orders_today if o.status not in
                  [AggregatorOrderStatus.DELIVERED.value,
                   AggregatorOrderStatus.CANCELLED.value,
                   AggregatorOrderStatus.REJECTED.value]]

        # Drivers
        drivers = self.db.query(OwnDeliveryDriver).filter(
            OwnDeliveryDriver.venue_id == venue_id,
            OwnDeliveryDriver.active == True
        ).all()

        return {
            "orders_today": len(orders_today),
            "active_orders": len(active),
            "revenue_today": sum(float(o.total) for o in orders_today
                                 if o.status == AggregatorOrderStatus.DELIVERED.value),
            "commission_today": sum(float(o.commission_amount) for o in orders_today
                                    if o.status == AggregatorOrderStatus.DELIVERED.value),
            "drivers_total": len(drivers),
            "drivers_available": len([d for d in drivers if d.status == DriverStatus.AVAILABLE.value]),
            "drivers_delivering": len([d for d in drivers if d.status == DriverStatus.DELIVERING.value]),
            "platforms_connected": len(self.get_connected_platforms(venue_id))
        }

    def get_platform_analytics(self, venue_id: int, platform: str,
                                 start_date: datetime = None,
                                 end_date: datetime = None) -> Dict[str, Any]:
        """
        Get detailed analytics for a specific delivery platform.

        Args:
            venue_id: Venue ID
            platform: Platform name (glovo, wolt, bolt_food, etc.)
            start_date: Start date for analytics (default: 30 days ago)
            end_date: End date for analytics (default: now)

        Returns:
            Dictionary with platform analytics including orders, revenue, performance metrics
        """
        from app.models.v6_features_models import AggregatorOrder, DeliveryPlatformCredentials

        if not self.db:
            return {}

        # Default to last 30 days
        if not end_date:
            end_date = datetime.now(timezone.utc)
        if not start_date:
            start_date = end_date - timedelta(days=30)

        if isinstance(platform, DeliveryPlatform):
            platform = platform.value

        # Get platform credentials
        creds = self.db.query(DeliveryPlatformCredentials).filter(
            DeliveryPlatformCredentials.venue_id == venue_id,
            DeliveryPlatformCredentials.platform == platform
        ).first()

        if not creds:
            return {
                "error": "Platform not connected",
                "platform": platform
            }

        # Get orders for this platform in date range
        orders = self.db.query(AggregatorOrder).filter(
            AggregatorOrder.venue_id == venue_id,
            AggregatorOrder.platform == platform,
            AggregatorOrder.ordered_at >= start_date,
            AggregatorOrder.ordered_at <= end_date
        ).all()

        # Calculate metrics
        total_orders = len(orders)
        delivered_orders = [o for o in orders if o.status == AggregatorOrderStatus.DELIVERED.value]
        rejected_orders = [o for o in orders if o.status == AggregatorOrderStatus.REJECTED.value]
        cancelled_orders = [o for o in orders if o.status == AggregatorOrderStatus.CANCELLED.value]

        total_revenue = sum(float(o.total) for o in delivered_orders)
        total_commission = sum(float(o.commission_amount) for o in delivered_orders)
        net_revenue = sum(float(o.net_revenue) for o in delivered_orders)
        avg_order_value = total_revenue / len(delivered_orders) if delivered_orders else 0

        # Calculate average delivery times
        delivery_times = []
        for order in delivered_orders:
            if order.ordered_at and order.delivered_at:
                time_diff = (order.delivered_at - order.ordered_at).total_seconds() / 60
                delivery_times.append(time_diff)

        avg_delivery_time = sum(delivery_times) / len(delivery_times) if delivery_times else 0

        # Calculate acceptance rate
        acceptance_rate = (len(delivered_orders) / total_orders * 100) if total_orders > 0 else 0

        # Daily breakdown
        daily_stats = {}
        for order in delivered_orders:
            day_key = order.ordered_at.date().isoformat()
            if day_key not in daily_stats:
                daily_stats[day_key] = {
                    "orders": 0,
                    "revenue": 0.0,
                    "commission": 0.0,
                    "net_revenue": 0.0
                }
            daily_stats[day_key]["orders"] += 1
            daily_stats[day_key]["revenue"] += float(order.total)
            daily_stats[day_key]["commission"] += float(order.commission_amount)
            daily_stats[day_key]["net_revenue"] += float(order.net_revenue)

        # Peak hours analysis
        hourly_distribution = {}
        for order in orders:
            hour = order.ordered_at.hour
            hourly_distribution[hour] = hourly_distribution.get(hour, 0) + 1

        peak_hour = max(hourly_distribution.items(), key=lambda x: x[1])[0] if hourly_distribution else None

        return {
            "platform": platform,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": (end_date - start_date).days
            },
            "settings": {
                "auto_accept": creds.auto_accept,
                "prep_time_minutes": creds.prep_time_minutes,
                "commission_percent": float(creds.commission_percent),
                "connected": creds.connected,
                "last_sync": creds.last_sync.isoformat() if creds.last_sync else None
            },
            "orders": {
                "total": total_orders,
                "delivered": len(delivered_orders),
                "rejected": len(rejected_orders),
                "cancelled": len(cancelled_orders),
                "acceptance_rate": round(acceptance_rate, 2)
            },
            "revenue": {
                "total": round(total_revenue, 2),
                "commission": round(total_commission, 2),
                "net": round(net_revenue, 2),
                "avg_order_value": round(avg_order_value, 2)
            },
            "performance": {
                "avg_delivery_time_minutes": round(avg_delivery_time, 1),
                "orders_per_day": round(total_orders / max(1, (end_date - start_date).days), 1),
                "peak_hour": peak_hour
            },
            "daily_breakdown": daily_stats,
            "hourly_distribution": hourly_distribution
        }

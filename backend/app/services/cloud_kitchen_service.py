"""
Cloud Kitchen / Ghost Kitchen Service - BJS V6
================================================
Multi-brand virtual kitchen operations with database integration.
"""

from datetime import datetime, timedelta, timezone, date, time
from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
import logging

logger = logging.getLogger(__name__)


class BrandStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    DISCONTINUED = "discontinued"


class StationStatus(str, Enum):
    IDLE = "idle"
    PREPARING = "preparing"
    BUSY = "busy"
    OFFLINE = "offline"


class OrderPriority(str, Enum):
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


# Pydantic models
class VirtualBrandResponse(BaseModel):
    id: int
    venue_id: int
    name: str
    cuisine_type: str
    status: str
    platforms: list
    orders_today: int
    revenue_today: float

    model_config = ConfigDict(from_attributes=True)


class CloudKitchenStationResponse(BaseModel):
    id: int
    venue_id: int
    name: str
    station_type: str
    status: str
    current_orders: int
    max_concurrent_orders: int

    model_config = ConfigDict(from_attributes=True)


class CloudKitchenService:
    """Cloud Kitchen operations management with database persistence."""

    def __init__(self, db_session: Session = None):
        self.db = db_session

    # ==================== VIRTUAL BRAND MANAGEMENT ====================

    def create_brand(self, venue_id: int, name: str, cuisine_type: str,
                     platforms: List[str] = None, description: str = None,
                     operating_hours: Dict = None, **kwargs) -> Dict[str, Any]:
        """Create a new virtual brand."""
        from app.models.v6_features_models import VirtualBrand

        if not self.db:
            logger.warning("No database session - returning mock response")
            return {"id": 1, "name": name, "venue_id": venue_id}

        brand = VirtualBrand(
            venue_id=venue_id,
            name=name,
            cuisine_type=cuisine_type,
            description=description or "",
            platforms=platforms or [],
            operating_hours=operating_hours or {},
            status=BrandStatus.DRAFT.value
        )

        self.db.add(brand)
        self.db.commit()
        self.db.refresh(brand)

        logger.info(f"Created virtual brand '{name}' for venue {venue_id}")

        return {
            "success": True,
            "id": brand.id,
            "venue_id": brand.venue_id,
            "name": brand.name,
            "cuisine_type": brand.cuisine_type,
            "platforms": brand.platforms,
            "status": brand.status
        }

    def activate_brand(self, brand_id: int) -> Dict[str, Any]:
        """Activate a brand to receive orders."""
        from app.models.v6_features_models import VirtualBrand

        if not self.db:
            return {"success": False, "error": "No database session"}

        brand = self.db.query(VirtualBrand).filter(
            VirtualBrand.id == brand_id
        ).first()

        if not brand:
            return {"success": False, "error": "Brand not found"}

        brand.status = BrandStatus.ACTIVE.value
        brand.activated_at = datetime.now(timezone.utc)
        self.db.commit()

        logger.info(f"Activated brand {brand_id}")
        return {"success": True, "brand_id": brand_id, "status": brand.status}

    def pause_brand(self, brand_id: int, reason: str = None) -> Dict[str, Any]:
        """Pause a brand temporarily."""
        from app.models.v6_features_models import VirtualBrand

        if not self.db:
            return {"success": False, "error": "No database session"}

        brand = self.db.query(VirtualBrand).filter(
            VirtualBrand.id == brand_id
        ).first()

        if not brand:
            return {"success": False, "error": "Brand not found"}

        brand.status = BrandStatus.PAUSED.value
        self.db.commit()

        logger.info(f"Paused brand {brand_id}: {reason}")
        return {"success": True, "brand_id": brand_id, "status": brand.status}

    def set_brand_status(self, brand_id: int, status: str) -> Dict[str, Any]:
        """Set brand status by status string."""
        from app.models.v6_features_models import VirtualBrand

        if not self.db:
            return {"success": False, "error": "No database session"}

        brand = self.db.query(VirtualBrand).filter(
            VirtualBrand.id == brand_id
        ).first()

        if not brand:
            return {"success": False, "error": "Brand not found"}

        brand.status = status
        if status == "active":
            brand.activated_at = datetime.now(timezone.utc)
        self.db.commit()

        return {"success": True, "brand_id": brand_id, "status": brand.status}

    def update_virtual_brand(self, brand_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update brand with given fields."""
        from app.models.v6_features_models import VirtualBrand

        if not self.db:
            return {"success": False, "error": "No database session"}

        brand = self.db.query(VirtualBrand).filter(
            VirtualBrand.id == brand_id
        ).first()

        if not brand:
            return {"success": False, "error": "Brand not found"}

        allowed_fields = ['name', 'description', 'cuisine_type', 'platforms',
                          'menu_items', 'operating_hours', 'avg_prep_time_minutes',
                          'logo_url', 'banner_url']

        for field, value in updates.items():
            if field in allowed_fields and value is not None:
                setattr(brand, field, value)

        self.db.commit()
        self.db.refresh(brand)

        return {
            "success": True,
            "id": brand.id,
            "name": brand.name,
            "status": brand.status
        }

    def add_platform(self, brand_id: int, platform: str) -> Dict[str, Any]:
        """Add a delivery platform to a brand."""
        from app.models.v6_features_models import VirtualBrand

        if not self.db:
            return {"success": False, "error": "No database session"}

        brand = self.db.query(VirtualBrand).filter(
            VirtualBrand.id == brand_id
        ).first()

        if not brand:
            return {"success": False, "error": "Brand not found"}

        platforms = list(brand.platforms or [])
        if platform not in platforms:
            platforms.append(platform)
            brand.platforms = platforms
            self.db.commit()

        return {"success": True, "brand_id": brand_id, "platforms": brand.platforms}

    def add_menu_item(self, brand_id: int, item_id: int) -> Dict[str, Any]:
        """Add a menu item to a brand."""
        from app.models.v6_features_models import VirtualBrand

        if not self.db:
            return {"success": False, "error": "No database session"}

        brand = self.db.query(VirtualBrand).filter(
            VirtualBrand.id == brand_id
        ).first()

        if not brand:
            return {"success": False, "error": "Brand not found"}

        menu_items = list(brand.menu_items or [])
        if item_id not in menu_items:
            menu_items.append(item_id)
            brand.menu_items = menu_items
            self.db.commit()

        return {"success": True, "brand_id": brand_id, "menu_items": brand.menu_items}

    def set_operating_hours(self, brand_id: int, day: str,
                            open_time: str, close_time: str) -> Dict[str, Any]:
        """Set operating hours for a brand."""
        from app.models.v6_features_models import VirtualBrand

        if not self.db:
            return {"success": False, "error": "No database session"}

        brand = self.db.query(VirtualBrand).filter(
            VirtualBrand.id == brand_id
        ).first()

        if not brand:
            return {"success": False, "error": "Brand not found"}

        hours = dict(brand.operating_hours or {})
        hours[day] = {"open": open_time, "close": close_time}
        brand.operating_hours = hours
        self.db.commit()

        return {"success": True, "brand_id": brand_id, "operating_hours": brand.operating_hours}

    def is_brand_open(self, brand_id: int) -> bool:
        """Check if brand is currently open."""
        from app.models.v6_features_models import VirtualBrand

        if not self.db:
            return False

        brand = self.db.query(VirtualBrand).filter(
            VirtualBrand.id == brand_id
        ).first()

        if not brand or brand.status != BrandStatus.ACTIVE.value:
            return False

        now = datetime.now(timezone.utc)
        day = now.strftime("%A").lower()
        hours = (brand.operating_hours or {}).get(day)

        if not hours:
            return False

        current_time = now.time()
        open_time = time.fromisoformat(hours["open"])
        close_time = time.fromisoformat(hours["close"])

        return open_time <= current_time <= close_time

    def get_brands(self, venue_id: int, status: str = None) -> List[Dict[str, Any]]:
        """Get all virtual brands for a venue."""
        from app.models.v6_features_models import VirtualBrand

        if not self.db:
            return []

        query = self.db.query(VirtualBrand).filter(
            VirtualBrand.venue_id == venue_id
        )

        if status:
            if isinstance(status, BrandStatus):
                status = status.value
            query = query.filter(VirtualBrand.status == status)

        brands = query.all()

        return [
            {
                "id": b.id,
                "venue_id": b.venue_id,
                "name": b.name,
                "description": b.description,
                "cuisine_type": b.cuisine_type,
                "platforms": b.platforms,
                "status": b.status,
                "orders_today": b.orders_today or 0,
                "revenue_today": float(b.revenue_today or 0),
                "avg_prep_time_minutes": b.avg_prep_time_minutes
            }
            for b in brands
        ]

    def get_virtual_brands(self, venue_id: int, status: str = None) -> List[Dict[str, Any]]:
        """Alias for get_brands for API compatibility."""
        return self.get_brands(venue_id, status)

    def get_brand(self, brand_id: int) -> Optional[Dict[str, Any]]:
        """Get a single brand."""
        from app.models.v6_features_models import VirtualBrand

        if not self.db:
            return None

        brand = self.db.query(VirtualBrand).filter(
            VirtualBrand.id == brand_id
        ).first()

        if not brand:
            return None

        return {
            "id": brand.id,
            "venue_id": brand.venue_id,
            "name": brand.name,
            "description": brand.description,
            "cuisine_type": brand.cuisine_type,
            "platforms": brand.platforms,
            "menu_items": brand.menu_items,
            "operating_hours": brand.operating_hours,
            "status": brand.status,
            "orders_today": brand.orders_today or 0,
            "revenue_today": float(brand.revenue_today or 0)
        }

    # ==================== STATION MANAGEMENT ====================

    def create_station(self, venue_id: int, name: str, station_type: str,
                       max_concurrent: int = 5, max_concurrent_orders: int = None) -> Dict[str, Any]:
        """Create a kitchen station."""
        from app.models.v6_features_models import CloudKitchenStation

        if not self.db:
            return {"success": False, "error": "No database session"}

        station = CloudKitchenStation(
            venue_id=venue_id,
            name=name,
            station_type=station_type,
            max_concurrent_orders=max_concurrent_orders or max_concurrent,
            status=StationStatus.IDLE.value
        )

        self.db.add(station)
        self.db.commit()
        self.db.refresh(station)

        logger.info(f"Created kitchen station '{name}' for venue {venue_id}")

        return {
            "success": True,
            "id": station.id,
            "venue_id": station.venue_id,
            "name": station.name,
            "station_type": station.station_type,
            "status": station.status
        }

    def assign_brand_to_station(self, station_id: int, brand_id: int) -> Dict[str, Any]:
        """Assign a single brand to a station."""
        from app.models.v6_features_models import CloudKitchenStation

        if not self.db:
            return {"success": False, "error": "No database session"}

        station = self.db.query(CloudKitchenStation).filter(
            CloudKitchenStation.id == station_id
        ).first()

        if not station:
            return {"success": False, "error": "Station not found"}

        brands = list(station.brands_assigned or [])
        if brand_id not in brands:
            brands.append(brand_id)
            station.brands_assigned = brands
            self.db.commit()

        return {"success": True, "station_id": station_id, "brands_assigned": station.brands_assigned}

    def assign_brands_to_station(self, station_id: int, brand_ids: List[int]) -> Dict[str, Any]:
        """Assign brands to a station."""
        from app.models.v6_features_models import CloudKitchenStation

        if not self.db:
            return {"success": False, "error": "No database session"}

        station = self.db.query(CloudKitchenStation).filter(
            CloudKitchenStation.id == station_id
        ).first()

        if not station:
            return {"success": False, "error": "Station not found"}

        station.brands_assigned = brand_ids
        self.db.commit()

        return {"success": True, "station_id": station_id, "brands_assigned": brand_ids}

    def update_station_status(self, station_id: int, status: StationStatus) -> Dict[str, Any]:
        """Update station status."""
        from app.models.v6_features_models import CloudKitchenStation

        if not self.db:
            return {"success": False, "error": "No database session"}

        station = self.db.query(CloudKitchenStation).filter(
            CloudKitchenStation.id == station_id
        ).first()

        if not station:
            return {"success": False, "error": "Station not found"}

        station.status = status.value if isinstance(status, StationStatus) else status
        self.db.commit()

        return {"success": True, "station_id": station_id, "status": station.status}

    def assign_staff_to_station(self, station_id: int, staff_id: int) -> Dict[str, Any]:
        """Assign a staff member to a station."""
        from app.models.v6_features_models import CloudKitchenStation

        if not self.db:
            return {"success": False, "error": "No database session"}

        station = self.db.query(CloudKitchenStation).filter(
            CloudKitchenStation.id == station_id
        ).first()

        if not station:
            return {"success": False, "error": "Station not found"}

        staff = list(station.staff_assigned or [])
        if staff_id not in staff:
            staff.append(staff_id)
            station.staff_assigned = staff
            self.db.commit()

        return {"success": True, "station_id": station_id, "staff_assigned": station.staff_assigned}

    def get_available_station(self, venue_id: int, station_type: str) -> Optional[Dict[str, Any]]:
        """Get an available station of a given type."""
        from app.models.v6_features_models import CloudKitchenStation

        if not self.db:
            return None

        station = self.db.query(CloudKitchenStation).filter(
            CloudKitchenStation.venue_id == venue_id,
            CloudKitchenStation.station_type == station_type,
            CloudKitchenStation.status != StationStatus.OFFLINE.value,
            CloudKitchenStation.current_orders < CloudKitchenStation.max_concurrent_orders
        ).order_by(CloudKitchenStation.current_orders.asc()).first()

        if station:
            return {
                "id": station.id,
                "name": station.name,
                "current_orders": station.current_orders,
                "max_concurrent_orders": station.max_concurrent_orders
            }

        return None

    def get_stations(self, venue_id: int) -> List[Dict[str, Any]]:
        """Get all stations for a venue."""
        from app.models.v6_features_models import CloudKitchenStation

        if not self.db:
            return []

        stations = self.db.query(CloudKitchenStation).filter(
            CloudKitchenStation.venue_id == venue_id
        ).all()

        return [
            {
                "id": s.id,
                "venue_id": s.venue_id,
                "name": s.name,
                "station_type": s.station_type,
                "brands_assigned": s.brands_assigned,
                "max_concurrent_orders": s.max_concurrent_orders,
                "current_orders": s.current_orders,
                "status": s.status,
                "staff_assigned": s.staff_assigned,
                "equipment": s.equipment
            }
            for s in stations
        ]

    def get_station_utilization(self, venue_id: int) -> Dict[str, Dict]:
        """Get station utilization stats."""
        from app.models.v6_features_models import CloudKitchenStation

        if not self.db:
            return {}

        stations = self.db.query(CloudKitchenStation).filter(
            CloudKitchenStation.venue_id == venue_id
        ).all()

        return {
            str(s.id): {
                "name": s.name,
                "type": s.station_type,
                "current_orders": s.current_orders,
                "max_capacity": s.max_concurrent_orders,
                "utilization": (s.current_orders / s.max_concurrent_orders * 100)
                if s.max_concurrent_orders else 0,
                "status": s.status
            }
            for s in stations
        }

    # ==================== ORDER MANAGEMENT ====================

    def route_order(self, venue_id: int, brand_id: int, platform: str,
                    platform_order_id: str, items: List[Dict]) -> Dict[str, Any]:
        """Route order to appropriate stations."""
        from app.models.v6_features_models import VirtualBrandOrder, VirtualBrand, CloudKitchenStation

        if not self.db:
            return {"success": False, "error": "No database session"}

        brand = self.db.query(VirtualBrand).filter(
            VirtualBrand.id == brand_id
        ).first()

        if not brand:
            return {"success": False, "error": "Brand not found"}

        total = sum(i.get("price", 0) * i.get("quantity", 1) for i in items)

        # Calculate station assignments
        station_assignments = {}
        stations = self.db.query(CloudKitchenStation).filter(
            CloudKitchenStation.venue_id == venue_id
        ).all()

        for item in items:
            station_type = item.get("station_type", "prep")
            # Find matching station
            for station in stations:
                if station.station_type == station_type:
                    if station.current_orders < station.max_concurrent_orders:
                        item_id = str(item.get('id', item.get('name', 'item')))
                        station_assignments[item_id] = station.id
                        break

        order = VirtualBrandOrder(
            venue_id=venue_id,
            brand_id=brand_id,
            platform=platform,
            platform_order_id=platform_order_id,
            items=items,
            station_assignments=station_assignments,
            total=total,
            status="received",
            estimated_ready=datetime.now(timezone.utc) + timedelta(minutes=brand.avg_prep_time_minutes or 20)
        )

        self.db.add(order)

        # Update brand stats
        brand.orders_today = (brand.orders_today or 0) + 1
        brand.revenue_today = float(brand.revenue_today or 0) + total

        # Update station order counts
        assigned_stations = set(station_assignments.values())
        for s in stations:
            if s.id in assigned_stations:
                s.current_orders = (s.current_orders or 0) + 1
                if s.current_orders >= s.max_concurrent_orders:
                    s.status = StationStatus.BUSY.value
                else:
                    s.status = StationStatus.PREPARING.value

        self.db.commit()
        self.db.refresh(order)

        logger.info(f"Routed order {order.id} for brand {brand.name} via {platform}")

        return {
            "success": True,
            "id": order.id,
            "brand_id": brand_id,
            "platform": platform,
            "platform_order_id": platform_order_id,
            "status": order.status,
            "total": float(total),
            "estimated_ready": order.estimated_ready.isoformat() if order.estimated_ready else None,
            "station_assignments": station_assignments
        }

    def complete_order(self, order_id: int) -> Dict[str, Any]:
        """Complete an order."""
        from app.models.v6_features_models import VirtualBrandOrder, CloudKitchenStation

        if not self.db:
            return {"success": False, "error": "No database session"}

        order = self.db.query(VirtualBrandOrder).filter(
            VirtualBrandOrder.id == order_id
        ).first()

        if not order:
            return {"success": False, "error": "Order not found"}

        order.status = "completed"
        order.completed_at = datetime.now(timezone.utc)

        # Update station order counts
        assigned_stations = set((order.station_assignments or {}).values())
        if assigned_stations:
            stations = self.db.query(CloudKitchenStation).filter(
                CloudKitchenStation.id.in_(assigned_stations)
            ).all()

            for s in stations:
                s.current_orders = max(0, (s.current_orders or 1) - 1)
                if s.current_orders == 0:
                    s.status = StationStatus.IDLE.value
                elif s.current_orders < s.max_concurrent_orders:
                    s.status = StationStatus.PREPARING.value

        self.db.commit()

        logger.info(f"Completed order {order_id}")
        return {"success": True, "order_id": order_id, "status": order.status}

    def update_order_status(self, order_id: int, status: str) -> Dict[str, Any]:
        """Update order status."""
        from app.models.v6_features_models import VirtualBrandOrder

        if not self.db:
            return {"success": False, "error": "No database session"}

        order = self.db.query(VirtualBrandOrder).filter(
            VirtualBrandOrder.id == order_id
        ).first()

        if not order:
            return {"success": False, "error": "Order not found"}

        old_status = order.status
        order.status = status

        if status == "completed":
            return self.complete_order(order_id)

        self.db.commit()

        logger.info(f"Order {order_id} status: {old_status} -> {status}")
        return {"success": True, "order_id": order_id, "status": status}

    def get_active_orders(self, venue_id: int, brand_id: int = None,
                          platform: str = None) -> List[Dict[str, Any]]:
        """Get active orders."""
        from app.models.v6_features_models import VirtualBrandOrder

        if not self.db:
            return []

        query = self.db.query(VirtualBrandOrder).filter(
            VirtualBrandOrder.venue_id == venue_id,
            VirtualBrandOrder.status.notin_(["completed", "cancelled"])
        )

        if brand_id:
            query = query.filter(VirtualBrandOrder.brand_id == brand_id)
        if platform:
            query = query.filter(VirtualBrandOrder.platform == platform)

        orders = query.order_by(VirtualBrandOrder.created_at.asc()).all()

        return [
            {
                "id": o.id,
                "brand_id": o.brand_id,
                "platform": o.platform,
                "platform_order_id": o.platform_order_id,
                "items": o.items,
                "total": float(o.total),
                "status": o.status,
                "created_at": o.created_at.isoformat(),
                "estimated_ready": o.estimated_ready.isoformat() if o.estimated_ready else None,
                "station_assignments": o.station_assignments
            }
            for o in orders
        ]

    # ==================== ANALYTICS & DASHBOARD ====================

    def get_brand_performance(self, venue_id: int, start: datetime,
                               end: datetime) -> Dict[str, Dict]:
        """Get brand performance for a time period."""
        from app.models.v6_features_models import VirtualBrand, VirtualBrandOrder

        if not self.db:
            return {}

        brands = self.db.query(VirtualBrand).filter(
            VirtualBrand.venue_id == venue_id
        ).all()

        performance = {}

        for brand in brands:
            orders = self.db.query(VirtualBrandOrder).filter(
                VirtualBrandOrder.brand_id == brand.id,
                VirtualBrandOrder.created_at >= start,
                VirtualBrandOrder.created_at <= end
            ).all()

            completed = [o for o in orders if o.status == "completed"]

            performance[str(brand.id)] = {
                "name": brand.name,
                "orders": len(orders),
                "completed": len(completed),
                "revenue": sum(float(o.total) for o in completed),
                "avg_order_value": (sum(float(o.total) for o in completed) / len(completed))
                if completed else 0,
                "platforms": {
                    p: len([o for o in orders if o.platform == p])
                    for p in (brand.platforms or [])
                }
            }

        return performance

    def get_dashboard(self, venue_id: int) -> Dict[str, Any]:
        """Get cloud kitchen dashboard data."""
        from app.models.v6_features_models import VirtualBrand, CloudKitchenStation, VirtualBrandOrder

        if not self.db:
            return {}

        today = date.today()
        today_start = datetime.combine(today, datetime.min.time())

        brands = self.db.query(VirtualBrand).filter(
            VirtualBrand.venue_id == venue_id
        ).all()

        stations = self.db.query(CloudKitchenStation).filter(
            CloudKitchenStation.venue_id == venue_id
        ).all()

        active_orders = self.db.query(VirtualBrandOrder).filter(
            VirtualBrandOrder.venue_id == venue_id,
            VirtualBrandOrder.status.notin_(["completed", "cancelled"]),
            VirtualBrandOrder.created_at >= today_start
        ).count()

        completed_orders = self.db.query(VirtualBrandOrder).filter(
            VirtualBrandOrder.venue_id == venue_id,
            VirtualBrandOrder.status == "completed",
            VirtualBrandOrder.created_at >= today_start
        ).all()

        return {
            "active_brands": len([b for b in brands if b.status == BrandStatus.ACTIVE.value]),
            "total_brands": len(brands),
            "active_stations": len([s for s in stations if s.status != StationStatus.OFFLINE.value]),
            "total_stations": len(stations),
            "active_orders": active_orders,
            "completed_today": len(completed_orders),
            "revenue_today": sum(float(b.revenue_today or 0) for b in brands),
            "avg_completion_time": self._calculate_avg_completion_time(completed_orders),
            "brands_summary": [
                {
                    "id": b.id,
                    "name": b.name,
                    "status": b.status,
                    "orders_today": b.orders_today or 0,
                    "revenue_today": float(b.revenue_today or 0)
                }
                for b in brands
            ],
            "stations_summary": [
                {
                    "id": s.id,
                    "name": s.name,
                    "status": s.status,
                    "current_orders": s.current_orders,
                    "capacity_percent": (s.current_orders / s.max_concurrent_orders * 100)
                    if s.max_concurrent_orders else 0
                }
                for s in stations
            ]
        }

    def _calculate_avg_completion_time(self, orders) -> float:
        """Calculate average order completion time in minutes."""
        times = []
        for o in orders:
            if o.completed_at and o.created_at:
                delta = (o.completed_at - o.created_at).total_seconds() / 60
                times.append(delta)
        return sum(times) / len(times) if times else 0

    def reset_daily_stats(self, venue_id: int) -> Dict[str, Any]:
        """Reset daily statistics (call at midnight)."""
        from app.models.v6_features_models import VirtualBrand

        if not self.db:
            return {"success": False, "error": "No database session"}

        brands = self.db.query(VirtualBrand).filter(
            VirtualBrand.venue_id == venue_id
        ).all()

        for brand in brands:
            brand.orders_today = 0
            brand.revenue_today = 0

        self.db.commit()

        logger.info(f"Reset daily stats for venue {venue_id}")
        return {"success": True, "brands_reset": len(brands)}

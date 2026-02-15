"""
Drive-Thru Module Service - BJS V6
===================================
Lane management, order display, vehicle timing, license plate recognition
with full database integration.
"""

from datetime import datetime, timedelta, timezone, date
from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
import logging

logger = logging.getLogger(__name__)


class LaneStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    MAINTENANCE = "maintenance"


class VehicleStatus(str, Enum):
    AT_MENU = "at_menu"
    ORDERING = "ordering"
    AT_PAYMENT = "at_payment"
    AT_PICKUP = "at_pickup"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


# Pydantic models for API responses
class DriveThruLaneResponse(BaseModel):
    id: int
    venue_id: int
    lane_number: int
    lane_type: str
    status: str
    queue_length: int
    avg_service_time_seconds: int
    total_vehicles_today: int
    revenue_today: float

    model_config = ConfigDict(from_attributes=True)


class DriveThruVehicleResponse(BaseModel):
    id: int
    venue_id: int
    lane_id: int
    license_plate: Optional[str]
    customer_name: Optional[str]
    order_id: Optional[int]
    status: str
    is_preorder: bool
    entered_at: datetime
    order_started_at: Optional[datetime]
    order_completed_at: Optional[datetime]
    payment_at: Optional[datetime]
    pickup_at: Optional[datetime]
    exited_at: Optional[datetime]
    total_time_seconds: Optional[int]

    model_config = ConfigDict(from_attributes=True)


class DriveThruService:
    """Drive-thru operations management with database persistence."""

    # Target times in seconds
    TARGET_TIMES = {
        "order": 60,      # Time to take order
        "payment": 30,    # Time at payment window
        "pickup": 45,     # Time at pickup window
        "total": 180      # Total drive-thru time
    }

    def __init__(self, db_session: Session = None):
        self.db = db_session

    # ==================== LANE MANAGEMENT ====================

    def create_lane(self, venue_id: int, lane_number: int,
                    lane_type: str = "standard") -> Dict[str, Any]:
        """Create a new drive-thru lane."""
        from app.models.v6_features_models import DriveThruLane

        if not self.db:
            logger.warning("No database session - returning mock response")
            return {"id": 1, "venue_id": venue_id, "lane_number": lane_number}

        # Check if lane already exists
        existing = self.db.query(DriveThruLane).filter(
            DriveThruLane.venue_id == venue_id,
            DriveThruLane.lane_number == lane_number
        ).first()

        if existing:
            return {
                "success": False,
                "error": f"Lane {lane_number} already exists for venue {venue_id}"
            }

        lane = DriveThruLane(
            venue_id=venue_id,
            lane_number=lane_number,
            lane_type=lane_type,
            status=LaneStatus.OPEN.value
        )

        self.db.add(lane)
        self.db.commit()
        self.db.refresh(lane)

        logger.info(f"Created drive-thru lane {lane_number} for venue {venue_id}")

        return {
            "success": True,
            "id": lane.id,
            "venue_id": lane.venue_id,
            "lane_number": lane.lane_number,
            "lane_type": lane.lane_type,
            "status": lane.status
        }

    def open_lane(self, lane_id: int) -> Dict[str, Any]:
        """Open a drive-thru lane."""
        from app.models.v6_features_models import DriveThruLane

        if not self.db:
            return {"success": False, "error": "No database session"}

        lane = self.db.query(DriveThruLane).filter(
            DriveThruLane.id == lane_id
        ).first()

        if not lane:
            return {"success": False, "error": "Lane not found"}

        lane.status = LaneStatus.OPEN.value
        self.db.commit()

        logger.info(f"Opened lane {lane_id}")
        return {"success": True, "lane_id": lane_id, "status": lane.status}

    def close_lane(self, lane_id: int) -> Dict[str, Any]:
        """Close a drive-thru lane."""
        from app.models.v6_features_models import DriveThruLane

        if not self.db:
            return {"success": False, "error": "No database session"}

        lane = self.db.query(DriveThruLane).filter(
            DriveThruLane.id == lane_id
        ).first()

        if not lane:
            return {"success": False, "error": "Lane not found"}

        lane.status = LaneStatus.CLOSED.value
        self.db.commit()

        logger.info(f"Closed lane {lane_id}")
        return {"success": True, "lane_id": lane_id, "status": lane.status}

    def get_lanes(self, venue_id: int) -> List[Dict[str, Any]]:
        """Get all lanes for a venue."""
        from app.models.v6_features_models import DriveThruLane

        if not self.db:
            return []

        lanes = self.db.query(DriveThruLane).filter(
            DriveThruLane.venue_id == venue_id
        ).all()

        return [
            {
                "id": l.id,
                "venue_id": l.venue_id,
                "lane_number": l.lane_number,
                "lane_type": l.lane_type,
                "status": l.status,
                "queue_length": l.queue_length,
                "avg_service_time_seconds": l.avg_service_time_seconds,
                "total_vehicles_today": l.total_vehicles_today,
                "revenue_today": float(l.revenue_today or 0)
            }
            for l in lanes
        ]

    def get_best_lane(self, venue_id: int, is_preorder: bool = False) -> Optional[Dict[str, Any]]:
        """Get lane with shortest queue."""
        from app.models.v6_features_models import DriveThruLane

        if not self.db:
            return None

        query = self.db.query(DriveThruLane).filter(
            DriveThruLane.venue_id == venue_id,
            DriveThruLane.status == LaneStatus.OPEN.value
        )

        if is_preorder:
            # Try preorder lanes first
            preorder_lanes = query.filter(
                DriveThruLane.lane_type == "preorder"
            ).order_by(DriveThruLane.queue_length.asc()).first()

            if preorder_lanes:
                return {
                    "id": preorder_lanes.id,
                    "lane_number": preorder_lanes.lane_number,
                    "queue_length": preorder_lanes.queue_length
                }

        lane = query.order_by(DriveThruLane.queue_length.asc()).first()

        if lane:
            return {
                "id": lane.id,
                "lane_number": lane.lane_number,
                "queue_length": lane.queue_length
            }

        return None

    # ==================== VEHICLE TRACKING ====================

    def register_vehicle(self, venue_id: int, lane_id: int,
                         license_plate: Optional[str] = None,
                         is_preorder: bool = False) -> Dict[str, Any]:
        """Register a new vehicle in the drive-thru lane."""
        from app.models.v6_features_models import DriveThruVehicle, DriveThruLane

        if not self.db:
            return {"success": False, "error": "No database session"}

        lane = self.db.query(DriveThruLane).filter(
            DriveThruLane.id == lane_id
        ).first()

        if not lane:
            return {"success": False, "error": "Lane not found"}

        vehicle = DriveThruVehicle(
            venue_id=venue_id,
            lane_id=lane_id,
            license_plate=license_plate,
            is_preorder=is_preorder,
            status=VehicleStatus.AT_MENU.value,
            entered_at=datetime.now(timezone.utc)
        )

        self.db.add(vehicle)

        # Update lane queue
        lane.queue_length = (lane.queue_length or 0) + 1

        self.db.commit()
        self.db.refresh(vehicle)

        logger.info(f"Registered vehicle {vehicle.id} in lane {lane_id}")

        return {
            "success": True,
            "id": vehicle.id,
            "venue_id": vehicle.venue_id,
            "lane_id": vehicle.lane_id,
            "license_plate": vehicle.license_plate,
            "status": vehicle.status,
            "entered_at": vehicle.entered_at.isoformat()
        }

    def start_order(self, vehicle_id: int) -> Dict[str, Any]:
        """Mark vehicle as ordering."""
        from app.models.v6_features_models import DriveThruVehicle

        if not self.db:
            return {"success": False, "error": "No database session"}

        vehicle = self.db.query(DriveThruVehicle).filter(
            DriveThruVehicle.id == vehicle_id
        ).first()

        if not vehicle:
            return {"success": False, "error": "Vehicle not found"}

        vehicle.status = VehicleStatus.ORDERING.value
        vehicle.order_started_at = datetime.now(timezone.utc)
        self.db.commit()

        return {"success": True, "vehicle_id": vehicle_id, "status": vehicle.status}

    def complete_order(self, vehicle_id: int, order_id: int) -> Dict[str, Any]:
        """Mark order as complete, vehicle moves to payment."""
        from app.models.v6_features_models import DriveThruVehicle

        if not self.db:
            return {"success": False, "error": "No database session"}

        vehicle = self.db.query(DriveThruVehicle).filter(
            DriveThruVehicle.id == vehicle_id
        ).first()

        if not vehicle:
            return {"success": False, "error": "Vehicle not found"}

        vehicle.order_id = order_id
        vehicle.order_completed_at = datetime.now(timezone.utc)
        vehicle.status = VehicleStatus.AT_PAYMENT.value
        self.db.commit()

        return {
            "success": True,
            "vehicle_id": vehicle_id,
            "order_id": order_id,
            "status": vehicle.status
        }

    def process_payment(self, vehicle_id: int, payment_method: str) -> Dict[str, Any]:
        """Process payment, vehicle moves to pickup."""
        from app.models.v6_features_models import DriveThruVehicle

        if not self.db:
            return {"success": False, "error": "No database session"}

        vehicle = self.db.query(DriveThruVehicle).filter(
            DriveThruVehicle.id == vehicle_id
        ).first()

        if not vehicle:
            return {"success": False, "error": "Vehicle not found"}

        vehicle.payment_at = datetime.now(timezone.utc)
        vehicle.status = VehicleStatus.AT_PICKUP.value
        self.db.commit()

        return {
            "success": True,
            "vehicle_id": vehicle_id,
            "payment_method": payment_method,
            "status": vehicle.status
        }

    def complete_pickup(self, vehicle_id: int) -> Dict[str, Any]:
        """Complete pickup, vehicle exits."""
        from app.models.v6_features_models import DriveThruVehicle, DriveThruLane

        if not self.db:
            return {"success": False, "error": "No database session"}

        vehicle = self.db.query(DriveThruVehicle).filter(
            DriveThruVehicle.id == vehicle_id
        ).first()

        if not vehicle:
            return {"success": False, "error": "Vehicle not found"}

        now = datetime.now(timezone.utc)
        vehicle.pickup_at = now
        vehicle.exited_at = now
        vehicle.status = VehicleStatus.COMPLETED.value
        vehicle.total_time_seconds = int((now - vehicle.entered_at).total_seconds())

        # Update lane stats
        lane = self.db.query(DriveThruLane).filter(
            DriveThruLane.id == vehicle.lane_id
        ).first()

        if lane:
            lane.queue_length = max(0, (lane.queue_length or 1) - 1)
            lane.total_vehicles_today = (lane.total_vehicles_today or 0) + 1

            # Update average service time (rolling average)
            old_total = lane.total_vehicles_today - 1
            if old_total > 0:
                lane.avg_service_time_seconds = int(
                    (lane.avg_service_time_seconds * old_total + vehicle.total_time_seconds) /
                    lane.total_vehicles_today
                )
            else:
                lane.avg_service_time_seconds = vehicle.total_time_seconds

        self.db.commit()

        logger.info(f"Vehicle {vehicle_id} completed in {vehicle.total_time_seconds}s")

        return {
            "success": True,
            "vehicle_id": vehicle_id,
            "status": vehicle.status,
            "total_time_seconds": vehicle.total_time_seconds
        }

    def mark_abandoned(self, vehicle_id: int) -> Dict[str, Any]:
        """Mark vehicle as abandoned (left lane without ordering)."""
        from app.models.v6_features_models import DriveThruVehicle, DriveThruLane

        if not self.db:
            return {"success": False, "error": "No database session"}

        vehicle = self.db.query(DriveThruVehicle).filter(
            DriveThruVehicle.id == vehicle_id
        ).first()

        if not vehicle:
            return {"success": False, "error": "Vehicle not found"}

        vehicle.status = VehicleStatus.ABANDONED.value
        vehicle.exited_at = datetime.now(timezone.utc)

        # Update lane queue
        lane = self.db.query(DriveThruLane).filter(
            DriveThruLane.id == vehicle.lane_id
        ).first()

        if lane:
            lane.queue_length = max(0, (lane.queue_length or 1) - 1)

        self.db.commit()

        return {"success": True, "vehicle_id": vehicle_id, "status": vehicle.status}

    # ==================== ORDER MANAGEMENT ====================

    def create_order(self, venue_id: int, vehicle_id: int,
                     items: List[Dict]) -> Dict[str, Any]:
        """Create a drive-thru order."""
        from app.models.v6_features_models import DriveThruOrderDisplay, DriveThruVehicle

        if not self.db:
            return {"success": False, "error": "No database session"}

        vehicle = self.db.query(DriveThruVehicle).filter(
            DriveThruVehicle.id == vehicle_id
        ).first()

        if not vehicle:
            return {"success": False, "error": "Vehicle not found"}

        subtotal = sum(i.get("price", 0) * i.get("quantity", 1) for i in items)
        tax = subtotal * 0.20  # 20% VAT

        display = DriveThruOrderDisplay(
            venue_id=venue_id,
            vehicle_id=vehicle_id,
            items=items,
            subtotal=subtotal,
            tax=tax,
            total=subtotal + tax,
            status="pending"
        )

        self.db.add(display)
        self.db.commit()
        self.db.refresh(display)

        return {
            "success": True,
            "id": display.id,
            "vehicle_id": vehicle_id,
            "items": items,
            "subtotal": float(subtotal),
            "tax": float(tax),
            "total": float(display.total)
        }

    def mark_order_ready(self, display_id: int) -> Dict[str, Any]:
        """Mark order as ready for pickup."""
        from app.models.v6_features_models import DriveThruOrderDisplay

        if not self.db:
            return {"success": False, "error": "No database session"}

        display = self.db.query(DriveThruOrderDisplay).filter(
            DriveThruOrderDisplay.id == display_id
        ).first()

        if not display:
            return {"success": False, "error": "Order display not found"}

        display.status = "ready"
        display.ready_at = datetime.now(timezone.utc)
        self.db.commit()

        return {"success": True, "id": display_id, "status": display.status}

    # ==================== DISPLAY BOARDS ====================

    def get_menu_board_data(self, venue_id: int) -> Dict[str, Any]:
        """Data for outdoor menu display."""
        return {
            "venue_id": venue_id,
            "current_wait_minutes": self._estimate_wait_time(venue_id),
            "featured_items": [],  # Would be populated from menu
            "promotions": []
        }

    def get_order_confirmation_display(self, vehicle_id: int) -> Dict[str, Any]:
        """Data for order confirmation screen."""
        from app.models.v6_features_models import DriveThruOrderDisplay

        if not self.db:
            return {"error": "No database session"}

        display = self.db.query(DriveThruOrderDisplay).filter(
            DriveThruOrderDisplay.vehicle_id == vehicle_id
        ).order_by(DriveThruOrderDisplay.created_at.desc()).first()

        if not display:
            return {"error": "No order found"}

        return {
            "order_id": display.id,
            "items": display.items,
            "total": float(display.total),
            "estimated_ready": 3  # minutes
        }

    def get_pickup_display(self, venue_id: int) -> List[Dict[str, Any]]:
        """Data for pickup window display showing ready orders."""
        from app.models.v6_features_models import DriveThruVehicle, DriveThruLane

        if not self.db:
            return []

        vehicles = self.db.query(DriveThruVehicle).filter(
            DriveThruVehicle.venue_id == venue_id,
            DriveThruVehicle.status == VehicleStatus.AT_PICKUP.value
        ).all()

        result = []
        for v in vehicles:
            lane = self.db.query(DriveThruLane).filter(
                DriveThruLane.id == v.lane_id
            ).first()

            result.append({
                "order_id": v.order_id,
                "vehicle": v.license_plate or f"Lane {lane.lane_number if lane else '?'}",
                "status": "READY"
            })

        return result

    # ==================== ANALYTICS ====================

    def _estimate_wait_time(self, venue_id: int) -> int:
        """Estimate wait time in minutes."""
        from app.models.v6_features_models import DriveThruLane

        if not self.db:
            return 0

        lanes = self.db.query(DriveThruLane).filter(
            DriveThruLane.venue_id == venue_id,
            DriveThruLane.status == LaneStatus.OPEN.value
        ).all()

        if not lanes:
            return 0

        min_queue = min(l.queue_length or 0 for l in lanes)
        avg_time = sum(l.avg_service_time_seconds or 180 for l in lanes) / len(lanes)

        return int((min_queue * avg_time) / 60)  # Convert to minutes

    def get_stats(self, venue_id: int) -> Dict[str, Any]:
        """Get drive-thru statistics for today."""
        from app.models.v6_features_models import DriveThruVehicle, DriveThruLane

        if not self.db:
            return {}

        today = date.today()
        today_start = datetime.combine(today, datetime.min.time())

        vehicles = self.db.query(DriveThruVehicle).filter(
            DriveThruVehicle.venue_id == venue_id,
            DriveThruVehicle.entered_at >= today_start
        ).all()

        completed = [v for v in vehicles if v.status == VehicleStatus.COMPLETED.value]
        times = [v.total_time_seconds for v in completed if v.total_time_seconds]

        lanes = self.db.query(DriveThruLane).filter(
            DriveThruLane.venue_id == venue_id
        ).all()

        return {
            "total_vehicles": len(vehicles),
            "completed": len(completed),
            "abandoned": len([v for v in vehicles if v.status == VehicleStatus.ABANDONED.value]),
            "currently_in_lane": len([v for v in vehicles if v.status not in
                                      [VehicleStatus.COMPLETED.value, VehicleStatus.ABANDONED.value]]),
            "avg_service_time": sum(times) / len(times) if times else 0,
            "fastest_time": min(times) if times else 0,
            "slowest_time": max(times) if times else 0,
            "target_met_percent": (len([t for t in times if t <= self.TARGET_TIMES["total"]]) /
                                   len(times) * 100) if times else 100,
            "revenue": sum(float(l.revenue_today or 0) for l in lanes),
            "lanes_open": len([l for l in lanes if l.status == LaneStatus.OPEN.value])
        }

    def reset_daily_stats(self, venue_id: int) -> Dict[str, Any]:
        """Reset daily statistics for all lanes (call at midnight)."""
        from app.models.v6_features_models import DriveThruLane

        if not self.db:
            return {"success": False, "error": "No database session"}

        lanes = self.db.query(DriveThruLane).filter(
            DriveThruLane.venue_id == venue_id
        ).all()

        for lane in lanes:
            lane.total_vehicles_today = 0
            lane.revenue_today = 0

        self.db.commit()

        logger.info(f"Reset daily stats for venue {venue_id}")
        return {"success": True, "lanes_reset": len(lanes)}

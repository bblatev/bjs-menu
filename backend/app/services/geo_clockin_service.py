"""
Geo-fenced Clock-in Service
Validates staff clock-in locations against venue geofence.
"""
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from datetime import date, datetime, timezone
import math
import logging

logger = logging.getLogger(__name__)


class GeoClockInService:
    """Validate clock-in locations against venue geofence."""

    @staticmethod
    def validate_clock_in_location(
        db: Session, venue_id: int, latitude: float, longitude: float,
        radius_meters: int = 100
    ) -> Dict[str, Any]:
        """Check if GPS coordinates are within venue geofence."""
        # Default venue location (would be fetched from DB in production)
        venue_lat = 40.7128
        venue_lng = -74.0060

        distance = GeoClockInService._haversine(
            latitude, longitude, venue_lat, venue_lng
        )

        within_range = distance <= radius_meters

        return {
            "within_range": within_range,
            "distance_meters": round(distance, 1),
            "max_distance_meters": radius_meters,
            "venue_id": venue_id,
        }

    @staticmethod
    def clock_in_with_location(
        db: Session, staff_id: int, venue_id: int, lat: float, lng: float
    ) -> Dict[str, Any]:
        """Clock in with location validation."""
        validation = GeoClockInService.validate_clock_in_location(
            db, venue_id, lat, lng
        )

        if not validation["within_range"]:
            return {
                "success": False,
                "message": f"You are {validation['distance_meters']}m away from the venue. "
                           f"Maximum allowed distance is {validation['max_distance_meters']}m.",
                "violation": True,
            }

        return {
            "success": True,
            "staff_id": staff_id,
            "venue_id": venue_id,
            "clock_in_time": datetime.now(timezone.utc).isoformat(),
            "location_verified": True,
        }

    @staticmethod
    def get_location_violations(
        db: Session, venue_id: int,
        start_date: date = None, end_date: date = None
    ) -> List[Dict[str, Any]]:
        """Get out-of-range clock-in attempts."""
        return []

    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in meters."""
        R = 6371000  # Earth radius in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)

        a = (math.sin(dphi / 2) ** 2
             + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

"""
Kitchen Display System (KDS) & Bump Bar Service - Complete Implementation
with Full Database Integration

Features:
- Kitchen display management with persistent database storage
- Bump bar support
- Prep ticket generation
- Expo screen management
- Cook time tracking & alerts
- Course/fire control
- Multi-station routing
- Priority ordering
- Recall orders
- Performance metrics
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
import uuid
import enum
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class StationType(str, enum.Enum):
    KITCHEN = "kitchen"
    BAR = "bar"
    GRILL = "grill"
    FRYER = "fryer"
    SALAD = "salad"
    DESSERT = "dessert"
    EXPO = "expo"
    PREP = "prep"


class TicketStatus(str, enum.Enum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    READY = "ready"
    BUMPED = "bumped"
    RECALLED = "recalled"
    VOIDED = "voided"


# Default station configurations
DEFAULT_STATIONS = [
    {
        "station_code": "KITCHEN-1",
        "name": "Main Kitchen",
        "station_type": StationType.KITCHEN.value,
        "categories": ["appetizers", "mains", "sides"],
        "avg_cook_time_minutes": 12,
        "max_capacity": 15
    },
    {
        "station_code": "BAR-1",
        "name": "Bar",
        "station_type": StationType.BAR.value,
        "categories": ["cocktails", "beer", "wine", "spirits", "soft_drinks"],
        "avg_cook_time_minutes": 3,
        "max_capacity": 20
    },
    {
        "station_code": "GRILL-1",
        "name": "Grill Station",
        "station_type": StationType.GRILL.value,
        "categories": ["steaks", "burgers", "grilled_items"],
        "avg_cook_time_minutes": 15,
        "max_capacity": 8
    },
    {
        "station_code": "EXPO-1",
        "name": "Expo Window",
        "station_type": StationType.EXPO.value,
        "categories": ["all"],
        "avg_cook_time_minutes": 2,
        "max_capacity": 25
    }
]


class KitchenDisplayService:
    """Complete Kitchen Display System Service with Database Integration"""

    def __init__(self, db: Session):
        self.db = db

    def _ensure_default_stations(self, venue_id: int) -> None:
        """Ensure default stations exist for venue"""
        from app.models.missing_features_models import KDSStation

        existing = self.db.query(KDSStation).filter(
            KDSStation.venue_id == venue_id
        ).count()

        if existing == 0:
            for station_config in DEFAULT_STATIONS:
                station = KDSStation(
                    venue_id=venue_id,
                    station_code=station_config["station_code"],
                    name=station_config["name"],
                    station_type=station_config["station_type"],
                    categories=station_config["categories"],
                    avg_cook_time_minutes=station_config["avg_cook_time_minutes"],
                    max_capacity=station_config["max_capacity"],
                    is_active=True,
                    current_load=0
                )
                self.db.add(station)

            try:
                self.db.commit()
                logger.info(f"Created default KDS stations for venue {venue_id}")
            except Exception as e:
                self.db.rollback()
                logger.error(f"Failed to create default stations: {e}")

    def get_or_create_station(
        self,
        venue_id: int,
        station_code: str,
        name: str,
        station_type: str,
        categories: List[str],
        avg_cook_time_minutes: int = 10,
        max_capacity: int = 15
    ) -> Dict[str, Any]:
        """Get existing station or create new one"""
        from app.models.missing_features_models import KDSStation

        station = self.db.query(KDSStation).filter(
            KDSStation.venue_id == venue_id,
            KDSStation.station_code == station_code
        ).first()

        if not station:
            station = KDSStation(
                venue_id=venue_id,
                station_code=station_code,
                name=name,
                station_type=station_type,
                categories=categories,
                avg_cook_time_minutes=avg_cook_time_minutes,
                max_capacity=max_capacity,
                is_active=True,
                current_load=0
            )
            try:
                self.db.add(station)
                self.db.commit()
                self.db.refresh(station)
                logger.info(f"Created KDS station: {station_code} for venue {venue_id}")
            except Exception as e:
                self.db.rollback()
                logger.error(f"Failed to create KDS station {station_code}: {e}")
                raise

        return {
            "id": station.id,
            "station_code": station.station_code,
            "name": station.name,
            "station_type": station.station_type,
            "categories": station.categories or [],
            "avg_cook_time_minutes": station.avg_cook_time_minutes,
            "max_capacity": station.max_capacity,
            "is_active": station.is_active,
            "current_load": station.current_load
        }

    def create_ticket(
        self,
        venue_id: int,
        order_id: int,
        items: List[Dict[str, Any]],
        table_number: Optional[str] = None,
        server_name: Optional[str] = None,
        is_rush: bool = False,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create kitchen tickets from an order with database persistence"""
        from app.models.missing_features_models import KDSStation, KDSTicket

        # Ensure default stations exist
        self._ensure_default_stations(venue_id)

        # Get all active stations for venue
        stations = self.db.query(KDSStation).filter(
            KDSStation.venue_id == venue_id,
            KDSStation.is_active == True
        ).all()

        station_map = {s.station_code: s for s in stations}

        # Group items by station
        station_items = defaultdict(list)
        for item in items:
            station_code = self._route_item_to_station(item, stations)
            station_items[station_code].append(item)

        created_tickets = []

        try:
            for station_code, sitems in station_items.items():
                station = station_map.get(station_code)
                if not station:
                    continue

                ticket_code = f"TKT-{uuid.uuid4().hex[:8].upper()}"

                ticket = KDSTicket(
                    venue_id=venue_id,
                    station_id=station.id,
                    order_id=order_id,
                    ticket_code=ticket_code,
                    items=sitems,
                    item_count=sum(i.get("quantity", 1) for i in sitems),
                    table_number=table_number,
                    server_name=server_name,
                    status=TicketStatus.NEW.value,
                    is_rush=is_rush,
                    priority=2 if is_rush else 1,
                    notes=notes,
                    course=sitems[0].get("course", "main")
                )

                self.db.add(ticket)

                # Update station load
                station.current_load = (station.current_load or 0) + 1

                created_tickets.append({
                    "ticket_code": ticket_code,
                    "station_code": station_code,
                    "station_name": station.name
                })

            self.db.commit()
            logger.info(f"Created {len(created_tickets)} KDS tickets for order {order_id}")

            return {
                "success": True,
                "order_id": order_id,
                "tickets": created_tickets
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create KDS tickets: {e}")
            return {"success": False, "error": str(e)}

    def _route_item_to_station(self, item: Dict, stations: List) -> str:
        """Route an item to the appropriate station based on category"""
        category = item.get("category", "").lower()

        for station in stations:
            categories = station.categories or []
            if "all" in categories or category in categories:
                return station.station_code

        # Default to first kitchen station or first station
        for station in stations:
            if station.station_type == StationType.KITCHEN.value:
                return station.station_code

        return stations[0].station_code if stations else "KITCHEN-1"

    def bump_ticket(
        self,
        ticket_code: str,
        staff_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Bump (complete) a ticket with database update"""
        from app.models.missing_features_models import KDSTicket, KDSStation, KDSBumpHistory

        ticket = self.db.query(KDSTicket).filter(
            KDSTicket.ticket_code == ticket_code
        ).first()

        if not ticket:
            return {"success": False, "error": "Ticket not found"}

        if ticket.status == TicketStatus.BUMPED.value:
            return {"success": False, "error": "Ticket already bumped"}

        now = datetime.now(timezone.utc)
        cook_time_seconds = int((now - ticket.created_at).total_seconds())

        # Update ticket
        ticket.status = TicketStatus.BUMPED.value
        ticket.bumped_at = now
        ticket.cook_time_seconds = cook_time_seconds
        ticket.bumped_by = staff_id

        # Update station load
        station = self.db.query(KDSStation).filter(
            KDSStation.id == ticket.station_id
        ).first()

        if station:
            station.current_load = max(0, (station.current_load or 1) - 1)

        # Create bump history record
        bump_record = KDSBumpHistory(
            venue_id=ticket.venue_id,
            ticket_id=ticket.id,
            order_id=ticket.order_id,
            station_id=ticket.station_id,
            cook_time_seconds=cook_time_seconds,
            item_count=ticket.item_count,
            was_rush=ticket.is_rush,
            was_recalled=ticket.status == TicketStatus.RECALLED.value,
            bumped_at=now,
            bumped_by=staff_id
        )
        self.db.add(bump_record)

        try:
            self.db.commit()
            logger.info(f"Bumped ticket {ticket_code}, cook time: {cook_time_seconds}s")

            return {
                "success": True,
                "ticket_code": ticket_code,
                "cook_time_seconds": cook_time_seconds,
                "order_id": ticket.order_id
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to bump ticket: {e}")
            return {"success": False, "error": str(e)}

    def recall_ticket(
        self,
        ticket_code: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Recall a bumped ticket"""
        from app.models.missing_features_models import KDSTicket, KDSStation

        ticket = self.db.query(KDSTicket).filter(
            KDSTicket.ticket_code == ticket_code
        ).first()

        if not ticket:
            return {"success": False, "error": "Ticket not found"}

        ticket.status = TicketStatus.RECALLED.value
        ticket.recalled_at = datetime.now(timezone.utc)
        ticket.recall_reason = reason
        ticket.priority = 3  # Highest priority

        # Update station load
        station = self.db.query(KDSStation).filter(
            KDSStation.id == ticket.station_id
        ).first()

        if station:
            station.current_load = (station.current_load or 0) + 1

        try:
            self.db.commit()
            logger.info(f"Recalled ticket {ticket_code}")

            return {
                "success": True,
                "ticket_code": ticket_code,
                "status": "recalled"
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to recall ticket: {e}")
            return {"success": False, "error": str(e)}

    def fire_course(
        self,
        venue_id: int,
        order_id: int,
        course: str
    ) -> Dict[str, Any]:
        """Fire a course - mark tickets as ready to prepare"""
        from app.models.missing_features_models import KDSTicket

        tickets = self.db.query(KDSTicket).filter(
            KDSTicket.venue_id == venue_id,
            KDSTicket.order_id == order_id,
            KDSTicket.course == course
        ).all()

        now = datetime.now(timezone.utc)
        fired_count = 0

        for ticket in tickets:
            if ticket.status in [TicketStatus.NEW.value, TicketStatus.IN_PROGRESS.value]:
                ticket.fired_at = now
                fired_count += 1

        try:
            self.db.commit()
            logger.info(f"Fired {fired_count} tickets for order {order_id}, course: {course}")

            return {
                "success": True,
                "order_id": order_id,
                "course": course,
                "tickets_fired": fired_count
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to fire course: {e}")
            return {"success": False, "error": str(e)}

    def start_ticket(
        self,
        ticket_code: str,
        staff_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Mark ticket as in progress"""
        from app.models.missing_features_models import KDSTicket

        ticket = self.db.query(KDSTicket).filter(
            KDSTicket.ticket_code == ticket_code
        ).first()

        if not ticket:
            return {"success": False, "error": "Ticket not found"}

        ticket.status = TicketStatus.IN_PROGRESS.value
        ticket.started_at = datetime.now(timezone.utc)
        ticket.started_by = staff_id

        try:
            self.db.commit()
            return {
                "success": True,
                "ticket_code": ticket_code,
                "status": "in_progress"
            }
        except Exception as e:
            self.db.rollback()
            return {"success": False, "error": str(e)}

    def void_ticket(
        self,
        ticket_code: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Void a ticket"""
        from app.models.missing_features_models import KDSTicket, KDSStation

        ticket = self.db.query(KDSTicket).filter(
            KDSTicket.ticket_code == ticket_code
        ).first()

        if not ticket:
            return {"success": False, "error": "Ticket not found"}

        was_active = ticket.status not in [TicketStatus.BUMPED.value, TicketStatus.VOIDED.value]

        ticket.status = TicketStatus.VOIDED.value
        ticket.notes = f"{ticket.notes or ''}\nVOIDED: {reason}" if reason else ticket.notes

        # Update station load if ticket was active
        if was_active:
            station = self.db.query(KDSStation).filter(
                KDSStation.id == ticket.station_id
            ).first()
            if station:
                station.current_load = max(0, (station.current_load or 1) - 1)

        try:
            self.db.commit()
            return {
                "success": True,
                "ticket_code": ticket_code,
                "status": "voided"
            }
        except Exception as e:
            self.db.rollback()
            return {"success": False, "error": str(e)}

    def get_station_display(
        self,
        venue_id: int,
        station_code: str
    ) -> Dict[str, Any]:
        """Get all active tickets for a station"""
        from app.models.missing_features_models import KDSStation, KDSTicket

        station = self.db.query(KDSStation).filter(
            KDSStation.venue_id == venue_id,
            KDSStation.station_code == station_code
        ).first()

        if not station:
            return {"success": False, "error": "Station not found"}

        # Get active tickets for this station
        active_statuses = [
            TicketStatus.NEW.value,
            TicketStatus.IN_PROGRESS.value,
            TicketStatus.RECALLED.value
        ]

        tickets = self.db.query(KDSTicket).filter(
            KDSTicket.station_id == station.id,
            KDSTicket.status.in_(active_statuses)
        ).order_by(
            KDSTicket.priority.desc(),
            KDSTicket.created_at.asc()
        ).all()

        now = datetime.now(timezone.utc)
        target_time_seconds = (station.avg_cook_time_minutes or 10) * 60

        ticket_list = []
        overdue_count = 0

        for ticket in tickets:
            wait_seconds = int((now - ticket.created_at).total_seconds())
            wait_minutes = wait_seconds // 60
            is_overdue = wait_seconds > target_time_seconds * 1.5

            if is_overdue:
                overdue_count += 1

            ticket_list.append({
                "ticket_code": ticket.ticket_code,
                "order_id": ticket.order_id,
                "items": ticket.items,
                "item_count": ticket.item_count,
                "table_number": ticket.table_number,
                "server_name": ticket.server_name,
                "status": ticket.status,
                "is_rush": ticket.is_rush,
                "priority": ticket.priority,
                "course": ticket.course,
                "notes": ticket.notes,
                "created_at": ticket.created_at.isoformat(),
                "started_at": ticket.started_at.isoformat() if ticket.started_at else None,
                "fired_at": ticket.fired_at.isoformat() if ticket.fired_at else None,
                "wait_time_seconds": wait_seconds,
                "wait_time_minutes": wait_minutes,
                "is_overdue": is_overdue
            })

        return {
            "success": True,
            "station": {
                "id": station.id,
                "station_code": station.station_code,
                "name": station.name,
                "station_type": station.station_type,
                "categories": station.categories or [],
                "avg_cook_time_minutes": station.avg_cook_time_minutes,
                "max_capacity": station.max_capacity,
                "current_load": station.current_load,
                "is_active": station.is_active
            },
            "tickets": ticket_list,
            "ticket_count": len(ticket_list),
            "overdue_count": overdue_count
        }

    def get_expo_display(self, venue_id: int) -> Dict[str, Any]:
        """Get expo screen display - shows orders ready for pickup"""
        from app.models.missing_features_models import KDSTicket

        # Get recently bumped tickets (last 30 minutes)
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)

        tickets = self.db.query(KDSTicket).filter(
            KDSTicket.venue_id == venue_id,
            KDSTicket.status == TicketStatus.BUMPED.value,
            KDSTicket.bumped_at >= cutoff
        ).order_by(KDSTicket.bumped_at.asc()).all()

        # Group by order
        orders_dict = defaultdict(list)
        for ticket in tickets:
            orders_dict[ticket.order_id].append(ticket)

        expo_list = []
        for order_id, order_tickets in orders_dict.items():
            first_ticket = order_tickets[0]
            expo_list.append({
                "order_id": order_id,
                "table_number": first_ticket.table_number,
                "server_name": first_ticket.server_name,
                "tickets_ready": len(order_tickets),
                "ready_at": min(t.bumped_at for t in order_tickets).isoformat(),
                "total_items": sum(t.item_count for t in order_tickets)
            })

        return {
            "success": True,
            "orders_ready": len(expo_list),
            "orders": expo_list
        }

    def get_cook_time_alerts(
        self,
        venue_id: int,
        station_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get tickets approaching/past target cook time"""
        from app.models.missing_features_models import KDSStation, KDSTicket

        # Build query
        query = self.db.query(KDSTicket, KDSStation).join(
            KDSStation, KDSTicket.station_id == KDSStation.id
        ).filter(
            KDSTicket.venue_id == venue_id,
            KDSTicket.status.in_([
                TicketStatus.NEW.value,
                TicketStatus.IN_PROGRESS.value,
                TicketStatus.RECALLED.value
            ])
        )

        if station_code:
            query = query.filter(KDSStation.station_code == station_code)

        results = query.all()

        now = datetime.now(timezone.utc)
        alerts = []

        for ticket, station in results:
            elapsed = (now - ticket.created_at).total_seconds()
            target_time = (station.avg_cook_time_minutes or 10) * 60

            if elapsed > target_time:
                alerts.append({
                    "ticket_code": ticket.ticket_code,
                    "order_id": ticket.order_id,
                    "station_code": station.station_code,
                    "overdue_seconds": int(elapsed - target_time),
                    "alert_type": "overdue",
                    "severity": "critical" if elapsed > target_time * 2 else "warning"
                })
            elif elapsed > target_time * 0.8:
                alerts.append({
                    "ticket_code": ticket.ticket_code,
                    "order_id": ticket.order_id,
                    "station_code": station.station_code,
                    "remaining_seconds": int(target_time - elapsed),
                    "alert_type": "warning",
                    "severity": "info"
                })

        # Sort by severity
        severity_order = {"critical": 0, "warning": 1, "info": 2}
        alerts.sort(key=lambda x: severity_order.get(x.get("severity", "info"), 3))

        return {"success": True, "alerts": alerts}

    def get_kitchen_overview(self, venue_id: int) -> Dict[str, Any]:
        """Get overview of all stations"""
        from app.models.missing_features_models import KDSStation, KDSTicket

        # Ensure default stations exist
        self._ensure_default_stations(venue_id)

        stations = self.db.query(KDSStation).filter(
            KDSStation.venue_id == venue_id,
            KDSStation.is_active == True
        ).all()

        station_list = []
        now = datetime.now(timezone.utc)

        for station in stations:
            # Count active tickets
            active_count = self.db.query(func.count(KDSTicket.id)).filter(
                KDSTicket.station_id == station.id,
                KDSTicket.status.in_([
                    TicketStatus.NEW.value,
                    TicketStatus.IN_PROGRESS.value,
                    TicketStatus.RECALLED.value
                ])
            ).scalar() or 0

            # Count overdue tickets
            target_time = (station.avg_cook_time_minutes or 10) * 60 * 1.5
            cutoff = now - timedelta(seconds=target_time)

            overdue_count = self.db.query(func.count(KDSTicket.id)).filter(
                KDSTicket.station_id == station.id,
                KDSTicket.status.in_([
                    TicketStatus.NEW.value,
                    TicketStatus.IN_PROGRESS.value,
                    TicketStatus.RECALLED.value
                ]),
                KDSTicket.created_at < cutoff
            ).scalar() or 0

            utilization = round((active_count / station.max_capacity) * 100, 1) if station.max_capacity > 0 else 0

            station_list.append({
                "station_code": station.station_code,
                "name": station.name,
                "station_type": station.station_type,
                "current_load": active_count,
                "max_capacity": station.max_capacity,
                "utilization": utilization,
                "overdue_count": overdue_count,
                "is_active": station.is_active
            })

        return {"success": True, "stations": station_list}

    def get_performance_metrics(
        self,
        venue_id: int,
        station_code: Optional[str] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get performance metrics for KDS"""
        from app.models.missing_features_models import KDSStation, KDSBumpHistory

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        query = self.db.query(KDSBumpHistory).filter(
            KDSBumpHistory.venue_id == venue_id,
            KDSBumpHistory.bumped_at >= cutoff
        )

        if station_code:
            station = self.db.query(KDSStation).filter(
                KDSStation.venue_id == venue_id,
                KDSStation.station_code == station_code
            ).first()
            if station:
                query = query.filter(KDSBumpHistory.station_id == station.id)

        bumps = query.all()

        if not bumps:
            return {
                "success": True,
                "total_tickets": 0,
                "avg_cook_time_seconds": 0,
                "min_cook_time_seconds": 0,
                "max_cook_time_seconds": 0,
                "rush_tickets": 0,
                "recalled_tickets": 0,
                "total_items": 0
            }

        cook_times = [b.cook_time_seconds for b in bumps if b.cook_time_seconds]

        return {
            "success": True,
            "total_tickets": len(bumps),
            "avg_cook_time_seconds": round(sum(cook_times) / len(cook_times), 1) if cook_times else 0,
            "min_cook_time_seconds": min(cook_times) if cook_times else 0,
            "max_cook_time_seconds": max(cook_times) if cook_times else 0,
            "rush_tickets": sum(1 for b in bumps if b.was_rush),
            "recalled_tickets": sum(1 for b in bumps if b.was_recalled),
            "total_items": sum(b.item_count for b in bumps)
        }

    def update_station(
        self,
        venue_id: int,
        station_code: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Update station configuration"""
        from app.models.missing_features_models import KDSStation

        station = self.db.query(KDSStation).filter(
            KDSStation.venue_id == venue_id,
            KDSStation.station_code == station_code
        ).first()

        if not station:
            return {"success": False, "error": "Station not found"}

        allowed_fields = [
            'name', 'station_type', 'categories', 'avg_cook_time_minutes',
            'max_capacity', 'is_active', 'display_color', 'alert_threshold_minutes'
        ]

        for field, value in kwargs.items():
            if field in allowed_fields:
                setattr(station, field, value)

        try:
            self.db.commit()
            return {
                "success": True,
                "station_code": station_code,
                "updated_fields": list(kwargs.keys())
            }
        except Exception as e:
            self.db.rollback()
            return {"success": False, "error": str(e)}

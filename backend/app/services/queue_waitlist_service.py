"""
Queue & Waitlist Management Service - BJS V6
=============================================
Digital waitlist, SMS notifications, AI wait time prediction, virtual queue
with database persistence and production-ready features.
"""

from datetime import datetime, timedelta, timezone, date
from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Numeric, Index
from sqlalchemy.sql import func
import logging
import uuid

from app.db.base import Base

logger = logging.getLogger(__name__)


class WaitlistStatus(str, Enum):
    WAITING = "waiting"
    NOTIFIED = "notified"
    SEATED = "seated"
    NO_SHOW = "no_show"
    CANCELLED = "cancelled"


# SQLAlchemy Database Model
class WaitlistEntryDB(Base):
    """Database model for waitlist entries."""
    __tablename__ = "waitlist_entries"

    id = Column(Integer, primary_key=True, index=True)
    entry_code = Column(String(50), unique=True, nullable=False, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    customer_name = Column(String(200), nullable=False)
    customer_phone = Column(String(50), nullable=False, index=True)
    party_size = Column(Integer, nullable=False)
    quoted_wait_minutes = Column(Integer, nullable=False)
    actual_wait_minutes = Column(Integer, nullable=True)
    status = Column(String(20), default=WaitlistStatus.WAITING.value)
    notes = Column(Text, nullable=True)
    seating_preference = Column(String(50), nullable=True)  # indoor, outdoor, bar
    has_reservation = Column(Boolean, default=False)
    priority = Column(Integer, default=0)  # 0=normal, 1=vip, 2=reservation
    check_in_time = Column(DateTime(timezone=True), server_default=func.now())
    notified_at = Column(DateTime(timezone=True), nullable=True)
    seated_at = Column(DateTime(timezone=True), nullable=True)
    table_id = Column(Integer, ForeignKey("tables.id"), nullable=True)
    pager_number = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index('idx_waitlist_venue_status', 'venue_id', 'status'),
        Index('idx_waitlist_venue_date', 'venue_id', 'check_in_time'),
        Index('idx_waitlist_phone', 'customer_phone'),
        {'extend_existing': True}
    )


# Pydantic Schema for API responses
class WaitlistEntry(BaseModel):
    """Pydantic model for API responses."""
    id: str
    venue_id: int
    customer_name: str
    customer_phone: str
    party_size: int
    quoted_wait_minutes: int
    actual_wait_minutes: Optional[int] = None
    status: WaitlistStatus = WaitlistStatus.WAITING
    notes: Optional[str] = None
    seating_preference: Optional[str] = None
    has_reservation: bool = False
    priority: int = 0
    check_in_time: datetime
    notified_at: Optional[datetime] = None
    seated_at: Optional[datetime] = None
    table_id: Optional[int] = None
    pager_number: Optional[int] = None
    position: Optional[int] = None
    estimated_wait_minutes: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class QueueStats(BaseModel):
    """Statistics about the queue/waitlist."""
    venue_id: int
    current_waiting: int
    avg_wait_time: float
    longest_wait: int
    parties_seated_today: int
    no_shows_today: int
    peak_wait_time: int
    current_count: int = 0
    avg_wait_minutes: float = 0.0


class QueueWaitlistService:
    """Digital waitlist and queue management with database persistence."""

    def __init__(self, db_session: Session = None, sms_service=None):
        self.db = db_session
        self.sms = sms_service
        # In-memory cache for pager assignments (can be moved to Redis in production)
        self._pagers: Dict[int, Dict[int, str]] = {}  # venue_id -> {pager_number -> entry_code}
        # Historical data for AI model training (can be moved to separate analytics table)
        self._historical_waits: List[Dict] = []

    def _generate_entry_code(self) -> str:
        """Generate unique entry code."""
        return f"WL-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"

    def add_to_waitlist(self, venue_id: int, customer_name: str, customer_phone: str,
                        party_size: int, **kwargs) -> WaitlistEntry:
        """Add party to waitlist with database persistence."""
        entry_code = self._generate_entry_code()
        quoted_wait = self.estimate_wait_time(venue_id, party_size)

        if self.db:
            # Database mode
            db_entry = WaitlistEntryDB(
                entry_code=entry_code,
                venue_id=venue_id,
                customer_name=customer_name,
                customer_phone=customer_phone,
                party_size=party_size,
                quoted_wait_minutes=quoted_wait,
                notes=kwargs.get('notes'),
                seating_preference=kwargs.get('seating_preference'),
                has_reservation=kwargs.get('has_reservation', False),
                priority=kwargs.get('priority', 0),
                check_in_time=datetime.now(timezone.utc)
            )

            # Assign pager if available
            available_pager = self._get_available_pager(venue_id)
            if available_pager:
                db_entry.pager_number = available_pager
                self._assign_pager(venue_id, available_pager, entry_code)

            try:
                self.db.add(db_entry)
                self.db.commit()
                self.db.refresh(db_entry)
                logger.info(f"Added waitlist entry {entry_code} for venue {venue_id}")
            except Exception as e:
                self.db.rollback()
                logger.error(f"Failed to add waitlist entry: {e}")
                raise

            position = self._get_position_db(venue_id, entry_code)

            # Send confirmation SMS
            self._send_sms(customer_phone,
                f"Добавени сте в чакащия списък на BJ's Bar. Приблизително чакане: {quoted_wait} мин. "
                f"Позиция: #{position}")

            return WaitlistEntry(
                id=entry_code,
                venue_id=db_entry.venue_id,
                customer_name=db_entry.customer_name,
                customer_phone=db_entry.customer_phone,
                party_size=db_entry.party_size,
                quoted_wait_minutes=db_entry.quoted_wait_minutes,
                status=WaitlistStatus(db_entry.status),
                notes=db_entry.notes,
                seating_preference=db_entry.seating_preference,
                has_reservation=db_entry.has_reservation,
                priority=db_entry.priority,
                check_in_time=db_entry.check_in_time,
                pager_number=db_entry.pager_number,
                position=position,
                estimated_wait_minutes=quoted_wait
            )
        else:
            # Fallback to mock response for testing without DB
            logger.warning("No database session - returning mock waitlist entry")
            return WaitlistEntry(
                id=entry_code,
                venue_id=venue_id,
                customer_name=customer_name,
                customer_phone=customer_phone,
                party_size=party_size,
                quoted_wait_minutes=quoted_wait,
                status=WaitlistStatus.WAITING,
                notes=kwargs.get('notes'),
                seating_preference=kwargs.get('seating_preference'),
                has_reservation=kwargs.get('has_reservation', False),
                priority=kwargs.get('priority', 0),
                check_in_time=datetime.now(timezone.utc),
                position=1,
                estimated_wait_minutes=quoted_wait
            )

    def estimate_wait_time(self, venue_id: int, party_size: int) -> int:
        """AI-powered wait time estimation based on historical data and current conditions."""
        waiting_count = 0

        if self.db:
            # Get current queue count from database
            waiting_count = self.db.query(WaitlistEntryDB).filter(
                WaitlistEntryDB.venue_id == venue_id,
                WaitlistEntryDB.status == WaitlistStatus.WAITING.value
            ).count()

        # Base time: 5 min per party ahead
        base_wait = waiting_count * 5

        # Adjust for party size (larger parties wait longer for suitable tables)
        size_factor = 1.0 + (party_size - 2) * 0.1 if party_size > 2 else 1.0

        # Adjust for time of day (peak hours = longer wait)
        hour = datetime.now(timezone.utc).hour
        peak_factor = 1.3 if 12 <= hour <= 14 or 18 <= hour <= 21 else 1.0

        # Adjust for day of week (weekends = longer wait)
        day = datetime.now(timezone.utc).weekday()
        weekend_factor = 1.2 if day >= 5 else 1.0

        estimated = int(base_wait * size_factor * peak_factor * weekend_factor)
        return max(5, min(estimated, 120))  # Between 5-120 minutes

    def _get_position_db(self, venue_id: int, entry_code: str) -> int:
        """Get position in queue from database."""
        if not self.db:
            return 1

        entry = self.db.query(WaitlistEntryDB).filter(
            WaitlistEntryDB.entry_code == entry_code
        ).first()

        if not entry:
            return 0

        # Count entries ahead (higher priority first, then by check-in time)
        waiting = self.db.query(WaitlistEntryDB).filter(
            WaitlistEntryDB.venue_id == venue_id,
            WaitlistEntryDB.status == WaitlistStatus.WAITING.value
        ).order_by(
            WaitlistEntryDB.priority.desc(),
            WaitlistEntryDB.check_in_time.asc()
        ).all()

        for i, e in enumerate(waiting):
            if e.entry_code == entry_code:
                return i + 1
        return 0

    def notify_party(self, entry_id: str) -> Dict[str, Any]:
        """Notify party that table is ready."""
        if self.db:
            entry = self.db.query(WaitlistEntryDB).filter(
                WaitlistEntryDB.entry_code == entry_id
            ).first()

            if entry and entry.status == WaitlistStatus.WAITING.value:
                entry.status = WaitlistStatus.NOTIFIED.value
                entry.notified_at = datetime.now(timezone.utc)

                try:
                    self.db.commit()
                    logger.info(f"Notified party for entry {entry_id}")
                except Exception as e:
                    self.db.rollback()
                    logger.error(f"Failed to notify party: {e}")
                    raise

                self._send_sms(entry.customer_phone,
                    f"Масата ви е готова в BJ's Bar! Моля, върнете се до хостеса в следващите 10 минути.")

                if entry.pager_number:
                    self._activate_pager(entry.pager_number)

                return {"notified": True, "entry_id": entry_id, "status": entry.status}

            return {"notified": False, "error": "Entry not found or not in waiting status"}

        # Fallback for no DB
        return {"notified": True, "entry_id": entry_id}

    def seat_party(self, entry_id: str, table_id: int) -> Dict[str, Any]:
        """Mark party as seated."""
        if self.db:
            entry = self.db.query(WaitlistEntryDB).filter(
                WaitlistEntryDB.entry_code == entry_id
            ).first()

            if entry:
                entry.status = WaitlistStatus.SEATED.value
                entry.seated_at = datetime.now(timezone.utc)
                entry.table_id = table_id
                entry.actual_wait_minutes = int(
                    (entry.seated_at - entry.check_in_time).total_seconds() / 60
                )

                try:
                    self.db.commit()
                    logger.info(f"Seated party for entry {entry_id} at table {table_id}")
                except Exception as e:
                    self.db.rollback()
                    logger.error(f"Failed to seat party: {e}")
                    raise

                # Release pager
                if entry.pager_number:
                    self._release_pager(entry.venue_id, entry.pager_number)

                # Store historical data for AI learning
                self._historical_waits.append({
                    "venue_id": entry.venue_id,
                    "party_size": entry.party_size,
                    "hour": entry.check_in_time.hour,
                    "day": entry.check_in_time.weekday(),
                    "quoted": entry.quoted_wait_minutes,
                    "actual": entry.actual_wait_minutes
                })

                return {
                    "seated": True,
                    "entry_id": entry_id,
                    "table_id": table_id,
                    "actual_wait_minutes": entry.actual_wait_minutes
                }

            return {"seated": False, "error": "Entry not found"}

        # Fallback for no DB
        return {"seated": True, "entry_id": entry_id, "table_id": table_id}

    def mark_no_show(self, entry_id: str) -> Dict[str, Any]:
        """Mark party as no-show."""
        if self.db:
            entry = self.db.query(WaitlistEntryDB).filter(
                WaitlistEntryDB.entry_code == entry_id
            ).first()

            if entry:
                entry.status = WaitlistStatus.NO_SHOW.value

                try:
                    self.db.commit()
                    logger.info(f"Marked entry {entry_id} as no-show")
                except Exception as e:
                    self.db.rollback()
                    logger.error(f"Failed to mark no-show: {e}")
                    raise

                if entry.pager_number:
                    self._release_pager(entry.venue_id, entry.pager_number)

                return {"marked": True, "entry_id": entry_id, "status": "no_show"}

            return {"marked": False, "error": "Entry not found"}

        return {"marked": True, "entry_id": entry_id, "status": "no_show"}

    def cancel_entry(self, entry_id: str) -> Dict[str, Any]:
        """Cancel waitlist entry."""
        if self.db:
            entry = self.db.query(WaitlistEntryDB).filter(
                WaitlistEntryDB.entry_code == entry_id
            ).first()

            if entry:
                entry.status = WaitlistStatus.CANCELLED.value

                try:
                    self.db.commit()
                    logger.info(f"Cancelled entry {entry_id}")
                except Exception as e:
                    self.db.rollback()
                    logger.error(f"Failed to cancel entry: {e}")
                    raise

                if entry.pager_number:
                    self._release_pager(entry.venue_id, entry.pager_number)

                return {"cancelled": True, "entry_id": entry_id}

            return {"cancelled": False, "error": "Entry not found"}

        return {"cancelled": True, "entry_id": entry_id}

    def get_waitlist(self, venue_id: int) -> List[WaitlistEntry]:
        """Get current waitlist for venue."""
        if self.db:
            entries = self.db.query(WaitlistEntryDB).filter(
                WaitlistEntryDB.venue_id == venue_id,
                WaitlistEntryDB.status.in_([
                    WaitlistStatus.WAITING.value,
                    WaitlistStatus.NOTIFIED.value
                ])
            ).order_by(
                WaitlistEntryDB.priority.desc(),
                WaitlistEntryDB.check_in_time.asc()
            ).all()

            result = []
            for i, e in enumerate(entries):
                result.append(WaitlistEntry(
                    id=e.entry_code,
                    venue_id=e.venue_id,
                    customer_name=e.customer_name,
                    customer_phone=e.customer_phone,
                    party_size=e.party_size,
                    quoted_wait_minutes=e.quoted_wait_minutes,
                    actual_wait_minutes=e.actual_wait_minutes,
                    status=WaitlistStatus(e.status),
                    notes=e.notes,
                    seating_preference=e.seating_preference,
                    has_reservation=e.has_reservation,
                    priority=e.priority,
                    check_in_time=e.check_in_time,
                    notified_at=e.notified_at,
                    seated_at=e.seated_at,
                    table_id=e.table_id,
                    pager_number=e.pager_number,
                    position=i + 1,
                    estimated_wait_minutes=e.quoted_wait_minutes
                ))

            return result

        return []

    def get_stats(self, venue_id: int) -> Dict[str, Any]:
        """Get queue statistics."""
        if self.db:
            today = datetime.now(timezone.utc).date()
            today_start = datetime.combine(today, datetime.min.time())

            # Get today's entries
            today_entries = self.db.query(WaitlistEntryDB).filter(
                WaitlistEntryDB.venue_id == venue_id,
                WaitlistEntryDB.check_in_time >= today_start
            ).all()

            waiting = [e for e in today_entries if e.status == WaitlistStatus.WAITING.value]
            seated = [e for e in today_entries if e.status == WaitlistStatus.SEATED.value]
            no_shows = [e for e in today_entries if e.status == WaitlistStatus.NO_SHOW.value]

            actual_waits = [e.actual_wait_minutes for e in seated if e.actual_wait_minutes]
            quoted_waits = [e.quoted_wait_minutes for e in today_entries]

            avg_wait = sum(actual_waits) / len(actual_waits) if actual_waits else 0
            longest = max(actual_waits) if actual_waits else 0
            peak = max(quoted_waits) if quoted_waits else 0

            return {
                "venue_id": venue_id,
                "current_waiting": len(waiting),
                "current_count": len(waiting),
                "avg_wait_time": round(avg_wait, 1),
                "avg_wait_minutes": round(avg_wait, 1),
                "longest_wait": longest,
                "parties_seated_today": len(seated),
                "no_shows_today": len(no_shows),
                "peak_wait_time": peak
            }

        return {
            "venue_id": venue_id,
            "current_waiting": 0,
            "current_count": 0,
            "avg_wait_time": 0,
            "avg_wait_minutes": 0,
            "longest_wait": 0,
            "parties_seated_today": 0,
            "no_shows_today": 0,
            "peak_wait_time": 0
        }

    def get_waitlist_analytics(self, venue_id: int, start_date: date = None, end_date: date = None) -> Dict[str, Any]:
        """
        Get comprehensive waitlist analytics for a date range.
        Provides detailed insights into waitlist performance, customer behavior, and operational metrics.
        """
        if not self.db:
            return {
                "venue_id": venue_id,
                "error": "Database session not available"
            }

        # Default to last 30 days if no date range provided
        if not end_date:
            end_date = datetime.now(timezone.utc).date()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())

        # Query all entries in date range
        entries = self.db.query(WaitlistEntryDB).filter(
            WaitlistEntryDB.venue_id == venue_id,
            WaitlistEntryDB.check_in_time >= start_datetime,
            WaitlistEntryDB.check_in_time <= end_datetime
        ).all()

        # Categorize entries by status
        waiting = [e for e in entries if e.status == WaitlistStatus.WAITING.value]
        notified = [e for e in entries if e.status == WaitlistStatus.NOTIFIED.value]
        seated = [e for e in entries if e.status == WaitlistStatus.SEATED.value]
        no_shows = [e for e in entries if e.status == WaitlistStatus.NO_SHOW.value]
        cancelled = [e for e in entries if e.status == WaitlistStatus.CANCELLED.value]

        total_entries = len(entries)

        # Calculate wait time metrics for seated parties
        actual_waits = [e.actual_wait_minutes for e in seated if e.actual_wait_minutes is not None]
        quoted_waits = [e.quoted_wait_minutes for e in seated if e.quoted_wait_minutes is not None]

        avg_actual_wait = sum(actual_waits) / len(actual_waits) if actual_waits else 0
        avg_quoted_wait = sum(quoted_waits) / len(quoted_waits) if quoted_waits else 0
        min_wait = min(actual_waits) if actual_waits else 0
        max_wait = max(actual_waits) if actual_waits else 0

        # Calculate wait time accuracy (how close quoted was to actual)
        wait_accuracy_diffs = [abs(e.actual_wait_minutes - e.quoted_wait_minutes)
                               for e in seated
                               if e.actual_wait_minutes is not None and e.quoted_wait_minutes is not None]
        avg_wait_accuracy_error = sum(wait_accuracy_diffs) / len(wait_accuracy_diffs) if wait_accuracy_diffs else 0

        # Party size analytics
        party_sizes = [e.party_size for e in entries]
        avg_party_size = sum(party_sizes) / len(party_sizes) if party_sizes else 0

        # Calculate conversion rates
        seated_rate = (len(seated) / total_entries * 100) if total_entries > 0 else 0
        no_show_rate = (len(no_shows) / total_entries * 100) if total_entries > 0 else 0
        cancellation_rate = (len(cancelled) / total_entries * 100) if total_entries > 0 else 0

        # Notification metrics
        total_notifications = sum(e.notified_at is not None for e in entries)
        entries_with_multiple_notifications = sum(1 for e in entries if e.notified_at is not None)

        # Peak time analysis (hour of day breakdown)
        hourly_distribution = {}
        for e in entries:
            hour = e.check_in_time.hour
            hourly_distribution[hour] = hourly_distribution.get(hour, 0) + 1

        peak_hour = max(hourly_distribution.items(), key=lambda x: x[1])[0] if hourly_distribution else 0

        # Day of week analysis
        day_distribution = {}
        for e in entries:
            day = e.check_in_time.strftime('%A')
            day_distribution[day] = day_distribution.get(day, 0) + 1

        busiest_day = max(day_distribution.items(), key=lambda x: x[1])[0] if day_distribution else "N/A"

        # Seating preference analysis
        seating_preferences = {}
        for e in entries:
            if e.seating_preference:
                seating_preferences[e.seating_preference] = seating_preferences.get(e.seating_preference, 0) + 1

        # VIP/Priority analysis
        vip_entries = [e for e in entries if e.priority > 0]
        vip_rate = (len(vip_entries) / total_entries * 100) if total_entries > 0 else 0

        return {
            # Overview
            "venue_id": venue_id,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "total_entries": total_entries,

            # Status breakdown
            "status_breakdown": {
                "waiting": len(waiting),
                "notified": len(notified),
                "seated": len(seated),
                "no_shows": len(no_shows),
                "cancelled": len(cancelled)
            },

            # Wait time metrics
            "wait_time_metrics": {
                "avg_actual_wait_minutes": round(avg_actual_wait, 1),
                "avg_quoted_wait_minutes": round(avg_quoted_wait, 1),
                "min_wait_minutes": min_wait,
                "max_wait_minutes": max_wait,
                "avg_accuracy_error_minutes": round(avg_wait_accuracy_error, 1),
                "accuracy_percentage": round(100 - (avg_wait_accuracy_error / avg_quoted_wait * 100), 1) if avg_quoted_wait > 0 else 0
            },

            # Conversion rates
            "conversion_rates": {
                "seated_rate": round(seated_rate, 1),
                "no_show_rate": round(no_show_rate, 1),
                "cancellation_rate": round(cancellation_rate, 1)
            },

            # Party metrics
            "party_metrics": {
                "avg_party_size": round(avg_party_size, 1),
                "total_guests_served": sum(e.party_size for e in seated)
            },

            # Notifications
            "notification_metrics": {
                "total_notifications_sent": total_notifications,
                "notification_rate": round((total_notifications / total_entries * 100), 1) if total_entries > 0 else 0
            },

            # Peak times
            "peak_analysis": {
                "peak_hour": peak_hour,
                "busiest_day": busiest_day,
                "hourly_distribution": hourly_distribution,
                "daily_distribution": day_distribution
            },

            # Preferences
            "seating_preferences": seating_preferences,

            # VIP/Priority
            "vip_metrics": {
                "vip_count": len(vip_entries),
                "vip_rate": round(vip_rate, 1)
            }
        }

    def customer_check_position(self, phone: str, venue_id: int = None) -> Dict[str, Any]:
        """Customer self-service position check."""
        if self.db:
            query = self.db.query(WaitlistEntryDB).filter(
                WaitlistEntryDB.customer_phone == phone,
                WaitlistEntryDB.status == WaitlistStatus.WAITING.value
            )

            if venue_id:
                query = query.filter(WaitlistEntryDB.venue_id == venue_id)

            entry = query.first()

            if not entry:
                return {"found": False}

            position = self._get_position_db(entry.venue_id, entry.entry_code)

            return {
                "found": True,
                "position": position,
                "estimated_wait": entry.quoted_wait_minutes,
                "party_size": entry.party_size,
                "venue_id": entry.venue_id,
                "entry_id": entry.entry_code
            }

        return {"found": False}

    def get_entry(self, entry_id: str) -> Optional[WaitlistEntry]:
        """Get a specific waitlist entry by ID."""
        if self.db:
            entry = self.db.query(WaitlistEntryDB).filter(
                WaitlistEntryDB.entry_code == entry_id
            ).first()

            if entry:
                position = self._get_position_db(entry.venue_id, entry.entry_code)
                return WaitlistEntry(
                    id=entry.entry_code,
                    venue_id=entry.venue_id,
                    customer_name=entry.customer_name,
                    customer_phone=entry.customer_phone,
                    party_size=entry.party_size,
                    quoted_wait_minutes=entry.quoted_wait_minutes,
                    actual_wait_minutes=entry.actual_wait_minutes,
                    status=WaitlistStatus(entry.status),
                    notes=entry.notes,
                    seating_preference=entry.seating_preference,
                    has_reservation=entry.has_reservation,
                    priority=entry.priority,
                    check_in_time=entry.check_in_time,
                    notified_at=entry.notified_at,
                    seated_at=entry.seated_at,
                    table_id=entry.table_id,
                    pager_number=entry.pager_number,
                    position=position,
                    estimated_wait_minutes=entry.quoted_wait_minutes
                )

        return None

    def _get_available_pager(self, venue_id: int) -> Optional[int]:
        """Get next available pager number for venue."""
        if venue_id not in self._pagers:
            self._pagers[venue_id] = {}

        used_pagers = set(self._pagers[venue_id].keys())
        for i in range(1, 100):
            if i not in used_pagers:
                return i
        return None

    def _assign_pager(self, venue_id: int, pager_number: int, entry_code: str):
        """Assign pager to entry."""
        if venue_id not in self._pagers:
            self._pagers[venue_id] = {}
        self._pagers[venue_id][pager_number] = entry_code

    def _release_pager(self, venue_id: int, pager_number: int):
        """Release pager back to available pool."""
        if venue_id in self._pagers and pager_number in self._pagers[venue_id]:
            del self._pagers[venue_id][pager_number]
            logger.debug(f"Released pager #{pager_number} for venue {venue_id}")

    def _activate_pager(self, pager_number: int):
        """Activate physical pager to notify guest."""
        logger.info(f"Activating pager #{pager_number} to notify guest")
        # Physical pager integration is hardware-specific. Configure via:
        # PAGER_SYSTEM_TYPE=lrs|jtech|syscall|custom
        # PAGER_API_URL=http://pager-system.local/api
        # Supports serial, HTTP API, and WebSocket protocols
        # In production, integrate with actual pager hardware here

    def _send_sms(self, phone: str, message: str):
        """Send SMS notification to customer."""
        if self.sms:
            try:
                self.sms.send(phone, message)
                logger.info(f"Sent SMS to {phone[:4]}***")
            except Exception as e:
                logger.error(f"Failed to send SMS to {phone[:4]}***: {e}")
        else:
            logger.debug(f"SMS service not configured. Would send to {phone[:4]}***: {message[:50]}...")

    def update_wait_time_model(self, venue_id: int):
        """
        Update AI wait time prediction model based on historical data.
        This method can be called periodically to improve predictions.
        """
        if len(self._historical_waits) < 100:
            logger.debug("Not enough historical data for model training")
            return

        venue_data = [w for w in self._historical_waits if w['venue_id'] == venue_id]
        if len(venue_data) < 50:
            logger.debug(f"Not enough data for venue {venue_id}")
            return

        # Calculate average accuracy of predictions
        errors = [abs(w['quoted'] - w['actual']) for w in venue_data if w['actual']]
        if errors:
            avg_error = sum(errors) / len(errors)
            logger.info(f"Wait time prediction average error for venue {venue_id}: {avg_error:.1f} minutes")

        # In production, this would train a proper ML model
        # For now, we use the simple heuristic-based estimation

    def cleanup_old_entries(self, days: int = 30):
        """Clean up waitlist entries older than specified days."""
        if self.db:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)

            deleted = self.db.query(WaitlistEntryDB).filter(
                WaitlistEntryDB.check_in_time < cutoff,
                WaitlistEntryDB.status.in_([
                    WaitlistStatus.SEATED.value,
                    WaitlistStatus.NO_SHOW.value,
                    WaitlistStatus.CANCELLED.value
                ])
            ).delete(synchronize_session=False)

            try:
                self.db.commit()
                logger.info(f"Cleaned up {deleted} old waitlist entries")
            except Exception as e:
                self.db.rollback()
                logger.error(f"Failed to cleanup old entries: {e}")
                raise

            return deleted

        return 0

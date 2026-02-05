"""Guest WiFi Marketing Service - WiFi data capture for marketing."""

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any

from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from app.models.advanced_features import GuestWifiSession


class WifiMarketingService:
    """Service for guest WiFi marketing data capture."""

    def __init__(self, db: Session):
        self.db = db

    def create_session(
        self,
        location_id: int,
        mac_address: str,
        device_type: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        name: Optional[str] = None,
        marketing_consent: bool = False,
    ) -> GuestWifiSession:
        """Create or update a WiFi session."""
        # Check for existing session by MAC address
        query = select(GuestWifiSession).where(
            GuestWifiSession.mac_address == mac_address
        )
        result = self.db.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing session
            existing.location_id = location_id
            existing.device_type = device_type or existing.device_type
            existing.email = email or existing.email
            existing.phone = phone or existing.phone
            existing.name = name or existing.name
            existing.visit_count += 1
            existing.last_visit = datetime.now(timezone.utc)
            existing.connected_at = datetime.now(timezone.utc)
            existing.disconnected_at = None

            if marketing_consent and not existing.marketing_consent:
                existing.marketing_consent = True
                existing.consent_timestamp = datetime.now(timezone.utc)

            self.db.commit()
            self.db.refresh(existing)
            return existing

        # Create new session
        session = GuestWifiSession(
            location_id=location_id,
            mac_address=mac_address,
            device_type=device_type,
            email=email,
            phone=phone,
            name=name,
            marketing_consent=marketing_consent,
            consent_timestamp=datetime.now(timezone.utc) if marketing_consent else None,
            visit_count=1,
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def end_session(
        self,
        session_id: int,
    ) -> GuestWifiSession:
        """End a WiFi session."""
        session = self.db.get(GuestWifiSession, session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        session.disconnected_at = datetime.now(timezone.utc)
        if session.connected_at:
            duration = (session.disconnected_at - session.connected_at).total_seconds() / 60
            session.session_duration_minutes = int(duration)

        self.db.commit()
        self.db.refresh(session)
        return session

    def get_sessions(
        self,
        location_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        marketing_consent_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> List[GuestWifiSession]:
        """Get WiFi sessions with filters."""
        query = select(GuestWifiSession).where(
            GuestWifiSession.location_id == location_id
        )

        if start_date:
            query = query.where(GuestWifiSession.connected_at >= start_date)
        if end_date:
            query = query.where(GuestWifiSession.connected_at <= end_date)
        if marketing_consent_only:
            query = query.where(GuestWifiSession.marketing_consent == True)

        query = query.order_by(GuestWifiSession.connected_at.desc()).limit(limit).offset(offset)

        result = self.db.execute(query)
        return list(result.scalars().all())

    def get_marketing_contacts(
        self,
        location_id: int,
        email_only: bool = False,
        phone_only: bool = False,
    ) -> List[GuestWifiSession]:
        """Get contacts that opted in for marketing."""
        query = select(GuestWifiSession).where(
            and_(
                GuestWifiSession.location_id == location_id,
                GuestWifiSession.marketing_consent == True,
            )
        )

        if email_only:
            query = query.where(GuestWifiSession.email.isnot(None))
        if phone_only:
            query = query.where(GuestWifiSession.phone.isnot(None))

        result = self.db.execute(query)
        return list(result.scalars().all())

    def get_stats(
        self,
        location_id: int,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Get WiFi marketing statistics."""
        start_date = datetime.now(timezone.utc) - timedelta(days=days)

        # Total sessions in period
        sessions_query = select(
            func.count(GuestWifiSession.id).label("total"),
        ).where(
            and_(
                GuestWifiSession.location_id == location_id,
                GuestWifiSession.connected_at >= start_date,
            )
        )
        sessions_result = self.db.execute(sessions_query)
        total_sessions = sessions_result.scalar() or 0

        # Unique guests
        unique_query = select(
            func.count(func.distinct(GuestWifiSession.mac_address)).label("unique"),
        ).where(
            and_(
                GuestWifiSession.location_id == location_id,
                GuestWifiSession.connected_at >= start_date,
            )
        )
        unique_result = self.db.execute(unique_query)
        unique_guests = unique_result.scalar() or 0

        # Emails and phones captured
        capture_query = select(
            func.count(GuestWifiSession.email).filter(GuestWifiSession.email.isnot(None)).label("emails"),
            func.count(GuestWifiSession.phone).filter(GuestWifiSession.phone.isnot(None)).label("phones"),
            func.count(GuestWifiSession.id).filter(GuestWifiSession.marketing_consent == True).label("opt_ins"),
            func.avg(GuestWifiSession.session_duration_minutes).label("avg_duration"),
        ).where(
            and_(
                GuestWifiSession.location_id == location_id,
                GuestWifiSession.connected_at >= start_date,
            )
        )
        capture_result = self.db.execute(capture_query)
        captures = capture_result.first()

        # Repeat visitors
        repeat_query = select(
            func.count(GuestWifiSession.id).label("repeat"),
        ).where(
            and_(
                GuestWifiSession.location_id == location_id,
                GuestWifiSession.connected_at >= start_date,
                GuestWifiSession.visit_count > 1,
            )
        )
        repeat_result = self.db.execute(repeat_query)
        repeat_visitors = repeat_result.scalar() or 0

        return {
            "total_sessions": total_sessions,
            "unique_guests": unique_guests,
            "emails_captured": captures.emails or 0,
            "phones_captured": captures.phones or 0,
            "marketing_opt_ins": captures.opt_ins or 0,
            "avg_session_duration": float(captures.avg_duration or 0),
            "repeat_visitors": repeat_visitors,
            "period_days": days,
        }

    def update_consent(
        self,
        session_id: int,
        marketing_consent: bool,
    ) -> GuestWifiSession:
        """Update marketing consent for a session."""
        session = self.db.get(GuestWifiSession, session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        session.marketing_consent = marketing_consent
        if marketing_consent:
            session.consent_timestamp = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(session)
        return session

    def export_marketing_list(
        self,
        location_id: int,
        format: str = "json",
    ) -> List[Dict[str, Any]]:
        """Export marketing contact list."""
        contacts = self.get_marketing_contacts(location_id)

        return [
            {
                "email": c.email,
                "phone": c.phone,
                "name": c.name,
                "visit_count": c.visit_count,
                "last_visit": c.last_visit.isoformat() if c.last_visit else None,
                "consent_date": c.consent_timestamp.isoformat() if c.consent_timestamp else None,
            }
            for c in contacts
            if c.email or c.phone
        ]

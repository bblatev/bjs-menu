"""Reservations & Waitlist Service - TouchBistro style."""

import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.models.reservations import (
    Reservation, Waitlist, TableAvailability, ReservationSettings, GuestHistory,
    ReservationStatus, WaitlistStatus, BookingSource
)
from app.services.communication_service import SMSService, EmailService


class ReservationService:
    """Manage restaurant reservations."""

    def __init__(self, db: Session):
        self.db = db
        self.sms_service = SMSService()
        self.email_service = EmailService()

    async def create_reservation(
        self,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new reservation."""
        try:
            guest_name = data.get("guest_name")
            party_size = data.get("party_size")
            reservation_date = data.get("reservation_date")
            guest_phone = data.get("guest_phone")
            guest_email = data.get("guest_email")
            location_id = data.get("location_id")
            seating_preference = data.get("seating_preference")
            special_requests = data.get("special_requests")
            occasion = data.get("occasion")
            source = data.get("source", BookingSource.WEBSITE)

            # Generate confirmation code
            confirmation_code = self._generate_confirmation_code()

            # Get settings for duration
            settings = self._get_settings(location_id)
            duration = settings.default_duration_minutes if settings else 90

            # Check availability
            available_tables = self._find_available_tables(
                location_id, reservation_date, party_size, duration
            )

            reservation = Reservation(
                location_id=location_id,
                guest_name=guest_name,
                guest_phone=guest_phone,
                guest_email=guest_email,
                party_size=party_size,
                reservation_date=reservation_date,
                duration_minutes=duration,
                seating_preference=seating_preference,
                special_requests=special_requests,
                occasion=occasion,
                source=source,
                confirmation_code=confirmation_code,
                status=ReservationStatus.CONFIRMED if settings and settings.auto_confirm else ReservationStatus.PENDING,
                table_ids=available_tables[:1] if available_tables else None
            )

            self.db.add(reservation)
            self.db.commit()

            # Update guest history
            self._update_guest_history(guest_phone, guest_email)

            # Send confirmation
            if settings and (settings.send_confirmation_email or settings.send_confirmation_sms):
                await self._send_confirmation(reservation, settings)

            return {"reservation": reservation}
        except Exception as e:
            return {"error": str(e)}

    def _generate_confirmation_code(self) -> str:
        """Generate unique confirmation code."""
        chars = string.ascii_uppercase + string.digits
        while True:
            code = ''.join(secrets.choice(chars) for _ in range(6))
            existing = self.db.query(Reservation).filter(
                Reservation.confirmation_code == code
            ).first()
            if not existing:
                return code

    def _get_settings(self, location_id: Optional[int]) -> Optional[ReservationSettings]:
        """Get reservation settings for location."""
        return self.db.query(ReservationSettings).filter(
            ReservationSettings.location_id == location_id
        ).first()

    def _find_available_tables(
        self,
        location_id: Optional[int],
        reservation_date: datetime,
        party_size: int,
        duration: int
    ) -> List[int]:
        """Find available tables for reservation."""
        # This would integrate with table management
        # For now, return empty list
        return []

    def _update_guest_history(
        self,
        phone: Optional[str],
        email: Optional[str]
    ) -> None:
        """Update or create guest history."""
        if not phone and not email:
            return

        guest = self.db.query(GuestHistory).filter(
            or_(
                GuestHistory.guest_phone == phone,
                GuestHistory.guest_email == email
            )
        ).first()

        if not guest:
            guest = GuestHistory(
                guest_phone=phone,
                guest_email=email,
                total_visits=0,
                first_visit_at=datetime.utcnow()
            )
            self.db.add(guest)

        self.db.commit()

    async def _send_confirmation(
        self,
        reservation: Reservation,
        settings: ReservationSettings
    ) -> None:
        """Send reservation confirmation."""
        restaurant_name = "V99 Restaurant"

        if settings.send_confirmation_sms and reservation.guest_phone:
            await self.sms_service.send_reservation_confirmation(
                to_number=reservation.guest_phone,
                guest_name=reservation.guest_name,
                date_time=reservation.reservation_date,
                party_size=reservation.party_size,
                confirmation_code=reservation.confirmation_code,
                restaurant_name=restaurant_name
            )

        if settings.send_confirmation_email and reservation.guest_email:
            self.email_service.send_email(
                to_email=reservation.guest_email,
                subject=f"Reservation Confirmed - {restaurant_name}",
                body_html=self._generate_confirmation_email(reservation, restaurant_name)
            )

        reservation.confirmed_at = datetime.utcnow()
        self.db.commit()

    def _generate_confirmation_email(
        self,
        reservation: Reservation,
        restaurant_name: str
    ) -> str:
        """Generate confirmation email HTML."""
        return f"""
        <div style="font-family: Arial; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #2563eb;">Reservation Confirmed</h1>
            <p>Dear {reservation.guest_name},</p>
            <p>Your reservation at {restaurant_name} has been confirmed!</p>

            <div style="background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <p><strong>Date:</strong> {reservation.reservation_date.strftime('%B %d, %Y')}</p>
                <p><strong>Time:</strong> {reservation.reservation_date.strftime('%I:%M %p')}</p>
                <p><strong>Party Size:</strong> {reservation.party_size} guests</p>
                <p><strong>Confirmation Code:</strong> {reservation.confirmation_code}</p>
            </div>

            <p>If you need to modify or cancel your reservation, please contact us or reply to this email.</p>
            <p>We look forward to seeing you!</p>
        </div>
        """

    async def cancel_reservation(
        self,
        reservation_id: int,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Cancel a reservation."""
        reservation = self.db.query(Reservation).filter(
            Reservation.id == reservation_id
        ).first()

        if not reservation:
            return {"error": "Reservation not found"}

        reservation.status = ReservationStatus.CANCELLED
        reservation.internal_notes = f"Cancelled: {reason}" if reason else "Cancelled"

        # Update guest history
        self._record_cancellation(reservation)

        self.db.commit()
        return {"reservation": reservation}

    def _record_cancellation(self, reservation: Reservation) -> None:
        """Record cancellation in guest history."""
        guest = self.db.query(GuestHistory).filter(
            or_(
                GuestHistory.guest_phone == reservation.guest_phone,
                GuestHistory.guest_email == reservation.guest_email
            )
        ).first()

        if guest:
            guest.total_cancellations += 1
            self.db.commit()

    def mark_no_show(self, reservation_id: int) -> Reservation:
        """Mark reservation as no-show."""
        reservation = self.db.query(Reservation).filter(
            Reservation.id == reservation_id
        ).first()

        if not reservation:
            raise ValueError("Reservation not found")

        reservation.status = ReservationStatus.NO_SHOW

        # Update guest history
        guest = self.db.query(GuestHistory).filter(
            or_(
                GuestHistory.guest_phone == reservation.guest_phone,
                GuestHistory.guest_email == reservation.guest_email
            )
        ).first()

        if guest:
            guest.total_no_shows += 1

            # Check for blacklist threshold
            if guest.total_no_shows >= 3:
                guest.is_blacklisted = True
                guest.blacklist_reason = "Multiple no-shows"

        self.db.commit()
        return reservation

    def seat_reservation(
        self,
        reservation_id: int,
        table_ids: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """Mark reservation as seated."""
        reservation = self.db.query(Reservation).filter(
            Reservation.id == reservation_id
        ).first()

        if not reservation:
            return {"error": "Reservation not found"}

        reservation.status = ReservationStatus.SEATED
        reservation.arrived_at = datetime.utcnow()
        reservation.seated_at = datetime.utcnow()

        if table_ids:
            reservation.table_ids = table_ids

        self.db.commit()
        return {"reservation": reservation}

    def get_reservations_for_date(
        self,
        date: datetime,
        location_id: Optional[int] = None
    ) -> List[Reservation]:
        """Get all reservations for a date."""
        start = datetime(date.year, date.month, date.day, 0, 0, 0)
        end = start + timedelta(days=1)

        query = self.db.query(Reservation).filter(
            Reservation.reservation_date >= start,
            Reservation.reservation_date < end,
            Reservation.status.notin_([ReservationStatus.CANCELLED])
        )

        if location_id:
            query = query.filter(Reservation.location_id == location_id)

        return query.order_by(Reservation.reservation_date).all()

    async def send_reminders(self) -> Dict[str, int]:
        """Send reservation reminders."""
        now = datetime.utcnow()
        sent_24h = 0
        sent_2h = 0

        # 24-hour reminders
        target_24h = now + timedelta(hours=24)
        reservations_24h = self.db.query(Reservation).filter(
            Reservation.reservation_date >= target_24h - timedelta(minutes=30),
            Reservation.reservation_date <= target_24h + timedelta(minutes=30),
            Reservation.reminder_24h_sent == False,
            Reservation.status == ReservationStatus.CONFIRMED
        ).all()

        for res in reservations_24h:
            if res.guest_phone:
                await self.sms_service.send_reservation_reminder(
                    to_number=res.guest_phone,
                    guest_name=res.guest_name,
                    date_time=res.reservation_date,
                    hours_until=24
                )
                res.reminder_24h_sent = True
                sent_24h += 1

        # 2-hour reminders
        target_2h = now + timedelta(hours=2)
        reservations_2h = self.db.query(Reservation).filter(
            Reservation.reservation_date >= target_2h - timedelta(minutes=15),
            Reservation.reservation_date <= target_2h + timedelta(minutes=15),
            Reservation.reminder_2h_sent == False,
            Reservation.status == ReservationStatus.CONFIRMED
        ).all()

        for res in reservations_2h:
            if res.guest_phone:
                await self.sms_service.send_reservation_reminder(
                    to_number=res.guest_phone,
                    guest_name=res.guest_name,
                    date_time=res.reservation_date,
                    hours_until=2
                )
                res.reminder_2h_sent = True
                sent_2h += 1

        self.db.commit()

        return {"24h_reminders": sent_24h, "2h_reminders": sent_2h}

    async def send_reminder(self, reservation_id: int) -> Dict[str, Any]:
        """Send reminder for a specific reservation."""
        reservation = self.db.query(Reservation).filter(
            Reservation.id == reservation_id
        ).first()

        if not reservation:
            return {"error": "Reservation not found"}

        if reservation.guest_phone:
            await self.sms_service.send_reservation_reminder(
                to_number=reservation.guest_phone,
                guest_name=reservation.guest_name,
                date_time=reservation.reservation_date,
                hours_until=24
            )
            return {"status": "sent", "method": "sms"}

        return {"status": "no_contact", "message": "No phone number available"}

    def get_available_slots(
        self,
        location_id: int,
        target_date: Any
    ) -> List[Dict[str, Any]]:
        """Get available time slots for a date."""
        # Get settings for the location
        settings = self._get_settings(location_id)

        # Default operating hours if no settings
        open_time = 11  # 11 AM
        close_time = 22  # 10 PM
        slot_interval = 30  # 30 minute slots

        if settings:
            # Could parse from settings if stored there
            pass

        # Get existing reservations for this date
        from datetime import date as date_type
        if isinstance(target_date, date_type):
            start = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0)
        else:
            start = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0)
        end = start + timedelta(days=1)

        existing = self.db.query(Reservation).filter(
            Reservation.location_id == location_id,
            Reservation.reservation_date >= start,
            Reservation.reservation_date < end,
            Reservation.status.notin_([ReservationStatus.CANCELLED, ReservationStatus.NO_SHOW])
        ).all()

        # Generate available slots
        available = []
        current_hour = open_time
        current_minute = 0

        while current_hour < close_time:
            slot_time = f"{current_hour:02d}:{current_minute:02d}"
            slot_datetime = start.replace(hour=current_hour, minute=current_minute)

            # Check if slot conflicts with existing reservations
            is_available = True
            for res in existing:
                res_end = res.reservation_date + timedelta(minutes=res.duration_minutes or 90)
                if res.reservation_date <= slot_datetime < res_end:
                    is_available = False
                    break

            if is_available:
                available.append({"time": slot_time, "available": True})

            # Move to next slot
            current_minute += slot_interval
            if current_minute >= 60:
                current_minute = 0
                current_hour += 1

        return available

    def check_availability(
        self,
        location_id: int,
        date: Any,
        party_size: int,
        preferred_time: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Check availability for a specific party size and date."""
        available_slots = self.get_available_slots(location_id, date)

        # Filter slots based on party size constraints if needed
        # For now, return all available slots

        available_times = available_slots
        suggested_times = []

        # If preferred time specified, find nearby alternatives
        if preferred_time:
            pref_str = preferred_time.strftime("%H:%M") if hasattr(preferred_time, 'strftime') else str(preferred_time)
            if pref_str in available_times:
                suggested_times = [pref_str]
            else:
                # Find closest available times
                suggested_times = available_times[:3]  # Suggest first 3 available

        return {
            "available_times": available_times,
            "suggested_times": suggested_times
        }


class WaitlistService:
    """Manage restaurant waitlist."""

    def __init__(self, db: Session):
        self.db = db
        self.sms_service = SMSService()

    async def add_to_waitlist(
        self,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add guest to waitlist."""
        try:
            guest_name = data.get("guest_name")
            party_size = data.get("party_size")
            guest_phone = data.get("guest_phone")
            location_id = data.get("location_id")
            seating_preference = data.get("seating_preference")
            notes = data.get("notes")

            # Calculate estimated wait
            estimated_wait = self._estimate_wait_time(location_id, party_size)

            # Get position
            position = self._get_next_position(location_id)

            entry = Waitlist(
                location_id=location_id,
                guest_name=guest_name,
                guest_phone=guest_phone,
                party_size=party_size,
                seating_preference=seating_preference,
                estimated_wait_minutes=estimated_wait,
                quoted_wait_minutes=estimated_wait,
                position=position,
                status=WaitlistStatus.WAITING,
                notes=notes
            )

            self.db.add(entry)
            self.db.commit()

            # Send SMS confirmation
            if guest_phone:
                await self.sms_service.send_waitlist_confirmation(
                    to_number=guest_phone,
                    guest_name=guest_name,
                    position=position,
                    estimated_wait=estimated_wait
                )
                entry.sms_confirmation_sent = True
                self.db.commit()

            return {"entry": entry}
        except Exception as e:
            return {"error": str(e)}

    def _estimate_wait_time(
        self,
        location_id: Optional[int],
        party_size: int
    ) -> int:
        """Estimate wait time based on current waitlist and table turnover."""
        # Count current waitlist
        waiting_count = self.db.query(Waitlist).filter(
            Waitlist.location_id == location_id,
            Waitlist.status == WaitlistStatus.WAITING
        ).count()

        # Calculate total covers waiting
        waiting_covers = self.db.query(func.sum(Waitlist.party_size)).filter(
            Waitlist.location_id == location_id,
            Waitlist.status == WaitlistStatus.WAITING
        ).scalar() or 0

        # Estimate based on average table turn time (45 min) and waiting covers
        # This is a simplified estimate
        base_wait = 15  # Minimum wait
        per_party_wait = 10  # Additional minutes per party ahead
        per_cover_wait = 2   # Additional minutes per cover ahead

        estimated = base_wait + (waiting_count * per_party_wait)

        # Add more time for larger parties
        if party_size > 4:
            estimated += 15
        if party_size > 6:
            estimated += 15

        return min(estimated, 120)  # Cap at 2 hours

    def _get_next_position(self, location_id: Optional[int]) -> int:
        """Get next position number for waitlist."""
        max_position = self.db.query(func.max(Waitlist.position)).filter(
            Waitlist.location_id == location_id,
            Waitlist.status == WaitlistStatus.WAITING
        ).scalar()

        return (max_position or 0) + 1

    async def notify_table_ready(self, entry_id: int) -> Waitlist:
        """Notify guest their table is ready."""
        entry = self.db.query(Waitlist).filter(
            Waitlist.id == entry_id
        ).first()

        if not entry:
            raise ValueError("Waitlist entry not found")

        entry.status = WaitlistStatus.NOTIFIED

        if entry.guest_phone and not entry.sms_ready_sent:
            await self.sms_service.send_table_ready_notification(
                to_number=entry.guest_phone,
                guest_name=entry.guest_name
            )
            entry.sms_ready_sent = True
            entry.sms_ready_sent_at = datetime.utcnow()

        self.db.commit()
        return entry

    async def notify_guest(self, waitlist_id: int) -> Dict[str, Any]:
        """Notify guest their table is ready (route-compatible wrapper)."""
        entry = self.db.query(Waitlist).filter(
            Waitlist.id == waitlist_id
        ).first()

        if not entry:
            return {"error": "Waitlist entry not found"}

        entry.status = WaitlistStatus.NOTIFIED

        if entry.guest_phone and not entry.sms_ready_sent:
            await self.sms_service.send_table_ready_notification(
                to_number=entry.guest_phone,
                guest_name=entry.guest_name
            )
            entry.sms_ready_sent = True
            entry.sms_ready_sent_at = datetime.utcnow()

        self.db.commit()
        return {"status": "notified", "entry": entry}

    def seat_from_waitlist(
        self,
        entry_id: int,
        table_ids: Optional[List[int]] = None
    ) -> Waitlist:
        """Seat a party from waitlist."""
        entry = self.db.query(Waitlist).filter(
            Waitlist.id == entry_id
        ).first()

        if not entry:
            raise ValueError("Waitlist entry not found")

        entry.status = WaitlistStatus.SEATED
        entry.seated_at = datetime.utcnow()
        entry.table_ids = table_ids

        # Calculate actual wait time
        if entry.added_at:
            wait_delta = datetime.utcnow() - entry.added_at
            entry.actual_wait_minutes = int(wait_delta.total_seconds() / 60)

        # Update positions for remaining entries
        self._update_positions(entry.location_id)

        self.db.commit()
        return entry

    def seat_guest(
        self,
        waitlist_id: int,
        table_ids: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """Seat a guest from waitlist (route-compatible wrapper)."""
        entry = self.db.query(Waitlist).filter(
            Waitlist.id == waitlist_id
        ).first()

        if not entry:
            return {"error": "Waitlist entry not found"}

        entry.status = WaitlistStatus.SEATED
        entry.seated_at = datetime.utcnow()
        entry.table_ids = table_ids

        # Calculate actual wait time
        if entry.added_at:
            wait_delta = datetime.utcnow() - entry.added_at
            entry.actual_wait_minutes = int(wait_delta.total_seconds() / 60)

        # Update positions for remaining entries
        self._update_positions(entry.location_id)

        self.db.commit()
        return {"entry": entry}

    async def remove_from_waitlist(
        self,
        entry_id: int,
        reason: Optional[str] = "left"
    ) -> Dict[str, Any]:
        """Remove guest from waitlist."""
        entry = self.db.query(Waitlist).filter(
            Waitlist.id == entry_id
        ).first()

        if not entry:
            return {"error": "Waitlist entry not found"}

        entry.status = WaitlistStatus.LEFT if reason == "left" else WaitlistStatus.CANCELLED
        entry.left_at = datetime.utcnow()
        entry.left_reason = reason

        # Update positions
        self._update_positions(entry.location_id)

        self.db.commit()
        return {"status": "removed", "entry": entry}

    def _update_positions(self, location_id: Optional[int]) -> None:
        """Recalculate positions after changes."""
        entries = self.db.query(Waitlist).filter(
            Waitlist.location_id == location_id,
            Waitlist.status == WaitlistStatus.WAITING
        ).order_by(Waitlist.added_at).all()

        for i, entry in enumerate(entries, 1):
            entry.position = i

    def get_current_waitlist(
        self,
        location_id: Optional[int] = None
    ) -> List[Waitlist]:
        """Get current active waitlist."""
        query = self.db.query(Waitlist).filter(
            Waitlist.status.in_([WaitlistStatus.WAITING, WaitlistStatus.NOTIFIED])
        )

        if location_id:
            query = query.filter(Waitlist.location_id == location_id)

        return query.order_by(Waitlist.position).all()

    def get_waitlist_stats(
        self,
        location_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get waitlist statistics."""
        query = self.db.query(Waitlist).filter(
            Waitlist.status.in_([WaitlistStatus.WAITING, WaitlistStatus.NOTIFIED])
        )

        if location_id:
            query = query.filter(Waitlist.location_id == location_id)

        entries = query.all()

        total_waiting = len(entries)
        total_covers = sum(e.party_size for e in entries)
        avg_wait = (
            sum(e.quoted_wait_minutes or 0 for e in entries) / len(entries)
            if entries else 0
        )

        # Longest wait
        longest_entry = min(entries, key=lambda x: x.added_at) if entries else None
        longest_wait = 0
        if longest_entry and longest_entry.added_at:
            longest_wait = int((datetime.utcnow() - longest_entry.added_at).total_seconds() / 60)

        return {
            "total_waiting": total_waiting,
            "total_covers": total_covers,
            "average_quoted_wait": round(avg_wait),
            "longest_current_wait": longest_wait,
            "notified_count": len([e for e in entries if e.status == WaitlistStatus.NOTIFIED])
        }

"""
Queue & Waitlist Service Stub
=============================
Service stub for V6 queue and waitlist management features.
"""


class WaitlistEntry:
    """Simple data object for a waitlist entry."""

    def __init__(self, **kwargs):
        self.id = kwargs.get("id", "")
        self.position = kwargs.get("position", 0)
        self.estimated_wait_minutes = kwargs.get("estimated_wait_minutes", 0)
        self.customer_name = kwargs.get("customer_name", "")
        self.customer_phone = kwargs.get("customer_phone", "")
        self.party_size = kwargs.get("party_size", 0)
        self.status = kwargs.get("status", "waiting")

    def dict(self):
        return {
            "id": self.id,
            "position": self.position,
            "estimated_wait_minutes": self.estimated_wait_minutes,
            "customer_name": self.customer_name,
            "customer_phone": self.customer_phone,
            "party_size": self.party_size,
            "status": self.status,
        }


class QueueWaitlistService:
    """Service for managing restaurant waitlists and queues."""

    def __init__(self, db=None):
        self.db = db

    def add_to_waitlist(self, venue_id: int, customer_name: str, customer_phone: str,
                        party_size: int, notes: str = None,
                        seating_preference: str = None) -> WaitlistEntry:
        """Add a party to the waitlist."""
        return WaitlistEntry(
            id=f"WL-{venue_id}-1",
            position=1,
            estimated_wait_minutes=15,
            customer_name=customer_name,
            customer_phone=customer_phone,
            party_size=party_size,
            status="waiting",
        )

    def get_waitlist(self, venue_id: int) -> list:
        """Get the current waitlist for a venue."""
        return []

    def notify_party(self, entry_id: str) -> dict:
        """Notify a party that their table is ready."""
        return {"notified": True}

    def seat_party(self, entry_id: str, table_id: int) -> dict:
        """Mark a party as seated."""
        return {"seated": True}

    def cancel_entry(self, entry_id: str) -> dict:
        """Cancel a waitlist entry."""
        return {"cancelled": True}

    def get_stats(self, venue_id: int) -> dict:
        """Get waitlist statistics for a venue."""
        return {"current_count": 0, "avg_wait_minutes": 0}

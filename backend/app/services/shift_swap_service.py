"""Shift swap marketplace service."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session


class ShiftSwapService:
    """Handles shift swap requests between staff members."""

    @staticmethod
    def get_available_swaps(db: Session, venue_id: int, staff_id: Optional[int] = None):
        """Get shifts available for swapping."""
        from app.models.staff import Shift
        from app.models.missing_features_models import ShiftTradeRequest

        query = db.query(ShiftTradeRequest).filter(
            ShiftTradeRequest.venue_id == venue_id,
            ShiftTradeRequest.status == "open",
        )
        if staff_id:
            query = query.filter(ShiftTradeRequest.requester_id != staff_id)

        swaps = query.order_by(ShiftTradeRequest.created_at.desc()).all()
        return [
            {
                "id": s.id,
                "requester_id": s.requester_id,
                "shift_date": str(s.shift_date) if hasattr(s, 'shift_date') else None,
                "shift_start": str(s.shift_start) if hasattr(s, 'shift_start') else None,
                "shift_end": str(s.shift_end) if hasattr(s, 'shift_end') else None,
                "reason": s.reason if hasattr(s, 'reason') else None,
                "status": s.status,
            }
            for s in swaps
        ]

    @staticmethod
    def request_swap(db: Session, venue_id: int, staff_id: int, shift_id: int, reason: str = ""):
        """Create a shift swap request."""
        from app.models.missing_features_models import ShiftTradeRequest

        swap = ShiftTradeRequest(
            venue_id=venue_id,
            requester_id=staff_id,
            shift_id=shift_id,
            reason=reason,
            status="open",
        )
        db.add(swap)
        db.commit()
        db.refresh(swap)
        return {"id": swap.id, "status": "open", "message": "Swap request created"}

    @staticmethod
    def accept_swap(db: Session, swap_id: int, acceptor_id: int):
        """Accept a shift swap request."""
        from app.models.missing_features_models import ShiftTradeRequest

        swap = db.query(ShiftTradeRequest).filter(ShiftTradeRequest.id == swap_id).first()
        if not swap:
            return None

        swap.acceptor_id = acceptor_id
        swap.status = "pending_approval"
        db.commit()
        return {"id": swap.id, "status": "pending_approval", "message": "Swap accepted, pending manager approval"}

    @staticmethod
    def approve_swap(db: Session, swap_id: int, manager_id: int):
        """Manager approves a shift swap."""
        from app.models.missing_features_models import ShiftTradeRequest

        swap = db.query(ShiftTradeRequest).filter(ShiftTradeRequest.id == swap_id).first()
        if not swap:
            return None

        swap.status = "approved"
        swap.approved_by = manager_id
        db.commit()
        return {"id": swap.id, "status": "approved", "message": "Swap approved"}

from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta, timezone
from app.models.hardware import WaiterCall
from app.models.platform_compat import WaiterCallStatus
from app.schemas.waiter_call import WaiterCallCreate, WaiterCallResponse, WaiterCallStatusUpdate
from fastapi import HTTPException, status


class WaiterCallService:
    def __init__(self, db: Session):
        self.db = db

    def _check_rate_limit(self, table_id: int) -> None:
        """Check waiter call rate limit for table."""
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        call_count = self.db.query(WaiterCall).filter(
            WaiterCall.table_id == table_id,
            WaiterCall.created_at >= one_hour_ago,
            WaiterCall.status != "spam"
        ).count()

        max_calls = 20  # reasonable default
        if call_count >= max_calls:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many waiter calls from this table. Please wait."
            )

    def create_call(self, request: WaiterCallCreate) -> WaiterCallResponse:
        """Create waiter call."""
        call = WaiterCall(
            table_id=request.table_id,
            table_number=str(request.table_id),
            call_type=request.reason.value if hasattr(request.reason, 'value') else str(request.reason),
            message=request.message,
            status="pending"
        )
        self.db.add(call)
        self.db.commit()
        self.db.refresh(call)

        return self._build_response(call)

    def get_active_calls(self) -> List[WaiterCallResponse]:
        """Get all active waiter calls."""
        calls = self.db.query(WaiterCall).filter(
            WaiterCall.status.in_(["pending", "acknowledged"])
        ).order_by(WaiterCall.created_at.asc()).all()

        return [self._build_response(call) for call in calls]

    def update_call_status(self, call_id: int, update: WaiterCallStatusUpdate) -> WaiterCallResponse:
        """Update waiter call status."""
        call = self.db.query(WaiterCall).filter(WaiterCall.id == call_id).first()

        if not call:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Waiter call not found"
            )

        new_status = update.status.value if hasattr(update.status, 'value') else str(update.status)
        call.status = new_status

        if new_status == "acknowledged" and not call.acknowledged_at:
            call.acknowledged_at = datetime.now(timezone.utc)

        if new_status in ["resolved", "spam"] and not call.completed_at:
            call.completed_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(call)

        return self._build_response(call)

    def _build_response(self, call: WaiterCall) -> WaiterCallResponse:
        """Build waiter call response."""
        return WaiterCallResponse(
            id=call.id,
            table_id=call.table_id,
            reason=call.call_type or "other",
            message=call.message,
            status=call.status or "pending",
            created_at=call.created_at,
            acknowledged_at=call.acknowledged_at,
            resolved_at=call.completed_at
        )

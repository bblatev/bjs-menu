from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
from app.models import WaiterCall, Table, TableToken, WaiterCallStatus
from app.schemas import WaiterCallCreate, WaiterCallResponse, WaiterCallStatusUpdate
from fastapi import HTTPException, status


class WaiterCallService:
    def __init__(self, db: Session):
        self.db = db
    
    def _validate_table_token(self, token: str) -> Table:
        """Validate table token and return table."""
        table_token = self.db.query(TableToken).filter(
            TableToken.token == token,
            TableToken.active == True
        ).first()
        
        if not table_token:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid table token"
            )
        
        return table_token.table
    
    def _check_rate_limit(self, table_id: int) -> None:
        """Check waiter call rate limit for table."""
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        call_count = self.db.query(WaiterCall).filter(
            WaiterCall.table_id == table_id,
            WaiterCall.created_at >= one_hour_ago,
            WaiterCall.status != WaiterCallStatus.SPAM
        ).count()
        
        from app.core.config import settings
        
        if call_count >= settings.WAITER_CALL_RATE_LIMIT_PER_TABLE_PER_HOUR:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many waiter calls from this table. Please wait."
            )
    
    def create_call(self, request: WaiterCallCreate) -> WaiterCallResponse:
        """Create waiter call."""
        table = self._validate_table_token(request.table_token)
        self._check_rate_limit(table.id)
        
        call = WaiterCall(
            table_id=table.id,
            reason=request.reason,
            message=request.message,
            status=WaiterCallStatus.PENDING
        )
        self.db.add(call)
        self.db.commit()
        self.db.refresh(call)
        
        # Broadcast waiter call created (async)
        import asyncio
        import logging
        try:
            from app.main import broadcast_waiter_call
            asyncio.create_task(broadcast_waiter_call(call.id, table.number, call.status))
        except Exception as e:
            logging.warning(f"Failed to broadcast waiter call: {e}")
        
        return self._build_response(call)
    
    def get_active_calls(self) -> List[WaiterCallResponse]:
        """Get all active waiter calls."""
        calls = self.db.query(WaiterCall).filter(
            WaiterCall.status.in_([WaiterCallStatus.PENDING, WaiterCallStatus.ACKNOWLEDGED])
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
        
        call.status = update.status
        
        if update.status == WaiterCallStatus.ACKNOWLEDGED and not call.acknowledged_at:
            call.acknowledged_at = datetime.utcnow()
        
        if update.status in [WaiterCallStatus.RESOLVED, WaiterCallStatus.SPAM] and not call.resolved_at:
            call.resolved_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(call)
        
        # Broadcast status update (async)
        import asyncio
        import logging
        try:
            from app.main import broadcast_waiter_call
            asyncio.create_task(broadcast_waiter_call(call.id, call.table.number, call.status))
        except Exception as e:
            logging.warning(f"Failed to broadcast waiter call status update: {e}")
        
        return self._build_response(call)
    
    def _build_response(self, call: WaiterCall) -> WaiterCallResponse:
        """Build waiter call response."""
        return WaiterCallResponse(
            id=call.id,
            table_number=call.table.number,
            reason=call.reason,
            message=call.message,
            status=call.status,
            created_at=call.created_at,
            acknowledged_at=call.acknowledged_at,
            resolved_at=call.resolved_at
        )

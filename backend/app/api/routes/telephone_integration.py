"""
Telephone System Integration API Endpoints
TouchSale feature: Integration with PBX systems (ELTA, Alcatel, Panasonic, Siemens, etc.)
For caller ID lookup, automatic reservations, and customer recognition
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Request
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, Field
import asyncio
import json

from app.db.session import get_db
from app.core.rbac import get_current_user
from app.core.rate_limit import limiter
from app.models import StaffUser, Customer, Reservation


logger = logging.getLogger(__name__)

router = APIRouter()


def require_admin(current_user = Depends(get_current_user)):
    """Require admin/owner role."""
    if not hasattr(current_user, 'role'):
        return current_user
    if current_user.role not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def require_manager(current_user = Depends(get_current_user)):
    """Require manager or above role."""
    if not hasattr(current_user, 'role'):
        return current_user
    if current_user.role not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Manager access required")
    return current_user



# =============================================================================
# SCHEMAS
# =============================================================================

class PBXConnectionConfig(BaseModel):
    """PBX system connection configuration"""
    system_type: str = Field(..., description="PBX type: elta, alcatel, panasonic, siemens, asterisk, generic_sip")
    host: str = Field(..., description="PBX server hostname or IP")
    port: int = Field(5060, description="Connection port")
    username: Optional[str] = None
    password: Optional[str] = None

    # Features
    caller_id_enabled: bool = Field(True, description="Enable caller ID lookup")
    auto_reservation_enabled: bool = Field(False, description="Auto-create reservation on call")
    call_logging_enabled: bool = Field(True, description="Log all calls")

    # Advanced settings
    trunk_id: Optional[str] = None
    extension_pattern: Optional[str] = Field(None, description="Extension pattern for restaurant lines")
    sip_domain: Optional[str] = None


class PBXConnectionResponse(PBXConnectionConfig):
    id: int
    venue_id: int
    is_active: bool
    connection_status: str
    last_connected_at: Optional[datetime]
    created_at: datetime


class IncomingCallEvent(BaseModel):
    """Incoming call notification"""
    caller_number: str
    called_number: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    trunk_id: Optional[str] = None


class CallerInfo(BaseModel):
    """Customer info based on caller ID"""
    phone_number: str
    customer_found: bool
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    is_vip: bool = False
    total_visits: int = 0
    last_visit: Optional[datetime] = None
    favorite_items: List[str] = []
    dietary_preferences: Optional[str] = None
    allergies: List[str] = []
    notes: Optional[str] = None
    active_reservation: Optional[Dict[str, Any]] = None


class CallLogEntry(BaseModel):
    id: int
    direction: str  # inbound, outbound
    caller_number: str
    called_number: str
    customer_id: Optional[int]
    customer_name: Optional[str]
    duration_seconds: int
    call_status: str  # answered, missed, voicemail
    notes: Optional[str]
    created_reservation: bool
    reservation_id: Optional[int]
    handled_by: Optional[int]
    timestamp: datetime


class QuickReservationRequest(BaseModel):
    """Create reservation during call"""
    phone_number: str
    customer_name: str
    party_size: int = Field(2, ge=1, le=50)
    date: str = Field(..., description="YYYY-MM-DD")
    time: str = Field(..., description="HH:MM")
    notes: Optional[str] = None


# =============================================================================
# IN-MEMORY STATE (Production: Use Redis)
# =============================================================================

# Active PBX connections
pbx_connections: Dict[int, Dict[str, Any]] = {}

# Call logs (Production: Store in database)
call_logs: List[Dict[str, Any]] = []
call_log_counter = 1

# WebSocket connections for real-time call notifications
call_notification_sockets: Dict[str, WebSocket] = {}


# =============================================================================
# PBX CONNECTION MANAGEMENT
# =============================================================================

@router.get("/")
@limiter.limit("60/minute")
async def get_telephone_root(request: Request, db: Session = Depends(get_db)):
    """Telephony integration status."""
    return await list_pbx_connections(request=request, db=db)


@router.post("/config", response_model=PBXConnectionResponse)
@limiter.limit("30/minute")
async def create_pbx_connection(
    request: Request,
    data: PBXConnectionConfig,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin)
):
    """Configure PBX system connection"""
    connection = {
        "id": len(pbx_connections) + 1,
        "venue_id": current_user.venue_id,
        **data.model_dump(),
        "is_active": False,
        "connection_status": "disconnected",
        "last_connected_at": None,
        "created_at": datetime.now(timezone.utc)
    }

    pbx_connections[connection["id"]] = connection

    return PBXConnectionResponse(**connection)


@router.get("/config", response_model=List[PBXConnectionResponse])
@limiter.limit("60/minute")
async def list_pbx_connections(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """List PBX configurations"""
    venue_connections = [
        PBXConnectionResponse(**c)
        for c in pbx_connections.values()
        if c.get("venue_id") == current_user.venue_id
    ]
    return venue_connections


@router.put("/config/{config_id}", response_model=PBXConnectionResponse)
@limiter.limit("30/minute")
async def update_pbx_connection(
    request: Request,
    config_id: int,
    data: PBXConnectionConfig,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin)
):
    """Update PBX configuration"""
    if config_id not in pbx_connections:
        raise HTTPException(status_code=404, detail="Configuration not found")

    connection = pbx_connections[config_id]
    if connection["venue_id"] != current_user.venue_id:
        raise HTTPException(status_code=403, detail="Access denied")

    connection.update(data.model_dump())

    return PBXConnectionResponse(**connection)


@router.post("/config/{config_id}/connect")
@limiter.limit("30/minute")
async def connect_pbx(
    request: Request,
    config_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin)
):
    """
    Connect to PBX system

    In production, this would establish actual connection to the PBX.
    """
    if config_id not in pbx_connections:
        raise HTTPException(status_code=404, detail="Configuration not found")

    connection = pbx_connections[config_id]

    # Mock connection (production: actual SIP/PBX connection)
    connection["is_active"] = True
    connection["connection_status"] = "connected"
    connection["last_connected_at"] = datetime.now(timezone.utc)

    return {
        "success": True,
        "message": f"Connected to {connection['system_type']} PBX at {connection['host']}"
    }


@router.post("/config/{config_id}/disconnect")
@limiter.limit("30/minute")
async def disconnect_pbx(
    request: Request,
    config_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin)
):
    """Disconnect from PBX system"""
    if config_id not in pbx_connections:
        raise HTTPException(status_code=404, detail="Configuration not found")

    connection = pbx_connections[config_id]
    connection["is_active"] = False
    connection["connection_status"] = "disconnected"

    return {"success": True, "message": "Disconnected from PBX"}


@router.post("/config/{config_id}/test")
@limiter.limit("30/minute")
async def test_pbx_connection(
    request: Request,
    config_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin)
):
    """Test PBX connection"""
    if config_id not in pbx_connections:
        raise HTTPException(status_code=404, detail="Configuration not found")

    connection = pbx_connections[config_id]

    # Mock test (production: actual connection test)
    return {
        "success": True,
        "system_type": connection["system_type"],
        "host": connection["host"],
        "latency_ms": 45,
        "features_available": [
            "caller_id",
            "call_logging",
            "call_transfer"
        ]
    }


# =============================================================================
# CALLER ID LOOKUP
# =============================================================================

@router.get("/caller/{phone_number}", response_model=CallerInfo)
@limiter.limit("60/minute")
async def lookup_caller(
    request: Request,
    phone_number: str,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Look up customer information by phone number

    Used when receiving incoming calls to display customer info.
    """
    # Normalize phone number
    normalized = phone_number.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not normalized.startswith("+"):
        normalized = "+" + normalized

    # Search for customer
    customer = db.query(Customer).filter(
        Customer.phone.ilike(f"%{normalized[-10:]}%"),  # Last 10 digits
        Customer.venue_id == current_user.venue_id
    ).first()

    if not customer:
        return CallerInfo(
            phone_number=phone_number,
            customer_found=False
        )

    # Get customer stats
    from sqlalchemy import func
    from app.models import Order

    order_count = db.query(func.count(Order.id)).filter(
        Order.customer_id == customer.id
    ).scalar() or 0

    last_order = db.query(Order).filter(
        Order.customer_id == customer.id
    ).order_by(Order.created_at.desc()).first()

    # Check for active reservation
    active_reservation = db.query(Reservation).filter(
        Reservation.customer_id == customer.id,
        Reservation.date >= datetime.now().date(),
        Reservation.status.in_(["pending", "confirmed"])
    ).first()

    reservation_info = None
    if active_reservation:
        reservation_info = {
            "id": active_reservation.id,
            "date": active_reservation.date.isoformat(),
            "time": active_reservation.time.isoformat() if active_reservation.time else None,
            "party_size": active_reservation.party_size,
            "status": active_reservation.status
        }

    return CallerInfo(
        phone_number=phone_number,
        customer_found=True,
        customer_id=customer.id,
        customer_name=customer.name,
        is_vip=customer.is_vip if hasattr(customer, 'is_vip') else False,
        total_visits=order_count,
        last_visit=last_order.created_at if last_order else None,
        favorite_items=[],  # Would be populated from order history
        dietary_preferences=customer.dietary_preferences if hasattr(customer, 'dietary_preferences') else None,
        allergies=customer.allergies if hasattr(customer, 'allergies') else [],
        notes=customer.notes if hasattr(customer, 'notes') else None,
        active_reservation=reservation_info
    )


# =============================================================================
# INCOMING CALL HANDLING
# =============================================================================

@router.post("/call/incoming")
@limiter.limit("30/minute")
async def handle_incoming_call(
    request: Request,
    event: IncomingCallEvent,
    db: Session = Depends(get_db)
):
    """
    Handle incoming call notification from PBX

    This endpoint is called by the PBX integration when a call comes in.
    It looks up the caller and notifies connected terminals.
    """
    global call_log_counter

    # Look up caller
    normalized = event.caller_number.replace(" ", "").replace("-", "")

    customer = db.query(Customer).filter(
        Customer.phone.ilike(f"%{normalized[-10:]}%")
    ).first()

    # Create call log entry
    log_entry = {
        "id": call_log_counter,
        "direction": "inbound",
        "caller_number": event.caller_number,
        "called_number": event.called_number,
        "customer_id": customer.id if customer else None,
        "customer_name": customer.name if customer else None,
        "duration_seconds": 0,
        "call_status": "ringing",
        "notes": None,
        "created_reservation": False,
        "reservation_id": None,
        "handled_by": None,
        "timestamp": event.timestamp
    }
    call_logs.append(log_entry)
    call_log_counter += 1

    # Prepare notification
    notification = {
        "type": "incoming_call",
        "call_id": log_entry["id"],
        "caller_number": event.caller_number,
        "customer_found": customer is not None,
        "customer_name": customer.name if customer else None,
        "customer_id": customer.id if customer else None,
        "is_vip": customer.is_vip if customer and hasattr(customer, 'is_vip') else False,
        "timestamp": event.timestamp.isoformat()
    }

    # Broadcast to all connected terminals
    await broadcast_call_notification(notification)

    return {
        "call_id": log_entry["id"],
        "customer_found": customer is not None,
        "customer_name": customer.name if customer else None
    }


@router.post("/call/{call_id}/answered")
@limiter.limit("30/minute")
async def mark_call_answered(
    request: Request,
    call_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Mark a call as answered"""
    for log in call_logs:
        if log["id"] == call_id:
            log["call_status"] = "answered"
            log["handled_by"] = current_user.id

            await broadcast_call_notification({
                "type": "call_answered",
                "call_id": call_id,
                "handled_by": current_user.full_name
            })

            return {"success": True}

    raise HTTPException(status_code=404, detail="Call not found")


@router.post("/call/{call_id}/ended")
@limiter.limit("30/minute")
async def mark_call_ended(
    request: Request,
    call_id: int,
    duration_seconds: int,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Mark a call as ended"""
    for log in call_logs:
        if log["id"] == call_id:
            log["duration_seconds"] = duration_seconds
            if log["call_status"] == "ringing":
                log["call_status"] = "missed"
            if notes:
                log["notes"] = notes

            await broadcast_call_notification({
                "type": "call_ended",
                "call_id": call_id,
                "duration": duration_seconds,
                "status": log["call_status"]
            })

            return {"success": True}

    raise HTTPException(status_code=404, detail="Call not found")


# =============================================================================
# QUICK RESERVATION FROM CALL
# =============================================================================

@router.post("/call/{call_id}/reservation")
@limiter.limit("30/minute")
async def create_reservation_from_call(
    request: Request,
    call_id: int,
    data: QuickReservationRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Create a reservation during an active call

    This is a streamlined flow for taking reservations over the phone.
    """
    # Find or create customer
    normalized = data.phone_number.replace(" ", "").replace("-", "")

    customer = db.query(Customer).filter(
        Customer.phone.ilike(f"%{normalized[-10:]}%"),
        Customer.venue_id == current_user.venue_id
    ).first()

    if not customer:
        customer = Customer(
            venue_id=current_user.venue_id,
            name=data.customer_name,
            phone=data.phone_number
        )
        db.add(customer)
        db.flush()

    # Create reservation
    from datetime import date as date_type, time as time_type

    res_date = date_type.fromisoformat(data.date)
    res_time = time_type.fromisoformat(data.time)

    reservation = Reservation(
        venue_id=current_user.venue_id,
        customer_id=customer.id,
        date=res_date,
        time=res_time,
        party_size=data.party_size,
        notes=data.notes,
        status="confirmed",
        source="phone",
        created_by=current_user.id
    )
    db.add(reservation)
    db.commit()
    db.refresh(reservation)

    # Update call log
    for log in call_logs:
        if log["id"] == call_id:
            log["created_reservation"] = True
            log["reservation_id"] = reservation.id
            break

    return {
        "success": True,
        "reservation_id": reservation.id,
        "customer_id": customer.id,
        "message": f"Reservation created for {data.customer_name} on {data.date} at {data.time}"
    }


# =============================================================================
# CALL LOGS
# =============================================================================

@router.get("/logs", response_model=List[CallLogEntry])
@limiter.limit("60/minute")
async def get_call_logs(
    request: Request,
    direction: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Get call history"""
    filtered_logs = call_logs.copy()

    if direction:
        filtered_logs = [l for l in filtered_logs if l["direction"] == direction]

    if status:
        filtered_logs = [l for l in filtered_logs if l["call_status"] == status]

    # Sort by timestamp descending
    filtered_logs.sort(key=lambda x: x["timestamp"], reverse=True)

    return filtered_logs[skip:skip + limit]


@router.get("/stats")
@limiter.limit("60/minute")
async def get_call_stats(
    request: Request,
    days: int = 7,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Get call statistics"""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    recent_logs = [l for l in call_logs if l["timestamp"] > cutoff]

    total = len(recent_logs)
    answered = len([l for l in recent_logs if l["call_status"] == "answered"])
    missed = len([l for l in recent_logs if l["call_status"] == "missed"])

    avg_duration = 0
    if answered > 0:
        avg_duration = sum(l["duration_seconds"] for l in recent_logs if l["call_status"] == "answered") / answered

    reservations_created = len([l for l in recent_logs if l["created_reservation"]])

    return {
        "period_days": days,
        "total_calls": total,
        "answered": answered,
        "missed": missed,
        "answer_rate": round(answered / total * 100, 2) if total > 0 else 0,
        "avg_duration_seconds": round(avg_duration, 0),
        "reservations_created": reservations_created,
        "conversion_rate": round(reservations_created / total * 100, 2) if total > 0 else 0
    }


# =============================================================================
# WEBSOCKET FOR REAL-TIME CALL NOTIFICATIONS
# =============================================================================

async def broadcast_call_notification(notification: Dict[str, Any]):
    """Broadcast call notification to all connected terminals"""
    message = json.dumps(notification)

    for terminal_id, ws in list(call_notification_sockets.items()):
        try:
            await ws.send_text(message)
        except Exception as e:
            # Remove disconnected socket
            logger.warning(f"Failed to send call notification to terminal {terminal_id}, removing disconnected socket: {e}")
            del call_notification_sockets[terminal_id]


@router.websocket("/ws/{terminal_id}")
async def websocket_call_notifications(
    websocket: WebSocket,
    terminal_id: str
):
    """
    WebSocket connection for real-time call notifications

    Terminals connect here to receive incoming call alerts.
    """
    await websocket.accept()
    call_notification_sockets[terminal_id] = websocket

    try:
        await websocket.send_json({
            "type": "connected",
            "terminal_id": terminal_id,
            "message": "Listening for incoming calls"
        })

        while True:
            try:
                # Keep connection alive
                data = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)

                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})

            except asyncio.TimeoutError:
                await websocket.send_json({"type": "keepalive"})

    except WebSocketDisconnect:
        pass
    finally:
        if terminal_id in call_notification_sockets:
            del call_notification_sockets[terminal_id]


# =============================================================================
# PBX SYSTEM SPECIFIC HANDLERS
# =============================================================================

@router.get("/systems")
@limiter.limit("60/minute")
async def get_supported_pbx_systems(request: Request):
    """Get list of supported PBX systems"""
    return {
        "systems": [
            {
                "type": "asterisk",
                "name": "Asterisk PBX",
                "description": "Open source PBX platform",
                "features": ["caller_id", "call_transfer", "voicemail", "call_recording"]
            },
            {
                "type": "elta",
                "name": "ELTA",
                "description": "ELTA telephone systems",
                "features": ["caller_id", "call_logging"]
            },
            {
                "type": "alcatel",
                "name": "Alcatel-Lucent",
                "description": "Alcatel enterprise communication",
                "features": ["caller_id", "call_transfer", "presence"]
            },
            {
                "type": "panasonic",
                "name": "Panasonic",
                "description": "Panasonic KX series",
                "features": ["caller_id", "call_logging", "door_phone"]
            },
            {
                "type": "siemens",
                "name": "Siemens/Unify",
                "description": "Siemens HiPath / Unify OpenScape",
                "features": ["caller_id", "call_transfer", "conference"]
            },
            {
                "type": "generic_sip",
                "name": "Generic SIP",
                "description": "Any SIP-compatible PBX",
                "features": ["caller_id"]
            }
        ]
    }

"""
WebSocket Endpoints for Real-time Updates
Handles connections for hardware monitoring, kitchen display, and notifications.

Auth: Supports two authentication modes:
  1. First-message auth (preferred): Client sends {"event":"auth","token":"..."} as
     the first message after connecting. Token is never exposed in URLs/logs.
  2. Query-string auth (legacy): Token passed as ?token=... query parameter.
     Kept for backward compatibility but discouraged.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException, Request
from typing import Optional
import asyncio
import json
import logging
import jwt
from jwt.exceptions import PyJWTError

from app.services.websocket_service import manager, EventType, WebSocketMessage
from app.core.config import settings
from app.core.rbac import get_current_user
from app.models import StaffUser
from app.core.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter()

# Timeout (seconds) for the client to send the first-message auth event.
_AUTH_TIMEOUT = 5.0


async def validate_ws_token(token: Optional[str]) -> Optional[dict]:
    """Validate WebSocket JWT token and return user info."""
    if not token:
        return None
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        user_id = payload.get("sub")
        if not user_id:
            return None
        return {"user_id": int(user_id), "venue_id": payload.get("venue_id", 1)}
    except (PyJWTError, ValueError, AttributeError):
        return None


async def authenticate_ws(
    websocket: WebSocket,
    query_token: Optional[str] = None,
) -> Optional[dict]:
    """Accept WebSocket and authenticate via cookie, first-message, or query-string token.

    Returns user info dict ``{"user_id": int, "venue_id": int}`` on success.
    Returns ``None`` if authentication fails (connection is already closed).

    Protocol (checked in order):
      1. Cookie auth: ``access_token`` HttpOnly cookie sent during WS handshake.
      2. Query-string auth (legacy): Token passed as ``?token=...``.
      3. First-message auth: Client sends ``{"event":"auth","token":"..."}``
         as the first message after connecting.
    """
    await websocket.accept()

    # --- Cookie auth (HttpOnly cookie sent during WS handshake) ---------------
    cookie_token = websocket.cookies.get("access_token")
    if cookie_token:
        auth = await validate_ws_token(cookie_token)
        if auth:
            await websocket.send_json({"event": "auth_success", "data": {"user_id": auth["user_id"]}})
            return auth
        # Cookie present but invalid — fall through to other methods

    # --- Legacy: token in query string ----------------------------------------
    if query_token:
        auth = await validate_ws_token(query_token)
        if auth:
            await websocket.send_json({"event": "auth_success", "data": {"user_id": auth["user_id"]}})
            return auth
        await websocket.close(code=4001, reason="Invalid token")
        return None

    # If cookie was present but invalid, don't wait for first-message
    if cookie_token:
        await websocket.close(code=4001, reason="Invalid cookie token")
        return None

    # --- First-message auth ---------------------------------------------------
    try:
        raw = await asyncio.wait_for(websocket.receive_text(), timeout=_AUTH_TIMEOUT)
        message = json.loads(raw)

        if message.get("event") != "auth" or not message.get("token"):
            await websocket.close(code=4001, reason="First message must be {\"event\":\"auth\",\"token\":\"...\"}")
            return None

        auth = await validate_ws_token(message["token"])
        if not auth:
            await websocket.close(code=4001, reason="Invalid token")
            return None

        await websocket.send_json({"event": "auth_success", "data": {"user_id": auth["user_id"]}})
        return auth

    except asyncio.TimeoutError:
        try:
            await websocket.close(code=4001, reason="Authentication timeout")
        except Exception as e:
            logger.debug(f"WebSocket close failed: {e}")
        return None
    except (json.JSONDecodeError, WebSocketDisconnect):
        try:
            await websocket.close(code=4001, reason="Invalid auth message")
        except Exception as e:
            logger.debug(f"WebSocket close failed: {e}")
        return None


@router.get("/")
@limiter.limit("60/minute")
def get_ws_root(request: Request):
    """WebSocket endpoints status."""
    return {"module": "websocket", "status": "active", "endpoints": ["/venue/{venue_id}", "/kitchen/{venue_id}", "/hardware/{venue_id}"], "stats_endpoint": "/stats"}


@router.websocket("/venue/{venue_id}")
async def venue_websocket(
    websocket: WebSocket,
    venue_id: int,
    channels: Optional[str] = Query(None, description="Comma-separated channels"),
    token: Optional[str] = Query(None, description="Auth token (legacy, prefer first-message auth)")
):
    """
    Main WebSocket endpoint for venue-wide real-time updates.

    Auth: Send ``{"event":"auth","token":"<jwt>"}`` as first message, or pass
    ``?token=<jwt>`` query param (legacy).

    Channels:
    - general: All venue notifications
    - kitchen: Kitchen orders and updates
    - bar: Bar orders, keg updates
    - inventory: Stock alerts, RFID events
    - hardware: Device status, sensor readings
    """
    # Parse channels
    channel_list = channels.split(",") if channels else ["general"]

    # Authenticate (first-message or legacy query-string)
    auth = await authenticate_ws(websocket, query_token=token)
    if not auth:
        return

    # Verify user belongs to this venue
    if auth["venue_id"] != venue_id:
        await websocket.close(code=4003, reason="Not authorized for this venue")
        return

    await manager.connect(
        websocket=websocket,
        venue_id=venue_id,
        channels=channel_list,
        user_id=auth["user_id"]
    )

    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                event_type = message.get("event")

                if event_type == "ping":
                    # Respond to ping
                    await manager.send_personal(websocket, WebSocketMessage(
                        event=EventType.PONG,
                        data={"timestamp": message.get("timestamp")},
                        venue_id=venue_id
                    ))

                elif event_type == "subscribe":
                    # Subscribe to additional channels
                    new_channels = message.get("channels", [])
                    for channel in new_channels:
                        channel_key = f"{venue_id}:{channel}"
                        if channel_key not in manager.channel_connections:
                            manager.channel_connections[channel_key] = set()
                        manager.channel_connections[channel_key].add(websocket)

                    await manager.send_personal(websocket, WebSocketMessage(
                        event="subscribed",
                        data={"channels": new_channels},
                        venue_id=venue_id
                    ))

                elif event_type == "unsubscribe":
                    # Unsubscribe from channels
                    remove_channels = message.get("channels", [])
                    for channel in remove_channels:
                        channel_key = f"{venue_id}:{channel}"
                        if channel_key in manager.channel_connections:
                            manager.channel_connections[channel_key].discard(websocket)

                    await manager.send_personal(websocket, WebSocketMessage(
                        event="unsubscribed",
                        data={"channels": remove_channels},
                        venue_id=venue_id
                    ))

            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received: {data[:100]}")

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info(f"WebSocket disconnected: venue={venue_id}")


@router.websocket("/kitchen/{venue_id}")
async def kitchen_websocket(
    websocket: WebSocket,
    venue_id: int,
    station: Optional[str] = Query(None, description="Kitchen station"),
    token: Optional[str] = Query(None, description="Auth token (legacy, prefer first-message auth)")
):
    """
    WebSocket for kitchen display system.
    Receives new orders and order updates.
    """
    auth = await authenticate_ws(websocket, query_token=token)
    if not auth:
        return

    channels = ["kitchen"]
    if station:
        channels.append(f"station:{station}")

    await manager.connect(
        websocket=websocket,
        venue_id=venue_id,
        channels=channels
    )

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("event") == "bump":
                # Kitchen bumped an order
                order_id = message.get("order_id")
                # Broadcast to venue that order is ready
                from app.services.websocket_service import emit_order_update
                await emit_order_update(
                    venue_id=venue_id,
                    order_id=order_id,
                    status="ready",
                    station=station
                )

            elif message.get("event") == "ping":
                await manager.send_personal(websocket, WebSocketMessage(
                    event=EventType.PONG,
                    data={},
                    venue_id=venue_id
                ))

    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.websocket("/hardware/{venue_id}")
async def hardware_websocket(
    websocket: WebSocket,
    venue_id: int,
    device_types: Optional[str] = Query(None, description="rfid,scale,flow_meter,temperature"),
    token: Optional[str] = Query(None, description="Auth token (legacy, prefer first-message auth)")
):
    """
    WebSocket for hardware monitoring dashboard.
    Receives sensor readings and device status updates.
    """
    auth = await authenticate_ws(websocket, query_token=token)
    if not auth:
        return

    channels = ["hardware", "inventory"]
    if device_types:
        for dt in device_types.split(","):
            channels.append(f"device:{dt}")

    await manager.connect(
        websocket=websocket,
        venue_id=venue_id,
        channels=channels
    )

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("event") == "ping":
                await manager.send_personal(websocket, WebSocketMessage(
                    event=EventType.PONG,
                    data={"stats": manager.get_stats()},
                    venue_id=venue_id
                ))

    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.get("/stats")
@limiter.limit("60/minute")
async def get_websocket_stats(request: Request):
    """Get WebSocket connection statistics."""
    return manager.get_stats()


@router.post("/broadcast/{venue_id}")
@limiter.limit("30/minute")
async def broadcast_message(
    request: Request,
    venue_id: int,
    event: str,
    data: dict,
    channel: Optional[str] = None,
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Broadcast a message to venue connections.
    Requires authentication.
    """
    # Verify user has access to venue
    if current_user.venue_id != venue_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized for this venue")
    message = WebSocketMessage(
        event=event,
        data=data,
        venue_id=venue_id
    )

    if channel:
        await manager.broadcast_channel(venue_id, channel, message)
    else:
        await manager.broadcast_venue(venue_id, message)

    return {"status": "broadcast_sent", "venue_id": venue_id, "channel": channel}


# =============================================================================
# GAP FEATURES WEBSOCKET ENDPOINTS
# =============================================================================

@router.websocket("/chat/{venue_id}")
async def chat_websocket(
    websocket: WebSocket,
    venue_id: int,
    channel_id: Optional[str] = Query(None, description="Chat channel ID"),
    token: Optional[str] = Query(None, description="Auth token (legacy, prefer first-message auth)")
):
    """
    WebSocket for team chat.
    Handles real-time messaging, typing indicators, and read receipts.
    """
    auth = await authenticate_ws(websocket, query_token=token)
    if not auth:
        return

    channels = ["general"]
    if channel_id:
        channels.append(f"chat:{channel_id}")

    await manager.connect(
        websocket=websocket,
        venue_id=venue_id,
        channels=channels,
        user_id=auth["user_id"]
    )

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            event_type = message.get("event")

            if event_type == "ping":
                await manager.send_personal(websocket, WebSocketMessage(
                    event=EventType.PONG,
                    data={},
                    venue_id=venue_id
                ))

            elif event_type == "typing":
                # Broadcast typing indicator
                from app.services.websocket_service import emit_chat_typing
                await emit_chat_typing(
                    venue_id=venue_id,
                    channel_id=message.get("channel_id", channel_id),
                    user_id=str(auth["user_id"]),
                    user_name=message.get("user_name", "Unknown"),
                    is_typing=message.get("is_typing", True)
                )

            elif event_type == "read":
                # Mark messages as read
                from app.services.websocket_service import WebSocketMessage as WSMsg
                await manager.broadcast_channel(
                    venue_id,
                    f"chat:{message.get('channel_id', channel_id)}",
                    WSMsg(
                        event="chat_read_receipt",
                        data={
                            "channel_id": message.get("channel_id", channel_id),
                            "user_id": str(auth["user_id"]),
                            "last_read_id": message.get("last_read_id")
                        }
                    )
                )

            elif event_type == "join_channel":
                # Join a chat channel
                new_channel = message.get("channel_id")
                if new_channel:
                    channel_key = f"{venue_id}:chat:{new_channel}"
                    if channel_key not in manager.channel_connections:
                        manager.channel_connections[channel_key] = set()
                    manager.channel_connections[channel_key].add(websocket)

                    await manager.send_personal(websocket, WebSocketMessage(
                        event="channel_joined",
                        data={"channel_id": new_channel},
                        venue_id=venue_id
                    ))

            elif event_type == "leave_channel":
                # Leave a chat channel
                leave_channel = message.get("channel_id")
                if leave_channel:
                    channel_key = f"{venue_id}:chat:{leave_channel}"
                    if channel_key in manager.channel_connections:
                        manager.channel_connections[channel_key].discard(websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.websocket("/integrations/{venue_id}")
async def integrations_websocket(
    websocket: WebSocket,
    venue_id: int,
    token: Optional[str] = Query(None, description="Auth token (legacy, prefer first-message auth)")
):
    """
    WebSocket for integration sync status updates.
    Receives real-time updates on sync progress.
    """
    auth = await authenticate_ws(websocket, query_token=token)
    if not auth:
        return

    await manager.connect(
        websocket=websocket,
        venue_id=venue_id,
        channels=["integrations"],
        user_id=auth["user_id"]
    )

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("event") == "ping":
                await manager.send_personal(websocket, WebSocketMessage(
                    event=EventType.PONG,
                    data={},
                    venue_id=venue_id
                ))

    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.websocket("/experiments/{venue_id}")
async def experiments_websocket(
    websocket: WebSocket,
    venue_id: int,
    token: Optional[str] = Query(None, description="Auth token (legacy, prefer first-message auth)")
):
    """
    WebSocket for A/B experiment updates.
    Receives real-time updates on experiment status and significance.
    """
    auth = await authenticate_ws(websocket, query_token=token)
    if not auth:
        return

    await manager.connect(
        websocket=websocket,
        venue_id=venue_id,
        channels=["experiments"],
        user_id=auth["user_id"]
    )

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("event") == "ping":
                await manager.send_personal(websocket, WebSocketMessage(
                    event=EventType.PONG,
                    data={},
                    venue_id=venue_id
                ))

    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.websocket("/compliance/{venue_id}")
async def compliance_websocket(
    websocket: WebSocket,
    venue_id: int,
    token: Optional[str] = Query(None, description="Auth token (legacy, prefer first-message auth)")
):
    """
    WebSocket for labor compliance alerts.
    Receives real-time alerts for violations, break reminders, overtime warnings.
    """
    auth = await authenticate_ws(websocket, query_token=token)
    if not auth:
        return

    await manager.connect(
        websocket=websocket,
        venue_id=venue_id,
        channels=["compliance"],
        user_id=auth["user_id"]
    )

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("event") == "ping":
                await manager.send_personal(websocket, WebSocketMessage(
                    event=EventType.PONG,
                    data={},
                    venue_id=venue_id
                ))

    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.websocket("/terminal/{venue_id}/{session_id}")
async def terminal_websocket(
    websocket: WebSocket,
    venue_id: int,
    session_id: str,
    token: Optional[str] = Query(None, description="Auth token (legacy, prefer first-message auth)")
):
    """
    WebSocket for POS terminal session.
    Handles payment terminal commands and status updates.
    """
    auth = await authenticate_ws(websocket, query_token=token)
    if not auth:
        return

    await manager.connect(
        websocket=websocket,
        venue_id=venue_id,
        channels=["terminal", f"session:{session_id}"],
        user_id=auth["user_id"]
    )

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            event_type = message.get("event")

            if event_type == "ping":
                await manager.send_personal(websocket, WebSocketMessage(
                    event=EventType.PONG,
                    data={},
                    venue_id=venue_id
                ))

            elif event_type == "command":
                # Terminal command received
                from app.services.websocket_service import emit_terminal_command_result
                command_type = message.get("command_type")
                command_id = message.get("command_id")

                # Acknowledge command receipt
                await manager.send_personal(websocket, WebSocketMessage(
                    event="command_acknowledged",
                    data={
                        "command_id": command_id,
                        "command_type": command_type
                    },
                    venue_id=venue_id
                ))

    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.websocket("/payments/{venue_id}")
async def payments_websocket(
    websocket: WebSocket,
    venue_id: int,
    token: Optional[str] = Query(None, description="Auth token (legacy, prefer first-message auth)")
):
    """
    WebSocket for payment status updates.
    Handles BNPL transaction status, refunds, etc.
    """
    auth = await authenticate_ws(websocket, query_token=token)
    if not auth:
        return

    await manager.connect(
        websocket=websocket,
        venue_id=venue_id,
        channels=["payments"],
        user_id=auth["user_id"]
    )

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("event") == "ping":
                await manager.send_personal(websocket, WebSocketMessage(
                    event=EventType.PONG,
                    data={},
                    venue_id=venue_id
                ))

    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.websocket("/mobile/{venue_id}/{device_id}")
async def mobile_websocket(
    websocket: WebSocket,
    venue_id: int,
    device_id: str,
    token: Optional[str] = Query(None, description="Auth token (legacy, prefer first-message auth)")
):
    """
    WebSocket for mobile device sync.
    Handles offline sync status and push notification delivery.
    """
    auth = await authenticate_ws(websocket, query_token=token)
    if not auth:
        return

    await manager.connect(
        websocket=websocket,
        venue_id=venue_id,
        channels=["mobile", f"device:{device_id}", f"user:{auth['user_id']}"],
        user_id=auth["user_id"]
    )

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            event_type = message.get("event")

            if event_type == "ping":
                await manager.send_personal(websocket, WebSocketMessage(
                    event=EventType.PONG,
                    data={},
                    venue_id=venue_id
                ))

            elif event_type == "sync_request":
                # Mobile device requesting sync
                from app.services.websocket_service import emit_sync_status
                await emit_sync_status(
                    venue_id=venue_id,
                    device_id=device_id,
                    sync_type=message.get("sync_type", "incremental"),
                    status="started"
                )

            elif event_type == "heartbeat":
                # Update device last seen
                await manager.send_personal(websocket, WebSocketMessage(
                    event="heartbeat_ack",
                    data={"device_id": device_id},
                    venue_id=venue_id
                ))

    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.websocket("/developer/{venue_id}")
async def developer_websocket(
    websocket: WebSocket,
    venue_id: int,
    token: Optional[str] = Query(None, description="Auth token (legacy, prefer first-message auth)")
):
    """
    WebSocket for developer portal.
    Receives webhook delivery status and API usage alerts.
    """
    auth = await authenticate_ws(websocket, query_token=token)
    if not auth:
        return

    await manager.connect(
        websocket=websocket,
        venue_id=venue_id,
        channels=["developer"],
        user_id=auth["user_id"]
    )

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("event") == "ping":
                await manager.send_personal(websocket, WebSocketMessage(
                    event=EventType.PONG,
                    data={},
                    venue_id=venue_id
                ))

    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.websocket("/reviews/{venue_id}")
async def reviews_websocket(
    websocket: WebSocket,
    venue_id: int,
    token: Optional[str] = Query(None, description="Auth token (legacy, prefer first-message auth)")
):
    """
    WebSocket for review/reputation management.
    Receives new review notifications and response alerts.
    """
    auth = await authenticate_ws(websocket, query_token=token)
    if not auth:
        return

    await manager.connect(
        websocket=websocket,
        venue_id=venue_id,
        channels=["reviews"],
        user_id=auth["user_id"]
    )

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("event") == "ping":
                await manager.send_personal(websocket, WebSocketMessage(
                    event=EventType.PONG,
                    data={},
                    venue_id=venue_id
                ))

    except WebSocketDisconnect:
        manager.disconnect(websocket)

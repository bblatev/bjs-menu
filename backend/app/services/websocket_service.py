"""
WebSocket Real-time Service
Live updates for hardware data, kitchen orders, and alerts
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Set, Any, List
from dataclasses import dataclass, asdict
from enum import Enum
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """WebSocket event types"""
    # Connection events
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    PING = "ping"
    PONG = "pong"

    # Hardware events
    RFID_SCAN = "rfid_scan"
    RFID_MOVEMENT = "rfid_movement"
    RFID_ALERT = "rfid_alert"

    KEG_UPDATE = "keg_update"
    KEG_LOW = "keg_low"
    KEG_EMPTY = "keg_empty"

    TANK_UPDATE = "tank_update"
    TANK_LOW = "tank_low"

    SCALE_READING = "scale_reading"
    FLOW_READING = "flow_reading"
    TEMPERATURE_ALERT = "temperature_alert"

    # Kitchen events
    NEW_ORDER = "new_order"
    ORDER_UPDATE = "order_update"
    ORDER_READY = "order_ready"
    TICKET_BUMP = "ticket_bump"

    # Stock events
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"
    STOCK_RECEIVED = "stock_received"

    # General alerts
    ALERT = "alert"
    NOTIFICATION = "notification"

    # Team Chat events (Gap Features)
    CHAT_MESSAGE = "chat_message"
    CHAT_MESSAGE_EDITED = "chat_message_edited"
    CHAT_MESSAGE_DELETED = "chat_message_deleted"
    CHAT_TYPING = "chat_typing"
    CHAT_READ_RECEIPT = "chat_read_receipt"
    ANNOUNCEMENT = "announcement"
    ANNOUNCEMENT_ACK = "announcement_ack"

    # A/B Testing events
    EXPERIMENT_STARTED = "experiment_started"
    EXPERIMENT_PAUSED = "experiment_paused"
    EXPERIMENT_COMPLETED = "experiment_completed"
    EXPERIMENT_SIGNIFICANCE = "experiment_significance"

    # Developer Portal events
    API_KEY_CREATED = "api_key_created"
    API_KEY_REVOKED = "api_key_revoked"
    APP_INSTALLED = "app_installed"
    APP_UNINSTALLED = "app_uninstalled"
    WEBHOOK_DELIVERED = "webhook_delivered"
    WEBHOOK_FAILED = "webhook_failed"

    # Integration events
    INTEGRATION_CONNECTED = "integration_connected"
    INTEGRATION_DISCONNECTED = "integration_disconnected"
    INTEGRATION_SYNC_STARTED = "integration_sync_started"
    INTEGRATION_SYNC_COMPLETED = "integration_sync_completed"
    INTEGRATION_SYNC_FAILED = "integration_sync_failed"

    # Hardware SDK events (Gap Features Phase 8)
    DEVICE_CONNECTED = "device_connected"
    DEVICE_DISCONNECTED = "device_disconnected"
    DEVICE_ERROR = "device_error"
    TERMINAL_COMMAND_RESULT = "terminal_command_result"
    PRINTER_STATUS = "printer_status"
    DRAWER_STATUS = "drawer_status"

    # BNPL events
    BNPL_SESSION_CREATED = "bnpl_session_created"
    BNPL_AUTHORIZED = "bnpl_authorized"
    BNPL_CAPTURED = "bnpl_captured"
    BNPL_FAILED = "bnpl_failed"
    BNPL_REFUNDED = "bnpl_refunded"

    # Labor Compliance events
    COMPLIANCE_VIOLATION = "compliance_violation"
    BREAK_REMINDER = "break_reminder"
    OVERTIME_WARNING = "overtime_warning"

    # Review/Reputation events
    REVIEW_REQUEST_SENT = "review_request_sent"
    REVIEW_RECEIVED = "review_received"
    REVIEW_RESPONSE_NEEDED = "review_response_needed"

    # Mobile/Offline events
    SYNC_STARTED = "sync_started"
    SYNC_COMPLETED = "sync_completed"
    SYNC_CONFLICT = "sync_conflict"
    PUSH_NOTIFICATION = "push_notification"


@dataclass
class WebSocketMessage:
    """Standard WebSocket message format"""
    event: str
    data: Dict[str, Any]
    timestamp: str = None
    venue_id: int = None

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()

    def to_json(self) -> str:
        return json.dumps(asdict(self))


class ConnectionManager:
    """
    Manages WebSocket connections and message broadcasting.
    Supports channels for targeted message delivery.
    """

    def __init__(self):
        # Active connections by venue
        self.venue_connections: Dict[int, Set[WebSocket]] = {}

        # Connections by channel (e.g., "kitchen", "bar", "stock")
        self.channel_connections: Dict[str, Set[WebSocket]] = {}

        # Connection metadata
        self.connection_info: Dict[WebSocket, Dict] = {}

        # Message queue for offline clients
        self.message_queue: Dict[int, List[WebSocketMessage]] = {}

        # Statistics
        self.stats = {
            "total_connections": 0,
            "messages_sent": 0,
            "messages_broadcast": 0
        }

    async def connect(
        self,
        websocket: WebSocket,
        venue_id: int,
        channels: List[str] = None,
        user_id: int = None
    ):
        """Accept a new WebSocket connection"""
        await websocket.accept()

        # Add to venue connections
        if venue_id not in self.venue_connections:
            self.venue_connections[venue_id] = set()
        self.venue_connections[venue_id].add(websocket)

        # Add to channel connections
        channels = channels or ["general"]
        for channel in channels:
            channel_key = f"{venue_id}:{channel}"
            if channel_key not in self.channel_connections:
                self.channel_connections[channel_key] = set()
            self.channel_connections[channel_key].add(websocket)

        # Store connection info
        self.connection_info[websocket] = {
            "venue_id": venue_id,
            "user_id": user_id,
            "channels": channels,
            "connected_at": datetime.utcnow().isoformat()
        }

        self.stats["total_connections"] += 1

        # Send welcome message
        await self.send_personal(websocket, WebSocketMessage(
            event=EventType.CONNECTED,
            data={
                "message": "Connected to real-time updates",
                "channels": channels,
                "venue_id": venue_id
            },
            venue_id=venue_id
        ))

        # Send queued messages
        if venue_id in self.message_queue:
            for msg in self.message_queue[venue_id][-50:]:  # Last 50
                await self.send_personal(websocket, msg)
            self.message_queue[venue_id] = []

        logger.info(f"WebSocket connected: venue={venue_id}, channels={channels}")

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        info = self.connection_info.get(websocket, {})
        venue_id = info.get("venue_id")
        channels = info.get("channels", [])

        # Remove from venue connections
        if venue_id and venue_id in self.venue_connections:
            self.venue_connections[venue_id].discard(websocket)
            if not self.venue_connections[venue_id]:
                del self.venue_connections[venue_id]

        # Remove from channel connections
        for channel in channels:
            channel_key = f"{venue_id}:{channel}"
            if channel_key in self.channel_connections:
                self.channel_connections[channel_key].discard(websocket)
                if not self.channel_connections[channel_key]:
                    del self.channel_connections[channel_key]

        # Remove connection info
        if websocket in self.connection_info:
            del self.connection_info[websocket]

        logger.info(f"WebSocket disconnected: venue={venue_id}")

    async def send_personal(self, websocket: WebSocket, message: WebSocketMessage):
        """Send message to a specific connection"""
        try:
            await websocket.send_text(message.to_json())
            self.stats["messages_sent"] += 1
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            self.disconnect(websocket)

    async def broadcast_venue(self, venue_id: int, message: WebSocketMessage):
        """Broadcast message to all connections for a venue"""
        message.venue_id = venue_id
        connections = self.venue_connections.get(venue_id, set()).copy()

        if not connections:
            # Queue message for later
            if venue_id not in self.message_queue:
                self.message_queue[venue_id] = []
            self.message_queue[venue_id].append(message)
            # Keep only last 100 messages
            self.message_queue[venue_id] = self.message_queue[venue_id][-100:]
            return

        disconnected = []
        for websocket in connections:
            try:
                await websocket.send_text(message.to_json())
            except Exception:
                disconnected.append(websocket)

        # Clean up disconnected
        for ws in disconnected:
            self.disconnect(ws)

        self.stats["messages_broadcast"] += 1

    async def broadcast_channel(
        self,
        venue_id: int,
        channel: str,
        message: WebSocketMessage
    ):
        """Broadcast message to a specific channel"""
        message.venue_id = venue_id
        channel_key = f"{venue_id}:{channel}"
        connections = self.channel_connections.get(channel_key, set()).copy()

        disconnected = []
        for websocket in connections:
            try:
                await websocket.send_text(message.to_json())
            except Exception:
                disconnected.append(websocket)

        for ws in disconnected:
            self.disconnect(ws)

    def get_stats(self) -> Dict:
        """Get connection statistics"""
        return {
            **self.stats,
            "active_venues": len(self.venue_connections),
            "active_connections": sum(len(c) for c in self.venue_connections.values()),
            "active_channels": len(self.channel_connections)
        }


# Global connection manager instance
manager = ConnectionManager()


# =============================================================================
# EVENT EMITTERS
# =============================================================================

async def emit_rfid_scan(
    venue_id: int,
    tag_id: str,
    tag_name: str,
    zone: str,
    movement: bool = False,
    previous_zone: str = None
):
    """Emit RFID scan event"""
    event = EventType.RFID_MOVEMENT if movement else EventType.RFID_SCAN

    await manager.broadcast_channel(venue_id, "inventory", WebSocketMessage(
        event=event,
        data={
            "tag_id": tag_id,
            "tag_name": tag_name,
            "zone": zone,
            "movement": movement,
            "previous_zone": previous_zone
        }
    ))


async def emit_rfid_alert(
    venue_id: int,
    alert_type: str,
    tag_id: str,
    message: str
):
    """Emit RFID alert event"""
    await manager.broadcast_venue(venue_id, WebSocketMessage(
        event=EventType.RFID_ALERT,
        data={
            "alert_type": alert_type,
            "tag_id": tag_id,
            "message": message,
            "priority": "high" if alert_type == "expiry_warning" else "normal"
        }
    ))


async def emit_keg_update(
    venue_id: int,
    keg_id: str,
    product_name: str,
    fill_percentage: float,
    status: str,
    tap_number: int = None
):
    """Emit keg status update"""
    event = EventType.KEG_EMPTY if status == "empty" else (
        EventType.KEG_LOW if status == "low" else EventType.KEG_UPDATE
    )

    await manager.broadcast_channel(venue_id, "bar", WebSocketMessage(
        event=event,
        data={
            "keg_id": keg_id,
            "product_name": product_name,
            "fill_percentage": fill_percentage,
            "status": status,
            "tap_number": tap_number
        }
    ))


async def emit_tank_update(
    venue_id: int,
    tank_id: str,
    tank_name: str,
    fill_percentage: float,
    status: str
):
    """Emit tank level update"""
    event = EventType.TANK_LOW if status in ["low", "critical"] else EventType.TANK_UPDATE

    await manager.broadcast_channel(venue_id, "inventory", WebSocketMessage(
        event=event,
        data={
            "tank_id": tank_id,
            "tank_name": tank_name,
            "fill_percentage": fill_percentage,
            "status": status
        }
    ))


async def emit_temperature_alert(
    venue_id: int,
    device_id: int,
    location: str,
    temperature: float,
    threshold: float,
    alert_type: str
):
    """Emit temperature alert for HACCP compliance"""
    await manager.broadcast_venue(venue_id, WebSocketMessage(
        event=EventType.TEMPERATURE_ALERT,
        data={
            "device_id": device_id,
            "location": location,
            "temperature": temperature,
            "threshold": threshold,
            "alert_type": alert_type,
            "priority": "critical"
        }
    ))


async def emit_new_order(
    venue_id: int,
    order_id: int,
    table_number: str,
    items: List[Dict],
    station: str = None
):
    """Emit new order for kitchen/bar display"""
    channel = station.lower() if station else "kitchen"

    await manager.broadcast_channel(venue_id, channel, WebSocketMessage(
        event=EventType.NEW_ORDER,
        data={
            "order_id": order_id,
            "table_number": table_number,
            "items": items,
            "station": station
        }
    ))


async def emit_order_update(
    venue_id: int,
    order_id: int,
    status: str,
    station: str = None
):
    """Emit order status update"""
    event = EventType.ORDER_READY if status == "ready" else EventType.ORDER_UPDATE

    await manager.broadcast_channel(venue_id, "kitchen", WebSocketMessage(
        event=event,
        data={
            "order_id": order_id,
            "status": status,
            "station": station
        }
    ))


async def emit_stock_alert(
    venue_id: int,
    item_id: int,
    item_name: str,
    quantity: float,
    threshold: float,
    alert_type: str
):
    """Emit stock level alert"""
    event = EventType.OUT_OF_STOCK if quantity <= 0 else EventType.LOW_STOCK

    await manager.broadcast_channel(venue_id, "inventory", WebSocketMessage(
        event=event,
        data={
            "item_id": item_id,
            "item_name": item_name,
            "quantity": quantity,
            "threshold": threshold,
            "alert_type": alert_type
        }
    ))


async def emit_notification(
    venue_id: int,
    title: str,
    message: str,
    priority: str = "normal",
    action_url: str = None
):
    """Emit general notification"""
    await manager.broadcast_venue(venue_id, WebSocketMessage(
        event=EventType.NOTIFICATION,
        data={
            "title": title,
            "message": message,
            "priority": priority,
            "action_url": action_url
        }
    ))


# =============================================================================
# BACKGROUND TASKS
# =============================================================================

class RealtimeMonitor:
    """
    Background task for monitoring and emitting real-time events.
    Polls database for changes and emits WebSocket events.
    """

    def __init__(self):
        self.running = False
        self.poll_interval = 5  # seconds

    async def start(self, db_session_factory):
        """Start the real-time monitor"""
        self.running = True
        logger.info("Real-time monitor started")

        while self.running:
            try:
                async with db_session_factory() as db:
                    await self._check_low_kegs(db)
                    await self._check_low_tanks(db)
                    await self._check_expiring_items(db)
            except Exception as e:
                logger.error(f"Monitor error: {e}")

            await asyncio.sleep(self.poll_interval)

    def stop(self):
        """Stop the monitor"""
        self.running = False
        logger.info("Real-time monitor stopped")

    async def _check_low_kegs(self, db):
        """Check for low/empty kegs"""
        from app.models.advanced_features_v9 import KegTracking

        kegs = db.query(KegTracking).filter(
            KegTracking.status.in_(["low", "empty"])
        ).all()

        for keg in kegs:
            await emit_keg_update(
                venue_id=keg.venue_id,
                keg_id=keg.keg_id,
                product_name=keg.product_name,
                fill_percentage=(keg.current_volume_ml / keg.initial_volume_ml * 100) if keg.initial_volume_ml > 0 else 0,
                status=keg.status,
                tap_number=keg.tap_number
            )

    async def _check_low_tanks(self, db):
        """Check for low tanks"""
        from app.models.advanced_features_v9 import BulkTankLevel

        tanks = db.query(BulkTankLevel).filter(
            BulkTankLevel.status.in_(["low", "critical"])
        ).all()

        for tank in tanks:
            await emit_tank_update(
                venue_id=tank.venue_id,
                tank_id=tank.tank_id,
                tank_name=tank.tank_name,
                fill_percentage=tank.fill_percentage,
                status=tank.status
            )

    async def _check_expiring_items(self, db):
        """Check for expiring RFID-tagged items"""
        from app.models.advanced_features_v9 import RFIDTag
        from datetime import timedelta

        threshold = datetime.utcnow() + timedelta(days=3)

        expiring = db.query(RFIDTag).filter(
            RFIDTag.is_active == True,
            RFIDTag.expiry_date.isnot(None),
            RFIDTag.expiry_date <= threshold
        ).limit(20).all()

        for tag in expiring:
            await emit_rfid_alert(
                venue_id=tag.venue_id,
                alert_type="expiry_warning",
                tag_id=tag.tag_id,
                message=f"{tag.tag_name} expires on {tag.expiry_date.strftime('%Y-%m-%d')}"
            )


# Global monitor instance
monitor = RealtimeMonitor()


# =============================================================================
# GAP FEATURES EVENT EMITTERS
# =============================================================================

# ==================== TEAM CHAT EVENTS ====================

async def emit_chat_message(
    venue_id: int,
    channel_id: str,
    message_id: str,
    sender_id: str,
    sender_name: str,
    content: str,
    message_type: str = "text",
    mentions: List[str] = None,
    reply_to_id: str = None
):
    """Emit a new chat message."""
    await manager.broadcast_channel(venue_id, f"chat:{channel_id}", WebSocketMessage(
        event=EventType.CHAT_MESSAGE,
        data={
            "channel_id": channel_id,
            "message_id": message_id,
            "sender_id": sender_id,
            "sender_name": sender_name,
            "content": content,
            "message_type": message_type,
            "mentions": mentions or [],
            "reply_to_id": reply_to_id
        }
    ))


async def emit_chat_message_edited(
    venue_id: int,
    channel_id: str,
    message_id: str,
    new_content: str,
    edited_at: str
):
    """Emit a message edit event."""
    await manager.broadcast_channel(venue_id, f"chat:{channel_id}", WebSocketMessage(
        event=EventType.CHAT_MESSAGE_EDITED,
        data={
            "channel_id": channel_id,
            "message_id": message_id,
            "new_content": new_content,
            "edited_at": edited_at
        }
    ))


async def emit_chat_message_deleted(
    venue_id: int,
    channel_id: str,
    message_id: str
):
    """Emit a message deletion event."""
    await manager.broadcast_channel(venue_id, f"chat:{channel_id}", WebSocketMessage(
        event=EventType.CHAT_MESSAGE_DELETED,
        data={
            "channel_id": channel_id,
            "message_id": message_id
        }
    ))


async def emit_chat_typing(
    venue_id: int,
    channel_id: str,
    user_id: str,
    user_name: str,
    is_typing: bool = True
):
    """Emit typing indicator."""
    await manager.broadcast_channel(venue_id, f"chat:{channel_id}", WebSocketMessage(
        event=EventType.CHAT_TYPING,
        data={
            "channel_id": channel_id,
            "user_id": user_id,
            "user_name": user_name,
            "is_typing": is_typing
        }
    ))


async def emit_announcement(
    venue_id: int,
    announcement_id: str,
    title: str,
    content: str,
    priority: str,
    created_by: str,
    require_acknowledgment: bool
):
    """Emit a team announcement."""
    await manager.broadcast_venue(venue_id, WebSocketMessage(
        event=EventType.ANNOUNCEMENT,
        data={
            "announcement_id": announcement_id,
            "title": title,
            "content": content,
            "priority": priority,
            "created_by": created_by,
            "require_acknowledgment": require_acknowledgment
        }
    ))


# ==================== A/B TESTING EVENTS ====================

async def emit_experiment_started(
    venue_id: int,
    experiment_id: str,
    experiment_name: str,
    experiment_type: str,
    variants: List[Dict]
):
    """Emit experiment started event."""
    await manager.broadcast_channel(venue_id, "experiments", WebSocketMessage(
        event=EventType.EXPERIMENT_STARTED,
        data={
            "experiment_id": experiment_id,
            "experiment_name": experiment_name,
            "experiment_type": experiment_type,
            "variants": variants
        }
    ))


async def emit_experiment_completed(
    venue_id: int,
    experiment_id: str,
    experiment_name: str,
    winner_variant: str,
    results: Dict
):
    """Emit experiment completed event."""
    await manager.broadcast_channel(venue_id, "experiments", WebSocketMessage(
        event=EventType.EXPERIMENT_COMPLETED,
        data={
            "experiment_id": experiment_id,
            "experiment_name": experiment_name,
            "winner_variant": winner_variant,
            "results": results
        }
    ))


async def emit_experiment_significance(
    venue_id: int,
    experiment_id: str,
    experiment_name: str,
    is_significant: bool,
    confidence_level: float
):
    """Emit when an experiment reaches statistical significance."""
    await manager.broadcast_channel(venue_id, "experiments", WebSocketMessage(
        event=EventType.EXPERIMENT_SIGNIFICANCE,
        data={
            "experiment_id": experiment_id,
            "experiment_name": experiment_name,
            "is_significant": is_significant,
            "confidence_level": confidence_level
        }
    ))


# ==================== DEVELOPER PORTAL EVENTS ====================

async def emit_api_key_created(
    venue_id: int,
    developer_id: str,
    key_name: str,
    scopes: List[str]
):
    """Emit API key created event."""
    await manager.broadcast_channel(venue_id, "developer", WebSocketMessage(
        event=EventType.API_KEY_CREATED,
        data={
            "developer_id": developer_id,
            "key_name": key_name,
            "scopes": scopes
        }
    ))


async def emit_app_installed(
    venue_id: int,
    app_id: str,
    app_name: str,
    installed_by: str
):
    """Emit app installed event."""
    await manager.broadcast_venue(venue_id, WebSocketMessage(
        event=EventType.APP_INSTALLED,
        data={
            "app_id": app_id,
            "app_name": app_name,
            "installed_by": installed_by
        }
    ))


async def emit_webhook_delivery(
    venue_id: int,
    webhook_id: str,
    endpoint_url: str,
    event_type: str,
    success: bool,
    response_status: int = None,
    error_message: str = None
):
    """Emit webhook delivery status."""
    event = EventType.WEBHOOK_DELIVERED if success else EventType.WEBHOOK_FAILED
    await manager.broadcast_channel(venue_id, "developer", WebSocketMessage(
        event=event,
        data={
            "webhook_id": webhook_id,
            "endpoint_url": endpoint_url,
            "event_type": event_type,
            "success": success,
            "response_status": response_status,
            "error_message": error_message
        }
    ))


# ==================== INTEGRATION EVENTS ====================

async def emit_integration_connected(
    venue_id: int,
    integration_type: str,
    integration_name: str,
    connected_by: str
):
    """Emit integration connected event."""
    await manager.broadcast_venue(venue_id, WebSocketMessage(
        event=EventType.INTEGRATION_CONNECTED,
        data={
            "integration_type": integration_type,
            "integration_name": integration_name,
            "connected_by": connected_by
        }
    ))


async def emit_integration_sync_status(
    venue_id: int,
    integration_type: str,
    sync_type: str,  # 'full', 'incremental'
    status: str,  # 'started', 'completed', 'failed'
    records_synced: int = 0,
    error_message: str = None
):
    """Emit integration sync status."""
    if status == "started":
        event = EventType.INTEGRATION_SYNC_STARTED
    elif status == "completed":
        event = EventType.INTEGRATION_SYNC_COMPLETED
    else:
        event = EventType.INTEGRATION_SYNC_FAILED

    await manager.broadcast_channel(venue_id, "integrations", WebSocketMessage(
        event=event,
        data={
            "integration_type": integration_type,
            "sync_type": sync_type,
            "status": status,
            "records_synced": records_synced,
            "error_message": error_message
        }
    ))


# ==================== HARDWARE SDK EVENTS ====================

async def emit_device_status(
    venue_id: int,
    device_id: str,
    device_type: str,
    status: str,  # 'connected', 'disconnected', 'error'
    device_name: str = None,
    error_message: str = None
):
    """Emit hardware device status change."""
    if status == "connected":
        event = EventType.DEVICE_CONNECTED
    elif status == "disconnected":
        event = EventType.DEVICE_DISCONNECTED
    else:
        event = EventType.DEVICE_ERROR

    await manager.broadcast_channel(venue_id, "hardware", WebSocketMessage(
        event=event,
        data={
            "device_id": device_id,
            "device_type": device_type,
            "device_name": device_name,
            "status": status,
            "error_message": error_message
        }
    ))


async def emit_terminal_command_result(
    venue_id: int,
    session_id: str,
    command_id: str,
    command_type: str,
    status: str,
    result: Dict = None,
    error_message: str = None
):
    """Emit terminal command result."""
    await manager.broadcast_channel(venue_id, "terminal", WebSocketMessage(
        event=EventType.TERMINAL_COMMAND_RESULT,
        data={
            "session_id": session_id,
            "command_id": command_id,
            "command_type": command_type,
            "status": status,
            "result": result,
            "error_message": error_message
        }
    ))


async def emit_printer_status(
    venue_id: int,
    device_id: str,
    printer_name: str,
    status: str,  # 'ready', 'printing', 'paper_low', 'paper_out', 'error'
    job_id: str = None,
    error_message: str = None
):
    """Emit printer status update."""
    await manager.broadcast_channel(venue_id, "hardware", WebSocketMessage(
        event=EventType.PRINTER_STATUS,
        data={
            "device_id": device_id,
            "printer_name": printer_name,
            "status": status,
            "job_id": job_id,
            "error_message": error_message
        }
    ))


async def emit_drawer_status(
    venue_id: int,
    device_id: str,
    drawer_name: str,
    status: str,  # 'closed', 'open', 'opened'
    opened_by: str = None
):
    """Emit cash drawer status update."""
    await manager.broadcast_channel(venue_id, "hardware", WebSocketMessage(
        event=EventType.DRAWER_STATUS,
        data={
            "device_id": device_id,
            "drawer_name": drawer_name,
            "status": status,
            "opened_by": opened_by
        }
    ))


# ==================== BNPL EVENTS ====================

async def emit_bnpl_status(
    venue_id: int,
    session_id: str,
    provider: str,
    status: str,  # 'created', 'authorized', 'captured', 'failed', 'refunded'
    order_id: str = None,
    amount: float = None,
    error_message: str = None
):
    """Emit BNPL transaction status update."""
    event_map = {
        "created": EventType.BNPL_SESSION_CREATED,
        "authorized": EventType.BNPL_AUTHORIZED,
        "captured": EventType.BNPL_CAPTURED,
        "failed": EventType.BNPL_FAILED,
        "refunded": EventType.BNPL_REFUNDED
    }
    event = event_map.get(status, EventType.NOTIFICATION)

    await manager.broadcast_channel(venue_id, "payments", WebSocketMessage(
        event=event,
        data={
            "session_id": session_id,
            "provider": provider,
            "status": status,
            "order_id": order_id,
            "amount": amount,
            "error_message": error_message
        }
    ))


# ==================== LABOR COMPLIANCE EVENTS ====================

async def emit_compliance_violation(
    venue_id: int,
    violation_id: str,
    violation_type: str,
    staff_id: str,
    staff_name: str,
    message: str,
    severity: str
):
    """Emit labor compliance violation."""
    await manager.broadcast_channel(venue_id, "compliance", WebSocketMessage(
        event=EventType.COMPLIANCE_VIOLATION,
        data={
            "violation_id": violation_id,
            "violation_type": violation_type,
            "staff_id": staff_id,
            "staff_name": staff_name,
            "message": message,
            "severity": severity
        }
    ))


async def emit_break_reminder(
    venue_id: int,
    staff_id: str,
    staff_name: str,
    shift_start: str,
    hours_worked: float,
    break_required: int  # minutes
):
    """Emit break reminder for staff."""
    await manager.broadcast_channel(venue_id, "compliance", WebSocketMessage(
        event=EventType.BREAK_REMINDER,
        data={
            "staff_id": staff_id,
            "staff_name": staff_name,
            "shift_start": shift_start,
            "hours_worked": hours_worked,
            "break_required": break_required
        }
    ))


async def emit_overtime_warning(
    venue_id: int,
    staff_id: str,
    staff_name: str,
    weekly_hours: float,
    threshold: float
):
    """Emit overtime warning."""
    await manager.broadcast_channel(venue_id, "compliance", WebSocketMessage(
        event=EventType.OVERTIME_WARNING,
        data={
            "staff_id": staff_id,
            "staff_name": staff_name,
            "weekly_hours": weekly_hours,
            "threshold": threshold
        }
    ))


# ==================== REVIEW/REPUTATION EVENTS ====================

async def emit_review_request_sent(
    venue_id: int,
    request_id: str,
    customer_id: str,
    method: str,
    platforms: List[str]
):
    """Emit review request sent event."""
    await manager.broadcast_channel(venue_id, "reviews", WebSocketMessage(
        event=EventType.REVIEW_REQUEST_SENT,
        data={
            "request_id": request_id,
            "customer_id": customer_id,
            "method": method,
            "platforms": platforms
        }
    ))


async def emit_review_received(
    venue_id: int,
    platform: str,
    rating: int,
    review_text: str,
    reviewer_name: str
):
    """Emit new review received event."""
    await manager.broadcast_venue(venue_id, WebSocketMessage(
        event=EventType.REVIEW_RECEIVED,
        data={
            "platform": platform,
            "rating": rating,
            "review_text": review_text,
            "reviewer_name": reviewer_name,
            "priority": "high" if rating <= 2 else "normal"
        }
    ))


# ==================== MOBILE/OFFLINE EVENTS ====================

async def emit_sync_status(
    venue_id: int,
    device_id: str,
    sync_type: str,  # 'full', 'incremental'
    status: str,  # 'started', 'completed', 'conflict'
    records_synced: int = 0,
    conflicts: List[Dict] = None
):
    """Emit mobile sync status."""
    if status == "started":
        event = EventType.SYNC_STARTED
    elif status == "completed":
        event = EventType.SYNC_COMPLETED
    else:
        event = EventType.SYNC_CONFLICT

    await manager.broadcast_channel(venue_id, "mobile", WebSocketMessage(
        event=event,
        data={
            "device_id": device_id,
            "sync_type": sync_type,
            "status": status,
            "records_synced": records_synced,
            "conflicts": conflicts
        }
    ))


async def emit_push_notification(
    venue_id: int,
    user_id: str,
    title: str,
    body: str,
    data: Dict = None,
    priority: str = "normal"
):
    """Emit push notification for mobile devices."""
    await manager.broadcast_channel(venue_id, f"user:{user_id}", WebSocketMessage(
        event=EventType.PUSH_NOTIFICATION,
        data={
            "title": title,
            "body": body,
            "data": data or {},
            "priority": priority
        }
    ))

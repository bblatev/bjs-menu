"""FastAPI application entry point."""

import logging
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from uuid import uuid4

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.api.routes import api_router
from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import engine, SessionLocal
from app.db.base import Base
from sqlalchemy import text

# Rate limiter instance
limiter = Limiter(key_func=get_remote_address, enabled=settings.rate_limit_enabled)


# WebSocket Connection Manager for real-time updates
class ConnectionManager:
    """Manages WebSocket connections for real-time updates with security features."""

    # Configuration
    MAX_CONNECTIONS_PER_CHANNEL = 1000
    MAX_MESSAGE_SIZE = 65536  # 64KB

    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.connection_metadata: Dict[int, Dict[str, Any]] = {}

    async def connect(
        self,
        websocket: WebSocket,
        channel: str = "default",
        user_id: Optional[int] = None,
        accept: bool = True
    ) -> bool:
        """Connect a WebSocket to a channel with connection limiting.

        Returns True if connection was successful, False if rejected.
        """
        # Check channel capacity
        if len(self.active_connections.get(channel, [])) >= self.MAX_CONNECTIONS_PER_CHANNEL:
            logger.warning(f"WebSocket connection rejected: channel '{channel}' at capacity")
            if accept:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return False

        if accept:
            await websocket.accept()

        if channel not in self.active_connections:
            self.active_connections[channel] = []
        self.active_connections[channel].append(websocket)

        # Store metadata for the connection
        self.connection_metadata[id(websocket)] = {
            "connected_at": datetime.now(timezone.utc),
            "user_id": user_id,
            "channel": channel,
            "last_ping": datetime.now(timezone.utc),
        }

        logger.debug(f"WebSocket connected to channel '{channel}', user_id={user_id}")
        return True

    def disconnect(self, websocket: WebSocket, channel: str = "default"):
        """Disconnect a WebSocket from a channel."""
        if channel in self.active_connections:
            if websocket in self.active_connections[channel]:
                self.active_connections[channel].remove(websocket)

        # Clean up metadata
        ws_id = id(websocket)
        if ws_id in self.connection_metadata:
            del self.connection_metadata[ws_id]

        logger.debug(f"WebSocket disconnected from channel '{channel}'")

    def update_ping(self, websocket: WebSocket):
        """Update last ping time for a connection."""
        ws_id = id(websocket)
        if ws_id in self.connection_metadata:
            self.connection_metadata[ws_id]["last_ping"] = datetime.now(timezone.utc)

    async def broadcast(self, message: Dict[str, Any], channel: str = "default"):
        """Broadcast a message to all connections in a channel."""
        if channel not in self.active_connections:
            return

        disconnected = []
        for connection in self.active_connections[channel]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.debug(f"WebSocket send failed: {e}")
                disconnected.append(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn, channel)

    async def broadcast_all(self, message: Dict[str, Any]):
        """Broadcast to all channels."""
        for channel in list(self.active_connections.keys()):
            await self.broadcast(message, channel)

    def get_connection_count(self, channel: Optional[str] = None) -> int:
        """Get the number of active connections."""
        if channel:
            return len(self.active_connections.get(channel, []))
        return sum(len(conns) for conns in self.active_connections.values())


# Global connection manager instance
ws_manager = ConnectionManager()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
auth_logger = logging.getLogger("auth")
request_logger = logging.getLogger("requests")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging all HTTP requests and responses."""

    async def dispatch(self, request: Request, call_next):
        import time

        # Skip logging for health checks and static files
        if request.url.path in ["/health", "/", "/docs", "/openapi.json"]:
            return await call_next(request)

        start_time = time.time()
        client_ip = request.client.host if request.client else "unknown"

        # Log request
        request_logger.info(
            f"Request: {request.method} {request.url.path} - Client: {client_ip}"
        )

        # Process request
        try:
            response = await call_next(request)
            process_time = time.time() - start_time

            # Log response
            log_level = logging.WARNING if response.status_code >= 400 else logging.INFO
            request_logger.log(
                log_level,
                f"Response: {request.method} {request.url.path} - "
                f"Status: {response.status_code} - Time: {process_time:.3f}s - Client: {client_ip}"
            )

            return response
        except Exception as e:
            process_time = time.time() - start_time
            request_logger.error(
                f"Error: {request.method} {request.url.path} - "
                f"Exception: {str(e)} - Time: {process_time:.3f}s - Client: {client_ip}"
            )
            raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Starting Inventory Management System")

    # Create tables if they don't exist (for SQLite dev)
    # In production with PostgreSQL, use Alembic migrations
    if settings.database_url.startswith("sqlite"):
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created (SQLite mode)")

    yield

    logger.info("Shutting down Inventory Management System")


app = FastAPI(
    title="Inventory Management System",
    description="Backend API for inventory scanning and management",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Rate limiting setup
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware - origins configured via CORS_ORIGINS env variable
# Restrict methods and headers for better security
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "Accept",
        "Origin",
        "X-Requested-With",
        "X-Request-ID",
    ],
    expose_headers=["X-Request-ID"],
    max_age=600,  # Cache preflight for 10 minutes
)

# Request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Include API routes
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health")
def health_check():
    """Basic liveness check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/health/ready")
def readiness_check():
    """Readiness probe with database connectivity check."""
    checks = {
        "database": "unknown",
        "websocket_manager": "unknown",
    }

    # Check database connectivity
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        checks["database"] = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        checks["database"] = f"unhealthy: {str(e)}"

    # Check WebSocket manager
    try:
        connection_count = ws_manager.get_connection_count()
        checks["websocket_manager"] = f"healthy ({connection_count} connections)"
    except Exception as e:
        logger.error(f"WebSocket manager health check failed: {e}")
        checks["websocket_manager"] = f"unhealthy: {str(e)}"

    # Determine overall status
    all_healthy = all(
        c.startswith("healthy") for c in checks.values()
    )

    return {
        "status": "ready" if all_healthy else "degraded",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "message": "Inventory Management System API",
        "docs": "/docs",
        "health": "/health",
    }


# WebSocket endpoints for real-time updates
@app.websocket("/ws/waiter-calls")
async def websocket_waiter_calls(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    """WebSocket endpoint for real-time waiter call updates.

    Optional token query parameter for authenticated connections.
    """
    user_id = None
    if token:
        payload = decode_access_token(token)
        if payload:
            user_id = int(payload.get("sub", 0))

    if not await ws_manager.connect(websocket, "waiter-calls", user_id=user_id):
        return

    try:
        while True:
            # Keep connection alive, listen for any client messages
            data = await websocket.receive_text()
            # Echo back or handle ping/pong
            if data == "ping":
                ws_manager.update_ping(websocket)
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, "waiter-calls")
    except Exception as e:
        logger.error(f"WebSocket error in waiter-calls: {e}", exc_info=True)
        ws_manager.disconnect(websocket, "waiter-calls")


@app.websocket("/ws/kitchen")
async def websocket_kitchen(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    """WebSocket endpoint for real-time kitchen updates."""
    user_id = None
    if token:
        payload = decode_access_token(token)
        if payload:
            user_id = int(payload.get("sub", 0))

    if not await ws_manager.connect(websocket, "kitchen", user_id=user_id):
        return

    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                ws_manager.update_ping(websocket)
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, "kitchen")
    except Exception as e:
        logger.error(f"WebSocket error in kitchen: {e}", exc_info=True)
        ws_manager.disconnect(websocket, "kitchen")


@app.websocket("/ws/orders")
async def websocket_orders(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    """WebSocket endpoint for real-time order updates."""
    user_id = None
    if token:
        payload = decode_access_token(token)
        if payload:
            user_id = int(payload.get("sub", 0))

    if not await ws_manager.connect(websocket, "orders", user_id=user_id):
        return

    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                ws_manager.update_ping(websocket)
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, "orders")
    except Exception as e:
        logger.error(f"WebSocket error in orders: {e}", exc_info=True)
        ws_manager.disconnect(websocket, "orders")


@app.websocket("/api/v1/ws/venue/{venue_id}")
async def websocket_venue(
    websocket: WebSocket,
    venue_id: int,
    channels: str = "general",
    token: Optional[str] = Query(None)
):
    """WebSocket endpoint for venue-specific real-time updates with channel support.

    Args:
        venue_id: The venue ID to connect to
        channels: Comma-separated list of channels to subscribe to
        token: Optional JWT token for authentication
    """
    # Authenticate if token provided
    user_id = None
    if token:
        payload = decode_access_token(token)
        if payload:
            user_id = int(payload.get("sub", 0))
        else:
            logger.warning(f"Invalid WebSocket token for venue {venue_id}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    channel_list = [ch.strip() for ch in channels.split(",") if ch.strip()][:10]  # Limit channels
    primary_channel = f"venue-{venue_id}"

    if not await ws_manager.connect(websocket, primary_channel, user_id=user_id):
        return

    # Subscribe to additional channels (don't re-accept the websocket)
    for channel in channel_list:
        if channel not in ["general", primary_channel]:
            await ws_manager.connect(websocket, channel, user_id=user_id, accept=False)

    try:
        # Send connection confirmation
        await websocket.send_json({
            "event": "connected",
            "data": {"venue_id": venue_id, "channels": channel_list, "user_id": user_id},
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        while True:
            data = await websocket.receive_text()

            # Enforce message size limit
            if len(data) > ws_manager.MAX_MESSAGE_SIZE:
                logger.warning(f"WebSocket message too large from venue {venue_id}")
                continue

            try:
                message = json.loads(data)
                event_type = message.get("event")

                if event_type == "ping":
                    ws_manager.update_ping(websocket)
                    await websocket.send_json({
                        "event": "pong",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                elif event_type == "subscribe":
                    new_channels = message.get("channels", [])[:10]  # Limit
                    for ch in new_channels:
                        if isinstance(ch, str) and len(ch) <= 64:  # Validate channel name
                            await ws_manager.connect(websocket, ch, user_id=user_id, accept=False)
                elif event_type == "unsubscribe":
                    remove_channels = message.get("channels", [])
                    for ch in remove_channels:
                        if isinstance(ch, str):
                            ws_manager.disconnect(websocket, ch)
            except json.JSONDecodeError:
                if data == "ping":
                    ws_manager.update_ping(websocket)
                    await websocket.send_text("pong")
    except WebSocketDisconnect:
        logger.debug(f"WebSocket disconnected from venue {venue_id}")
        ws_manager.disconnect(websocket, primary_channel)
        for channel in channel_list:
            ws_manager.disconnect(websocket, channel)
    except Exception as e:
        logger.error(f"WebSocket error in venue {venue_id}: {e}", exc_info=True)
        ws_manager.disconnect(websocket, primary_channel)
        for channel in channel_list:
            ws_manager.disconnect(websocket, channel)


# Helper function to broadcast waiter call updates (called from routes)
def get_ws_manager():
    """Get the WebSocket manager instance."""
    return ws_manager

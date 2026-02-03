"""FastAPI application entry point."""

import logging
import json
from contextlib import asynccontextmanager
from typing import List, Dict, Any

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.api.routes import api_router
from app.core.config import settings
from app.db.session import engine
from app.db.base import Base

# Rate limiter instance
limiter = Limiter(key_func=get_remote_address, enabled=settings.rate_limit_enabled)


# WebSocket Connection Manager for real-time updates
class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: str = "default"):
        await websocket.accept()
        if channel not in self.active_connections:
            self.active_connections[channel] = []
        self.active_connections[channel].append(websocket)

    def disconnect(self, websocket: WebSocket, channel: str = "default"):
        if channel in self.active_connections:
            if websocket in self.active_connections[channel]:
                self.active_connections[channel].remove(websocket)

    async def broadcast(self, message: Dict[str, Any], channel: str = "default"):
        if channel in self.active_connections:
            disconnected = []
            for connection in self.active_connections[channel]:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.append(connection)
            # Clean up disconnected clients
            for conn in disconnected:
                self.disconnect(conn, channel)

    async def broadcast_all(self, message: Dict[str, Any]):
        """Broadcast to all channels."""
        for channel in self.active_connections:
            await self.broadcast(message, channel)


# Global connection manager instance
ws_manager = ConnectionManager()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


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
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


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
async def websocket_waiter_calls(websocket: WebSocket):
    """WebSocket endpoint for real-time waiter call updates."""
    await ws_manager.connect(websocket, "waiter-calls")
    try:
        while True:
            # Keep connection alive, listen for any client messages
            data = await websocket.receive_text()
            # Echo back or handle ping/pong
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, "waiter-calls")
    except Exception:
        ws_manager.disconnect(websocket, "waiter-calls")


@app.websocket("/ws/kitchen")
async def websocket_kitchen(websocket: WebSocket):
    """WebSocket endpoint for real-time kitchen updates."""
    await ws_manager.connect(websocket, "kitchen")
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, "kitchen")
    except Exception:
        ws_manager.disconnect(websocket, "kitchen")


@app.websocket("/ws/orders")
async def websocket_orders(websocket: WebSocket):
    """WebSocket endpoint for real-time order updates."""
    await ws_manager.connect(websocket, "orders")
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, "orders")
    except Exception:
        ws_manager.disconnect(websocket, "orders")


@app.websocket("/api/v1/ws/venue/{venue_id}")
async def websocket_venue(websocket: WebSocket, venue_id: int, channels: str = "general"):
    """WebSocket endpoint for venue-specific real-time updates with channel support."""
    channel_list = channels.split(",") if channels else ["general"]
    primary_channel = f"venue-{venue_id}"

    await ws_manager.connect(websocket, primary_channel)
    for channel in channel_list:
        if channel not in ["general", primary_channel]:
            await ws_manager.connect(websocket, channel)

    try:
        # Send connection confirmation
        await websocket.send_json({
            "event": "connected",
            "data": {"venue_id": venue_id, "channels": channel_list},
            "timestamp": __import__('datetime').datetime.utcnow().isoformat()
        })

        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                if message.get("event") == "ping":
                    await websocket.send_json({
                        "event": "pong",
                        "timestamp": __import__('datetime').datetime.utcnow().isoformat()
                    })
                elif message.get("event") == "subscribe":
                    new_channels = message.get("channels", [])
                    for ch in new_channels:
                        await ws_manager.connect(websocket, ch)
                elif message.get("event") == "unsubscribe":
                    remove_channels = message.get("channels", [])
                    for ch in remove_channels:
                        ws_manager.disconnect(websocket, ch)
            except json.JSONDecodeError:
                if data == "ping":
                    await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, primary_channel)
        for channel in channel_list:
            ws_manager.disconnect(websocket, channel)
    except Exception:
        ws_manager.disconnect(websocket, primary_channel)
        for channel in channel_list:
            ws_manager.disconnect(websocket, channel)


# Helper function to broadcast waiter call updates (called from routes)
def get_ws_manager():
    """Get the WebSocket manager instance."""
    return ws_manager

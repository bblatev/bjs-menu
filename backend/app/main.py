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

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.rate_limit import limiter

from app.api.routes import api_router
from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import engine, SessionLocal
from app.db.base import Base
from app.services.audit_service import log_action as _audit_log_action
from sqlalchemy import text

# Public paths that do NOT require authentication
# All other /api/v1/* paths require a valid Bearer token
PUBLIC_PATH_PREFIXES = [
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/guest-orders/menu",
    "/api/v1/guest-orders/create",
    "/api/v1/orders/guest",
    "/api/v1/table/",
    "/api/v1/admin/tables",      # Guest QR flow needs table info
    "/api/v1/menu-items",        # Guest menu browsing
    "/api/v1/menu/categories",   # Guest menu browsing
    "/api/v1/menu/items",        # Guest menu browsing
    "/ws/",                      # WebSocket (has its own auth)
]

PUBLIC_EXACT_PATHS = [
    "/",
    "/health",
    "/health/ready",
]

# Rate limiter instance (imported from app.core.rate_limit)


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

# Configure logging - use JSON format in production, human-readable in dev
if settings.debug:
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
else:
    import json as _json

    class JSONFormatter(logging.Formatter):
        def format(self, record):
            return _json.dumps({
                "ts": self.formatTime(record, self.datefmt),
                "level": record.levelname,
                "logger": record.name,
                "msg": record.getMessage(),
                "module": record.module,
                "line": record.lineno,
            })

    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logging.basicConfig(level=getattr(logging, settings.log_level), handlers=[handler])
logger = logging.getLogger(__name__)
auth_logger = logging.getLogger("auth")
request_logger = logging.getLogger("requests")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        csp_origins = " ".join(settings.cors_origins_list)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://js.stripe.com; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob: https://api.qrserver.com; "
            f"connect-src 'self' ws: wss: https://api.stripe.com {csp_origins}; "
            "frame-src https://js.stripe.com; "
            "font-src 'self' data:;"
        )
        # Note: HSTS is set at the nginx layer to avoid duplicate headers
        return response


class AuthEnforcementMiddleware(BaseHTTPMiddleware):
    """Global authentication enforcement middleware.

    All /api/v1/* endpoints require a valid Bearer token UNLESS
    the path is in PUBLIC_PATH_PREFIXES or PUBLIC_EXACT_PATHS.
    This provides defence-in-depth even if individual route files
    forget to add Depends(get_current_user).
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method

        # Always allow OPTIONS (CORS preflight)
        if method == "OPTIONS":
            return await call_next(request)

        # Check exact public paths (all methods)
        if path in PUBLIC_EXACT_PATHS:
            return await call_next(request)

        # For GET requests: allow public browsing endpoints through,
        # require auth for sensitive data endpoints
        if method == "GET":
            # Public GET paths that guests/anonymous users can access
            public_get_prefixes = [
                "/api/v1/guest-orders",
                "/api/v1/menu/",
                "/api/v1/menu-complete",
                "/api/v1/menu-items",
                "/api/v1/tables",
                "/api/v1/reservations/availability",
                "/api/v1/locations",
                "/api/v1/orders/table/",
            ]
            for prefix in public_get_prefixes:
                if path.startswith(prefix):
                    return await call_next(request)

            # All other GET endpoints require authentication
            if path.startswith("/api/v1/"):
                auth_header = request.headers.get("Authorization", "")
                if not auth_header.startswith("Bearer "):
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "Authentication required"},
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                token = auth_header.split(" ", 1)[1]
                payload = decode_access_token(token)
                if payload is None:
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "Invalid or expired token"},
                        headers={"WWW-Authenticate": "Bearer"},
                    )
            return await call_next(request)

        # For state-changing methods (POST/PUT/PATCH/DELETE),
        # only allow specific public endpoints
        public_write_paths = [
            "/api/v1/auth/login",
            "/api/v1/auth/login/pin",
            "/api/v1/auth/register",
            "/api/v1/orders/guest",
            "/api/v1/guest-orders/create",
            "/api/v1/orders/table/",
            "/api/v1/waiter/calls",
        ]
        for pub_path in public_write_paths:
            if path.startswith(pub_path):
                return await call_next(request)

        # All other POST/PUT/PATCH/DELETE on /api/v1/* require authentication
        if path.startswith("/api/v1/"):
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Authentication required for this operation"},
                    headers={"WWW-Authenticate": "Bearer"},
                )

            token = auth_header.split(" ", 1)[1]
            payload = decode_access_token(token)
            if payload is None:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid or expired token"},
                    headers={"WWW-Authenticate": "Bearer"},
                )

        return await call_next(request)


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


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """Auto-log all state-changing API requests to the audit_log_entries table.

    Captures: user_id (from JWT), action (from HTTP method), entity_type (from URL path),
    IP address, and response status.
    """

    # Map HTTP methods to audit actions
    METHOD_ACTION_MAP = {
        "POST": "create",
        "PUT": "update",
        "PATCH": "update",
        "DELETE": "delete",
    }

    async def dispatch(self, request: Request, call_next):
        method = request.method
        path = request.url.path

        # Only audit state-changing methods on API paths
        if method not in self.METHOD_ACTION_MAP or not path.startswith("/api/v1/"):
            return await call_next(request)

        # Skip auditing auth login/register (logged separately with more detail)
        if any(path.startswith(p) for p in ["/api/v1/auth/login", "/api/v1/auth/register"]):
            return await call_next(request)

        response = await call_next(request)

        # Only audit successful operations (2xx status codes)
        if 200 <= response.status_code < 300:
            try:
                # Extract user info from JWT if present
                user_id = None
                user_name = ""
                auth_header = request.headers.get("Authorization", "")
                if auth_header.startswith("Bearer "):
                    token = auth_header.split(" ", 1)[1]
                    payload = decode_access_token(token)
                    if payload:
                        user_id = int(payload.get("sub", 0)) or None
                        user_name = payload.get("email", "")

                # Parse entity type and ID from URL path
                # e.g. /api/v1/menu/items/5 -> entity_type=menu_items, entity_id=5
                parts = path.replace("/api/v1/", "").strip("/").split("/")
                entity_type = "_".join(parts[:2]) if len(parts) >= 2 else (parts[0] if parts else "unknown")
                # Try to find an entity ID (numeric segment)
                entity_id = ""
                for part in reversed(parts):
                    if part.isdigit():
                        entity_id = part
                        break

                client_ip = request.client.host if request.client else ""

                _audit_log_action(
                    action=self.METHOD_ACTION_MAP[method],
                    entity_type=entity_type[:50],
                    entity_id=entity_id,
                    user_id=user_id,
                    user_name=user_name[:200],
                    ip_address=client_ip,
                    details={
                        "method": method,
                        "path": path,
                        "status_code": response.status_code,
                    },
                )
            except Exception as e:
                # Never let audit logging break the request, but log the failure
                logger.warning(f"Audit logging failed for {method} {path}: {e}")

        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Starting Inventory Management System")

    # Create tables if they don't exist (for SQLite dev)
    # In production with PostgreSQL, use Alembic migrations
    if settings.database_url.startswith("sqlite"):
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created (SQLite mode)")

    # Audit log retention: purge entries older than 90 days on startup
    # Uses a flag in AppSetting to only run once per day
    retention_db = None
    try:
        from datetime import datetime, timedelta, timezone
        from app.db.session import SessionLocal
        from app.models.operations import AuditLogEntry, AppSetting
        retention_db = SessionLocal()
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        last_run = retention_db.query(AppSetting).filter(
            AppSetting.key == "audit_retention_last_run"
        ).first()
        if not last_run or last_run.value != today_str:
            cutoff = datetime.now(timezone.utc) - timedelta(days=90)
            deleted = retention_db.query(AuditLogEntry).filter(
                AuditLogEntry.created_at < cutoff
            ).delete(synchronize_session=False)
            if last_run:
                last_run.value = today_str
            else:
                retention_db.add(AppSetting(category="system", key="audit_retention_last_run", value=today_str))
            retention_db.commit()
            if deleted:
                logger.info(f"Audit log retention: purged {deleted} entries older than 90 days")
        else:
            logger.debug("Audit log retention: already ran today, skipping")
    except Exception as e:
        logger.warning(f"Audit log retention skipped: {e}")
    finally:
        if retention_db:
            retention_db.close()

    yield

    logger.info("Shutting down Inventory Management System")


app = FastAPI(
    title="Inventory Management System",
    description="Backend API for inventory scanning and management",
    version="1.0.0",
    lifespan=lifespan,
    redirect_slashes=True,
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

# Security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Authentication enforcement middleware (POST/PUT/PATCH/DELETE require auth)
app.add_middleware(AuthEnforcementMiddleware)

# Audit logging middleware (records state changes to audit_log_entries table)
app.add_middleware(AuditLoggingMiddleware)

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
    """Readiness probe with database, Redis, and WebSocket connectivity check."""
    checks = {
        "database": "unknown",
        "websocket_manager": "unknown",
        "redis": "unknown",
    }

    # Check database connectivity
    db = None
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        checks["database"] = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        checks["database"] = f"unhealthy: {str(e)}"
    finally:
        if db:
            db.close()

    # Check Redis connectivity
    try:
        import redis
        redis_url = getattr(settings, 'redis_url', None)
        if redis_url:
            r = redis.from_url(redis_url, socket_connect_timeout=2)
            r.ping()
            checks["redis"] = "healthy"
        else:
            checks["redis"] = "not configured"
    except ImportError:
        checks["redis"] = "not installed"
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        checks["redis"] = f"unhealthy: {str(e)}"

    # Check WebSocket manager
    try:
        connection_count = ws_manager.get_connection_count()
        checks["websocket_manager"] = f"healthy ({connection_count} connections)"
    except Exception as e:
        logger.error(f"WebSocket manager health check failed: {e}")
        checks["websocket_manager"] = f"unhealthy: {str(e)}"

    # Determine overall status (redis "not configured"/"not installed" counts as OK)
    all_healthy = all(
        c.startswith("healthy") or c in ("not configured", "not installed")
        for c in checks.values()
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

"""
Observability Middleware and Utilities

Provides:
- Correlation ID tracking across requests
- Request/response logging
- Prometheus metrics (when enabled)
- Performance monitoring

When CORRELATION_IDS_ENABLED is active:
- Every request gets a unique correlation ID
- ID is propagated through all logs and downstream calls
- Response headers include correlation ID for debugging
"""

import time
import uuid
import logging
from typing import Callable, Optional, Dict, Any
from datetime import datetime
from contextvars import ContextVar

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.feature_flags import is_enabled


# Context variable for correlation ID
correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)

# Logger
logger = logging.getLogger("zver_pos")


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID from context."""
    return correlation_id_var.get()


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID in context."""
    correlation_id_var.set(correlation_id)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add correlation IDs to requests.

    Extracts correlation ID from X-Correlation-ID header or generates new one.
    Adds correlation ID to response headers.
    """

    HEADER_NAME = "X-Correlation-ID"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not is_enabled("CORRELATION_IDS_ENABLED"):
            return await call_next(request)

        # Get or generate correlation ID
        correlation_id = request.headers.get(self.HEADER_NAME)
        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        # Set in context
        set_correlation_id(correlation_id)

        # Process request
        response = await call_next(request)

        # Add to response headers
        response.headers[self.HEADER_NAME] = correlation_id

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for request/response logging.

    Logs request details, timing, and response status.
    """

    # Paths to exclude from logging
    EXCLUDED_PATHS = {"/health", "/metrics", "/favicon.ico"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip excluded paths
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        start_time = time.time()
        correlation_id = get_correlation_id() or "no-correlation-id"

        # Log request
        logger.info(
            f"[{correlation_id}] {request.method} {request.url.path} started",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "query": str(request.query_params),
                "client_ip": request.client.host if request.client else None,
            }
        )

        # Process request
        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000

            # Log response
            logger.info(
                f"[{correlation_id}] {request.method} {request.url.path} "
                f"completed {response.status_code} in {duration_ms:.2f}ms",
                extra={
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                }
            )

            return response

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"[{correlation_id}] {request.method} {request.url.path} "
                f"failed after {duration_ms:.2f}ms: {str(e)}",
                extra={
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e),
                    "duration_ms": duration_ms,
                },
                exc_info=True
            )
            raise


class MetricsCollector:
    """
    Prometheus metrics collector.

    When PROMETHEUS_METRICS is enabled, exposes metrics at /metrics endpoint.
    """

    def __init__(self):
        self.request_count: Dict[str, int] = {}
        self.request_duration: Dict[str, float] = {}
        self.error_count: Dict[str, int] = {}

    def is_active(self) -> bool:
        return is_enabled("PROMETHEUS_METRICS")

    def record_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
    ) -> None:
        """Record request metrics."""
        if not self.is_active():
            return

        key = f"{method}:{path}"

        # Increment request count
        self.request_count[key] = self.request_count.get(key, 0) + 1

        # Update duration (simple moving average)
        current = self.request_duration.get(key, 0)
        count = self.request_count[key]
        self.request_duration[key] = current + (duration_ms - current) / count

        # Track errors
        if status_code >= 400:
            error_key = f"{key}:{status_code}"
            self.error_count[error_key] = self.error_count.get(error_key, 0) + 1

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        if not self.is_active():
            return {"status": "disabled"}

        return {
            "request_counts": self.request_count,
            "avg_duration_ms": self.request_duration,
            "error_counts": self.error_count,
            "collected_at": datetime.utcnow().isoformat(),
        }

    def get_prometheus_format(self) -> str:
        """Get metrics in Prometheus text format."""
        if not self.is_active():
            return "# Metrics disabled\n"

        lines = []

        # Request count
        lines.append("# HELP http_requests_total Total HTTP requests")
        lines.append("# TYPE http_requests_total counter")
        for key, count in self.request_count.items():
            method, path = key.split(":", 1)
            lines.append(
                f'http_requests_total{{method="{method}",path="{path}"}} {count}'
            )

        # Request duration
        lines.append("# HELP http_request_duration_ms Average request duration")
        lines.append("# TYPE http_request_duration_ms gauge")
        for key, duration in self.request_duration.items():
            method, path = key.split(":", 1)
            lines.append(
                f'http_request_duration_ms{{method="{method}",path="{path}"}} {duration:.2f}'
            )

        # Error count
        lines.append("# HELP http_errors_total Total HTTP errors")
        lines.append("# TYPE http_errors_total counter")
        for key, count in self.error_count.items():
            parts = key.split(":")
            method, path, status = parts[0], parts[1], parts[2]
            lines.append(
                f'http_errors_total{{method="{method}",path="{path}",status="{status}"}} {count}'
            )

        return "\n".join(lines) + "\n"


# Global metrics collector
metrics_collector = MetricsCollector()


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect request metrics."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not metrics_collector.is_active():
            return await call_next(request)

        start_time = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000

        metrics_collector.record_request(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        return response


def setup_observability(app):
    """
    Setup observability middleware on FastAPI app.

    Call this during app initialization.
    """
    # Add middleware in order (first added = outermost)
    if is_enabled("PROMETHEUS_METRICS"):
        app.add_middleware(MetricsMiddleware)

    if is_enabled("CORRELATION_IDS_ENABLED"):
        app.add_middleware(RequestLoggingMiddleware)
        app.add_middleware(CorrelationIdMiddleware)

    # Add metrics endpoint
    @app.get("/metrics")
    async def get_metrics():
        if not metrics_collector.is_active():
            return {"status": "disabled"}
        return Response(
            content=metrics_collector.get_prometheus_format(),
            media_type="text/plain"
        )

    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "features": {
                "correlation_ids": is_enabled("CORRELATION_IDS_ENABLED"),
                "prometheus_metrics": is_enabled("PROMETHEUS_METRICS"),
            }
        }

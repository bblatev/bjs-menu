"""Prometheus-compatible metrics for application monitoring."""

import time
import logging
from typing import Dict, List, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collects HTTP request metrics in Prometheus exposition format."""

    def __init__(self):
        self.request_count: Dict[str, int] = {}
        self.request_duration: Dict[str, List[float]] = {}
        self.error_count: Dict[int, int] = {}
        self.active_requests: int = 0
        # Infrastructure gauges
        self.db_pool_size: int = 20
        self.db_pool_checked_out: int = 0
        self.redis_connected: int = 1
        self.ws_active_connections: int = 0

    def record_request(self, method: str, path: str, status: int, duration: float):
        # Normalize path to avoid cardinality explosion
        normalized = self._normalize_path(path)
        key = f"{method} {normalized}"
        self.request_count[key] = self.request_count.get(key, 0) + 1
        if key not in self.request_duration:
            self.request_duration[key] = []
        durations = self.request_duration[key]
        durations.append(duration)
        if len(durations) > 1000:
            self.request_duration[key] = durations[-1000:]
        if status >= 400:
            self.error_count[status] = self.error_count.get(status, 0) + 1

    @staticmethod
    def _normalize_path(path: str) -> str:
        """Replace numeric IDs with :id to limit cardinality."""
        parts = path.split("/")
        return "/".join(":id" if p.isdigit() else p for p in parts)

    def get_prometheus_metrics(self) -> str:
        lines: List[str] = []
        lines.append("# HELP http_requests_total Total HTTP requests")
        lines.append("# TYPE http_requests_total counter")
        for key, count in sorted(self.request_count.items()):
            method, path = key.split(" ", 1)
            lines.append(f'http_requests_total{{method="{method}",path="{path}"}} {count}')

        lines.append("# HELP http_errors_total Total HTTP errors by status code")
        lines.append("# TYPE http_errors_total counter")
        for code, count in sorted(self.error_count.items()):
            lines.append(f'http_errors_total{{status="{code}"}} {count}')

        lines.append("# HELP http_active_requests Current active requests")
        lines.append("# TYPE http_active_requests gauge")
        lines.append(f"http_active_requests {self.active_requests}")

        lines.append("# HELP http_request_duration_seconds Request duration histogram")
        lines.append("# TYPE http_request_duration_seconds summary")
        for key, durations in sorted(self.request_duration.items()):
            if durations:
                method, path = key.split(" ", 1)
                avg = sum(durations) / len(durations)
                p99 = sorted(durations)[int(len(durations) * 0.99)] if len(durations) > 1 else durations[0]
                lines.append(f'http_request_duration_seconds{{method="{method}",path="{path}",quantile="0.99"}} {p99:.4f}')
                lines.append(f'http_request_duration_seconds{{method="{method}",path="{path}",quantile="0.5"}} {avg:.4f}')

        # Database connection pool metrics
        lines.append("# HELP db_pool_size Total database connection pool size")
        lines.append("# TYPE db_pool_size gauge")
        lines.append(f"db_pool_size {self.db_pool_size}")
        lines.append("# HELP db_pool_checked_out Database connections currently in use")
        lines.append("# TYPE db_pool_checked_out gauge")
        lines.append(f"db_pool_checked_out {self.db_pool_checked_out}")

        # Redis connection status
        lines.append("# HELP redis_connected Redis connection status (1=connected, 0=disconnected)")
        lines.append("# TYPE redis_connected gauge")
        lines.append(f"redis_connected {self.redis_connected}")

        # WebSocket active connections
        lines.append("# HELP ws_active_connections Active WebSocket connections")
        lines.append("# TYPE ws_active_connections gauge")
        lines.append(f"ws_active_connections {self.ws_active_connections}")

        return "\n".join(lines) + "\n"


metrics = MetricsCollector()


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware that records request metrics."""

    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/metrics":
            return await call_next(request)

        metrics.active_requests += 1
        start = time.time()
        try:
            response = await call_next(request)
            duration = time.time() - start
            metrics.record_request(
                request.method,
                request.url.path,
                response.status_code,
                duration,
            )
            return response
        except Exception:
            duration = time.time() - start
            metrics.record_request(request.method, request.url.path, 500, duration)
            raise
        finally:
            metrics.active_requests -= 1

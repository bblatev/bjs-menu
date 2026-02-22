"""CSRF protection using double-submit cookie pattern.

When using HttpOnly cookie auth, we need CSRF protection for state-changing
requests (POST, PUT, PATCH, DELETE). GET/HEAD/OPTIONS are safe.

The client reads the csrf_token cookie (not HttpOnly) and sends it back
as the X-CSRF-Token header. The server compares the two values.
"""

import logging
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Methods that require CSRF protection
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Paths exempt from CSRF (webhooks, health checks, public APIs)
CSRF_EXEMPT_PATHS = {
    "/health",
    "/health/ready",
    "/api/v1/auth/login",
    "/api/v1/auth/login/pin",
    "/api/v1/auth/register",
    "/api/v1/auth/pin-reset/confirm",
    "/api/v1/auth/refresh",
    "/api/v1/webhooks/",  # prefix match
    "/api/v1/stripe/webhook",
}


def _is_csrf_exempt(path: str) -> bool:
    """Check if a path is exempt from CSRF protection."""
    for exempt in CSRF_EXEMPT_PATHS:
        if exempt.endswith("/"):
            if path.startswith(exempt):
                return True
        elif path == exempt:
            return True
    return False


class CSRFMiddleware(BaseHTTPMiddleware):
    """Double-submit cookie CSRF protection.

    Only enforced when the request is authenticated via cookies
    (i.e., has an access_token cookie but no Authorization header).
    Requests using Bearer token auth are not vulnerable to CSRF.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Only check unsafe methods
        if request.method not in UNSAFE_METHODS:
            return await call_next(request)

        # Skip exempt paths
        if _is_csrf_exempt(request.url.path):
            return await call_next(request)

        # Only enforce CSRF when auth comes from cookies (not Bearer header)
        auth_header = request.headers.get("Authorization", "")
        has_cookie_auth = "access_token" in request.cookies
        has_bearer_auth = auth_header.startswith("Bearer ")

        if has_cookie_auth and not has_bearer_auth:
            # Cookie-based auth: require CSRF token
            cookie_csrf = request.cookies.get("csrf_token", "")
            header_csrf = request.headers.get("X-CSRF-Token", "")

            if not cookie_csrf or not header_csrf or cookie_csrf != header_csrf:
                logger.warning(
                    f"CSRF validation failed: path={request.url.path} "
                    f"method={request.method} cookie={'set' if cookie_csrf else 'missing'} "
                    f"header={'set' if header_csrf else 'missing'}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="CSRF validation failed",
                )

        return await call_next(request)

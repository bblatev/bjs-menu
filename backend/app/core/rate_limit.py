"""Shared rate limiter instance for use across route files."""

from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request

from app.core.config import settings

limiter = Limiter(key_func=get_remote_address, enabled=settings.rate_limit_enabled)


def get_user_or_ip(request: Request) -> str:
    """Rate limit by user ID if authenticated, else by IP."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        from app.core.security import decode_access_token
        token = auth.split(" ", 1)[1]
        payload = decode_access_token(token)
        if payload and payload.get("sub"):
            return f"user:{payload['sub']}"
    return get_remote_address(request)


user_limiter = Limiter(key_func=get_user_or_ip, enabled=settings.rate_limit_enabled)

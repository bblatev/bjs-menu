"""Security utilities: JWT tokens, password hashing, and session management."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from urllib.parse import urlparse
import logging

import jwt
from jwt.exceptions import PyJWTError
import bcrypt

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Redirect URI validation – prevents open-redirect attacks
# ---------------------------------------------------------------------------

# Allowed redirect hosts for OAuth callbacks and return URLs
_ALLOWED_REDIRECT_HOSTS = {
    "menu.bjs.bar",
    "localhost",
    "127.0.0.1",
}


def validate_redirect_uri(uri: str) -> bool:
    """Validate that a redirect URI points to an allowed host.

    Prevents open redirect attacks by ensuring the URI host is whitelisted.
    """
    if not uri:
        return False
    try:
        parsed = urlparse(uri)
        # Must have a scheme and host
        if not parsed.scheme or not parsed.netloc:
            return False
        # Only allow https in production (http for localhost dev)
        host = parsed.hostname or ""
        if host not in _ALLOWED_REDIRECT_HOSTS:
            return False
        return True
    except Exception:
        return False


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hash.

    Uses bcrypt's built-in timing-safe comparison.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception as e:
        logger.warning(f"Password verification error: {e}")
        return False


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')


def verify_pin(plain_pin: str, hashed_pin: str) -> bool:
    """Verify a plain PIN against a hash.

    Uses bcrypt's built-in timing-safe comparison.
    """
    try:
        return bcrypt.checkpw(
            plain_pin.encode('utf-8'),
            hashed_pin.encode('utf-8')
        )
    except Exception as e:
        logger.warning(f"PIN verification error: {e}")
        return False


def get_pin_hash(pin: str) -> str:
    """Hash a PIN code using bcrypt."""
    return bcrypt.hashpw(
        pin.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token with a unique JTI for blacklisting support."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)

    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({
        "exp": expire,
        "iat": now,
        "jti": secrets.token_urlsafe(16),  # Unique token ID for blacklisting
    })
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode and validate a JWT token. Checks Redis blacklist if available."""
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
            options={"require_exp": True}
        )

        # Check token blacklist (Redis-backed)
        jti = payload.get("jti")
        if jti and _is_token_blacklisted(jti):
            logger.debug(f"Token {jti} is blacklisted")
            return None

        return payload
    except PyJWTError as e:
        logger.debug(f"JWT decode error: {e}")
        return None


def blacklist_token(token: str) -> bool:
    """Add a token to the blacklist (invalidate session).

    The token is stored in Redis with TTL matching its expiration time.
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
            options={"require_exp": True, "verify_exp": False}
        )
    except PyJWTError:
        return False

    jti = payload.get("jti")
    if not jti:
        return False

    exp = payload.get("exp", 0)
    ttl = max(int(exp - datetime.now(timezone.utc).timestamp()), 60)

    try:
        import redis
        redis_url = getattr(settings, 'redis_url', None)
        if redis_url:
            r = redis.from_url(redis_url, socket_connect_timeout=2)
            r.setex(f"token_blacklist:{jti}", ttl, "1")
            return True
    except Exception as e:
        logger.warning(f"Redis blacklist failed: {e}")

    # Fallback: in-memory blacklist (cleared on restart)
    _memory_blacklist[jti] = datetime.now(timezone.utc) + timedelta(seconds=ttl)
    return True


def _is_token_blacklisted(jti: str) -> bool:
    """Check if a token JTI is blacklisted."""
    try:
        import redis
        redis_url = getattr(settings, 'redis_url', None)
        if redis_url:
            r = redis.from_url(redis_url, socket_connect_timeout=1)
            return bool(r.get(f"token_blacklist:{jti}"))
    except Exception as e:
        logger.warning(f"Redis blacklist check failed (token may be allowed through): {e}")

    # Fallback: in-memory
    expiry = _memory_blacklist.get(jti)
    if expiry:
        if datetime.now(timezone.utc) < expiry:
            return True
        else:
            del _memory_blacklist[jti]
    return False


# In-memory blacklist fallback (for when Redis is unavailable)
_memory_blacklist: Dict[str, datetime] = {}


# ---------------------------------------------------------------------------
# Cookie configuration
# ---------------------------------------------------------------------------
COOKIE_ACCESS_NAME = "access_token"
COOKIE_REFRESH_NAME = "refresh_token"
COOKIE_CSRF_NAME = "csrf_token"
COOKIE_SECURE = not settings.debug  # Secure=True in production
COOKIE_DOMAIN = None  # Use default (current domain)
COOKIE_SAMESITE = "lax"
ACCESS_TOKEN_MAX_AGE = settings.access_token_expire_minutes * 60  # in seconds
REFRESH_TOKEN_MAX_AGE = 7 * 24 * 60 * 60  # 7 days in seconds


def create_refresh_token(data: dict[str, Any]) -> str:
    """Create a long-lived refresh JWT token (7 days)."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=7)
    to_encode.update({
        "exp": expire,
        "iat": now,
        "jti": secrets.token_urlsafe(16),
        "purpose": "refresh",
    })
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_refresh_token(token: str) -> dict[str, Any] | None:
    """Decode and validate a refresh token. Returns payload or None."""
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
            options={"require_exp": True}
        )
        if payload.get("purpose") != "refresh":
            return None
        jti = payload.get("jti")
        if jti and _is_token_blacklisted(jti):
            return None
        return payload
    except PyJWTError:
        return None


def generate_csrf_token() -> str:
    """Generate a random CSRF token."""
    return secrets.token_urlsafe(32)


def generate_pin_reset_token(user_id: int) -> str:
    """Generate a time-limited PIN reset token (valid for 15 minutes)."""
    return jwt.encode(
        {
            "sub": str(user_id),
            "purpose": "pin_reset",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
            "jti": secrets.token_urlsafe(16),
        },
        settings.secret_key,
        algorithm=settings.algorithm,
    )


def verify_pin_reset_token(token: str) -> Optional[int]:
    """Verify a PIN reset token. Returns user_id if valid, None otherwise."""
    try:
        payload = jwt.decode(
            token, settings.secret_key,
            algorithms=[settings.algorithm],
            options={"require_exp": True},
        )
        if payload.get("purpose") != "pin_reset":
            return None
        return int(payload["sub"])
    except (PyJWTError, KeyError, ValueError):
        return None

"""Security utilities: JWT tokens, password hashing, and session management."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import logging

from jose import JWTError, jwt
import bcrypt

from app.core.config import settings

logger = logging.getLogger(__name__)


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
    except JWTError as e:
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
    except JWTError:
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
    except Exception:
        pass

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
    except (JWTError, KeyError, ValueError):
        return None

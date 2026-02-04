"""Security utilities: JWT tokens and password hashing."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import logging

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hash.

    Uses bcrypt's built-in timing-safe comparison.
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.warning(f"Password verification error: {e}")
        return False


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_pin(plain_pin: str, hashed_pin: str) -> bool:
    """Verify a plain PIN against a hash.

    Uses bcrypt's built-in timing-safe comparison.
    """
    try:
        return pwd_context.verify(plain_pin, hashed_pin)
    except Exception as e:
        logger.warning(f"PIN verification error: {e}")
        return False


def get_pin_hash(pin: str) -> str:
    """Hash a PIN code using bcrypt."""
    return pwd_context.hash(pin)


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token.

    Uses timezone-aware UTC datetime for expiration.
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)

    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({
        "exp": expire,
        "iat": now,  # Issued at time
    })
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode and validate a JWT token.

    Returns the payload if valid, None if invalid or expired.
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
            options={"require_exp": True}
        )
        return payload
    except JWTError as e:
        logger.debug(f"JWT decode error: {e}")
        return None

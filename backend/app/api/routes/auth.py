"""Authentication routes."""

import logging
import secrets
import time
from collections import defaultdict
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger("auth")

# PIN brute-force lockout: track failed attempts per IP
_pin_failures: dict[str, list[float]] = defaultdict(list)
PIN_LOCKOUT_WINDOW = 300  # 5-minute window
PIN_MAX_FAILURES = 10  # Lock after 10 failures in window

from app.core.rbac import CurrentUser
from app.core.security import create_access_token, get_password_hash, get_pin_hash, verify_password, verify_pin
from app.db.session import DbSession
from app.models.user import User
from app.schemas.auth import LoginRequest, PinLoginRequest, Token
from app.schemas.user import UserCreate, UserResponse
from app.services.audit_service import log_login

router = APIRouter()

# Rate limiter for auth endpoints (stricter limits)
limiter = Limiter(key_func=get_remote_address)


# Pydantic schemas for typed endpoints
class SetPinRequest(BaseModel):
    """Request schema for setting user PIN."""
    pin_code: str = Field(..., min_length=4, max_length=6, pattern=r"^\d{4,6}$")


# Security: Add constant-time delay to prevent timing attacks
MIN_AUTH_DELAY_MS = 100  # Minimum delay in milliseconds


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
def login(request: Request, login_request: LoginRequest, db: DbSession):
    """Authenticate user and return JWT token."""
    client_ip = request.client.host if request.client else "unknown"
    user = db.query(User).filter(User.email == login_request.email).first()

    if not user or not verify_password(login_request.password, user.password_hash):
        logger.warning(f"Failed login attempt for email: {login_request.email} from IP: {client_ip}")
        log_login(user_id=0, email=login_request.email, ip_address=client_ip, success=False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        logger.warning(f"Login attempt for inactive user: {login_request.email} (ID: {user.id}) from IP: {client_ip}")
        log_login(user_id=user.id, email=login_request.email, ip_address=client_ip, success=False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
        )

    logger.info(f"Successful login: {user.email} (ID: {user.id}, role: {user.role.value}) from IP: {client_ip}")
    log_login(user_id=user.id, email=user.email, ip_address=client_ip, success=True)
    token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role.value}
    )
    return Token(access_token=token)


@router.post("/login/pin", response_model=Token)
@limiter.limit("5/minute")
def login_with_pin(request: Request, pin_request: PinLoginRequest, db: DbSession):
    """Authenticate user with PIN code.

    Uses constant-time comparison to prevent timing attacks.
    """
    start_time = time.monotonic()
    client_ip = request.client.host if request.client else "unknown"

    # Check PIN brute-force lockout
    now = time.monotonic()
    _pin_failures[client_ip] = [t for t in _pin_failures[client_ip] if now - t < PIN_LOCKOUT_WINDOW]
    if len(_pin_failures[client_ip]) >= PIN_MAX_FAILURES:
        logger.warning(f"PIN login locked out for IP: {client_ip} ({len(_pin_failures[client_ip])} failures)")
        _ensure_min_delay(start_time)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed PIN attempts. Try again in 5 minutes.",
        )

    # Validate PIN format (4-6 digits)
    if not pin_request.pin or not pin_request.pin.isdigit() or len(pin_request.pin) < 4 or len(pin_request.pin) > 6:
        logger.warning(f"Invalid PIN format attempt from IP: {client_ip}")
        # Add delay before responding to prevent timing-based format detection
        _ensure_min_delay(start_time)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PIN must be 4-6 digits",
        )

    # Authenticate against database users only
    # Query all active users with a PIN set
    users_with_pin = db.query(User).filter(
        User.pin_hash.isnot(None),
        User.is_active == True
    ).all()

    # Use constant-time comparison to prevent timing attacks
    # We check ALL users' PINs regardless of whether we find a match
    user = None
    found_match = False
    dummy_hash = get_pin_hash("0000")  # For constant-time comparison when no users

    for u in users_with_pin:
        # verify_pin uses bcrypt which has built-in timing protection
        is_match = verify_pin(pin_request.pin, u.pin_hash)
        if is_match and not found_match:
            user = u
            found_match = True
        # Continue checking all users to maintain constant time

    # If no users with PIN, still do a dummy comparison for timing consistency
    if not users_with_pin:
        verify_pin(pin_request.pin, dummy_hash)

    # Ensure minimum response time to prevent timing attacks
    _ensure_min_delay(start_time)

    if not user:
        _pin_failures[client_ip].append(time.monotonic())
        logger.warning(f"Failed PIN login attempt from IP: {client_ip} (attempt {len(_pin_failures[client_ip])})")
        log_login(user_id=0, email="pin_login", ip_address=client_ip, success=False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid PIN",
        )

    # Clear lockout on successful login
    _pin_failures.pop(client_ip, None)
    logger.info(f"Successful PIN login: {user.email} (ID: {user.id}, role: {user.role.value}) from IP: {client_ip}")
    log_login(user_id=user.id, email=user.email, ip_address=client_ip, success=True)
    token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role.value}
    )
    return Token(access_token=token)


def _ensure_min_delay(start_time: float):
    """Ensure minimum delay has elapsed to prevent timing attacks."""
    elapsed_ms = (time.monotonic() - start_time) * 1000
    if elapsed_ms < MIN_AUTH_DELAY_MS:
        time.sleep((MIN_AUTH_DELAY_MS - elapsed_ms) / 1000)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(request: Request, user_create: UserCreate, db: DbSession):
    """Register a new user (for initial setup only)."""
    client_ip = request.client.host if request.client else "unknown"

    # Check if any users exist (only allow registration if no users)
    existing_user = db.query(User).first()
    if existing_user:
        logger.warning(f"Registration attempt blocked (users exist) from IP: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registration is closed. Contact administrator.",
        )

    # Create first user as owner
    user = User(
        email=user_create.email,
        password_hash=get_password_hash(user_create.password),
        name=user_create.name,
        role=user_create.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info(f"New user registered: {user.email} (ID: {user.id}, role: {user.role.value}) from IP: {client_ip}")
    return user


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: CurrentUser, db: DbSession):
    """Get current authenticated user info."""
    user = db.query(User).filter(User.id == current_user.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.post("/me/pin")
def set_user_pin(current_user: CurrentUser, db: DbSession, data: SetPinRequest):
    """Set or update PIN for current user.

    PIN must be 4-6 digits.
    """
    user = db.query(User).filter(User.id == current_user.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.pin_hash = get_pin_hash(data.pin_code)
    db.commit()
    logger.info(f"PIN set for user: {user.email} (ID: {user.id})")
    return {"message": "PIN set successfully"}


@router.delete("/me/pin")
def clear_user_pin(current_user: CurrentUser, db: DbSession):
    """Clear PIN for current user."""
    user = db.query(User).filter(User.id == current_user.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.pin_hash = None
    db.commit()
    logger.info(f"PIN cleared for user: {user.email} (ID: {user.id})")
    return {"message": "PIN cleared successfully"}

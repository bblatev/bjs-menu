"""Authentication routes."""

import logging
import secrets
import time
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger("auth")

# PIN brute-force lockout: track failed attempts per IP
# Uses database-backed storage so lockout persists across restarts
PIN_LOCKOUT_WINDOW = 300  # 5-minute window
PIN_MAX_FAILURES = 10  # Lock after 10 failures in window


def _get_pin_failures(db, client_ip: str) -> int:
    """Get count of recent PIN failures for an IP from the database."""
    from app.models.operations import AppSetting
    from datetime import datetime, timezone, timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=PIN_LOCKOUT_WINDOW)
    cutoff_ts = cutoff.timestamp()
    key = f"pin_lockout:{client_ip}"
    record = db.query(AppSetting).filter(
        AppSetting.category == "security", AppSetting.key == key
    ).first()
    if not record or not record.value:
        return 0
    try:
        data = record.value if isinstance(record.value, dict) else {}
        failures = [t for t in data.get("timestamps", []) if t > cutoff_ts]
        return len(failures)
    except (TypeError, AttributeError):
        return 0


def _record_pin_failure(db, client_ip: str):
    """Record a PIN failure for an IP in the database."""
    from app.models.operations import AppSetting
    from datetime import datetime, timezone, timedelta
    key = f"pin_lockout:{client_ip}"
    now_ts = datetime.now(timezone.utc).timestamp()
    cutoff_ts = (datetime.now(timezone.utc) - timedelta(seconds=PIN_LOCKOUT_WINDOW)).timestamp()
    record = db.query(AppSetting).filter(
        AppSetting.category == "security", AppSetting.key == key
    ).first()
    if record:
        try:
            data = record.value if isinstance(record.value, dict) else {}
            timestamps = [t for t in data.get("timestamps", []) if t > cutoff_ts]
        except (TypeError, AttributeError):
            timestamps = []
        timestamps.append(now_ts)
        record.value = {"timestamps": timestamps}
    else:
        record = AppSetting(
            category="security", key=key, value={"timestamps": [now_ts]}
        )
        db.add(record)
    db.commit()


def _clear_pin_failures(db, client_ip: str):
    """Clear PIN failures for an IP on successful login."""
    from app.models.operations import AppSetting
    key = f"pin_lockout:{client_ip}"
    db.query(AppSetting).filter(
        AppSetting.category == "security", AppSetting.key == key
    ).delete()
    db.commit()


from app.core.rbac import CurrentUser, RequireManager
from app.core.security import (
    create_access_token, create_refresh_token, decode_refresh_token,
    get_password_hash, get_pin_hash,
    verify_password, verify_pin, blacklist_token,
    generate_pin_reset_token, verify_pin_reset_token,
    generate_csrf_token,
    COOKIE_ACCESS_NAME, COOKIE_REFRESH_NAME, COOKIE_CSRF_NAME,
    COOKIE_SECURE, COOKIE_DOMAIN, COOKIE_SAMESITE,
    ACCESS_TOKEN_MAX_AGE, REFRESH_TOKEN_MAX_AGE,
)
from app.db.session import DbSession
from app.models.user import User
from app.schemas.auth import LoginRequest, PinLoginRequest, Token
from app.schemas.user import UserCreate, UserResponse
from app.services.audit_service import log_login

from app.core.rate_limit import limiter

router = APIRouter()


# Pydantic schemas for typed endpoints
class SetPinRequest(BaseModel):
    """Request schema for setting user PIN."""
    pin_code: str = Field(..., min_length=4, max_length=6, pattern=r"^\d{4,6}$")


class ChangePasswordRequest(BaseModel):
    """Request schema for changing user password."""
    old_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


# Security: Add constant-time delay to prevent timing attacks
MIN_AUTH_DELAY_MS = 100  # Minimum delay in milliseconds


def _set_auth_cookies(response: JSONResponse, user: "User") -> JSONResponse:
    """Set HttpOnly auth cookies on a response after successful login."""
    token_data = {"sub": str(user.id), "email": user.email, "role": user.role.value}
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data=token_data)
    csrf_token = generate_csrf_token()

    # HttpOnly access token (4 hours)
    response.set_cookie(
        key=COOKIE_ACCESS_NAME,
        value=access_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        domain=COOKIE_DOMAIN,
        max_age=ACCESS_TOKEN_MAX_AGE,
        path="/",
    )
    # HttpOnly refresh token (7 days) — restricted to refresh endpoint
    response.set_cookie(
        key=COOKIE_REFRESH_NAME,
        value=refresh_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="strict",
        domain=COOKIE_DOMAIN,
        max_age=REFRESH_TOKEN_MAX_AGE,
        path="/api/v1/auth/refresh",
    )
    # CSRF token (readable by JS, not HttpOnly)
    response.set_cookie(
        key=COOKIE_CSRF_NAME,
        value=csrf_token,
        httponly=False,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        domain=COOKIE_DOMAIN,
        max_age=ACCESS_TOKEN_MAX_AGE,
        path="/",
    )
    return response


@router.post("/login")
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
    # Return token in body for API clients; also set cookies for browser clients
    response = JSONResponse(content={"access_token": token, "token_type": "bearer"})
    _set_auth_cookies(response, user)
    return response


@router.post("/login/pin")
@limiter.limit("5/minute")
def login_with_pin(request: Request, pin_request: PinLoginRequest, db: DbSession):
    """Authenticate user with PIN code.

    Uses constant-time comparison to prevent timing attacks.
    """
    start_time = time.monotonic()
    client_ip = request.client.host if request.client else "unknown"

    # Check PIN brute-force lockout (database-backed, persists across restarts)
    failure_count = _get_pin_failures(db, client_ip)
    if failure_count >= PIN_MAX_FAILURES:
        logger.warning(f"PIN login locked out for IP: {client_ip} ({failure_count} failures)")
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
        _record_pin_failure(db, client_ip)
        updated_count = _get_pin_failures(db, client_ip)
        logger.warning(f"Failed PIN login attempt from IP: {client_ip} (attempt {updated_count})")
        log_login(user_id=0, email="pin_login", ip_address=client_ip, success=False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid PIN",
        )

    # Clear lockout on successful login
    _clear_pin_failures(db, client_ip)
    logger.info(f"Successful PIN login: {user.email} (ID: {user.id}, role: {user.role.value}) from IP: {client_ip}")
    log_login(user_id=user.id, email=user.email, ip_address=client_ip, success=True)
    token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role.value}
    )
    response = JSONResponse(content={"access_token": token, "token_type": "bearer"})
    _set_auth_cookies(response, user)
    return response


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
@limiter.limit("60/minute")
def get_current_user_info(request: Request, current_user: CurrentUser, db: DbSession):
    """Get current authenticated user info."""
    user = db.query(User).filter(User.id == current_user.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.post("/me/pin")
@limiter.limit("30/minute")
def set_user_pin(request: Request, current_user: CurrentUser, db: DbSession, data: SetPinRequest):
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
@limiter.limit("30/minute")
def clear_user_pin(request: Request, current_user: CurrentUser, db: DbSession):
    """Clear PIN for current user."""
    user = db.query(User).filter(User.id == current_user.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.pin_hash = None
    db.commit()
    logger.info(f"PIN cleared for user: {user.email} (ID: {user.id})")
    return {"message": "PIN cleared successfully"}


# ===== Session Management =====

@router.post("/logout")
@limiter.limit("30/minute")
def logout(request: Request, current_user: CurrentUser):
    """Invalidate the current JWT token (logout) and clear auth cookies."""
    # Blacklist access token from header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        blacklist_token(token)

    # Blacklist access token from cookie
    cookie_token = request.cookies.get(COOKIE_ACCESS_NAME)
    if cookie_token:
        blacklist_token(cookie_token)

    # Blacklist refresh token from cookie
    refresh_token = request.cookies.get(COOKIE_REFRESH_NAME)
    if refresh_token:
        blacklist_token(refresh_token)

    logger.info(f"User logged out: {current_user.email} (ID: {current_user.user_id})")

    response = JSONResponse(content={"message": "Logged out successfully"})
    # Clear all auth cookies
    response.delete_cookie(COOKIE_ACCESS_NAME, path="/", domain=COOKIE_DOMAIN)
    response.delete_cookie(COOKIE_REFRESH_NAME, path="/api/v1/auth/refresh", domain=COOKIE_DOMAIN)
    response.delete_cookie(COOKIE_CSRF_NAME, path="/", domain=COOKIE_DOMAIN)
    return response


@router.post("/refresh")
@limiter.limit("10/minute")
def refresh_tokens(request: Request):
    """Use refresh token to get new access + refresh tokens.

    The refresh token is sent automatically via HttpOnly cookie
    (the cookie path is restricted to /api/v1/auth/refresh).
    """
    refresh_tok = request.cookies.get(COOKIE_REFRESH_NAME)
    if not refresh_tok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token",
        )

    payload = decode_refresh_token(refresh_tok)
    if not payload:
        # Clear stale cookies
        response = JSONResponse(
            status_code=401,
            content={"detail": "Invalid or expired refresh token"},
        )
        response.delete_cookie(COOKIE_REFRESH_NAME, path="/api/v1/auth/refresh", domain=COOKIE_DOMAIN)
        return response

    # Blacklist the old refresh token (rotation)
    blacklist_token(refresh_tok)

    # Issue new tokens
    token_data = {
        "sub": payload["sub"],
        "email": payload.get("email", ""),
        "role": payload.get("role", "staff"),
    }
    new_access = create_access_token(data=token_data)
    new_refresh = create_refresh_token(data=token_data)
    csrf_token = generate_csrf_token()

    response = JSONResponse(content={"access_token": new_access, "token_type": "bearer"})
    response.set_cookie(
        key=COOKIE_ACCESS_NAME, value=new_access,
        httponly=True, secure=COOKIE_SECURE, samesite=COOKIE_SAMESITE,
        domain=COOKIE_DOMAIN, max_age=ACCESS_TOKEN_MAX_AGE, path="/",
    )
    response.set_cookie(
        key=COOKIE_REFRESH_NAME, value=new_refresh,
        httponly=True, secure=COOKIE_SECURE, samesite="strict",
        domain=COOKIE_DOMAIN, max_age=REFRESH_TOKEN_MAX_AGE, path="/api/v1/auth/refresh",
    )
    response.set_cookie(
        key=COOKIE_CSRF_NAME, value=csrf_token,
        httponly=False, secure=COOKIE_SECURE, samesite=COOKIE_SAMESITE,
        domain=COOKIE_DOMAIN, max_age=ACCESS_TOKEN_MAX_AGE, path="/",
    )
    return response


# ===== PIN Recovery =====

class PinResetRequestModel(BaseModel):
    """Request to initiate PIN reset (manager/owner action)."""
    user_id: int = Field(..., description="User ID whose PIN to reset")


class PinResetConfirmModel(BaseModel):
    """Confirm PIN reset with token."""
    reset_token: str = Field(..., description="PIN reset token from manager")
    new_pin: str = Field(..., min_length=4, max_length=6, pattern=r"^\d{4,6}$")


@router.post("/pin-reset/request")
@limiter.limit("10/minute")
def request_pin_reset(
    request: Request,
    data: PinResetRequestModel,
    current_user: RequireManager,
    db: DbSession,
):
    """Manager/Owner initiates PIN reset for a locked-out user.

    Returns a time-limited reset token (valid for 15 minutes) that the
    user can use to set a new PIN.
    """
    target_user = db.query(User).filter(User.id == data.user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    reset_token = generate_pin_reset_token(target_user.id)

    # Clear lockout for the target user's IP (best-effort)
    from app.models.operations import AppSetting
    db.query(AppSetting).filter(
        AppSetting.category == "security",
        AppSetting.key.like(f"pin_lockout:%"),
    ).delete(synchronize_session=False)
    db.commit()

    logger.info(
        f"PIN reset requested for user {target_user.email} (ID: {target_user.id}) "
        f"by {current_user.email} (ID: {current_user.user_id})"
    )
    return {
        "message": f"PIN reset token generated for {target_user.email}",
        "reset_token": reset_token,
        "expires_in_minutes": 15,
    }


@router.post("/pin-reset/confirm")
@limiter.limit("5/minute")
def confirm_pin_reset(request: Request, data: PinResetConfirmModel, db: DbSession):
    """User confirms PIN reset using the token from their manager.

    No existing authentication required - the reset token serves as proof.
    """
    user_id = verify_pin_reset_token(data.reset_token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.pin_hash = get_pin_hash(data.new_pin)
    db.commit()

    logger.info(f"PIN reset completed for user: {user.email} (ID: {user.id})")
    return {"message": "PIN reset successfully. You can now log in with your new PIN."}


@router.post("/change-password")
@limiter.limit("5/minute")
def change_password(
    request: Request,
    current_user: CurrentUser,
    db: DbSession,
    data: ChangePasswordRequest,
):
    """Change password for the current user."""
    user = db.query(User).filter(User.id == current_user.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(data.old_password, user.password_hash):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    user.password_hash = get_password_hash(data.new_password)
    db.commit()

    # Blacklist current token to force re-login
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        blacklist_token(auth_header.split(" ", 1)[1])

    logger.info(f"Password changed for user: {user.email} (ID: {user.id})")
    return {"message": "Password changed. Please log in again."}

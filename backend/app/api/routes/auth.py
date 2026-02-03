"""Authentication routes."""

from fastapi import APIRouter, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.rbac import CurrentUser
from app.core.security import create_access_token, get_password_hash, verify_password
from app.db.session import DbSession
from app.models.user import User
from app.schemas.auth import LoginRequest, PinLoginRequest, Token
from app.schemas.user import UserCreate, UserResponse

router = APIRouter()

# Rate limiter for auth endpoints (stricter limits)
limiter = Limiter(key_func=get_remote_address)


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
def login(request: Request, login_request: LoginRequest, db: DbSession):
    """Authenticate user and return JWT token."""
    user = db.query(User).filter(User.email == login_request.email).first()
    if not user or not verify_password(login_request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
        )

    token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role.value}
    )
    return Token(access_token=token)


@router.post("/login/pin", response_model=Token)
@limiter.limit("10/minute")
def login_with_pin(request: Request, pin_request: PinLoginRequest, db: DbSession):
    """Authenticate user with PIN code."""
    # Validate PIN format (4-6 digits)
    if not pin_request.pin or not pin_request.pin.isdigit() or len(pin_request.pin) < 4 or len(pin_request.pin) > 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PIN must be 4-6 digits",
        )

    # Authenticate against database users only
    user = db.query(User).filter(User.pin == pin_request.pin).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid PIN",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
        )

    token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role.value}
    )
    return Token(access_token=token)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(request: Request, user_create: UserCreate, db: DbSession):
    """Register a new user (for initial setup only)."""
    # Check if any users exist (only allow registration if no users)
    existing_user = db.query(User).first()
    if existing_user:
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
    return user


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: CurrentUser, db: DbSession):
    """Get current authenticated user info."""
    user = db.query(User).filter(User.id == current_user.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

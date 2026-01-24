"""Authentication routes."""

from fastapi import APIRouter, HTTPException, status

from app.core.rbac import CurrentUser
from app.core.security import create_access_token, get_password_hash, verify_password
from app.db.session import DbSession
from app.models.user import User
from app.schemas.auth import LoginRequest, PinLoginRequest, Token
from app.schemas.user import UserCreate, UserResponse

router = APIRouter()


@router.post("/login", response_model=Token)
def login(request: LoginRequest, db: DbSession):
    """Authenticate user and return JWT token."""
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not verify_password(request.password, user.password_hash):
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
def login_with_pin(request: PinLoginRequest, db: DbSession):
    """Authenticate user with PIN code."""
    # Default PINs for demo/testing (waiter terminals)
    default_pins = {
        "1234": {"id": 1, "email": "waiter@bjs.bar", "role": "staff"},
        "0000": {"id": 2, "email": "manager@bjs.bar", "role": "manager"},
        "9999": {"id": 3, "email": "admin@bjs.bar", "role": "owner"},
    }

    # Check default PINs first
    if request.pin in default_pins:
        user_data = default_pins[request.pin]
        token = create_access_token(
            data={"sub": str(user_data["id"]), "email": user_data["email"], "role": user_data["role"]}
        )
        return Token(access_token=token)

    # Then check database users
    user = db.query(User).filter(User.pin == request.pin).first()
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
def register(request: UserCreate, db: DbSession):
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
        email=request.email,
        password_hash=get_password_hash(request.password),
        name=request.name,
        role=request.role,
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

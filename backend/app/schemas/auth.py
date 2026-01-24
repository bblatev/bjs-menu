"""Authentication schemas."""

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """Login request body."""

    email: EmailStr
    password: str


class PinLoginRequest(BaseModel):
    """PIN login request body."""

    pin: str


class Token(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """JWT token payload."""

    sub: str
    email: str
    role: str
    exp: int

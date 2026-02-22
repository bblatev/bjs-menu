"""Authentication schemas."""

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Login request body."""

    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class PinLoginRequest(BaseModel):
    """PIN login request body."""

    pin: str = Field(..., min_length=4, max_length=8)


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

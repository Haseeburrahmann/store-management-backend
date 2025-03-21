"""
Auth schema models for validation.
"""
from typing import Optional
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """Schema for login request."""
    email: EmailStr
    password: str


class Token(BaseModel):
    """Schema for authentication token."""
    access_token: str
    token_type: str


class TokenPayload(BaseModel):
    """Schema for token payload."""
    sub: Optional[str] = None
    exp: Optional[int] = None
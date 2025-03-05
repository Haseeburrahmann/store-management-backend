# app/schemas/user.py
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

class UserCreate(BaseModel):
    """Schema for creating users"""
    email: EmailStr
    full_name: str
    password: str
    phone_number: Optional[str] = None
    role_id: Optional[str] = None
    is_active: bool = True

class UserUpdate(BaseModel):
    """Schema for updating users"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    password: Optional[str] = None
    role_id: Optional[str] = None
    is_active: Optional[bool] = None

class UserResponse(BaseModel):
    """Schema for user responses"""
    id: str = Field(..., alias="_id")
    email: EmailStr
    full_name: str
    phone_number: Optional[str] = None
    role_id: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }

class UserWithPermissions(UserResponse):
    """Schema for user with permissions"""
    permissions: List[str] = []

class Token(BaseModel):
    """Schema for authentication token"""
    access_token: str
    token_type: str

class TokenPayload(BaseModel):
    """Schema for token payload"""
    sub: Optional[str] = None
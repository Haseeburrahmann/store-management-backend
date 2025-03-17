"""
User schema models for validation.
"""
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime


class UserBase(BaseModel):
    """Base user schema with common fields."""
    email: EmailStr
    full_name: str
    phone_number: Optional[str] = None
    is_active: bool = True


class UserCreate(UserBase):
    """Schema for creating users."""
    password: str
    role_id: Optional[str] = None


class UserUpdate(BaseModel):
    """Schema for updating users."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    password: Optional[str] = None
    role_id: Optional[str] = None
    is_active: Optional[bool] = None

    model_config = {
        "extra": "ignore"
    }


class UserResponse(UserBase):
    """Schema for user responses."""
    id: str = Field(..., alias="_id")
    role_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {
            datetime: lambda v: v.isoformat()
        }
    }


class UserWithPermissions(UserResponse):
    """Schema for user with permissions."""
    permissions: List[str] = []
    role_name: Optional[str] = None
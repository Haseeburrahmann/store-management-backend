"""
Store schema models for validation.
"""
from typing import Optional
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime


class StoreBase(BaseModel):
    """Base store schema with common fields."""
    name: str
    address: str
    city: str
    state: str
    zip_code: str
    phone: str
    email: Optional[EmailStr] = None
    is_active: bool = True


class StoreCreate(StoreBase):
    """Schema for creating stores."""
    manager_id: Optional[str] = None


class StoreUpdate(BaseModel):
    """Schema for updating stores."""
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    manager_id: Optional[str] = None
    is_active: Optional[bool] = None

    model_config = {
        "extra": "ignore"
    }


class StoreResponse(StoreBase):
    """Schema for store responses."""
    id: str = Field(..., alias="_id")
    manager_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {
            datetime: lambda v: v.isoformat()
        }
    }


class StoreWithManager(StoreResponse):
    """Schema for store with manager info."""
    manager_name: Optional[str] = None
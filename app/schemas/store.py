# app/schemas/store.py - Fixed StoreUpdate schema

from typing import Optional
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime


class StoreCreate(BaseModel):
    """Schema for creating stores"""
    name: str
    address: str
    city: str
    state: str
    zip_code: str
    phone: str
    email: Optional[EmailStr] = None
    manager_id: Optional[str] = None
    is_active: bool = True


class StoreUpdate(BaseModel):
    """Schema for updating stores"""
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    manager_id: Optional[str] = None
    is_active: Optional[bool] = None

    class Config:
        # Allow processing partial updates correctly
        extra = "ignore"
        json_schema_extra = {
            "example": {
                "city": "Chicago",
                "is_active": True
            }
        }


class StoreResponse(BaseModel):
    """Schema for store responses"""
    id: str = Field(..., alias="_id")
    name: str
    address: str
    city: str
    state: str
    zip_code: str
    phone: str
    email: Optional[EmailStr] = None
    manager_id: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }


class StoreWithManager(StoreResponse):
    """Schema for store with manager details"""
    manager_name: Optional[str] = None
"""
Role schema models for validation.
"""
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class RoleBase(BaseModel):
    """Base role schema with common fields."""
    name: str
    description: Optional[str] = None


class RoleCreate(RoleBase):
    """Schema for creating roles."""
    permissions: List[str] = []


class RoleUpdate(BaseModel):
    """Schema for updating roles."""
    name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[List[str]] = None

    model_config = {
        "extra": "ignore"
    }


class RoleResponse(RoleBase):
    """Schema for role responses."""
    id: str = Field(..., alias="_id")
    permissions: List[str]
    created_at: datetime
    updated_at: datetime

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {
            datetime: lambda v: v.isoformat()
        }
    }
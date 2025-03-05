# app/schemas/role.py
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class RoleCreate(BaseModel):
    """Schema for creating roles"""
    name: str
    description: Optional[str] = None
    permissions: List[str] = []

class RoleUpdate(BaseModel):
    """Schema for updating roles"""
    name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[List[str]] = None

class RoleResponse(BaseModel):
    """Schema for role responses"""
    id: str = Field(..., alias="_id")
    name: str
    description: Optional[str] = None
    permissions: List[str]
    created_at: datetime
    updated_at: datetime

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }
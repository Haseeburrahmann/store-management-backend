# app/models/role.py
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from bson import ObjectId
from app.utils.object_id import PyObjectId

class RoleModel(BaseModel):
    """Database model for roles"""
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    name: str
    description: Optional[str] = None
    permissions: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_schema_extra": {
            "example": {
                "name": "Admin",
                "description": "Administrator with all permissions",
                "permissions": ["users:read", "users:write", "roles:read", "roles:write"]
            }
        }
    }
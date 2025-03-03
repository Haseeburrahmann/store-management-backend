from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from bson import ObjectId


# Custom type for handling ObjectId
class PyObjectId(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return str(v)

    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type, _handler):
        return {
            "type": "string",
            "description": "ObjectId"
        }


class RoleModel(BaseModel):
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


class RoleDB(RoleModel):
    """Role model for database operations"""
    pass


class RoleOut(BaseModel):
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
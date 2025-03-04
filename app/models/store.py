# app/models/store.py
from typing import Optional
from datetime import datetime
from bson import ObjectId
from pydantic import Field, BaseModel

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

class Store(BaseModel):
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    name: str
    address: str
    city: str
    state: str
    zip_code: str
    phone: str
    email: Optional[str] = None
    manager_id: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_schema_extra": {
            "example": {
                "name": "Downtown Store",
                "address": "123 Main St",
                "city": "New York",
                "state": "NY",
                "zip_code": "10001",
                "phone": "555-123-4567",
                "email": "downtown@example.com",
                "is_active": True
            }
        }
    }

class StoreDB(Store):
    """Store model for database operations"""
    pass

class StoreOut(BaseModel):
    id: str = Field(..., alias="_id")
    name: str
    address: str
    city: str
    state: str
    zip_code: str
    phone: str
    email: Optional[str] = None
    manager_id: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }
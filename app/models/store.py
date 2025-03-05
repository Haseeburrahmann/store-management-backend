# app/models/store.py
from typing import Optional
from datetime import datetime
from bson import ObjectId
from pydantic import Field, BaseModel, EmailStr
from app.utils.object_id import PyObjectId

class StoreModel(BaseModel):
    """Database model for stores"""
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    name: str
    address: str
    city: str
    state: str
    zip_code: str
    phone: str
    email: Optional[EmailStr] = None
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
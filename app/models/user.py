# app/models/user.py
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from bson import ObjectId
from app.utils.object_id import PyObjectId

class UserModel(BaseModel):
    """Database model for users"""
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    email: EmailStr
    full_name: str
    password: str
    phone_number: Optional[str] = None
    role_id: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_schema_extra": {
            "example": {
                "email": "user@example.com",
                "password": "password123",
                "full_name": "John Doe",
                "phone_number": "1234567890",
                "is_active": True
            }
        }
    }
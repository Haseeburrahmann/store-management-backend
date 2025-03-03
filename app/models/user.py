from typing import Optional, List
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


class UserModel(BaseModel):
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    email: str
    password: str
    full_name: str
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


class UserDB(UserModel):
    """User model for database operations"""
    pass


class UserOut(BaseModel):
    id: str = Field(..., alias="_id")
    email: str
    full_name: str
    phone_number: Optional[str] = None
    role_id: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }



# app/models/store.py
from typing import Optional
from datetime import datetime
from bson import ObjectId
from pydantic import Field, BaseModel, EmailStr, validator
from app.utils.object_id import PyObjectId


class StoreModel(BaseModel):
    """Database model for stores with enhanced validation"""
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

    @validator('manager_id')
    def validate_manager_id(cls, v):
        """
        Validate that manager_id looks like a valid ID
        This is a basic validation - full validation happens in the service
        """
        if v is None:
            return v

        # Check if looks like a valid ObjectId
        if len(v) == 24 and all(c in '0123456789abcdefABCDEF' for c in v):
            return v

        # Check if it's in a format we expect for our app
        if v.startswith("EMP-") or v.startswith("USR-"):
            return v

        # If it doesn't match our expected formats, reject it
        raise ValueError("manager_id must be a valid ObjectId string or application-specific ID format")

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
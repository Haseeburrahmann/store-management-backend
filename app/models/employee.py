# app/models/employee.py
from datetime import datetime
from typing import Optional
from bson import ObjectId
from pydantic import Field, EmailStr, BaseModel
from app.utils.object_id import PyObjectId

class EmployeeModel(BaseModel):
    """Database model for employees"""
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    user_id: Optional[str] = None
    position: str
    hire_date: datetime = Field(default_factory=datetime.utcnow)
    store_id: Optional[str] = None
    hourly_rate: float
    employment_status: str = "active"  # active, on_leave, terminated
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_schema_extra": {
            "example": {
                "user_id": "60d21b4967d0d8992e610c85",
                "position": "Cashier",
                "hourly_rate": 15.50,
                "employment_status": "active",
                "emergency_contact_name": "Jane Doe",
                "emergency_contact_phone": "555-987-6543"
            }
        }
    }
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from bson import ObjectId
from app.utils.object_id import PyObjectId

class HoursStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class HoursModel(BaseModel):
    """Database model for hours records"""
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    employee_id: str
    store_id: str
    clock_in: datetime
    clock_out: Optional[datetime] = None
    break_start: Optional[datetime] = None
    break_end: Optional[datetime] = None
    total_minutes: Optional[int] = None
    status: HoursStatus = HoursStatus.PENDING
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
        "json_schema_extra": {
            "example": {
                "employee_id": "60d21b4967d0d8992e610c85",
                "store_id": "60d21b4967d0d8992e610c86",
                "clock_in": "2023-06-01T09:00:00",
                "clock_out": "2023-06-01T17:30:00",
                "break_start": "2023-06-01T12:00:00",
                "break_end": "2023-06-01T12:30:00",
                "total_minutes": 480,
                "status": "pending",
                "notes": "Regular shift"
            }
        }
    }
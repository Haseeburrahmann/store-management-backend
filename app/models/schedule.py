# app/models/schedule.py
from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field
from bson import ObjectId
from app.utils.object_id import PyObjectId


class ScheduleShiftModel(BaseModel):
    """Database model for schedule shifts"""
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    employee_id: str
    date: str  # ISO date string YYYY-MM-DD
    start_time: str  # Time in format HH:MM (24-hour)
    end_time: str  # Time in format HH:MM (24-hour)
    notes: Optional[str] = None

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
        "json_schema_extra": {
            "example": {
                "employee_id": "60d21b4967d0d8992e610c85",
                "date": "2023-06-01",
                "start_time": "09:00",
                "end_time": "17:00",
                "notes": "Regular shift"
            }
        }
    }


class ScheduleModel(BaseModel):
    """Database model for schedules"""
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    title: str
    store_id: str
    start_date: str  # ISO date string YYYY-MM-DD
    end_date: str  # ISO date string YYYY-MM-DD
    shifts: List[ScheduleShiftModel] = []
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
        "json_schema_extra": {
            "example": {
                "title": "Weekly Schedule",
                "store_id": "60d21b4967d0d8992e610c86",
                "start_date": "2023-06-01",
                "end_date": "2023-06-07",
                "created_by": "60d21b4967d0d8992e610c87"
            }
        }
    }
# app/models/timesheet.py
from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field
from bson import ObjectId
from app.utils.object_id import PyObjectId


class TimesheetStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"


class WeeklyTimesheetModel(BaseModel):
    """Database model for weekly timesheets"""
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    employee_id: str
    store_id: str
    week_start_date: str  # ISO date string YYYY-MM-DD
    week_end_date: str  # ISO date string YYYY-MM-DD
    time_entries: List[str] = []  # Array of TimeEntry IDs
    total_hours: float
    status: TimesheetStatus = TimesheetStatus.DRAFT
    submitted_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
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
                "week_start_date": "2023-06-04",
                "week_end_date": "2023-06-10",
                "time_entries": ["60d21b4967d0d8992e610c88", "60d21b4967d0d8992e610c89"],
                "total_hours": 40.5,
                "status": "draft"
            }
        }
    }
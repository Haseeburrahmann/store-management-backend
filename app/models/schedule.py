# app/models/schedule.py
from typing import Optional, List, Dict
from datetime import date, datetime
from pydantic import BaseModel, Field, validator
from bson import ObjectId


class ShiftModel(BaseModel):
    """Simplified shift model that focuses on days rather than specific dates"""
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    employee_id: str
    day_of_week: str  # "monday", "tuesday", etc.
    start_time: str   # "09:00" - 24-hour format
    end_time: str     # "17:00" - 24-hour format
    notes: Optional[str] = None

    @validator('day_of_week')
    def validate_day_of_week(cls, day):
        valid_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        day_lower = day.lower()
        if day_lower not in valid_days:
            raise ValueError(f"Invalid day of week: {day}. Must be one of {valid_days}")
        return day_lower

    @validator('start_time', 'end_time')
    def validate_time_format(cls, time_str):
        import re
        if not re.match(r'^([01]\d|2[0-3]):([0-5]\d)$', time_str):
            raise ValueError(f"Time must be in HH:MM format (24-hour): {time_str}")
        return time_str

    @validator('end_time')
    def validate_end_after_start(cls, end_time, values):
        if 'start_time' in values and end_time <= values['start_time']:
            raise ValueError("End time must be after start time")
        return end_time

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }


class ScheduleModel(BaseModel):
    """Simplified weekly schedule model"""
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    store_id: str
    title: str
    week_start_date: date  # Monday of the week
    week_end_date: date    # Sunday of the week
    shifts: List[ShiftModel] = []
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @validator('week_end_date', always=True)
    def set_week_end_date(cls, week_end_date, values):
        """Set week_end_date to 6 days after week_start_date if not provided"""
        if 'week_start_date' in values and (not week_end_date):
            from datetime import timedelta
            return values['week_start_date'] + timedelta(days=6)
        return week_end_date

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_schema_extra": {
            "example": {
                "store_id": "60d21b4967d0d8992e610c86",
                "title": "Weekly Schedule - First Week of June",
                "week_start_date": "2023-06-04",
                "week_end_date": "2023-06-10",
                "created_by": "60d21b4967d0d8992e610c87"
            }
        }
    }
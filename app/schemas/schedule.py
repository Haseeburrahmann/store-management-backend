# app/schemas/schedule.py
from typing import Optional, List, Dict
from datetime import date, datetime
from pydantic import BaseModel, Field, validator


class ShiftCreate(BaseModel):
    """Schema for creating a shift"""
    employee_id: str
    day_of_week: str  # "monday", "tuesday", etc.
    start_time: str   # "09:00" format
    end_time: str     # "17:00" format
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


class ShiftUpdate(BaseModel):
    """Schema for updating a shift"""
    employee_id: Optional[str] = None
    day_of_week: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    notes: Optional[str] = None

    @validator('day_of_week')
    def validate_day_of_week(cls, day):
        if day is None:
            return day
        valid_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        day_lower = day.lower()
        if day_lower not in valid_days:
            raise ValueError(f"Invalid day of week: {day}. Must be one of {valid_days}")
        return day_lower

    @validator('start_time', 'end_time')
    def validate_time_format(cls, time_str):
        if time_str is None:
            return time_str
        import re
        if not re.match(r'^([01]\d|2[0-3]):([0-5]\d)$', time_str):
            raise ValueError(f"Time must be in HH:MM format (24-hour): {time_str}")
        return time_str


class ShiftResponse(BaseModel):
    """Schema for shift responses"""
    id: str = Field(..., alias="_id")
    employee_id: str
    day_of_week: str
    start_time: str
    end_time: str
    notes: Optional[str] = None
    employee_name: Optional[str] = None  # Added for convenience

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }


class ScheduleCreate(BaseModel):
    """Schema for creating a schedule"""
    store_id: str
    title: str
    week_start_date: date
    shifts: Optional[List[ShiftCreate]] = None


class ScheduleUpdate(BaseModel):
    """Schema for updating a schedule"""
    title: Optional[str] = None
    shifts: Optional[List[ShiftCreate]] = None


class ScheduleResponse(BaseModel):
    """Schema for schedule responses"""
    id: str = Field(..., alias="_id")
    store_id: str
    title: str
    week_start_date: date
    week_end_date: date
    shifts: List[ShiftResponse]
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }


class ScheduleWithDetails(ScheduleResponse):
    """Schema for schedule with additional details"""
    store_name: Optional[str] = None
    created_by_name: Optional[str] = None


class ScheduleSummary(BaseModel):
    """Schema for schedule summary (used in listings)"""
    id: str = Field(..., alias="_id")
    store_id: str
    store_name: Optional[str] = None
    title: str
    week_start_date: date
    week_end_date: date
    shift_count: int
    created_at: datetime

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }
# app/schemas/schedule.py
from typing import List, Optional
from pydantic import BaseModel, Field, validator
from datetime import datetime, date
import re


class ScheduleShiftCreate(BaseModel):
    """Schema for creating schedule shifts"""
    employee_id: str
    date: str  # ISO date string YYYY-MM-DD
    start_time: str  # Time in format HH:MM (24-hour)
    end_time: str  # Time in format HH:MM (24-hour)
    notes: Optional[str] = None

    @validator('date')
    def validate_date_format(cls, v):
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', v):
            raise ValueError('Date must be in YYYY-MM-DD format')
        return v

    @validator('start_time', 'end_time')
    def validate_time_format(cls, v):
        if not re.match(r'^([01]\d|2[0-3]):([0-5]\d)$', v):
            raise ValueError('Time must be in HH:MM format (24-hour)')
        return v

    @validator('end_time')
    def validate_end_time_after_start_time(cls, v, values):
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError('End time must be after start time')
        return v


class ScheduleShiftUpdate(BaseModel):
    """Schema for updating schedule shifts"""
    employee_id: Optional[str] = None
    date: Optional[str] = None  # ISO date string YYYY-MM-DD
    start_time: Optional[str] = None  # Time in format HH:MM (24-hour)
    end_time: Optional[str] = None  # Time in format HH:MM (24-hour)
    notes: Optional[str] = None

    @validator('date')
    def validate_date_format(cls, v):
        if v and not re.match(r'^\d{4}-\d{2}-\d{2}$', v):
            raise ValueError('Date must be in YYYY-MM-DD format')
        return v

    @validator('start_time', 'end_time')
    def validate_time_format(cls, v):
        if v and not re.match(r'^([01]\d|2[0-3]):([0-5]\d)$', v):
            raise ValueError('Time must be in HH:MM format (24-hour)')
        return v


class ScheduleShiftResponse(BaseModel):
    """Schema for schedule shift responses"""
    id: str = Field(..., alias="_id")
    employee_id: str
    date: str  # ISO date string YYYY-MM-DD
    start_time: str  # Time in format HH:MM (24-hour)
    end_time: str  # Time in format HH:MM (24-hour)
    notes: Optional[str] = None

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }


class ScheduleCreate(BaseModel):
    """Schema for creating schedules"""
    title: str
    store_id: str
    start_date: str  # ISO date string YYYY-MM-DD
    end_date: str  # ISO date string YYYY-MM-DD
    shifts: List[ScheduleShiftCreate] = []

    @validator('start_date', 'end_date')
    def validate_date_format(cls, v):
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', v):
            raise ValueError('Date must be in YYYY-MM-DD format')
        return v

    @validator('end_date')
    def validate_end_date_after_start_date(cls, v, values):
        if 'start_date' in values and v < values['start_date']:
            raise ValueError('End date must be on or after start date')
        return v


class ScheduleUpdate(BaseModel):
    """Schema for updating schedules"""
    title: Optional[str] = None
    store_id: Optional[str] = None
    start_date: Optional[str] = None  # ISO date string YYYY-MM-DD
    end_date: Optional[str] = None  # ISO date string YYYY-MM-DD

    @validator('start_date', 'end_date')
    def validate_date_format(cls, v):
        if v and not re.match(r'^\d{4}-\d{2}-\d{2}$', v):
            raise ValueError('Date must be in YYYY-MM-DD format')
        return v


class ScheduleResponse(BaseModel):
    """Schema for schedule responses"""
    id: str = Field(..., alias="_id")
    title: str
    store_id: str
    start_date: str  # ISO date string YYYY-MM-DD
    end_date: str  # ISO date string YYYY-MM-DD
    shifts: List[ScheduleShiftResponse]
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }


class ScheduleWithDetails(ScheduleResponse):
    """Schema for schedule with store and employee information"""
    store_name: Optional[str] = None
    employee_names: Optional[dict] = None
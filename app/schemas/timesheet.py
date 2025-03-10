# app/schemas/timesheet.py
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, validator
from datetime import datetime
import re
from app.models.timesheet import TimesheetStatus


class TimesheetCreate(BaseModel):
    """Schema for creating timesheets"""
    employee_id: str
    store_id: str
    week_start_date: str  # ISO date string YYYY-MM-DD
    week_end_date: str  # ISO date string YYYY-MM-DD
    time_entries: List[str] = []  # Array of TimeEntry IDs
    total_hours: float
    notes: Optional[str] = None

    @validator('week_start_date', 'week_end_date')
    def validate_date_format(cls, v):
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', v):
            raise ValueError('Date must be in YYYY-MM-DD format')
        return v

    @validator('week_end_date')
    def validate_end_date_after_start_date(cls, v, values):
        if 'week_start_date' in values and v < values['week_start_date']:
            raise ValueError('End date must be on or after start date')
        return v

    @validator('total_hours')
    def validate_total_hours(cls, v):
        if v < 0:
            raise ValueError('Total hours must be non-negative')
        return v


class TimesheetUpdate(BaseModel):
    """Schema for updating timesheets"""
    time_entries: Optional[List[str]] = None  # Array of TimeEntry IDs
    total_hours: Optional[float] = None
    notes: Optional[str] = None

    @validator('total_hours')
    def validate_total_hours(cls, v):
        if v is not None and v < 0:
            raise ValueError('Total hours must be non-negative')
        return v


class TimesheetSubmit(BaseModel):
    """Schema for submitting timesheets"""
    notes: Optional[str] = None


class TimesheetApproval(BaseModel):
    """Schema for approving/rejecting timesheets"""
    status: TimesheetStatus
    notes: Optional[str] = None

    @validator('status')
    def validate_status(cls, v):
        if v not in [TimesheetStatus.APPROVED, TimesheetStatus.REJECTED]:
            raise ValueError('Status must be either approved or rejected')
        return v


class TimesheetResponse(BaseModel):
    """Schema for timesheet responses"""
    id: str = Field(..., alias="_id")
    employee_id: str
    store_id: str
    week_start_date: str  # ISO date string YYYY-MM-DD
    week_end_date: str  # ISO date string YYYY-MM-DD
    time_entries: List[str]  # Array of TimeEntry IDs
    total_hours: float
    status: str
    submitted_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }


class TimesheetWithDetails(TimesheetResponse):
    """Schema for timesheet with employee and store information"""
    employee_name: Optional[str] = None
    store_name: Optional[str] = None
    time_entry_details: Optional[List[Dict]] = None  # Details of time entries
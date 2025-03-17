"""
Timesheet schema models for validation.
"""
from typing import Dict, Optional, List
from datetime import date, datetime
from pydantic import BaseModel, Field, validator


class TimesheetStatus:
    """Timesheet status constants."""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"


class DailyHoursUpdate(BaseModel):
    """Schema for updating hours for a specific day."""
    day: str
    hours: float

    @validator('day')
    def validate_day(cls, day):
        valid_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        day_lower = day.lower()
        if day_lower not in valid_days:
            raise ValueError(f"Invalid day: {day}. Must be one of {valid_days}")
        return day_lower

    @validator('hours')
    def validate_hours(cls, hours):
        if hours < 0:
            raise ValueError("Hours cannot be negative")
        if hours > 24:
            raise ValueError("Hours cannot exceed 24 per day")
        return hours


class TimesheetBase(BaseModel):
    """Base timesheet schema with common fields."""
    employee_id: str
    store_id: str
    week_start_date: date
    hourly_rate: float


class TimesheetCreate(TimesheetBase):
    """Schema for creating a new timesheet."""
    daily_hours: Optional[Dict[str, float]] = None
    notes: Optional[str] = None


class TimesheetUpdate(BaseModel):
    """Schema for updating an existing timesheet."""
    daily_hours: Optional[Dict[str, float]] = None
    notes: Optional[str] = None

    model_config = {
        "extra": "ignore"
    }


class TimesheetSubmit(BaseModel):
    """Schema for submitting a timesheet for approval."""
    notes: Optional[str] = None


class TimesheetApproval(BaseModel):
    """Schema for approving or rejecting a timesheet."""
    status: str  # "approved" or "rejected"
    notes: Optional[str] = None

    @validator('status')
    def validate_status(cls, status):
        if status not in ['approved', 'rejected']:
            raise ValueError("Status must be either 'approved' or 'rejected'")
        return status


class TimesheetResponse(BaseModel):
    """Schema for timesheet responses."""
    id: str = Field(..., alias="_id")
    employee_id: str
    store_id: str
    week_start_date: date
    week_end_date: date
    daily_hours: Dict[str, float]
    total_hours: float
    hourly_rate: float
    total_earnings: float
    status: str
    notes: Optional[str] = None
    submitted_at: Optional[datetime] = None
    submitted_by: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    payment_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }
    }


class TimesheetWithDetails(TimesheetResponse):
    """Schema for timesheet with employee and store information."""
    employee_name: Optional[str] = None
    store_name: Optional[str] = None
    payment_status: Optional[str] = None


class TimesheetSummary(BaseModel):
    """Schema for timesheet summary (used in listings)."""
    id: str = Field(..., alias="_id")
    employee_id: str
    employee_name: Optional[str] = None
    store_id: str
    store_name: Optional[str] = None
    week_start_date: date
    week_end_date: date
    total_hours: float
    total_earnings: float
    status: str
    submitted_at: Optional[datetime] = None

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }
    }
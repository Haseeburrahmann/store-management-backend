# app/models/timesheet.py
from enum import Enum
from typing import Dict, Optional, List
from datetime import date, datetime
from pydantic import BaseModel, Field, validator
from bson import ObjectId


class TimesheetStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"


class TimesheetModel(BaseModel):
    """
    Simplified timesheet model containing all hours for a week.
    Each timesheet represents one employee's hours for one week at one store.
    """
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    employee_id: str
    store_id: str
    week_start_date: date  # Monday of the week
    week_end_date: date  # Sunday of the week

    # Store daily hours as a dictionary with day names as keys
    daily_hours: Dict[str, float] = Field(
        default_factory=lambda: {
            "monday": 0,
            "tuesday": 0,
            "wednesday": 0,
            "thursday": 0,
            "friday": 0,
            "saturday": 0,
            "sunday": 0
        }
    )

    total_hours: float = 0  # Sum of all daily hours
    hourly_rate: float  # Copy from employee profile for historical record
    total_earnings: float = 0  # Pre-calculated: total_hours * hourly_rate

    status: TimesheetStatus = TimesheetStatus.DRAFT
    notes: Optional[str] = None

    # Submission and approval metadata
    submitted_at: Optional[datetime] = None
    submitted_by: Optional[str] = None  # Usually the employee, but could be admin
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @validator('daily_hours')
    def validate_daily_hours(cls, daily_hours):
        """Validate that all daily hours are non-negative and <= 24"""
        valid_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

        # Ensure all days are present
        for day in valid_days:
            if day not in daily_hours:
                daily_hours[day] = 0

        # Validate hours for each day
        for day, hours in daily_hours.items():
            if day not in valid_days:
                raise ValueError(f"Invalid day: {day}")
            if hours < 0:
                raise ValueError(f"Hours cannot be negative for {day}")
            if hours > 24:
                raise ValueError(f"Hours cannot exceed 24 for {day}")

        return daily_hours

    @validator('total_hours', always=True)
    def calculate_total_hours(cls, total_hours, values):
        """Calculate total hours from daily hours"""
        if 'daily_hours' in values:
            return sum(values['daily_hours'].values())
        return total_hours

    @validator('total_earnings', always=True)
    def calculate_total_earnings(cls, total_earnings, values):
        """Calculate total earnings from total hours and hourly rate"""
        if 'total_hours' in values and 'hourly_rate' in values:
            return round(values['total_hours'] * values['hourly_rate'], 2)
        return total_earnings

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
                "employee_id": "60d21b4967d0d8992e610c85",
                "store_id": "60d21b4967d0d8992e610c86",
                "week_start_date": "2023-06-04",
                "week_end_date": "2023-06-10",
                "daily_hours": {
                    "monday": 8,
                    "tuesday": 7.5,
                    "wednesday": 8,
                    "thursday": 8,
                    "friday": 7,
                    "saturday": 0,
                    "sunday": 0
                },
                "hourly_rate": 15.50,
                "status": "draft"
            }
        }
    }
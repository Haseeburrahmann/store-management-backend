from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from bson import ObjectId
from app.models.hours import HoursStatus

class HourCreate(BaseModel):
    """Schema for creating hours records"""
    employee_id: str
    store_id: str
    clock_in: datetime
    clock_out: Optional[datetime] = None
    break_start: Optional[datetime] = None
    break_end: Optional[datetime] = None
    notes: Optional[str] = None

    @validator('clock_out', 'break_start', 'break_end', pre=True)
    def validate_times(cls, v, values):
        if v is None:
            return v

        # Convert string to datetime if needed
        if isinstance(v, str):
            try:
                v = datetime.fromisoformat(v.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                try:
                    v = datetime.strptime(v, "%Y-%m-%dT%H:%M:%S")
                except (ValueError, TypeError):
                    raise ValueError(f"Invalid datetime format: {v}")

        # Compare datetimes
        if 'clock_in' in values:
            clock_in = values['clock_in']
            # Convert clock_in to datetime if it's a string
            if isinstance(clock_in, str):
                try:
                    clock_in = datetime.fromisoformat(clock_in.replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    try:
                        clock_in = datetime.strptime(clock_in, "%Y-%m-%dT%H:%M:%S")
                    except (ValueError, TypeError):
                        raise ValueError(f"Invalid datetime format for clock_in: {clock_in}")

            if v < clock_in:
                raise ValueError('Time must be after clock_in time')

        return v

    @validator('break_end', pre=True)
    def validate_break_end(cls, v, values):
        if v is None or 'break_start' not in values or values['break_start'] is None:
            return v

        # Convert string to datetime if needed
        if isinstance(v, str):
            try:
                v = datetime.fromisoformat(v.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                try:
                    v = datetime.strptime(v, "%Y-%m-%dT%H:%M:%S")
                except (ValueError, TypeError):
                    raise ValueError(f"Invalid datetime format: {v}")

        # Convert break_start to datetime if it's a string
        break_start = values['break_start']
        if isinstance(break_start, str):
            try:
                break_start = datetime.fromisoformat(break_start.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                try:
                    break_start = datetime.strptime(break_start, "%Y-%m-%dT%H:%M:%S")
                except (ValueError, TypeError):
                    raise ValueError(f"Invalid datetime format for break_start: {break_start}")

        if v < break_start:
            raise ValueError('Break end must be after break start')

        return v


class HourUpdate(BaseModel):
    """Schema for updating hours records"""
    clock_out: Optional[datetime] = None
    break_start: Optional[datetime] = None
    break_end: Optional[datetime] = None
    notes: Optional[str] = None

    @validator('clock_out', 'break_start', 'break_end', pre=True)
    def validate_times(cls, v, values, **kwargs):
        # Convert string to datetime if needed
        if isinstance(v, str):
            try:
                v = datetime.fromisoformat(v.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                try:
                    v = datetime.strptime(v, "%Y-%m-%dT%H:%M:%S")
                except (ValueError, TypeError):
                    raise ValueError(f"Invalid datetime format: {v}")
        return v


class HourApproval(BaseModel):
    """Schema for approving hours records"""
    status: HoursStatus
    notes: Optional[str] = None


class HourResponse(BaseModel):
    """Schema for hours responses"""
    id: str = Field(..., alias="_id")
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
    created_at: datetime
    updated_at: datetime

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }


class HourWithEmployee(HourResponse):
    """Schema for hours with employee information"""
    employee_name: Optional[str] = None
    store_name: Optional[str] = None


class TimeSheetSummary(BaseModel):
    """Schema for timesheet summary"""
    employee_id: str
    employee_name: Optional[str] = None
    total_hours: float
    approved_hours: float
    pending_hours: float
    week_start_date: datetime
    week_end_date: datetime
    daily_hours: Dict[str, float]


class ClockInRequest(BaseModel):
    """Schema for clock in requests"""
    employee_id: str
    store_id: str
    notes: Optional[str] = None


class ClockOutRequest(BaseModel):
    """Schema for clock out requests"""
    break_start: Optional[datetime] = None
    break_end: Optional[datetime] = None
    notes: Optional[str] = None

    @validator('break_start', 'break_end', pre=True)
    def validate_times(cls, v, values, **kwargs):
        # Convert string to datetime if needed
        if isinstance(v, str):
            try:
                v = datetime.fromisoformat(v.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                try:
                    v = datetime.strptime(v, "%Y-%m-%dT%H:%M:%S")
                except (ValueError, TypeError):
                    raise ValueError(f"Invalid datetime format: {v}")
        return v
# app/schemas/payment.py
from datetime import date, datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    CONFIRMED = "confirmed"
    DISPUTED = "disputed"
    CANCELLED = "cancelled"


class PaymentCreate(BaseModel):
    """Schema for creating a payment manually"""
    employee_id: str
    store_id: Optional[str] = None  # Added store_id field
    timesheet_ids: List[str]
    period_start_date: date
    period_end_date: date
    total_hours: float
    hourly_rate: float
    gross_amount: Optional[float] = None
    notes: Optional[str] = None

    @validator('gross_amount', always=True)
    def calculate_gross_amount(cls, v, values):
        """Calculate gross amount if not provided"""
        if v is None and 'total_hours' in values and 'hourly_rate' in values:
            return round(values['total_hours'] * values['hourly_rate'], 2)
        return v

    model_config = {
        "json_encoders": {
            date: lambda v: v.isoformat()
        }
    }


class PaymentUpdate(BaseModel):
    """Schema for updating a payment"""
    status: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "status": "paid",
                "notes": "Payment processed via cash on 2023-06-15"
            }
        }


class PaymentResponse(BaseModel):
    """Schema for payment responses"""
    id: str = Field(..., alias="_id")
    employee_id: str
    employee_name: Optional[str] = None
    store_id: Optional[str] = None  # Added store_id field
    store_name: Optional[str] = None  # Added store_name field
    timesheet_ids: List[str]
    period_start_date: date
    period_end_date: date
    total_hours: float
    hourly_rate: float
    gross_amount: float
    status: str
    payment_date: Optional[datetime] = None
    confirmation_date: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {
            date: lambda v: v.isoformat(),
            datetime: lambda v: v.isoformat()
        }
    }


class PaymentWithDetails(PaymentResponse):
    """Schema for payment with additional details"""
    employee_name: Optional[str] = None
    store_name: Optional[str] = None
    timesheet_details: Optional[List[Dict[str, Any]]] = None


class PaymentStatusUpdate(BaseModel):
    """Schema for updating a payment status"""
    status: str
    notes: Optional[str] = None

    @validator('status')
    def validate_status(cls, v):
        valid_statuses = [status.value for status in PaymentStatus]
        if v not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
        return v


class PaymentConfirmation(BaseModel):
    """Schema for confirming payment receipt"""
    notes: Optional[str] = None


class PaymentDispute(BaseModel):
    """Schema for disputing a payment"""
    reason: str
    details: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "reason": "Incorrect amount",
                "details": "The payment amount doesn't match my calculated hours"
            }
        }


class PaymentGenerationRequest(BaseModel):
    """Schema for requesting payment generation for a period"""
    start_date: date
    end_date: date
    store_id: Optional[str] = None  # Added optional store_id for filtering

    model_config = {
        "json_schema_extra": {
            "example": {
                "start_date": "2023-06-04",
                "end_date": "2023-06-10",
                "store_id": "60d21b4967d0d8992e610c86"  # Added example store_id
            }
        },
        "json_encoders": {
            date: lambda v: v.isoformat()
        }
    }


class PaymentSummary(BaseModel):
    """Schema for summarized payment information"""
    id: str = Field(..., alias="_id")
    employee_id: str
    employee_name: Optional[str] = None
    store_id: Optional[str] = None  # Added store_id field
    store_name: Optional[str] = None  # Added store_name field
    period_start_date: date
    period_end_date: date
    total_hours: float
    gross_amount: float
    status: str
    payment_date: Optional[datetime] = None

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {
            date: lambda v: v.isoformat(),
            datetime: lambda v: v.isoformat()
        }
    }
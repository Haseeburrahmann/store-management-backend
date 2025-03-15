# app/models/payment.py
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field
from bson import ObjectId


class PaymentStatus(str):
    PENDING = "pending"
    PAID = "paid"
    CONFIRMED = "confirmed"
    DISPUTED = "disputed"
    CANCELLED = "cancelled"


class PaymentModel(BaseModel):
    """Database model for payments"""
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    employee_id: str
    store_id: Optional[str] = None  # Added store_id field
    timesheet_ids: List[str] = []
    period_start_date: date
    period_end_date: date
    total_hours: float
    hourly_rate: float
    gross_amount: float
    status: str = PaymentStatus.PENDING
    payment_date: Optional[datetime] = None
    confirmation_date: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_schema_extra": {
            "example": {
                "employee_id": "60d21b4967d0d8992e610c85",
                "store_id": "60d21b4967d0d8992e610c86",  # Added example store_id
                "period_start_date": "2023-06-04",
                "period_end_date": "2023-06-10",
                "total_hours": 40.5,
                "hourly_rate": 15.0,
                "gross_amount": 607.5,
                "status": "pending"
            }
        },
        "json_encoders": {
            # Add JSON encoders for date and datetime
            date: lambda v: v.isoformat(),
            datetime: lambda v: v.isoformat()
        }
    }
# app/models/employee.py
from datetime import datetime
from typing import Optional
from bson import ObjectId
from pydantic import Field, EmailStr
from app.models.user import User


class Employee(User):
    position: str
    hire_date: datetime
    store_id: Optional[ObjectId] = None
    hourly_rate: float
    employment_status: str = "active"  # active, on_leave, terminated
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None

    class Config:
        collection = "employees"
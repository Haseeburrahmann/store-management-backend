# app/schemas/employee.py
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime

class EmployeeCreate(BaseModel):
    """Schema for creating employees"""
    user_id: Optional[str] = None
    position: str
    hire_date: Optional[datetime] = None
    store_id: Optional[str] = None
    hourly_rate: float
    employment_status: str = "active"  # active, on_leave, terminated
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None

class EmployeeUpdate(BaseModel):
    """Schema for updating employees"""
    position: Optional[str] = None
    store_id: Optional[str] = None
    hourly_rate: Optional[float] = None
    employment_status: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None

class EmployeeResponse(BaseModel):
    """Schema for employee responses"""
    id: str = Field(..., alias="_id")
    user_id: Optional[str] = None
    position: str
    hire_date: datetime
    store_id: Optional[str] = None
    hourly_rate: float
    employment_status: str
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }


class EmployeeUserCreateModel(BaseModel):
    """Schema for creating employees with user accounts"""
    # User fields
    email: str
    full_name: str
    password: str
    phone_number: Optional[str] = None
    role_id: Optional[str] = None

    # Employee fields
    position: str
    hire_date: Optional[datetime] = None
    store_id: Optional[str] = None
    hourly_rate: float
    employment_status: str = "active"
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None

class EmployeeWithUserInfo(EmployeeResponse):
    """Schema for employee with user information"""
    email: Optional[str] = None
    full_name: Optional[str] = None
    phone_number: Optional[str] = None

class EmployeeWithStoreInfo(EmployeeWithUserInfo):
    """Schema for employee with store information"""
    store_name: Optional[str] = None
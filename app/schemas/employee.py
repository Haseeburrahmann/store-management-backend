# app/schemas/employee.py
from typing import Optional
from pydantic import BaseModel, Field, EmailStr, validator
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

    @validator('hourly_rate')
    def validate_hourly_rate(cls, v):
        if v <= 0:
            raise ValueError('Hourly rate must be greater than zero')
        return v

    @validator('employment_status')
    def validate_status(cls, v):
        valid_statuses = ['active', 'on_leave', 'terminated']
        if v not in valid_statuses:
            raise ValueError(f'Status must be one of: {", ".join(valid_statuses)}')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "60d21b4967d0d8992e610c85",
                "position": "Cashier",
                "store_id": "60d21b4967d0d8992e610c86",
                "hourly_rate": 15.50,
                "employment_status": "active",
                "emergency_contact_name": "Jane Doe",
                "emergency_contact_phone": "555-987-6543",
                "address": "123 Main St",
                "city": "New York",
                "state": "NY",
                "zip_code": "10001"
            }
        }


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
    user_id: Optional[str] = None

    @validator('hourly_rate')
    def validate_hourly_rate(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Hourly rate must be greater than zero')
        return v

    @validator('employment_status')
    def validate_status(cls, v):
        if v is None:
            return v

        valid_statuses = ['active', 'on_leave', 'terminated']
        if v not in valid_statuses:
            raise ValueError(f'Status must be one of: {", ".join(valid_statuses)}')
        return v

    class Config:
        # Allow partial updates
        extra = "ignore"
        json_schema_extra = {
            "example": {
                "position": "Senior Cashier",
                "hourly_rate": 17.50
            }
        }


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
    email: EmailStr
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

    @validator('hourly_rate')
    def validate_hourly_rate(cls, v):
        if v <= 0:
            raise ValueError('Hourly rate must be greater than zero')
        return v

    @validator('employment_status')
    def validate_status(cls, v):
        valid_statuses = ['active', 'on_leave', 'terminated']
        if v not in valid_statuses:
            raise ValueError(f'Status must be one of: {", ".join(valid_statuses)}')
        return v

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "email": "employee@example.com",
                "full_name": "John Smith",
                "password": "securepassword123",
                "phone_number": "555-123-4567",
                "role_id": "60d21b4967d0d8992e610c87",
                "position": "Cashier",
                "hourly_rate": 15.50,
                "store_id": "60d21b4967d0d8992e610c88"
            }
        }


class EmployeeWithUserInfo(EmployeeResponse):
    """Schema for employee with user information"""
    email: Optional[str] = None
    full_name: Optional[str] = None
    phone_number: Optional[str] = None


class EmployeeWithStoreInfo(EmployeeWithUserInfo):
    """Schema for employee with store information"""
    store_name: Optional[str] = None
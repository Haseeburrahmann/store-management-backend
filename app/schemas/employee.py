# app/schemas/employee.py
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr
from app.schemas.user import UserBase, UserCreate, UserUpdate, UserInDB


class EmployeeBase(UserBase):
    position: str
    hourly_rate: float
    employment_status: Optional[str] = "active"
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None


class EmployeeCreate(UserCreate, EmployeeBase):
    store_id: Optional[str] = None
    hire_date: Optional[datetime] = Field(default_factory=datetime.now)


# Completely redefine EmployeeUpdate to make all fields optional
class EmployeeUpdate(BaseModel):
    # User fields (from UserUpdate)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    password: Optional[str] = None
    role_id: Optional[str] = None
    is_active: Optional[bool] = None

    # Employee fields
    position: Optional[str] = None
    hourly_rate: Optional[float] = None
    employment_status: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    store_id: Optional[str] = None
    hire_date: Optional[datetime] = None


class EmployeeInDB(UserInDB, EmployeeBase):
    store_id: Optional[str] = None
    hire_date: datetime
    user_id: Optional[str] = None

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_schema_extra": {
            "example": {
                "_id": "60d21b4967d0d8992e610c85",
                "email": "employee@example.com",
                "full_name": "Employee Name",
                "phone_number": "555-123-4567",
                "is_active": True,
                "password": "**********",
                "role_id": "60d21b4967d0d8992e610c86",
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00",
                "position": "Cashier",
                "hire_date": "2023-01-01T00:00:00",
                "hourly_rate": 15.0,
                "employment_status": "active",
                "store_id": "60d21b4967d0d8992e610c87",
                "user_id": "60d21b4967d0d8992e610c88"
            }
        }
    }


class Employee(EmployeeInDB):
    pass


class EmployeeWithStore(Employee):
    store_name: Optional[str] = None
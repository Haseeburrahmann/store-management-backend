from datetime import datetime
from typing import Optional
from bson import ObjectId
from pydantic import BaseModel, Field, EmailStr


class User(BaseModel):
    id: str = Field(default_factory=lambda: str(ObjectId()))
    email: EmailStr
    hashed_password: str
    full_name: Optional[str] = None
    role: str = "employee"  # employee, manager, admin
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
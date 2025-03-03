from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from bson import ObjectId


# Custom type for handling ObjectId
class PyObjectId(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return str(v)

    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type, _handler):
        return {
            "type": "string",
            "description": "ObjectId"
        }


class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    phone_number: Optional[str] = None
    is_active: bool = True


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    password: Optional[str] = None
    role_id: Optional[str] = None
    is_active: Optional[bool] = None


class UserInDB(UserBase):
    id: str = Field(..., alias="_id")
    password: str
    role_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }


class UserResponse(UserBase):
    id: str = Field(..., alias="_id")
    role_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }


class UserWithPermissions(UserResponse):
    permissions: List[str] = []


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenPayload(BaseModel):
    sub: Optional[str] = None
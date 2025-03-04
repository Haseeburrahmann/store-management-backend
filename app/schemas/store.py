# app/schemas/store.py
from typing import Optional
from pydantic import BaseModel, EmailStr

class StoreBase(BaseModel):
    name: str
    address: str
    city: str
    state: str
    zip_code: str
    phone: str
    email: Optional[str] = None
    is_active: bool = True

class StoreCreate(StoreBase):
    pass

class StoreUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    manager_id: Optional[str] = None
    is_active: Optional[bool] = None

class StoreResponse(StoreBase):
    id: str
    manager_id: Optional[str] = None
    manager_name: Optional[str] = None

class StoreWithManager(StoreResponse):
    pass
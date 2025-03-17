# app/schemas/inventory_request.py
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class InventoryItemRequestCreate(BaseModel):
    """Schema for creating a new item within an inventory request"""
    name: str
    quantity: float
    unit_type: str
    notes: Optional[str] = None


class InventoryRequestCreate(BaseModel):
    """Schema for creating a new inventory request"""
    store_id: str
    items: List[InventoryItemRequestCreate]
    notes: Optional[str] = None


class InventoryItemRequestResponse(BaseModel):
    """Schema for returning a single item in an inventory request"""
    name: str
    quantity: float
    unit_type: str
    notes: Optional[str] = None


class InventoryRequestUpdate(BaseModel):
    """Schema for updating an inventory request"""
    items: Optional[List[InventoryItemRequestCreate]] = None
    notes: Optional[str] = None


class InventoryRequestResponse(BaseModel):
    """Schema for returning an inventory request"""
    id: str = Field(..., alias="_id")
    store_id: str
    store_name: Optional[str] = None
    employee_id: str
    employee_name: Optional[str] = None
    items: List[InventoryItemRequestResponse]
    status: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    fulfilled_at: Optional[datetime] = None
    fulfilled_by: Optional[str] = None
    fulfilled_by_name: Optional[str] = None

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }


class InventoryRequestSummary(BaseModel):
    """Schema for returning a summarized inventory request (for listings)"""
    id: str = Field(..., alias="_id")
    store_id: str
    store_name: Optional[str] = None
    employee_id: str
    employee_name: Optional[str] = None
    item_count: int
    status: str
    created_at: datetime
    fulfilled_at: Optional[datetime] = None

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }


class InventoryRequestFulfill(BaseModel):
    """Schema for fulfilling an inventory request"""
    notes: Optional[str] = None


class InventoryRequestCancel(BaseModel):
    """Schema for cancelling an inventory request"""
    reason: str
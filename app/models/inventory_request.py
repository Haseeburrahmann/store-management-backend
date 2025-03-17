# app/models/inventory_request.py
from enum import Enum
from typing import Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from bson import ObjectId


class InventoryRequestStatus(str, Enum):
    PENDING = "pending"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"


class InventoryItemRequest(BaseModel):
    """Model for a single item within an inventory request"""
    name: str
    quantity: float
    unit_type: str  # "packet", "box", "single", etc.
    notes: Optional[str] = None


class InventoryRequestModel(BaseModel):
    """Database model for inventory requests"""
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    store_id: str
    employee_id: str
    items: List[InventoryItemRequest]
    status: str = InventoryRequestStatus.PENDING
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    fulfilled_at: Optional[datetime] = None
    fulfilled_by: Optional[str] = None

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_schema_extra": {
            "example": {
                "store_id": "60d21b4967d0d8992e610c86",
                "employee_id": "60d21b4967d0d8992e610c85",
                "items": [
                    {
                        "name": "Paper Towels",
                        "quantity": 5,
                        "unit_type": "packet",
                        "notes": "For kitchen area"
                    },
                    {
                        "name": "Printer Paper",
                        "quantity": 2,
                        "unit_type": "box",
                        "notes": "Running low"
                    }
                ],
                "status": "pending",
                "notes": "Needed by end of week"
            }
        }
    }
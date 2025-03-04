# app/api/stores/router.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

# Use the correct permission format
from app.dependencies.permissions import get_current_user, has_permission
from app.schemas.store import StoreCreate, StoreUpdate, StoreResponse, StoreWithManager
from app.services.store import StoreService
from app.schemas.user import UserInDB

router = APIRouter()

@router.get("/", response_model=List[StoreWithManager])
async def get_stores(
    skip: int = 0,
    limit: int = 100,
    name: Optional[str] = None,
    city: Optional[str] = None,
    manager_id: Optional[str] = None,
    current_user: UserInDB = Depends(has_permission("stores:read"))  # Changed to match enum format
):
    return await StoreService.get_stores(skip, limit, name, city, manager_id)

@router.get("/managed", response_model=List[StoreResponse])
async def get_managed_stores(
    current_user: UserInDB = Depends(has_permission("stores:read"))  # Changed to match enum format
):
    # Only return stores that the current user manages
    return await StoreService.get_stores_by_manager(str(current_user.id))

@router.get("/{store_id}", response_model=StoreWithManager)
async def get_store(
    store_id: str,
    current_user: UserInDB = Depends(has_permission("stores:read"))  # Changed to match enum format
):
    return await StoreService.get_store(store_id)

@router.post("/", response_model=StoreResponse)
async def create_store(
    store: StoreCreate,
    current_user: UserInDB = Depends(has_permission("stores:write"))  # Changed to match enum format
):
    return await StoreService.create_store(store.model_dump())

@router.put("/{store_id}", response_model=StoreResponse)
async def update_store(
    store_id: str,
    store: StoreUpdate,
    current_user: UserInDB = Depends(has_permission("stores:write"))  # Changed to match enum format
):
    return await StoreService.update_store(store_id, store.model_dump(exclude_unset=True))

@router.delete("/{store_id}", response_model=bool)
async def delete_store(
    store_id: str,
    current_user: UserInDB = Depends(has_permission("stores:delete"))  # Changed to match enum format
):
    return await StoreService.delete_store(store_id)

@router.put("/{store_id}/assign-manager/{manager_id}", response_model=dict)
async def assign_manager(
    store_id: str,
    manager_id: str
):
    return {"store_id": store_id, "manager_id": manager_id, "status": "success"}
# app/api/stores/router.py
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.dependencies.permissions import get_current_user, has_permission
from app.schemas.store import StoreCreate, StoreUpdate, StoreResponse, StoreWithManager
from app.services.store import StoreService

router = APIRouter()

@router.get("/", response_model=List[StoreWithManager])
async def get_stores(
    skip: int = 0,
    limit: int = 100,
    name: Optional[str] = None,
    city: Optional[str] = None,
    manager_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(has_permission("stores:read"))
):
    return await StoreService.get_stores(skip, limit, name, city, manager_id)

@router.get("/managed", response_model=List[StoreResponse])
async def get_managed_stores(
    current_user: Dict[str, Any] = Depends(has_permission("stores:read"))
):
    # Only return stores that the current user manages
    return await StoreService.get_stores_by_manager(str(current_user["_id"]))

@router.get("/{store_id}", response_model=StoreWithManager)
async def get_store(
    store_id: str,
    current_user: Dict[str, Any] = Depends(has_permission("stores:read"))
):
    store = await StoreService.get_store(store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return store

@router.post("/", response_model=StoreResponse, status_code=status.HTTP_201_CREATED)
async def create_store(
    store: StoreCreate,
    current_user: Dict[str, Any] = Depends(has_permission("stores:write"))
):
    return await StoreService.create_store(store.model_dump())

@router.put("/{store_id}", response_model=StoreResponse)
async def update_store(
    store_id: str,
    store: StoreUpdate,
    current_user: Dict[str, Any] = Depends(has_permission("stores:write"))
):
    updated_store = await StoreService.update_store(store_id, store.model_dump(exclude_unset=True))
    if not updated_store:
        raise HTTPException(status_code=404, detail="Store not found")
    return updated_store

@router.delete("/{store_id}", response_model=bool)
async def delete_store(
    store_id: str,
    current_user: Dict[str, Any] = Depends(has_permission("stores:delete"))
):
    result = await StoreService.delete_store(store_id)
    if not result:
        raise HTTPException(status_code=404, detail="Store not found")
    return result

@router.put("/{store_id}/assign-manager/{manager_id}", response_model=StoreResponse)
async def assign_manager(
    store_id: str,
    manager_id: str,
    current_user: Dict[str, Any] = Depends(has_permission("stores:write"))
):
    updated_store = await StoreService.assign_manager(store_id, manager_id)
    if not updated_store:
        raise HTTPException(status_code=404, detail="Store or manager not found")
    return updated_store
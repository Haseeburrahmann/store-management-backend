"""
Store API routes for store management.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.domains.stores.service import store_service
from app.core.permissions import has_permission
from app.schemas.store import StoreCreate, StoreUpdate, StoreResponse, StoreWithManager

router = APIRouter()


@router.get("/", response_model=List[StoreWithManager])
async def get_stores(
        skip: int = 0,
        limit: int = 100,
        name: Optional[str] = None,
        city: Optional[str] = None,
        manager_id: Optional[str] = None,
        current_user: dict = Depends(has_permission("stores:read"))
):
    """
    Get all stores with optional filtering.

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        name: Filter by name pattern
        city: Filter by city pattern
        manager_id: Filter by manager ID
        current_user: Current user from token

    Returns:
        List of stores
    """
    try:
        stores = await store_service.get_stores(skip, limit, name, city, manager_id)
        return stores
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching stores: {str(e)}"
        )


@router.get("/managed", response_model=List[StoreResponse])
async def get_managed_stores(
        current_user: dict = Depends(has_permission("stores:read"))
):
    """
    Get stores managed by the current user.

    Args:
        current_user: Current user from token

    Returns:
        List of stores
    """
    try:
        # Only return stores that the current user manages
        return await store_service.get_stores_by_manager(str(current_user["_id"]))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching managed stores: {str(e)}"
        )


@router.get("/{store_id}", response_model=StoreWithManager)
async def get_store(
        store_id: str,
        current_user: dict = Depends(has_permission("stores:read"))
):
    """
    Get store by ID.

    Args:
        store_id: Store ID
        current_user: Current user from token

    Returns:
        Store

    Raises:
        HTTPException: If store not found
    """
    try:
        store = await store_service.get_store(store_id)
        if not store:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Store with ID {store_id} not found"
            )
        return store
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching store: {str(e)}"
        )


@router.post("/", response_model=StoreResponse, status_code=status.HTTP_201_CREATED)
async def create_store(
        store_data: StoreCreate,
        current_user: dict = Depends(has_permission("stores:write"))
):
    """
    Create new store.

    Args:
        store_data: Store creation data
        current_user: Current user from token

    Returns:
        Created store
    """
    try:
        store = await store_service.create_store(store_data.model_dump())
        return store
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating store: {str(e)}"
        )


@router.put("/{store_id}", response_model=StoreResponse)
async def update_store(
        store_id: str,
        store_data: StoreUpdate,
        current_user: dict = Depends(has_permission("stores:write"))
):
    """
    Update existing store.

    Args:
        store_id: Store ID
        store_data: Store update data
        current_user: Current user from token

    Returns:
        Updated store

    Raises:
        HTTPException: If store not found
    """
    try:
        updated_store = await store_service.update_store(store_id, store_data.model_dump(exclude_unset=True))
        if not updated_store:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Store with ID {store_id} not found"
            )
        return updated_store
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating store: {str(e)}"
        )


@router.delete("/{store_id}", response_model=bool)
async def delete_store(
        store_id: str,
        current_user: dict = Depends(has_permission("stores:delete"))
):
    """
    Delete store.

    Args:
        store_id: Store ID
        current_user: Current user from token

    Returns:
        True if store was deleted

    Raises:
        HTTPException: If store not found or cannot be deleted
    """
    try:
        # Check if store exists
        existing_store = await store_service.get_store(store_id)
        if not existing_store:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Store with ID {store_id} not found"
            )

        # Delete store
        result = await store_service.delete_store(store_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete store"
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting store: {str(e)}"
        )


@router.put("/{store_id}/assign-manager/{manager_id}", response_model=StoreResponse)
async def assign_manager(
        store_id: str,
        manager_id: str,
        current_user: dict = Depends(has_permission("stores:write"))
):
    """
    Assign manager to store.

    Args:
        store_id: Store ID
        manager_id: Manager ID
        current_user: Current user from token

    Returns:
        Updated store

    Raises:
        HTTPException: If store not found or manager invalid
    """
    try:
        updated_store = await store_service.assign_manager(store_id, manager_id)
        if not updated_store:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Store with ID {store_id} not found"
            )
        return updated_store
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error assigning manager: {str(e)}"
        )
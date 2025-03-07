# app/api/stores/router.py
from typing import List, Optional, Dict, Any

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.dependencies.permissions import get_current_user, has_permission
from app.schemas.store import StoreCreate, StoreUpdate, StoreResponse, StoreWithManager
from app.services.store import StoreService, stores_collection
from app.services.user import get_user_by_id

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
    """
    Get store by ID with robust error handling
    """
    try:
        print(f"GET request for store with ID: {store_id}")

        # Check if provided ID is valid format
        if not (len(store_id) == 24 and all(c in '0123456789abcdefABCDEF' for c in store_id)):
            print(f"Invalid store ID format: {store_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid store ID format. Expected 24-character hex string, got: {store_id}"
            )

        # Attempt to get the store
        store = await StoreService.get_store(store_id)

        # If store is None, it wasn't found
        if not store:
            print(f"Store not found with ID: {store_id}")
            # Get all stores for debugging
            all_stores = await stores_collection.find().to_list(length=100)
            store_ids = [str(s.get('_id')) for s in all_stores]
            print(f"Available store IDs: {store_ids}")

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Store not found with ID: {store_id}"
            )

        return store
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        print(f"Unexpected error in get_store: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving store: {str(e)}"
        )


@router.post("/", response_model=StoreResponse, status_code=status.HTTP_201_CREATED)
async def create_store(
        store: StoreCreate,
        current_user: Dict[str, Any] = Depends(has_permission("stores:write"))
):
    # Additional validation for manager_id
    if store.manager_id:
        # Check if manager exists
        manager = await get_user_by_id(store.manager_id)
        if not manager:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Manager with ID {store.manager_id} not found"
            )

        # Check if user has Manager role
        if manager.get("role_id"):
            from app.services.role import get_role_by_id
            role = await get_role_by_id(manager.get("role_id"))
            if role and role.get("name") != "Manager" and role.get("name") != "Admin":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"User {manager.get('email')} does not have Manager or Admin role"
                )

    # Create the store
    return await StoreService.create_store(store.model_dump())


@router.put("/{store_id}", response_model=StoreResponse)
async def update_store(
        store_id: str,
        store: StoreUpdate,
        current_user: Dict[str, Any] = Depends(has_permission("stores:write"))
):
    """
    Update existing store with enhanced error handling
    """
    try:
        print(f"PUT request for store update with ID: {store_id}")

        # Check if store exists first
        existing_store = await StoreService.get_store(store_id)
        if not existing_store:
            print(f"Store not found with ID: {store_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Store not found with ID: {store_id}"
            )

        # Get update data from model
        update_data = store.model_dump(exclude_unset=True)
        print(f"Update data: {update_data}")

        # Additional validation for manager_id if changing
        if store.manager_id:
            print(f"Validating manager ID: {store.manager_id}")

            # Check if manager exists
            from app.services.user import get_user_by_id
            manager = await get_user_by_id(store.manager_id)
            if not manager:
                print(f"Manager not found with ID: {store.manager_id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Manager with ID {store.manager_id} not found"
                )

            # Check if user has Manager role
            if manager.get("role_id"):
                from app.services.role import get_role_by_id
                role = await get_role_by_id(manager.get("role_id"))
                if role and role.get("name") != "Manager" and role.get("name") != "Admin":
                    print(f"User has role: {role.get('name')}, not Manager or Admin")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"User {manager.get('email')} does not have Manager or Admin role"
                    )

        # Handle the case where we want to remove a manager
        if "manager_id" in update_data and update_data["manager_id"] is None:
            print("Removing manager from store")
            # This is allowed - we'll set manager_id to None

        # Update the store
        updated_store = await StoreService.update_store(store_id, update_data)

        # Handle update failure
        if not updated_store:
            print(f"Failed to update store: {store_id}")
            # Try to get specific error information
            from app.services.store import stores_collection
            existing_doc = await stores_collection.find_one(
                {"_id": ObjectId(store_id)}) or await stores_collection.find_one({"_id": store_id})
            doc_exists = existing_doc is not None

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update store. Document exists: {doc_exists}"
            )

        return updated_store
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        print(f"Unexpected error in update_store: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating store: {str(e)}"
        )

@router.delete("/{store_id}", response_model=bool)
async def delete_store(
        store_id: str,
        current_user: Dict[str, Any] = Depends(has_permission("stores:delete"))
):
    # Check if store exists
    existing_store = await StoreService.get_store(store_id)
    if not existing_store:
        raise HTTPException(status_code=404, detail="Store not found")

    result = await StoreService.delete_store(store_id)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to delete store")
    return result


@router.put("/{store_id}/assign-manager/{manager_id}", response_model=StoreResponse)
async def assign_manager(
        store_id: str,
        manager_id: str,
        current_user: Dict[str, Any] = Depends(has_permission("stores:write"))
):
    # Check if store exists
    existing_store = await StoreService.get_store(store_id)
    if not existing_store:
        raise HTTPException(status_code=404, detail="Store not found")

    # Check if manager exists
    manager = await get_user_by_id(manager_id)
    if not manager:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Manager with ID {manager_id} not found"
        )

    # Check if user has Manager role
    if manager.get("role_id"):
        from app.services.role import get_role_by_id
        role = await get_role_by_id(manager.get("role_id"))
        if role and role.get("name") != "Manager" and role.get("name") != "Admin":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User {manager.get('email')} does not have Manager or Admin role"
            )

    updated_store = await StoreService.assign_manager(store_id, manager_id)
    if not updated_store:
        raise HTTPException(status_code=500, detail="Failed to assign manager")
    return updated_store


@router.get("/debug/lookup/{store_id}")
async def debug_lookup_store(
        store_id: str,
        current_user: Dict[str, Any] = Depends(has_permission("stores:read"))
):
    """
    Debug endpoint to test store lookup with different methods
    """
    try:
        result = {
            "requested_id": store_id,
            "lookup_results": {}
        }

        # Get all stores for reference
        all_stores = await stores_collection.find().to_list(length=100)

        # Method 1: Direct ObjectId lookup
        try:
            obj_id = ObjectId(store_id)
            store = await stores_collection.find_one({"_id": obj_id})
            result["lookup_results"]["direct_objectid"] = {
                "success": store is not None,
                "store_name": store.get("name") if store else None
            }
        except Exception as e:
            result["lookup_results"]["direct_objectid"] = {
                "success": False,
                "error": str(e)
            }

        # Method 2: String lookup
        store = await stores_collection.find_one({"_id": store_id})
        result["lookup_results"]["string_id"] = {
            "success": store is not None,
            "store_name": store.get("name") if store else None
        }

        # Method 3: String comparison
        store_match = None
        for store in all_stores:
            if str(store.get("_id")) == store_id:
                store_match = store
                break

        result["lookup_results"]["string_comparison"] = {
            "success": store_match is not None,
            "store_name": store_match.get("name") if store_match else None,
            "total_stores_checked": len(all_stores)
        }

        # List of all store IDs for reference
        result["all_store_ids"] = [str(store.get("_id")) for store in all_stores]
        result["all_stores_info"] = [{
            "id": str(store.get("_id")),
            "name": store.get("name"),
            "manager_id": store.get("manager_id")
        } for store in all_stores]

        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in debug lookup: {str(e)}"
        )


@router.get("/debug/all")
async def debug_get_all_stores(
        current_user: Dict[str, Any] = Depends(has_permission("stores:read"))
):
    """
    Debug endpoint to get all stores with their raw IDs
    """
    try:
        # Get all stores from database directly
        stores = await stores_collection.find().to_list(length=100)

        # Process stores to show raw ID information
        result = []
        for store in stores:
            store_info = {
                "raw_id": str(store.get("_id")),
                "id_type": type(store.get("_id")).__name__,
                "name": store.get("name"),
                "manager_id": store.get("manager_id"),
                "manager_id_type": type(store.get("manager_id")).__name__ if store.get("manager_id") else None
            }
            result.append(store_info)

        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error debugging stores: {str(e)}"
        )
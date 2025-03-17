"""
Store service for business logic.
"""
from typing import Dict, List, Optional, Any
from fastapi import HTTPException, status

from app.domains.stores.repository import StoreRepository
from app.domains.users.service import user_service
from app.domains.roles.service import role_service
from app.utils.id_handler import IdHandler
from app.utils.datetime_handler import DateTimeHandler


class StoreService:
    """
    Service for store-related business logic.
    """

    def __init__(self, store_repo: Optional[StoreRepository] = None):
        """
        Initialize with store repository.

        Args:
            store_repo: Optional store repository instance
        """
        self.store_repo = store_repo or StoreRepository()

    async def get_stores(
            self,
            skip: int = 0,
            limit: int = 100,
            name: Optional[str] = None,
            city: Optional[str] = None,
            manager_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get stores with optional filtering.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            name: Filter by name pattern
            city: Filter by city pattern
            manager_id: Filter by manager ID

        Returns:
            List of store documents
        """
        # Build query
        query = {}

        if name:
            query["name"] = {"$regex": name, "$options": "i"}

        if city:
            query["city"] = {"$regex": city, "$options": "i"}

        if manager_id:
            obj_id = IdHandler.ensure_object_id(manager_id)
            query["manager_id"] = str(obj_id) if obj_id else manager_id

        # Get stores
        stores = await self.store_repo.find_many(query, skip, limit)

        # Enrich with manager names
        result = []
        for store in stores:
            store_with_manager = dict(store)

            if store.get("manager_id"):
                manager = await user_service.get_user_by_id(store["manager_id"])
                if manager:
                    store_with_manager["manager_name"] = manager.get("full_name")

            result.append(store_with_manager)

        return result

    async def get_store(self, store_id: str) -> Optional[Dict[str, Any]]:
        """
        Get store by ID.

        Args:
            store_id: Store ID

        Returns:
            Store document or None if not found
        """
        store = await self.store_repo.find_by_id(store_id)

        if not store:
            return None

        # Enrich with manager name
        if store.get("manager_id"):
            manager = await user_service.get_user_by_id(store["manager_id"])
            if manager:
                store["manager_name"] = manager.get("full_name")

        return store

    async def get_stores_by_manager(self, manager_id: str) -> List[Dict[str, Any]]:
        """
        Get stores managed by a specific user.

        Args:
            manager_id: Manager ID

        Returns:
            List of store documents
        """
        return await self.store_repo.find_by_manager(manager_id)

    async def create_store(self, store_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new store.

        Args:
            store_data: Store data

        Returns:
            Created store document

        Raises:
            HTTPException: If validation fails
        """
        # Validate manager if provided
        if store_data.get("manager_id"):
            await self._validate_manager(store_data["manager_id"])

        # Set default values
        if "is_active" not in store_data:
            store_data["is_active"] = True

        # Create store
        return await self.store_repo.create(store_data)

    async def update_store(self, store_id: str, store_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update an existing store.

        Args:
            store_id: Store ID
            store_data: Updated store data

        Returns:
            Updated store document or None if not found

        Raises:
            HTTPException: If validation fails
        """
        # Check if store exists
        existing_store = await self.store_repo.find_by_id(store_id)
        if not existing_store:
            return None

        # Validate manager if provided
        if store_data.get("manager_id"):
            await self._validate_manager(store_data["manager_id"])

        # Update store
        return await self.store_repo.update(store_id, store_data)

    async def delete_store(self, store_id: str) -> bool:
        """
        Delete a store.

        Args:
            store_id: Store ID

        Returns:
            True if store was deleted

        Raises:
            HTTPException: If store has associated resources
        """
        # Check if store exists
        existing_store = await self.store_repo.find_by_id(store_id)
        if not existing_store:
            return False

        # Check for associated resources (employees, schedules, etc.)
        # This would be implemented with checks to employee, schedule repositories
        # For now, we'll just delete the store

        # Delete store
        return await self.store_repo.delete(store_id)

    async def assign_manager(self, store_id: str, manager_id: str) -> Optional[Dict[str, Any]]:
        """
        Assign a manager to a store.

        Args:
            store_id: Store ID
            manager_id: Manager ID

        Returns:
            Updated store document or None if not found

        Raises:
            HTTPException: If validation fails
        """
        # Check if store exists
        existing_store = await self.store_repo.find_by_id(store_id)
        if not existing_store:
            return None

        # Validate manager
        await self._validate_manager(manager_id)

        # Update store
        return await self.store_repo.update(store_id, {"manager_id": manager_id})

    async def _validate_manager(self, manager_id: str) -> None:
        """
        Validate that a user exists and has a manager role.

        Args:
            manager_id: Manager ID

        Raises:
            HTTPException: If validation fails
        """
        # Check if user exists
        manager = await user_service.get_user_by_id(manager_id)
        if not manager:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Manager with ID {manager_id} not found"
            )

        # Check if user has manager role
        if not await role_service.user_has_role(manager_id, ["Manager", "Admin"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User {manager.get('email')} does not have Manager or Admin role"
            )


# Create global instance
store_service = StoreService()
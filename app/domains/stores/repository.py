"""
Store repository for database operations.
"""
from typing import Dict, List, Optional, Any

from app.db.base_repository import BaseRepository
from app.db.mongodb import get_stores_collection
from app.utils.id_handler import IdHandler


class StoreRepository(BaseRepository):
    """
    Repository for store data access.
    Extends BaseRepository with store-specific operations.
    """

    def __init__(self):
        """Initialize with stores collection."""
        super().__init__(get_stores_collection())

    async def find_by_manager(self, manager_id: str) -> List[Dict[str, Any]]:
        """
        Find stores by manager ID.

        Args:
            manager_id: Manager ID

        Returns:
            List of store documents
        """
        manager_obj_id = IdHandler.ensure_object_id(manager_id)
        query = {"manager_id": manager_obj_id} if manager_obj_id else {"manager_id": manager_id}

        stores = await self.collection.find(query).to_list(length=100)
        return IdHandler.format_object_ids(stores)

    async def find_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Find a store by name.

        Args:
            name: Store name

        Returns:
            Store document or None if not found
        """
        store = await self.collection.find_one({"name": name})
        return IdHandler.format_object_ids(store) if store else None

    async def find_active_stores(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Find active stores with pagination.

        Args:
            skip: Number of documents to skip
            limit: Maximum number of documents to return

        Returns:
            List of active store documents
        """
        return await self.find_many({"is_active": True}, skip, limit)

    async def find_by_location(self, city: Optional[str] = None, state: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Find stores by location.

        Args:
            city: City name
            state: State name

        Returns:
            List of store documents
        """
        query = {}

        if city:
            query["city"] = {"$regex": city, "$options": "i"}

        if state:
            query["state"] = {"$regex": state, "$options": "i"}

        return await self.find_many(query)
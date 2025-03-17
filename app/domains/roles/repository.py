"""
Role repository for database operations.
"""
from typing import Dict, List, Optional, Any

from app.db.base_repository import BaseRepository
from app.db.mongodb import get_roles_collection
from app.utils.id_handler import IdHandler


class RoleRepository(BaseRepository):
    """
    Repository for role data access.
    Extends BaseRepository with role-specific operations.
    """

    def __init__(self):
        """Initialize with roles collection."""
        super().__init__(get_roles_collection())

    async def find_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Find a role by name.

        Args:
            name: Role name

        Returns:
            Role document or None if not found
        """
        role = await self.collection.find_one({"name": name})
        return IdHandler.format_object_ids(role) if role else None

    async def name_exists(self, name: str) -> bool:
        """
        Check if role name already exists.

        Args:
            name: Role name to check

        Returns:
            True if name exists
        """
        count = await self.collection.count_documents({"name": name})
        return count > 0
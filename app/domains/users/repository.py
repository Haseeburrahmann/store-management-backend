"""
User repository for database operations.
"""
from typing import Dict, List, Optional, Any

from app.db.base_repository import BaseRepository
from app.db.mongodb import get_users_collection
from app.utils.id_handler import IdHandler


class UserRepository(BaseRepository):
    """
    Repository for user data access.
    Extends BaseRepository with user-specific operations.
    """

    def __init__(self):
        """Initialize with users collection."""
        super().__init__(get_users_collection())

    async def find_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Find a user by email.

        Args:
            email: User email

        Returns:
            User document or None if not found
        """
        user = await self.collection.find_one({"email": email})
        return IdHandler.format_object_ids(user) if user else None

    async def find_by_role(self, role_id: str) -> List[Dict[str, Any]]:
        """
        Find users by role ID.

        Args:
            role_id: Role ID

        Returns:
            List of user documents
        """
        role_obj_id = IdHandler.ensure_object_id(role_id)
        query = {"role_id": role_obj_id} if role_obj_id else {"role_id": role_id}

        users = await self.collection.find(query).to_list(length=100)
        return IdHandler.format_object_ids(users)

    async def find_active_users(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Find active users with pagination.

        Args:
            skip: Number of documents to skip
            limit: Maximum number of documents to return

        Returns:
            List of active user documents
        """
        return await self.find_many({"is_active": True}, skip, limit)

    async def email_exists(self, email: str) -> bool:
        """
        Check if email already exists.

        Args:
            email: Email to check

        Returns:
            True if email exists
        """
        count = await self.collection.count_documents({"email": email})
        return count > 0
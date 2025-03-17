"""
User service for business logic.
"""
from typing import Dict, List, Optional, Any
from fastapi import HTTPException, status

from app.core.security import get_password_hash, verify_password
from app.domains.users.repository import UserRepository
from app.utils.id_handler import IdHandler
from app.utils.datetime_handler import DateTimeHandler


class UserService:
    """
    Service for user-related business logic.
    """

    def __init__(self, user_repo: Optional[UserRepository] = None):
        """
        Initialize with user repository.

        Args:
            user_repo: Optional user repository instance
        """
        self.user_repo = user_repo or UserRepository()

    async def get_users(
            self,
            skip: int = 0,
            limit: int = 100,
            email: Optional[str] = None,
            role_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get users with optional filtering.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            email: Filter by email pattern
            role_id: Filter by role ID

        Returns:
            List of user documents
        """
        # Build query
        query = {}

        if email:
            query["email"] = {"$regex": email, "$options": "i"}

        if role_id:
            obj_id = IdHandler.ensure_object_id(role_id)
            query["role_id"] = str(obj_id) if obj_id else role_id

        return await self.user_repo.find_many(query, skip, limit)

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User document or None if not found
        """
        return await self.user_repo.find_by_id(user_id)

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Get user by email.

        Args:
            email: User email

        Returns:
            User document or None if not found
        """
        return await self.user_repo.find_by_email(email)

    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new user.

        Args:
            user_data: User data

        Returns:
            Created user document

        Raises:
            HTTPException: If email already exists
        """
        # Check if email already exists
        if await self.user_repo.email_exists(user_data.get("email", "")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Hash password
        if "password" in user_data:
            user_data["password"] = get_password_hash(user_data["password"])

        # Set default values
        if "is_active" not in user_data:
            user_data["is_active"] = True

        # Create user
        return await self.user_repo.create(user_data)

    async def update_user(self, user_id: str, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update an existing user.

        Args:
            user_id: User ID
            user_data: Updated user data

        Returns:
            Updated user document or None if not found

        Raises:
            HTTPException: If email already exists
        """
        # Check if user exists
        existing_user = await self.user_repo.find_by_id(user_id)
        if not existing_user:
            return None

        # Check if email is being changed and already exists
        if "email" in user_data and user_data["email"] != existing_user.get("email"):
            if await self.user_repo.email_exists(user_data["email"]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )

        # Hash password if provided
        if "password" in user_data and user_data["password"]:
            user_data["password"] = get_password_hash(user_data["password"])

        # Update user
        return await self.user_repo.update(user_id, user_data)

    async def delete_user(self, user_id: str) -> bool:
        """
        Delete a user.

        Args:
            user_id: User ID

        Returns:
            True if user was deleted
        """
        return await self.user_repo.delete(user_id)

    async def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Authenticate a user with email and password.

        Args:
            email: User email
            password: User password

        Returns:
            User document if authentication successful, None otherwise
        """
        user = await self.user_repo.find_by_email(email)
        if not user:
            return None

        if not verify_password(password, user.get("password", "")):
            return None

        return user

    async def is_active(self, user_id: str) -> bool:
        """
        Check if a user is active.

        Args:
            user_id: User ID

        Returns:
            True if user is active
        """
        user = await self.user_repo.find_by_id(user_id)
        return user is not None and user.get("is_active", False)


# Create global instance
user_service = UserService()
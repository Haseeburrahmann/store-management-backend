"""
Role service for business logic.
"""
from typing import Dict, List, Optional, Any, Set
from fastapi import HTTPException, status

from app.core.permissions import DEFAULT_ROLES
from app.domains.roles.repository import RoleRepository
from app.utils.id_handler import IdHandler
from app.utils.datetime_handler import DateTimeHandler


class RoleService:
    """
    Service for role-related business logic.
    """

    def __init__(self, role_repo: Optional[RoleRepository] = None):
        """
        Initialize with role repository.

        Args:
            role_repo: Optional role repository instance
        """
        self.role_repo = role_repo or RoleRepository()

    async def get_roles(
        self,
        skip: int = 0,
        limit: int = 100,
        name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get roles with optional filtering.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            name: Filter by name pattern

        Returns:
            List of role documents
        """
        # Build query
        query = {}

        if name:
            query["name"] = {"$regex": name, "$options": "i"}

        return await self.role_repo.find_many(query, skip, limit)

    async def get_role_by_id(self, role_id: str) -> Optional[Dict[str, Any]]:
        """
        Get role by ID.

        Args:
            role_id: Role ID

        Returns:
            Role document or None if not found
        """
        return await self.role_repo.find_by_id(role_id)

    async def get_role_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get role by name.

        Args:
            name: Role name

        Returns:
            Role document or None if not found
        """
        return await self.role_repo.find_by_name(name)

    async def create_role(self, role_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new role.

        Args:
            role_data: Role data

        Returns:
            Created role document

        Raises:
            HTTPException: If name already exists
        """
        # Check if name already exists
        if await self.role_repo.name_exists(role_data.get("name", "")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role with name '{role_data.get('name')}' already exists"
            )

        # Create role
        return await self.role_repo.create(role_data)

    async def update_role(self, role_id: str, role_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update an existing role.

        Args:
            role_id: Role ID
            role_data: Updated role data

        Returns:
            Updated role document or None if not found

        Raises:
            HTTPException: If name already exists or trying to modify default role
        """
        # Check if role exists
        existing_role = await self.role_repo.find_by_id(role_id)
        if not existing_role:
            return None

        # Check if it's a default role
        role_name = existing_role.get("name")
        for default_role in DEFAULT_ROLES.values():
            if default_role["name"] == role_name:
                # Restrict modifications to default roles
                if "name" in role_data and role_data["name"] != role_name:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Cannot change the name of default role '{role_name}'"
                    )

        # Check if name is being changed and already exists
        if "name" in role_data and role_data["name"] != existing_role.get("name"):
            if await self.role_repo.name_exists(role_data["name"]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Role with name '{role_data['name']}' already exists"
                )

        # Update role
        return await self.role_repo.update(role_id, role_data)

    async def delete_role(self, role_id: str) -> bool:
        """
        Delete a role.

        Args:
            role_id: Role ID

        Returns:
            True if role was deleted

        Raises:
            HTTPException: If trying to delete a default role
        """
        # Check if role exists
        existing_role = await self.role_repo.find_by_id(role_id)
        if not existing_role:
            return False

        # Check if it's a default role
        role_name = existing_role.get("name")
        for default_role in DEFAULT_ROLES.values():
            if default_role["name"] == role_name:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot delete default role '{role_name}'"
                )

        # Delete role
        return await self.role_repo.delete(role_id)

    async def create_default_roles(self) -> None:
        """
        Create default roles if they don't exist.
        """
        for role_key, role_data in DEFAULT_ROLES.items():
            # Check if role already exists
            existing_role = await self.role_repo.find_by_name(role_data["name"])
            if not existing_role:
                print(f"Creating default role: {role_data['name']}")
                await self.role_repo.create(role_data)
            else:
                # Update permissions if needed
                current_permissions = set(existing_role.get("permissions", []))
                default_permissions = set(role_data["permissions"])

                if current_permissions != default_permissions:
                    print(f"Updating permissions for role: {role_data['name']}")
                    await self.role_repo.update(
                        str(existing_role["_id"]),
                        {"permissions": role_data["permissions"]}
                    )

    async def get_role_permissions(self, role_id: Optional[str]) -> Set[str]:
        """
        Get permissions for a role.

        Args:
            role_id: Role ID

        Returns:
            Set of permission strings
        """
        if not role_id:
            return set()

        role = await self.role_repo.find_by_id(role_id)
        if not role:
            return set()

        return set(role.get("permissions", []))

    async def user_has_role(self, user_id: str, role_names: List[str]) -> bool:
        """
        Check if a user has one of the specified roles.

        Args:
            user_id: User ID
            role_names: List of role names to check

        Returns:
            True if user has one of the roles
        """
        # Get user from database
        from app.domains.users.service import user_service
        user = await user_service.get_user_by_id(user_id)
        if not user or "role_id" not in user:
            return False

        # Get role
        role = await self.role_repo.find_by_id(user["role_id"])
        if not role:
            return False

        # Check if role name matches
        return role.get("name") in role_names


# Create global instance
role_service = RoleService()
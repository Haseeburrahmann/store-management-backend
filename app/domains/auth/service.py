"""
Auth service for authentication and authorization.
"""
from datetime import timedelta
from typing import Dict, Optional, Any, Tuple

from fastapi import HTTPException, status

from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.domains.users.service import user_service
from app.domains.roles.service import role_service


class AuthService:
    """
    Service for authentication and authorization.
    """

    async def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Authenticate a user with email and password.

        Args:
            email: User email
            password: User password

        Returns:
            User document if authentication successful, None otherwise
        """
        # Get user by email
        user = await user_service.get_user_by_email(email)
        if not user:
            return None

        # Check if user is active
        if not user.get("is_active", False):
            return None

        # Verify password
        if not verify_password(password, user.get("password", "")):
            return None

        return user

    async def login(self, email: str, password: str) -> Dict[str, str]:
        """
        Login a user and return access token.

        Args:
            email: User email
            password: User password

        Returns:
            Dict with access token and token type

        Raises:
            HTTPException: If authentication fails
        """
        # Authenticate user
        user = await self.authenticate_user(email, password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            subject=str(user["_id"]),
            expires_delta=access_token_expires
        )

        return {"access_token": access_token, "token_type": "bearer"}

    async def register(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register a new user.

        Args:
            user_data: User data

        Returns:
            Created user document

        Raises:
            HTTPException: If email already exists
        """
        # Check if user with this email already exists
        existing_user = await user_service.get_user_by_email(user_data.get("email", ""))
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Set default role if not provided
        if "role_id" not in user_data:
            employee_role = await role_service.get_role_by_name("Employee")
            if employee_role:
                user_data["role_id"] = str(employee_role["_id"])

        # Create user
        return await user_service.create_user(user_data)

    async def check_user_permission(self, user_id: str, required_permission: str) -> bool:
        """
        Check if a user has a specific permission.

        Args:
            user_id: User ID
            required_permission: Permission string to check

        Returns:
            True if user has the permission
        """
        # Get user
        user = await user_service.get_user_by_id(user_id)
        if not user or not user.get("is_active", False):
            return False

        # Get role permissions
        role_id = user.get("role_id")
        if not role_id:
            return False

        # Get role permissions
        permissions = await role_service.get_role_permissions(role_id)

        # Check permission
        return required_permission in permissions


# Create global instance
auth_service = AuthService()
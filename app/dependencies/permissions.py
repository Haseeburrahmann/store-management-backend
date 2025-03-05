# app/dependencies/permissions.py
from typing import List, Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from jose import jwt, JWTError
from pydantic import ValidationError
from app.core.config import settings
from app.core.security import oauth2_scheme, check_permissions
from app.services.user import get_user_by_id
from app.services.role import get_role_by_id
from bson import ObjectId


async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """
    Get the current user from JWT token
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except (JWTError, ValidationError):
        raise credentials_exception

    user = await get_user_by_id(ObjectId(user_id))
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
        current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get the current active user
    """
    if not current_user.get("is_active", False):
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_user_permissions(user: Dict[str, Any]) -> List[str]:
    """
    Get permissions for the current user based on their role
    """
    if not user.get("role_id"):
        return []

    role = await get_role_by_id(user["role_id"])
    if not role:
        return []

    return role.get("permissions", [])


def has_permission(required_permission: str):
    """
    Dependency to check if the current user has the required permission
    """

    async def permission_checker(
            current_user: Dict[str, Any] = Depends(get_current_active_user)
    ):
        user_permissions = await get_user_permissions(current_user)

        # Debug prints
        print(f"User permissions: {user_permissions}")
        print(f"Required permission: {required_permission}")

        if not check_permissions(user_permissions, required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )

        return current_user

    return permission_checker
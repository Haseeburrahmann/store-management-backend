# app/dependencies/permissions.py
from typing import List, Optional, Dict, Any, Callable
from fastapi import Depends, HTTPException, status
from jose import jwt, JWTError
from pydantic import ValidationError

from app.core.config import settings
from app.core.security import oauth2_scheme, check_permissions
from app.services.user import get_user_by_id
from app.services.role import get_role_by_id
from app.utils.formatting import ensure_object_id


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

    user = await get_user_by_id(user_id)
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

    role_id = user.get("role_id")
    role = await get_role_by_id(role_id)
    if not role:
        return []

    return role.get("permissions", [])


def has_permission(required_permission: str) -> Callable:
    """
    Dependency to check if the current user has the required permission
    """

    async def permission_checker(
            current_user: Dict[str, Any] = Depends(get_current_active_user)
    ) -> Dict[str, Any]:
        user_permissions = await get_user_permissions(current_user)

        if not check_permissions(user_permissions, required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )

        return current_user

    return permission_checker


def has_store_permission(required_permission: str, store_id_param: str = "store_id") -> Callable:
    """
    Dependency to check if the current user has the required permission for a specific store
    """

    async def store_permission_checker(
            store_id: str,
            current_user: Dict[str, Any] = Depends(get_current_active_user)
    ) -> Dict[str, Any]:
        # Get user permissions
        user_permissions = await get_user_permissions(current_user)

        # Check if user has admin-level permission for this action
        if check_permissions(user_permissions, required_permission):
            return current_user

        # Check if user is a manager of this specific store
        from app.services.store import StoreService
        store = await StoreService.get_store(store_id)

        if store and store.get("manager_id") and str(store.get("manager_id")) == str(current_user.get("_id")):
            # Manager has access to their own store
            return current_user

        # User doesn't have permission for this store
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Not enough permissions for store {store_id}",
        )

    return store_permission_checker


def has_employee_permission(required_permission: str) -> Callable:
    """
    Dependency to check if the current user has the required permission for an employee
    This allows managers to access their store's employees
    """

    async def employee_permission_checker(
            employee_id: str,
            current_user: Dict[str, Any] = Depends(get_current_active_user)
    ) -> Dict[str, Any]:
        # Get user permissions
        user_permissions = await get_user_permissions(current_user)

        # Check if user has admin-level permission for this action
        if check_permissions(user_permissions, required_permission):
            return current_user

        # Check if current user is this employee
        from app.services.employee import EmployeeService
        employee = await EmployeeService.get_employee(employee_id)

        if employee and employee.get("user_id") and str(employee.get("user_id")) == str(current_user.get("_id")):
            # Employee has access to their own data
            return current_user

        # Check if user is a manager of this employee's store
        if employee and employee.get("store_id"):
            from app.services.store import StoreService
            store = await StoreService.get_store(employee.get("store_id"))

            if store and store.get("manager_id") and str(store.get("manager_id")) == str(current_user.get("_id")):
                # Manager has access to employees in their store
                return current_user

        # User doesn't have permission for this employee
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Not enough permissions for employee {employee_id}",
        )

    return employee_permission_checker
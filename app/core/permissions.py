"""
Permission system with simplified resource:action format.
"""
from enum import Enum
from typing import Dict, List, Set, Optional, Callable, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.core.config import settings


# Permission constants
class PermissionArea(str, Enum):
    """Resource areas for permissions"""
    USERS = "users"
    ROLES = "roles"
    STORES = "stores"
    EMPLOYEES = "employees"
    HOURS = "hours"
    PAYMENTS = "payments"
    INVENTORY = "inventory"
    STOCK_REQUESTS = "stock_requests"
    SALES = "sales"
    REPORTS = "reports"
    SCHEDULES = "schedules"
    TIMESHEETS = "timesheets"


class PermissionAction(str, Enum):
    """Actions for permissions"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    APPROVE = "approve"


def get_permission_string(area: PermissionArea, action: PermissionAction) -> str:
    """
    Generate a permission string in the format 'area:action'

    Args:
        area: Permission area (resource)
        action: Permission action

    Returns:
        Permission string
    """
    return f"{area.value}:{action.value}"


# Default roles with permissions
DEFAULT_ROLES = {
    "admin": {
        "name": "Admin",
        "description": "Administrator with full system access",
        "permissions": [
            get_permission_string(area, action)
            for area in PermissionArea
            for action in PermissionAction
        ]
    },
    "manager": {
        "name": "Manager",
        "description": "Store manager with limited administrative access",
        "permissions": [
            # Users & roles - limited access
            get_permission_string(PermissionArea.USERS, PermissionAction.READ),

            # Full access to store management
            get_permission_string(PermissionArea.STORES, PermissionAction.READ),
            get_permission_string(PermissionArea.STORES, PermissionAction.WRITE),

            # Full access to employees, hours, payments
            get_permission_string(PermissionArea.EMPLOYEES, PermissionAction.READ),
            get_permission_string(PermissionArea.EMPLOYEES, PermissionAction.WRITE),
            get_permission_string(PermissionArea.HOURS, PermissionAction.READ),
            get_permission_string(PermissionArea.HOURS, PermissionAction.WRITE),
            get_permission_string(PermissionArea.HOURS, PermissionAction.APPROVE),
            get_permission_string(PermissionArea.PAYMENTS, PermissionAction.READ),
            get_permission_string(PermissionArea.PAYMENTS, PermissionAction.WRITE),
            get_permission_string(PermissionArea.PAYMENTS, PermissionAction.APPROVE),

            # Full access to inventory and stock requests
            get_permission_string(PermissionArea.INVENTORY, PermissionAction.READ),
            get_permission_string(PermissionArea.INVENTORY, PermissionAction.WRITE),
            get_permission_string(PermissionArea.STOCK_REQUESTS, PermissionAction.READ),
            get_permission_string(PermissionArea.STOCK_REQUESTS, PermissionAction.WRITE),
            get_permission_string(PermissionArea.STOCK_REQUESTS, PermissionAction.APPROVE),

            # Full access to sales and reports
            get_permission_string(PermissionArea.SALES, PermissionAction.READ),
            get_permission_string(PermissionArea.SALES, PermissionAction.WRITE),
            get_permission_string(PermissionArea.REPORTS, PermissionAction.READ),

            # Hours tracking
            get_permission_string(PermissionArea.SCHEDULES, PermissionAction.READ),
            get_permission_string(PermissionArea.SCHEDULES, PermissionAction.WRITE),
            get_permission_string(PermissionArea.TIMESHEETS, PermissionAction.READ),
            get_permission_string(PermissionArea.TIMESHEETS, PermissionAction.WRITE),
            get_permission_string(PermissionArea.TIMESHEETS, PermissionAction.APPROVE),
        ]
    },
    "employee": {
        "name": "Employee",
        "description": "Regular store employee with limited access",
        "permissions": [
            # Read-only access to own profile
            get_permission_string(PermissionArea.USERS, PermissionAction.READ),
            get_permission_string(PermissionArea.USERS, PermissionAction.WRITE),

            # Limited access to hours (clock in/out)
            get_permission_string(PermissionArea.HOURS, PermissionAction.READ),
            get_permission_string(PermissionArea.HOURS, PermissionAction.WRITE),
            get_permission_string(PermissionArea.ROLES, PermissionAction.READ),

            # Limited access to payments (view own)
            get_permission_string(PermissionArea.PAYMENTS, PermissionAction.READ),

            # Limited access to inventory (view)
            get_permission_string(PermissionArea.INVENTORY, PermissionAction.READ),

            # Stock requests - can create and view
            get_permission_string(PermissionArea.STOCK_REQUESTS, PermissionAction.READ),
            get_permission_string(PermissionArea.STOCK_REQUESTS, PermissionAction.WRITE),

            # Sales - can record
            get_permission_string(PermissionArea.SALES, PermissionAction.WRITE),
            get_permission_string(PermissionArea.SALES, PermissionAction.READ),

            # Hours tracking
            get_permission_string(PermissionArea.STORES, PermissionAction.READ),
            get_permission_string(PermissionArea.SCHEDULES, PermissionAction.READ),
            get_permission_string(PermissionArea.EMPLOYEES, PermissionAction.READ),
            get_permission_string(PermissionArea.TIMESHEETS, PermissionAction.READ),
            get_permission_string(PermissionArea.TIMESHEETS, PermissionAction.WRITE),
        ]
    }
}


class PermissionChecker:
    """
    Permission checking service with caching.
    Provides methods to check and enforce permissions.
    """

    def __init__(self):
        """Initialize permission checker with empty cache."""
        self._permissions_cache = {}  # user_id -> permissions set

    def clear_cache(self):
        """Clear the permissions cache."""
        self._permissions_cache = {}

    def clear_user_cache(self, user_id: str):
        """
        Clear the permissions cache for a specific user.

        Args:
            user_id: User ID to clear from cache
        """
        if user_id in self._permissions_cache:
            del self._permissions_cache[user_id]

    async def get_user_permissions(self, user: Dict[str, Any]) -> Set[str]:
        """
        Get permissions for a user with caching.

        Args:
            user: User dictionary with _id and role_id fields

        Returns:
            Set of permission strings
        """
        if not user:
            return set()

        user_id = str(user.get("_id", ""))

        # Return from cache if available
        if user_id in self._permissions_cache:
            return self._permissions_cache[user_id]

        # Get role permissions from database
        permissions = set()
        role_id = user.get("role_id")

        if role_id:
            from app.db.mongodb import get_roles_collection
            roles_collection = get_roles_collection()

            # Find role document
            from app.utils.id_handler import IdHandler
            role, _ = await IdHandler.find_document_by_id(
                roles_collection,
                role_id,
                "Role not found"
            )

            if role and "permissions" in role:
                permissions = set(role["permissions"])

        # Cache permissions
        self._permissions_cache[user_id] = permissions

        return permissions

    async def has_permission(self, user: Dict[str, Any], required_permission: str) -> bool:
        """
        Check if a user has a specific permission.

        Args:
            user: User dictionary
            required_permission: Permission string to check

        Returns:
            True if user has the permission, False otherwise
        """
        if not user:
            return False

        # Get user permissions
        user_permissions = await self.get_user_permissions(user)

        # Check permission directly
        if required_permission in user_permissions:
            return True

        return False

    def requires_permission(self, required_permission: str) -> Callable:
        """
        FastAPI dependency for routes that require a specific permission.

        Args:
            required_permission: Permission string required for access

        Returns:
            Dependency function
        """

        async def dependency(current_user: Dict[str, Any] = Depends(get_current_user)):
            has_perm = await self.has_permission(current_user, required_permission)
            if not has_perm:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Not enough permissions: {required_permission} required"
                )
            return current_user

        return dependency

    async def get_user_permission_list(self, user: Dict[str, Any]) -> List[str]:
        """
        Get list of permissions for a user.

        Args:
            user: User dictionary

        Returns:
            List of permission strings
        """
        perms = await self.get_user_permissions(user)
        return list(perms)


# Create OAuth2 scheme for token handling
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

# Create global permission checker instance
permission_checker = PermissionChecker()


async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """
    Get the current user from JWT token.

    Args:
        token: JWT token from Authorization header

    Returns:
        User dictionary

    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decode token
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Get user from database
    from app.db.mongodb import get_users_collection
    from app.utils.id_handler import IdHandler

    users_collection = get_users_collection()
    user, _ = await IdHandler.find_document_by_id(users_collection, user_id)

    if user is None:
        raise credentials_exception

    return IdHandler.format_object_ids(user)


async def get_current_active_user(
        current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get the current active user.

    Args:
        current_user: User dictionary from get_current_user

    Returns:
        User dictionary

    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


def has_permission(required_permission: str) -> Callable:
    """
    Dependency to check if the current user has the required permission.

    Args:
        required_permission: Permission string required for access

    Returns:
        Dependency function
    """
    return permission_checker.requires_permission(required_permission)
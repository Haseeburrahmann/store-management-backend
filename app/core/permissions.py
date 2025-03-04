# app/core/permissions.py
from enum import Enum
from typing import Dict, List, Set


class PermissionArea(str, Enum):
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


class PermissionAction(str, Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    APPROVE = "approve"


def get_permission_string(area: PermissionArea, action: PermissionAction) -> str:
    """
    Generate a permission string in the format 'area:action'
    """
    return f"{area}:{action}"


# Predefined roles with their permissions
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
        ]
    },
    "employee": {
        "name": "Employee",
        "description": "Regular store employee with limited access",
        "permissions": [
            # Read-only access to own profile
            get_permission_string(PermissionArea.USERS, PermissionAction.READ),

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
        ]
    }
}

def has_permission(user_permissions: List[str], required_permission: str) -> bool:
    """
    Check if a user has the required permission
    """
    return required_permission in user_permissions
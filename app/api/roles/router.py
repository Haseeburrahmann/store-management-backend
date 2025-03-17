"""
Role API routes for role management.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.domains.roles.service import role_service
from app.core.permissions import has_permission
from app.schemas.role import RoleCreate, RoleUpdate, RoleResponse

router = APIRouter()


@router.get("/", response_model=List[RoleResponse])
async def read_roles(
        skip: int = 0,
        limit: int = 100,
        name: Optional[str] = None,
        current_user: dict = Depends(has_permission("roles:read"))
):
    """
    Get all roles with optional filtering.

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        name: Filter by name pattern
        current_user: Current user from token

    Returns:
        List of roles
    """
    try:
        roles = await role_service.get_roles(skip, limit, name)
        return roles
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching roles: {str(e)}"
        )


@router.get("/{role_id}", response_model=RoleResponse)
async def read_role(
        role_id: str,
        current_user: dict = Depends(has_permission("roles:read"))
):
    """
    Get role by ID.

    Args:
        role_id: Role ID
        current_user: Current user from token

    Returns:
        Role

    Raises:
        HTTPException: If role not found
    """
    try:
        role = await role_service.get_role_by_id(role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role with ID {role_id} not found"
            )
        return role
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching role: {str(e)}"
        )


@router.post("/", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_new_role(
        role_data: RoleCreate,
        current_user: dict = Depends(has_permission("roles:write"))
):
    """
    Create new role.

    Args:
        role_data: Role creation data
        current_user: Current user from token

    Returns:
        Created role
    """
    try:
        role = await role_service.create_role(role_data.model_dump())
        return role
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating role: {str(e)}"
        )


@router.put("/{role_id}", response_model=RoleResponse)
async def update_existing_role(
        role_id: str,
        role_data: RoleUpdate,
        current_user: dict = Depends(has_permission("roles:write"))
):
    """
    Update existing role.

    Args:
        role_id: Role ID
        role_data: Role update data
        current_user: Current user from token

    Returns:
        Updated role

    Raises:
        HTTPException: If role not found
    """
    try:
        updated_role = await role_service.update_role(role_id, role_data.model_dump(exclude_unset=True))
        if not updated_role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role with ID {role_id} not found"
            )
        return updated_role
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating role: {str(e)}"
        )


@router.delete("/{role_id}", response_model=bool)
async def delete_existing_role(
        role_id: str,
        current_user: dict = Depends(has_permission("roles:delete"))
):
    """
    Delete role.

    Args:
        role_id: Role ID
        current_user: Current user from token

    Returns:
        True if role was deleted

    Raises:
        HTTPException: If role not found or cannot be deleted
    """
    try:
        result = await role_service.delete_role(role_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role with ID {role_id} not found"
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting role: {str(e)}"
        )
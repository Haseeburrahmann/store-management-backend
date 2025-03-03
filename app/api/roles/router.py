from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from bson import ObjectId

from app.core.permissions import PermissionArea, PermissionAction, get_permission_string
from app.dependencies.permissions import has_permission
from app.schemas.role import RoleCreate, RoleUpdate, RoleResponse
from app.services.role import create_role, update_role, delete_role, get_role_by_id, list_roles, get_role_by_name

router = APIRouter()


@router.get("/", response_model=List[RoleResponse])
async def read_roles(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: dict = Depends(has_permission(get_permission_string(PermissionArea.ROLES, PermissionAction.READ)))
):
    """
    Retrieve roles with pagination.
    """
    roles = await list_roles(skip=skip, limit=limit)
    return roles


@router.post("/", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_new_role(
        role_in: RoleCreate,
        current_user: dict = Depends(
            has_permission(get_permission_string(PermissionArea.ROLES, PermissionAction.WRITE)))
):
    """
    Create new role.
    """
    # Check if role with this name already exists
    role = await get_role_by_name(role_in.name)
    if role:
        raise HTTPException(
            status_code=400,
            detail="A role with this name already exists."
        )

    role_data = role_in.dict()
    created_role = await create_role(role_data)

    return RoleResponse(
        _id=str(created_role.id),
        name=created_role.name,
        description=created_role.description,
        permissions=created_role.permissions,
        created_at=created_role.created_at,
        updated_at=created_role.updated_at
    )


@router.get("/{role_id}", response_model=RoleResponse)
async def read_role(
        role_id: str,
        current_user: dict = Depends(has_permission(get_permission_string(PermissionArea.ROLES, PermissionAction.READ)))
):
    """
    Get a specific role by id.
    """
    role = await get_role_by_id(ObjectId(role_id))
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    return RoleResponse(
        _id=str(role.id),
        name=role.name,
        description=role.description,
        permissions=role.permissions,
        created_at=role.created_at,
        updated_at=role.updated_at
    )


@router.put("/{role_id}", response_model=RoleResponse)
async def update_role_by_id(
        role_id: str,
        role_in: RoleUpdate,
        current_user: dict = Depends(
            has_permission(get_permission_string(PermissionArea.ROLES, PermissionAction.WRITE)))
):
    """
    Update a role.
    """
    role = await get_role_by_id(ObjectId(role_id))
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    role_data = role_in.dict(exclude_unset=True)

    # If name is changed, check if it already exists
    if "name" in role_data and role_data["name"] != role.name:
        existing_role = await get_role_by_name(role_data["name"])
        if existing_role:
            raise HTTPException(
                status_code=400,
                detail="A role with this name already exists."
            )

    updated_role = await update_role(ObjectId(role_id), role_data)

    return RoleResponse(
        _id=str(updated_role.id),
        name=updated_role.name,
        description=updated_role.description,
        permissions=updated_role.permissions,
        created_at=updated_role.created_at,
        updated_at=updated_role.updated_at
    )


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role_by_id(
        role_id: str,
        current_user: dict = Depends(
            has_permission(get_permission_string(PermissionArea.ROLES, PermissionAction.DELETE)))
):
    """
    Delete a role.
    """
    role = await get_role_by_id(ObjectId(role_id))
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    # Check if role is used by any users before deleting
    # This requires an additional query to the users collection
    # For simplicity, we'll implement this later

    await delete_role(ObjectId(role_id))

    return None
# app/api/roles/router.py
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.dependencies.permissions import get_current_user, has_permission
from app.schemas.role import RoleCreate, RoleUpdate, RoleResponse
from app.services.role import get_roles, get_role_by_id, create_role, update_role, delete_role
from bson import ObjectId

router = APIRouter()

@router.get("/", response_model=List[RoleResponse])
async def read_roles(
    skip: int = 0,
    limit: int = 100,
    name: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(has_permission("roles:read"))
):
    """
    Get all roles with optional filtering
    """
    roles = await get_roles(skip, limit, name)
    return roles

@router.get("/{role_id}", response_model=RoleResponse)
async def read_role(
    role_id: str,
    current_user: Dict[str, Any] = Depends(has_permission("roles:read"))
):
    """
    Get role by ID
    """
    role = await get_role_by_id(role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role

@router.post("/", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_new_role(
    role_data: RoleCreate,
    current_user: Dict[str, Any] = Depends(has_permission("roles:write"))
):
    """
    Create new role
    """
    return await create_role(role_data.model_dump())

@router.put("/{role_id}", response_model=RoleResponse)
async def update_existing_role(
    role_id: str,
    role_data: RoleUpdate,
    current_user: Dict[str, Any] = Depends(has_permission("roles:write"))
):
    """
    Update existing role
    """
    updated_role = await update_role(role_id, role_data.model_dump(exclude_unset=True))
    if not updated_role:
        raise HTTPException(status_code=404, detail="Role not found")
    return updated_role

@router.delete("/{role_id}", response_model=bool)
async def delete_existing_role(
    role_id: str,
    current_user: Dict[str, Any] = Depends(has_permission("roles:delete"))
):
    """
    Delete role
    """
    result = await delete_role(role_id)
    if not result:
        raise HTTPException(status_code=404, detail="Role not found")
    return result
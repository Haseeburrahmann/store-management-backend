# app/api/users/router.py
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.dependencies.permissions import get_current_user, has_permission, get_current_active_user
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserWithPermissions
from app.services.user import get_users, get_user_by_id, create_user, update_user, delete_user
from app.services.role import get_role_by_id
from bson import ObjectId

router = APIRouter()


@router.get("/", response_model=List[UserResponse])
async def read_users(
        skip: int = 0,
        limit: int = 100,
        email: Optional[str] = None,
        role_id: Optional[str] = None,
        current_user: Dict[str, Any] = Depends(has_permission("users:read"))
):
    """
    Get all users with optional filtering
    """
    users = await get_users(skip, limit, email, role_id)
    return users


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: Dict[str, Any] = Depends(get_current_active_user)):
    """
    Get current user profile
    """
    from app.utils.formatting import format_object_ids
    # Format ObjectIds to strings before returning
    return format_object_ids(current_user)


@router.get("/{user_id}", response_model=UserResponse)
async def read_user(
        user_id: str,
        current_user: Dict[str, Any] = Depends(has_permission("users:read"))
):
    """
    Get user by ID
    """
    user = await get_user_by_id(ObjectId(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_new_user(
        user_data: UserCreate,
        current_user: Dict[str, Any] = Depends(has_permission("users:write"))
):
    """
    Create new user
    """
    return await create_user(user_data.model_dump())


@router.put("/{user_id}", response_model=UserResponse)
async def update_existing_user(
        user_id: str,
        user_data: UserUpdate,
        current_user: Dict[str, Any] = Depends(has_permission("users:write"))
):
    """
    Update existing user
    """
    updated_user = await update_user(user_id, user_data.model_dump(exclude_unset=True))
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    return updated_user


@router.delete("/{user_id}", response_model=bool)
async def delete_existing_user(
        user_id: str,
        current_user: Dict[str, Any] = Depends(has_permission("users:delete"))
):
    """
    Delete user
    """
    result = await delete_user(user_id)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return result
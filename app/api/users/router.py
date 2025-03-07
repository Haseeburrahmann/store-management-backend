# app/api/users/router.py
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.dependencies.permissions import get_current_user, has_permission, get_current_active_user
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserWithPermissions
from app.services.user import get_users, get_user_by_id, create_user, update_user, delete_user
from app.utils.formatting import ensure_object_id

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
    # User already formatted by dependency
    return current_user


@router.get("/{user_id}", response_model=UserResponse)
async def read_user(
        user_id: str,
        current_user: Dict[str, Any] = Depends(has_permission("users:read"))
):
    """
    Get user by ID
    """
    # Use the improved get_user_by_id that handles different ID formats
    user = await get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    return user


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_new_user(
        user_data: UserCreate,
        current_user: Dict[str, Any] = Depends(has_permission("users:write"))
):
    """
    Create new user
    """
    # Check if email already exists
    from app.services.user import get_user_by_email
    existing_user = await get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

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
    # First check if user exists to provide better error message
    existing_user = await get_user_by_id(user_id)
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )

    updated_user = await update_user(user_id, user_data.model_dump(exclude_unset=True))
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating user"
        )
    return updated_user


@router.delete("/{user_id}", response_model=bool)
async def delete_existing_user(
        user_id: str,
        current_user: Dict[str, Any] = Depends(has_permission("users:delete"))
):
    """
    Delete user
    """
    # Check if user exists first
    existing_user = await get_user_by_id(user_id)
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )

    # Check if user is trying to delete themselves
    if str(current_user["_id"]) == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    result = await delete_user(user_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting user"
        )
    return result
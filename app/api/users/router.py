"""
User API routes for user management.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.domains.users.service import user_service
from app.core.permissions import has_permission, get_current_active_user
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserWithPermissions

router = APIRouter()


@router.get("/", response_model=List[UserResponse])
async def read_users(
        skip: int = 0,
        limit: int = 100,
        email: Optional[str] = None,
        role_id: Optional[str] = None,
        current_user: dict = Depends(has_permission("users:read"))
):
    """
    Get all users with optional filtering.

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        email: Filter by email pattern
        role_id: Filter by role ID
        current_user: Current user from token

    Returns:
        List of users
    """
    try:
        users = await user_service.get_users(skip, limit, email, role_id)
        return users
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching users: {str(e)}"
        )


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: dict = Depends(get_current_active_user)):
    """
    Get current user profile.

    Args:
        current_user: Current user from token

    Returns:
        Current user profile
    """
    return current_user


@router.get("/{user_id}", response_model=UserResponse)
async def read_user(
        user_id: str,
        current_user: dict = Depends(has_permission("users:read"))
):
    """
    Get user by ID.

    Args:
        user_id: User ID
        current_user: Current user from token

    Returns:
        User

    Raises:
        HTTPException: If user not found
    """
    try:
        user = await user_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching user: {str(e)}"
        )


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_new_user(
        user_data: UserCreate,
        current_user: dict = Depends(has_permission("users:write"))
):
    """
    Create new user.

    Args:
        user_data: User creation data
        current_user: Current user from token

    Returns:
        Created user
    """
    try:
        user = await user_service.create_user(user_data.model_dump())
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating user: {str(e)}"
        )


@router.put("/{user_id}", response_model=UserResponse)
async def update_existing_user(
        user_id: str,
        user_data: UserUpdate,
        current_user: dict = Depends(has_permission("users:write"))
):
    """
    Update existing user.

    Args:
        user_id: User ID
        user_data: User update data
        current_user: Current user from token

    Returns:
        Updated user

    Raises:
        HTTPException: If user not found
    """
    try:
        # Check if user exists
        existing_user = await user_service.get_user_by_id(user_id)
        if not existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )

        # Update user
        updated_user = await user_service.update_user(user_id, user_data.model_dump(exclude_unset=True))
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error updating user"
            )

        return updated_user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user: {str(e)}"
        )


@router.delete("/{user_id}", response_model=bool)
async def delete_existing_user(
        user_id: str,
        current_user: dict = Depends(has_permission("users:delete"))
):
    """
    Delete user.

    Args:
        user_id: User ID
        current_user: Current user from token

    Returns:
        True if user was deleted

    Raises:
        HTTPException: If user not found or cannot be deleted
    """
    try:
        # Check if user exists
        existing_user = await user_service.get_user_by_id(user_id)
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

        # Delete user
        result = await user_service.delete_user(user_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error deleting user"
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting user: {str(e)}"
        )
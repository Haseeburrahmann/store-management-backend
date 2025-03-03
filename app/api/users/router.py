from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from bson import ObjectId

from app.core.permissions import PermissionArea, PermissionAction, get_permission_string
from app.dependencies.permissions import get_current_active_user, has_permission
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserWithPermissions
from app.services.user import create_user, update_user, delete_user, get_user_by_id, list_users, get_user_by_email
from app.services.role import get_role_by_id

router = APIRouter()


@router.get("/", response_model=List[UserResponse])
async def read_users(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=100),
        current_user: dict = Depends(has_permission(get_permission_string(PermissionArea.USERS, PermissionAction.READ)))
):
    """
    Retrieve users with pagination.
    """
    users = await list_users(skip=skip, limit=limit)
    return users


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_new_user(
        user_in: UserCreate,
        current_user: dict = Depends(
            has_permission(get_permission_string(PermissionArea.USERS, PermissionAction.WRITE)))
):
    """
    Create new user.
    """
    # Check if user with this email already exists
    user = await get_user_by_email(user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="A user with this email already exists."
        )

    user_data = user_in.dict()
    created_user = await create_user(user_data)

    # Convert to response model
    return UserResponse(
        _id=str(created_user.id),
        email=created_user.email,
        full_name=created_user.full_name,
        phone_number=created_user.phone_number,
        is_active=created_user.is_active,
        role_id=str(created_user.role_id) if created_user.role_id else None,
        created_at=created_user.created_at,
        updated_at=created_user.updated_at
    )


@router.get("/me", response_model=UserWithPermissions)
async def read_user_me(
        current_user: dict = Depends(get_current_active_user)
):
    """
    Get current user with permissions.
    """
    user = await get_user_by_id(current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get user permissions based on role
    permissions = []
    if user.role_id:
        role = await get_role_by_id(user.role_id)
        if role:
            permissions = role.permissions

    return UserWithPermissions(
        _id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        phone_number=user.phone_number,
        is_active=user.is_active,
        role_id=str(user.role_id) if user.role_id else None,
        created_at=user.created_at,
        updated_at=user.updated_at,
        permissions=permissions
    )


@router.put("/me", response_model=UserResponse)
async def update_user_me(
        user_in: UserUpdate,
        current_user: dict = Depends(get_current_active_user)
):
    """
    Update current user.
    """
    user_data = user_in.dict(exclude_unset=True)

    # User can't change their own role
    if "role_id" in user_data:
        del user_data["role_id"]

    updated_user = await update_user(current_user.id, user_data)

    return UserResponse(
        _id=str(updated_user.id),
        email=updated_user.email,
        full_name=updated_user.full_name,
        phone_number=updated_user.phone_number,
        is_active=updated_user.is_active,
        role_id=str(updated_user.role_id) if updated_user.role_id else None,
        created_at=updated_user.created_at,
        updated_at=updated_user.updated_at
    )


@router.get("/{user_id}", response_model=UserResponse)
async def read_user(
        user_id: str,
        current_user: dict = Depends(has_permission(get_permission_string(PermissionArea.USERS, PermissionAction.READ)))
):
    """
    Get a specific user by id.
    """
    user = await get_user_by_id(ObjectId(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse(
        _id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        phone_number=user.phone_number,
        is_active=user.is_active,
        role_id=str(user.role_id) if user.role_id else None,
        created_at=user.created_at,
        updated_at=user.updated_at
    )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user_by_id(
        user_id: str,
        user_in: UserUpdate,
        current_user: dict = Depends(
            has_permission(get_permission_string(PermissionArea.USERS, PermissionAction.WRITE)))
):
    """
    Update a user.
    """
    user = await get_user_by_id(ObjectId(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user_data = user_in.dict(exclude_unset=True)

    # If role_id is provided, convert it to ObjectId
    if "role_id" in user_data and user_data["role_id"]:
        try:
            user_data["role_id"] = ObjectId(user_data["role_id"])
        except:
            raise HTTPException(status_code=400, detail="Invalid role ID")

    updated_user = await update_user(ObjectId(user_id), user_data)

    return UserResponse(
        _id=str(updated_user.id),
        email=updated_user.email,
        full_name=updated_user.full_name,
        phone_number=updated_user.phone_number,
        is_active=updated_user.is_active,
        role_id=str(updated_user.role_id) if updated_user.role_id else None,
        created_at=updated_user.created_at,
        updated_at=updated_user.updated_at
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_by_id(
        user_id: str,
        current_user: dict = Depends(
            has_permission(get_permission_string(PermissionArea.USERS, PermissionAction.DELETE)))
):
    """
    Delete a user.
    """
    user = await get_user_by_id(ObjectId(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent deleting yourself
    if str(user.id) == str(current_user.id):
        raise HTTPException(status_code=400, detail="You cannot delete your own user account")

    await delete_user(ObjectId(user_id))

    return None
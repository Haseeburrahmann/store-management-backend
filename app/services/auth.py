from typing import Optional
from datetime import timedelta
from app.models.user import UserDB
from bson import ObjectId

from fastapi import HTTPException, status
from app.core.security import verify_password, create_access_token
from app.services.user import get_user_by_email, create_user
from app.services.role import get_role_by_name
from app.schemas.user import UserCreate, UserInDB
from app.schemas.auth import Token
from app.core.config import settings


async def authenticate_user(email: str, password: str) -> Optional[UserDB]:
    """
    Authenticate a user
    """
    user = await get_user_by_email(email)
    if not user:
        return None
    if not verify_password(password, user.password):
        return None
    return user


async def login_for_access_token(email: str, password: str) -> Token:
    """
    Login for access token
    """
    user = await authenticate_user(email, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=str(user.id), expires_delta=access_token_expires
    )

    return Token(access_token=access_token, token_type="bearer")


async def register_new_user(user_data: UserCreate) -> UserInDB:
    """
    Register a new user
    """
    # Check if user with this email already exists
    existing_user = await get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # By default, assign 'employee' role to new users
    employee_role = await get_role_by_name("Employee")

    user_dict = user_data.dict()
    if employee_role:
        user_dict["role_id"] = employee_role.id

    return await create_user(user_dict)
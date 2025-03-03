from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta

from app.core.config import settings
from app.core.security import create_access_token
from app.schemas.auth import Token
from app.schemas.user import UserCreate, UserResponse
from app.services.auth import authenticate_user
from app.services.user import create_user, get_user_by_email
from app.dependencies.permissions import get_current_active_user

router = APIRouter()


@router.post("/login", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)
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

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/register", response_model=UserResponse)
async def register_user(user_in: UserCreate):
    # Check if user already exists
    existing_user = await get_user_by_email(user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Convert to dict for service function
    user_dict = user_in.model_dump()

    # Get the employee role
    from app.services.role import get_role_by_name
    employee_role = await get_role_by_name("Employee")
    if employee_role:
        user_dict["role_id"] = str(employee_role.id)

    # Create user
    user = await create_user(user_dict)

    # Convert to response model
    return UserResponse(
        _id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone_number=user.phone_number,
        is_active=user.is_active,
        role_id=user.role_id,
        created_at=user.created_at,
        updated_at=user.updated_at
    )


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: dict = Depends(get_current_active_user)):
    return current_user
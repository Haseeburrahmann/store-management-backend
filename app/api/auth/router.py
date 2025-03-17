"""
Auth API routes for authentication and authorization.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.domains.auth.service import auth_service
from app.domains.users.service import user_service
from app.core.permissions import get_current_active_user
from app.schemas.auth import Token
from app.schemas.user import UserCreate, UserResponse

router = APIRouter()


@router.post("/login", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Login with username (email) and password to get access token.

    Args:
        form_data: OAuth2 form with username and password

    Returns:
        Access token and token type
    """
    try:
        # The username field in OAuth2PasswordRequestForm contains the email
        result = await auth_service.login(form_data.username, form_data.password)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login error: {str(e)}"
        )


@router.post("/register", response_model=UserResponse)
async def register_user(user_in: UserCreate):
    """
    Register a new user.

    Args:
        user_in: User creation data

    Returns:
        Created user
    """
    try:
        # Convert to dict
        user_dict = user_in.model_dump()

        # Register user
        user = await auth_service.register(user_dict)
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration error: {str(e)}"
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
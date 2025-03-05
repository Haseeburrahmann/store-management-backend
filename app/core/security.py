# app/core/security.py
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import ValidationError

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def check_permissions(user_permissions: List[str], required_permission: str) -> bool:
    """
    Check if a user has the required permission

    Handles both formats:
    - Simple format: "area:action" (e.g., "users:read")
    - Full enum format: "PermissionArea.AREA:PermissionAction.ACTION"
    """
    # If the required permission is already in the full format, check directly
    if required_permission in user_permissions:
        return True

    # If the required permission is in simple format, convert to full format
    if ":" in required_permission and "PermissionArea" not in required_permission:
        area, action = required_permission.split(":")
        area_upper = area.upper()
        action_upper = action.upper()

        # Check with the full format
        full_permission = f"PermissionArea.{area_upper}:PermissionAction.{action_upper}"
        if full_permission in user_permissions:
            return True

        # Handle potential singular/plural inconsistencies
        if area_upper.endswith('S') and len(area_upper) > 1:
            # Try singular form if plural was provided
            singular_area = area_upper[:-1]
            singular_permission = f"PermissionArea.{singular_area}:PermissionAction.{action_upper}"
            if singular_permission in user_permissions:
                return True
        else:
            # Try plural form if singular was provided
            plural_permission = f"PermissionArea.{area_upper}S:PermissionAction.{action_upper}"
            if plural_permission in user_permissions:
                return True

    # Convert the other way - check if a simplified version of a user permission matches the required permission
    for permission in user_permissions:
        if "PermissionArea." in permission and "PermissionAction." in permission:
            # Extract the actual area and action
            parts = permission.split(":")
            if len(parts) == 2:
                area_part = parts[0].replace("PermissionArea.", "").lower()
                action_part = parts[1].replace("PermissionAction.", "").lower()
                simple_permission = f"{area_part}:{action_part}"

                if simple_permission == required_permission:
                    return True

    # No match found
    return False
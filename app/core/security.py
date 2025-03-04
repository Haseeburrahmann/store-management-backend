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
    """
    # Convert from "area:action" to "PermissionArea.AREA:PermissionAction.ACTION"
    if ":" in required_permission:
        area, action = required_permission.split(":")
        area_upper = area.upper()
        action_upper = action.upper()

        # Try both singular and plural forms
        if area_upper in ["STORE", "USER", "ROLE", "EMPLOYEE", "HOUR", "PAYMENT", "REPORT", "SALE"]:
            plural_area = f"{area_upper}S"
            full_permission_plural = f"PermissionArea.{plural_area}:PermissionAction.{action_upper}"
            if full_permission_plural in user_permissions:
                return True

        # Standard format check
        full_permission = f"PermissionArea.{area_upper}:PermissionAction.{action_upper}"
        if full_permission in user_permissions:
            return True

    # Direct check as fallback
    return required_permission in user_permissions
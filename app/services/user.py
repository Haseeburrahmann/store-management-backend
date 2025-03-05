# app/services/user.py
from datetime import datetime
from typing import List, Optional
from bson import ObjectId
from app.core.db import get_database
from app.models.user import UserModel
from app.core.security import get_password_hash, verify_password
from app.utils.formatting import format_object_ids

# Get database connection once
db = get_database()

async def get_users(skip: int = 0, limit: int = 100, email: Optional[str] = None, role_id: Optional[str] = None) -> List[dict]:
    """
    Get all users with optional filtering
    """
    query = {}

    if email:
        query["email"] = {"$regex": email, "$options": "i"}

    if role_id:
        query["role_id"] = role_id

    users = await db.users.find(query).skip(skip).limit(limit).to_list(length=limit)
    # Format ObjectIds to strings
    return format_object_ids(users)


async def get_user_by_id(user_id: ObjectId) -> Optional[dict]:
    """
    Get user by ID
    """
    user = await db.users.find_one({"_id": user_id})
    # Format ObjectIds to strings
    return format_object_ids(user) if user else None


async def get_user_by_email(email: str) -> Optional[dict]:
    """
    Get user by email
    """
    user = await db.users.find_one({"email": email})
    return user


async def create_user(user_data: dict) -> dict:
    """
    Create new user
    """
    # Hash the password
    user_data["password"] = get_password_hash(user_data["password"])

    # Create user model
    user_model = UserModel(**user_data)

    # Insert into database
    result = await db.users.insert_one(user_model.model_dump(by_alias=True))

    # Get the created user
    created_user = await get_user_by_id(result.inserted_id)
    return created_user


async def update_user(user_id: str, user_data: dict) -> Optional[dict]:
    """
    Update existing user
    """
    # Handle password update
    if "password" in user_data and user_data["password"]:
        user_data["password"] = get_password_hash(user_data["password"])

    # Update timestamp - Fixed version
    user_data["updated_at"] = datetime.utcnow()

    # Update user
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": user_data}
    )

    # Get updated user
    updated_user = await get_user_by_id(ObjectId(user_id))
    # Format before returning to avoid ObjectId validation errors
    return format_object_ids(updated_user) if updated_user else None


async def delete_user(user_id: str) -> bool:
    """
    Delete user
    """
    result = await db.users.delete_one({"_id": ObjectId(user_id)})
    return result.deleted_count > 0


async def authenticate_user(email: str, password: str) -> Optional[dict]:
    """
    Authenticate user with email and password
    """
    user = await get_user_by_email(email)

    if not user:
        return None

    if not verify_password(password, user["password"]):
        return None

    return user
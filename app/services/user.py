from typing import List, Optional, Dict, Any
from bson import ObjectId
from datetime import datetime
from app.core.db import get_database
from app.models.user import UserDB, UserOut
from app.core.security import get_password_hash

# Database collection
users_collection = get_database()["users"]


async def get_user_by_email(email: str) -> Optional[UserDB]:
    """
    Get a user by email
    """
    user_data = await users_collection.find_one({"email": email})
    if user_data:
        # Convert ObjectId to string for Pydantic model
        user_data["_id"] = str(user_data["_id"])
        if "role_id" in user_data and user_data["role_id"]:
            user_data["role_id"] = str(user_data["role_id"])
        return UserDB(**user_data)
    return None


async def get_user_by_id(id: str) -> Optional[UserDB]:
    """
    Get a user by ID
    """
    # Convert string ID to ObjectId for MongoDB
    obj_id = ObjectId(id) if isinstance(id, str) else id

    user_data = await users_collection.find_one({"_id": obj_id})
    if user_data:
        # Convert ObjectId to string for Pydantic model
        user_data["_id"] = str(user_data["_id"])
        if "role_id" in user_data and user_data["role_id"]:
            user_data["role_id"] = str(user_data["role_id"])
        return UserDB(**user_data)
    return None


async def create_user(user_data: Dict[str, Any]) -> UserDB:
    """
    Create a new user
    """
    # Hash the password
    user_data["password"] = get_password_hash(user_data["password"])

    # Convert role_id to ObjectId if present
    if "role_id" in user_data and user_data["role_id"]:
        user_data["role_id"] = ObjectId(user_data["role_id"])

    user_data["created_at"] = datetime.utcnow()
    user_data["updated_at"] = datetime.utcnow()

    result = await users_collection.insert_one(user_data)

    # Get the created user
    created_user = await get_user_by_id(str(result.inserted_id))
    return created_user


async def update_user(id: str, update_data: Dict[str, Any]) -> Optional[UserDB]:
    """
    Update a user
    """
    # Convert string ID to ObjectId for MongoDB
    obj_id = ObjectId(id)

    # Don't allow updating the email directly
    if "email" in update_data:
        del update_data["email"]

    # Hash the password if it's being updated
    if "password" in update_data:
        update_data["password"] = get_password_hash(update_data["password"])

    # Convert role_id to ObjectId if present and valid
    if "role_id" in update_data and update_data["role_id"]:
        if ObjectId.is_valid(update_data["role_id"]):
            update_data["role_id"] = ObjectId(update_data["role_id"])
        else:
            # Remove invalid role_id
            del update_data["role_id"]

    update_data["updated_at"] = datetime.utcnow()

    await users_collection.update_one(
        {"_id": obj_id}, {"$set": update_data}
    )

    return await get_user_by_id(id)


async def delete_user(id: str) -> bool:
    """
    Delete a user
    """
    # Convert string ID to ObjectId for MongoDB
    obj_id = ObjectId(id)

    result = await users_collection.delete_one({"_id": obj_id})
    return result.deleted_count > 0


async def list_users(skip: int = 0, limit: int = 100) -> List[UserOut]:
    """
    List all users with pagination
    """
    users = []
    cursor = users_collection.find().skip(skip).limit(limit)

    async for user_data in cursor:
        # Convert ObjectId to string for Pydantic model
        user_data["_id"] = str(user_data["_id"])
        if "role_id" in user_data and user_data["role_id"]:
            user_data["role_id"] = str(user_data["role_id"])

        # Add default values for any missing required fields
        if "is_active" not in user_data:
            user_data["is_active"] = True  # Default to active users

            # Update the database
            await users_collection.update_one(
                {"_id": ObjectId(user_data["_id"])},
                {"$set": {"is_active": True}}
            )

        users.append(UserOut(**user_data))

    return users
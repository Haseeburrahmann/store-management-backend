# app/services/user.py
from datetime import datetime
from typing import List, Optional, Dict, Any
from bson import ObjectId
from fastapi import HTTPException, status

from app.core.db import get_database, get_users_collection
from app.models.user import UserModel
from app.core.security import get_password_hash, verify_password
from app.utils.formatting import format_object_ids, ensure_object_id
from app.utils.id_handler import IdHandler

# Get database and collections
db = get_database()
users_collection = get_users_collection()


async def get_users(
        skip: int = 0,
        limit: int = 100,
        email: Optional[str] = None,
        role_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get all users with optional filtering
    """
    try:
        query = {}

        if email:
            query["email"] = {"$regex": email, "$options": "i"}

        if role_id:
            # Since role_id is stored as a string in the database,
            # use string comparison directly
            query["role_id"] = role_id

            # Log the query for debugging
            print(f"Querying users with role_id: {role_id}")
            print(f"Final query: {query}")

        users = await users_collection.find(query).skip(skip).limit(limit).to_list(length=limit)
        formatted_users = format_object_ids(users)

        # Log results for debugging
        print(f"Found {len(formatted_users)} users matching query")

        return formatted_users
    except Exception as e:
        print(f"Error getting users: {str(e)}")
        return []


async def get_user_by_id(user_id: Any) -> Optional[Dict[str, Any]]:
    """
    Get user by ID using the centralized ID handler
    """
    try:
        print(f"Looking up user with ID: {user_id}, type: {type(user_id)}")

        # Use centralized method for consistent lookup
        user, _ = await IdHandler.find_document_by_id(
            users_collection,
            user_id,
            not_found_msg=f"User with ID {user_id} not found"
        )

        if not user:
            print(f"User not found with ID: {user_id}")
            return None

        print(f"Found user with email: {user.get('email', 'unknown')}")
        return IdHandler.format_object_ids(user)
    except Exception as e:
        print(f"Error getting user by ID: {str(e)}")
        return None


async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Get user by email
    """
    try:
        user = await users_collection.find_one({"email": email})
        return format_object_ids(user) if user else None
    except Exception as e:
        print(f"Error getting user by email: {str(e)}")
        return None


async def create_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new user
    """
    try:
        # Hash the password
        if "password" in user_data:
            user_data["password"] = get_password_hash(user_data["password"])

        # Create user model
        user_model = UserModel(**user_data)

        # Insert into database
        result = await users_collection.insert_one(user_model.model_dump(by_alias=True))

        # Get the created user
        created_user = await get_user_by_id(result.inserted_id)

        if not created_user:
            # Fallback return if user can't be retrieved
            return {
                "_id": str(result.inserted_id),
                **{k: v for k, v in user_data.items() if k != "password"},
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }

        return created_user
    except Exception as e:
        print(f"Error creating user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating user: {str(e)}"
        )


async def update_user(user_id: str, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Enhanced update_user with improved error handling and debugging
    """
    try:
        print(f"Updating user with ID: {user_id}")
        print(f"Update data: {user_data}")

        # Handle password update
        if "password" in user_data and user_data["password"]:
            user_data["password"] = get_password_hash(user_data["password"])
            print("Password hashed for update")

        # Update timestamp
        user_data["updated_at"] = datetime.utcnow()

        # Convert user_id to ObjectId if valid
        user_obj_id = ensure_object_id(user_id)

        if user_obj_id:
            print(f"Using ObjectId for update: {user_obj_id}")
            # Verify user exists before update
            user = await users_collection.find_one({"_id": user_obj_id})
            if not user:
                print(f"User not found with ObjectId: {user_obj_id}")

                # Try string comparison as fallback
                all_users = await users_collection.find().to_list(length=100)
                for u in all_users:
                    if str(u.get("_id")) == user_id:
                        user = u
                        user_obj_id = u.get("_id")
                        print(f"Found user via string comparison: {u.get('email', 'unknown')}")
                        break

                if not user:
                    print(f"User not found with ID: {user_id}")
                    return None

            # Update user
            update_result = await users_collection.update_one(
                {"_id": user_obj_id},
                {"$set": user_data}
            )

            print(f"Update result: matched={update_result.matched_count}, modified={update_result.modified_count}")

            if update_result.matched_count == 0:
                print(f"No user matched for update")
                return None

            # Get updated user
            updated_user = await get_user_by_id(user_obj_id)
            print(f"Retrieved updated user: {updated_user is not None}")
            return updated_user
        else:
            print(f"Invalid ObjectId format, trying string comparison")
            # Try string comparison for ID
            all_users = await users_collection.find().to_list(length=100)
            for user in all_users:
                if str(user.get("_id")) == user_id:
                    # Update user
                    update_result = await users_collection.update_one(
                        {"_id": user.get("_id")},
                        {"$set": user_data}
                    )

                    print(
                        f"Update result via string comparison: matched={update_result.matched_count}, modified={update_result.modified_count}")

                    # Get updated user
                    updated_user = await get_user_by_id(user.get("_id"))
                    print(f"Retrieved updated user via string comparison: {updated_user is not None}")
                    return updated_user

            print(f"User not found with ID after exhaustive search: {user_id}")
            return None
    except Exception as e:
        print(f"Error updating user: {str(e)}")
        return None


async def delete_user(user_id: str) -> bool:
    """
    Delete user
    """
    try:
        # Convert to ObjectId if valid
        user_obj_id = ensure_object_id(user_id)

        if user_obj_id:
            # Check if user exists
            user = await users_collection.find_one({"_id": user_obj_id})
            if user:
                # Delete user
                result = await users_collection.delete_one({"_id": user_obj_id})
                return result.deleted_count > 0

        # Try string comparison as fallback
        all_users = await users_collection.find().to_list(length=100)
        for user in all_users:
            if str(user.get("_id")) == user_id:
                # Delete user
                result = await users_collection.delete_one({"_id": user.get("_id")})
                return result.deleted_count > 0

        return False
    except Exception as e:
        print(f"Error deleting user: {str(e)}")
        return False


async def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Authenticate user with email and password
    """
    try:
        user = await get_user_by_email(email)

        if not user:
            return None

        if not verify_password(password, user["password"]):
            return None

        return user
    except Exception as e:
        print(f"Error authenticating user: {str(e)}")
        return None


async def get_user_with_role(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get user with role information
    """
    try:
        user = await get_user_by_id(user_id)
        if not user:
            return None

        # If user has a role_id, get role details
        if user.get("role_id"):
            from app.services.role import get_role_by_id
            role = await get_role_by_id(user["role_id"])
            if role:
                user["role_name"] = role.get("name")
                user["permissions"] = role.get("permissions", [])

        return user
    except Exception as e:
        print(f"Error getting user with role: {str(e)}")
        return None
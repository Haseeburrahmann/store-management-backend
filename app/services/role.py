from typing import List, Optional
from bson import ObjectId
from datetime import datetime
from app.core.db import get_database
from app.models.role import RoleDB, RoleOut
from app.core.permissions import DEFAULT_ROLES

# Database collection
roles_collection = get_database()["roles"]


async def create_default_roles() -> None:
    """
    Create default roles if they don't exist
    """
    for role_key, role_data in DEFAULT_ROLES.items():
        existing_role = await roles_collection.find_one({"name": role_data["name"]})
        if not existing_role:
            await roles_collection.insert_one({
                "name": role_data["name"],
                "description": role_data["description"],
                "permissions": role_data["permissions"],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            })


async def get_role_by_id(id: ObjectId) -> Optional[RoleDB]:
    """
    Get a role by ID
    """
    # Convert to ObjectId if it's a string
    obj_id = ObjectId(id) if isinstance(id, str) else id

    role_data = await roles_collection.find_one({"_id": obj_id})
    if role_data:
        # Convert _id from ObjectId to string
        role_data["_id"] = str(role_data["_id"])
        return RoleDB(**role_data)
    return None


async def get_role_by_name(name: str) -> Optional[RoleDB]:
    """
    Get a role by name
    """
    role_data = await roles_collection.find_one({"name": name})
    if role_data:
        # Convert _id from ObjectId to string for Pydantic model
        role_data["_id"] = str(role_data["_id"])
        return RoleDB(**role_data)
    return None

async def create_role(role_data: dict) -> RoleDB:
    """
    Create a new role
    """
    role_data["created_at"] = datetime.utcnow()
    role_data["updated_at"] = datetime.utcnow()

    result = await roles_collection.insert_one(role_data)

    # Get the created role
    created_role = await get_role_by_id(result.inserted_id)
    return created_role


async def update_role(id: ObjectId, update_data: dict) -> Optional[RoleDB]:
    """
    Update a role
    """
    update_data["updated_at"] = datetime.utcnow()

    await roles_collection.update_one(
        {"_id": id}, {"$set": update_data}
    )

    return await get_role_by_id(id)


async def delete_role(id: ObjectId) -> bool:
    """
    Delete a role
    """
    result = await roles_collection.delete_one({"_id": id})
    return result.deleted_count > 0


async def list_roles(skip: int = 0, limit: int = 100) -> List[RoleOut]:
    """
    List all roles with pagination
    """
    roles = []
    cursor = roles_collection.find().skip(skip).limit(limit)

    async for role_data in cursor:
        # Convert ObjectId to string
        role_data["_id"] = str(role_data["_id"])

        # Set default values for missing fields
        if "created_at" not in role_data or role_data["created_at"] is None:
            role_data["created_at"] = datetime.utcnow()
        if "updated_at" not in role_data or role_data["updated_at"] is None:
            role_data["updated_at"] = datetime.utcnow()

        # Update the database with these fields if they were missing
        if "created_at" not in role_data or "updated_at" not in role_data:
            await roles_collection.update_one(
                {"_id": ObjectId(role_data["_id"])},
                {"$set": {
                    "created_at": role_data["created_at"],
                    "updated_at": role_data["updated_at"]
                }}
            )

        roles.append(RoleOut(**role_data))

    return roles
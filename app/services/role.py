# app/services/role.py
from typing import List, Optional
from bson import ObjectId
from app.core.db import get_database
from app.models.role import RoleModel
from datetime import datetime
from app.utils.formatting import format_object_ids

# Get database connection once when the module is loaded
db = get_database()

async def get_roles(skip: int = 0, limit: int = 100, name: Optional[str] = None) -> List[dict]:
    """
    Get all roles with optional filtering
    """
    query = {}

    if name:
        query["name"] = {"$regex": name, "$options": "i"}

    roles = await db.roles.find(query).skip(skip).limit(limit).to_list(length=limit)
    return format_object_ids(roles)


async def get_role_by_id(role_id: str) -> Optional[dict]:
    """
    Get role by ID
    """
    role = await db.roles.find_one({"_id": ObjectId(role_id)})
    return format_object_ids(role) if role else None


async def get_role_by_name(name: str) -> Optional[dict]:
    """
    Get role by name
    """
    role = await db.roles.find_one({"name": name})
    return format_object_ids(role) if role else None


async def create_role(role_data: dict) -> dict:
    """
    Create new role
    """
    try:
        # Create role model
        role_model = RoleModel(**role_data)

        # Insert into database
        result = await db.roles.insert_one(role_model.model_dump(by_alias=True))

        # Get the created role
        created_role = await db.roles.find_one({"_id": result.inserted_id})

        # Format and return
        if created_role:
            return format_object_ids(created_role)
        else:
            # Log error and return a meaningful response
            print(f"Error: Role was inserted but could not be retrieved. ID: {result.inserted_id}")
            return {
                "_id": str(result.inserted_id),
                "name": role_data.get("name", "Unknown"),
                "description": role_data.get("description", ""),
                "permissions": role_data.get("permissions", []),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
    except Exception as e:
        print(f"Error creating role: {str(e)}")
        raise


async def update_role(role_id: str, role_data: dict) -> Optional[dict]:
    """
    Update existing role
    """
    # Update timestamp directly with datetime instead of using model
    role_data["updated_at"] = datetime.utcnow()

    # Update role
    await db.roles.update_one(
        {"_id": ObjectId(role_id)},
        {"$set": role_data}
    )

    # Get updated role
    updated_role = await get_role_by_id(role_id)
    return updated_role


async def delete_role(role_id: str) -> bool:
    """
    Delete role
    """
    try:
        print(f"Attempting to delete role with ID: {role_id}")

        # Look up all roles first to debug
        all_roles = await db.roles.find().to_list(length=100)
        all_ids = [str(role.get('_id')) for role in all_roles]
        print(f"All role IDs in database: {all_ids}")

        # Try to convert the string ID to ObjectId
        try:
            object_id = ObjectId(role_id)
            # First attempt with ObjectId
            role = await db.roles.find_one({"_id": object_id})
        except Exception as e:
            print(f"Error converting to ObjectId: {str(e)}")
            role = None

        # If not found with ObjectId, try with string
        if not role:
            # Try to find by string comparison
            for db_role in all_roles:
                if str(db_role.get('_id')) == role_id:
                    # Found a match by string comparison
                    print(f"Found role by string comparison: {db_role.get('name')}")
                    result = await db.roles.delete_one({"_id": db_role.get('_id')})
                    return result.deleted_count > 0

            print(f"Role not found with ID: {role_id}")
            return False
        else:
            # Role was found with ObjectId
            result = await db.roles.delete_one({"_id": object_id})
            return result.deleted_count > 0

    except Exception as e:
        print(f"Error deleting role: {str(e)}")
        return False


async def create_default_roles() -> None:
    """
    Create default roles if they don't exist
    """
    from app.core.permissions import DEFAULT_ROLES

    for role_key, role_data in DEFAULT_ROLES.items():
        existing_role = await get_role_by_name(role_data["name"])
        if not existing_role:
            await create_role(role_data)
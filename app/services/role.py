# app/services/role.py
from typing import List, Optional, Dict, Any
from bson import ObjectId
from datetime import datetime
from fastapi import HTTPException, status

from app.core.db import get_database, get_roles_collection
from app.models.role import RoleModel
from app.core.permissions import DEFAULT_ROLES
from app.utils.formatting import format_object_ids, ensure_object_id

# Get database and collections
db = get_database()
roles_collection = get_roles_collection()


async def get_roles(
        skip: int = 0,
        limit: int = 100,
        name: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get all roles with optional filtering
    """
    try:
        query = {}

        if name:
            query["name"] = {"$regex": name, "$options": "i"}

        roles = await roles_collection.find(query).skip(skip).limit(limit).to_list(length=limit)
        return format_object_ids(roles)
    except Exception as e:
        print(f"Error getting roles: {str(e)}")
        return []


async def get_role_by_id(role_id: Any) -> Optional[Dict[str, Any]]:
    """
    Get role by ID, with flexible ID format handling
    """
    try:
        # Try with ObjectId
        obj_id = ensure_object_id(role_id)
        if obj_id:
            role = await roles_collection.find_one({"_id": obj_id})
            if role:
                return format_object_ids(role)

        # Try with string ID if ObjectId didn't work
        if isinstance(role_id, str):
            # Try direct string lookup
            role = await roles_collection.find_one({"_id": role_id})
            if role:
                return format_object_ids(role)

            # Try string comparison as last resort
            all_roles = await roles_collection.find().to_list(length=100)
            for r in all_roles:
                if str(r.get("_id")) == role_id:
                    return format_object_ids(r)

        return None
    except Exception as e:
        print(f"Error getting role by ID: {str(e)}")
        return None


async def get_role_by_name(name: str) -> Optional[Dict[str, Any]]:
    """
    Get role by name
    """
    try:
        role = await roles_collection.find_one({"name": name})
        return format_object_ids(role) if role else None
    except Exception as e:
        print(f"Error getting role by name: {str(e)}")
        return None


async def create_role(role_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create new role
    """
    try:
        # Create role model
        role_model = RoleModel(**role_data)

        # Insert into database
        result = await roles_collection.insert_one(role_model.model_dump(by_alias=True))

        # Get the created role
        created_role = await roles_collection.find_one({"_id": result.inserted_id})
        if not created_role:
            print(f"Error: Role was inserted but could not be retrieved. ID: {result.inserted_id}")
            return {
                "_id": str(result.inserted_id),
                "name": role_data.get("name", "Unknown"),
                "description": role_data.get("description", ""),
                "permissions": role_data.get("permissions", []),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }

        return format_object_ids(created_role)
    except Exception as e:
        print(f"Error creating role: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating role: {str(e)}"
        )


async def update_role(role_id: str, role_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Update existing role
    """
    try:
        # Update timestamp
        role_data["updated_at"] = datetime.utcnow()

        # Try with ObjectId
        role_obj_id = ensure_object_id(role_id)
        if role_obj_id:
            # Check if role exists
            role = await roles_collection.find_one({"_id": role_obj_id})
            if role:
                # Update role
                await roles_collection.update_one(
                    {"_id": role_obj_id},
                    {"$set": role_data}
                )

                # Get updated role
                updated_role = await get_role_by_id(role_obj_id)
                return updated_role

        # Try string comparison as fallback
        all_roles = await roles_collection.find().to_list(length=100)
        for role in all_roles:
            if str(role.get("_id")) == role_id:
                # Update role
                await roles_collection.update_one(
                    {"_id": role.get("_id")},
                    {"$set": role_data}
                )

                # Get updated role
                updated_role = await get_role_by_id(role.get("_id"))
                return updated_role

        return None
    except Exception as e:
        print(f"Error updating role: {str(e)}")
        return None


async def delete_role(role_id: str) -> bool:
    """
    Delete role
    """
    try:
        # Try with ObjectId
        role_obj_id = ensure_object_id(role_id)
        if role_obj_id:
            # Check if role exists
            role = await roles_collection.find_one({"_id": role_obj_id})
            if role:
                # Check if it's a default role
                role_name = role.get("name")
                for default_role in DEFAULT_ROLES.values():
                    if default_role["name"] == role_name:
                        # Don't delete default roles
                        print(f"Cannot delete default role: {role_name}")
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Cannot delete default role: {role_name}"
                        )

                # Delete role
                result = await roles_collection.delete_one({"_id": role_obj_id})
                return result.deleted_count > 0

        # Try string comparison as fallback
        all_roles = await roles_collection.find().to_list(length=100)
        for role in all_roles:
            if str(role.get("_id")) == role_id:
                # Check if it's a default role
                role_name = role.get("name")
                for default_role in DEFAULT_ROLES.values():
                    if default_role["name"] == role_name:
                        # Don't delete default roles
                        print(f"Cannot delete default role: {role_name}")
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Cannot delete default role: {role_name}"
                        )

                # Delete role
                result = await roles_collection.delete_one({"_id": role.get("_id")})
                return result.deleted_count > 0

        return False
    except Exception as e:
        print(f"Error deleting role: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        return False


async def create_default_roles() -> None:
    """
    Create default roles if they don't exist
    """
    try:
        for role_key, role_data in DEFAULT_ROLES.items():
            # Check if role already exists
            existing_role = await get_role_by_name(role_data["name"])
            if not existing_role:
                print(f"Creating default role: {role_data['name']}")
                await create_role(role_data)
            else:
                # Update permissions if needed to ensure they match the defaults
                current_permissions = set(existing_role.get("permissions", []))
                default_permissions = set(role_data["permissions"])

                if current_permissions != default_permissions:
                    print(f"Updating permissions for role: {role_data['name']}")
                    await update_role(
                        str(existing_role["_id"]),
                        {"permissions": role_data["permissions"]}
                    )
    except Exception as e:
        print(f"Error creating default roles: {str(e)}")


async def get_role_with_permissions(role_id: str) -> Optional[Dict[str, Any]]:
    """
    Get role with formatted permissions
    """
    try:
        role = await get_role_by_id(role_id)
        if not role:
            return None

        # Format permissions for easier checking
        permissions = role.get("permissions", [])

        # Group permissions by area
        permission_groups = {}
        for permission in permissions:
            if ":" in permission:
                area, action = permission.split(":")
                if area not in permission_groups:
                    permission_groups[area] = []
                permission_groups[area].append(action)

        role["permission_groups"] = permission_groups
        return role
    except Exception as e:
        print(f"Error getting role with permissions: {str(e)}")
        return None


async def check_user_has_permission(user_id: str, required_permission: str) -> bool:
    """
    Check if a user has the required permission
    """
    try:
        # Get user
        from app.services.user import get_user_by_id
        user = await get_user_by_id(user_id)
        if not user or not user.get("role_id"):
            return False

        # Get role
        role = await get_role_by_id(user["role_id"])
        if not role:
            return False

        # Check permission
        from app.core.security import check_permissions
        return check_permissions(role.get("permissions", []), required_permission)
    except Exception as e:
        print(f"Error checking user permission: {str(e)}")
        return False
# app/utils/fix_permissions.py
from app.core.db import get_database
from app.core.permissions import PermissionArea, PermissionAction, get_permission_string
import asyncio


async def fix_permission_formats():
    """
    Update permission formats in the database from 'PermissionArea.AREA:PermissionAction.ACTION'
    to 'area:action'
    """
    db = await get_database()
    roles_collection = db.roles

    # Get all roles
    roles = await roles_collection.find().to_list(length=100)

    update_count = 0
    for role in roles:
        fixed_permissions = []
        need_update = False

        for permission in role["permissions"]:
            # Check if permission is in old format
            if "PermissionArea." in permission and "PermissionAction." in permission:
                need_update = True
                # Extract the parts
                parts = permission.split(":")
                area_part = parts[0].replace("PermissionArea.", "")
                action_part = parts[1].replace("PermissionAction.", "")

                # Find matching enums
                try:
                    area = PermissionArea[area_part]
                    action = PermissionAction[action_part]
                    fixed_permission = get_permission_string(area, action)
                    fixed_permissions.append(fixed_permission)
                except (KeyError, IndexError):
                    # If we can't match, keep the original
                    print(f"Warning: Could not fix permission {permission}")
                    fixed_permissions.append(permission)
            else:
                # Already in correct format
                fixed_permissions.append(permission)

        # Only update if needed
        if need_update:
            update_count += 1
            await roles_collection.update_one(
                {"_id": role["_id"]},
                {"$set": {"permissions": fixed_permissions}}
            )

    return f"Updated {update_count} roles with fixed permissions"


# Command to run the script
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(fix_permission_formats())
    print(result)



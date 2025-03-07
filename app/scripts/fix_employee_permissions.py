import asyncio
from app.services.role import get_role_by_name, update_role


async def fix_employee_permissions():
    # Get the Employee role
    employee_role = await get_role_by_name("Employee")
    if not employee_role:
        print("ERROR: Employee role not found!")
        return

    # Get current permissions
    current_permissions = employee_role.get("permissions", [])
    print(f"Current permissions: {current_permissions}")

    # Define the minimum required permissions
    required_permissions = [
        "users:read",  # Access own profile
        "employees:read",  # Access own employee info
        "hours:read",  # View hours
        "hours:write",  # Clock in/out
        "stores:read"  # View store info for clock in
    ]

    # Add missing permissions
    updated = False
    for perm in required_permissions:
        if perm not in current_permissions:
            current_permissions.append(perm)
            updated = True
            print(f"Added permission: {perm}")

    # Update the role if changes were made
    if updated:
        result = await update_role(
            str(employee_role["_id"]),
            {"permissions": current_permissions}
        )
        if result:
            print("Successfully updated Employee role permissions")
        else:
            print("Failed to update Employee role permissions")
    else:
        print("No permission updates needed")


# Run the fix
if __name__ == "__main__":
    asyncio.run(fix_employee_permissions())
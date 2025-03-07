import asyncio
from app.services.role import get_role_by_name


async def check_employee_permissions():
    employee_role = await get_role_by_name("Employee")
    print("\nEmployee Role Permissions Check:")
    print("---------------------------------")
    if not employee_role:
        print("ERROR: Employee role not found!")
        return

    print(f"Role ID: {employee_role.get('_id')}")
    print(f"Role Name: {employee_role.get('name')}")
    permissions = employee_role.get('permissions', [])
    print(f"Total permissions: {len(permissions)}")
    print("\nPermissions list:")
    for perm in permissions:
        print(f"  - {perm}")

    # Check for critical permissions
    critical_perms = ["users:read", "hours:read", "hours:write"]
    print("\nCritical permission check:")
    for perm in critical_perms:
        if perm in permissions:
            print(f"  ✓ {perm}")
        else:
            print(f"  ✗ {perm} (MISSING)")


# Run the check
if __name__ == "__main__":
    asyncio.run(check_employee_permissions())
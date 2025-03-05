from typing import Optional
from app.schemas.user import UserInDB
from app.services.role import get_role_by_id


async def get_user_role(current_user: UserInDB) -> Optional[str]:
    """
    Helper function to get the role name for a user
    """
    if hasattr(current_user, 'role_name'):
        return current_user.role_name

    user_role = None
    if hasattr(current_user, 'role_id') and current_user.role_id:
        role = await get_role_by_id(current_user.role_id)
        if role:
            # Check if role is a dictionary or a Pydantic model
            if hasattr(role, 'get'):  # It's a dictionary
                user_role = role.get("name")
            elif hasattr(role, 'name'):  # It's a Pydantic model
                user_role = role.name
            else:
                # Try to access it as a dictionary item
                try:
                    user_role = role["name"]
                except (TypeError, KeyError):
                    user_role = None

    return user_role
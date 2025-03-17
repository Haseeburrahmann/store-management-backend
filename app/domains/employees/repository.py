"""
Employee repository for database operations.
"""
from typing import Dict, List, Optional, Any

from app.db.base_repository import BaseRepository
from app.db.mongodb import get_employees_collection
from app.utils.id_handler import IdHandler


class EmployeeRepository(BaseRepository):
    """
    Repository for employee data access.
    Extends BaseRepository with employee-specific operations.
    """

    def __init__(self):
        """Initialize with employees collection."""
        super().__init__(get_employees_collection())

    async def find_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Find an employee by user ID.

        Args:
            user_id: User ID

        Returns:
            Employee document or None if not found
        """
        # Try different formats for the user_id to enhance compatibility
        user_obj_id = IdHandler.ensure_object_id(user_id)

        # Try with ObjectId
        if user_obj_id:
            employee = await self.collection.find_one({"user_id": user_obj_id})
            if employee:
                return IdHandler.format_object_ids(employee)

        # Try with string ID
        employee = await self.collection.find_one({"user_id": user_id})
        if employee:
            return IdHandler.format_object_ids(employee)

        # Try string comparison as last resort
        all_employees = await self.collection.find().to_list(length=100)
        for emp in all_employees:
            if str(emp.get('user_id')) == user_id:
                return IdHandler.format_object_ids(emp)

        return None

    async def find_by_store(self, store_id: str) -> List[Dict[str, Any]]:
        """
        Find employees by store ID.

        Args:
            store_id: Store ID

        Returns:
            List of employee documents
        """
        # Try different formats for store_id
        store_obj_id = IdHandler.ensure_object_id(store_id)

        query = {}
        if store_obj_id:
            query = {"store_id": store_obj_id}
        else:
            query = {"store_id": store_id}

        employees = await self.collection.find(query).to_list(length=100)
        return IdHandler.format_object_ids(employees)

    async def find_by_position(self, position: str) -> List[Dict[str, Any]]:
        """
        Find employees by position.

        Args:
            position: Position name or pattern

        Returns:
            List of employee documents
        """
        query = {"position": {"$regex": position, "$options": "i"}}
        employees = await self.collection.find(query).to_list(length=100)
        return IdHandler.format_object_ids(employees)

    async def find_by_status(self, status: str) -> List[Dict[str, Any]]:
        """
        Find employees by employment status.

        Args:
            status: Employment status

        Returns:
            List of employee documents
        """
        query = {"employment_status": status}
        employees = await self.collection.find(query).to_list(length=100)
        return IdHandler.format_object_ids(employees)
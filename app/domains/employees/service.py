"""
Employee service for business logic.
"""
from typing import Dict, List, Optional, Any
from fastapi import HTTPException, status
from datetime import datetime

from app.domains.employees.repository import EmployeeRepository
from app.domains.users.service import user_service
from app.domains.stores.service import store_service
from app.domains.roles.service import role_service
from app.utils.id_handler import IdHandler
from app.utils.datetime_handler import DateTimeHandler


class EmployeeService:
    """
    Service for employee-related business logic.
    """

    def __init__(self, employee_repo: Optional[EmployeeRepository] = None):
        """
        Initialize with employee repository.

        Args:
            employee_repo: Optional employee repository instance
        """
        self.employee_repo = employee_repo or EmployeeRepository()

    async def get_employees(
            self,
            skip: int = 0,
            limit: int = 100,
            position: Optional[str] = None,
            store_id: Optional[str] = None,
            status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get employees with optional filtering.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            position: Filter by position pattern
            store_id: Filter by store ID
            status: Filter by employment status

        Returns:
            List of employee documents
        """
        # Build query
        query = {}

        if position:
            query["position"] = {"$regex": position, "$options": "i"}

        if store_id:
            store_obj_id = IdHandler.ensure_object_id(store_id)
            if store_obj_id:
                query["store_id"] = store_obj_id
            else:
                query["store_id"] = store_id

        if status:
            query["employment_status"] = status

        # Get employees
        employees = await self.employee_repo.find_many(query, skip, limit)

        # Enrich with user and store info
        result = []
        for employee in employees:
            employee_with_info = await self._enrich_employee_data(employee)
            result.append(employee_with_info)

        return result

    async def get_employee(self, employee_id: str) -> Optional[Dict[str, Any]]:
        """
        Get employee by ID.

        Args:
            employee_id: Employee ID

        Returns:
            Employee document or None if not found
        """
        employee = await self.employee_repo.find_by_id(employee_id)

        if not employee:
            return None

        # Enrich with user and store info
        return await self._enrich_employee_data(employee)

    async def get_employee_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get employee by user ID.

        Args:
            user_id: User ID

        Returns:
            Employee document or None if not found
        """
        employee = await self.employee_repo.find_by_user_id(user_id)

        if not employee:
            return None

        # Enrich with user and store info
        return await self._enrich_employee_data(employee)

    async def get_employees_by_store(self, store_id: str) -> List[Dict[str, Any]]:
        """
        Get employees by store ID.

        Args:
            store_id: Store ID

        Returns:
            List of employee documents
        """
        employees = await self.employee_repo.find_by_store(store_id)

        # Enrich with user and store info
        result = []
        for employee in employees:
            employee_with_info = await self._enrich_employee_data(employee)
            result.append(employee_with_info)

        return result

    async def create_employee(self, employee_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new employee.

        Args:
            employee_data: Employee data

        Returns:
            Created employee document

        Raises:
            HTTPException: If validation fails
        """
        # Validate user_id if provided
        if employee_data.get("user_id"):
            user = await user_service.get_user_by_id(employee_data["user_id"])
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"User with ID {employee_data['user_id']} not found"
                )

            # Check if user already has an employee profile
            existing_employee = await self.employee_repo.find_by_user_id(employee_data["user_id"])
            if existing_employee:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"User already has an employee profile"
                )

        # Validate store_id if provided
        if employee_data.get("store_id"):
            store = await store_service.get_store(employee_data["store_id"])
            if not store:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Store with ID {employee_data['store_id']} not found"
                )

        # Set default hire date if not provided
        if "hire_date" not in employee_data or not employee_data["hire_date"]:
            employee_data["hire_date"] = DateTimeHandler.get_current_datetime()

        # Create employee
        created_employee = await self.employee_repo.create(employee_data)

        # Enrich with user and store info
        return await self._enrich_employee_data(created_employee)

    async def update_employee(self, employee_id: str, employee_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update an existing employee.

        Args:
            employee_id: Employee ID
            employee_data: Updated employee data

        Returns:
            Updated employee document or None if not found

        Raises:
            HTTPException: If validation fails
        """
        # Check if employee exists
        existing_employee = await self.employee_repo.find_by_id(employee_id)
        if not existing_employee:
            return None

        # Validate user_id if it's being changed
        if "user_id" in employee_data and employee_data["user_id"] != existing_employee.get("user_id"):
            # Check if user exists
            user = await user_service.get_user_by_id(employee_data["user_id"])
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"User with ID {employee_data['user_id']} not found"
                )

            # Check if user already has an employee profile
            existing_user_employee = await self.employee_repo.find_by_user_id(employee_data["user_id"])
            if existing_user_employee and str(existing_user_employee["_id"]) != employee_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"User already has an employee profile"
                )

        # Validate store_id if it's being changed
        if "store_id" in employee_data and employee_data["store_id"] != existing_employee.get("store_id"):
            store = await store_service.get_store(employee_data["store_id"])
            if not store:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Store with ID {employee_data['store_id']} not found"
                )

        # Update employee
        updated_employee = await self.employee_repo.update(employee_id, employee_data)

        if not updated_employee:
            return None

        # Enrich with user and store info
        return await self._enrich_employee_data(updated_employee)

    async def delete_employee(self, employee_id: str) -> bool:
        """
        Delete an employee.

        Args:
            employee_id: Employee ID

        Returns:
            True if employee was deleted

        Raises:
            HTTPException: If deletion fails
        """
        # Check if employee exists
        existing_employee = await self.employee_repo.find_by_id(employee_id)
        if not existing_employee:
            return False

        # TODO: Check for associated resources (timesheets, schedules, etc.)
        # For now, we'll just delete the employee

        # Delete employee
        return await self.employee_repo.delete(employee_id)

    async def assign_to_store(self, employee_id: str, store_id: str) -> Optional[Dict[str, Any]]:
        """
        Assign an employee to a store.

        Args:
            employee_id: Employee ID
            store_id: Store ID

        Returns:
            Updated employee document or None if not found

        Raises:
            HTTPException: If validation fails
        """
        # Check if employee exists
        existing_employee = await self.employee_repo.find_by_id(employee_id)
        if not existing_employee:
            return None

        # Check if store exists
        store = await store_service.get_store(store_id)
        if not store:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Store with ID {store_id} not found"
            )

        # Update employee
        return await self.update_employee(employee_id, {"store_id": store_id})

    async def create_employee_with_user(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new employee with a user account.

        Args:
            data: Combined user and employee data

        Returns:
            Created employee document

        Raises:
            HTTPException: If validation fails
        """
        try:
            # Extract user data
            user_data = {
                "email": data.get("email"),
                "full_name": data.get("full_name"),
                "password": data.get("password"),
                "phone_number": data.get("phone_number"),
                "role_id": data.get("role_id"),
                "is_active": True
            }

            # Check if email already exists
            existing_user = await user_service.get_user_by_email(user_data["email"])
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"User with email {user_data['email']} already exists"
                )

            # Validate role if provided
            if user_data.get("role_id"):
                role = await role_service.get_role_by_id(user_data["role_id"])
                if not role:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Role with ID {user_data['role_id']} not found"
                    )
            else:
                # Set default role (Employee)
                employee_role = await role_service.get_role_by_name("Employee")
                if employee_role:
                    user_data["role_id"] = str(employee_role["_id"])

            # Create user
            created_user = await user_service.create_user(user_data)

            # Extract employee data
            employee_data = {
                "position": data.get("position"),
                "hourly_rate": data.get("hourly_rate"),
                "employment_status": data.get("employment_status", "active"),
                "emergency_contact_name": data.get("emergency_contact_name"),
                "emergency_contact_phone": data.get("emergency_contact_phone"),
                "address": data.get("address"),
                "city": data.get("city"),
                "state": data.get("state"),
                "zip_code": data.get("zip_code"),
                "store_id": data.get("store_id"),
                "user_id": str(created_user["_id"]),
                "hire_date": data.get("hire_date") or DateTimeHandler.get_current_datetime()
            }

            # Create employee
            try:
                created_employee = await self.create_employee(employee_data)
                return created_employee
            except Exception as e:
                # If employee creation fails, delete the user to avoid orphaned users
                await user_service.delete_user(str(created_user["_id"]))
                raise e

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating employee with user: {str(e)}"
            )

    async def _enrich_employee_data(self, employee: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich employee data with user and store information.

        Args:
            employee: Employee document

        Returns:
            Enriched employee document
        """
        if not employee:
            return {}

        employee_with_info = dict(employee)

        # Add user info if available
        if employee.get("user_id"):
            user = await user_service.get_user_by_id(employee["user_id"])
            if user:
                employee_with_info["full_name"] = user.get("full_name")
                employee_with_info["email"] = user.get("email")
                employee_with_info["phone_number"] = user.get("phone_number")

        # Add store info if available
        if employee.get("store_id"):
            store = await store_service.get_store(employee["store_id"])
            if store:
                employee_with_info["store_name"] = store.get("name")

        return employee_with_info


# Create global instance
employee_service = EmployeeService()
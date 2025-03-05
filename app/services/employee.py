# app/services/employee.py
from typing import List, Optional
from bson import ObjectId
from datetime import datetime
from app.core.db import get_database
from app.models.employee import EmployeeModel
from app.services.user import get_user_by_id
from app.services.store import StoreService
from app.utils.formatting import format_object_ids

# Get database connection once
db = get_database()


class EmployeeService:
    @staticmethod
    async def get_employees(
            skip: int = 0,
            limit: int = 100,
            position: Optional[str] = None,
            store_id: Optional[str] = None,
            status: Optional[str] = None
    ) -> List[dict]:
        """
        Get all employees with optional filtering
        """
        try:
            query = {}

            if position:
                query["position"] = {"$regex": position, "$options": "i"}

            if store_id:
                query["store_id"] = store_id

            if status:
                query["employment_status"] = status

            employees = await db.employees.find(query).skip(skip).limit(limit).to_list(length=limit)

            # Add user and store info
            result = []
            for employee in employees:
                employee_with_info = dict(employee)

                # Add user info
                if employee.get("user_id"):
                    user = await get_user_by_id(ObjectId(employee["user_id"]))
                    if user:
                        employee_with_info["full_name"] = user.get("full_name")
                        employee_with_info["email"] = user.get("email")
                        employee_with_info["phone_number"] = user.get("phone_number")

                # Add store info
                if employee.get("store_id"):
                    store = await StoreService.get_store(employee["store_id"])
                    if store:
                        employee_with_info["store_name"] = store.get("name")

                result.append(employee_with_info)

            return format_object_ids(result)
        except Exception as e:
            print(f"Error getting employees: {str(e)}")
            return []

    @staticmethod
    async def get_employees_by_store(store_id: str) -> List[dict]:
        """
        Get employees in a specific store
        """
        return await EmployeeService.get_employees(store_id=store_id)

    @staticmethod
    async def get_employee(employee_id: str) -> Optional[dict]:
        """
        Get employee by ID with user and store info
        """
        try:
            print(f"Attempting to find employee with ID: {employee_id}")

            # List all employees for debugging
            all_employees = await db.employees.find().to_list(length=100)
            all_ids = [str(emp.get('_id')) for emp in all_employees]
            print(f"All employee IDs in database: {all_ids}")

            # Try with ObjectId
            try:
                object_id = ObjectId(employee_id)
                employee = await db.employees.find_one({"_id": object_id})
                if employee:
                    print(f"Found employee with ObjectId lookup")
                else:
                    print(f"Employee not found with ObjectId lookup: {employee_id}")
            except Exception as e:
                print(f"Error looking up employee with ObjectId: {str(e)}")
                employee = None

            # If not found with ObjectId, try string comparison
            if not employee:
                print("Trying string comparison for employee...")
                for emp in all_employees:
                    if str(emp.get('_id')) == employee_id:
                        employee = emp
                        print(f"Found employee by string comparison")
                        break

            if not employee:
                print(f"Employee not found with ID: {employee_id}")
                return None

            employee_with_info = dict(employee)

            # Add user info
            if employee.get("user_id"):
                user = await get_user_by_id(ObjectId(employee["user_id"]))
                if user:
                    employee_with_info["full_name"] = user.get("full_name")
                    employee_with_info["email"] = user.get("email")
                    employee_with_info["phone_number"] = user.get("phone_number")

            # Add store info
            if employee.get("store_id"):
                store = await StoreService.get_store(employee["store_id"])
                if store:
                    employee_with_info["store_name"] = store.get("name")

            return format_object_ids(employee_with_info)
        except Exception as e:
            print(f"Error getting employee: {str(e)}")
            return None

    @staticmethod
    async def get_employee_by_user_id(user_id: str) -> Optional[dict]:
        """
        Get employee by user ID
        """
        try:
            print(f"Looking up employee by user ID: {user_id}")

            # Find all employees for debugging
            all_employees = await db.employees.find().to_list(length=100)

            # Try direct lookup first
            employee = await db.employees.find_one({"user_id": user_id})

            # If not found, try string comparison
            if not employee:
                print("Trying string comparison for user_id...")
                for emp in all_employees:
                    if str(emp.get('user_id')) == user_id:
                        employee = emp
                        print(f"Found employee by string comparison of user_id")
                        break

            if not employee:
                print(f"No employee found for user ID: {user_id}")
                return None

            print(f"Found employee for user ID: {user_id}")
            return await EmployeeService.get_employee(str(employee["_id"]))
        except Exception as e:
            print(f"Error getting employee by user ID: {str(e)}")
            return None

    @staticmethod
    async def create_employee(employee_data: dict) -> dict:
        """
        Create new employee
        """
        try:
            print(f"Creating employee with data: {employee_data}")

            # Create employee model
            employee_model = EmployeeModel(**employee_data)

            # Insert into database
            result = await db.employees.insert_one(employee_model.model_dump(by_alias=True))
            print(f"Employee created with ID: {result.inserted_id}")

            # Get the created employee
            created_employee = await EmployeeService.get_employee(str(result.inserted_id))
            if not created_employee:
                print(f"Error: Employee was inserted but could not be retrieved. ID: {result.inserted_id}")
                return {
                    "_id": str(result.inserted_id),
                    **employee_data,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }

            return created_employee
        except Exception as e:
            print(f"Error creating employee: {str(e)}")
            raise

    @staticmethod
    async def update_employee(employee_id: str, employee_data: dict) -> Optional[dict]:
        """
        Update existing employee
        """
        try:
            print(f"Updating employee with ID: {employee_id}")

            # List all employees for debugging
            all_employees = await db.employees.find().to_list(length=100)
            all_ids = [str(emp.get('_id')) for emp in all_employees]
            print(f"All employee IDs in database: {all_ids}")

            # Update timestamp directly
            employee_data["updated_at"] = datetime.utcnow()

            # Try with ObjectId
            employee = None
            try:
                object_id = ObjectId(employee_id)
                # Check if employee exists first
                employee = await db.employees.find_one({"_id": object_id})
                if employee:
                    print(f"Found employee with ObjectId")
                else:
                    print(f"Employee not found with ObjectId: {employee_id}")
            except Exception as e:
                print(f"Error looking up employee with ObjectId: {str(e)}")

            # If not found with ObjectId, try string comparison
            if not employee:
                print("Trying string comparison...")
                for emp in all_employees:
                    if str(emp.get('_id')) == employee_id:
                        employee = emp
                        object_id = emp.get('_id')
                        print(f"Found employee by string comparison")
                        break

            if not employee:
                print(f"Employee not found with ID: {employee_id}")
                return None

            # Update the employee
            await db.employees.update_one(
                {"_id": object_id},
                {"$set": employee_data}
            )

            # Get the updated employee
            updated_employee = await EmployeeService.get_employee(employee_id)
            return updated_employee
        except Exception as e:
            print(f"Error updating employee: {str(e)}")
            return None

    @staticmethod
    async def delete_employee(employee_id: str) -> bool:
        """
        Delete employee
        """
        try:
            print(f"Attempting to delete employee with ID: {employee_id}")

            # List all employees for debugging
            all_employees = await db.employees.find().to_list(length=100)
            all_ids = [str(emp.get('_id')) for emp in all_employees]
            print(f"All employee IDs in database: {all_ids}")

            # Try with ObjectId
            employee = None
            try:
                object_id = ObjectId(employee_id)
                # Check if employee exists first
                employee = await db.employees.find_one({"_id": object_id})
                if employee:
                    print(f"Found employee with ObjectId")
                else:
                    print(f"Employee not found with ObjectId: {employee_id}")
            except Exception as e:
                print(f"Error looking up employee with ObjectId: {str(e)}")

            # If not found with ObjectId, try string comparison
            if not employee:
                print("Trying string comparison...")
                for emp in all_employees:
                    if str(emp.get('_id')) == employee_id:
                        employee = emp
                        object_id = emp.get('_id')
                        print(f"Found employee by string comparison")
                        break

            if not employee:
                print(f"Employee not found with ID: {employee_id}")
                return False

            # Delete the employee
            result = await db.employees.delete_one({"_id": object_id})
            return result.deleted_count > 0
        except Exception as e:
            print(f"Error deleting employee: {str(e)}")
            return False

    @staticmethod
    async def assign_to_store(employee_id: str, store_id: str) -> Optional[dict]:
        """
        Assign employee to store
        """
        try:
            print(f"Attempting to assign employee {employee_id} to store {store_id}")

            # List all employees for debugging
            all_employees = await db.employees.find().to_list(length=100)
            employee_ids = [str(emp.get('_id')) for emp in all_employees]
            print(f"All employee IDs in database: {employee_ids}")

            # List all stores for debugging
            all_stores = await db.stores.find().to_list(length=100)
            store_ids = [str(store.get('_id')) for store in all_stores]
            print(f"All store IDs in database: {store_ids}")

            # Find employee by ID
            employee = None
            for emp in all_employees:
                if str(emp.get('_id')) == employee_id:
                    employee = emp
                    print(f"Found employee by string comparison")
                    break

            if not employee:
                print(f"Employee with ID {employee_id} not found")
                return None

            # Find store by ID
            store = None
            for s in all_stores:
                if str(s.get('_id')) == store_id:
                    store = s
                    print(f"Found store by string comparison: {store.get('name')}")
                    break

            if not store:
                print(f"Store with ID {store_id} not found")
                return None

            # Update employee with store ID
            return await EmployeeService.update_employee(employee_id, {"store_id": store_id})
        except Exception as e:
            print(f"Error assigning employee to store: {str(e)}")
            return None
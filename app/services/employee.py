# app/services/employee.py
from typing import List, Optional, Dict, Any
from bson import ObjectId
from datetime import datetime
from fastapi import HTTPException, status

from app.core.db import get_database, get_employees_collection
from app.models.employee import EmployeeModel
from app.services.user import get_user_by_id
from app.services.store import StoreService
from app.utils.formatting import format_object_ids, ensure_object_id
from app.utils.id_handler import IdHandler

# Get database and collections
db = get_database()
employees_collection = get_employees_collection()


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
            print(f"Getting employees with filters - position: {position}, store: {store_id}, status: {status}")
            query = {}

            if position:
                query["position"] = {"$regex": position, "$options": "i"}

            if store_id:
                # Try with both string and ObjectId formats for maximum compatibility
                store_obj_id = ensure_object_id(store_id)
                if store_obj_id:
                    # Use $or to try both formats
                    query["$or"] = [
                        {"store_id": store_obj_id},
                        {"store_id": store_id}
                    ]
                else:
                    query["store_id"] = store_id

            if status:
                query["employment_status"] = status

            print(f"Query: {query}")
            employees = await employees_collection.find(query).skip(skip).limit(limit).to_list(length=limit)
            print(f"Found {len(employees)} employees")

            # Add user and store info
            result = []
            for employee in employees:
                employee_with_info = dict(employee)

                # Add user info
                if employee.get("user_id"):
                    print(f"Getting user info for employee {employee.get('_id')}")
                    user = await get_user_by_id(employee["user_id"])
                    if user:
                        employee_with_info["full_name"] = user.get("full_name")
                        employee_with_info["email"] = user.get("email")
                        employee_with_info["phone_number"] = user.get("phone_number")
                    else:
                        print(f"User not found for ID: {employee.get('user_id')}")

                # Add store info
                if employee.get("store_id"):
                    print(f"Getting store info for employee {employee.get('_id')}")
                    store = await StoreService.get_store(str(employee["store_id"]))
                    if store:
                        employee_with_info["store_name"] = store.get("name")
                    else:
                        print(f"Store not found for ID: {employee.get('store_id')}")

                result.append(employee_with_info)

            return format_object_ids(result)
        except Exception as e:
            print(f"Error getting employees: {str(e)}")
            return []

    @staticmethod
    async def get_employee(employee_id: str) -> Optional[dict]:
        """
        Get employee by ID using the centralized ID handler
        """
        try:
            print(f"Looking up employee with ID: {employee_id}")

            # Use centralized method for consistent lookup
            employee, _ = await IdHandler.find_document_by_id(
                employees_collection,
                employee_id,
                not_found_msg=f"Employee with ID {employee_id} not found"
            )

            if not employee:
                print(f"Employee not found with ID: {employee_id}")
                return None

            # Enrich employee data with user and store info
            employee_with_info = dict(employee)

            # Add user info
            if employee.get("user_id"):
                print(f"Getting user info for user_id: {employee.get('user_id')}")
                user = await get_user_by_id(employee["user_id"])
                if user:
                    print(f"Found user: {user.get('email')}")
                    employee_with_info["full_name"] = user.get("full_name")
                    employee_with_info["email"] = user.get("email")
                    employee_with_info["phone_number"] = user.get("phone_number")
                else:
                    print(f"User not found for ID: {employee.get('user_id')}")

            # Add store info
            if employee.get("store_id"):
                print(f"Getting store info for store_id: {employee.get('store_id')}")
                store = await StoreService.get_store(str(employee["store_id"]))
                if store:
                    print(f"Found store: {store.get('name')}")
                    employee_with_info["store_name"] = store.get("name")
                else:
                    print(f"Store not found for ID: {employee.get('store_id')}")

            return IdHandler.format_object_ids(employee_with_info)
        except Exception as e:
            print(f"Error getting employee: {str(e)}")
            return None

    @staticmethod
    async def get_employee_by_user_id(user_id: str) -> Optional[dict]:
        """
        Get employee by user ID with enhanced error handling
        """
        try:
            print(f"Looking up employee by user ID: {user_id}")

            # Multiple lookup strategies
            employee = None

            # 1. Try with ObjectId
            user_obj_id = ensure_object_id(user_id)
            if user_obj_id:
                print(f"Trying lookup with ObjectId: {user_obj_id}")
                employee = await employees_collection.find_one({"user_id": user_obj_id})
                if employee:
                    print(f"Found employee with ObjectId user_id")
                else:
                    print(f"No employee found with ObjectId user_id")

            # 2. Try with string ID
            if not employee:
                print(f"Trying direct string lookup: {user_id}")
                employee = await employees_collection.find_one({"user_id": user_id})
                if employee:
                    print(f"Found employee with string user_id")
                else:
                    print(f"No employee found with string user_id")

            # 3. Try string comparison
            if not employee:
                print("Trying string comparison for user_id...")
                all_employees = await employees_collection.find().to_list(length=100)
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
        Create new employee with enhanced validation and error handling
        """
        try:
            print(f"Creating employee with data: {employee_data}")

            # Validate user_id if provided
            if "user_id" in employee_data and employee_data["user_id"]:
                user_id = employee_data["user_id"]
                print(f"Validating user ID: {user_id}")

                user = await get_user_by_id(user_id)
                if not user:
                    print(f"User not found with ID: {user_id}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"User with ID {user_id} not found"
                    )

                # Store as string for consistency
                employee_data["user_id"] = str(user["_id"])
                print(f"Validated user ID: {employee_data['user_id']}")

            # Validate store_id if provided
            if "store_id" in employee_data and employee_data["store_id"]:
                store_id = employee_data["store_id"]
                print(f"Validating store ID: {store_id}")

                store = await StoreService.get_store(store_id)
                if not store:
                    print(f"Store not found with ID: {store_id}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Store with ID {store_id} not found"
                    )

                # Store as string for consistency
                employee_data["store_id"] = str(store["_id"])
                print(f"Validated store ID: {employee_data['store_id']}")

            # Create employee model
            try:
                employee_model = EmployeeModel(**employee_data)
            except Exception as e:
                print(f"Validation error: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid employee data: {str(e)}"
                )

            # Insert into database
            result = await employees_collection.insert_one(employee_model.model_dump(by_alias=True))
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
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating employee: {str(e)}"
            )

    @staticmethod
    async def update_employee(employee_id: str, employee_data: dict) -> Optional[dict]:
        """
        Update existing employee with enhanced error handling
        """
        try:
            print(f"Updating employee with ID: {employee_id}")
            print(f"Update data: {employee_data}")

            # Update timestamp
            employee_data["updated_at"] = datetime.utcnow()

            # Find the employee using multiple lookup strategies
            employee = None
            employee_obj_id = None

            # 1. Try with ObjectId
            obj_id = ensure_object_id(employee_id)
            if obj_id:
                print(f"Looking up employee with ObjectId: {obj_id}")
                employee = await employees_collection.find_one({"_id": obj_id})
                if employee:
                    employee_obj_id = obj_id
                    print(f"Found employee with ObjectId")
                else:
                    print(f"No employee found with ObjectId")

            # 2. Try string ID lookup
            if not employee:
                print(f"Looking up employee with string ID: {employee_id}")
                employee = await employees_collection.find_one({"_id": employee_id})
                if employee:
                    employee_obj_id = employee["_id"]
                    print(f"Found employee with string ID")
                else:
                    print(f"No employee found with string ID")

            # 3. Try string comparison
            if not employee:
                print("Trying string comparison...")
                all_employees = await employees_collection.find().to_list(length=100)
                for emp in all_employees:
                    if str(emp.get('_id')) == employee_id:
                        employee = emp
                        employee_obj_id = emp["_id"]
                        print(f"Found employee by string comparison")
                        break

            if not employee:
                print(f"Employee not found with ID: {employee_id}")
                return None

            # Validate fields that reference other entities

            # Validate user_id if it's being updated
            if "user_id" in employee_data and employee_data["user_id"]:
                user_id = employee_data["user_id"]
                print(f"Validating user ID: {user_id}")

                user = await get_user_by_id(user_id)
                if not user:
                    print(f"User not found with ID: {user_id}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"User with ID {user_id} not found"
                    )

                # Store as string for consistency
                employee_data["user_id"] = str(user["_id"])
                print(f"Validated user ID: {employee_data['user_id']}")

            # Validate store_id if it's being updated
            if "store_id" in employee_data and employee_data["store_id"]:
                store_id = employee_data["store_id"]
                print(f"Validating store ID: {store_id}")

                store = await StoreService.get_store(store_id)
                if not store:
                    print(f"Store not found with ID: {store_id}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Store with ID {store_id} not found"
                    )

                # Store as string for consistency
                employee_data["store_id"] = str(store["_id"])
                print(f"Validated store ID: {employee_data['store_id']}")

            # Update the employee
            print(f"Updating employee with ID: {employee_obj_id}")
            update_result = await employees_collection.update_one(
                {"_id": employee_obj_id},
                {"$set": employee_data}
            )

            print(f"Update result: matched={update_result.matched_count}, modified={update_result.modified_count}")

            if update_result.matched_count == 0:
                print(f"No employee matched the ID: {employee_obj_id}")
                return None

            # Get the updated employee
            updated_employee = await EmployeeService.get_employee(employee_id)
            return updated_employee
        except Exception as e:
            print(f"Error updating employee: {str(e)}")
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error updating employee: {str(e)}"
            )

    @staticmethod
    async def delete_employee(employee_id: str) -> bool:
        """
        Delete employee with enhanced error handling
        """
        try:
            print(f"Attempting to delete employee with ID: {employee_id}")

            # Find the employee using multiple lookup strategies
            employee = None
            employee_obj_id = None

            # 1. Try with ObjectId
            obj_id = ensure_object_id(employee_id)
            if obj_id:
                print(f"Looking up employee with ObjectId: {obj_id}")
                employee = await employees_collection.find_one({"_id": obj_id})
                if employee:
                    employee_obj_id = obj_id
                    print(f"Found employee with ObjectId")
                else:
                    print(f"No employee found with ObjectId")

            # 2. Try string ID lookup
            if not employee:
                print(f"Looking up employee with string ID: {employee_id}")
                employee = await employees_collection.find_one({"_id": employee_id})
                if employee:
                    employee_obj_id = employee["_id"]
                    print(f"Found employee with string ID")
                else:
                    print(f"No employee found with string ID")

            # 3. Try string comparison
            if not employee:
                print("Trying string comparison...")
                all_employees = await employees_collection.find().to_list(length=100)
                for emp in all_employees:
                    if str(emp.get('_id')) == employee_id:
                        employee = emp
                        employee_obj_id = emp["_id"]
                        print(f"Found employee by string comparison")
                        break

            if not employee:
                print(f"Employee not found with ID: {employee_id}")
                return False

            # Delete the employee
            result = await employees_collection.delete_one({"_id": employee_obj_id})

            print(f"Delete result: deleted={result.deleted_count}")
            return result.deleted_count > 0
        except Exception as e:
            print(f"Error deleting employee: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error deleting employee: {str(e)}"
            )

    @staticmethod
    async def assign_to_store(employee_id: str, store_id: str) -> Optional[dict]:
        """
        Assign employee to store with enhanced validation
        """
        try:
            print(f"Attempting to assign employee {employee_id} to store {store_id}")

            # Find employee
            employee = await EmployeeService.get_employee(employee_id)
            if not employee:
                print(f"Employee with ID {employee_id} not found")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Employee with ID {employee_id} not found"
                )

            # Find store
            store = await StoreService.get_store(store_id)
            if not store:
                print(f"Store with ID {store_id} not found")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Store with ID {store_id} not found"
                )

            # Update employee with store ID
            return await EmployeeService.update_employee(employee_id, {"store_id": str(store["_id"])})
        except Exception as e:
            print(f"Error assigning employee to store: {str(e)}")
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error assigning employee to store: {str(e)}"
            )
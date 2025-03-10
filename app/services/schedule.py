# app/services/schedule.py
from datetime import datetime
from typing import List, Optional, Dict, Any
from bson import ObjectId
from fastapi import HTTPException, status

from app.core.db import get_database, get_schedules_collection, get_employees_collection, get_stores_collection
from app.utils.formatting import format_object_ids, ensure_object_id
from app.utils.id_handler import IdHandler

# Get database and collections
db = get_database()
schedules_collection = get_schedules_collection()
employees_collection = get_employees_collection()
stores_collection = get_stores_collection()


class ScheduleService:
    @staticmethod
    async def get_schedules(
            skip: int = 0,
            limit: int = 100,
            store_id: Optional[str] = None,
            employee_id: Optional[str] = None,
            start_date: Optional[str] = None,
            end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all schedules with optional filtering
        """
        try:
            query = {}

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

            if start_date:
                if "end_date" in query:
                    query["end_date"]["$gte"] = start_date
                else:
                    query["end_date"] = {"$gte": start_date}

            if end_date:
                if "start_date" in query:
                    query["start_date"]["$lte"] = end_date
                else:
                    query["start_date"] = {"$lte": end_date}

            # Filtering by employee ID is more complex since employees are in the shifts array
            employee_filter = None
            if employee_id:
                employee_obj_id = ensure_object_id(employee_id)
                if employee_obj_id:
                    employee_filter = {"shifts.employee_id": employee_obj_id}
                else:
                    employee_filter = {"shifts.employee_id": employee_id}

            # First get the schedules based on main filters
            schedules = await schedules_collection.find(query).skip(skip).limit(limit).to_list(length=limit)

            # Then filter by employee ID if needed
            if employee_filter and schedules:
                filtered_schedules = []
                for schedule in schedules:
                    # Check if any shift has this employee
                    if "shifts" in schedule:
                        for shift in schedule.get("shifts", []):
                            shift_emp_id = shift.get("employee_id")
                            if (isinstance(shift_emp_id,
                                           ObjectId) and employee_obj_id and shift_emp_id == employee_obj_id) or \
                                    (isinstance(shift_emp_id, str) and shift_emp_id == employee_id) or \
                                    (str(shift_emp_id) == employee_id):
                                filtered_schedules.append(schedule)
                                break
                schedules = filtered_schedules

            # Enrich schedules with store and employee info
            result = []
            for schedule in schedules:
                schedule_with_info = dict(schedule)

                # Add store info
                if schedule.get("store_id"):
                    store = await stores_collection.find_one({"_id": schedule.get("store_id")})
                    if store:
                        schedule_with_info["store_name"] = store.get("name")

                # Get names of all employees in shifts
                if "shifts" in schedule:
                    employee_names = {}
                    for shift in schedule.get("shifts", []):
                        emp_id = shift.get("employee_id")
                        if emp_id and emp_id not in employee_names:
                            employee = await employees_collection.find_one({"_id": emp_id})
                            if employee and employee.get("user_id"):
                                from app.services.user import get_user_by_id
                                user = await get_user_by_id(employee.get("user_id"))
                                if user:
                                    employee_names[str(emp_id)] = user.get("full_name")

                    schedule_with_info["employee_names"] = employee_names

                result.append(schedule_with_info)

            return format_object_ids(result)
        except Exception as e:
            print(f"Error getting schedules: {str(e)}")
            return []

    @staticmethod
    async def get_schedule(schedule_id: str) -> Optional[Dict[str, Any]]:
        """
        Get schedule by ID using the centralized ID handler
        """
        try:
            print(f"Looking up schedule with ID: {schedule_id}")

            # Use centralized method for consistent lookup
            schedule, _ = await IdHandler.find_document_by_id(
                schedules_collection,
                schedule_id,
                not_found_msg=f"Schedule with ID {schedule_id} not found"
            )

            if not schedule:
                print(f"Schedule not found with ID: {schedule_id}")
                return None

            # Enrich schedule with store and employee info
            schedule_with_info = dict(schedule)

            # Add store info
            if schedule.get("store_id"):
                store = await stores_collection.find_one({"_id": schedule.get("store_id")})
                if store:
                    schedule_with_info["store_name"] = store.get("name")

            # Get names of all employees in shifts
            if "shifts" in schedule:
                employee_names = {}
                for shift in schedule.get("shifts", []):
                    emp_id = shift.get("employee_id")
                    if emp_id and str(emp_id) not in employee_names:
                        employee = await employees_collection.find_one({"_id": emp_id})
                        if employee and employee.get("user_id"):
                            from app.services.user import get_user_by_id
                            user = await get_user_by_id(employee.get("user_id"))
                            if user:
                                employee_names[str(emp_id)] = user.get("full_name")

                schedule_with_info["employee_names"] = employee_names

            return IdHandler.format_object_ids(schedule_with_info)
        except Exception as e:
            print(f"Error getting schedule: {str(e)}")
            return None

    @staticmethod
    async def get_schedules_by_store(store_id: str) -> List[Dict[str, Any]]:
        """
        Get schedules for a specific store
        """
        try:
            print(f"Getting schedules for store ID: {store_id}")
            return await ScheduleService.get_schedules(store_id=store_id)
        except Exception as e:
            print(f"Error getting schedules by store: {str(e)}")
            return []

    @staticmethod
    async def create_schedule(schedule_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new schedule
        """
        try:
            print(f"Creating schedule: {schedule_data}")

            # Validate store exists
            if "store_id" in schedule_data:
                from app.services.store import StoreService
                store = await StoreService.get_store(schedule_data["store_id"])
                if not store:
                    raise ValueError(f"Store with ID {schedule_data['store_id']} not found")

            # Make sure shifts is always an array
            if "shifts" not in schedule_data:
                schedule_data["shifts"] = []

            # Add timestamps
            now = datetime.utcnow()
            schedule_data["created_at"] = now
            schedule_data["updated_at"] = now

            # Insert into database
            result = await schedules_collection.insert_one(schedule_data)

            # Get the created schedule
            if result.inserted_id:
                created_schedule = await ScheduleService.get_schedule(str(result.inserted_id))
                if created_schedule:
                    return created_schedule

            raise ValueError("Failed to retrieve created schedule")
        except ValueError as e:
            print(f"Validation error creating schedule: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            print(f"Error creating schedule: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating schedule: {str(e)}"
            )

    @staticmethod
    async def update_schedule(schedule_id: str, schedule_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update an existing schedule
        """
        try:
            print(f"Updating schedule with ID: {schedule_id}")

            # Find the schedule
            schedule, schedule_obj_id = await IdHandler.find_document_by_id(
                schedules_collection,
                schedule_id,
                not_found_msg=f"Schedule with ID {schedule_id} not found"
            )

            if not schedule:
                return None

            # Validate store exists if changing store
            if "store_id" in schedule_data:
                from app.services.store import StoreService
                store = await StoreService.get_store(schedule_data["store_id"])
                if not store:
                    raise ValueError(f"Store with ID {schedule_data['store_id']} not found")

            # Update timestamp
            schedule_data["updated_at"] = datetime.utcnow()

            # Update the schedule
            update_result = await schedules_collection.update_one(
                {"_id": schedule_obj_id},
                {"$set": schedule_data}
            )

            if update_result.matched_count == 0:
                return None

            # Get the updated schedule
            updated_schedule = await ScheduleService.get_schedule(schedule_id)
            return updated_schedule
        except ValueError as e:
            print(f"Validation error updating schedule: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            print(f"Error updating schedule: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error updating schedule: {str(e)}"
            )

    @staticmethod
    async def delete_schedule(schedule_id: str) -> bool:
        """
        Delete a schedule
        """
        try:
            print(f"Deleting schedule with ID: {schedule_id}")

            # Find the schedule
            schedule, schedule_obj_id = await IdHandler.find_document_by_id(
                schedules_collection,
                schedule_id,
                not_found_msg=f"Schedule with ID {schedule_id} not found"
            )

            if not schedule:
                return False

            # Delete the schedule
            delete_result = await schedules_collection.delete_one({"_id": schedule_obj_id})

            return delete_result.deleted_count > 0
        except Exception as e:
            print(f"Error deleting schedule: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error deleting schedule: {str(e)}"
            )

    @staticmethod
    async def add_shift(schedule_id: str, shift_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Add a shift to a schedule
        """
        try:
            print(f"Adding shift to schedule {schedule_id}: {shift_data}")

            # Find the schedule
            schedule, schedule_obj_id = await IdHandler.find_document_by_id(
                schedules_collection,
                schedule_id,
                not_found_msg=f"Schedule with ID {schedule_id} not found"
            )

            if not schedule:
                return None

            # Validate employee exists
            if "employee_id" in shift_data:
                from app.services.employee import EmployeeService
                employee = await EmployeeService.get_employee(shift_data["employee_id"])
                if not employee:
                    raise ValueError(f"Employee with ID {shift_data['employee_id']} not found")

            # Add an ID to the shift
            shift_data["_id"] = str(ObjectId())

            # Update timestamp for the schedule
            update_data = {
                "updated_at": datetime.utcnow()
            }

            # Add the shift to the schedule
            update_result = await schedules_collection.update_one(
                {"_id": schedule_obj_id},
                {
                    "$set": update_data,
                    "$push": {"shifts": shift_data}
                }
            )

            if update_result.matched_count == 0:
                return None

            # Get the updated schedule
            updated_schedule = await ScheduleService.get_schedule(schedule_id)
            return updated_schedule
        except ValueError as e:
            print(f"Validation error adding shift: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            print(f"Error adding shift: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error adding shift: {str(e)}"
            )

    @staticmethod
    async def update_shift(schedule_id: str, shift_id: str, shift_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update a shift in a schedule
        """
        try:
            print(f"Updating shift {shift_id} in schedule {schedule_id}: {shift_data}")

            # Find the schedule
            schedule, schedule_obj_id = await IdHandler.find_document_by_id(
                schedules_collection,
                schedule_id,
                not_found_msg=f"Schedule with ID {schedule_id} not found"
            )

            if not schedule:
                return None

            # Find the shift in the schedule
            shift_exists = False
            for shift in schedule.get("shifts", []):
                if str(shift.get("_id")) == shift_id:
                    shift_exists = True
                    break

            if not shift_exists:
                raise ValueError(f"Shift with ID {shift_id} not found in schedule {schedule_id}")

            # Validate employee exists if changing employee
            if "employee_id" in shift_data:
                from app.services.employee import EmployeeService
                employee = await EmployeeService.get_employee(shift_data["employee_id"])
                if not employee:
                    raise ValueError(f"Employee with ID {shift_data['employee_id']} not found")

            # Update timestamp for the schedule
            shift_data["updated_at"] = datetime.utcnow()

            # Use the positional $ operator to update the specific shift
            update_data = {}
            for key, value in shift_data.items():
                update_data[f"shifts.$.{key}"] = value

            # Also update the schedule's updated_at timestamp
            update_data["updated_at"] = datetime.utcnow()

            # Update the shift
            update_result = await schedules_collection.update_one(
                {
                    "_id": schedule_obj_id,
                    "shifts._id": shift_id
                },
                {"$set": update_data}
            )

            if update_result.matched_count == 0:
                return None

            # Get the updated schedule
            updated_schedule = await ScheduleService.get_schedule(schedule_id)
            return updated_schedule
        except ValueError as e:
            print(f"Validation error updating shift: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            print(f"Error updating shift: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error updating shift: {str(e)}"
            )

    @staticmethod
    async def delete_shift(schedule_id: str, shift_id: str) -> Optional[Dict[str, Any]]:
        """
        Delete a shift from a schedule
        """
        try:
            print(f"Deleting shift {shift_id} from schedule {schedule_id}")

            # Find the schedule
            schedule, schedule_obj_id = await IdHandler.find_document_by_id(
                schedules_collection,
                schedule_id,
                not_found_msg=f"Schedule with ID {schedule_id} not found"
            )

            if not schedule:
                return None

            # Update the schedule's updated_at timestamp and pull the shift
            update_result = await schedules_collection.update_one(
                {"_id": schedule_obj_id},
                {
                    "$set": {"updated_at": datetime.utcnow()},
                    "$pull": {"shifts": {"_id": shift_id}}
                }
            )

            if update_result.matched_count == 0:
                return None

            # Get the updated schedule
            updated_schedule = await ScheduleService.get_schedule(schedule_id)
            return updated_schedule
        except Exception as e:
            print(f"Error deleting shift: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error deleting shift: {str(e)}"
            )

    @staticmethod
    async def get_employee_shifts(
            employee_id: str,
            start_date: Optional[str] = None,
            end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all shifts for an employee across schedules
        """
        try:
            print(f"Getting shifts for employee {employee_id} from {start_date} to {end_date}")

            # Build the query
            query = {}

            if start_date or end_date:
                date_filter = {}
                if start_date:
                    date_filter["$gte"] = start_date
                if end_date:
                    date_filter["$lte"] = end_date

                if start_date and end_date:
                    # Either start_date is within range or end_date is within range
                    query["$or"] = [
                        {"start_date": date_filter},
                        {"end_date": date_filter},
                        # Or the range completely contains our range
                        {
                            "start_date": {"$lte": start_date},
                            "end_date": {"$gte": end_date}
                        }
                    ]
                else:
                    if start_date:
                        query["end_date"] = {"$gte": start_date}
                    if end_date:
                        query["start_date"] = {"$lte": end_date}

            # Get all schedules matching the date range
            schedules = await schedules_collection.find(query).to_list(length=100)

            # Extract shifts for the employee
            employee_shifts = []

            employee_obj_id = ensure_object_id(employee_id)

            for schedule in schedules:
                schedule_info = {
                    "schedule_id": str(schedule["_id"]),
                    "schedule_title": schedule.get("title", "Untitled Schedule"),
                    "store_id": str(schedule.get("store_id")),
                    "store_name": None
                }

                # Get store info
                if schedule.get("store_id"):
                    store = await stores_collection.find_one({"_id": schedule.get("store_id")})
                    if store:
                        schedule_info["store_name"] = store.get("name")

                # Find shifts for this employee
                for shift in schedule.get("shifts", []):
                    shift_emp_id = shift.get("employee_id")
                    if (isinstance(shift_emp_id, ObjectId) and employee_obj_id and shift_emp_id == employee_obj_id) or \
                            (isinstance(shift_emp_id, str) and shift_emp_id == employee_id) or \
                            (str(shift_emp_id) == employee_id):
                        # Add schedule info to the shift
                        shift_with_info = dict(shift)
                        shift_with_info.update(schedule_info)
                        employee_shifts.append(shift_with_info)

            return format_object_ids(employee_shifts)
        except Exception as e:
            print(f"Error getting employee shifts: {str(e)}")
            return []
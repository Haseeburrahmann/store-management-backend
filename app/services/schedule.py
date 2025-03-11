# app/services/schedule.py
from datetime import datetime
from typing import List, Optional, Dict, Any
from bson import ObjectId
from fastapi import HTTPException, status

from app.core.db import get_database, get_schedules_collection, get_employees_collection, get_stores_collection
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
        Get all schedules with standardized ID handling
        """
        try:
            query = {}

            if store_id:
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

            # First get the schedules based on main filters
            schedules = await schedules_collection.find(query).skip(skip).limit(limit).to_list(length=limit)

            # Then filter by employee ID if needed
            if employee_id and schedules:
                filtered_schedules = []
                for schedule in schedules:
                    # Check if any shift has this employee
                    if "shifts" in schedule:
                        for shift in schedule.get("shifts", []):
                            shift_emp_id = shift.get("employee_id")
                            if IdHandler.id_to_str(shift_emp_id) == IdHandler.id_to_str(employee_id):
                                filtered_schedules.append(schedule)
                                break
                schedules = filtered_schedules

            # Enrich schedules with store and employee info
            result = []
            for schedule in schedules:
                schedule_with_info = dict(schedule)

                # Add store info using centralized ID handler
                if schedule.get("store_id"):
                    store, _ = await IdHandler.find_document_by_id(
                        stores_collection,
                        schedule.get("store_id"),
                        not_found_msg=f"Store not found for ID: {schedule.get('store_id')}"
                    )

                    if store:
                        schedule_with_info["store_name"] = store.get("name")

                # Get names of all employees in shifts
                if "shifts" in schedule:
                    employee_names = {}
                    for shift in schedule.get("shifts", []):
                        emp_id = shift.get("employee_id")
                        if emp_id and IdHandler.id_to_str(emp_id) not in employee_names:
                            employee, _ = await IdHandler.find_document_by_id(
                                employees_collection,
                                emp_id,
                                not_found_msg=f"Employee not found for ID: {emp_id}"
                            )

                            if employee and employee.get("user_id"):
                                from app.services.user import get_user_by_id
                                user = await get_user_by_id(employee.get("user_id"))
                                if user:
                                    employee_names[IdHandler.id_to_str(emp_id)] = user.get("full_name")

                    schedule_with_info["employee_names"] = employee_names

                result.append(schedule_with_info)

            return IdHandler.format_object_ids(result)
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

            # Add store info using centralized ID handler
            if schedule.get("store_id"):
                store, _ = await IdHandler.find_document_by_id(
                    stores_collection,
                    schedule.get("store_id"),
                    not_found_msg=f"Store not found for ID: {schedule.get('store_id')}"
                )

                if store:
                    schedule_with_info["store_name"] = store.get("name")

            # Get names of all employees in shifts
            if "shifts" in schedule:
                employee_names = {}
                for shift in schedule.get("shifts", []):
                    emp_id = shift.get("employee_id")
                    if emp_id and IdHandler.id_to_str(emp_id) not in employee_names:
                        employee, _ = await IdHandler.find_document_by_id(
                            employees_collection,
                            emp_id,
                            not_found_msg=f"Employee not found for ID: {emp_id}"
                        )

                        if employee and employee.get("user_id"):
                            from app.services.user import get_user_by_id
                            user = await get_user_by_id(employee.get("user_id"))
                            if user:
                                employee_names[IdHandler.id_to_str(emp_id)] = user.get("full_name")

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
        Create a new schedule with standardized ID handling
        """
        try:
            print(f"Creating schedule: {schedule_data}")

            # Validate store exists using centralized ID handler
            if "store_id" in schedule_data:
                store, store_obj_id = await IdHandler.find_document_by_id(
                    stores_collection,
                    schedule_data["store_id"],
                    not_found_msg=f"Store with ID {schedule_data['store_id']} not found"
                )

                if not store:
                    raise ValueError(f"Store with ID {schedule_data['store_id']} not found")

                # Ensure store_id is stored consistently as string
                schedule_data["store_id"] = IdHandler.id_to_str(store_obj_id)

            # Make sure shifts is always an array
            if "shifts" not in schedule_data:
                schedule_data["shifts"] = []

            # Ensure created_by is stored as string
            if "created_by" in schedule_data:
                from app.services.user import get_user_by_id
                user, user_obj_id = await IdHandler.find_document_by_id(
                    get_database().users,
                    schedule_data["created_by"],
                    not_found_msg=f"User with ID {schedule_data['created_by']} not found"
                )

                if user:
                    schedule_data["created_by"] = IdHandler.id_to_str(user_obj_id)

            # Add timestamps
            now = datetime.utcnow()
            schedule_data["created_at"] = now
            schedule_data["updated_at"] = now

            # Insert into database
            result = await schedules_collection.insert_one(schedule_data)

            # Get the created schedule using our standardized method
            created_schedule, _ = await IdHandler.find_document_by_id(
                schedules_collection,
                str(result.inserted_id),
                not_found_msg=f"Failed to retrieve created schedule"
            )

            if created_schedule:
                return IdHandler.format_object_ids(created_schedule)

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

    async def update_schedule(schedule_id: str, schedule_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            # Convert schedule_id to ObjectId
            schedule_obj_id = ObjectId(schedule_id)

            # Find existing schedule
            existing_schedule = await schedules_collection.find_one({"_id": schedule_obj_id})
            if not existing_schedule:
                raise HTTPException(status_code=404, detail="Schedule not found")

            # Prepare update document
            update_doc = {
                "$set": {
                    "title": schedule_data.get("title", existing_schedule.get("title")),
                    "start_date": schedule_data.get("start_date", existing_schedule.get("start_date")),
                    "end_date": schedule_data.get("end_date", existing_schedule.get("end_date")),
                    "updated_at": datetime.utcnow()
                }
            }

            # Process shifts with comprehensive handling
            if "shifts" in schedule_data:
                processed_shifts = []
                for shift in schedule_data["shifts"]:
                    # Generate or preserve shift ID
                    shift_id = shift.get('_id', '')
                    if not shift_id or shift_id.startswith('temp_'):
                        shift_id = str(ObjectId())

                    clean_shift = {
                        "_id": shift_id,
                        "employee_id": str(shift["employee_id"]),
                        "date": shift["date"],
                        "start_time": shift["start_time"],
                        "end_time": shift["end_time"],
                        "notes": shift.get("notes"),
                        # Optional: preserve additional metadata if needed
                        "employee_name": shift.get("employee_name")
                    }
                    processed_shifts.append(clean_shift)

                # Replace entire shifts array
                update_doc["$set"]["shifts"] = processed_shifts

            # Perform update
            result = await schedules_collection.update_one(
                {"_id": schedule_obj_id},
                update_doc
            )

            # Retrieve updated schedule
            updated_schedule = await schedules_collection.find_one({"_id": schedule_obj_id})

            # Convert ObjectIds to strings and process schedule
            if updated_schedule:
                updated_schedule["_id"] = str(updated_schedule["_id"])
                updated_schedule["store_id"] = str(updated_schedule.get("store_id", ""))
                updated_schedule["created_by"] = str(updated_schedule.get("created_by", ""))

                # Process shifts
                if "shifts" in updated_schedule:
                    for shift in updated_schedule["shifts"]:
                        shift["_id"] = str(shift.get("_id", ""))
                        shift["employee_id"] = str(shift.get("employee_id", ""))

            return updated_schedule

        except Exception as e:
            print(f"Comprehensive update error: {str(e)}")
            import traceback
            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail=f"Update failed: {str(e)}"
            )

    @staticmethod
    async def delete_schedule(schedule_id: str) -> bool:
        """
        Delete a schedule with standardized ID handling
        """
        try:
            print(f"Deleting schedule with ID: {schedule_id}")

            # Find the schedule using centralized ID handler
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
        Add a shift to a schedule with standardized ID handling
        """
        try:
            print(f"Adding shift to schedule {schedule_id}: {shift_data}")

            # Find the schedule using centralized ID handler
            schedule, schedule_obj_id = await IdHandler.find_document_by_id(
                schedules_collection,
                schedule_id,
                not_found_msg=f"Schedule with ID {schedule_id} not found"
            )

            if not schedule:
                return None

            # Validate employee exists using centralized ID handler
            if "employee_id" in shift_data:
                employee, employee_obj_id = await IdHandler.find_document_by_id(
                    employees_collection,
                    shift_data["employee_id"],
                    not_found_msg=f"Employee with ID {shift_data['employee_id']} not found"
                )

                if not employee:
                    raise ValueError(f"Employee with ID {shift_data['employee_id']} not found")

                # Ensure employee_id is stored consistently as string
                shift_data["employee_id"] = IdHandler.id_to_str(employee_obj_id)

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

            # Get the updated schedule using our standardized method
            updated_schedule, _ = await IdHandler.find_document_by_id(
                schedules_collection,
                schedule_id,
                not_found_msg=f"Failed to retrieve updated schedule"
            )

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
        Update a shift in a schedule with standardized ID handling
        """
        try:
            print(f"Updating shift {shift_id} in schedule {schedule_id}: {shift_data}")

            # Find the schedule using centralized ID handler
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
                if IdHandler.id_to_str(shift.get("_id")) == shift_id:
                    shift_exists = True
                    break

            if not shift_exists:
                raise ValueError(f"Shift with ID {shift_id} not found in schedule {schedule_id}")

            # Validate employee exists if changing employee
            if "employee_id" in shift_data:
                employee, employee_obj_id = await IdHandler.find_document_by_id(
                    employees_collection,
                    shift_data["employee_id"],
                    not_found_msg=f"Employee with ID {shift_data['employee_id']} not found"
                )

                if not employee:
                    raise ValueError(f"Employee with ID {shift_data['employee_id']} not found")

                # Ensure employee_id is stored consistently as string
                shift_data["employee_id"] = IdHandler.id_to_str(employee_obj_id)

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

            # Get the updated schedule using our standardized method
            updated_schedule, _ = await IdHandler.find_document_by_id(
                schedules_collection,
                schedule_id,
                not_found_msg=f"Failed to retrieve updated schedule"
            )

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
        Delete a shift from a schedule with standardized ID handling
        """
        try:
            print(f"Deleting shift {shift_id} from schedule {schedule_id}")

            # Find the schedule using centralized ID handler
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

            # Get the updated schedule using our standardized method
            updated_schedule, _ = await IdHandler.find_document_by_id(
                schedules_collection,
                schedule_id,
                not_found_msg=f"Failed to retrieve updated schedule"
            )

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
        Get all shifts for an employee across schedules with standardized ID handling
        """
        try:
            print(f"Getting shifts for employee {employee_id} from {start_date} to {end_date}")

            # Validate employee exists using centralized ID handler
            employee, employee_obj_id = await IdHandler.find_document_by_id(
                employees_collection,
                employee_id,
                not_found_msg=f"Employee with ID {employee_id} not found"
            )

            if not employee:
                return []

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
            employee_id_str = IdHandler.id_to_str(employee_obj_id)

            for schedule in schedules:
                schedule_info = {
                    "schedule_id": IdHandler.id_to_str(schedule["_id"]),
                    "schedule_title": schedule.get("title", "Untitled Schedule"),
                    "store_id": IdHandler.id_to_str(schedule.get("store_id")),
                    "store_name": None
                }

                # Get store info using centralized ID handler
                if schedule.get("store_id"):
                    store, _ = await IdHandler.find_document_by_id(
                        stores_collection,
                        schedule.get("store_id"),
                        not_found_msg=f"Store not found for ID: {schedule.get('store_id')}"
                    )

                    if store:
                        schedule_info["store_name"] = store.get("name")

                # Find shifts for this employee
                for shift in schedule.get("shifts", []):
                    shift_emp_id = IdHandler.id_to_str(shift.get("employee_id"))
                    if shift_emp_id == employee_id_str:
                        # Add schedule info to the shift
                        shift_with_info = dict(shift)
                        shift_with_info.update(schedule_info)
                        employee_shifts.append(shift_with_info)

            return IdHandler.format_object_ids(employee_shifts)
        except Exception as e:
            print(f"Error getting employee shifts: {str(e)}")
            return []
# app/services/schedule.py
import re
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

    # Improved schedule.py functions

    @staticmethod
    async def get_schedule(schedule_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific schedule by ID with standardized ID handling
        """
        try:
            print(f"Getting schedule with ID: {schedule_id}")

            # Find the schedule using centralized ID handler
            schedule, schedule_obj_id = await IdHandler.find_document_by_id(
                schedules_collection,
                schedule_id,
                not_found_msg=f"Schedule with ID {schedule_id} not found"
            )

            if not schedule:
                return None

            # Format for frontend consistency
            formatted_schedule = dict(schedule)
            formatted_schedule["_id"] = IdHandler.id_to_str(schedule.get("_id"))
            formatted_schedule["store_id"] = IdHandler.id_to_str(schedule.get("store_id"))

            if "created_by" in schedule:
                formatted_schedule["created_by"] = IdHandler.id_to_str(schedule.get("created_by"))

            # Format shifts array
            if "shifts" in schedule:
                formatted_shifts = []
                for shift in schedule.get("shifts", []):
                    formatted_shift = dict(shift)
                    formatted_shift["_id"] = IdHandler.id_to_str(shift.get("_id"))
                    formatted_shift["employee_id"] = IdHandler.id_to_str(shift.get("employee_id"))
                    formatted_shifts.append(formatted_shift)
                formatted_schedule["shifts"] = formatted_shifts

            # Add store info
            if schedule.get("store_id"):
                store, _ = await IdHandler.find_document_by_id(
                    stores_collection,
                    schedule.get("store_id"),
                    not_found_msg=f"Store not found for ID: {schedule.get('store_id')}"
                )

                if store:
                    formatted_schedule["store_name"] = store.get("name")

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

                formatted_schedule["employee_names"] = employee_names

            return formatted_schedule
        except Exception as e:
            print(f"Error getting schedule: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting schedule: {str(e)}"
            )

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
        Create a new schedule with enhanced validation
        """
        try:
            print(f"Creating schedule: {schedule_data}")

            # Validate required fields
            required_fields = ["title", "store_id", "start_date", "end_date"]
            for field in required_fields:
                if field not in schedule_data:
                    raise ValueError(f"Missing required field: {field}")

            # Validate store exists using centralized ID handler
            store, store_obj_id = await IdHandler.find_document_by_id(
                stores_collection,
                schedule_data["store_id"],
                not_found_msg=f"Store with ID {schedule_data['store_id']} not found"
            )

            if not store:
                raise ValueError(f"Store with ID {schedule_data['store_id']} not found")

            # Ensure store_id is stored consistently as string
            schedule_data["store_id"] = IdHandler.id_to_str(store_obj_id)

            # Validate dates
            start_date = schedule_data["start_date"]
            end_date = schedule_data["end_date"]

            # Check date format
            if not (re.match(r'^\d{4}-\d{2}-\d{2}$', start_date) and re.match(r'^\d{4}-\d{2}-\d{2}$', end_date)):
                raise ValueError("Dates must be in YYYY-MM-DD format")

            # Check date range
            if start_date > end_date:
                raise ValueError("End date must be on or after start date")

            # Validate shifts if provided
            if "shifts" in schedule_data and schedule_data["shifts"]:
                validated_shifts = []

                for shift in schedule_data["shifts"]:
                    # Validate required shift fields
                    shift_required_fields = ["employee_id", "date", "start_time", "end_time"]
                    for field in shift_required_fields:
                        if field not in shift:
                            raise ValueError(f"Shift missing required field: {field}")

                    # Validate employee exists
                    employee, employee_obj_id = await IdHandler.find_document_by_id(
                        employees_collection,
                        shift["employee_id"],
                        not_found_msg=f"Employee with ID {shift['employee_id']} not found"
                    )

                    if not employee:
                        raise ValueError(f"Employee with ID {shift['employee_id']} not found")

                    # Ensure employee_id is stored consistently as string
                    validated_shift = dict(shift)
                    validated_shift["employee_id"] = IdHandler.id_to_str(employee_obj_id)

                    # Validate shift date
                    shift_date = shift["date"]
                    if not re.match(r'^\d{4}-\d{2}-\d{2}$', shift_date):
                        raise ValueError(f"Shift date must be in YYYY-MM-DD format: {shift_date}")

                    # Check if shift date is within schedule range
                    if shift_date < start_date or shift_date > end_date:
                        raise ValueError(
                            f"Shift date {shift_date} must be within schedule date range ({start_date} - {end_date})")

                    # Validate shift times
                    start_time = shift["start_time"]
                    end_time = shift["end_time"]

                    if not re.match(r'^([01]\d|2[0-3]):([0-5]\d)$', start_time):
                        raise ValueError(f"Shift start time must be in HH:MM format (24-hour): {start_time}")

                    if not re.match(r'^([01]\d|2[0-3]):([0-5]\d)$', end_time):
                        raise ValueError(f"Shift end time must be in HH:MM format (24-hour): {end_time}")

                    if end_time <= start_time:
                        raise ValueError("Shift end time must be after start time")

                    # Add an ID to the shift
                    validated_shift["_id"] = str(ObjectId())

                    validated_shifts.append(validated_shift)

                schedule_data["shifts"] = validated_shifts
            else:
                schedule_data["shifts"] = []

            # Ensure created_by is stored as string if provided
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
            inserted_id = result.inserted_id

            # Get the created schedule
            created_schedule = await schedules_collection.find_one({"_id": inserted_id})
            if not created_schedule:
                raise ValueError("Failed to retrieve created schedule")

            # Format for frontend consistency
            formatted_schedule = dict(created_schedule)
            formatted_schedule["_id"] = IdHandler.id_to_str(inserted_id)
            formatted_schedule["store_id"] = IdHandler.id_to_str(created_schedule.get("store_id"))

            if "created_by" in formatted_schedule:
                formatted_schedule["created_by"] = IdHandler.id_to_str(formatted_schedule.get("created_by"))

            # Format shifts array
            if "shifts" in formatted_schedule:
                formatted_shifts = []
                for shift in formatted_schedule.get("shifts", []):
                    formatted_shift = dict(shift)
                    formatted_shift["_id"] = IdHandler.id_to_str(shift.get("_id"))
                    formatted_shift["employee_id"] = IdHandler.id_to_str(shift.get("employee_id"))
                    formatted_shifts.append(formatted_shift)
                formatted_schedule["shifts"] = formatted_shifts

            # Add store name
            formatted_schedule["store_name"] = store.get("name")

            # Get names of employees in shifts efficiently
            employee_names = {}
            if "shifts" in formatted_schedule:
                employee_ids = set()
                for shift in formatted_schedule.get("shifts", []):
                    emp_id = shift.get("employee_id")
                    if emp_id:
                        employee_ids.add(emp_id)

                for emp_id in employee_ids:
                    employee, _ = await IdHandler.find_document_by_id(
                        employees_collection,
                        emp_id,
                        not_found_msg=f"Employee not found for ID: {emp_id}"
                    )

                    if employee and employee.get("user_id"):
                        from app.services.user import get_user_by_id
                        user = await get_user_by_id(employee.get("user_id"))
                        if user:
                            employee_names[emp_id] = user.get("full_name")

            formatted_schedule["employee_names"] = employee_names

            return formatted_schedule
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

    # In app/services/schedule.py
    @staticmethod
    async def update_schedule(schedule_id: str, schedule_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            print(f"Processing schedule update for ID: {schedule_id}")

            # Convert schedule_id to ObjectId
            schedule_obj_id = IdHandler.ensure_object_id(schedule_id)
            if not schedule_obj_id:
                print(f"Invalid schedule ID format: {schedule_id}")
                return None

            # Find existing schedule
            existing_schedule = await schedules_collection.find_one({"_id": schedule_obj_id})
            if not existing_schedule:
                print(f"Schedule not found with ID: {schedule_id}")
                return None

            # Create a complete new document based on the existing one
            new_schedule = dict(existing_schedule)

            # Update basic fields
            for field in ["title", "store_id", "start_date", "end_date"]:
                if field in schedule_data:
                    new_schedule[field] = schedule_data[field]

            # Update timestamp
            new_schedule["updated_at"] = datetime.utcnow()

            # Handle shifts with the helper method
            if "shifts" in schedule_data and isinstance(schedule_data["shifts"], list):
                print(f"Processing {len(schedule_data['shifts'])} shifts")

                # Use the helper method to process each shift
                processed_shifts = [IdHandler.process_shift(shift) for shift in schedule_data["shifts"]]

                # Replace the shifts array completely
                new_schedule["shifts"] = processed_shifts
                print(f"Final processed shifts: {len(processed_shifts)}")

            # Replace the entire document
            result = await schedules_collection.replace_one(
                {"_id": schedule_obj_id},
                new_schedule
            )

            print(f"Update result: matched={result.matched_count}, modified={result.modified_count}")

            # Get the updated document
            updated_schedule = await schedules_collection.find_one({"_id": schedule_obj_id})
            if updated_schedule:
                return IdHandler.format_object_ids(updated_schedule)
            else:
                print(f"Failed to retrieve updated schedule")
                return None

        except Exception as e:
            print(f"Error updating schedule: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

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
        Add a shift to a schedule with improved validation and ID handling
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

            schedule_id_str = IdHandler.id_to_str(schedule_obj_id)

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

            # Validate shift dates fall within schedule dates
            if "date" in shift_data:
                schedule_start = schedule.get("start_date")
                schedule_end = schedule.get("end_date")
                shift_date = shift_data["date"]

                if shift_date < schedule_start or shift_date > schedule_end:
                    raise ValueError(
                        f"Shift date {shift_date} must be within schedule date range ({schedule_start} - {schedule_end})")

            # Validate shift times
            if "start_time" in shift_data and "end_time" in shift_data:
                start_time = shift_data["start_time"]
                end_time = shift_data["end_time"]

                # Simple format validation (HH:MM)
                if not re.match(r'^([01]\d|2[0-3]):([0-5]\d)$', start_time):
                    raise ValueError("Start time must be in HH:MM format (24-hour)")

                if not re.match(r'^([01]\d|2[0-3]):([0-5]\d)$', end_time):
                    raise ValueError("End time must be in HH:MM format (24-hour)")

                # Validate end time is after start time
                if end_time <= start_time:
                    raise ValueError("End time must be after start time")

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
            updated_schedule = await schedules_collection.find_one({"_id": schedule_obj_id})
            if not updated_schedule:
                print("Failed to retrieve updated schedule")
                return None

            # Format the updated schedule
            formatted_schedule = dict(updated_schedule)
            formatted_schedule["_id"] = schedule_id_str
            formatted_schedule["store_id"] = IdHandler.id_to_str(updated_schedule.get("store_id"))
            formatted_schedule["created_by"] = IdHandler.id_to_str(updated_schedule.get("created_by"))

            # Format shifts array
            if "shifts" in updated_schedule:
                formatted_shifts = []
                for shift in updated_schedule.get("shifts", []):
                    formatted_shift = dict(shift)
                    formatted_shift["_id"] = IdHandler.id_to_str(shift.get("_id"))
                    formatted_shift["employee_id"] = IdHandler.id_to_str(shift.get("employee_id"))
                    formatted_shifts.append(formatted_shift)
                formatted_schedule["shifts"] = formatted_shifts

            # Add store name
            store = await stores_collection.find_one({"_id": updated_schedule.get("store_id")})
            if store:
                formatted_schedule["store_name"] = store.get("name")

            # Get names of employees in shifts
            employee_names = {}
            if "shifts" in updated_schedule:
                for shift in updated_schedule.get("shifts", []):
                    emp_id = shift.get("employee_id")
                    if emp_id and IdHandler.id_to_str(emp_id) not in employee_names:
                        employee = await employees_collection.find_one({"_id": emp_id})
                        if employee and employee.get("user_id"):
                            from app.services.user import get_user_by_id
                            user = await get_user_by_id(employee.get("user_id"))
                            if user:
                                employee_names[IdHandler.id_to_str(emp_id)] = user.get("full_name")

            formatted_schedule["employee_names"] = employee_names

            return formatted_schedule
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
        Update a shift in a schedule with improved error handling and ID consistency
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

            schedule_id_str = IdHandler.id_to_str(schedule_obj_id)
            shift_id_str = IdHandler.id_to_str(shift_id)

            # Find the shift in the schedule
            shift_exists = False
            current_shift = None

            for shift in schedule.get("shifts", []):
                shift_in_schedule_id = IdHandler.id_to_str(shift.get("_id"))
                if shift_in_schedule_id == shift_id_str:
                    shift_exists = True
                    current_shift = shift
                    break

            if not shift_exists or not current_shift:
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

            # Validate shift dates fall within schedule dates if changing date
            if "date" in shift_data:
                schedule_start = schedule.get("start_date")
                schedule_end = schedule.get("end_date")
                shift_date = shift_data["date"]

                if shift_date < schedule_start or shift_date > schedule_end:
                    raise ValueError(
                        f"Shift date {shift_date} must be within schedule date range ({schedule_start} - {schedule_end})")

            # Validate shift times if changing times
            start_time = shift_data.get("start_time") or current_shift.get("start_time")
            end_time = shift_data.get("end_time") or current_shift.get("end_time")

            if "start_time" in shift_data:
                # Simple format validation (HH:MM)
                if not re.match(r'^([01]\d|2[0-3]):([0-5]\d)$', shift_data["start_time"]):
                    raise ValueError("Start time must be in HH:MM format (24-hour)")

            if "end_time" in shift_data:
                # Simple format validation (HH:MM)
                if not re.match(r'^([01]\d|2[0-3]):([0-5]\d)$', shift_data["end_time"]):
                    raise ValueError("End time must be in HH:MM format (24-hour)")

            # Validate end time is after start time
            if end_time <= start_time:
                raise ValueError("End time must be after start time")

            # Create a merge of current shift with updates
            merged_shift = {**current_shift}
            for key, value in shift_data.items():
                merged_shift[key] = value

            # Preserve the shift ID
            merged_shift["_id"] = shift_id_str

            # Update the schedule with the new shift data
            # This is a more reliable approach than the positional $ operator
            shifts = schedule.get("shifts", [])
            updated_shifts = []

            for shift in shifts:
                if IdHandler.id_to_str(shift.get("_id")) == shift_id_str:
                    updated_shifts.append(merged_shift)
                else:
                    updated_shifts.append(shift)

            # Update timestamp
            now = datetime.utcnow()

            # Update the whole schedule document
            update_result = await schedules_collection.update_one(
                {"_id": schedule_obj_id},
                {
                    "$set": {
                        "shifts": updated_shifts,
                        "updated_at": now
                    }
                }
            )

            if update_result.matched_count == 0:
                return None

            # Get the updated schedule
            updated_schedule = await schedules_collection.find_one({"_id": schedule_obj_id})
            if not updated_schedule:
                print("Failed to retrieve updated schedule")
                return None

            # Format for frontend consistency
            formatted_schedule = dict(updated_schedule)
            formatted_schedule["_id"] = schedule_id_str
            formatted_schedule["store_id"] = IdHandler.id_to_str(updated_schedule.get("store_id"))
            formatted_schedule["created_by"] = IdHandler.id_to_str(updated_schedule.get("created_by"))

            # Format shifts array
            if "shifts" in updated_schedule:
                formatted_shifts = []
                for shift in updated_schedule.get("shifts", []):
                    formatted_shift = dict(shift)
                    formatted_shift["_id"] = IdHandler.id_to_str(shift.get("_id"))
                    formatted_shift["employee_id"] = IdHandler.id_to_str(shift.get("employee_id"))
                    formatted_shifts.append(formatted_shift)
                formatted_schedule["shifts"] = formatted_shifts

            # Add store name
            store = await stores_collection.find_one({"_id": updated_schedule.get("store_id")})
            if store:
                formatted_schedule["store_name"] = store.get("name")

            # Get names of employees in shifts efficiently
            employee_names = {}
            if "shifts" in updated_schedule:
                employee_ids = set()
                for shift in updated_schedule.get("shifts", []):
                    emp_id = shift.get("employee_id")
                    if emp_id:
                        employee_ids.add(IdHandler.id_to_str(emp_id))

                for emp_id in employee_ids:
                    employee, _ = await IdHandler.find_document_by_id(
                        employees_collection,
                        emp_id,
                        not_found_msg=f"Employee not found for ID: {emp_id}"
                    )

                    if employee and employee.get("user_id"):
                        from app.services.user import get_user_by_id
                        user = await get_user_by_id(employee.get("user_id"))
                        if user:
                            employee_names[emp_id] = user.get("full_name")

            formatted_schedule["employee_names"] = employee_names

            return formatted_schedule
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
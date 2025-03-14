# app/services/schedule.py
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
from bson import ObjectId
from fastapi import HTTPException, status

from app.core.db import get_database, get_schedules_collection, get_employees_collection, get_stores_collection
from app.models.schedule import ScheduleModel, ShiftModel
from app.utils.id_handler import IdHandler  # Import IdHandler for ID management
from app.utils.datetime_handler import DateTimeHandler  # Import DateTimeHandler for date handling

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
            week_start_date: Optional[date] = None,
            include_details: bool = False
    ) -> List[Dict[str, Any]]:
        """Get schedules with optional filtering"""
        try:
            query = {}

            if store_id:
                query["store_id"] = store_id

            if week_start_date:
                # Convert date to datetime for MongoDB query
                week_start_datetime = datetime.combine(week_start_date, datetime.min.time())
                query["week_start_date"] = week_start_datetime

            # Get schedules from database
            schedules = await schedules_collection.find(query).skip(skip).limit(limit).to_list(length=limit)

            # Format schedules for API response
            result = []
            for schedule in schedules:
                schedule_with_info = dict(schedule)

                # Add shift_count field for ScheduleSummary
                if "shifts" in schedule:
                    schedule_with_info["shift_count"] = len(schedule["shifts"])
                else:
                    schedule_with_info["shift_count"] = 0

                # Get store info if requested
                if include_details and "store_id" in schedule:
                    store, _ = await IdHandler.find_document_by_id(
                        stores_collection,
                        schedule["store_id"],
                        not_found_msg=f"Store not found for ID: {schedule['store_id']}"
                    )

                    if store:
                        schedule_with_info["store_name"] = store["name"]

                # Get creator info if requested
                if include_details and "created_by" in schedule:
                    from app.services.user import get_user_by_id
                    creator = await get_user_by_id(schedule["created_by"])
                    if creator:
                        schedule_with_info["created_by_name"] = creator["full_name"]

                # Enrich shifts with employee names if requested
                if include_details and "shifts" in schedule:
                    enriched_shifts = []
                    for shift in schedule["shifts"]:
                        shift_with_info = dict(shift)
                        if "employee_id" in shift:
                            employee, _ = await IdHandler.find_document_by_id(
                                employees_collection,
                                shift["employee_id"],
                                not_found_msg=f"Employee not found for ID: {shift['employee_id']}"
                            )

                            if employee and "user_id" in employee:
                                from app.services.user import get_user_by_id
                                user = await get_user_by_id(employee["user_id"])
                                if user:
                                    shift_with_info["employee_name"] = user["full_name"]
                        enriched_shifts.append(shift_with_info)
                    schedule_with_info["shifts"] = enriched_shifts

                # Format all IDs consistently
                schedule_with_info = IdHandler.format_object_ids(schedule_with_info)
                result.append(schedule_with_info)

            return result
        except Exception as e:
            print(f"Error getting schedules: {str(e)}")
            return []

    @staticmethod
    async def get_schedule(schedule_id: str, include_details: bool = True) -> Optional[Dict[str, Any]]:
        """Get a schedule by ID using IdHandler"""
        try:
            # Find schedule using IdHandler
            schedule, _ = await IdHandler.find_document_by_id(
                schedules_collection,
                schedule_id,
                not_found_msg=f"Schedule with ID {schedule_id} not found"
            )

            if not schedule:
                return None

            # Format for API response
            schedule_with_info = dict(schedule)

            # Get store info if requested
            if include_details and "store_id" in schedule:
                store, _ = await IdHandler.find_document_by_id(
                    stores_collection,
                    schedule["store_id"],
                    not_found_msg=f"Store not found for ID: {schedule['store_id']}"
                )

                if store:
                    schedule_with_info["store_name"] = store["name"]

            # Get creator info if requested
            if include_details and "created_by" in schedule:
                from app.services.user import get_user_by_id
                creator = await get_user_by_id(schedule["created_by"])
                if creator:
                    schedule_with_info["created_by_name"] = creator["full_name"]

            # Enrich shifts with employee names if requested
            if include_details and "shifts" in schedule:
                enriched_shifts = []
                for shift in schedule["shifts"]:
                    shift_with_info = dict(shift)
                    if "employee_id" in shift:
                        employee, _ = await IdHandler.find_document_by_id(
                            employees_collection,
                            shift["employee_id"],
                            not_found_msg=f"Employee not found for ID: {shift['employee_id']}"
                        )

                        if employee and "user_id" in employee:
                            from app.services.user import get_user_by_id
                            user = await get_user_by_id(employee["user_id"])
                            if user:
                                shift_with_info["employee_name"] = user["full_name"]
                    enriched_shifts.append(shift_with_info)
                schedule_with_info["shifts"] = enriched_shifts

            # Format all IDs consistently
            return IdHandler.format_object_ids(schedule_with_info)
        except Exception as e:
            print(f"Error getting schedule: {str(e)}")
            return None

    @staticmethod
    async def create_schedule(schedule_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new schedule using IdHandler for ID management and DateTimeHandler for date handling"""
        try:
            # Validate required fields
            for field in ["store_id", "title", "week_start_date", "created_by"]:
                if field not in schedule_data:
                    raise ValueError(f"Missing required field: {field}")

            # Check if store exists using IdHandler
            store, store_obj_id = await IdHandler.find_document_by_id(
                stores_collection,
                schedule_data["store_id"],
                not_found_msg=f"Store with ID {schedule_data['store_id']} not found"
            )

            if not store:
                raise ValueError(f"Store with ID {schedule_data['store_id']} not found")

            # Store the standardized store_id
            schedule_data["store_id"] = IdHandler.id_to_str(store_obj_id)

            # Check if creator exists using IdHandler
            from app.services.user import get_user_by_id
            creator = await get_user_by_id(schedule_data["created_by"])
            if not creator:
                raise ValueError(f"Creator with ID {schedule_data['created_by']} not found")

            # Handle week_start_date (normalize to datetime for MongoDB storage)
            if isinstance(schedule_data["week_start_date"], str):
                # Parse date string
                week_start_date = DateTimeHandler.parse_date(schedule_data["week_start_date"])
                if not week_start_date:
                    raise ValueError(
                        f"Invalid week_start_date format: {schedule_data['week_start_date']}. Expected YYYY-MM-DD")

                schedule_data["week_start_date"] = week_start_date
            elif isinstance(schedule_data["week_start_date"], date) and not isinstance(schedule_data["week_start_date"],
                                                                                       datetime):
                # Convert date to datetime for MongoDB storage
                schedule_data["week_start_date"] = datetime.combine(schedule_data["week_start_date"],
                                                                    datetime.min.time())

            # Calculate week_end_date if not provided
            if "week_end_date" not in schedule_data:
                if isinstance(schedule_data["week_start_date"], datetime):
                    week_start = schedule_data["week_start_date"].date()
                else:
                    week_start = schedule_data["week_start_date"]

                week_end = week_start + timedelta(days=6)

                # Convert to datetime for MongoDB storage
                schedule_data["week_end_date"] = datetime.combine(week_end, datetime.min.time())
            elif isinstance(schedule_data["week_end_date"], date) and not isinstance(schedule_data["week_end_date"],
                                                                                     datetime):
                # Convert date to datetime for MongoDB storage
                schedule_data["week_end_date"] = datetime.combine(schedule_data["week_end_date"], datetime.min.time())

            # Check for existing schedule for the same week and store
            existing_schedule = await schedules_collection.find_one({
                "store_id": schedule_data["store_id"],
                "week_start_date": schedule_data["week_start_date"]
            })

            if existing_schedule:
                raise ValueError(
                    f"Schedule already exists for store {schedule_data['store_id']} for week starting {schedule_data['week_start_date']}")

            # Initialize empty shifts array if not provided
            if "shifts" not in schedule_data:
                schedule_data["shifts"] = []

            # Validate shifts if provided
            if schedule_data["shifts"]:
                validated_shifts = []
                for shift in schedule_data["shifts"]:
                    # Validate required shift fields
                    for field in ["employee_id", "day_of_week", "start_time", "end_time"]:
                        if field not in shift:
                            raise ValueError(f"Shift missing required field: {field}")

                    # Check if employee exists using IdHandler
                    employee, employee_obj_id = await IdHandler.find_document_by_id(
                        employees_collection,
                        shift["employee_id"],
                        not_found_msg=f"Employee with ID {shift['employee_id']} not found"
                    )

                    if not employee:
                        raise ValueError(f"Employee with ID {shift['employee_id']} not found")

                    # Store the standardized employee_id
                    shift["employee_id"] = IdHandler.id_to_str(employee_obj_id)

                    # Validate day_of_week
                    valid_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
                    day_lower = shift["day_of_week"].lower()
                    if day_lower not in valid_days:
                        raise ValueError(f"Invalid day of week: {shift['day_of_week']}. Must be one of {valid_days}")
                    shift["day_of_week"] = day_lower

                    # Validate start_time and end_time format (HH:MM)
                    for time_field in ["start_time", "end_time"]:
                        time_str = shift[time_field]
                        valid_time = DateTimeHandler.parse_time(time_str)
                        if not valid_time:
                            raise ValueError(f"Time must be in HH:MM format (24-hour): {time_str}")

                    # Validate end_time is after start_time
                    if shift["end_time"] <= shift["start_time"]:
                        raise ValueError("End time must be after start time")

                    # Generate an ID for the shift if not provided
                    if "_id" not in shift:
                        shift["_id"] = str(ObjectId())

                    validated_shifts.append(shift)

                schedule_data["shifts"] = validated_shifts

            # Add timestamps
            schedule_data["created_at"] = datetime.utcnow()
            schedule_data["updated_at"] = datetime.utcnow()

            # Insert into database
            result = await schedules_collection.insert_one(schedule_data)
            inserted_id = result.inserted_id

            # Get the created schedule using IdHandler
            created_schedule, _ = await IdHandler.find_document_by_id(
                schedules_collection,
                str(inserted_id),
                not_found_msg="Failed to retrieve created schedule"
            )

            if not created_schedule:
                raise ValueError("Failed to retrieve created schedule")

            # Format all IDs consistently
            return IdHandler.format_object_ids(created_schedule)
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
        """Update an existing schedule using IdHandler"""
        try:
            # Find schedule using IdHandler
            schedule, schedule_obj_id = await IdHandler.find_document_by_id(
                schedules_collection,
                schedule_id,
                not_found_msg=f"Schedule with ID {schedule_id} not found"
            )

            if not schedule:
                return None

            # Prepare update data
            update_data = {}

            # Handle basic fields
            if "title" in schedule_data:
                update_data["title"] = schedule_data["title"]

            # Handle shifts if provided
            if "shifts" in schedule_data:
                if schedule_data["shifts"] is None:
                    # Clear all shifts
                    update_data["shifts"] = []
                else:
                    # Validate and process each shift
                    validated_shifts = []
                    for shift in schedule_data["shifts"]:
                        # Validate required shift fields
                        for field in ["employee_id", "day_of_week", "start_time", "end_time"]:
                            if field not in shift:
                                raise ValueError(f"Shift missing required field: {field}")

                        # Check if employee exists using IdHandler
                        employee, employee_obj_id = await IdHandler.find_document_by_id(
                            employees_collection,
                            shift["employee_id"],
                            not_found_msg=f"Employee with ID {shift['employee_id']} not found"
                        )

                        if not employee:
                            raise ValueError(f"Employee with ID {shift['employee_id']} not found")

                        # Store the standardized employee_id
                        shift["employee_id"] = IdHandler.id_to_str(employee_obj_id)

                        # Validate day_of_week
                        valid_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
                        day_lower = shift["day_of_week"].lower()
                        if day_lower not in valid_days:
                            raise ValueError(
                                f"Invalid day of week: {shift['day_of_week']}. Must be one of {valid_days}")
                        shift["day_of_week"] = day_lower

                        # Validate start_time and end_time format (HH:MM)
                        for time_field in ["start_time", "end_time"]:
                            time_str = shift[time_field]
                            valid_time = DateTimeHandler.parse_time(time_str)
                            if not valid_time:
                                raise ValueError(f"Time must be in HH:MM format (24-hour): {time_str}")

                        # Validate end_time is after start_time
                        if shift["end_time"] <= shift["start_time"]:
                            raise ValueError("End time must be after start time")

                        # Generate an ID for the shift if not provided
                        if "_id" not in shift:
                            shift["_id"] = str(ObjectId())

                        validated_shifts.append(shift)

                    update_data["shifts"] = validated_shifts

            # Update timestamp
            update_data["updated_at"] = datetime.utcnow()

            # Update the schedule
            update_result = await schedules_collection.update_one(
                {"_id": schedule_obj_id},
                {"$set": update_data}
            )

            if update_result.matched_count == 0:
                return None

            # Get the updated schedule using IdHandler
            updated_schedule, _ = await IdHandler.find_document_by_id(
                schedules_collection,
                schedule_id,
                not_found_msg="Failed to retrieve updated schedule"
            )

            # Format all IDs consistently
            return IdHandler.format_object_ids(updated_schedule)
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
        """Delete a schedule using IdHandler"""
        try:
            # Find schedule using IdHandler
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
        """Add a shift to an existing schedule using IdHandler"""
        try:
            # Find schedule using IdHandler
            schedule, schedule_obj_id = await IdHandler.find_document_by_id(
                schedules_collection,
                schedule_id,
                not_found_msg=f"Schedule with ID {schedule_id} not found"
            )

            if not schedule:
                return None

            # Validate required shift fields
            for field in ["employee_id", "day_of_week", "start_time", "end_time"]:
                if field not in shift_data:
                    raise ValueError(f"Shift missing required field: {field}")

            # Check if employee exists using IdHandler
            employee, employee_obj_id = await IdHandler.find_document_by_id(
                employees_collection,
                shift_data["employee_id"],
                not_found_msg=f"Employee with ID {shift_data['employee_id']} not found"
            )

            if not employee:
                raise ValueError(f"Employee with ID {shift_data['employee_id']} not found")

            # Store the standardized employee_id
            shift_data["employee_id"] = IdHandler.id_to_str(employee_obj_id)

            # Validate day_of_week
            valid_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            day_lower = shift_data["day_of_week"].lower()
            if day_lower not in valid_days:
                raise ValueError(f"Invalid day of week: {shift_data['day_of_week']}. Must be one of {valid_days}")
            shift_data["day_of_week"] = day_lower

            # Validate start_time and end_time format (HH:MM)
            for time_field in ["start_time", "end_time"]:
                time_str = shift_data[time_field]
                valid_time = DateTimeHandler.parse_time(time_str)
                if not valid_time:
                    raise ValueError(f"Time must be in HH:MM format (24-hour): {time_str}")

            # Validate end_time is after start_time
            if shift_data["end_time"] <= shift_data["start_time"]:
                raise ValueError("End time must be after start time")

            # Generate an ID for the shift
            shift_data["_id"] = str(ObjectId())

            # Add the shift to the schedule
            update_result = await schedules_collection.update_one(
                {"_id": schedule_obj_id},
                {
                    "$push": {"shifts": shift_data},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )

            if update_result.matched_count == 0:
                return None

            # Get the updated schedule using IdHandler
            updated_schedule, _ = await IdHandler.find_document_by_id(
                schedules_collection,
                schedule_id,
                not_found_msg="Failed to retrieve updated schedule"
            )

            # Format all IDs consistently
            return IdHandler.format_object_ids(updated_schedule)
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
        """Update a shift in a schedule using IdHandler"""
        try:
            # Find schedule using IdHandler
            schedule, schedule_obj_id = await IdHandler.find_document_by_id(
                schedules_collection,
                schedule_id,
                not_found_msg=f"Schedule with ID {schedule_id} not found"
            )

            if not schedule:
                return None

            # Find the shift
            existing_shift = None
            for shift in schedule.get("shifts", []):
                if IdHandler.id_to_str(shift.get("_id")) == shift_id:
                    existing_shift = shift
                    break

            if not existing_shift:
                raise ValueError(f"Shift with ID {shift_id} not found in schedule {schedule_id}")

            # Validate and update shift fields
            updated_shift = dict(existing_shift)

            if "employee_id" in shift_data:
                # Check if employee exists using IdHandler
                employee, employee_obj_id = await IdHandler.find_document_by_id(
                    employees_collection,
                    shift_data["employee_id"],
                    not_found_msg=f"Employee with ID {shift_data['employee_id']} not found"
                )

                if not employee:
                    raise ValueError(f"Employee with ID {shift_data['employee_id']} not found")

                # Store the standardized employee_id
                updated_shift["employee_id"] = IdHandler.id_to_str(employee_obj_id)

            if "day_of_week" in shift_data:
                # Validate day_of_week
                valid_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
                day_lower = shift_data["day_of_week"].lower()
                if day_lower not in valid_days:
                    raise ValueError(f"Invalid day of week: {shift_data['day_of_week']}. Must be one of {valid_days}")

                updated_shift["day_of_week"] = day_lower

            for time_field in ["start_time", "end_time"]:
                if time_field in shift_data:
                    # Validate time format (HH:MM)
                    time_str = shift_data[time_field]
                    valid_time = DateTimeHandler.parse_time(time_str)
                    if not valid_time:
                        raise ValueError(f"Time must be in HH:MM format (24-hour): {time_str}")

                    updated_shift[time_field] = shift_data[time_field]

            # Validate end_time is after start_time
            if "start_time" in updated_shift and "end_time" in updated_shift:
                if updated_shift["end_time"] <= updated_shift["start_time"]:
                    raise ValueError("End time must be after start time")

            if "notes" in shift_data:
                updated_shift["notes"] = shift_data["notes"]

            # Update the shift in the schedule
            # We need to pull the existing shift and push the updated one
            update_result = await schedules_collection.update_one(
                {"_id": schedule_obj_id},
                {
                    "$pull": {"shifts": {"_id": shift_id}},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )

            if update_result.matched_count == 0:
                return None

            # Push the updated shift
            await schedules_collection.update_one(
                {"_id": schedule_obj_id},
                {
                    "$push": {"shifts": updated_shift},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )

            # Get the updated schedule using IdHandler
            updated_schedule, _ = await IdHandler.find_document_by_id(
                schedules_collection,
                schedule_id,
                not_found_msg="Failed to retrieve updated schedule"
            )

            # Format all IDs consistently
            return IdHandler.format_object_ids(updated_schedule)
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
        """Delete a shift from a schedule using IdHandler"""
        try:
            # Find schedule using IdHandler
            schedule, schedule_obj_id = await IdHandler.find_document_by_id(
                schedules_collection,
                schedule_id,
                not_found_msg=f"Schedule with ID {schedule_id} not found"
            )

            if not schedule:
                return None

            # Check if shift exists
            shift_exists = False
            for shift in schedule.get("shifts", []):
                if IdHandler.id_to_str(shift.get("_id")) == shift_id:
                    shift_exists = True
                    break

            if not shift_exists:
                raise ValueError(f"Shift with ID {shift_id} not found in schedule {schedule_id}")

            # Remove the shift from the schedule
            update_result = await schedules_collection.update_one(
                {"_id": schedule_obj_id},
                {
                    "$pull": {"shifts": {"_id": shift_id}},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )

            if update_result.matched_count == 0:
                return None

            # Get the updated schedule using IdHandler
            updated_schedule, _ = await IdHandler.find_document_by_id(
                schedules_collection,
                schedule_id,
                not_found_msg="Failed to retrieve updated schedule"
            )

            # Format all IDs consistently
            return IdHandler.format_object_ids(updated_schedule)
        except ValueError as e:
            print(f"Validation error deleting shift: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            print(f"Error deleting shift: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error deleting shift: {str(e)}"
            )

    @staticmethod
    async def get_employee_schedule(
            employee_id: str,
            week_start_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """Get all shifts for an employee using IdHandler"""
        try:
            # Validate employee exists using IdHandler
            employee, employee_obj_id = await IdHandler.find_document_by_id(
                employees_collection,
                employee_id,
                not_found_msg=f"Employee with ID {employee_id} not found"
            )

            if not employee:
                return []

            # Standardize employee ID
            employee_id_str = IdHandler.id_to_str(employee_obj_id)

            # Calculate current week's start date if not provided
            if not week_start_date:
                today = datetime.utcnow().date()
                days_since_monday = today.weekday()  # Monday is 0, Sunday is 6
                week_start_date = today - timedelta(days=days_since_monday)

            # Convert to datetime for MongoDB query
            week_start_datetime = datetime.combine(week_start_date, datetime.min.time())

            # Find all schedules that might contain this employee's shifts
            schedules = await schedules_collection.find({
                "week_start_date": week_start_datetime
            }).to_list(length=100)

            # Extract shifts for this employee
            employee_shifts = []
            for schedule in schedules:
                for shift in schedule.get("shifts", []):
                    if IdHandler.id_to_str(shift.get("employee_id")) == employee_id_str:
                        shift_info = dict(shift)
                        shift_info["schedule_id"] = IdHandler.id_to_str(schedule.get("_id"))
                        shift_info["schedule_title"] = schedule.get("title")
                        shift_info["store_id"] = IdHandler.id_to_str(schedule.get("store_id"))

                        store, _ = await IdHandler.find_document_by_id(
                            stores_collection,
                            schedule.get("store_id"),
                            not_found_msg=f"Store not found for ID: {schedule.get('store_id')}"
                        )

                        if store:
                            shift_info["store_name"] = store.get("name")

                        # Format all IDs consistently
                        shift_info = IdHandler.format_object_ids(shift_info)
                        employee_shifts.append(shift_info)

            return employee_shifts
        except Exception as e:
            print(f"Error getting employee schedule: {str(e)}")
            return []

    @staticmethod
    async def get_all_employee_schedules(
            employee_id: str,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None,
            skip: int = 0,
            limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get all schedules that contain shifts for a specific employee
        across all time periods or within an optional date range

        Args:
            employee_id: The ID of the employee
            start_date: Optional start date for filtering schedules
            end_date: Optional end date for filtering schedules
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return (for pagination)

        Returns:
            List of schedule objects containing the employee's shifts
        """
        try:
            # First, ensure we have a valid ObjectId for the employee
            try:
                # Convert the employee_id string to ObjectId
                employee_obj_id = ObjectId(employee_id)
            except Exception as e:
                print(f"Invalid employee ID format: {employee_id}, error: {str(e)}")
                return []

            # Create a query to find all schedules with shifts for this employee
            # We need to handle both string IDs and ObjectId formats in the database
            employee_id_str = str(employee_obj_id)  # String version

            # Build the base query
            query = {
                "shifts": {
                    "$elemMatch": {
                        "$or": [
                            {"employee_id": employee_id_str},  # Match string format
                            {"employee_id": employee_obj_id}  # Match ObjectId format
                        ]
                    }
                }
            }

            # Add date range filters if provided
            if start_date:
                start_datetime = datetime.combine(start_date, datetime.min.time())
                if "week_start_date" not in query:
                    query["week_start_date"] = {}
                query["week_start_date"]["$gte"] = start_datetime

            if end_date:
                end_datetime = datetime.combine(end_date, datetime.max.time())
                if "week_start_date" not in query:
                    query["week_start_date"] = {}
                query["week_start_date"]["$lte"] = end_datetime

            # Debug log to check the query
            print(f"Query for employee schedules: {query}")

            # Execute the query to find matching schedules
            schedules = await schedules_collection.find(query).sort("week_start_date", -1).skip(skip).limit(
                limit).to_list(length=limit)

            print(f"Found {len(schedules)} schedules for employee {employee_id}")

            # Process each schedule to include only shifts for this employee
            result = []
            for schedule in schedules:
                schedule_with_info = dict(schedule)

                # Filter shifts to include only those for this employee
                employee_shifts = []
                for shift in schedule.get("shifts", []):
                    shift_employee_id = shift.get("employee_id")

                    # Convert ObjectId to string if necessary
                    if isinstance(shift_employee_id, ObjectId):
                        shift_employee_id = str(shift_employee_id)

                    # Compare string representations to handle both ObjectId and string formats
                    if shift_employee_id == employee_id_str:
                        employee_shifts.append(shift)

                # Replace the full shifts list with only this employee's shifts
                schedule_with_info["shifts"] = employee_shifts
                schedule_with_info["shift_count"] = len(employee_shifts)

                # Get store info
                if "store_id" in schedule:
                    store, _ = await IdHandler.find_document_by_id(
                        stores_collection,
                        schedule["store_id"],
                        not_found_msg=f"Store not found for ID: {schedule['store_id']}"
                    )

                    if store:
                        schedule_with_info["store_name"] = store["name"]

                # Format IDs consistently
                schedule_with_info = IdHandler.format_object_ids(schedule_with_info)
                result.append(schedule_with_info)

            return result
        except Exception as e:
            print(f"Error getting all employee schedules: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
# app/services/timesheet.py
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
from bson import ObjectId
from fastapi import HTTPException, status

from app.core.db import get_database, get_timesheets_collection, get_employees_collection, get_stores_collection
from app.models.timesheet import TimesheetStatus
from app.utils.id_handler import IdHandler  # Import IdHandler for ID management
from app.utils.datetime_handler import DateTimeHandler  # Import DateTimeHandler for date handling

# Get database and collections
db = get_database()
timesheets_collection = get_timesheets_collection()
employees_collection = get_employees_collection()
stores_collection = get_stores_collection()


class TimesheetService:
    @staticmethod
    async def get_timesheets(
            skip: int = 0,
            limit: int = 100,
            employee_id: Optional[str] = None,
            store_id: Optional[str] = None,
            status: Optional[str] = None,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """Get timesheets with optional filtering"""
        try:
            query = {}

            if employee_id:
                query["employee_id"] = employee_id

            if store_id:
                query["store_id"] = store_id

            if status:
                query["status"] = status

            if start_date:
                # Convert date to datetime for MongoDB query
                start_datetime = datetime.combine(start_date, datetime.min.time())
                query["week_end_date"] = {"$gte": start_datetime}

            if end_date:
                # Convert date to datetime for MongoDB query
                end_datetime = datetime.combine(end_date, datetime.min.time())
                if "week_start_date" in query:
                    query["week_start_date"]["$lte"] = end_datetime
                else:
                    query["week_start_date"] = {"$lte": end_datetime}

            timesheets = await timesheets_collection.find(query).skip(skip).limit(limit).to_list(length=limit)

            # Enrich with employee and store names
            result = []
            for timesheet in timesheets:
                timesheet_with_info = dict(timesheet)

                # Get employee info if available
                if "employee_id" in timesheet:
                    employee, _ = await IdHandler.find_document_by_id(
                        employees_collection,
                        timesheet["employee_id"],
                        not_found_msg=f"Employee not found for ID: {timesheet['employee_id']}"
                    )

                    if employee and "user_id" in employee:
                        from app.services.user import get_user_by_id
                        user = await get_user_by_id(employee["user_id"])
                        if user:
                            timesheet_with_info["employee_name"] = user["full_name"]

                # Get store info if available
                if "store_id" in timesheet:
                    store, _ = await IdHandler.find_document_by_id(
                        stores_collection,
                        timesheet["store_id"],
                        not_found_msg=f"Store not found for ID: {timesheet['store_id']}"
                    )

                    if store:
                        timesheet_with_info["store_name"] = store["name"]

                # Format all IDs consistently
                timesheet_with_info = IdHandler.format_object_ids(timesheet_with_info)
                result.append(timesheet_with_info)

            return result
        except Exception as e:
            print(f"Error getting timesheets: {str(e)}")
            return []

    @staticmethod
    async def get_timesheet(timesheet_id: str) -> Optional[Dict[str, Any]]:
        """Get a timesheet by ID using IdHandler"""
        try:
            # Find timesheet using IdHandler
            timesheet, _ = await IdHandler.find_document_by_id(
                timesheets_collection,
                timesheet_id,
                not_found_msg=f"Timesheet with ID {timesheet_id} not found"
            )

            if not timesheet:
                return None

            timesheet_with_info = dict(timesheet)

            # Get employee info
            if "employee_id" in timesheet:
                employee, _ = await IdHandler.find_document_by_id(
                    employees_collection,
                    timesheet["employee_id"],
                    not_found_msg=f"Employee not found for ID: {timesheet['employee_id']}"
                )

                if employee and "user_id" in employee:
                    from app.services.user import get_user_by_id
                    user = await get_user_by_id(employee["user_id"])
                    if user:
                        timesheet_with_info["employee_name"] = user["full_name"]

            # Get store info
            if "store_id" in timesheet:
                store, _ = await IdHandler.find_document_by_id(
                    stores_collection,
                    timesheet["store_id"],
                    not_found_msg=f"Store not found for ID: {timesheet['store_id']}"
                )

                if store:
                    timesheet_with_info["store_name"] = store["name"]

            # Format all IDs consistently
            return IdHandler.format_object_ids(timesheet_with_info)
        except Exception as e:
            print(f"Error getting timesheet: {str(e)}")
            return None

    @staticmethod
    async def create_timesheet(timesheet_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new timesheet using IdHandler for ID management and DateTimeHandler for date handling"""
        try:
            # Validate required fields
            for field in ["employee_id", "store_id", "week_start_date", "hourly_rate"]:
                if field not in timesheet_data:
                    raise ValueError(f"Missing required field: {field}")

            # Check if employee exists using IdHandler
            employee, employee_obj_id = await IdHandler.find_document_by_id(
                employees_collection,
                timesheet_data["employee_id"],
                not_found_msg=f"Employee with ID {timesheet_data['employee_id']} not found"
            )

            if not employee:
                raise ValueError(f"Employee with ID {timesheet_data['employee_id']} not found")

            # Store the standardized employee_id
            timesheet_data["employee_id"] = IdHandler.id_to_str(employee_obj_id)

            # Check if store exists using IdHandler
            store, store_obj_id = await IdHandler.find_document_by_id(
                stores_collection,
                timesheet_data["store_id"],
                not_found_msg=f"Store with ID {timesheet_data['store_id']} not found"
            )

            if not store:
                raise ValueError(f"Store with ID {timesheet_data['store_id']} not found")

            # Store the standardized store_id
            timesheet_data["store_id"] = IdHandler.id_to_str(store_obj_id)

            # Handle week_start_date (normalize to datetime for MongoDB storage)
            if isinstance(timesheet_data["week_start_date"], str):
                # Parse date string
                week_start_date = DateTimeHandler.parse_date(timesheet_data["week_start_date"])
                if not week_start_date:
                    raise ValueError(
                        f"Invalid week_start_date format: {timesheet_data['week_start_date']}. Expected YYYY-MM-DD")

                timesheet_data["week_start_date"] = week_start_date
            elif isinstance(timesheet_data["week_start_date"], date) and not isinstance(
                    timesheet_data["week_start_date"], datetime):
                # Convert date to datetime for MongoDB storage
                timesheet_data["week_start_date"] = datetime.combine(timesheet_data["week_start_date"],
                                                                     datetime.min.time())

            # Calculate week_end_date if not provided
            if "week_end_date" not in timesheet_data:
                if isinstance(timesheet_data["week_start_date"], datetime):
                    week_start = timesheet_data["week_start_date"].date()
                else:
                    week_start = timesheet_data["week_start_date"]

                week_end = week_start + timedelta(days=6)

                # Convert to datetime for MongoDB storage
                timesheet_data["week_end_date"] = datetime.combine(week_end, datetime.min.time())
            elif isinstance(timesheet_data["week_end_date"], date) and not isinstance(timesheet_data["week_end_date"],
                                                                                      datetime):
                # Convert date to datetime for MongoDB storage
                timesheet_data["week_end_date"] = datetime.combine(timesheet_data["week_end_date"], datetime.min.time())

            # Check for existing timesheet for the same week and employee
            existing_timesheet = await timesheets_collection.find_one({
                "employee_id": timesheet_data["employee_id"],
                "week_start_date": timesheet_data["week_start_date"]
            })

            if existing_timesheet:
                raise ValueError(
                    f"Timesheet already exists for employee {timesheet_data['employee_id']} for week starting {timesheet_data['week_start_date']}")

            # Create a default daily_hours dictionary if not provided
            if "daily_hours" not in timesheet_data or not timesheet_data["daily_hours"]:
                timesheet_data["daily_hours"] = {
                    "monday": 0,
                    "tuesday": 0,
                    "wednesday": 0,
                    "thursday": 0,
                    "friday": 0,
                    "saturday": 0,
                    "sunday": 0
                }

            # Calculate total_hours and total_earnings
            total_hours = sum(timesheet_data["daily_hours"].values())
            total_earnings = total_hours * timesheet_data["hourly_rate"]

            timesheet_data["total_hours"] = total_hours
            timesheet_data["total_earnings"] = total_earnings
            timesheet_data["status"] = TimesheetStatus.DRAFT.value
            timesheet_data["created_at"] = datetime.utcnow()
            timesheet_data["updated_at"] = datetime.utcnow()

            # Insert into database
            result = await timesheets_collection.insert_one(timesheet_data)
            inserted_id = result.inserted_id

            # Get the created timesheet using IdHandler
            created_timesheet, _ = await IdHandler.find_document_by_id(
                timesheets_collection,
                str(inserted_id),
                not_found_msg="Failed to retrieve created timesheet"
            )

            if not created_timesheet:
                raise ValueError("Failed to retrieve created timesheet")

            # Return formatted timesheet
            return IdHandler.format_object_ids(created_timesheet)
        except ValueError as e:
            print(f"Validation error creating timesheet: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            print(f"Error creating timesheet: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating timesheet: {str(e)}"
            )

    @staticmethod
    async def update_timesheet(timesheet_id: str, timesheet_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing timesheet using IdHandler"""
        try:
            # Find timesheet using IdHandler
            timesheet, timesheet_obj_id = await IdHandler.find_document_by_id(
                timesheets_collection,
                timesheet_id,
                not_found_msg=f"Timesheet with ID {timesheet_id} not found"
            )

            if not timesheet:
                return None

            # Check if timesheet is in draft or rejected status
            current_status = timesheet["status"]
            if current_status not in [TimesheetStatus.DRAFT.value, TimesheetStatus.REJECTED.value]:
                raise ValueError(f"Cannot update timesheet in {current_status} status")

            # Update daily_hours if provided
            if "daily_hours" in timesheet_data:
                # Validate daily hours
                daily_hours = timesheet_data["daily_hours"]
                valid_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

                for day, hours in daily_hours.items():
                    if day not in valid_days:
                        raise ValueError(f"Invalid day: {day}")
                    if hours < 0:
                        raise ValueError(f"Hours cannot be negative for {day}")
                    if hours > 24:
                        raise ValueError(f"Hours cannot exceed 24 for {day}")

                # Merge with existing daily hours
                updated_daily_hours = timesheet["daily_hours"].copy()
                for day, hours in daily_hours.items():
                    updated_daily_hours[day] = hours

                # Recalculate total hours and earnings
                total_hours = sum(updated_daily_hours.values())
                hourly_rate = timesheet["hourly_rate"]
                total_earnings = total_hours * hourly_rate

                # Update the data
                timesheet_data["daily_hours"] = updated_daily_hours
                timesheet_data["total_hours"] = total_hours
                timesheet_data["total_earnings"] = total_earnings

            # Update timestamp
            timesheet_data["updated_at"] = datetime.utcnow()

            # Update the timesheet
            update_result = await timesheets_collection.update_one(
                {"_id": timesheet_obj_id},
                {"$set": timesheet_data}
            )

            if update_result.matched_count == 0:
                return None

            # Get the updated timesheet using IdHandler
            updated_timesheet, _ = await IdHandler.find_document_by_id(
                timesheets_collection,
                timesheet_id,
                not_found_msg=f"Failed to retrieve updated timesheet"
            )

            # Format all IDs consistently
            return IdHandler.format_object_ids(updated_timesheet)
        except ValueError as e:
            print(f"Validation error updating timesheet: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            print(f"Error updating timesheet: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error updating timesheet: {str(e)}"
            )

    @staticmethod
    async def update_daily_hours(timesheet_id: str, day: str, hours: float) -> Optional[Dict[str, Any]]:
        """Update hours for a specific day in a timesheet"""
        try:
            # Validate day
            valid_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            day_lower = day.lower()
            if day_lower not in valid_days:
                raise ValueError(f"Invalid day: {day}. Must be one of {valid_days}")

            # Validate hours
            if hours < 0:
                raise ValueError("Hours cannot be negative")
            if hours > 24:
                raise ValueError("Hours cannot exceed 24 per day")

            # Find timesheet using IdHandler
            timesheet, timesheet_obj_id = await IdHandler.find_document_by_id(
                timesheets_collection,
                timesheet_id,
                not_found_msg=f"Timesheet with ID {timesheet_id} not found"
            )

            if not timesheet:
                return None

            # Check if timesheet is in draft or rejected status
            current_status = timesheet["status"]
            if current_status not in [TimesheetStatus.DRAFT.value, TimesheetStatus.REJECTED.value]:
                raise ValueError(f"Cannot update timesheet in {current_status} status")

            # Update daily hours
            daily_hours = timesheet["daily_hours"].copy()
            daily_hours[day_lower] = hours

            # Recalculate total hours and earnings
            total_hours = sum(daily_hours.values())
            hourly_rate = timesheet["hourly_rate"]
            total_earnings = total_hours * hourly_rate

            # Update the timesheet
            update_result = await timesheets_collection.update_one(
                {"_id": timesheet_obj_id},
                {"$set": {
                    f"daily_hours.{day_lower}": hours,
                    "total_hours": total_hours,
                    "total_earnings": total_earnings,
                    "updated_at": datetime.utcnow()
                }}
            )

            if update_result.matched_count == 0:
                return None

            # Get the updated timesheet using IdHandler
            updated_timesheet, _ = await IdHandler.find_document_by_id(
                timesheets_collection,
                timesheet_id,
                not_found_msg=f"Failed to retrieve updated timesheet"
            )

            # Format all IDs consistently
            return IdHandler.format_object_ids(updated_timesheet)
        except ValueError as e:
            print(f"Validation error updating daily hours: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            print(f"Error updating daily hours: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error updating daily hours: {str(e)}"
            )

    @staticmethod
    async def submit_timesheet(timesheet_id: str, notes: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Submit a timesheet for approval"""
        try:
            # Find timesheet using IdHandler
            timesheet, timesheet_obj_id = await IdHandler.find_document_by_id(
                timesheets_collection,
                timesheet_id,
                not_found_msg=f"Timesheet with ID {timesheet_id} not found"
            )

            if not timesheet:
                return None

            # Check if timesheet is in draft or rejected status
            current_status = timesheet["status"]
            if current_status not in [TimesheetStatus.DRAFT.value, TimesheetStatus.REJECTED.value]:
                raise ValueError(f"Cannot submit timesheet in {current_status} status")

            # Update data
            update_data = {
                "status": TimesheetStatus.SUBMITTED.value,
                "submitted_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }

            if notes:
                update_data["notes"] = notes

            # Update the timesheet
            update_result = await timesheets_collection.update_one(
                {"_id": timesheet_obj_id},
                {"$set": update_data}
            )

            if update_result.matched_count == 0:
                return None

            # Get the updated timesheet using IdHandler
            updated_timesheet, _ = await IdHandler.find_document_by_id(
                timesheets_collection,
                timesheet_id,
                not_found_msg=f"Failed to retrieve updated timesheet"
            )

            # Format all IDs consistently
            return IdHandler.format_object_ids(updated_timesheet)
        except ValueError as e:
            print(f"Validation error submitting timesheet: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            print(f"Error submitting timesheet: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error submitting timesheet: {str(e)}"
            )

    @staticmethod
    async def approve_timesheet(
            timesheet_id: str,
            approver_id: str,
            status: str,
            notes: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Approve or reject a timesheet"""
        try:
            # Validate status
            if status not in ["approved", "rejected"]:
                raise ValueError("Status must be either 'approved' or 'rejected'")

            # Find timesheet using IdHandler
            timesheet, timesheet_obj_id = await IdHandler.find_document_by_id(
                timesheets_collection,
                timesheet_id,
                not_found_msg=f"Timesheet with ID {timesheet_id} not found"
            )

            if not timesheet:
                return None

            # Check if timesheet is in submitted status
            current_status = timesheet["status"]
            if current_status != TimesheetStatus.SUBMITTED.value:
                raise ValueError(f"Cannot approve/reject timesheet in {current_status} status")

            # Validate approver exists using IdHandler
            from app.services.user import get_user_by_id
            approver = await get_user_by_id(approver_id)
            if not approver:
                raise ValueError(f"Approver with ID {approver_id} not found")

            # Update data
            update_data = {
                "status": status,
                "approved_by": approver_id,
                "approved_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }

            if notes:
                if status == "rejected":
                    update_data["rejection_reason"] = notes
                else:
                    update_data["notes"] = notes

            # Update the timesheet
            update_result = await timesheets_collection.update_one(
                {"_id": timesheet_obj_id},
                {"$set": update_data}
            )

            if update_result.matched_count == 0:
                return None

            # Get the updated timesheet using IdHandler
            updated_timesheet, _ = await IdHandler.find_document_by_id(
                timesheets_collection,
                timesheet_id,
                not_found_msg=f"Failed to retrieve updated timesheet"
            )

            # Format all IDs consistently
            return IdHandler.format_object_ids(updated_timesheet)
        except ValueError as e:
            print(f"Validation error approving timesheet: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            print(f"Error approving timesheet: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error approving timesheet: {str(e)}"
            )

    @staticmethod
    async def delete_timesheet(timesheet_id: str) -> bool:
        """Delete a timesheet"""
        try:
            # Find timesheet using IdHandler
            timesheet, timesheet_obj_id = await IdHandler.find_document_by_id(
                timesheets_collection,
                timesheet_id,
                not_found_msg=f"Timesheet with ID {timesheet_id} not found"
            )

            if not timesheet:
                return False

            # Check if timesheet is in draft or rejected status
            current_status = timesheet["status"]
            if current_status not in [TimesheetStatus.DRAFT.value, TimesheetStatus.REJECTED.value]:
                raise ValueError(f"Cannot delete timesheet in {current_status} status")

            # Delete the timesheet
            delete_result = await timesheets_collection.delete_one({"_id": timesheet_obj_id})

            return delete_result.deleted_count > 0
        except ValueError as e:
            print(f"Validation error deleting timesheet: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            print(f"Error deleting timesheet: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error deleting timesheet: {str(e)}"
            )

    @staticmethod
    async def get_current_week_timesheet(employee_id: str) -> Optional[Dict[str, Any]]:
        """Get the current week's timesheet for an employee"""
        try:
            # Calculate current week's start date (Monday)
            today = datetime.utcnow().date()
            days_since_monday = today.weekday()  # Monday is 0, Sunday is 6
            week_start = today - timedelta(days=days_since_monday)

            # Convert to datetime for MongoDB query
            week_start_datetime = datetime.combine(week_start, datetime.min.time())

            # Find timesheet for current week
            timesheet = await timesheets_collection.find_one({
                "employee_id": employee_id,
                "week_start_date": week_start_datetime
            })

            if not timesheet:
                return None

            # Format the timesheet
            return IdHandler.format_object_ids(timesheet)
        except Exception as e:
            print(f"Error getting current week timesheet: {str(e)}")
            return None

    @staticmethod
    async def create_or_get_current_timesheet(employee_id: str, store_id: str) -> Dict[str, Any]:
        """Create a new timesheet for the current week or get existing one"""
        try:
            # Calculate current week's start date (Monday)
            today = datetime.utcnow().date()
            days_since_monday = today.weekday()  # Monday is 0, Sunday is 6
            week_start = today - timedelta(days=days_since_monday)
            week_end = week_start + timedelta(days=6)

            # Convert to datetime for MongoDB storage
            week_start_datetime = datetime.combine(week_start, datetime.min.time())

            # Check if timesheet already exists
            existing_timesheet = await timesheets_collection.find_one({
                "employee_id": employee_id,
                "week_start_date": week_start_datetime
            })

            if existing_timesheet:
                return IdHandler.format_object_ids(existing_timesheet)

            # Get the employee information using IdHandler
            employee, _ = await IdHandler.find_document_by_id(
                employees_collection,
                employee_id,
                not_found_msg=f"Employee with ID {employee_id} not found"
            )

            if not employee:
                raise ValueError(f"Employee with ID {employee_id} not found")

            hourly_rate = employee.get("hourly_rate", 0)

            # Create a new timesheet
            timesheet_data = {
                "employee_id": employee_id,
                "store_id": store_id,
                "week_start_date": week_start_datetime,
                "week_end_date": datetime.combine(week_end, datetime.min.time()),
                "hourly_rate": hourly_rate,
                "daily_hours": {
                    "monday": 0,
                    "tuesday": 0,
                    "wednesday": 0,
                    "thursday": 0,
                    "friday": 0,
                    "saturday": 0,
                    "sunday": 0
                },
                "total_hours": 0,
                "total_earnings": 0,
                "status": TimesheetStatus.DRAFT.value,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }

            result = await timesheets_collection.insert_one(timesheet_data)

            # Get the created timesheet using IdHandler
            created_timesheet, _ = await IdHandler.find_document_by_id(
                timesheets_collection,
                str(result.inserted_id),
                not_found_msg="Failed to retrieve created timesheet"
            )

            # Format all IDs consistently
            return IdHandler.format_object_ids(created_timesheet)
        except ValueError as e:
            print(f"Validation error creating current timesheet: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            print(f"Error creating current timesheet: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating current timesheet: {str(e)}"
            )
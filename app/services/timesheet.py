# app/services/timesheet.py
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from bson import ObjectId
from fastapi import HTTPException, status

from app.core.db import get_database, get_timesheets_collection, get_employees_collection, get_stores_collection, \
    get_hours_collection
from app.models.timesheet import TimesheetStatus
from app.utils.formatting import format_object_ids, ensure_object_id
from app.utils.id_handler import IdHandler

# Get database and collections
db = get_database()
timesheets_collection = get_timesheets_collection()
employees_collection = get_employees_collection()
stores_collection = get_stores_collection()
hours_collection = get_hours_collection()


class TimesheetService:
    @staticmethod
    async def get_timesheets(
            skip: int = 0,
            limit: int = 100,
            employee_id: Optional[str] = None,
            store_id: Optional[str] = None,
            status: Optional[str] = None,
            start_date: Optional[str] = None,
            end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all timesheets with optional filtering
        """
        try:
            query = {}

            if employee_id:
                # Try with both string and ObjectId formats for maximum compatibility
                employee_obj_id = ensure_object_id(employee_id)
                if employee_obj_id:
                    # Use $or to try both formats
                    query["$or"] = [
                        {"employee_id": employee_obj_id},
                        {"employee_id": employee_id}
                    ]
                else:
                    query["employee_id"] = employee_id

            if store_id:
                # Try with both string and ObjectId formats for maximum compatibility
                store_obj_id = ensure_object_id(store_id)
                if store_obj_id:
                    # Use $or to try both formats if there's already an $or
                    if "$or" in query:
                        # We need to use $and to combine multiple $or clauses
                        query = {
                            "$and": [
                                {"$or": query["$or"]},
                                {"$or": [
                                    {"store_id": store_obj_id},
                                    {"store_id": store_id}
                                ]}
                            ]
                        }
                    else:
                        query["$or"] = [
                            {"store_id": store_obj_id},
                            {"store_id": store_id}
                        ]
                else:
                    query["store_id"] = store_id

            if status:
                query["status"] = status

            if start_date:
                query["week_start_date"] = {"$gte": start_date}

            if end_date:
                if "week_start_date" in query:
                    query["week_start_date"]["$lte"] = end_date
                else:
                    query["week_start_date"] = {"$lte": end_date}

            print(f"Timesheet query: {query}")
            timesheets = await timesheets_collection.find(query).skip(skip).limit(limit).to_list(length=limit)
            print(f"Found {len(timesheets)} timesheets")

            # Enrich timesheet data with employee and store info
            result = []
            for timesheet in timesheets:
                timesheet_with_info = dict(timesheet)

                # Add employee info
                if timesheet.get("employee_id"):
                    employee = await employees_collection.find_one({"_id": timesheet.get("employee_id")})
                    if employee and employee.get("user_id"):
                        from app.services.user import get_user_by_id
                        user = await get_user_by_id(employee.get("user_id"))
                        if user:
                            timesheet_with_info["employee_name"] = user.get("full_name")

                # Add store info
                if timesheet.get("store_id"):
                    store = await stores_collection.find_one({"_id": timesheet.get("store_id")})
                    if store:
                        timesheet_with_info["store_name"] = store.get("name")

                # Get time entry details if requested
                if timesheet.get("time_entries"):
                    time_entry_details = []
                    for entry_id in timesheet.get("time_entries"):
                        entry = await hours_collection.find_one({"_id": entry_id})
                        if entry:
                            time_entry_details.append(format_object_ids(entry))

                    if time_entry_details:
                        timesheet_with_info["time_entry_details"] = time_entry_details

                result.append(timesheet_with_info)

            return format_object_ids(result)
        except Exception as e:
            print(f"Error getting timesheets: {str(e)}")
            return []

    @staticmethod
    async def get_timesheet(timesheet_id: str) -> Optional[Dict[str, Any]]:
        """
        Get timesheet by ID using the centralized ID handler
        """
        try:
            print(f"Looking up timesheet with ID: {timesheet_id}")

            # Use centralized method for consistent lookup
            timesheet, _ = await IdHandler.find_document_by_id(
                timesheets_collection,
                timesheet_id,
                not_found_msg=f"Timesheet with ID {timesheet_id} not found"
            )

            if not timesheet:
                print(f"Timesheet not found with ID: {timesheet_id}")
                return None

            # Enrich timesheet data with employee and store info
            timesheet_with_info = dict(timesheet)

            # Add employee info
            if timesheet.get("employee_id"):
                employee = await employees_collection.find_one({"_id": timesheet.get("employee_id")})
                if employee and employee.get("user_id"):
                    from app.services.user import get_user_by_id
                    user = await get_user_by_id(employee.get("user_id"))
                    if user:
                        timesheet_with_info["employee_name"] = user.get("full_name")

            # Add store info
            if timesheet.get("store_id"):
                store = await stores_collection.find_one({"_id": timesheet.get("store_id")})
                if store:
                    timesheet_with_info["store_name"] = store.get("name")

            # Get time entry details
            if timesheet.get("time_entries"):
                time_entry_details = []
                for entry_id in timesheet.get("time_entries"):
                    entry_obj_id = ensure_object_id(entry_id)
                    if entry_obj_id:
                        entry = await hours_collection.find_one({"_id": entry_obj_id})
                    else:
                        entry = await hours_collection.find_one({"_id": entry_id})

                    if not entry:
                        # Try string comparison
                        all_entries = await hours_collection.find().to_list(length=500)
                        for e in all_entries:
                            if str(e.get("_id")) == entry_id:
                                entry = e
                                break

                    if entry:
                        time_entry_details.append(format_object_ids(entry))

                if time_entry_details:
                    timesheet_with_info["time_entry_details"] = time_entry_details

            return IdHandler.format_object_ids(timesheet_with_info)
        except Exception as e:
            print(f"Error getting timesheet: {str(e)}")
            return None

    @staticmethod
    async def update_timesheet(timesheet_id: str, timesheet_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update an existing timesheet
        """
        try:
            print(f"Updating timesheet with ID: {timesheet_id}")

            # Find the timesheet
            timesheet, timesheet_obj_id = await IdHandler.find_document_by_id(
                timesheets_collection,
                timesheet_id,
                not_found_msg=f"Timesheet with ID {timesheet_id} not found"
            )

            if not timesheet:
                return None

            # Check if timesheet is in a state that can be updated
            current_status = timesheet.get("status")
            if current_status not in [TimesheetStatus.DRAFT.value, TimesheetStatus.REJECTED.value]:
                if "status" not in timesheet_data or timesheet_data["status"] != current_status:
                    raise ValueError(f"Cannot update timesheet in {current_status} status unless approving/rejecting")

            # Validate time entries if updating them
            if "time_entries" in timesheet_data and timesheet_data["time_entries"]:
                validated_entries = []
                for entry_id in timesheet_data["time_entries"]:
                    entry_obj_id = ensure_object_id(entry_id)
                    if entry_obj_id:
                        entry = await hours_collection.find_one({"_id": entry_obj_id})
                    else:
                        entry = await hours_collection.find_one({"_id": entry_id})

                    if not entry:
                        # Try string comparison
                        all_entries = await hours_collection.find().to_list(length=500)
                        for e in all_entries:
                            if str(e.get("_id")) == entry_id:
                                entry = e
                                break

                    if entry:
                        validated_entries.append(str(entry["_id"]))
                    else:
                        print(f"Warning: Time entry with ID {entry_id} not found")

                timesheet_data["time_entries"] = validated_entries

            # Update timestamp
            timesheet_data["updated_at"] = datetime.utcnow()

            # Update the timesheet
            update_result = await timesheets_collection.update_one(
                {"_id": timesheet_obj_id},
                {"$set": timesheet_data}
            )

            if update_result.matched_count == 0:
                return None

            # Get the updated timesheet
            updated_timesheet = await TimesheetService.get_timesheet(timesheet_id)
            return updated_timesheet
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
    async def delete_timesheet(timesheet_id: str) -> bool:
        """
        Delete a timesheet
        """
        try:
            print(f"Deleting timesheet with ID: {timesheet_id}")

            # Find the timesheet
            timesheet, timesheet_obj_id = await IdHandler.find_document_by_id(
                timesheets_collection,
                timesheet_id,
                not_found_msg=f"Timesheet with ID {timesheet_id} not found"
            )

            if not timesheet:
                return False

            # Only allow deletion of draft or rejected timesheets
            current_status = timesheet.get("status")
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
    async def submit_timesheet(timesheet_id: str, notes: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Submit a timesheet for approval
        """
        try:
            print(f"Submitting timesheet with ID: {timesheet_id}")

            # Find the timesheet
            timesheet, timesheet_obj_id = await IdHandler.find_document_by_id(
                timesheets_collection,
                timesheet_id,
                not_found_msg=f"Timesheet with ID {timesheet_id} not found"
            )

            if not timesheet:
                return None

            # Check if timesheet is in draft status
            current_status = timesheet.get("status")
            if current_status != TimesheetStatus.DRAFT.value:
                raise ValueError(f"Cannot submit timesheet in {current_status} status")

            # Update the timesheet
            update_data = {
                "status": TimesheetStatus.SUBMITTED.value,
                "submitted_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }

            if notes:
                update_data["notes"] = notes

            update_result = await timesheets_collection.update_one(
                {"_id": timesheet_obj_id},
                {"$set": update_data}
            )

            if update_result.matched_count == 0:
                return None

            # Get the updated timesheet
            updated_timesheet = await TimesheetService.get_timesheet(timesheet_id)
            return updated_timesheet
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
            approval_status: TimesheetStatus,
            notes: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Approve or reject a timesheet
        """
        try:
            print(f"Processing {approval_status.value} for timesheet with ID: {timesheet_id}")

            # Validate approval status
            if approval_status not in [TimesheetStatus.APPROVED, TimesheetStatus.REJECTED]:
                raise ValueError("Approval status must be either approved or rejected")

            # Find the timesheet
            timesheet, timesheet_obj_id = await IdHandler.find_document_by_id(
                timesheets_collection,
                timesheet_id,
                not_found_msg=f"Timesheet with ID {timesheet_id} not found"
            )

            if not timesheet:
                return None

            # Check if timesheet is in submitted status
            current_status = timesheet.get("status")
            if current_status != TimesheetStatus.SUBMITTED.value:
                raise ValueError(f"Cannot approve/reject timesheet in {current_status} status")

            # Validate approver exists
            from app.services.user import get_user_by_id
            approver = await get_user_by_id(approver_id)
            if not approver:
                raise ValueError(f"Approver with ID {approver_id} not found")

            # Update the timesheet
            update_data = {
                "status": approval_status.value,
                "approved_by": str(approver["_id"]),
                "approved_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }

            if notes:
                if approval_status == TimesheetStatus.REJECTED:
                    update_data["rejection_reason"] = notes
                else:
                    update_data["notes"] = notes

            update_result = await timesheets_collection.update_one(
                {"_id": timesheet_obj_id},
                {"$set": update_data}
            )

            if update_result.matched_count == 0:
                return None

            # Get the updated timesheet
            updated_timesheet = await TimesheetService.get_timesheet(timesheet_id)
            return updated_timesheet
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
    async def add_time_entry(timesheet_id: str, time_entry_id: str) -> Optional[Dict[str, Any]]:
        """
        Add a time entry to a timesheet
        """
        try:
            print(f"Adding time entry {time_entry_id} to timesheet {timesheet_id}")

            # Find the timesheet
            timesheet, timesheet_obj_id = await IdHandler.find_document_by_id(
                timesheets_collection,
                timesheet_id,
                not_found_msg=f"Timesheet with ID {timesheet_id} not found"
            )

            if not timesheet:
                return None

            # Check if timesheet is in draft or rejected status
            current_status = timesheet.get("status")
            if current_status not in [TimesheetStatus.DRAFT.value, TimesheetStatus.REJECTED.value]:
                raise ValueError(f"Cannot add time entries to timesheet in {current_status} status")

            # Validate time entry exists
            entry_obj_id = ensure_object_id(time_entry_id)
            entry = None

            if entry_obj_id:
                entry = await hours_collection.find_one({"_id": entry_obj_id})
            else:
                entry = await hours_collection.find_one({"_id": time_entry_id})

            if not entry:
                # Try string comparison
                all_entries = await hours_collection.find().to_list(length=500)
                for e in all_entries:
                    if str(e.get("_id")) == time_entry_id:
                        entry = e
                        break

            if not entry:
                raise ValueError(f"Time entry with ID {time_entry_id} not found")

            # Check if time entry already exists in timesheet
            if "time_entries" in timesheet:
                for existing_entry in timesheet["time_entries"]:
                    if str(existing_entry) == str(entry["_id"]):
                        print(f"Time entry {time_entry_id} already exists in timesheet {timesheet_id}")
                        return await TimesheetService.get_timesheet(timesheet_id)

            # Calculate new total hours including this entry
            total_hours = timesheet.get("total_hours", 0)

            if entry.get("total_minutes"):
                # Convert minutes to hours
                entry_hours = entry["total_minutes"] / 60
                total_hours += entry_hours

            # Update the timesheet
            update_data = {
                "updated_at": datetime.utcnow(),
                "total_hours": total_hours
            }

            update_result = await timesheets_collection.update_one(
                {"_id": timesheet_obj_id},
                {
                    "$set": update_data,
                    "$push": {"time_entries": str(entry["_id"])}
                }
            )

            if update_result.matched_count == 0:
                return None

            # Get the updated timesheet
            updated_timesheet = await TimesheetService.get_timesheet(timesheet_id)
            return updated_timesheet
        except ValueError as e:
            print(f"Validation error adding time entry: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            print(f"Error adding time entry: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error adding time entry: {str(e)}"
            )

    @staticmethod
    async def remove_time_entry(timesheet_id: str, time_entry_id: str) -> Optional[Dict[str, Any]]:
        """
        Remove a time entry from a timesheet
        """
        try:
            print(f"Removing time entry {time_entry_id} from timesheet {timesheet_id}")

            # Find the timesheet
            timesheet, timesheet_obj_id = await IdHandler.find_document_by_id(
                timesheets_collection,
                timesheet_id,
                not_found_msg=f"Timesheet with ID {timesheet_id} not found"
            )

            if not timesheet:
                return None

            # Check if timesheet is in draft or rejected status
            current_status = timesheet.get("status")
            if current_status not in [TimesheetStatus.DRAFT.value, TimesheetStatus.REJECTED.value]:
                raise ValueError(f"Cannot remove time entries from timesheet in {current_status} status")

            # Find the time entry
            entry_obj_id = ensure_object_id(time_entry_id)
            entry = None

            if entry_obj_id:
                entry = await hours_collection.find_one({"_id": entry_obj_id})
            else:
                entry = await hours_collection.find_one({"_id": time_entry_id})

            if not entry:
                # Try string comparison
                all_entries = await hours_collection.find().to_list(length=500)
                for e in all_entries:
                    if str(e.get("_id")) == time_entry_id:
                        entry = e
                        break

            # Recalculate total hours
            total_hours = timesheet.get("total_hours", 0)

            if entry and entry.get("total_minutes"):
                # Convert minutes to hours and subtract
                entry_hours = entry["total_minutes"] / 60
                total_hours -= entry_hours

            # Update the timesheet
            update_data = {
                "updated_at": datetime.utcnow(),
                "total_hours": max(0, total_hours)  # Ensure we don't go negative
            }

            update_result = await timesheets_collection.update_one(
                {"_id": timesheet_obj_id},
                {
                    "$set": update_data,
                    "$pull": {"time_entries": time_entry_id}
                }
            )

            if update_result.matched_count == 0:
                return None

            # Get the updated timesheet
            updated_timesheet = await TimesheetService.get_timesheet(timesheet_id)
            return updated_timesheet
        except ValueError as e:
            print(f"Validation error removing time entry: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            print(f"Error removing time entry: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error removing time entry: {str(e)}"
            )

    @staticmethod
    async def generate_timesheet_from_hours(
            employee_id: str,
            store_id: str,
            week_start_date: str,
            week_end_date: str
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a timesheet from hours records in the specified date range
        """
        try:
            print(f"Generating timesheet for employee {employee_id} from {week_start_date} to {week_end_date}")

            # Validate employee exists
            from app.services.employee import EmployeeService
            employee = await EmployeeService.get_employee(employee_id)
            if not employee:
                raise ValueError(f"Employee with ID {employee_id} not found")

            # Validate store exists
            from app.services.store import StoreService
            store = await StoreService.get_store(store_id)
            if not store:
                raise ValueError(f"Store with ID {store_id} not found")

            # Convert date strings to datetime objects for query
            try:
                start_date = datetime.fromisoformat(week_start_date)
                end_date = datetime.fromisoformat(week_end_date)
            except ValueError:
                raise ValueError("Invalid date format. Use ISO format (YYYY-MM-DD)")

            # Check if a timesheet already exists for this period
            existing_timesheet = await timesheets_collection.find_one({
                "employee_id": employee_id,
                "week_start_date": week_start_date,
                "week_end_date": week_end_date
            })

            if existing_timesheet:
                return await TimesheetService.get_timesheet(str(existing_timesheet["_id"]))

            # Find all hours records for this employee in the date range
            employee_obj_id = ensure_object_id(employee_id)
            query = {
                "clock_in": {
                    "$gte": start_date,
                    "$lte": end_date
                }
            }

            if employee_obj_id:
                query["employee_id"] = employee_obj_id
            else:
                query["employee_id"] = employee_id

            hours_records = await hours_collection.find(query).to_list(length=100)

            if not hours_records:
                raise ValueError(f"No hours records found for employee {employee_id} in the specified date range")

            # Calculate total hours
            total_hours = 0
            time_entries = []

            for record in hours_records:
                if record.get("total_minutes"):
                    total_hours += record["total_minutes"] / 60
                    time_entries.append(str(record["_id"]))

            # Create timesheet
            timesheet_data = {
                "employee_id": employee_id,
                "store_id": store_id,
                "week_start_date": week_start_date,
                "week_end_date": week_end_date,
                "time_entries": time_entries,
                "total_hours": total_hours,
                "status": TimesheetStatus.DRAFT.value,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }

            result = await timesheets_collection.insert_one(timesheet_data)

            # Get the created timesheet
            if result.inserted_id:
                created_timesheet = await TimesheetService.get_timesheet(str(result.inserted_id))
                if created_timesheet:
                    return created_timesheet

            raise ValueError("Failed to create timesheet")
        except ValueError as e:
            print(f"Validation error generating timesheet: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            print(f"Error generating timesheet: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error generating timesheet: {str(e)}"
            )

    @staticmethod
    async def get_employee_current_timesheet(employee_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current timesheet for an employee
        """
        try:
            # Calculate current week boundaries
            now = datetime.utcnow()
            # Assuming weeks start on Monday
            today = now.date()
            start_of_week = today - timedelta(days=today.weekday())
            end_of_week = start_of_week + timedelta(days=6)

            # Format dates as strings
            week_start_date = start_of_week.isoformat()
            week_end_date = end_of_week.isoformat()

            print(f"Looking for timesheet for employee {employee_id} for week {week_start_date} to {week_end_date}")

            # Try both string and ObjectId for lookup
            employee_obj_id = ensure_object_id(employee_id)
            query = {
                "week_start_date": week_start_date,
                "week_end_date": week_end_date
            }

            if employee_obj_id:
                query["$or"] = [
                    {"employee_id": employee_obj_id},
                    {"employee_id": employee_id}
                ]
            else:
                query["employee_id"] = employee_id

            timesheet = await timesheets_collection.find_one(query)

            if timesheet:
                return await TimesheetService.get_timesheet(str(timesheet["_id"]))

            # If no timesheet exists for the current week, return None
            return None
        except Exception as e:
            print(f"Error getting employee current timesheet: {str(e)}")
            return None

    @staticmethod
    async def create_timesheet(timesheet_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new timesheet
        """
        try:
            print(f"Creating timesheet: {timesheet_data}")

            # Validate employee exists
            if "employee_id" in timesheet_data:
                from app.services.employee import EmployeeService
                employee = await EmployeeService.get_employee(timesheet_data["employee_id"])
                if not employee:
                    raise ValueError(f"Employee with ID {timesheet_data['employee_id']} not found")

            # Validate store exists
            if "store_id" in timesheet_data:
                from app.services.store import StoreService
                store = await StoreService.get_store(timesheet_data["store_id"])
                if not store:
                    raise ValueError(f"Store with ID {timesheet_data['store_id']} not found")

            # Set default status if not provided
            if "status" not in timesheet_data:
                timesheet_data["status"] = TimesheetStatus.DRAFT.value

            # Validate time entries if provided
            if "time_entries" in timesheet_data and timesheet_data["time_entries"]:
                validated_entries = []
                for entry_id in timesheet_data["time_entries"]:
                    entry_obj_id = ensure_object_id(entry_id)
                    if entry_obj_id:
                        entry = await hours_collection.find_one({"_id": entry_obj_id})
                    else:
                        entry = await hours_collection.find_one({"_id": entry_id})

                    if not entry:
                        # Try string comparison
                        all_entries = await hours_collection.find().to_list(length=500)
                        for e in all_entries:
                            if str(e.get("_id")) == entry_id:
                                entry = e
                                break

                    if entry:
                        validated_entries.append(str(entry["_id"]))
                    else:
                        print(f"Warning: Time entry with ID {entry_id} not found")

                timesheet_data["time_entries"] = validated_entries

            # Add timestamps
            now = datetime.utcnow()
            timesheet_data["created_at"] = now
            timesheet_data["updated_at"] = now

            # Insert into database
            result = await timesheets_collection.insert_one(timesheet_data)

            # Get the created timesheet
            if result.inserted_id:
                created_timesheet = await TimesheetService.get_timesheet(str(result.inserted_id))
                if created_timesheet:
                    return created_timesheet

            raise ValueError("Failed to retrieve created timesheet")
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
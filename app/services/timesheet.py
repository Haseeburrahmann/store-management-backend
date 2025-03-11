# app/services/timesheet.py
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from bson import ObjectId
from fastapi import HTTPException, status

from app.core.db import get_database, get_timesheets_collection, get_employees_collection, get_stores_collection, \
    get_hours_collection
from app.models.timesheet import TimesheetStatus
from app.utils.id_handler import IdHandler

# Get database and collections
db = get_database()
timesheets_collection = get_timesheets_collection()
employees_collection = get_employees_collection()
stores_collection = get_stores_collection()
hours_collection = get_hours_collection()


class TimesheetService:
    # Improved timesheet.py functions

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
        Get all timesheets with standardized ID handling
        """
        try:
            query = {}

            if employee_id:
                query["employee_id"] = IdHandler.id_to_str(employee_id)

            if store_id:
                query["store_id"] = IdHandler.id_to_str(store_id)

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

                # Ensure all IDs are strings
                timesheet_with_info["_id"] = IdHandler.id_to_str(timesheet.get("_id"))
                timesheet_with_info["employee_id"] = IdHandler.id_to_str(timesheet.get("employee_id"))
                timesheet_with_info["store_id"] = IdHandler.id_to_str(timesheet.get("store_id"))

                if timesheet.get("approved_by"):
                    timesheet_with_info["approved_by"] = IdHandler.id_to_str(timesheet.get("approved_by"))

                # Format time entries array
                if "time_entries" in timesheet:
                    timesheet_with_info["time_entries"] = [
                        IdHandler.id_to_str(entry) for entry in timesheet.get("time_entries", [])
                    ]

                # Add employee info using centralized ID handler
                if timesheet.get("employee_id"):
                    employee, _ = await IdHandler.find_document_by_id(
                        employees_collection,
                        IdHandler.id_to_str(timesheet.get("employee_id")),
                        not_found_msg=f"Employee not found for ID: {timesheet.get('employee_id')}"
                    )

                    if employee and employee.get("user_id"):
                        from app.services.user import get_user_by_id
                        user = await get_user_by_id(IdHandler.id_to_str(employee.get("user_id")))
                        if user:
                            timesheet_with_info["employee_name"] = user.get("full_name")

                # Add store info using centralized ID handler
                if timesheet.get("store_id"):
                    store, _ = await IdHandler.find_document_by_id(
                        stores_collection,
                        IdHandler.id_to_str(timesheet.get("store_id")),
                        not_found_msg=f"Store not found for ID: {timesheet.get('store_id')}"
                    )

                    if store:
                        timesheet_with_info["store_name"] = store.get("name")

                # Get time entry details if requested
                if timesheet.get("time_entries"):
                    time_entry_details = []
                    for entry_id in timesheet.get("time_entries", []):
                        entry_id_str = IdHandler.id_to_str(entry_id)
                        entry, _ = await IdHandler.find_document_by_id(
                            hours_collection,
                            entry_id_str,
                            not_found_msg=f"Time entry not found for ID: {entry_id_str}"
                        )

                        if entry:
                            # Format time entry
                            formatted_entry = dict(entry)
                            formatted_entry["_id"] = IdHandler.id_to_str(entry.get("_id"))
                            formatted_entry["employee_id"] = IdHandler.id_to_str(entry.get("employee_id"))
                            formatted_entry["store_id"] = IdHandler.id_to_str(entry.get("store_id"))

                            if entry.get("approved_by"):
                                formatted_entry["approved_by"] = IdHandler.id_to_str(entry.get("approved_by"))

                            time_entry_details.append(formatted_entry)

                    if time_entry_details:
                        timesheet_with_info["time_entry_details"] = time_entry_details

                result.append(timesheet_with_info)

            return result
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

            # Add employee info using centralized ID handler
            if timesheet.get("employee_id"):
                employee, _ = await IdHandler.find_document_by_id(
                    employees_collection,
                    timesheet.get("employee_id"),
                    not_found_msg=f"Employee not found for ID: {timesheet.get('employee_id')}"
                )

                if employee and employee.get("user_id"):
                    from app.services.user import get_user_by_id
                    user = await get_user_by_id(employee.get("user_id"))
                    if user:
                        timesheet_with_info["employee_name"] = user.get("full_name")

            # Add store info using centralized ID handler
            if timesheet.get("store_id"):
                store, _ = await IdHandler.find_document_by_id(
                    stores_collection,
                    timesheet.get("store_id"),
                    not_found_msg=f"Store not found for ID: {timesheet.get('store_id')}"
                )

                if store:
                    timesheet_with_info["store_name"] = store.get("name")

            # Get time entry details
            if timesheet.get("time_entries"):
                time_entry_details = []
                for entry_id in timesheet.get("time_entries"):
                    entry, _ = await IdHandler.find_document_by_id(
                        hours_collection,
                        entry_id,
                        not_found_msg=f"Time entry not found for ID: {entry_id}"
                    )

                    if entry:
                        time_entry_details.append(IdHandler.format_object_ids(entry))

                if time_entry_details:
                    timesheet_with_info["time_entry_details"] = time_entry_details

            return IdHandler.format_object_ids(timesheet_with_info)
        except Exception as e:
            print(f"Error getting timesheet: {str(e)}")
            return None

    @staticmethod
    async def submit_timesheet(timesheet_id: str, notes: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Submit a timesheet for approval with standardized ID handling
        """
        try:
            print(f"Submitting timesheet with ID: {timesheet_id}")

            # Find the timesheet using centralized ID handler
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

            # Get the updated timesheet using centralized ID handler
            updated_timesheet, _ = await IdHandler.find_document_by_id(
                timesheets_collection,
                timesheet_id,
                not_found_msg=f"Failed to retrieve updated timesheet"
            )

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
    async def update_timesheet(timesheet_id: str, timesheet_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update an existing timesheet with standardized ID handling
        """
        try:
            print(f"Updating timesheet with ID: {timesheet_id}")

            # Find the timesheet using centralized ID handler
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
                    entry, _ = await IdHandler.find_document_by_id(
                        hours_collection,
                        entry_id,
                        not_found_msg=f"Time entry not found for ID: {entry_id}"
                    )

                    if entry:
                        validated_entries.append(IdHandler.id_to_str(entry["_id"]))
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

            # Get the updated timesheet using our standardized method
            updated_timesheet, _ = await IdHandler.find_document_by_id(
                timesheets_collection,
                timesheet_id,
                not_found_msg=f"Failed to retrieve updated timesheet"
            )

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
        Delete a timesheet with standardized ID handling
        """
        try:
            print(f"Deleting timesheet with ID: {timesheet_id}")

            # Find the timesheet using centralized ID handler
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
    async def approve_timesheet(
            timesheet_id: str,
            approver_id: str,
            approval_status: TimesheetStatus,
            notes: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Approve or reject a timesheet with enhanced validation
        """
        try:
            print(f"Processing {approval_status.value} for timesheet with ID: {timesheet_id}")

            # Validate approval status
            if approval_status not in [TimesheetStatus.APPROVED, TimesheetStatus.REJECTED]:
                raise ValueError("Approval status must be either approved or rejected")

            # Find the timesheet using centralized ID handler
            timesheet, timesheet_obj_id = await IdHandler.find_document_by_id(
                timesheets_collection,
                timesheet_id,
                not_found_msg=f"Timesheet with ID {timesheet_id} not found"
            )

            if not timesheet:
                return None

            timesheet_id_str = IdHandler.id_to_str(timesheet_obj_id)

            # Check if timesheet is in submitted status
            current_status = timesheet.get("status")
            if current_status != TimesheetStatus.SUBMITTED.value:
                raise ValueError(f"Cannot approve/reject timesheet in {current_status} status")

            # Validate approver exists using centralized ID handler
            from app.services.user import get_user_by_id
            approver = await get_user_by_id(approver_id)
            if not approver:
                raise ValueError(f"Approver with ID {approver_id} not found")

            approver_id_str = IdHandler.id_to_str(approver["_id"])

            # Validate timesheet has time entries
            if not timesheet.get("time_entries") or len(timesheet.get("time_entries", [])) == 0:
                raise ValueError("Cannot approve/reject an empty timesheet")

            # Update the timesheet
            update_data = {
                "status": approval_status.value,
                "approved_by": approver_id_str,
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
            return await TimesheetService.get_timesheet(timesheet_id)
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
        Add a time entry to a timesheet with improved error handling and calculations
        """
        try:
            print(f"Adding time entry {time_entry_id} to timesheet {timesheet_id}")

            # Find the timesheet using centralized ID handler
            timesheet, timesheet_obj_id = await IdHandler.find_document_by_id(
                timesheets_collection,
                timesheet_id,
                not_found_msg=f"Timesheet with ID {timesheet_id} not found"
            )

            if not timesheet:
                return None

            timesheet_id_str = IdHandler.id_to_str(timesheet_obj_id)

            # Check if timesheet is in draft or rejected status
            current_status = timesheet.get("status")
            if current_status not in [TimesheetStatus.DRAFT.value, TimesheetStatus.REJECTED.value]:
                raise ValueError(f"Cannot add time entries to timesheet in {current_status} status")

            # Validate time entry exists using centralized ID handler
            entry, entry_obj_id = await IdHandler.find_document_by_id(
                hours_collection,
                time_entry_id,
                not_found_msg=f"Time entry with ID {time_entry_id} not found"
            )

            if not entry:
                raise ValueError(f"Time entry with ID {time_entry_id} not found")

            entry_id_str = IdHandler.id_to_str(entry_obj_id)

            # Ensure time entry belongs to the same employee
            if IdHandler.id_to_str(entry.get("employee_id")) != IdHandler.id_to_str(timesheet.get("employee_id")):
                raise ValueError("Time entry does not belong to the same employee as the timesheet")

            # Check if time entry already exists in timesheet
            if "time_entries" in timesheet:
                existing_entries = [IdHandler.id_to_str(entry_id) for entry_id in timesheet["time_entries"]]
                if entry_id_str in existing_entries:
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
                "total_hours": round(total_hours, 2)  # Round to 2 decimal places for consistency
            }

            # Use addToSet instead of push to avoid duplicates
            update_result = await timesheets_collection.update_one(
                {"_id": timesheet_obj_id},
                {
                    "$set": update_data,
                    "$addToSet": {"time_entries": entry_id_str}
                }
            )

            if update_result.matched_count == 0:
                return None

            # Get the updated timesheet
            return await TimesheetService.get_timesheet(timesheet_id)
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
        Remove a time entry from a timesheet with improved calculations and error handling
        """
        try:
            print(f"Removing time entry {time_entry_id} from timesheet {timesheet_id}")

            # Find the timesheet using centralized ID handler
            timesheet, timesheet_obj_id = await IdHandler.find_document_by_id(
                timesheets_collection,
                timesheet_id,
                not_found_msg=f"Timesheet with ID {timesheet_id} not found"
            )

            if not timesheet:
                return None

            timesheet_id_str = IdHandler.id_to_str(timesheet_obj_id)

            # Check if timesheet is in draft or rejected status
            current_status = timesheet.get("status")
            if current_status not in [TimesheetStatus.DRAFT.value, TimesheetStatus.REJECTED.value]:
                raise ValueError(f"Cannot remove time entries from timesheet in {current_status} status")

            # Check if the time entry is in the timesheet
            time_entry_id_str = IdHandler.id_to_str(time_entry_id)
            if "time_entries" not in timesheet or time_entry_id_str not in [
                IdHandler.id_to_str(entry_id) for entry_id in timesheet["time_entries"]
            ]:
                raise ValueError(f"Time entry {time_entry_id} not found in timesheet {timesheet_id}")

            # Find the time entry using centralized ID handler
            entry, entry_obj_id = await IdHandler.find_document_by_id(
                hours_collection,
                time_entry_id,
                not_found_msg=f"Time entry with ID {time_entry_id} not found"
            )

            # Calculate updated total hours
            total_hours = timesheet.get("total_hours", 0)

            if entry and entry.get("total_minutes"):
                # Convert minutes to hours and subtract
                entry_hours = entry["total_minutes"] / 60
                total_hours -= entry_hours
                # Ensure we don't go negative
                total_hours = max(0, total_hours)

            # Update the timesheet
            update_data = {
                "updated_at": datetime.utcnow(),
                "total_hours": round(total_hours, 2)  # Round to 2 decimal places for consistency
            }

            # Remove the time entry from the timesheet
            update_result = await timesheets_collection.update_one(
                {"_id": timesheet_obj_id},
                {
                    "$set": update_data,
                    "$pull": {"time_entries": time_entry_id_str}
                }
            )

            if update_result.matched_count == 0:
                return None

            # Get the updated timesheet
            return await TimesheetService.get_timesheet(timesheet_id)
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
    async def get_employee_current_timesheet(employee_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current timesheet for an employee
        """
        try:
            # Get the current date
            today = datetime.utcnow()

            # Calculate the week start (Sunday) and end (Saturday)
            week_start = today - timedelta(days=today.weekday() + 1)
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

            week_end = week_start + timedelta(days=6)
            week_end = week_end.replace(hour=23, minute=59, second=59, microsecond=999)

            # Find timesheet for the current week
            query = {
                "employee_id": employee_id,
                "week_start_date": {"$lte": today},
                "week_end_date": {"$gte": today}
            }

            timesheet = await timesheets_collection.find_one(query)

            # Return formatted timesheet if found
            if timesheet:
                return IdHandler.format_object_ids(timesheet)

            return None
        except Exception as e:
            print(f"Error getting current timesheet: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting current timesheet: {str(e)}"
            )

    @staticmethod
    async def generate_timesheet_from_hours(
            employee_id: str,
            store_id: str,
            week_start_date: str,
            week_end_date: str
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a timesheet from hours records with improved validation and ID handling
        """
        try:
            print(f"Generating timesheet for employee {employee_id} from {week_start_date} to {week_end_date}")

            # Validate dates
            if not (re.match(r'^\d{4}-\d{2}-\d{2}$', week_start_date) and re.match(r'^\d{4}-\d{2}-\d{2}$',
                                                                                   week_end_date)):
                raise ValueError("Dates must be in YYYY-MM-DD format")

            if week_start_date > week_end_date:
                raise ValueError("End date must be on or after start date")

            # Convert string dates to datetime objects for querying hours
            start_date = datetime.strptime(week_start_date, "%Y-%m-%d")
            end_date = datetime.strptime(week_end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)

            # Validate employee exists using centralized ID handler
            employee, employee_obj_id = await IdHandler.find_document_by_id(
                employees_collection,
                employee_id,
                not_found_msg=f"Employee with ID {employee_id} not found"
            )

            if not employee:
                raise ValueError(f"Employee with ID {employee_id} not found")

            employee_id_str = IdHandler.id_to_str(employee_obj_id)

            # Validate store exists using centralized ID handler
            store, store_obj_id = await IdHandler.find_document_by_id(
                stores_collection,
                store_id,
                not_found_msg=f"Store with ID {store_id} not found"
            )

            if not store:
                raise ValueError(f"Store with ID {store_id} not found")

            store_id_str = IdHandler.id_to_str(store_obj_id)

            # Check if a timesheet already exists for this period
            existing_timesheet = await timesheets_collection.find_one({
                "employee_id": employee_id_str,
                "week_start_date": week_start_date,
                "week_end_date": week_end_date
            })

            if existing_timesheet:
                print(f"Timesheet already exists for this period")
                existing_timesheet_id = IdHandler.id_to_str(existing_timesheet["_id"])

                return await TimesheetService.get_timesheet(existing_timesheet_id)

            # Get hours for this period
            hours_records = await hours_collection.find({
                "employee_id": employee_id_str,
                "clock_in": {"$gte": start_date, "$lte": end_date},
                "clock_out": {"$ne": None}  # Only include completed hours
            }).to_list(length=100)

            if not hours_records:
                raise ValueError(f"No hours records found for employee {employee_id} in the specified period")

            # Calculate total hours and gather time entry IDs
            total_hours = 0
            time_entry_ids = []

            for hour in hours_records:
                if hour.get("total_minutes"):
                    # Convert minutes to hours
                    hours = hour.get("total_minutes") / 60
                    total_hours += hours

                time_entry_ids.append(IdHandler.id_to_str(hour["_id"]))

            # Create timesheet data
            timesheet_data = {
                "employee_id": employee_id_str,
                "store_id": store_id_str,
                "week_start_date": week_start_date,
                "week_end_date": week_end_date,
                "time_entries": time_entry_ids,
                "total_hours": round(total_hours, 2),
                "status": TimesheetStatus.DRAFT.value,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }

            # Insert into database
            result = await timesheets_collection.insert_one(timesheet_data)
            inserted_id = result.inserted_id

            # Get the created timesheet
            created_timesheet = await timesheets_collection.find_one({"_id": inserted_id})
            if not created_timesheet:
                raise ValueError("Failed to retrieve created timesheet")

            # Format for frontend consistency
            formatted_timesheet = dict(created_timesheet)
            formatted_timesheet["_id"] = IdHandler.id_to_str(created_timesheet["_id"])
            formatted_timesheet["employee_id"] = employee_id_str
            formatted_timesheet["store_id"] = store_id_str

            # Add employee name if possible
            if employee.get("user_id"):
                from app.services.user import get_user_by_id
                user = await get_user_by_id(employee.get("user_id"))
                if user:
                    formatted_timesheet["employee_name"] = user.get("full_name")

            # Add store name
            formatted_timesheet["store_name"] = store.get("name")

            # Get time entry details
            time_entry_details = []
            for entry_id in time_entry_ids:
                entry, _ = await IdHandler.find_document_by_id(
                    hours_collection,
                    entry_id,
                    not_found_msg=f"Time entry not found for ID: {entry_id}"
                )

                if entry:
                    # Format time entry
                    formatted_entry = dict(entry)
                    formatted_entry["_id"] = IdHandler.id_to_str(entry.get("_id"))
                    formatted_entry["employee_id"] = IdHandler.id_to_str(entry.get("employee_id"))
                    formatted_entry["store_id"] = IdHandler.id_to_str(entry.get("store_id"))

                    if entry.get("approved_by"):
                        formatted_entry["approved_by"] = IdHandler.id_to_str(entry.get("approved_by"))

                    time_entry_details.append(formatted_entry)

            if time_entry_details:
                formatted_timesheet["time_entry_details"] = time_entry_details

            return formatted_timesheet
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

# app/services/hours.py
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from bson import ObjectId
from fastapi import HTTPException, status

from app.core.db import get_database, get_hours_collection, get_employees_collection, get_stores_collection
from app.models.hours import HoursStatus
from app.schemas.hours import HourCreate, HourUpdate, HourApproval, TimeSheetSummary
from app.utils.datetime_handler import DateTimeHandler
from app.utils.formatting import format_object_ids
from app.utils.id_handler import IdHandler

# Get database and collections
db = get_database()
hours_collection = get_hours_collection()
employees_collection = get_employees_collection()
stores_collection = get_stores_collection()


class HourService:
    @staticmethod
    async def create_hour(hour_data: HourCreate) -> Dict[str, Any]:
        """
        Create a new hours record with standardized ID handling
        """
        try:
            print(f"Creating hour record with data: {hour_data.model_dump()}")

            # Validate employee exists using centralized ID handler
            employee, _ = await IdHandler.find_document_by_id(
                employees_collection,
                hour_data.employee_id,
                not_found_msg=f"Employee with ID {hour_data.employee_id} not found"
            )

            if not employee:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Employee with ID {hour_data.employee_id} not found"
                )

            # Validate store exists using centralized ID handler
            store, _ = await IdHandler.find_document_by_id(
                stores_collection,
                hour_data.store_id,
                not_found_msg=f"Store with ID {hour_data.store_id} not found"
            )

            if not store:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Store with ID {hour_data.store_id} not found"
                )

            # Calculate total minutes if clock_out is provided
            total_minutes = None
            if hour_data.clock_out:
                total_minutes = HourService.calculate_work_minutes(
                    hour_data.clock_in,
                    hour_data.clock_out,
                    hour_data.break_start,
                    hour_data.break_end
                )
                print(f"Calculated total minutes: {total_minutes}")

            # Convert model to dict
            hour_dict = hour_data.model_dump()

            # Store IDs consistently as strings
            hour_dict["employee_id"] = IdHandler.id_to_str(employee["_id"])
            hour_dict["store_id"] = IdHandler.id_to_str(store["_id"])

            # Add additional fields
            hour_dict.update({
                "total_minutes": total_minutes,
                "status": HoursStatus.PENDING.value,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            })

            # Insert into database
            result = await hours_collection.insert_one(hour_dict)
            print(f"Hour record created with ID: {result.inserted_id}")

            # Get the newly created record using our standardized method
            new_hour, _ = await IdHandler.find_document_by_id(
                hours_collection,
                str(result.inserted_id),
                not_found_msg=f"Failed to retrieve created hour record"
            )

            if new_hour:
                return IdHandler.format_object_ids(new_hour)

            print("Failed to create hours record")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create hours record"
            )
        except Exception as e:
            print(f"Error creating hour record: {str(e)}")
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating hour record: {str(e)}"
            )

    @staticmethod
    async def get_hour(hour_id: str) -> Optional[Dict[str, Any]]:
        """
        Get hour record by ID using the centralized ID handler
        """
        try:
            print(f"Looking up hour record with ID: {hour_id}")

            # Use centralized method for consistent lookup
            hour, _ = await IdHandler.find_document_by_id(
                hours_collection,
                hour_id,
                not_found_msg=f"Hour record with ID {hour_id} not found"
            )

            if not hour:
                print(f"Hour record not found with ID: {hour_id}")
                return None

            # Enrich hour data with employee and store info
            hour_with_info = dict(hour)

            # Add employee info using centralized ID handler
            if hour.get("employee_id"):
                print(f"Getting employee info for employee_id: {hour.get('employee_id')}")
                employee, _ = await IdHandler.find_document_by_id(
                    employees_collection,
                    hour.get("employee_id"),
                    not_found_msg=f"Employee not found for ID: {hour.get('employee_id')}"
                )

                if employee:
                    print(f"Found employee")

                    # Get user info if available
                    if employee.get("user_id"):
                        from app.services.user import get_user_by_id
                        user = await get_user_by_id(employee.get("user_id"))
                        if user:
                            hour_with_info["employee_name"] = user.get("full_name")
                else:
                    print(f"Employee not found for ID: {hour.get('employee_id')}")

            # Add store info using centralized ID handler
            if hour.get("store_id"):
                print(f"Getting store info for store_id: {hour.get('store_id')}")
                store, _ = await IdHandler.find_document_by_id(
                    stores_collection,
                    hour.get("store_id"),
                    not_found_msg=f"Store not found for ID: {hour.get('store_id')}"
                )

                if store:
                    print(f"Found store: {store.get('name')}")
                    hour_with_info["store_name"] = store.get("name")
                else:
                    print(f"Store not found for ID: {hour.get('store_id')}")

            return IdHandler.format_object_ids(hour_with_info)
        except Exception as e:
            print(f"Error getting hour record: {str(e)}")
            return None

    @staticmethod
    async def update_hour(hour_id: str, hour_data: HourUpdate, current_user_id: str) -> Optional[Dict[str, Any]]:
        """
        Update an hour record with standardized ID handling
        """
        try:
            print(f"Updating hour record with ID: {hour_id}")
            print(f"Update data: {hour_data.model_dump()}")

            # Find the hour record using centralized ID handler
            hour, hour_obj_id = await IdHandler.find_document_by_id(
                hours_collection,
                hour_id,
                not_found_msg=f"Hour record with ID {hour_id} not found"
            )

            if not hour:
                print(f"Hour record not found with ID: {hour_id}")
                return None

            # Check if record is already approved
            if hour.get("status") == HoursStatus.APPROVED.value:
                print(f"Cannot update approved hour record: {hour_id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot update an approved hours record"
                )

            # Prepare update data
            update_data = hour_data.model_dump(exclude_unset=True)
            update_data["updated_at"] = datetime.utcnow()

            # Calculate total minutes if clock_out is provided
            if hour_data.clock_out:
                clock_in = hour["clock_in"]
                break_start = update_data.get("break_start", hour.get("break_start"))
                break_end = update_data.get("break_end", hour.get("break_end"))

                update_data["total_minutes"] = HourService.calculate_work_minutes(
                    clock_in,
                    hour_data.clock_out,
                    break_start,
                    break_end
                )
                print(f"Recalculated total minutes: {update_data['total_minutes']}")

            # Update the record
            print(f"Updating hour with ID: {hour_obj_id}")
            update_result = await hours_collection.update_one(
                {"_id": hour_obj_id},
                {"$set": update_data}
            )

            print(f"Update result: matched={update_result.matched_count}, modified={update_result.modified_count}")

            if update_result.matched_count == 0:
                print(f"No hour matched the ID: {hour_obj_id}")
                return None

            # Return the updated record using centralized ID handler
            updated_hour, _ = await IdHandler.find_document_by_id(
                hours_collection,
                hour_id,
                not_found_msg=f"Failed to retrieve updated hour record"
            )

            if updated_hour:
                return IdHandler.format_object_ids(updated_hour)

            print(f"Error retrieving updated hour record")
            return None
        except Exception as e:
            print(f"Error updating hour record: {str(e)}")
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error updating hour record: {str(e)}"
            )

    # Update calculate_work_minutes function with the improved date handling

    @staticmethod
    def calculate_work_minutes(clock_in, clock_out, break_start=None, break_end=None):
        """
        Calculate working minutes, accounting for breaks
        Using improved datetime handling
        """
        try:
            # Input validation and normalization
            clock_in_normalized = DateTimeHandler.normalize_datetime(clock_in)
            clock_out_normalized = DateTimeHandler.normalize_datetime(clock_out)

            if not clock_in_normalized or not clock_out_normalized:
                print("Invalid clock in/out times")
                return 0

            # Basic validation - ensure clock_out is after clock_in
            if not DateTimeHandler.is_valid_range(clock_in_normalized, clock_out_normalized):
                print("Clock out time must be after clock in time")
                return 0

            # Calculate total duration in minutes
            duration_minutes = int((clock_out_normalized - clock_in_normalized).total_seconds() / 60)

            # Process break times if both are provided
            if break_start and break_end:
                break_start_normalized = DateTimeHandler.normalize_datetime(break_start)
                break_end_normalized = DateTimeHandler.normalize_datetime(break_end)

                if not break_start_normalized or not break_end_normalized:
                    print("Invalid break times")
                    return duration_minutes

                # Validate break times
                if not DateTimeHandler.is_valid_range(break_start_normalized, break_end_normalized):
                    print("Break end time must be after break start time")
                    return duration_minutes

                # Ensure break is within shift
                if break_start_normalized < clock_in_normalized:
                    print("Break start cannot be before clock in")
                    break_start_normalized = clock_in_normalized

                if break_end_normalized > clock_out_normalized:
                    print("Break end cannot be after clock out")
                    break_end_normalized = clock_out_normalized

                # Calculate break duration
                break_minutes = int((break_end_normalized - break_start_normalized).total_seconds() / 60)
                duration_minutes -= break_minutes

            return max(0, duration_minutes)  # Ensure we don't return negative minutes
        except Exception as e:
            print(f"Error calculating work minutes: {str(e)}")
            # Return 0 minutes for safety
            return 0

    # Improved hours.py functions

    @staticmethod
    async def get_hours(
            employee_id: Optional[str] = None,
            store_id: Optional[str] = None,
            start_date: Optional[datetime] = None,
            end_date: Optional[datetime] = None,
            status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get hours records with standardized ID handling
        """
        try:
            print(f"Getting hours with filters - employee: {employee_id}, store: {store_id}, status: {status}")
            # Build query filters
            query = {}

            if employee_id:
                # Always store as string for consistency in queries
                query["employee_id"] = IdHandler.id_to_str(employee_id)

            if store_id:
                # Always store as string for consistency in queries
                query["store_id"] = IdHandler.id_to_str(store_id)

            if start_date:
                print(f"Adding start date filter: {start_date}")
                query["clock_in"] = {"$gte": start_date}

            if end_date:
                print(f"Adding end date filter: {end_date}")
                if "clock_in" in query:
                    query["clock_in"]["$lte"] = end_date
                else:
                    query["clock_in"] = {"$lte": end_date}

            if status:
                print(f"Adding status filter: {status}")
                query["status"] = status

            print(f"Final query: {query}")

            # Get records
            cursor = hours_collection.find(query).sort("clock_in", -1)
            hours_records = await cursor.to_list(length=100)
            print(f"Found {len(hours_records)} hour records")

            # Enrich records with employee and store info
            enriched_records = []
            for record in hours_records:
                hour_with_info = dict(record)

                # Ensure all IDs are strings for frontend consistency
                hour_with_info["_id"] = IdHandler.id_to_str(record.get("_id"))
                hour_with_info["employee_id"] = IdHandler.id_to_str(record.get("employee_id"))
                hour_with_info["store_id"] = IdHandler.id_to_str(record.get("store_id"))

                if record.get("approved_by"):
                    hour_with_info["approved_by"] = IdHandler.id_to_str(record.get("approved_by"))

                # Add employee info using centralized ID handler
                if record.get("employee_id"):
                    employee, _ = await IdHandler.find_document_by_id(
                        employees_collection,
                        IdHandler.id_to_str(record.get("employee_id")),
                        not_found_msg=f"Employee not found for ID: {record.get('employee_id')}"
                    )

                    if employee and employee.get("user_id"):
                        from app.services.user import get_user_by_id
                        user = await get_user_by_id(IdHandler.id_to_str(employee.get("user_id")))
                        if user:
                            hour_with_info["employee_name"] = user.get("full_name")

                # Add store info using centralized ID handler
                if record.get("store_id"):
                    store, _ = await IdHandler.find_document_by_id(
                        stores_collection,
                        IdHandler.id_to_str(record.get("store_id")),
                        not_found_msg=f"Store not found for ID: {record.get('store_id')}"
                    )

                    if store:
                        hour_with_info["store_name"] = store.get("name")

                enriched_records.append(hour_with_info)

            # No need to call format_object_ids as we've already formatted the IDs
            return enriched_records
        except Exception as e:
            print(f"Error getting hours: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting hours: {str(e)}"
            )

    @staticmethod
    async def clock_in(employee_id: str, store_id: str, notes: Optional[str] = None) -> Dict[str, Any]:
        """
        Clock in an employee with improved error handling and ID consistency
        """
        try:
            print(f"Clocking in employee: {employee_id} at store: {store_id}")

            # Validate employee exists using centralized ID handler
            employee, employee_obj_id = await IdHandler.find_document_by_id(
                employees_collection,
                employee_id,
                not_found_msg=f"Employee with ID {employee_id} not found"
            )

            if not employee:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Employee with ID {employee_id} not found"
                )

            # Validate store exists using centralized ID handler
            store, store_obj_id = await IdHandler.find_document_by_id(
                stores_collection,
                store_id,
                not_found_msg=f"Store with ID {store_id} not found"
            )

            if not store:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Store with ID {store_id} not found"
                )

            # Use string IDs consistently
            employee_id_str = IdHandler.id_to_str(employee_obj_id)
            store_id_str = IdHandler.id_to_str(store_obj_id)

            # Check if employee is already clocked in
            active_shift = await hours_collection.find_one({
                "employee_id": employee_id_str,
                "clock_out": None
            })

            if active_shift:
                print(f"Employee {employee_id} is already clocked in")
                active_shift_formatted = dict(active_shift)
                active_shift_formatted["_id"] = IdHandler.id_to_str(active_shift.get("_id"))
                active_shift_formatted["employee_id"] = IdHandler.id_to_str(active_shift.get("employee_id"))
                active_shift_formatted["store_id"] = IdHandler.id_to_str(active_shift.get("store_id"))

                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Employee is already clocked in",
                    headers={"X-Active-Shift": IdHandler.id_to_str(active_shift.get("_id"))}
                )

            # Create hours record
            now = datetime.utcnow()
            hour_data = {
                "employee_id": employee_id_str,
                "store_id": store_id_str,
                "clock_in": now,
                "status": HoursStatus.PENDING.value,
                "notes": notes,
                "created_at": now,
                "updated_at": now
            }

            # Insert into database
            result = await hours_collection.insert_one(hour_data)
            inserted_id = result.inserted_id

            # Get the newly created record
            created_hour = await hours_collection.find_one({"_id": inserted_id})
            if not created_hour:
                print("Failed to retrieve created hour record")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create hours record"
                )

            # Format for frontend consistency
            formatted_hour = dict(created_hour)
            formatted_hour["_id"] = IdHandler.id_to_str(created_hour.get("_id"))
            formatted_hour["employee_id"] = employee_id_str
            formatted_hour["store_id"] = store_id_str

            # Add employee name if possible
            if employee.get("user_id"):
                from app.services.user import get_user_by_id
                user = await get_user_by_id(employee.get("user_id"))
                if user:
                    formatted_hour["employee_name"] = user.get("full_name")

            # Add store name
            formatted_hour["store_name"] = store.get("name")

            return formatted_hour
        except HTTPException:
            raise
        except Exception as e:
            print(f"Error clocking in employee: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error clocking in employee: {str(e)}"
            )

    @staticmethod
    async def clock_out(
            employee_id: str,
            break_start: Optional[datetime] = None,
            break_end: Optional[datetime] = None,
            notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Clock out an employee with improved validation and ID handling
        """
        try:
            print(f"Clocking out employee: {employee_id}")

            # Validate employee exists using centralized ID handler
            employee, employee_obj_id = await IdHandler.find_document_by_id(
                employees_collection,
                employee_id,
                not_found_msg=f"Employee with ID {employee_id} not found"
            )

            if not employee:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Employee with ID {employee_id} not found"
                )

            employee_id_str = IdHandler.id_to_str(employee_obj_id)

            # Find the active shift
            active_shift = await hours_collection.find_one({
                "employee_id": employee_id_str,
                "clock_out": None
            })

            if not active_shift:
                print(f"No active shift found for employee: {employee_id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No active shift found for employee"
                )

            # Validate break times if provided
            clock_in_time = active_shift["clock_in"]
            clock_out_time = datetime.utcnow()

            filtered_break_start = None
            filtered_break_end = None

            if break_start and break_end:
                # Use the utility function to handle timezone issues
                break_start_utc = break_start.replace(tzinfo=None) if hasattr(break_start,
                                                                              'tzinfo') and break_start.tzinfo else break_start
                break_end_utc = break_end.replace(tzinfo=None) if hasattr(break_end,
                                                                          'tzinfo') and break_end.tzinfo else break_end

                if break_start_utc >= break_end_utc:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Break end time must be after break start time"
                    )

                if break_start_utc < clock_in_time:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Break start time must be after clock in time"
                    )

                if break_end_utc > clock_out_time:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Break end time must be before clock out time"
                    )

                filtered_break_start = break_start_utc
                filtered_break_end = break_end_utc

            # Calculate total minutes using the improved function
            total_minutes = HourService.calculate_work_minutes(
                clock_in_time,
                clock_out_time,
                filtered_break_start or active_shift.get("break_start"),
                filtered_break_end or active_shift.get("break_end")
            )

            # Update the record
            update_data = {
                "clock_out": clock_out_time,
                "total_minutes": total_minutes,
                "updated_at": datetime.utcnow()
            }

            if filtered_break_start:
                update_data["break_start"] = filtered_break_start

            if filtered_break_end:
                update_data["break_end"] = filtered_break_end

            if notes:
                update_data["notes"] = notes

            print(f"Updating hour record with ID: {active_shift['_id']}")
            await hours_collection.update_one(
                {"_id": active_shift["_id"]},
                {"$set": update_data}
            )

            # Get the updated record
            updated_hour = await hours_collection.find_one({"_id": active_shift["_id"]})
            if not updated_hour:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to retrieve updated hour record"
                )

            # Format for frontend consistency
            formatted_hour = dict(updated_hour)
            formatted_hour["_id"] = IdHandler.id_to_str(updated_hour.get("_id"))
            formatted_hour["employee_id"] = IdHandler.id_to_str(updated_hour.get("employee_id"))
            formatted_hour["store_id"] = IdHandler.id_to_str(updated_hour.get("store_id"))

            if updated_hour.get("approved_by"):
                formatted_hour["approved_by"] = IdHandler.id_to_str(updated_hour.get("approved_by"))

            # Add employee name if possible
            if employee.get("user_id"):
                from app.services.user import get_user_by_id
                user = await get_user_by_id(employee.get("user_id"))
                if user:
                    formatted_hour["employee_name"] = user.get("full_name")

            # Add store name
            store = await stores_collection.find_one({"_id": updated_hour.get("store_id")})
            if store:
                formatted_hour["store_name"] = store.get("name")

            return formatted_hour
        except HTTPException:
            raise
        except Exception as e:
            print(f"Error clocking out employee: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error clocking out employee: {str(e)}"
            )

    @staticmethod
    async def get_active_hour(employee_id: str) -> Optional[Dict[str, Any]]:
        """
        Get active hour record for an employee with standardized ID handling
        """
        try:
            print(f"Getting active hour for employee: {employee_id}")

            # Find employee using centralized ID handler
            employee, employee_obj_id = await IdHandler.find_document_by_id(
                employees_collection,
                employee_id,
                not_found_msg=f"Employee with ID {employee_id} not found"
            )

            if not employee:
                print(f"Employee not found with ID: {employee_id}")
                return None

            # Look up active hour
            active_hour = await hours_collection.find_one({
                "employee_id": IdHandler.id_to_str(employee_obj_id),
                "clock_out": None
            })

            if active_hour:
                return IdHandler.format_object_ids(active_hour)

            print(f"No active hour found for employee: {employee_id}")
            return None
        except Exception as e:
            print(f"Error getting active hour: {str(e)}")
            return None

    @staticmethod
    async def approve_hour(hour_id: str, approval_data: HourApproval, approver_id: str) -> Optional[Dict[str, Any]]:
        """
        Approve or reject an hour record with standardized ID handling and proper state transitions
        """
        try:
            print(f"Processing approval for hour record: {hour_id}")
            print(f"Approval data: {approval_data}")

            # Find the hour record using centralized ID handler
            hour, hour_obj_id = await IdHandler.find_document_by_id(
                hours_collection,
                hour_id,
                not_found_msg=f"Hour record with ID {hour_id} not found"
            )

            if not hour:
                raise ValueError(f"Hour record with ID {hour_id} not found")

            # Get current status
            current_status = hour.get("status")
            new_status = approval_data.status.value

            # Define valid state transitions
            valid_transitions = {
                HoursStatus.PENDING.value: [HoursStatus.APPROVED.value, HoursStatus.REJECTED.value],
                HoursStatus.REJECTED.value: [HoursStatus.PENDING.value]
                # Add other valid transitions if needed
            }

            # Validate the state transition
            if current_status not in valid_transitions or new_status not in valid_transitions.get(current_status, []):
                raise ValueError(f"Invalid status transition from {current_status} to {new_status}")

            # Check if clock out time exists
            if not hour.get("clock_out"):
                raise ValueError("Cannot approve an hours record without clock out time")

            # Validate approver exists using centralized ID handler
            from app.services.user import get_user_by_id
            approver = await get_user_by_id(approver_id)
            if not approver:
                raise ValueError(f"Approver with ID {approver_id} not found")

            # Update the approval status
            update_data = {
                "status": approval_data.status.value,
                "approved_by": IdHandler.id_to_str(approver["_id"]),
                "approved_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }

            if approval_data.notes:
                if approval_data.status == HoursStatus.REJECTED:
                    update_data["rejection_reason"] = approval_data.notes
                else:
                    update_data["approval_notes"] = approval_data.notes

            print(f"Updating hour record with approval status: {approval_data.status.value}")
            update_result = await hours_collection.update_one(
                {"_id": hour_obj_id},
                {"$set": update_data}
            )

            print(f"Update result: matched={update_result.matched_count}, modified={update_result.modified_count}")

            if update_result.matched_count == 0:
                raise ValueError(f"No hour record matched the ID: {hour_id}")

            # Return the updated record using centralized ID handler
            updated_hour, _ = await IdHandler.find_document_by_id(
                hours_collection,
                hour_id,
                not_found_msg=f"Failed to retrieve updated hour record"
            )

            if updated_hour:
                return IdHandler.format_object_ids(updated_hour)

            raise ValueError(f"Failed to retrieve updated hour record")
        except ValueError as e:
            print(f"Validation error approving hour record: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            print(f"Error approving hour record: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unexpected error: {str(e)}"
            )

    @staticmethod
    async def delete_hour(hour_id: str) -> bool:
        """
        Delete an hour record with standardized ID handling
        """
        try:
            print(f"Attempting to delete hour record with ID: {hour_id}")

            # Find the hour record using centralized ID handler
            hour, hour_obj_id = await IdHandler.find_document_by_id(
                hours_collection,
                hour_id,
                not_found_msg=f"Hour record with ID {hour_id} not found"
            )

            if not hour:
                print(f"Hour record not found with ID: {hour_id}")
                return False

            # Check if already approved
            if hour.get("status") == HoursStatus.APPROVED.value:
                print(f"Cannot delete approved hour record: {hour_id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot delete an approved hours record"
                )

            # Delete the record
            print(f"Deleting hour record with ID: {hour_obj_id}")
            result = await hours_collection.delete_one({"_id": hour_obj_id})

            print(f"Delete result: deleted={result.deleted_count}")
            return result.deleted_count > 0
        except Exception as e:
            print(f"Error deleting hour record: {str(e)}")
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error deleting hour record: {str(e)}"
            )
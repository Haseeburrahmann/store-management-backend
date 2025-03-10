# app/services/hours.py
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from bson import ObjectId
from fastapi import HTTPException, status

from app.core.db import get_database, get_hours_collection, get_employees_collection, get_stores_collection
from app.models.hours import HoursStatus
from app.schemas.hours import HourCreate, HourUpdate, HourApproval, TimeSheetSummary
from app.utils.formatting import format_object_ids, ensure_object_id
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
        Create a new hours record with enhanced validation and error handling
        """
        try:
            print(f"Creating hour record with data: {hour_data.model_dump()}")

            # Find the employee using multiple lookup strategies
            employee = None
            employee_id = hour_data.employee_id

            # 1. Try with ObjectId
            obj_id = ensure_object_id(employee_id)
            if obj_id:
                employee = await employees_collection.find_one({"_id": obj_id})

            # 2. Try with string ID if ObjectId lookup failed
            if not employee:
                employee = await employees_collection.find_one({"_id": employee_id})

            # 3. Try string comparison as last resort
            if not employee:
                all_employees = await employees_collection.find().to_list(length=100)
                for emp in all_employees:
                    if str(emp.get('_id')) == employee_id:
                        employee = emp
                        break

            if not employee:
                print(f"Employee with ID {employee_id} not found")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Employee with ID {employee_id} not found"
                )

            # Similar approach for store lookup
            store = None
            store_id = hour_data.store_id

            # Try multiple lookup strategies for store
            obj_id = ensure_object_id(store_id)
            if obj_id:
                store = await stores_collection.find_one({"_id": obj_id})

            if not store:
                store = await stores_collection.find_one({"_id": store_id})

            if not store:
                all_stores = await stores_collection.find().to_list(length=100)
                for s in all_stores:
                    if str(s.get('_id')) == store_id:
                        store = s
                        break

            if not store:
                print(f"Store with ID {store_id} not found")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Store with ID {store_id} not found"
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

            # Use the original string IDs that were found in the database
            hour_dict["employee_id"] = employee_id
            hour_dict["store_id"] = store_id

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

            # Get the newly created record
            if result.inserted_id:
                new_hour = await hours_collection.find_one({"_id": result.inserted_id})
                if new_hour:
                    print(f"Retrieved new hour record")
                    return format_object_ids(new_hour)
                else:
                    print(f"Error retrieving new hour record")

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

            # Add employee info
            if hour.get("employee_id"):
                print(f"Getting employee info for employee_id: {hour.get('employee_id')}")
                employee = await employees_collection.find_one({"_id": hour.get("employee_id")})
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

            # Add store info
            if hour.get("store_id"):
                print(f"Getting store info for store_id: {hour.get('store_id')}")
                store = await stores_collection.find_one({"_id": hour.get("store_id")})
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
        Update an hour record with enhanced error handling
        """
        try:
            print(f"Updating hour record with ID: {hour_id}")
            print(f"Update data: {hour_data.model_dump()}")

            # Find the hour record using multiple lookup strategies
            hour = None
            hour_obj_id = None

            # 1. Try with ObjectId
            obj_id = ensure_object_id(hour_id)
            if obj_id:
                print(f"Looking up hour with ObjectId: {obj_id}")
                hour = await hours_collection.find_one({"_id": obj_id})
                if hour:
                    hour_obj_id = obj_id
                    print(f"Found hour with ObjectId")
                else:
                    print(f"No hour found with ObjectId")

            # 2. Try string ID lookup
            if not hour:
                print(f"Looking up hour with string ID: {hour_id}")
                hour = await hours_collection.find_one({"_id": hour_id})
                if hour:
                    hour_obj_id = hour["_id"]
                    print(f"Found hour with string ID")
                else:
                    print(f"No hour found with string ID")

            # 3. Try string comparison
            if not hour:
                print("Trying string comparison...")
                all_hours = await hours_collection.find().to_list(length=100)
                for h in all_hours:
                    if str(h.get('_id')) == hour_id:
                        hour = h
                        hour_obj_id = h["_id"]
                        print(f"Found hour by string comparison")
                        break

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

            # Return the updated record
            updated_hour = await hours_collection.find_one({"_id": hour_obj_id})
            if updated_hour:
                print(f"Retrieved updated hour record")
                return format_object_ids(updated_hour)

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

    @staticmethod
    def calculate_work_minutes(
            clock_in: datetime,
            clock_out: datetime,
            break_start: Optional[datetime] = None,
            break_end: Optional[datetime] = None
    ) -> int:
        """
        Calculate work minutes between clock in and clock out, accounting for breaks
        """
        # Calculate total duration in minutes
        total_minutes = (clock_out - clock_in).total_seconds() / 60

        # Subtract break time if applicable
        if break_start and break_end:
            break_minutes = (break_end - break_start).total_seconds() / 60
            total_minutes -= break_minutes

        return int(total_minutes)

    @staticmethod
    async def get_hours(
            employee_id: Optional[str] = None,
            store_id: Optional[str] = None,
            start_date: Optional[datetime] = None,
            end_date: Optional[datetime] = None,
            status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get hours records with enhanced filtering and error handling
        """
        try:
            print(f"Getting hours with filters - employee: {employee_id}, store: {store_id}, status: {status}")
            # Build query filters
            query = {}

            if employee_id:
                # Try to convert to ObjectId if valid
                employee_obj_id = ensure_object_id(employee_id)
                if employee_obj_id:
                    print(f"Using ObjectId for employee filter: {employee_obj_id}")
                    query["employee_id"] = employee_obj_id
                else:
                    print(f"Using string ID for employee filter: {employee_id}")
                    query["employee_id"] = employee_id

            if store_id:
                # Try to convert to ObjectId if valid
                store_obj_id = ensure_object_id(store_id)
                if store_obj_id:
                    print(f"Using ObjectId for store filter: {store_obj_id}")
                    query["store_id"] = store_obj_id
                else:
                    print(f"Using string ID for store filter: {store_id}")
                    query["store_id"] = store_id

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

                # Add employee info
                if record.get("employee_id"):
                    emp_id = record.get("employee_id")
                    employee = await employees_collection.find_one({"_id": emp_id})
                    if employee and employee.get("user_id"):
                        from app.services.user import get_user_by_id
                        user = await get_user_by_id(employee.get("user_id"))
                        if user:
                            hour_with_info["employee_name"] = user.get("full_name")

                # Add store info
                if record.get("store_id"):
                    store_id = record.get("store_id")
                    store = await stores_collection.find_one({"_id": store_id})
                    if store:
                        hour_with_info["store_name"] = store.get("name")

                enriched_records.append(hour_with_info)

            # Format records
            return format_object_ids(enriched_records)
        except Exception as e:
            print(f"Error getting hours: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting hours: {str(e)}"
            )

    @staticmethod
    async def clock_in(employee_id: str, store_id: str, notes: Optional[str] = None) -> Dict[str, Any]:
        """
        Clock in an employee with enhanced validation
        """
        try:
            print(f"Clocking in employee: {employee_id} at store: {store_id}")

            # Validate employee exists
            employee = None
            employee_obj_id = ensure_object_id(employee_id)
            if employee_obj_id:
                employee = await employees_collection.find_one({"_id": employee_obj_id})

            if not employee:
                # Try string lookup as fallback
                all_employees = await employees_collection.find().to_list(length=100)
                for emp in all_employees:
                    if str(emp.get('_id')) == employee_id:
                        employee = emp
                        employee_obj_id = emp.get('_id')
                        break

            if not employee:
                print(f"Employee with ID {employee_id} not found")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Employee with ID {employee_id} not found"
                )

            # Validate store exists
            store = None
            store_obj_id = ensure_object_id(store_id)
            if store_obj_id:
                store = await stores_collection.find_one({"_id": store_obj_id})

            if not store:
                # Try string lookup as fallback
                all_stores = await stores_collection.find().to_list(length=100)
                for s in all_stores:
                    if str(s.get('_id')) == store_id:
                        store = s
                        store_obj_id = s.get('_id')
                        break

            if not store:
                print(f"Store with ID {store_id} not found")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Store with ID {store_id} not found"
                )

            # Check if employee is already clocked in
            active_shift = await hours_collection.find_one({
                "employee_id": employee_obj_id,
                "clock_out": None
            })

            if active_shift:
                print(f"Employee {employee_id} is already clocked in")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Employee is already clocked in"
                )

            # Create hours record
            hour_data = HourCreate(
                employee_id=str(employee_obj_id),
                store_id=str(store_obj_id),
                clock_in=datetime.utcnow(),
                notes=notes
            )

            return await HourService.create_hour(hour_data)
        except Exception as e:
            print(f"Error clocking in employee: {str(e)}")
            if isinstance(e, HTTPException):
                raise e
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
        Clock out an employee with enhanced validation
        """
        try:
            print(f"Clocking out employee: {employee_id}")

            # Validate employee exists
            employee = None
            employee_obj_id = ensure_object_id(employee_id)
            if employee_obj_id:
                employee = await employees_collection.find_one({"_id": employee_obj_id})

            if not employee:
                # Try string lookup as fallback
                all_employees = await employees_collection.find().to_list(length=100)
                for emp in all_employees:
                    if str(emp.get('_id')) == employee_id:
                        employee = emp
                        employee_obj_id = emp.get('_id')
                        break

            if not employee:
                print(f"Employee with ID {employee_id} not found")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Employee with ID {employee_id} not found"
                )

            # Find the active shift
            active_shift = await hours_collection.find_one({
                "employee_id": employee_obj_id,
                "clock_out": None
            })

            if not active_shift:
                print(f"No active shift found for employee: {employee_id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No active shift found for employee"
                )

            # Validate break times if provided
            if break_start and break_end:
                if break_start >= break_end:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Break end time must be after break start time"
                    )

                clock_in_time = active_shift["clock_in"]
                if break_start < clock_in_time:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Break start time must be after clock in time"
                    )

            # Calculate total minutes
            clock_out_time = datetime.utcnow()
            total_minutes = HourService.calculate_work_minutes(
                active_shift["clock_in"],
                clock_out_time,
                break_start or active_shift.get("break_start"),
                break_end or active_shift.get("break_end")
            )

            # Update the record
            update_data = {
                "clock_out": clock_out_time,
                "total_minutes": total_minutes,
                "updated_at": datetime.utcnow()
            }

            if break_start:
                update_data["break_start"] = break_start

            if break_end:
                update_data["break_end"] = break_end

            if notes:
                update_data["notes"] = notes or active_shift.get("notes")

            print(f"Updating hour record with ID: {active_shift['_id']}")
            await hours_collection.update_one(
                {"_id": active_shift["_id"]},
                {"$set": update_data}
            )

            # Return the updated record
            updated_hour = await hours_collection.find_one({"_id": active_shift["_id"]})
            if updated_hour:
                print(f"Employee {employee_id} clocked out successfully")
                return format_object_ids(updated_hour)

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update hours record"
            )
        except Exception as e:
            print(f"Error clocking out employee: {str(e)}")
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error clocking out employee: {str(e)}"
            )

    @staticmethod
    async def get_active_hour(employee_id: str) -> Optional[Dict[str, Any]]:
        """
        Get active hour record for an employee with enhanced lookup strategies
        """
        try:
            print(f"Getting active hour for employee: {employee_id}")

            # Find employee using multiple strategies
            employee_obj_id = ensure_object_id(employee_id)

            # Try with ObjectId
            if employee_obj_id:
                print(f"Trying lookup with ObjectId: {employee_obj_id}")
                active_hour = await hours_collection.find_one({
                    "employee_id": employee_obj_id,
                    "clock_out": None
                })
                if active_hour:
                    print(f"Found active hour with ObjectId lookup")
                    return format_object_ids(active_hour)

            # Try with string ID
            print(f"Trying lookup with string ID: {employee_id}")
            active_hour = await hours_collection.find_one({
                "employee_id": employee_id,
                "clock_out": None
            })
            if active_hour:
                print(f"Found active hour with string ID lookup")
                return format_object_ids(active_hour)

            # Try string comparison as last resort
            print("Trying string comparison for employee ID...")
            all_hours = await hours_collection.find({"clock_out": None}).to_list(length=100)
            for hour in all_hours:
                if str(hour.get("employee_id")) == employee_id:
                    print(f"Found active hour via string comparison")
                    return format_object_ids(hour)

            print(f"No active hour found for employee: {employee_id}")
            return None
        except Exception as e:
            print(f"Error getting active hour: {str(e)}")
            return None

    @staticmethod
    async def get_time_sheet_summary(
            employee_id: str,
            week_start: datetime
    ) -> TimeSheetSummary:
        """
        Get weekly timesheet summary for an employee with enhanced validation
        """
        try:
            print(f"Getting timesheet summary for employee: {employee_id}, week starting: {week_start}")

            # Calculate week boundaries
            week_end = week_start + timedelta(days=7)

            # Find employee using multiple strategies
            employee_obj_id = ensure_object_id(employee_id)

            # Build query based on available ID format
            query = {
                "clock_in": {"$gte": week_start, "$lt": week_end}
            }

            if employee_obj_id:
                query["employee_id"] = employee_obj_id
            else:
                query["employee_id"] = employee_id

            print(f"Query: {query}")
            cursor = hours_collection.find(query).sort("clock_in", 1)
            hours_records = await cursor.to_list(length=100)
            print(f"Found {len(hours_records)} hour records for the week")

            # If no records found with direct query, try string comparison
            if not hours_records and not employee_obj_id:
                print("No records found, trying string comparison...")
                all_hours = await hours_collection.find({
                    "clock_in": {"$gte": week_start, "$lt": week_end}
                }).to_list(length=100)

                hours_records = [
                    hour for hour in all_hours
                    if str(hour.get("employee_id")) == employee_id
                ]
                print(f"Found {len(hours_records)} records via string comparison")

            # Initialize summary data
            total_hours = 0
            approved_hours = 0
            pending_hours = 0
            daily_hours = {}

            # Get employee details
            employee = None
            if employee_obj_id:
                employee = await employees_collection.find_one({"_id": employee_obj_id})

            if not employee:
                # Try string lookup as fallback
                all_employees = await employees_collection.find().to_list(length=100)
                for emp in all_employees:
                    if str(emp.get('_id')) == employee_id:
                        employee = emp
                        break

            employee_name = "Unknown"
            if employee:
                # Try to get user data for name
                if employee.get("user_id"):
                    from app.services.user import get_user_by_id
                    user = await get_user_by_id(employee.get("user_id"))
                    if user:
                        employee_name = user.get("full_name", "Unknown")

            # Calculate summary
            for record in hours_records:
                minutes = record.get("total_minutes", 0) or 0
                hours = minutes / 60 if minutes else 0

                # Add to total
                total_hours += hours

                # Add to appropriate status total
                if record.get("status") == HoursStatus.APPROVED.value:
                    approved_hours += hours
                elif record.get("status") == HoursStatus.PENDING.value:
                    pending_hours += hours

                # Add to daily summary
                day_str = record.get("clock_in").strftime("%Y-%m-%d")
                daily_hours[day_str] = daily_hours.get(day_str, 0) + hours

            # Create summary object
            summary = TimeSheetSummary(
                employee_id=employee_id,
                employee_name=employee_name,
                total_hours=round(total_hours, 2),
                approved_hours=round(approved_hours, 2),
                pending_hours=round(pending_hours, 2),
                week_start_date=week_start,
                week_end_date=week_end,
                daily_hours={k: round(v, 2) for k, v in daily_hours.items()}
            )

            return summary
        except Exception as e:
            print(f"Error getting timesheet summary: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting timesheet summary: {str(e)}"
            )

    @staticmethod
    async def approve_hour(hour_id: str, approval_data: HourApproval, approver_id: str) -> Optional[Dict[str, Any]]:
        """
        Approve or reject an hour record with enhanced validation
        """
        try:
            print(f"Processing approval for hour record: {hour_id}")
            print(f"Approval data: {approval_data}")

            # Find the hour record using multiple lookup strategies
            hour = None
            hour_obj_id = None

            # 1. Try with ObjectId
            obj_id = ensure_object_id(hour_id)
            if obj_id:
                print(f"Looking up hour with ObjectId: {obj_id}")
                hour = await hours_collection.find_one({"_id": obj_id})
                if hour:
                    hour_obj_id = obj_id
                    print(f"Found hour with ObjectId")
                else:
                    print(f"No hour found with ObjectId")

            # 2. Try string ID lookup
            if not hour:
                print(f"Looking up hour with string ID: {hour_id}")
                hour = await hours_collection.find_one({"_id": hour_id})
                if hour:
                    hour_obj_id = hour["_id"]
                    print(f"Found hour with string ID")
                else:
                    print(f"No hour found with string ID")

            # 3. Try string comparison
            if not hour:
                print("Trying string comparison...")
                all_hours = await hours_collection.find().to_list(length=100)
                for h in all_hours:
                    if str(h.get('_id')) == hour_id:
                        hour = h
                        hour_obj_id = h["_id"]
                        print(f"Found hour by string comparison")
                        break

            if not hour:
                print(f"Hour record not found with ID: {hour_id}")
                return None

            # Check if already processed
            if hour.get("status") != HoursStatus.PENDING.value:
                print(f"Hour record already {hour.get('status')}: {hour_id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Hours record already {hour.get('status')}"
                )

            # Check if clock out time exists
            if not hour.get("clock_out"):
                print(f"Cannot approve hours without clock out: {hour_id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot approve an hours record without clock out time"
                )

            # Validate approver exists
            approver_obj_id = ensure_object_id(approver_id)
            if not approver_obj_id:
                approver_obj_id = approver_id

            from app.services.user import get_user_by_id
            approver = await get_user_by_id(approver_id)
            if not approver:
                print(f"Approver with ID {approver_id} not found")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Approver with ID {approver_id} not found"
                )

            # Update the approval status
            update_data = {
                "status": approval_data.status.value,
                "approved_by": approver_obj_id,
                "approved_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }

            if approval_data.notes:
                update_data["notes"] = approval_data.notes

            print(f"Updating hour record with approval status: {approval_data.status.value}")
            update_result = await hours_collection.update_one(
                {"_id": hour_obj_id},
                {"$set": update_data}
            )

            print(f"Update result: matched={update_result.matched_count}, modified={update_result.modified_count}")

            if update_result.matched_count == 0:
                print(f"No hour matched the ID: {hour_obj_id}")
                return None

            # Return the updated record
            updated_hour = await hours_collection.find_one({"_id": hour_obj_id})
            if updated_hour:
                print(f"Hour record {hour_id} approval status updated to: {approval_data.status.value}")
                return format_object_ids(updated_hour)

            print(f"Error retrieving updated hour record")
            return None
        except Exception as e:
            print(f"Error approving hour record: {str(e)}")
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error approving hour record: {str(e)}"
            )

    @staticmethod
    async def delete_hour(hour_id: str) -> bool:
        """
        Delete an hour record with enhanced validation
        """
        try:
            print(f"Attempting to delete hour record with ID: {hour_id}")

            # Find the hour record using multiple lookup strategies
            hour = None
            hour_obj_id = None

            # 1. Try with ObjectId
            obj_id = ensure_object_id(hour_id)
            if obj_id:
                print(f"Looking up hour with ObjectId: {obj_id}")
                hour = await hours_collection.find_one({"_id": obj_id})
                if hour:
                    hour_obj_id = obj_id
                    print(f"Found hour with ObjectId")
                else:
                    print(f"No hour found with ObjectId")

            # 2. Try string ID lookup
            if not hour:
                print(f"Looking up hour with string ID: {hour_id}")
                hour = await hours_collection.find_one({"_id": hour_id})
                if hour:
                    hour_obj_id = hour["_id"]
                    print(f"Found hour with string ID")
                else:
                    print(f"No hour found with string ID")

            # 3. Try string comparison
            if not hour:
                print("Trying string comparison...")
                all_hours = await hours_collection.find().to_list(length=100)
                for h in all_hours:
                    if str(h.get('_id')) == hour_id:
                        hour = h
                        hour_obj_id = h["_id"]
                        print(f"Found hour by string comparison")
                        break

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
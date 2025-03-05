# app/services/hours.py
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from bson import ObjectId
from fastapi import HTTPException, status

from app.core.db import get_database
from app.models.hours import HoursStatus
from app.schemas.hours import HourCreate, HourUpdate, HourApproval, TimeSheetSummary

# Get database connection once
db = get_database()


class HourService:
    @staticmethod
    async def create_hour(hour_data: HourCreate) -> Dict[str, Any]:
        """
        Create a new hours record
        """
        try:
            print(f"Creating hour record for employee: {hour_data.employee_id}")

            # Validate employee exists
            employee = await db.employees.find_one({"_id": ObjectId(hour_data.employee_id)})
            if not employee:
                print(f"Employee with ID {hour_data.employee_id} not found")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Employee with ID {hour_data.employee_id} not found"
                )

            # Validate store exists with flexible lookup
            store = await HourService.find_store(hour_data.store_id)
            if not store:
                print(f"Store with ID {hour_data.store_id} not found")
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

            # Convert model to dict
            hour_dict = hour_data.model_dump(by_alias=True)

            # Store IDs in database format
            hour_dict["employee_id"] = employee["_id"]
            hour_dict["store_id"] = store["_id"]

            hour_dict.update({
                "total_minutes": total_minutes,
                "status": HoursStatus.PENDING.value,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            })

            # Insert into database
            result = await db.hours.insert_one(hour_dict)
            print(f"Hour record created with ID: {result.inserted_id}")

            # Get the newly created record
            if result.inserted_id:
                new_hour = await db.hours.find_one({"_id": result.inserted_id})
                # Convert ObjectIds to strings for response
                return HourService.format_hour_record(new_hour)

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
        Get hour record by ID
        """
        try:
            print(f"Getting hour record with ID: {hour_id}")

            # List all hours for debugging
            all_hours = await db.hours.find().to_list(length=100)
            all_ids = [str(hour.get('_id')) for hour in all_hours]
            print(f"All hour IDs in database: {all_ids}")

            # Try with ObjectId
            try:
                object_id = ObjectId(hour_id)
                hour = await db.hours.find_one({"_id": object_id})
                if hour:
                    print(f"Found hour record with ObjectId")
                    return HourService.format_hour_record(hour)
            except Exception as e:
                print(f"Error looking up hour with ObjectId: {str(e)}")

            # Try string comparison
            for db_hour in all_hours:
                if str(db_hour.get('_id')) == hour_id:
                    print(f"Found hour record by string comparison")
                    return HourService.format_hour_record(db_hour)

            print(f"Hour record not found with ID: {hour_id}")
            return None
        except Exception as e:
            print(f"Error getting hour record: {str(e)}")
            return None

    @staticmethod
    async def update_hour(hour_id: str, hour_data: HourUpdate, current_user_id: str) -> Optional[Dict[str, Any]]:
        """
        Update an hour record
        """
        try:
            print(f"Updating hour record with ID: {hour_id}")

            # Get the current record
            current_hour = await db.hours.find_one({"_id": ObjectId(hour_id)})
            if not current_hour:
                print(f"Hour record not found with ID: {hour_id}")
                return None

            # Check if record is already approved
            if current_hour.get("status") == HoursStatus.APPROVED.value:
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
                clock_in = current_hour["clock_in"]
                break_start = update_data.get("break_start", current_hour.get("break_start"))
                break_end = update_data.get("break_end", current_hour.get("break_end"))

                update_data["total_minutes"] = HourService.calculate_work_minutes(
                    clock_in,
                    hour_data.clock_out,
                    break_start,
                    break_end
                )

            # Update the record
            await db.hours.update_one(
                {"_id": ObjectId(hour_id)},
                {"$set": update_data}
            )
            print(f"Hour record updated: {hour_id}")

            # Return the updated record
            updated_hour = await db.hours.find_one({"_id": ObjectId(hour_id)})
            if updated_hour:
                return HourService.format_hour_record(updated_hour)

            return None
        except Exception as e:
            print(f"Error updating hour record: {str(e)}")
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error updating hour record: {str(e)}"
            )

    # ...rest of the methods remain the same, just replace any instance of
    # "db = await HourService.get_database()" with the global db instance

    @staticmethod
    async def find_store(store_id: str) -> Optional[Dict[str, Any]]:
        """
        Find store with flexible ID format support
        """
        print(f"Looking for store with ID: {store_id}")

        # List all stores for debugging
        all_stores = await db.stores.find().to_list(length=100)
        store_ids = [str(s.get('_id')) for s in all_stores]
        print(f"All store IDs: {store_ids}")

        # Try with ObjectId first
        try:
            store = await db.stores.find_one({"_id": ObjectId(store_id)})
            if store:
                print(f"Found store by ObjectId: {store.get('name')}")
                return store
        except Exception as e:
            print(f"Error looking up store with ObjectId: {str(e)}")

        # Try with string ID directly
        store = await db.stores.find_one({"_id": store_id})
        if store:
            print(f"Found store by string ID: {store.get('name')}")
            return store

        # Try by string comparison
        for s in all_stores:
            if str(s.get("_id")) == store_id:
                print(f"Found store by string comparison: {s.get('name')}")
                return s

        print(f"Store not found with ID: {store_id}")
        return None

    @staticmethod
    def format_hour_record(hour: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format hour record by converting ObjectIds to strings
        """
        if not hour:
            return {}

        formatted = dict(hour)
        formatted["_id"] = str(formatted["_id"])
        formatted["employee_id"] = str(formatted["employee_id"])
        formatted["store_id"] = str(formatted["store_id"])

        if formatted.get("approved_by"):
            formatted["approved_by"] = str(formatted["approved_by"])

        return formatted

    # Add this method to HourService class
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

    # Add this method to HourService class
    @staticmethod
    async def clock_in(employee_id: str, store_id: str, notes: Optional[str] = None) -> Dict[str, Any]:
        """
        Clock in an employee
        """
        try:
            print(f"Clocking in employee: {employee_id} at store: {store_id}")

            # Check if employee is already clocked in
            active_shift = await db.hours.find_one({
                "employee_id": ObjectId(employee_id),
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
                employee_id=employee_id,
                store_id=store_id,
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
        Clock out an employee
        """
        try:
            print(f"Clocking out employee: {employee_id}")

            # Find the active shift
            active_shift = await db.hours.find_one({
                "employee_id": ObjectId(employee_id),
                "clock_out": None
            })

            if not active_shift:
                print(f"No active shift found for employee: {employee_id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No active shift found for employee"
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
            await db.hours.update_one(
                {"_id": active_shift["_id"]},
                {
                    "$set": {
                        "clock_out": clock_out_time,
                        "break_start": break_start,
                        "break_end": break_end,
                        "notes": notes or active_shift.get("notes"),
                        "total_minutes": total_minutes,
                        "updated_at": datetime.utcnow()
                    }
                }
            )

            # Return the updated record
            updated_hour = await db.hours.find_one({"_id": active_shift["_id"]})
            if updated_hour:
                print(f"Employee {employee_id} clocked out successfully")
                return HourService.format_hour_record(updated_hour)

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
    async def approve_hour(hour_id: str, approval_data: HourApproval, approver_id: str) -> Optional[Dict[str, Any]]:
        """
        Approve or reject an hour record
        """
        try:
            print(f"Approving hour record: {hour_id}")

            # Get the current record
            current_hour = await db.hours.find_one({"_id": ObjectId(hour_id)})
            if not current_hour:
                print(f"Hour record not found: {hour_id}")
                return None

            # Check if already processed
            if current_hour.get("status") != HoursStatus.PENDING.value:
                print(f"Hour record already {current_hour.get('status')}: {hour_id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Hours record already {current_hour.get('status')}"
                )

            # Check if clock out time exists
            if not current_hour.get("clock_out"):
                print(f"Cannot approve hours without clock out: {hour_id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot approve an hours record without clock out time"
                )

            # Update the approval status
            await db.hours.update_one(
                {"_id": ObjectId(hour_id)},
                {
                    "$set": {
                        "status": approval_data.status.value,
                        "approved_by": ObjectId(approver_id),
                        "approved_at": datetime.utcnow(),
                        "notes": approval_data.notes or current_hour.get("notes"),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            print(f"Hour record {hour_id} approval status updated to: {approval_data.status.value}")

            # Return the updated record
            updated_hour = await db.hours.find_one({"_id": ObjectId(hour_id)})
            if updated_hour:
                return HourService.format_hour_record(updated_hour)

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
        Delete an hour record
        """
        try:
            print(f"Deleting hour record: {hour_id}")

            # Get the current record
            current_hour = await db.hours.find_one({"_id": ObjectId(hour_id)})
            if not current_hour:
                print(f"Hour record not found: {hour_id}")
                return False

            # Check if already approved
            if current_hour.get("status") == HoursStatus.APPROVED.value:
                print(f"Cannot delete approved hour record: {hour_id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot delete an approved hours record"
                )

            # Delete the record
            result = await db.hours.delete_one({"_id": ObjectId(hour_id)})
            print(f"Hour record deleted: {result.deleted_count > 0}")
            return result.deleted_count > 0
        except Exception as e:
            print(f"Error deleting hour record: {str(e)}")
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error deleting hour record: {str(e)}"
            )

    @staticmethod
    async def get_hours(
            employee_id: Optional[str] = None,
            store_id: Optional[str] = None,
            start_date: Optional[datetime] = None,
            end_date: Optional[datetime] = None,
            status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get hours records with filtering options
        """
        try:
            print(f"Getting hours with filters: employee={employee_id}, store={store_id}, status={status}")

            # Build query filters
            query = {}

            if employee_id:
                query["employee_id"] = ObjectId(employee_id)

            if store_id:
                query["store_id"] = ObjectId(store_id)

            if start_date:
                query["clock_in"] = {"$gte": start_date}

            if end_date:
                if "clock_in" in query:
                    query["clock_in"]["$lte"] = end_date
                else:
                    query["clock_in"] = {"$lte": end_date}

            if status:
                query["status"] = status

            # Get records
            cursor = db.hours.find(query).sort("clock_in", -1)
            hours_records = await cursor.to_list(length=100)
            print(f"Found {len(hours_records)} hour records")

            # Format records
            return [HourService.format_hour_record(record) for record in hours_records]
        except Exception as e:
            print(f"Error getting hours: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting hours: {str(e)}"
            )

    @staticmethod
    async def get_active_hour(employee_id: str) -> Optional[Dict[str, Any]]:
        """
        Get active hour record for an employee
        """
        try:
            print(f"Getting active hour for employee: {employee_id}")

            # Try with ObjectId
            try:
                active_hour = await db.hours.find_one({
                    "employee_id": ObjectId(employee_id),
                    "clock_out": None
                })
            except Exception as e:
                print(f"Error with ObjectId lookup: {str(e)}")
                active_hour = None

            # If not found, try with string comparison
            if not active_hour:
                # Get all hours
                all_hours = await db.hours.find({"clock_out": None}).to_list(length=100)
                # Find the one for this employee
                for hour in all_hours:
                    if str(hour.get("employee_id")) == employee_id:
                        active_hour = hour
                        break

            if active_hour:
                print(f"Found active hour for employee: {employee_id}")
                return HourService.format_hour_record(active_hour)

            print(f"No active hour found for employee: {employee_id}")
            return None
        except Exception as e:
            print(f"Error getting active hour: {str(e)}")
            return None

    @staticmethod
    async def get_hours_with_details(
            query: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Get hours records with employee and store details
        """
        try:
            print(f"Getting hours with details, query: {query}")

            # Get records
            cursor = db.hours.find(query).sort("clock_in", -1)
            hours_records = await cursor.to_list(length=100)
            print(f"Found {len(hours_records)} hour records")

            # Process records and add details
            result = []
            for record in hours_records:
                formatted_record = HourService.format_hour_record(record)

                # Add employee details
                employee = await db.employees.find_one({"_id": ObjectId(record["employee_id"])})
                if employee:
                    formatted_record["employee_name"] = employee.get("full_name", "Unknown")

                # Add store details
                store = await db.stores.find_one({"_id": ObjectId(record["store_id"])})
                if store:
                    formatted_record["store_name"] = store.get("name", "Unknown")

                result.append(formatted_record)

            return result
        except Exception as e:
            print(f"Error getting hours with details: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting hours with details: {str(e)}"
            )

    @staticmethod
    async def get_time_sheet_summary(
            employee_id: str,
            week_start: datetime
    ) -> TimeSheetSummary:
        """
        Get weekly timesheet summary for an employee
        """
        try:
            print(f"Getting timesheet summary for employee: {employee_id}, week starting: {week_start}")

            # Calculate week boundaries
            week_end = week_start + timedelta(days=7)

            # Get all hours for the week
            query = {
                "employee_id": ObjectId(employee_id),
                "clock_in": {"$gte": week_start, "$lt": week_end}
            }

            cursor = db.hours.find(query).sort("clock_in", 1)
            hours_records = await cursor.to_list(length=100)
            print(f"Found {len(hours_records)} hour records for the week")

            # Initialize summary data
            total_hours = 0
            approved_hours = 0
            pending_hours = 0
            daily_hours = {}

            # Get employee details
            employee = await db.employees.find_one({"_id": ObjectId(employee_id)})
            employee_name = employee.get("full_name", "Unknown") if employee else "Unknown"

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
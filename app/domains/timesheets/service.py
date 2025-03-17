"""
Timesheet service for business logic.
"""
from typing import Dict, List, Optional, Any
from datetime import date, datetime, timedelta
from fastapi import HTTPException, status

from app.domains.timesheets.repository import TimesheetRepository
from app.domains.employees.service import employee_service
from app.domains.stores.service import store_service
from app.domains.users.service import user_service
from app.utils.id_handler import IdHandler
from app.utils.datetime_handler import DateTimeHandler
from app.schemas.timesheet import TimesheetStatus


class TimesheetService:
    """
    Service for timesheet-related business logic.
    """

    def __init__(self, timesheet_repo: Optional[TimesheetRepository] = None):
        """
        Initialize with timesheet repository.

        Args:
            timesheet_repo: Optional timesheet repository instance
        """
        self.timesheet_repo = timesheet_repo or TimesheetRepository()

    async def get_timesheets(
            self,
            skip: int = 0,
            limit: int = 100,
            employee_id: Optional[str] = None,
            store_id: Optional[str] = None,
            status: Optional[str] = None,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Get timesheets with optional filtering.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            employee_id: Filter by employee ID
            store_id: Filter by store ID
            status: Filter by status
            start_date: Filter by start date
            end_date: Filter by end date

        Returns:
            List of timesheet documents
        """
        # Build query
        query = {}

        if employee_id:
            employee_obj_id = IdHandler.ensure_object_id(employee_id)
            if employee_obj_id:
                query["employee_id"] = employee_obj_id
            else:
                query["employee_id"] = employee_id

        if store_id:
            store_obj_id = IdHandler.ensure_object_id(store_id)
            if store_obj_id:
                query["store_id"] = store_obj_id
            else:
                query["store_id"] = store_id

        if status:
            # Handle multiple statuses (comma-separated)
            if "," in status:
                statuses = [s.strip() for s in status.split(",")]
                query["status"] = {"$in": statuses}
            else:
                query["status"] = status

        if start_date:
            start_datetime = DateTimeHandler.date_to_datetime(start_date)
            query["week_end_date"] = {"$gte": start_datetime}

        if end_date:
            end_datetime = DateTimeHandler.date_to_datetime(end_date, set_to_end_of_day=True)
            if "week_end_date" in query:
                query["week_start_date"] = {"$lte": end_datetime}
            else:
                query["week_start_date"] = {"$lte": end_datetime}

        # Get timesheets
        timesheets = await self.timesheet_repo.find_many(query, skip, limit)

        # Enrich with employee and store info
        result = []
        for timesheet in timesheets:
            timesheet_with_info = await self._enrich_timesheet_data(timesheet)
            result.append(timesheet_with_info)

        return result

    async def get_timesheet(self, timesheet_id: str) -> Optional[Dict[str, Any]]:
        """
        Get timesheet by ID.

        Args:
            timesheet_id: Timesheet ID

        Returns:
            Timesheet document or None if not found
        """
        timesheet = await self.timesheet_repo.find_by_id(timesheet_id)

        if not timesheet:
            return None

        # Enrich with employee and store info
        return await self._enrich_timesheet_data(timesheet)

    async def get_timesheets_by_employee(
            self,
            employee_id: str,
            status: Optional[str] = None,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Get timesheets for a specific employee.

        Args:
            employee_id: Employee ID
            status: Filter by status
            start_date: Filter by start date
            end_date: Filter by end date

        Returns:
            List of timesheet documents
        """
        # Get all timesheets for this employee
        timesheets = await self.timesheet_repo.find_by_employee(employee_id)

        # Apply filters
        filtered_timesheets = []

        for timesheet in timesheets:
            include = True

            if status:
                # Handle multiple statuses (comma-separated)
                if "," in status:
                    statuses = [s.strip() for s in status.split(",")]
                    if timesheet.get("status") not in statuses:
                        include = False
                elif timesheet.get("status") != status:
                    include = False

            if start_date:
                timesheet_end = timesheet.get("week_end_date")
                if isinstance(timesheet_end, datetime):
                    timesheet_end = timesheet_end.date()

                if timesheet_end < start_date:
                    include = False

            if end_date:
                timesheet_start = timesheet.get("week_start_date")
                if isinstance(timesheet_start, datetime):
                    timesheet_start = timesheet_start.date()

                if timesheet_start > end_date:
                    include = False

            if include:
                filtered_timesheets.append(timesheet)

        # Enrich with employee and store info
        result = []
        for timesheet in filtered_timesheets:
            timesheet_with_info = await self._enrich_timesheet_data(timesheet)
            result.append(timesheet_with_info)

        # Sort by week_start_date (descending)
        result.sort(key=lambda x: x.get("week_start_date", ""), reverse=True)

        return result

    async def get_current_week_timesheet(self, employee_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current week's timesheet for an employee.

        Args:
            employee_id: Employee ID

        Returns:
            Timesheet document or None if not found
        """
        # Calculate current week's start date (Monday)
        week_start_date, _ = DateTimeHandler.get_week_boundaries(DateTimeHandler.get_current_date())

        # Find timesheet for current week
        timesheet = await self.timesheet_repo.find_by_employee_and_week(employee_id, week_start_date)

        if not timesheet:
            return None

        # Enrich with employee and store info
        return await self._enrich_timesheet_data(timesheet)

    async def create_timesheet(self, timesheet_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new timesheet.

        Args:
            timesheet_data: Timesheet data

        Returns:
            Created timesheet document

        Raises:
            HTTPException: If validation fails
        """
        # Validate employee
        employee_id = timesheet_data.get("employee_id")
        employee = await employee_service.get_employee(employee_id)
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Employee with ID {employee_id} not found"
            )

        # Validate store
        store_id = timesheet_data.get("store_id")
        store = await store_service.get_store(store_id)
        if not store:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Store with ID {store_id} not found"
            )

        # Convert week_start_date to date object if string
        if isinstance(timesheet_data.get("week_start_date"), str):
            week_start_date = DateTimeHandler.parse_date(timesheet_data["week_start_date"])
            if not week_start_date:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid week_start_date format: {timesheet_data['week_start_date']}"
                )

            timesheet_data["week_start_date"] = week_start_date

        # Check if timesheet already exists for this employee and week
        existing_timesheet = await self.timesheet_repo.find_by_employee_and_week(
            employee_id,
            timesheet_data["week_start_date"]
        )

        if existing_timesheet:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Timesheet already exists for employee {employee_id} for week starting {timesheet_data['week_start_date']}"
            )

        # Calculate week_end_date if not provided
        if "week_end_date" not in timesheet_data:
            week_start_date = timesheet_data["week_start_date"]
            week_end_date = week_start_date + timedelta(days=6)
            timesheet_data["week_end_date"] = week_end_date

        # Create default daily_hours if not provided
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
        hourly_rate = timesheet_data.get("hourly_rate", 0)

        # If hourly_rate not provided, get from employee
        if not hourly_rate and employee:
            hourly_rate = employee.get("hourly_rate", 0)
            timesheet_data["hourly_rate"] = hourly_rate

        total_earnings = round(total_hours * hourly_rate, 2)

        timesheet_data["total_hours"] = total_hours
        timesheet_data["total_earnings"] = total_earnings
        timesheet_data["status"] = TimesheetStatus.DRAFT

        # Create timesheet
        created_timesheet = await self.timesheet_repo.create(timesheet_data)

        # Enrich with employee and store info
        return await self._enrich_timesheet_data(created_timesheet)

    async def create_or_get_current_timesheet(self, employee_id: str, store_id: str) -> Dict[str, Any]:
        """
        Create a new timesheet for the current week or get existing one.

        Args:
            employee_id: Employee ID
            store_id: Store ID

        Returns:
            Timesheet document

        Raises:
            HTTPException: If validation fails
        """
        # Calculate current week's start date (Monday)
        week_start_date, week_end_date = DateTimeHandler.get_week_boundaries(DateTimeHandler.get_current_date())

        # Check if timesheet already exists
        existing_timesheet = await self.timesheet_repo.find_by_employee_and_week(employee_id, week_start_date)

        if existing_timesheet:
            # Enrich with employee and store info
            return await self._enrich_timesheet_data(existing_timesheet)

        # Get employee info
        employee = await employee_service.get_employee(employee_id)
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Employee with ID {employee_id} not found"
            )

        # Get store info
        store = await store_service.get_store(store_id)
        if not store:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Store with ID {store_id} not found"
            )

        # Create timesheet data
        timesheet_data = {
            "employee_id": employee_id,
            "store_id": store_id,
            "week_start_date": week_start_date,
            "week_end_date": week_end_date,
            "hourly_rate": employee.get("hourly_rate", 0),
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
            "status": TimesheetStatus.DRAFT
        }

        # Create timesheet
        created_timesheet = await self.timesheet_repo.create(timesheet_data)

        # Enrich with employee and store info
        return await self._enrich_timesheet_data(created_timesheet)

    async def update_timesheet(self, timesheet_id: str, timesheet_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update an existing timesheet.

        Args:
            timesheet_id: Timesheet ID
            timesheet_data: Updated timesheet data

        Returns:
            Updated timesheet document or None if not found

        Raises:
            HTTPException: If validation fails
        """
        # Check if timesheet exists
        existing_timesheet = await self.timesheet_repo.find_by_id(timesheet_id)
        if not existing_timesheet:
            return None

        # Check if timesheet is in draft or rejected status
        current_status = existing_timesheet.get("status")
        if current_status not in [TimesheetStatus.DRAFT, TimesheetStatus.REJECTED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot update timesheet in {current_status} status"
            )

        # Update daily_hours if provided
        if "daily_hours" in timesheet_data:
            # Validate daily hours
            for day, hours in timesheet_data["daily_hours"].items():
                if day not in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid day: {day}"
                    )

                if hours < 0 or hours > 24:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Hours must be between 0 and 24 for {day}"
                    )

            # Merge with existing daily hours
            daily_hours = existing_timesheet.get("daily_hours", {}).copy()
            for day, hours in timesheet_data["daily_hours"].items():
                daily_hours[day] = hours

            # Calculate total hours and earnings
            total_hours = sum(daily_hours.values())
            hourly_rate = existing_timesheet.get("hourly_rate", 0)
            total_earnings = round(total_hours * hourly_rate, 2)

            # Update the data
            timesheet_data["daily_hours"] = daily_hours
            timesheet_data["total_hours"] = total_hours
            timesheet_data["total_earnings"] = total_earnings

        # Update the timesheet
        updated_timesheet = await self.timesheet_repo.update(timesheet_id, timesheet_data)

        if not updated_timesheet:
            return None

        # Enrich with employee and store info
        return await self._enrich_timesheet_data(updated_timesheet)

    async def update_daily_hours(self, timesheet_id: str, day: str, hours: float) -> Optional[Dict[str, Any]]:
        """
        Update hours for a specific day in a timesheet.

        Args:
            timesheet_id: Timesheet ID
            day: Day of the week (monday, tuesday, etc.)
            hours: Hours for the day

        Returns:
            Updated timesheet document or None if not found

        Raises:
            HTTPException: If validation fails
        """
        # Check if timesheet exists
        existing_timesheet = await self.timesheet_repo.find_by_id(timesheet_id)
        if not existing_timesheet:
            return None

        # Check if timesheet is in draft or rejected status
        current_status = existing_timesheet.get("status")
        if current_status not in [TimesheetStatus.DRAFT, TimesheetStatus.REJECTED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot update timesheet in {current_status} status"
            )

        # Validate day
        if day not in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid day: {day}"
            )

        # Validate hours
        if hours < 0 or hours > 24:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Hours must be between 0 and 24"
            )

        # Update daily hours
        updated_timesheet = await self.timesheet_repo.update_daily_hours(timesheet_id, day, hours)

        if not updated_timesheet:
            return None

        # Enrich with employee and store info
        return await self._enrich_timesheet_data(updated_timesheet)

    async def submit_timesheet(self, timesheet_id: str, notes: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Submit a timesheet for approval.

        Args:
            timesheet_id: Timesheet ID
            notes: Submission notes

        Returns:
            Updated timesheet document or None if not found

        Raises:
            HTTPException: If validation fails
        """
        # Check if timesheet exists
        existing_timesheet = await self.timesheet_repo.find_by_id(timesheet_id)
        if not existing_timesheet:
            return None

        # Check if timesheet is in draft or rejected status
        current_status = existing_timesheet.get("status")
        if current_status not in [TimesheetStatus.DRAFT, TimesheetStatus.REJECTED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot submit timesheet in {current_status} status"
            )

        # Submit timesheet
        submitted_timesheet = await self.timesheet_repo.submit_timesheet(timesheet_id, notes)

        if not submitted_timesheet:
            return None

        # Enrich with employee and store info
        return await self._enrich_timesheet_data(submitted_timesheet)

    async def approve_timesheet(
            self,
            timesheet_id: str,
            approver_id: str,
            status: str,
            notes: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Approve or reject a timesheet.

        Args:
            timesheet_id: Timesheet ID
            approver_id: Approver user ID
            status: New status (approved or rejected)
            notes: Approval/rejection notes

        Returns:
            Updated timesheet document or None if not found

        Raises:
            HTTPException: If validation fails
        """
        # Check if timesheet exists
        existing_timesheet = await self.timesheet_repo.find_by_id(timesheet_id)
        if not existing_timesheet:
            return None

        # Check if timesheet is in submitted status
        current_status = existing_timesheet.get("status")
        if current_status != TimesheetStatus.SUBMITTED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot approve/reject timesheet in {current_status} status"
            )

        # Validate status
        if status not in [TimesheetStatus.APPROVED, TimesheetStatus.REJECTED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}. Must be 'approved' or 'rejected'"
            )

        # Approve/reject timesheet
        updated_timesheet = await self.timesheet_repo.approve_timesheet(
            timesheet_id=timesheet_id,
            approver_id=approver_id,
            status=status,
            notes=notes
        )

        if not updated_timesheet:
            return None

        # Enrich with employee and store info
        return await self._enrich_timesheet_data(updated_timesheet)

    async def delete_timesheet(self, timesheet_id: str) -> bool:
        """
        Delete a timesheet.

        Args:
            timesheet_id: Timesheet ID

        Returns:
            True if timesheet was deleted

        Raises:
            HTTPException: If deletion fails
        """
        # Check if timesheet exists
        existing_timesheet = await self.timesheet_repo.find_by_id(timesheet_id)
        if not existing_timesheet:
            return False

        # Check if timesheet is in draft or rejected status
        current_status = existing_timesheet.get("status")
        if current_status not in [TimesheetStatus.DRAFT, TimesheetStatus.REJECTED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete timesheet in {current_status} status"
            )

        # Delete timesheet
        return await self.timesheet_repo.delete(timesheet_id)

    async def _enrich_timesheet_data(self, timesheet: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich timesheet data with employee and store information.

        Args:
            timesheet: Timesheet document

        Returns:
            Enriched timesheet document
        """
        if not timesheet:
            return {}

        timesheet_with_info = dict(timesheet)

        # Add employee info if available
        if timesheet.get("employee_id"):
            employee = await employee_service.get_employee(timesheet["employee_id"])
            if employee:
                timesheet_with_info["employee_name"] = employee.get("full_name")

        # Add store info if available
        if timesheet.get("store_id"):
            store = await store_service.get_store(timesheet["store_id"])
            if store:
                timesheet_with_info["store_name"] = store.get("name")

        # Add payment info if available
        if timesheet.get("payment_id"):
            # We'll need to import the payment service here to avoid circular imports
            from app.domains.payments.service import payment_service
            payment = await payment_service.get_payment(timesheet["payment_id"])
            if payment:
                timesheet_with_info["payment_status"] = payment.get("status")

        return timesheet_with_info


# Create global instance
timesheet_service = TimesheetService()
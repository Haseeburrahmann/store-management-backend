"""
Schedule service for business logic.
"""
from typing import Dict, List, Optional, Any
from datetime import date, datetime, timedelta
from fastapi import HTTPException, status

from app.domains.schedules.repository import ScheduleRepository
from app.domains.employees.service import employee_service
from app.domains.stores.service import store_service
from app.domains.users.service import user_service
from app.utils.id_handler import IdHandler
from app.utils.datetime_handler import DateTimeHandler


class ScheduleService:
    """
    Service for schedule-related business logic.
    """

    def __init__(self, schedule_repo: Optional[ScheduleRepository] = None):
        """
        Initialize with schedule repository.

        Args:
            schedule_repo: Optional schedule repository instance
        """
        self.schedule_repo = schedule_repo or ScheduleRepository()

    async def get_schedules(
            self,
            skip: int = 0,
            limit: int = 100,
            store_id: Optional[str] = None,
            week_start_date: Optional[date] = None,
            include_details: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get schedules with optional filtering.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            store_id: Filter by store ID
            week_start_date: Filter by week start date
            include_details: Include additional details about employees and stores

        Returns:
            List of schedule documents
        """
        # Build query
        query = {}

        if store_id:
            store_obj_id = IdHandler.ensure_object_id(store_id)
            if store_obj_id:
                query["store_id"] = store_obj_id
            else:
                query["store_id"] = store_id

        if week_start_date:
            # Convert date to datetime for MongoDB
            start_datetime = DateTimeHandler.date_to_datetime(week_start_date)
            query["week_start_date"] = start_datetime

        # Get schedules
        schedules = await self.schedule_repo.find_many(query, skip, limit)

        # Transform to schedule summaries or detailed schedules
        result = []
        for schedule in schedules:
            if include_details:
                # Get full details
                schedule_with_details = await self._enrich_schedule_data(schedule)
                result.append(schedule_with_details)
            else:
                # Create summary
                schedule_summary = {
                    "_id": schedule["_id"],
                    "store_id": schedule["store_id"],
                    "title": schedule["title"],
                    "week_start_date": schedule["week_start_date"],
                    "week_end_date": schedule["week_end_date"],
                    "shift_count": len(schedule.get("shifts", [])),
                    "created_at": schedule["created_at"]
                }

                # Add store name if available
                store = await store_service.get_store(schedule["store_id"])
                if store:
                    schedule_summary["store_name"] = store.get("name")

                result.append(schedule_summary)

        return result

    async def get_schedule(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        """
        Get schedule by ID.

        Args:
            schedule_id: Schedule ID

        Returns:
            Schedule document or None if not found
        """
        schedule = await self.schedule_repo.find_by_id(schedule_id)

        if not schedule:
            return None

        # Enrich with additional data
        return await self._enrich_schedule_data(schedule)

    async def get_schedules_by_store(
            self,
            store_id: str,
            week_start_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Get schedules for a specific store.

        Args:
            store_id: Store ID
            week_start_date: Filter by week start date

        Returns:
            List of schedule documents
        """
        # Build query
        query = {"store_id": store_id}

        if week_start_date:
            # Convert date to datetime for MongoDB
            start_datetime = DateTimeHandler.date_to_datetime(week_start_date)
            query["week_start_date"] = start_datetime

        # Get schedules
        schedules = await self.schedule_repo.find_many(query)

        # Create summaries
        result = []
        for schedule in schedules:
            schedule_summary = {
                "_id": schedule["_id"],
                "store_id": schedule["store_id"],
                "title": schedule["title"],
                "week_start_date": schedule["week_start_date"],
                "week_end_date": schedule["week_end_date"],
                "shift_count": len(schedule.get("shifts", [])),
                "created_at": schedule["created_at"]
            }

            # Add store name
            store = await store_service.get_store(store_id)
            if store:
                schedule_summary["store_name"] = store.get("name")

            result.append(schedule_summary)

        return result

    async def get_employee_schedule(
            self,
            employee_id: str,
            week_start_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Get schedule information for a specific employee.

        Args:
            employee_id: Employee ID
            week_start_date: Filter by week start date

        Returns:
            List of shift information for the employee
        """
        # Get current week if not specified
        if not week_start_date:
            week_start_date, _ = DateTimeHandler.get_week_boundaries(DateTimeHandler.get_current_date())

        # Find all schedules that might contain this employee's shifts
        schedules = await self.schedule_repo.find_with_employee_shifts(employee_id)

        # Filter schedules by week if specified
        if week_start_date:
            start_datetime = DateTimeHandler.date_to_datetime(week_start_date)
            schedules = [
                s for s in schedules
                if isinstance(s.get("week_start_date"), datetime) and
                   s["week_start_date"].date() == week_start_date
            ]

        # Extract shifts for this employee
        employee_shifts = []
        for schedule in schedules:
            # Get store info
            store = await store_service.get_store(schedule.get("store_id"))
            store_name = store.get("name") if store else "Unknown Store"

            for shift in schedule.get("shifts", []):
                if str(shift.get("employee_id")) == employee_id:
                    shift_info = dict(shift)
                    shift_info["schedule_id"] = schedule["_id"]
                    shift_info["schedule_title"] = schedule.get("title")
                    shift_info["store_id"] = schedule.get("store_id")
                    shift_info["store_name"] = store_name
                    shift_info["week_start_date"] = schedule.get("week_start_date")
                    shift_info["week_end_date"] = schedule.get("week_end_date")

                    # Format the shift info (convert ObjectIds to strings)
                    employee_shifts.append(IdHandler.format_object_ids(shift_info))

        return employee_shifts

    async def get_all_employee_schedules(
            self,
            employee_id: str,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None,
            skip: int = 0,
            limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get all schedules containing shifts for a specific employee with date range filtering.

        Args:
            employee_id: Employee ID
            start_date: Start date for filtering
            end_date: End date for filtering
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of schedule summaries
        """
        # Find all schedules with this employee's shifts
        schedules = await self.schedule_repo.find_with_employee_shifts(employee_id)

        # Filter by date range if specified
        if start_date or end_date:
            filtered_schedules = []

            for schedule in schedules:
                schedule_start = schedule.get("week_start_date")
                if isinstance(schedule_start, datetime):
                    schedule_start = schedule_start.date()

                include = True

                if start_date and schedule_start < start_date:
                    include = False

                if end_date:
                    schedule_end = schedule.get("week_end_date")
                    if isinstance(schedule_end, datetime):
                        schedule_end = schedule_end.date()

                    if schedule_end > end_date:
                        include = False

                if include:
                    filtered_schedules.append(schedule)

            schedules = filtered_schedules

        # Apply pagination
        schedules = schedules[skip:skip + limit]

        # Process each schedule to include only shifts for this employee
        result = []
        for schedule in schedules:
            schedule_with_info = dict(schedule)

            # Filter shifts for this employee
            employee_shifts = []
            for shift in schedule.get("shifts", []):
                if str(shift.get("employee_id")) == employee_id:
                    # Add employee name to shift
                    shift_with_info = dict(shift)
                    employee = await employee_service.get_employee(employee_id)
                    if employee:
                        shift_with_info["employee_name"] = employee.get("full_name")

                    employee_shifts.append(shift_with_info)

            schedule_with_info["shifts"] = employee_shifts
            schedule_with_info["shift_count"] = len(employee_shifts)

            # Add store name
            store = await store_service.get_store(schedule.get("store_id"))
            if store:
                schedule_with_info["store_name"] = store.get("name")

            # Format all IDs
            schedule_with_info = IdHandler.format_object_ids(schedule_with_info)
            result.append(schedule_with_info)

        return result

    async def create_schedule(self, schedule_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new schedule.

        Args:
            schedule_data: Schedule data

        Returns:
            Created schedule document

        Raises:
            HTTPException: If validation fails
        """
        # Validate store
        if "store_id" in schedule_data:
            store = await store_service.get_store(schedule_data["store_id"])
            if not store:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Store with ID {schedule_data['store_id']} not found"
                )

        # Set week_end_date if not provided
        if "week_start_date" in schedule_data and "week_end_date" not in schedule_data:
            start_date = schedule_data["week_start_date"]
            if isinstance(start_date, str):
                start_date = DateTimeHandler.parse_date(start_date)

            end_date = start_date + timedelta(days=6)
            schedule_data["week_end_date"] = end_date

        # Validate shifts if provided
        if "shifts" in schedule_data and schedule_data["shifts"]:
            valid_shifts = []

            for shift in schedule_data["shifts"]:
                # Validate employee
                employee_id = shift.get("employee_id")
                employee = await employee_service.get_employee(employee_id)
                if not employee:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Employee with ID {employee_id} not found"
                    )

                # Add ID to shift if not provided
                if "_id" not in shift:
                    shift["_id"] = IdHandler.generate_id()

                valid_shifts.append(shift)

            schedule_data["shifts"] = valid_shifts
        else:
            # Initialize empty shifts array
            schedule_data["shifts"] = []

        # Create schedule
        created_schedule = await self.schedule_repo.create(schedule_data)

        # Enrich with additional data
        return await self._enrich_schedule_data(created_schedule)

    async def update_schedule(self, schedule_id: str, schedule_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update an existing schedule.

        Args:
            schedule_id: Schedule ID
            schedule_data: Updated schedule data

        Returns:
            Updated schedule document or None if not found

        Raises:
            HTTPException: If validation fails
        """
        # Check if schedule exists
        existing_schedule = await self.schedule_repo.find_by_id(schedule_id)
        if not existing_schedule:
            return None

        # Validate shifts if provided
        if "shifts" in schedule_data and schedule_data["shifts"] is not None:
            valid_shifts = []

            for shift in schedule_data["shifts"]:
                # Validate employee
                employee_id = shift.get("employee_id")
                employee = await employee_service.get_employee(employee_id)
                if not employee:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Employee with ID {employee_id} not found"
                    )

                # Add ID to shift if not provided
                if "_id" not in shift:
                    shift["_id"] = IdHandler.generate_id()

                valid_shifts.append(shift)

            schedule_data["shifts"] = valid_shifts

        # Update schedule
        updated_schedule = await self.schedule_repo.update(schedule_id, schedule_data)

        if not updated_schedule:
            return None

        # Enrich with additional data
        return await self._enrich_schedule_data(updated_schedule)

    async def delete_schedule(self, schedule_id: str) -> bool:
        """
        Delete a schedule.

        Args:
            schedule_id: Schedule ID

        Returns:
            True if schedule was deleted
        """
        return await self.schedule_repo.delete(schedule_id)

    async def add_shift(self, schedule_id: str, shift_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Add a shift to a schedule.

        Args:
            schedule_id: Schedule ID
            shift_data: Shift data

        Returns:
            Updated schedule document or None if not found

        Raises:
            HTTPException: If validation fails
        """
        # Validate employee
        employee_id = shift_data.get("employee_id")
        employee = await employee_service.get_employee(employee_id)
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Employee with ID {employee_id} not found"
            )

        # Add shift to schedule
        updated_schedule = await self.schedule_repo.add_shift(schedule_id, shift_data)

        if not updated_schedule:
            return None

        # Enrich with additional data
        return await self._enrich_schedule_data(updated_schedule)

    async def update_shift(self, schedule_id: str, shift_id: str, shift_data: Dict[str, Any]) -> Optional[
        Dict[str, Any]]:
        """
        Update a shift in a schedule.

        Args:
            schedule_id: Schedule ID
            shift_id: Shift ID
            shift_data: Updated shift data

        Returns:
            Updated schedule document or None if not found

        Raises:
            HTTPException: If validation fails
        """
        # Validate employee if provided
        if "employee_id" in shift_data:
            employee_id = shift_data["employee_id"]
            employee = await employee_service.get_employee(employee_id)
            if not employee:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Employee with ID {employee_id} not found"
                )

        # Update shift in schedule
        updated_schedule = await self.schedule_repo.update_shift(schedule_id, shift_id, shift_data)

        if not updated_schedule:
            return None

        # Enrich with additional data
        return await self._enrich_schedule_data(updated_schedule)

    async def delete_shift(self, schedule_id: str, shift_id: str) -> Optional[Dict[str, Any]]:
        """
        Delete a shift from a schedule.

        Args:
            schedule_id: Schedule ID
            shift_id: Shift ID

        Returns:
            Updated schedule document or None if not found
        """
        # Delete shift from schedule
        updated_schedule = await self.schedule_repo.delete_shift(schedule_id, shift_id)

        if not updated_schedule:
            return None

        # Enrich with additional data
        return await self._enrich_schedule_data(updated_schedule)

    async def _enrich_schedule_data(self, schedule: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich schedule data with store, creator, and employee information.

        Args:
            schedule: Schedule document

        Returns:
            Enriched schedule document
        """
        if not schedule:
            return {}

        schedule_with_info = dict(schedule)

        # Add store info if available
        if schedule.get("store_id"):
            store = await store_service.get_store(schedule["store_id"])
            if store:
                schedule_with_info["store_name"] = store.get("name")

        # Add creator info if available
        if schedule.get("created_by"):
            creator = await user_service.get_user_by_id(schedule["created_by"])
            if creator:
                schedule_with_info["created_by_name"] = creator.get("full_name")

        # Enrich shifts with employee names if available
        if "shifts" in schedule and schedule["shifts"]:
            enriched_shifts = []

            for shift in schedule["shifts"]:
                shift_with_info = dict(shift)

                if shift.get("employee_id"):
                    employee = await employee_service.get_employee(shift["employee_id"])
                    if employee:
                        shift_with_info["employee_name"] = employee.get("full_name")

                enriched_shifts.append(shift_with_info)

            schedule_with_info["shifts"] = enriched_shifts

        return schedule_with_info


# Create global instance
schedule_service = ScheduleService()
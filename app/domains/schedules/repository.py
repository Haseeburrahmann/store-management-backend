"""
Schedule repository for database operations.
"""
from typing import Dict, List, Optional, Any
from datetime import date, datetime

from app.db.base_repository import BaseRepository
from app.db.mongodb import get_schedules_collection
from app.utils.id_handler import IdHandler
from app.utils.datetime_handler import DateTimeHandler


class ScheduleRepository(BaseRepository):
    """
    Repository for schedule data access.
    Extends BaseRepository with schedule-specific operations.
    """

    def __init__(self):
        """Initialize with schedules collection."""
        super().__init__(get_schedules_collection())

    async def find_by_store(self, store_id: str) -> List[Dict[str, Any]]:
        """
        Find schedules by store ID.

        Args:
            store_id: Store ID

        Returns:
            List of schedule documents
        """
        store_obj_id = IdHandler.ensure_object_id(store_id)
        query = {"store_id": store_obj_id} if store_obj_id else {"store_id": store_id}

        schedules = await self.collection.find(query).to_list(length=100)
        return IdHandler.format_object_ids(schedules)

    async def find_by_date_range(self, start_date: date, end_date: Optional[date] = None) -> List[Dict[str, Any]]:
        """
        Find schedules within a date range.

        Args:
            start_date: Start date
            end_date: End date (optional)

        Returns:
            List of schedule documents
        """
        # Convert dates to datetime for MongoDB
        start_datetime = DateTimeHandler.date_to_datetime(start_date)

        query = {"week_start_date": {"$gte": start_datetime}}

        if end_date:
            end_datetime = DateTimeHandler.date_to_datetime(end_date, set_to_end_of_day=True)
            query["week_start_date"]["$lte"] = end_datetime

        schedules = await self.collection.find(query).to_list(length=100)
        return IdHandler.format_object_ids(schedules)

    async def find_by_week(self, week_start_date: date) -> Optional[Dict[str, Any]]:
        """
        Find a schedule by week start date.

        Args:
            week_start_date: Week start date (Monday)

        Returns:
            Schedule document or None if not found
        """
        # Convert date to datetime for MongoDB
        start_datetime = DateTimeHandler.date_to_datetime(week_start_date)

        schedule = await self.collection.find_one({"week_start_date": start_datetime})
        return IdHandler.format_object_ids(schedule) if schedule else None

    async def find_by_store_and_week(self, store_id: str, week_start_date: date) -> Optional[Dict[str, Any]]:
        """
        Find a schedule by store ID and week start date.

        Args:
            store_id: Store ID
            week_start_date: Week start date (Monday)

        Returns:
            Schedule document or None if not found
        """
        # Convert date to datetime for MongoDB
        start_datetime = DateTimeHandler.date_to_datetime(week_start_date)

        store_obj_id = IdHandler.ensure_object_id(store_id)
        query = {
            "store_id": store_obj_id if store_obj_id else store_id,
            "week_start_date": start_datetime
        }

        schedule = await self.collection.find_one(query)
        return IdHandler.format_object_ids(schedule) if schedule else None

    async def find_with_employee_shifts(self, employee_id: str) -> List[Dict[str, Any]]:
        """
        Find schedules containing shifts for a specific employee.

        Args:
            employee_id: Employee ID

        Returns:
            List of schedule documents
        """
        employee_obj_id = IdHandler.ensure_object_id(employee_id)
        employee_id_str = str(employee_id)

        # We need to match schedules where shifts.employee_id matches
        # MongoDB array element matching
        query = {
            "shifts": {
                "$elemMatch": {
                    "$or": [
                        {"employee_id": employee_obj_id},
                        {"employee_id": employee_id_str}
                    ]
                }
            }
        }

        schedules = await self.collection.find(query).to_list(length=100)
        return IdHandler.format_object_ids(schedules)

    async def add_shift(self, schedule_id: str, shift_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Add a shift to a schedule.

        Args:
            schedule_id: Schedule ID
            shift_data: Shift data

        Returns:
            Updated schedule document or None if not found
        """
        # Generate an ID for the shift if not provided
        if "_id" not in shift_data:
            shift_data["_id"] = IdHandler.generate_id()

        # Find the schedule first
        schedule_obj_id = IdHandler.ensure_object_id(schedule_id)
        if not schedule_obj_id:
            return None

        # Add shift to schedule
        result = await self.collection.update_one(
            {"_id": schedule_obj_id},
            {
                "$push": {"shifts": shift_data},
                "$set": {"updated_at": DateTimeHandler.get_current_datetime()}
            }
        )

        if result.matched_count == 0:
            return None

        # Get updated schedule
        updated_schedule = await self.find_by_id(schedule_id)
        return updated_schedule

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
        """
        # Find the schedule first
        schedule = await self.find_by_id(schedule_id)
        if not schedule:
            return None

        # Find the shift in the schedule
        shifts = schedule.get("shifts", [])
        shift_index = None

        for i, shift in enumerate(shifts):
            if str(shift.get("_id")) == shift_id:
                shift_index = i
                break

        if shift_index is None:
            return None

        # Get the existing shift
        existing_shift = shifts[shift_index]

        # Update shift data, preserving ID
        updated_shift = {**existing_shift, **shift_data, "_id": existing_shift["_id"]}

        # Update shift in schedule
        schedule_obj_id = IdHandler.ensure_object_id(schedule_id)
        result = await self.collection.update_one(
            {"_id": schedule_obj_id},
            {
                "$set": {
                    f"shifts.{shift_index}": updated_shift,
                    "updated_at": DateTimeHandler.get_current_datetime()
                }
            }
        )

        if result.matched_count == 0:
            return None

        # Get updated schedule
        updated_schedule = await self.find_by_id(schedule_id)
        return updated_schedule

    async def delete_shift(self, schedule_id: str, shift_id: str) -> Optional[Dict[str, Any]]:
        """
        Delete a shift from a schedule.

        Args:
            schedule_id: Schedule ID
            shift_id: Shift ID

        Returns:
            Updated schedule document or None if not found
        """
        # Find the schedule first
        schedule_obj_id = IdHandler.ensure_object_id(schedule_id)
        if not schedule_obj_id:
            return None

        # Remove shift from schedule
        result = await self.collection.update_one(
            {"_id": schedule_obj_id},
            {
                "$pull": {"shifts": {"_id": shift_id}},
                "$set": {"updated_at": DateTimeHandler.get_current_datetime()}
            }
        )

        if result.matched_count == 0:
            return None

        # Get updated schedule
        updated_schedule = await self.find_by_id(schedule_id)
        return updated_schedule
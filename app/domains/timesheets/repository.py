"""
Timesheet repository for database operations.
"""
from typing import Dict, List, Optional, Any
from datetime import date, datetime

from app.db.base_repository import BaseRepository
from app.db.mongodb import get_timesheets_collection
from app.utils.id_handler import IdHandler
from app.utils.datetime_handler import DateTimeHandler
from app.schemas.timesheet import TimesheetStatus


class TimesheetRepository(BaseRepository):
    """
    Repository for timesheet data access.
    Extends BaseRepository with timesheet-specific operations.
    """

    def __init__(self):
        """Initialize with timesheets collection."""
        super().__init__(get_timesheets_collection())

    async def find_by_employee(self, employee_id: str) -> List[Dict[str, Any]]:
        """
        Find timesheets by employee ID.

        Args:
            employee_id: Employee ID

        Returns:
            List of timesheet documents
        """
        employee_obj_id = IdHandler.ensure_object_id(employee_id)
        query = {"employee_id": employee_obj_id} if employee_obj_id else {"employee_id": employee_id}

        timesheets = await self.collection.find(query).to_list(length=100)
        return IdHandler.format_object_ids(timesheets)

    async def find_by_store(self, store_id: str) -> List[Dict[str, Any]]:
        """
        Find timesheets by store ID.

        Args:
            store_id: Store ID

        Returns:
            List of timesheet documents
        """
        store_obj_id = IdHandler.ensure_object_id(store_id)
        query = {"store_id": store_obj_id} if store_obj_id else {"store_id": store_id}

        timesheets = await self.collection.find(query).to_list(length=100)
        return IdHandler.format_object_ids(timesheets)

    async def find_by_status(self, status: str) -> List[Dict[str, Any]]:
        """
        Find timesheets by status.

        Args:
            status: Timesheet status

        Returns:
            List of timesheet documents
        """
        query = {"status": status}

        timesheets = await self.collection.find(query).to_list(length=100)
        return IdHandler.format_object_ids(timesheets)

    async def find_by_date_range(self, start_date: date, end_date: Optional[date] = None) -> List[Dict[str, Any]]:
        """
        Find timesheets within a date range.

        Args:
            start_date: Start date
            end_date: End date (optional)

        Returns:
            List of timesheet documents
        """
        # Convert dates to datetime for MongoDB
        start_datetime = DateTimeHandler.date_to_datetime(start_date)

        query = {"week_end_date": {"$gte": start_datetime}}

        if end_date:
            end_datetime = DateTimeHandler.date_to_datetime(end_date, set_to_end_of_day=True)
            query["week_start_date"] = {"$lte": end_datetime}

        timesheets = await self.collection.find(query).to_list(length=100)
        return IdHandler.format_object_ids(timesheets)

    async def find_by_employee_and_week(self, employee_id: str, week_start_date: date) -> Optional[Dict[str, Any]]:
        """
        Find a timesheet by employee ID and week start date.

        Args:
            employee_id: Employee ID
            week_start_date: Week start date

        Returns:
            Timesheet document or None if not found
        """
        # Convert date to datetime for MongoDB
        start_datetime = DateTimeHandler.date_to_datetime(week_start_date)

        employee_obj_id = IdHandler.ensure_object_id(employee_id)
        query = {
            "employee_id": employee_obj_id if employee_obj_id else employee_id,
            "week_start_date": start_datetime
        }

        timesheet = await self.collection.find_one(query)
        return IdHandler.format_object_ids(timesheet) if timesheet else None

    async def find_by_payment(self, payment_id: str) -> List[Dict[str, Any]]:
        """
        Find timesheets by payment ID.

        Args:
            payment_id: Payment ID

        Returns:
            List of timesheet documents
        """
        payment_obj_id = IdHandler.ensure_object_id(payment_id)
        query = {"payment_id": payment_obj_id} if payment_obj_id else {"payment_id": payment_id}

        timesheets = await self.collection.find(query).to_list(length=100)
        return IdHandler.format_object_ids(timesheets)

    async def find_approved_not_paid(self, start_date: Optional[date] = None, end_date: Optional[date] = None) -> List[
        Dict[str, Any]]:
        """
        Find approved timesheets that haven't been paid yet.

        Args:
            start_date: Start date (optional)
            end_date: End date (optional)

        Returns:
            List of timesheet documents
        """
        query = {
            "status": TimesheetStatus.APPROVED,
            "$or": [
                {"payment_id": {"$exists": False}},
                {"payment_id": None}
            ]
        }

        if start_date:
            start_datetime = DateTimeHandler.date_to_datetime(start_date)
            query["week_start_date"] = {"$gte": start_datetime}

        if end_date:
            end_datetime = DateTimeHandler.date_to_datetime(end_date, set_to_end_of_day=True)
            if "week_start_date" in query:
                query["week_start_date"]["$lte"] = end_datetime
            else:
                query["week_end_date"] = {"$lte": end_datetime}

        timesheets = await self.collection.find(query).to_list(length=1000)
        return IdHandler.format_object_ids(timesheets)

    async def update_daily_hours(self, timesheet_id: str, day: str, hours: float) -> Optional[Dict[str, Any]]:
        """
        Update hours for a specific day in a timesheet.

        Args:
            timesheet_id: Timesheet ID
            day: Day of the week (monday, tuesday, etc.)
            hours: Hours for the day

        Returns:
            Updated timesheet document or None if not found
        """
        # Find the timesheet first to recalculate total hours and earnings
        timesheet = await self.find_by_id(timesheet_id)
        if not timesheet:
            return None

        # Update daily hours
        daily_hours = timesheet.get("daily_hours", {})
        daily_hours[day] = hours

        # Calculate total hours and earnings
        total_hours = sum(daily_hours.values())
        hourly_rate = timesheet.get("hourly_rate", 0)
        total_earnings = round(total_hours * hourly_rate, 2)

        # Update the timesheet
        update_data = {
            f"daily_hours.{day}": hours,
            "total_hours": total_hours,
            "total_earnings": total_earnings,
            "updated_at": DateTimeHandler.get_current_datetime()
        }

        timesheet_obj_id = IdHandler.ensure_object_id(timesheet_id)
        result = await self.collection.update_one(
            {"_id": timesheet_obj_id},
            {"$set": update_data}
        )

        if result.matched_count == 0:
            return None

        # Get the updated timesheet
        updated_timesheet = await self.find_by_id(timesheet_id)
        return updated_timesheet

    async def submit_timesheet(self, timesheet_id: str, notes: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Submit a timesheet for approval.

        Args:
            timesheet_id: Timesheet ID
            notes: Submission notes

        Returns:
            Updated timesheet document or None if not found
        """
        # Update data
        update_data = {
            "status": TimesheetStatus.SUBMITTED,
            "submitted_at": DateTimeHandler.get_current_datetime(),
            "updated_at": DateTimeHandler.get_current_datetime()
        }

        if notes:
            update_data["notes"] = notes

        timesheet_obj_id = IdHandler.ensure_object_id(timesheet_id)
        result = await self.collection.update_one(
            {"_id": timesheet_obj_id},
            {"$set": update_data}
        )

        if result.matched_count == 0:
            return None

        # Get the updated timesheet
        updated_timesheet = await self.find_by_id(timesheet_id)
        return updated_timesheet

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
        """
        # Update data
        update_data = {
            "status": status,
            "approved_by": approver_id,
            "approved_at": DateTimeHandler.get_current_datetime(),
            "updated_at": DateTimeHandler.get_current_datetime()
        }

        if notes:
            if status == TimesheetStatus.REJECTED:
                update_data["rejection_reason"] = notes
            else:
                update_data["notes"] = notes

        timesheet_obj_id = IdHandler.ensure_object_id(timesheet_id)
        result = await self.collection.update_one(
            {"_id": timesheet_obj_id},
            {"$set": update_data}
        )

        if result.matched_count == 0:
            return None

        # Get the updated timesheet
        updated_timesheet = await self.find_by_id(timesheet_id)
        return updated_timesheet
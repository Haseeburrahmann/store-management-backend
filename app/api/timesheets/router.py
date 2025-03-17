"""
Timesheet API routes for timesheet management.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from datetime import date

from app.domains.timesheets.service import timesheet_service
from app.domains.employees.service import employee_service
from app.core.permissions import has_permission, get_current_user
from app.schemas.timesheet import (
    TimesheetCreate, TimesheetUpdate, TimesheetResponse, TimesheetWithDetails,
    TimesheetSubmit, TimesheetApproval, DailyHoursUpdate, TimesheetSummary
)

router = APIRouter()


@router.get("/", response_model=List[TimesheetSummary])
async def get_timesheets(
        skip: int = 0,
        limit: int = 100,
        employee_id: Optional[str] = None,
        store_id: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        current_user: dict = Depends(has_permission("hours:read"))
):
    """
    Get all timesheets with optional filtering.

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        employee_id: Filter by employee ID
        store_id: Filter by store ID
        status: Filter by status
        start_date: Filter by start date
        end_date: Filter by end date
        current_user: Current user from token

    Returns:
        List of timesheets
    """
    try:
        timesheets = await timesheet_service.get_timesheets(
            skip=skip,
            limit=limit,
            employee_id=employee_id,
            store_id=store_id,
            status=status,
            start_date=start_date,
            end_date=end_date
        )
        return timesheets
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching timesheets: {str(e)}"
        )


@router.get("/me", response_model=List[TimesheetSummary])
async def get_my_timesheets(
        status: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 100,
        current_user: dict = Depends(get_current_user)
):
    """
    Get current user's timesheets.

    Args:
        status: Filter by status
        start_date: Filter by start date
        end_date: Filter by end date
        skip: Number of records to skip
        limit: Maximum number of records to return
        current_user: Current user from token

    Returns:
        List of user's timesheets
    """
    try:
        # Get employee ID for current user
        employee = await employee_service.get_employee_by_user_id(str(current_user["_id"]))

        if not employee:
            # Return empty list if employee not found, instead of 404 error
            return []

        # Get timesheets for this employee
        return await timesheet_service.get_timesheets_by_employee(
            employee_id=str(employee["_id"]),
            status=status,
            start_date=start_date,
            end_date=end_date
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching timesheets: {str(e)}"
        )


@router.get("/me/current", response_model=TimesheetWithDetails)
async def get_my_current_timesheet(
        current_user: dict = Depends(get_current_user)
):
    """
    Get current user's timesheet for the current week.

    Args:
        current_user: Current user from token

    Returns:
        Current week's timesheet
    """
    try:
        # Get employee ID for current user
        employee = await employee_service.get_employee_by_user_id(str(current_user["_id"]))

        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No employee profile found for your user account"
            )

        timesheet = await timesheet_service.get_current_week_timesheet(str(employee["_id"]))

        if not timesheet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No timesheet found for the current week"
            )

        return timesheet
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching current timesheet: {str(e)}"
        )


@router.get("/{timesheet_id}", response_model=TimesheetWithDetails)
async def get_timesheet(
        timesheet_id: str,
        current_user: dict = Depends(has_permission("hours:read"))
):
    """
    Get timesheet by ID.

    Args:
        timesheet_id: Timesheet ID
        current_user: Current user from token

    Returns:
        Timesheet
    """
    try:
        timesheet = await timesheet_service.get_timesheet(timesheet_id)

        if not timesheet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Timesheet with ID {timesheet_id} not found"
            )

        return timesheet
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching timesheet: {str(e)}"
        )


@router.post("/", response_model=TimesheetResponse, status_code=status.HTTP_201_CREATED)
async def create_timesheet(
        timesheet_data: TimesheetCreate,
        current_user: dict = Depends(has_permission("hours:write"))
):
    """
    Create a new timesheet.

    Args:
        timesheet_data: Timesheet creation data
        current_user: Current user from token

    Returns:
        Created timesheet
    """
    try:
        timesheet = await timesheet_service.create_timesheet(timesheet_data.model_dump())
        return timesheet
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating timesheet: {str(e)}"
        )


@router.post("/me/start-new", response_model=TimesheetResponse)
async def start_my_timesheet(
        store_id: str,
        current_user: dict = Depends(get_current_user)
):
    """
    Start a new timesheet for the current user for the current week.

    Args:
        store_id: Store ID
        current_user: Current user from token

    Returns:
        Created or existing timesheet
    """
    try:
        # Get employee ID for current user
        employee = await employee_service.get_employee_by_user_id(str(current_user["_id"]))

        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee profile not found"
            )

        return await timesheet_service.create_or_get_current_timesheet(
            employee_id=str(employee["_id"]),
            store_id=store_id
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting timesheet: {str(e)}"
        )


@router.put("/{timesheet_id}", response_model=TimesheetResponse)
async def update_timesheet(
        timesheet_id: str,
        timesheet_data: TimesheetUpdate,
        current_user: dict = Depends(has_permission("hours:write"))
):
    """
    Update a timesheet.

    Args:
        timesheet_id: Timesheet ID
        timesheet_data: Timesheet update data
        current_user: Current user from token

    Returns:
        Updated timesheet
    """
    try:
        updated_timesheet = await timesheet_service.update_timesheet(
            timesheet_id=timesheet_id,
            timesheet_data=timesheet_data.model_dump(exclude_unset=True)
        )

        if not updated_timesheet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Timesheet with ID {timesheet_id} not found"
            )

        return updated_timesheet
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating timesheet: {str(e)}"
        )


@router.put("/{timesheet_id}/day-hours", response_model=TimesheetResponse)
async def update_daily_hours(
        timesheet_id: str,
        daily_hours: DailyHoursUpdate,
        current_user: dict = Depends(has_permission("hours:write"))
):
    """
    Update hours for a specific day in a timesheet.

    Args:
        timesheet_id: Timesheet ID
        daily_hours: Day and hours to update
        current_user: Current user from token

    Returns:
        Updated timesheet
    """
    try:
        updated_timesheet = await timesheet_service.update_daily_hours(
            timesheet_id=timesheet_id,
            day=daily_hours.day,
            hours=daily_hours.hours
        )

        if not updated_timesheet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Timesheet with ID {timesheet_id} not found"
            )

        return updated_timesheet
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating daily hours: {str(e)}"
        )


@router.post("/{timesheet_id}/submit", response_model=TimesheetResponse)
async def submit_timesheet(
        timesheet_id: str,
        submit_data: TimesheetSubmit,
        current_user: dict = Depends(has_permission("hours:write"))
):
    """
    Submit a timesheet for approval.

    Args:
        timesheet_id: Timesheet ID
        submit_data: Submission notes
        current_user: Current user from token

    Returns:
        Submitted timesheet
    """
    try:
        submitted_timesheet = await timesheet_service.submit_timesheet(
            timesheet_id=timesheet_id,
            notes=submit_data.notes
        )

        if not submitted_timesheet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Timesheet with ID {timesheet_id} not found"
            )

        return submitted_timesheet
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error submitting timesheet: {str(e)}"
        )


@router.post("/{timesheet_id}/approve", response_model=TimesheetResponse)
async def approve_timesheet(
        timesheet_id: str,
        approval_data: TimesheetApproval,
        current_user: dict = Depends(has_permission("hours:approve"))
):
    """
    Approve or reject a timesheet.

    Args:
        timesheet_id: Timesheet ID
        approval_data: Approval status and notes
        current_user: Current user from token

    Returns:
        Approved/rejected timesheet
    """
    try:
        processed_timesheet = await timesheet_service.approve_timesheet(
            timesheet_id=timesheet_id,
            approver_id=str(current_user["_id"]),
            status=approval_data.status,
            notes=approval_data.notes
        )

        if not processed_timesheet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Timesheet with ID {timesheet_id} not found"
            )

        return processed_timesheet
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error approving/rejecting timesheet: {str(e)}"
        )


@router.delete("/{timesheet_id}", response_model=bool)
async def delete_timesheet(
        timesheet_id: str,
        current_user: dict = Depends(has_permission("hours:delete"))
):
    """
    Delete a timesheet.

    Args:
        timesheet_id: Timesheet ID
        current_user: Current user from token

    Returns:
        True if timesheet was deleted
    """
    try:
        result = await timesheet_service.delete_timesheet(timesheet_id)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Timesheet with ID {timesheet_id} not found"
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting timesheet: {str(e)}"
        )
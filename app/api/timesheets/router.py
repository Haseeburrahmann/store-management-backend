# app/api/timesheets/router.py
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from datetime import date

from app.dependencies.permissions import get_current_user, has_permission
from app.schemas.timesheet import TimesheetCreate, TimesheetUpdate, TimesheetResponse, TimesheetWithDetails
from app.schemas.timesheet import TimesheetSubmit, TimesheetApproval
from app.services.timesheet import TimesheetService
from app.models.timesheet import TimesheetStatus
from app.utils.id_handler import IdHandler

router = APIRouter()


@router.get("/", response_model=List[TimesheetWithDetails])
async def get_timesheets(
        skip: int = 0,
        limit: int = 100,
        employee_id: Optional[str] = None,
        store_id: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        current_user: Dict[str, Any] = Depends(has_permission("hours:read"))
):
    """
    Get all timesheets with optional filtering
    """
    try:
        print(f"Getting timesheets with filters: employee_id={employee_id}, store_id={store_id}, "
              f"status={status}, start_date={start_date}, end_date={end_date}")

        # Convert dates to string format if provided
        start_date_str = start_date.isoformat() if start_date else None
        end_date_str = end_date.isoformat() if end_date else None

        return await TimesheetService.get_timesheets(
            skip=skip,
            limit=limit,
            employee_id=employee_id,
            store_id=store_id,
            status=status,
            start_date=start_date_str,
            end_date=end_date_str
        )
    except Exception as e:
        print(f"Error getting timesheets: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting timesheets: {str(e)}"
        )


@router.get("/me", response_model=List[TimesheetResponse])
async def get_my_timesheets(
        status: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get current user's timesheets
    """
    try:
        print(f"Getting timesheets for current user: {current_user.get('email')}")

        # Get employee ID for current user
        from app.services.employee import EmployeeService
        employee = await EmployeeService.get_employee_by_user_id(str(current_user["_id"]))

        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee profile not found"
            )

        # Convert dates to string format if provided
        start_date_str = start_date.isoformat() if start_date else None
        end_date_str = end_date.isoformat() if end_date else None

        return await TimesheetService.get_timesheets(
            employee_id=str(employee["_id"]),
            status=status,
            start_date=start_date_str,
            end_date=end_date_str
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting timesheets for current user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting timesheets: {str(e)}"
        )


@router.get("/me/current", response_model=TimesheetWithDetails)
async def get_my_current_timesheet(
        current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get current user's current timesheet for the week
    """
    try:
        print(f"Getting current timesheet for user: {current_user.get('email')}")

        # Get employee ID for current user
        from app.services.employee import EmployeeService
        employee = await EmployeeService.get_employee_by_user_id(str(current_user["_id"]))

        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee profile not found"
            )

        timesheet = await TimesheetService.get_employee_current_timesheet(str(employee["_id"]))

        if not timesheet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No current timesheet found"
            )

        return timesheet
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting current timesheet: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting current timesheet: {str(e)}"
        )


@router.get("/{timesheet_id}", response_model=TimesheetWithDetails)
async def get_timesheet(
        timesheet_id: str,
        current_user: Dict[str, Any] = Depends(has_permission("hours:read"))
):
    """
    Get timesheet by ID
    """
    try:
        print(f"Getting timesheet with ID: {timesheet_id}")
        timesheet = await TimesheetService.get_timesheet(timesheet_id)

        # Use the helper method to raise a consistent 404 error if not found
        IdHandler.raise_if_not_found(
            timesheet,
            f"Timesheet with ID {timesheet_id} not found",
            status.HTTP_404_NOT_FOUND
        )

        return timesheet
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting timesheet: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting timesheet: {str(e)}"
        )


@router.post("/", response_model=TimesheetResponse, status_code=status.HTTP_201_CREATED)
async def create_timesheet(
        timesheet: TimesheetCreate,
        current_user: Dict[str, Any] = Depends(has_permission("hours:write"))
):
    """
    Create new timesheet
    """
    try:
        print(f"Creating timesheet for week: {timesheet.week_start_date} to {timesheet.week_end_date}")

        # Convert to dict
        timesheet_data = timesheet.model_dump()

        return await TimesheetService.create_timesheet(timesheet_data)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating timesheet: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating timesheet: {str(e)}"
        )


@router.post("/generate", response_model=TimesheetResponse)
async def generate_timesheet(
        employee_id: str,
        store_id: str,
        start_date: date,
        end_date: date,
        current_user: Dict[str, Any] = Depends(has_permission("hours:write"))
):
    """
    Generate a timesheet from hours records
    """
    try:
        print(f"Generating timesheet for employee {employee_id} from {start_date} to {end_date}")

        # Convert dates to string format
        start_date_str = start_date.isoformat()
        end_date_str = end_date.isoformat()

        return await TimesheetService.generate_timesheet_from_hours(
            employee_id=employee_id,
            store_id=store_id,
            week_start_date=start_date_str,
            week_end_date=end_date_str
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generating timesheet: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating timesheet: {str(e)}"
        )


@router.put("/{timesheet_id}", response_model=TimesheetResponse)
async def update_timesheet(
        timesheet_id: str,
        timesheet: TimesheetUpdate,
        current_user: Dict[str, Any] = Depends(has_permission("hours:write"))
):
    """
    Update existing timesheet
    """
    try:
        print(f"Updating timesheet with ID: {timesheet_id}")

        # Get update data excluding unset fields
        update_data = timesheet.model_dump(exclude_unset=True)

        updated_timesheet = await TimesheetService.update_timesheet(timesheet_id, update_data)

        # Use the helper method to raise a consistent 404 error if not found
        IdHandler.raise_if_not_found(
            updated_timesheet,
            f"Timesheet with ID {timesheet_id} not found",
            status.HTTP_404_NOT_FOUND
        )

        return updated_timesheet
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating timesheet: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating timesheet: {str(e)}"
        )


@router.delete("/{timesheet_id}", response_model=bool)
async def delete_timesheet(
        timesheet_id: str,
        current_user: Dict[str, Any] = Depends(has_permission("hours:delete"))
):
    """
    Delete timesheet
    """
    try:
        print(f"Deleting timesheet with ID: {timesheet_id}")

        # Check if timesheet exists first
        timesheet = await TimesheetService.get_timesheet(timesheet_id)
        IdHandler.raise_if_not_found(
            timesheet,
            f"Timesheet with ID {timesheet_id} not found",
            status.HTTP_404_NOT_FOUND
        )

        result = await TimesheetService.delete_timesheet(timesheet_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting timesheet: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting timesheet: {str(e)}"
        )


@router.post("/{timesheet_id}/submit", response_model=TimesheetResponse)
async def submit_timesheet(
        timesheet_id: str,
        submit_data: TimesheetSubmit,
        current_user: Dict[str, Any] = Depends(has_permission("hours:write"))
):
    """
    Submit timesheet for approval
    """
    try:
        print(f"Submitting timesheet with ID: {timesheet_id}")

        # Submit the timesheet
        updated_timesheet = await TimesheetService.submit_timesheet(
            timesheet_id=timesheet_id,
            notes=submit_data.notes
        )

        # Use the helper method to raise a consistent 404 error if not found
        IdHandler.raise_if_not_found(
            updated_timesheet,
            f"Timesheet with ID {timesheet_id} not found",
            status.HTTP_404_NOT_FOUND
        )

        return updated_timesheet
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error submitting timesheet: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error submitting timesheet: {str(e)}"
        )


@router.post("/{timesheet_id}/approve", response_model=TimesheetResponse)
async def approve_timesheet(
        timesheet_id: str,
        approval_data: TimesheetApproval,
        current_user: Dict[str, Any] = Depends(has_permission("hours:approve"))
):
    """
    Approve or reject timesheet
    """
    try:
        print(f"Processing {approval_data.status} for timesheet with ID: {timesheet_id}")

        # Approve or reject the timesheet
        updated_timesheet = await TimesheetService.approve_timesheet(
            timesheet_id=timesheet_id,
            approver_id=str(current_user["_id"]),
            approval_status=approval_data.status,
            notes=approval_data.notes
        )

        # Use the helper method to raise a consistent 404 error if not found
        IdHandler.raise_if_not_found(
            updated_timesheet,
            f"Timesheet with ID {timesheet_id} not found",
            status.HTTP_404_NOT_FOUND
        )

        return updated_timesheet
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error approving timesheet: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error approving timesheet: {str(e)}"
        )


@router.post("/{timesheet_id}/time-entries/{time_entry_id}", response_model=TimesheetResponse)
async def add_time_entry(
        timesheet_id: str,
        time_entry_id: str,
        current_user: Dict[str, Any] = Depends(has_permission("hours:write"))
):
    """
    Add time entry to timesheet
    """
    try:
        print(f"Adding time entry {time_entry_id} to timesheet {timesheet_id}")

        updated_timesheet = await TimesheetService.add_time_entry(timesheet_id, time_entry_id)

        # Use the helper method to raise a consistent 404 error if not found
        IdHandler.raise_if_not_found(
            updated_timesheet,
            f"Timesheet with ID {timesheet_id} not found",
            status.HTTP_404_NOT_FOUND
        )

        return updated_timesheet
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error adding time entry: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding time entry: {str(e)}"
        )


@router.delete("/{timesheet_id}/time-entries/{time_entry_id}", response_model=TimesheetResponse)
async def remove_time_entry(
        timesheet_id: str,
        time_entry_id: str,
        current_user: Dict[str, Any] = Depends(has_permission("hours:write"))
):
    """
    Remove time entry from timesheet
    """
    try:
        print(f"Removing time entry {time_entry_id} from timesheet {timesheet_id}")

        updated_timesheet = await TimesheetService.remove_time_entry(timesheet_id, time_entry_id)

        # Use the helper method to raise a consistent 404 error if not found
        IdHandler.raise_if_not_found(
            updated_timesheet,
            f"Timesheet with ID {timesheet_id} not found",
            status.HTTP_404_NOT_FOUND
        )

        return updated_timesheet
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error removing time entry: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error removing time entry: {str(e)}"
        )
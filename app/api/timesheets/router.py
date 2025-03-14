# app/api/timesheets/router.py
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from datetime import date

from starlette.responses import JSONResponse

from app.dependencies.permissions import get_current_user, has_permission
from app.schemas.timesheet import (
    TimesheetCreate, TimesheetUpdate, TimesheetResponse, TimesheetWithDetails,
    TimesheetSubmit, TimesheetApproval, DailyHoursUpdate, TimesheetSummary
)
from app.services.timesheet import TimesheetService, timesheets_collection

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
    Get all timesheets with optional filtering
    """
    return await TimesheetService.get_timesheets(
        skip=skip,
        limit=limit,
        employee_id=employee_id,
        store_id=store_id,
        status=status,
        start_date=start_date,
        end_date=end_date
    )


@router.get("/me", response_model=List[TimesheetSummary])
async def get_my_timesheets(
        status: Optional[str] = None,  # Changed from status_filter to status for consistency
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 100,
        current_user: dict = Depends(get_current_user)
):
    """
    Get current user's timesheets
    """
    try:
        # Log user info for debugging
        print(f"Getting timesheets for user: {current_user['_id']} (email: {current_user.get('email', 'unknown')})")

        # Get employee ID for current user
        from app.services.employee import EmployeeService
        employee = await EmployeeService.get_employee_by_user_id(str(current_user["_id"]))

        if not employee:
            # Log this case for debugging
            print(f"No employee record found for user {current_user['_id']}")
            # Return empty list if employee not found, instead of 404 error
            return []

        print(f"Found employee: {employee['_id']} for user {current_user['_id']}")

        # Get timesheets
        timesheets = await TimesheetService.get_timesheets(
            employee_id=str(employee["_id"]),
            status=status,  # Using simple 'status' parameter now
            start_date=start_date,
            end_date=end_date,
            skip=skip,
            limit=limit
        )

        return timesheets

    except Exception as e:
        # Log the error for debugging
        print(f"Error in get_my_timesheets: {str(e)}")
        # Return a proper error response
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching timesheets: {str(e)}"
        )


@router.get("/me/current", response_model=TimesheetWithDetails)
async def get_my_current_timesheet(
        current_user: dict = Depends(get_current_user)
):
    """
    Get current user's timesheet for the current week
    """
    try:
        # Get employee ID for current user
        from app.services.employee import EmployeeService
        employee = await EmployeeService.get_employee_by_user_id(str(current_user["_id"]))

        # If user doesn't have an employee profile (e.g., admin user)
        if not employee:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"detail": "No employee profile found for your user account. This is normal for admin users."}
            )

        timesheet = await TimesheetService.get_current_week_timesheet(str(employee["_id"]))

        if not timesheet:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"detail": "No timesheet found for the current week"}
            )

        return timesheet
    except Exception as e:
        print(f"Error getting current timesheet: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving current timesheet: {str(e)}"
        )


@router.get("/{timesheet_id}", response_model=TimesheetWithDetails)
async def get_timesheet(
        timesheet_id: str,
        current_user: dict = Depends(has_permission("hours:read"))
):
    """
    Get timesheet by ID
    """
    try:
        timesheet = await TimesheetService.get_timesheet(timesheet_id)

        if not timesheet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Timesheet with ID {timesheet_id} not found"
            )

        return timesheet
    except Exception as e:
        # Log the error for debugging
        print(f"Error in get_timesheet endpoint: {str(e)}")
        import traceback
        traceback.print_exc()

        # Re-raise as HTTP exception
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving timesheet: {str(e)}"
        )


@router.post("/", response_model=TimesheetResponse, status_code=status.HTTP_201_CREATED)
async def create_timesheet(
        timesheet: TimesheetCreate,
        current_user: dict = Depends(has_permission("hours:write"))
):
    """
    Create a new timesheet
    """
    return await TimesheetService.create_timesheet(timesheet.model_dump())


@router.post("/me/start-new", response_model=TimesheetResponse)
async def start_my_timesheet(
        store_id: str,
        current_user: dict = Depends(get_current_user)
):
    """
    Start a new timesheet for the current user for the current week
    """
    # Get employee ID for current user
    from app.services.employee import EmployeeService
    employee = await EmployeeService.get_employee_by_user_id(str(current_user["_id"]))

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found"
        )

    return await TimesheetService.create_or_get_current_timesheet(
        employee_id=str(employee["_id"]),
        store_id=store_id
    )


@router.put("/{timesheet_id}", response_model=TimesheetResponse)
async def update_timesheet(
        timesheet_id: str,
        timesheet: TimesheetUpdate,
        current_user: dict = Depends(has_permission("hours:write"))
):
    """
    Update a timesheet
    """
    updated_timesheet = await TimesheetService.update_timesheet(
        timesheet_id=timesheet_id,
        timesheet_data=timesheet.model_dump(exclude_unset=True)
    )

    if not updated_timesheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Timesheet with ID {timesheet_id} not found"
        )

    return updated_timesheet


@router.put("/{timesheet_id}/day-hours", response_model=TimesheetResponse)
async def update_daily_hours(
        timesheet_id: str,
        daily_hours: DailyHoursUpdate,
        current_user: dict = Depends(has_permission("hours:write"))
):
    """
    Update hours for a specific day in a timesheet
    """
    updated_timesheet = await TimesheetService.update_daily_hours(
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


@router.post("/{timesheet_id}/submit", response_model=TimesheetResponse)
async def submit_timesheet(
        timesheet_id: str,
        submit_data: TimesheetSubmit,
        current_user: dict = Depends(has_permission("hours:write"))
):
    """
    Submit a timesheet for approval
    """
    submitted_timesheet = await TimesheetService.submit_timesheet(
        timesheet_id=timesheet_id,
        notes=submit_data.notes
    )

    if not submitted_timesheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Timesheet with ID {timesheet_id} not found"
        )

    return submitted_timesheet


@router.post("/{timesheet_id}/approve", response_model=TimesheetResponse)
async def approve_timesheet(
        timesheet_id: str,
        approval_data: TimesheetApproval,
        current_user: dict = Depends(has_permission("hours:approve"))
):
    """
    Approve or reject a timesheet
    """
    processed_timesheet = await TimesheetService.approve_timesheet(
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


@router.delete("/{timesheet_id}", response_model=bool)
async def delete_timesheet(
        timesheet_id: str,
        current_user: dict = Depends(has_permission("hours:delete"))
):
    """
    Delete a timesheet
    """
    result = await TimesheetService.delete_timesheet(timesheet_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Timesheet with ID {timesheet_id} not found"
        )

    return result


@router.get("/diagnostic", response_model=Dict[str, Any])
async def timesheet_diagnostic():
    """Diagnostic endpoint to check timesheet data"""
    try:
        # Count total timesheets
        total = await timesheets_collection.count_documents({})

        # Get a sample timesheet
        sample = await timesheets_collection.find_one({})

        # Count by status
        status_counts = {}
        for status in ["draft", "submitted", "approved", "rejected"]:
            count = await timesheets_collection.count_documents({"status": status})
            status_counts[status] = count

        # Get unique employee IDs
        pipeline = [
            {"$group": {"_id": "$employee_id"}},
            {"$project": {"employee_id": "$_id", "_id": 0}}
        ]
        unique_employees = await timesheets_collection.aggregate(pipeline).to_list(length=100)
        employee_ids = [str(emp.get("employee_id")) for emp in unique_employees]

        # Format the sample for display
        sample_formatted = None
        if sample:
            sample_formatted = {k: str(v) for k, v in sample.items()}

        return {
            "total_timesheets": total,
            "status_counts": status_counts,
            "unique_employee_ids": employee_ids,
            "sample_timesheet": sample_formatted
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Diagnostic error: {str(e)}")
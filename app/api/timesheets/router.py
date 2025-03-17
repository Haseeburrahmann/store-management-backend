# app/api/timesheets/router.py
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from datetime import date, datetime, timedelta

from starlette.responses import JSONResponse

from app.dependencies.permissions import get_current_user, has_permission
from app.models.timesheet import TimesheetStatus
from app.schemas.timesheet import (
    TimesheetCreate, TimesheetUpdate, TimesheetResponse, TimesheetWithDetails,
    TimesheetSubmit, TimesheetApproval, DailyHoursUpdate, TimesheetSummary
)
from app.services.timesheet import TimesheetService, timesheets_collection
from app.utils.id_handler import IdHandler

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


@router.post("/me/start-past", response_model=TimesheetResponse)
async def start_past_timesheet(
        store_id: str = Query(..., description="Store ID where the work was performed"),
        week_start_date: str = Query(..., description="Start date of the week (YYYY-MM-DD)"),
        current_user: dict = Depends(get_current_user)
):
    """
    Start a new timesheet for a past week
    """
    try:
        # Validate date format
        try:
            start_date = datetime.fromisoformat(week_start_date).date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format for week_start_date. Expected YYYY-MM-DD"
            )

        # Validate the date is a Monday (start of week)
        if start_date.weekday() != 0:  # 0 is Monday
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Week start date must be a Monday"
            )

        # Get employee ID for current user
        from app.services.employee import EmployeeService
        employee = await EmployeeService.get_employee_by_user_id(str(current_user["_id"]))

        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee profile not found"
            )

        # Format the week_start_date as datetime for MongoDB
        week_start_datetime = datetime.combine(start_date, datetime.min.time())

        # Check if a timesheet already exists for this week
        existing_timesheet = await timesheets_collection.find_one({
            "employee_id": str(employee["_id"]),
            "week_start_date": week_start_datetime
        })

        if existing_timesheet:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A timesheet already exists for this week"
            )

        # Check if the store exists
        from app.services.store import StoreService
        store = await StoreService.get_store(store_id)
        if not store:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Store with ID {store_id} not found"
            )

        # Calculate week_end_date (Sunday of the week)
        week_end_date = start_date + timedelta(days=6)
        week_end_datetime = datetime.combine(week_end_date, datetime.min.time())

        # Get the employee's hourly rate
        hourly_rate = employee.get("hourly_rate", 0)

        # Create timesheet data
        timesheet_data = {
            "employee_id": str(employee["_id"]),
            "store_id": store_id,
            "week_start_date": week_start_datetime,
            "week_end_date": week_end_datetime,
            "hourly_rate": hourly_rate,
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
            "status": TimesheetStatus.DRAFT.value,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        # Insert the timesheet
        result = await timesheets_collection.insert_one(timesheet_data)

        # Get the newly created timesheet
        new_timesheet = await timesheets_collection.find_one({"_id": result.inserted_id})

        # Format the result
        return IdHandler.format_object_ids(new_timesheet)

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        print(f"Error in start_past_timesheet endpoint: {str(e)}")
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating past timesheet: {str(e)}"
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
# app/api/hours/router.py
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime, date
from app.dependencies.permissions import get_current_user, has_permission
from app.schemas.hours import HourCreate, HourUpdate, HourResponse, HourWithEmployee, HourApproval, ClockInRequest, \
    ClockOutRequest
from app.services.hours import HourService
from app.services.employee import EmployeeService
from app.services.store import StoreService
from app.core.db import get_hours_collection
from fastapi import status

router = APIRouter()
hours_collection = get_hours_collection()


@router.get("/", response_model=List[HourWithEmployee])
@router.get("/", response_model=List[HourWithEmployee])
async def get_hours(
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        employee_id: Optional[str] = None,
        store_id: Optional[str] = None,
        status_filter: Optional[str] = None,
        current_user: Dict[str, Any] = Depends(has_permission("hours:read"))
):
    """
    Get all hours records with optional filtering
    """
    try:
        print(f"Getting hours with filters: start_date={start_date}, end_date={end_date}, "
              f"employee_id={employee_id}, store_id={store_id}, status={status_filter}")

        # Convert dates to datetime if provided
        start_datetime = datetime.combine(start_date, datetime.min.time()) if start_date else None
        end_datetime = datetime.combine(end_date, datetime.max.time()) if end_date else None

        # Validate employee_id if provided
        if employee_id:
            employee = await EmployeeService.get_employee(employee_id)
            if not employee:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Employee with ID {employee_id} not found"
                )

        # Validate store_id if provided
        if store_id:
            store = await StoreService.get_store(store_id)
            if not store:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Store with ID {store_id} not found"
                )

        return await HourService.get_hours(
            employee_id=employee_id,
            store_id=store_id,
            start_date=start_datetime,
            end_date=end_datetime,
            status=status_filter
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting hours: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting hours: {str(e)}"
        )


@router.get("/me", response_model=List[HourResponse])
async def get_my_hours(
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get current user's hours records
    """
    try:
        print(f"Getting hours for current user: {current_user.get('email')}")

        # Get employee ID for current user
        employee = await EmployeeService.get_employee_by_user_id(str(current_user["_id"]))

        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee profile not found"
            )

        # Convert dates to datetime if provided
        start_datetime = datetime.combine(start_date, datetime.min.time()) if start_date else None
        end_datetime = datetime.combine(end_date, datetime.max.time()) if end_date else None

        return await HourService.get_hours(
            employee_id=str(employee["_id"]),
            start_date=start_datetime,
            end_date=end_datetime
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting hours for current user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting hours: {str(e)}"
        )


@router.get("/active", response_model=HourResponse)
async def get_active_hours(
        current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get currently active hours for the current user
    """
    try:
        print(f"Getting active hours for current user: {current_user.get('email')}")

        # Get employee ID for current user
        employee = await EmployeeService.get_employee_by_user_id(str(current_user["_id"]))

        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee profile not found"
            )

        active_hour = await HourService.get_active_hour(str(employee["_id"]))
        if not active_hour:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active hours found"
            )

        return active_hour
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting active hours: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting active hours: {str(e)}"
        )


@router.get("/{hour_id}", response_model=HourWithEmployee)
async def get_hour(
        hour_id: str,
        current_user: Dict[str, Any] = Depends(has_permission("hours:read"))
):
    """
    Get hour record by ID
    """
    try:
        print(f"Getting hour record with ID: {hour_id}")

        hour = await HourService.get_hour(hour_id)
        if not hour:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Hour record with ID {hour_id} not found"
            )

        return hour
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting hour record: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting hour record: {str(e)}"
        )


@router.post("/clock-in", response_model=HourResponse)
async def clock_in_endpoint(
        request: ClockInRequest,
        current_user: Dict[str, Any] = Depends(has_permission("hours:write"))
):
    """
    Clock in for an employee
    """
    try:
        print(f"Processing clock-in request for employee: {request.employee_id}")

        # Validate employee exists
        employee = await EmployeeService.get_employee(request.employee_id)
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee with ID {request.employee_id} not found"
            )

        # Validate store exists
        store = await StoreService.get_store(request.store_id)
        if not store:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Store with ID {request.store_id} not found"
            )

        # Check if employee is already clocked in
        active_hour = await HourService.get_active_hour(request.employee_id)
        if active_hour:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Employee is already clocked in"
            )

        return await HourService.clock_in(request.employee_id, request.store_id, request.notes)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error processing clock-in: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing clock-in: {str(e)}"
        )


@router.post("/clock-out/{employee_id}", response_model=HourResponse)
async def clock_out_endpoint(
        employee_id: str,
        request: ClockOutRequest,
        current_user: Dict[str, Any] = Depends(has_permission("hours:write"))
):
    """
    Clock out for an employee
    """
    try:
        print(f"Processing clock-out request for employee: {employee_id}")

        # Validate employee exists
        employee = await EmployeeService.get_employee(employee_id)
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee with ID {employee_id} not found"
            )

        # Check if employee is clocked in
        active_hour = await HourService.get_active_hour(employee_id)
        if not active_hour:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Employee is not clocked in"
            )

        # Validate break times if provided
        if request.break_start and request.break_end:
            if request.break_start >= request.break_end:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Break end time must be after break start time"
                )

            clock_in_time = active_hour.get("clock_in")
            if request.break_start < clock_in_time:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Break start time must be after clock in time"
                )

        return await HourService.clock_out(employee_id, request.break_start, request.break_end, request.notes)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error processing clock-out: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing clock-out: {str(e)}"
        )


@router.post("/", response_model=HourResponse, status_code=status.HTTP_201_CREATED)
async def create_hour(
        hour: HourCreate,
        current_user: Dict[str, Any] = Depends(has_permission("hours:write"))
):
    """
    Create a new hour record manually
    """
    try:
        print(f"Creating new hour record")

        # Validate employee exists
        employee = await EmployeeService.get_employee(hour.employee_id)
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee with ID {hour.employee_id} not found"
            )

        # Validate store exists
        store = await StoreService.get_store(hour.store_id)
        if not store:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Store with ID {hour.store_id} not found"
            )

        # Validate break times if provided
        if hour.break_start and hour.break_end:
            if hour.break_start >= hour.break_end:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Break end time must be after break start time"
                )

            if hour.break_start < hour.clock_in:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Break start time must be after clock in time"
                )

            if hour.clock_out and hour.break_end > hour.clock_out:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Break end time must be before clock out time"
                )

        return await HourService.create_hour(hour)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating hour record: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating hour record: {str(e)}"
        )


@router.put("/{hour_id}", response_model=HourResponse)
async def update_hour(
        hour_id: str,
        hour: HourUpdate,
        current_user: Dict[str, Any] = Depends(has_permission("hours:write"))
):
    """
    Update an existing hour record
    """
    try:
        print(f"Updating hour record with ID: {hour_id}")

        # Check if hour exists
        existing_hour = await HourService.get_hour(hour_id)
        if not existing_hour:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Hour record with ID {hour_id} not found"
            )

        # Check if already approved
        if existing_hour.get("status") == "approved":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot update an approved hours record"
            )

        # Validate break times if provided
        if hour.break_start and hour.break_end:
            if hour.break_start >= hour.break_end:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Break end time must be after break start time"
                )

        # Update the hour
        updated_hour = await HourService.update_hour(hour_id, hour, str(current_user["_id"]))
        if not updated_hour:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update hour record"
            )

        return updated_hour
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating hour record: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating hour record: {str(e)}"
        )


@router.put("/{hour_id}/approve", response_model=HourResponse)
async def approve_hour(
        hour_id: str,
        approval: HourApproval,
        current_user: Dict[str, Any] = Depends(has_permission("hours:approve"))
):
    """
    Approve or reject an hour record
    """
    try:
        print(f"Processing approval for hour record: {hour_id}")

        # Check if hour exists
        existing_hour = await HourService.get_hour(hour_id)
        if not existing_hour:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Hour record with ID {hour_id} not found"
            )

        # Check if already processed
        if existing_hour.get("status") != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Hours record already {existing_hour.get('status')}"
            )

        # Check if clock out time exists
        if not existing_hour.get("clock_out"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot approve an hours record without clock out time"
            )

        updated_hour = await HourService.approve_hour(hour_id, approval, str(current_user["_id"]))
        if not updated_hour:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update approval status"
            )

        return updated_hour
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error approving hour record: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error approving hour record: {str(e)}"
        )


@router.delete("/{hour_id}", response_model=bool)
async def delete_hour(
        hour_id: str,
        current_user: Dict[str, Any] = Depends(has_permission("hours:delete"))
):
    """
    Delete an hour record
    """
    try:
        print(f"Deleting hour record with ID: {hour_id}")

        # Check if hour exists
        existing_hour = await HourService.get_hour(hour_id)
        if not existing_hour:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Hour record with ID {hour_id} not found"
            )

        # Check if already approved
        if existing_hour.get("status") == "approved":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete an approved hours record"
            )

        result = await HourService.delete_hour(hour_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting hour record: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting hour record: {str(e)}"
        )


@router.get("/debug/lookup/{hour_id}")
async def debug_lookup_hour(
        hour_id: str,
        current_user: Dict[str, Any] = Depends(has_permission("hours:read"))
):
    """
    Debug endpoint to test different hour lookup methods
    """
    from app.utils.formatting import ensure_object_id

    try:
        result = {
            "requested_id": hour_id,
            "lookup_results": {}
        }

        # Method 1: Direct ObjectId lookup
        obj_id = ensure_object_id(hour_id)
        if obj_id:
            hour = await hours_collection.find_one({"_id": obj_id})
            result["lookup_results"]["objectid_lookup"] = {
                "success": hour is not None,
                "employee_id": str(hour.get("employee_id")) if hour else None,
                "clock_in": hour.get("clock_in").isoformat() if hour and hour.get("clock_in") else None
            }
        else:
            result["lookup_results"]["objectid_lookup"] = {
                "success": False,
                "error": "Invalid ObjectId format"
            }

        # Method 2: String ID lookup
        hour = await hours_collection.find_one({"_id": hour_id})
        result["lookup_results"]["string_id_lookup"] = {
            "success": hour is not None,
            "employee_id": str(hour.get("employee_id")) if hour else None,
            "clock_in": hour.get("clock_in").isoformat() if hour and hour.get("clock_in") else None
        }

        # Method 3: String comparison
        all_hours = await hours_collection.find().to_list(length=100)
        hour_match = None
        for h in all_hours:
            if str(h.get('_id')) == hour_id:
                hour_match = h
                break

        result["lookup_results"]["string_comparison"] = {
            "success": hour_match is not None,
            "employee_id": str(hour_match.get("employee_id")) if hour_match else None,
            "clock_in": hour_match.get("clock_in").isoformat() if hour_match and hour_match.get("clock_in") else None,
            "total_hours_checked": len(all_hours)
        }

        # Method 4: Service method lookup
        service_result = await HourService.get_hour(hour_id)
        result["lookup_results"]["service_method"] = {
            "success": service_result is not None,
            "employee_id": service_result.get("employee_id") if service_result else None,
            "clock_in": service_result.get("clock_in").isoformat() if service_result and service_result.get(
                "clock_in") else None
        }

        # List all hour IDs for reference
        result["all_hour_ids"] = [str(h.get("_id")) for h in all_hours]

        return result
    except Exception as e:
        print(f"Error in debug lookup: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in debug lookup: {str(e)}"
        )
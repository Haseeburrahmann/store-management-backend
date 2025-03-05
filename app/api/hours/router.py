# app/api/hours/router.py
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from datetime import datetime, date
from app.dependencies.permissions import get_current_user, has_permission
from app.schemas.hours import HourCreate, HourUpdate, HourResponse, HourWithEmployee, HourApproval, ClockInRequest, \
    ClockOutRequest
from app.services.hours import HourService
from app.services.employee import EmployeeService

router = APIRouter()


@router.get("/", response_model=List[HourWithEmployee])
async def get_hours(
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        employee_id: Optional[str] = None,
        store_id: Optional[str] = None,
        status: Optional[str] = None,
        current_user: Dict[str, Any] = Depends(has_permission("hours:read"))
):
    """
    Get all hours records with optional filtering
    """
    # Convert dates to datetime if provided
    start_datetime = datetime.combine(start_date, datetime.min.time()) if start_date else None
    end_datetime = datetime.combine(end_date, datetime.max.time()) if end_date else None

    return await HourService.get_hours(
        employee_id=employee_id,
        store_id=store_id,
        start_date=start_datetime,
        end_date=end_datetime,
        status=status
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
    # Get employee ID for current user
    employee = await EmployeeService.get_employee_by_user_id(str(current_user["_id"]))

    if not employee:
        raise HTTPException(status_code=404, detail="Employee profile not found")

    # Convert dates to datetime if provided
    start_datetime = datetime.combine(start_date, datetime.min.time()) if start_date else None
    end_datetime = datetime.combine(end_date, datetime.max.time()) if end_date else None

    return await HourService.get_hours(
        employee_id=str(employee["_id"]),
        start_date=start_datetime,
        end_date=end_datetime
    )


@router.get("/active", response_model=HourResponse)
async def get_active_hours(
        current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get currently active hours for the current user
    """
    # Get employee ID for current user
    employee = await EmployeeService.get_employee_by_user_id(str(current_user["_id"]))

    if not employee:
        raise HTTPException(status_code=404, detail="Employee profile not found")

    active_hour = await HourService.get_active_hour(str(employee["_id"]))
    if not active_hour:
        raise HTTPException(status_code=404, detail="No active hours found")

    return active_hour


@router.get("/{hour_id}", response_model=HourWithEmployee)
async def get_hour(
        hour_id: str,
        current_user: Dict[str, Any] = Depends(has_permission("hours:read"))
):
    """
    Get hour record by ID
    """
    hour = await HourService.get_hour(hour_id)
    if not hour:
        raise HTTPException(status_code=404, detail="Hour record not found")
    return hour


@router.post("/clock-in", response_model=HourResponse)
async def clock_in_endpoint(
        request: ClockInRequest,
        current_user: Dict[str, Any] = Depends(has_permission("hours:write"))
):
    """
    Clock in for an employee
    """
    return await HourService.clock_in(request.employee_id, request.store_id, request.notes)


@router.post("/clock-out", response_model=HourResponse)
async def clock_out_endpoint(
        request: ClockOutRequest,
        employee_id: str,
        current_user: Dict[str, Any] = Depends(has_permission("hours:write"))
):
    """
    Clock out for an employee
    """
    return await HourService.clock_out(employee_id, request.break_start, request.break_end, request.notes)


@router.post("/", response_model=HourResponse, status_code=status.HTTP_201_CREATED)
async def create_hour(
        hour: HourCreate,
        current_user: Dict[str, Any] = Depends(has_permission("hours:write"))
):
    """
    Create a new hour record manually
    """
    return await HourService.create_hour(hour)


@router.put("/{hour_id}", response_model=HourResponse)
async def update_hour(
        hour_id: str,
        hour: HourUpdate,
        current_user: Dict[str, Any] = Depends(has_permission("hours:write"))
):
    """
    Update an existing hour record
    """
    updated_hour = await HourService.update_hour(hour_id, hour, str(current_user["_id"]))
    if not updated_hour:
        raise HTTPException(status_code=404, detail="Hour record not found")
    return updated_hour


@router.put("/{hour_id}/approve", response_model=HourResponse)
async def approve_hour(
        hour_id: str,
        approval: HourApproval,
        current_user: Dict[str, Any] = Depends(has_permission("hours:approve"))
):
    """
    Approve or reject an hour record
    """
    updated_hour = await HourService.approve_hour(hour_id, approval, str(current_user["_id"]))
    if not updated_hour:
        raise HTTPException(status_code=404, detail="Hour record not found")
    return updated_hour


@router.delete("/{hour_id}", response_model=bool)
async def delete_hour(
        hour_id: str,
        current_user: Dict[str, Any] = Depends(has_permission("hours:delete"))
):
    """
    Delete an hour record
    """
    result = await HourService.delete_hour(hour_id)
    if not result:
        raise HTTPException(status_code=404, detail="Hour record not found")
    return result
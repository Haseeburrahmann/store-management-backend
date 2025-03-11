# app/api/schedules/router.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from datetime import date

from app.dependencies.permissions import get_current_user, has_permission
from app.schemas.schedule import (
    ScheduleCreate, ScheduleUpdate, ScheduleResponse, ScheduleWithDetails,
    ScheduleSummary, ShiftCreate, ShiftUpdate, ShiftResponse
)
from app.services.schedule import ScheduleService

router = APIRouter()


@router.get("/", response_model=List[ScheduleSummary])
async def get_schedules(
        skip: int = 0,
        limit: int = 100,
        store_id: Optional[str] = None,
        week_start_date: Optional[date] = None,
        current_user: dict = Depends(has_permission("stores:read"))
):
    """
    Get all schedules with optional filtering
    """
    return await ScheduleService.get_schedules(
        skip=skip,
        limit=limit,
        store_id=store_id,
        week_start_date=week_start_date
    )


@router.get("/{schedule_id}", response_model=ScheduleWithDetails)
async def get_schedule(
        schedule_id: str,
        current_user: dict = Depends(has_permission("stores:read"))
):
    """
    Get schedule by ID
    """
    schedule = await ScheduleService.get_schedule(schedule_id)

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule with ID {schedule_id} not found"
        )

    return schedule


@router.post("/", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
        schedule: ScheduleCreate,
        current_user: dict = Depends(has_permission("stores:write"))
):
    """
    Create a new schedule
    """
    # Add the current user as creator
    schedule_data = schedule.model_dump()
    schedule_data["created_by"] = str(current_user["_id"])

    return await ScheduleService.create_schedule(schedule_data)


@router.put("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
        schedule_id: str,
        schedule: ScheduleUpdate,
        current_user: dict = Depends(has_permission("stores:write"))
):
    """
    Update a schedule
    """
    updated_schedule = await ScheduleService.update_schedule(
        schedule_id=schedule_id,
        schedule_data=schedule.model_dump(exclude_unset=True)
    )

    if not updated_schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule with ID {schedule_id} not found"
        )

    return updated_schedule


@router.delete("/{schedule_id}", response_model=bool)
async def delete_schedule(
        schedule_id: str,
        current_user: dict = Depends(has_permission("stores:delete"))
):
    """
    Delete a schedule
    """
    result = await ScheduleService.delete_schedule(schedule_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule with ID {schedule_id} not found"
        )

    return result


@router.post("/{schedule_id}/shifts", response_model=ScheduleResponse)
async def add_shift(
        schedule_id: str,
        shift: ShiftCreate,
        current_user: dict = Depends(has_permission("stores:write"))
):
    """
    Add a shift to a schedule
    """
    updated_schedule = await ScheduleService.add_shift(
        schedule_id=schedule_id,
        shift_data=shift.model_dump()
    )

    if not updated_schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule with ID {schedule_id} not found"
        )

    return updated_schedule


@router.put("/{schedule_id}/shifts/{shift_id}", response_model=ScheduleResponse)
async def update_shift(
        schedule_id: str,
        shift_id: str,
        shift: ShiftUpdate,
        current_user: dict = Depends(has_permission("stores:write"))
):
    """
    Update a shift in a schedule
    """
    updated_schedule = await ScheduleService.update_shift(
        schedule_id=schedule_id,
        shift_id=shift_id,
        shift_data=shift.model_dump(exclude_unset=True)
    )

    if not updated_schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule with ID {schedule_id} or shift with ID {shift_id} not found"
        )

    return updated_schedule


@router.delete("/{schedule_id}/shifts/{shift_id}", response_model=ScheduleResponse)
async def delete_shift(
        schedule_id: str,
        shift_id: str,
        current_user: dict = Depends(has_permission("stores:write"))
):
    """
    Delete a shift from a schedule
    """
    updated_schedule = await ScheduleService.delete_shift(
        schedule_id=schedule_id,
        shift_id=shift_id
    )

    if not updated_schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule with ID {schedule_id} or shift with ID {shift_id} not found"
        )

    return updated_schedule


@router.get("/employee/me", response_model=List[dict])
async def get_my_schedule(
        week_start_date: Optional[date] = None,
        current_user: dict = Depends(get_current_user)
):
    """
    Get current user's schedule
    """
    # Get employee ID for current user
    from app.services.employee import EmployeeService
    employee = await EmployeeService.get_employee_by_user_id(str(current_user["_id"]))

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found"
        )

    return await ScheduleService.get_employee_schedule(
        employee_id=str(employee["_id"]),
        week_start_date=week_start_date
    )


@router.get("/employee/{employee_id}", response_model=List[dict])
async def get_employee_schedule(
        employee_id: str,
        week_start_date: Optional[date] = None,
        current_user: dict = Depends(has_permission("stores:read"))
):
    """
    Get employee's schedule
    """
    return await ScheduleService.get_employee_schedule(
        employee_id=employee_id,
        week_start_date=week_start_date
    )


@router.get("/store/{store_id}", response_model=List[ScheduleSummary])
async def get_store_schedules(
        store_id: str,
        week_start_date: Optional[date] = None,
        current_user: dict = Depends(has_permission("stores:read"))
):
    """
    Get all schedules for a store
    """
    return await ScheduleService.get_schedules(
        store_id=store_id,
        week_start_date=week_start_date
    )
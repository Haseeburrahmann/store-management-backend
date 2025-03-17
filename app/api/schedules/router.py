"""
Schedule API routes for schedule management.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from datetime import date

from app.domains.schedules.service import schedule_service
from app.domains.employees.service import employee_service
from app.core.permissions import has_permission, get_current_user
from app.schemas.schedule import (
    ScheduleCreate, ScheduleUpdate, ScheduleResponse, ScheduleWithDetails,
    ScheduleSummary, ShiftCreate, ShiftUpdate, ShiftResponse
)

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
    Get all schedules with optional filtering.

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        store_id: Filter by store ID
        week_start_date: Filter by week start date
        current_user: Current user from token

    Returns:
        List of schedules
    """
    try:
        schedules = await schedule_service.get_schedules(
            skip=skip,
            limit=limit,
            store_id=store_id,
            week_start_date=week_start_date
        )
        return schedules
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching schedules: {str(e)}"
        )


@router.get("/{schedule_id}", response_model=ScheduleWithDetails)
async def get_schedule(
        schedule_id: str,
        current_user: dict = Depends(has_permission("stores:read"))
):
    """
    Get schedule by ID.

    Args:
        schedule_id: Schedule ID
        current_user: Current user from token

    Returns:
        Schedule
    """
    try:
        schedule = await schedule_service.get_schedule(schedule_id)
        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule with ID {schedule_id} not found"
            )
        return schedule
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching schedule: {str(e)}"
        )


@router.post("/", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
        schedule_data: ScheduleCreate,
        current_user: dict = Depends(has_permission("stores:write"))
):
    """
    Create a new schedule.

    Args:
        schedule_data: Schedule creation data
        current_user: Current user from token

    Returns:
        Created schedule
    """
    try:
        # Add the current user as creator
        schedule_dict = schedule_data.model_dump()
        schedule_dict["created_by"] = str(current_user["_id"])

        schedule = await schedule_service.create_schedule(schedule_dict)
        return schedule
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating schedule: {str(e)}"
        )


@router.put("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
        schedule_id: str,
        schedule_data: ScheduleUpdate,
        current_user: dict = Depends(has_permission("stores:write"))
):
    """
    Update an existing schedule.

    Args:
        schedule_id: Schedule ID
        schedule_data: Schedule update data
        current_user: Current user from token

    Returns:
        Updated schedule
    """
    try:
        updated_schedule = await schedule_service.update_schedule(
            schedule_id=schedule_id,
            schedule_data=schedule_data.model_dump(exclude_unset=True)
        )

        if not updated_schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule with ID {schedule_id} not found"
            )

        return updated_schedule
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating schedule: {str(e)}"
        )


@router.delete("/{schedule_id}", response_model=bool)
async def delete_schedule(
        schedule_id: str,
        current_user: dict = Depends(has_permission("stores:delete"))
):
    """
    Delete a schedule.

    Args:
        schedule_id: Schedule ID
        current_user: Current user from token

    Returns:
        True if schedule was deleted
    """
    try:
        result = await schedule_service.delete_schedule(schedule_id)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule with ID {schedule_id} not found"
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting schedule: {str(e)}"
        )


@router.post("/{schedule_id}/shifts", response_model=ScheduleResponse)
async def add_shift(
        schedule_id: str,
        shift_data: ShiftCreate,
        current_user: dict = Depends(has_permission("stores:write"))
):
    """
    Add a shift to a schedule.

    Args:
        schedule_id: Schedule ID
        shift_data: Shift creation data
        current_user: Current user from token

    Returns:
        Updated schedule
    """
    try:
        updated_schedule = await schedule_service.add_shift(
            schedule_id=schedule_id,
            shift_data=shift_data.model_dump()
        )

        if not updated_schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule with ID {schedule_id} not found"
            )

        return updated_schedule
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding shift: {str(e)}"
        )


@router.put("/{schedule_id}/shifts/{shift_id}", response_model=ScheduleResponse)
async def update_shift(
        schedule_id: str,
        shift_id: str,
        shift_data: ShiftUpdate,
        current_user: dict = Depends(has_permission("stores:write"))
):
    """
    Update a shift in a schedule.

    Args:
        schedule_id: Schedule ID
        shift_id: Shift ID
        shift_data: Shift update data
        current_user: Current user from token

    Returns:
        Updated schedule
    """
    try:
        updated_schedule = await schedule_service.update_shift(
            schedule_id=schedule_id,
            shift_id=shift_id,
            shift_data=shift_data.model_dump(exclude_unset=True)
        )

        if not updated_schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule with ID {schedule_id} or shift with ID {shift_id} not found"
            )

        return updated_schedule
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating shift: {str(e)}"
        )


@router.delete("/{schedule_id}/shifts/{shift_id}", response_model=ScheduleResponse)
async def delete_shift(
        schedule_id: str,
        shift_id: str,
        current_user: dict = Depends(has_permission("stores:write"))
):
    """
    Delete a shift from a schedule.

    Args:
        schedule_id: Schedule ID
        shift_id: Shift ID
        current_user: Current user from token

    Returns:
        Updated schedule
    """
    try:
        updated_schedule = await schedule_service.delete_shift(
            schedule_id=schedule_id,
            shift_id=shift_id
        )

        if not updated_schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule with ID {schedule_id} or shift with ID {shift_id} not found"
            )

        return updated_schedule
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting shift: {str(e)}"
        )


@router.get("/employee/me", response_model=List[dict])
async def get_my_schedule(
        week_start_date: Optional[date] = None,
        current_user: dict = Depends(get_current_user)
):
    """
    Get current user's schedule.

    Args:
        week_start_date: Filter by week start date
        current_user: Current user from token

    Returns:
        List of shifts for the current user
    """
    try:
        # Get employee ID for current user
        employee = await employee_service.get_employee_by_user_id(str(current_user["_id"]))

        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee profile not found"
            )

        return await schedule_service.get_employee_schedule(
            employee_id=str(employee["_id"]),
            week_start_date=week_start_date
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching schedule: {str(e)}"
        )


@router.get("/employee/{employee_id}", response_model=List[dict])
async def get_employee_schedule(
        employee_id: str,
        week_start_date: Optional[date] = None,
        current_user: dict = Depends(has_permission("stores:read"))
):
    """
    Get employee's schedule.

    Args:
        employee_id: Employee ID
        week_start_date: Filter by week start date
        current_user: Current user from token

    Returns:
        List of shifts for the employee
    """
    try:
        return await schedule_service.get_employee_schedule(
            employee_id=employee_id,
            week_start_date=week_start_date
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching employee schedule: {str(e)}"
        )


@router.get("/store/{store_id}", response_model=List[ScheduleSummary])
async def get_store_schedules(
        store_id: str,
        week_start_date: Optional[date] = None,
        current_user: dict = Depends(has_permission("stores:read"))
):
    """
    Get all schedules for a store.

    Args:
        store_id: Store ID
        week_start_date: Filter by week start date
        current_user: Current user from token

    Returns:
        List of schedules for the store
    """
    try:
        return await schedule_service.get_schedules_by_store(
            store_id=store_id,
            week_start_date=week_start_date
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching store schedules: {str(e)}"
        )


@router.get("/employee/{employee_id}/all", response_model=List[ScheduleSummary])
async def get_all_employee_schedules(
        employee_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 100,
        current_user: dict = Depends(has_permission("stores:read"))
):
    """
    Get all schedules containing shifts for a specific employee.

    Args:
        employee_id: Employee ID
        start_date: Start date for filtering
        end_date: End date for filtering
        skip: Number of records to skip
        limit: Maximum number of records to return
        current_user: Current user from token

    Returns:
        List of schedules containing shifts for the employee
    """
    try:
        return await schedule_service.get_all_employee_schedules(
            employee_id=employee_id,
            start_date=start_date,
            end_date=end_date,
            skip=skip,
            limit=limit
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching employee schedules: {str(e)}"
        )
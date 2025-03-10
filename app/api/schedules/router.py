# app/api/schedules/router.py
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from datetime import date

from app.dependencies.permissions import get_current_user, has_permission
from app.schemas.schedule import ScheduleCreate, ScheduleUpdate, ScheduleResponse, ScheduleWithDetails
from app.schemas.schedule import ScheduleShiftCreate, ScheduleShiftUpdate, ScheduleShiftResponse
from app.services.schedule import ScheduleService
from app.utils.id_handler import IdHandler

router = APIRouter()


@router.get("/", response_model=List[ScheduleWithDetails])
async def get_schedules(
        skip: int = 0,
        limit: int = 100,
        store_id: Optional[str] = None,
        employee_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        current_user: Dict[str, Any] = Depends(has_permission("stores:read"))
):
    """
    Get all schedules with optional filtering
    """
    try:
        print(f"Getting schedules with filters: store_id={store_id}, employee_id={employee_id}, "
              f"start_date={start_date}, end_date={end_date}")

        # Convert dates to string format if provided
        start_date_str = start_date.isoformat() if start_date else None
        end_date_str = end_date.isoformat() if end_date else None

        return await ScheduleService.get_schedules(
            skip=skip,
            limit=limit,
            store_id=store_id,
            employee_id=employee_id,
            start_date=start_date_str,
            end_date=end_date_str
        )
    except Exception as e:
        print(f"Error getting schedules: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting schedules: {str(e)}"
        )


@router.get("/{schedule_id}", response_model=ScheduleWithDetails)
async def get_schedule(
        schedule_id: str,
        current_user: Dict[str, Any] = Depends(has_permission("stores:read"))
):
    """
    Get schedule by ID
    """
    try:
        print(f"Getting schedule with ID: {schedule_id}")
        schedule = await ScheduleService.get_schedule(schedule_id)

        # Use the helper method to raise a consistent 404 error if not found
        IdHandler.raise_if_not_found(
            schedule,
            f"Schedule with ID {schedule_id} not found",
            status.HTTP_404_NOT_FOUND
        )

        return schedule
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting schedule: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting schedule: {str(e)}"
        )


@router.post("/", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
        schedule: ScheduleCreate,
        current_user: Dict[str, Any] = Depends(has_permission("stores:write"))
):
    """
    Create new schedule
    """
    try:
        print(f"Creating schedule: {schedule.title}")

        # Convert to dict and add created_by field
        schedule_data = schedule.model_dump()
        schedule_data["created_by"] = str(current_user["_id"])

        return await ScheduleService.create_schedule(schedule_data)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating schedule: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating schedule: {str(e)}"
        )


@router.put("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
        schedule_id: str,
        schedule: ScheduleUpdate,
        current_user: Dict[str, Any] = Depends(has_permission("stores:write"))
):
    """
    Update existing schedule
    """
    try:
        print(f"Updating schedule with ID: {schedule_id}")

        # Get update data excluding unset fields
        update_data = schedule.model_dump(exclude_unset=True)

        updated_schedule = await ScheduleService.update_schedule(schedule_id, update_data)

        # Use the helper method to raise a consistent 404 error if not found
        IdHandler.raise_if_not_found(
            updated_schedule,
            f"Schedule with ID {schedule_id} not found",
            status.HTTP_404_NOT_FOUND
        )

        return updated_schedule
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating schedule: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating schedule: {str(e)}"
        )


@router.delete("/{schedule_id}", response_model=bool)
async def delete_schedule(
        schedule_id: str,
        current_user: Dict[str, Any] = Depends(has_permission("stores:delete"))
):
    """
    Delete schedule
    """
    try:
        print(f"Deleting schedule with ID: {schedule_id}")

        # Check if schedule exists first
        schedule = await ScheduleService.get_schedule(schedule_id)
        IdHandler.raise_if_not_found(
            schedule,
            f"Schedule with ID {schedule_id} not found",
            status.HTTP_404_NOT_FOUND
        )

        result = await ScheduleService.delete_schedule(schedule_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting schedule: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting schedule: {str(e)}"
        )


@router.post("/{schedule_id}/shifts", response_model=ScheduleResponse)
async def add_shift(
        schedule_id: str,
        shift: ScheduleShiftCreate,
        current_user: Dict[str, Any] = Depends(has_permission("stores:write"))
):
    """
    Add a shift to a schedule
    """
    try:
        print(f"Adding shift to schedule {schedule_id}")

        # Convert shift to dict
        shift_data = shift.model_dump()

        updated_schedule = await ScheduleService.add_shift(schedule_id, shift_data)

        # Raise 404 if schedule not found
        IdHandler.raise_if_not_found(
            updated_schedule,
            f"Schedule with ID {schedule_id} not found",
            status.HTTP_404_NOT_FOUND
        )

        return updated_schedule
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error adding shift: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding shift: {str(e)}"
        )


@router.put("/{schedule_id}/shifts/{shift_id}", response_model=ScheduleResponse)
async def update_shift(
        schedule_id: str,
        shift_id: str,
        shift: ScheduleShiftUpdate,
        current_user: Dict[str, Any] = Depends(has_permission("stores:write"))
):
    """
    Update a shift in a schedule
    """
    try:
        print(f"Updating shift {shift_id} in schedule {schedule_id}")

        # Get update data excluding unset fields
        update_data = shift.model_dump(exclude_unset=True)

        updated_schedule = await ScheduleService.update_shift(schedule_id, shift_id, update_data)

        # Raise 404 if schedule or shift not found
        IdHandler.raise_if_not_found(
            updated_schedule,
            f"Schedule with ID {schedule_id} or shift with ID {shift_id} not found",
            status.HTTP_404_NOT_FOUND
        )

        return updated_schedule
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating shift: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating shift: {str(e)}"
        )


@router.delete("/{schedule_id}/shifts/{shift_id}", response_model=ScheduleResponse)
async def delete_shift(
        schedule_id: str,
        shift_id: str,
        current_user: Dict[str, Any] = Depends(has_permission("stores:write"))
):
    """
    Delete a shift from a schedule
    """
    try:
        print(f"Deleting shift {shift_id} from schedule {schedule_id}")

        updated_schedule = await ScheduleService.delete_shift(schedule_id, shift_id)

        # Raise 404 if schedule or shift not found
        IdHandler.raise_if_not_found(
            updated_schedule,
            f"Schedule with ID {schedule_id} or shift with ID {shift_id} not found",
            status.HTTP_404_NOT_FOUND
        )

        return updated_schedule
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting shift: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting shift: {str(e)}"
        )


@router.get("/employee/{employee_id}/shifts", response_model=List[Dict[str, Any]])
async def get_employee_shifts(
        employee_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        current_user: Dict[str, Any] = Depends(has_permission("hours:read"))
):
    """
    Get all shifts for an employee
    """
    try:
        print(f"Getting shifts for employee {employee_id} from {start_date} to {end_date}")

        # Convert dates to string format if provided
        start_date_str = start_date.isoformat() if start_date else None
        end_date_str = end_date.isoformat() if end_date else None

        # Get shifts for the employee
        shifts = await ScheduleService.get_employee_shifts(employee_id, start_date_str, end_date_str)

        return shifts
    except Exception as e:
        print(f"Error getting employee shifts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting employee shifts: {str(e)}"
        )


@router.get("/store/{store_id}", response_model=List[ScheduleWithDetails])
async def get_store_schedules(
        store_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        current_user: Dict[str, Any] = Depends(has_permission("stores:read"))
):
    """
    Get all schedules for a store
    """
    try:
        print(f"Getting schedules for store {store_id} from {start_date} to {end_date}")

        # Convert dates to string format if provided
        start_date_str = start_date.isoformat() if start_date else None
        end_date_str = end_date.isoformat() if end_date else None

        return await ScheduleService.get_schedules(
            store_id=store_id,
            start_date=start_date_str,
            end_date=end_date_str
        )
    except Exception as e:
        print(f"Error getting store schedules: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting store schedules: {str(e)}"
        )
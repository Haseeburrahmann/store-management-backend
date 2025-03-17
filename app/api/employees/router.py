"""
Employee API routes for employee management.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.domains.employees.service import employee_service
from app.domains.stores.service import store_service
from app.core.permissions import has_permission, get_current_user
from app.schemas.employee import (
    EmployeeCreate, EmployeeUpdate, EmployeeResponse, EmployeeWithUserInfo,
    EmployeeWithStoreInfo, EmployeeUserCreateModel
)

router = APIRouter()


@router.get("/", response_model=List[EmployeeWithStoreInfo])
async def get_employees(
    skip: int = 0,
    limit: int = 100,
    position: Optional[str] = None,
    store_id: Optional[str] = None,
    status: Optional[str] = None,
    current_user: dict = Depends(has_permission("employees:read"))
):
    """
    Get all employees with optional filtering.

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        position: Filter by position pattern
        store_id: Filter by store ID
        status: Filter by employment status
        current_user: Current user from token

    Returns:
        List of employees
    """
    try:
        employees = await employee_service.get_employees(
            skip=skip,
            limit=limit,
            position=position,
            store_id=store_id,
            status=status
        )
        return employees
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching employees: {str(e)}"
        )


@router.get("/by-store/{store_id}", response_model=List[EmployeeWithUserInfo])
async def get_employees_by_store(
    store_id: str,
    current_user: dict = Depends(has_permission("employees:read"))
):
    """
    Get employees by store ID.

    Args:
        store_id: Store ID
        current_user: Current user from token

    Returns:
        List of employees
    """
    try:
        # First verify store exists
        store = await store_service.get_store(store_id)
        if not store:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Store with ID {store_id} not found"
            )

        return await employee_service.get_employees_by_store(store_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching employees: {str(e)}"
        )


@router.get("/me", response_model=EmployeeWithStoreInfo)
async def get_my_employee_profile(
    current_user: dict = Depends(get_current_user)
):
    """
    Get current user's employee profile.

    Args:
        current_user: Current user from token

    Returns:
        Employee profile
    """
    try:
        employee = await employee_service.get_employee_by_user_id(str(current_user["_id"]))
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee profile not found"
            )
        return employee
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching employee profile: {str(e)}"
        )


@router.get("/{employee_id}", response_model=EmployeeWithStoreInfo)
async def get_employee(
    employee_id: str,
    current_user: dict = Depends(has_permission("employees:read"))
):
    """
    Get employee by ID.

    Args:
        employee_id: Employee ID
        current_user: Current user from token

    Returns:
        Employee
    """
    try:
        employee = await employee_service.get_employee(employee_id)
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee with ID {employee_id} not found"
            )
        return employee
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching employee: {str(e)}"
        )


@router.post("/", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
async def create_employee(
    employee_data: EmployeeCreate,
    current_user: dict = Depends(has_permission("employees:write"))
):
    """
    Create new employee.

    Args:
        employee_data: Employee creation data
        current_user: Current user from token

    Returns:
        Created employee
    """
    try:
        employee = await employee_service.create_employee(employee_data.model_dump())
        return employee
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating employee: {str(e)}"
        )


@router.put("/{employee_id}", response_model=EmployeeResponse)
async def update_employee(
    employee_id: str,
    employee_data: EmployeeUpdate,
    current_user: dict = Depends(has_permission("employees:write"))
):
    """
    Update existing employee.

    Args:
        employee_id: Employee ID
        employee_data: Employee update data
        current_user: Current user from token

    Returns:
        Updated employee
    """
    try:
        updated_employee = await employee_service.update_employee(
            employee_id=employee_id,
            employee_data=employee_data.model_dump(exclude_unset=True)
        )

        if not updated_employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee with ID {employee_id} not found"
            )

        return updated_employee
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating employee: {str(e)}"
        )


@router.delete("/{employee_id}", response_model=bool)
async def delete_employee(
    employee_id: str,
    current_user: dict = Depends(has_permission("employees:delete"))
):
    """
    Delete employee.

    Args:
        employee_id: Employee ID
        current_user: Current user from token

    Returns:
        True if employee was deleted
    """
    try:
        # Check if employee exists
        existing_employee = await employee_service.get_employee(employee_id)
        if not existing_employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee with ID {employee_id} not found"
            )

        # Delete employee
        result = await employee_service.delete_employee(employee_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting employee: {str(e)}"
        )


@router.put("/{employee_id}/assign-store/{store_id}", response_model=EmployeeResponse)
async def assign_to_store(
    employee_id: str,
    store_id: str,
    current_user: dict = Depends(has_permission("employees:write"))
):
    """
    Assign employee to store.

    Args:
        employee_id: Employee ID
        store_id: Store ID
        current_user: Current user from token

    Returns:
        Updated employee
    """
    try:
        # Check if employee exists
        employee = await employee_service.get_employee(employee_id)
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee with ID {employee_id} not found"
            )

        # Check if store exists
        store = await store_service.get_store(store_id)
        if not store:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Store with ID {store_id} not found"
            )

        # Assign employee to store
        updated_employee = await employee_service.assign_to_store(employee_id, store_id)
        if not updated_employee:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to assign employee to store"
            )

        return updated_employee
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error assigning employee to store: {str(e)}"
        )


@router.post("/with-user", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
async def create_employee_with_user(
    data: EmployeeUserCreateModel,
    current_user: dict = Depends(has_permission("employees:write"))
):
    """
    Create a new employee with a user account.

    Args:
        data: Combined user and employee data
        current_user: Current user from token

    Returns:
        Created employee
    """
    try:
        # Convert to dict
        employee_user_data = data.model_dump()

        # Create employee with user
        created_employee = await employee_service.create_employee_with_user(employee_user_data)
        return created_employee
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating employee with user: {str(e)}"
        )
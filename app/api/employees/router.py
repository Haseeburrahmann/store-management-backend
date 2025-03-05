# app/api/employees/router.py
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import ValidationError

from app.dependencies.permissions import get_current_user, has_permission
from app.schemas.employee import EmployeeUpdate, EmployeeResponse, EmployeeWithUserInfo, EmployeeWithStoreInfo, \
    EmployeeUserCreateModel, EmployeeCreate
from app.services.employee import EmployeeService

router = APIRouter()

@router.get("/", response_model=List[EmployeeWithStoreInfo])
async def get_employees(
    skip: int = 0,
    limit: int = 100,
    position: Optional[str] = None,
    store_id: Optional[str] = None,
    status: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(has_permission("employees:read"))
):
    """
    Get all employees with optional filtering
    """
    return await EmployeeService.get_employees(skip, limit, position, store_id, status)

@router.get("/by-store/{store_id}", response_model=List[EmployeeWithUserInfo])
async def get_employees_by_store(
    store_id: str,
    current_user: Dict[str, Any] = Depends(has_permission("employees:read"))
):
    """
    Get employees by store ID
    """
    return await EmployeeService.get_employees_by_store(store_id)

@router.get("/me", response_model=EmployeeWithStoreInfo)
async def get_my_employee_profile(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get current user's employee profile
    """
    employee = await EmployeeService.get_employee_by_user_id(str(current_user["_id"]))
    if not employee:
        raise HTTPException(status_code=404, detail="Employee profile not found")
    return employee

@router.get("/{employee_id}", response_model=EmployeeWithStoreInfo)
async def get_employee(
    employee_id: str,
    current_user: Dict[str, Any] = Depends(has_permission("employees:read"))
):
    """
    Get employee by ID
    """
    employee = await EmployeeService.get_employee(employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee

@router.post("/", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
async def create_employee(
    employee: EmployeeCreate,
    current_user: Dict[str, Any] = Depends(has_permission("employees:write"))
):
    """
    Create new employee
    """
    try:
        print(f"Received employee data: {employee.model_dump()}")
        return await EmployeeService.create_employee(employee.model_dump())
    except ValidationError as e:
        print(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        print(f"Error creating employee: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating employee: {str(e)}"
        )

@router.put("/{employee_id}", response_model=EmployeeResponse)
async def update_employee(
    employee_id: str,
    employee: EmployeeUpdate,
    current_user: Dict[str, Any] = Depends(has_permission("employees:write"))
):
    """
    Update existing employee
    """
    updated_employee = await EmployeeService.update_employee(employee_id, employee.model_dump(exclude_unset=True))
    if not updated_employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return updated_employee

@router.delete("/{employee_id}", response_model=bool)
async def delete_employee(
    employee_id: str,
    current_user: Dict[str, Any] = Depends(has_permission("employees:delete"))
):
    """
    Delete employee
    """
    result = await EmployeeService.delete_employee(employee_id)
    if not result:
        raise HTTPException(status_code=404, detail="Employee not found")
    return result

@router.put("/{employee_id}/assign-store/{store_id}", response_model=EmployeeResponse)
async def assign_to_store(
    employee_id: str,
    store_id: str,
    current_user: Dict[str, Any] = Depends(has_permission("employees:write"))
):
    """
    Assign employee to store
    """
    updated_employee = await EmployeeService.assign_to_store(employee_id, store_id)
    if not updated_employee:
        raise HTTPException(status_code=404, detail="Employee or store not found")
    return updated_employee


@router.post("/with-user", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
async def create_employee_with_user(
        employee_data: EmployeeUserCreateModel,  # You'll need to create this model
        current_user: Dict[str, Any] = Depends(has_permission("employees:write"))
):
    """
    Create a new employee with a user account
    """
    try:
        # Extract user data
        user_data = {
            "email": employee_data.email,
            "full_name": employee_data.full_name,
            "password": employee_data.password,
            "phone_number": employee_data.phone_number,
            "role_id": employee_data.role_id,
            "is_active": True
        }

        # Create user
        from app.services.user import create_user
        user_id = await create_user(user_data)

        # Create employee data
        employee_model_data = employee_data.model_dump(exclude={
            "email", "full_name", "password", "phone_number", "role_id"
        })
        employee_model_data["user_id"] = user_id

        # Create employee
        return await EmployeeService.create_employee(employee_model_data)
    except Exception as e:
        print(f"Error creating employee with user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating employee with user: {str(e)}"
        )
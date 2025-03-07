# app/api/employees/router.py
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import ValidationError

from app.dependencies.permissions import get_current_user, has_permission
from app.schemas.employee import EmployeeUpdate, EmployeeResponse, EmployeeWithUserInfo, EmployeeWithStoreInfo, \
    EmployeeUserCreateModel, EmployeeCreate
from app.services.employee import EmployeeService
from app.services.store import StoreService
from app.services.user import get_user_by_id

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
    print(f"Getting employees with filters: position={position}, store_id={store_id}, status={status}")
    return await EmployeeService.get_employees(skip, limit, position, store_id, status)


@router.get("/by-store/{store_id}", response_model=List[EmployeeWithUserInfo])
async def get_employees_by_store(
        store_id: str,
        current_user: Dict[str, Any] = Depends(has_permission("employees:read"))
):
    """
    Get employees by store ID
    """
    # First verify store exists
    store = await StoreService.get_store(store_id)
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Store with ID {store_id} not found"
        )

    return await EmployeeService.get_employees(store_id=store_id)


@router.get("/me", response_model=EmployeeWithStoreInfo)
async def get_my_employee_profile(
        current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get current user's employee profile
    """
    print(f"Getting employee profile for user: {current_user.get('email')}")
    employee = await EmployeeService.get_employee_by_user_id(str(current_user["_id"]))
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found"
        )
    return employee


@router.get("/{employee_id}", response_model=EmployeeWithStoreInfo)
async def get_employee(
        employee_id: str,
        current_user: Dict[str, Any] = Depends(has_permission("employees:read"))
):
    """
    Get employee by ID
    """
    print(f"Getting employee with ID: {employee_id}")
    employee = await EmployeeService.get_employee(employee_id)
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with ID {employee_id} not found"
        )
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
        print(f"Creating employee: {employee.position}")

        # Validate user_id if provided
        if employee.user_id:
            user = await get_user_by_id(employee.user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"User with ID {employee.user_id} not found"
                )

        # Validate store_id if provided
        if employee.store_id:
            store = await StoreService.get_store(employee.store_id)
            if not store:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Store with ID {employee.store_id} not found"
                )

        return await EmployeeService.create_employee(employee.model_dump())
    except ValidationError as e:
        print(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error: {str(e)}"
        )
    except HTTPException:
        raise
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
    try:
        print(f"Updating employee with ID: {employee_id}")

        # Verify employee exists
        existing_employee = await EmployeeService.get_employee(employee_id)
        if not existing_employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee with ID {employee_id} not found"
            )

        # Get update data
        update_data = employee.model_dump(exclude_unset=True)
        print(f"Update data: {update_data}")

        # Validate user_id if changing
        if update_data.get("user_id"):
            user = await get_user_by_id(update_data["user_id"])
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"User with ID {update_data['user_id']} not found"
                )

        # Validate store_id if changing
        if update_data.get("store_id"):
            store = await StoreService.get_store(update_data["store_id"])
            if not store:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Store with ID {update_data['store_id']} not found"
                )

        # Update employee
        updated_employee = await EmployeeService.update_employee(employee_id, update_data)
        if not updated_employee:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update employee"
            )

        return updated_employee
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating employee: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating employee: {str(e)}"
        )


@router.delete("/{employee_id}", response_model=bool)
async def delete_employee(
        employee_id: str,
        current_user: Dict[str, Any] = Depends(has_permission("employees:delete"))
):
    """
    Delete employee
    """
    try:
        print(f"Deleting employee with ID: {employee_id}")

        # Verify employee exists
        existing_employee = await EmployeeService.get_employee(employee_id)
        if not existing_employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee with ID {employee_id} not found"
            )

        result = await EmployeeService.delete_employee(employee_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting employee: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting employee: {str(e)}"
        )


@router.put("/{employee_id}/assign-store/{store_id}", response_model=EmployeeResponse)
async def assign_to_store(
        employee_id: str,
        store_id: str,
        current_user: Dict[str, Any] = Depends(has_permission("employees:write"))
):
    """
    Assign employee to store
    """
    try:
        print(f"Assigning employee {employee_id} to store {store_id}")

        # Validate both exist before attempting assignment
        employee = await EmployeeService.get_employee(employee_id)
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee with ID {employee_id} not found"
            )

        store = await StoreService.get_store(store_id)
        if not store:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Store with ID {store_id} not found"
            )

        updated_employee = await EmployeeService.assign_to_store(employee_id, store_id)
        if not updated_employee:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to assign employee to store"
            )

        return updated_employee
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error assigning employee to store: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error assigning employee to store: {str(e)}"
        )


@router.post("/with-user", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
async def create_employee_with_user(
        employee_data: EmployeeUserCreateModel,
        current_user: Dict[str, Any] = Depends(has_permission("employees:write"))
):
    """
    Create a new employee with a user account
    """
    try:
        print(f"Creating employee with user account: {employee_data.email}")

        # First check if a user with this email already exists
        from app.services.user import get_user_by_email
        existing_user = await get_user_by_email(employee_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User with email {employee_data.email} already exists"
            )

        # Validate the role if provided
        if employee_data.role_id:
            from app.services.role import get_role_by_id
            role = await get_role_by_id(employee_data.role_id)
            if not role:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Role with ID {employee_data.role_id} not found"
                )

        # Validate store if provided
        if employee_data.store_id:
            store = await StoreService.get_store(employee_data.store_id)
            if not store:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Store with ID {employee_data.store_id} not found"
                )

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
        created_user = await create_user(user_data)
        if not created_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )

        # Create employee data
        employee_model_data = employee_data.model_dump(exclude={
            "email", "full_name", "password", "phone_number", "role_id"
        })
        employee_model_data["user_id"] = str(created_user["_id"])

        # Create employee
        created_employee = await EmployeeService.create_employee(employee_model_data)
        if not created_employee:
            # Try to rollback user creation if employee creation fails
            from app.services.user import delete_user
            await delete_user(str(created_user["_id"]))

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create employee record"
            )

        return created_employee
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating employee with user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating employee with user: {str(e)}"
        )


@router.get("/debug/lookup/{employee_id}")
async def debug_lookup_employee(
        employee_id: str,
        current_user: Dict[str, Any] = Depends(has_permission("employees:read"))
):
    """
    Debug endpoint to test different employee lookup methods
    """
    from app.utils.formatting import ensure_object_id
    from app.core.db import get_employees_collection
    employees_collection = get_employees_collection()

    try:
        result = {
            "requested_id": employee_id,
            "lookup_results": {}
        }

        # Method 1: Direct ObjectId lookup
        obj_id = ensure_object_id(employee_id)
        if obj_id:
            employee = await employees_collection.find_one({"_id": obj_id})
            result["lookup_results"]["objectid_lookup"] = {
                "success": employee is not None,
                "employee_position": employee.get("position") if employee else None
            }
        else:
            result["lookup_results"]["objectid_lookup"] = {
                "success": False,
                "error": "Invalid ObjectId format"
            }

        # Method 2: String ID lookup
        employee = await employees_collection.find_one({"_id": employee_id})
        result["lookup_results"]["string_id_lookup"] = {
            "success": employee is not None,
            "employee_position": employee.get("position") if employee else None
        }

        # Method 3: String comparison
        all_employees = await employees_collection.find().to_list(length=100)
        employee_match = None
        for emp in all_employees:
            if str(emp.get("_id")) == employee_id:
                employee_match = emp
                break

        result["lookup_results"]["string_comparison"] = {
            "success": employee_match is not None,
            "employee_position": employee_match.get("position") if employee_match else None,
            "total_employees_checked": len(all_employees)
        }

        # Method 4: Service method lookup
        employee = await EmployeeService.get_employee(employee_id)
        result["lookup_results"]["service_method"] = {
            "success": employee is not None,
            "employee_position": employee.get("position") if employee else None
        }

        # List all employee IDs for reference
        result["all_employee_ids"] = [str(emp.get("_id")) for emp in all_employees]

        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in debug lookup: {str(e)}"
        )
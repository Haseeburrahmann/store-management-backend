# app/api/employees/router.py
from typing import List, Optional
from fastapi import APIRouter, Depends, Path, Query, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.db import get_database
from app.dependencies.permissions import get_current_user, has_permission
from app.schemas.employee import EmployeeCreate, EmployeeUpdate, Employee, EmployeeWithStore
from app.services.employee import (
    create_employee,
    get_employees,
    get_employee,
    update_employee,
    delete_employee,
    assign_employee_to_store,
    get_employees_by_store
)
from app.schemas.user import UserInDB  # Import UserInDB to ensure correct typing

router = APIRouter(tags=["employees"])


@router.post("/", response_model=Employee, status_code=status.HTTP_201_CREATED)
async def create_new_employee(
        employee_data: EmployeeCreate,
        db: AsyncIOMotorDatabase = Depends(get_database),
        current_user: UserInDB = Depends(get_current_user),
        _: bool = Depends(has_permission("PermissionArea.EMPLOYEES:PermissionAction.WRITE"))
):
    return await create_employee(db, employee_data)


@router.get("/", response_model=List[EmployeeWithStore])
async def read_employees(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=100),
        store_id: Optional[str] = None,
        search: Optional[str] = None,
        status: Optional[str] = None,
        db: AsyncIOMotorDatabase = Depends(get_database),
        current_user: UserInDB = Depends(get_current_user),
        _: bool = Depends(has_permission("PermissionArea.EMPLOYEES:PermissionAction.READ"))
):
    # Access attributes directly, not with get()
    if hasattr(current_user, "role_name") and current_user.role_name == "Manager" and hasattr(current_user,
                                                                                              "managed_store_id"):
        if store_id and store_id != current_user.managed_store_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Managers can only view employees from their assigned store"
            )
        store_id = current_user.managed_store_id

    return await get_employees(db, skip, limit, store_id, search, status)


@router.get("/store/{store_id}", response_model=List[Employee])
async def read_employees_by_store(
        store_id: str = Path(...),
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=100),
        db: AsyncIOMotorDatabase = Depends(get_database),
        current_user: UserInDB = Depends(get_current_user),
        _: bool = Depends(has_permission("PermissionArea.EMPLOYEES:PermissionAction.READ"))
):
    # Access attributes directly, not with get()
    if hasattr(current_user, "role_name") and current_user.role_name == "Manager" and hasattr(current_user,
                                                                                              "managed_store_id"):
        if store_id != current_user.managed_store_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Managers can only view employees from their assigned store"
            )

    return await get_employees_by_store(db, store_id, skip, limit)


@router.get("/{employee_id}", response_model=EmployeeWithStore)
async def read_employee(
        employee_id: str = Path(...),
        db: AsyncIOMotorDatabase = Depends(get_database),
        current_user: UserInDB = Depends(get_current_user),
        _: bool = Depends(has_permission("PermissionArea.EMPLOYEES:PermissionAction.READ"))
):
    employee = await get_employee(db, employee_id)

    # Access attributes directly, not with get()
    if hasattr(current_user, "role_name") and current_user.role_name == "Manager" and hasattr(current_user,
                                                                                              "managed_store_id"):
        if not employee.get("store_id") or employee["store_id"] != current_user.managed_store_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Managers can only view employees from their assigned store"
            )

    return employee


@router.put("/{employee_id}", response_model=Employee)
async def update_existing_employee(
        employee_id: str = Path(...),
        employee_data: EmployeeUpdate = None,
        db: AsyncIOMotorDatabase = Depends(get_database),
        current_user: UserInDB = Depends(get_current_user),
        _: bool = Depends(has_permission("PermissionArea.EMPLOYEES:PermissionAction.WRITE"))
):
    # Get existing employee
    existing_employee = await get_employee(db, employee_id)

    # Access attributes directly, not with get()
    if hasattr(current_user, "role_name") and current_user.role_name == "Manager" and hasattr(current_user,
                                                                                              "managed_store_id"):
        if not existing_employee.get("store_id") or existing_employee["store_id"] != current_user.managed_store_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Managers can only update employees from their assigned store"
            )

    return await update_employee(db, employee_id, employee_data)


@router.delete("/{employee_id}", status_code=status.HTTP_200_OK)
async def delete_existing_employee(
        employee_id: str = Path(...),
        db: AsyncIOMotorDatabase = Depends(get_database),
        current_user: UserInDB = Depends(get_current_user),
        _: bool = Depends(has_permission("PermissionArea.EMPLOYEES:PermissionAction.DELETE"))
):
    # Get existing employee
    existing_employee = await get_employee(db, employee_id)

    # Access attributes directly, not with get()
    if hasattr(current_user, "role_name") and current_user.role_name == "Manager" and hasattr(current_user,
                                                                                              "managed_store_id"):
        if not existing_employee.get("store_id") or existing_employee["store_id"] != current_user.managed_store_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Managers can only delete employees from their assigned store"
            )

    return await delete_employee(db, employee_id)


@router.put("/{employee_id}/assign-store/{store_id}", response_model=Employee)
async def assign_to_store(
        employee_id: str = Path(...),
        store_id: str = Path(...),
        db: AsyncIOMotorDatabase = Depends(get_database),
        current_user: UserInDB = Depends(get_current_user),
        _: bool = Depends(has_permission("PermissionArea.EMPLOYEES:PermissionAction.WRITE"))
):
    # Access attributes directly, not with get()
    if hasattr(current_user, "role_name") and current_user.role_name == "Manager" and hasattr(current_user,
                                                                                              "managed_store_id"):
        if store_id != current_user.managed_store_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Managers can only assign employees to their assigned store"
            )

    return await assign_employee_to_store(db, employee_id, store_id)
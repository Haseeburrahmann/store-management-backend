# app/api/inventory_requests/router.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from datetime import date

from app.dependencies.permissions import get_current_user, has_permission
from app.schemas.inventory_request import (
    InventoryRequestCreate,
    InventoryRequestResponse,
    InventoryRequestSummary,
    InventoryRequestFulfill,
    InventoryRequestCancel
)
from app.services.inventory_request import InventoryRequestService
from app.services.employee import EmployeeService

router = APIRouter()


@router.get("/", response_model=List[InventoryRequestSummary])
async def get_inventory_requests(
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        store_id: Optional[str] = None,
        current_user: dict = Depends(has_permission("inventory:read"))
):
    """
    Get all inventory requests with optional filtering
    """
    return await InventoryRequestService.get_inventory_requests(
        skip=skip,
        limit=limit,
        status=status,
        store_id=store_id
    )


@router.get("/me", response_model=List[InventoryRequestSummary])
async def get_my_inventory_requests(
        status: Optional[str] = None,
        current_user: dict = Depends(get_current_user)
):
    """
    Get current user's inventory requests
    """
    # Get employee ID for current user
    employee = await EmployeeService.get_employee_by_user_id(str(current_user["_id"]))

    if not employee:
        # Return empty list if employee not found
        return []

    # Get requests for this employee
    return await InventoryRequestService.get_employee_inventory_requests(
        employee_id=str(employee["_id"]),
        status=status
    )


@router.get("/{request_id}", response_model=InventoryRequestResponse)
async def get_inventory_request(
        request_id: str,
        current_user: dict = Depends(has_permission("inventory:read"))
):
    """
    Get inventory request by ID
    """
    request = await InventoryRequestService.get_inventory_request(request_id)

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory request with ID {request_id} not found"
        )

    return request


@router.post("/", response_model=InventoryRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_inventory_request(
        request: InventoryRequestCreate,
        current_user: dict = Depends(has_permission("inventory:write"))
):
    """
    Create a new inventory request
    """
    # Get employee ID for current user
    employee = await EmployeeService.get_employee_by_user_id(str(current_user["_id"]))

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found"
        )

    return await InventoryRequestService.create_inventory_request(
        request_data=request.model_dump(),
        employee_id=str(employee["_id"])
    )


@router.put("/{request_id}/fulfill", response_model=InventoryRequestResponse)
async def fulfill_inventory_request(
        request_id: str,
        request_data: InventoryRequestFulfill,
        current_user: dict = Depends(has_permission("inventory:approve"))
):
    """
    Mark an inventory request as fulfilled
    """
    fulfilled_request = await InventoryRequestService.fulfill_inventory_request(
        request_id=request_id,
        fulfilled_by=str(current_user["_id"]),
        notes=request_data.notes
    )

    if not fulfilled_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory request with ID {request_id} not found"
        )

    return fulfilled_request


@router.put("/{request_id}/cancel", response_model=InventoryRequestResponse)
async def cancel_inventory_request(
        request_id: str,
        request_data: InventoryRequestCancel,
        current_user: dict = Depends(has_permission("inventory:write"))
):
    """
    Cancel an inventory request
    """
    # First verify this request belongs to the current user or user has admin permissions
    request = await InventoryRequestService.get_inventory_request(request_id)

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory request with ID {request_id} not found"
        )

    # Get employee for current user
    employee = await EmployeeService.get_employee_by_user_id(str(current_user["_id"]))

    # Check if user has inventory:delete permission, which would allow canceling any request
    has_delete_permission = False
    from app.dependencies.permissions import get_user_permissions
    user_permissions = await get_user_permissions(current_user)
    from app.core.security import check_permissions
    if check_permissions(user_permissions, "inventory:delete"):
        has_delete_permission = True

    # Only allow employee who created the request to cancel it, unless they have delete permission
    if not has_delete_permission and (not employee or str(request["employee_id"]) != str(employee["_id"])):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only cancel your own inventory requests"
        )

    cancelled_request = await InventoryRequestService.cancel_inventory_request(
        request_id=request_id,
        reason=request_data.reason
    )

    return cancelled_request


@router.get("/store/{store_id}", response_model=List[InventoryRequestSummary])
async def get_store_inventory_requests(
        store_id: str,
        status: Optional[str] = None,
        current_user: dict = Depends(has_permission("inventory:read"))
):
    """
    Get inventory requests for a specific store
    """
    # Verify store exists
    from app.services.store import StoreService
    store = await StoreService.get_store(store_id)

    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Store with ID {store_id} not found"
        )

    return await InventoryRequestService.get_store_inventory_requests(
        store_id=store_id,
        status=status
    )
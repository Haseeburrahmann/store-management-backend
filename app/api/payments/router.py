# app/api/payments/router.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from datetime import date

from app.dependencies.permissions import get_current_user, has_permission
from app.schemas.payment import (
    PaymentCreate, PaymentUpdate, PaymentResponse, PaymentWithDetails,
    PaymentStatusUpdate, PaymentConfirmation, PaymentDispute,
    PaymentGenerationRequest, PaymentSummary
)
from app.services.payment import PaymentService
from app.services.employee import EmployeeService

router = APIRouter()


@router.get("/", response_model=List[PaymentSummary])
async def get_payments(
        skip: int = 0,
        limit: int = 100,
        employee_id: Optional[str] = None,
        store_id: Optional[str] = None,  # Add this parameter
        status: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        current_user: dict = Depends(has_permission("payments:read"))
):
    """
    Get all payments with optional filtering
    """
    print(f"Request for payments with store_id: {store_id}, type: {type(store_id)}")

    return await PaymentService.get_payments(
        skip=skip,
        limit=limit,
        employee_id=employee_id,
        store_id=store_id,  # Make sure to pass it here too
        status=status,
        start_date=start_date,
        end_date=end_date
    )


@router.post("/generate", response_model=List[PaymentResponse])
async def generate_payments(
        request: PaymentGenerationRequest,
        current_user: dict = Depends(has_permission("payments:write"))
):
    """
    Generate payments for approved timesheets in a specific period
    """
    return await PaymentService.generate_payments_for_period(
        start_date=request.start_date,
        end_date=request.end_date,
        store_id=request.store_id  # Pass optional store_id for filtering
    )

@router.get("/me", response_model=List[PaymentSummary])
async def get_my_payments(
        status: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        current_user: dict = Depends(get_current_user)
):
    """
    Get current user's payments
    """
    try:
        # Get employee ID for current user
        employee = await EmployeeService.get_employee_by_user_id(str(current_user["_id"]))

        if not employee:
            # Return empty list if employee not found, instead of 404 error
            return []

        # Get payments for this employee
        return await PaymentService.get_employee_payments(
            employee_id=str(employee["_id"]),
            status=status,
            start_date=start_date,
            end_date=end_date
        )
    except Exception as e:
        # Log the error for debugging
        print(f"Error in get_my_payments: {str(e)}")
        # Return a proper error response
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching payments: {str(e)}"
        )


@router.get("/{payment_id}", response_model=PaymentWithDetails)
async def get_payment(
        payment_id: str,
        include_timesheet_details: bool = False,
        current_user: dict = Depends(has_permission("payments:read"))
):
    """
    Get payments by ID with optional timesheet details
    """
    payment = await PaymentService.get_payment(
        payment_id=payment_id,
        include_timesheet_details=include_timesheet_details
    )

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment with ID {payment_id} not found"
        )

    return payment


@router.post("/", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
        payment: PaymentCreate,
        current_user: dict = Depends(has_permission("payments:write"))
):
    """
    Create a new payments manually
    """
    return await PaymentService.create_payment(payment.model_dump())


@router.put("/{payment_id}", response_model=PaymentResponse)
async def update_payment(
        payment_id: str,
        payment: PaymentUpdate,
        current_user: dict = Depends(has_permission("payments:write"))
):
    """
    Update a payments
    """
    # Only allow updating status and notes
    updated_payment = await PaymentService.update_payment_status(
        payment_id=payment_id,
        new_status=payment.status,
        notes=payment.notes
    )

    if not updated_payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment with ID {payment_id} not found"
        )

    return updated_payment


@router.delete("/{payment_id}", response_model=bool)
async def delete_payment(
        payment_id: str,
        current_user: dict = Depends(has_permission("payments:delete"))
):
    """
    Delete a payments (only allowed for pending or cancelled payments)
    """
    result = await PaymentService.delete_payment(payment_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment with ID {payment_id} not found"
        )

    return result


@router.post("/{payment_id}/process", response_model=PaymentResponse)
async def process_payment(
        payment_id: str,
        payment_data: PaymentStatusUpdate,
        current_user: dict = Depends(has_permission("payments:approve"))
):
    """
    Process a payments (mark as paid)
    """
    if payment_data.status != "paid":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status. Must be 'paid' for processing"
        )

    updated_payment = await PaymentService.process_payment(
        payment_id=payment_id,
        notes=payment_data.notes
    )

    if not updated_payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment with ID {payment_id} not found"
        )

    return updated_payment


@router.post("/{payment_id}/confirm", response_model=PaymentResponse)
async def confirm_payment(
        payment_id: str,
        confirmation: PaymentConfirmation,
        current_user: dict = Depends(get_current_user)
):
    """
    Confirm receipt of payments as an employee
    """
    # First, verify this payments belongs to the current user
    payment = await PaymentService.get_payment(payment_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment with ID {payment_id} not found"
        )

    # Get employee for current user
    employee = await EmployeeService.get_employee_by_user_id(str(current_user["_id"]))
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have an employee profile"
        )

    # Verify payments belongs to this employee
    if str(payment["employee_id"]) != str(employee["_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only confirm your own payments"
        )

    # Verify payments is in 'paid' status
    if payment["status"] != "paid":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot confirm payments in {payment['status']} status. Payment must be in 'paid' status"
        )

    # Confirm the payments
    updated_payment = await PaymentService.confirm_payment(
        payment_id=payment_id,
        notes=confirmation.notes
    )

    return updated_payment


@router.post("/{payment_id}/dispute", response_model=PaymentResponse)
async def dispute_payment(
        payment_id: str,
        dispute: PaymentDispute,
        current_user: dict = Depends(get_current_user)
):
    """
    Dispute a payments as an employee
    """
    # First, verify this payments belongs to the current user
    payment = await PaymentService.get_payment(payment_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment with ID {payment_id} not found"
        )

    # Get employee for current user
    employee = await EmployeeService.get_employee_by_user_id(str(current_user["_id"]))
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have an employee profile"
        )

    # Verify payments belongs to this employee
    if str(payment["employee_id"]) != str(employee["_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only dispute your own payments"
        )

    # Verify payments is in 'paid' status
    if payment["status"] != "paid":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot dispute payments in {payment['status']} status. Payment must be in 'paid' status"
        )

    # Dispute the payments
    updated_payment = await PaymentService.dispute_payment(
        payment_id=payment_id,
        reason=dispute.reason,
        details=dispute.details
    )

    return updated_payment


@router.post("/{payment_id}/cancel", response_model=PaymentResponse)
async def cancel_payment(
        payment_id: str,
        payment_data: PaymentStatusUpdate,
        current_user: dict = Depends(has_permission("payments:approve"))
):
    """
    Cancel a payments
    """
    if payment_data.status != "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status. Must be 'cancelled' for cancellation"
        )

    updated_payment = await PaymentService.cancel_payment(
        payment_id=payment_id,
        reason=payment_data.notes
    )

    if not updated_payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment with ID {payment_id} not found"
        )

    return updated_payment
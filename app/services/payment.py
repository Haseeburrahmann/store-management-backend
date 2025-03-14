# app/services/payment.py
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
from bson import ObjectId
from fastapi import HTTPException, status

from app.core.db import get_database, get_payments_collection, get_timesheets_collection, get_employees_collection
from app.models.payment import PaymentModel, PaymentStatus
from app.utils.id_handler import IdHandler
from app.utils.datetime_handler import DateTimeHandler

# Get database and collections
db = get_database()
payments_collection = get_payments_collection()
timesheets_collection = get_timesheets_collection()
employees_collection = get_employees_collection()


class PaymentService:
    @staticmethod
    async def get_payments(
            skip: int = 0,
            limit: int = 100,
            employee_id: Optional[str] = None,
            status: Optional[str] = None,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """Get payments with optional filtering"""
        try:
            query = {}

            if employee_id:
                query["employee_id"] = employee_id

            if status:
                # Handle multiple status values (comma-separated)
                if ',' in status:
                    statuses = [s.strip() for s in status.split(',')]
                    query["status"] = {"$in": statuses}
                else:
                    query["status"] = status

            if start_date:
                query["period_end_date"] = {"$gte": datetime.combine(start_date, datetime.min.time())}

            if end_date:
                query["period_start_date"] = {"$lte": datetime.combine(end_date, datetime.min.time())}

            payments = await payments_collection.find(query).skip(skip).limit(limit).to_list(length=limit)

            # Enrich with employee names
            result = []
            for payment in payments:
                payment_with_info = dict(payment)

                # Get employee info if available
                if "employee_id" in payment:
                    employee, _ = await IdHandler.find_document_by_id(
                        employees_collection,
                        payment["employee_id"],
                        not_found_msg=f"Employee not found for ID: {payment['employee_id']}"
                    )

                    if employee and "user_id" in employee:
                        from app.services.user import get_user_by_id
                        user = await get_user_by_id(employee["user_id"])
                        if user:
                            payment_with_info["employee_name"] = user["full_name"]

                # Format all IDs consistently
                payment_with_info = IdHandler.format_object_ids(payment_with_info)
                result.append(payment_with_info)

            return result
        except Exception as e:
            print(f"Error getting payments: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    @staticmethod
    async def get_payment(payment_id: str, include_timesheet_details: bool = False) -> Optional[Dict[str, Any]]:
        """Get a single payment by ID with optional timesheet details"""
        try:
            payment, payment_obj_id = await IdHandler.find_document_by_id(
                payments_collection,
                payment_id,
                not_found_msg=f"Payment with ID {payment_id} not found"
            )

            if not payment:
                return None

            # Format for API response
            payment_with_info = dict(payment)

            # Get employee info if available
            if "employee_id" in payment:
                employee, _ = await IdHandler.find_document_by_id(
                    employees_collection,
                    payment["employee_id"],
                    not_found_msg=f"Employee not found for ID: {payment['employee_id']}"
                )

                if employee and "user_id" in employee:
                    from app.services.user import get_user_by_id
                    user = await get_user_by_id(employee["user_id"])
                    if user:
                        payment_with_info["employee_name"] = user["full_name"]

            # Include timesheet details if requested
            if include_timesheet_details and "timesheet_ids" in payment:
                timesheet_details = []
                for timesheet_id in payment["timesheet_ids"]:
                    timesheet, _ = await IdHandler.find_document_by_id(
                        timesheets_collection,
                        timesheet_id,
                        not_found_msg=f"Timesheet not found for ID: {timesheet_id}"
                    )
                    if timesheet:
                        timesheet_details.append(IdHandler.format_object_ids(timesheet))

                payment_with_info["timesheet_details"] = timesheet_details

            # Format all IDs consistently
            return IdHandler.format_object_ids(payment_with_info)

        except Exception as e:
            print(f"Error getting payment: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    @staticmethod
    async def create_payment(payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a single payment manually"""
        try:
            # Validate required fields
            for field in ["employee_id", "period_start_date", "period_end_date", "total_hours", "hourly_rate"]:
                if field not in payment_data:
                    raise ValueError(f"Missing required field: {field}")

            # Check if employee exists
            employee, employee_obj_id = await IdHandler.find_document_by_id(
                employees_collection,
                payment_data["employee_id"],
                not_found_msg=f"Employee with ID {payment_data['employee_id']} not found"
            )

            if not employee:
                raise ValueError(f"Employee with ID {payment_data['employee_id']} not found")

            # Store the standardized employee_id
            payment_data["employee_id"] = IdHandler.id_to_str(employee_obj_id)

            # Validate timesheets if provided
            if "timesheet_ids" in payment_data and payment_data["timesheet_ids"]:
                validated_timesheet_ids = []
                for timesheet_id in payment_data["timesheet_ids"]:
                    timesheet, timesheet_obj_id = await IdHandler.find_document_by_id(
                        timesheets_collection,
                        timesheet_id,
                        not_found_msg=f"Timesheet with ID {timesheet_id} not found"
                    )

                    if not timesheet:
                        raise ValueError(f"Timesheet with ID {timesheet_id} not found")

                    # Check if timesheet is already linked to another payment
                    if "payment_id" in timesheet and timesheet["payment_id"]:
                        existing_payment_id = IdHandler.id_to_str(timesheet["payment_id"])
                        raise ValueError(f"Timesheet {timesheet_id} is already linked to payment {existing_payment_id}")

                    validated_timesheet_ids.append(IdHandler.id_to_str(timesheet_obj_id))

                payment_data["timesheet_ids"] = validated_timesheet_ids

            # Handle date conversions for proper MongoDB storage
            if isinstance(payment_data["period_start_date"], str):
                date_obj = DateTimeHandler.parse_date(payment_data["period_start_date"])
                payment_data["period_start_date"] = datetime.combine(date_obj, datetime.min.time())
            elif isinstance(payment_data["period_start_date"], date) and not isinstance(
                    payment_data["period_start_date"], datetime):
                payment_data["period_start_date"] = datetime.combine(payment_data["period_start_date"],
                                                                     datetime.min.time())

            if isinstance(payment_data["period_end_date"], str):
                date_obj = DateTimeHandler.parse_date(payment_data["period_end_date"])
                payment_data["period_end_date"] = datetime.combine(date_obj, datetime.min.time())
            elif isinstance(payment_data["period_end_date"], date) and not isinstance(payment_data["period_end_date"],
                                                                                      datetime):
                payment_data["period_end_date"] = datetime.combine(payment_data["period_end_date"], datetime.min.time())

            # Calculate gross amount if not provided
            if "gross_amount" not in payment_data or not payment_data["gross_amount"]:
                payment_data["gross_amount"] = round(payment_data["total_hours"] * payment_data["hourly_rate"], 2)

            # Set default values
            payment_data["status"] = PaymentStatus.PENDING
            payment_data["created_at"] = datetime.utcnow()
            payment_data["updated_at"] = datetime.utcnow()

            # Create the payment
            result = await payments_collection.insert_one(payment_data)
            payment_id = result.inserted_id

            # Update linked timesheets to reference this payment
            if "timesheet_ids" in payment_data and payment_data["timesheet_ids"]:
                for timesheet_id in payment_data["timesheet_ids"]:
                    await timesheets_collection.update_one(
                        {"_id": IdHandler.ensure_object_id(timesheet_id)},
                        {"$set": {"payment_id": payment_id}}
                    )

            # Get the created payment
            created_payment = await payments_collection.find_one({"_id": payment_id})

            # Return formatted payment
            return IdHandler.format_object_ids(created_payment)
        except ValueError as e:
            print(f"Validation error creating payment: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            print(f"Error creating payment: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating payment: {str(e)}"
            )

    @staticmethod
    async def update_payment_status(
            payment_id: str,
            new_status: str,
            notes: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Update the status of a payment"""
        try:
            # Find payment using IdHandler
            payment, payment_obj_id = await IdHandler.find_document_by_id(
                payments_collection,
                payment_id,
                not_found_msg=f"Payment with ID {payment_id} not found"
            )

            if not payment:
                return None

            # Validate status transition
            current_status = payment["status"]
            valid_transitions = {
                PaymentStatus.PENDING: [PaymentStatus.PAID, PaymentStatus.CANCELLED],
                PaymentStatus.PAID: [PaymentStatus.CONFIRMED, PaymentStatus.DISPUTED],
                PaymentStatus.DISPUTED: [PaymentStatus.PAID, PaymentStatus.CANCELLED],
                PaymentStatus.CONFIRMED: [],  # Terminal state
                PaymentStatus.CANCELLED: [PaymentStatus.PENDING]  # Allow reactivation
            }

            if new_status not in valid_transitions.get(current_status, []):
                raise ValueError(f"Invalid status transition from {current_status} to {new_status}")

            # Update data fields based on status
            update_data = {
                "status": new_status,
                "updated_at": datetime.utcnow()
            }

            if notes:
                update_data["notes"] = notes

            if new_status == PaymentStatus.PAID:
                update_data["payment_date"] = datetime.utcnow()
            elif new_status == PaymentStatus.CONFIRMED:
                update_data["confirmation_date"] = datetime.utcnow()

            # Perform update
            result = await payments_collection.update_one(
                {"_id": payment_obj_id},
                {"$set": update_data}
            )

            if result.modified_count == 0:
                return None

            # Return updated payment
            updated_payment = await payments_collection.find_one({"_id": payment_obj_id})
            return IdHandler.format_object_ids(updated_payment)
        except ValueError as e:
            print(f"Validation error updating payment status: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            print(f"Error updating payment status: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error updating payment status: {str(e)}"
            )

    @staticmethod
    async def delete_payment(payment_id: str) -> bool:
        """Delete a payment if it's in pending or cancelled status"""
        try:
            # Find payment using IdHandler
            payment, payment_obj_id = await IdHandler.find_document_by_id(
                payments_collection,
                payment_id,
                not_found_msg=f"Payment with ID {payment_id} not found"
            )

            if not payment:
                return False

            # Only allow deletion of pending or cancelled payments
            if payment["status"] not in [PaymentStatus.PENDING, PaymentStatus.CANCELLED]:
                raise ValueError(f"Cannot delete payment in {payment['status']} status")

            # Remove payment references from timesheets
            if "timesheet_ids" in payment and payment["timesheet_ids"]:
                for timesheet_id in payment["timesheet_ids"]:
                    await timesheets_collection.update_one(
                        {"_id": IdHandler.ensure_object_id(timesheet_id)},
                        {"$unset": {"payment_id": ""}}
                    )

            # Delete the payment
            result = await payments_collection.delete_one({"_id": payment_obj_id})

            return result.deleted_count > 0
        except ValueError as e:
            print(f"Validation error deleting payment: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            print(f"Error deleting payment: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error deleting payment: {str(e)}"
            )

    @staticmethod
    async def generate_payments_for_period(
            start_date: date,
            end_date: date
    ) -> List[Dict[str, Any]]:
        """Generate payments from approved timesheets for a specific period"""
        try:
            # Convert dates to datetime for MongoDB query
            if isinstance(start_date, str):
                start_date = DateTimeHandler.parse_date(start_date)
            if isinstance(end_date, str):
                end_date = DateTimeHandler.parse_date(end_date)

            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())

            # Find approved timesheets in the period that aren't already linked to a payment
            timesheets = await timesheets_collection.find({
                "status": "approved",
                "week_start_date": {"$gte": start_datetime},
                "week_end_date": {"$lte": end_datetime},
                "$or": [
                    {"payment_id": {"$exists": False}},
                    {"payment_id": None}
                ]
            }).to_list(length=1000)

            print(f"Found {len(timesheets)} approved timesheets for payment generation")

            # Group timesheets by employee
            employee_timesheets = {}
            for timesheet in timesheets:
                emp_id = IdHandler.id_to_str(timesheet["employee_id"])
                if emp_id not in employee_timesheets:
                    employee_timesheets[emp_id] = []
                employee_timesheets[emp_id].append(timesheet)

            # Generate a payment for each employee
            generated_payments = []
            for employee_id, emp_timesheets in employee_timesheets.items():
                if not emp_timesheets:
                    continue

                # Get employee data to ensure they exist
                employee, _ = await IdHandler.find_document_by_id(
                    employees_collection,
                    employee_id,
                    not_found_msg=f"Employee with ID {employee_id} not found"
                )

                if not employee:
                    print(f"Warning: Employee with ID {employee_id} not found, skipping payment generation")
                    continue

                # Calculate payment details
                total_hours = sum(ts["total_hours"] for ts in emp_timesheets)
                # Use the most recent hourly rate in case it changed
                hourly_rate = emp_timesheets[0]["hourly_rate"]
                gross_amount = round(total_hours * hourly_rate, 2)

                # Create payment record
                payment_data = {
                    "employee_id": employee_id,
                    "timesheet_ids": [IdHandler.id_to_str(ts["_id"]) for ts in emp_timesheets],
                    "period_start_date": start_date,
                    "period_end_date": end_date,
                    "total_hours": total_hours,
                    "hourly_rate": hourly_rate,
                    "gross_amount": gross_amount,
                    "status": PaymentStatus.PENDING,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }

                # Insert payment
                result = await payments_collection.insert_one(payment_data)
                payment_id = result.inserted_id

                # Update timesheets to reference this payment
                for ts in emp_timesheets:
                    await timesheets_collection.update_one(
                        {"_id": ts["_id"]},
                        {"$set": {"payment_id": payment_id}}
                    )

                # Get the created payment
                payment = await payments_collection.find_one({"_id": payment_id})
                generated_payments.append(IdHandler.format_object_ids(payment))

            return generated_payments
        except Exception as e:
            print(f"Error generating payments: {str(e)}")
            import traceback
            traceback.print_exc()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error generating payments: {str(e)}"
            )

    @staticmethod
    async def get_employee_payments(
            employee_id: str,
            status: Optional[str] = None,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """Get payments for a specific employee"""
        try:
            # Build query for employee payments
            query = {"employee_id": employee_id}

            if status:
                # Handle multiple status values (comma-separated)
                if ',' in status:
                    statuses = [s.strip() for s in status.split(',')]
                    query["status"] = {"$in": statuses}
                else:
                    query["status"] = status

            if start_date:
                query["period_end_date"] = {"$gte": datetime.combine(start_date, datetime.min.time())}

            if end_date:
                query["period_start_date"] = {"$lte": datetime.combine(end_date, datetime.min.time())}

            # Get payments
            payments = await payments_collection.find(query).sort("period_start_date", -1).to_list(length=100)

            # Format and return
            return [IdHandler.format_object_ids(payment) for payment in payments]
        except Exception as e:
            print(f"Error getting employee payments: {str(e)}")
            return []

    @staticmethod
    async def confirm_payment(
            payment_id: str,
            notes: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Confirm receipt of a payment by an employee"""
        return await PaymentService.update_payment_status(
            payment_id=payment_id,
            new_status=PaymentStatus.CONFIRMED,
            notes=notes
        )

    @staticmethod
    async def dispute_payment(
            payment_id: str,
            reason: str,
            details: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Dispute a payment with a reason"""
        notes = f"Disputed: {reason}"
        if details:
            notes += f" - {details}"

        return await PaymentService.update_payment_status(
            payment_id=payment_id,
            new_status=PaymentStatus.DISPUTED,
            notes=notes
        )

    @staticmethod
    async def process_payment(
            payment_id: str,
            notes: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Mark a payment as paid (processed)"""
        return await PaymentService.update_payment_status(
            payment_id=payment_id,
            new_status=PaymentStatus.PAID,
            notes=notes
        )

    @staticmethod
    async def cancel_payment(
            payment_id: str,
            reason: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Cancel a payment"""
        return await PaymentService.update_payment_status(
            payment_id=payment_id,
            new_status=PaymentStatus.CANCELLED,
            notes=reason
        )
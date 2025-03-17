# app/services/inventory_request.py
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status

from app.core.db import get_database, get_employees_collection, get_stores_collection
from app.models.inventory_request import InventoryRequestModel, InventoryRequestStatus
from app.utils.id_handler import IdHandler
from app.utils.datetime_handler import DateTimeHandler

# Get database and setup collection
db = get_database()
inventory_requests_collection = db.inventory_requests
employees_collection = get_employees_collection()
stores_collection = get_stores_collection()


class InventoryRequestService:
    @staticmethod
    async def get_inventory_requests(
            skip: int = 0,
            limit: int = 100,
            store_id: Optional[str] = None,
            employee_id: Optional[str] = None,
            status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get inventory requests with optional filtering"""
        try:
            query = {}

            # Add filters if provided
            if store_id:
                query["store_id"] = store_id

            if employee_id:
                query["employee_id"] = employee_id

            if status:
                # Handle multiple statuses (comma-separated)
                if ',' in status:
                    statuses = [s.strip() for s in status.split(',')]
                    query["status"] = {"$in": statuses}
                else:
                    query["status"] = status

            # Get requests from database
            requests = await inventory_requests_collection.find(query).sort("created_at", -1).skip(skip).limit(limit).to_list(length=limit)

            # Enrich with employee and store names
            result = []
            for request in requests:
                request_with_info = dict(request)
                request_with_info["item_count"] = len(request.get("items", []))

                # Get employee info if available
                if "employee_id" in request:
                    employee, _ = await IdHandler.find_document_by_id(
                        employees_collection,
                        request["employee_id"],
                        not_found_msg=f"Employee not found for ID: {request['employee_id']}"
                    )

                    if employee and "user_id" in employee:
                        from app.services.user import get_user_by_id
                        user = await get_user_by_id(employee["user_id"])
                        if user:
                            request_with_info["employee_name"] = user["full_name"]

                # Get store info if available
                if "store_id" in request:
                    store, _ = await IdHandler.find_document_by_id(
                        stores_collection,
                        request["store_id"],
                        not_found_msg=f"Store not found for ID: {request['store_id']}"
                    )

                    if store:
                        request_with_info["store_name"] = store["name"]

                # Get fulfiller info if available
                if "fulfilled_by" in request and request["fulfilled_by"]:
                    from app.services.user import get_user_by_id
                    user = await get_user_by_id(request["fulfilled_by"])
                    if user:
                        request_with_info["fulfilled_by_name"] = user["full_name"]

                # Format all IDs consistently
                request_with_info = IdHandler.format_object_ids(request_with_info)
                result.append(request_with_info)

            return result
        except Exception as e:
            print(f"Error getting inventory requests: {str(e)}")
            return []

    @staticmethod
    async def get_inventory_request(request_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific inventory request by ID"""
        try:
            # Find request using IdHandler
            request, _ = await IdHandler.find_document_by_id(
                inventory_requests_collection,
                request_id,
                not_found_msg=f"Inventory request with ID {request_id} not found"
            )

            if not request:
                return None

            # Add additional info
            request_with_info = dict(request)

            # Get employee info if available
            if "employee_id" in request:
                employee, _ = await IdHandler.find_document_by_id(
                    employees_collection,
                    request["employee_id"],
                    not_found_msg=f"Employee not found for ID: {request['employee_id']}"
                )

                if employee and "user_id" in employee:
                    from app.services.user import get_user_by_id
                    user = await get_user_by_id(employee["user_id"])
                    if user:
                        request_with_info["employee_name"] = user["full_name"]

            # Get store info if available
            if "store_id" in request:
                store, _ = await IdHandler.find_document_by_id(
                    stores_collection,
                    request["store_id"],
                    not_found_msg=f"Store not found for ID: {request['store_id']}"
                )

                if store:
                    request_with_info["store_name"] = store["name"]

            # Get fulfiller info if available
            if "fulfilled_by" in request and request["fulfilled_by"]:
                from app.services.user import get_user_by_id
                user = await get_user_by_id(request["fulfilled_by"])
                if user:
                    request_with_info["fulfilled_by_name"] = user["full_name"]

            # Format all IDs consistently
            return IdHandler.format_object_ids(request_with_info)
        except Exception as e:
            print(f"Error getting inventory request: {str(e)}")
            return None

    @staticmethod
    async def create_inventory_request(request_data: Dict[str, Any], employee_id: str) -> Dict[str, Any]:
        """Create a new inventory request"""
        try:
            # Validate required fields
            for field in ["store_id", "items"]:
                if field not in request_data:
                    raise ValueError(f"Missing required field: {field}")

            # Check if store exists using IdHandler
            store, store_obj_id = await IdHandler.find_document_by_id(
                stores_collection,
                request_data["store_id"],
                not_found_msg=f"Store with ID {request_data['store_id']} not found"
            )

            if not store:
                raise ValueError(f"Store with ID {request_data['store_id']} not found")

            # Store the standardized store_id
            request_data["store_id"] = IdHandler.id_to_str(store_obj_id)

            # Check if employee exists using IdHandler
            employee, employee_obj_id = await IdHandler.find_document_by_id(
                employees_collection,
                employee_id,
                not_found_msg=f"Employee with ID {employee_id} not found"
            )

            if not employee:
                raise ValueError(f"Employee with ID {employee_id} not found")

            # Store the standardized employee_id
            request_data["employee_id"] = IdHandler.id_to_str(employee_obj_id)

            # Validate items array
            if not request_data["items"] or not isinstance(request_data["items"], list) or len(request_data["items"]) == 0:
                raise ValueError("Items must be a non-empty list")

            for item in request_data["items"]:
                if not item.get("name"):
                    raise ValueError("All items must have a name")
                if "quantity" not in item:
                    raise ValueError("All items must have a quantity")
                if not item.get("unit_type"):
                    raise ValueError("All items must have a unit type")

            # Set default values
            request_data["status"] = InventoryRequestStatus.PENDING
            request_data["created_at"] = datetime.utcnow()
            request_data["updated_at"] = datetime.utcnow()

            # Insert into database
            result = await inventory_requests_collection.insert_one(request_data)
            inserted_id = result.inserted_id

            # Get the created request
            created_request, _ = await IdHandler.find_document_by_id(
                inventory_requests_collection,
                str(inserted_id),
                not_found_msg="Failed to retrieve created inventory request"
            )

            if not created_request:
                raise ValueError("Failed to retrieve created inventory request")

            # Format and return
            return IdHandler.format_object_ids(created_request)
        except ValueError as e:
            print(f"Validation error creating inventory request: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            print(f"Error creating inventory request: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating inventory request: {str(e)}"
            )

    @staticmethod
    async def update_inventory_request(request_id: str, request_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing inventory request"""
        try:
            # Find request using IdHandler
            request, request_obj_id = await IdHandler.find_document_by_id(
                inventory_requests_collection,
                request_id,
                not_found_msg=f"Inventory request with ID {request_id} not found"
            )

            if not request:
                return None

            # Check if request is in pending status
            if request["status"] != InventoryRequestStatus.PENDING:
                raise ValueError(f"Cannot update inventory request in {request['status']} status")

            # Prepare update data
            update_data = {
                "updated_at": datetime.utcnow()
            }

            # Update items if provided
            if "items" in request_data and request_data["items"]:
                update_data["items"] = request_data["items"]

            # Update notes if provided
            if "notes" in request_data:
                update_data["notes"] = request_data["notes"]

            # Update the request
            update_result = await inventory_requests_collection.update_one(
                {"_id": request_obj_id},
                {"$set": update_data}
            )

            if update_result.matched_count == 0:
                return None

            # Get the updated request
            updated_request, _ = await IdHandler.find_document_by_id(
                inventory_requests_collection,
                request_id,
                not_found_msg="Failed to retrieve updated inventory request"
            )

            # Format and return
            return IdHandler.format_object_ids(updated_request)
        except ValueError as e:
            print(f"Validation error updating inventory request: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            print(f"Error updating inventory request: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error updating inventory request: {str(e)}"
            )

    @staticmethod
    async def fulfill_inventory_request(request_id: str, fulfilled_by: str, notes: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Mark an inventory request as fulfilled"""
        try:
            # Find request using IdHandler
            request, request_obj_id = await IdHandler.find_document_by_id(
                inventory_requests_collection,
                request_id,
                not_found_msg=f"Inventory request with ID {request_id} not found"
            )

            if not request:
                return None

            # Check if request is in pending status
            if request["status"] != InventoryRequestStatus.PENDING:
                raise ValueError(f"Cannot fulfill inventory request in {request['status']} status")

            # Prepare update data
            update_data = {
                "status": InventoryRequestStatus.FULFILLED,
                "fulfilled_at": datetime.utcnow(),
                "fulfilled_by": fulfilled_by,
                "updated_at": datetime.utcnow()
            }

            # Add notes if provided
            if notes:
                update_data["notes"] = notes

            # Update the request
            update_result = await inventory_requests_collection.update_one(
                {"_id": request_obj_id},
                {"$set": update_data}
            )

            if update_result.matched_count == 0:
                return None

            # Get the updated request
            updated_request, _ = await IdHandler.find_document_by_id(
                inventory_requests_collection,
                request_id,
                not_found_msg="Failed to retrieve updated inventory request"
            )

            # Format and return
            return IdHandler.format_object_ids(updated_request)
        except ValueError as e:
            print(f"Validation error fulfilling inventory request: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            print(f"Error fulfilling inventory request: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error fulfilling inventory request: {str(e)}"
            )

    @staticmethod
    async def cancel_inventory_request(request_id: str, reason: str) -> Optional[Dict[str, Any]]:
        """Cancel an inventory request"""
        try:
            # Find request using IdHandler
            request, request_obj_id = await IdHandler.find_document_by_id(
                inventory_requests_collection,
                request_id,
                not_found_msg=f"Inventory request with ID {request_id} not found"
            )

            if not request:
                return None

            # Check if request is in pending status
            if request["status"] != InventoryRequestStatus.PENDING:
                raise ValueError(f"Cannot cancel inventory request in {request['status']} status")

            # Prepare update data
            update_data = {
                "status": InventoryRequestStatus.CANCELLED,
                "notes": reason,
                "updated_at": datetime.utcnow()
            }

            # Update the request
            update_result = await inventory_requests_collection.update_one(
                {"_id": request_obj_id},
                {"$set": update_data}
            )

            if update_result.matched_count == 0:
                return None

            # Get the updated request
            updated_request, _ = await IdHandler.find_document_by_id(
                inventory_requests_collection,
                request_id,
                not_found_msg="Failed to retrieve updated inventory request"
            )

            # Format and return
            return IdHandler.format_object_ids(updated_request)
        except ValueError as e:
            print(f"Validation error cancelling inventory request: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            print(f"Error cancelling inventory request: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error cancelling inventory request: {str(e)}"
            )

    @staticmethod
    async def get_employee_inventory_requests(employee_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get inventory requests for a specific employee"""
        return await InventoryRequestService.get_inventory_requests(
            employee_id=employee_id,
            status=status
        )

    @staticmethod
    async def get_store_inventory_requests(store_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get inventory requests for a specific store"""
        return await InventoryRequestService.get_inventory_requests(
            store_id=store_id,
            status=status
        )
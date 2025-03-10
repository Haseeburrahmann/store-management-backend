# app/services/store.py
from typing import List, Optional, Dict, Any
from bson import ObjectId
from datetime import datetime
from fastapi import HTTPException, status

from app.core.db import get_database, get_stores_collection
from app.models.store import StoreModel
from app.services.user import get_user_by_id
from app.utils.formatting import format_object_ids, ensure_object_id
from app.utils.id_handler import IdHandler

# Get database and collections
db = get_database()
stores_collection = get_stores_collection()


class StoreService:
    @staticmethod
    async def get_stores(
            skip: int = 0,
            limit: int = 100,
            name: Optional[str] = None,
            city: Optional[str] = None,
            manager_id: Optional[str] = None
    ) -> List[dict]:
        """
        Get all stores with optional filtering
        """
        try:
            query = {}

            if name:
                query["name"] = {"$regex": name, "$options": "i"}

            if city:
                query["city"] = {"$regex": city, "$options": "i"}

            if manager_id:
                # Try to convert to ObjectId if valid
                manager_obj_id = ensure_object_id(manager_id)
                if manager_obj_id:
                    query["manager_id"] = manager_obj_id
                else:
                    query["manager_id"] = manager_id

            stores = await stores_collection.find(query).skip(skip).limit(limit).to_list(length=limit)

            # Add manager names if available
            result = []
            for store in stores:
                store_with_manager = dict(store)
                if store.get("manager_id"):
                    manager_obj_id = ensure_object_id(store["manager_id"])
                    if manager_obj_id:
                        manager = await get_user_by_id(manager_obj_id)
                        if manager:
                            store_with_manager["manager_name"] = manager.get("full_name")
                result.append(store_with_manager)

            return format_object_ids(result)
        except Exception as e:
            print(f"Error getting stores: {str(e)}")
            return []

    @staticmethod
    async def get_stores_by_manager(manager_id: str) -> List[dict]:
        """
        Get stores managed by a specific user
        """
        try:
            # Try with ObjectId
            manager_obj_id = ensure_object_id(manager_id)

            if manager_obj_id:
                stores = await stores_collection.find({"manager_id": manager_obj_id}).to_list(length=100)
            else:
                # Try with string ID
                stores = await stores_collection.find({"manager_id": manager_id}).to_list(length=100)

                # Try string comparison if needed
                if not stores:
                    all_stores = await stores_collection.find().to_list(length=100)
                    stores = [
                        store for store in all_stores
                        if str(store.get("manager_id")) == manager_id
                    ]

            return format_object_ids(stores)
        except Exception as e:
            print(f"Error getting stores by manager: {str(e)}")
            return []

    @staticmethod
    async def get_store(store_id: str) -> Optional[dict]:
        """
        Get store by ID using the centralized ID handler
        """
        try:
            print(f"Looking up store with ID: {store_id}")

            # Use centralized method for consistent lookup
            store, _ = await IdHandler.find_document_by_id(
                stores_collection,
                store_id,
                not_found_msg=f"Store with ID {store_id} not found"
            )

            if not store:
                print(f"Store not found with ID: {store_id}")
                return None

            # Get manager info if available
            if store and store.get("manager_id"):
                print(f"Getting manager info for manager_id: {store.get('manager_id')}")
                from app.services.user import get_user_by_id
                manager = await get_user_by_id(store.get("manager_id"))
                if manager:
                    print(f"Found manager: {manager.get('full_name')}")
                    store_with_manager = dict(store)
                    store_with_manager["manager_name"] = manager.get("full_name")
                    return IdHandler.format_object_ids(store_with_manager)
                else:
                    print(f"Manager not found for ID: {store.get('manager_id')}")

            # Return store without manager info if no manager found
            print(f"Returning store without manager info: {store.get('name')}")
            return IdHandler.format_object_ids(store)
        except Exception as e:
            print(f"Error in get_store: {str(e)}")
            # Return None instead of raising an exception to let the router handle the 404
            return None

    @staticmethod
    async def create_store(store_data: dict) -> dict:
        """
        Create new store with strict manager validation
        """
        try:
            # Handle manager_id if provided
            if "manager_id" in store_data and store_data["manager_id"]:
                manager_id = store_data["manager_id"]
                print(f"Validating manager ID: {manager_id}")

                # Use the user service to find the manager
                from app.services.user import get_user_by_id
                manager = await get_user_by_id(manager_id)

                if not manager:
                    print(f"Manager not found with ID: {manager_id}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Manager with ID {manager_id} not found"
                    )

                # Validate manager has the Manager role
                manager_role_id = manager.get("role_id")
                if manager_role_id:
                    from app.services.role import get_role_by_id
                    role = await get_role_by_id(manager_role_id)

                    if not role:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Role not found for user {manager.get('email')}"
                        )

                    if role.get("name") != "Manager" and role.get("name") != "Admin":
                        print(f"User has role: {role.get('name')}, not Manager or Admin")
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"User {manager.get('email')} does not have Manager or Admin role"
                        )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"User {manager.get('email')} does not have a role assigned"
                    )

                # Use string format of ID consistently
                store_data["manager_id"] = str(manager.get('_id'))
                print(f"Validated manager ID: {store_data['manager_id']}")

            # Create store model - this will fail if the data doesn't match the model
            try:
                store_model = StoreModel(**store_data)
            except Exception as e:
                # Catch validation errors from the model
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid store data: {str(e)}"
                )

            # Insert into database
            result = await stores_collection.insert_one(store_model.model_dump(by_alias=True))
            print(f"Store created with ID: {result.inserted_id}")

            # Get the created store
            created_store = await stores_collection.find_one({"_id": result.inserted_id})
            if not created_store:
                print(f"Error: Store was inserted but could not be retrieved. ID: {result.inserted_id}")
                return {
                    "_id": str(result.inserted_id),
                    **store_data,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }

            return format_object_ids(created_store)
        except Exception as e:
            print(f"Error creating store: {str(e)}")
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating store: {str(e)}"
            )

    @staticmethod
    async def update_store(store_id: str, store_data: dict) -> Optional[dict]:
        """
        Update existing store with enhanced error handling
        """
        try:
            print(f"Updating store with ID: {store_id}")
            print(f"Update data: {store_data}")

            # Update timestamp directly
            store_data["updated_at"] = datetime.utcnow()

            # Try with ObjectId
            store_obj_id = ensure_object_id(store_id)

            # Get the existing store first to validate it exists
            existing_store = None

            if store_obj_id:
                print(f"Looking up store with ObjectId: {store_obj_id}")
                existing_store = await stores_collection.find_one({"_id": store_obj_id})
                if existing_store:
                    print(f"Found store with ObjectId: {existing_store.get('name')}")

            # Try string lookup if ObjectId lookup failed
            if not existing_store:
                print(f"Looking up store with string ID: {store_id}")
                existing_store = await stores_collection.find_one({"_id": store_id})
                if existing_store:
                    print(f"Found store with string ID: {existing_store.get('name')}")

            # Try string comparison as last resort
            if not existing_store:
                print(f"Trying string comparison for store ID: {store_id}")
                all_stores = await stores_collection.find().to_list(length=100)
                for s in all_stores:
                    if str(s.get('_id')) == store_id:
                        existing_store = s
                        print(f"Found store via string comparison: {existing_store.get('name')}")
                        break

            if not existing_store:
                print(f"Store not found with ID: {store_id}")
                return None

            # If we're here, we found the store and can update it

            # Handle manager_id validation for existing stores
            # Skip manager validation if not changing manager
            if "manager_id" in store_data:
                manager_id = store_data["manager_id"]

                if manager_id:
                    # Validate manager exists
                    from app.services.user import get_user_by_id
                    manager = await get_user_by_id(manager_id)

                    if not manager:
                        print(f"Manager not found with ID: {manager_id}")
                        raise Exception(f"Manager with ID {manager_id} not found")

                    # Validate manager has correct role
                    if manager.get("role_id"):
                        from app.services.role import get_role_by_id
                        role = await get_role_by_id(manager.get("role_id"))

                        if role and role.get("name") != "Manager" and role.get("name") != "Admin":
                            print(f"User has role: {role.get('name')}, not Manager or Admin")
                            raise Exception(f"User {manager.get('email')} does not have Manager or Admin role")

                    # Use string format of manager ID consistently
                    store_data["manager_id"] = str(manager.get('_id'))

            # Get the correct ID to use for update
            update_id = existing_store.get('_id')
            print(f"Using ID for update: {update_id}, type: {type(update_id)}")

            # Update the store
            update_result = await stores_collection.update_one(
                {"_id": update_id},
                {"$set": store_data}
            )

            print(f"Update result: matched={update_result.matched_count}, modified={update_result.modified_count}")

            if update_result.matched_count == 0:
                print(f"No store matched for update")
                return None

            # Get the updated store
            updated_store = await stores_collection.find_one({"_id": update_id})
            if not updated_store:
                print(f"Unable to retrieve updated store")
                return None

            return format_object_ids(updated_store)
        except Exception as e:
            print(f"Error updating store: {str(e)}")
            return None

    @staticmethod
    async def delete_store(store_id: str) -> bool:
        """
        Delete store
        """
        try:
            # Try with ObjectId
            store_obj_id = ensure_object_id(store_id)
            if store_obj_id:
                # Check if store exists first
                store = await stores_collection.find_one({"_id": store_obj_id})
                if store:
                    # Delete the store
                    result = await stores_collection.delete_one({"_id": store_obj_id})
                    return result.deleted_count > 0

            # Try string comparison as fallback
            all_stores = await stores_collection.find().to_list(length=100)
            for store in all_stores:
                if str(store.get('_id')) == store_id:
                    # Delete using the original ObjectId
                    result = await stores_collection.delete_one({"_id": store.get('_id')})
                    return result.deleted_count > 0

            return False
        except Exception as e:
            print(f"Error deleting store: {str(e)}")
            return False

    @staticmethod
    async def assign_manager(store_id: str, manager_id: str) -> Optional[dict]:
        """
        Assign manager to store
        """
        try:
            # Validate store exists
            store_obj_id = ensure_object_id(store_id)
            if store_obj_id:
                store = await stores_collection.find_one({"_id": store_obj_id})
            else:
                # Try string comparison
                all_stores = await stores_collection.find().to_list(length=100)
                store = None
                for s in all_stores:
                    if str(s.get('_id')) == store_id:
                        store = s
                        store_obj_id = s.get('_id')
                        break

            if not store:
                print(f"Store with ID {store_id} not found")
                return None

            # Validate manager exists
            manager_obj_id = ensure_object_id(manager_id)
            if manager_obj_id:
                manager = await db.users.find_one({"_id": manager_obj_id})
            else:
                # Try string comparison
                all_users = await db.users.find().to_list(length=100)
                manager = None
                for user in all_users:
                    if str(user.get('_id')) == manager_id:
                        manager = user
                        manager_obj_id = user.get('_id')
                        break

            if not manager:
                print(f"Manager with ID {manager_id} not found")
                return None

            # Update the store with manager ID (keep as string for consistency)
            update_result = await stores_collection.update_one(
                {"_id": store_obj_id},
                {"$set": {
                    "manager_id": str(manager_obj_id),
                    "updated_at": datetime.utcnow()
                }}
            )

            if update_result.modified_count == 0:
                print("Store not updated")
                return None

            # Get the updated store
            updated_store = await stores_collection.find_one({"_id": store_obj_id})
            if not updated_store:
                print("Updated store not found")
                return None

            # Add manager name to result
            result = dict(updated_store)
            result["manager_name"] = manager.get("full_name")

            return format_object_ids(result)
        except Exception as e:
            print(f"Error in assign_manager: {str(e)}")
            return None

    @staticmethod
    async def get_active_stores() -> List[dict]:
        """
        Get all active stores
        """
        try:
            stores = await stores_collection.find({"is_active": True}).to_list(length=100)
            return format_object_ids(stores)
        except Exception as e:
            print(f"Error getting active stores: {str(e)}")
            return []

    @staticmethod
    async def check_store_exists(store_id: str) -> bool:
        """
        Check if a store exists
        """
        try:
            store = await StoreService.get_store(store_id)
            return store is not None
        except Exception as e:
            print(f"Error checking store existence: {str(e)}")
            return False
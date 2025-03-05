# app/services/store.py
from typing import List, Optional
from bson import ObjectId
from app.core.db import get_database
from app.models.store import StoreModel
from app.services.user import get_user_by_id
from app.utils.formatting import format_object_ids
from datetime import datetime

# Get database connection once
db = get_database()


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
        query = {}

        if name:
            query["name"] = {"$regex": name, "$options": "i"}

        if city:
            query["city"] = {"$regex": city, "$options": "i"}

        if manager_id:
            query["manager_id"] = manager_id

        stores = await db.stores.find(query).skip(skip).limit(limit).to_list(length=limit)

        # Add manager names if available
        result = []
        for store in stores:
            store_with_manager = dict(store)
            if store.get("manager_id"):
                manager = await get_user_by_id(ObjectId(store["manager_id"]))
                if manager:
                    store_with_manager["manager_name"] = manager.get("full_name")
            result.append(store_with_manager)

        return format_object_ids(result)

    @staticmethod
    async def get_stores_by_manager(manager_id: str) -> List[dict]:
        """
        Get stores managed by a specific user
        """
        stores = await db.stores.find({"manager_id": manager_id}).to_list(length=100)
        return format_object_ids(stores)

    @staticmethod
    async def get_store(store_id: str) -> Optional[dict]:
        """
        Get store by ID with manager info
        """
        try:
            print(f"Attempting to find store with ID: {store_id}")

            # List all stores for debugging
            all_stores = await db.stores.find().to_list(length=100)
            all_ids = [str(store.get('_id')) for store in all_stores]
            print(f"All store IDs in database: {all_ids}")

            # Try with ObjectId
            object_id = None
            try:
                object_id = ObjectId(store_id)
                store = await db.stores.find_one({"_id": object_id})
                print(f"Store lookup with ObjectId {object_id} result: {store is not None}")
            except Exception as e:
                print(f"Error looking up with ObjectId: {str(e)}")
                store = None

            # If not found with ObjectId, try string comparison
            if not store:
                print("Trying string comparison...")
                for db_store in all_stores:
                    db_id = str(db_store.get('_id'))
                    print(f"Comparing {db_id} with {store_id}: {db_id == store_id}")
                    if db_id == store_id:
                        store = db_store
                        print(f"Found store by string comparison: {store.get('name')}")
                        break

            if not store:
                print(f"Store not found with ID: {store_id}")
                return None

            # Get manager info if available
            if store and store.get("manager_id"):
                manager = await get_user_by_id(ObjectId(store["manager_id"]))
                if manager:
                    store_with_manager = dict(store)
                    store_with_manager["manager_name"] = manager.get("full_name")
                    return format_object_ids(store_with_manager)

            return format_object_ids(store)
        except Exception as e:
            print(f"Error in get_store: {str(e)}")
            return None

    @staticmethod
    async def create_store(store_data: dict) -> dict:
        """
        Create new store
        """
        try:
            # Create store model
            store_model = StoreModel(**store_data)

            # Insert into database
            result = await db.stores.insert_one(store_model.model_dump(by_alias=True))

            # Get the created store
            created_store = await db.stores.find_one({"_id": result.inserted_id})
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
            raise

    @staticmethod
    async def update_store(store_id: str, store_data: dict) -> Optional[dict]:
        """
        Update existing store
        """
        try:
            print(f"Attempting to update store with ID: {store_id}")

            # List all stores for debugging
            all_stores = await db.stores.find().to_list(length=100)
            all_ids = [str(store.get('_id')) for store in all_stores]
            print(f"All store IDs in database: {all_ids}")

            # Update timestamp directly
            store_data["updated_at"] = datetime.utcnow()

            # Try with ObjectId
            store_obj_id = None
            try:
                store_obj_id = ObjectId(store_id)
                # Check if store exists first
                store = await db.stores.find_one({"_id": store_obj_id})
                if store:
                    print(f"Found store with ObjectId: {store.get('name')}")
                else:
                    print(f"Store not found with ObjectId: {store_obj_id}")
                    store = None
            except Exception as e:
                print(f"Error looking up with ObjectId: {str(e)}")
                store = None

            # If not found with ObjectId, try string comparison
            if not store:
                print("Trying string comparison...")
                for db_store in all_stores:
                    db_id = str(db_store.get('_id'))
                    if db_id == store_id:
                        store = db_store
                        store_obj_id = db_store.get('_id')
                        print(f"Found store by string comparison: {store.get('name')}")
                        break

            if not store:
                print(f"Store not found with ID: {store_id}")
                return None

            # Update the store using the found ObjectId
            print(f"Updating store with ID: {store_obj_id}")
            await db.stores.update_one(
                {"_id": store_obj_id},
                {"$set": store_data}
            )

            # Get the updated store
            updated_store = await db.stores.find_one({"_id": store_obj_id})
            if not updated_store:
                print(f"Failed to retrieve updated store")
                return None

            print(f"Successfully updated store: {updated_store.get('name')}")
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
            print(f"Attempting to delete store with ID: {store_id}")

            # List all stores for debugging
            all_stores = await db.stores.find().to_list(length=100)
            all_ids = [str(store.get('_id')) for store in all_stores]
            print(f"All store IDs in database: {all_ids}")

            # Try to convert the string ID to ObjectId
            object_id = None
            try:
                object_id = ObjectId(store_id)
                print(f"Converted to ObjectId: {object_id}")
            except Exception as e:
                print(f"Error converting to ObjectId: {str(e)}")
                return False

            # Check if store exists first
            store = await db.stores.find_one({"_id": object_id})
            if not store:
                print(f"Store not found with ObjectId {object_id}")

                # Try string comparison as fallback
                found_store = None
                for db_store in all_stores:
                    if str(db_store.get('_id')) == store_id:
                        found_store = db_store
                        print(f"Found store by string comparison: {found_store.get('name')}")
                        break

                if found_store:
                    # Delete using the original ObjectId
                    result = await db.stores.delete_one({"_id": found_store.get('_id')})
                    print(f"Delete result after string comparison: {result.deleted_count}")
                    return result.deleted_count > 0
                else:
                    print(f"Store not found with ID {store_id} after exhaustive search")
                    return False

            # Delete the store
            result = await db.stores.delete_one({"_id": object_id})
            print(f"Delete result: {result.deleted_count}")
            return result.deleted_count > 0
        except Exception as e:
            print(f"Error deleting store: {str(e)}")
            return False

    @staticmethod
    async def assign_manager(store_id: str, manager_id: str) -> Optional[dict]:
        """
        Assign manager to store
        """
        try:
            print(f"Attempting to assign manager {manager_id} to store {store_id}")

            # List all users for debugging
            all_users = await db.users.find().to_list(length=100)
            all_user_ids = [str(user.get('_id')) for user in all_users]
            print(f"All user IDs in database: {all_user_ids}")

            # List all stores for debugging
            all_stores = await db.stores.find().to_list(length=100)
            all_store_ids = [str(store.get('_id')) for store in all_stores]
            print(f"All store IDs in database: {all_store_ids}")

            # Find the manager directly with string comparison
            manager = None
            for user in all_users:
                if str(user.get('_id')) == manager_id:
                    manager = user
                    print(f"Found manager by string comparison: {user.get('full_name')}")
                    break

            if not manager:
                print(f"Manager with ID {manager_id} not found")
                return None

            # Find the store directly with string comparison
            store = None
            for db_store in all_stores:
                if str(db_store.get('_id')) == store_id:
                    store = db_store
                    print(f"Found store by string comparison: {store.get('name')}")
                    break

            if not store:
                print(f"Store with ID {store_id} not found")
                return None

            # Update the store directly
            store_obj_id = store.get('_id')
            update_result = await db.stores.update_one(
                {"_id": store_obj_id},
                {"$set": {
                    "manager_id": manager_id,
                    "updated_at": datetime.utcnow()
                }}
            )

            print(f"Update result: {update_result.modified_count} documents modified")

            if update_result.modified_count == 0:
                print("Store not updated")
                return None

            # Get the updated store
            updated_store = await db.stores.find_one({"_id": store_obj_id})
            if not updated_store:
                print("Updated store not found")
                return None

            # Add manager name to result
            result = dict(updated_store)
            result["manager_name"] = manager.get("full_name")

            print(f"Successfully assigned manager {manager.get('full_name')} to store {updated_store.get('name')}")
            return format_object_ids(result)
        except Exception as e:
            print(f"Error in assign_manager: {str(e)}")
            return None
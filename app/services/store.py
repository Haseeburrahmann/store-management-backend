# app/services/store.py
from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from fastapi import HTTPException

from app.core.db import get_database
from app.models.store import Store, StoreOut
from app.schemas.store import StoreCreate, StoreUpdate


class StoreService:
    @staticmethod
    async def get_stores(skip: int = 0, limit: int = 100, name: Optional[str] = None,
                         city: Optional[str] = None, manager_id: Optional[str] = None) -> List[StoreOut]:
        db = get_database()  # No await needed
        query = {}

        if name:
            query["name"] = {"$regex": name, "$options": "i"}
        if city:
            query["city"] = {"$regex": city, "$options": "i"}
        if manager_id:
            query["manager_id"] = manager_id

        stores_cursor = db.stores.find(query).skip(skip).limit(limit)
        stores = await stores_cursor.to_list(length=limit)

        # Get manager names
        store_list = []
        for store in stores:
            store_with_manager = dict(store)
            if store.get("manager_id"):
                manager = await db.users.find_one({"_id": ObjectId(store["manager_id"])})
                if manager:
                    store_with_manager["manager_name"] = manager.get("full_name", "Unknown")
            store_list.append(StoreOut(**store_with_manager))

        return store_list

    @staticmethod
    async def get_store(store_id: str) -> StoreOut:
        db = get_database()

        try:
            # First try using ObjectId conversion
            store = await db.stores.find_one({"_id": ObjectId(store_id)})

            if not store:
                # If not found, try alternative approaches
                print(f"Store not found with ObjectId, trying alternative approaches")

                # Try querying all stores to find a match
                all_stores = await db.stores.find().to_list(length=100)
                for s in all_stores:
                    if str(s.get('_id')) == store_id:
                        store = s
                        break

                if not store:
                    raise HTTPException(status_code=404, detail="Store not found")

            store_with_manager = dict(store)
            if store.get("manager_id"):
                manager = await db.users.find_one({"_id": ObjectId(store["manager_id"])})
                if manager:
                    store_with_manager["manager_name"] = manager.get("full_name", "Unknown")

            return StoreOut(**store_with_manager)

        except Exception as e:
            print(f"Error finding store: {str(e)}")
            raise HTTPException(status_code=404, detail="Store not found")

    @staticmethod
    async def create_store(store_data: dict) -> StoreOut:
        db = get_database()  # No await needed
        store = Store(**store_data)

        result = await db.stores.insert_one(store.model_dump(by_alias=True))
        created_store = await db.stores.find_one({"_id": result.inserted_id})

        return StoreOut(**created_store)

    @staticmethod
    async def update_store(store_id: str, store_data: dict) -> StoreOut:
        db = get_database()

        try:
            # First try using ObjectId conversion
            store = await db.stores.find_one({"_id": ObjectId(store_id)})
            store_id_obj = ObjectId(store_id)

            if not store:
                # If not found, try alternative approaches
                print(f"Store not found with ObjectId, trying alternative approaches")

                # Try querying all stores to find a match
                all_stores = await db.stores.find().to_list(length=100)
                for s in all_stores:
                    if str(s.get('_id')) == store_id:
                        store = s
                        store_id_obj = s.get('_id')
                        break

                if not store:
                    raise HTTPException(status_code=404, detail="Store not found")

            update_data = {k: v for k, v in store_data.items() if v is not None}

            if "manager_id" in update_data and update_data["manager_id"]:
                # Validate manager exists and has manager role
                manager = await db.users.find_one({"_id": ObjectId(update_data["manager_id"])})
                if not manager:
                    raise HTTPException(status_code=404, detail="Manager not found")

                # Get manager's role
                role = await db.roles.find_one({"_id": ObjectId(manager.get("role_id"))})
                if not role or "PermissionArea.STORES:PermissionAction.READ" not in role.get("permissions", []):
                    raise HTTPException(status_code=400, detail="Selected user does not have manager permissions")

                update_data["manager_id"] = str(ObjectId(update_data["manager_id"]))

            update_data["updated_at"] = datetime.utcnow()

            await db.stores.update_one(
                {"_id": store_id_obj},
                {"$set": update_data}
            )

            updated_store = await db.stores.find_one({"_id": store_id_obj})
            return StoreOut(**updated_store)

        except Exception as e:
            print(f"Error updating store: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error updating store: {str(e)}")

    @staticmethod
    async def delete_store(store_id: str) -> bool:
        db = get_database()

        try:
            # Try direct deletion without checking first
            print(f"Attempting to delete store with ID: {store_id}")
            result = await db.stores.delete_one({"_id": ObjectId(store_id)})

            if result.deleted_count == 0:
                # If deletion failed, check if store exists with a different ID format
                print(f"No store deleted with ObjectId format, trying alternative approaches")

                # Try querying all stores to find a match
                all_stores = await db.stores.find().to_list(length=100)
                for store in all_stores:
                    print(f"Found store in DB: {store}")
                    if str(store.get('_id')) == store_id:
                        print(f"Found matching store, trying to delete again")
                        result = await db.stores.delete_one({"_id": store.get('_id')})
                        return result.deleted_count > 0

                # If we get here, truly no matching store was found
                print(f"Store not found with any ID format: {store_id}")
                raise HTTPException(status_code=404, detail="Store not found")

            print(f"Successfully deleted store: {result.deleted_count} document(s) deleted")
            return result.deleted_count > 0

        except Exception as e:
            print(f"Error deleting store: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error deleting store: {str(e)}")

    @staticmethod
    async def assign_manager(store_id: str, manager_id: str) -> StoreOut:
        db = get_database()
        store = await db.stores.find_one({"_id": ObjectId(store_id)})

        if not store:
            raise HTTPException(status_code=404, detail="Store not found")

        # Validate manager exists
        manager = await db.users.find_one({"_id": ObjectId(manager_id)})
        if not manager:
            raise HTTPException(status_code=404, detail="Manager not found")

        # Update store with new manager
        await db.stores.update_one(
            {"_id": ObjectId(store_id)},
            {
                "$set": {
                    "manager_id": str(manager_id),  # Store as string, not ObjectId string
                    "updated_at": datetime.utcnow()
                }
            }
        )

        # Get the updated store
        updated_store = await db.stores.find_one({"_id": ObjectId(store_id)})

        # Add manager name to the response
        result = dict(updated_store)
        result["manager_name"] = manager.get("full_name", "Unknown")

        print(f"Updated store: {result}")
        return StoreOut(**result)

    @staticmethod
    async def get_stores_by_manager(manager_id: str) -> List[StoreOut]:
        db = get_database()  # No await needed
        stores_cursor = db.stores.find({"manager_id": manager_id})
        stores = await stores_cursor.to_list(length=100)

        store_list = []
        for store in stores:
            store_with_manager = dict(store)
            manager = await db.users.find_one({"_id": ObjectId(manager_id)})
            if manager:
                store_with_manager["manager_name"] = manager.get("full_name", "Unknown")
            store_list.append(StoreOut(**store_with_manager))

        return store_list
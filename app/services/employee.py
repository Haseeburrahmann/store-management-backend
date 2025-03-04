# app/services/employee.py
from datetime import datetime
from typing import List, Optional, Dict, Any
from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.schemas.employee import EmployeeCreate, EmployeeUpdate
from app.services.user import create_user, update_user, delete_user, get_user_by_id


async def create_employee(db: AsyncIOMotorDatabase, employee_data: EmployeeCreate) -> Dict[str, Any]:
    # First create the user
    user_data = {k: v for k, v in employee_data.dict().items() if
                 k in ["email", "password", "full_name", "phone_number", "role_id"]}
    user = await create_user(user_data)

    # Then create the employee with user_id
    employee_dict = employee_data.dict(exclude={"password"})

    # Access the user ID based on the returned user object
    user_id = None
    if hasattr(user, "id"):
        user_id = user.id
    elif hasattr(user, "_id"):
        user_id = user._id
    else:
        user_id = user["_id"] if isinstance(user, dict) else None

    employee_dict["user_id"] = ObjectId(user_id)

    # Convert store_id to ObjectId if it exists
    if employee_dict.get("store_id"):
        employee_dict["store_id"] = ObjectId(employee_dict["store_id"])

    # Add required timestamp fields
    current_time = datetime.now()
    employee_dict["created_at"] = current_time
    employee_dict["updated_at"] = current_time

    employee_collection = db.employees
    result = await employee_collection.insert_one(employee_dict)

    created_employee = await employee_collection.find_one({"_id": result.inserted_id})

    if not created_employee:
        # Rollback user creation if employee creation fails
        await delete_user(str(user_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create employee"
        )

    # Format response
    created_employee["_id"] = str(created_employee["_id"])

    # Convert ObjectId fields to strings
    if created_employee.get("store_id"):
        created_employee["store_id"] = str(created_employee["store_id"])
    if created_employee.get("user_id"):
        created_employee["user_id"] = str(created_employee["user_id"])

    # Add missing fields required by the response model
    created_employee["password"] = "**********"  # Add a placeholder for password

    return created_employee


async def get_employees(
        db: AsyncIOMotorDatabase,
        skip: int = 0,
        limit: int = 100,
        store_id: Optional[str] = None,
        search: Optional[str] = None,
        status: Optional[str] = None
) -> List[Dict[str, Any]]:
    employee_collection = db.employees
    store_collection = db.stores

    # Build the query
    query = {}
    if store_id:
        query["store_id"] = ObjectId(store_id)
    if search:
        query["$or"] = [
            {"full_name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"position": {"$regex": search, "$options": "i"}}
        ]
    if status:
        query["employment_status"] = status

    # Get employees
    cursor = employee_collection.find(query).skip(skip).limit(limit)
    employees = await cursor.to_list(length=limit)

    # Add store information to employees
    result = []
    for employee in employees:
        # Convert ALL ObjectId fields to strings
        employee["_id"] = str(employee["_id"])

        if employee.get("store_id"):
            store_id_obj = employee["store_id"]
            employee["store_id"] = str(store_id_obj)

            # Get store name
            store = await store_collection.find_one({"_id": store_id_obj})
            if store:
                employee["store_name"] = store["name"]

        # Convert user_id to string if present
        if employee.get("user_id"):
            employee["user_id"] = str(employee["user_id"])

        # Add password placeholder if missing
        if "password" not in employee:
            employee["password"] = "**********"

        result.append(employee)

    return result


async def get_employee(db: AsyncIOMotorDatabase, employee_id: str) -> Dict[str, Any]:
    employee_collection = db.employees
    store_collection = db.stores

    employee = await employee_collection.find_one({"_id": ObjectId(employee_id)})

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with ID {employee_id} not found"
        )

    # Convert ObjectId to string
    employee["_id"] = str(employee["_id"])

    # Convert user_id to string if present
    if employee.get("user_id"):
        employee["user_id"] = str(employee["user_id"])

    # Add store information if applicable
    if employee.get("store_id"):
        store_id_obj = employee["store_id"]
        employee["store_id"] = str(store_id_obj)

        # Get store name
        store = await store_collection.find_one({"_id": store_id_obj})
        if store:
            employee["store_name"] = store["name"]

    # Add password placeholder if missing
    if "password" not in employee:
        employee["password"] = "**********"

    return employee


async def update_employee(db: AsyncIOMotorDatabase, employee_id: str, employee_data: EmployeeUpdate) -> Dict[str, Any]:
    employee_collection = db.employees

    # Get existing employee
    existing_employee = await employee_collection.find_one({"_id": ObjectId(employee_id)})
    if not existing_employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with ID {employee_id} not found"
        )

    # Update user data if applicable
    user_data = {k: v for k, v in employee_data.dict(exclude_unset=True).items()
                 if k in ["email", "password", "full_name", "phone_number", "role_id"]}

    if user_data and existing_employee.get("user_id"):
        user_id = str(existing_employee["user_id"])
        await update_user(user_id, user_data)

    # Update employee data
    employee_update_data = employee_data.dict(exclude_unset=True)

    # Convert store_id to ObjectId if it exists and is valid
    if "store_id" in employee_update_data and employee_update_data["store_id"]:
        if ObjectId.is_valid(employee_update_data["store_id"]):
            employee_update_data["store_id"] = ObjectId(employee_update_data["store_id"])
        else:
            # Either remove the field or raise an exception
            del employee_update_data["store_id"]

    # Update the updated_at timestamp
    employee_update_data["updated_at"] = datetime.now()

    if employee_update_data:
        await employee_collection.update_one(
            {"_id": ObjectId(employee_id)},
            {"$set": employee_update_data}
        )

    # Get updated employee
    updated_employee = await employee_collection.find_one({"_id": ObjectId(employee_id)})

    # Convert ObjectId to string
    updated_employee["_id"] = str(updated_employee["_id"])
    if updated_employee.get("store_id"):
        updated_employee["store_id"] = str(updated_employee["store_id"])
    if updated_employee.get("user_id"):
        updated_employee["user_id"] = str(updated_employee["user_id"])

    # Add password placeholder if missing
    if "password" not in updated_employee:
        updated_employee["password"] = "**********"

    return updated_employee


async def delete_employee(db: AsyncIOMotorDatabase, employee_id: str) -> Dict[str, str]:
    employee_collection = db.employees

    # Get existing employee
    existing_employee = await employee_collection.find_one({"_id": ObjectId(employee_id)})
    if not existing_employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with ID {employee_id} not found"
        )

    # Delete the employee
    await employee_collection.delete_one({"_id": ObjectId(employee_id)})

    # Delete associated user
    if existing_employee.get("user_id"):
        user_id = str(existing_employee["user_id"])
        await delete_user(user_id)

    return {"message": f"Employee with ID {employee_id} deleted successfully"}


async def assign_employee_to_store(db: AsyncIOMotorDatabase, employee_id: str, store_id: str) -> Dict[str, Any]:
    employee_collection = db.employees
    store_collection = db.stores

    # Verify employee exists
    employee = await employee_collection.find_one({"_id": ObjectId(employee_id)})
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with ID {employee_id} not found"
        )

    # Try to find the store
    store = await store_collection.find_one({"_id": ObjectId(store_id)})

    if not store:
        # Try with string ID as fallback
        store = await store_collection.find_one({"_id": store_id})

    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Store with ID {store_id} not found"
        )

    # Update employee store
    await employee_collection.update_one(
        {"_id": ObjectId(employee_id)},
        {"$set": {
            "store_id": ObjectId(store_id),
            "updated_at": datetime.now()
        }}
    )

    # Get updated employee
    updated_employee = await employee_collection.find_one({"_id": ObjectId(employee_id)})

    # Convert ALL ObjectId fields to strings
    result = {}
    for key, value in updated_employee.items():
        if isinstance(value, ObjectId):
            result[key] = str(value)
        else:
            result[key] = value

    # Add store name
    result["store_name"] = store.get("name", "Unknown Store")

    # Add password placeholder if missing
    if "password" not in result:
        result["password"] = "**********"

    return result


async def get_employees_by_store(db: AsyncIOMotorDatabase, store_id: str, skip: int = 0, limit: int = 100) -> List[
    Dict[str, Any]]:
    employee_collection = db.employees

    cursor = employee_collection.find({"store_id": ObjectId(store_id)}).skip(skip).limit(limit)
    employees = await cursor.to_list(length=limit)

    # Convert ObjectId to string and add password
    for employee in employees:
        employee["_id"] = str(employee["_id"])
        if employee.get("store_id"):
            employee["store_id"] = str(employee["store_id"])
        if employee.get("user_id"):
            employee["user_id"] = str(employee["user_id"])

        # Add password placeholder if missing
        if "password" not in employee:
            employee["password"] = "**********"

    return employees
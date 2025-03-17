from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import os

# Get MongoDB connection details directly from environment
MONGODB_URL = os.environ.get("MONGODB_URL", "mongodb://localhost:27017")
MONGODB_DB = os.environ.get("MONGODB_DB", "store_management")

# print(f"DB CONNECTION: Using {MONGODB_URL} for database {MONGODB_DB}")

# Create a MongoDB client
client = AsyncIOMotorClient(MONGODB_URL)

# Get database instance
database = client[MONGODB_DB]

def get_database() -> AsyncIOMotorDatabase:
    """
    Get database connection.
    Returns MongoDB database instance.
    """
    return database

# Collection accessor methods for consistent access
def get_users_collection():
    return database.users

def get_roles_collection():
    return database.roles

def get_stores_collection():
    return database.stores

def get_employees_collection():
    return database.employees

def get_schedules_collection():
    return database.schedules

def get_timesheets_collection():
    return database.timesheets

def get_payments_collection():
    return database.payments

def get_inventory_requests_collection():
    return database.inventory_requests
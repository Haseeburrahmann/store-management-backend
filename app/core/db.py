# app/core/db.py - Update to include schedule and timesheet collections
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings

# Create a MongoDB client
client = AsyncIOMotorClient(settings.database_url)

# Get database instance
database = client[settings.database_name]

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

def get_hours_collection():
    return database.hours

def get_schedules_collection():
    return database.schedules

def get_timesheets_collection():
    return database.timesheets

# Future collections can be added here
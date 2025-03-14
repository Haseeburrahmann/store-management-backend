# app/core/db.py - Modified for direct connection testing
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import os

# Hardcoded connection string for testing
connection_string = "mongodb+srv://mohdhaseeb42012:Haseeb%4012@storemanagementdb.7f7lp.mongodb.net/?retryWrites=true&w=majority&appName=StoreManagementDB"
database_name = "store_management"

# Log connection attempt
print(f"Connecting to MongoDB with: {connection_string}")

# Create a MongoDB client
client = AsyncIOMotorClient(connection_string)

# Get database instance
database = client[database_name]

# Rest of the file remains the same...

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

# Future collections can be added here

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

# Future collections can be added here
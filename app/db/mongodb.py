"""
MongoDB connection management.
"""
import os
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Dict, Any

class MongoDB:
    """
    MongoDB connection manager.
    Provides access to database and collections with connection management.
    """

    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None

    @classmethod
    def get_mongodb_url(cls) -> str:
        """
        Get MongoDB connection URL from environment variables.

        Returns:
            MongoDB connection URL
        """
        return os.environ.get("MONGODB_URL", "mongodb://localhost:27017")

    @classmethod
    def get_database_name(cls) -> str:
        """
        Get database name from environment variables.

        Returns:
            Database name
        """
        return os.environ.get("MONGODB_DB", "store_management")

    @classmethod
    def connect_to_mongodb(cls):
        """
        Connect to MongoDB if not already connected.
        This is synchronous to allow connection at import time.
        """
        if cls.client is None:
            mongodb_url = cls.get_mongodb_url()
            database_name = cls.get_database_name()

            print(f"Connecting to MongoDB at {mongodb_url} (database: {database_name})")

            cls.client = AsyncIOMotorClient(mongodb_url)
            cls.db = cls.client[database_name]

            print("Connected to MongoDB")

    @classmethod
    async def close_mongodb_connection(cls):
        """
        Close MongoDB connection if open.
        """
        if cls.client is not None:
            cls.client.close()
            cls.client = None
            cls.db = None
            print("Closed MongoDB connection")

    @classmethod
    def get_database(cls) -> AsyncIOMotorDatabase:
        """
        Get database instance.

        Returns:
            AsyncIOMotorDatabase instance
        """
        if cls.db is None:
            cls.connect_to_mongodb()
        return cls.db

    @classmethod
    def get_collection(cls, collection_name: str):
        """
        Get collection by name.

        Args:
            collection_name: Name of collection

        Returns:
            AsyncIOMotorCollection instance
        """
        if cls.db is None:
            cls.connect_to_mongodb()
        return cls.db[collection_name]

# Database instance - establish connection at import time
mongodb = MongoDB()
mongodb.connect_to_mongodb()

# Helper functions to get collections
def get_collection(name: str):
    return mongodb.get_collection(name)

def get_database():
    return mongodb.get_database()

# Collection getters for specific collections
def get_users_collection():
    return get_collection("users")

def get_roles_collection():
    return get_collection("roles")

def get_stores_collection():
    return get_collection("stores")

def get_employees_collection():
    return get_collection("employees")

def get_schedules_collection():
    return get_collection("schedules")

def get_timesheets_collection():
    return get_collection("timesheets")

def get_payments_collection():
    return get_collection("payments")
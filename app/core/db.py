# app/core/db.py
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

# Create a MongoDB client
client = AsyncIOMotorClient(settings.database_url)

# Get database instance
database = client[settings.database_name]

def get_database():
    """
    Get database connection
    Returns MongoDB database instance
    """
    return database
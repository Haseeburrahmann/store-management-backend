# app/core/db.py
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

# Create a MongoDB client
client = AsyncIOMotorClient(settings.database_url)

# Get database
def get_database():
    return client[settings.database_name]
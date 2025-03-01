from pymongo import MongoClient
from app.core.config import settings

client = MongoClient(settings.DATABASE_URL)
db = client[settings.DATABASE_NAME]

# Collections
users = db.users
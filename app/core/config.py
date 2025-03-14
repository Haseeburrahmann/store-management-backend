import os
from pydantic_settings import BaseSettings
from typing import Any, Dict


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Store Management System"
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "your-secret-key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # MongoDB settings - directly use os.environ
    database_url: str = os.environ.get("MONGODB_URL", "mongodb://localhost:27017")
    database_name: str = os.environ.get("MONGODB_DB", "store_management")

    class Config:
        env_file = ".env"
        extra = "ignore"
        env_file_encoding = "utf-8"
        env_ignore_empty = True

settings = Settings()

# Print debug info at startup
print(f"DEBUG - MONGODB_URL from environ: {os.environ.get('MONGODB_URL', 'not set')}")
print(f"DEBUG - MONGODB_URL from settings: {settings.database_url}")
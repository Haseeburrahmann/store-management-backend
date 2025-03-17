"""
Configuration settings for the application.
"""
import os
from pydantic_settings import BaseSettings
from typing import Any, Dict, List, Optional, Union


class Settings(BaseSettings):
    """
    Application settings with default values.
    Values can be overridden by environment variables.
    """
    # API settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Store Management System"

    # Security settings
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS settings
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:4200", "http://localhost:3000"]

    # MongoDB settings
    MONGODB_URL: str = os.environ.get("MONGODB_URL", "mongodb://localhost:27017")
    MONGODB_DB: str = os.environ.get("MONGODB_DB", "store_management")

    # Logging settings
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Create settings instance
settings = Settings()


# Print configuration summary at startup
def print_config_info():
    """Print configuration information at startup."""
    print(f"API Version: {settings.API_V1_STR}")
    print(f"Project Name: {settings.PROJECT_NAME}")
    print(f"MongoDB URL: {settings.MONGODB_URL}")
    print(f"MongoDB Database: {settings.MONGODB_DB}")
    print(f"CORS Origins: {settings.BACKEND_CORS_ORIGINS}")
    print(f"Log Level: {settings.LOG_LEVEL}")
import os
from pydantic_settings import BaseSettings
from typing import Any, Dict


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Store Management System"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # MongoDB settings - lowercase to match what your app seems to be using
    database_url: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    database_name: str = os.getenv("MONGODB_DB", "store_management")

    # Make sure environment variables are properly read
    model_config = {
        "env_file": ".env",
        "extra": "ignore"
    }


settings = Settings()
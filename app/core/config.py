# app/core/config.py
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Store Management API"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = "API for Store Management System"

    # MongoDB settings
    DATABASE_URL: str
    DATABASE_NAME: str

    # JWT settings
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:4200"]

    class Config:
        env_file = ".env"


settings = Settings()
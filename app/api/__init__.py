# app/api/__init__.py
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1")

# We'll include the routers later in the main.py file
# This avoids circular imports
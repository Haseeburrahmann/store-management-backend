# app/main.py
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.roles import router as roles_router
from app.api.stores.router import router as stores_router
from app.api.employees.router import router as employee_router
from app.api.schedules.router import router as schedules_router
from app.api.timesheets.router import router as timesheets_router
from app.core.config import settings
from app.services.role import create_default_roles, get_role_by_name
from app.services.user import get_user_by_email, create_user
from bson import ObjectId

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set up CORS - Updated to be more permissive
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router.router, prefix=f"{settings.API_V1_STR}/auth", tags=["authentication"])
app.include_router(users_router.router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])
app.include_router(roles_router.router, prefix=f"{settings.API_V1_STR}/roles", tags=["roles"])
app.include_router(stores_router, prefix=f"{settings.API_V1_STR}/stores", tags=["stores"])
app.include_router(employee_router, prefix=f"{settings.API_V1_STR}/employees", tags=["employees"])
app.include_router(schedules_router, prefix=f"{settings.API_V1_STR}/schedules", tags=["schedules"])
app.include_router(timesheets_router, prefix=f"{settings.API_V1_STR}/timesheets", tags=["timesheets"])


async def create_admin_user():
    """
    Create default admin user if not exists
    """
    # Get admin role
    admin_role = await get_role_by_name("Admin")
    if not admin_role:
        print("Admin role not found")
        return

    # Check if admin user already exists
    admin_user = await get_user_by_email("admin@example.com")
    if admin_user:
        print("Admin user already exists")
        return

    # Create admin user
    user_data = {
        "email": "admin@example.com",
        "password": "admin123",  # Change this to a secure password
        "full_name": "Admin User",
        "role_id": str(admin_role["_id"])  # Use string format of ObjectId
    }

    await create_user(user_data)
    print("Admin user created successfully")


@app.on_event("startup")
async def startup_event():
    """
    Event triggered on application startup
    """
    # Create default roles
    await create_default_roles()
    # Create admin user
    await create_admin_user()


@app.get("/")
async def root():
    """
    Root endpoint
    """
    return {"message": "Welcome to Store Management System API"}
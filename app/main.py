"""
Main application entry point.
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.core.config import settings, print_config_info
from app.db.mongodb import mongodb
from app.domains.roles.service import role_service

# Import API routers
from app.api.auth.router import router as auth_router
from app.api.users.router import router as users_router
from app.api.roles.router import router as roles_router
from app.api.stores.router import router as stores_router
from app.api.employees.router import router as employees_router
from app.api.schedules.router import router as schedules_router

# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Event triggered on application startup."""
    print_config_info()

    # Connect to MongoDB - this is now redundant as the connection happens on-demand
    # but we'll keep it to ensure the connection is tested during startup
    mongodb.connect_to_mongodb()

    # Create default roles
    await role_service.create_default_roles()

    # Create admin user if not exists
    await create_admin_user()

    logger.info("Application started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Event triggered on application shutdown."""
    # Close MongoDB connection
    await mongodb.close_mongodb_connection()

    logger.info("Application shutdown")


# Include API routers
app.include_router(auth_router, prefix=f"{settings.API_V1_STR}/auth", tags=["authentication"])
app.include_router(users_router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])
app.include_router(roles_router, prefix=f"{settings.API_V1_STR}/roles", tags=["roles"])
app.include_router(stores_router, prefix=f"{settings.API_V1_STR}/stores", tags=["stores"])
app.include_router(employees_router, prefix=f"{settings.API_V1_STR}/employees", tags=["employees"])
app.include_router(schedules_router, prefix=f"{settings.API_V1_STR}/schedules", tags=["schedules"])


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": f"Welcome to {settings.PROJECT_NAME} API"}


async def create_admin_user():
    """Create default admin user if not exists."""
    try:
        # Get admin role
        from app.domains.roles.service import role_service
        admin_role = await role_service.get_role_by_name("Admin")
        if not admin_role:
            logger.warning("Admin role not found")
            return

        # Check if admin user already exists
        from app.domains.users.service import user_service
        admin_user = await user_service.get_user_by_email("admin@example.com")
        if admin_user:
            logger.info("Admin user already exists")
            return

        # Create admin user
        user_data = {
            "email": "admin@example.com",
            "password": "admin123",  # Change this to a secure password in production
            "full_name": "Admin User",
            "role_id": str(admin_role["_id"])
        }

        await user_service.create_user(user_data)
        logger.info("Admin user created successfully")
    except Exception as e:
        logger.error(f"Error creating admin user: {str(e)}")
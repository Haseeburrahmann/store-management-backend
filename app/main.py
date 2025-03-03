from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.roles import router as roles_router
from app.core.config import settings
from app.services.role import create_default_roles, get_role_by_name
from app.services.user import get_user_by_email, create_user

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router.router, prefix=f"{settings.API_V1_STR}/auth", tags=["authentication"])
app.include_router(users_router.router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])
app.include_router(roles_router.router, prefix=f"{settings.API_V1_STR}/roles", tags=["roles"])


async def create_admin_user():
    admin_role = await get_role_by_name("Admin")
    if not admin_role:
        print("Admin role not found")
        return

    admin_user = await get_user_by_email("admin@example.com")
    if admin_user:
        print("Admin user already exists")
        return

    user_data = {
        "email": "admin@example.com",
        "password": "admin123",  # Change this to a secure password
        "full_name": "Admin User",
        "role_id": str(admin_role.id)
    }

    await create_user(user_data)
    print("Admin user created successfully")


@app.on_event("startup")
async def startup_event():
    # Create default roles
    await create_default_roles()
    # Create admin user
    await create_admin_user()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200","http://localhost:4200/users"],  # Specify your frontend URL exactly
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Welcome to Store Management System API"}
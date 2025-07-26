from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from fastapi.responses import HTMLResponse
from fastapi import Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from config import get_db, get_supabase_client, get_supabase_admin_client
from models import UserProfile
from routers.users.schemas import UserRoleUpdateRequest, UserRoleUpdateResponse
from uuid import UUID
import os

from routers.auth.auth import router as auth_router
from routers.users.users import router as users_router
from routers.admin.admin import router as admin_router
from routers.products.products import router as products_router

ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")
IS_PRODUCTION = ENVIRONMENT == "prod"

app = FastAPI(
    title="UstaadCart API",
    description="A comprehensive API for UstaadCart, a platform for suppliers and vendors to connect.",
    version="1.0.0",
    root_path="/Prod" if IS_PRODUCTION else "",
    docs_url="/apidocs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    servers=[
        {"url": "https://your-aws-api.execute-api.region.amazonaws.com/Prod", "description": "Production Server"},
        {"url": "http://localhost:8000", "description": "Local Development Server"},
        {"url": "https://your-ngrok-tunnel.ngrok-free.app/", "description": "Ngrok Tunnel"},
    ],
)
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(admin_router)
app.include_router(products_router)

# =================
# TEMPORARY DEVELOPMENT ROUTE (REMOVE IN PRODUCTION)
# =================

# =================
# TEMPORARY DEVELOPMENT ROUTES (REMOVE IN PRODUCTION)
# =================

@app.put("/temp/users/{user_id}/change-role", response_model=UserRoleUpdateResponse)
async def temp_change_user_role(
    user_id: str,
    role_update: UserRoleUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    TEMPORARY ROUTE - Change user role with database and Supabase metadata update
    WARNING: This should ONLY be used in development and REMOVED in production!
    
    Updates both the UserProfile in database and user metadata in Supabase.
    This ensures the role change is reflected in JWT tokens on next login.
    
    Usage: PUT /temp/users/{user_id}/change-role
    Body: {
        "new_role": "admin"  // or "vendor", "supplier", "user"
    }
    """
    try:
        # Only allow in development environment
        if ENVIRONMENT == "prod":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This endpoint is not available in production"
            )
        
        # Validate user_id format
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID format. Must be a valid UUID."
            )
        
        # Find user profile in database
        result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_uuid))
        user_profile = result.scalar_one_or_none()
        
        if not user_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found in database"
            )
        
        # Store old role for response
        old_role = user_profile.role
        
        # Update role in database
        user_profile.role = role_update.new_role
        await db.commit()
        await db.refresh(user_profile)
        
        # Update Supabase user metadata
        supabase_updated = False
        supabase_error_message = None
        try:
            supabase_admin = get_supabase_admin_client()
            
            # Debug: Check if we're using the admin client correctly
            print(f"Attempting to update user metadata for user: {user_id}")
            print(f"Using service role key: {get_supabase_admin_client().supabase_key[:10]}...")
            
            # Try to update user metadata - this updates the JWT claims on next login
            supabase_response = supabase_admin.auth.admin.update_user_by_id(
                uid=user_id,
                attributes={
                    "user_metadata": {"role": role_update.new_role},
                }
            )
            
            if supabase_response.user:
                supabase_updated = True
                print(f"Successfully updated Supabase metadata for user: {user_id}")
            else:
                print(f"Supabase update returned no user object for: {user_id}")
                supabase_error_message = "No user object returned from Supabase"
            
        except Exception as supabase_error:
            supabase_error_message = str(supabase_error)
            # Log the detailed error but don't fail the request
            print(f"Warning: Failed to update Supabase metadata: {supabase_error_message}")
            print(f"Error type: {type(supabase_error).__name__}")
            supabase_updated = False
        
        return UserRoleUpdateResponse(
            success=True,
            message=f"Successfully changed role from {old_role} to {role_update.new_role}",
            user_id=user_id,
            new_role=role_update.new_role,
            old_role=old_role,
            updated_in_database=True,
            updated_in_supabase=supabase_updated,
            supabase_error=supabase_error_message if not supabase_updated else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while changing user role: {str(e)}"
        )

@app.get("/docs", include_in_schema=False)
async def api_documentation(request: Request):
    openapi_url = "/Prod/openapi.json" if IS_PRODUCTION else "/openapi.json"
    
    return HTMLResponse(
        f"""
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <title>UstaadCart API DOCS</title>

    <script src="https://unpkg.com/@stoplight/elements/web-components.min.js"></script>
    <link rel="stylesheet" href="https://unpkg.com/@stoplight/elements/styles.min.css">
  </head>
  <body>

    <elements-api
      apiDescriptionUrl="{openapi_url}"
      router="hash"
      theme="dark"
    />

  </body>
</html>"""
    )

@app.get("/", response_class=HTMLResponse)
def home():
    """This is the first and default route for the UstaadCart Backend"""
    return """
    <html>
      <head>
        <title>UstaadCart API</title>
        <style>
          body { font-family: Arial, sans-serif; margin: 40px; background-color: #f8f9fa; }
          h1 { color: #333; }
          ul { list-style-type: none; padding: 0; }
          li { margin: 10px 0; }
          a { color: #0066cc; text-decoration: none; }
          a:hover { text-decoration: underline; }
          hr { margin: 20px 0; }
          h2 { color: #555; }
        </style>
      </head>
      <body>
        <h1>Welcome to UstaadCart API</h1>
        <hr>
        <ul>
          <li><a href="/docs">Spotlight API Documentation</a></li>
          <li><a href="/redoc">Redoc API Documentation</a></li>
          <li><a href="/apidocs">Swagger API Documentation</a></li>
          <li><a href="/openapi.json">OpenAPI Specification</a></li>
          <hr>
          <li><a href="http://localhost:3000">Frontend Website</a></li>
          <hr>
          <h2>Blogging Platform API - Built with FastAPI & Supabase</h2>
        </ul>
      </body>
    </html>
    """


handler = Mangum(app)

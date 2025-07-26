from fastapi import APIRouter, Depends, HTTPException, status, Request, Form, Query
from dependencies.rbac import require_admin, require_admin_write, require_analytics, require_user_management, require_user_management_write
from routers.auth.auth import get_current_user
from routers.users.schemas import UserListItem, UserListResponse
from routers.products.schemas import (
    CategoryCreate, CategoryUpdate, CategoryResponse, 
    CategoryWithChildrenResponse, CategoryListResponse
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from config import get_db, get_supabase_client
from models import UserProfile, Category
from utils.response_helpers import safe_model_validate, safe_model_validate_list, user_profile_to_dict, category_to_dict
from typing import Optional
from datetime import datetime
import logging
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])
supabase = get_supabase_client()

def category_to_response(category: Category) -> CategoryResponse:
    """Helper function to convert Category model to CategoryResponse"""
    category_dict = category_to_dict(category)
    return CategoryResponse.model_validate(category_dict)

@router.get("/users", response_model=UserListResponse)
async def list_all_users(
    page: int = 1,
    limit: int = 20,
    role: Optional[str] = None,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_user_management)
):
    """
    Admin only: List all users with pagination and optional role filter
    """
    try:
        offset = (page - 1) * limit
        
        query = select(UserProfile)
        if role:
            query = query.where(UserProfile.role == role)
        
        query = query.offset(offset).limit(limit)
        result = await db.execute(query)
        users = result.scalars().all()
        
        # Use safe model validation to handle UUID conversion
        user_list = [safe_model_validate(UserListItem, user) for user in users]
        
        return UserListResponse(
            users=user_list,
            page=page,
            limit=limit,
            total=len(users)
        )
        
    except Exception as e:
        logger.error(f"List users failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users"
        )

@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    new_role: str = Form(..., description="New role: user, admin"),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_user_management_write)
):
    """
    Admin only: Update user role
    """
    try:
        if new_role not in ['user', 'admin']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role. Must be one of: user, admin"
            )
        
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        user_profile = result.scalar_one_or_none()
        
        if not user_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        old_role = user_profile.role
        user_profile.role = new_role
        user_profile.updated_at = datetime.utcnow()

        metadata_updated = False
        try:
            supabase.auth.admin.update_user_by_id(
                user_id,
                {
                    "user_metadata": {
                        "role": new_role,
                        "username": user_profile.username,
                        "first_name": user_profile.first_name,
                        "last_name": user_profile.last_name,
                    }
                }
            )
            metadata_updated = True
            logger.info(f"Updated Supabase user metadata for {user_id} with role: {new_role}")
        except Exception as supabase_error:
            logger.error(f"Failed to update Supabase metadata: {str(supabase_error)}")
        
        await db.commit()
        await db.refresh(user_profile)
        
        return {
            "message": f"User role updated from {old_role} to {new_role}",
            "user_id": user_id,
            "old_role": old_role,
            "new_role": new_role,
            "updated_by": current_user["role"],
            "metadata_updated": metadata_updated,
            "note": "Role will be available in JWT tokens after next login" if metadata_updated else "Role updated in database only"
        }
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Update user role failed: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user role"
        )


# =================
# CATEGORY MANAGEMENT ROUTES
# =================

@router.post("/categories", response_model=CategoryResponse)
async def create_category(
    category_data: CategoryCreate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_admin_write)  # This will run after get_current_user
):
    """Admin only: Create a new product category"""
    try:
        # Check if parent category exists (if provided)
        if category_data.parent_id:
            result = await db.execute(
                select(Category).where(Category.id == category_data.parent_id)
            )
            parent_category = result.scalar_one_or_none()
            if not parent_category:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Parent category not found"
                )
        
        # Check if category name already exists
        result = await db.execute(
            select(Category).where(Category.name == category_data.name)
        )
        existing_category = result.scalar_one_or_none()
        if existing_category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category name already exists"
            )
        
        # Create category
        category = Category(**category_data.model_dump())
        db.add(category)
        await db.commit()
        await db.refresh(category)
        
        # Convert to response model with proper string conversion
        return category_to_response(category)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating category: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create category"
        )


@router.get("/categories", response_model=CategoryListResponse)
async def list_categories(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    parent_id: Optional[str] = Query(None),
    include_inactive: bool = Query(False),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_admin)
):
    """Admin only: List all categories with pagination"""
    try:
        # Build query
        query = select(Category)
        
        if parent_id:
            query = query.where(Category.parent_id == parent_id)
        else:
            query = query.where(Category.parent_id.is_(None))  # Root categories only
        
        if not include_inactive:
            query = query.where(Category.is_active == True)
        
        # Get total count
        count_query = select(func.count(Category.id)).where(
            Category.parent_id == parent_id if parent_id else Category.parent_id.is_(None)
        )
        if not include_inactive:
            count_query = count_query.where(Category.is_active == True)
        
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit).order_by(Category.name)
        
        result = await db.execute(query)
        categories = result.scalars().all()
        
        # Get children for each category
        categories_with_children = []
        for category in categories:
            # Get children
            children_result = await db.execute(
                select(Category)
                .where(Category.parent_id == category.id)
                .where(Category.is_active == True)
                .order_by(Category.name)
            )
            children = children_result.scalars().all()
            
            # Convert children to response models
            children_responses = [category_to_response(child) for child in children]
            
            # Create category response with proper string conversion using helper
            category_dict = category_to_dict(category)
            category_dict['children'] = children_responses
            category_response = CategoryWithChildrenResponse.model_validate(category_dict)
            categories_with_children.append(category_response)
        
        return CategoryListResponse(
            categories=categories_with_children,
            page=page,
            limit=limit,
            total=total
        )
        
    except Exception as e:
        logger.error(f"Error listing categories: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list categories"
        )


@router.get("/categories/{category_id}", response_model=CategoryWithChildrenResponse)
async def get_category(
    category_id: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_admin)
):
    """Admin only: Get category details by ID"""
    try:
        # Get category
        result = await db.execute(
            select(Category).where(Category.id == category_id)
        )
        category = result.scalar_one_or_none()
        
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        
        # Get children
        children_result = await db.execute(
            select(Category)
            .where(Category.parent_id == category.id)
            .order_by(Category.name)
        )
        children = children_result.scalars().all()
        
        # Convert children to response models
        children_responses = [category_to_response(child) for child in children]
        
        # Create category response with proper string conversion using helper
        category_dict = category_to_dict(category)
        category_dict['children'] = children_responses
        return CategoryWithChildrenResponse.model_validate(category_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting category: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get category"
        )


@router.put("/categories/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: str,
    category_update: CategoryUpdate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_admin_write)
):
    """Admin only: Update category"""
    try:
        # Get category
        result = await db.execute(
            select(Category).where(Category.id == category_id)
        )
        category = result.scalar_one_or_none()
        
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        
        # Check if new name already exists (if name is being updated)
        if category_update.name and category_update.name != category.name:
            result = await db.execute(
                select(Category).where(
                    Category.name == category_update.name,
                    Category.id != category_id
                )
            )
            existing_category = result.scalar_one_or_none()
            if existing_category:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Category name already exists"
                )
        
        # Check if parent category exists (if being updated)
        if category_update.parent_id:
            # Prevent circular reference
            if category_update.parent_id == category_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Category cannot be its own parent"
                )
            
            result = await db.execute(
                select(Category).where(Category.id == category_update.parent_id)
            )
            parent_category = result.scalar_one_or_none()
            if not parent_category:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Parent category not found"
                )
        
        # Update category
        update_data = category_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(category, field, value)
        
        category.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(category)
        
        return category_to_response(category)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating category: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update category"
        )


@router.delete("/categories/{category_id}")
async def delete_category(
    category_id: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_admin_write)
):
    """Admin only: Delete category (only if no products are using it)"""
    try:
        # Get category
        result = await db.execute(
            select(Category).where(Category.id == category_id)
        )
        category = result.scalar_one_or_none()
        
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        
        # Check if category has products (prevent deletion if products exist)
        from models import Product
        result = await db.execute(
            select(func.count(Product.id)).where(Product.category_id == category_id)
        )
        product_count = result.scalar()
        
        if product_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete category. {product_count} products are using this category."
            )
        
        # Check if category has children
        result = await db.execute(
            select(func.count(Category.id)).where(Category.parent_id == category_id)
        )
        children_count = result.scalar()
        
        if children_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete category. {children_count} subcategories exist under this category."
            )
        
        # Delete category
        await db.delete(category)
        await db.commit()
        
        return {"message": "Category deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting category: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete category"
        )

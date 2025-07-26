from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_
from config import get_db, get_supabase_admin_client
from models import UserProfile, VendorProfile, SupplierProfile, Review
from routers.auth.auth import get_current_user
from dependencies.rbac import require_profile_read, require_profile_write, require_admin_write
from utils.response_helpers import safe_model_validate, safe_model_validate_list, user_profile_to_dict, vendor_profile_to_dict, supplier_profile_to_dict, review_to_dict
from .schemas import (
    UserProfileUpdate, UserProfileResponse, ProfileImageUpload, UserResponse,
    VendorProfileCreate, VendorProfileUpdate, VendorProfileResponse,
    SupplierProfileCreate, SupplierProfileUpdate, SupplierProfileResponse,
    ReviewCreate, ReviewUpdate, ReviewResponse, ReviewWithUserResponse,
    VendorWithUserResponse, SupplierWithUserResponse, SupplierListResponse,
)
from .helpers import user_helpers
from typing import Optional, List
from datetime import datetime
import logging
from datetime import datetime
import uuid
from uuid import UUID

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])

security = HTTPBearer()

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user's profile using optimized JWT structure
    """
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user["user_id"])
    )
    profile = result.scalar_one_or_none()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found"
        )
    
    user_data = user_profile_to_dict(profile)
    user_data.update({
        "user_id": current_user["user_id"],
        "email": current_user["email"],
        "role": current_user["role"]
    })
    
    return safe_model_validate(UserResponse, user_data)


@router.put("/me", response_model=UserProfileResponse)
async def update_current_user_profile(
    profile_update: UserProfileUpdate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_profile_write)
):
    """Update current user's profile information"""
    try:
        user_id = current_user["user_id"]
        user_email = current_user["email"]
        
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        if profile_update.username and profile_update.username != profile.username:
            result = await db.execute(
                select(UserProfile).where(
                    and_(
                        UserProfile.username == profile_update.username,
                        UserProfile.id != profile.id
                    )
                )
            )
            existing_user = result.scalar_one_or_none()
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )
        
        update_data = profile_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(profile, field, value)
        
        profile.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(profile)
        
        user_data = user_profile_to_dict(profile)
        user_data.update({
            "user_id": current_user["user_id"],
            "email": user_email,
            "role": current_user["role"]
        })
        
        return safe_model_validate(UserProfileResponse, user_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user profile: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )

@router.post("/me/profile-image", response_model=ProfileImageUpload)
async def upload_profile_image(
    file: UploadFile = File(..., description="Profile image file (JPEG, PNG, GIF, or WebP, max 5MB)"),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a new profile image
    
    Accepts image files in the following formats:
    - JPEG (.jpg, .jpeg)
    - PNG (.png) 
    - GIF (.gif)
    - WebP (.webp)
    
    Maximum file size: 5MB
    """
    try:
        user_id = current_user["user_id"]
        
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file uploaded"
            )
        
        if profile.avatar_url:
            await user_helpers.delete_profile_image(profile.avatar_url)
        

        image_url = await user_helpers.upload_profile_image(str(profile.id), file)
        
        profile.avatar_url = image_url
        profile.updated_at = datetime.utcnow()
        await db.commit()
        
        return ProfileImageUpload(
            avatar_url=image_url,
            message="Profile image uploaded successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading profile image: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload profile image"
        )

@router.delete("/me/profile-image")
async def delete_profile_image(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete current user's profile image"""
    try:
        user_id = current_user["user_id"]
        
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        if not profile.avatar_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No profile image found"
            )
        
        deleted = await user_helpers.delete_profile_image(profile.avatar_url)

        profile.avatar_url = None
        profile.updated_at = datetime.utcnow()
        
        await db.commit()
        
        return {
            "message": "Profile image deleted successfully",
            "storage_deleted": deleted
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting profile image: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete profile image"
        )


# =================
# VENDOR ROUTES
# =================

@router.post("/vendor-profile", response_model=VendorProfileResponse)
async def create_vendor_profile(
    vendor_data: VendorProfileCreate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create vendor profile for current user"""
    try:
        # Check if user role is vendor
        if current_user.get("role") != "vendor":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only users with vendor role can create vendor profiles"
            )
        
        # Get user profile
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == current_user["user_id"])
        )
        user_profile = result.scalar_one_or_none()
        
        if not user_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        # Check if vendor profile already exists
        result = await db.execute(
            select(VendorProfile).where(VendorProfile.user_profile_id == user_profile.id)
        )
        existing_vendor = result.scalar_one_or_none()
        
        if existing_vendor:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vendor profile already exists"
            )
        
        # Create vendor profile
        vendor_profile = VendorProfile(
            user_profile_id=user_profile.id,
            **vendor_data.model_dump()
        )
        
        db.add(vendor_profile)
        await db.commit()
        await db.refresh(vendor_profile)
        
        return safe_model_validate(VendorProfileResponse, vendor_profile)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating vendor profile: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create vendor profile"
        )


@router.get("/vendor-profile/me", response_model=VendorProfileResponse)
async def get_my_vendor_profile(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's vendor profile"""
    try:
        # Get user profile
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == current_user["user_id"])
        )
        user_profile = result.scalar_one_or_none()
        
        if not user_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        # Get vendor profile
        result = await db.execute(
            select(VendorProfile).where(VendorProfile.user_profile_id == user_profile.id)
        )
        vendor_profile = result.scalar_one_or_none()
        
        if not vendor_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vendor profile not found"
            )
        
        return safe_model_validate(VendorProfileResponse, vendor_profile)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting vendor profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get vendor profile"
        )


@router.put("/vendor-profile/me", response_model=VendorProfileResponse)
async def update_my_vendor_profile(
    vendor_update: VendorProfileUpdate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user's vendor profile"""
    try:
        # Get user profile
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == current_user["user_id"])
        )
        user_profile = result.scalar_one_or_none()
        
        if not user_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        # Get vendor profile
        result = await db.execute(
            select(VendorProfile).where(VendorProfile.user_profile_id == user_profile.id)
        )
        vendor_profile = result.scalar_one_or_none()
        
        if not vendor_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vendor profile not found"
            )
        
        # Update vendor profile
        update_data = vendor_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(vendor_profile, field, value)
        
        vendor_profile.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(vendor_profile)
        
        return safe_model_validate(VendorProfileResponse, vendor_profile)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating vendor profile: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update vendor profile"
        )


@router.get("/vendor/{vendor_id}", response_model=VendorWithUserResponse)
async def get_vendor_details(
    vendor_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get vendor details by vendor profile ID"""
    try:
        # Get vendor profile with user profile
        result = await db.execute(
            select(VendorProfile, UserProfile)
            .join(UserProfile, VendorProfile.user_profile_id == UserProfile.id)
            .where(VendorProfile.id == vendor_id)
            .where(VendorProfile.is_active == True)
        )
        vendor_data = result.first()
        
        if not vendor_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vendor not found"
            )
        
        vendor_profile, user_profile = vendor_data
        
        return VendorWithUserResponse(
            user_profile=user_profile,
            vendor_profile=vendor_profile
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting vendor details: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get vendor details"
        )


# =================
# SUPPLIER ROUTES
# =================

@router.post("/supplier-profile", response_model=SupplierProfileResponse)
async def create_supplier_profile(
    supplier_data: SupplierProfileCreate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create supplier profile for current user"""
    try:
        # Check if user role is supplier
        if current_user.get("role") != "supplier":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only users with supplier role can create supplier profiles"
            )
        
        # Get user profile
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == current_user["user_id"])
        )
        user_profile = result.scalar_one_or_none()
        
        if not user_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        # Check if supplier profile already exists
        result = await db.execute(
            select(SupplierProfile).where(SupplierProfile.user_profile_id == user_profile.id)
        )
        existing_supplier = result.scalar_one_or_none()
        
        if existing_supplier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Supplier profile already exists"
            )
        
        # Create supplier profile
        supplier_profile = SupplierProfile(
            user_profile_id=user_profile.id,
            **supplier_data.model_dump()
        )
        
        db.add(supplier_profile)
        await db.commit()
        await db.refresh(supplier_profile)
        
        return safe_model_validate(SupplierProfileResponse, supplier_profile)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating supplier profile: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create supplier profile"
        )


@router.get("/supplier-profile/me", response_model=SupplierProfileResponse)
async def get_my_supplier_profile(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's supplier profile"""
    try:
        # Get user profile
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == current_user["user_id"])
        )
        user_profile = result.scalar_one_or_none()
        
        if not user_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        # Get supplier profile
        result = await db.execute(
            select(SupplierProfile).where(SupplierProfile.user_profile_id == user_profile.id)
        )
        supplier_profile = result.scalar_one_or_none()
        
        if not supplier_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Supplier profile not found"
            )
        
        return safe_model_validate(SupplierProfileResponse, supplier_profile)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting supplier profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get supplier profile"
        )


@router.put("/supplier-profile/me", response_model=SupplierProfileResponse)
async def update_my_supplier_profile(
    supplier_update: SupplierProfileUpdate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user's supplier profile"""
    try:
        # Get user profile
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == current_user["user_id"])
        )
        user_profile = result.scalar_one_or_none()
        
        if not user_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        # Get supplier profile
        result = await db.execute(
            select(SupplierProfile).where(SupplierProfile.user_profile_id == user_profile.id)
        )
        supplier_profile = result.scalar_one_or_none()
        
        if not supplier_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Supplier profile not found"
            )
        
        # Update supplier profile
        update_data = supplier_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(supplier_profile, field, value)
        
        supplier_profile.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(supplier_profile)
        
        return safe_model_validate(SupplierProfileResponse, supplier_profile)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating supplier profile: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update supplier profile"
        )


@router.get("/supplier/{supplier_id}", response_model=SupplierWithUserResponse)
async def get_supplier_details(
    supplier_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get supplier details by supplier profile ID"""
    try:
        # Get supplier profile with user profile
        result = await db.execute(
            select(SupplierProfile, UserProfile)
            .join(UserProfile, SupplierProfile.user_profile_id == UserProfile.id)
            .where(SupplierProfile.id == supplier_id)
            .where(SupplierProfile.is_active == True)
        )
        supplier_data = result.first()
        
        if not supplier_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Supplier not found"
            )
        
        supplier_profile, user_profile = supplier_data
        
        return SupplierWithUserResponse(
            user_profile=user_profile,
            supplier_profile=supplier_profile
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting supplier details: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get supplier details"
        )


@router.get("/suppliers", response_model=SupplierListResponse)
async def get_all_suppliers(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    city: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    product_category: Optional[str] = Query(None),
    verified_only: bool = Query(False),
    db: AsyncSession = Depends(get_db)
):
    """Get all suppliers with pagination and filtering"""
    try:
        # Build base query
        query = select(SupplierProfile, UserProfile).join(
            UserProfile, SupplierProfile.user_profile_id == UserProfile.id
        ).where(SupplierProfile.is_active == True)
        
        # Apply filters
        if city:
            query = query.where(SupplierProfile.city.ilike(f"%{city}%"))
        
        if state:
            query = query.where(SupplierProfile.state.ilike(f"%{state}%"))
        
        if product_category:
            query = query.where(SupplierProfile.product_categories.contains([product_category]))
        
        if verified_only:
            query = query.where(SupplierProfile.is_verified == True)
        
        # Get total count
        count_query = select(func.count(SupplierProfile.id)).select_from(
            query.subquery()
        )
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)
        
        # Execute query
        result = await db.execute(query)
        suppliers_data = result.all()
        
        suppliers = [
            SupplierWithUserResponse(
                user_profile=user_profile,
                supplier_profile=supplier_profile
            )
            for supplier_profile, user_profile in suppliers_data
        ]
        
        return SupplierListResponse(
            suppliers=suppliers,
            page=page,
            limit=limit,
            total=total
        )
        
    except Exception as e:
        logger.error(f"Error getting suppliers: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get suppliers"
        )


# =================
# REVIEW ROUTES
# =================

@router.post("/reviews", response_model=ReviewResponse)
async def create_review(
    review_data: ReviewCreate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a review for another user"""
    try:
        # Get reviewer user profile
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == current_user["user_id"])
        )
        reviewer_profile = result.scalar_one_or_none()
        
        if not reviewer_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reviewer profile not found"
            )
        
        # Get reviewed user profile
        result = await db.execute(
            select(UserProfile).where(UserProfile.id == review_data.reviewed_user_id)
        )
        reviewed_profile = result.scalar_one_or_none()
        
        if not reviewed_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User to review not found"
            )
        
        # Check if review already exists
        result = await db.execute(
            select(Review).where(
                and_(
                    Review.reviewer_user_id == reviewer_profile.id,
                    Review.reviewed_user_id == review_data.reviewed_user_id
                )
            )
        )
        existing_review = result.scalar_one_or_none()
        
        if existing_review:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already reviewed this user"
            )
        
        # Create review
        review = Review(
            reviewer_user_id=reviewer_profile.id,
            **review_data.model_dump()
        )
        
        db.add(review)
        await db.commit()
        await db.refresh(review)
        
        # Update ratings
        await user_helpers.update_vendor_rating(review_data.reviewed_user_id, db)
        await user_helpers.update_supplier_rating(review_data.reviewed_user_id, db)
        
        return safe_model_validate(ReviewResponse, review)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating review: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create review"
        )


@router.put("/reviews/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: str,
    review_update: ReviewUpdate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a review (only by the reviewer)"""
    try:
        # Get user profile
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == current_user["user_id"])
        )
        user_profile = result.scalar_one_or_none()
        
        if not user_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        # Get review
        result = await db.execute(
            select(Review).where(Review.id == review_id)
        )
        review = result.scalar_one_or_none()
        
        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review not found"
            )
        
        # Check if user is the reviewer
        if review.reviewer_user_id != user_profile.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own reviews"
            )
        
        # Update review
        update_data = review_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(review, field, value)
        
        review.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(review)
        
        # Update ratings if rating changed
        if "rating" in update_data:
            await user_helpers.update_vendor_rating(str(review.reviewed_user_id), db)
            await user_helpers.update_supplier_rating(str(review.reviewed_user_id), db)
        
        return safe_model_validate(ReviewResponse, review)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating review: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update review"
        )


@router.get("/reviews/user/{user_id}", response_model=List[ReviewWithUserResponse])
async def get_user_reviews(
    user_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Get all reviews for a specific user"""
    try:
        offset = (page - 1) * limit
        
        # Get reviews with reviewer information
        result = await db.execute(
            select(Review, UserProfile)
            .join(UserProfile, Review.reviewer_user_id == UserProfile.id)
            .where(Review.reviewed_user_id == user_id)
            .where(Review.is_hidden == False)
            .order_by(Review.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        reviews_data = result.all()
        
        reviews = []
        for review, reviewer_profile in reviews_data:
            review_dict = review_to_dict(review)
            review_dict.update({
                "reviewer_name": reviewer_profile.display_name or reviewer_profile.first_name,
                "reviewer_avatar": reviewer_profile.avatar_url
            })
            reviews.append(safe_model_validate(ReviewWithUserResponse, review_dict))
        
        return reviews
        
    except Exception as e:
        logger.error(f"Error getting user reviews: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user reviews"
        )


@router.delete("/reviews/{review_id}")
async def delete_review(
    review_id: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a review (only by the reviewer)"""
    try:
        # Get user profile
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == current_user["user_id"])
        )
        user_profile = result.scalar_one_or_none()
        
        if not user_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        # Get review
        result = await db.execute(
            select(Review).where(Review.id == review_id)
        )
        review = result.scalar_one_or_none()
        
        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review not found"
            )
        
        # Check if user is the reviewer
        if review.reviewer_user_id != user_profile.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own reviews"
            )
        
        reviewed_user_id = str(review.reviewed_user_id)
        
        # Delete review
        await db.delete(review)
        await db.commit()
        
        # Update ratings
        await user_helpers.update_vendor_rating(reviewed_user_id, db)
        await user_helpers.update_supplier_rating(reviewed_user_id, db)
        
        return {"message": "Review deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting review: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete review"
        )



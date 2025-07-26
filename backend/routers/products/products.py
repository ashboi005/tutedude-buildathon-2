from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_
from config import get_db
from models import UserProfile, SupplierProfile, Product, BulkPricingTier, Category
from routers.auth.auth import get_current_user
from utils.response_helpers import safe_model_validate, safe_model_validate_list, category_to_dict
from routers.products.schemas import (
    ProductCreate, ProductUpdate, ProductResponse, ProductWithPricingResponse, ProductListResponse,
    BulkPricingTierCreate, BulkPricingTierUpdate, BulkPricingTierResponse,
    ProductImageUpload, PriceCalculationRequest, PriceCalculationResponse,
    CategoryResponse, CategoryWithChildrenResponse
)
from routers.users.helpers import user_helpers
from typing import Optional, List
from datetime import datetime
import logging
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/products", tags=["Products"])
security = HTTPBearer()


# =================
# CATEGORY ROUTES (PUBLIC)
# =================

@router.get("/categories", response_model=List[CategoryWithChildrenResponse])
async def get_active_categories(
    db: AsyncSession = Depends(get_db)
):
    """Get all active categories for product creation"""
    try:
        # Get root categories
        result = await db.execute(
            select(Category)
            .where(Category.parent_id.is_(None))
            .where(Category.is_active == True)
            .order_by(Category.name)
        )
        root_categories = result.scalars().all()
        
        # Get children for each category
        categories_with_children = []
        for category in root_categories:
            # Get children
            children_result = await db.execute(
                select(Category)
                .where(Category.parent_id == category.id)
                .where(Category.is_active == True)
                .order_by(Category.name)
            )
            children = children_result.scalars().all()
            
            # Convert children to response models using safe validation
            children_responses = [safe_model_validate(CategoryResponse, child) for child in children]
            
            # Create category response with proper string conversion
            category_dict = category_to_dict(category)
            category_dict['children'] = children_responses
            categories_with_children.append(safe_model_validate(CategoryWithChildrenResponse, category_dict))
        
        return categories_with_children
        
    except Exception as e:
        logger.error(f"Error getting categories: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get categories"
        )


@router.get("/by-category/{category_id}", response_model=ProductListResponse)
async def get_products_by_category(
    category_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    is_active: bool = Query(True),
    db: AsyncSession = Depends(get_db)
):
    """Get all products by category with pagination and filtering"""
    try:
        # Verify category exists
        result = await db.execute(
            select(Category).where(Category.id == category_id)
        )
        category = result.scalar_one_or_none()
        
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        
        # Build query for products in this category
        query = select(Product, Category, SupplierProfile, UserProfile).join(
            Category, Product.category_id == Category.id
        ).join(
            SupplierProfile, Product.supplier_profile_id == SupplierProfile.id
        ).join(
            UserProfile, SupplierProfile.user_profile_id == UserProfile.id
        ).where(Product.category_id == category_id)
        
        # Apply filters
        if is_active:
            query = query.where(Product.is_active == True)
        
        if min_price is not None:
            query = query.where(Product.base_price >= min_price)
        
        if max_price is not None:
            query = query.where(Product.base_price <= max_price)
        
        # Get total count
        count_query = select(func.count(Product.id)).where(
            Product.category_id == category_id
        )
        if is_active:
            count_query = count_query.where(Product.is_active == True)
        if min_price is not None:
            count_query = count_query.where(Product.base_price >= min_price)
        if max_price is not None:
            count_query = count_query.where(Product.base_price <= max_price)
        
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit).order_by(Product.created_at.desc())
        
        result = await db.execute(query)
        products_data = result.all()
        
        # Build response
        products_with_pricing = []
        for product, category, supplier_profile, user_profile in products_data:
            # Get pricing tiers
            pricing_result = await db.execute(
                select(BulkPricingTier)
                .where(BulkPricingTier.product_id == product.id)
                .order_by(BulkPricingTier.min_quantity)
            )
            pricing_tiers = pricing_result.scalars().all()
            
            # Convert using safe validation
            product_dict = safe_model_validate(ProductResponse, product).__dict__.copy()
            product_dict['bulk_pricing_tiers'] = [
                safe_model_validate(BulkPricingTierResponse, tier) for tier in pricing_tiers
            ]
            product_dict['category'] = safe_model_validate(CategoryResponse, category)
            product_dict['supplier_name'] = user_profile.display_name or f"{user_profile.first_name} {user_profile.last_name}".strip()
            
            products_with_pricing.append(safe_model_validate(ProductWithPricingResponse, product_dict))
        
        return ProductListResponse(
            products=products_with_pricing,
            page=page,
            limit=limit,
            total=total
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting products by category: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get products by category"
        )


# =================
# PRODUCT ROUTES
# =================

@router.post("/", response_model=ProductWithPricingResponse)
async def create_product(
    product_data: ProductCreate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new product (suppliers only)"""
    try:
        # Check if user is a supplier
        if current_user.get("role") != "supplier":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only suppliers can create products"
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
        
        # Verify category exists
        result = await db.execute(
            select(Category).where(Category.id == product_data.category_id)
        )
        category = result.scalar_one_or_none()
        
        if not category or not category.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found or inactive"
            )
        
        # Create product (exclude bulk_pricing_tiers from product creation)
        product_dict = product_data.model_dump(exclude={'bulk_pricing_tiers'})
        product = Product(
            supplier_profile_id=supplier_profile.id,
            **product_dict
        )
        
        db.add(product)
        await db.flush()  # Get the product ID
        
        # Create bulk pricing tiers
        for tier_data in product_data.bulk_pricing_tiers:
            pricing_tier = BulkPricingTier(
                product_id=product.id,
                **tier_data.model_dump()
            )
            db.add(pricing_tier)
        
        await db.commit()
        await db.refresh(product)
        
        # Get product with pricing and category
        result = await db.execute(
            select(Product, Category)
            .join(Category, Product.category_id == Category.id)
            .where(Product.id == product.id)
        )
        product_data, category_data = result.first()
        
        # Get pricing tiers
        result = await db.execute(
            select(BulkPricingTier)
            .where(BulkPricingTier.product_id == product.id)
            .order_by(BulkPricingTier.min_quantity)
        )
        pricing_tiers = result.scalars().all()
        
        # Build response
        product_dict = product_data.__dict__.copy()
        product_dict['bulk_pricing_tiers'] = [
            BulkPricingTierResponse.model_validate(tier) for tier in pricing_tiers
        ]
        product_dict['category'] = CategoryResponse.model_validate(category_data)
        
        return ProductWithPricingResponse.model_validate(product_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating product: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create product"
        )


@router.get("/my-products", response_model=ProductListResponse)
async def get_my_products(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    category_id: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current supplier's products"""
    try:
        # Check if user is a supplier
        if current_user.get("role") != "supplier":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only suppliers can access this endpoint"
            )
        
        # Get supplier profile
        result = await db.execute(
            select(UserProfile, SupplierProfile)
            .join(SupplierProfile, UserProfile.id == SupplierProfile.user_profile_id)
            .where(UserProfile.user_id == current_user["user_id"])
        )
        profile_data = result.first()
        
        if not profile_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Supplier profile not found"
            )
        
        user_profile, supplier_profile = profile_data
        
        # Build query
        query = select(Product, Category).join(
            Category, Product.category_id == Category.id
        ).where(Product.supplier_profile_id == supplier_profile.id)
        
        # Apply filters
        if category_id:
            query = query.where(Product.category_id == category_id)
        
        if is_active is not None:
            query = query.where(Product.is_active == is_active)
        
        # Get total count
        count_query = select(func.count(Product.id)).where(
            Product.supplier_profile_id == supplier_profile.id
        )
        if category_id:
            count_query = count_query.where(Product.category_id == category_id)
        if is_active is not None:
            count_query = count_query.where(Product.is_active == is_active)
        
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit).order_by(Product.created_at.desc())
        
        result = await db.execute(query)
        products_data = result.all()
        
        # Build response
        products_with_pricing = []
        for product, category in products_data:
            # Get pricing tiers
            result = await db.execute(
                select(BulkPricingTier)
                .where(BulkPricingTier.product_id == product.id)
                .order_by(BulkPricingTier.min_quantity)
            )
            pricing_tiers = result.scalars().all()
            
            product_dict = product.__dict__.copy()
            product_dict['bulk_pricing_tiers'] = [
                BulkPricingTierResponse.model_validate(tier) for tier in pricing_tiers
            ]
            product_dict['category'] = CategoryResponse.model_validate(category)
            
            products_with_pricing.append(ProductWithPricingResponse.model_validate(product_dict))
        
        return ProductListResponse(
            products=products_with_pricing,
            page=page,
            limit=limit,
            total=total
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting supplier products: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get products"
        )


@router.get("/{product_id}", response_model=ProductWithPricingResponse)
async def get_product(
    product_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get product details by ID"""
    try:
        # Get product with category
        result = await db.execute(
            select(Product, Category)
            .join(Category, Product.category_id == Category.id)
            .where(Product.id == product_id)
            .where(Product.is_active == True)
        )
        product_data = result.first()
        
        if not product_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        product, category = product_data
        
        # Get pricing tiers
        result = await db.execute(
            select(BulkPricingTier)
            .where(BulkPricingTier.product_id == product.id)
            .order_by(BulkPricingTier.min_quantity)
        )
        pricing_tiers = result.scalars().all()
        
        # Build response
        product_dict = product.__dict__.copy()
        product_dict['bulk_pricing_tiers'] = [
            BulkPricingTierResponse.model_validate(tier) for tier in pricing_tiers
        ]
        product_dict['category'] = CategoryResponse.model_validate(category)
        
        return ProductWithPricingResponse.model_validate(product_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting product: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get product"
        )


@router.put("/{product_id}", response_model=ProductWithPricingResponse)
async def update_product(
    product_id: str,
    product_update: ProductUpdate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update product (only by owner supplier)"""
    try:
        # Get supplier profile
        result = await db.execute(
            select(UserProfile, SupplierProfile)
            .join(SupplierProfile, UserProfile.id == SupplierProfile.user_profile_id)
            .where(UserProfile.user_id == current_user["user_id"])
        )
        profile_data = result.first()
        
        if not profile_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Supplier profile not found"
            )
        
        user_profile, supplier_profile = profile_data
        
        # Get product
        result = await db.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        # Check if user owns the product
        if product.supplier_profile_id != supplier_profile.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own products"
            )
        
        # Verify category exists (if being updated)
        if product_update.category_id:
            result = await db.execute(
                select(Category).where(Category.id == product_update.category_id)
            )
            category = result.scalar_one_or_none()
            
            if not category or not category.is_active:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Category not found or inactive"
                )
        
        # Update product
        update_data = product_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(product, field, value)
        
        product.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(product)
        
        # Return updated product with pricing and category
        result = await db.execute(
            select(Product, Category)
            .join(Category, Product.category_id == Category.id)
            .where(Product.id == product.id)
        )
        product_data, category_data = result.first()
        
        # Get pricing tiers
        result = await db.execute(
            select(BulkPricingTier)
            .where(BulkPricingTier.product_id == product.id)
            .order_by(BulkPricingTier.min_quantity)
        )
        pricing_tiers = result.scalars().all()
        
        # Build response
        product_dict = product_data.__dict__.copy()
        product_dict['bulk_pricing_tiers'] = [
            BulkPricingTierResponse.model_validate(tier) for tier in pricing_tiers
        ]
        product_dict['category'] = CategoryResponse.model_validate(category_data)
        
        return ProductWithPricingResponse.model_validate(product_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating product: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update product"
        )


@router.delete("/{product_id}")
async def delete_product(
    product_id: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete product (only by owner supplier)"""
    try:
        # Get supplier profile
        result = await db.execute(
            select(UserProfile, SupplierProfile)
            .join(SupplierProfile, UserProfile.id == SupplierProfile.user_profile_id)
            .where(UserProfile.user_id == current_user["user_id"])
        )
        profile_data = result.first()
        
        if not profile_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Supplier profile not found"
            )
        
        user_profile, supplier_profile = profile_data
        
        # Get product
        result = await db.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        # Check if user owns the product
        if product.supplier_profile_id != supplier_profile.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own products"
            )
        
        # Delete product images from storage
        if product.primary_image_url:
            await user_helpers.delete_profile_image(product.primary_image_url)
        
        if product.additional_images:
            for image_url in product.additional_images:
                await user_helpers.delete_profile_image(image_url)
        
        # Delete product (cascades to pricing tiers)
        await db.delete(product)
        await db.commit()
        
        return {"message": "Product deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting product: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete product"
        )


# =================
# PRODUCT IMAGE ROUTES
# =================

@router.post("/{product_id}/upload-image", response_model=ProductImageUpload)
async def upload_product_image(
    product_id: str,
    file: UploadFile = File(..., description="Product image file (JPEG, PNG, GIF, or WebP, max 5MB)"),
    is_primary: bool = Form(True, description="Set as primary image"),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload product image"""
    try:
        # Get supplier profile
        result = await db.execute(
            select(UserProfile, SupplierProfile)
            .join(SupplierProfile, UserProfile.id == SupplierProfile.user_profile_id)
            .where(UserProfile.user_id == current_user["user_id"])
        )
        profile_data = result.first()
        
        if not profile_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Supplier profile not found"
            )
        
        user_profile, supplier_profile = profile_data
        
        # Get product
        result = await db.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        # Check if user owns the product
        if product.supplier_profile_id != supplier_profile.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only upload images for your own products"
            )
        
        # Upload image
        image_url = await user_helpers.upload_profile_image(f"product_{product.id}", file)
        
        # Update product
        if is_primary:
            # Delete old primary image if exists
            if product.primary_image_url:
                await user_helpers.delete_profile_image(product.primary_image_url)
            product.primary_image_url = image_url
        else:
            # Add to additional images
            if not product.additional_images:
                product.additional_images = []
            product.additional_images.append(image_url)
        
        product.updated_at = datetime.utcnow()
        await db.commit()
        
        return ProductImageUpload(
            image_url=image_url,
            message=f"{'Primary' if is_primary else 'Additional'} image uploaded successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading product image: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload product image"
        )


# =================
# BULK PRICING ROUTES
# =================

@router.post("/{product_id}/pricing-tiers", response_model=BulkPricingTierResponse)
async def add_pricing_tier(
    product_id: str,
    tier_data: BulkPricingTierCreate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add bulk pricing tier to product"""
    try:
        # Get supplier profile
        result = await db.execute(
            select(UserProfile, SupplierProfile)
            .join(SupplierProfile, UserProfile.id == SupplierProfile.user_profile_id)
            .where(UserProfile.user_id == current_user["user_id"])
        )
        profile_data = result.first()
        
        if not profile_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Supplier profile not found"
            )
        
        user_profile, supplier_profile = profile_data
        
        # Get product
        result = await db.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        # Check if user owns the product
        if product.supplier_profile_id != supplier_profile.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only manage pricing for your own products"
            )
        
        # Check for overlapping pricing tiers
        result = await db.execute(
            select(BulkPricingTier)
            .where(BulkPricingTier.product_id == product_id)
            .order_by(BulkPricingTier.min_quantity)
        )
        existing_tiers = result.scalars().all()
        
        # Validate no overlap
        for tier in existing_tiers:
            if (tier_data.min_quantity >= tier.min_quantity and 
                (tier.max_quantity is None or tier_data.min_quantity <= tier.max_quantity)):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Pricing tier overlaps with existing tier"
                )
            
            if (tier_data.max_quantity is not None and 
                tier_data.max_quantity >= tier.min_quantity and 
                (tier.max_quantity is None or tier_data.max_quantity <= tier.max_quantity)):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Pricing tier overlaps with existing tier"
                )
        
        # Create pricing tier
        pricing_tier = BulkPricingTier(
            product_id=product.id,
            **tier_data.model_dump()
        )
        
        db.add(pricing_tier)
        await db.commit()
        await db.refresh(pricing_tier)
        
        return BulkPricingTierResponse.model_validate(pricing_tier)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding pricing tier: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add pricing tier"
        )


@router.put("/pricing-tiers/{tier_id}", response_model=BulkPricingTierResponse)
async def update_pricing_tier(
    tier_id: str,
    tier_update: BulkPricingTierUpdate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update bulk pricing tier"""
    try:
        # Get supplier profile
        result = await db.execute(
            select(UserProfile, SupplierProfile)
            .join(SupplierProfile, UserProfile.id == SupplierProfile.user_profile_id)
            .where(UserProfile.user_id == current_user["user_id"])
        )
        profile_data = result.first()
        
        if not profile_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Supplier profile not found"
            )
        
        user_profile, supplier_profile = profile_data
        
        # Get pricing tier with product
        result = await db.execute(
            select(BulkPricingTier, Product)
            .join(Product, BulkPricingTier.product_id == Product.id)
            .where(BulkPricingTier.id == tier_id)
        )
        tier_data = result.first()
        
        if not tier_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pricing tier not found"
            )
        
        pricing_tier, product = tier_data
        
        # Check if user owns the product
        if product.supplier_profile_id != supplier_profile.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only manage pricing for your own products"
            )
        
        # Update pricing tier
        update_data = tier_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(pricing_tier, field, value)
        
        pricing_tier.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(pricing_tier)
        
        return BulkPricingTierResponse.model_validate(pricing_tier)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating pricing tier: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update pricing tier"
        )


@router.delete("/pricing-tiers/{tier_id}")
async def delete_pricing_tier(
    tier_id: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete bulk pricing tier"""
    try:
        # Get supplier profile
        result = await db.execute(
            select(UserProfile, SupplierProfile)
            .join(SupplierProfile, UserProfile.id == SupplierProfile.user_profile_id)
            .where(UserProfile.user_id == current_user["user_id"])
        )
        profile_data = result.first()
        
        if not profile_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Supplier profile not found"
            )
        
        user_profile, supplier_profile = profile_data
        
        # Get pricing tier with product
        result = await db.execute(
            select(BulkPricingTier, Product)
            .join(Product, BulkPricingTier.product_id == Product.id)
            .where(BulkPricingTier.id == tier_id)
        )
        tier_data = result.first()
        
        if not tier_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pricing tier not found"
            )
        
        pricing_tier, product = tier_data
        
        # Check if user owns the product
        if product.supplier_profile_id != supplier_profile.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only manage pricing for your own products"
            )
        
        # Check if this is the last pricing tier
        result = await db.execute(
            select(func.count(BulkPricingTier.id))
            .where(BulkPricingTier.product_id == product.id)
        )
        tier_count = result.scalar()
        
        if tier_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the last pricing tier. Products must have at least one pricing tier."
            )
        
        # Delete pricing tier
        await db.delete(pricing_tier)
        await db.commit()
        
        return {"message": "Pricing tier deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting pricing tier: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete pricing tier"
        )


# =================
# PUBLIC PRODUCT ROUTES
# =================

@router.get("/", response_model=ProductListResponse)
async def list_products(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    category_id: Optional[str] = Query(None),
    supplier_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """List all active products with filtering"""
    try:
        # Build base query
        query = select(Product, Category).join(
            Category, Product.category_id == Category.id
        ).where(Product.is_active == True)
        
        # Apply filters
        if category_id:
            query = query.where(Product.category_id == category_id)
        
        if supplier_id:
            query = query.where(Product.supplier_profile_id == supplier_id)
        
        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    Product.name.ilike(search_term),
                    Product.description.ilike(search_term),
                    Product.brand.ilike(search_term)
                )
            )
        
        # Price filtering requires joining with pricing tiers
        if min_price is not None or max_price is not None:
            # Subquery to get minimum price for each product
            price_subquery = select(
                BulkPricingTier.product_id,
                func.min(BulkPricingTier.price_per_unit).label('min_price')
            ).group_by(BulkPricingTier.product_id).subquery()
            
            query = query.join(price_subquery, Product.id == price_subquery.c.product_id)
            
            if min_price is not None:
                query = query.where(price_subquery.c.min_price >= min_price)
            if max_price is not None:
                query = query.where(price_subquery.c.min_price <= max_price)
        
        # Get total count
        count_query = select(func.count(Product.id)).where(Product.is_active == True)
        if category_id:
            count_query = count_query.where(Product.category_id == category_id)
        if supplier_id:
            count_query = count_query.where(Product.supplier_profile_id == supplier_id)
        
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit).order_by(Product.created_at.desc())
        
        result = await db.execute(query)
        products_data = result.all()
        
        # Build response
        products_with_pricing = []
        for product, category in products_data:
            # Get pricing tiers
            result = await db.execute(
                select(BulkPricingTier)
                .where(BulkPricingTier.product_id == product.id)
                .order_by(BulkPricingTier.min_quantity)
            )
            pricing_tiers = result.scalars().all()
            
            product_dict = product.__dict__.copy()
            product_dict['bulk_pricing_tiers'] = [
                BulkPricingTierResponse.model_validate(tier) for tier in pricing_tiers
            ]
            product_dict['category'] = CategoryResponse.model_validate(category)
            
            products_with_pricing.append(ProductWithPricingResponse.model_validate(product_dict))
        
        return ProductListResponse(
            products=products_with_pricing,
            page=page,
            limit=limit,
            total=total
        )
        
    except Exception as e:
        logger.error(f"Error listing products: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list products"
        )

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid


# Category Schemas
class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    parent_id: Optional[str] = None

class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    parent_id: Optional[str] = None
    is_active: Optional[bool] = None

class CategoryResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    parent_id: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class CategoryWithChildrenResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    parent_id: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    children: List["CategoryResponse"] = []

    class Config:
        from_attributes = True

class CategoryListResponse(BaseModel):
    """Response schema for category listing"""
    categories: List[CategoryWithChildrenResponse]
    page: int
    limit: int
    total: int


# Bulk Pricing Tier Schemas
class BulkPricingTierCreate(BaseModel):
    min_quantity: int = Field(..., gt=0)
    max_quantity: Optional[int] = Field(None, gt=0)
    price_per_unit: float = Field(..., gt=0)

    @validator('max_quantity')
    def validate_max_quantity(cls, v, values):
        if v is not None and 'min_quantity' in values and v <= values['min_quantity']:
            raise ValueError('max_quantity must be greater than min_quantity')
        return v

class BulkPricingTierUpdate(BaseModel):
    min_quantity: Optional[int] = Field(None, gt=0)
    max_quantity: Optional[int] = Field(None, gt=0)
    price_per_unit: Optional[float] = Field(None, gt=0)

    @validator('max_quantity')
    def validate_max_quantity(cls, v, values):
        if v is not None and 'min_quantity' in values and v <= values['min_quantity']:
            raise ValueError('max_quantity must be greater than min_quantity')
        return v

class BulkPricingTierResponse(BaseModel):
    id: str
    product_id: str
    min_quantity: int
    max_quantity: Optional[int] = None
    price_per_unit: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Product Schemas
class ProductCreate(BaseModel):
    category_id: str
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    unit: str = Field(..., min_length=1, max_length=50)
    brand: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    minimum_order_quantity: int = Field(1, gt=0)
    stock_quantity: Optional[int] = Field(None, ge=0)
    specifications: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    bulk_pricing_tiers: List[BulkPricingTierCreate] = []

    @validator('bulk_pricing_tiers')
    def validate_pricing_tiers(cls, v):
        if not v:
            raise ValueError('At least one pricing tier is required')
        
        # Check for overlapping ranges
        sorted_tiers = sorted(v, key=lambda x: x.min_quantity)
        for i in range(len(sorted_tiers) - 1):
            current = sorted_tiers[i]
            next_tier = sorted_tiers[i + 1]
            
            if current.max_quantity is not None and current.max_quantity >= next_tier.min_quantity:
                raise ValueError('Pricing tiers cannot have overlapping quantity ranges')
        
        return v

class ProductUpdate(BaseModel):
    category_id: Optional[str] = None
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    unit: Optional[str] = Field(None, min_length=1, max_length=50)
    brand: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    minimum_order_quantity: Optional[int] = Field(None, gt=0)
    stock_quantity: Optional[int] = Field(None, ge=0)
    specifications: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None

class ProductResponse(BaseModel):
    id: str
    supplier_profile_id: str
    category_id: str
    name: str
    description: Optional[str] = None
    unit: str
    brand: Optional[str] = None
    model: Optional[str] = None
    primary_image_url: Optional[str] = None
    additional_images: Optional[List[str]] = None
    minimum_order_quantity: int = 1
    stock_quantity: Optional[int] = None
    specifications: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    is_active: bool = True
    is_featured: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ProductWithPricingResponse(BaseModel):
    id: str
    supplier_profile_id: str
    category_id: str
    name: str
    description: Optional[str] = None
    unit: str
    brand: Optional[str] = None
    model: Optional[str] = None
    primary_image_url: Optional[str] = None
    additional_images: Optional[List[str]] = None
    minimum_order_quantity: int = 1
    stock_quantity: Optional[int] = None
    specifications: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    is_active: bool = True
    is_featured: bool = False
    created_at: datetime
    updated_at: datetime
    bulk_pricing_tiers: List[BulkPricingTierResponse] = []
    category: CategoryResponse

    class Config:
        from_attributes = True

class ProductListResponse(BaseModel):
    """Response schema for product listing"""
    products: List[ProductWithPricingResponse]
    page: int
    limit: int
    total: int

class ProductImageUpload(BaseModel):
    """Response schema for product image upload"""
    image_url: str
    message: str


# Price calculation schemas
class PriceCalculationRequest(BaseModel):
    product_id: str
    quantity: int = Field(..., gt=0)

class PriceCalculationResponse(BaseModel):
    product_id: str
    quantity: int
    price_per_unit: float
    total_price: float
    tier_used: BulkPricingTierResponse

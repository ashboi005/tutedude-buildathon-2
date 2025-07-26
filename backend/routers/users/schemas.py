from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime

class UserProfileUpdate(BaseModel):
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    bio: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    timezone: Optional[str] = None
    language: Optional[str] = None

class ProfileImageUpload(BaseModel):
    """Response schema for profile image upload"""
    avatar_url: str
    message: str

class UserProfileResponse(BaseModel):
    id: str
    user_id: str
    email: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    role: str = "user"
    date_of_birth: Optional[datetime] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    preferences: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserResponse(BaseModel):
    id: str  
    user_id: str 
    email: str 
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    role: str = "user"  
    date_of_birth: Optional[datetime] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    preferences: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserProfilePublic(BaseModel):
    """Public profile information (without email)"""
    id: str
    user_id: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserListItem(BaseModel):
    """Simplified user model for admin list endpoints"""
    id: str
    user_id: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    role: str = "user"
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserListResponse(BaseModel):
    """Response schema for paginated user list"""
    users: list[UserListItem]
    page: int
    limit: int
    total: int


# Vendor Profile Schemas
class VendorProfileCreate(BaseModel):
    street_address: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    operating_hours: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    specialties: Optional[List[str]] = None
    payment_methods: Optional[List[str]] = None
    phone_number: Optional[str] = Field(None, max_length=20)

class VendorProfileUpdate(BaseModel):
    street_address: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    operating_hours: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    specialties: Optional[List[str]] = None
    payment_methods: Optional[List[str]] = None
    phone_number: Optional[str] = Field(None, max_length=20)

class VendorProfileResponse(BaseModel):
    id: str
    user_profile_id: str
    street_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    operating_hours: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    specialties: Optional[List[str]] = None
    payment_methods: Optional[List[str]] = None
    phone_number: Optional[str] = None
    is_verified: bool = False
    is_active: bool = True
    average_rating: float = 0.0
    total_reviews: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Supplier Profile Schemas
class SupplierProfileCreate(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=200)
    company_type: Optional[str] = Field(None, max_length=100)
    business_registration: Optional[str] = Field(None, max_length=100)
    tax_id: Optional[str] = Field(None, max_length=50)
    gst_number: Optional[str] = Field(None, max_length=50)
    warehouse_address: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: str = Field(default="India", max_length=100)
    description: Optional[str] = None
    contact_person: Optional[str] = Field(None, max_length=100)
    phone_number: Optional[str] = Field(None, max_length=20)
    alternate_phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=255)
    website_url: Optional[str] = Field(None, max_length=500)
    certifications: Optional[List[str]] = None
    years_in_business: Optional[int] = None

class SupplierProfileUpdate(BaseModel):
    company_name: Optional[str] = Field(None, min_length=1, max_length=200)
    company_type: Optional[str] = Field(None, max_length=100)
    business_registration: Optional[str] = Field(None, max_length=100)
    tax_id: Optional[str] = Field(None, max_length=50)
    gst_number: Optional[str] = Field(None, max_length=50)
    warehouse_address: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    contact_person: Optional[str] = Field(None, max_length=100)
    phone_number: Optional[str] = Field(None, max_length=20)
    alternate_phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=255)
    website_url: Optional[str] = Field(None, max_length=500)
    certifications: Optional[List[str]] = None
    years_in_business: Optional[int] = None

class SupplierProfileResponse(BaseModel):
    id: str
    user_profile_id: str
    company_name: str
    company_type: Optional[str] = None
    business_registration: Optional[str] = None
    tax_id: Optional[str] = None
    gst_number: Optional[str] = None
    warehouse_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: str = "India"
    description: Optional[str] = None
    contact_person: Optional[str] = None
    phone_number: Optional[str] = None
    alternate_phone: Optional[str] = None
    email: Optional[str] = None
    website_url: Optional[str] = None
    certifications: Optional[List[str]] = None
    years_in_business: Optional[int] = None
    is_verified: bool = False
    is_active: bool = True
    average_rating: float = 0.0
    total_reviews: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Review Schemas
class ReviewCreate(BaseModel):
    reviewed_user_id: str
    rating: int = Field(..., ge=1, le=5)
    title: Optional[str] = Field(None, max_length=200)
    comment: Optional[str] = None
    transaction_id: Optional[str] = Field(None, max_length=100)
    review_type: Optional[str] = Field(None, max_length=50)

    @validator('rating')
    def validate_rating(cls, v):
        if v < 1 or v > 5:
            raise ValueError('Rating must be between 1 and 5')
        return v

class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)
    title: Optional[str] = Field(None, max_length=200)
    comment: Optional[str] = None
    review_type: Optional[str] = Field(None, max_length=50)

    @validator('rating')
    def validate_rating(cls, v):
        if v is not None and (v < 1 or v > 5):
            raise ValueError('Rating must be between 1 and 5')
        return v

class ReviewResponse(BaseModel):
    id: str
    reviewer_user_id: str
    reviewed_user_id: str
    rating: int
    title: Optional[str] = None
    comment: Optional[str] = None
    transaction_id: Optional[str] = None
    review_type: Optional[str] = None
    is_verified: bool = False
    is_hidden: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ReviewWithUserResponse(BaseModel):
    id: str
    reviewer_user_id: str
    reviewed_user_id: str
    rating: int
    title: Optional[str] = None
    comment: Optional[str] = None
    transaction_id: Optional[str] = None
    review_type: Optional[str] = None
    is_verified: bool = False
    is_hidden: bool = False
    created_at: datetime
    updated_at: datetime
    reviewer_name: Optional[str] = None
    reviewer_avatar: Optional[str] = None

    class Config:
        from_attributes = True


# Combined Schemas for detailed responses
class VendorWithUserResponse(BaseModel):
    # User Profile Info
    user_profile: UserProfilePublic
    # Vendor Specific Info
    vendor_profile: VendorProfileResponse

    class Config:
        from_attributes = True

class SupplierWithUserResponse(BaseModel):
    # User Profile Info
    user_profile: UserProfilePublic
    # Supplier Specific Info
    supplier_profile: SupplierProfileResponse

    class Config:
        from_attributes = True

class SupplierListResponse(BaseModel):
    """Response schema for supplier listing"""
    suppliers: List[SupplierWithUserResponse]
    page: int
    limit: int
    total: int

class VendorListResponse(BaseModel):
    """Response schema for vendor listing"""
    vendors: List[VendorWithUserResponse]
    page: int
    limit: int
    total: int


class UserRoleUpdateRequest(BaseModel):
    """Request schema for updating user role"""
    new_role: str = Field(..., description="New role to assign to the user")
    
    @validator('new_role')
    def validate_role(cls, v):
        valid_roles = ['user', 'vendor', 'supplier', 'admin']
        if v not in valid_roles:
            raise ValueError(f'Role must be one of: {", ".join(valid_roles)}')
        return v


class UserRoleUpdateResponse(BaseModel):
    """Response schema for role update operations"""
    success: bool
    message: str
    user_id: str
    new_role: str
    old_role: Optional[str] = None
    updated_in_database: bool
    updated_in_supabase: bool
    supabase_error: Optional[str] = None  # For debugging Supabase issues

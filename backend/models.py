from sqlalchemy import (
    Boolean, 
    String, 
    Text, 
    DateTime, 
    SmallInteger,
    CheckConstraint,
    PrimaryKeyConstraint,
    UniqueConstraint,
    Index,
    Computed,
    text,
    ForeignKey,
    Column,
    Float,
    Integer
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.declarative import declarative_base
from typing import Optional, List
import uuid

Base = declarative_base()


class Users(Base):
    """
    Supabase auth.users table schema
    This mirrors the Supabase authentication table to enable proper foreign key relationships
    """
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "email_change_confirm_status >= 0 AND email_change_confirm_status <= 2",
            name="users_email_change_confirm_status_check",
        ),
        PrimaryKeyConstraint("id", name="users_pkey"),
        UniqueConstraint("phone", name="users_phone_key"),
        Index("confirmation_token_idx", "confirmation_token", unique=True),
        Index(
            "email_change_token_current_idx", "email_change_token_current", unique=True
        ),
        Index("email_change_token_new_idx", "email_change_token_new", unique=True),
        Index("reauthentication_token_idx", "reauthentication_token", unique=True),
        Index("recovery_token_idx", "recovery_token", unique=True),
        Index("users_email_partial_key", "email", unique=True),
        Index("users_instance_id_email_idx", "instance_id"),
        Index("users_instance_id_idx", "instance_id"),
        Index("users_is_anonymous_idx", "is_anonymous"),
        {
            "comment": "Auth: Stores user login data within a secure schema.",
            "schema": "auth",
        },
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    
    is_sso_user: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
        comment="Auth: Set this column to true when the account comes from SSO. These accounts can have duplicate emails.",
    )
    is_anonymous: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    instance_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    aud: Mapped[Optional[str]] = mapped_column(String(255))
    role: Mapped[Optional[str]] = mapped_column(String(255))
    
    email: Mapped[Optional[str]] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(Text, server_default=text("NULL::character varying"))
    
    encrypted_password: Mapped[Optional[str]] = mapped_column(String(255))
    
    email_confirmed_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(True))
    confirmation_token: Mapped[Optional[str]] = mapped_column(String(255))
    confirmation_sent_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(True))
    
    recovery_token: Mapped[Optional[str]] = mapped_column(String(255))
    recovery_sent_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(True))
    
    email_change_token_new: Mapped[Optional[str]] = mapped_column(String(255))
    email_change: Mapped[Optional[str]] = mapped_column(String(255))
    email_change_sent_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(True))
    email_change_token_current: Mapped[Optional[str]] = mapped_column(
        String(255), server_default=text("''::character varying")
    )
    email_change_confirm_status: Mapped[Optional[int]] = mapped_column(SmallInteger, server_default=text("0"))
    
    phone_confirmed_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(True))
    phone_change: Mapped[Optional[str]] = mapped_column(Text, server_default=text("''::character varying"))
    phone_change_token: Mapped[Optional[str]] = mapped_column(
        String(255), server_default=text("''::character varying")
    )
    phone_change_sent_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(True))
    
    last_sign_in_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(True))
    invited_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(True))
    
    raw_app_meta_data: Mapped[Optional[dict]] = mapped_column(JSONB)
    raw_user_meta_data: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    is_super_admin: Mapped[Optional[bool]] = mapped_column(Boolean)
    banned_until: Mapped[Optional[DateTime]] = mapped_column(DateTime(True))
    
    reauthentication_token: Mapped[Optional[str]] = mapped_column(
        String(255), server_default=text("''::character varying")
    )
    reauthentication_sent_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(True))
    
    created_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(True))
    updated_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(True))
    deleted_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(True))
    
    confirmed_at: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(True),
        Computed("LEAST(email_confirmed_at, phone_confirmed_at)", persisted=True),
    )

    user_profile: Mapped[Optional["UserProfile"]] = relationship(
        "UserProfile", 
        back_populates="user", 
        uselist=False,
        cascade="all, delete-orphan"
    )


class UserProfile(Base):
    """
    Custom user profile table for additional user information
    This extends the basic auth.users table with application-specific data
    """
    __tablename__ = "user_profiles"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )
    
    username: Mapped[Optional[str]] = mapped_column(String(100), unique=True, index=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100))
    display_name: Mapped[Optional[str]] = mapped_column(String(100))
    bio: Mapped[Optional[str]] = mapped_column(Text)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500))
    
    # Role-based access control
    role: Mapped[str] = mapped_column(String(50), default="user", nullable=False)
    
    date_of_birth: Mapped[Optional[DateTime]] = mapped_column(DateTime(True))
    timezone: Mapped[Optional[str]] = mapped_column(String(50))
    language: Mapped[Optional[str]] = mapped_column(String(10), default="en")
    
    preferences: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(True), 
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(True), 
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False
    )
    
    user: Mapped["Users"] = relationship("Users", back_populates="user_profile")
    vendor_profile: Mapped[Optional["VendorProfile"]] = relationship(
        "VendorProfile", 
        back_populates="user_profile", 
        uselist=False,
        cascade="all, delete-orphan"
    )
    supplier_profile: Mapped[Optional["SupplierProfile"]] = relationship(
        "SupplierProfile", 
        back_populates="user_profile", 
        uselist=False,
        cascade="all, delete-orphan"
    )


class VendorProfile(Base):
    """
    Vendor-specific profile information for local street vendors
    """
    __tablename__ = "vendor_profiles"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("user_profiles.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )
    
    # Location Information
    street_address: Mapped[Optional[str]] = mapped_column(String(255))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    state: Mapped[Optional[str]] = mapped_column(String(100))
    postal_code: Mapped[Optional[str]] = mapped_column(String(20))
    latitude: Mapped[Optional[float]] = mapped_column(Float)
    longitude: Mapped[Optional[float]] = mapped_column(Float)
    operating_hours: Mapped[Optional[dict]] = mapped_column(JSONB)  # JSON for flexible schedule
    
    # Business Details
    description: Mapped[Optional[str]] = mapped_column(Text)
    specialties: Mapped[Optional[list]] = mapped_column(JSONB)  # Array of specialties
    payment_methods: Mapped[Optional[list]] = mapped_column(JSONB)  # Accepted payment methods
    
    # Contact Information
    phone_number: Mapped[Optional[str]] = mapped_column(String(20))
    
    # Business Status
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Rating System
    average_rating: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_reviews: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(True), 
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(True), 
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False
    )
    
    user_profile: Mapped["UserProfile"] = relationship("UserProfile", back_populates="vendor_profile")
    reviews_received: Mapped[list["Review"]] = relationship(
        "Review", 
        foreign_keys="Review.reviewed_user_id",
        back_populates="reviewed_vendor",
        cascade="all, delete-orphan"
    )
    reviews_given: Mapped[list["Review"]] = relationship(
        "Review", 
        foreign_keys="Review.reviewer_user_id",
        back_populates="reviewer_vendor"
    )


class SupplierProfile(Base):
    """
    Supplier-specific profile information for wholesale suppliers
    """
    __tablename__ = "supplier_profiles"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("user_profiles.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )
    
    # Business Information
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    company_type: Mapped[Optional[str]] = mapped_column(String(100))  # e.g., "Manufacturer", "Distributor", "Wholesaler"
    business_registration: Mapped[Optional[str]] = mapped_column(String(100))
    tax_id: Mapped[Optional[str]] = mapped_column(String(50))
    gst_number: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Location Information
    warehouse_address: Mapped[Optional[str]] = mapped_column(String(255))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    state: Mapped[Optional[str]] = mapped_column(String(100))
    postal_code: Mapped[Optional[str]] = mapped_column(String(20))
    country: Mapped[str] = mapped_column(String(100), default="India", nullable=False)
    
    # Business Details
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Contact Information
    contact_person: Mapped[Optional[str]] = mapped_column(String(100))
    phone_number: Mapped[Optional[str]] = mapped_column(String(20))
    alternate_phone: Mapped[Optional[str]] = mapped_column(String(20))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    website_url: Mapped[Optional[str]] = mapped_column(String(500))
    
    # Business Credentials
    certifications: Mapped[Optional[list]] = mapped_column(JSONB)  # Business certifications
    years_in_business: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Business Status
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Rating System
    average_rating: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_reviews: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(True), 
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(True), 
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False
    )
    
    user_profile: Mapped["UserProfile"] = relationship("UserProfile", back_populates="supplier_profile")
    products: Mapped[List["Product"]] = relationship(
        "Product", 
        back_populates="supplier_profile",
        cascade="all, delete-orphan"
    )
    reviews_received: Mapped[list["Review"]] = relationship(
        "Review", 
        foreign_keys="Review.reviewed_user_id",
        back_populates="reviewed_supplier",
        cascade="all, delete-orphan"
    )
    reviews_given: Mapped[list["Review"]] = relationship(
        "Review", 
        foreign_keys="Review.reviewer_user_id",
        back_populates="reviewer_supplier"
    )


class Review(Base):
    """
    Review system for vendors and suppliers to rate each other
    """
    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("reviewer_user_id", "reviewed_user_id", name="unique_review_per_user_pair"),
        CheckConstraint("rating >= 1 AND rating <= 5", name="rating_range_check"),
        CheckConstraint("reviewer_user_id != reviewed_user_id", name="no_self_review_check"),
    )
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Reviewer (who is giving the review)
    reviewer_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("user_profiles.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Reviewed (who is receiving the review)
    reviewed_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("user_profiles.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Review Content
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5 stars
    title: Mapped[Optional[str]] = mapped_column(String(200))
    comment: Mapped[Optional[str]] = mapped_column(Text)
    
    # Review Context
    transaction_id: Mapped[Optional[str]] = mapped_column(String(100))  # Optional order/transaction reference
    review_type: Mapped[Optional[str]] = mapped_column(String(50))  # e.g., "product_quality", "delivery", "communication"
    
    # Status
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(True), 
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(True), 
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False
    )
    
    # Relationships
    reviewer_vendor: Mapped[Optional["VendorProfile"]] = relationship(
        "VendorProfile",
        foreign_keys=[reviewer_user_id],
        back_populates="reviews_given",
        primaryjoin="Review.reviewer_user_id == VendorProfile.user_profile_id"
    )
    reviewer_supplier: Mapped[Optional["SupplierProfile"]] = relationship(
        "SupplierProfile",
        foreign_keys=[reviewer_user_id],
        back_populates="reviews_given",
        primaryjoin="Review.reviewer_user_id == SupplierProfile.user_profile_id"
    )
    reviewed_vendor: Mapped[Optional["VendorProfile"]] = relationship(
        "VendorProfile",
        foreign_keys=[reviewed_user_id],
        back_populates="reviews_received",
        primaryjoin="Review.reviewed_user_id == VendorProfile.user_profile_id"
    )
    reviewed_supplier: Mapped[Optional["SupplierProfile"]] = relationship(
        "SupplierProfile",
        foreign_keys=[reviewed_user_id],
        back_populates="reviews_received",
        primaryjoin="Review.reviewed_user_id == SupplierProfile.user_profile_id"
    )


class Category(Base):
    """
    Product categories managed by admins
    """
    __tablename__ = "categories"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Category hierarchy (for subcategories)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("categories.id", ondelete="CASCADE")
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(True), 
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(True), 
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False
    )
    
    # Relationships
    parent: Mapped[Optional["Category"]] = relationship(
        "Category", 
        remote_side="Category.id",
        back_populates="children"
    )
    children: Mapped[List["Category"]] = relationship(
        "Category", 
        back_populates="parent",
        cascade="all, delete-orphan"
    )
    products: Mapped[List["Product"]] = relationship(
        "Product", 
        back_populates="category",
        cascade="all, delete-orphan"
    )


class Product(Base):
    """
    Products listed by suppliers
    """
    __tablename__ = "products"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("supplier_profiles.id", ondelete="CASCADE"),
        nullable=False
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False
    )
    
    # Basic Product Information
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Product Specifications
    unit: Mapped[str] = mapped_column(String(50), nullable=False)  # kg, piece, liter, etc.
    brand: Mapped[Optional[str]] = mapped_column(String(100))
    model: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Product Images
    primary_image_url: Mapped[Optional[str]] = mapped_column(String(500))
    additional_images: Mapped[Optional[List[str]]] = mapped_column(JSONB)  # Array of image URLs
    
    # Inventory
    minimum_order_quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    stock_quantity: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Product Details
    specifications: Mapped[Optional[dict]] = mapped_column(JSONB)  # Flexible specifications
    tags: Mapped[Optional[List[str]]] = mapped_column(JSONB)  # Search tags
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(True), 
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(True), 
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False
    )
    
    # Relationships
    supplier_profile: Mapped["SupplierProfile"] = relationship(
        "SupplierProfile", 
        back_populates="products"
    )
    category: Mapped["Category"] = relationship(
        "Category", 
        back_populates="products"
    )
    bulk_pricing_tiers: Mapped[List["BulkPricingTier"]] = relationship(
        "BulkPricingTier", 
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="BulkPricingTier.min_quantity"
    )


class BulkPricingTier(Base):
    """
    Bulk pricing tiers for products
    Example: 1-10 units = $5/unit, 11-50 units = $4.5/unit, 51+ units = $4/unit
    """
    __tablename__ = "bulk_pricing_tiers"
    __table_args__ = (
        CheckConstraint("min_quantity > 0", name="min_quantity_positive_check"),
        CheckConstraint("max_quantity > min_quantity OR max_quantity IS NULL", name="max_quantity_greater_check"),
        CheckConstraint("price_per_unit > 0", name="price_positive_check"),
        UniqueConstraint("product_id", "min_quantity", name="unique_product_min_quantity"),
    )
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Quantity Range
    min_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    max_quantity: Mapped[Optional[int]] = mapped_column(Integer)  # NULL means unlimited
    
    # Pricing
    price_per_unit: Mapped[float] = mapped_column(Float, nullable=False)
    
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(True), 
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(True), 
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False
    )
    
    # Relationships
    product: Mapped["Product"] = relationship(
        "Product", 
        back_populates="bulk_pricing_tiers"
    )

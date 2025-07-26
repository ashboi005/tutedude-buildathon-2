"""
Response helper utilities for handling UUID conversions and model validation
"""
from typing import Any, Dict, List, Union
import uuid
from datetime import datetime
from pydantic import BaseModel


def convert_uuids_to_strings(obj: Any) -> Any:
    """
    Recursively convert UUID objects to strings in any data structure
    """
    if isinstance(obj, uuid.UUID):
        return str(obj)
    elif isinstance(obj, dict):
        return {key: convert_uuids_to_strings(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_uuids_to_strings(item) for item in obj]
    elif hasattr(obj, '__dict__'):
        # Handle SQLAlchemy models and other objects with __dict__
        result = {}
        for key, value in obj.__dict__.items():
            if not key.startswith('_'):  # Skip SQLAlchemy internal attributes
                result[key] = convert_uuids_to_strings(value)
        return result
    else:
        return obj


def safe_model_validate(model_class: BaseModel, data: Any) -> BaseModel:
    """
    Safely validate a model by converting UUIDs to strings first
    """
    if hasattr(data, '__dict__'):
        # If it's a SQLAlchemy model, convert to dict first
        data = data.__dict__.copy()
    
    # Convert UUIDs to strings
    clean_data = convert_uuids_to_strings(data)
    
    # Remove SQLAlchemy internal keys if present
    if isinstance(clean_data, dict):
        clean_data = {k: v for k, v in clean_data.items() if not k.startswith('_')}
    
    return model_class.model_validate(clean_data)


def safe_model_validate_list(model_class: BaseModel, data_list: List[Any]) -> List[BaseModel]:
    """
    Safely validate a list of models by converting UUIDs to strings first
    """
    return [safe_model_validate(model_class, item) for item in data_list]


# Custom base model that handles UUID conversion automatically
class UUIDResponseModel(BaseModel):
    """
    Base response model that automatically converts UUIDs to strings
    """
    
    @classmethod
    def from_orm(cls, obj: Any):
        """Override from_orm to handle UUID conversion"""
        clean_data = convert_uuids_to_strings(obj)
        return cls.model_validate(clean_data)
    
    @classmethod
    def model_validate(cls, obj: Any, **kwargs):
        """Override model_validate to handle UUID conversion"""
        clean_data = convert_uuids_to_strings(obj)
        return super().model_validate(clean_data, **kwargs)


# Specific helper functions for common models
def user_profile_to_dict(user_profile) -> Dict[str, Any]:
    """Convert UserProfile model to dict with string UUIDs"""
    return {
        'id': str(user_profile.id),
        'user_id': str(user_profile.user_id),
        'username': user_profile.username,
        'first_name': user_profile.first_name,
        'last_name': user_profile.last_name,
        'display_name': user_profile.display_name,
        'bio': user_profile.bio,
        'avatar_url': user_profile.avatar_url,
        'role': user_profile.role,
        'date_of_birth': user_profile.date_of_birth,
        'timezone': user_profile.timezone,
        'language': user_profile.language,
        'preferences': user_profile.preferences,
        'created_at': user_profile.created_at,
        'updated_at': user_profile.updated_at
    }


def vendor_profile_to_dict(vendor_profile) -> Dict[str, Any]:
    """Convert VendorProfile model to dict with string UUIDs"""
    return {
        'id': str(vendor_profile.id),
        'user_profile_id': str(vendor_profile.user_profile_id),
        'street_address': vendor_profile.street_address,
        'city': vendor_profile.city,
        'state': vendor_profile.state,
        'postal_code': vendor_profile.postal_code,
        'latitude': vendor_profile.latitude,
        'longitude': vendor_profile.longitude,
        'operating_hours': vendor_profile.operating_hours,
        'description': vendor_profile.description,
        'specialties': vendor_profile.specialties,
        'payment_methods': vendor_profile.payment_methods,
        'phone_number': vendor_profile.phone_number,
        'is_verified': vendor_profile.is_verified,
        'is_active': vendor_profile.is_active,
        'average_rating': vendor_profile.average_rating,
        'total_reviews': vendor_profile.total_reviews,
        'created_at': vendor_profile.created_at,
        'updated_at': vendor_profile.updated_at
    }


def supplier_profile_to_dict(supplier_profile) -> Dict[str, Any]:
    """Convert SupplierProfile model to dict with string UUIDs"""
    return {
        'id': str(supplier_profile.id),
        'user_profile_id': str(supplier_profile.user_profile_id),
        'company_name': supplier_profile.company_name,
        'company_type': supplier_profile.company_type,
        'business_registration': supplier_profile.business_registration,
        'tax_id': supplier_profile.tax_id,
        'gst_number': supplier_profile.gst_number,
        'warehouse_address': supplier_profile.warehouse_address,
        'city': supplier_profile.city,
        'state': supplier_profile.state,
        'postal_code': supplier_profile.postal_code,
        'country': supplier_profile.country,
        'description': supplier_profile.description,
        'contact_person': supplier_profile.contact_person,
        'phone_number': supplier_profile.phone_number,
        'alternate_phone': supplier_profile.alternate_phone,
        'email': supplier_profile.email,
        'website_url': supplier_profile.website_url,
        'certifications': supplier_profile.certifications,
        'years_in_business': supplier_profile.years_in_business,
        'is_verified': supplier_profile.is_verified,
        'is_active': supplier_profile.is_active,
        'average_rating': supplier_profile.average_rating,
        'total_reviews': supplier_profile.total_reviews,
        'created_at': supplier_profile.created_at,
        'updated_at': supplier_profile.updated_at
    }


def review_to_dict(review) -> Dict[str, Any]:
    """Convert Review model to dict with string UUIDs"""
    return {
        'id': str(review.id),
        'reviewer_user_id': str(review.reviewer_user_id),
        'reviewed_user_id': str(review.reviewed_user_id),
        'rating': review.rating,
        'title': review.title,
        'comment': review.comment,
        'transaction_id': review.transaction_id,
        'review_type': review.review_type,
        'is_verified': review.is_verified,
        'is_hidden': review.is_hidden,
        'created_at': review.created_at,
        'updated_at': review.updated_at
    }


def category_to_dict(category) -> Dict[str, Any]:
    """Convert Category model to dict with string UUIDs"""
    return {
        'id': str(category.id),
        'name': category.name,
        'description': category.description,
        'parent_id': str(category.parent_id) if category.parent_id else None,
        'is_active': category.is_active,
        'created_at': category.created_at,
        'updated_at': category.updated_at
    }

"""
RBAC dependencies for FastAPI routes
Role-based access control implemented as dependencies that run after authentication
"""
from fastapi import Depends, HTTPException, status, Request
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

RESOURCES_FOR_ROLES = {
    'admin': {
        'admin': ['read', 'write', 'delete'], 
        'users': ['read', 'write', 'delete'], 
        'users/profiles': ['read', 'write', 'delete'], 
        'users/vendor-profiles': ['read', 'write', 'delete'],
        'users/supplier-profiles': ['read', 'write', 'delete'],
        'users/reviews': ['read', 'write', 'delete'],
        'categories': ['read', 'write', 'delete'],
        'products': ['read', 'write', 'delete'],
        'analytics': ['read'],  
        'settings': ['read', 'write'], 
        'reports': ['read', 'write'],  
    },
    'supplier': {
        'users/me': ['read', 'write'], 
        'users/profiles': ['read'], 
        'users/supplier-profiles': ['read', 'write'],  # Only their own profile
        'users/vendor-profiles': ['read'],  # Can view vendor profiles
        'users/reviews': ['read', 'write'],  # Can give and receive reviews
        'categories': ['read'],  # Can view categories
        'products': ['read', 'write', 'delete'],  # Full product management
        'products/bulk-pricing': ['read', 'write', 'delete'],  # Manage pricing
    },
    'vendor': {
        'users/me': ['read', 'write'], 
        'users/profiles': ['read'], 
        'users/vendor-profiles': ['read', 'write'],  # Only their own profile
        'users/supplier-profiles': ['read'],  # Can view supplier profiles
        'users/reviews': ['read', 'write'],  # Can give and receive reviews
        'categories': ['read'],  # Can view categories
        'products': ['read'],  # Can view products only
    },
    'user': {
        'users/me': ['read', 'write'], 
        'users/profiles': ['read'], 
        'users/vendor-profiles': ['read'], 
        'users/supplier-profiles': ['read'],
        'categories': ['read'], 
        'products': ['read'],  # Can view products
    }
}

def normalize_path(path: str) -> str:
    """Normalize request path for RBAC checking"""    
    if path.startswith('/'):
        path = path[1:]

    segments = path.split('/')
    
    if len(segments) == 0:
        return path
    
    if segments[0] == 'admin':
        if len(segments) >= 2:
            if segments[1] == 'categories':
                return 'categories'
            return f'admin/{segments[1]}'
        return 'admin'
    
    elif segments[0] == 'users':
        if len(segments) >= 2:
            if segments[1] == 'me':
                return 'users/me'
            elif segments[1] == 'profile' or segments[1] == 'profiles':
                return 'users/profiles'
            elif segments[1] == 'vendor-profile' or segments[1] == 'vendor-profiles':
                return 'users/vendor-profiles'
            elif segments[1] == 'supplier-profile' or segments[1] == 'supplier-profiles':
                return 'users/supplier-profiles'
            elif segments[1] == 'reviews':
                return 'users/reviews'
        return 'users'
    
    elif segments[0] == 'products':
        if len(segments) >= 2:
            if segments[1] == 'bulk-pricing' or 'bulk-pricing' in segments:
                return 'products/bulk-pricing'
        return 'products'
    
    elif segments[0] == 'categories':
        return 'categories'
    
    elif segments[0] == 'analytics':
        return 'analytics'
    
    elif segments[0] == 'settings':
        return 'settings'
    
    elif segments[0] == 'reports':
        return 'reports'
    
    return segments[0]

def translate_method_to_action(method: str) -> str:
    """Map HTTP methods to RBAC actions"""
    method_permission_mapping = {
        'GET': 'read',
        'POST': 'write',
        'PUT': 'write',
        'PATCH': 'write',
        'DELETE': 'delete',
    }
    return method_permission_mapping.get(method.upper(), 'read')

def has_permission(user_role: str, resource_name: str, required_permission: str) -> bool:
    """Check if user role has permission for the resource and action"""
    if user_role not in RESOURCES_FOR_ROLES:
        return False
    
    user_permissions = RESOURCES_FOR_ROLES[user_role]
    
    if resource_name in user_permissions:
        return required_permission in user_permissions[resource_name]
    
    parent_resource = resource_name.split('/')[0] if '/' in resource_name else resource_name
    if parent_resource in user_permissions:
        return required_permission in user_permissions[parent_resource]
    
    return False

def require_permission(resource: str = None, permission: str = None):
    """
    Create an RBAC dependency that checks permissions
    
    Args:
        resource: Specific resource name (auto-detected if not provided)
        permission: Specific permission (auto-detected if not provided)
    """
    def check_rbac(request: Request):
        """RBAC dependency function"""
        try:
            current_user = getattr(request.state, 'current_user', None)
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )

            user_role = 'user'  # default fallback to match registration default
            if isinstance(current_user, dict) and 'role' in current_user:
                user_role = current_user['role']
            else:
                user_role = getattr(current_user, 'role', 'user')

            resource_name = resource or normalize_path(str(request.url.path))
            required_permission = permission or translate_method_to_action(request.method)
            
            logger.info(f"RBAC Check - User: {user_role}, Resource: {resource_name}, Permission: {required_permission}")

            if not has_permission(user_role, resource_name, required_permission):
                logger.warning(f"Access denied - User: {user_role}, Resource: {resource_name}, Permission: {required_permission}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied. {user_role.title()} role does not have {required_permission} permission for {resource_name}"
                )
            
            logger.info(f"Access granted - User: {user_role}, Resource: {resource_name}, Permission: {required_permission}")
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"RBAC dependency error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authorization check failed"
            )
    
    return check_rbac

# Admin permissions
require_admin = require_permission("admin", "read")
require_admin_write = require_permission("admin", "write")
require_admin_delete = require_permission("admin", "delete")

# User management permissions
require_user_management = require_permission("users", "read")
require_user_management_write = require_permission("users", "write")
require_user_management_delete = require_permission("users", "delete")

# Profile permissions
require_profile_read = require_permission("users/profiles", "read")
require_profile_write = require_permission("users/profiles", "write")

require_vendor_profile_read = require_permission("users/vendor-profiles", "read")
require_vendor_profile_write = require_permission("users/vendor-profiles", "write")

require_supplier_profile_read = require_permission("users/supplier-profiles", "read")
require_supplier_profile_write = require_permission("users/supplier-profiles", "write")

# Review permissions
require_review_read = require_permission("users/reviews", "read")
require_review_write = require_permission("users/reviews", "write")

# Category permissions (admin only for write/delete)
require_category_read = require_permission("categories", "read")
require_category_write = require_permission("categories", "write")
require_category_delete = require_permission("categories", "delete")

# Product permissions
require_product_read = require_permission("products", "read")
require_product_write = require_permission("products", "write")  # Suppliers only
require_product_delete = require_permission("products", "delete")  # Suppliers only

# Bulk pricing permissions (suppliers only)
require_bulk_pricing_read = require_permission("products/bulk-pricing", "read")
require_bulk_pricing_write = require_permission("products/bulk-pricing", "write")
require_bulk_pricing_delete = require_permission("products/bulk-pricing", "delete")

# Analytics and reports (admin only)
require_analytics = require_permission("analytics", "read")
require_settings = require_permission("settings", "read")
require_settings_write = require_permission("settings", "write")
require_reports = require_permission("reports", "read")
require_reports_write = require_permission("reports", "write")

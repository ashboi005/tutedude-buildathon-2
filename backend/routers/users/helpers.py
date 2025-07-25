from fastapi import HTTPException, status, UploadFile
from supabase import Client
from config import get_supabase_admin_client, get_supabase_storage, get_db
from models import VendorProfile, SupplierProfile, Review
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import uuid
import os
from typing import List
import logging

logger = logging.getLogger(__name__)

class UserHelpers:
    """Helper functions for user operations"""
    
    def __init__(self):
        self._admin_client = None
        self._storage = None
    
    @property
    def admin_client(self) -> Client:
        if self._admin_client is None:
            self._admin_client = get_supabase_admin_client()
        return self._admin_client
    
    @property
    def storage(self):
        if self._storage is None:
            self._storage = get_supabase_storage()
        return self._storage
    async def upload_profile_image(self, user_id: str, file: UploadFile) -> str:
        """
        Upload profile image to Supabase Storage and return the public URL
        """        
        try:            
            logger.info(f"Starting upload for user_id: {user_id}")
            
            allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
            if file.content_type not in allowed_types:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File type {file.content_type} not allowed"
                )
            
            file_content = await file.read()
            if len(file_content) > 5 * 1024 * 1024:  
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File size must be less than 5MB"
                )
        
            await file.seek(0)
            
            file_extension = os.path.splitext(file.filename)[1] if file.filename else '.jpg'
            unique_filename = f"profiles/{user_id}/{uuid.uuid4()}{file_extension}"
            
            bucket_name = os.getenv("SUPABASE_STORAGE_BUCKET", "blog-media")
            
            try:
                supabase_client = get_supabase_admin_client()
                
                response = supabase_client.storage.from_(bucket_name).upload(
                    path=unique_filename,
                    file=file_content,
                    file_options={"content-type": file.content_type}
                )
                
                logger.info(f"Upload response: {response}")
                
                if hasattr(response, 'error') and response.error:
                    logger.error(f"Upload error: {response.error}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to upload image"
                    )
                
                public_url = supabase_client.storage.from_(bucket_name).get_public_url(unique_filename)
                logger.info(f"Public URL: {public_url}")
                
                return public_url
                
            except Exception as upload_error:
                logger.error(f"Upload error: {str(upload_error)}")
                logger.error(f"Upload error type: {type(upload_error)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Upload failed: {str(upload_error)}"
                )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error uploading profile image: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload image"
            )
    
    async def delete_profile_image(self, image_url: str) -> bool:
        """
        Delete profile image from Supabase Storage
        """
        try:
            bucket_name = os.getenv("SUPABASE_STORAGE_BUCKET", "blog-media")
            
            if "/storage/v1/object/public/" in image_url:
                parts = image_url.split("/storage/v1/object/public/")[1]
                path_parts = parts.split("/", 1)
                if len(path_parts) > 1:
                    file_path = path_parts[1]  
                    
                    response = self.storage.from_(bucket_name).remove([file_path])
                    
                    if response.get("error"):
                        logger.warning(f"Failed to delete image from storage: {response['error']}")
                        return False
                    
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error deleting profile image: {str(e)}")
            return False

    async def update_vendor_rating(self, user_profile_id: str, db: AsyncSession):
        """
        Update vendor's average rating and total reviews count
        """
        try:
            # Get all reviews for this vendor
            result = await db.execute(
                select(func.avg(Review.rating), func.count(Review.id))
                .where(Review.reviewed_user_id == user_profile_id)
                .where(Review.is_hidden == False)
            )
            avg_rating, total_reviews = result.first()
            
            # Update vendor profile
            result = await db.execute(
                select(VendorProfile).where(VendorProfile.user_profile_id == user_profile_id)
            )
            vendor_profile = result.scalar_one_or_none()
            
            if vendor_profile:
                vendor_profile.average_rating = float(avg_rating or 0.0)
                vendor_profile.total_reviews = int(total_reviews or 0)
                await db.commit()
                
        except Exception as e:
            logger.error(f"Error updating vendor rating: {str(e)}")
            await db.rollback()

    async def update_supplier_rating(self, user_profile_id: str, db: AsyncSession):
        """
        Update supplier's average rating and total reviews count
        """
        try:
            # Get all reviews for this supplier
            result = await db.execute(
                select(func.avg(Review.rating), func.count(Review.id))
                .where(Review.reviewed_user_id == user_profile_id)
                .where(Review.is_hidden == False)
            )
            avg_rating, total_reviews = result.first()
            
            # Update supplier profile
            result = await db.execute(
                select(SupplierProfile).where(SupplierProfile.user_profile_id == user_profile_id)
            )
            supplier_profile = result.scalar_one_or_none()
            
            if supplier_profile:
                supplier_profile.average_rating = float(avg_rating or 0.0)
                supplier_profile.total_reviews = int(total_reviews or 0)
                await db.commit()
                
        except Exception as e:
            logger.error(f"Error updating supplier rating: {str(e)}")
            await db.rollback()


user_helpers = UserHelpers()

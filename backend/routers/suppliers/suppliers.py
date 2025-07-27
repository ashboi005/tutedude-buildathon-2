from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from config import get_db
from models import UserProfile, SupplierSubscription, Order, Product, SupplierProfile, VendorProfile
from routers.auth.auth import get_current_user
from dependencies.rbac import require_vendor, require_supplier
from typing import List
from .schemas import OrderResponseForSupplier, SubscriptionResponse
from utils.notifications import (
    send_email, send_sms, 
    get_supplier_update_email, get_supplier_update_sms
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/suppliers", tags=["Suppliers"])


@router.post("/{supplier_id}/subscribe", status_code=status.HTTP_201_CREATED)
async def subscribe_to_supplier(
    supplier_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_vendor)  # Only vendors can subscribe
):
    """Subscribe to a supplier for updates"""
    try:
        # Check if supplier exists
        supplier_result = await db.execute(
            select(UserProfile).where(UserProfile.id == supplier_id)
        )
        supplier = supplier_result.scalar_one_or_none()
        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier not found")
        
        # Check if already subscribed
        existing_subscription = await db.execute(
            select(SupplierSubscription).where(
                and_(
                    SupplierSubscription.vendor_user_id == current_user["user_id"],
                    SupplierSubscription.supplier_user_id == supplier_id
                )
            )
        )
        if existing_subscription.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Already subscribed to this supplier")
        
        # Create subscription
        subscription = SupplierSubscription(
            vendor_user_id=current_user["user_id"],
            supplier_user_id=supplier_id
        )
        
        db.add(subscription)
        await db.commit()
        
        return {"message": "Successfully subscribed to supplier"}
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Subscription failed: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to subscribe to supplier"
        )


@router.post("/{supplier_id}/unsubscribe", status_code=status.HTTP_200_OK)
async def unsubscribe_from_supplier(
    supplier_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_vendor)
):
    """Unsubscribe from a supplier"""
    try:
        # Find and delete subscription
        result = await db.execute(
            select(SupplierSubscription).where(
                and_(
                    SupplierSubscription.vendor_user_id == current_user["user_id"],
                    SupplierSubscription.supplier_user_id == supplier_id
                )
            )
        )
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        await db.delete(subscription)
        await db.commit()
        
        return {"message": "Successfully unsubscribed from supplier"}
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Unsubscription failed: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unsubscribe from supplier"
        )


@router.get("/orders/my-supplier-orders", response_model=List[OrderResponseForSupplier])
async def get_my_supplier_orders(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_supplier)  # Only suppliers can see this
):
    """Get all orders for products sold by the current supplier"""
    try:
        # Get orders where seller_id matches current_user's profile id
        result = await db.execute(
            select(Order).where(Order.seller_id == current_user["user_id"])
            .order_by(Order.created_at.desc())
        )
        orders = result.scalars().all()
        
        # Convert to response format
        order_responses = []
        for order in orders:
            # Get product details
            product_result = await db.execute(
                select(Product).where(Product.id == order.product_id)
            )
            product = product_result.scalar_one_or_none()
            
            # Get buyer details
            buyer_result = await db.execute(
                select(UserProfile).where(UserProfile.id == order.buyer_id)
            )
            buyer = buyer_result.scalar_one_or_none()
            
            order_data = {
                "id": str(order.id),
                "buyer_id": str(order.buyer_id),
                "buyer_name": f"{buyer.first_name or ''} {buyer.last_name or ''}".strip() if buyer else "Unknown",
                "product_id": str(order.product_id),
                "product_name": product.name if product else "Unknown Product",
                "quantity": order.quantity,
                "price_per_unit": order.price_per_unit,
                "total_amount": order.total_amount,
                "order_type": order.order_type,
                "payment_status": order.payment_status,
                "order_status": order.order_status,
                "due_date": order.due_date,
                "delivery_address": order.delivery_address,
                "estimated_delivery": order.estimated_delivery,
                "actual_delivery": order.actual_delivery,
                "notes": order.notes,
                "created_at": order.created_at,
                "updated_at": order.updated_at
            }
            
            order_responses.append(OrderResponseForSupplier.model_validate(order_data))
        
        return order_responses
        
    except Exception as e:
        logger.error(f"Get supplier orders failed: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve supplier orders"
        )


@router.get("/my-subscriptions", response_model=List[SubscriptionResponse])
async def get_my_subscriptions(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_vendor)
):
    """Get all suppliers the current vendor is subscribed to"""
    try:
        result = await db.execute(
            select(SupplierSubscription, UserProfile, SupplierProfile)
            .join(UserProfile, SupplierSubscription.supplier_user_id == UserProfile.id)
            .join(SupplierProfile, UserProfile.id == SupplierProfile.user_profile_id)
            .where(SupplierSubscription.vendor_user_id == current_user["user_id"])
        )
        
        subscriptions = []
        for subscription, user_profile, supplier_profile in result.all():
            subscription_data = {
                "id": str(subscription.id),
                "supplier_id": str(user_profile.id),
                "supplier_name": f"{user_profile.first_name or ''} {user_profile.last_name or ''}".strip(),
                "company_name": supplier_profile.company_name,
                "created_at": subscription.created_at
            }
            subscriptions.append(SubscriptionResponse.model_validate(subscription_data))
        
        return subscriptions
        
    except Exception as e:
        logger.error(f"Get subscriptions failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve subscriptions"
        )


async def notify_subscribers(
    supplier_id: str, 
    update_type: str, 
    product_name: str = None,
    db: AsyncSession = None,
    background_tasks: BackgroundTasks = None
):
    """Notify all subscribers of a supplier about updates"""
    try:
        # Get supplier details
        supplier_result = await db.execute(
            select(UserProfile, SupplierProfile)
            .join(SupplierProfile, UserProfile.id == SupplierProfile.user_profile_id)
            .where(UserProfile.id == supplier_id)
        )
        supplier_data = supplier_result.first()
        if not supplier_data:
            return
        
        user_profile, supplier_profile = supplier_data
        supplier_name = supplier_profile.company_name or f"{user_profile.first_name} {user_profile.last_name}"
        
        # Get all subscribers
        subscribers_result = await db.execute(
            select(SupplierSubscription, UserProfile, VendorProfile)
            .join(UserProfile, SupplierSubscription.vendor_user_id == UserProfile.id)
            .join(VendorProfile, UserProfile.id == VendorProfile.user_profile_id)
            .where(SupplierSubscription.supplier_user_id == supplier_id)
        )
        
        # Send notifications to each subscriber
        for subscription, user_profile, vendor_profile in subscribers_result.all():
            # Get email and phone from user profile or vendor profile
            email = None
            phone = None
            
            # Try to get contact info (you might need to adjust based on your user model)
            if hasattr(user_profile, 'email'):
                email = user_profile.email
            if vendor_profile.phone_number:
                phone = vendor_profile.phone_number
            
            if background_tasks:
                # Send email
                if email:
                    subject, body = get_supplier_update_email(supplier_name, update_type, product_name)
                    background_tasks.add_task(send_email, email, subject, body)
                
                # Send SMS
                if phone:
                    sms_body = get_supplier_update_sms(supplier_name, update_type)
                    background_tasks.add_task(send_sms, phone, sms_body)
        
        logger.info(f"Scheduled notifications for {len(list(subscribers_result))} subscribers of supplier {supplier_id}")
        
    except Exception as e:
        logger.error(f"Failed to notify subscribers: {str(e)}")

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from config import get_db
from models import UserProfile, VendorProfile, SupplierProfile, Order, Product, BulkOrderWindow, BulkPricingTier
from routers.auth.auth import get_current_user
from dependencies.rbac import require_profile_read, require_profile_write
from utils.response_helpers import safe_model_validate, safe_model_validate_list
from .schemas import (
    OrderCreate, OrderResponse, OrderWithDetailsResponse, OrderListResponse,
    BulkOrderWindowCreate, BulkOrderWindowResponse, BulkOrderWindowWithOrdersResponse, 
    BulkOrderWindowListResponse, PendingPaymentResponse
)
from typing import Optional, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orders", tags=["Orders"])


def calculate_price_for_quantity(bulk_pricing_tiers: List[BulkPricingTier], quantity: int) -> float:
    """Calculate price per unit based on quantity and bulk pricing tiers"""
    if not bulk_pricing_tiers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No pricing information available for this product"
        )
    
    # Sort tiers by min_quantity
    sorted_tiers = sorted(bulk_pricing_tiers, key=lambda x: x.min_quantity)
    
    # Find the appropriate tier
    applicable_tier = None
    for tier in sorted_tiers:
        if quantity >= tier.min_quantity:
            if tier.max_quantity is None or quantity <= tier.max_quantity:
                applicable_tier = tier
            elif quantity > tier.max_quantity:
                continue  # Check next tier
        else:
            break  # No more applicable tiers
    
    if not applicable_tier:
        # Use the first tier if quantity is below minimum
        applicable_tier = sorted_tiers[0]
    
    return applicable_tier.price_per_unit


async def check_vendor_eligibility_for_pay_later(vendor_profile: VendorProfile) -> bool:
    """Check if vendor is eligible for buy now, pay later (rating >= 4.5)"""
    return vendor_profile.average_rating >= 4.5


@router.post("/create", response_model=OrderResponse)
async def create_order(
    order_data: OrderCreate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_profile_write)
):
    """
    Create a new order (buy now, buy now pay later, or join bulk order)
    """
    try:
        # Get buyer profile
        buyer_result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == current_user["user_id"])
        )
        buyer_profile = buyer_result.scalar_one_or_none()
        if not buyer_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Buyer profile not found"
            )
        
        # Get vendor profile for balance and eligibility checks
        vendor_result = await db.execute(
            select(VendorProfile).where(VendorProfile.user_profile_id == buyer_profile.id)
        )
        vendor_profile = vendor_result.scalar_one_or_none()
        if not vendor_profile:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only vendors can place orders"
            )
        
        # Check if vendor is active
        if not vendor_profile.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account is suspended. Please contact support."
            )
        
        # Get product details
        product_result = await db.execute(
            select(Product).where(Product.id == order_data.product_id)
        )
        product = product_result.scalar_one_or_none()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        if not product.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Product is not available"
            )
        
        # Check minimum order quantity
        if order_data.quantity < product.minimum_order_quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Minimum order quantity is {product.minimum_order_quantity} {product.unit}"
            )
        
        # Get bulk pricing tiers
        pricing_result = await db.execute(
            select(BulkPricingTier)
            .where(BulkPricingTier.product_id == product.id)
            .order_by(BulkPricingTier.min_quantity)
        )
        bulk_pricing_tiers = pricing_result.scalars().all()
        
        # Calculate price per unit
        price_per_unit = calculate_price_for_quantity(bulk_pricing_tiers, order_data.quantity)
        total_amount = price_per_unit * order_data.quantity
        
        # Validate order type and check eligibility
        if order_data.order_type == "buy_now_pay_later":
            if not await check_vendor_eligibility_for_pay_later(vendor_profile):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Buy now, pay later requires a minimum rating of 4.5"
                )
        
        # For buy now orders, check balance
        if order_data.order_type == "buy_now":
            if vendor_profile.balance < total_amount:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient balance. Required: ₹{total_amount:.2f}, Available: ₹{vendor_profile.balance:.2f}"
                )
        
        # Handle bulk order window
        bulk_order_window_id = None
        if order_data.bulk_order_window_id:
            window_result = await db.execute(
                select(BulkOrderWindow).where(BulkOrderWindow.id == order_data.bulk_order_window_id)
            )
            bulk_window = window_result.scalar_one_or_none()
            if not bulk_window:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Bulk order window not found"
                )
            
            if bulk_window.status != "open":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Bulk order window is no longer open"
                )
            
            if datetime.utcnow() > bulk_window.window_end_time:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Bulk order window has expired"
                )
            
            bulk_order_window_id = bulk_window.id
            order_data.order_type = "bulk_order"
        
        # Create order
        order = Order(
            buyer_id=buyer_profile.id,
            seller_id=product.supplier_profile_id,
            product_id=product.id,
            quantity=order_data.quantity,
            price_per_unit=price_per_unit,
            total_amount=total_amount,
            order_type=order_data.order_type,
            payment_status="pending",
            bulk_order_window_id=bulk_order_window_id,
            delivery_address=order_data.delivery_address,
            notes=order_data.notes
        )
        
        # Set due date for pay later orders
        if order_data.order_type == "buy_now_pay_later":
            order.due_date = datetime.utcnow() + timedelta(days=5)
        
        # For buy now orders, deduct balance and mark as paid
        if order_data.order_type == "buy_now":
            vendor_profile.balance -= total_amount
            order.payment_status = "paid"
        
        # For bulk orders, payment will be handled when window closes
        if order_data.order_type == "bulk_order":
            order.payment_status = "pending"
        
        db.add(order)
        await db.commit()
        await db.refresh(order)
        
        return safe_model_validate(OrderResponse, order)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating order: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create order"
        )


@router.get("/my-orders", response_model=OrderListResponse)
async def get_my_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    order_type: Optional[str] = Query(None),
    payment_status: Optional[str] = Query(None),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_profile_read)
):
    """
    Get current user's orders
    """
    try:
        # Get user profile
        user_result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == current_user["user_id"])
        )
        user_profile = user_result.scalar_one_or_none()
        if not user_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        # Build query
        query = select(Order).where(Order.buyer_id == user_profile.id)
        
        if order_type:
            query = query.where(Order.order_type == order_type)
        if payment_status:
            query = query.where(Order.payment_status == payment_status)
        
        # Get total count
        count_query = select(func.count(Order.id)).where(Order.buyer_id == user_profile.id)
        if order_type:
            count_query = count_query.where(Order.order_type == order_type)
        if payment_status:
            count_query = count_query.where(Order.payment_status == payment_status)
        
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit).order_by(Order.created_at.desc())
        
        result = await db.execute(query)
        orders = result.scalars().all()
        
        # Convert to response models with additional details
        orders_with_details = []
        for order in orders:
            order_dict = safe_model_validate(OrderResponse, order).model_dump()
            
            # Get product details
            product_result = await db.execute(
                select(Product).where(Product.id == order.product_id)
            )
            product = product_result.scalar_one_or_none()
            if product:
                order_dict["product_name"] = product.name
                order_dict["product_unit"] = product.unit
            
            # Get seller details
            seller_result = await db.execute(
                select(UserProfile).where(UserProfile.id == order.seller_id)
            )
            seller = seller_result.scalar_one_or_none()
            if seller:
                order_dict["seller_name"] = seller.display_name or seller.first_name
            
            orders_with_details.append(OrderWithDetailsResponse.model_validate(order_dict))
        
        return OrderListResponse(
            orders=orders_with_details,
            page=page,
            limit=limit,
            total=total
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting orders: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve orders"
        )


@router.get("/pending-payments", response_model=List[PendingPaymentResponse])
async def get_pending_payments(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_profile_read)
):
    """
    Get vendor's pending payment orders (buy now, pay later)
    """
    try:
        # Get user profile
        user_result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == current_user["user_id"])
        )
        user_profile = user_result.scalar_one_or_none()
        if not user_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        # Get pending payment orders
        query = select(Order).where(
            and_(
                Order.buyer_id == user_profile.id,
                Order.payment_status == "pending",
                Order.order_type == "buy_now_pay_later"
            )
        ).order_by(Order.due_date.asc())
        
        result = await db.execute(query)
        orders = result.scalars().all()
        
        pending_payments = []
        for order in orders:
            # Get product and seller details
            product_result = await db.execute(
                select(Product).where(Product.id == order.product_id)
            )
            product = product_result.scalar_one_or_none()
            
            seller_result = await db.execute(
                select(UserProfile).where(UserProfile.id == order.seller_id)
            )
            seller = seller_result.scalar_one_or_none()
            
            if order.due_date:
                days_remaining = max(0, (order.due_date - datetime.utcnow()).days)
            else:
                days_remaining = 0
            
            pending_payment = PendingPaymentResponse(
                order_id=str(order.id),
                product_name=product.name if product else "Unknown Product",
                seller_name=seller.display_name or seller.first_name if seller else "Unknown Seller",
                total_amount=order.total_amount,
                due_date=order.due_date,
                days_remaining=days_remaining
            )
            pending_payments.append(pending_payment)
        
        return pending_payments
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting pending payments: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve pending payments"
        )


@router.post("/pay-pending/{order_id}")
async def pay_pending_order(
    order_id: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_profile_write)
):
    """
    Pay for a pending order (buy now, pay later)
    """
    try:
        # Get user profile
        user_result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == current_user["user_id"])
        )
        user_profile = user_result.scalar_one_or_none()
        if not user_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        # Get vendor profile for balance
        vendor_result = await db.execute(
            select(VendorProfile).where(VendorProfile.user_profile_id == user_profile.id)
        )
        vendor_profile = vendor_result.scalar_one_or_none()
        if not vendor_profile:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only vendors can pay for orders"
            )
        
        # Get order
        order_result = await db.execute(
            select(Order).where(
                and_(
                    Order.id == order_id,
                    Order.buyer_id == user_profile.id
                )
            )
        )
        order = order_result.scalar_one_or_none()
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        if order.payment_status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order payment is not pending"
            )
        
        if order.order_type != "buy_now_pay_later":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This order is not a pay later order"
            )
        
        # Check if order is overdue
        if order.due_date and datetime.utcnow() > order.due_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order payment is overdue. Please contact support."
            )
        
        # Check balance
        if vendor_profile.balance < order.total_amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient balance. Required: ₹{order.total_amount:.2f}, Available: ₹{vendor_profile.balance:.2f}"
            )
        
        # Deduct balance and mark as paid
        vendor_profile.balance -= order.total_amount
        order.payment_status = "paid"
        
        await db.commit()
        
        return {
            "message": "Payment successful",
            "order_id": str(order.id),
            "amount_paid": order.total_amount,
            "remaining_balance": vendor_profile.balance
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error paying pending order: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process payment"
        )


@router.post("/bulk-windows", response_model=BulkOrderWindowResponse)
async def create_bulk_order_window(
    window_data: BulkOrderWindowCreate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_profile_write)
):
    """
    Create a new bulk order window
    """
    try:
        # Get user profile
        user_result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == current_user["user_id"])
        )
        user_profile = user_result.scalar_one_or_none()
        if not user_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        # Check if user is a vendor
        vendor_result = await db.execute(
            select(VendorProfile).where(VendorProfile.user_profile_id == user_profile.id)
        )
        vendor_profile = vendor_result.scalar_one_or_none()
        if not vendor_profile:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only vendors can create bulk order windows"
            )
        
        if not vendor_profile.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account is suspended. Please contact support."
            )
        
        # Calculate window end time
        window_end_time = datetime.utcnow() + timedelta(hours=window_data.window_duration_hours)
        
        # Create bulk order window
        bulk_window = BulkOrderWindow(
            creator_id=user_profile.id,
            title=window_data.title,
            description=window_data.description,
            window_end_time=window_end_time
        )
        
        db.add(bulk_window)
        await db.commit()
        await db.refresh(bulk_window)
        
        return safe_model_validate(BulkOrderWindowResponse, bulk_window)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating bulk order window: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create bulk order window"
        )


@router.get("/bulk-windows", response_model=BulkOrderWindowListResponse)
async def get_open_bulk_windows(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_profile_read)
):
    """
    Get open bulk order windows
    """
    try:
        # Build query for open windows that haven't expired
        current_time = datetime.utcnow()
        query = select(BulkOrderWindow).where(
            and_(
                BulkOrderWindow.status == "open",
                BulkOrderWindow.window_end_time > current_time
            )
        )
        
        # Get total count
        count_query = select(func.count(BulkOrderWindow.id)).where(
            and_(
                BulkOrderWindow.status == "open",
                BulkOrderWindow.window_end_time > current_time
            )
        )
        
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit).order_by(BulkOrderWindow.window_end_time.asc())
        
        result = await db.execute(query)
        windows = result.scalars().all()
        
        windows_response = [safe_model_validate(BulkOrderWindowResponse, window) for window in windows]
        
        return BulkOrderWindowListResponse(
            windows=windows_response,
            page=page,
            limit=limit,
            total=total
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting bulk order windows: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve bulk order windows"
        )


@router.get("/bulk-windows/{window_id}", response_model=BulkOrderWindowWithOrdersResponse)
async def get_bulk_window_details(
    window_id: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_profile_read)
):
    """
    Get bulk order window details with current orders
    """
    try:
        # Get bulk order window
        window_result = await db.execute(
            select(BulkOrderWindow).where(BulkOrderWindow.id == window_id)
        )
        bulk_window = window_result.scalar_one_or_none()
        if not bulk_window:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bulk order window not found"
            )
        
        # Get orders in this window
        orders_result = await db.execute(
            select(Order).where(Order.bulk_order_window_id == window_id)
        )
        orders = orders_result.scalars().all()
        
        # Convert orders to response format with details
        orders_with_details = []
        for order in orders:
            order_dict = safe_model_validate(OrderResponse, order).model_dump()
            
            # Get product details
            product_result = await db.execute(
                select(Product).where(Product.id == order.product_id)
            )
            product = product_result.scalar_one_or_none()
            if product:
                order_dict["product_name"] = product.name
                order_dict["product_unit"] = product.unit
            
            # Get buyer details
            buyer_result = await db.execute(
                select(UserProfile).where(UserProfile.id == order.buyer_id)
            )
            buyer = buyer_result.scalar_one_or_none()
            if buyer:
                order_dict["buyer_name"] = buyer.display_name or buyer.first_name
            
            orders_with_details.append(OrderWithDetailsResponse.model_validate(order_dict))
        
        # Get creator details
        creator_result = await db.execute(
            select(UserProfile).where(UserProfile.id == bulk_window.creator_id)
        )
        creator = creator_result.scalar_one_or_none()
        
        # Convert window to response
        window_dict = safe_model_validate(BulkOrderWindowResponse, bulk_window).model_dump()
        window_dict["orders"] = orders_with_details
        if creator:
            window_dict["creator_name"] = creator.display_name or creator.first_name
        
        return BulkOrderWindowWithOrdersResponse.model_validate(window_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting bulk window details: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve bulk window details"
        )

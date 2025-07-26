from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from config import get_db
from models import UserProfile, VendorProfile, SupplierProfile, Payment
from routers.auth.auth import get_current_user
from dependencies.rbac import require_profile_read, require_profile_write
from utils.response_helpers import safe_model_validate
from .schemas import (
    PaymentCreate, PaymentResponse, PaymentVerification, BalanceResponse,
    PaymentOrderResponse, PaymentVerificationResponse
)
from typing import List
import razorpay
import hmac
import hashlib
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["Payments"])

# Initialize Razorpay client
razorpay_client = razorpay.Client(
    auth=(
        os.getenv("RAZORPAY_KEY_ID", "rzp_test_your_key_id"),  # Replace with your test key
        os.getenv("RAZORPAY_KEY_SECRET", "your_key_secret")     # Replace with your test secret
    )
)


@router.get("/balance", response_model=BalanceResponse)
async def get_balance(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_profile_read)
):
    """
    Get user's current balance
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
        
        # Get balance from vendor or supplier profile
        balance = 0.0
        if current_user["role"] == "vendor":
            vendor_result = await db.execute(
                select(VendorProfile).where(VendorProfile.user_profile_id == user_profile.id)
            )
            vendor_profile = vendor_result.scalar_one_or_none()
            if vendor_profile:
                balance = vendor_profile.balance
        elif current_user["role"] == "supplier":
            supplier_result = await db.execute(
                select(SupplierProfile).where(SupplierProfile.user_profile_id == user_profile.id)
            )
            supplier_profile = supplier_result.scalar_one_or_none()
            if supplier_profile:
                balance = supplier_profile.balance
        
        return BalanceResponse(balance=balance)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting balance: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve balance"
        )


@router.post("/create-order", response_model=PaymentOrderResponse)
async def create_payment_order(
    payment_data: PaymentCreate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_profile_write)
):
    """
    Create a Razorpay order for adding balance
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
        
        # Validate user role
        if current_user["role"] not in ["vendor", "supplier"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only vendors and suppliers can add balance"
            )
        
        # Create Razorpay order
        amount_in_paisa = int(payment_data.amount * 100)  # Convert to paisa
        razorpay_order = razorpay_client.order.create({
            "amount": amount_in_paisa,
            "currency": payment_data.currency,
            "payment_capture": 1,
            "notes": {
                "user_id": str(user_profile.id),
                "description": payment_data.description or "Add balance to account"
            }
        })
        
        # Create payment record
        payment = Payment(
            user_id=user_profile.id,
            amount=payment_data.amount,
            currency=payment_data.currency,
            razorpay_order_id=razorpay_order["id"],
            status="pending",
            description=payment_data.description or "Add balance to account"
        )
        
        db.add(payment)
        await db.commit()
        await db.refresh(payment)
        
        return PaymentOrderResponse(
            order_id=razorpay_order["id"],
            amount=payment_data.amount,
            currency=payment_data.currency,
            key=os.getenv("RAZORPAY_KEY_ID", "rzp_test_your_key_id"),
            payment_id=str(payment.id)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating payment order: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create payment order"
        )


@router.post("/verify-payment", response_model=PaymentVerificationResponse)
async def verify_payment(
    verification_data: PaymentVerification,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_profile_write)
):
    """
    Verify Razorpay payment and add balance to user account
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
        
        # Get payment record
        payment_result = await db.execute(
            select(Payment).where(
                Payment.razorpay_order_id == verification_data.razorpay_order_id,
                Payment.user_id == user_profile.id
            )
        )
        payment = payment_result.scalar_one_or_none()
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment record not found"
            )
        
        if payment.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment already processed"
            )
        
        # Verify signature
        razorpay_key_secret = os.getenv("RAZORPAY_KEY_SECRET", "your_key_secret")
        generated_signature = hmac.new(
            razorpay_key_secret.encode(),
            f"{verification_data.razorpay_order_id}|{verification_data.razorpay_payment_id}".encode(),
            hashlib.sha256
        ).hexdigest()
        
        if generated_signature != verification_data.razorpay_signature:
            payment.status = "failed"
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid payment signature"
            )
        
        # Update payment record
        payment.razorpay_payment_id = verification_data.razorpay_payment_id
        payment.razorpay_signature = verification_data.razorpay_signature
        payment.status = "completed"
        
        # Add balance to user account
        if current_user["role"] == "vendor":
            vendor_result = await db.execute(
                select(VendorProfile).where(VendorProfile.user_profile_id == user_profile.id)
            )
            vendor_profile = vendor_result.scalar_one_or_none()
            if vendor_profile:
                vendor_profile.balance += payment.amount
        elif current_user["role"] == "supplier":
            supplier_result = await db.execute(
                select(SupplierProfile).where(SupplierProfile.user_profile_id == user_profile.id)
            )
            supplier_profile = supplier_result.scalar_one_or_none()
            if supplier_profile:
                supplier_profile.balance += payment.amount
        
        await db.commit()
        
        # Get updated balance
        new_balance = 0.0
        if current_user["role"] == "vendor" and vendor_profile:
            new_balance = vendor_profile.balance
        elif current_user["role"] == "supplier" and supplier_profile:
            new_balance = supplier_profile.balance
        
        return PaymentVerificationResponse(
            message="Payment verified successfully",
            amount_added=payment.amount,
            new_balance=new_balance,
            payment_id=verification_data.razorpay_payment_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying payment: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify payment"
        )


@router.get("/history", response_model=List[PaymentResponse])
async def get_payment_history(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_profile_read)
):
    """
    Get user's payment history
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
        
        # Get payment history
        payments_result = await db.execute(
            select(Payment)
            .where(Payment.user_id == user_profile.id)
            .order_by(Payment.created_at.desc())
        )
        payments = payments_result.scalars().all()
        
        return [safe_model_validate(PaymentResponse, payment) for payment in payments]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting payment history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve payment history"
        )

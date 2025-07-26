from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentMethod(str, Enum):
    RAZORPAY = "razorpay"
    MANUAL = "manual"


class PaymentCreate(BaseModel):
    amount: float = Field(gt=0, description="Amount to add to balance")
    currency: str = Field(default="INR", description="Currency code")
    description: Optional[str] = Field(None, max_length=255, description="Payment description")


class PaymentResponse(BaseModel):
    id: str
    user_id: str
    amount: float
    currency: str
    payment_method: str
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    status: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PaymentVerification(BaseModel):
    razorpay_order_id: str = Field(description="Razorpay order ID")
    razorpay_payment_id: str = Field(description="Razorpay payment ID")
    razorpay_signature: str = Field(description="Razorpay signature for verification")


class BalanceResponse(BaseModel):
    balance: float = Field(description="Current balance amount")
    currency: str = Field(default="INR", description="Currency code")


class PaymentOrderResponse(BaseModel):
    order_id: str = Field(description="Razorpay order ID")
    amount: float = Field(description="Payment amount")
    currency: str = Field(description="Currency code")
    key: str = Field(description="Razorpay public key")
    payment_id: str = Field(description="Internal payment record ID")


class PaymentVerificationResponse(BaseModel):
    message: str = Field(description="Success message")
    amount_added: float = Field(description="Amount added to balance")
    new_balance: float = Field(description="Updated balance")
    payment_id: str = Field(description="Razorpay payment ID")

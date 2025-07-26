from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class OrderType(str, Enum):
    BUY_NOW = "buy_now"
    BUY_NOW_PAY_LATER = "buy_now_pay_later"
    BULK_ORDER = "bulk_order"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class OrderStatus(str, Enum):
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class OrderCreate(BaseModel):
    product_id: str
    quantity: int = Field(gt=0)
    order_type: OrderType
    delivery_address: Optional[str] = None
    notes: Optional[str] = None
    bulk_order_window_id: Optional[str] = None


class OrderResponse(BaseModel):
    id: str
    buyer_id: str
    seller_id: str
    product_id: str
    quantity: int
    price_per_unit: float
    total_amount: float
    order_type: str
    payment_status: str
    due_date: Optional[datetime] = None
    bulk_order_window_id: Optional[str] = None
    order_status: str
    delivery_address: Optional[str] = None
    estimated_delivery: Optional[datetime] = None
    actual_delivery: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class OrderWithDetailsResponse(OrderResponse):
    buyer_name: Optional[str] = None
    seller_name: Optional[str] = None
    product_name: Optional[str] = None
    product_unit: Optional[str] = None


class OrderListResponse(BaseModel):
    orders: List[OrderWithDetailsResponse]
    page: int
    limit: int
    total: int


class BulkOrderWindowCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    window_duration_hours: int = Field(default=3, gt=0, le=24)


class BulkOrderWindowResponse(BaseModel):
    id: str
    creator_id: str
    title: str
    description: Optional[str] = None
    window_start_time: datetime
    window_end_time: datetime
    status: str
    total_participants: int
    total_amount: float
    created_at: datetime
    updated_at: datetime


class BulkOrderWindowWithOrdersResponse(BulkOrderWindowResponse):
    orders: List[OrderWithDetailsResponse]
    creator_name: Optional[str] = None


class BulkOrderWindowListResponse(BaseModel):
    windows: List[BulkOrderWindowResponse]
    page: int
    limit: int
    total: int


class PaymentCreate(BaseModel):
    amount: float = Field(gt=0)
    currency: str = Field(default="INR")
    description: Optional[str] = None


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
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class BalanceResponse(BaseModel):
    balance: float
    currency: str = "INR"


class PendingPaymentResponse(BaseModel):
    order_id: str
    product_name: str
    seller_name: str
    total_amount: float
    due_date: datetime
    days_remaining: int

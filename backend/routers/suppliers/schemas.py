from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class OrderResponseForSupplier(BaseModel):
    id: str
    buyer_id: str
    buyer_name: str
    product_id: str
    product_name: str
    quantity: int
    price_per_unit: float
    total_amount: float
    order_type: str
    payment_status: str
    order_status: str
    due_date: Optional[datetime] = None
    delivery_address: Optional[str] = None
    estimated_delivery: Optional[datetime] = None
    actual_delivery: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class SubscriptionResponse(BaseModel):
    id: str
    supplier_id: str
    supplier_name: str
    company_name: str
    created_at: datetime

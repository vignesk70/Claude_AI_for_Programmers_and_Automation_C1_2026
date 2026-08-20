from datetime import datetime
from typing import Optional
from enum import Enum

from pydantic import BaseModel, Field


class OrderStatus(str, Enum):
    """Order status values."""
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class OrderCreate(BaseModel):
    """Schema for creating a new order."""
    customer_name: str = Field(min_length=1, max_length=100)
    customer_email: str
    product_name: str = Field(min_length=1, max_length=200)
    quantity: int = Field(gt=0)
    price: float = Field(gt=0)
    status: OrderStatus = OrderStatus.PENDING
    notes: Optional[str] = None


class OrderUpdate(BaseModel):
    """Schema for updating an existing order."""
    status: Optional[OrderStatus] = None
    notes: Optional[str] = None


class OrderResponse(BaseModel):
    """Schema for order responses."""
    id: str
    customer_name: str
    customer_email: str
    product_name: str
    quantity: int
    price: float
    status: OrderStatus
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

from datetime import datetime
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db import get_db
from app.schemas.orders import OrderCreate, OrderResponse, OrderUpdate, OrderStatus

router = APIRouter(tags=["Orders"])


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")


@router.post("/orders", response_model=OrderResponse)
async def create_order(order: OrderCreate):
    """Create a new order."""
    db = get_db()
    
    now = datetime.utcnow()
    order_doc = {
        "customer_name": order.customer_name,
        "customer_email": order.customer_email,
        "product_name": order.product_name,
        "quantity": order.quantity,
        "price": order.price,
        "status": order.status.value,
        "notes": order.notes,
        "created_at": now,
        "updated_at": now,
    }
    
    result = db.orders.insert_one(order_doc)
    order_doc["id"] = str(result.inserted_id)
    
    return OrderResponse(**order_doc)


@router.get("/orders", response_model=list[OrderResponse])
async def list_orders(status: Optional[OrderStatus] = None, limit: int = 50):
    """List orders with optional status filter."""
    db = get_db()
    
    query = {}
    if status:
        query["status"] = status.value
    
    orders = list(db.orders.find(query).sort("created_at", -1).limit(limit))
    
    return [
        OrderResponse(
            id=str(order["_id"]),
            customer_name=order["customer_name"],
            customer_email=order["customer_email"],
            product_name=order["product_name"],
            quantity=order["quantity"],
            price=order["price"],
            status=OrderStatus(order["status"]),
            notes=order.get("notes"),
            created_at=order["created_at"],
            updated_at=order["updated_at"],
        )
        for order in orders
    ]


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(order_id: str):
    """Get a specific order by ID."""
    db = get_db()
    
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=400, detail="Invalid order ID")
    
    order = db.orders.find_one({"_id": ObjectId(order_id)})
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return OrderResponse(
        id=str(order["_id"]),
        customer_name=order["customer_name"],
        customer_email=order["customer_email"],
        product_name=order["product_name"],
        quantity=order["quantity"],
        price=order["price"],
        status=OrderStatus(order["status"]),
        notes=order.get("notes"),
        created_at=order["created_at"],
        updated_at=order["updated_at"],
    )


@router.patch("/orders/{order_id}", response_model=OrderResponse)
async def update_order(order_id: str, update: OrderUpdate):
    """Update an order's status or notes."""
    db = get_db()
    
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=400, detail="Invalid order ID")
    
    update_data = {}
    if update.status is not None:
        update_data["status"] = update.status.value
    if update.notes is not None:
        update_data["notes"] = update.notes
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")
    
    update_data["updated_at"] = datetime.utcnow()
    
    result = db.orders.find_one_and_update(
        {"_id": ObjectId(order_id)},
        {"$set": update_data},
        return_document=True,
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return OrderResponse(
        id=str(result["_id"]),
        customer_name=result["customer_name"],
        customer_email=result["customer_email"],
        product_name=result["product_name"],
        quantity=result["quantity"],
        price=result["price"],
        status=OrderStatus(result["status"]),
        notes=result.get("notes"),
        created_at=result["created_at"],
        updated_at=result["updated_at"],
    )


@router.delete("/orders/{order_id}")
async def delete_order(order_id: str):
    """Delete an order."""
    db = get_db()
    
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=400, detail="Invalid order ID")
    
    result = db.orders.delete_one({"_id": ObjectId(order_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return {"message": "Order deleted successfully"}

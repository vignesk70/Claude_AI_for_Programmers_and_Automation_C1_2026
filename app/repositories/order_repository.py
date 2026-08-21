from typing import Any

from app.schemas.orders import OrderContext, OrderItem, OrderStatus

# Projection is an allowlist of fields the repository returns to the app.
ORDER_CONTEXT_PROJECTION = {
    "_id": 0,
    "order_id": 1,
    "status": 1,
    "items": 1,
    "estimated_delivery": 1,
    "delivered_at": 1,
}


class OrderRepository:
    def __init__(
        self,
        database: Any,
    ) -> None:
        # Repositories own database access; services do not.
        self.collection = database.orders

    async def get_order_for_customer(
        self,
        customer_id: str,
        order_id: str,
    ) -> OrderContext | None:
        """Look up an order scoped to a specific customer."""
        doc = self.collection.find_one(
            {"customer_id": customer_id, "order_id": order_id},
            projection=ORDER_CONTEXT_PROJECTION,
        )
        if doc is None:
            return None
        return OrderContext(
            order_id=doc["order_id"],
            status=OrderStatus(doc["status"]),
            estimated_delivery=doc.get("estimated_delivery"),
            delivered_at=doc.get("delivered_at"),
        )

    async def get_order_by_id(self, order_id: str) -> dict | None:
        """Look up an order by its MongoDB _id."""
        from bson import ObjectId

        if not ObjectId.is_valid(order_id):
            return None
        return self.collection.find_one({"_id": ObjectId(order_id)})

    async def get_order_by_order_id(self, order_id: str) -> dict | None:
        """Look up an order by its business order_id."""
        return self.collection.find_one({"order_id": order_id})

    async def list_orders(
        self,
        customer_id: str | None = None,
        order_id: str | None = None,
        status: OrderStatus | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """List orders with optional filters, sorted by order_date descending."""
        query = {}
        if customer_id is not None:
            query["customer_id"] = customer_id
        if order_id is not None:
            query["order_id"] = order_id
        if status is not None:
            query["status"] = status.value
        return list(self.collection.find(query).sort("order_date", -1).limit(limit))

    async def create_order(self, order_doc: dict) -> str:
        """Insert a new order and return its MongoDB _id as a string."""
        result = self.collection.insert_one(order_doc)
        return str(result.inserted_id)

    async def update_order(self, order_id: str, update_data: dict) -> dict | None:
        """Update an order by business order_id and return the updated document."""
        return self.collection.find_one_and_update(
            {"order_id": order_id},
            {"$set": update_data},
            return_document=True,
        )

    async def delete_order(self, order_id: str) -> bool:
        """Delete an order by business order_id. Returns True if deleted, False if not found."""
        result = self.collection.delete_one({"order_id": order_id})
        return result.deleted_count > 0

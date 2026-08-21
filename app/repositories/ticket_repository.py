from typing import Any

from app.schemas.enums import TicketStatus


class TicketRepository:
    """Data access layer for support tickets in MongoDB."""

    def __init__(self, database: Any) -> None:
        self.collection = database.tickets

    async def generate_ticket_id(self) -> str:
        """Generate the next sequential ticket ID (e.g. TKT-0001)."""
        last_ticket = self.collection.find_one(
            {}, sort=[("created_at", -1)], projection={"ticket_id": 1}
        )
        if last_ticket is None:
            return "TKT-0001"
        last_id = last_ticket["ticket_id"]
        next_num = int(last_id.split("-")[1]) + 1
        return f"TKT-{next_num:04d}"

    async def create_ticket(self, ticket_doc: dict) -> str:
        """Insert a new ticket document and return its ticket_id."""
        self.collection.insert_one(ticket_doc)
        return ticket_doc["ticket_id"]

    async def get_ticket(self, ticket_id: str) -> dict | None:
        """Look up a ticket by its ticket_id."""
        return self.collection.find_one({"ticket_id": ticket_id})

    async def get_ticket_for_customer(self, ticket_id: str, customer_id: str) -> dict | None:
        """Look up a ticket scoped to a specific customer (ownership check)."""
        return self.collection.find_one(
            {"ticket_id": ticket_id, "customer_id": customer_id}
        )

    async def list_tickets(
        self,
        customer_id: str | None = None,
        status: TicketStatus | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """List tickets with optional filters, sorted by created_at descending."""
        query: dict[str, Any] = {}
        if customer_id is not None:
            query["customer_id"] = customer_id
        if status is not None:
            query["status"] = status.value
        return list(self.collection.find(query).sort("created_at", -1).limit(limit))

    async def add_message(self, ticket_id: str, message: dict) -> dict | None:
        """Append a message to a ticket's conversation history and update timestamp."""
        from datetime import datetime

        return self.collection.find_one_and_update(
            {"ticket_id": ticket_id},
            {
                "$push": {"messages": message},
                "$set": {"updated_at": datetime.utcnow()},
            },
            return_document=True,
        )

    async def update_ticket(self, ticket_id: str, update_data: dict) -> dict | None:
        """Update ticket fields and return the updated document."""
        from datetime import datetime

        update_data["updated_at"] = datetime.utcnow()
        return self.collection.find_one_and_update(
            {"ticket_id": ticket_id},
            {"$set": update_data},
            return_document=True,
        )

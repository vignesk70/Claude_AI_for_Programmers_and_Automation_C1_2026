from fastapi import APIRouter, HTTPException

from app.db import get_db
from app.repositories.order_repository import OrderRepository
from app.repositories.ticket_repository import TicketRepository
from app.schemas.enums import TicketStatus
from app.schemas.support import SupportRequest, SupportResponse
from app.schemas.tickets import (
    CreateTicketRequest,
    FollowUpRequest,
    FollowUpResponse,
    TicketResponse,
)
from app.services.support import (
    create_support_ticket,
    follow_up_on_ticket,
    handle_support_request,
)

router = APIRouter(tags=["Support"])


def _get_ticket_repo() -> TicketRepository:
    return TicketRepository(get_db())


def _get_order_repo() -> OrderRepository:
    return OrderRepository(get_db())


# ---------------------------------------------------------------------------
# Ticket-based endpoints
# ---------------------------------------------------------------------------


@router.post("/tickets", response_model=TicketResponse)
async def create_ticket(request: CreateTicketRequest) -> TicketResponse:
    """Create a new support ticket with an initial AI-powered response."""
    ticket_repo = _get_ticket_repo()
    order_repo = _get_order_repo()
    return await create_support_ticket(request, ticket_repo, order_repo)


@router.post("/tickets/followup", response_model=FollowUpResponse)
async def ticket_followup(request: FollowUpRequest) -> FollowUpResponse:
    """Follow up on an existing ticket with conversation history context."""
    ticket_repo = _get_ticket_repo()
    order_repo = _get_order_repo()
    try:
        return await follow_up_on_ticket(request, ticket_repo, order_repo)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/tickets/{ticket_id}", response_model=TicketResponse)
async def get_ticket(ticket_id: str, customer_id: str) -> TicketResponse:
    """Get a ticket by ID scoped to a customer (ownership check)."""
    ticket_repo = _get_ticket_repo()
    doc = await ticket_repo.get_ticket_for_customer(ticket_id, customer_id)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    return _doc_to_ticket_response(doc)


@router.get("/tickets", response_model=list[TicketResponse])
async def list_tickets(
    customer_id: str,
    status: TicketStatus | None = None,
    limit: int = 50,
) -> list[TicketResponse]:
    """List tickets for a customer with optional status filter."""
    ticket_repo = _get_ticket_repo()
    docs = await ticket_repo.list_tickets(customer_id=customer_id, status=status, limit=limit)
    return [_doc_to_ticket_response(doc) for doc in docs]


# ---------------------------------------------------------------------------
# Main chat endpoint (creates tickets automatically)
# ---------------------------------------------------------------------------


@router.post("/support", response_model=SupportResponse)
async def support_chat(request: SupportRequest) -> SupportResponse:
    """Unified support chat — creates a ticket on first message, follows up on subsequent ones.

    - First message: send customer_id + message → returns ticket_id + AI response
    - Follow-up: send ticket_id + customer_id + message → AI responds with full history
    """
    ticket_repo = _get_ticket_repo()
    order_repo = _get_order_repo()
    try:
        return await handle_support_request(request, ticket_repo, order_repo)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _doc_to_ticket_response(doc: dict) -> TicketResponse:
    """Convert a MongoDB ticket document to a TicketResponse."""
    from app.schemas.tickets import ConversationMessage

    messages = [
        ConversationMessage(
            role=msg["role"],
            content=msg["content"],
            order_context=msg.get("order_context"),
            timestamp=msg["timestamp"],
        )
        for msg in doc.get("messages", [])
    ]
    return TicketResponse(
        ticket_id=doc["ticket_id"],
        customer_id=doc["customer_id"],
        order_id=doc.get("order_id"),
        subject=doc["subject"],
        status=TicketStatus(doc["status"]),
        messages=messages,
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )

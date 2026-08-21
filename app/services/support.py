import json
import re
from datetime import datetime

from app.prompts.support import SUPPORT_ASSISTANT_SYSTEM_PROMPT
from app.repositories.order_repository import OrderRepository
from app.repositories.ticket_repository import TicketRepository
from app.schemas.enums import TicketStatus
from app.schemas.support import SupportRequest, SupportResponse
from app.schemas.tickets import (
    ConversationMessage,
    CreateTicketRequest,
    FollowUpRequest,
    FollowUpResponse,
    TicketResponse,
)
from app.services.llm import chat


# Regex patterns for ID extraction (instant, no LLM call needed)
_ORDER_ID_PATTERN = re.compile(r'\bORD-\d{3,5}\b', re.IGNORECASE)
_CUSTOMER_ID_PATTERN = re.compile(r'\bCUST-\d{2,5}\b', re.IGNORECASE)
_TICKET_ID_PATTERN = re.compile(r'\bTKT-\d{3,5}\b', re.IGNORECASE)


def _extract_ids(message: str) -> dict:
    """Extract order_id, customer_id, and ticket_id from the customer message using regex."""
    order_match = _ORDER_ID_PATTERN.search(message)
    customer_match = _CUSTOMER_ID_PATTERN.search(message)
    ticket_match = _TICKET_ID_PATTERN.search(message)

    return {
        "order_id": order_match.group(0).upper() if order_match else None,
        "customer_id": customer_match.group(0).upper() if customer_match else None,
        "ticket_id": ticket_match.group(0).upper() if ticket_match else None,
    }


async def _resolve_order_context(
    order_id: str | None,
    customer_id: str,
    order_repo: OrderRepository,
) -> tuple[dict | None, str]:
    """Build order context for the LLM prompt (requires both IDs for ownership check)."""
    if not order_id or not customer_id:
        return None, ""

    order_doc = await order_repo.get_order_for_customer(customer_id, order_id)
    if order_doc is None:
        return None, ""

    order_context = {
        "order_id": order_doc.order_id,
        "status": order_doc.status.value,
        "estimated_delivery": str(order_doc.estimated_delivery),
        "delivered_at": str(order_doc.delivered_at),
    }
    context_text = f"\n\nOrder Context:\n{json.dumps(order_context, indent=2)}"
    return order_context, context_text


def _parse_llm_response(response_text: str) -> dict:
    """Parse the LLM JSON response with fallback."""
    try:
        return json.loads(response_text)
    except (json.JSONDecodeError, AttributeError):
        return {"needs_info": False, "response": response_text}


# ---------------------------------------------------------------------------
# Unified chat → ticket handler (the main entry point)
# ---------------------------------------------------------------------------

async def handle_support_request(
    request: SupportRequest,
    ticket_repo: TicketRepository,
    order_repo: OrderRepository,
) -> SupportResponse:
    """Handle a support request — creates a ticket on first message, follows up on subsequent ones.

    All IDs are resolved by priority: explicit request field > extracted from message text.
    - If ticket_id is resolved → follow-up on existing ticket.
    - Otherwise → create a new ticket.
    """

    # Extract all IDs from message text
    extracted = _extract_ids(request.message)

    # Resolve IDs: explicit > extracted from message
    resolved_customer_id = request.customer_id or extracted.get("customer_id")
    resolved_order_id = request.order_id or extracted.get("order_id")
    resolved_ticket_id = request.ticket_id or extracted.get("ticket_id")

    # Build a lightweight copy with resolved IDs for downstream functions
    request.customer_id = resolved_customer_id
    request.order_id = resolved_order_id
    request.ticket_id = resolved_ticket_id

    if resolved_ticket_id:
        return await _follow_up(request, ticket_repo, order_repo)
    else:
        return await _create_ticket_and_respond(request, ticket_repo, order_repo)


# ---------------------------------------------------------------------------
# New ticket creation (first message)
# ---------------------------------------------------------------------------

async def _create_ticket_and_respond(
    request: SupportRequest,
    ticket_repo: TicketRepository,
    order_repo: OrderRepository,
) -> SupportResponse:
    """Create a new ticket, get AI response, persist everything.

    Assumes request.customer_id, request.order_id are already resolved by handle_support_request.
    """

    customer_id = request.customer_id
    order_id = request.order_id

    # Order context (requires both IDs)
    order_context, context_text = await _resolve_order_context(
        order_id, customer_id, order_repo,
    )

    # Call LLM
    result = await chat(
        prompt=request.message + context_text,
        system_prompt=SUPPORT_ASSISTANT_SYSTEM_PROMPT,
        response_format="json_object",
    )
    parsed = _parse_llm_response(result["response"])

    now = datetime.utcnow()
    ticket_id = await ticket_repo.generate_ticket_id()

    # Auto-generate subject from the message if not provided
    subject = request.subject or request.message[:80]

    # Build messages
    user_message = ConversationMessage(
        role="user",
        content=request.message,
        order_context=order_context,
        timestamp=now,
    )
    assistant_content = parsed.get("response") or parsed.get("question", "")
    assistant_message = ConversationMessage(
        role="assistant",
        content=assistant_content,
        timestamp=now,
    )

    # Persist ticket
    ticket_doc = {
        "ticket_id": ticket_id,
        "customer_id": customer_id,
        "order_id": order_id,
        "subject": subject,
        "status": TicketStatus.OPEN.value,
        "messages": [
            user_message.model_dump(mode="json"),
            assistant_message.model_dump(mode="json"),
        ],
        "created_at": now,
        "updated_at": now,
    }
    await ticket_repo.create_ticket(ticket_doc)

    return SupportResponse(
        ticket_id=ticket_id,
        needs_info=parsed.get("needs_info", False),
        question=parsed.get("question"),
        info_type=parsed.get("info_type"),
        response=parsed.get("response"),
        action=parsed.get("action"),
        order_context=order_context,
    )


# ---------------------------------------------------------------------------
# Follow-up on existing ticket
# ---------------------------------------------------------------------------

async def _follow_up(
    request: SupportRequest,
    ticket_repo: TicketRepository,
    order_repo: OrderRepository,
) -> SupportResponse:
    """Follow up on an existing ticket with full conversation history.

    Assumes request.ticket_id, request.customer_id, request.order_id
    are already resolved by handle_support_request.
    """

    customer_id = request.customer_id
    ticket_id = request.ticket_id

    # If customer_id wasn't resolved, try to get it from the ticket directly
    if not customer_id:
        ticket_doc = await ticket_repo.get_ticket(ticket_id)
        if ticket_doc is None:
            raise ValueError(f"Ticket {ticket_id} not found")
        customer_id = ticket_doc.get("customer_id")
        request.customer_id = customer_id
    else:
        # Verify ticket exists and belongs to this customer
        ticket_doc = await ticket_repo.get_ticket_for_customer(ticket_id, customer_id)
        if ticket_doc is None:
            raise ValueError(f"Ticket {ticket_id} not found for customer {customer_id}")

    # Resolve order_id: request > ticket's stored value
    order_id = request.order_id or ticket_doc.get("order_id")
    request.order_id = order_id

    # Order context
    order_context, context_text = await _resolve_order_context(
        order_id, customer_id, order_repo,
    )

    # Build conversation history from stored messages
    history = [
        {"role": msg["role"], "content": msg["content"]}
        for msg in ticket_doc.get("messages", [])
    ]

    # Call LLM with full conversation context
    result = await chat(
        prompt=request.message + context_text,
        system_prompt=SUPPORT_ASSISTANT_SYSTEM_PROMPT,
        response_format="json_object",
        conversation_history=history,
    )
    parsed = _parse_llm_response(result["response"])

    now = datetime.utcnow()

    # Save user message
    user_msg = {
        "role": "user",
        "content": request.message,
        "order_context": order_context,
        "timestamp": now,
    }
    await ticket_repo.add_message(request.ticket_id, user_msg)

    # Save assistant message
    assistant_content = parsed.get("response") or parsed.get("question", "")
    assistant_msg = {
        "role": "assistant",
        "content": assistant_content,
        "timestamp": now,
    }
    await ticket_repo.add_message(request.ticket_id, assistant_msg)

    # Update status to in_progress if still open
    if ticket_doc.get("status") == TicketStatus.OPEN.value:
        await ticket_repo.update_ticket(
            request.ticket_id, {"status": TicketStatus.IN_PROGRESS.value}
        )

    return SupportResponse(
        ticket_id=request.ticket_id,
        needs_info=parsed.get("needs_info", False),
        question=parsed.get("question"),
        info_type=parsed.get("info_type"),
        response=parsed.get("response"),
        action=parsed.get("action"),
        order_context=order_context,
    )


# ---------------------------------------------------------------------------
# Dedicated ticket endpoints (used by /api/tickets routes)
# ---------------------------------------------------------------------------

async def create_support_ticket(
    request: CreateTicketRequest,
    ticket_repo: TicketRepository,
    order_repo: OrderRepository,
) -> TicketResponse:
    """Create a new support ticket via the dedicated /api/tickets endpoint."""

    extracted = _extract_ids(request.message)
    order_id = request.order_id or extracted.get("order_id")
    customer_id = request.customer_id

    order_context, context_text = await _resolve_order_context(
        order_id, customer_id, order_repo,
    )

    result = await chat(
        prompt=request.message + context_text,
        system_prompt=SUPPORT_ASSISTANT_SYSTEM_PROMPT,
        response_format="json_object",
    )
    parsed = _parse_llm_response(result["response"])

    now = datetime.utcnow()
    ticket_id = await ticket_repo.generate_ticket_id()

    user_message = ConversationMessage(
        role="user", content=request.message,
        order_context=order_context, timestamp=now,
    )
    assistant_message = ConversationMessage(
        role="assistant",
        content=parsed.get("response") or parsed.get("question", ""),
        timestamp=now,
    )

    ticket_doc = {
        "ticket_id": ticket_id,
        "customer_id": customer_id,
        "order_id": order_id,
        "subject": request.subject,
        "status": TicketStatus.OPEN.value,
        "messages": [
            user_message.model_dump(mode="json"),
            assistant_message.model_dump(mode="json"),
        ],
        "created_at": now,
        "updated_at": now,
    }
    await ticket_repo.create_ticket(ticket_doc)

    return TicketResponse(
        ticket_id=ticket_id,
        customer_id=customer_id,
        order_id=order_id,
        subject=request.subject,
        status=TicketStatus.OPEN,
        messages=[user_message, assistant_message],
        created_at=now,
        updated_at=now,
    )


async def follow_up_on_ticket(
    request: FollowUpRequest,
    ticket_repo: TicketRepository,
    order_repo: OrderRepository,
) -> FollowUpResponse:
    """Follow up via the dedicated /api/tickets/followup endpoint."""

    ticket_doc = await ticket_repo.get_ticket_for_customer(
        request.ticket_id, request.customer_id,
    )
    if ticket_doc is None:
        raise ValueError(f"Ticket {request.ticket_id} not found for customer {request.customer_id}")

    order_id = request.order_id or ticket_doc.get("order_id")
    extracted = _extract_ids(request.message)
    order_id = order_id or extracted.get("order_id")
    customer_id = request.customer_id

    order_context, context_text = await _resolve_order_context(
        order_id, customer_id, order_repo,
    )

    history = [
        {"role": msg["role"], "content": msg["content"]}
        for msg in ticket_doc.get("messages", [])
    ]

    result = await chat(
        prompt=request.message + context_text,
        system_prompt=SUPPORT_ASSISTANT_SYSTEM_PROMPT,
        response_format="json_object",
        conversation_history=history,
    )
    parsed = _parse_llm_response(result["response"])

    now = datetime.utcnow()

    await ticket_repo.add_message(request.ticket_id, {
        "role": "user", "content": request.message,
        "order_context": order_context, "timestamp": now,
    })

    assistant_content = parsed.get("response") or parsed.get("question", "")
    updated_doc = await ticket_repo.add_message(request.ticket_id, {
        "role": "assistant", "content": assistant_content, "timestamp": now,
    })

    if ticket_doc.get("status") == TicketStatus.OPEN.value:
        await ticket_repo.update_ticket(
            request.ticket_id, {"status": TicketStatus.IN_PROGRESS.value}
        )

    return FollowUpResponse(
        ticket_id=request.ticket_id,
        status=TicketStatus.IN_PROGRESS if ticket_doc.get("status") == TicketStatus.OPEN.value else TicketStatus(ticket_doc["status"]),
        assistant_message=assistant_content,
        order_context=order_context,
        action=parsed.get("action"),
        needs_info=parsed.get("needs_info", False),
        question=parsed.get("question"),
    )

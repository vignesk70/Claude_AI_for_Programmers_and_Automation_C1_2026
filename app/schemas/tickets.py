from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.enums import Priority, TicketCategory, TicketStatus


class ConversationMessage(BaseModel):
    """A single message in a ticket conversation."""
    role: str = Field(pattern="^(user|assistant|system)$")
    content: str
    order_context: Optional[dict] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CreateTicketRequest(BaseModel):
    """Request to create a new support ticket."""
    customer_id: str = Field(min_length=1)
    subject: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=2000)
    order_id: Optional[str] = None


class FollowUpRequest(BaseModel):
    """Request to follow up on an existing ticket."""
    ticket_id: str = Field(min_length=1)
    customer_id: str = Field(min_length=1)
    message: str = Field(min_length=1, max_length=2000)
    order_id: Optional[str] = None


class TicketResponse(BaseModel):
    """Full ticket returned from the API."""
    ticket_id: str
    customer_id: str
    order_id: Optional[str] = None
    subject: str
    status: TicketStatus
    category: Optional[TicketCategory] = None
    priority: Priority = Priority.MEDIUM
    messages: list[ConversationMessage]
    created_at: datetime
    updated_at: datetime


class FollowUpResponse(BaseModel):
    """Response after a follow-up message."""
    ticket_id: str
    status: TicketStatus
    assistant_message: str
    order_context: Optional[dict] = None
    action: Optional[str] = None
    needs_info: bool = False
    question: Optional[str] = None

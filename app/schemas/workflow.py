from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class WorkflowStep(str, Enum):
    """Steps the deterministic workflow can execute."""

    ANALYSIS = "ANALYSIS"
    ORDER_LOOKUP = "ORDER_LOOKUP"
    FAQ_LOOKUP = "FAQ_LOOKUP"
    DATABASE_INSERT = "DATABASE_INSERT"
    RESPONSE_GENERATION = "RESPONSE_GENERATION"
    DATABASE_UPDATE = "DATABASE_UPDATE"


class ProcessTicketRequest(BaseModel):
    """Incoming request for the deterministic ticket workflow."""

    customer_message: str = Field(min_length=5, max_length=5000)
    customer_id: str = Field(min_length=3, max_length=50)
    order_id: Optional[str] = Field(default=None, min_length=3, max_length=50)
    subject: Optional[str] = Field(default=None, max_length=200)


class ProcessTicketResponse(BaseModel):
    """Result of the deterministic ticket workflow."""

    ticket_id: str
    final_status: str
    executed_steps: list[WorkflowStep]
    analysis: dict
    order_context: Optional[dict] = None
    faq_sources: list[dict] = Field(default_factory=list)
    draft_response: str
    requires_human_review: bool
    human_review_reason: Optional[str] = None

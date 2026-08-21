from typing import Optional

from pydantic import BaseModel, Field


class SupportRequest(BaseModel):
    """Support conversation request.

    All IDs (customer_id, order_id, ticket_id) can be provided explicitly
    OR extracted automatically from the message text:
      - CUST-XXX  → customer_id
      - ORD-XXXX  → order_id
      - TKT-XXXX  → ticket_id (triggers follow-up on existing ticket)

    Examples:
      First message:  {"message": "Hi CUST-101 here, order ORD-1001 hasn't arrived"}
      Follow-up:      {"message": "Regarding TKT-0001, I still need a refund"}
    """
    message: str = Field(min_length=1, max_length=2000)
    customer_id: Optional[str] = None
    ticket_id: Optional[str] = None
    order_id: Optional[str] = None
    subject: Optional[str] = Field(default=None, max_length=200)


class SupportResponse(BaseModel):
    """Support assistant response."""
    ticket_id: str
    needs_info: bool = False
    question: Optional[str] = None
    info_type: Optional[str] = None
    response: Optional[str] = None
    action: Optional[str] = None
    order_context: Optional[dict] = None

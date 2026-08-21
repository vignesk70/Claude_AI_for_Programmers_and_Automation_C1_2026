from pydantic import BaseModel, Field

from app.schemas.enums import TicketCategory


class FAQSource(BaseModel):
    """Approved FAQ record retrieved from MongoDB."""
    faq_id: str = Field(min_length=3, max_length=50)
    category: TicketCategory
    question: str = Field(min_length=3, max_length=500)
    answer: str = Field(min_length=3, max_length=2000)


class FAQAnswerDecision(BaseModel):
    """LLM must state both its answer and whether the supplied sources support it."""
    answer: str = Field(min_length=1, max_length=2000)
    supported_by_sources: bool


class FAQAskRequest(BaseModel):
    """Request to ask a question using approved FAQ sources."""
    question: str = Field(min_length=5, max_length=1000)


class FAQAskResponse(BaseModel):
    """Response with answer, sources used, and human review flag."""
    answer: str = Field(min_length=1, max_length=2000)
    sources: list[FAQSource] = Field(default_factory=list)
    requires_human_review: bool

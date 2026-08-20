from typing import Literal, Optional
from app.prompts import summarize
from app.schemas.enums import TicketCategory, Sentiment, Priority

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["healthy"] = "ok"


class ChatRequest(BaseModel):
    prompt: str
    system_prompt: Optional[str] = ""
    max_tokens: Optional[int] = None
    response_format: Optional[Literal["text", "json_object"]] = "text"


class ChatResponse(BaseModel):
    response: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None


class SummarizeRequest(BaseModel):
    prompt: str
    max_tokens: Optional[int] = None
    response_format: Optional[Literal["text", "json_object"]] = "json_object"


class CategorizeRequest(BaseModel):
    prompt: str
    max_tokens: Optional[int] = None


class CategorizeResponse(BaseModel):
    category: str
    summary: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None


class AnalyseTicketRequest(BaseModel):
    """Support ticket analysis request."""
    text: str = Field(min_length=5, max_length=5000)


class TicketAnalysis(BaseModel):
    """Comprehensive support ticket analysis."""
    summary: str = Field(min_length=5, max_length=300)
    category: TicketCategory
    sentiment: Sentiment
    priority: Priority
    needs_order_lookup: bool = False
    needs_faq_lookup: bool = False
    needs_human_review: bool = False
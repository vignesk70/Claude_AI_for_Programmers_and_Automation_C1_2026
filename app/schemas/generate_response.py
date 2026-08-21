from typing import Optional

from pydantic import BaseModel, Field, model_validator


class GenerateResponseRequest(BaseModel):
    """Request to generate a customer response using trusted context."""
    customer_message: str = Field(min_length=5, max_length=5000)
    customer_id: Optional[str] = Field(default=None, min_length=3, max_length=50)
    order_id: Optional[str] = Field(default=None, min_length=3, max_length=50)
    faq_ids: list[str] = Field(default_factory=list, max_length=3)

    @model_validator(mode="after")
    def validate_order_context(self) -> "GenerateResponseRequest":
        if self.order_id and not self.customer_id:
            raise ValueError("customer_id is required when order_id is provided")
        return self


class ResponseContextUsed(BaseModel):
    """Shows exactly which trusted context the application used."""
    order_id: Optional[str] = None
    faq_ids: list[str] = Field(default_factory=list)


class GenerateResponseResponse(BaseModel):
    """Generated customer response with context and usage metadata."""
    draft_response: str = Field(min_length=1, max_length=5000)
    context_used: ResponseContextUsed

from fastapi import APIRouter

from app.core.prompt_data import serialize_prompt_payload
from app.db import get_db
from app.prompts.response_generation import RESPONSE_GENERATION_SYSTEM_PROMPT
from app.repositories.faq_repository import FAQRepository
from app.repositories.order_repository import OrderRepository
from app.schemas.generate_response import (
    GenerateResponseRequest,
    GenerateResponseResponse,
    ResponseContextUsed,
)
from app.services.llm import chat

router = APIRouter(tags=["GenerateResponse"])


@router.post(
    "/generate-response",
    response_model=GenerateResponseResponse,
)
async def generate_response(request: GenerateResponseRequest) -> GenerateResponseResponse:
    """Generate a customer response draft using trusted order + FAQ context."""
    db = get_db()
    order_repo = OrderRepository(db)
    faq_repo = FAQRepository(db)

    # Retrieve trusted order context (requires both IDs for ownership check)
    order_context = None
    if request.order_id and request.customer_id:
        order_doc = await order_repo.get_order_for_customer(
            request.customer_id, request.order_id,
        )
        if order_doc:
            order_context = {
                "order_id": order_doc.order_id,
                "status": order_doc.status.value,
                "estimated_delivery": str(order_doc.estimated_delivery),
                "delivered_at": str(order_doc.delivered_at),
            }

    # Retrieve approved FAQ context by IDs
    faq_sources = faq_repo.get_by_ids(request.faq_ids)
    faq_context = [faq.model_dump(mode="json") for faq in faq_sources]

    # Build the prompt payload with trusted context
    payload = {
        "customer_message": request.customer_message,
        "trusted_order_context": order_context,
        "trusted_faq_context": faq_context,
    }

    user_prompt = (
        "Customer request and application context:\n"
        + serialize_prompt_payload(payload)
    )

    result = await chat(
        prompt=user_prompt,
        system_prompt=RESPONSE_GENERATION_SYSTEM_PROMPT,
    )

    return GenerateResponseResponse(
        draft_response=result["response"],
        context_used=ResponseContextUsed(
            order_id=order_context["order_id"] if order_context else None,
            faq_ids=[faq.faq_id for faq in faq_sources],
        ),
    )

import json

from fastapi import APIRouter

from app.prompts.categorize import CATEGORIZE_SYSTEM_PROMPT
from app.schemas.common import CategorizeRequest, CategorizeResponse
from app.services.llm import chat

router = APIRouter(tags=["Categorize"])


@router.post("/categorize", response_model=CategorizeResponse)
async def categorize_endpoint(request: CategorizeRequest) -> CategorizeResponse:
    """Categorize a support issue into one of: delivery, refund, billing, product, account, general."""
    result = chat(
        prompt=request.prompt,
        system_prompt=CATEGORIZE_SYSTEM_PROMPT,
        max_tokens=request.max_tokens,
        response_format="json_object",
    )
    
    # Parse the JSON response to extract the category and summary
    try:
        parsed = json.loads(result["response"])
        category = parsed.get("category", "general")
        summary = parsed.get("summary")
    except (json.JSONDecodeError, AttributeError):
        category = "general"
        summary = None
    
    return CategorizeResponse(
        category=category,
        summary=summary,
        input_tokens=result["input_tokens"],
        output_tokens=result["output_tokens"],
    )

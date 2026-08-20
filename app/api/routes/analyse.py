import json

from fastapi import APIRouter

from app.prompts.analyse import ANALYSE_SYSTEM_PROMPT
from app.schemas.common import AnalyseTicketRequest, TicketAnalysis
from app.schemas.enums import Priority, Sentiment, TicketCategory
from app.services.llm import chat

router = APIRouter(tags=["Analyse"])


@router.post("/analyse", response_model=TicketAnalysis)
async def analyse_endpoint(request: AnalyseTicketRequest) -> TicketAnalysis:
    """Perform comprehensive analysis of a support ticket."""
    result = chat(
        prompt=request.text,
        system_prompt=ANALYSE_SYSTEM_PROMPT,
        response_format="json_object",
    )
    
    try:
        parsed = json.loads(result["response"])
        
        # Parse enums with fallbacks
        try:
            category = TicketCategory(parsed.get("category", "general"))
        except ValueError:
            category = TicketCategory.GENERAL
        
        try:
            sentiment = Sentiment(parsed.get("sentiment", "neutral"))
        except ValueError:
            sentiment = Sentiment.NEUTRAL
        
        try:
            priority = Priority(parsed.get("priority", "medium"))
        except ValueError:
            priority = Priority.MEDIUM
        
        return TicketAnalysis(
            summary=parsed.get("summary", ""),
            category=category,
            sentiment=sentiment,
            priority=priority,
            needs_order_lookup=parsed.get("needs_order_lookup", False),
            needs_faq_lookup=parsed.get("needs_faq_lookup", False),
            needs_human_review=parsed.get("needs_human_review", False),
        )
    except (json.JSONDecodeError, AttributeError):
        # Return a safe default if parsing fails
        return TicketAnalysis(
            summary="Unable to analyze ticket",
            category=TicketCategory.GENERAL,
            sentiment=Sentiment.NEUTRAL,
            priority=Priority.MEDIUM,
        )

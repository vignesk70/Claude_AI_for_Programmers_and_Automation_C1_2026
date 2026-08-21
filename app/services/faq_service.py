import json

from app.core.prompt_data import serialize_prompt_payload
from app.prompts.faq_answer import FAQ_ANSWER_SYSTEM_PROMPT
from app.repositories.faq_repository import FAQRepository
from app.schemas.faq import FAQAnswerDecision, FAQAskResponse, FAQSource
from app.services.llm import chat

# Application-owned fallback used when approved evidence is unavailable.
NO_APPROVED_FAQ_ANSWER = (
    "I couldn't find approved FAQ information that answers this "
    "question. Please refer this request for human review."
)


async def handle_faq_request(
    question: str,
    faq_repo: FAQRepository,
) -> FAQAskResponse:
    """Search approved FAQs and use the LLM to answer from sources.

    Flow:
    1. Search MongoDB for relevant FAQ sources.
    2. If none found -> return fallback + requires_human_review.
    3. Otherwise -> call LLM with FAQ context -> parse answer decision.
    """
    # Step 1: Retrieve approved FAQ sources
    sources = faq_repo.search(question, limit=3)

    # Step 2: No approved evidence -> application fallback, no LLM call
    if not sources:
        return FAQAskResponse(
            answer=NO_APPROVED_FAQ_ANSWER,
            sources=[],
            requires_human_review=True,
        )

    # Step 3: Call LLM with FAQ context
    payload = {
        "customer_question": question,
        "approved_faq_sources": [
            source.model_dump(mode="json") for source in sources
        ],
    }

    result = await chat(
        prompt=serialize_prompt_payload(payload),
        system_prompt=FAQ_ANSWER_SYSTEM_PROMPT,
        response_format="json_object",
    )

    # Parse the LLM's answer decision
    try:
        parsed = json.loads(result["response"])
        decision = FAQAnswerDecision.model_validate(parsed)
    except (json.JSONDecodeError, Exception):
        decision = FAQAnswerDecision(
            answer=result["response"],
            supported_by_sources=False,
        )

    return FAQAskResponse(
        answer=decision.answer,
        sources=sources,
        requires_human_review=not decision.supported_by_sources,
    )

from fastapi import APIRouter

from app.prompts.summarize import SUMMARIZE_SYSTEM_PROMPT
from app.schemas.common import ChatRequest, ChatResponse, SummarizeRequest
from app.services.llm import chat

router = APIRouter(tags=["Chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest) -> ChatResponse:
    """Send a prompt to the local Ollama model and return the response."""
    result = chat(
        prompt=request.prompt,
        system_prompt=request.system_prompt,
        max_tokens=request.max_tokens,
        response_format=request.response_format,
    )
    return ChatResponse(**result)


@router.post("/summarize", response_model=ChatResponse)
async def summarize_endpoint(request: SummarizeRequest) -> ChatResponse:
    """Send a prompt to the local Ollama model with the summarize system prompt."""
    result = chat(
        prompt=request.prompt,
        system_prompt=SUMMARIZE_SYSTEM_PROMPT,
        max_tokens=request.max_tokens,
        response_format=request.response_format,
    )
    return ChatResponse(**result)

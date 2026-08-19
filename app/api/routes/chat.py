from fastapi import APIRouter

from app.schemas.common import ChatRequest, ChatResponse
from app.services.llm import chat

router = APIRouter(tags=["Chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest) -> ChatResponse:
    """Send a prompt to the local Ollama model and return the response."""
    result = chat(prompt=request.prompt, system_prompt=request.system_prompt)
    return ChatResponse(response=result)

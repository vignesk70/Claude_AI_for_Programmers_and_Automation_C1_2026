from typing import Literal, Optional

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["healthy"] = "ok"


class ChatRequest(BaseModel):
    prompt: str
    system_prompt: Optional[str] = ""


class ChatResponse(BaseModel):
    response: str
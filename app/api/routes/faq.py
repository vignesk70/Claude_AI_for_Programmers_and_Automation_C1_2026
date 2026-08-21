from fastapi import APIRouter

from app.db import get_db
from app.repositories.faq_repository import FAQRepository
from app.schemas.faq import FAQAskRequest, FAQAskResponse
from app.services.faq_service import handle_faq_request

router = APIRouter(prefix="/faq", tags=["FAQ"])


@router.post("/ask", response_model=FAQAskResponse)
async def ask_faq(request: FAQAskRequest) -> FAQAskResponse:
    """Ask a question answered from approved FAQ sources."""
    faq_repo = FAQRepository(get_db())
    return await handle_faq_request(request.question, faq_repo)

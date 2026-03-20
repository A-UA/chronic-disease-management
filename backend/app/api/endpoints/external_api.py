from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from pydantic import BaseModel

from app.api.deps import get_api_key_context, get_db
from app.db.models import ApiKey

router = APIRouter()

class ExternalChatRequest(BaseModel):
    kb_id: UUID
    query: str

@router.post("/chat/completions")
async def external_chat_completions(
    request: ExternalChatRequest,
    api_key: ApiKey = Depends(get_api_key_context),
    db: AsyncSession = Depends(get_db)
):
    # In a real app, this would route to the same RAG logic but formatted for OpenAI API spec
    # and tracking usage against api_key.id
    
    return {
        "id": "chatcmpl-mock",
        "object": "chat.completion",
        "model": "rag-custom",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": f"Mocked external response for kb {request.kb_id} using key from org {api_key.org_id}"
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30
        }
    }

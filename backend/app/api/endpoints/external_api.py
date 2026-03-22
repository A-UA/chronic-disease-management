import json
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from pydantic import BaseModel

from app.api.deps import get_api_key_context, get_db
from app.db.models import ApiKey
from app.services.provider_registry import registry
from app.services.chat import retrieve_chunks, build_rag_prompt

router = APIRouter()

class ExternalChatRequest(BaseModel):
    kb_id: UUID
    query: str
    limit: int = 5

@router.post("/chat/completions")
async def external_chat_completions(
    request: ExternalChatRequest,
    api_key: ApiKey = Depends(get_api_key_context),
    db: AsyncSession = Depends(get_db)
):
    llm_provider = registry.get_llm()

    chunks = await retrieve_chunks(
        db=db,
        query=request.query,
        kb_id=request.kb_id,
        org_id=api_key.org_id,
        user_id=api_key.id, # Treating api key as user for cache/quota
        limit=request.limit,
    )

    prompt, citations = build_rag_prompt(request.query, chunks)
    full_response = await llm_provider.complete_text(prompt)

    prompt_tokens = len(prompt) // 4
    completion_tokens = len(full_response) // 4
    total_tokens = prompt_tokens + completion_tokens

    # 实际项目中这里还需要调用扣费逻辑

    return {
        "id": "chatcmpl-ext",
        "object": "chat.completion",
        "model": "rag-custom",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": full_response
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens
        }
    }
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.rag.prompt import build_rag_prompt
from app.ai.rag.retrieval import retrieve_chunks
from app.ai.rag.tokens import count_tokens
from app.models import ApiKey, UsageLog
from app.routers.deps import get_api_key_context, get_db
from app.services.rag.provider_service import provider_service
from app.services.system.quota import update_tenant_quota

router = APIRouter()


class ExternalChatRequest(BaseModel):
    kb_id: int
    query: str
    limit: int = 5


@router.post("/chat/completions")
async def external_chat_completions(
    request: ExternalChatRequest,
    api_key: ApiKey = Depends(get_api_key_context),
    db: AsyncSession = Depends(get_db),
):
    llm_provider = provider_service.get_llm()

    chunks = await retrieve_chunks(
        db=db,
        query=request.query,
        kb_id=request.kb_id,
        org_id=api_key.org_id,
        user_id=api_key.id,
        limit=request.limit,
    )

    prompt, citations = build_rag_prompt(request.query, chunks)
    full_response = await llm_provider.complete_text(prompt)

    # 精确计算 token 数（与内部聊天保持一致）
    prompt_tokens = count_tokens(prompt, llm_provider.model_name)
    completion_tokens = count_tokens(full_response, llm_provider.model_name)
    total_tokens = prompt_tokens + completion_tokens

    # 记录用量日志
    usage = UsageLog(
        tenant_id=api_key.tenant_id,
        org_id=api_key.org_id,
        api_key_id=api_key.id,
        model=llm_provider.model_name,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        action_type="external_chat",
    )
    db.add(usage)

    # 扣减组织配额
    await update_tenant_quota(db, api_key.tenant_id, total_tokens)

    # 更新 API Key 自身的 token 消耗累计
    stmt = (
        update(ApiKey)
        .where(ApiKey.id == api_key.id)
        .values(token_used=ApiKey.token_used + total_tokens)
    )
    await db.execute(stmt)
    await db.commit()

    return {
        "id": "chatcmpl-ext",
        "object": "chat.completion",
        "model": llm_provider.model_name,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": full_response},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        },
    }

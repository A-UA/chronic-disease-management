"""外部 API 服务"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.rag.prompt import build_rag_prompt
from app.ai.rag.retrieval import retrieve_chunks
from app.ai.rag.tokens import count_tokens
from app.models import ApiKey, UsageLog
from app.repositories.api_key_repo import ApiKeyRepository
from app.services.rag.provider_service import provider_service
from app.services.system.quota import update_tenant_quota


class ExternalApiService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.api_key_repo = ApiKeyRepository(db)

    async def chat_completions(self, *, api_key: ApiKey, kb_id: int, query: str, limit: int) -> dict:
        """处理外部请求并记录计费统计"""
        llm_provider = provider_service.get_llm()

        chunks = await retrieve_chunks(
            db=self.db,
            query=query,
            kb_id=kb_id,
            org_id=api_key.org_id,
            user_id=api_key.id,
            limit=limit,
        )

        prompt, citations = build_rag_prompt(query, chunks)
        full_response = await llm_provider.complete_text(prompt)

        prompt_tokens = count_tokens(prompt, llm_provider.model_name)
        completion_tokens = count_tokens(full_response, llm_provider.model_name)
        total_tokens = prompt_tokens + completion_tokens

        usage = UsageLog(
            tenant_id=api_key.tenant_id,
            org_id=api_key.org_id,
            api_key_id=api_key.id,
            model=llm_provider.model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            action_type="external_chat",
        )
        self.db.add(usage)

        await update_tenant_quota(self.db, api_key.tenant_id, total_tokens)

        await self.api_key_repo.increment_token_usage(api_key.id, total_tokens)
        await self.db.commit()

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

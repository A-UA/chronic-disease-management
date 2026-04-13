"""外部 API 端点 — 纯 HTTP 适配层"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.models import ApiKey
from app.routers.deps import ExternalApiServiceDep, get_api_key_context

router = APIRouter()


class ExternalChatRequest(BaseModel):
    kb_id: int
    query: str
    limit: int = 5


@router.post("/chat/completions")
async def external_chat_completions(
    request: ExternalChatRequest,
    service: ExternalApiServiceDep,
    api_key: ApiKey = Depends(get_api_key_context),
):
    """外部对话请求端点"""
    return await service.chat_completions(
        api_key=api_key,
        kb_id=request.kb_id,
        query=request.query,
        limit=request.limit,
    )

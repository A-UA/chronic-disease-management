"""Agent 内部 API — 仅供 Java/NestJS 业务后端调用"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.internal import (
    ChatRequest,
    ChatSyncResponse,
    CompressRequest,
    CompressResponse,
    DeleteChunksRequest,
    DeleteChunksResponse,
    HealthResponse,
    IngestRequest,
    IngestResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(req: IngestRequest) -> IngestResponse:
    """文档切块 + Embedding + 写入 Milvus"""
    # TODO(Task 5): 对接 RAG ingestion pipeline
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.delete("/chunks", response_model=DeleteChunksResponse)
async def delete_chunks(req: DeleteChunksRequest) -> DeleteChunksResponse:
    """按文档 ID 删除 Milvus 中的切块"""
    # TODO(Task 5): 对接 Milvus 删除
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.post("/chat")
async def chat_stream(req: ChatRequest):
    """RAG 检索 + LLM 对话（SSE 流式）"""

    # TODO(Task 6): 对接 RAG retrieval + LLM streaming
    async def event_generator():
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/chat/sync", response_model=ChatSyncResponse)
async def chat_sync(req: ChatRequest) -> ChatSyncResponse:
    """RAG 检索 + LLM 对话（同步模式）"""
    # TODO(Task 6): 对接 RAG retrieval + LLM sync
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.post("/compress", response_model=CompressResponse)
async def compress_history(req: CompressRequest) -> CompressResponse:
    """对话历史压缩"""
    # TODO(Task 6): 对接 compress 模块
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """健康检查"""
    return HealthResponse(status="ok")

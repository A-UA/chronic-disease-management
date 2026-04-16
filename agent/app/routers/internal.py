"""Agent 内部 API — 仅供 Java/NestJS 业务后端调用"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
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
async def chat_stream(req: ChatRequest, request: Request):
    """RAG 检索 + LLM 对话（SSE 流式）"""
    import json

    from langchain_core.messages import AIMessage, HumanMessage

    from app.graph.graph import build_agent_graph
    from app.graph.security import SecurityContext

    forward_headers = {k: v for k, v in request.headers.items() if k.lower() in ("x-identity-base64", "authorization")}

    ctx = SecurityContext(
        tenant_id=req.tenant_id,
        org_id=0,
        user_id=0,
        auth_headers=forward_headers,
    )

    graph = build_agent_graph()

    lc_messages = []
    for m in req.history:
        if m.role == "user":
            lc_messages.append(HumanMessage(content=m.content))
        elif m.role == "assistant":
            lc_messages.append(AIMessage(content=m.content))

    lc_messages.append(HumanMessage(content=req.query))

    state = {
        "messages": lc_messages,
        "query": req.query,
        "kb_ids": req.kb_ids,
        "iteration": 0,
        "max_iterations": 3,
    }

    async def event_generator():
        try:
            async for event in graph.astream_events(
                state,
                config={"configurable": {"context": ctx}},
                version="v2"
            ):
                kind = event["event"]

                # Streaming LLM tokens
                if kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if getattr(chunk, "content", None):
                        data = json.dumps({"type": "token", "content": chunk.content})
                        yield f"data: {data}\n\n"

                # Tool Call Notification
                elif kind == "on_tool_start":
                    data = json.dumps({
                        "type": "tool_start",
                        "name": event["name"],
                        "inputs": event["data"].get("input", {})
                    })
                    yield f"data: {data}\n\n"

                elif kind == "on_tool_end":
                    data = json.dumps({
                        "type": "tool_end",
                        "name": event["name"]
                    })
                    yield f"data: {data}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as e:
            logger.error("Error during streaming", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/chat/sync", response_model=ChatSyncResponse)
async def chat_sync(req: ChatRequest, request: Request) -> ChatSyncResponse:
    """RAG 检索 + LLM 对话（同步模式）"""
    from langchain_core.messages import AIMessage, HumanMessage

    from app.graph.graph import build_agent_graph
    from app.graph.security import SecurityContext

    # 提取头信息以透传给网关
    forward_headers = {k: v for k, v in request.headers.items() if k.lower() in ("x-identity-base64", "authorization")}

    # 构建安全上下文（由于已经剥离本地 DB，不再需要查库权限，透传 Header 即可由于 Gateway 拦截）
    ctx = SecurityContext(
        tenant_id=req.tenant_id,
        org_id=0,
        user_id=0,
        auth_headers=forward_headers,
    )

    graph = build_agent_graph()

    # 组装消息历史
    lc_messages = []
    for m in req.history:
        if m.role == "user":
            lc_messages.append(HumanMessage(content=m.content))
        elif m.role == "assistant":
            lc_messages.append(AIMessage(content=m.content))

    lc_messages.append(HumanMessage(content=req.query))

    state = {
        "messages": lc_messages,
        "query": req.query,
        "kb_ids": req.kb_ids,
        "iteration": 0,
        "max_iterations": 3,
    }

    result = await graph.ainvoke(
        state,
        config={"configurable": {"context": ctx}}
    )

    return ChatSyncResponse(
        answer=result.get("final_answer", ""),
        citations=[],
        usage={},
    )


@router.post("/compress", response_model=CompressResponse)
async def compress_history(req: CompressRequest) -> CompressResponse:
    """对话历史压缩"""
    # TODO(Task 6): 对接 compress 模块
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """健康检查"""
    return HealthResponse(status="ok")

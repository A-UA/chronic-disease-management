import json
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.agent.ingestion import (
    process_document_to_milvus,
    delete_vectors_by_kb,
    delete_vectors_by_doc,
)
from sse_starlette.sse import EventSourceResponse
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from pydantic import BaseModel, Field
from typing import Any, List, Dict
from app.agent.graph import create_agent_graph
from app.config import settings

internal_router = APIRouter(prefix="/internal")
graph = create_agent_graph()


class ChatRequest(BaseModel):
    query: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    history: List[Dict[str, str]] = Field(default_factory=list)


def _convert_history(history: List[Dict[str, str]]):
    converted = []
    for msg in history:
        if msg.get("role") == "user":
            converted.append(HumanMessage(content=msg.get("content", "")))
        elif msg.get("role") == "assistant":
            converted.append(AIMessage(content=msg.get("content", "")))
        elif msg.get("role") == "system":
            converted.append(SystemMessage(content=msg.get("content", "")))
    return converted


@internal_router.post("/chat")
async def chat_stream(req: ChatRequest):
    async def event_generator():
        try:
            messages = _convert_history(req.history)
            messages.append(HumanMessage(content=req.query))

            config = {"configurable": req.metadata}

            # 累积 Token 使用统计（可能有多轮 LLM 调用，如工具回调后再次生成）
            total_input_tokens = 0
            total_output_tokens = 0

            async for event in graph.astream_events(
                {"messages": messages}, config=config, version="v2"
            ):
                kind = event["event"]
                if kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if chunk.content:
                        yield {"event": "message", "data": chunk.content}
                elif kind == "on_chat_model_end":
                    # 从 AIMessage.usage_metadata 中提取 Token 用量
                    output = event["data"].get("output")
                    if hasattr(output, "usage_metadata") and output.usage_metadata:
                        usage = output.usage_metadata
                        total_input_tokens += usage.get("input_tokens", 0)
                        total_output_tokens += usage.get("output_tokens", 0)
                elif kind == "on_tool_start":
                    yield {
                        "event": "tool_start",
                        "data": json.dumps(
                            {"tool": event["name"], "input": event["data"].get("input")},
                            ensure_ascii=False,
                        ),
                    }
                elif kind == "on_tool_end":
                    output = event["data"].get("output")
                    tool_data: dict[str, Any] = {"tool": event["name"]}

                    # 提取 content_and_artifact 模式的 artifact 数据
                    if isinstance(output, ToolMessage) and output.artifact:
                        tool_data["artifact"] = output.artifact

                    tool_data["output"] = str(output) if not isinstance(output, ToolMessage) else output.content
                    yield {
                        "event": "tool_end",
                        "data": json.dumps(tool_data, ensure_ascii=False),
                    }

            # 流结束后发送 Token 使用统计事件
            combined_tokens = total_input_tokens + total_output_tokens
            if combined_tokens > 0:
                yield {
                    "event": "usage",
                    "data": json.dumps({
                        "input_tokens": total_input_tokens,
                        "output_tokens": total_output_tokens,
                        "total_tokens": combined_tokens,
                        "model": settings.CHAT_MODEL,
                    }),
                }
        except Exception as e:
            yield {"event": "error", "data": str(e)}

    return EventSourceResponse(event_generator())


@internal_router.post("/chat/sync")
async def chat_sync(req: ChatRequest):
    messages = _convert_history(req.history)
    messages.append(HumanMessage(content=req.query))
    config = {"configurable": req.metadata}
    response = await graph.ainvoke({"messages": messages}, config=config)
    return {"reply": response["messages"][-1].content}


@internal_router.post("/knowledge/parse")
async def parse_knowledge_document(
    file: UploadFile = File(...),
    kb_id: str = Form(...),
    org_id: str = Form(None),
):
    try:
        content = await file.read()
        chunk_count = process_document_to_milvus(
            content, file.filename or "unknown", kb_id, org_id
        )
        return {
            "status": "success",
            "filename": file.filename,
            "chunk_count": chunk_count,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@internal_router.delete("/knowledge/vectors/kb/{kb_id}")
async def delete_kb_vectors(kb_id: str):
    """删除指定知识库的所有向量"""
    try:
        deleted = delete_vectors_by_kb(kb_id)
        return {"status": "success", "kb_id": kb_id, "deleted_count": deleted}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@internal_router.delete("/knowledge/vectors/kb/{kb_id}/doc/{filename}")
async def delete_doc_vectors(kb_id: str, filename: str):
    """删除指定知识库中某个文档的向量"""
    try:
        deleted = delete_vectors_by_doc(kb_id, filename)
        return {"status": "success", "kb_id": kb_id, "filename": filename, "deleted_count": deleted}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

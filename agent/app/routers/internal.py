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

# 初始化内部路由，前缀为 /internal
internal_router = APIRouter(prefix="/internal")
# 创建并初始化 Agent 状态图
graph = create_agent_graph()


class ChatRequest(BaseModel):
    """聊天请求模型"""
    query: str  # 用户输入的查询文本
    metadata: dict[str, Any] = Field(default_factory=dict)  # 元数据，包含 kb_id 等配置
    history: List[Dict[str, str]] = Field(default_factory=list)  # 历史对话记录


def _convert_history(history: List[Dict[str, str]]):
    """将字典格式的历史记录转换为 LangChain 消息对象列表"""
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
    """SSE 流式聊天接口"""
    async def event_generator():
        try:
            # 转换历史消息并添加当前用户查询
            messages = _convert_history(req.history)
            messages.append(HumanMessage(content=req.query))

            # 将元数据作为配置传入 LangGraph
            config = {"configurable": req.metadata}

            # 累积 Token 使用统计（可能有多轮 LLM 调用）
            total_input_tokens = 0
            total_output_tokens = 0

            # 订阅状态图生成的事件流 (v2 版本支持更多细粒度事件)
            async for event in graph.astream_events(
                {"messages": messages}, config=config, version="v2"
            ):
                kind = event["event"]
                # 处理模型生成的文字流
                if kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if chunk.content:
                        yield {"event": "message", "data": chunk.content}
                # 处理模型调用结束，提取 Token 使用量
                elif kind == "on_chat_model_end":
                    output = event["data"].get("output")
                    if hasattr(output, "usage_metadata") and output.usage_metadata:
                        usage = output.usage_metadata
                        total_input_tokens += usage.get("input_tokens", 0)
                        total_output_tokens += usage.get("output_tokens", 0)
                # 处理工具开始调用
                elif kind == "on_tool_start":
                    yield {
                        "event": "tool_start",
                        "data": json.dumps(
                            {"tool": event["name"], "input": event["data"].get("input")},
                            ensure_ascii=False,
                        ),
                    }
                # 处理工具调用结束，提取引用数据 (artifact)
                elif kind == "on_tool_end":
                    output = event["data"].get("output")
                    tool_data: dict[str, Any] = {"tool": event["name"]}

                    # 提取 content_and_artifact 模式下的结构化引用数据
                    if isinstance(output, ToolMessage) and output.artifact:
                        tool_data["artifact"] = output.artifact

                    # 获取工具输出文本
                    tool_data["output"] = str(output) if not isinstance(output, ToolMessage) else output.content
                    yield {
                        "event": "tool_end",
                        "data": json.dumps(tool_data, ensure_ascii=False),
                    }

            # 所有事件处理完毕后，发送 Token 使用统计
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
            # 捕获并向前端推送错误事件
            yield {"event": "error", "data": str(e)}

    # 返回 SSE 响应
    return EventSourceResponse(event_generator())


@internal_router.post("/chat/sync")
async def chat_sync(req: ChatRequest):
    """同步聊天接口（非流式）"""
    messages = _convert_history(req.history)
    messages.append(HumanMessage(content=req.query))
    config = {"configurable": req.metadata}
    # 直接运行状态图直到结束
    response = await graph.ainvoke({"messages": messages}, config=config)
    # 返回最后一条消息内容
    return {"reply": response["messages"][-1].content}


@internal_router.post("/knowledge/parse")
async def parse_knowledge_document(
    file: UploadFile = File(...),  # 上传的文件流
    kb_id: str = Form(...),        # 所属知识库 ID
    org_id: str = Form(None),      # 组织 ID (可选)
):
    """解析知识库文档并写入 Milvus 向量数据库"""
    try:
        content = await file.read()
        # 执行文档解析、切片并写入向量库
        chunk_count = process_document_to_milvus(
            content, file.filename or "unknown", kb_id, org_id
        )
        return {
            "status": "success",
            "filename": file.filename,
            "chunk_count": chunk_count,
        }
    except Exception as e:
        # 异常处理
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
    """删除指定知识库中某个特定文档的向量"""
    try:
        deleted = delete_vectors_by_doc(kb_id, filename)
        return {"status": "success", "kb_id": kb_id, "filename": filename, "deleted_count": deleted}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

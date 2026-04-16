import json
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.agent.ingestion import process_document_to_milvus
from sse_starlette.sse import EventSourceResponse
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from pydantic import BaseModel, Field
from typing import Any, List, Dict
from app.agent.graph import create_agent_graph

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
            
            # 传递配置，特别是 kb_id
            config = {"configurable": req.metadata}
            
            async for event in graph.astream_events({"messages": messages}, config=config, version="v2"):
                kind = event["event"]
                if kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if chunk.content:
                        yield {"event": "message", "data": chunk.content}
                elif kind == "on_tool_start":
                    yield {"event": "tool_start", "data": json.dumps({"tool": event["name"], "input": event["data"].get("input")}, ensure_ascii=False)}
                elif kind == "on_tool_end":
                    yield {"event": "tool_end", "data": json.dumps({"tool": event["name"], "output": event["data"].get("output")}, ensure_ascii=False)}
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
    kb_id: str = Form(...)
):
    try:
        content = await file.read()
        chunk_count = process_document_to_milvus(content, file.filename, kb_id)
        return {
            "status": "success",
            "filename": file.filename,
            "chunk_count": chunk_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

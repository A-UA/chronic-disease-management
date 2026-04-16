from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse
from langchain_core.messages import HumanMessage
from pydantic import BaseModel
from typing import Any
from app.agent.graph import create_agent_graph

internal_router = APIRouter(prefix="/internal")
graph = create_agent_graph()

class ChatRequest(BaseModel):
    query: str
    metadata: dict[str, Any] = {}

@internal_router.post("/chat")
async def chat_stream(req: ChatRequest):
    async def event_generator():
        messages = [HumanMessage(content=req.query)]
        # We use standard astream_events pattern
        async for event in graph.astream_events({"messages": messages}, version="v2"):
            kind = event["event"]
            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if chunk.content:
                    yield {"event": "message", "data": chunk.content}
            # Add other tools/logging events naturally mapped for SSE...
                    
    return EventSourceResponse(event_generator())

@internal_router.post("/chat/sync")
async def chat_sync(req: ChatRequest):
    messages = [HumanMessage(content=req.query)]
    response = await graph.ainvoke({"messages": messages})
    return {"reply": response["messages"][-1].content}

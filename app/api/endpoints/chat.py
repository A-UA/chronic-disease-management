import json
import asyncio
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.api.deps import get_current_user, get_current_org, get_db, verify_quota
from app.db.models import User, Message, UsageLog, Conversation
from app.services.chat import retrieve_chunks, build_rag_prompt
from app.services.quota import update_org_quota

router = APIRouter()

class ChatRequest(BaseModel):
    kb_id: UUID
    conversation_id: UUID
    query: str

async def mock_llm_stream(prompt: str) -> AsyncGenerator[str, None]:
    # Mock LLM stream generator
    words = ["Here", " is", " a", " mocked", " response", " to", " your", " query."]
    for word in words:
        await asyncio.sleep(0.1)
        yield word

@router.post("/chat")
async def chat_endpoint(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    org_id: UUID = Depends(get_current_org),
    _ = Depends(verify_quota),
    db: AsyncSession = Depends(get_db)
):
    # 1. Retrieve chunks
    chunks = await retrieve_chunks(db, request.query, request.kb_id)
    
    # 2. Build prompt
    prompt, citations = build_rag_prompt(request.query, chunks)
    
    # 3. Create conversation if not exists
    conversation = await db.get(Conversation, request.conversation_id)
    if not conversation:
        conversation = Conversation(
            id=request.conversation_id,
            kb_id=request.kb_id,
            org_id=org_id,
            user_id=current_user.id,
            title=request.query[:50]
        )
        db.add(conversation)
        
    # 4. Save User Message
    user_msg = Message(
        conversation_id=conversation.id,
        role="user",
        content=request.query
    )
    db.add(user_msg)
    await db.commit()

    # 5. Generator for SSE
    async def generate() -> AsyncGenerator[str, None]:
        # Yield metadata (citations)
        yield f"event: meta\ndata: {json.dumps({'citations': citations})}\n\n"
        
        full_response = ""
        # Stream chunks from LLM
        async for chunk_text in mock_llm_stream(prompt):
            full_response += chunk_text
            yield f"event: chunk\ndata: {json.dumps({'text': chunk_text})}\n\n"
            
        # Dummy token counts
        prompt_tokens = len(prompt) // 4
        completion_tokens = len(full_response) // 4
        
        # Save Assistant Message
        assistant_msg = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=full_response,
            metadata_={"citations": citations, "tokens": {"input": prompt_tokens, "output": completion_tokens}}
        )
        db.add(assistant_msg)
        
        # Save Usage
        usage = UsageLog(
            org_id=org_id,
            user_id=current_user.id,
            model="gpt-4o-mock",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            action_type="chat",
            resource_id=conversation.id
        )
        db.add(usage)
        await db.commit()
        
        # Deduct quota from Organization
        await update_org_quota(db, org_id, usage.total_tokens)
        
        # Yield done
        yield f"event: done\ndata: {json.dumps({'tokens': usage.total_tokens})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

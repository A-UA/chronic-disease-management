import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_org, get_current_user, get_db, verify_quota
from app.db.models import Conversation, KnowledgeBase, Message, UsageLog, User
from app.schemas.admin import ConversationRead
from app.services.chat import RetrievalFilters, build_rag_prompt, extract_statement_citations_structured, retrieve_chunks
from app.services.provider_registry import registry
from app.services.quota import check_quota_during_stream, update_org_quota
from app.services.rag_ingestion import count_tokens

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatRequest(BaseModel):
    kb_id: int
    conversation_id: int
    query: str
    document_ids: list[int] | None = None
    file_types: list[str] | None = None
    patient_id: int | None = None


@router.get("/conversations", response_model=list[ConversationRead])
async def list_conversations(
    skip: int = 0,
    limit: int = 50,
    org_id: int = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """获取当前组织的对话列表"""
    stmt = (
        select(Conversation)
        .where(Conversation.org_id == org_id)
        .offset(skip)
        .limit(limit)
        .order_by(Conversation.created_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("")
async def chat_endpoint(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    org_id: int = Depends(get_current_org),
    _=Depends(verify_quota),
    db: AsyncSession = Depends(get_db),
):
    # 1. 构造过滤器
    filters: RetrievalFilters = {}
    if request.document_ids:
        filters["document_ids"] = request.document_ids
    if request.file_types:
        filters["file_types"] = request.file_types
    if request.patient_id:
        filters["patient_id"] = request.patient_id

    kb = await db.get(KnowledgeBase, request.kb_id)
    if kb is None:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    if kb.org_id != org_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # 2. 获取对话历史用于 Condense Query
    conversation = await db.get(Conversation, request.conversation_id)
    if conversation:
        if conversation.org_id != org_id or conversation.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Conversation does not belong to current user")
        if conversation.kb_id != request.kb_id:
            raise HTTPException(status_code=400, detail="Conversation knowledge base mismatch")
    else:
        conversation = Conversation(
            id=request.conversation_id,
            kb_id=request.kb_id,
            org_id=org_id,
            user_id=current_user.id,
            title=request.query[:50],
        )
        db.add(conversation)

    history_stmt = (
        select(Message)
        .where(Message.conversation_id == request.conversation_id)
        .order_by(Message.created_at.desc())
        .limit(10)
    )
    history_res = await db.execute(history_stmt)
    history_msgs = history_res.scalars().all()[::-1]
    history_list = [{"role": m.role, "content": m.content} for m in history_msgs]

    llm_provider = registry.get_llm()

    chunks = await retrieve_chunks(
        db,
        request.query,
        request.kb_id,
        org_id,
        user_id=current_user.id,
        filters=filters or None,
        history=history_list,
        llm_provider=llm_provider,
    )

    prompt, citations = build_rag_prompt(request.query, chunks)

    user_msg = Message(
        conversation_id=conversation.id,
        org_id=org_id,
        role="user",
        content=request.query,
        metadata_={"filters": filters or None},
    )
    db.add(user_msg)
    await db.commit()

    async def generate() -> AsyncGenerator[str, None]:
        yield f"event: meta\ndata: {json.dumps({'citations': citations})}\n\n"

        full_response = ""
        quota_exceeded = False
        
        # 在生成器内部开启独立会话，并手动管理 RLS 上下文
        from app.db.session import AsyncSessionLocal
        from sqlalchemy import text
        async with AsyncSessionLocal() as db_gen:
            await db_gen.execute(
                text("SELECT set_config('app.current_org_id', :org_id, true)"),
                {"org_id": str(org_id)},
            )
            await db_gen.execute(
                text("SELECT set_config('app.current_user_id', :user_id, true)"),
                {"user_id": str(current_user.id)},
            )

            try:
                # 预计算 prompt tokens
                prompt_tokens = count_tokens(prompt, llm_provider.model_name)
                completion_tokens = 0
                
                async for chunk_text in llm_provider.stream_text(prompt):
                    full_response += chunk_text
                    
                    # 优化：增量计算 token，避免 O(N^2)
                    chunk_tokens = count_tokens(chunk_text, llm_provider.model_name)
                    completion_tokens += chunk_tokens
                    
                    if not await check_quota_during_stream(org_id, prompt_tokens + completion_tokens, db=db_gen):
                        quota_exceeded = True
                        yield f"event: error\ndata: {json.dumps({'detail': 'Quota exceeded. Response cut short.'})}\n\n"
                        break

                    yield f"event: chunk\ndata: {json.dumps({'text': chunk_text})}\n\n"
            except Exception as e:
                logger.error(f"LLM streaming error: {str(e)}")
                yield f"event: error\ndata: {json.dumps({'detail': 'LLM streaming failed.'})}\n\n"

            try:
                statement_citations = []
                done_statement_citations = []
                if full_response and not quota_exceeded:
                    try:
                        statement_citations = await extract_statement_citations_structured(
                            full_response, citations, llm_provider
                        )
                        done_statement_citations = [
                            {
                                "text": item["text"],
                                "citation_refs": [citation["ref"] for citation in item["citations"]],
                                "chunk_ids": [citation.get("chunk_id") for citation in item["citations"]],
                            }
                            for item in statement_citations
                        ]
                    except Exception:
                        logger.warning("Statement citation extraction failed", exc_info=True)

                assistant_msg = Message(
                    conversation_id=conversation.id,
                    org_id=org_id, # 补上 org_id
                    role="assistant",
                    content=full_response or "[回答生成中断]",
                    metadata_={
                        "citations": citations,
                        "statement_citations": statement_citations,
                        "tokens": {"input": prompt_tokens, "output": completion_tokens},
                        "filters": filters or None,
                        "quota_exceeded": quota_exceeded,
                        "observability": {
                            "raw_query": request.query,
                            "retrieved_chunk_count": len(chunks),
                            "llm_model": llm_provider.model_name,
                            "citation_count": len(citations),
                            "statement_count": len(statement_citations),
                        },
                    },
                )
                db_gen.add(assistant_msg)

                total_tokens = prompt_tokens + completion_tokens
                usage = UsageLog(
                    org_id=org_id,
                    user_id=current_user.id,
                    model=llm_provider.model_name,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    action_type="chat",
                    resource_id=conversation.id,
                )
                db_gen.add(usage)
                await db_gen.commit()

                await update_org_quota(db_gen, org_id, total_tokens)
                yield f"event: done\ndata: {json.dumps({'tokens': total_tokens, 'statement_citations': done_statement_citations})}\n\n"
            except Exception:
                logger.exception("Failed to save chat audit records")

    return StreamingResponse(generate(), media_type="text/event-stream")

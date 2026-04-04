import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_org_id, get_effective_org_id, get_current_user,
    get_current_tenant_id, inject_rls_context, get_db, verify_quota,
)
from app.db.models import Conversation, KnowledgeBase, Message, UsageLog, User
from app.schemas.admin import ConversationRead
from app.services.chat import RetrievalFilters, build_rag_prompt, extract_statement_citations_structured, retrieve_chunks
from app.services.conversation_context import build_retrieval_query_from_history
from app.services.provider_registry import registry
from app.services.quota import check_quota_during_stream, update_tenant_quota
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


# --- 工具函数 ---

def _generate_title(query: str, max_len: int = 50) -> str:
    """生成对话标题：取第一个句号/问号截断，避免在词语中间断开"""
    import re
    # 先尝试按句子边界截取
    match = re.search(r'[。？?!]', query)
    if match and match.end() <= max_len:
        return query[:match.end()]
    # 如果查询本身就短，直接返回
    if len(query) <= max_len:
        return query
    # 否则在最后一个空格或标点处截断
    truncated = query[:max_len]
    last_break = max(truncated.rfind(' '), truncated.rfind('。'), truncated.rfind('，'))
    if last_break > max_len // 2:
        return truncated[:last_break] + '...'
    return truncated + '...'


def _estimate_tokens_chinese(text: str) -> int:
    """快速估算 Token 数（中文约 1.5 字/token），避免调用 tiktoken 的 CPU 开销"""
    return max(1, int(len(text) / 1.5))


def _load_history_by_token_budget(
    messages: list[Message],
    max_tokens: int = 2000,
) -> list[dict[str, str]]:
    """基于 Token 预算动态加载对话历史，而非固定条数截断"""
    result = []
    token_budget = 0
    # messages 已按时间正序排列，从最近的往前取
    for msg in reversed(messages):
        msg_tokens = _estimate_tokens_chinese(msg.content)
        if token_budget + msg_tokens > max_tokens:
            break
        result.append({"role": msg.role, "content": msg.content})
        token_budget += msg_tokens
    return list(reversed(result))


@router.get("/conversations", response_model=list[ConversationRead])
async def list_conversations(
    skip: int = 0,
    limit: int = 50,
    tenant_id: int = Depends(inject_rls_context),
    effective_org_id: int | None = Depends(get_effective_org_id),
    db: AsyncSession = Depends(get_db),
):
    """获取对话列表（admin 看全租户，普通用户看本部门）"""
    stmt = (
        select(Conversation)
        .where(Conversation.tenant_id == tenant_id)
    )
    if effective_org_id is not None:
        stmt = stmt.where(Conversation.org_id == effective_org_id)
    stmt = stmt.offset(skip).limit(limit).order_by(Conversation.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("")
async def chat_endpoint(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
    org_id: int = Depends(get_current_org_id),
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
    if kb.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # 2. 获取对话历史用于 Condense Query
    conversation = await db.get(Conversation, request.conversation_id)
    if conversation:
        if conversation.tenant_id != tenant_id or conversation.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Conversation does not belong to current user")
        if conversation.kb_id != request.kb_id:
            raise HTTPException(status_code=400, detail="Conversation knowledge base mismatch")
    else:
        conversation = Conversation(
            id=request.conversation_id,
            kb_id=request.kb_id,
            tenant_id=tenant_id,
            org_id=org_id,
            user_id=current_user.id,
            title=_generate_title(request.query),
        )
        db.add(conversation)

    # 动态加载历史：基于 Token 预算而非固定条数
    history_stmt = (
        select(Message)
        .where(Message.conversation_id == request.conversation_id)
        .order_by(Message.created_at.desc())
        .limit(20)  # 取足够多的候选消息
    )
    history_res = await db.execute(history_stmt)
    history_msgs = list(history_res.scalars().all())[::-1]
    history_list = _load_history_by_token_budget(history_msgs, max_tokens=2000)

    # 接入上下文增强服务：对追问型查询拼接历史上下文
    enhanced_query = build_retrieval_query_from_history(request.query, history_list)

    llm_provider = registry.get_llm()

    chunks = await retrieve_chunks(
        db,
        enhanced_query,  # 使用上下文增强后的查询
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
        tenant_id=tenant_id,
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
                text("SELECT set_config('app.current_tenant_id', :tid, true)"),
                {"tid": str(tenant_id)},
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
                    
                    # 优化：使用字符数粗略估算而非每个 chunk 都调 tiktoken
                    completion_tokens += _estimate_tokens_chinese(chunk_text)
                    
                    if not await check_quota_during_stream(tenant_id, prompt_tokens + completion_tokens, db=db_gen):
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
                    tenant_id=tenant_id,
                    org_id=org_id,
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

                # 用精确的 tiktoken 重新计算最终 completion_tokens
                completion_tokens = count_tokens(full_response, llm_provider.model_name) if full_response else 0

                total_tokens = prompt_tokens + completion_tokens
                usage = UsageLog(
                    tenant_id=tenant_id,
                    org_id=org_id,
                    user_id=current_user.id,
                    model=llm_provider.model_name,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    action_type="chat",
                    resource_id=conversation.id,
                )
                db_gen.add(usage)
                await update_tenant_quota(db_gen, tenant_id, total_tokens)
                await db_gen.commit()

                yield f"event: done\ndata: {json.dumps({'tokens': total_tokens, 'statement_citations': done_statement_citations})}\n\n"
            except Exception:
                logger.exception("Failed to save chat audit records")

    return StreamingResponse(generate(), media_type="text/event-stream")

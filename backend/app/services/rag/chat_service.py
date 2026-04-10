from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.rag.conversation import (
    build_retrieval_query_from_history,
    estimate_tokens_chinese,
    load_history_by_token_budget,
)
from app.ai.rag.prompt import build_rag_prompt
from app.ai.rag.retrieval import (
    RetrievalFilters,
    extract_statement_citations_structured,
    retrieve_chunks,
)
from app.ai.rag.tokens import count_tokens
from app.base.database import AsyncSessionLocal
from app.models import Conversation, KnowledgeBase, Message, UsageLog, User
from app.services.rag.provider_service import provider_service
from app.services.system.quota import check_quota_during_stream, update_tenant_quota

logger = logging.getLogger(__name__)


def _generate_title(query: str, max_len: int = 50) -> str:
    import re

    match = re.search(r"[。？?!]", query)
    if match and match.end() <= max_len:
        return query[: match.end()]
    if len(query) <= max_len:
        return query
    truncated = query[:max_len]
    last_break = max(truncated.rfind(" "), truncated.rfind("。"), truncated.rfind("，"))
    if last_break > max_len // 2:
        return truncated[:last_break] + "..."
    return truncated + "..."


def build_filters(
    document_ids: list[int] | None = None,
    file_types: list[str] | None = None,
    patient_id: int | None = None,
) -> RetrievalFilters:
    filters: RetrievalFilters = {}
    if document_ids:
        filters["document_ids"] = document_ids
    if file_types:
        filters["file_types"] = file_types
    if patient_id:
        filters["patient_id"] = patient_id
    return filters


async def _get_or_create_conversation(
    db: AsyncSession,
    *,
    kb_id: int,
    tenant_id: int,
    org_id: int,
    current_user: User,
    query: str,
    conversation_id: int | None,
) -> Conversation:
    conversation: Conversation | None = None
    if conversation_id is not None:
        conversation = await db.get(Conversation, conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if (
            conversation.tenant_id != tenant_id
            or conversation.user_id != current_user.id
        ):
            raise HTTPException(
                status_code=403,
                detail="Conversation does not belong to current user",
            )
        if conversation.kb_id != kb_id:
            raise HTTPException(
                status_code=400,
                detail="Conversation knowledge base mismatch",
            )

    if conversation is None:
        from app.base.snowflake import get_next_id

        conversation = Conversation(
            id=get_next_id(),
            kb_id=kb_id,
            tenant_id=tenant_id,
            org_id=org_id,
            user_id=current_user.id,
            title=_generate_title(query),
        )
        db.add(conversation)
    return conversation


async def _load_history(
    db: AsyncSession,
    conversation_id: int,
    max_tokens: int = 2000,
) -> list[dict[str, str]]:
    history_stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(20)
    )
    history_res = await db.execute(history_stmt)
    history_msgs = list(history_res.scalars().all())[::-1]
    return load_history_by_token_budget(history_msgs, max_tokens=max_tokens)


async def handle_standard_chat(
    *,
    request,
    current_user: User,
    tenant_id: int,
    org_id: int,
    db: AsyncSession,
) -> StreamingResponse:
    kb = await db.get(KnowledgeBase, request.kb_id)
    if kb is None:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    if kb.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    filters = build_filters(
        document_ids=request.document_ids,
        file_types=request.file_types,
        patient_id=request.patient_id,
    )
    conversation = await _get_or_create_conversation(
        db,
        kb_id=request.kb_id,
        tenant_id=tenant_id,
        org_id=org_id,
        current_user=current_user,
        query=request.query,
        conversation_id=request.conversation_id,
    )
    history_list = await _load_history(db, conversation.id)
    enhanced_query = build_retrieval_query_from_history(request.query, history_list)

    llm_provider = provider_service.get_llm()
    chunks = await retrieve_chunks(
        db,
        enhanced_query,
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
        yield (
            f"event: meta\ndata: "
            f"{json.dumps({'conversation_id': str(conversation.id), 'citations': citations})}\n\n"
        )

        full_response = ""
        quota_exceeded = False

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
                prompt_tokens = count_tokens(prompt, llm_provider.model_name)
                completion_tokens = 0

                async for chunk_text in llm_provider.stream_text(prompt):
                    full_response += chunk_text
                    completion_tokens += estimate_tokens_chinese(chunk_text)

                    if not await check_quota_during_stream(
                        tenant_id,
                        prompt_tokens + completion_tokens,
                        db=db_gen,
                    ):
                        quota_exceeded = True
                        yield (
                            "event: error\ndata: "
                            f"{json.dumps({'detail': 'Quota exceeded. Response cut short.'})}\n\n"
                        )
                        break

                    yield f"event: chunk\ndata: {json.dumps({'text': chunk_text})}\n\n"
            except Exception as exc:
                logger.error("LLM streaming error: %s", exc)
                yield (
                    "event: error\ndata: "
                    f"{json.dumps({'detail': 'LLM streaming failed.'})}\n\n"
                )

            try:
                statement_citations = []
                done_statement_citations = []
                if full_response and not quota_exceeded:
                    try:
                        statement_citations = (
                            await extract_statement_citations_structured(
                                full_response,
                                citations,
                                llm_provider,
                            )
                        )
                        done_statement_citations = [
                            {
                                "text": item["text"],
                                "citation_refs": [
                                    citation["ref"] for citation in item["citations"]
                                ],
                                "chunk_ids": [
                                    citation.get("chunk_id")
                                    for citation in item["citations"]
                                ],
                            }
                            for item in statement_citations
                        ]
                    except Exception:
                        logger.warning(
                            "Statement citation extraction failed",
                            exc_info=True,
                        )

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

                completion_tokens = (
                    count_tokens(full_response, llm_provider.model_name)
                    if full_response
                    else 0
                )
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

                yield (
                    "event: done\ndata: "
                    f"{json.dumps({'tokens': total_tokens, 'statement_citations': done_statement_citations})}\n\n"
                )
            except Exception:
                logger.exception("Failed to save chat audit records")

    return StreamingResponse(generate(), media_type="text/event-stream")

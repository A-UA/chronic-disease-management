import json
from collections.abc import AsyncGenerator
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_org, get_current_user, get_db, verify_quota
from app.db.models import Conversation, Message, UsageLog, User
from app.services.chat import RetrievalFilters, build_rag_prompt, extract_statement_citations_structured, retrieve_chunks
from app.services.conversation_context import build_contextual_retrieval_query
from app.services.llm import get_llm_provider
from app.services.query_rewrite import prepare_retrieval_query
from app.services.quota import check_quota_during_stream, update_org_quota

router = APIRouter()


class ChatRequest(BaseModel):
    kb_id: UUID
    conversation_id: UUID
    query: str
    document_ids: list[UUID] | None = None
    file_types: list[str] | None = None


@router.post("")
async def chat_endpoint(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    org_id: UUID = Depends(get_current_org),
    _=Depends(verify_quota),
    db: AsyncSession = Depends(get_db),
):
    filters: RetrievalFilters = {}
    if request.document_ids:
        filters["document_ids"] = request.document_ids
    if request.file_types:
        filters["file_types"] = request.file_types

    retrieval_query = await build_contextual_retrieval_query(db, request.conversation_id, request.query)
    prepared_query = prepare_retrieval_query(retrieval_query)
    chunks = await retrieve_chunks(db, retrieval_query, request.kb_id, org_id, filters=filters or None)
    prompt, citations = build_rag_prompt(request.query, chunks)

    conversation = await db.get(Conversation, request.conversation_id)
    if not conversation:
        conversation = Conversation(
            id=request.conversation_id,
            kb_id=request.kb_id,
            org_id=org_id,
            user_id=current_user.id,
            title=request.query[:50],
        )
        db.add(conversation)

    user_msg = Message(
        conversation_id=conversation.id,
        role="user",
        content=request.query,
        metadata_={"filters": filters or None},
    )
    db.add(user_msg)
    await db.commit()

    llm_provider = get_llm_provider()

    async def generate() -> AsyncGenerator[str, None]:
        yield f"event: meta\ndata: {json.dumps({'citations': citations})}\n\n"

        full_response = ""
        async for chunk_text in llm_provider.stream_text(prompt):
            full_response += chunk_text
            tokens_so_far = (len(prompt) + len(full_response)) // 4
            if not await check_quota_during_stream(org_id, tokens_so_far, db=db):
                yield f"event: error\ndata: {json.dumps({'detail': 'Quota exceeded. Response cut short.'})}\n\n"
                break

            yield f"event: chunk\ndata: {json.dumps({'text': chunk_text})}\n\n"

        prompt_tokens = len(prompt) // 4
        completion_tokens = len(full_response) // 4
        statement_citations = await extract_statement_citations_structured(full_response, citations, llm_provider)
        done_statement_citations = [
            {
                "text": item["text"],
                "citation_refs": [citation["ref"] for citation in item["citations"]],
                "chunk_ids": [citation.get("chunk_id") for citation in item["citations"]],
            }
            for item in statement_citations
        ]

        assistant_msg = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=full_response,
            metadata_={
                "citations": citations,
                "statement_citations": statement_citations,
                "tokens": {"input": prompt_tokens, "output": completion_tokens},
                "filters": filters or None,
                "observability": {
                    "raw_query": request.query,
                    "retrieval_query": prepared_query.retrieval_query,
                    "normalized_query": prepared_query.normalized_query,
                    "retrieved_chunk_count": len(chunks),
                    "citation_count": len(citations),
                    "statement_count": len(statement_citations),
                    "llm_model": llm_provider.model_name,
                },
            },
        )
        db.add(assistant_msg)

        usage = UsageLog(
            org_id=org_id,
            user_id=current_user.id,
            model=llm_provider.model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            action_type="chat",
            resource_id=conversation.id,
        )
        db.add(usage)
        await db.commit()

        await update_org_quota(db, org_id, usage.total_tokens)
        yield f"event: done\ndata: {json.dumps({'tokens': usage.total_tokens, 'statement_citations': done_statement_citations})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

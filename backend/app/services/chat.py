from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from typing import TypedDict
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.db.models import Chunk, Document
from app.services.embeddings import get_embedding_provider
from app.services.query_rewrite import prepare_retrieval_query
from app.services.quota import redis_client
from app.services.reranker import get_reranker_provider

logger = logging.getLogger(__name__)
_DOC_REF_PATTERN = re.compile(r"(?:\[\s*Doc\s*(\d+)\s*\]|\bDoc\s*(\d+)\b)", re.IGNORECASE)
_STATEMENT_BOUNDARY_PATTERN = re.compile(r"\n+|(?<=[。！？.!?])(?=\s*(?:Conclusion:|Evidence:|Uncertainty:))")


class Citation(TypedDict):
    doc_id: str
    chunk_id: str | None
    ref: str
    page: int | None
    chunk_index: int | None
    snippet: str
    source_span: dict[str, int]


class RetrievalFilters(TypedDict, total=False):
    document_ids: list[UUID]
    file_types: list[str]


class StatementCitation(TypedDict):
    text: str
    citations: list[Citation]


@dataclass(slots=True)
class RetrievedChunk:
    chunk: Chunk
    fused_score: float
    final_score: float
    sources: tuple[str, ...]
    vector_rank: int | None = None
    keyword_rank: int | None = None
    rerank_score: float | None = None


def _build_cache_key(query: str, kb_id: UUID, org_id: UUID, filters: RetrievalFilters | None = None) -> str:
    payload = {
        "query": query.lower(),
        "filters": {
            "document_ids": sorted(str(item) for item in filters.get("document_ids", [])) if filters else [],
            "file_types": sorted(filters.get("file_types", [])) if filters else [],
        },
    }
    query_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return f"rag_cache:{org_id}:{kb_id}:{query_hash}"


def _dedupe_sources(existing: tuple[str, ...], source: str) -> tuple[str, ...]:
    if source in existing:
        return existing
    return existing + (source,)


def _apply_retrieval_filters(stmt: Select, filters: RetrievalFilters | None) -> Select:
    if not filters:
        return stmt

    document_ids = filters.get("document_ids") or []
    if document_ids:
        stmt = stmt.where(Chunk.document_id.in_(document_ids))

    file_types = filters.get("file_types") or []
    if file_types:
        stmt = stmt.join(Document, Document.id == Chunk.document_id).where(Document.file_type.in_(file_types))

    return stmt


def _build_snippet_and_span(content: str, max_length: int = 120) -> tuple[str, dict[str, int]]:
    if not content:
        return "", {"start": 0, "end": 0}

    start = 0
    while start < len(content) and content[start].isspace():
        start += 1

    end = len(content)
    while end > start and content[end - 1].isspace():
        end -= 1

    span_end = min(end, start + max_length)
    raw_snippet = content[start:span_end]
    if span_end < end:
        snippet = raw_snippet.rstrip() + "..."
    else:
        snippet = raw_snippet
    return snippet, {"start": start, "end": span_end}


def build_statement_citations(answer_text: str, citations: list[Citation]) -> list[StatementCitation]:
    ref_map = {citation["ref"].lower(): citation for citation in citations}
    statements: list[StatementCitation] = []
    for raw_part in _STATEMENT_BOUNDARY_PATTERN.split(answer_text):
        part = raw_part.strip()
        if not part:
            continue
        refs: list[str] = []
        for match in _DOC_REF_PATTERN.finditer(part):
            doc_number = match.group(1) or match.group(2)
            if doc_number is not None:
                refs.append(f"doc {doc_number}")
        mapped = [ref_map[ref] for ref in refs if ref in ref_map]
        statements.append({"text": part, "citations": mapped})
    return statements


def _serialize_ranked_results(results: list[RetrievedChunk]) -> str:
    payload = []
    for result in results:
        payload.append(
            {
                "chunk_id": str(result.chunk.id),
                "fused_score": result.fused_score,
                "final_score": result.final_score,
                "sources": list(result.sources),
                "vector_rank": result.vector_rank,
                "keyword_rank": result.keyword_rank,
                "rerank_score": result.rerank_score,
            }
        )
    return json.dumps(payload)


async def _load_cached_ranked_results(db: AsyncSession, cached_data: str) -> list[RetrievedChunk] | None:
    cached_payload = json.loads(cached_data)
    if not cached_payload:
        return []

    if isinstance(cached_payload[0], str):
        chunk_ids = [UUID(cid) for cid in cached_payload]
        cached_meta = [{"chunk_id": cid} for cid in cached_payload]
    else:
        chunk_ids = [UUID(item["chunk_id"]) for item in cached_payload]
        cached_meta = cached_payload

    stmt = select(Chunk).where(Chunk.id.in_(chunk_ids))
    result = await db.execute(stmt)
    chunk_by_id = {str(chunk.id): chunk for chunk in result.scalars().all()}

    ranked_results: list[RetrievedChunk] = []
    for item in cached_meta:
        chunk = chunk_by_id.get(item["chunk_id"])
        if chunk is None:
            continue
        ranked_results.append(
            RetrievedChunk(
                chunk=chunk,
                fused_score=float(item.get("fused_score", 0.0)),
                final_score=float(item.get("final_score", item.get("fused_score", 0.0))),
                sources=tuple(item.get("sources", ["cache"])),
                vector_rank=item.get("vector_rank"),
                keyword_rank=item.get("keyword_rank"),
                rerank_score=item.get("rerank_score"),
            )
        )
    return ranked_results


async def retrieve_ranked_chunks(
    db: AsyncSession,
    query: str,
    kb_id: UUID,
    org_id: UUID,
    limit: int = 5,
    filters: RetrievalFilters | None = None,
) -> list[RetrievedChunk]:
    prepared_query = prepare_retrieval_query(query)
    retrieval_query = prepared_query.retrieval_query
    cache_key = _build_cache_key(retrieval_query, kb_id, org_id, filters)

    cached_data = await redis_client.get(cache_key)
    if cached_data:
        try:
            cached_results = await _load_cached_ranked_results(db, cached_data)
            if cached_results is not None:
                return cached_results
        except Exception:
            logger.warning("Failed to load cached ranked results", exc_info=True)

    embedding_provider = get_embedding_provider()
    query_embedding = embedding_provider.embed_query(retrieval_query)
    vector_stmt = (
        select(Chunk)
        .where(Chunk.org_id == org_id, Chunk.kb_id == kb_id)
        .order_by(Chunk.embedding.cosine_distance(query_embedding))
        .limit(limit * 2)
    )
    vector_stmt = _apply_retrieval_filters(vector_stmt, filters)
    vector_res = await db.execute(vector_stmt)
    vector_chunks = list(vector_res.scalars().all())

    keyword_stmt = (
        select(Chunk)
        .where(
            Chunk.org_id == org_id,
            Chunk.kb_id == kb_id,
            Chunk.tsv_content.op("@@")(func.plainto_tsquery("chinese", retrieval_query)),
        )
        .order_by(func.ts_rank(Chunk.tsv_content, func.plainto_tsquery("chinese", retrieval_query)).desc())
        .limit(limit * 2)
    )
    keyword_stmt = _apply_retrieval_filters(keyword_stmt, filters)
    keyword_res = await db.execute(keyword_stmt)
    keyword_chunks = list(keyword_res.scalars().all())

    k = 60
    retrieved_by_id: dict[UUID, RetrievedChunk] = {}

    for rank, chunk in enumerate(vector_chunks):
        retrieved = retrieved_by_id.get(chunk.id)
        if retrieved is None:
            retrieved = RetrievedChunk(chunk=chunk, fused_score=0.0, final_score=0.0, sources=())
            retrieved_by_id[chunk.id] = retrieved
        retrieved.fused_score += 1.0 / (k + rank + 1)
        retrieved.final_score = retrieved.fused_score
        retrieved.vector_rank = rank + 1
        retrieved.sources = _dedupe_sources(retrieved.sources, "vector")

    for rank, chunk in enumerate(keyword_chunks):
        retrieved = retrieved_by_id.get(chunk.id)
        if retrieved is None:
            retrieved = RetrievedChunk(chunk=chunk, fused_score=0.0, final_score=0.0, sources=())
            retrieved_by_id[chunk.id] = retrieved
        retrieved.fused_score += 1.0 / (k + rank + 1)
        retrieved.final_score = retrieved.fused_score
        retrieved.keyword_rank = rank + 1
        retrieved.sources = _dedupe_sources(retrieved.sources, "keyword")

    fused_results = sorted(retrieved_by_id.values(), key=lambda item: item.fused_score, reverse=True)

    try:
        reranker = get_reranker_provider()
        reranked_results = await reranker.rerank(retrieval_query, fused_results, limit)
    except Exception:
        logger.warning("Reranker failed; falling back to fused ranking", exc_info=True)
        reranked_results = fused_results[:limit]
        for result in reranked_results:
            result.final_score = result.fused_score
            result.rerank_score = None

    if reranked_results:
        await redis_client.setex(cache_key, 3600, _serialize_ranked_results(reranked_results))

    return reranked_results


async def retrieve_chunks(
    db: AsyncSession,
    query: str,
    kb_id: UUID,
    org_id: UUID,
    limit: int = 5,
    filters: RetrievalFilters | None = None,
) -> list[Chunk]:
    ranked_results = await retrieve_ranked_chunks(db, query, kb_id, org_id, limit=limit, filters=filters)
    return [result.chunk for result in ranked_results]


def build_rag_prompt(query: str, chunks: list[Chunk], patient_name: str | None = None) -> tuple[str, list[dict[str, Citation]]]:
    context_blocks = []
    citations = []

    for i, chunk in enumerate(chunks):
        content = chunk.content
        if patient_name:
            content = content.replace(patient_name, "[PATIENT]")

        doc_ref = f"Doc {i + 1}"
        snippet, source_span = _build_snippet_and_span(content)
        context_blocks.append(f"[{doc_ref}] (page={chunk.page_number}): {content}")
        citations.append(
            {
                "doc_id": str(chunk.document_id),
                "chunk_id": str(chunk.id) if getattr(chunk, "id", None) is not None else None,
                "ref": doc_ref,
                "page": chunk.page_number,
                "chunk_index": getattr(chunk, "chunk_index", None),
                "snippet": snippet,
                "source_span": source_span,
            }
        )

    context_str = "\n\n".join(context_blocks)

    if patient_name:
        query = query.replace(patient_name, "[PATIENT]")

    prompt = (
        "You are a clinical knowledge assistant. Answer strictly from the provided context.\n"
        "If the context is insufficient or conflicting, state that explicitly and do not invent facts.\n"
        "Answer format:\n"
        "1. Conclusion: one short answer to the user's question, and it must include at least one citation like [Doc 1].\n"
        "2. Evidence: support the conclusion with document refs like [Doc 1], and every evidence sentence must include refs.\n"
        "3. Uncertainty: explain what is missing or uncertain, or write 'None'.\n\n"
        f"Context:\n{context_str}\n\n"
        f"Question: {query}"
    )

    return prompt, citations

import hashlib
import json
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


class Citation(TypedDict):
    doc_id: str
    ref: str
    page: int | None


class RetrievalFilters(TypedDict, total=False):
    document_ids: list[UUID]
    file_types: list[str]


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
            chunk_ids = json.loads(cached_data)
            stmt = select(Chunk).where(Chunk.id.in_([UUID(cid) for cid in chunk_ids]))
            result = await db.execute(stmt)
            cached_chunks = list(result.scalars().all())
            return [
                RetrievedChunk(
                    chunk=chunk,
                    fused_score=0.0,
                    final_score=0.0,
                    sources=("cache",),
                )
                for chunk in cached_chunks
            ]
        except Exception:
            pass

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
            retrieved = RetrievedChunk(
                chunk=chunk,
                fused_score=0.0,
                final_score=0.0,
                sources=(),
            )
            retrieved_by_id[chunk.id] = retrieved

        retrieved.fused_score += 1.0 / (k + rank + 1)
        retrieved.final_score = retrieved.fused_score
        retrieved.vector_rank = rank + 1
        retrieved.sources = _dedupe_sources(retrieved.sources, "vector")

    for rank, chunk in enumerate(keyword_chunks):
        retrieved = retrieved_by_id.get(chunk.id)
        if retrieved is None:
            retrieved = RetrievedChunk(
                chunk=chunk,
                fused_score=0.0,
                final_score=0.0,
                sources=(),
            )
            retrieved_by_id[chunk.id] = retrieved

        retrieved.fused_score += 1.0 / (k + rank + 1)
        retrieved.final_score = retrieved.fused_score
        retrieved.keyword_rank = rank + 1
        retrieved.sources = _dedupe_sources(retrieved.sources, "keyword")

    fused_results = sorted(
        retrieved_by_id.values(),
        key=lambda item: item.fused_score,
        reverse=True,
    )

    reranker = get_reranker_provider()
    reranked_results = await reranker.rerank(retrieval_query, fused_results, limit)

    if reranked_results:
        await redis_client.setex(
            cache_key,
            3600,
            json.dumps([str(result.chunk.id) for result in reranked_results]),
        )

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
        context_blocks.append(f"[{doc_ref}]: {content}")
        citations.append(
            {
                "doc_id": str(chunk.document_id),
                "ref": doc_ref,
                "page": chunk.page_number,
            }
        )

    context_str = "\n\n".join(context_blocks)

    if patient_name:
        query = query.replace(patient_name, "[PATIENT]")

    prompt = (
        "You are a helpful AI assistant. Answer the user's question based strictly on the following context. "
        "The context belongs to a patient (referred to as [PATIENT]).\n"
        "If the answer is not in the context, say you don't know.\n\n"
        f"Context:\n{context_str}\n\n"
        f"Question: {query}"
    )

    return prompt, citations

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypedDict, Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.core.config import settings
from app.db.models import Chunk, Document
from app.plugins.provider_compat import registry
from app.modules.rag.query_rewrite import prepare_retrieval_query
from app.modules.system.quota import redis_client
from app.telemetry.tracing import trace_span

if TYPE_CHECKING:
    from app.plugins.llm.base import LLMPlugin as LLMProvider

logger = logging.getLogger(__name__)
_DOC_REF_PATTERN = re.compile(
    r"(?:\[\s*Doc\s*(\d+)\s*\]|\bDoc\s*(\d+)\b)", re.IGNORECASE
)
_STATEMENT_BOUNDARY_PATTERN = re.compile(
    r"\n+|(?<=[。！？.!?])(?=\s*(?:Conclusion:|Evidence:|Uncertainty:))"
)


class Citation(TypedDict):
    doc_id: str
    chunk_id: str | None
    ref: str
    page: int | None
    chunk_index: int | None
    snippet: str
    source_span: dict[str, int]


class RetrievalFilters(TypedDict, total=False):
    document_ids: list[int]
    file_types: list[str]
    patient_id: int | None
    metadata: dict[str, Any]


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


def _build_cache_key(
    query: str,
    kb_id: int,
    org_id: int,
    user_id: int,
    filters: RetrievalFilters | None = None,
) -> str:
    """增强版 Cache Key：包含用户 ID 和更细粒度的过滤条件，防止越权缓存命中"""
    payload = {
        "query": query.lower(),
        "user_id": str(user_id),
        "filters": {
            "document_ids": sorted(
                str(item) for item in filters.get("document_ids", [])
            )
            if filters
            else [],
            "file_types": sorted(filters.get("file_types", [])) if filters else [],
            "patient_id": str(filters.get("patient_id"))
            if filters and filters.get("patient_id")
            else None,
            "metadata": filters.get("metadata") if filters else {},
        },
    }
    query_hash = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()
    ).hexdigest()
    return f"rag_cache:{org_id}:{kb_id}:{query_hash}"


async def condense_query(
    query: str, history: list[dict[str, str]], llm_provider: LLMProvider
) -> str:
    """将对话历史与当前问题压缩为一个独立的检索词（Query Condensing）"""
    if not history:
        return query

    history_str = "\n".join([f"{m['role']}: {m['content']}" for m in history[-5:]])
    prompt = (
        "Given the following conversation and a follow-up question, rephrase the follow-up "
        "question to be a standalone question that can be used for search. "
        "Do not answer the question, just return the standalone question.\n\n"
        f"Chat History:\n{history_str}\n"
        f"Follow-up Question: {query}\n"
        "Standalone Question:"
    )

    try:
        condensed = await llm_provider.complete_text(prompt)
        return condensed.strip() if condensed else query
    except Exception:
        logger.warning("Query condensation failed; using raw query")
        return query


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
    patient_id = filters.get("patient_id")
    if file_types or patient_id:
        stmt = stmt.join(Document, Document.id == Chunk.document_id)
    if file_types:
        stmt = stmt.where(Document.file_type.in_(file_types))
    if patient_id:
        stmt = stmt.where(Document.patient_id == patient_id)

    metadata_filters = filters.get("metadata") or {}
    for key, value in metadata_filters.items():
        if key.endswith("__in") and isinstance(value, list):
            base_key = key[:-4]
            from sqlalchemy import or_

            stmt = stmt.where(
                or_(*(Chunk.metadata_.contains({base_key: v}) for v in value))
            )
        elif key.endswith("__gt"):
            base_key = key[:-4]
            stmt = stmt.where(
                func.cast(Chunk.metadata_[base_key].astext, func.float) > value
            )
        else:
            stmt = stmt.where(Chunk.metadata_.contains({key: value}))

    return stmt


def _build_snippet_and_span(
    content: str, max_length: int = 120
) -> tuple[str, dict[str, int]]:
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


def build_statement_citations(
    answer_text: str, citations: list[Citation]
) -> list[StatementCitation]:
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


async def extract_statement_citations_structured(
    answer_text: str,
    citations: list[Citation],
    llm_provider: LLMProvider,
) -> list[StatementCitation]:
    if not answer_text.strip():
        return []
    if not citations:
        return build_statement_citations(answer_text, citations)

    citation_refs = [
        {
            "ref": citation["ref"],
            "doc_id": citation["doc_id"],
            "chunk_id": citation.get("chunk_id"),
            "page": citation.get("page"),
        }
        for citation in citations
    ]
    prompt = (
        "Map each statement in the answer to the most relevant citation refs. "
        'Return strict JSON with shape {"statements":[{"text":"...","refs":["Doc 1"]}]}. '
        "Do not invent refs outside the provided citation list.\n\n"
        f"Available citations: {json.dumps(citation_refs, ensure_ascii=False)}\n"
        f"Answer: {answer_text}"
    )
    try:
        completion = await llm_provider.complete_text(prompt)
        parsed = json.loads(completion or "{}")
        items = parsed.get("statements", [])
        ref_map = {citation["ref"].lower(): citation for citation in citations}
        structured: list[StatementCitation] = []
        for item in items:
            text = (item.get("text") or "").strip()
            refs = [str(ref).lower() for ref in item.get("refs", [])]
            mapped = [ref_map[ref] for ref in refs if ref in ref_map]
            if text:
                structured.append({"text": text, "citations": mapped})
        if structured:
            return structured
    except Exception:
        logger.warning(
            "Structured statement citation extraction failed; falling back to regex mapping",
            exc_info=True,
        )

    return build_statement_citations(answer_text, citations)


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


async def _load_cached_ranked_results(
    db: AsyncSession, cached_data: str
) -> list[RetrievedChunk] | None:
    try:
        cached_meta = json.loads(cached_data)
        if not cached_meta:
            return []

        chunk_ids = [int(item["chunk_id"]) for item in cached_meta]
        stmt = select(Chunk).where(Chunk.id.in_(chunk_ids))
        result = await db.execute(stmt)
        chunk_by_id = {str(chunk.id): chunk for chunk in result.scalars().all()}

        ranked_results: list[RetrievedChunk] = []
        for item in cached_meta:
            chunk = chunk_by_id.get(item["chunk_id"])
            if chunk is None:
                return None
            ranked_results.append(
                RetrievedChunk(
                    chunk=chunk,
                    fused_score=float(item.get("fused_score", 0.0)),
                    final_score=float(item.get("final_score", 0.0)),
                    sources=tuple(item.get("sources", ["cache"])),
                    vector_rank=item.get("vector_rank"),
                    keyword_rank=item.get("keyword_rank"),
                    rerank_score=item.get("rerank_score"),
                )
            )
        return ranked_results
    except Exception:
        return None


async def expand_query(
    query: str, history: list[dict[str, str]], llm_provider: LLMProvider
) -> list[str]:
    """将原始查询扩展为多个不同维度的检索词（仅对复杂查询执行）"""
    # 简单查询跳过扩展：短查询或不含问号的陈述句
    if len(query) < 15 or not any(c in query for c in '?？吗呢什么怎么如何为什么'):
        return [query]

    history_str = (
        "\n".join([f"{m['role']}: {m['content']}" for m in history[-3:]])
        if history
        else "None"
    )
    prompt = (
        "You are an AI language model assistant. Your task is to generate 3 "
        "different versions of the given user question to retrieve relevant documents from a vector database. "
        "By generating multiple perspectives on the user query, your goal is to help "
        "the user overcome some of the limitations of the distance-based similarity search. "
        "Provide these alternative questions separated by newlines. "
        "Do not include any other text.\n\n"
        f"Conversation History: {history_str}\n"
        f"Original question: {query}\n"
    )
    try:
        completion = await llm_provider.complete_text(prompt)
        queries = [q.strip() for q in completion.split("\n") if q.strip()]
        # 总是包含原始查询或压缩后的查询
        return queries[:3]
    except Exception:
        logger.warning("Query expansion failed; using original query")
        return [query]


async def retrieve_ranked_chunks(
    db: AsyncSession,
    query: str,
    kb_id: int,
    org_id: int,
    user_id: int,
    limit: int = 5,
    filters: RetrievalFilters | None = None,
    history: list[dict[str, str]] | None = None,
    llm_provider: LLMProvider | None = None,
) -> list[RetrievedChunk]:
    with trace_span("rag.retrieve_ranked_chunks", {"kb_id": kb_id, "query_len": len(query)}):
        # 查询压缩（仅当有历史上下文时）
        search_query = query
        if history and llm_provider:
            with trace_span("rag.condense_query"):
                search_query = await condense_query(query, history, llm_provider)

        # 查询复杂度判断：短查询或简单查询跳过 Multi-Query 扩展
        if llm_provider:
            with trace_span("rag.expand_query"):
                all_queries = await expand_query(search_query, history or [], llm_provider)
            if search_query not in all_queries:
                all_queries.append(search_query)
        else:
            all_queries = [search_query]

        # 2. 缓存检查 (针对主查询)
        cache_key = _build_cache_key(search_query, kb_id, org_id, user_id, filters)
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            cached_results = await _load_cached_ranked_results(db, cached_data)
            if cached_results:
                return cached_results

        # 3. 多路检索
        embedding_provider = registry.get_embedding()
        retrieved_by_id: dict[int, RetrievedChunk] = {}

        vector_weight = getattr(settings, "RAG_VECTOR_WEIGHT", 0.7)
        keyword_weight = getattr(settings, "RAG_KEYWORD_WEIGHT", 0.3)
        k_rrf = getattr(settings, "RAG_RRF_K", 60)

        async def _single_query_search(q: str):
            prepared = prepare_retrieval_query(q)
            rq = prepared.retrieval_query

            # 向量检索
            with trace_span("rag.vector_search"):
                emb = await embedding_provider.embed_query(rq)
                v_stmt = (
                    select(Chunk)
                    .where(Chunk.org_id == org_id, Chunk.kb_id == kb_id)
                    .order_by(Chunk.embedding.cosine_distance(emb))
                    .limit(limit * 2)
                )
                v_stmt = _apply_retrieval_filters(v_stmt, filters)

            # 关键词检索
            with trace_span("rag.keyword_search"):
                k_stmt = (
                    select(Chunk)
                    .where(
                        Chunk.org_id == org_id,
                        Chunk.kb_id == kb_id,
                        Chunk.tsv_content.op("@@")(func.plainto_tsquery("simple", rq)),
                    )
                    .order_by(
                        func.ts_rank(Chunk.tsv_content, func.plainto_tsquery("simple", rq)).desc()
                    )
                    .limit(limit * 2)
                )
                k_stmt = _apply_retrieval_filters(k_stmt, filters)

            v_res, k_res = await asyncio.gather(db.execute(v_stmt), db.execute(k_stmt))
            return list(v_res.scalars().all()), list(k_res.scalars().all()), rq

        # 并行执行所有扩展查询
        with trace_span("rag.multi_query_search", {"query_count": len(all_queries)}):
            search_tasks = [_single_query_search(q) for q in all_queries]
            all_res = await asyncio.gather(*search_tasks)

        # 4. RRF 融合
        with trace_span("rag.rrf_fusion"):
            for v_chunks, k_chunks, rq in all_res:
                for rank, chunk in enumerate(v_chunks):
                    item = retrieved_by_id.setdefault(
                        chunk.id,
                        RetrievedChunk(chunk=chunk, fused_score=0.0, final_score=0.0, sources=()),
                    )
                    item.fused_score += vector_weight / (k_rrf + rank + 1)
                    item.vector_rank = min(item.vector_rank or 999, rank + 1)
                    item.sources = _dedupe_sources(item.sources, "vector")

                for rank, chunk in enumerate(k_chunks):
                    item = retrieved_by_id.setdefault(
                        chunk.id,
                        RetrievedChunk(chunk=chunk, fused_score=0.0, final_score=0.0, sources=()),
                    )
                    item.fused_score += keyword_weight / (k_rrf + rank + 1)
                    item.keyword_rank = min(item.keyword_rank or 999, rank + 1)
                    item.sources = _dedupe_sources(item.sources, "keyword")

        # 排序与重排
        min_score_threshold = getattr(settings, "RAG_MIN_SCORE_THRESHOLD", 0.0)
        fused_results = sorted(
            [r for r in retrieved_by_id.values() if r.fused_score >= min_score_threshold],
            key=lambda x: x.fused_score,
            reverse=True,
        )

        with trace_span("rag.rerank", {"candidates": len(fused_results)}):
            try:
                reranker = registry.get_reranker()
                reranked_results = await reranker.rerank(search_query, fused_results, limit)
            except Exception:
                logger.warning("Reranker failed; falling back to fused ranking")
                reranked_results = fused_results[:limit]
                for r in reranked_results:
                    r.final_score = r.fused_score

        # 缓存主查询结果
        if reranked_results:
            await redis_client.setex(
                cache_key,
                getattr(settings, "RAG_CACHE_TTL", 3600),
                _serialize_ranked_results(reranked_results),
            )

        return reranked_results


async def retrieve_chunks(
    db: AsyncSession,
    query: str,
    kb_id: int,
    org_id: int,
    user_id: int,
    limit: int = 5,
    filters: RetrievalFilters | None = None,
    history: list[dict[str, str]] | None = None,
    llm_provider: LLMProvider | None = None,
) -> list[Chunk]:
    ranked = await retrieve_ranked_chunks(
        db, query, kb_id, org_id, user_id, limit, filters, history, llm_provider
    )
    return [r.chunk for r in ranked]


def build_rag_prompt(
    query: str, chunks: list[Chunk], patient_name: str | None = None,
    language: str = "zh",
) -> tuple[str, list[dict[str, Citation]]]:
    context_blocks = []
    citations = []
    for i, chunk in enumerate(chunks):
        content = chunk.content
        if patient_name:
            content = content.replace(patient_name, "[PATIENT]")
        doc_ref = f"Doc {i + 1}"
        snippet, span = _build_snippet_and_span(content)
        context_blocks.append(f"[{doc_ref}] (page={chunk.page_number}): {content}")
        citations.append(
            {
                "doc_id": str(chunk.document_id),
                "chunk_id": str(chunk.id),
                "ref": doc_ref,
                "page": chunk.page_number,
                "snippet": snippet,
                "source_span": span,
            }
        )

    context_str = "\n\n".join(context_blocks)
    if patient_name:
        query = query.replace(patient_name, "[PATIENT]")

    if language == "zh":
        prompt = (
            "你是一个慢病管理临床推理助手。请严格基于以下「参考资料」回答问题。\n\n"
            "**规则：**\n"
            "1. 只使用参考资料中的信息，不得编造任何内容。\n"
            "2. 使用 **[Doc n]** 标注引用来源（n 为参考资料编号）。\n"
            "3. 若参考资料不足以回答，明确说明信息缺失，不要臆测。\n"
            "4. 使用中文回答。\n\n"
            "**格式要求：**\n"
            "- 使用 Markdown 格式输出，包括标题、列表、粗体等。\n"
            "- 先给出简洁结论，再展开详细分析。\n"
            "- 证据部分使用列表逐条列出，每条引用 [Doc n]。\n"
            "- 若存在不确定性，单独说明。\n\n"
            f"**参考资料：**\n{context_str}\n\n"
            f"**问题：** {query}\n\n"
        )
    else:
        prompt = (
            "You are a Chronic Disease Management Clinical Reasoning Assistant. "
            "Answer ONLY based on the provided Context.\n\n"
            "**Rules:**\n"
            "1. Use ONLY information from the Context. Never fabricate.\n"
            "2. Cite sources using **[Doc n]** notation.\n"
            "3. If Context is insufficient, clearly state what is missing.\n\n"
            "**Format:**\n"
            "- Use Markdown: headings, lists, bold, etc.\n"
            "- Lead with a concise conclusion, then expand with analysis.\n"
            "- List evidence with citations [Doc n].\n"
            "- Note any uncertainties separately.\n\n"
            f"**Context:**\n{context_str}\n\n"
            f"**Question:** {query}\n\n"
        )
    return prompt, citations



from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypedDict

import redis.asyncio as redis

from app.ai.rag.query_rewrite import prepare_retrieval_query
from app.config import settings
from app.plugins.registry import PluginRegistry

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
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


@dataclass
class RetrievedChunkContent:
    """Milvus 返回的结构化 Chunk 承载类。替代了原有依赖 Postgres 的 Chunk ORM模型"""
    id: int | str
    document_id: int
    content: str
    page_number: int | None = None
    section_title: str | None = None
    token_count: int | None = None


@dataclass(slots=True)
class RetrievedChunk:
    chunk: RetrievedChunkContent
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
    """增强版 Cache Key"""
    payload = {
        "query": query.lower(),
        "user_id": str(user_id),
        "filters": {
            "document_ids": sorted(
                str(item) for item in filters.get("document_ids", [])
            )
            if filters
            else [],
        },
    }
    query_hash = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()
    ).hexdigest()
    return f"rag_cache:{org_id}:{kb_id}:{query_hash}"


async def condense_query(
    query: str, history: list[dict[str, str]], llm_provider: LLMProvider
) -> str:
    """将对话历史与当前问题压缩为一个独立的检索词"""
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
            "chunk_id": getattr(citation, "chunk_id", ""),
            "page": getattr(citation, "page", None),
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
        pass

    return build_statement_citations(answer_text, citations)


def _serialize_ranked_results(results: list[RetrievedChunk]) -> str:
    payload = []
    for result in results:
        payload.append(
            {
                "chunk_id": str(result.chunk.id),
                "document_id": result.chunk.document_id,
                "content": result.chunk.content,
                "page_number": result.chunk.page_number,
                "section_title": result.chunk.section_title,
                "fused_score": result.fused_score,
                "final_score": result.final_score,
                "sources": list(result.sources),
                "vector_rank": result.vector_rank,
                "keyword_rank": result.keyword_rank,
                "rerank_score": result.rerank_score,
            }
        )
    return json.dumps(payload)


async def _load_cached_ranked_results(cached_data: str) -> list[RetrievedChunk] | None:
    try:
        cached_meta = json.loads(cached_data)
        if not cached_meta:
            return []

        ranked_results: list[RetrievedChunk] = []
        for item in cached_meta:
            chunk = RetrievedChunkContent(
                id=item["chunk_id"],
                document_id=item["document_id"],
                content=item["content"],
                page_number=item.get("page_number"),
                section_title=item.get("section_title"),
                token_count=item.get("token_count"),
            )
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
    """将原始查询扩展为多个不同维度的检索词"""
    if len(query) < 15 or not any(c in query for c in "?？吗呢什么怎么如何为什么"):
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
        return queries[:3]
    except Exception:
        return [query]


async def retrieve_ranked_chunks(
    milvus_store,
    query: str,
    kb_id: int,
    org_id: int,
    user_id: int,
    limit: int = 5,
    filters: RetrievalFilters | None = None,
    history: list[dict[str, str]] | None = None,
    llm_provider: LLMProvider | None = None,
) -> list[RetrievedChunk]:
    with trace_span(
        "rag.retrieve_ranked_chunks", {"kb_id": kb_id, "query_len": len(query)}
    ):
        search_query = query
        if history and llm_provider:
            with trace_span("rag.condense_query"):
                search_query = await condense_query(query, history, llm_provider)

        if llm_provider:
            with trace_span("rag.expand_query"):
                all_queries = await expand_query(
                    search_query, history or [], llm_provider
                )
            if search_query not in all_queries:
                all_queries.append(search_query)
        else:
            all_queries = [search_query]

        cache_key = _build_cache_key(search_query, kb_id, org_id, user_id, filters)
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            cached_results = await _load_cached_ranked_results(cached_data)
            if cached_results is not None:
                return cached_results

        embedding_provider = PluginRegistry.get("embedding")
        retrieved_by_id: dict[str, RetrievedChunk] = {}

        async def _single_query_search(q: str):
            prepared = prepare_retrieval_query(q)
            rq = prepared.retrieval_query

            with trace_span("rag.vector_search"):
                emb = await embedding_provider.embed_query(rq)
                milvus_filters = {"kb_id": kb_id}
                if filters and filters.get("document_ids"):
                    milvus_filters["document_id"] = filters["document_ids"]

                v_res = await milvus_store.search("kb", emb, limit=limit * 2, filters=milvus_filters)
            return v_res, rq

        with trace_span("rag.multi_query_search", {"query_count": len(all_queries)}):
            search_tasks = [_single_query_search(q) for q in all_queries]
            all_res = await asyncio.gather(*search_tasks)

        # 归并计算 Score
        for v_res, rq in all_res:
            for rank, hit in enumerate(v_res):
                payload = hit["payload"]
                chunk_id = str(hit["id"])

                item = retrieved_by_id.setdefault(
                    chunk_id,
                    RetrievedChunk(
                        chunk=RetrievedChunkContent(
                            id=chunk_id,
                            document_id=payload.get("document_id", 0),
                            content=payload.get("content", ""),
                            page_number=payload.get("page_number", 0),
                            section_title=payload.get("section_title", ""),
                            token_count=payload.get("token_count", 0),
                        ),
                        fused_score=0.0,
                        final_score=0.0,
                        sources=(),
                    ),
                )

                # 直接记录最高的分数作为融合依据
                sim_score = hit["score"]
                item.fused_score = max(item.fused_score, sim_score)
                item.vector_rank = min(item.vector_rank or 999, rank + 1)
                item.sources = _dedupe_sources(item.sources, "vector")

        min_score_threshold = getattr(settings, "RAG_MIN_SCORE_THRESHOLD", 0.0)
        fused_results = sorted(
            [r for r in retrieved_by_id.values() if r.fused_score >= min_score_threshold],
            key=lambda x: x.fused_score,
            reverse=True,
        )

        with trace_span("rag.rerank", {"candidates": len(fused_results)}):
            try:
                reranker = PluginRegistry.get("reranker")
                if reranker and hasattr(reranker, "rerank"):
                    reranked_results = await reranker.rerank(
                        search_query, fused_results, limit
                    )
                else:
                    reranked_results = fused_results[:limit]
                    for r in reranked_results:
                        r.final_score = r.fused_score
            except Exception:
                logger.warning("Reranker failed; falling back to vector ranking")
                reranked_results = fused_results[:limit]
                for r in reranked_results:
                    r.final_score = r.fused_score

        if reranked_results:
            await redis_client.setex(
                cache_key,
                getattr(settings, "RAG_CACHE_TTL", 3600),
                _serialize_ranked_results(reranked_results),
            )

        return reranked_results


async def retrieve_chunks(
    milvus_store,
    query: str,
    kb_id: int,
    org_id: int,
    user_id: int,
    limit: int = 5,
    filters: RetrievalFilters | None = None,
    history: list[dict[str, str]] | None = None,
    llm_provider: LLMProvider | None = None,
) -> list[RetrievedChunkContent]:
    ranked = await retrieve_ranked_chunks(
        milvus_store, query, kb_id, org_id, user_id, limit, filters, history, llm_provider
    )
    return [r.chunk for r in ranked]


def build_rag_prompt(
    query: str,
    chunks: list[RetrievedChunkContent],
    patient_name: str | None = None,
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

"""Chat 检索管线测试：retrieve_ranked_chunks / retrieve_chunks / build_rag_prompt / citations"""
import json
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.chat import (
    retrieve_ranked_chunks,
    retrieve_chunks,
    build_rag_prompt,
    build_statement_citations,
    extract_statement_citations_structured,
    condense_query,
)


def _chunk(content="诊断：2型糖尿病。", page=1):
    c = MagicMock()
    c.id = uuid4()
    c.document_id = uuid4()
    c.page_number = page
    c.content = content
    c.chunk_index = 0
    return c


def _db_returning(*chunk_lists):
    """构建 mock db，对应 vector / keyword 两次 execute"""
    results = []
    for cl in chunk_lists:
        r = MagicMock()
        r.scalars.return_value.all.return_value = cl
        results.append(r)
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=results)
    return db


def _embed_provider(dim=3):
    p = MagicMock()
    p.embed_query = AsyncMock(return_value=[0.1] * dim)
    return p


# ── retrieve_ranked_chunks ──

@pytest.mark.asyncio
async def test_ranked_chunks_fusion_and_sources():
    a, b = _chunk(), _chunk()
    db = _db_returning([a, b], [b])
    reranker = AsyncMock()
    reranker.rerank = AsyncMock(side_effect=lambda q, r, l: r[:l])

    with patch("app.services.chat.registry.get_embedding", return_value=_embed_provider()), \
         patch("app.services.chat.registry.get_reranker", return_value=reranker), \
         patch("app.services.chat.redis_client.get", AsyncMock(return_value=None)), \
         patch("app.services.chat.redis_client.setex", AsyncMock()):
        results = await retrieve_ranked_chunks(db, "q", uuid4(), uuid4(), uuid4())

    assert len(results) == 2
    # b 出现在 vector + keyword，分数应更高
    assert results[0].chunk is b
    assert "vector" in results[0].sources and "keyword" in results[0].sources


@pytest.mark.asyncio
async def test_ranked_chunks_fallback_on_reranker_error():
    a = _chunk()
    db = _db_returning([a], [])
    reranker = AsyncMock()
    reranker.rerank = AsyncMock(side_effect=RuntimeError("down"))

    with patch("app.services.chat.registry.get_embedding", return_value=_embed_provider()), \
         patch("app.services.chat.registry.get_reranker", return_value=reranker), \
         patch("app.services.chat.redis_client.get", AsyncMock(return_value=None)), \
         patch("app.services.chat.redis_client.setex", AsyncMock()):
        results = await retrieve_ranked_chunks(db, "q", uuid4(), uuid4(), uuid4())

    assert len(results) == 1
    assert results[0].final_score == results[0].fused_score


@pytest.mark.asyncio
async def test_ranked_chunks_uses_cache():
    a, b = _chunk(), _chunk()
    cached = json.dumps([
        {"chunk_id": str(b.id), "fused_score": 0.9, "final_score": 0.95,
         "sources": ["vector", "keyword"], "vector_rank": 1, "keyword_rank": 1, "rerank_score": 0.95},
        {"chunk_id": str(a.id), "fused_score": 0.3, "final_score": 0.3,
         "sources": ["vector"], "vector_rank": 2, "keyword_rank": None, "rerank_score": None},
    ])
    r = MagicMock()
    r.scalars.return_value.all.return_value = [a, b]
    db = AsyncMock()
    db.execute = AsyncMock(return_value=r)

    with patch("app.services.chat.redis_client.get", AsyncMock(return_value=cached)):
        results = await retrieve_ranked_chunks(db, "q", uuid4(), uuid4(), uuid4())

    assert results[0].chunk.id == b.id
    assert results[0].final_score == 0.95


@pytest.mark.asyncio
async def test_ranked_chunks_with_filters():
    doc_id = uuid4()
    stmts = []

    async def capture_execute(stmt):
        stmts.append(stmt)
        r = MagicMock()
        r.scalars.return_value.all.return_value = []
        return r

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=capture_execute)
    reranker = AsyncMock()
    reranker.rerank = AsyncMock(return_value=[])

    with patch("app.services.chat.registry.get_embedding", return_value=_embed_provider()), \
         patch("app.services.chat.registry.get_reranker", return_value=reranker), \
         patch("app.services.chat.redis_client.get", AsyncMock(return_value=None)), \
         patch("app.services.chat.redis_client.setex", AsyncMock()):
        await retrieve_ranked_chunks(
            db, "q", uuid4(), uuid4(), uuid4(),
            filters={"document_ids": [doc_id], "file_types": ["pdf"]},
        )

    assert len(stmts) == 2
    for s in stmts:
        sql = str(s)
        assert "chunks.document_id" in sql
        assert "documents.file_type" in sql


# ── retrieve_chunks ──

@pytest.mark.asyncio
async def test_retrieve_chunks_returns_raw_chunks():
    a = _chunk()
    db = _db_returning([a], [])
    reranker = AsyncMock()
    reranker.rerank = AsyncMock(side_effect=lambda q, r, l: r[:l])

    with patch("app.services.chat.registry.get_embedding", return_value=_embed_provider()), \
         patch("app.services.chat.registry.get_reranker", return_value=reranker), \
         patch("app.services.chat.redis_client.get", AsyncMock(return_value=None)), \
         patch("app.services.chat.redis_client.setex", AsyncMock()):
        chunks = await retrieve_chunks(db, "q", uuid4(), uuid4(), uuid4())

    assert chunks == [a]


# ── build_rag_prompt ──

def test_build_rag_prompt_citations():
    c = _chunk("诊断：2型糖尿病。", page=3)
    prompt, citations = build_rag_prompt("问题", [c])
    assert "诊断：2型糖尿病" in prompt
    assert "page=3" in prompt
    assert len(citations) == 1
    assert citations[0]["page"] == 3
    assert citations[0]["doc_id"] == str(c.document_id)


def test_build_rag_prompt_multiple_chunks():
    c1 = _chunk("A", page=1)
    c2 = _chunk("B", page=2)
    prompt, citations = build_rag_prompt("q", [c1, c2])
    assert "[Doc 1]" in prompt and "[Doc 2]" in prompt
    assert len(citations) == 2


# ── statement citations ──

def test_build_statement_citations_regex():
    answer = "Conclusion: 建议复查 [Doc 1]。\nEvidence: 数据支持 [Doc 2]。"
    citations = [
        {"ref": "Doc 1", "doc_id": "d1", "chunk_id": "c1", "page": 1, "snippet": "s", "source_span": {}},
        {"ref": "Doc 2", "doc_id": "d2", "chunk_id": "c2", "page": 2, "snippet": "s", "source_span": {}},
    ]
    result = build_statement_citations(answer, citations)
    assert len(result) >= 2
    assert any(s["citations"] for s in result)


@pytest.mark.asyncio
async def test_extract_structured_citations_uses_llm():
    llm = MagicMock()
    llm.complete_text = AsyncMock(
        return_value='{"statements":[{"text":"建议复查","refs":["Doc 1"]}]}'
    )
    citations = [
        {"ref": "Doc 1", "doc_id": "d1", "chunk_id": "c1", "page": 1, "snippet": "s", "source_span": {}},
    ]
    result = await extract_statement_citations_structured("建议复查", citations, llm)
    assert len(result) == 1
    assert result[0]["text"] == "建议复查"
    assert result[0]["citations"][0]["doc_id"] == "d1"


@pytest.mark.asyncio
async def test_extract_structured_citations_fallback():
    llm = MagicMock()
    llm.complete_text = AsyncMock(side_effect=RuntimeError("fail"))
    citations = [
        {"ref": "Doc 1", "doc_id": "d1", "chunk_id": "c1", "page": 1, "snippet": "s", "source_span": {}},
    ]
    result = await extract_statement_citations_structured("text [Doc 1]", citations, llm)
    assert isinstance(result, list)


# ── condense query ──

@pytest.mark.asyncio
async def test_condense_query_with_history():
    llm = MagicMock()
    llm.complete_text = AsyncMock(return_value="独立问题")
    r = await condense_query("追问", [{"role": "user", "content": "原始"}], llm)
    assert r == "独立问题"


@pytest.mark.asyncio
async def test_condense_query_no_history():
    r = await condense_query("问题", [], MagicMock())
    assert r == "问题"


@pytest.mark.asyncio
async def test_condense_query_llm_failure():
    llm = MagicMock()
    llm.complete_text = AsyncMock(side_effect=RuntimeError("fail"))
    r = await condense_query("问题", [{"role": "user", "content": "x"}], llm)
    assert r == "问题"

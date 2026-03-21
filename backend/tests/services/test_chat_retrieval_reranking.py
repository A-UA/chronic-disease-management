import json
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.chat import retrieve_ranked_chunks


def _build_chunk():
    chunk = MagicMock()
    chunk.id = uuid4()
    chunk.document_id = uuid4()
    chunk.page_number = 1
    chunk.content = "诊断：2 型糖尿病。"
    return chunk


@pytest.mark.asyncio
async def test_retrieve_ranked_chunks_returns_structured_scores_and_sources():
    kb_id = uuid4()
    org_id = uuid4()

    chunk_a = _build_chunk()
    chunk_b = _build_chunk()

    vector_result = MagicMock()
    vector_result.scalars.return_value.all.return_value = [chunk_a, chunk_b]

    keyword_result = MagicMock()
    keyword_result.scalars.return_value.all.return_value = [chunk_b]

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[vector_result, keyword_result])

    provider = MagicMock()
    provider.embed_query.return_value = [0.1] * 3

    reranker = AsyncMock()
    reranker.rerank = AsyncMock(side_effect=lambda query, results, limit: results[:limit])

    with patch("app.services.chat.get_embedding_provider", return_value=provider), patch(
        "app.services.chat.get_reranker_provider",
        return_value=reranker,
    ), patch("app.services.chat.redis_client.get", AsyncMock(return_value=None)), patch(
        "app.services.chat.redis_client.setex",
        AsyncMock(return_value=True),
    ):
        results = await retrieve_ranked_chunks(mock_db, "血糖高怎么办？", kb_id, org_id)

    assert len(results) == 2
    assert results[0].chunk is chunk_b
    assert results[0].sources == ("vector", "keyword")
    assert results[0].fused_score > results[1].fused_score
    assert results[0].final_score == results[0].fused_score


@pytest.mark.asyncio
async def test_retrieve_ranked_chunks_calls_reranker_with_retrieval_query():
    kb_id = uuid4()
    org_id = uuid4()

    chunk = _build_chunk()

    vector_result = MagicMock()
    vector_result.scalars.return_value.all.return_value = [chunk]

    keyword_result = MagicMock()
    keyword_result.scalars.return_value.all.return_value = []

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[vector_result, keyword_result])

    provider = MagicMock()
    provider.embed_query.return_value = [0.1] * 3

    reranker = AsyncMock()
    reranker.rerank = AsyncMock(side_effect=lambda query, results, limit: results[:limit])

    with patch("app.services.chat.get_embedding_provider", return_value=provider), patch(
        "app.services.chat.get_reranker_provider",
        return_value=reranker,
    ), patch("app.services.chat.redis_client.get", AsyncMock(return_value=None)), patch(
        "app.services.chat.redis_client.setex",
        AsyncMock(return_value=True),
    ):
        await retrieve_ranked_chunks(mock_db, "  血糖高怎么办？\n\n", kb_id, org_id)

    reranker.rerank.assert_awaited_once()
    rerank_query, rerank_results, rerank_limit = reranker.rerank.await_args.args
    assert rerank_query == "血糖高怎么办?"
    assert len(rerank_results) == 1
    assert rerank_results[0].sources == ("vector",)
    assert rerank_limit == 5


@pytest.mark.asyncio
async def test_retrieve_ranked_chunks_applies_metadata_filters_to_queries():
    kb_id = uuid4()
    org_id = uuid4()
    document_id = uuid4()

    vector_result = MagicMock()
    vector_result.scalars.return_value.all.return_value = []

    keyword_result = MagicMock()
    keyword_result.scalars.return_value.all.return_value = []

    statements = []

    async def execute(stmt):
        statements.append(stmt)
        if len(statements) == 1:
            return vector_result
        return keyword_result

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=execute)

    provider = MagicMock()
    provider.embed_query.return_value = [0.1] * 3

    reranker = AsyncMock()
    reranker.rerank = AsyncMock(return_value=[])

    with patch("app.services.chat.get_embedding_provider", return_value=provider), patch(
        "app.services.chat.get_reranker_provider",
        return_value=reranker,
    ), patch("app.services.chat.redis_client.get", AsyncMock(return_value=None)), patch(
        "app.services.chat.redis_client.setex",
        AsyncMock(return_value=True),
    ):
        await retrieve_ranked_chunks(
            mock_db,
            "血糖高怎么办？",
            kb_id,
            org_id,
            filters={"document_ids": [document_id], "file_types": ["pdf"]},
        )

    assert len(statements) == 2
    assert "documents.file_type" in str(statements[0])
    assert "chunks.document_id" in str(statements[0])
    assert "documents.file_type" in str(statements[1])
    assert "chunks.document_id" in str(statements[1])


@pytest.mark.asyncio
async def test_retrieve_ranked_chunks_preserves_cached_order_and_scores():
    kb_id = uuid4()
    org_id = uuid4()

    chunk_a = _build_chunk()
    chunk_b = _build_chunk()

    cached_payload = [
        {
            "chunk_id": str(chunk_b.id),
            "fused_score": 0.9,
            "final_score": 0.95,
            "sources": ["vector", "keyword"],
            "vector_rank": 1,
            "keyword_rank": 1,
            "rerank_score": 0.95,
        },
        {
            "chunk_id": str(chunk_a.id),
            "fused_score": 0.3,
            "final_score": 0.3,
            "sources": ["vector"],
            "vector_rank": 2,
            "keyword_rank": None,
            "rerank_score": None,
        },
    ]

    result = MagicMock()
    result.scalars.return_value.all.return_value = [chunk_a, chunk_b]
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=result)

    with patch("app.services.chat.redis_client.get", AsyncMock(return_value=json.dumps(cached_payload))):
        ranked = await retrieve_ranked_chunks(mock_db, "血糖高怎么办？", kb_id, org_id)

    assert [item.chunk.id for item in ranked] == [chunk_b.id, chunk_a.id]
    assert ranked[0].final_score == 0.95
    assert ranked[0].sources == ("vector", "keyword")


@pytest.mark.asyncio
async def test_retrieve_ranked_chunks_falls_back_when_reranker_raises():
    kb_id = uuid4()
    org_id = uuid4()

    chunk_a = _build_chunk()
    chunk_b = _build_chunk()

    vector_result = MagicMock()
    vector_result.scalars.return_value.all.return_value = [chunk_a, chunk_b]
    keyword_result = MagicMock()
    keyword_result.scalars.return_value.all.return_value = [chunk_b]

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[vector_result, keyword_result])

    provider = MagicMock()
    provider.embed_query.return_value = [0.1] * 3
    reranker = AsyncMock()
    reranker.rerank = AsyncMock(side_effect=RuntimeError("reranker down"))

    with patch("app.services.chat.get_embedding_provider", return_value=provider), patch(
        "app.services.chat.get_reranker_provider",
        return_value=reranker,
    ), patch("app.services.chat.redis_client.get", AsyncMock(return_value=None)), patch(
        "app.services.chat.redis_client.setex",
        AsyncMock(return_value=True),
    ):
        ranked = await retrieve_ranked_chunks(mock_db, "血糖高怎么办？", kb_id, org_id)

    assert ranked[0].chunk is chunk_b
    assert ranked[0].final_score == ranked[0].fused_score

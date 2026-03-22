from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.chat import retrieve_chunks
from app.services.rag_ingestion import process_document


@pytest.mark.asyncio
async def test_process_document_uses_runtime_embedding_provider():
    mock_doc = MagicMock()
    mock_doc.id = uuid4()
    mock_doc.kb_id = uuid4()
    mock_doc.org_id = uuid4()
    mock_doc.uploader_id = uuid4()
    mock_doc.status = "pending"
    mock_doc.failed_reason = None

    mock_db = AsyncMock()
    mock_db.get.return_value = mock_doc
    mock_db.add = MagicMock()

    provider = MagicMock()
    provider.embed_documents.return_value = [[0.9] * 3]

    with patch("app.services.rag_ingestion.AsyncSessionLocal") as mock_session_factory, patch(
        "app.services.rag_ingestion.registry.get_embedding",
        return_value=provider,
    ):
        mock_session_factory.return_value.__aenter__.return_value = mock_db

        await process_document(mock_doc.id, "诊断:\n稳定样本")

    provider.embed_documents.assert_called_once()


@pytest.mark.asyncio
async def test_retrieve_chunks_uses_runtime_embedding_provider():
    kb_id = uuid4()
    org_id = uuid4()

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    provider = MagicMock()
    provider.embed_query.return_value = [0.9] * 3

    with patch("app.services.chat.registry.get_embedding", return_value=provider), patch(
        "app.services.chat.redis_client.get",
        AsyncMock(return_value=None),
    ) as mock_cache_get, patch(
        "app.services.chat.redis_client.setex",
        AsyncMock(return_value=True),
    ):
        chunks = await retrieve_chunks(mock_db, "  血糖高怎么办？\n\n", kb_id, org_id)

    assert chunks == []
    provider.embed_query.assert_called_once_with("血糖高怎么办?")
    assert mock_cache_get.await_count == 1
    assert mock_db.execute.await_count == 2


@pytest.mark.asyncio
async def test_process_document_uses_openai_provider_when_configured(monkeypatch):
    mock_doc = MagicMock()
    mock_doc.id = uuid4()
    mock_doc.kb_id = uuid4()
    mock_doc.org_id = uuid4()
    mock_doc.uploader_id = uuid4()
    mock_doc.status = "pending"
    mock_doc.failed_reason = None

    mock_db = AsyncMock()
    mock_db.get.return_value = mock_doc
    mock_db.add = MagicMock()

    mock_client = MagicMock()
    mock_client.embeddings.create.return_value = MagicMock(data=[MagicMock(embedding=[0.8] * 3)])
    mock_openai_client = MagicMock(return_value=mock_client)

    monkeypatch.setattr("app.services.embeddings.settings.EMBEDDING_PROVIDER", "openai")
    monkeypatch.setattr("app.services.embeddings.settings.OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("app.services.embeddings.settings.EMBEDDING_MODEL", "text-embedding-3-small")
    monkeypatch.setattr("app.services.embeddings.settings.EMBEDDING_BASE_URL", "")
    monkeypatch.setattr("app.services.embeddings.settings.LLM_BASE_URL", "")
    monkeypatch.setattr("app.services.embeddings.OpenAI", mock_openai_client)

    with patch("app.services.rag_ingestion.AsyncSessionLocal") as mock_session_factory:
        mock_session_factory.return_value.__aenter__.return_value = mock_db

        await process_document(mock_doc.id, "诊断:\n稳定样本")

    mock_openai_client.assert_called_once_with(
        api_key="test-key",
        base_url="",
    )
    mock_client.embeddings.create.assert_called_once()

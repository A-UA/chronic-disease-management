import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.rag_ingestion import process_document


@pytest.mark.asyncio
async def test_process_document_marks_document_completed_on_success():
    mock_doc = MagicMock()
    mock_doc.id = uuid4()
    mock_doc.kb_id = uuid4()
    mock_doc.org_id = uuid4()
    mock_doc.uploader_id = uuid4()
    mock_doc.status = "pending"

    mock_db = AsyncMock()
    mock_db.get.return_value = mock_doc
    mock_db.add = MagicMock()

    with patch("app.services.rag_ingestion.AsyncSessionLocal") as mock_session_factory, patch(
        "app.services.rag_ingestion.embeddings_model.embed_documents",
        return_value=[[0.1] * 1536],
    ) as mock_embed_documents:
        mock_session_factory.return_value.__aenter__.return_value = mock_db

        await process_document(mock_doc.id, "诊断:\n稳定样本")

    assert mock_db.get.called
    assert mock_db.add.called
    assert mock_embed_documents.called
    assert mock_doc.status == "completed"
    assert mock_doc.failed_reason is None
    assert mock_db.commit.called


@pytest.mark.asyncio
async def test_process_document_marks_document_failed_on_embedding_error():
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

    with patch("app.services.rag_ingestion.AsyncSessionLocal") as mock_session_factory, patch(
        "app.services.rag_ingestion.embeddings_model.embed_documents",
        side_effect=RuntimeError("embedding failed"),
    ):
        mock_session_factory.return_value.__aenter__.return_value = mock_db

        await process_document(mock_doc.id, "诊断:\n异常样本")

    assert mock_doc.status == "failed"
    assert mock_doc.failed_reason == "embedding failed"
    assert mock_db.commit.called

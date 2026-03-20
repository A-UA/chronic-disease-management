import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.rag import process_document

@pytest.mark.asyncio
async def test_process_document():
    # Mock document
    mock_doc = MagicMock()
    mock_doc.id = uuid4()
    mock_doc.kb_id = uuid4()
    mock_doc.org_id = uuid4()
    mock_doc.uploader_id = uuid4()
    mock_doc.status = "pending"
    
    # Mock db session
    mock_db = AsyncMock()
    mock_db.get.return_value = mock_doc
    
    # Mock the AsyncSessionLocal context manager
    with patch("app.services.rag.AsyncSessionLocal") as mock_session_factory:
        mock_session_factory.return_value.__aenter__.return_value = mock_db
        
        file_content = "This is a dummy document content. " * 100
        
        await process_document(mock_doc.id, file_content)
        
        assert mock_db.get.called
        assert mock_db.add.called
        assert mock_doc.status == "completed"
        assert mock_db.commit.called
